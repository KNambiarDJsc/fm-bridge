"""
FM Trading Agency — Bridge Data Models
=========================================
Pydantic v2 models.  Every endpoint validates against these.
Every downstream service (fm-agents, fm-quant, fm-web) imports from here.

Design: "Pydantic models are the contract."
   — study OpenAlgo / OpenBB for this pattern.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════

class Regime(str, Enum):
    BULL_TREND    = "BULL_TREND"
    BEAR_TREND    = "BEAR_TREND"
    RANGE         = "RANGE"
    VOLATILE      = "VOLATILE"
    TRAP          = "TRAP"
    EVENT_DRIVEN  = "EVENT_DRIVEN"
    UNKNOWN       = "UNKNOWN"


class MarketSession(str, Enum):
    PRE_OPEN           = "PRE_OPEN"
    OPENING_VOLATILITY = "OPENING_VOLATILITY"   # 09:15 - 10:30
    MIDDAY_CHOP        = "MIDDAY_CHOP"          # 10:30 - 14:00
    POWER_HOUR         = "POWER_HOUR"           # 14:00 - 15:00
    CLOSING            = "CLOSING"              # 15:00 - 15:30
    POST_CLOSE         = "POST_CLOSE"
    EXPIRY_MORNING     = "EXPIRY_MORNING"       # Thursday 09:15 - 11:00


class VerdictType(str, Enum):
    BULL_TRADE  = "BULL_TRADE"
    BEAR_TRADE  = "BEAR_TRADE"
    HEDGE_TRADE = "HEDGE_TRADE"
    WAIT        = "WAIT"


class RiskState(str, Enum):
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class OPRSignal(str, Enum):
    CALL_DOMINANT = "CALL_DOMINANT"   # bearish — more call premium than put
    PUT_DOMINANT  = "PUT_DOMINANT"    # bullish — more put premium than call
    NEUTRAL       = "NEUTRAL"


# ════════════════════════════════════════════════════════════════
# CORE MARKET DATA
# ════════════════════════════════════════════════════════════════

class OHLCVBar(BaseModel):
    ts:     str   = Field(...,  description="ISO timestamp")
    open:   float = Field(...,  ge=0)
    high:   float = Field(...,  ge=0)
    low:    float = Field(...,  ge=0)
    close:  float = Field(...,  ge=0)
    volume: int   = Field(0,    ge=0)


class MarketQuote(BaseModel):
    symbol:    str
    price:     float  = Field(..., ge=0)
    chg_pct:   float  = 0.0
    high:      float  = 0.0
    low:       float  = 0.0
    open:      float  = 0.0
    prev_close:float  = 0.0
    volume:    int    = 0
    source:    str    = "zerodha"
    fetched_ms:int    = 0


class VIXReading(BaseModel):
    vix:    Optional[float] = None
    source: str             = "zerodha"
    error:  Optional[str]   = None


class HistoricalData(BaseModel):
    symbol:   str
    interval: str
    bars:     list[OHLCVBar]
    count:    int
    source:   str = "zerodha"


# ════════════════════════════════════════════════════════════════
# INDICATOR PACK
# ════════════════════════════════════════════════════════════════

class IndicatorPack(BaseModel):
    """Full 12+ indicator output from pandas-ta. All values can be None if data insufficient."""
    symbol:      str
    interval:    str
    spot:        float = 0.0

    # Moving averages
    ema9:    Optional[float] = None
    ema20:   Optional[float] = None
    ema50:   Optional[float] = None
    sma200:  Optional[float] = None

    # Momentum
    rsi:         Optional[float] = None
    rsi_zone:    Optional[str]   = None   # OVERSOLD / SWEET_SPOT / NEUTRAL / OVERBOUGHT
    macd:        Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist:   Optional[float] = None
    macd_dir:    Optional[str]   = None   # BULL / BEAR
    stoch_k:     Optional[float] = None
    stoch_d:     Optional[float] = None
    williams_r:  Optional[float] = None
    cci:         Optional[float] = None

    # Trend strength
    adx:         Optional[float] = None
    adx_strength:Optional[str]   = None   # STRONG / MODERATE / WEAK
    supertrend:  Optional[float] = None
    supertrend_dir: Optional[str]= None   # LONG / SHORT

    # Volatility
    atr:         Optional[float] = None
    atr_pct:     Optional[float] = None
    bb_upper:    Optional[float] = None
    bb_lower:    Optional[float] = None
    bb_mid:      Optional[float] = None
    bb_width:    Optional[float] = None

    # Volume
    vwap:        Optional[float] = None
    vol_ratio:   Optional[float] = None   # current vol / 20-day avg
    obv_dir:     Optional[str]   = None   # UP / DOWN
    cmf:         Optional[float] = None

    # EMA stack alignment
    ema_stack:   Optional[str]   = None   # BULL / BEAR / MIXED

    computed_at: datetime = Field(default_factory=datetime.utcnow)
    computed_by: str      = "pandas-ta"


class MultiTFIndicators(BaseModel):
    """Indicators for all 4 timeframes — feeds L3 Technical agent."""
    symbol:   str
    daily:    Optional[IndicatorPack] = None
    hourly:   Optional[IndicatorPack] = None
    intraday: Optional[IndicatorPack] = None   # 15M
    scalp:    Optional[IndicatorPack] = None   # 5M

    alignment: Optional[str] = None   # BULL_ALIGNED / BEAR_ALIGNED / MIXED
    fetched_at: datetime      = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════
# OPTIONS CHAIN
# ════════════════════════════════════════════════════════════════

class OIStrike(BaseModel):
    strike:  float
    ce_oi:   int   = 0
    pe_oi:   int   = 0
    ce_iv:   Optional[float] = None
    pe_iv:   Optional[float] = None


class OptionsChain(BaseModel):
    """Full options chain with derived intelligence — fed to L6 Options agent and OPR engine."""
    symbol:    str
    spot:      Optional[float] = None
    expiry:    Optional[str]   = None   # nearest expiry date string

    # Core metrics (the ones LLMs must NOT compute — computed here)
    pcr:       Optional[float] = None   # Put/Call OI ratio
    max_pain:  Optional[float] = None   # Max pain strike
    call_wall: Optional[float] = None   # Highest CE OI strike
    put_wall:  Optional[float] = None   # Highest PE OI strike

    # OPR (Options Premium Ratio) — THE institutional sentiment detector
    opr:            Optional[float] = None   # = Total Put Premium / Total Call Premium
    opr_signal:     Optional[str]   = None   # CALL_DOMINANT / PUT_DOMINANT / NEUTRAL
    opr_trend:      Optional[str]   = None   # RISING / FALLING / FLAT (vs prev fetch)

    # Gamma zones
    max_gamma_strike: Optional[float] = None
    gamma_flip_level: Optional[float] = None   # above = dealer long gamma, below = short

    # IV
    atm_iv:         Optional[float] = None
    iv_percentile:  Optional[float] = None   # 0-100 vs last 52 weeks
    iv_rank:        Optional[float] = None

    # OI map (5 strikes above + below ATM)
    oi_map:    list[OIStrike] = []
    total_ce_oi: int = 0
    total_pe_oi: int = 0

    # Days to expiry
    dte:      int = 0
    is_expiry_day: bool = False

    fetched_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════
# MACRO CONTEXT
# ════════════════════════════════════════════════════════════════

class MacroContext(BaseModel):
    """All macro inputs for L1 Macro Sieve. Auto-fetched at 9 AM."""
    # Oil
    brent_oil:        Optional[float] = None
    oil_shock_active: bool            = False   # oil > $100

    # FII / DII flows (Rs Cr)
    fii_net:          Optional[float] = None
    dii_net:          Optional[float] = None
    dii_fii_ratio:    Optional[float] = None
    domestic_floor_active: bool       = False   # DII > 1.5x FII

    # RBI & macro
    rbi_stance:       Optional[str]   = None   # HAWKISH / NEUTRAL / DOVISH
    g_sec_yield_10y:  Optional[float] = None
    inr_usd:          Optional[float] = None

    # India VIX (from bridge /vix)
    india_vix:        Optional[float] = None
    vix_regime:       Optional[str]   = None   # CALM(<13) / NORMAL(13-20) / STRESSED(>20)

    # Computed risk context
    risk_context:     str             = "UNKNOWN"  # RISK_ON / RISK_OFF / TRANSITION
    macro_score:      Optional[int]   = None   # 0-100

    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    data_age_minutes: float = 0.0


# ════════════════════════════════════════════════════════════════
# INDEX OPPORTUNITY SCORE
# ════════════════════════════════════════════════════════════════

class IndexScore(BaseModel):
    """Opportunity score for one index — feeds the Heatmap widget."""
    name:     str
    score:    int   = Field(0, ge=0, le=100)
    regime:   str   = "SIDE"   # BULL / BEAR / SIDE
    price:    float = 0.0
    change_pct: float = 0.0
    rsi:      Optional[float] = None
    atr_pct:  Optional[float] = None
    r30:      Optional[float] = None   # 30-day return %

    # Score components (for transparency / debugging)
    tech_momentum:    Optional[float] = None
    regime_clarity:   Optional[float] = None
    relative_strength:Optional[float] = None
    options_activity: Optional[float] = None

    error:    Optional[str] = None


class MultiIndexHeatmap(BaseModel):
    indices:    list[IndexScore]
    best:       Optional[IndexScore] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════
# MARKET SESSION
# ════════════════════════════════════════════════════════════════

class SessionContext(BaseModel):
    """What the market session tells us about behaviour."""
    session:            MarketSession
    ist_time:           str   # HH:MM
    is_expiry_day:      bool  = False
    days_to_expiry:     int   = 0   # days to nearest Thursday
    minutes_to_close:   int   = 0

    # Session-specific characteristics
    volatility_bias:    str   = "NORMAL"    # HIGH / NORMAL / LOW
    manipulation_risk:  str   = "LOW"       # HIGH on expiry morning
    recommended_action: str   = "NORMAL"    # WAIT_FOR_SETTLE / TRADE / REDUCE_SIZE

    # Phase 1 → Phase 3 contract: tells L9 sovereign how to weight signals
    session_confidence_multiplier: float = 1.0
    # e.g. OPENING_VOLATILITY = 0.7 (reduce conviction), POWER_HOUR = 1.1


# ════════════════════════════════════════════════════════════════
# CAPITAL SHIELD (Risk Governor contract)
# ════════════════════════════════════════════════════════════════

class CapitalShield(BaseModel):
    """Live capital protection state — fed to L8 Risk Governor."""
    capital:           float  = 1_000_000

    # Drawdown tracking
    daily_pnl:         float  = 0.0
    daily_dd_pct:      float  = 0.0
    weekly_pnl:        float  = 0.0
    weekly_dd_pct:     float  = 0.0
    daily_dd_limit:    float  = 1.0    # %
    weekly_dd_limit:   float  = 3.0    # %

    # Kill switch
    kill_switch:       bool   = False
    kill_switch_reason:Optional[str] = None

    # Exposure
    open_risk_pct:     float  = 0.0
    max_open_risk_pct: float  = 1.25
    cash_reserve_pct:  float  = 30.0
    cash_available:    float  = 0.0

    # Streak
    loss_streak:       int    = 0
    max_streak_before_reduce: int = 3

    # Risk state
    risk_state:        RiskState = RiskState.LOW
    trade_authorized:  bool  = True

    # Position sizing (for L8)
    max_risk_per_trade: float = 5_000   # Rs
    unit_count:         int   = 0


# ════════════════════════════════════════════════════════════════
# VERDICT CONTRACT (THE product interface — document 6 item 7)
# ════════════════════════════════════════════════════════════════

class TradePlan(BaseModel):
    """Fully specified trade plan — bull or bear."""
    direction:   str   # LONG / SHORT
    entry_low:   float
    entry_high:  float
    stop_loss:   float
    target1:     float
    target2:     float
    target3:     Optional[float] = None
    rr:          float = 0.0
    instrument:  str   = ""
    entry_trigger:   str = ""
    invalidation:    str = ""
    holding_period:  str = "INTRADAY"
    lot_size:    int   = 25

    @field_validator("stop_loss")
    @classmethod
    def check_sl_direction(cls, v: float, info: Any) -> float:
        """Directional math hard-code — BEAR MATH LAW enforced in Pydantic."""
        data = info.data
        entry = data.get("entry_low", 0)
        direction = data.get("direction", "LONG")
        if direction == "LONG" and entry > 0 and v >= entry:
            raise ValueError(f"BULL trade: SL ({v}) must be < entry ({entry})")
        if direction == "SHORT" and entry > 0 and v <= entry:
            raise ValueError(f"BEAR trade: SL ({v}) must be > entry ({entry})")
        return v


class HedgePlan(BaseModel):
    """Per-trade hedge recommendation — py_vollib computes premium (Phase 2)."""
    hedge_type:        str   # BUY_PE_HEDGE / BUY_CE_HEDGE / IRON_CONDOR / NONE
    strike:            Optional[float] = None
    premium_per_unit:  Optional[float] = None
    premium_per_lot:   Optional[float] = None
    cost_pct_position: Optional[float] = None
    protection_range:  Optional[str]   = None
    exit_rule:         str             = "Exit at 80% premium decay or when T1 hit"
    disclaimer:        str             = "Estimated via Black-Scholes. Verify live quote before placing."

    # Iron Condor fields (hedge trade)
    sell_ce:   Optional[float] = None
    sell_pe:   Optional[float] = None
    buy_ce:    Optional[float] = None
    buy_pe:    Optional[float] = None
    net_credit_per_lot: Optional[float] = None
    max_loss_per_lot:   Optional[float] = None


class WaitSignal(BaseModel):
    """WAIT verdict — must always include a specific re-entry trigger (spec §2.1)."""
    reason:              str
    instruction:         str
    re_entry_trigger:    str   # EXACT price level
    re_entry_condition:  str   # EXACT event (e.g. "15-min close > 24,050 on vol > 1.15x avg")
    re_entry_window_minutes: int = Field(30, le=30)  # spec: max 30 min
    pivot_plan:          str   # what happens if trigger is NOT met in the window


class FinalVerdict(BaseModel):
    """
    THE product interface contract (document 6, item 7).
    Everything feeds THIS object.  Frontend renders ONLY from this.
    """
    verdict:        VerdictType
    regime:         Regime     = Regime.UNKNOWN
    best_index:     str        = ""
    opportunity_score: int     = Field(0, ge=0, le=100)
    confidence:     int        = Field(0, ge=0, le=100)
    risk_state:     RiskState  = RiskState.MODERATE
    hedge_active:   bool       = False

    # Trade plan (populated for BULL_TRADE / BEAR_TRADE)
    trade_plan:  Optional[TradePlan]  = None

    # Hedge (populated for all 3 trade verdicts)
    hedge_plan:  Optional[HedgePlan]  = None

    # Wait signal (populated for WAIT only)
    wait_signal: Optional[WaitSignal] = None

    # Supporting scores
    execution_score: int = 0
    layer_scores: dict[str, int] = {}   # L1..L9 confidence scores

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until:  Optional[datetime] = None   # WAIT verdict: expires after window


# ════════════════════════════════════════════════════════════════
# API RESPONSE WRAPPERS
# ════════════════════════════════════════════════════════════════

class BridgeResponse(BaseModel):
    """Standard wrapper for all bridge API responses."""
    status:   str             = "success"
    data:     Optional[Any]   = None
    error:    Optional[str]   = None
    fetched_at: int           = 0   # Unix ms