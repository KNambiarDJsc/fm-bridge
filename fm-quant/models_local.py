"""
FM Trading Agency — Local model re-exports for fm-quant.

When fm-quant runs as part of the monorepo, this imports directly
from fm-bridge/models.  When run standalone (tests, notebooks),
it falls back to minimal inline definitions.

Import this instead of importing from fm-bridge directly
so fm-quant stays independently testable.
"""
from __future__ import annotations

import sys
import os

# Try bridge models first (monorepo mode)
_bridge_path = os.path.join(os.path.dirname(__file__), "..", "fm-bridge")
if os.path.exists(_bridge_path):
    sys.path.insert(0, _bridge_path)

try:
    from models import (
        Regime, MarketSession, VerdictType, RiskState, OPRSignal,
        IndicatorPack, OptionsChain, OIStrike, MacroContext,
        SessionContext, CapitalShield, TradePlan, HedgePlan,
        WaitSignal, FinalVerdict, IndexScore,
    )
    from config import LOT_SIZES, STRIKE_STEP
    _BRIDGE_MODELS = True

except ImportError:
    # Standalone fallback — minimal definitions for testing
    _BRIDGE_MODELS = False
    from enum import Enum
    from dataclasses import dataclass, field
    from typing import Optional
    from pydantic import BaseModel

    class Regime(str, Enum):
        BULL_TREND   = "BULL_TREND"
        BEAR_TREND   = "BEAR_TREND"
        RANGE        = "RANGE"
        VOLATILE     = "VOLATILE"
        TRAP         = "TRAP"
        EVENT_DRIVEN = "EVENT_DRIVEN"
        UNKNOWN      = "UNKNOWN"

    class RiskState(str, Enum):
        LOW      = "LOW"
        MODERATE = "MODERATE"
        HIGH     = "HIGH"
        CRITICAL = "CRITICAL"

    class VerdictType(str, Enum):
        BULL_TRADE  = "BULL_TRADE"
        BEAR_TRADE  = "BEAR_TRADE"
        HEDGE_TRADE = "HEDGE_TRADE"
        WAIT        = "WAIT"

    class OPRSignal(str, Enum):
        CALL_DOMINANT = "CALL_DOMINANT"
        PUT_DOMINANT  = "PUT_DOMINANT"
        NEUTRAL       = "NEUTRAL"

    class MarketSession(str, Enum):
        OPENING_VOLATILITY = "OPENING_VOLATILITY"
        MIDDAY_CHOP        = "MIDDAY_CHOP"
        POWER_HOUR         = "POWER_HOUR"
        CLOSING            = "CLOSING"
        PRE_OPEN           = "PRE_OPEN"
        POST_CLOSE         = "POST_CLOSE"
        EXPIRY_MORNING     = "EXPIRY_MORNING"

    class IndicatorPack(BaseModel):
        symbol: str = ""; interval: str = "day"; spot: float = 0.0
        ema9: Optional[float] = None; ema20: Optional[float] = None
        ema50: Optional[float] = None; sma200: Optional[float] = None
        rsi: Optional[float] = None; rsi_zone: Optional[str] = None
        macd: Optional[float] = None; macd_signal: Optional[float] = None
        macd_hist: Optional[float] = None; macd_dir: Optional[str] = None
        adx: Optional[float] = None; adx_strength: Optional[str] = None
        atr: Optional[float] = None; atr_pct: Optional[float] = None
        bb_upper: Optional[float] = None; bb_lower: Optional[float] = None
        bb_width: Optional[float] = None; vwap: Optional[float] = None
        stoch_k: Optional[float] = None; stoch_d: Optional[float] = None
        cci: Optional[float] = None; williams_r: Optional[float] = None
        cmf: Optional[float] = None; obv_dir: Optional[str] = None
        supertrend: Optional[float] = None; supertrend_dir: Optional[str] = None
        ema_stack: Optional[str] = None; vol_ratio: Optional[float] = None

    class OIStrike(BaseModel):
        strike: float; ce_oi: int = 0; pe_oi: int = 0
        ce_iv: Optional[float] = None; pe_iv: Optional[float] = None

    class OptionsChain(BaseModel):
        symbol: str = ""; spot: Optional[float] = None; expiry: Optional[str] = None
        pcr: Optional[float] = None; max_pain: Optional[float] = None
        call_wall: Optional[float] = None; put_wall: Optional[float] = None
        opr: Optional[float] = None; opr_signal: Optional[str] = None
        opr_trend: Optional[str] = None; max_gamma_strike: Optional[float] = None
        gamma_flip_level: Optional[float] = None; atm_iv: Optional[float] = None
        iv_percentile: Optional[float] = None; oi_map: list = []
        total_ce_oi: int = 0; total_pe_oi: int = 0; dte: int = 0
        is_expiry_day: bool = False

    class MacroContext(BaseModel):
        brent_oil: Optional[float] = None; oil_shock_active: bool = False
        fii_net: Optional[float] = None; dii_net: Optional[float] = None
        dii_fii_ratio: Optional[float] = None; domestic_floor_active: bool = False
        india_vix: Optional[float] = None; vix_regime: Optional[str] = None
        risk_context: str = "UNKNOWN"; macro_score: Optional[int] = None

    class SessionContext(BaseModel):
        session: MarketSession = MarketSession.MIDDAY_CHOP
        ist_time: str = "11:00"; is_expiry_day: bool = False
        days_to_expiry: int = 2; minutes_to_close: int = 270
        volatility_bias: str = "NORMAL"; manipulation_risk: str = "LOW"
        recommended_action: str = "TRADE"
        session_confidence_multiplier: float = 1.0

    class CapitalShield(BaseModel):
        capital: float = 1_000_000; daily_pnl: float = 0.0
        daily_dd_pct: float = 0.0; weekly_pnl: float = 0.0
        weekly_dd_pct: float = 0.0; daily_dd_limit: float = 1.0
        weekly_dd_limit: float = 3.0; kill_switch: bool = False
        kill_switch_reason: Optional[str] = None; open_risk_pct: float = 0.0
        max_open_risk_pct: float = 1.25; cash_reserve_pct: float = 30.0
        cash_available: float = 300_000; loss_streak: int = 0
        max_risk_per_trade: float = 5_000; unit_count: int = 0
        risk_state: RiskState = RiskState.LOW; trade_authorized: bool = True

    class TradePlan(BaseModel):
        direction: str; entry_low: float; entry_high: float
        stop_loss: float; target1: float; target2: float
        target3: Optional[float] = None; rr: float = 0.0
        instrument: str = ""; entry_trigger: str = ""
        invalidation: str = ""; holding_period: str = "INTRADAY"
        lot_size: int = 25

    class HedgePlan(BaseModel):
        hedge_type: str; strike: Optional[float] = None
        premium_per_unit: Optional[float] = None; premium_per_lot: Optional[float] = None
        cost_pct_position: Optional[float] = None; protection_range: Optional[str] = None
        exit_rule: str = "Exit at 80% decay or T1 hit"
        disclaimer: str = "Estimated via BSM. Verify live quote."
        sell_ce: Optional[float] = None; sell_pe: Optional[float] = None
        buy_ce: Optional[float] = None; buy_pe: Optional[float] = None
        net_credit_per_lot: Optional[float] = None; max_loss_per_lot: Optional[float] = None

    class WaitSignal(BaseModel):
        reason: str; instruction: str; re_entry_trigger: str
        re_entry_condition: str; re_entry_window_minutes: int = 30
        pivot_plan: str

    class FinalVerdict(BaseModel):
        verdict: VerdictType; regime: Regime = Regime.UNKNOWN
        best_index: str = ""; opportunity_score: int = 0
        confidence: int = 0; risk_state: RiskState = RiskState.MODERATE
        hedge_active: bool = False; trade_plan: Optional[TradePlan] = None
        hedge_plan: Optional[HedgePlan] = None; wait_signal: Optional[WaitSignal] = None
        execution_score: int = 0; layer_scores: dict = {}

    class IndexScore(BaseModel):
        name: str; score: int = 0; regime: str = "SIDE"
        price: float = 0.0; change_pct: float = 0.0
        rsi: Optional[float] = None; atr_pct: Optional[float] = None
        r30: Optional[float] = None; error: Optional[str] = None

    LOT_SIZES: dict[str, int] = {
        "NIFTY 50": 25, "BANK NIFTY": 15, "NIFTY IT": 25,
        "NIFTY FINANCIAL": 25, "_default": 25,
    }
    STRIKE_STEP: dict[str, int] = {
        "NIFTY 50": 50, "BANK NIFTY": 100, "NIFTY FINANCIAL": 50, "_default": 50,
    }