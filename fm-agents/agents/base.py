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
    """Format MacroContext dict into compact string."""
    if not mc:
        return "No macro data available."
    return (
        f"Brent Oil: ${mc.get('brent_oil', '?')} | "
        f"OilShock: {mc.get('oil_shock_active', False)} | "
        f"FII: ₹{mc.get('fii_net', '?')}Cr | "
        f"DII: ₹{mc.get('dii_net', '?')}Cr | "
        f"DomFloor: {mc.get('domestic_floor_active', False)} | "
        f"VIX: {mc.get('india_vix', '?')} ({mc.get('vix_regime', '?')}) | "
        f"RiskCtx: {mc.get('risk_context', '?')} | "
        f"RBI: {mc.get('rbi_stance', '?')}"
    )
