"""
FM Trading Agency — Journal Data Models
==========================================
Pydantic models for the trade journal.
Every trade is logged with full attribution:
  - Which verdict generated it
  - L1-L9 layer scores at time of entry
  - Entry/exit prices, P&L
  - Hedge cost and effectiveness
  - Outcome (WIN/LOSS/BREAKEVEN)
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class TradeStatus(str, Enum):
    PENDING   = "PENDING"     # Trade plan issued, not yet entered
    ACTIVE    = "ACTIVE"      # Position is open
    CLOSED    = "CLOSED"      # Position closed, P&L resolved
    CANCELLED = "CANCELLED"   # Trade plan cancelled (not entered)


class TradeOutcome(str, Enum):
    WIN       = "WIN"
    LOSS      = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING   = "PENDING"


class VerdictType(str, Enum):
    BULL_TRADE  = "BULL_TRADE"
    BEAR_TRADE  = "BEAR_TRADE"
    HEDGE_TRADE = "HEDGE_TRADE"
    WAIT        = "WAIT"


# ── Trade Entry (logged when verdict is issued) ────────────────

class TradeEntry(BaseModel):
    """A single trade journal entry. Created when a verdict is acted upon."""

    id:                str              = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    created_at:        datetime         = Field(default_factory=datetime.utcnow)
    trade_date:        date             = Field(default_factory=date.today)

    # ── Verdict context ────────────────────────────────────────
    symbol:            str              = "NIFTY 50"
    verdict:           VerdictType      = VerdictType.BULL_TRADE
    regime:            str              = "UNKNOWN"
    execution_score:   int              = 0
    confidence:        int              = 0
    rationale:         str              = ""

    # ── Layer scores at time of entry ──────────────────────────
    layer_scores:      dict[str, int]   = Field(default_factory=dict)  # {"L1":75,"L2":80,...}

    # ── Trade plan ─────────────────────────────────────────────
    direction:         str              = "LONG"     # LONG | SHORT | NEUTRAL
    instrument:        str              = ""         # "Long Futures", "ATM CE", etc.
    entry_price:       Optional[float]  = None
    stop_loss:         Optional[float]  = None
    target1:           Optional[float]  = None
    target2:           Optional[float]  = None
    target3:           Optional[float]  = None
    rr_ratio:          Optional[float]  = None
    lot_size:          int              = 25
    units:             int              = 1
    holding_period:    str              = "INTRADAY"

    # ── Hedge ──────────────────────────────────────────────────
    hedge_type:        str              = "NONE"     # BUY_PE_HEDGE | BUY_CE_HEDGE | IRON_CONDOR | NONE
    hedge_strike:      Optional[float]  = None
    hedge_premium:     Optional[float]  = None       # ₹ per lot
    hedge_cost_pct:    Optional[float]  = None       # cost as % of position

    # ── Execution ──────────────────────────────────────────────
    status:            TradeStatus      = TradeStatus.PENDING
    entry_time:        Optional[datetime] = None
    exit_time:         Optional[datetime] = None
    exit_price:        Optional[float]  = None
    exit_reason:       str              = ""         # "T1 hit", "SL hit", "manual", "time exit"

    # ── P&L ────────────────────────────────────────────────────
    gross_pnl:         Optional[float]  = None       # ₹ before hedge
    hedge_pnl:         Optional[float]  = None       # ₹ from hedge leg
    net_pnl:           Optional[float]  = None       # gross + hedge
    net_pnl_pct:       Optional[float]  = None       # % of capital
    outcome:           TradeOutcome     = TradeOutcome.PENDING

    # ── Session context ────────────────────────────────────────
    entry_session:     str              = ""         # OPENING_VOLATILITY, POWER_HOUR, etc.
    entry_hour:        Optional[int]    = None       # 9, 10, 11, ... for time-of-day analysis
    vix_at_entry:      Optional[float]  = None
    spot_at_verdict:   Optional[float]  = None

    # ── Notes ──────────────────────────────────────────────────
    notes:             str              = ""


# ── Trade Close Request ────────────────────────────────────────

class CloseTradeRequest(BaseModel):
    trade_id:     str
    exit_price:   float
    exit_reason:  str     = "manual"
    hedge_pnl:    float   = 0.0
    notes:        str     = ""


# ── Weekly Summary ─────────────────────────────────────────────

class WeeklySummary(BaseModel):
    week_start:        date
    week_end:          date
    total_trades:      int    = 0
    wins:              int    = 0
    losses:            int    = 0
    breakevens:        int    = 0
    win_rate:          float  = 0.0
    gross_pnl:         float  = 0.0
    hedge_pnl:         float  = 0.0
    net_pnl:           float  = 0.0
    net_pnl_pct:       float  = 0.0      # vs capital
    target_pct:        float  = 2.0      # weekly target
    pace:              str    = "ON_TRACK"  # ON_TRACK | BEHIND | AT_RISK | EXCEEDED
    max_drawdown_pct:  float  = 0.0
    best_trade_pnl:    float  = 0.0
    worst_trade_pnl:   float  = 0.0
    avg_rr_achieved:   float  = 0.0


# ── Agent Accuracy Row ─────────────────────────────────────────

class AgentAccuracy(BaseModel):
    agent:       str          # "L1", "L2", ..., "L9"
    total:       int    = 0
    correct:     int    = 0   # score was in winning direction
    accuracy:    float  = 0.0
    avg_score:   float  = 0.0
    correlation: float  = 0.0 # correlation with trade outcome


# ── Time-of-Day Stats ─────────────────────────────────────────

class HourStats(BaseModel):
    hour:         int          # 9, 10, 11, 12, 13, 14, 15
    total:        int    = 0
    wins:         int    = 0
    losses:       int    = 0
    win_rate:     float  = 0.0
    avg_pnl:      float  = 0.0
    best_pnl:     float  = 0.0
    worst_pnl:    float  = 0.0


# ── Hedge Effectiveness ───────────────────────────────────────

class HedgeEffectiveness(BaseModel):
    total_hedged:         int    = 0
    total_hedge_cost:     float  = 0.0
    total_hedge_recovery: float  = 0.0
    avg_recovery_pct:     float  = 0.0      # % of primary loss recovered
    hedge_positive_count: int    = 0         # trades where hedge added value
    avg_cost_pct:         float  = 0.0       # avg hedge cost as % of position
    worth_it:             bool   = False     # recovery > cost over all trades


# ── Drawdown Event ─────────────────────────────────────────────

class DrawdownEvent(BaseModel):
    start_date:   date
    end_date:     Optional[date]  = None
    peak_capital: float           = 0.0
    trough:       float           = 0.0
    dd_pct:       float           = 0.0
    recovery_days: Optional[int]  = None
    kill_switch:  bool            = False
