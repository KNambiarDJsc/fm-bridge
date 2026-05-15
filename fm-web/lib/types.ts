// FM Trading Agency — TypeScript Types
// Mirrors the Pydantic models from fm-bridge/models/__init__.py
// and fm-agents/schemas/agent_outputs.py
// Keep these in sync when backend models change.

// ── Enums ──────────────────────────────────────────────────────

export type VerdictType = "BULL_TRADE" | "BEAR_TRADE" | "HEDGE_TRADE" | "WAIT";
export type Regime = "BULL_TREND" | "BEAR_TREND" | "RANGE" | "VOLATILE" | "TRAP" | "EVENT_DRIVEN" | "UNKNOWN";
export type RiskState = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
export type OPRSignal = "CALL_DOMINANT" | "PUT_DOMINANT" | "NEUTRAL";
export type MarketSession = "PRE_OPEN" | "OPENING_VOLATILITY" | "MIDDAY_CHOP" | "POWER_HOUR" | "CLOSING" | "POST_CLOSE" | "EXPIRY_MORNING";

// ── Market Data ────────────────────────────────────────────────

export interface OHLCVBar {
    ts: string; open: number; high: number; low: number; close: number; volume: number;
}

export interface MarketQuote {
    symbol: string; price: number; chg_pct: number;
    high: number; low: number; open: number; prev_close: number; volume: number;
}

export interface VIXReading {
    vix: number | null; source: string; error?: string;
}

// ── Indicators ─────────────────────────────────────────────────

export interface IndicatorPack {
    symbol: string; interval: string; spot: number;
    ema9?: number; ema20?: number; ema50?: number; sma200?: number;
    rsi?: number; rsi_zone?: string;
    macd?: number; macd_signal?: number; macd_hist?: number; macd_dir?: string;
    adx?: number; adx_strength?: string;
    atr?: number; atr_pct?: number;
    bb_upper?: number; bb_lower?: number; bb_width?: number;
    vwap?: number; vol_ratio?: number; obv_dir?: string;
    supertrend?: number; supertrend_dir?: string;
    ema_stack?: string; cci?: number; williams_r?: number; cmf?: number;
    stoch_k?: number; stoch_d?: number;
    computed_by?: string;
}

// ── Options ────────────────────────────────────────────────────

export interface OIStrike {
    strike: number; ce_oi: number; pe_oi: number; ce_iv?: number; pe_iv?: number;
}

export interface OptionsChain {
    symbol: string; spot?: number; expiry?: string;
    pcr?: number; max_pain?: number; call_wall?: number; put_wall?: number;
    opr?: number; opr_signal?: string; opr_trend?: string;
    max_gamma_strike?: number; gamma_flip_level?: number;
    atm_iv?: number; iv_percentile?: number; iv_rank?: number;
    oi_map: OIStrike[];
    total_ce_oi: number; total_pe_oi: number;
    dte: number; is_expiry_day: boolean;
}

// ── Macro ──────────────────────────────────────────────────────

export interface MacroContext {
    brent_oil?: number; oil_shock_active: boolean;
    fii_net?: number; dii_net?: number; dii_fii_ratio?: number;
    domestic_floor_active: boolean;
    rbi_stance?: string;
    india_vix?: number; vix_regime?: string;
    risk_context: string; macro_score?: number;
    data_age_minutes?: number;
}

// ── Session ────────────────────────────────────────────────────

export interface SessionContext {
    session: MarketSession; ist_time: string;
    is_expiry_day: boolean; days_to_expiry: number;
    minutes_to_close: number;
    volatility_bias: string; manipulation_risk: string;
    recommended_action: string;
    session_confidence_multiplier: number;
}

// ── Capital Shield ─────────────────────────────────────────────

export interface CapitalShield {
    capital: number;
    daily_pnl: number; daily_dd_pct: number; daily_dd_limit: number;
    weekly_pnl: number; weekly_dd_pct: number; weekly_dd_limit: number;
    kill_switch: boolean; kill_switch_reason?: string;
    open_risk_pct: number; max_open_risk_pct: number;
    cash_reserve_pct: number; cash_available: number;
    loss_streak: number; max_risk_per_trade: number;
    risk_state: RiskState; trade_authorized: boolean;
    unit_count: number;
}

// ── Index Scores ───────────────────────────────────────────────

export interface IndexScore {
    name: string; score: number; regime: string;
    price: number; change_pct: number;
    rsi?: number; atr_pct?: number; r30?: number;
    tech_momentum?: number; regime_clarity?: number;
    relative_strength?: number; options_activity?: number;
    error?: string;
}

export interface MultiIndexHeatmap {
    indices: IndexScore[];
    best?: IndexScore;
    fetched_at?: string;
}

// ── Trade / Hedge / Wait ───────────────────────────────────────

export interface TradePlan {
    direction: "LONG" | "SHORT";
    entry_low: number; entry_high: number;
    stop_loss: number; target1: number; target2: number; target3?: number;
    rr: number; instrument: string;
    entry_trigger: string; invalidation: string;
    holding_period: string; lot_size: number;
}

export interface HedgePlan {
    hedge_type: "BUY_PE_HEDGE" | "BUY_CE_HEDGE" | "IRON_CONDOR" | "NONE";
    strike?: number;
    premium_per_unit?: number; premium_per_lot?: number;
    cost_pct_position?: number; protection_range?: string;
    exit_rule?: string; disclaimer?: string;
    sell_ce?: number; sell_pe?: number; buy_ce?: number; buy_pe?: number;
    net_credit_per_lot?: number; max_loss_per_lot?: number;
}

export interface WaitSignal {
    reason: string; instruction: string;
    re_entry_trigger: string; re_entry_condition: string;
    re_entry_window_minutes: number; pivot_plan: string;
}

// ── FINAL VERDICT — the product interface contract ─────────────

export interface FinalVerdict {
    verdict: VerdictType;
    regime: Regime;
    best_index: string;
    opportunity_score: number;
    confidence: number;
    risk_state: RiskState;
    hedge_active: boolean;
    trade_plan?: TradePlan;
    hedge_plan?: HedgePlan;
    wait_signal?: WaitSignal;
    execution_score: number;
    layer_scores: Record<string, number>;
    rationale?: string;
    generated_at?: string;
    pipeline_ms?: number;
}

// ── Agent Outputs (for Section C narrative cards) ──────────────

export interface LegendConsensus {
    bull: number; neutral: number; bear: number; total: number; summary: string;
}

export interface AnalysisResult {
    status: string;
    data: FinalVerdict;
    // Full agent outputs for sections
    l1?: Record<string, unknown>;
    l2?: Record<string, unknown>;
    l3?: Record<string, unknown>;
    l4?: Record<string, unknown>;
    l5?: Record<string, unknown>;
    l6?: Record<string, unknown>;
    l7?: Record<string, unknown>;
    l8?: Record<string, unknown>;
    l9?: Record<string, unknown>;
}
