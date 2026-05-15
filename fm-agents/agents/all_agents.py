"""
FM Trading Agency — All 9 Agent Nodes
========================================
L1 Macro Sieve → L2 Fundamentals → L3 Technical → L4 Patterns →
L5 Sentiment → L6 Options → L7 Strategy → L8 Risk → L9 Sovereign

Each agent:
  • READS pre-computed numbers from state (never recomputes them)
  • INTERPRETS and REASONS about them
  • Returns a typed Pydantic schema (Zero-Placeholder Policy enforced)

L1-L6 run in PARALLEL (LangGraph fan-out)
L7-L9 run SEQUENTIALLY after all parallel agents complete
"""

from __future__ import annotations
from typing import Any

from schemas.agent_outputs import (
    AgentState,
    L1MacroResult, L2FundamentalsResult, L3TechnicalResult,
    L4PatternResult, L5SentimentResult, L6OptionsResult,
    L7StrategyResult, L8RiskResult, L9SovereignResult,
    LegendConsensus, WaitDetails, StrategyPlan, BearPivotEntry,
)
from agents.base import call_agent, fmt_ind, fmt_oc, fmt_macro, fmt_oi_change

import logging
log = logging.getLogger("fm.agents")


# ════════════════════════════════════════════════════════════════
# L1 — MACRO SIEVE
# ════════════════════════════════════════════════════════════════

def run_l1_macro(state: AgentState, llm) -> dict:
    mc   = state.get("macro_context", {})
    sess = state.get("session_ctx", {})
    sym  = state.get("symbol", "NIFTY 50")

    system = (
        "You are L1 Macro Sieve — the first filter in a 9-layer trading pipeline. "
        "Your job: assess the macro environment and determine if trading is safe. "
        "You READ pre-computed numbers — you do NOT recompute them. "
        "OIL SHOCK LAW: oil > $100 blocks LONG positions only (SHORT is a bear confirmation). "
        "If LONG is blocked, set short_search_triggered=true. "
        "ZERO-PLACEHOLDER: confidence must be 1-100, never 0."
    )

    # Gift Nifty premium tells us pre-market direction
    gift     = mc.get("gift_nifty")
    gift_prem= mc.get("gift_premium")
    global_r = mc.get("global_risk", "")
    events   = mc.get("events_next_7_days", [])
    ev_str   = ", ".join(f"{e['event']} in {e['days_away']}d" for e in events[:2]) if events else "None"

    user = (
        f"INDEX: {sym}\n"
        f"━━━ MACRO DATA ━━━\n{fmt_macro(mc)}\n"
        f"━━━ SESSION ━━━\n"
        f"Session: {sess.get('session', '?')} | "
        f"Expiry: {sess.get('is_expiry_day', False)} | "
        f"DTE: {sess.get('days_to_expiry', '?')}\n"
        f"{'━━━ GIFT NIFTY ━━━\n' if gift else ''}"
        f"{f'GIFT Nifty: {gift:.0f} (premium: {'+' if (gift_prem or 0)>=0 else ''}{gift_prem:.0f}pts) → ' if gift else ''}"
        f"{'Bullish gap-up expected' if (gift_prem or 0) > 50 else ('Bearish gap-down expected' if (gift_prem or 0) < -50 else 'Flat open') if gift else ''}\n"
        f"Global Risk: {global_r} | Upcoming: {ev_str}\n\n"
        f"Assess the macro environment. If oil > $100, LONG is blocked — set "
        f"short_search_triggered=true and oil_shock_active=true.\n"
        f"If GIFT Nifty shows strong negative premium (< -100pts), flag gap_risk=HIGH.\n\n"
        f'Return JSON: {{"agent":"l1_macro_sieve","status":"ALLOW|BLOCK|WATCH",'
        f'"risk_context":"RISK_ON|RISK_OFF|TRANSITION",'
        f'"oil_shock_active":false,"oil_shock_veto_applies":"LONG_ONLY|NONE",'
        f'"post_expiry_phase":false,"domestic_floor_active":false,'
        f'"short_search_triggered":false,"liquidity_state":"NORMAL|TIGHT|AMPLE",'
        f'"gap_risk":"LOW|MODERATE|HIGH","macro_score":0,"confidence":0,'
        f'"rationale":"2-3 sentences"}}' 
    )
    result = call_agent(llm, system, user, L1MacroResult, "L1")
    return {"l1_result": result}


