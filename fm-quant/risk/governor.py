"""
FM Trading Agency — Risk Governor
====================================
Hard capital governance engine. This is NOT an opinion module.
It VETOES trades. The AI agents MUST obey its output.

From document 6, gap 3:
  Daily DD limit   1%
  Weekly DD        3%
  Max exposure     capped at 1.25%
  Overnight risk   limited (no unhedged overnight above 0.5%)
  Hedge mandatory  yes — always compute hedge cost
  Volatility sizing dynamic — ATR-based lot count

The Risk Governor produces a RiskDecision:
  authorized: bool   — if False, no trade is placed, period.
  unit_count:  int   — how many lots to trade
  veto_reason: str   — why it was vetoed if authorized=False
  mandatory_hedge: HedgeRequirement — hedge IS required, not optional
  size_reduction_pct: float — if streak/DD, reduce size by this much

This runs BEFORE L9 Sovereign. L9 cannot override the Risk Governor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import CapitalShield, RiskState, SessionContext

import logging
log = logging.getLogger("fm.quant.risk")


# ════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class HedgeRequirement:
    mandatory:       bool  = True
    max_cost_pct:    float = 2.0     # max hedge cost as % of capital
    reason:          str   = ""


@dataclass
class RiskDecision:
    """
    The Risk Governor's final word.
    authorized=False means NO TRADE, full stop.
    """
    authorized:          bool   = True
    unit_count:          int    = 0
    max_risk_per_trade:  float  = 0.0   # ₹
    veto_reason:         str    = ""
    risk_state:          RiskState = RiskState.LOW

    # Size modifiers
    size_reduction_pct:  float  = 0.0   # e.g. 50 = halve size (loss streak rule)
    volatility_sizing:   bool   = True  # use ATR-based sizing

    # Hedge requirements
    hedge:               HedgeRequirement = None

    # Context
    daily_dd_pct:        float  = 0.0
    weekly_dd_pct:       float  = 0.0
    kill_switch:         bool   = False
    loss_streak:         int    = 0

    # Warnings (non-blocking — inform the trader)
    warnings:            list[str] = None

    def __post_init__(self):
        if self.hedge is None:
            self.hedge = HedgeRequirement()
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> dict:
        return {
            "authorized":          self.authorized,
            "unit_count":          self.unit_count,
            "max_risk_per_trade":  self.max_risk_per_trade,
            "veto_reason":         self.veto_reason,
            "risk_state":          self.risk_state.value,
            "size_reduction_pct":  self.size_reduction_pct,
            "daily_dd_pct":        self.daily_dd_pct,
            "weekly_dd_pct":       self.weekly_dd_pct,
            "kill_switch":         self.kill_switch,
            "loss_streak":         self.loss_streak,
            "hedge_mandatory":     self.hedge.mandatory,
            "hedge_max_cost_pct":  self.hedge.max_cost_pct,
            "warnings":            self.warnings,
        }


# ════════════════════════════════════════════════════════════════
# POSITION SIZING (ATR-based)
# ════════════════════════════════════════════════════════════════

def compute_position_size(
    capital:        float,
    risk_pct:       float,          # % of capital to risk
    stop_distance:  float,          # SL distance in points
    lot_size:       int,
    size_reduction: float = 0.0,    # 0-100 reduction %
) -> tuple[int, float]:
    """
    ATR / stop-distance based position sizing.
    Returns (unit_count, risk_per_unit_rs)

    Rule: never risk more than risk_pct% of capital on one trade.
    units = floor(capital × risk_pct / 100 / (stop_distance × lot_size))
    """
    if stop_distance <= 0 or lot_size <= 0:
        return 0, 0.0

    risk_budget = capital * (risk_pct / 100)
    # Apply size reduction (loss streak rule)
    if size_reduction > 0:
        risk_budget *= (1 - size_reduction / 100)

    risk_per_unit = stop_distance * lot_size
    units = int(math.floor(risk_budget / risk_per_unit))
    return max(0, units), round(risk_per_unit, 0)


# ════════════════════════════════════════════════════════════════
# HARD VETO CHECKS
# ════════════════════════════════════════════════════════════════

def _check_kill_switch(shield: CapitalShield) -> Optional[str]:
    if shield.kill_switch:
        return f"Kill switch ACTIVE: {shield.kill_switch_reason or 'Daily DD limit hit'}"
    return None


def _check_daily_dd(shield: CapitalShield) -> Optional[str]:
    if shield.daily_dd_pct >= shield.daily_dd_limit:
        return (
            f"Daily DD {shield.daily_dd_pct:.2f}% has hit limit "
            f"{shield.daily_dd_limit:.1f}% — no new trades today."
        )
    return None


def _check_weekly_dd(shield: CapitalShield) -> Optional[str]:
    if shield.weekly_dd_pct >= shield.weekly_dd_limit:
        return (
            f"Weekly DD {shield.weekly_dd_pct:.2f}% has hit limit "
            f"{shield.weekly_dd_limit:.1f}% — no new trades this week."
        )
    return None


def _check_open_risk(shield: CapitalShield) -> Optional[str]:
    if shield.open_risk_pct >= shield.max_open_risk_pct:
        return (
            f"Open risk {shield.open_risk_pct:.2f}% at max "
            f"{shield.max_open_risk_pct:.2f}% — close existing positions first."
        )
    return None


def _check_session(session: Optional[SessionContext]) -> Optional[str]:
    if not session:
        return None
    if session.session.value in ("PRE_OPEN", "POST_CLOSE"):
        return f"Market session {session.session.value} — trading not active."
    return None


# ════════════════════════════════════════════════════════════════
# SIZE REDUCTION TRIGGERS
# ════════════════════════════════════════════════════════════════

def _compute_size_reduction(shield: CapitalShield) -> tuple[float, list[str]]:
    """Returns (reduction_pct, reasons)."""
    reduction = 0.0
    reasons: list[str] = []

    # Loss streak rule: 3+ consecutive losses → halve size
    if shield.loss_streak >= 3:
        reduction = 50.0
        reasons.append(f"Loss streak {shield.loss_streak} — size halved (spec §10.5)")

    # Approaching daily DD limit (70%+ used) → reduce 30%
    dd_used_pct = shield.daily_dd_pct / shield.daily_dd_limit * 100 if shield.daily_dd_limit > 0 else 0
    if dd_used_pct >= 70 and reduction == 0:
        reduction = 30.0
        reasons.append(f"Daily DD {shield.daily_dd_pct:.2f}% ({dd_used_pct:.0f}% of limit) — size reduced 30%")

    return reduction, reasons


# ════════════════════════════════════════════════════════════════
# HEDGE REQUIREMENT DETERMINATION
# ════════════════════════════════════════════════════════════════

def _determine_hedge_req(
    shield:   CapitalShield,
    vix:      Optional[float],
    dte_days: int,
) -> HedgeRequirement:
    """
    Determine if hedge is mandatory and what the cost cap is.

    Rules:
    • Hedge always mandatory for overnight positions (holding_period != INTRADAY)
    • Hedge mandatory if VIX > 20 (high volatility)
    • Hedge mandatory if DTE <= 1 (expiry day — gamma risk)
    • Max hedge cost: 2% of capital (spec §D3)
    """
    vix_val = vix or 15.0

    mandatory = (
        vix_val > 20 or
        dte_days <= 1 or
        shield.risk_state in (RiskState.HIGH, RiskState.CRITICAL)
    )

    reason_parts = []
    if vix_val > 20:
        reason_parts.append(f"VIX {vix_val:.1f} > 20")
    if dte_days <= 1:
        reason_parts.append("expiry day — gamma risk")
    if shield.risk_state in (RiskState.HIGH, RiskState.CRITICAL):
        reason_parts.append(f"capital shield: {shield.risk_state.value}")

    reason = ", ".join(reason_parts) if reason_parts else "standard protection"

    return HedgeRequirement(
        mandatory    = mandatory,
        max_cost_pct = 2.0,
        reason       = f"Hedge mandatory: {reason}" if mandatory else "Hedge recommended",
    )


# ════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════

def evaluate(
    shield:         CapitalShield,
    stop_distance:  float,          # SL distance in index points
    lot_size:       int     = 25,
    session:        Optional[SessionContext] = None,
    vix:            Optional[float]  = None,
    dte_days:       int     = 3,
) -> RiskDecision:
    """
    Main Risk Governor entry point.

    Returns RiskDecision.
    If authorized=False → trade is vetoed. Period. No override.
    If authorized=True → trade is allowed with the computed unit_count.

    Called by fm-agents L8 Risk Governor node with the live CapitalShield.
    """
    warnings: list[str] = []

    # ── Hard vetoes (any one is enough to block) ──────────────────
    veto = (
        _check_kill_switch(shield) or
        _check_daily_dd(shield)    or
        _check_weekly_dd(shield)   or
        _check_open_risk(shield)   or
        _check_session(session)
    )
    if veto:
        return RiskDecision(
            authorized          = False,
            unit_count          = 0,
            veto_reason         = veto,
            risk_state          = shield.risk_state,
            kill_switch         = shield.kill_switch,
            daily_dd_pct        = shield.daily_dd_pct,
            weekly_dd_pct       = shield.weekly_dd_pct,
            loss_streak         = shield.loss_streak,
            hedge               = _determine_hedge_req(shield, vix, dte_days),
        )

    # ── Size reduction (non-blocking, but reduces size) ───────────
    size_reduction, reduction_reasons = _compute_size_reduction(shield)
    warnings.extend(reduction_reasons)

    # ── Session warnings (non-blocking) ──────────────────────────
    if session:
        sm = session.session_confidence_multiplier
        if sm < 0.8:
            warnings.append(
                f"Session {session.session.value} — confidence mult {sm:.1f}x, "
                "consider smaller size or waiting."
            )

    # ── Position sizing ───────────────────────────────────────────
    unit_count, risk_per_unit = compute_position_size(
        capital        = shield.capital,
        risk_pct       = 0.5,   # 0.5% capital risk per trade (spec §8)
        stop_distance  = stop_distance,
        lot_size       = lot_size,
        size_reduction = size_reduction,
    )

    if unit_count == 0:
        return RiskDecision(
            authorized         = False,
            unit_count         = 0,
            max_risk_per_trade = shield.max_risk_per_trade,
            veto_reason        = (
                f"Position sizing: 0 lots available at ₹{stop_distance:.0f} stop "
                f"(risk budget ₹{shield.max_risk_per_trade:.0f}, lot size {lot_size})"
            ),
            risk_state         = shield.risk_state,
            daily_dd_pct       = shield.daily_dd_pct,
            weekly_dd_pct      = shield.weekly_dd_pct,
            loss_streak        = shield.loss_streak,
            hedge              = _determine_hedge_req(shield, vix, dte_days),
            warnings           = warnings,
        )

    # ── Warning: approaching DD limit ─────────────────────────────
    dd_used = shield.daily_dd_pct / shield.daily_dd_limit * 100 if shield.daily_dd_limit else 0
    if dd_used >= 50:
        warnings.append(
            f"⚠ Daily DD {shield.daily_dd_pct:.2f}% ({dd_used:.0f}% of {shield.daily_dd_limit:.1f}% limit)"
        )

    return RiskDecision(
        authorized          = True,
        unit_count          = unit_count,
        max_risk_per_trade  = risk_per_unit * unit_count,
        risk_state          = shield.risk_state,
        size_reduction_pct  = size_reduction,
        daily_dd_pct        = shield.daily_dd_pct,
        weekly_dd_pct       = shield.weekly_dd_pct,
        kill_switch         = False,
        loss_streak         = shield.loss_streak,
        hedge               = _determine_hedge_req(shield, vix, dte_days),
        warnings            = warnings,
    )