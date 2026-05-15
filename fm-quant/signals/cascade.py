"""
FM Trading Agency — Always-Trade Decision Cascade
===================================================
The heart of the Always-Trade mandate (spec §2.1).

This is the QUANT LAYER of the Sovereign Orchestrator (document 6, gap 1).
It does NOT call any LLM. It produces a structured CascadeDecision
that the LangGraph orchestrator (Phase 3 fm-orchestrator) will enrich
with AI reasoning before generating the FinalVerdict.

The cascade runs AFTER all agents have produced their outputs.
It resolves conflicts, enforces the Always-Trade mandate, and
selects the trade type + direction.

Decision flow (spec §2.1, §10.4):
  STEP 1: Kill switch active → WAIT (size-reduce, not blocked)
  STEP 2: Synthetic data → WAIT
  STEP 3: L9 score ≥ 65 + LONG → BULL_TRADE
  STEP 4: L9 score ≥ 65 + SHORT → BEAR_TRADE
  STEP 5: Oil shock + L4 short viable → BEAR_TRADE (SHORT_SELL_SEARCH)
  STEP 6: Bull trap detected → BEAR_TRADE (bear pivot entry)
  STEP 7: ADX < 15 + VIX 14-20 → HEDGE_TRADE (Iron Condor)
  STEP 8: Expiry day + Max Pain gravity → HEDGE_TRADE (Max Pain pin)
  STEP 9: Macro veto + options flow clear → options-only directional
  STEP 10: All blocked → WAIT (≤ 30 min, specific re-entry trigger)

The WAIT verdict is NOT NO_TRADE.
WAIT always includes: re_entry_trigger, re_entry_window_minutes (≤ 30),
                       re_entry_condition, pivot_plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import (
    VerdictType, Regime, IndicatorPack, OptionsChain,
    MacroContext, SessionContext, CapitalShield,
)
from regime.engine import RegimeResult

import logging
log = logging.getLogger("fm.quant.cascade")


# ════════════════════════════════════════════════════════════════
# INPUT CONTRACT — all data the cascade needs
# ════════════════════════════════════════════════════════════════

@dataclass
class CascadeInput:
    """Everything the cascade needs to make a decision."""
    # Computed by Phase 2 quant engine
    regime_result:       Optional[RegimeResult]   = None
    execution_score:     int                       = 0      # 0-100 (from L9)
    directional_bias:    str                       = "NEUTRAL"  # LONG/SHORT/NEUTRAL

    # From OptionsChain
    adx:                 float  = 20.0
    vix:                 float  = 15.0
    oil_shock:           bool   = False
    bull_trap:           bool   = False     # L4 detected bull trap
    bear_pivot:          bool   = False     # L4 has a bear pivot entry ready
    options_flow_clear:  bool   = True      # L6 gives green light
    max_pain:            Optional[float] = None
    dte:                 int    = 3

    # Capital shield
    kill_switch:         bool   = False
    data_is_synthetic:   bool   = False

    # Current price
    spot:                float  = 0.0

    # Session
    is_expiry_day:       bool   = False
    session_mult:        float  = 1.0
    ist_time:            str    = "11:00"


# ════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class CascadeDecision:
    """
    The cascade's verdict.
    This is NOT a FinalVerdict yet — it needs AI enrichment in Phase 3.
    It IS the contract that tells the orchestrator what TYPE of trade to issue.
    """
    verdict:         VerdictType
    direction:       str           # LONG / SHORT / NEUTRAL
    cascade_step:    int           # which step fired (1-10)
    cascade_reason:  str           # why this step fired

    # Hedge type selection (for hedge_calc.py to use)
    hedge_type:      str           = "BUY_PE_HEDGE"  # BUY_PE / BUY_CE / IRON_CONDOR / NONE

    # Wait fields (only populated if verdict == WAIT)
    re_entry_trigger:    Optional[str] = None
    re_entry_condition:  Optional[str] = None
    re_entry_window_min: int           = 30
    pivot_plan:          Optional[str] = None

    # Context
    execution_score: int = 0
    session_mult:    float = 1.0
    confidence:      int = 0

    def to_dict(self) -> dict:
        return {
            "verdict":            self.verdict.value,
            "direction":          self.direction,
            "cascade_step":       self.cascade_step,
            "cascade_reason":     self.cascade_reason,
            "hedge_type":         self.hedge_type,
            "re_entry_trigger":   self.re_entry_trigger,
            "re_entry_condition": self.re_entry_condition,
            "re_entry_window_min":self.re_entry_window_min,
            "pivot_plan":         self.pivot_plan,
            "execution_score":    self.execution_score,
            "session_mult":       self.session_mult,
            "confidence":         self.confidence,
        }


# ════════════════════════════════════════════════════════════════
# WAIT SIGNAL BUILDER
# ════════════════════════════════════════════════════════════════

def _wait(
    spot:         float,
    reason:       str,
    step:         int,
    bull_trigger: Optional[float] = None,
    bear_trigger: Optional[float] = None,
    window_min:   int = 30,
) -> CascadeDecision:
    """Build a WAIT verdict with specific re-entry trigger (never vague)."""
    bT = bull_trigger or round(spot * 1.002, 0)
    sT = bear_trigger or round(spot * 0.998, 0)

    re_entry = (
        f"BULL: 15-min close > {bT:.0f} on volume > 1.15× avg | "
        f"BEAR: 15-min close < {sT:.0f} with rising volume"
    )
    pivot = (
        f"If no trigger in {window_min} min → re-scan. "
        f"If BULL trigger not met by {window_min} min, evaluate BEAR at {sT:.0f}."
    )
    return CascadeDecision(
        verdict              = VerdictType.WAIT,
        direction            = "NEUTRAL",
        cascade_step         = step,
        cascade_reason       = reason,
        hedge_type           = "NONE",
        re_entry_trigger     = f"BULL: {bT:.0f} / BEAR: {sT:.0f}",
        re_entry_condition   = re_entry,
        re_entry_window_min  = min(30, window_min),
        pivot_plan           = pivot,
    )


# ════════════════════════════════════════════════════════════════
# CASCADE
# ════════════════════════════════════════════════════════════════

def run_cascade(ci: CascadeInput) -> CascadeDecision:
    """
    Run the Always-Trade decision cascade.

    Returns a CascadeDecision — the quant layer of the Sovereign Orchestrator.
    Every path produces a verdict. There is no void return.
    """
    score = ci.execution_score
    spot  = ci.spot or 0
    SCORE_THRESHOLD = 65

    # ── STEP 1: Kill switch → WAIT (not blocked, just reduce size) ─
    if ci.kill_switch:
        return _wait(
            spot    = spot,
            reason  = "Kill switch ACTIVE — daily DD limit hit. Size reduced to 50% per spec §10.5.",
            step    = 1,
            window_min = 30,
        )

    # ── STEP 2: Synthetic data → WAIT ─────────────────────────────
    if ci.data_is_synthetic:
        return _wait(
            spot   = spot,
            reason = "Synthetic / insufficient data — bridge disconnected. Connect Zerodha bridge.",
            step   = 2,
            window_min = 30,
        )

    # ── STEP 3: Score ≥ 65, LONG direction → BULL TRADE ──────────
    if score >= SCORE_THRESHOLD and ci.directional_bias == "LONG" and not ci.oil_shock:
        return CascadeDecision(
            verdict       = VerdictType.BULL_TRADE,
            direction     = "LONG",
            cascade_step  = 3,
            cascade_reason= f"Score {score} ≥ {SCORE_THRESHOLD}, LONG direction, oil clear → BULL",
            hedge_type    = "BUY_PE_HEDGE",
            execution_score = score,
            session_mult  = ci.session_mult,
            confidence    = min(95, score),
        )

    # ── STEP 4: Score ≥ 65, SHORT direction → BEAR TRADE ──────────
    if score >= SCORE_THRESHOLD and ci.directional_bias == "SHORT":
        return CascadeDecision(
            verdict       = VerdictType.BEAR_TRADE,
            direction     = "SHORT",
            cascade_step  = 4,
            cascade_reason= f"Score {score} ≥ {SCORE_THRESHOLD}, SHORT direction → BEAR",
            hedge_type    = "BUY_CE_HEDGE",
            execution_score = score,
            session_mult  = ci.session_mult,
            confidence    = min(95, score),
        )

    # ── STEP 5: Oil shock + L4 short viable → BEAR (oil confirmation)
    if ci.oil_shock and ci.bear_pivot:
        return CascadeDecision(
            verdict       = VerdictType.BEAR_TRADE,
            direction     = "SHORT",
            cascade_step  = 5,
            cascade_reason= f"Oil shock active (LONG blocked) + L4 bear pivot viable → BEAR SHORT_SELL_SEARCH",
            hedge_type    = "BUY_CE_HEDGE",
            execution_score = max(60, score),
            confidence    = 72,
        )

    # ── STEP 6: Bull trap detected → BEAR pivot entry ─────────────
    if ci.bull_trap and ci.bear_pivot:
        return CascadeDecision(
            verdict       = VerdictType.BEAR_TRADE,
            direction     = "SHORT",
            cascade_step  = 6,
            cascade_reason= "L4 BULL TRAP detected — SHORT_SELL_SEARCH activated. Bear pivot entry available.",
            hedge_type    = "BUY_CE_HEDGE",
            execution_score = max(55, score),
            confidence    = 68,
        )

    # ── STEP 7: ADX < 15 + VIX 14-20 → HEDGE (Iron Condor) ───────
    ADX_HEDGE_MAX   = 15
    VIX_HEDGE_MIN   = 14
    VIX_HEDGE_MAX   = 20
    if ci.adx < ADX_HEDGE_MAX and VIX_HEDGE_MIN <= ci.vix <= VIX_HEDGE_MAX:
        return CascadeDecision(
            verdict       = VerdictType.HEDGE_TRADE,
            direction     = "NEUTRAL",
            cascade_step  = 7,
            cascade_reason= (
                f"ADX {ci.adx:.0f} < {ADX_HEDGE_MAX} (weak trend) + "
                f"VIX {ci.vix:.1f} in {VIX_HEDGE_MIN}-{VIX_HEDGE_MAX} range → IRON CONDOR at Max Pain"
            ),
            hedge_type    = "IRON_CONDOR",
            execution_score = 70,
            confidence    = 70,
        )

    # ── STEP 8: Expiry day + Max Pain gravity → MAX PAIN PLAY ─────
    if ci.is_expiry_day and ci.max_pain and spot > 0:
        pull = abs(ci.max_pain - spot)
        if pull > 100:   # significant distance from Max Pain
            return CascadeDecision(
                verdict       = VerdictType.HEDGE_TRADE,
                direction     = "NEUTRAL",
                cascade_step  = 8,
                cascade_reason= (
                    f"EXPIRY DAY — Max Pain {ci.max_pain:.0f} vs spot {spot:.0f} "
                    f"({pull:.0f} pts pull). Sell ATM straddle at Max Pain."
                ),
                hedge_type    = "IRON_CONDOR",
                execution_score = 75,
                confidence    = 72,
            )

    # ── STEP 9: Macro veto + L6 options flow clear → options-only ─
    if (ci.oil_shock or (ci.regime_result and ci.regime_result.regime == Regime.EVENT_DRIVEN)) \
            and ci.options_flow_clear:
        direction = "SHORT" if ci.directional_bias in ("SHORT", "NEUTRAL") else "LONG"
        return CascadeDecision(
            verdict       = VerdictType.BEAR_TRADE if direction == "SHORT" else VerdictType.BULL_TRADE,
            direction     = direction,
            cascade_step  = 9,
            cascade_reason= (
                f"Macro/event veto blocks futures — options-only {direction} via L6 flow. "
                "Buy ATM PE/CE only — defined risk = max loss."
            ),
            hedge_type    = "NONE",   # option premium IS the hedge
            execution_score = 60,
            confidence    = 62,
        )

    # ── STEP 10: All paths blocked → WAIT ────────────────────────
    return _wait(
        spot       = spot,
        reason     = (
            f"Mixed signals — no edge ≥ {SCORE_THRESHOLD} (score={score}). "
            "No clear bull, bear, or hedge setup. "
            "Waiting for market to show its hand."
        ),
        step       = 10,
        window_min = 30,
    )


# ════════════════════════════════════════════════════════════════
# CONVENIENCE: build CascadeInput from Phase 1 bridge objects
# ════════════════════════════════════════════════════════════════

def build_cascade_input(
    ind:            Optional[IndicatorPack]  = None,
    oc:             Optional[OptionsChain]   = None,
    macro:          Optional[MacroContext]   = None,
    session:        Optional[SessionContext] = None,
    shield:         Optional[CapitalShield]  = None,
    regime_result:  Optional[RegimeResult]   = None,
    execution_score: int  = 0,
    bull_trap:      bool  = False,
    bear_pivot:     bool  = False,
    data_is_synthetic: bool = False,
) -> CascadeInput:
    """Build a CascadeInput from all the Phase 1 bridge objects."""
    directional_bias = "NEUTRAL"
    if regime_result:
        directional_bias = regime_result.directional_bias

    return CascadeInput(
        regime_result      = regime_result,
        execution_score    = execution_score,
        directional_bias   = directional_bias,
        adx                = (ind.adx        if ind    else 20.0) or 20.0,
        vix                = (macro.india_vix if macro  else 15.0) or 15.0,
        oil_shock          = (macro.oil_shock_active if macro else False),
        bull_trap          = bull_trap,
        bear_pivot         = bear_pivot,
        options_flow_clear = (oc is not None),
        max_pain           = (oc.max_pain    if oc     else None),
        dte                = (oc.dte         if oc     else 3),
        kill_switch        = (shield.kill_switch  if shield else False),
        data_is_synthetic  = data_is_synthetic,
        spot               = (ind.spot       if ind    else 0.0) or 0.0,
        is_expiry_day      = (session.is_expiry_day if session else False),
        session_mult       = (session.session_confidence_multiplier if session else 1.0),
        ist_time           = (session.ist_time if session else "11:00"),
    )