# ════════════════════════════════════════════════════════════════
# L2 — FUNDAMENTALS
# ════════════════════════════════════════════════════════════════

def run_l2_fundamentals(state: AgentState, llm) -> dict:
    mc  = state.get("macro_context", {})
    sym = state.get("symbol", "NIFTY 50")

    system = (
        "You are L2 Fundamentals — assessing index-level valuation health. "
        "Use macro context and general knowledge of NSE index fundamentals. "
        "ZERO-PLACEHOLDER: fundamental_score and confidence must be 1-100."
    )

    user = (
        f"INDEX: {sym}\n"
        f"MACRO: {fmt_macro(mc)}\n"
        f"VIX regime: {mc.get('vix_regime', '?')}\n\n"
        f"Assess: Is the index fundamentally healthy? "
        f"Is valuation stretched? Are earnings accelerating?\n\n"
        f'Return JSON: {{"agent":"l2_fundamentals","status":"ALLOW|WATCH|BLOCK",'
        f'"valuation_status":"OVERVALUED|FAIR|UNDERVALUED",'
        f'"valuation_context":"one line","earnings_trend":"ACCELERATING|STABLE|DECELERATING",'
        f'"sector_leadership":"leading sectors","institutional_flow":"BUILDING|DISTRIBUTING|FLAT",'
        f'"fundamental_score":0,"confidence":0,"rationale":"2-3 sentences"}}'
    )

    result = call_agent(llm, system, user, L2FundamentalsResult, "L2")
    return {"l2_result": result}


# ════════════════════════════════════════════════════════════════
# L3 — TECHNICAL
# ════════════════════════════════════════════════════════════════

def run_l3_technical(state: AgentState, llm) -> dict:
    ind  = state.get("indicator_pack", {})
    mti  = state.get("multi_tf", {})
    rr   = state.get("regime_result", {})
    sym  = state.get("symbol", "NIFTY 50")
    spot = state.get("spot", 0)

    system = (
        "You are L3 Technical — synthesising technical indicator data. "
        "CRITICAL: You READ the pre-computed indicators — you do NOT recalculate RSI/MACD/EMA. "
        "Your job is to INTERPRET what these numbers mean together as a coherent technical picture. "
        "SYNTHETIC DATA LAW: if status=BLOCKED appears in indicators, set status=BLOCKED. "
        "ZERO-PLACEHOLDER: all scores must be 1-100."
    )

    multi_tf_str = ""
    if mti:
        alignment = mti.get("alignment", "MIXED")
        daily   = (mti.get("daily",    {}) or {}).get("indicators", {})
        hourly  = (mti.get("hourly",   {}) or {}).get("indicators", {})
        intra   = (mti.get("intraday", {}) or {}).get("indicators", {})
        multi_tf_str = (
            f"Multi-TF: {alignment} | "
            f"Daily RSI: {daily.get('rsi','?')} | "
            f"1H RSI: {hourly.get('rsi','?')} | "
            f"15M RSI: {intra.get('rsi','?')}"
        )

    user = (
        f"INDEX: {sym} | SPOT: {spot}\n"
        f"INDICATORS: {fmt_ind(ind)}\n"
        f"REGIME (from quant engine): {rr.get('regime', '?')} "
        f"(conf {rr.get('confidence', '?')})\n"
        f"{multi_tf_str}\n\n"
        f"Synthesise the technical picture. What is the dominant direction? "
        f"Is the setup actionable?\n\n"
        f'Return JSON: {{"agent":"l3_technical","status":"ALLOW|BLOCKED",'
        f'"trend_regime":"string","setup_type":"string","direction":"LONG|SHORT|NEUTRAL",'
        f'"ema_stack":"{ind.get("ema_stack","MIXED")}",'
        f'"rsi_zone":"{ind.get("rsi_zone","NEUTRAL")}",'
        f'"macd_status":"BULL_CROSS|BEAR_CROSS|DIVERGENCE|NEUTRAL",'
        f'"vwap_position":"ABOVE|BELOW|AT",'
        f'"supertrend_dir":"{ind.get("supertrend_dir","NEUTRAL")}",'
        f'"adx_strength":"{ind.get("adx_strength","WEAK")}",'
        f'"multi_tf_alignment":{{"daily":"string","hourly":"string",'
        f'"intraday":"string","scalp":"string","summary":"BULL_ALIGNED|BEAR_ALIGNED|MIXED"}},'
        f'"technical_score":0,"confidence":0,"rationale":"2-3 sentences"}}'
    )

    result = call_agent(llm, system, user, L3TechnicalResult, "L3")
    return {"l3_result": result}


