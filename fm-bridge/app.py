"""
FM Trading Agency — Bridge v5.0
=================================
Main FastAPI application entry point.

Run with:
    python app.py

Or for development (auto-reload):
    uvicorn app:app --reload --port 8002

What this does at startup:
  1. Authenticates with Zerodha (TOTP auto-login or manual flow)
  2. Starts KiteTicker WebSocket for sub-1s tick updates
  3. Starts APScheduler (7 AM options chain, 9 AM macro context)
  4. Starts FastAPI HTTP server on :8002
  5. Exposes WebSocket /ws/ticks for browser real-time updates

Endpoints overview:
  GET  /health                     — bridge status
  GET  /api/ping                   — heartbeat
  GET  /api/ltp                    — live LTP
  GET  /api/quote                  — full OHLC quote
  GET  /api/vix                    — India VIX
  GET  /api/all-ltp                — bulk LTP all indices
  GET  /historical                 — OHLCV bars (legacy format)
  GET  /api/timeframes/{symbol}    — multi-TF indicators (1D/1H/15M/5M)
  GET  /api/options-chain          — PCR, Max Pain, OPR, OI map
  GET  /api/multi-index            — 10-index opportunity heatmap
  GET  /api/macro-context          — oil, FII/DII, VIX, risk context
  GET  /api/indicators             — full pandas-ta indicator pack
  GET  /api/session                — current market session context
  GET  /api/capital-shield         — risk governor / drawdown state
  POST /api/capital-shield/update-pnl
  POST /api/capital-shield/reset-kill-switch
  GET  /api/positions              — paper trading positions
  POST /api/positions
  WS   /ws/ticks                   — real-time tick stream (JSON)
"""

from __future__ import annotations

import sys
import asyncio
import json
import logging
import time
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Logging setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fm.bridge")

# ── Suppress noisy uvicorn access log ────────────────────────────
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────
# LIFESPAN (startup / shutdown)
# ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Runs startup tasks before yielding, then shutdown tasks after.
    """
    # ── STARTUP ───────────────────────────────────────────────────
    log.info("=" * 58)
    log.info("  FM Trading Agency — Bridge v5.0  starting ...")
    log.info("=" * 58)

    # 1. Authenticate with Zerodha
    from auth import authenticate
    from config import get_settings
    settings = get_settings()

    kite = authenticate(settings)

    # 2. Inject kite into all services that need it
    import services.market_data as md
    import services.multi_index as mi
    md.set_kite(kite)
    mi.set_kite(kite)

    # 3. Start KiteTicker WebSocket (real-time ticks)
    from ws.ticker import start_ticker
    start_ticker(kite)

    # 4. Start APScheduler
    from scheduler.jobs import start_scheduler
    start_scheduler()

    # 5. Pre-warm caches immediately on startup
    #    (so the trader gets data right away if it's after 9 AM)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _prewarm_caches)

    log.info("")
    log.info("  [OK]  Bridge running at  http://localhost:8002")
    log.info("  [OK]  WebSocket ticks at ws://localhost:8002/ws/ticks")
    log.info("  [OK]  Docs at           http://localhost:8002/docs")
    log.info("")
    _print_endpoints()

    yield   # ← FastAPI serves requests here

    # ── SHUTDOWN ──────────────────────────────────────────────────
    log.info("Bridge shutting down ...")
    from ws.ticker   import stop_ticker
    from scheduler.jobs     import stop_scheduler
    stop_ticker()
    stop_scheduler()
    log.info("Bridge stopped.")


def _prewarm_caches() -> None:
    """Run in executor to avoid blocking the event loop."""
    try:
        from services.macro_context  import fetch_macro_context
        from services.options_chain  import prefetch_all
        from services.multi_index    import get_multi_index_heatmap
        log.info("Pre-warming caches ...")
        fetch_macro_context(force=True)
        prefetch_all()
        get_multi_index_heatmap(force=True)
        log.info("[OK]  Cache pre-warm complete")
    except Exception as e:
        log.warning("Cache pre-warm partial failure (non-fatal): %s", e)


def _print_endpoints():
    log.info("  Endpoints:")
    endpoints = [
        "GET  /health                     — bridge status",
        "GET  /api/ltp                    — live price",
        "GET  /api/quote                  — full OHLC quote",
        "GET  /api/vix                    — India VIX",
        "GET  /api/all-ltp                — bulk LTP all indices",
        "GET  /historical                 — OHLCV bars",
        "GET  /api/timeframes/{symbol}    — multi-TF indicators",
        "GET  /api/options-chain          — PCR, Max Pain, OPR",
        "GET  /api/multi-index            — 10-index heatmap",
        "GET  /api/macro-context          — oil + FII/DII + VIX",
        "GET  /api/indicators             — pandas-ta indicator pack",
        "GET  /api/session                — market session context",
        "GET  /api/capital-shield         — risk governor state",
        "WS   /ws/ticks                   — real-time tick stream",
    ]
    for ep in endpoints:
        log.info("  " + ep)


# ─────────────────────────────────────────────────────────────────
# APP CREATION
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "FM Trading Agency Bridge",
    description = "NSE market data, options intelligence, and Zerodha integration",
    version     = "5.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS (allow all for local development) ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────
from routers import (
    live_router, historical_router, options_router,
    context_router, positions_router, legacy_router,
)
app.include_router(live_router)
app.include_router(historical_router)
app.include_router(options_router)
app.include_router(context_router)
app.include_router(positions_router)
app.include_router(legacy_router)


# ── Health endpoint (root level) ──────────────────────────────────
@app.get("/health")
def health():
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


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET /ws/ticks — real-time tick stream for browsers
# ─────────────────────────────────────────────────────────────────

class _WSManager:
    """Simple WebSocket connection manager for /ws/ticks."""
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast(self, msg: dict):
        text = json.dumps(msg)
        dead: list[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)


_ws_manager = _WSManager()


def _tick_callback(name: str, price: float) -> None:
    """Called by the ticker on every tick — schedules broadcast."""
    msg = {"type": "tick", "symbol": name, "price": price, "ts": int(time.time() * 1000)}
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_ws_manager.broadcast(msg), loop)
    except RuntimeError:
        pass


# Register the callback once (after app is created)
from ws.ticker import subscribe_ws
subscribe_ws(_tick_callback)


@app.websocket("/ws/ticks")
async def ws_ticks(websocket: WebSocket):
    """
    Real-time tick stream via WebSocket.
    Send { "subscribe": ["NIFTY 50", "BANK NIFTY"] } to filter.
    Receives { "type": "tick", "symbol": "...", "price": 24150.5, "ts": ... }
    """
    await _ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — ignore messages (subscription filter is Phase 2 feature)
            await asyncio.wait_for(websocket.receive_text(), timeout=30)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await _ws_manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from config import get_settings
    s = get_settings()
    print(f"\n  Starting FM Bridge on {s.bridge_host}:{s.bridge_port} ...\n")
    uvicorn.run(
        "app:app",
        host       = s.bridge_host,
        port       = s.bridge_port,
        log_level  = "warning",
        access_log = False,
        reload     = False,
    )