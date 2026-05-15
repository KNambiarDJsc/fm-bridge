"""
FM Trading Agency — Relative Strength Engine
==============================================
Answers the most important question every morning:
  "Which index gives the BEST setup today?"

From document 6, gap 6 — MISSING in prior roadmap:
  Index   Score
  BankNifty  82
  Pharma     74
  Nifty      61

Scoring factors (weighted):
  Trend alignment    0.25  — EMA stack + price vs SMA200
  OPR/PCR signal     0.20  — options market institutional sentiment
  Breadth strength   0.15  — sector breadth (how many stocks above MA)
  Volatility fit     0.15  — is vol compatible with strategy type?
  Momentum quality   0.15  — RSI sweet spot + ADX strength
  Event stress       0.10  — macro event penalty from EventIntelligence

Returns a ranked list with the best index highlighted.
The best index is what the copilot trades today.
If today's best is 15+ points above the trader's current index,
the system suggests switching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import IndicatorPack, OptionsChain, MacroContext, IndexScore

import logging
log = logging.getLogger("fm.quant.rel_strength")


# ════════════════════════════════════════════════════════════════
# INPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class IndexInputs:
    """All data needed to score one index."""
    name:    str
    ind:     Optional[IndicatorPack]  = None
    oc:      Optional[OptionsChain]   = None
    macro:   Optional[MacroContext]   = None
    event_stress: float               = 0.0   # 0-100, injected by EventIntelligence
    breadth_score: float              = 50.0  # % stocks above 20MA in the index


# ════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ════════════════════════════════════════════════════════════════

def _score_trend(ind: Optional[IndicatorPack]) -> float:
    """0–100. How strong and clear is the trend?"""
    if not ind:
        return 50.0
    score = 50.0

    if ind.ema_stack == "BULL":
        score += 25
    elif ind.ema_stack == "BEAR":
        score -= 25

    if ind.adx is not None:
        if ind.adx > 25:   score += 15
        elif ind.adx > 20: score += 8
        else:              score -= 10   # weak trend = low clarity

    if ind.supertrend_dir == "LONG":   score += 10
    elif ind.supertrend_dir == "SHORT":score -= 10

    return max(0, min(100, score))


def _score_options_flow(oc: Optional[OptionsChain]) -> float:
    """0–100. What is the institutional options market saying?"""
    if not oc:
        return 50.0
    score = 50.0

    if oc.pcr is not None:
        if oc.pcr > 1.3:   score += 20
        elif oc.pcr < 0.7: score -= 20
        elif oc.pcr > 1.0: score += 8

    if oc.opr_signal == "PUT_DOMINANT":    score += 15
    elif oc.opr_signal == "CALL_DOMINANT": score -= 15

    # Max Pain gravity — if price is far below Max Pain, gravity pulls up
    if oc.max_pain and oc.spot:
        if oc.spot < oc.max_pain - 100: score += 8    # bullish gravity
        elif oc.spot > oc.max_pain + 100: score -= 8  # bearish gravity

    return max(0, min(100, score))


def _score_volatility_fit(
    ind: Optional[IndicatorPack],
    oc:  Optional[OptionsChain],
    macro: Optional[MacroContext],
) -> float:
    """
    0–100. Is the current volatility profile compatible with trading?
    High VIX + high ATR = harder to trade (but not impossible if hedged).
    Low VIX + low ADX = range trade or hedge opportunity.
    """
    if not ind:
        return 50.0
    score = 50.0
    vix = (macro.india_vix if macro else None) or 15.0

    # Ideal VIX range: 13-18 (enough premium, not panic)
    if 13 <= vix <= 18:
        score += 15
    elif vix > 25:
        score -= 20   # too volatile, signals unreliable
    elif vix < 10:
        score -= 5    # too calm, very small moves

    if ind.atr_pct:
        if ind.atr_pct < 0.5:
            score -= 10   # almost no range
        elif ind.atr_pct > 2.0:
            score -= 10   # very wide — oversized stops required

    if ind.bb_width:
        if ind.bb_width < 1.0:
            score -= 5    # Bollinger squeeze — breakout pending but direction unclear

    return max(0, min(100, score))


def _score_momentum(ind: Optional[IndicatorPack]) -> float:
    """0–100. Is momentum in a tradeable zone?"""
    if not ind:
        return 50.0
    score = 50.0

    if ind.rsi is not None:
        if 50 <= ind.rsi <= 65:
            score += 20    # sweet spot
        elif ind.rsi > 70:
            score -= 10    # overbought
        elif ind.rsi < 30:
            score += 10    # oversold (potential bounce — still a trade)
        elif ind.rsi < 40:
            score -= 8     # weakening

    if ind.macd_dir == "BULL":  score += 10
    elif ind.macd_dir == "BEAR":score -= 10

    if ind.stoch_k and ind.stoch_d:
        if ind.stoch_k > ind.stoch_d and ind.stoch_k < 80:
            score += 8    # stochastic bullish cross, not overbought
        elif ind.stoch_k < ind.stoch_d and ind.stoch_k > 20:
            score -= 8

    return max(0, min(100, score))


def score_index(inputs: IndexInputs) -> IndexScore:
    """
    Compute the opportunity score for one index.
    Returns an IndexScore with all components.
    """
    ind    = inputs.ind
    oc     = inputs.oc
    macro  = inputs.macro

    trend      = _score_trend(ind)
    options    = _score_options_flow(oc)
    vol_fit    = _score_volatility_fit(ind, oc, macro)
    momentum   = _score_momentum(ind)
    breadth    = inputs.breadth_score
    event_pen  = 100 - inputs.event_stress   # invert: 0 stress = 100 score

    # Weighted composite (weights per spec §5.2 + document 6 gap 6)
    composite = (
        trend      * 0.25 +
        options    * 0.20 +
        breadth    * 0.15 +
        vol_fit    * 0.15 +
        momentum   * 0.15 +
        event_pen  * 0.10
    )
    score = int(round(composite))

    # Regime label
    regime = "SIDE"
    if (ind and ind.ema_stack == "BULL" and
        (ind.rsi is None or ind.rsi > 50)):
        regime = "BULL"
    elif (ind and ind.ema_stack == "BEAR" and
          (ind.rsi is None or ind.rsi < 50)):
        regime = "BEAR"

    price      = (ind.spot     if ind else 0.0) or 0.0
    change_pct = 0.0
    rsi        = ind.rsi        if ind else None
    atr_pct    = ind.atr_pct   if ind else None

    return IndexScore(
        name       = inputs.name,
        score      = score,
        regime     = regime,
        price      = price,
        change_pct = change_pct,
        rsi        = rsi,
        atr_pct    = atr_pct,
    )


# ════════════════════════════════════════════════════════════════
# RANKING ENGINE
# ════════════════════════════════════════════════════════════════

@dataclass
class RelativeStrengthReport:
    """Ranked opportunity list with switch recommendation."""
    ranked:       list[IndexScore]           # sorted by score desc
    best:         Optional[IndexScore]       = None
    current:      Optional[IndexScore]       = None  # trader's current index
    switch_to:    Optional[str]              = None  # name of better index if gap >= 15
    switch_reason:Optional[str]              = None
    summary:      str                        = ""

    def to_dict(self) -> dict:
        return {
            "ranked":        [s.model_dump() for s in self.ranked],
            "best":          self.best.model_dump() if self.best else None,
            "current":       self.current.model_dump() if self.current else None,
            "switch_to":     self.switch_to,
            "switch_reason": self.switch_reason,
            "summary":       self.summary,
        }


def rank_indices(
    all_inputs: list[IndexInputs],
    current_index: str = "NIFTY 50",
) -> RelativeStrengthReport:
    """
    Score all indices and return a ranked report.
    Answers: "Which index gives the best setup today?"
    """
    scores = []
    for inp in all_inputs:
        try:
            s = score_index(inp)
            scores.append(s)
        except Exception as e:
            log.error("Scoring error for %s: %s", inp.name, e)
            scores.append(IndexScore(name=inp.name, score=0, error=str(e)))

    valid   = [s for s in scores if not s.error]
    errored = [s for s in scores if s.error]
    ranked  = sorted(valid, key=lambda x: x.score, reverse=True) + errored

    best    = ranked[0] if ranked else None
    current = next((s for s in ranked if s.name == current_index), None)

    switch_to     = None
    switch_reason = None

    if best and current and best.name != current.name:
        gap = best.score - current.score
        if gap >= 15:
            switch_to     = best.name
            switch_reason = (
                f"{best.name} scores {best.score}/100 vs "
                f"{current.name}'s {current.score}/100 "
                f"(gap {gap} pts — above 15pt threshold)"
            )

    summary = (
        f"Best today: {best.name} ({best.score}/100, {best.regime})" if best
        else "No index data available."
    )
    if switch_to:
        summary += f" — consider switching from {current_index}."

    return RelativeStrengthReport(
        ranked        = ranked,
        best          = best,
        current       = current,
        switch_to     = switch_to,
        switch_reason = switch_reason,
        summary       = summary,
    )