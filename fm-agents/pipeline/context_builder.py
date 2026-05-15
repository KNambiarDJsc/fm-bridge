"""
FM Trading Agency — Context Builder
=====================================
Fetches all data from fm-bridge and runs fm-quant BEFORE the agents start.
The agents then READ pre-computed numbers — they never fetch or compute.

This separation is critical:
  fm-bridge  → live market data (HTTP calls)
  fm-quant   → math (indicators, regime, OPR, hedge pricing, risk)
  fm-agents  → interpretation and reasoning (LLM calls)
"""

from __future__ import annotations

import sys
import os
import time
import logging
from typing import Optional

import requests

from schemas.agent_outputs import AgentState

log = logging.getLogger("fm.agents.context")

# Add fm-quant to path
_QUANT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "fm-quant")
if os.path.exists(_QUANT_PATH):
    sys.path.insert(0, _QUANT_PATH)


def _get(bridge_url: str, path: str, params: dict = None, timeout: int = 10) -> dict:
    """GET from bridge with fallback to empty dict."""
    try:
        r = requests.get(f"{bridge_url}{path}", params=params, timeout=timeout)
        if r.ok:
            return r.json()
    except Exception as e:
        log.warning("Bridge GET %s failed: %s", path, e)
    return {}


def build_context(
    symbol:      str   = "NIFTY 50",
    bridge_url:  str   = "http://localhost:8002",
    timeout:     int   = 10,
) -> AgentState:
    """
    Fetch all data from bridge + run quant engine.
    Returns a populated AgentState ready for the LangGraph pipeline.
    """
    t0 = time.time()
    log.info("Building context for %s ...", symbol)

    state: AgentState = {
        "symbol":          symbol,
        "spot":            0.0,
        "ist_time":        "",
        "indicator_pack":  {},
        "options_chain":   {},
        "macro_context":   {},
        "session_ctx":     {},
        "capital_shield":  {},
        "global_cues":     {},
        "news_headlines":  [],
        "regime_result":   {},
        "chain_intel":     {},
        "risk_decision":   {},
        "cascade_input":   {},
        "cascade_result":  {},
    }

    # ── 1. Live price ─────────────────────────────────────────────
    ltp = _get(bridge_url, "/api/ltp", {"index": symbol}, timeout)
    state["spot"] = float(ltp.get("price", 0) or 0)
    log.debug("spot=%s", state["spot"])

    # ── 2. Indicators ─────────────────────────────────────────────
    ind = _get(bridge_url, "/api/indicators", {"symbol": symbol, "interval": "day"}, timeout)
    state["indicator_pack"] = ind.get("indicators") or ind

    # ── 3. Options chain ──────────────────────────────────────────
    oc = _get(bridge_url, "/api/options-chain", {"symbol": symbol}, timeout)
    state["options_chain"] = oc

    # ── 4. Macro context ──────────────────────────────────────────
    mc = _get(bridge_url, "/api/macro-context", timeout=timeout)
    state["macro_context"] = mc

    # ── NEW: Global cues (GIFT Nifty, USD/INR, Dow, RBI, event calendar) ──
    try:
        gcues = _get(bridge_url, "/api/global-cues", timeout=timeout)
        if gcues:
            # Merge global cue fields into macro_context dict for agents
            mc_merged = dict(mc)
            for k in ["usd_inr","gift_nifty","gift_premium","gift_premium_pct",
                      "dow_change_pct","nasdaq_change_pct","global_risk",
                      "rbi_latest_headline","events_next_7_days","next_expiry",
                      "days_to_expiry","is_rbi_week","is_fomc_week","is_result_season",
                      "inr_weak"]:
                if k in gcues:
                    mc_merged[k] = gcues[k]
            # Override RBI stance with live RSS value
            if gcues.get("rbi_stance"):
                mc_merged["rbi_stance"] = gcues["rbi_stance"]
            state["macro_context"] = mc_merged
            state["global_cues"]   = gcues
    except Exception as e:
        log.debug("Global cues fetch failed (non-fatal): %s", e)

    # ── 5. Session context ────────────────────────────────────────
    sess = _get(bridge_url, "/api/session", timeout=timeout)
    state["session_ctx"]   = sess
    state["ist_time"]      = sess.get("ist_time", "")

    # ── 6. Capital shield ─────────────────────────────────────────
    shield = _get(bridge_url, "/api/capital-shield", timeout=timeout)
    state["capital_shield"] = shield

    # ── 7. Multi-TF indicators ────────────────────────────────────
    mti = _get(bridge_url, f"/api/timeframes/{symbol}", timeout=timeout + 5)
    state["multi_tf"] = mti

    # ── 8. News headlines ─────────────────────────────────────────
    try:
        from news.fetcher import fetch_all_headlines
        state["news_headlines"] = fetch_all_headlines(symbol)
    except Exception as e:
        log.warning("News fetch failed: %s", e)
        state["news_headlines"] = []

    # ── 9. Run quant engine (Phase 2) ─────────────────────────────
    try:
        _run_quant(state)
    except Exception as e:
        log.warning("Quant engine failed (non-fatal): %s", e)

    t1 = time.time()
    log.info(
        "Context ready in %.1fs | spot=%s | headlines=%d | regime=%s",
        t1 - t0, state["spot"], len(state["news_headlines"]),
        state.get("regime_result", {}).get("regime", "?"),
    )
    return state


