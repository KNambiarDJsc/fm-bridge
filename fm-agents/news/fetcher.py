"""
FM Trading Agency — News Fetcher
===================================
Fetches REAL headlines from three free sources.
Anti-hallucination rule: L5 agent receives ACTUAL headlines,
not LLM-invented ones.

Sources:
  1. Yahoo Finance (yfinance) — NSE/BSE stock + index news
  2. Google News RSS — macro: RBI, Fed, CPI, oil, earnings
  3. Economic Times RSS — India market news

All fetches are synchronous with short timeouts.
Called once at pipeline start, results passed to L5.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import requests

import logging
log = logging.getLogger("fm.agents.news")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_TIMEOUT = 8


# ─────────────────────────────────────────────────────────────────
# 1. Yahoo Finance — index + market news
# ─────────────────────────────────────────────────────────────────

def fetch_yfinance_news(symbol: str = "^NSEI", max_items: int = 5) -> list[str]:
    """Real headlines from Yahoo Finance for an index or stock."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        news = ticker.get_news(count=max_items)
        headlines = []
        for item in news:
            # yfinance returns nested content structure
            if "content" in item:
                title = item["content"].get("title", "")
            else:
                title = item.get("title", "")
            if title:
                headlines.append(title.strip())
        log.debug("yfinance: %d headlines for %s", len(headlines), symbol)
        return headlines[:max_items]
    except Exception as e:
        log.warning("yfinance news fetch failed for %s: %s", symbol, e)
        return []


# ─────────────────────────────────────────────────────────────────
# 2. Google News RSS — macro/India market queries
# ─────────────────────────────────────────────────────────────────

def fetch_google_news_rss(query: str, max_items: int = 5) -> list[str]:
    """
    Google News RSS feed for a query.
    URL: news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en
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
        items = root.findall(".//item")
        headlines = []
        for item in items[:max_items]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                # Google RSS titles include source after " - "
                title = title_el.text.split(" - ")[0].strip()
                if title:
                    headlines.append(title)
        log.debug("Google RSS '%s': %d headlines", query, len(headlines))
        return headlines
    except Exception as e:
        log.warning("Google RSS fetch failed for '%s': %s", query, e)
        return []


# ─────────────────────────────────────────────────────────────────
# 3. Economic Times RSS — India market specific
# ─────────────────────────────────────────────────────────────────

def fetch_et_rss(max_items: int = 5) -> list[str]:
    """Economic Times markets RSS feed."""
    try:
        url = "https://economictimes.indiatimes.com/markets/rss.cms"
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if not r.ok:
            return []
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        headlines = []
        for item in items[:max_items]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                headlines.append(title_el.text.strip())
        log.debug("ET RSS: %d headlines", len(headlines))
        return headlines
    except Exception as e:
        log.warning("ET RSS fetch failed: %s", e)
        return []


# ─────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────

def fetch_all_headlines(symbol: str = "NIFTY 50") -> list[str]:
    """
    Fetch headlines from all sources and return deduplicated list.
    Called once at pipeline start — results passed to L5 Sentiment agent.

    Returns max 10 unique, non-empty headlines.
    """
    headlines: list[str] = []
    seen: set[str] = set()

    def _add(items: list[str]) -> None:
        for h in items:
            h = h.strip()
            if h and h.lower() not in seen and len(h) > 10:
                seen.add(h.lower())
                headlines.append(h)

    # Map FM index name to Yahoo ticker
    yf_map = {
        "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK",
        "NIFTY IT": "^CNXIT", "NIFTY PHARMA": "^CNXPHARMA",
    }
    yf_ticker = yf_map.get(symbol, "^NSEI")

    # Source 1: Yahoo Finance
    _add(fetch_yfinance_news(yf_ticker, max_items=4))

    # Source 2: Google News RSS — India market + relevant queries
    _add(fetch_google_news_rss("NSE India stock market today", max_items=3))
    _add(fetch_google_news_rss("RBI monetary policy", max_items=2))

    # Source 3: Economic Times
    _add(fetch_et_rss(max_items=4))

    result = headlines[:10]
    log.info("Headlines fetched: %d total from 3 sources", len(result))
    return result