# ════════════════════════════════════════════════════════════════
# L4 — PATTERNS
# ════════════════════════════════════════════════════════════════

def run_l4_patterns(state: AgentState, llm) -> dict:
    ind  = state.get("indicator_pack", {})
    oc   = state.get("options_chain",  {})
    sym  = state.get("symbol", "NIFTY 50")
    spot = state.get("spot", 0)

    system = (
        "You are L4 Pattern Engine — detecting chart patterns and their implications. "
        "BULL TRAP LAW: if a bullish breakout is detected but volume is weak and OPR is CALL_DOMINANT, "
        "classify as TRAP and set bull_trap_detected=true. "
        "SHORT_SELL_SEARCH LAW: every BLOCK or TRAP must return a bear_pivot_entry plan. "
        "ZERO-PLACEHOLDER: all scores must be 1-100."
    )

    rr  = state.get("regime_result", {})
    user = (
        f"INDEX: {sym} | SPOT: {spot}\n"
        f"EMA Stack: {ind.get('ema_stack','?')} | RSI: {ind.get('rsi','?')} | "
        f"ADX: {ind.get('adx','?')} | Supertrend: {ind.get('supertrend_dir','?')}\n"
        f"BB: upper={ind.get('bb_upper','?')} lower={ind.get('bb_lower','?')}\n"
        f"OPR Signal: {oc.get('opr_signal','?')} | PCR: {oc.get('pcr','?')}\n"
        f"Regime: {rr.get('regime','?')} | Bias: {rr.get('directional_bias','?')}\n\n"
        f"Identify the dominant chart pattern. If bull trap, provide bear pivot entry. "
        f"All blocking patterns MUST provide an opposite-direction alternative.\n\n"
        f'Return JSON: {{"agent":"l4_patterns","status":"ALLOW|BLOCK",'
        f'"primary_pattern":"pattern name or NO_PATTERN",'
        f'"pattern_state":"CONFIRMED|FORMING|FAILED|TRAP|NONE",'
        f'"direction":"LONG|SHORT|NEUTRAL","pattern_confidence":0,'
        f'"measured_move_target1":null,"measured_move_target2":null,'
        f'"invalidation_level":null,"trap_risk":"LOW|MODERATE|HIGH",'
        f'"failure_risk":"LOW|MODERATE|HIGH",'
        f'"bull_trap_detected":false,'
        f'"bear_pivot_entry":{{"entry_level":0,"stop_level":0,"target":0,"rr":0.0,'
        f'"condition":"string","instrument":"Short Futures / ATM PE"}},'
        f'"short_sell_search_active":false,'
        f'"entry_logic":"string","confidence":0,"rationale":"2-3 sentences"}}'
    )

    result = call_agent(llm, system, user, L4PatternResult, "L4")
    return {"l4_result": result}


# ════════════════════════════════════════════════════════════════
# L5 — SENTIMENT
# ════════════════════════════════════════════════════════════════

