"""
FM Trading Agency — Multi-Index Service
==========================================
Scores all 10 NSE indices and returns ranked opportunity data.
Powers the Index Opportunity Heatmap on the frontend.

Uses a ThreadPoolExecutor (like OpenAlgo's broker infra pattern)
to fetch + score all indices in parallel — ~2s for 10 indices.

Scoring formula (per spec §5.2):
  techMomentum    × 0.25
  regimeClarity   × 0.20
  relativeStrength× 0.20
  fundValuation   × 0.15  (placeholder — requires P/E data)
  optionsActivity × 0.10  (from OPR/PCR if available)
  liquidity       × 0.10  (inverse ATR%)
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd

from config import INSTRUMENT_MAP, get_settings
from models import IndexScore, MultiIndexHeatmap
from services.indicators import compute_indicators, _ema
from services.options_chain import fetch_options_chain

import logging
log = logging.getLogger("fm.multi_index")

# ── Cache ─────────────────────────────────────────────────────────
_cache: Optional[MultiIndexHeatmap] = None
_cache_ts: float = 0

# Shared kite instance (set by app.py)
_kite = None

def set_kite(k) -> None:
    global _kite
    _kite = k


# ─────────────────────────────────────────────────────────────────
# SCORE COMPUTATION
# ─────────────────────────────────────────────────────────────────

def _score_one(name: str) -> IndexScore:
    """Fetch 90-day daily bars and compute opportunity score for one index."""
    if not _kite:
        return IndexScore(name=name, score=0, error="Bridge not connected")

    try:
        from datetime import datetime, timedelta
        token = INSTRUMENT_MAP.get(name, 256265)
        to_dt = datetime.now()
        fr_dt = to_dt - timedelta(days=120)  # 120 days for 200+ bars
        data = _kite.historical_data(
            instrument_token = token,
            from_date        = fr_dt.strftime("%Y-%m-%d"),
            to_date          = to_dt.strftime("%Y-%m-%d"),
            interval         = "day",
            continuous       = False,
            oi               = False,
        )
        if len(data) < 30:
            return IndexScore(name=name, score=0, error="Insufficient bars")

        df = pd.DataFrame(data)[["open", "high", "low", "close", "volume"]]
        closes = df["close"].tolist()
        last   = closes[-1]
        prev   = closes[-2] if len(closes) >= 2 else last
        change = round((last / prev - 1) * 100, 2)

        # ── Indicators (fast path — no pandas-ta for speed) ───────
        ind = compute_indicators(df, name, "day")

        # ── Score components ──────────────────────────────────────
        # 1. Tech Momentum (0-100)
        tech_score = 50
        if ind.ema20 and ind.ema50:
            if last > ind.ema20: tech_score += 15
            else:                tech_score -= 15
            if ind.ema20 > ind.ema50: tech_score += 15
            else:                     tech_score -= 15
        tech_score = max(0, min(100, tech_score))

        # 2. Regime Clarity (0-100) — how far from EMA20
        regime_clarity = 50
        if ind.ema20:
            dist_pct = abs(last / ind.ema20 - 1) * 100
            regime_clarity = min(100, 50 + dist_pct * 4)

        # 3. Relative Strength (0-100) — 30-day return normalised
        r30 = 0.0
        if len(closes) >= 30:
            r30 = round((last / closes[-30] - 1) * 100, 1)
        rel_strength = max(0, min(100, 50 + r30 * 5))

        # 4. Fundamental Valuation (placeholder — P/E data in Phase 5)
        fund_val = 50

        # 5. Options Activity (from OPR/PCR if available for this index)
        opts_activity = 50
        try:
            oc = fetch_options_chain(name)
            if oc.pcr is not None:
                if oc.pcr > 1.3:    opts_activity = 70  # bullish PCR
                elif oc.pcr < 0.7:  opts_activity = 30  # bearish PCR
            if oc.opr_signal == "PUT_DOMINANT":  opts_activity = min(100, opts_activity + 15)
            elif oc.opr_signal == "CALL_DOMINANT": opts_activity = max(0, opts_activity - 15)
        except Exception:
            pass   # options chain unavailable for this index — use neutral

        # 6. Liquidity (0-100) — inverse ATR%
        liquidity = 50
        if ind.atr_pct:
            liquidity = max(0, min(100, 100 - ind.atr_pct * 15))

        # ── Weighted composite ────────────────────────────────────
        score = round(
            tech_score    * 0.25 +
            regime_clarity* 0.20 +
            rel_strength  * 0.20 +
            fund_val      * 0.15 +
            opts_activity * 0.10 +
            liquidity     * 0.10
        )

        # ── Regime label ──────────────────────────────────────────
        regime = "SIDE"
        if (ind.ema20 and ind.ema50 and
            last > ind.ema20 and ind.ema20 > ind.ema50 and
            (ind.rsi is None or ind.rsi > 50)):
            regime = "BULL"
        elif (ind.ema20 and ind.ema50 and
              last < ind.ema20 and ind.ema20 < ind.ema50 and
              (ind.rsi is None or ind.rsi < 50)):
            regime = "BEAR"

        return IndexScore(
            name              = name,
            score             = int(score),
            regime            = regime,
            price             = last,
            change_pct        = change,
            rsi               = ind.rsi,
            atr_pct           = ind.atr_pct,
            r30               = r30,
            tech_momentum     = round(tech_score, 1),
            regime_clarity    = round(regime_clarity, 1),
            relative_strength = round(rel_strength, 1),
            options_activity  = round(opts_activity, 1),
        )

    except Exception as e:
        log.error("Score error for %s: %s", name, e)
        return IndexScore(name=name, score=0, error=str(e))


# ─────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────

def get_multi_index_heatmap(force: bool = False) -> MultiIndexHeatmap:
    """
    Score all indices in parallel and return ranked heatmap.
    Cached for 5 minutes.  force=True bypasses cache.
    """
    global _cache, _cache_ts
    ttl = 300  # 5 minutes

    if _cache and not force and (time.time() - _cache_ts < ttl):
        return _cache

    log.info("Scoring %d indices in parallel ...", len(INSTRUMENT_MAP))
    names = list(INSTRUMENT_MAP.keys())
    scores: list[IndexScore] = []

    # Parallel fetch + score (OpenAlgo-style thread pool)
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_score_one, name): name for name in names}
        for fut in as_completed(futures):
            scores.append(fut.result())

    # Sort by score descending
    valid = sorted([s for s in scores if not s.error], key=lambda x: x.score, reverse=True)
    errored = [s for s in scores if s.error]
    all_scores = valid + errored

    best = valid[0] if valid else None
    result = MultiIndexHeatmap(indices=all_scores, best=best)

    _cache    = result
    _cache_ts = time.time()
    log.info("Heatmap ready — best: %s (%d/100)", best.name if best else "N/A", best.score if best else 0)
    return result