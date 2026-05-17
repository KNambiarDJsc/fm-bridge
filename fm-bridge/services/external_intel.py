"""
FM Trading Agency — External Intelligence Service
===================================================
Aggregates all free external data sources that the bridge uses
to enrich the global_cues and macro context.

CONFIRMED WORKING (tested 2026-05-18):
  ✓ yfinance         — all global indices, forex, commodities
  ✓ Finnhub          — US market news (free tier, needs key)
  ✓ alternative.me   — Fear & Greed index (free, no key)
  ✓ Twelve Data      — NSE market open/close status (demo key works)
  ✓ Google News RSS  — all queries (no key)

NEEDS API KEY (optional, stored in .env):
  • FINNHUB_API_KEY   — global news, India ADR quotes, earnings calendar
  • NEWSAPI_KEY       — English-language news headlines
  • TWELVE_DATA_KEY   — real-time price streaming (free tier)

NO KEY NEEDED (always works):
  • yfinance          — all pricing data
  • alternative.me    — Fear & Greed
  • Google News RSS   — news

All functions are cached for 5 minutes.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from datetime import datetime
from typing import Optional

import requests
import logging
log = logging.getLogger("fm.external_intel")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
_TIMEOUT  = 8
_CACHE:   dict = {}
_CACHE_TS:dict = {}
_TTL      = 300  # 5 minutes


def _cached(key: str, fn, *args, ttl=_TTL):
    now = time.time()
    if key in _CACHE and (now - _CACHE_TS.get(key, 0)) < ttl:
        return _CACHE[key]
    try:
        result = fn(*args)
        _CACHE[key]    = result
        _CACHE_TS[key] = now
        return result
    except Exception as e:
        log.warning("external_intel %s failed: %s", key, e)
        return _CACHE.get(key)  # return stale if exists


# ═══════════════════════════════════════════════════════════════
# 1. GLOBAL MARKET SNAPSHOT (yfinance — no key, all symbols work)
# ═══════════════════════════════════════════════════════════════

_GLOBAL_SYMBOLS = {
    # US equity indices
    "^GSPC":    ("SP500",       "equity"),
    "^DJI":     ("DOW",         "equity"),
    "^IXIC":    ("NASDAQ",      "equity"),
    "^VIX":     ("VIX",         "volatility"),
    # Asian indices
    "^N225":    ("NIKKEI",      "equity"),
    "^HSI":     ("HANGSENG",    "equity"),
    # Currency
    "DX-Y.NYB": ("DXY",        "forex"),
    "USDINR=X": ("USD_INR",    "forex"),
    # Commodities
    "CL=F":     ("WTI_CRUDE",  "commodity"),
    "GC=F":     ("GOLD",       "commodity"),
    # India ADRs (US-listed, real-time even after NSE close)
    "INFY":     ("INFY_ADR",   "adr"),
    "HDB":      ("HDB_ADR",    "adr"),   # HDFC Bank
    "IBN":      ("IBN_ADR",    "adr"),   # ICICI Bank
    "WIT":      ("WIT_ADR",    "adr"),   # Wipro
}


def get_global_snapshot() -> dict:
    """
    Fetch all global market data via yfinance in one call.
    Works 24/7 — critical for after-hours dashboard data richness.
    Returns dict: symbol_key -> {price, change_pct, prev_close}
    """
    def _fetch():
        import yfinance as yf
        result = {}
        for sym, (key, category) in _GLOBAL_SYMBOLS.items():
            try:
                fi    = yf.Ticker(sym).fast_info
                price = fi.last_price
                prev  = fi.previous_close or price
                chg   = (price - prev) / prev * 100 if prev else 0
                result[key] = {
                    "price":       round(price, 4),
                    "prev_close":  round(prev, 4),
                    "change_pct":  round(chg, 3),
                    "category":    category,
                    "symbol":      sym,
                }
            except Exception as e:
                log.debug("yfinance %s failed: %s", sym, e)
        log.info("Global snapshot: %d symbols fetched", len(result))
        return result
    return _cached("global_snapshot", _fetch) or {}


# ═══════════════════════════════════════════════════════════════
# 2. FEAR & GREED INDEX (alternative.me — free, no key)
# ═══════════════════════════════════════════════════════════════

def get_fear_greed() -> dict:
    """
    Crypto Fear & Greed from alternative.me — free, no key, confirmed working.
    Value 0-100. Classification: Extreme Fear / Fear / Neutral / Greed / Extreme Greed.
    Used as a proxy for global risk sentiment.
    """
    def _fetch():
        r = requests.get(
            "https://api.alternative.me/fng/?limit=2&format=json",
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        data    = r.json().get("data", [])
        current = data[0] if data else {}
        prev    = data[1] if len(data) > 1 else {}
        return {
            "value":               int(current.get("value", 50)),
            "classification":      current.get("value_classification", "Neutral"),
            "prev_value":          int(prev.get("value", 50)) if prev else None,
            "time_until_update":   int(current.get("time_until_update", 0)),
        }
    return _cached("fear_greed", _fetch, ttl=900) or {"value": 50, "classification": "Neutral"}


# ═══════════════════════════════════════════════════════════════
# 3. FINNHUB NEWS + EARNINGS (needs FINNHUB_API_KEY)
# ═══════════════════════════════════════════════════════════════

def get_finnhub_news(category: str = "general", max_items: int = 8) -> list[str]:
    """
    Finnhub global market news — 100 items on free tier.
    Requires FINNHUB_API_KEY in .env (free at finnhub.io).
    categories: general, forex, crypto, merger
    """
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return []
    def _fetch():
        r = requests.get(
            f"https://finnhub.io/api/v1/news?category={category}&token={api_key}",
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        items = r.json()
        headlines = [item.get("headline", "") for item in items[:max_items] if item.get("headline")]
        log.debug("Finnhub %s news: %d headlines", category, len(headlines))
        return headlines
    return _cached(f"finnhub_news_{category}", _fetch, ttl=600) or []


def get_finnhub_india_adr_news(symbol: str = "INFY", days: int = 1) -> list[str]:
    """
    Company-specific news for India ADRs (INFY, HDB, IBN, WIT).
    Good proxy for India sector news during US market hours.
    """
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return []
    from datetime import date, timedelta
    today = date.today().strftime("%Y-%m-%d")
    from_d = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    def _fetch():
        r = requests.get(
            f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_d}&to={today}&token={api_key}",
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        items = r.json()[:5]
        return [item.get("headline","") for item in items if item.get("headline")]
    return _cached(f"finnhub_adr_{symbol}", _fetch, ttl=600) or []


def get_finnhub_earnings_calendar(days_ahead: int = 7) -> list[dict]:
    """
    Upcoming earnings announcements — free on Finnhub.
    Returns [{date, symbol, hour (bmo/amc), epsEstimate, revenueEstimate}]
    """
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return []
    from datetime import date, timedelta
    today  = date.today().strftime("%Y-%m-%d")
    to_d   = (date.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    def _fetch():
        r = requests.get(
            f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={to_d}&token={api_key}",
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        return r.json().get("earningsCalendar", [])[:20]
    return _cached("finnhub_earnings", _fetch, ttl=3600) or []


def get_finnhub_market_status(exchange: str = "US") -> dict:
    """US / global exchange open/close status. Free on Finnhub."""
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return {}
    def _fetch():
        r = requests.get(
            f"https://finnhub.io/api/v1/stock/market-status?exchange={exchange}&token={api_key}",
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    return _cached(f"finnhub_status_{exchange}", _fetch, ttl=60) or {}


# ═══════════════════════════════════════════════════════════════
# 4. NEWSAPI (needs NEWSAPI_KEY)
# ═══════════════════════════════════════════════════════════════

def get_newsapi_headlines(
    query: str = "india stock market nifty",
    max_items: int = 5,
) -> list[str]:
    """
    NewsAPI — English-language news search.
    Free tier: 100 requests/day, developer plan.
    Requires NEWSAPI_KEY in .env (free at newsapi.org).
    Best for: breaking macro news, central bank decisions.
    """
    api_key = os.getenv("NEWSAPI_KEY", "").strip()
    if not api_key:
        return []
    def _fetch():
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": max_items,
                "apiKey":   api_key,
            },
            headers=_HEADERS, timeout=_TIMEOUT
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [a.get("title","") for a in articles if a.get("title")]
    return _cached(f"newsapi_{query[:20]}", _fetch, ttl=600) or []


# ═══════════════════════════════════════════════════════════════
# 5. TWELVE DATA — NSE market open status (demo key works!)
# ═══════════════════════════════════════════════════════════════

def get_nse_market_state() -> dict:
    """
    Twelve Data market_state endpoint — demo key works for this.
    Returns whether NSE is open, time to open, time to close.
    """
    api_key = os.getenv("TWELVE_DATA_KEY", "demo").strip() or "demo"
    def _fetch():
        r = requests.get(
            f"https://api.twelvedata.com/market_state",
            params={"apikey": api_key},
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        states = r.json()
        # Find NSE entry
        for s in states:
            if "NSE" in s.get("name","") or s.get("code","") == "XNSE":
                return {
                    "is_open":       s.get("is_market_open", False),
                    "time_to_open":  s.get("time_to_open", ""),
                    "time_to_close": s.get("time_to_close", ""),
                    "exchange":      s.get("name","NSE"),
                }
        return {}
    return _cached("nse_market_state", _fetch, ttl=60) or {}


# ═══════════════════════════════════════════════════════════════
# 6. AGGREGATED INTEL SUMMARY (used by agents + global_cues)
# ═══════════════════════════════════════════════════════════════

def get_full_external_intel() -> dict:
    """
    Single call that returns all external intelligence.
    Called by context_builder and global_cues service.
    Everything cached — fast after first call.
    """
    snapshot  = get_global_snapshot()
    fg        = get_fear_greed()
    nse_state = get_nse_market_state()

    # Derive useful signals from snapshot
    sp500  = snapshot.get("SP500", {})
    vix    = snapshot.get("VIX", {})
    dow    = snapshot.get("DOW", {})
    nq     = snapshot.get("NASDAQ", {})
    dxy    = snapshot.get("DXY", {})
    crude  = snapshot.get("WTI_CRUDE", {})
    gold   = snapshot.get("GOLD", {})
    usdinr = snapshot.get("USD_INR", {})
    nifty  = snapshot.get("SP500", {})   # fallback if ^NSEI unavailable

    vix_level = vix.get("price", 0)
    fg_value  = fg.get("value", 50)

    global_risk = "NEUTRAL"
    if vix_level > 25 or fg_value < 25 or (sp500.get("change_pct",0) < -1.5):
        global_risk = "RISK_OFF"
    elif vix_level < 15 and fg_value > 60 and (sp500.get("change_pct",0) > 0.5):
        global_risk = "RISK_ON"

    return {
        # ── Price data ───────────────────────────────────────
        "snapshot":          snapshot,
        "sp500_chg":         sp500.get("change_pct"),
        "dow_chg":           dow.get("change_pct"),
        "nasdaq_chg":        nq.get("change_pct"),
        "vix_level":         vix_level,
        "dxy_chg":           dxy.get("change_pct"),
        "wti_crude":         crude.get("price"),
        "gold_price":        gold.get("price"),
        "usd_inr":           usdinr.get("price"),
        # ── Sentiment ────────────────────────────────────────
        "fear_greed_value":  fg_value,
        "fear_greed_label":  fg.get("classification","Neutral"),
        "global_risk":       global_risk,
        # ── Market state ────────────────────────────────────
        "nse_is_open":       nse_state.get("is_open", False),
        "nse_time_to_open":  nse_state.get("time_to_open",""),
        # ── India ADRs (US-listed, real-time signals) ────────
        "infy_adr_chg":      snapshot.get("INFY_ADR", {}).get("change_pct"),
        "hdb_adr_chg":       snapshot.get("HDB_ADR",  {}).get("change_pct"),
        "ibn_adr_chg":       snapshot.get("IBN_ADR",  {}).get("change_pct"),
        "wit_adr_chg":       snapshot.get("WIT_ADR",  {}).get("change_pct"),
    }