def run_l5_sentiment(state: AgentState, llm) -> dict:
    mc        = state.get("macro_context", {})
    headlines = state.get("news_headlines", [])
    event_ctx = state.get("event_context",  {})
    sym       = state.get("symbol", "NIFTY 50")

    system = (
        "You are L5 Sentiment — assessing market mood from news, flow data, and events. "
        "ANTI-HALLUCINATION LAW: Only use the actual headlines provided below. "
        "Do NOT invent headlines. If no headlines, say so. "
        "ZERO-PLACEHOLDER: fear_greed_proxy and confidence must be 1-100."
    )

    headlines_str = "\n".join([f"  • {h}" for h in headlines[:8]]) if headlines else "  (No headlines available)"

    # RBI and event calendar context
    rbi_hl      = mc.get("rbi_latest_headline", "")
    events      = mc.get("events_next_7_days", [])
    is_rbi_week = mc.get("is_rbi_week", False)
    is_fomc_week= mc.get("is_fomc_week", False)
    is_results  = mc.get("is_result_season", False)
    ev_str = ", ".join(f"{e['event']} ({e['days_away']}d away)" for e in events[:3]) if events else "No major events"

    user = (
        f"INDEX: {sym}\n"
        f"ACTUAL HEADLINES (use only these — do not invent others):\n{headlines_str}\n\n"
        f"MACRO FLOW: FII={mc.get('fii_net','?')}Cr | DII={mc.get('dii_net','?')}Cr | "
        f"DomFloor={mc.get('domestic_floor_active',False)}\n"
        f"EVENT CONTEXT: severity={event_ctx.get('event_severity','?')} | "
        f"events={event_ctx.get('detected_events',[])} | "
        f"narrative={event_ctx.get('narrative','')}\n"
        f"━━━ CALENDAR EVENTS ━━━\n"
        f"Upcoming: {ev_str}\n"
        f"{'⚠️ RBI WEEK — expect reduced risk appetite' if is_rbi_week else ''}"
        f"{'⚠️ FOMC WEEK — watch USD/INR and FII flows' if is_fomc_week else ''}"
        f"{'📊 RESULT SEASON — individual stock moves may diverge from index' if is_results else ''}\n"
        f"{f'RBI Latest: {rbi_hl}' if rbi_hl else ''}\n\n"
        f"Assess market sentiment direction. "
        f"Legend consensus: estimate BULL/NEUTRAL/BEAR split based on technical picture.\n\n"
        f'Return JSON: {{"agent":"l5_sentiment","status":"ALLOW|WATCH",'
        f'"narrative_direction":"RISING_BULLISH|STABLE|FADING|REVERSING",'
        f'"volatility_sentiment":"CALM|CAUTIOUS|STRESSED",'
        f'"fear_greed_proxy":0,"fear_greed_label":"Fear|Neutral|Greed",'
        f'"domestic_floor_signal":{str(mc.get("domestic_floor_active",False)).lower()},'
        f'"top_headlines":{str(headlines[:3])},'
        f'"legend_consensus":{{"bull":0,"neutral":0,"bear":0,"total":20,"summary":"string"}},'
        f'"confidence":0,"rationale":"2-3 sentences"}}' 
    )

    result = call_agent(llm, system, user, L5SentimentResult, "L5")
    return {"l5_result": result}


