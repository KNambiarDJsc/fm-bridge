"""
FM Trading Agency — API Routers
==================================
All FastAPI route handlers.  Every response is a validated Pydantic model.
Legacy endpoints (without /api/ prefix) are preserved for the HTML prototype.
"""

from __future__ import annotations

import time
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from models import (
    BridgeResponse, MarketQuote, VIXReading, HistoricalData,
    OptionsChain, MacroContext, MultiIndexHeatmap, MultiTFIndicators,
    CapitalShield, SessionContext,
)

# ═══════════════════════════════════════════════════════════════
# LIVE DATA ROUTER  (prices, quotes, VIX)
# ═══════════════════════════════════════════════════════════════

live_router = APIRouter(prefix="/api", tags=["live"])


@live_router.get("/ping")
def ping():
    return {"status": "ok", "ts": int(time.time() * 1000)}


@live_router.get("/ltp")
def get_ltp(index: str = Query("NIFTY 50")):
    from services.market_data import get_ltp
    return get_ltp(index)


@live_router.get("/quote")
def get_quote(index: str = Query("NIFTY 50")) -> dict:
    from services.market_data import get_quote
    q = get_quote(index)
    return q.model_dump()


@live_router.get("/vix")
def get_vix():
    from services.market_data import get_vix
    return get_vix().model_dump()


@live_router.get("/all-ltp")
def get_all_ltp():
    """Bulk LTP for all tracked indices — used by heatmap real-time update."""
    from services.market_data import get_all_ltp
    return {"prices": get_all_ltp(), "ts": int(time.time() * 1000)}


@live_router.get("/profile")
def get_profile():
    from services.market_data import _kite
    if not _kite:
        return {"error": "Not connected"}
    try:
        return _kite.profile()
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# HISTORICAL ROUTER  (OHLCV bars, multi-timeframe)
# ═══════════════════════════════════════════════════════════════

historical_router = APIRouter(tags=["historical"])


@historical_router.get("/historical")
@historical_router.get("/api/historical")
def get_historical(
    symbol:   str = Query("NIFTY 50"),
    interval: str = Query("day"),
    range:    str = Query("1y"),
):
    """OHLCV bars for charting. Preserves original format for HTML prototype."""
    from services.market_data import get_historical
    h = get_historical(symbol, interval, range)
    # Return in the same format the HTML prototype expects
    bars = [[b.ts, b.open, b.high, b.low, b.close, b.volume] for b in h.bars]
    return {"status": "success", "data": bars, "count": len(bars), "symbol": symbol, "interval": interval}


@historical_router.get("/api/timeframes/{symbol:path}")
def get_timeframes(symbol: str):
    """1D/1H/15M/5M indicators in one shot — feeds Section B3 multi-TF panel."""
    from services.indicators import compute_multi_tf
    from services.market_data import _kite
    if not _kite:
        return {"error": "Bridge not connected"}
    mti = compute_multi_tf(symbol, _kite)
    return mti.model_dump()


# ═══════════════════════════════════════════════════════════════
# OPTIONS ROUTER  (chain, OPR, positions)
# ═══════════════════════════════════════════════════════════════

options_router = APIRouter(prefix="/api", tags=["options"])


@options_router.get("/options-chain")
def get_options_chain(symbol: str = Query("NIFTY 50")):
    """NSE option chain: PCR, Max Pain, OPR, Call/Put Walls, OI map."""
    from services.options_chain import fetch_options_chain
    oc = fetch_options_chain(symbol)
    return oc.model_dump()


@options_router.get("/multi-index")
def get_multi_index():
    """Score all 10 indices in parallel — heatmap data."""
    from services.multi_index import get_multi_index_heatmap
    hm = get_multi_index_heatmap()
    return hm.model_dump()


# ═══════════════════════════════════════════════════════════════
# CONTEXT ROUTER  (macro, indicators, session, capital shield)
# ═══════════════════════════════════════════════════════════════

context_router = APIRouter(prefix="/api", tags=["context"])


@context_router.get("/macro-context")
def get_macro_context():
    """
    All macro inputs for L1 Macro Sieve.
    Auto-fetched at 9 AM.  Returns cached data with age in minutes.
    """
    from services.macro_context import fetch_macro_context
    ctx = fetch_macro_context()
    return ctx.model_dump()


