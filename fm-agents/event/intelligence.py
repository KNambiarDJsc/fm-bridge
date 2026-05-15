"""
FM Trading Agency — Event Intelligence Engine
===============================================
Gap 5 from document 6.

Architecture (as specified):
  News headlines (fetched by news/fetcher.py)
        ↓
  Event Classifier (LLM — good at this)
    → BANKING_STRESS / VOLATILITY_EXPANSION / MACRO_RISK / EARNINGS_SURPRISE / NONE
        ↓
  Impact Engine (deterministic — NOT LLM)
    if BANKING_STRESS: banknifty_event_stress += 20
    if ICICI/HDFC down >3%: banknifty_event_stress += 15
        ↓
  Context Scorer → { market_stress: 72, banking_risk: 81, ... }
        ↓
  AI Narrative (LLM — one sentence only)
    → "Banking pressure increasing due to ICICI weakness."

The LLM classifies events and writes the narrative.
The NUMBERS come from the deterministic impact engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import logging
log = logging.getLogger("fm.agents.event")


# ════════════════════════════════════════════════════════════════
# EVENT TYPES
# ════════════════════════════════════════════════════════════════

EVENT_TYPES = {
    "BANKING_STRESS":       "Banking sector under pressure",
    "VOLATILITY_EXPANSION": "Market volatility expanding",
    "MACRO_RISK":           "Macro-level risk event",
    "EARNINGS_SURPRISE":    "Earnings miss or beat",
    "RBI_ACTION":           "RBI policy action or statement",
    "GLOBAL_RISK_OFF":      "Global risk-off sentiment",
    "SECTOR_ROTATION":      "Sector rotation in progress",
    "OIL_SHOCK":            "Oil price shock",
    "NONE":                 "No significant event",
}

# Keyword → impact mapping (deterministic)
_KEYWORD_IMPACTS: list[tuple[list[str], str, float]] = [
    # (keywords, index_affected, stress_delta)
    (["ICICI", "HDFC", "SBI", "Axis Bank", "Kotak"],          "BANK NIFTY",   15.0),
    (["banking sector", "bank stocks", "NPA", "NPL"],          "BANK NIFTY",   12.0),
    (["RBI rate hike", "rate increase", "hawkish RBI"],        "NIFTY 50",     10.0),
    (["RBI cut", "rate cut", "dovish", "accommodative"],       "NIFTY 50",     -8.0),  # negative = relief
    (["Infosys", "TCS", "Wipro", "HCL Tech"],                  "NIFTY IT",     15.0),
    (["IT sector", "tech sector"],                             "NIFTY IT",     10.0),
    (["VIX spike", "circuit breaker", "crash", "selloff"],     "NIFTY 50",     25.0),
    (["FII selling", "FII outflow", "foreign selling"],        "NIFTY 50",     12.0),
    (["FII buying", "FII inflow", "foreign buying"],           "NIFTY 50",     -8.0),
    (["oil surge", "crude spike", "$100", "$110", "$120"],     "NIFTY 50",     15.0),
    (["oil falls", "crude drops", "oil cheap"],                "NIFTY 50",     -5.0),
    (["GDP data", "inflation", "CPI", "IIP"],                  "NIFTY 50",      8.0),
    (["Fed rate", "US Fed", "Powell"],                         "NIFTY 50",      8.0),
    (["pharma", "drug", "FDA", "approval"],                    "NIFTY PHARMA", 12.0),
    (["auto", "EV", "vehicle sales"],                          "NIFTY AUTO",   10.0),
]


# ════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class EventContext:
    """Event intelligence output — passed to all agents."""
    # Stress scores per index (0–100; higher = more stressed)
    index_stress: dict[str, float] = field(default_factory=dict)

    # Portfolio-level stress
    market_stress:   float = 0.0
    banking_risk:    float = 0.0
    tech_risk:       float = 0.0
    macro_risk:      float = 0.0
    volatility_risk: float = 0.0

    # Classified events
    detected_events: list[str]  = field(default_factory=list)
    event_severity:  str        = "LOW"   # LOW | MEDIUM | HIGH | CRITICAL

    # Headlines that triggered the events
    triggering_headlines: list[str] = field(default_factory=list)

    # AI narrative (one sentence — written by LLM)
    narrative: str = "No significant market events detected."

    def get_stress(self, index: str) -> float:
        """Get event stress score for a specific index (0=none, 100=extreme)."""
        return min(100.0, self.index_stress.get(index, self.market_stress * 0.5))

    def to_dict(self) -> dict:
        return {
            "index_stress":        self.index_stress,
            "market_stress":       round(self.market_stress, 1),
            "banking_risk":        round(self.banking_risk, 1),
            "tech_risk":           round(self.tech_risk, 1),
            "macro_risk":          round(self.macro_risk, 1),
            "volatility_risk":     round(self.volatility_risk, 1),
            "detected_events":     self.detected_events,
            "event_severity":      self.event_severity,
            "triggering_headlines":self.triggering_headlines,
            "narrative":           self.narrative,
        }


# ════════════════════════════════════════════════════════════════
# IMPACT ENGINE (deterministic — NOT LLM)
# ════════════════════════════════════════════════════════════════

def _compute_impact(headlines: list[str]) -> EventContext:
    """
    Rule-based impact engine.
    Scans headlines for keywords, applies stress deltas.
    Returns EventContext with numeric stress scores.
    """
    ctx = EventContext()
    ctx.index_stress = {
        "NIFTY 50": 0.0, "BANK NIFTY": 0.0,
        "NIFTY IT": 0.0, "NIFTY PHARMA": 0.0,
        "NIFTY AUTO": 0.0, "NIFTY METAL": 0.0,
    }

    combined = " ".join(headlines).lower()
    triggered: list[str] = []

    for keywords, index, delta in _KEYWORD_IMPACTS:
        for kw in keywords:
            if kw.lower() in combined:
                ctx.index_stress[index] = ctx.index_stress.get(index, 0) + delta
                triggered.append(kw)
                break   # one keyword per rule is enough

    # Classify events from keywords
    if any(k in combined for k in ["bank", "icici", "hdfc", "sbi", "npa"]):
        ctx.detected_events.append("BANKING_STRESS")
        ctx.banking_risk = ctx.index_stress.get("BANK NIFTY", 0)

    if any(k in combined for k in ["vix", "circuit", "crash", "selloff", "panic"]):
        ctx.detected_events.append("VOLATILITY_EXPANSION")
        ctx.volatility_risk = 30.0

    if any(k in combined for k in ["rbi", "fed", "rate", "cpi", "gdp", "oil"]):
        ctx.detected_events.append("MACRO_RISK")
        ctx.macro_risk = 20.0

    if any(k in combined for k in ["infosys", "tcs", "wipro", "it sector", "tech"]):
        ctx.detected_events.append("SECTOR_ROTATION")
        ctx.tech_risk = ctx.index_stress.get("NIFTY IT", 0)

    # Market-level stress = max of all index stresses, capped at 100
    all_stresses = list(ctx.index_stress.values()) + [ctx.volatility_risk, ctx.macro_risk]
    ctx.market_stress = min(100.0, max(all_stresses)) if all_stresses else 0.0

    # Cap individual stresses at 100
    ctx.index_stress = {k: min(100.0, v) for k, v in ctx.index_stress.items()}

    # Severity
    ms = ctx.market_stress
    if ms >= 60:    ctx.event_severity = "HIGH"
    elif ms >= 35:  ctx.event_severity = "MEDIUM"
    elif ms >= 15:  ctx.event_severity = "LOW"
    else:           ctx.event_severity = "NONE"

    ctx.triggering_headlines = [h for h in headlines if any(
        kw.lower() in h.lower() for kw in triggered
    )][:3]

    if not ctx.detected_events:
        ctx.detected_events = ["NONE"]

    return ctx


# ════════════════════════════════════════════════════════════════
# AI NARRATIVE (LLM — one sentence only)
# ════════════════════════════════════════════════════════════════

def _generate_narrative(ctx: EventContext, llm) -> str:
    """
    Ask the LLM to write ONE sentence explaining the event context.
    The LLM explains — it does NOT compute the numbers.
    """
    if ctx.event_severity == "NONE" or not ctx.detected_events or ctx.detected_events == ["NONE"]:
        return "No significant market events detected — standard technical signals apply."

    events_str  = ", ".join(ctx.detected_events)
    stress_str  = ", ".join([
        f"{k}: {v:.0f}/100"
        for k, v in ctx.index_stress.items()
        if v > 10
    ])
    headlines_str = " | ".join(ctx.triggering_headlines[:3])

    prompt = (
        f"You are a market analyst. In EXACTLY ONE sentence (max 25 words), "
        f"explain the current market event context.\n\n"
        f"Events detected: {events_str}\n"
        f"Stress levels: {stress_str}\n"
        f"Headlines: {headlines_str}\n\n"
        f"Write one crisp sentence that a trader can read in 3 seconds. "
        f"No fluff. No disclaimer. Just the key insight."
    )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        # Keep only first sentence
        sentence = text.split(".")[0].strip() + "."
        return sentence if len(sentence) > 10 else ctx.narrative
    except Exception as e:
        log.warning("Event narrative LLM failed: %s", e)
        # Fallback: build from data
        if ctx.banking_risk > 30:
            return f"Banking sector under pressure — {ctx.event_severity.lower()} market stress detected."
        if ctx.macro_risk > 20:
            return f"Macro risk elevated — monitor {', '.join(ctx.detected_events[:2])}."
        return "Market events detected — elevated caution advised."


# ════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════

def analyse_events(headlines: list[str], llm=None) -> EventContext:
    """
    Full event intelligence pipeline.
    1. Impact engine (deterministic) — computes stress scores
    2. Narrative (LLM) — writes one-sentence explanation
    """
    if not headlines:
        return EventContext(narrative="No headlines available for event analysis.")

    ctx = _compute_impact(headlines)

    if llm is not None:
        ctx.narrative = _generate_narrative(ctx, llm)

    log.info(
        "Event context: severity=%s, market_stress=%.0f, events=%s",
        ctx.event_severity, ctx.market_stress, ctx.detected_events,
    )
    return ctx