def run_l6_options(state: AgentState, llm) -> dict:
    oc     = state.get("options_chain",  {})
    ci     = state.get("chain_intel",    {})
    spot   = state.get("spot", 0)
    sym    = state.get("symbol", "NIFTY 50")

    system = (
        "You are L6 Options Flow Intelligence — interpreting derivatives market signals. "
        "CRITICAL: OPR, PCR, Max Pain, GEX, OI Change are PRE-COMPUTED. You READ and INTERPRET them. "
        "You do NOT calculate these numbers yourself. "
        "OI CHANGE LAW: Long buildup = new bulls, high conviction. Short covering = weak rally. "
        "ZERO-PLACEHOLDER: all scores must be 1-100."
    )

    # Get IV rank from stored history
    atm_iv = oc.get("atm_iv")
    iv_rank_live = iv_pct_live = None
    iv_regime_live = ci.get("iv_regime", "FAIR")
    try:
        from services.options_chain import get_iv_rank
        iv_rank_live, iv_pct_live, iv_regime_live = get_iv_rank(sym, atm_iv)
    except Exception:
        pass

    user = (
        f"INDEX: {sym} | SPOT: {spot}\n"
        f"OPTIONS CHAIN: {fmt_oc(oc)}\n"
        f"━━━ OI CHANGE ANALYSIS ━━━\n{fmt_oi_change(ci)}\n"
        f"━━━ DEALER INTELLIGENCE ━━━\n"
        f"GEX: {ci.get('net_gex','?')} | Dealer Stance: {ci.get('dealer_stance','?')}\n"
        f"Gamma Flip: {ci.get('gamma_flip_level','?')} | "
        f"IV Regime: {iv_regime_live} | "
        f"IV Rank: {iv_rank_live if iv_rank_live is not None else '?'} | "
        f"IV%ile: {iv_pct_live if iv_pct_live is not None else ci.get('iv_percentile','?')}\n"
        f"Call Wall: {ci.get('call_oi_wall','?')} | Put Wall: {ci.get('put_oi_wall','?')}\n"
        f"Max Pain Pull: {ci.get('max_pain_pull_pts','?')}pts | "
        f"Expiry Pin Risk: {ci.get('expiry_pin_risk','?')}\n\n"
        f"KEY: If IV is CHEAP (< 30th pct), buy options outright. "
        f"If IV is EXPENSIVE (> 70th pct), sell spreads or use iron condor.\n"
        f"KEY: If OI shows LONG_BUILDUP, strong directional conviction. "
        f"If SHORT_COVERING, don't chase — rally may be temporary.\n\n"
        f"Interpret the options market intelligence. "
        f"What is the institutional positioning? What vehicle is best?\n\n"
        f'Return JSON: {{"agent":"l6_options_flow","status":"ALLOW|WATCH|BLOCK",'
        f'"options_bias":"BULLISH|BEARISH|NEUTRAL",'
        f'"opr_interpretation":"string","pcr_signal":"string","max_pain_pull":"string",'
        f'"oi_change_pattern":"{(ci.get('oi_change') or {{}}).get('pattern','NEUTRAL')}",'
        f'"call_wall_level":{oc.get("call_wall") or "null"},'
        f'"put_wall_level":{oc.get("put_wall") or "null"},'
        f'"gamma_flip_level":{ci.get("gamma_flip_level") or "null"},'
        f'"dealer_stance":"{ci.get("dealer_stance","NEUTRAL")}",'
        f'"iv_regime":"{iv_regime_live}",'
        f'"best_execution_vehicle":"Futures|ATM CE|ATM PE|Iron Condor|Bull Call Spread|Bear Put Spread",'
        f'"flow_conviction_score":0,"confidence":0,"rationale":"2-3 sentences"}}' 
    )

    result = call_agent(llm, system, user, L6OptionsResult, "L6")
    return {"l6_result": result}


