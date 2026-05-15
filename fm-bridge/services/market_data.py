"""
FM Trading Agency — Market Data Service
==========================================
Live price, quote, VIX, and historical OHLCV from Zerodha Kite Connect.
All data is returned as validated Pydantic models.

The LTP cache is updated by the WebSocket ticker in websocket/ticker.py.
This service provides the HTTP polling fallback.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from config import INSTRUMENT_MAP, EXCHANGE_MAP, get_settings
from models import (
    MarketQuote, VIXReading, HistoricalData, OHLCVBar
)

import logging
log = logging.getLogger("fm.market_data")

# ── In-memory LTP cache (updated by background poller) ───────────
# When WebSocket ticker is running this is updated sub-second.
# If bridge runs without WebSocket it falls back to 5s polling.
_ltp_cache:  dict[str, float]  = {}
_ltp_ts:     dict[str, float]  = {}

# Shared KiteConnect instance (set by app.py on startup)
_kite = None

def set_kite(k) -> None:
    global _kite
    _kite = k

def update_ltp(symbol: str, price: float) -> None:
    """Called by WebSocket ticker and background poller."""
    _ltp_cache[symbol] = price
    _ltp_ts[symbol]    = time.time()


# ────────────────────────────────────────────────────────────────
# LTP (Last Traded Price)
# ────────────────────────────────────────────────────────────────

def get_ltp(symbol: str = "NIFTY 50") -> dict:
    """Fastest price fetch — tries cache first, then live API."""
    # Return from cache if < 3 seconds old
    cached_price = _ltp_cache.get(symbol)
    cache_age    = time.time() - _ltp_ts.get(symbol, 0)
    if cached_price and cache_age < 3:
        return {
            "price":   cached_price,
            "symbol":  symbol,
            "source":  "ws_cache",
            "age_ms":  int(cache_age * 1000),
            "fetched": int(time.time() * 1000),
        }

    if not _kite:
        return {"error": "Bridge not connected", "price": None}

    try:
        sym  = EXCHANGE_MAP.get(symbol, "NSE:NIFTY 50")
        data = _kite.ltp([sym])
        price = data.get(sym, {}).get("last_price", 0)
        update_ltp(symbol, price)
        return {
            "price":   price,
            "symbol":  symbol,
            "source":  "zerodha_live",
            "fetched": int(time.time() * 1000),
        }
    except Exception as e:
        log.error("LTP fetch error for %s: %s", symbol, e)
        return {"error": str(e), "price": None}


def get_all_ltp() -> dict[str, float]:
    """Return latest LTP for all tracked indices — used by heatmap."""
    if not _kite:
        return {}
    try:
        syms = list(EXCHANGE_MAP.values())
        data = _kite.ltp(syms)
        result = {}
        for name, sym in EXCHANGE_MAP.items():
            p = data.get(sym, {}).get("last_price")
            if p:
                update_ltp(name, p)
                result[name] = p
        return result
    except Exception as e:
        log.error("Bulk LTP fetch error: %s", e)
        # Return whatever is cached
        return dict(_ltp_cache)


# ────────────────────────────────────────────────────────────────
# FULL QUOTE
# ────────────────────────────────────────────────────────────────

def get_quote(symbol: str = "NIFTY 50") -> MarketQuote:
    if not _kite:
        return MarketQuote(symbol=symbol, price=0, source="error")
    try:
        sym  = EXCHANGE_MAP.get(symbol, "NSE:NIFTY 50")
        data = _kite.quote([sym])
        q    = data.get(sym, {})
        ohlc = q.get("ohlc", {})
        price     = q.get("last_price", 0)
        prev_close = ohlc.get("close", price)
        chg = round((price - prev_close) / max(1, prev_close) * 100, 2)
        update_ltp(symbol, price)
        return MarketQuote(
            symbol     = symbol,
            price      = price,
            chg_pct    = chg,
            high       = ohlc.get("high", 0),
            low        = ohlc.get("low", 0),
            open       = ohlc.get("open", 0),
            prev_close = prev_close,
            volume     = q.get("volume", 0),
            source     = "zerodha",
            fetched_ms = int(time.time() * 1000),
        )
    except Exception as e:
        log.error("Quote fetch error for %s: %s", symbol, e)
        return MarketQuote(symbol=symbol, price=0, source=f"error:{e}")


# ────────────────────────────────────────────────────────────────
# VIX
# ────────────────────────────────────────────────────────────────

def get_vix() -> VIXReading:
    """India VIX — tries Zerodha first, then NSE public API."""
    # ── Zerodha ──────────────────────────────────────────────────
    if _kite:
        try:
            data = _kite.ltp(["NSE:INDIA VIX"])
            v = data.get("NSE:INDIA VIX", {}).get("last_price")
            if v and v > 0:
                return VIXReading(vix=round(float(v), 2), source="zerodha")
        except Exception:
            pass

    # ── NSE API fallback ──────────────────────────────────────────
    try:
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        })
        sess.get("https://www.nseindia.com", timeout=5)
        r = sess.get(
            "https://www.nseindia.com/api/allIndices",
            headers={"Referer": "https://www.nseindia.com"},
            timeout=8,
        )
        if r.ok:
            for idx in r.json().get("data", []):
                if "VIX" in idx.get("index", ""):
                    return VIXReading(vix=round(float(idx["last"]), 2), source="nse_api")
    except Exception as e:
        log.warning("NSE VIX fetch failed: %s", e)

    return VIXReading(vix=None, error="VIX unavailable — bridge not connected or NSE unreachable")


# ────────────────────────────────────────────────────────────────
# HISTORICAL OHLCV
# ────────────────────────────────────────────────────────────────

_RANGE_DAYS = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
    "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
}

def get_historical(
    symbol: str   = "NIFTY 50",
    interval: str = "day",
    range: str    = "1y",
) -> HistoricalData:
    if not _kite:
        return HistoricalData(symbol=symbol, interval=interval, bars=[], count=0, source="error")

    days      = _RANGE_DAYS.get(range, 365)
    to_date   = datetime.now()
    from_date = to_date - timedelta(days=days)
    token     = INSTRUMENT_MAP.get(symbol, 256265)

    try:
        data = _kite.historical_data(
            instrument_token = token,
            from_date        = from_date.strftime("%Y-%m-%d"),
            to_date          = to_date.strftime("%Y-%m-%d"),
            interval         = interval,
            continuous       = False,
            oi               = False,
        )
        bars = [
            OHLCVBar(
                ts     = d["date"].strftime("%Y-%m-%dT%H:%M:%S+0530"),
                open   = float(d["open"]),
                high   = float(d["high"]),
                low    = float(d["low"]),
                close  = float(d["close"]),
                volume = int(d["volume"]),
            )
            for d in data
            if d.get("close", 0) > 0
        ]
        return HistoricalData(
            symbol   = symbol,
            interval = interval,
            bars     = bars,
            count    = len(bars),
            source   = "zerodha",
        )
    except Exception as e:
        log.error("Historical data error for %s: %s", symbol, e)
        return HistoricalData(symbol=symbol, interval=interval, bars=[], count=0, source=f"error:{e}")