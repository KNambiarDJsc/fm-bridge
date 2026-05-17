"""
FM Trading Agency — News & Intelligence Fetcher v2
====================================================
Confirmed-working sources (tested 2026-05-18):

  TIER 1 — Tavily Search API (optional, best quality)
    Set TAVILY_API_KEY in fm-agents/.env for AI-ranked real-time news.
    Free tier: 1,000 credits/month. Falls back silently if not set.

  TIER 2 — Free, no API key, confirmed working right now
    ✓ Google News RSS    — 100 items per query, real-time, India-focused
    ✓ Yahoo Finance      — index/stock specific news via yfinance
    ✓ Investing.com RSS  — 10 India market items
    ✓ SeekingAlpha RSS   — India ETF news (INDY)
    ✓ feedparser         — for any feed with encoding issues

  DEAD (403 as of 2026-05-18 — do not use):
    ✗ Moneycontrol RSS   — all feeds return 403
    ✗ Economic Times RSS — 403
    ✗ Business Standard  — 403
    ✗ LiveMint           — 403
    ✗ Reuters India feed — SSL/connection error
    ✗ CNBC TV18          — 403
    ✗ RBI RSS            — 200 but empty (0 items via feedparser)

After-hours value: All these sources update continuously 24/7.
Google News has global pre-market context even at 7 AM IST.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from typing import Optional

import requests
import feedparser

import logging
log = logging.getLogger("fm.agents.news")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}
_TIMEOUT = 8


# ═══════════════════════════════════════════════════════════════
# SOURCE 1 — Tavily Search (best quality, optional)
# ═══════════════════════════════════════════════════════════════

def fetch_tavily(query: str, max_items: int = 5) -> list[str]:
    """
    Tavily AI search — ranked real-time web results.
    Only runs if TAVILY_API_KEY is set. Silent fallback if not.
    Free tier: 1,000 credits/month (1 credit per call).
    Sign up: app.tavily.com
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key":        api_key,
                "query":          query,
                "topic":          "news",
                "time_range":     "day",
                "max_results":    max_items,
                "search_depth":   "basic",
                "include_answer": False,
            },
            timeout=10,
        )
        if r.status_code != 200:
            log.debug("Tavily HTTP %d for '%s'", r.status_code, query)
            return []
        results = r.json().get("results", [])
        headlines = [res["title"] for res in results if res.get("title")]
        log.debug("Tavily: %d results for '%s'", len(headlines), query)
        return headlines[:max_items]
    except Exception as e:
        log.debug("Tavily failed: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# SOURCE 2 — Google News RSS (confirmed ✓, 100 items/query)
# ═══════════════════════════════════════════════════════════════

def fetch_google_news(query: str, max_items: int = 5) -> list[str]:
    """
    Google News RSS — best free source, 100 results per query.
    Real-time, India-focused (hl=en-IN&gl=IN).
    Works 24/7 including after market hours.
    """
    try:
        encoded = quote_plus(query)
        url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        )
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if not r.ok:
            return []
        root = ET.fromstring(r.content)
        headlines = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "")
            # Google News includes source after " - " — strip it
            title = title.split(" - ")[0].strip()
            if title and len(title) > 12:
                headlines.append(title)
        log.debug("Google News '%s': %d headlines", query, len(headlines))
        return headlines
    except Exception as e:
        log.warning("Google News failed for '%s': %s", query, e)
        return []


# ═══════════════════════════════════════════════════════════════
# SOURCE 3 — Yahoo Finance news (confirmed ✓)
# ═══════════════════════════════════════════════════════════════