def run_l7_strategy(state: AgentState, llm_deep) -> dict:
    ind    = state.get("indicator_pack", {})
    oc     = state.get("options_chain",  {})
    spot   = state.get("spot", 0)
    sym    = state.get("symbol", "NIFTY 50")
    rr     = state.get("regime_result",  {})

    l1 = state.get("l1_result") or L1MacroResult()
    l2 = state.get("l2_result") or L2FundamentalsResult()
    l3 = state.get("l3_result") or L3TechnicalResult()
    l4 = state.get("l4_result") or L4PatternResult()
    l5 = state.get("l5_result") or L5SentimentResult()
    l6 = state.get("l6_result") or L6OptionsResult()

    # Compute directional math for trade plans
    sl_bull   = round(spot * 0.993)
    t1_bull   = round(spot * 1.009)
    t2_bull   = round(spot * 1.016)
    t3_bull   = round(spot * 1.025)
    sl_bear   = round(spot * 1.007)
    t1_bear   = round(spot * 0.991)
    t2_bear   = round(spot * 0.984)
    t3_bear   = round(spot * 0.975)

    system = (
        "You are L7 Strategy Allocation Engine — choosing the optimal trading strategy. "
        "v5.0 MANDATE: You MUST return all three strategy plans (bull, bear, hedge) simultaneously. "
        "The primary_recommendation selects which one to execute. "
        "BEAR MATH LAW: for bear plans, SL MUST be > entry, targets MUST be < entry. "
        "BULL MATH LAW: for bull plans, SL MUST be < entry, targets MUST be > entry. "
        "ZERO-PLACEHOLDER: all scores must be 1-100."
    )

    user = (
        f"INDEX: {sym} | SPOT: {spot}\n"
        f"REGIME: {rr.get('regime','?')} | Bias: {rr.get('directional_bias','?')} "
        f"(conf {rr.get('confidence','?')})\n"
        f"L1 Macro: {l1.status} | {l1.risk_context} | OilShock: {l1.oil_shock_active}\n"
        f"L2 Fundamentals: {l2.fundamental_score}/100 | {l2.earnings_trend}\n"
        f"L3 Technical: {l3.direction} | {l3.setup_type} | Score: {l3.technical_score}\n"
        f"L4 Pattern: {l4.primary_pattern} ({l4.pattern_state}) | Trap: {l4.bull_trap_detected}\n"
        f"L5 Sentiment: {l5.narrative_direction} | F&G: {l5.fear_greed_proxy}\n"
        f"L6 Options: {l6.options_bias} | {l6.best_execution_vehicle} | "
        f"Conv: {l6.flow_conviction_score}\n\n"
        f"DIRECTIONAL MATH REFERENCE (use these levels):\n"
        f"  BULL: Entry ~{spot}, SL {sl_bull} (MUST be < entry), T1 {t1_bull}, T2 {t2_bull}, T3 {t3_bull}\n"
        f"  BEAR: Entry ~{spot}, SL {sl_bear} (MUST be > entry), T1 {t1_bear}, T2 {t2_bear}, T3 {t3_bear}\n"
        f"  HEDGE: Iron Condor at Max Pain {oc.get('max_pain', spot)}\n\n"
        f"Select primary recommendation and fill all three plans.\n\n"
        f'Return JSON: {{"agent":"l7_strategy","status":"ALLOW|BLOCK",'
        f'"primary_recommendation":"BULL_TRADE|BEAR_TRADE|HEDGE_TRADE|WAIT",'
        f'"bull_plan":{{"selected_strategy":"string","entry_zone":"string",'
        f'"stop_loss":{sl_bull},"target1":{t1_bull},"target2":{t2_bull},"target3":{t3_bull},'
        f'"rr":"1:2","instrument":"string","entry_trigger":"string","invalidation":"string",'
        f'"holding_period":"INTRADAY|SWING","fit_score":0}},'
        f'"bear_plan":{{"selected_strategy":"string","entry_zone":"string",'
        f'"stop_loss":{sl_bear},"target1":{t1_bear},"target2":{t2_bear},"target3":{t3_bear},'
        f'"rr":"1:1.8","instrument":"string","entry_trigger":"string","invalidation":"string",'
        f'"holding_period":"INTRADAY|SWING","fit_score":0}},'
        f'"hedge_plan_strategy":{{"selected_strategy":"IRON_CONDOR",'
        f'"entry_zone":"Max Pain zone","stop_loss":0,"target1":0,"target2":0,'
        f'"instrument":"Iron Condor","entry_trigger":"string","invalidation":"string",'
        f'"holding_period":"EXPIRY","fit_score":0}},'
        f'"rejected_strategies":[],"strategy_conflict_flag":false,'
        f'"confidence":0,"rationale":"3 sentences"}}'
    )

    result = call_agent(llm_deep, system, user, L7StrategyResult, "L7")
    return {"l7_result": result}


# ════════════════════════════════════════════════════════════════
# L8 — RISK GOVERNOR (reads from fm-quant RiskDecision)
# ════════════════════════════════════════════════════════════════

def run_l8_risk(state: AgentState) -> dict:
    """
    L8 reads directly from the fm-quant RiskDecision.
    NO LLM CALL — this is the hard governance layer.
    The risk numbers are already computed by fm-quant/risk/governor.py.
    """
    rd   = state.get("risk_decision", {})
    sess = state.get("session_ctx",   {})
    spot = state.get("spot", 0)

    result = L8RiskResult(
        authorized          = rd.get("authorized",         True),
        unit_count          = rd.get("unit_count",         0),
        max_risk_per_trade  = rd.get("max_risk_per_trade", 0),
        kill_switch         = rd.get("kill_switch",        False),
        veto_reason         = rd.get("veto_reason",        ""),
        risk_state          = rd.get("risk_state",         "LOW"),
        daily_dd_pct        = rd.get("daily_dd_pct",       0.0),
        weekly_dd_pct       = rd.get("weekly_dd_pct",      0.0),
        loss_streak         = rd.get("loss_streak",        0),
        size_reduction_pct  = rd.get("size_reduction_pct", 0.0),
        hedge_mandatory     = rd.get("hedge_mandatory",    True),
        confidence          = 90,   # Risk decisions are deterministic
        warnings            = rd.get("warnings",           []),
    )
    return {"l8_result": result}