@context_router.get("/indicators")
def get_indicators(
    symbol:   str = Query("NIFTY 50"),
    interval: str = Query("day"),
    range:    str = Query("6mo"),
):
    """Full indicator pack for one symbol/interval via pandas-ta."""
    from services.market_data import get_historical
    from services.indicators  import compute_indicators
    import pandas as pd

    h = get_historical(symbol, interval, range)
    if not h.bars:
        return {"error": "No bars available"}

    df = pd.DataFrame([
        {"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume}
        for b in h.bars
    ])
    pack = compute_indicators(df, symbol, interval)
    return pack.model_dump()


@context_router.get("/session")
def get_session():
    """Current market session context — tells agents how to weight signals."""
    from services.market_session import get_session_context
    return get_session_context().model_dump()


@context_router.get("/global-cues")
def get_global_cues():
    """
    Global market cues: GIFT Nifty, USD/INR, Dow, Nasdaq, Gold, RBI stance, event calendar.
    Cached 15 min. Called at 8:55 AM by scheduler.
    """
    from services.market_data import _kite
    from services.global_cues import fetch_global_cues
    cues = fetch_global_cues(kite=_kite)
    return cues.to_dict()


@context_router.get("/external-intel")
def get_external_intel():
    """External intelligence: global markets, Fear & Greed, ADRs, NSE state."""
    from services.external_intel import get_full_external_intel
    return get_full_external_intel()

@context_router.get("/event-calendar")
def get_event_calendar():
    """Upcoming market events for the next 7 days (RBI MPC, FOMC, expiry, results season)."""
    from services.global_cues import get_upcoming_events
    return get_upcoming_events(days_ahead=14)


@context_router.get("/iv-history/{symbol}")
def get_iv_history(symbol: str):
    """Rolling ATM IV history and current IV rank/percentile for a symbol."""
    import json
    from pathlib import Path
    from services.options_chain import get_iv_rank, _cache as oc_cache
    hist_file = Path.home() / ".fm_iv_history.json"
    history = {}
    if hist_file.exists():
        try:
            data = json.loads(hist_file.read_text())
            history = data.get(symbol, {})
        except Exception:
            pass
    # Current IV from cache
    oc = oc_cache.get(symbol)
    current_iv = oc.atm_iv if oc else None
    iv_rank, iv_pct, iv_regime = get_iv_rank(symbol, current_iv)
    return {
        "symbol":     symbol,
        "current_iv": current_iv,
        "iv_rank":    iv_rank,
        "iv_pct":     iv_pct,
        "iv_regime":  iv_regime,
        "history_days": len(history),
        "history":    dict(list(sorted(history.items()))[-30:]),  # last 30 days
    }


@context_router.get("/capital-shield")
def get_capital_shield():
    """Live capital protection state — L8 Risk Governor reads this."""
    from services.capital_shield import get_shield
    return get_shield().model_dump()


@context_router.post("/capital-shield/reset-kill-switch")
def reset_kill_switch():
    """Admin: manually reset kill switch after reviewing drawdown."""
    from services.capital_shield import reset_kill_switch
    return reset_kill_switch().model_dump()


@context_router.post("/capital-shield/update-pnl")
async def update_pnl(request: Request):
    """Log a completed trade's P&L — updates capital shield state."""
    from services.capital_shield import update_pnl
    try:
        body = await request.json()
        pnl  = float(body.get("pnl", 0))
        return update_pnl(pnl).model_dump()
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# PAPER POSITIONS (preserved from original bridge)
# ═══════════════════════════════════════════════════════════════

positions_router = APIRouter(prefix="/api", tags=["positions"])

from pathlib import Path as _Path
import json as _json

_POS_FILE = _Path.home() / ".fm_paper_positions.json"


@positions_router.get("/positions")
def get_positions():
    if _POS_FILE.exists():
        try:
            return {"positions": _json.loads(_POS_FILE.read_text())}
        except Exception:
            pass
    return {"positions": []}


@positions_router.post("/positions")
async def save_positions(request: Request):
    try:
        body = await request.json()
        _POS_FILE.write_text(_json.dumps(body))
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# LEGACY ENDPOINTS (kept for HTML prototype compatibility)
# ═══════════════════════════════════════════════════════════════

legacy_router = APIRouter(tags=["legacy"])


@legacy_router.get("/ping")
def ping_legacy():
    return {"status": "ok", "ts": int(time.time() * 1000)}


@legacy_router.get("/vix")
def vix_legacy():
    from services.market_data import get_vix
    return get_vix().model_dump()


@legacy_router.get("/ltp")
def ltp_legacy(symbol: str = Query("NIFTY 50"), access_token: str = Query("")):
    from services.market_data import get_ltp, _kite
    if access_token and _kite:
        _kite.set_access_token(access_token)
    return get_ltp(symbol)


@legacy_router.get("/health")
def health_legacy():
    from services.market_data import _kite
    from config import load_token
    cfg = load_token()
    return {
        "status":     "ok",
        "bridge":     "FM Trading Agency v5.0",
        "logged_in":  _kite is not None,
        "token_date": cfg.get("token_date"),
        "ts":         time.time(),
    }


@legacy_router.get("/positions")
def positions_legacy():
    if _POS_FILE.exists():
        try:
            return {"status": "success", "data": {"net": _json.loads(_POS_FILE.read_text())}}
        except Exception:
            pass
    return {"status": "success", "data": {"net": [], "day": []}}