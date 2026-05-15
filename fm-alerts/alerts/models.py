"""
FM Trading Agency — Alert Models
====================================
Pydantic models for every alert type.
Every alert has a type, priority, and formatted Telegram message.

Alert hierarchy (all 5 types from Phase 6 spec):
  1. MORNING_BRIEFING       — 9:15 AM full analysis summary
  2. ENTRY_ZONE             — price entered the entry zone
  3. TARGET_HIT             — T1 or T2 hit → partial exit signal
  4. HEDGE_ADJUSTMENT       — Iron Condor: price within 1% of short strike
  5. KILL_SWITCH            — 1% daily DD breach → stop trading
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AlertType(str, Enum):
    MORNING_BRIEFING  = "MORNING_BRIEFING"
    ENTRY_ZONE        = "ENTRY_ZONE"
    TARGET_HIT        = "TARGET_HIT"
    HEDGE_ADJUSTMENT  = "HEDGE_ADJUSTMENT"
    KILL_SWITCH       = "KILL_SWITCH"
    STOP_LOSS_HIT     = "STOP_LOSS_HIT"
    RE_ENTRY_WINDOW   = "RE_ENTRY_WINDOW"   # WAIT → re-entry trigger approaching


class AlertPriority(str, Enum):
    CRITICAL = "CRITICAL"   # kill switch, SL hit — fire immediately
    HIGH     = "HIGH"       # entry zone, target hit
    MEDIUM   = "MEDIUM"     # morning briefing, hedge adj
    LOW      = "LOW"        # re-entry window


class Alert(BaseModel):
    id:           str           = Field(default_factory=lambda: datetime.utcnow().strftime("%H%M%S%f")[:10])
    alert_type:   AlertType
    priority:     AlertPriority
    symbol:       str           = "NIFTY 50"
    timestamp:    datetime      = Field(default_factory=datetime.utcnow)
    title:        str           = ""
    message:      str           = ""          # full Telegram-formatted message
    price:        Optional[float] = None
    fired:        bool          = False
    fire_count:   int           = 0           # deduplicate — don't re-fire same alert too often


# ── Active Trade State ──────────────────────────────────────────
# This is the in-memory state the price monitor watches.
# Populated from the latest FinalVerdict.

class ActiveTrade(BaseModel):
    """Live trade plan the monitors watch."""
    symbol:           str           = ""
    verdict:          str           = ""       # BULL_TRADE | BEAR_TRADE | HEDGE_TRADE | WAIT
    direction:        str           = "LONG"
    entry_low:        float         = 0.0
    entry_high:       float         = 0.0
    stop_loss:        float         = 0.0
    target1:          float         = 0.0
    target2:          float         = 0.0
    target3:          Optional[float] = None
    instrument:       str           = ""
    hedge_type:       str           = "NONE"
    hedge_strike:     Optional[float] = None
    ic_short_call:    Optional[float] = None   # Iron Condor short call strike
    ic_short_put:     Optional[float] = None   # Iron Condor short put strike
    units:            int           = 1
    rr_ratio:         float         = 0.0
    execution_score:  int           = 0
    confidence:       int           = 0
    regime:           str           = ""
    rationale:        str           = ""
    # re-entry trigger for WAIT verdicts
    re_entry_trigger: str           = ""
    re_entry_window:  int           = 30      # minutes
    # alert fire state
    entry_alert_fired:  bool        = False
    t1_alert_fired:     bool        = False
    t2_alert_fired:     bool        = False
    sl_alert_fired:     bool        = False
    hedge_alert_fired:  bool        = False
    # Source verdict timestamp
    verdict_ts:       Optional[datetime] = None