# ════════════════════════════════════════════════════════════════
# L9 — SOVEREIGN DECISION ENGINE (DEEP model)
# ════════════════════════════════════════════════════════════════

def run_l9_sovereign(state: AgentState, llm_deep) -> dict:
    spot   = state.get("spot", 0)
    sym    = state.get("symbol", "NIFTY 50")
    sess   = state.get("session_ctx",   {})
    rr     = state.get("regime_result", {})
    cas    = state.get("cascade_result",{})   # from fm-quant cascade
    mc     = state.get("macro_context", {})
    oc     = state.get("options_chain", {})

    l1 = state.get("l1_result") or L1MacroResult()
    l2 = state.get("l2_result") or L2FundamentalsResult()
    l3 = state.get("l3_result") or L3TechnicalResult()
    l4 = state.get("l4_result") or L4PatternResult()
    l5 = state.get("l5_result") or L5SentimentResult()
    l6 = state.get("l6_result") or L6OptionsResult()
    l7 = state.get("l7_result") or L7StrategyResult()
    l8 = state.get("l8_result") or L8RiskResult()

    # Compute execution score from layer confidence scores
    scores = [
        l1.confidence * 0.10, l2.confidence * 0.08, l3.technical_score * 0.18,
        l4.pattern_confidence * 0.12, l5.confidence * 0.08,
        l6.flow_conviction_score * 0.14, l7.confidence * 0.15,
        l8.confidence * 0.15,
    ]
    execution_score = int(sum(scores))

    # Session multiplier from quant engine
    sess_mult = sess.get("session_confidence_multiplier", 1.0)
    execution_score = max(1, min(95, int(execution_score * sess_mult)))

    # Cascade suggestion (from fm-quant — the quant recommendation)
    cascade_verdict = cas.get("verdict", "WAIT")
    cascade_reason  = cas.get("cascade_reason", "")

    system = (
        "You are L9 Sovereign Decision Engine — the FINAL AUTHORITY. "
        "v5.0 ALWAYS-TRADE MANDATE: final_verdict must be one of: "
        "BULL_TRADE | BEAR_TRADE | HEDGE_TRADE | WAIT. "
        "NO_TRADE IS ABOLISHED. WAIT is not NO_TRADE — it requires re_entry_trigger, "
        "re_entry_window_minutes (max 30), re_entry_condition, pivot_plan. "
        "BEAR MATH LAW: SL MUST be > entry for SHORT, < entry for LONG. "
        "ZERO-PLACEHOLDER LAW: confidence_score and execution_score must be 1-100. "
        "L8 Risk Governor is ABSOLUTE — if authorized=False, verdict MUST be WAIT."
    )

    sl_long  = round(spot * 0.993)
    t1_long  = round(spot * 1.009)
    t2_long  = round(spot * 1.016)
    sl_short = round(spot * 1.007)
    t1_short = round(spot * 0.991)
    t2_short = round(spot * 0.984)

    user = (
        f"INDEX: {sym} | SPOT: {spot} | IST: {sess.get('ist_time','?')}\n\n"
        f"=== QUANT CASCADE RECOMMENDATION ===\n"
        f"Cascade says: {cascade_verdict} (step {cas.get('cascade_step','?')})\n"
        f"Reason: {cascade_reason}\n\n"
        f"=== ALL LAYER OUTPUTS ===\n"
        f"L1 Macro: {l1.status} | {l1.risk_context} | OilShock: {l1.oil_shock_active} "
        f"| ShortTriggered: {l1.short_search_triggered} (conf {l1.confidence})\n"
        f"L2 Fund: {l2.fundamental_score}/100 | {l2.valuation_status} "
        f"| {l2.earnings_trend} (conf {l2.confidence})\n"
        f"L3 Tech: {l3.direction} | Score {l3.technical_score} "
        f"| EMA {l3.ema_stack} | RSI {l3.rsi_zone} (conf {l3.confidence})\n"
        f"L4 Pattern: {l4.primary_pattern} ({l4.pattern_state}) "
        f"| Trap: {l4.bull_trap_detected} (conf {l4.confidence})\n"
        f"L5 Sentiment: {l5.narrative_direction} | F&G {l5.fear_greed_proxy} (conf {l5.confidence})\n"
        f"L6 Options: {l6.options_bias} | {l6.dealer_stance} "
        f"| {l6.iv_regime} IV (conf {l6.confidence})\n"
        f"L7 Strategy: recommends {l7.primary_recommendation} (conf {l7.confidence})\n"
        f"L8 Risk: authorized={l8.authorized} | units={l8.unit_count} "
        f"| {l8.risk_state} | dd={l8.daily_dd_pct:.1f}%\n\n"
        f"=== EXECUTION SCORE ===\n"
        f"Computed: {execution_score}/100 (session mult {sess_mult:.1f}x)\n"
        f"Threshold: ≥65 to execute\n\n"
        f"=== DECISION RULES ===\n"
        f"1. If L8 authorized=False → WAIT (kill switch or DD limit)\n"
        f"2. If score ≥65 + LONG signals dominant → BULL_TRADE\n"
        f"3. If score ≥65 + SHORT signals → BEAR_TRADE\n"
        f"4. If oil shock + bear viable → BEAR_TRADE\n"
        f"5. If ADX weak + VIX 14-20 → HEDGE_TRADE (Iron Condor)\n"
        f"6. Expiry day + Max Pain pull → HEDGE_TRADE\n"
        f"7. All blocked → WAIT with specific re-entry trigger\n\n"
        f"DIRECTIONAL MATH (HARD RULE — do not deviate):\n"
        f"  BULL: SL={sl_long} (<{spot}), T1={t1_long}, T2={t2_long}\n"
        f"  BEAR: SL={sl_short} (>{spot}), T1={t1_short}, T2={t2_short}\n\n"
        f'Return JSON: {{"agent":"l9_sovereign_decision",'
        f'"final_verdict":"BULL_TRADE|BEAR_TRADE|HEDGE_TRADE|WAIT",'
        f'"direction":"LONG|SHORT|NEUTRAL",'
        f'"confidence_score":0,"execution_score":{execution_score},'
        f'"market_regime":"string",'
        f'"strategy_selected":"string",'
        f'"entry_zone":{{"low":{round(spot*0.998)},"high":{round(spot*1.002)}}},'
        f'"stop_loss":0,"target1":0,"target2":0,"target3":null,'
        f'"rr_ratio":0.0,"instrument":"string",'
        f'"entry_trigger":"string","invalidation_logic":"string",'
        f'"holding_period":"INTRADAY|SWING",'
        f'"position_sizing":"N units",'
        f'"wait_details":{{"re_entry_trigger":"price level",'
        f'"re_entry_condition":"exact condition",'
        f'"re_entry_window_minutes":30,'
        f'"pivot_plan":"what to do if trigger missed"}},'
        f'"oil_shock_active":{str(l1.oil_shock_active).lower()},'
        f'"bear_pivot_activated":{str(l4.bull_trap_detected).lower()},'
        f'"hedge_trade_activated":false,'
        f'"top5_reasons_for":["r1","r2","r3","r4","r5"],'
        f'"top5_risks_against":["r1","r2","r3","r4","r5"],'
        f'"macro_condition":"one line","technical_condition":"one line",'
        f'"pattern_condition":"one line","sentiment_condition":"one line",'
        f'"options_condition":"one line",'
        f'"authorized":{str(l8.authorized).lower()},'
        f'"rationale":"3 sentences explaining the final decision"}}'
    )

    result = call_agent(llm_deep, system, user, L9SovereignResult, "L9")
    return {"l9_result": result}
