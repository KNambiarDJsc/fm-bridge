"""
FM Trading Agency — Agent Base
================================
Shared infrastructure for all 9 agents.

Every agent:
  1. Gets context (bridge data + quant numbers)
  2. Builds a structured prompt with RETURN ONLY JSON instruction
  3. Calls the LLM
  4. Parses + validates the JSON response against its Pydantic schema
  5. Returns a typed result (Zero-Placeholder Policy enforced)

This base keeps all 9 agent files thin and focused on their
domain logic, not on boilerplate.
"""

from __future__ import annotations

import json
import os
import re
import logging
from typing import TypeVar, Type

from pydantic import BaseModel

log = logging.getLogger("fm.agents.base")

T = TypeVar("T", bound=BaseModel)

# ── LangSmith tracing (optional — only active when LANGSMITH_API_KEY is set) ──
# Uses @traceable decorator from langsmith SDK.
# Per docs: "Requires LANGSMITH_TRACING_V2=true in environment"
# If langsmith is not installed or key not set, tracing is silently skipped.
_langsmith_enabled = bool(os.getenv("LANGSMITH_API_KEY") and os.getenv("LANGSMITH_TRACING_V2") == "true")

try:
    if _langsmith_enabled:
        from langsmith import traceable as _traceable
        log.info("LangSmith tracing ENABLED (project: %s)", os.getenv("LANGSMITH_PROJECT", "fm-trading-agency"))
    else:
        # No-op decorator when LangSmith is not configured
        def _traceable(*args, **kwargs):
            def decorator(fn):
                return fn
            # Handle both @_traceable and @_traceable(name=...) forms
            if len(args) == 1 and callable(args[0]):
                return args[0]
            return decorator
except ImportError:
    log.info("langsmith not installed — tracing disabled. pip install langsmith to enable.")
    def _traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


def _extract_json(text: str) -> str:
    """
    Extract JSON from LLM response.
    Handles: raw JSON, ```json ... ```, ``` ... ```, mixed prose + JSON.
    """
    # Remove markdown code blocks
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)

    # Find first { and last } — extract the object
    start = text.find("{")
    end   = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text.strip()


@_traceable(name="call_agent", run_type="llm", metadata={"service": "fm-agents"})
def call_agent(
    llm,
    system_prompt: str,
    user_prompt:   str,
    schema:        Type[T],
    agent_name:    str = "agent",
    fallback:      T | None = None,
) -> T:
    """
    Call the LLM, parse JSON, validate against schema.
    Returns schema instance.  Falls back to defaults on any error.
    
    Decorated with @traceable so every LLM call appears in LangSmith
    with inputs (prompts), outputs (parsed JSON), latency, and errors.
    Set LANGSMITH_API_KEY + LANGSMITH_TRACING_V2=true in .env to activate.
    """
    full_prompt = (
        f"{system_prompt}\n\n"
        f"CRITICAL: Return ONLY valid JSON matching the schema. "
        f"No prose, no markdown, no explanation. Just the JSON object.\n\n"
        f"{user_prompt}"
    )

    try:
        response = llm.invoke(full_prompt)
        text = response.content if hasattr(response, "content") else str(response)
        json_str = _extract_json(text)
        data = json.loads(json_str)
        result = schema(**data)
        conf = data.get("confidence", data.get("execution_score", "?"))
        log.debug("%s: parsed OK (conf=%s)", agent_name, conf)
        return result

    except json.JSONDecodeError as e:
        log.warning("%s: JSON parse error: %s — using defaults", agent_name, e)
        return fallback or schema()
    except Exception as e:
        log.warning("%s: error: %s — using defaults", agent_name, e)
        return fallback or schema()