def fetch_yahoo_news(symbol: str = "^NSEI", max_items: int = 4) -> list[str]:
    """Index or stock-specific news from Yahoo Finance via yfinance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        news = ticker.get_news(count=max_items)
        headlines = []
        for item in news:
            title = (
                item.get("content", {}).get("title") or
                item.get("title", "")
            )
            if title:
                headlines.append(title.strip())
        log.debug("Yahoo Finance %s: %d headlines", symbol, len(headlines))
        return headlines[:max_items]
    except Exception as e:
        log.warning("Yahoo Finance news failed for %s: %s", symbol, e)
        return []


# ═══════════════════════════════════════════════════════════════
# SOURCE 4 — Investing.com RSS (confirmed ✓, 10 items)
# ═══════════════════════════════════════════════════════════════

def fetch_investing_rss(max_items: int = 5) -> list[str]:
    """
    Investing.com India RSS — 10 quality financial news items.
    Confirmed working. Uses feedparser for encoding robustness.
    """
    try:
        d = feedparser.parse(
            "https://in.investing.com/rss/news.rss",
            request_headers=_HEADERS,
        )
        headlines = []
        for entry in d.entries[:max_items]:
            title = entry.get("title", "").strip()
            if title and len(title) > 12:
                headlines.append(title)
        log.debug("Investing.com: %d headlines", len(headlines))
        return headlines
    except Exception as e:
        log.warning("Investing.com RSS failed: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# SOURCE 5 — SeekingAlpha India (confirmed ✓, 30 items)
# ═══════════════════════════════════════════════════════════════

def fetch_seekingalpha_india(max_items: int = 3) -> list[str]:
    """
    SeekingAlpha INDY (India ETF) RSS — 30 items covering
    India macro, policy, earnings. Good after-hours context.
    """
    try:
        d = feedparser.parse(
            "https://seekingalpha.com/api/sa/combined/INDY.xml",
            request_headers=_HEADERS,
        )
        headlines = []
        for entry in d.entries[:max_items]:
            title = entry.get("title", "").strip()
            if title and len(title) > 12:
                headlines.append(f"[SA] {title}")
        log.debug("SeekingAlpha: %d headlines", len(headlines))
        return headlines
    except Exception as e:
        log.debug("SeekingAlpha RSS failed: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

# Index → Yahoo Finance ticker mapping
_YF_MAP = {
    "NIFTY 50":     "^NSEI",
    "BANK NIFTY":   "^NSEBANK",
    "NIFTY IT":     "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO":   "^CNXAUTO",
}

# Google News query set — covers every angle the event engine needs
_GOOGLE_QUERIES = [
    "nifty sensex india stock market today",           # broad market
    "bank nifty india banking stocks outlook",         # banking
    "FII DII india foreign institutional investors",   # flows
    "RBI monetary policy india interest rates",        # RBI
    "global markets us dow nasdaq impact india",       # global cues
    "india vix volatility options expiry NSE",         # volatility
    "india inflation oil rupee macro economy",         # macro
]


def fetch_all_headlines(symbol: str = "NIFTY 50") -> list[str]:
    """
    Fetch headlines from all sources. Deduped, max 20 returned.

    Priority order (highest quality first):
      1. Tavily     — AI-ranked, real-time  (needs TAVILY_API_KEY)
      2. Google News — 7 targeted queries, 3 headlines each = up to 21
      3. Yahoo Finance — symbol-specific news
      4. Investing.com — 5 quality items
      5. SeekingAlpha  — India macro context

    Works 24/7. After market hours, Google News + Investing.com +
    SeekingAlpha provide next-day context and global overnight news.
    """
    headlines: list[str] = []
    seen: set[str] = set()

    def _add(items: list[str]) -> None:
        for h in items:
            h = h.strip()
            key = h.lower()[:80]   # normalise for dedup
            if h and key not in seen and len(h) > 12:
                seen.add(key)
                headlines.append(h)

    yf_ticker = _YF_MAP.get(symbol, "^NSEI")

    # ── Tier 1: Tavily (if key is set) ──────────────────────────
    _add(fetch_tavily(
        f"NSE nifty {symbol} india stock market analysis today",
        max_items=6,
    ))

    # ── Tier 2: Google News — multiple targeted queries ──────────
    for query in _GOOGLE_QUERIES:
        _add(fetch_google_news(query, max_items=3))

    # ── Tier 3: Yahoo Finance — symbol-specific ──────────────────
    _add(fetch_yahoo_news(yf_ticker, max_items=4))

    # ── Tier 4: Investing.com ────────────────────────────────────
    _add(fetch_investing_rss(max_items=5))

    # ── Tier 5: SeekingAlpha India ───────────────────────────────
    _add(fetch_seekingalpha_india(max_items=3))

    result = headlines[:20]
    log.info(
        "Headlines: %d unique | symbol=%s | tavily=%s",
        len(result), symbol,
        "yes" if os.getenv("TAVILY_API_KEY") else "no",
    )
    return result