def _run_quant(state: AgentState) -> None:
    """Run fm-quant modules to pre-compute all math before agents run."""

    from models_local import (
        IndicatorPack, OptionsChain, MacroContext, SessionContext, CapitalShield
    )

    ind_dict    = state.get("indicator_pack",  {}) or {}
    oc_dict     = state.get("options_chain",   {}) or {}
    mc_dict     = state.get("macro_context",   {}) or {}
    sess_dict   = state.get("session_ctx",     {}) or {}
    shield_dict = state.get("capital_shield",  {}) or {}

    # Build Pydantic objects for quant engine
    ind    = _safe_model(IndicatorPack,  {**ind_dict,  "symbol": state.get("symbol",""), "interval":"day"})
    oc     = _safe_model(OptionsChain,   {**oc_dict})
    macro  = _safe_model(MacroContext,   {**mc_dict})
    sess   = _safe_model(SessionContext, {**sess_dict})
    shield = _safe_model(CapitalShield,  {**shield_dict})

    # ── Regime detection ─────────────────────────────────────────
    from regime.engine import detect_regime
    rr = detect_regime(ind=ind, oc=oc, macro=macro, session=sess)
    state["regime_result"] = rr.to_dict()

    # ── Chain intelligence (advanced options analysis) ────────────
    from options.chain_analysis import analyse_chain
    ci = analyse_chain(oc)
    state["chain_intel"] = ci.to_dict()

    # ── Risk Governor ─────────────────────────────────────────────
    from risk.governor import evaluate
    spot = state.get("spot", 0)
    l3_ind = state.get("indicator_pack", {}) or {}
    atr_pct  = float(l3_ind.get("atr_pct", 1.0) or 1.0)
    stop_dist = max(1, spot * atr_pct / 100 * 1.5)  # 1.5× ATR as proxy stop
    lot_size  = 25   # default; L8 will refine

    rd = evaluate(
        shield       = shield,
        stop_distance= stop_dist,
        lot_size     = lot_size,
        session      = sess,
        vix          = macro.india_vix,
        dte_days     = oc.dte,
    )
    state["risk_decision"] = rd.to_dict()

    # ── Always-Trade Cascade ──────────────────────────────────────
    from signals.cascade import build_cascade_input, run_cascade

    # We don't have L9 score yet — use a proxy from quant signals
    tech_score = int(l3_ind.get("rsi", 50) or 50)
    proxy_score = min(90, max(10, tech_score))

    ci_obj = build_cascade_input(
        ind            = ind,
        oc             = oc,
        macro          = macro,
        session        = sess,
        shield         = shield,
        regime_result  = rr,
        execution_score= proxy_score,
        data_is_synthetic = False,
    )
    cascade = run_cascade(ci_obj)
    state["cascade_result"] = cascade.to_dict()


def _safe_model(cls, data: dict):
    """Build a Pydantic model from a dict, ignoring unknown fields."""
    try:
        fields = set(cls.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered)
    except Exception as e:
        log.debug("Safe model %s failed: %s — using defaults", cls.__name__, e)
        return cls()
