"""
FM Trading Agency — LangGraph Pipeline
=========================================
9-layer pipeline built as a LangGraph StateGraph.

Architecture (study TradingAgents/graph/trading_graph.py):
  START
    ↓
  [PREPARE] — fetch bridge data, run quant engine
    ↓
  ┌─────────────────────────────────────────┐
  │  L1  L2  L3  L4  L5  L6  (PARALLEL)   │
  └─────────────────────────────────────────┘
    ↓  (fan-in — all 6 complete)
  L7 Strategy  (DEEP model)
    ↓
  L8 Risk Governor  (no LLM — reads from fm-quant)
    ↓
  L9 Sovereign  (DEEP model)
    ↓
  [BUILD_VERDICT] — construct FinalVerdict
    ↓
  END

Timing target: 8-12 seconds total
  Parallel L1-L6: ~4-6s (6 concurrent Gemini Flash calls)
  Sequential L7-L9: ~4-6s (2 Gemini Pro calls + 1 no-LLM)
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from schemas.agent_outputs import AgentState
from agents.all_agents import (
    run_l1_macro, run_l2_fundamentals, run_l3_technical,
    run_l4_patterns, run_l5_sentiment, run_l6_options,
    run_l7_strategy, run_l8_risk, run_l9_sovereign,
)

log = logging.getLogger("fm.agents.pipeline")


# ════════════════════════════════════════════════════════════════
# NODE WRAPPERS
# They close over the LLM instances injected at graph-build time.
# ════════════════════════════════════════════════════════════════

def make_nodes(llm_quick, llm_deep):
    """
    Create all node functions with LLM instances injected.
    Returns dict of node_name → callable(state) → dict.
    """

    def node_l1(state: AgentState) -> dict:
        return run_l1_macro(state, llm_quick)

    def node_l2(state: AgentState) -> dict:
        return run_l2_fundamentals(state, llm_quick)

    def node_l3(state: AgentState) -> dict:
        return run_l3_technical(state, llm_quick)

    def node_l4(state: AgentState) -> dict:
        return run_l4_patterns(state, llm_quick)

    def node_l5(state: AgentState) -> dict:
        return run_l5_sentiment(state, llm_quick)

    def node_l6(state: AgentState) -> dict:
        return run_l6_options(state, llm_quick)

    def node_l7(state: AgentState) -> dict:
        return run_l7_strategy(state, llm_deep)

    def node_l8(state: AgentState) -> dict:
        return run_l8_risk(state)   # no LLM

    def node_l9(state: AgentState) -> dict:
        return run_l9_sovereign(state, llm_deep)

    return {
        "l1": node_l1, "l2": node_l2, "l3": node_l3,
        "l4": node_l4, "l5": node_l5, "l6": node_l6,
        "l7": node_l7, "l8": node_l8, "l9": node_l9,
    }


# ════════════════════════════════════════════════════════════════
# BUILD VERDICT NODE — constructs FinalVerdict from L9 output
# ════════════════════════════════════════════════════════════════

def build_verdict_node(state: AgentState) -> dict:
    """
    Builds the FinalVerdict dict from L9 output + hedge computation.
    This is deterministic — no LLM call.
    """
    from schemas.agent_outputs import (
        L9SovereignResult, L8RiskResult, L6OptionsResult
    )

    l9  = state.get("l9_result") or L9SovereignResult()
    l8  = state.get("l8_result") or L8RiskResult()
    oc  = state.get("options_chain", {})
    rr  = state.get("regime_result", {})

    # Build layer scores dict
    layer_scores = {}
    for name, attr in [
        ("L1", "l1_result"), ("L2", "l2_result"), ("L3", "l3_result"),
        ("L4", "l4_result"), ("L5", "l5_result"), ("L6", "l6_result"),
        ("L7", "l7_result"), ("L8", "l8_result"), ("L9", "l9_result"),
    ]:
        obj = state.get(attr)
        if obj:
            conf = getattr(obj, "confidence", None) or getattr(obj, "technical_score", None) or 50
            layer_scores[name] = conf

    # Get hedge plan from quant engine
    hedge_dict = None
    try:
        spot    = state.get("spot", 0)
        vix     = (state.get("macro_context") or {}).get("india_vix") or 15.0
        dte     = oc.get("dte", 3)
        verdict = l9.final_verdict

        if verdict in ("BULL_TRADE", "BEAR_TRADE", "HEDGE_TRADE"):
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "fm-quant"))
            from options.hedge_calc import compute_hedge
            entry = l9.entry_zone.get("low", spot) if l9.entry_zone else spot
            hp = compute_hedge(
                verdict     = verdict,
                entry_price = entry,
                stop_loss   = l9.stop_loss or spot,
                spot        = spot,
                vix         = vix,
                dte_days    = dte,
                symbol      = state.get("symbol", "NIFTY 50"),
                max_pain    = oc.get("max_pain"),
                call_wall   = oc.get("call_wall"),
                put_wall    = oc.get("put_wall"),
            )
            hedge_dict = hp.model_dump()
    except Exception as e:
        log.warning("Hedge computation failed: %s", e)

    # Build trade plan dict
    trade_plan_dict = None
    if l9.final_verdict in ("BULL_TRADE", "BEAR_TRADE") and l9.stop_loss:
        direction = "LONG" if l9.final_verdict == "BULL_TRADE" else "SHORT"
        trade_plan_dict = {
            "direction":      direction,
            "entry_low":      l9.entry_zone.get("low",  state.get("spot", 0)) if l9.entry_zone else 0,
            "entry_high":     l9.entry_zone.get("high", state.get("spot", 0)) if l9.entry_zone else 0,
            "stop_loss":      l9.stop_loss,
            "target1":        l9.target1 or 0,
            "target2":        l9.target2 or 0,
            "target3":        l9.target3,
            "rr":             l9.rr_ratio or 0,
            "instrument":     l9.instrument,
            "entry_trigger":  l9.entry_trigger,
            "invalidation":   l9.invalidation_logic,
            "holding_period": l9.holding_period,
            "lot_size":       25,
        }

    # Wait signal dict
    wait_dict = None
    if l9.final_verdict == "WAIT" and l9.wait_details:
        wd = l9.wait_details
        wait_dict = {
            "reason":               l9.rationale,
            "instruction":          wd.re_entry_condition or "",
            "re_entry_trigger":     wd.re_entry_trigger or "",
            "re_entry_condition":   wd.re_entry_condition or "",
            "re_entry_window_minutes": min(30, wd.re_entry_window_minutes or 30),
            "pivot_plan":           wd.pivot_plan or "",
        }

    final = {
        "verdict":           l9.final_verdict,
        "regime":            rr.get("regime", "UNKNOWN"),
        "best_index":        state.get("symbol", "NIFTY 50"),
        "opportunity_score": l9.execution_score,
        "confidence":        l9.confidence_score,
        "risk_state":        l8.risk_state,
        "hedge_active":      hedge_dict is not None and l9.final_verdict != "WAIT",
        "trade_plan":        trade_plan_dict,
        "hedge_plan":        hedge_dict,
        "wait_signal":       wait_dict,
        "execution_score":   l9.execution_score,
        "layer_scores":      layer_scores,
        "rationale":         l9.rationale,
        "generated_at":      time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    log.info(
        "VERDICT: %s | Score: %d | Conf: %d | Regime: %s",
        final["verdict"], final["execution_score"],
        final["confidence"], final["regime"],
    )
    return {"final_verdict": final}


# ════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ════════════════════════════════════════════════════════════════

def build_pipeline(llm_quick, llm_deep) -> Any:
    """
    Build and compile the LangGraph StateGraph.

    Topology:
      START → [l1, l2, l3, l4, l5, l6 in parallel] → l7 → l8 → l9 → build_verdict → END
    """
    nodes = make_nodes(llm_quick, llm_deep)

    graph = StateGraph(AgentState)

    # ── Add all nodes ─────────────────────────────────────────────
    for name, fn in nodes.items():
        graph.add_node(name, fn)
    graph.add_node("build_verdict", build_verdict_node)

    # ── Correct parallel fan-out pattern (from LangGraph docs) ───
    # Pattern: START → prepare → [l1, l2, l3, l4, l5, l6] → l7 → l8 → l9 → verdict
    #
    # LangGraph parallel execution requires:
    #   1. A preceding node (or START) fans OUT to multiple nodes via multiple add_edge calls
    #   2. All parallel nodes fan IN to the same next node
    #   3. The fan-in node runs only after ALL parallel branches complete (same superstep)
    #
    # We fan out from START directly to all 6 agents using the START constant.
    # Each L1-L6 node has an edge FROM START (fan-out) and an edge TO l7 (fan-in).
    # LangGraph will execute L1-L6 in the same superstep (concurrently).
    # L7 only executes after all 6 complete.

    parallel_agents = ["l1", "l2", "l3", "l4", "l5", "l6"]

    # Fan-out: START → each parallel agent
    for name in parallel_agents:
        graph.add_edge(START, name)

    # Fan-in: each parallel agent → l7 (l7 waits for all 6)
    for name in parallel_agents:
        graph.add_edge(name, "l7")

    # Sequential: L7 → L8 → L9 → build_verdict → END
    graph.add_edge("l7", "l8")
    graph.add_edge("l8", "l9")
    graph.add_edge("l9", "build_verdict")
    graph.add_edge("build_verdict", END)

    compiled = graph.compile()
    log.info("Pipeline compiled: START→[L1-L6 parallel]→L7→L8→L9→verdict")

    # Wrap invoke() with LangSmith trace so the entire pipeline run
    # (all 9 agents) appears as a single trace tree in LangSmith.
    # Per SDK docs: use langsmith.trace() context manager for root runs.
    import os
    if os.getenv("LANGSMITH_API_KEY") and os.getenv("LANGSMITH_TRACING_V2") == "true":
        try:
            from langsmith import trace as ls_trace

            _original_invoke = compiled.invoke

            def traced_invoke(state: dict, *args, **kwargs) -> dict:
                symbol = state.get("symbol", "NIFTY 50")
                with ls_trace(
                    name      = f"FM Pipeline — {symbol}",
                    run_type  = "chain",
                    inputs    = {"symbol": symbol},
                    tags      = ["fm-trading-agency", "pipeline"],
                    metadata  = {
                        "symbol":  symbol,
                        "regime":  state.get("regime_result", {}).get("regime", "?"),
                        "session": (state.get("session_ctx") or {}).get("session", "?"),
                    },
                    project_name = os.getenv("LANGSMITH_PROJECT", "fm-trading-agency"),
                ) as root_run:
                    result = _original_invoke(state, *args, **kwargs)
                    verdict = result.get("final_verdict", {})
                    root_run.outputs = {
                        "verdict":        verdict.get("verdict", "?"),
                        "execution_score":verdict.get("execution_score", 0),
                        "regime":         verdict.get("market_regime", "?"),
                    }
                    return result

            compiled.invoke = traced_invoke
            log.info("LangSmith pipeline tracing ENABLED")
        except ImportError:
            pass  # langsmith not installed — skip silently

    return compiled