"""
FM Trading Agency — LLM Provider Factory
==========================================
Returns the correct LangChain LLM based on LLM_PROVIDER env var.

Two tiers:
  DEEP  → complex reasoning, structured JSON, longer context
          Used by: L7 Strategy, L9 Sovereign
  QUICK → fast structured output, JSON schema enforcement
          Used by: L1-L6 analysts

Provider switching is zero-code — change LLM_PROVIDER in .env.
All providers return a LangChain-compatible chat model.
"""

from __future__ import annotations

import os
import logging
from typing import Literal

log = logging.getLogger("fm.agents.llm")


def get_llm(tier: Literal["deep", "quick", "lite"] = "quick"):
    """
    Return an LLM configured for the requested tier.

    tier="deep"  → Gemini 2.5 Pro / Claude Sonnet / GPT-4o
    tier="quick" → Gemini 2.5 Flash / Claude Haiku / GPT-4o-mini
    tier="lite"  → Gemini 2.5 Flash-Lite (ultra-fast, L1-L3 pass-through)
    """
    from config import get_settings
    s = get_settings()
    provider = s.llm_provider.lower()

    # ── Enable LangSmith tracing ──────────────────────────────────
    if s.langsmith_tracing and s.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"]  = "true"
        os.environ["LANGCHAIN_API_KEY"]      = s.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"]      = s.langsmith_project

    # ── GEMINI (default) ──────────────────────────────────────────
    if provider == "gemini":
        return _get_gemini(s, tier)

    # ── CLAUDE ────────────────────────────────────────────────────
    elif provider == "claude":
        return _get_claude(s, tier)

    # ── OPENAI ────────────────────────────────────────────────────
    elif provider == "openai":
        return _get_openai(s, tier)

    else:
        log.warning("Unknown LLM_PROVIDER '%s' — defaulting to Gemini", provider)
        return _get_gemini(s, tier)


def _get_gemini(s, tier: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not s.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY not set in .env. "
            "Get one at https://aistudio.google.com/apikey"
        )

    model_map = {
        "deep":  s.gemini_deep_model,
        "quick": s.gemini_quick_model,
        "lite":  s.gemini_lite_model,
    }
    model = model_map.get(tier, s.gemini_quick_model)

    log.debug("Gemini %s → %s", tier, model)
    return ChatGoogleGenerativeAI(
        model               = model,
        google_api_key      = s.google_api_key,
        temperature         = 0.1,          # low temp = consistent JSON
        max_output_tokens   = 2048,
        convert_system_message_to_human = True,  # Gemini quirk
    )


def _get_claude(s, tier: str):
    from langchain_anthropic import ChatAnthropic

    if not s.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    model_map = {
        "deep":  s.claude_deep_model,
        "quick": s.claude_quick_model,
        "lite":  s.claude_quick_model,   # no lite tier for Claude
    }
    model = model_map.get(tier, s.claude_quick_model)

    log.debug("Claude %s → %s", tier, model)
    return ChatAnthropic(
        model               = model,
        anthropic_api_key   = s.anthropic_api_key,
        temperature         = 0.1,
        max_tokens          = 2048,
    )


def _get_openai(s, tier: str):
    from langchain_openai import ChatOpenAI

    if not s.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in .env")

    model_map = {
        "deep":  s.openai_deep_model,
        "quick": s.openai_quick_model,
        "lite":  s.openai_quick_model,
    }
    model = model_map.get(tier, s.openai_quick_model)

    log.debug("OpenAI %s → %s", tier, model)
    return ChatOpenAI(
        model               = model,
        openai_api_key      = s.openai_api_key,
        temperature         = 0.1,
        max_tokens          = 2048,
    )
