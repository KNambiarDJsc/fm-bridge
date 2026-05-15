"""
FM Trading Agency — Regime Engine
====================================
Detects the current market regime from quantitative inputs.

THIS IS DETERMINISTIC QUANT LOGIC — NOT GPT.
The regime is computed from numbers, not narratives.

Regimes:
  BULL_TREND    — price above all MAs, ADX strong, RSI sweet spot
  BEAR_TREND    — price below all MAs, ADX strong, RSI falling
  RANGE         — ADX weak, price oscillating around VWAP
  VOLATILE      — VIX elevated, ATR expanding, regime unclear
  TRAP          — bull/bear trap pattern — FALSE breakout detected
  EVENT_DRIVEN  — macro event dominates (RBI/Fed/expiry)

Output contract:
{
    "regime": "BEARISH_VOLATILE",
    "confidence": 82,
    "sub_regime": "EXPIRY_MANIPULATION",
    "directional_bias": "SHORT",
    "adx": 28.4,
    "vix": 18.2,
    ...
}

This object feeds:
  • L3 Technical agent (reads regime, does NOT recompute it)
  • L7 Strategy Engine (selects strategy archetype)
  • L9 Sovereign (weights confidence multiplier)
  • Opportunity scorer (relative strength component)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import (
    Regime, IndicatorPack, OptionsChain,
    MacroContext, SessionContext
)


# ════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class RegimeResult:
    """
    Regime detection output.
    LLMs read this — they do NOT recompute it.
    """
    regime:           Regime              = Regime.UNKNOWN
    confidence:       int                 = 0       # 0-100
    sub_regime:       Optional[str]       = None    # finer classification
    directional_bias: str                 = "NEUTRAL"   # LONG / SHORT / NEUTRAL

    # Raw inputs (for transparency / debugging)
    adx:              Optional[float]     = None
    vix:              Optional[float]     = None
    rsi:              Optional[float]     = None
    ema_stack:        Optional[str]       = None    # BULL / BEAR / MIXED
    opr_signal:       Optional[str]       = None    # CALL_DOMINANT / PUT_DOMINANT / NEUTRAL
    pcr:              Optional[float]     = None

    # Session modifier
    session_mult:     float               = 1.0
    is_expiry:        bool                = False

    # Why (for L3 to read and interpret — not for L3 to compute)
    reasoning:        list[str]           = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regime":           self.regime.value,
            "confidence":       self.confidence,
            "sub_regime":       self.sub_regime,
            "directional_bias": self.directional_bias,
            "adx":              self.adx,
            "vix":              self.vix,
            "rsi":              self.rsi,
            "ema_stack":        self.ema_stack,
            "opr_signal":       self.opr_signal,
            "pcr":              self.pcr,
            "session_mult":     self.session_mult,
            "is_expiry":        self.is_expiry,
            "reasoning":        self.reasoning,
        }


# ════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ════════════════════════════════════════════════════════════════

@dataclass
class RegimeFeatures:
    """Raw features fed into the regime classifier."""
    # Technical
    adx:           float = 20.0
    rsi:           float = 50.0
    ema_stack:     str   = "MIXED"   # BULL / BEAR / MIXED
    price_vs_vwap: str   = "ABOVE"  # ABOVE / BELOW
    macd_dir:      str   = "BULL"   # BULL / BEAR
    atr_pct:       float = 1.0      # ATR as % of price
    bb_width:      float = 2.0      # Bollinger Band width %
    supertrend:    str   = "LONG"   # LONG / SHORT

    # Macro
    vix:           float = 15.0
    oil_shock:     bool  = False
    macro_risk_ctx: str  = "TRANSITION"  # RISK_ON / RISK_OFF / TRANSITION

    # Options
    opr_signal:    str   = "NEUTRAL"  # CALL_DOMINANT / PUT_DOMINANT / NEUTRAL
    pcr:           float = 1.0
    dte:           int   = 3
    is_expiry:     bool  = False

    # Session
    session:       str   = "MIDDAY_CHOP"
    session_mult:  float = 1.0


def extract_features(
    ind:     Optional[IndicatorPack],
    oc:      Optional[OptionsChain],
    macro:   Optional[MacroContext],
    session: Optional[SessionContext],
) -> RegimeFeatures:
    """Extract numeric features from all context objects."""
    f = RegimeFeatures()

    if ind:
        f.adx           = ind.adx          or 20.0
        f.rsi           = ind.rsi          or 50.0
        f.ema_stack     = ind.ema_stack    or "MIXED"
        f.macd_dir      = ind.macd_dir     or "BULL"
        f.atr_pct       = ind.atr_pct      or 1.0
        f.bb_width      = ind.bb_width     or 2.0
        f.supertrend    = ind.supertrend_dir or "LONG"
        spot = ind.spot or 1
        if ind.vwap:
            f.price_vs_vwap = "ABOVE" if spot > ind.vwap else "BELOW"

    if oc:
        f.opr_signal = oc.opr_signal or "NEUTRAL"
        f.pcr        = oc.pcr        or 1.0
        f.dte        = oc.dte
        f.is_expiry  = oc.is_expiry_day

    if macro:
        f.vix          = macro.india_vix   or 15.0
        f.oil_shock    = macro.oil_shock_active
        f.macro_risk_ctx = macro.risk_context or "TRANSITION"

    if session:
        f.session       = session.session.value
        f.session_mult  = session.session_confidence_multiplier
        f.is_expiry     = f.is_expiry or session.is_expiry_day

    return f


# ════════════════════════════════════════════════════════════════
# REGIME RULES (deterministic — no ML, no GPT)
# ════════════════════════════════════════════════════════════════
# Each rule returns (score_delta, reason_string) if it fires.
# Score starts at 50.  Final score mapped to confidence.

def _classify(f: RegimeFeatures) -> RegimeResult:
    """
    Rule-based regime classifier.
    Returns a RegimeResult with regime, confidence, and reasoning.
    """
    reasons: list[str] = []
    bull_score = 0    # +ve = bullish, -ve = bearish
    trend_strength = 0
    volatile_score = 0

    # ── EMA Stack ─────────────────────────────────────────────────
    if f.ema_stack == "BULL":
        bull_score    += 30
        trend_strength += 20
        reasons.append("EMA stack bullish (9>20>50)")
    elif f.ema_stack == "BEAR":
        bull_score    -= 30
        trend_strength += 20
        reasons.append("EMA stack bearish (9<20<50)")
    else:
        reasons.append("EMA stack mixed — no clear trend")

    # ── RSI ───────────────────────────────────────────────────────
    if f.rsi > 60:
        bull_score += 15
        reasons.append(f"RSI {f.rsi:.0f} — bullish momentum zone")
    elif f.rsi < 40:
        bull_score -= 15
        reasons.append(f"RSI {f.rsi:.0f} — bearish momentum zone")
    elif 50 <= f.rsi <= 65:
        bull_score += 8
        reasons.append(f"RSI {f.rsi:.0f} — sweet spot")

    # ── MACD ──────────────────────────────────────────────────────
    if f.macd_dir == "BULL":
        bull_score    += 10
        trend_strength += 5
        reasons.append("MACD bullish cross")
    elif f.macd_dir == "BEAR":
        bull_score    -= 10
        trend_strength += 5
        reasons.append("MACD bearish cross")

    # ── VWAP ──────────────────────────────────────────────────────
    if f.price_vs_vwap == "ABOVE":
        bull_score += 10
        reasons.append("Price above VWAP — intraday bullish")
    else:
        bull_score -= 10
        reasons.append("Price below VWAP — intraday bearish")

    # ── Supertrend ────────────────────────────────────────────────
    if f.supertrend == "LONG":
        bull_score += 10
        reasons.append("Supertrend: LONG signal")
    elif f.supertrend == "SHORT":
        bull_score -= 10
        reasons.append("Supertrend: SHORT signal")

    # ── ADX (trend strength, not direction) ───────────────────────
    if f.adx > 25:
        trend_strength += 30
        reasons.append(f"ADX {f.adx:.0f} — STRONG trend")
    elif f.adx > 20:
        trend_strength += 15
        reasons.append(f"ADX {f.adx:.0f} — moderate trend")
    else:
        trend_strength -= 10
        reasons.append(f"ADX {f.adx:.0f} — WEAK trend (range/chop likely)")

    # ── Volatility (VIX + ATR) ────────────────────────────────────
    if f.vix > 22:
        volatile_score += 40
        reasons.append(f"VIX {f.vix:.1f} — STRESSED market")
    elif f.vix > 18:
        volatile_score += 20
        reasons.append(f"VIX {f.vix:.1f} — elevated volatility")
    elif f.vix < 13:
        volatile_score -= 10
        reasons.append(f"VIX {f.vix:.1f} — calm market")

    if f.atr_pct > 1.5:
        volatile_score += 15
        reasons.append(f"ATR% {f.atr_pct:.1f} — expanding range")

    # ── Bollinger squeeze ─────────────────────────────────────────
    if f.bb_width and f.bb_width < 1.5:
        volatile_score += 10
        reasons.append("Bollinger squeeze — breakout pending")

    # ── OPR signal ────────────────────────────────────────────────
    if f.opr_signal == "PUT_DOMINANT":
        bull_score += 12
        reasons.append("OPR: PUT_DOMINANT — institutions hedging longs (bullish)")
    elif f.opr_signal == "CALL_DOMINANT":
        bull_score -= 12
        reasons.append("OPR: CALL_DOMINANT — call writing/covering (bearish)")

    # ── PCR ───────────────────────────────────────────────────────
    if f.pcr > 1.3:
        bull_score += 8
        reasons.append(f"PCR {f.pcr:.2f} — bullish (heavy put buying)")
    elif f.pcr < 0.7:
        bull_score -= 8
        reasons.append(f"PCR {f.pcr:.2f} — bearish (call dominance)")

    # ── Macro ─────────────────────────────────────────────────────
    if f.oil_shock:
        bull_score -= 25
        reasons.append("Oil shock ACTIVE — LONG positions vetoed")
    if f.macro_risk_ctx == "RISK_OFF":
        bull_score -= 15
        reasons.append("Macro: RISK_OFF context")
    elif f.macro_risk_ctx == "RISK_ON":
        bull_score += 10
        reasons.append("Macro: RISK_ON context")

    # ── Expiry day special rules ──────────────────────────────────
    sub_regime = None
    if f.is_expiry:
        volatile_score += 20
        sub_regime = "EXPIRY_MANIPULATION"
        reasons.append("EXPIRY DAY — Max Pain gravity dominant, manipulation risk HIGH")

    # ── Session modifier ──────────────────────────────────────────
    if f.session in ("OPENING_VOLATILITY", "EXPIRY_MORNING"):
        volatile_score += 15
        reasons.append(f"Session: {f.session} — reduced signal reliability")

    # ════════════════════════════════════════════════════════════
    # REGIME CLASSIFICATION
    # ════════════════════════════════════════════════════════════
    abs_bull = abs(bull_score)
    directional_bias = "LONG" if bull_score > 0 else ("SHORT" if bull_score < 0 else "NEUTRAL")

    # Determine primary regime
    if volatile_score >= 50:
        if abs_bull >= 30:
            regime = Regime.VOLATILE
            sub_regime = sub_regime or ("VOLATILE_BULL" if bull_score > 0 else "VOLATILE_BEAR")
        else:
            regime = Regime.VOLATILE
    elif trend_strength >= 35 and abs_bull >= 25:
        regime = Regime.BULL_TREND if bull_score > 0 else Regime.BEAR_TREND
    elif trend_strength < 10 and volatile_score < 30:
        regime = Regime.RANGE
        directional_bias = "NEUTRAL"
        sub_regime = sub_regime or "RANGE_BOUND"
        reasons.append("Low ADX + low volatility → range-bound")
    elif f.is_expiry:
        regime = Regime.EVENT_DRIVEN
        sub_regime = "EXPIRY_DAY"
    elif f.macro_risk_ctx == "RISK_OFF" or f.oil_shock:
        regime = Regime.EVENT_DRIVEN
        sub_regime = sub_regime or "MACRO_RISK"
    else:
        regime = Regime.VOLATILE

    # ── Confidence (based on signal alignment) ────────────────────
    # High confidence when many signals agree; low when mixed
    signal_agreement = abs_bull + trend_strength - volatile_score // 2
    confidence = max(30, min(95, 50 + signal_agreement // 2))
    # Apply session multiplier
    confidence = int(confidence * f.session_mult)
    confidence = max(20, min(95, confidence))

    return RegimeResult(
        regime           = regime,
        confidence       = confidence,
        sub_regime       = sub_regime,
        directional_bias = directional_bias,
        adx              = f.adx,
        vix              = f.vix,
        rsi              = f.rsi,
        ema_stack        = f.ema_stack,
        opr_signal       = f.opr_signal,
        pcr              = f.pcr,
        session_mult     = f.session_mult,
        is_expiry        = f.is_expiry,
        reasoning        = reasons,
    )


# ════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════

def detect_regime(
    ind:     Optional[IndicatorPack]   = None,
    oc:      Optional[OptionsChain]    = None,
    macro:   Optional[MacroContext]    = None,
    session: Optional[SessionContext]  = None,
) -> RegimeResult:
    """
    Main entry point. Pass in the data objects from fm-bridge.
    Returns a RegimeResult. All downstream agents read this object.
    """
    features = extract_features(ind, oc, macro, session)
    return _classify(features)