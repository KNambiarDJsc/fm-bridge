"""
FM Trading Agency — Agent Output Schemas
==========================================
Every agent returns a Pydantic model.
LLMs MUST return structured JSON matching these schemas.

Zero-Placeholder Policy enforced here:
  confidence=0 is FORBIDDEN unless data is literally missing.
  Validators catch and replace zero-confidence with minimum 1.

Directional Math Hard-Code:
  BULL: SL < entry, targets > entry
  BEAR: SL > entry, targets < entry
  Validated in FinalVerdict construction.

These schemas are the contract between the LLM and the rest of the system.
"""

from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


# ════════════════════════════════════════════════════════════════
# ZERO-PLACEHOLDER VALIDATOR
# ════════════════════════════════════════════════════════════════

def _no_zero(v: int) -> int:
    """Enforce Zero-Placeholder Policy: confidence cannot be 0."""
    if v == 0:
        return 1   # minimum non-zero
    return v


# ════════════════════════════════════════════════════════════════
# L1 — MACRO SIEVE
# ════════════════════════════════════════════════════════════════

class L1MacroResult(BaseModel):
    agent:                  str  = "l1_macro_sieve"
    status:                 str  = "ALLOW"          # ALLOW | BLOCK | WATCH
    risk_context:           str  = "TRANSITION"     # RISK_ON | RISK_OFF | TRANSITION
    oil_shock_active:       bool = False
    oil_shock_veto_applies: str  = "LONG_ONLY"      # LONG_ONLY | NONE
    post_expiry_phase:      bool = False
    domestic_floor_active:  bool = False
    short_search_triggered: bool = False            # NEW v5: auto-triggers when LONG blocked
    liquidity_state:        str  = "NORMAL"
    gap_risk:               str  = "LOW"
    macro_score:            int  = Field(50, ge=1, le=100)
    confidence:             int  = Field(50, ge=1, le=100)
    rationale:              str  = ""

    _nz_conf = field_validator("confidence", "macro_score", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L2 — FUNDAMENTALS
# ════════════════════════════════════════════════════════════════

class L2FundamentalsResult(BaseModel):
    agent:              str = "l2_fundamentals"
    status:             str = "ALLOW"
    valuation_status:   str = "FAIR"          # OVERVALUED | FAIR | UNDERVALUED
    valuation_context:  str = ""
    earnings_trend:     str = "STABLE"        # ACCELERATING | STABLE | DECELERATING
    sector_leadership:  str = ""
    institutional_flow: str = "FLAT"          # BUILDING | DISTRIBUTING | FLAT
    fundamental_score:  int = Field(50, ge=1, le=100)
    confidence:         int = Field(50, ge=1, le=100)
    rationale:          str = ""

    _nz = field_validator("confidence", "fundamental_score", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L3 — TECHNICAL
# ════════════════════════════════════════════════════════════════

class MultiTFAlignment(BaseModel):
    daily:    str = "neutral"
    hourly:   str = "neutral"
    intraday: str = "neutral"
    scalp:    str = "neutral"
    summary:  str = "MIXED"   # BULL_ALIGNED | BEAR_ALIGNED | MIXED


class L3TechnicalResult(BaseModel):
    agent:                    str = "l3_technical"
    status:                   str = "ALLOW"       # ALLOW | BLOCKED (synthetic data)
    trend_regime:             str = "NEUTRAL"
    setup_type:               str = "NO_SETUP"
    direction:                str = "NEUTRAL"     # LONG | SHORT | NEUTRAL
    ema_stack:                str = "MIXED"
    rsi_zone:                 str = "NEUTRAL"
    macd_status:              str = "NEUTRAL"
    vwap_position:            str = "NEUTRAL"
    supertrend_dir:           str = "NEUTRAL"
    adx_strength:             str = "WEAK"
    multi_tf_alignment:       Optional[MultiTFAlignment] = None
    technical_score:          int = Field(50, ge=1, le=100)
    confidence:               int = Field(50, ge=1, le=100)
    rationale:                str = ""

    _nz = field_validator("confidence", "technical_score", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L4 — PATTERNS
# ════════════════════════════════════════════════════════════════

class BearPivotEntry(BaseModel):
    """Bear pivot entry plan — populated when bull trap detected."""
    entry_level:       float = 0.0
    stop_level:        float = 0.0
    target:            float = 0.0
    rr:                float = 0.0
    condition:         str   = ""
    instrument:        str   = "Short Futures / ATM PE"


class L4PatternResult(BaseModel):
    agent:                   str  = "l4_patterns"
    status:                  str  = "ALLOW"
    primary_pattern:         str  = "NO_PATTERN"
    pattern_state:           str  = "NONE"         # CONFIRMED | FORMING | FAILED | TRAP | NONE
    direction:               str  = "NEUTRAL"
    pattern_confidence:      int  = Field(50, ge=1, le=100)
    measured_move_target1:   Optional[float] = None
    measured_move_target2:   Optional[float] = None
    invalidation_level:      Optional[float] = None
    trap_risk:               str  = "LOW"
    failure_risk:            str  = "LOW"
    bull_trap_detected:      bool = False
    bear_pivot_entry:        Optional[BearPivotEntry] = None
    short_sell_search_active:bool = False
    entry_logic:             str  = ""
    confidence:              int  = Field(50, ge=1, le=100)
    rationale:               str  = ""

    _nz = field_validator("confidence", "pattern_confidence", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L5 — SENTIMENT
# ════════════════════════════════════════════════════════════════

class LegendSignal(BaseModel):
    name:       str
    signal:     str   # BUY | SELL | NEUTRAL
    confidence: int   = Field(50, ge=1, le=100)
    reasoning:  str   = ""

    _nz = field_validator("confidence", mode="before")(_no_zero)


class LegendConsensus(BaseModel):
    bull:    int = 0
    neutral: int = 0
    bear:    int = 0
    total:   int = 0
    summary: str = ""


class L5SentimentResult(BaseModel):
    agent:                 str  = "l5_sentiment"
    status:                str  = "ALLOW"
    narrative_direction:   str  = "STABLE"
    volatility_sentiment:  str  = "CALM"
    fear_greed_proxy:      int  = Field(50, ge=1, le=100)
    fear_greed_label:      str  = "Neutral"
    domestic_floor_signal: bool = False
    top_headlines:         list[str] = []        # REAL headlines — anti-hallucination rule
    legend_consensus:      Optional[LegendConsensus] = None
    confidence:            int  = Field(50, ge=1, le=100)
    rationale:             str  = ""

    _nz = field_validator("confidence", "fear_greed_proxy", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L6 — OPTIONS FLOW
# ════════════════════════════════════════════════════════════════

class L6OptionsResult(BaseModel):
    agent:                   str  = "l6_options_flow"
    status:                  str  = "ALLOW"
    options_bias:            str  = "NEUTRAL"   # BULLISH | BEARISH | NEUTRAL
    opr_interpretation:      str  = ""
    pcr_signal:              str  = "NEUTRAL"
    max_pain_pull:           str  = "NEUTRAL"
    call_wall_level:         Optional[float] = None
    put_wall_level:          Optional[float] = None
    gamma_flip_level:        Optional[float] = None
    dealer_stance:           str  = "NEUTRAL"    # LONG_GAMMA | SHORT_GAMMA | NEUTRAL
    iv_regime:               str  = "FAIR"       # CHEAP | FAIR | EXPENSIVE
    best_execution_vehicle:  str  = "Futures"    # Futures | ATM CE | ATM PE | Iron Condor
    flow_conviction_score:   int  = Field(50, ge=1, le=100)
    confidence:              int  = Field(50, ge=1, le=100)
    rationale:               str  = ""

    _nz = field_validator("confidence", "flow_conviction_score", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L7 — STRATEGY (TRIPLE OUTPUT — bull + bear + hedge plans)
# ════════════════════════════════════════════════════════════════

class StrategyPlan(BaseModel):
    selected_strategy:   str   = ""
    entry_zone:          str   = ""
    stop_loss:           float = 0.0
    target1:             float = 0.0
    target2:             float = 0.0
    target3:             Optional[float] = None
    rr:                  str   = "1:2"
    instrument:          str   = ""
    entry_trigger:       str   = ""
    invalidation:        str   = ""
    holding_period:      str   = "INTRADAY"
    fit_score:           int   = Field(50, ge=1, le=100)

    _nz = field_validator("fit_score", mode="before")(_no_zero)


class L7StrategyResult(BaseModel):
    agent:                   str  = "l7_strategy"
    status:                  str  = "ALLOW"
    primary_recommendation:  str  = "WAIT"    # BULL_TRADE | BEAR_TRADE | HEDGE_TRADE | WAIT
    bull_plan:               Optional[StrategyPlan] = None
    bear_plan:               Optional[StrategyPlan] = None
    hedge_plan_strategy:     Optional[StrategyPlan] = None
    rejected_strategies:     list[dict] = []
    strategy_conflict_flag:  bool = False
    confidence:              int  = Field(50, ge=1, le=100)
    rationale:               str  = ""

    _nz = field_validator("confidence", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L8 — RISK GOVERNOR (structured from fm-quant RiskDecision)
# ════════════════════════════════════════════════════════════════

class L8RiskResult(BaseModel):
    agent:                  str  = "l8_risk_governor"
    authorized:             bool = True
    unit_count:             int  = 0
    max_risk_per_trade:     float = 0.0
    kill_switch:            bool = False
    veto_reason:            str  = ""
    risk_state:             str  = "LOW"
    daily_dd_pct:           float = 0.0
    weekly_dd_pct:          float = 0.0
    loss_streak:            int  = 0
    size_reduction_pct:     float = 0.0
    hedge_mandatory:        bool = True
    confidence:             int  = Field(80, ge=1, le=100)
    warnings:               list[str] = []

    _nz = field_validator("confidence", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# L9 — SOVEREIGN DECISION ENGINE
# ════════════════════════════════════════════════════════════════

class WaitDetails(BaseModel):
    re_entry_trigger:      str  = ""
    re_entry_condition:    str  = ""
    re_entry_window_minutes:   int  = 30
    pivot_plan:            str  = ""


class L9SovereignResult(BaseModel):
    agent:                   str  = "l9_sovereign_decision"
    final_verdict:           str  = "WAIT"   # BULL_TRADE | BEAR_TRADE | HEDGE_TRADE | WAIT
    direction:               str  = "NEUTRAL"
    confidence_score:        int  = Field(50, ge=1, le=100)
    execution_score:         int  = Field(50, ge=1, le=100)
    market_regime:           str  = ""
    strategy_selected:       str  = ""
    entry_zone:              Optional[dict] = None   # {"low": x, "high": y}
    stop_loss:               Optional[float] = None
    target1:                 Optional[float] = None
    target2:                 Optional[float] = None
    target3:                 Optional[float] = None
    rr_ratio:                Optional[float] = None
    instrument:              str  = ""
    entry_trigger:           str  = ""
    invalidation_logic:      str  = ""
    holding_period:          str  = "INTRADAY"
    position_sizing:         str  = ""
    wait_details:            Optional[WaitDetails] = None
    oil_shock_active:        bool = False
    bear_pivot_activated:    bool = False
    hedge_trade_activated:   bool = False
    top5_reasons_for:        list[str] = []
    top5_risks_against:      list[str] = []
    macro_condition:         str  = ""
    technical_condition:     str  = ""
    pattern_condition:       str  = ""
    sentiment_condition:     str  = ""
    options_condition:       str  = ""
    authorized:              bool = True
    rationale:               str  = ""

    _nz = field_validator("confidence_score", "execution_score", mode="before")(_no_zero)


# ════════════════════════════════════════════════════════════════
# PIPELINE STATE (LangGraph AgentState)
# ════════════════════════════════════════════════════════════════

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph state passed between all nodes."""
    # Input context (populated at pipeline start)
    symbol:         str
    spot:           float
    ist_time:       str

    # Phase 1 bridge data (fetched before pipeline starts)
    indicator_pack: dict
    options_chain:  dict
    macro_context:  dict
    session_ctx:    dict
    capital_shield: dict
    news_headlines: list[str]

    # Phase 2 quant results (computed before pipeline starts)
    regime_result:  dict
    chain_intel:    dict
    risk_decision:  dict
    cascade_input:  dict

    # Agent outputs (L1-L9)
    l1_result:  Optional[L1MacroResult]
    l2_result:  Optional[L2FundamentalsResult]
    l3_result:  Optional[L3TechnicalResult]
    l4_result:  Optional[L4PatternResult]
    l5_result:  Optional[L5SentimentResult]
    l6_result:  Optional[L6OptionsResult]
    l7_result:  Optional[L7StrategyResult]
    l8_result:  Optional[L8RiskResult]
    l9_result:  Optional[L9SovereignResult]

    # Final
    final_verdict: Optional[dict]
    error:         Optional[str]