def fmt_ind(ind: dict) -> str:
    """Format IndicatorPack dict into a compact string for prompts."""
    if not ind:
        return "No indicator data available."
    return (
        f"Spot: {ind.get('spot', '?')} | "
        f"EMA Stack: {ind.get('ema_stack', '?')} | "
        f"RSI: {ind.get('rsi', '?')} ({ind.get('rsi_zone', '?')}) | "
        f"MACD: {ind.get('macd_dir', '?')} | "
        f"ADX: {ind.get('adx', '?')} ({ind.get('adx_strength', '?')}) | "
        f"Supertrend: {ind.get('supertrend_dir', '?')} | "
        f"VWAP: {ind.get('vwap', '?')} | "
        f"ATR%: {ind.get('atr_pct', '?')} | "
        f"BB Width: {ind.get('bb_width', '?')}"
    )


def fmt_oc(oc: dict) -> str:
    """Format OptionsChain dict into compact string."""
    if not oc:
        return "No options data available."
    return (
        f"PCR: {oc.get('pcr', '?')} | "
        f"MaxPain: {oc.get('max_pain', '?')} | "
        f"CallWall: {oc.get('call_wall', '?')} | "
        f"PutWall: {oc.get('put_wall', '?')} | "
        f"OPR: {oc.get('opr', '?')} ({oc.get('opr_signal', '?')}) | "
        f"ATM IV: {oc.get('atm_iv', '?')}% | "
        f"DTE: {oc.get('dte', '?')} | "
        f"Expiry: {oc.get('is_expiry_day', False)}"
    )


def fmt_macro(mc: dict) -> str:
    """Format MacroContext dict into compact string for agent prompts."""
    if not mc:
        return "No macro data available."

    # Core domestic macro
    lines = [
        f"Brent: ${mc.get('brent_oil','?')} | OilShock: {mc.get('oil_shock_active',False)} | "
        f"FII: ₹{mc.get('fii_net','?')}Cr | DII: ₹{mc.get('dii_net','?')}Cr | "
        f"VIX: {mc.get('india_vix','?')} ({mc.get('vix_regime','?')}) | "
        f"RBI: {mc.get('rbi_stance','?')} | Risk: {mc.get('risk_context','?')}",
    ]

    # NEW: Global cues (if available)
    usd_inr  = mc.get("inr_usd") or mc.get("usd_inr")
    gift     = mc.get("gift_nifty")
    gift_prem= mc.get("gift_premium")
    dow_chg  = mc.get("dow_change_pct")
    nq_chg   = mc.get("nasdaq_change_pct")
    global_r = mc.get("global_risk", "")

    if usd_inr or gift or dow_chg is not None:
        parts = []
        if usd_inr:    parts.append(f"USD/INR: {usd_inr:.2f}{'⚠' if usd_inr > 84 else ''}")
        if gift:       parts.append(f"GIFT Nifty: {gift:.0f} ({'+' if (gift_prem or 0)>=0 else ''}{gift_prem:.0f}pts)")
        if dow_chg is not None: parts.append(f"Dow: {dow_chg:+.1f}%")
        if nq_chg is not None:  parts.append(f"Nasdaq: {nq_chg:+.1f}%")
        if global_r:   parts.append(f"GlobalRisk: {global_r}")
        lines.append("GLOBAL: " + " | ".join(parts))

    # RBI latest news
    rbi_hl = mc.get("rbi_latest_headline")
    if rbi_hl:
        lines.append(f"RBI Latest: {rbi_hl[:80]}")

    # Upcoming events
    events = mc.get("events_next_7_days", [])
    if events:
        ev_str = " | ".join(f"{e['event']} ({e['days_away']}d)" for e in events[:3])
        lines.append(f"EVENTS: {ev_str}")

    return "\n".join(lines)


def fmt_oi_change(ci: dict) -> str:
    """Format OI change analysis for agent prompts."""
    if not ci:
        return "No OI change data."
    oi_chg = ci.get("oi_change", {})
    if not oi_chg:
        return "OI change: not available."
    return (
        f"OI Pattern: {oi_chg.get('pattern','?')} ({oi_chg.get('dominant_side','?')}) | "
        f"CE Added: {oi_chg.get('ce_oi_added',0):,} | PE Added: {oi_chg.get('pe_oi_added',0):,} | "
        f"{oi_chg.get('narrative','')}"
    )
