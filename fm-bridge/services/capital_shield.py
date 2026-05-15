"""
FM Trading Agency — Capital Shield Service
============================================
Tracks live capital protection state.
Feeds L8 Risk Governor with hard limits.

This is NOT an opinion — it is a hard governance engine.
It CAN veto trades.  The AI agents must obey its output.

Persistent state is stored in ~/.fm_capital_shield.json
so the kill switch survives bridge restarts.

Rules (from spec §10.5 and document 6 item 3):
  Daily DD limit:   1% of capital
  Weekly DD limit:  3% of capital
  Max open risk:    1.25% at any time
  Max per-trade risk: 0.5%
  Cash reserve:     30% minimum (must never be deployed)
  Loss streak:      after 3 consecutive losses → reduce size 50%
  Kill switch:      triggered at daily DD limit, resets at session end
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz

from models import CapitalShield, RiskState
from config import get_settings

import logging
log = logging.getLogger("fm.capital_shield")

_STATE_FILE = Path.home() / ".fm_capital_shield.json"
_IST = pytz.timezone("Asia/Kolkata")
_shield: Optional[CapitalShield] = None


def _seed_daily_pnl_from_journal(today: str, settings) -> float:
    """Query fm-journal for today's closed trades and sum their P&L.
    Returns today's net P&L so the capital shield starts with accurate state.
    Falls back to 0.0 if journal is unavailable.
    """
    journal_url = getattr(settings, "journal_url", "http://localhost:8004")
    try:
        import requests as _req
        r = _req.get(
            f"{journal_url}/api/trades",
            params={"status": "CLOSED", "from_date": today, "to_date": today, "limit": 100},
            timeout=3,
        )
        if r.status_code == 200:
            trades = r.json().get("trades", [])
            total_pnl = sum(float(t.get("net_pnl") or 0) for t in trades)
            if total_pnl != 0:
                log.info("Seeded daily P&L from journal: ₹%.0f (%d trades today)", total_pnl, len(trades))
            return total_pnl
    except Exception as e:
        log.debug("Journal seed failed: %s", e)
    return 0.0


def _load() -> CapitalShield:
    """Load capital shield state from disk.
    
    On a new trading day: resets daily_pnl / daily_dd_pct from fm-journal
    so the risk governor has the right starting P&L even after a bridge restart.
    This fixes the gap where bridge restart mid-session would forget today's P&L.
    """
    settings = get_settings()
    today = datetime.now(_IST).strftime("%Y-%m-%d")

    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text())
            # Same day — trust the persisted state (handles intra-day restarts)
            if data.get("_date") == today:
                data.pop("_date", None)
                shield = CapitalShield(**{k: v for k, v in data.items() if k in CapitalShield.model_fields})
                log.info("Capital shield restored (today's pnl=%.2f, dd=%.3f%%)",
                         shield.daily_pnl, shield.daily_dd_pct)
                return shield
            # New day — reset daily stats but try to seed from journal first
            log.info("New trading day — resetting daily stats")
        except Exception as e:
            log.warning("Failed to load capital shield state: %s — using defaults", e)

    # Try to seed daily_pnl from fm-journal for the current date
    # This ensures the risk governor starts with correct P&L even after bridge restart
    seeded_pnl = _seed_daily_pnl_from_journal(today, settings)
    seeded_dd  = round(abs(min(0, seeded_pnl)) / max(settings.default_capital, 1) * 100, 3)

    shield = CapitalShield(
        capital              = settings.default_capital,
        daily_dd_limit       = settings.daily_dd_limit_pct,
        weekly_dd_limit      = settings.weekly_dd_limit_pct,
        max_open_risk_pct    = 1.25,
        cash_reserve_pct     = settings.cash_reserve_pct,
        max_risk_per_trade   = settings.default_capital * (settings.max_risk_per_trade / 100),
        cash_available       = settings.default_capital * (settings.cash_reserve_pct / 100),
        daily_pnl            = seeded_pnl,
        daily_dd_pct         = seeded_dd,
    )
    # Persist the seeded state
    _save(shield)
    return shield


def _save(shield: CapitalShield) -> None:
    try:
        data = shield.model_dump()
        data["_date"] = datetime.now(_IST).strftime("%Y-%m-%d")
        # Convert datetime to string for JSON
        data["fetched_at"] = data["fetched_at"].isoformat() if hasattr(data.get("fetched_at"), "isoformat") else str(data.get("fetched_at", ""))
        _STATE_FILE.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        log.warning("Failed to save capital shield state: %s", e)


def get_shield() -> CapitalShield:
    """Get current capital shield state."""
    global _shield
    if _shield is None:
        _shield = _load()
    return _shield


def update_pnl(trade_pnl: float) -> CapitalShield:
    """
    Update P&L after a trade closes.
    Recomputes drawdown percentages and risk state.
    Triggers kill switch if daily DD limit breached.
    """
    global _shield
    shield = get_shield()

    shield.daily_pnl  += trade_pnl
    shield.weekly_pnl += trade_pnl

    # Track loss streak
    if trade_pnl < 0:
        shield.loss_streak += 1
    else:
        shield.loss_streak  = 0

    # Drawdown percentages
    shield.daily_dd_pct  = round(abs(min(0, shield.daily_pnl)) / shield.capital * 100, 3)
    shield.weekly_dd_pct = round(abs(min(0, shield.weekly_pnl)) / shield.capital * 100, 3)

    # Kill switch check
    if shield.daily_dd_pct >= shield.daily_dd_limit:
        shield.kill_switch        = True
        shield.kill_switch_reason = (
            f"Daily DD {shield.daily_dd_pct:.2f}% hit limit of {shield.daily_dd_limit:.1f}%"
        )
        shield.trade_authorized   = False
        log.warning("🔴  KILL SWITCH ACTIVE: %s", shield.kill_switch_reason)

    # Risk state
    dd = shield.daily_dd_pct
    if dd >= shield.daily_dd_limit * 0.9:
        shield.risk_state = RiskState.CRITICAL
    elif dd >= shield.daily_dd_limit * 0.6:
        shield.risk_state = RiskState.HIGH
    elif dd >= shield.daily_dd_limit * 0.3:
        shield.risk_state = RiskState.MODERATE
    else:
        shield.risk_state = RiskState.LOW

    # Position sizing (0.5% capital risk rule, halved if loss streak ≥ 3)
    base_risk = shield.capital * 0.005
    if shield.loss_streak >= 3:
        base_risk *= 0.5
        log.info("Loss streak %d — risk budget halved to ₹%.0f", shield.loss_streak, base_risk)
    shield.max_risk_per_trade = round(base_risk, 0)

    _shield = shield
    _save(shield)
    return shield


def compute_unit_count(shield: CapitalShield, stop_distance_pts: float, lot_size: int) -> int:
    """
    How many units (lots) can the trader take given the risk budget?
    units = floor(max_risk_per_trade / (stop_distance × lot_size))
    Always at least 0.
    """
    if stop_distance_pts <= 0 or lot_size <= 0:
        return 0
    units = int(shield.max_risk_per_trade / (stop_distance_pts * lot_size))
    return max(0, units)


def authorize_trade(stop_distance_pts: float, lot_size: int) -> dict:
    """
    Final authorization check before a trade is issued.
    Returns {authorized, unit_count, reason}.
    """
    shield = get_shield()

    if shield.kill_switch:
        return {
            "authorized": False,
            "unit_count": 0,
            "reason": f"Kill switch active: {shield.kill_switch_reason}",
        }
    if shield.weekly_dd_pct >= shield.weekly_dd_limit:
        return {
            "authorized": False,
            "unit_count": 0,
            "reason": f"Weekly DD {shield.weekly_dd_pct:.2f}% exceeds limit {shield.weekly_dd_limit:.1f}%",
        }
    if shield.open_risk_pct >= shield.max_open_risk_pct:
        return {
            "authorized": False,
            "unit_count": 0,
            "reason": f"Open risk {shield.open_risk_pct:.2f}% at max {shield.max_open_risk_pct:.2f}%",
        }

    units = compute_unit_count(shield, stop_distance_pts, lot_size)
    return {
        "authorized": units > 0,
        "unit_count": units,
        "reason": "Authorized" if units > 0 else "Risk budget too small for 1 lot at this stop",
        "risk_per_unit": round(stop_distance_pts * lot_size, 0),
        "total_risk":    round(stop_distance_pts * lot_size * units, 0),
        "risk_pct":      round(stop_distance_pts * lot_size * units / shield.capital * 100, 3),
    }


def reset_kill_switch() -> CapitalShield:
    """Manually reset kill switch (admin action)."""
    shield = get_shield()
    shield.kill_switch        = False
    shield.kill_switch_reason = None
    shield.trade_authorized   = True
    _save(shield)
    log.info("Kill switch reset manually.")
    return shield