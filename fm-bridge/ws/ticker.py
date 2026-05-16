"""
FM Trading Agency — WebSocket Tick Streamer
=============================================
Real-time price updates via Zerodha KiteTicker.
Replaces the 5-second polling loop.

Architecture (inspired by OpenAlgo websocket_proxy):
  KiteTicker (Zerodha) → on_ticks callback → ZMQ PUB socket
  fm-web / fm-agents subscribe to ZMQ socket for live prices

FastAPI WebSocket endpoint /ws/ticks also available for direct browser connection.

ZMQ allows multiple consumers (frontend + AI backend + alerts service)
without multiple Zerodha connections (Zerodha rate-limits these).
"""

from __future__ import annotations

import json
import threading
import time
from typing import Optional, Callable

import zmq

from config import INSTRUMENT_MAP, EXCHANGE_MAP, get_settings
from services.market_data import update_ltp

import logging
log = logging.getLogger("fm.ticker")


# ── Reverse map: token → index name ──────────────────────────────
_TOKEN_TO_NAME = {v: k for k, v in INSTRUMENT_MAP.items()}

# ── ZMQ publisher ─────────────────────────────────────────────────
_zmq_context: Optional[zmq.Context] = None
_zmq_socket:  Optional[zmq.Socket]  = None

# ── Active tick subscribers (for FastAPI WebSocket path) ──────────
_ws_subscribers: list[Callable] = []
_sub_lock = threading.Lock()

# ── Ticker state ──────────────────────────────────────────────────
_ticker = None
_running = False


def _get_zmq_socket() -> zmq.Socket:
    global _zmq_context, _zmq_socket
    if _zmq_socket is None:
        settings = get_settings()
        _zmq_context = zmq.Context()
        _zmq_socket  = _zmq_context.socket(zmq.PUB)
        _zmq_socket.bind(f"tcp://127.0.0.1:{settings.zmq_port}")
        log.info("ZMQ PUB socket bound on port %d", settings.zmq_port)
    return _zmq_socket


def _publish_tick(name: str, price: float, tick: dict) -> None:
    """Publish a tick to all consumers."""
    try:
        sock = _get_zmq_socket()
        msg  = json.dumps({
            "symbol": name,
            "price":  price,
            "ts":     int(time.time() * 1000),
            **{k: tick.get(k) for k in ["volume", "buy_quantity", "sell_quantity"] if k in tick},
        })
        # ZMQ topic = index name (allows filtered subscription)
        sock.send_multipart([name.encode(), msg.encode()], zmq.NOBLOCK)
    except zmq.ZMQError as e:
        log.debug("ZMQ publish error (non-fatal): %s", e)

    # Also push to FastAPI WebSocket subscribers
    with _sub_lock:
        for cb in list(_ws_subscribers):
            try:
                cb(name, price)
            except Exception:
                pass


def subscribe_ws(callback: Callable) -> None:
    """Register a FastAPI WebSocket handler to receive ticks."""
    with _sub_lock:
        _ws_subscribers.append(callback)


def unsubscribe_ws(callback: Callable) -> None:
    with _sub_lock:
        if callback in _ws_subscribers:
            _ws_subscribers.remove(callback)


# ─────────────────────────────────────────────────────────────────
# KITETICKER CALLBACKS
# ─────────────────────────────────────────────────────────────────

def _on_ticks(ws, ticks: list) -> None:
    for tick in ticks:
        token = tick.get("instrument_token")
        price = tick.get("last_price") or tick.get("last_traded_price")
        if not (token and price):
            continue
        name = _TOKEN_TO_NAME.get(token)
        if not name:
            continue
        # Update LTP cache (used by HTTP endpoints as fallback)
        update_ltp(name, float(price))
        # Publish to all consumers
        _publish_tick(name, float(price), tick)


def _on_connect(ws, response) -> None:
    """Subscribe to all tracked instruments on connect."""
    tokens = list(INSTRUMENT_MAP.values())
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_LTP, tokens)
    log.info("KiteTicker connected — subscribed %d instruments (LTP mode)", len(tokens))


def _on_close(ws, code, reason) -> None:
    log.warning("KiteTicker closed: %s %s", code, reason)


def _on_error(ws, code, reason) -> None:
    log.error("KiteTicker error: %s %s", code, reason)


def _on_reconnect(ws, attempts) -> None:
    log.info("KiteTicker reconnecting (attempt %d) ...", attempts)


def _on_noreconnect(ws) -> None:
    log.error("KiteTicker: max reconnects reached — falling back to HTTP polling")


# ─────────────────────────────────────────────────────────────────
# START / STOP
# ─────────────────────────────────────────────────────────────────

def start_ticker(kite) -> None:
    """Start the KiteTicker WebSocket in a background thread."""
    global _ticker, _running
    if _running:
        log.debug("Ticker already running")
        return

    try:
        from kiteconnect import KiteTicker
        access_token = kite.access_token
        api_key      = kite.api_key

        _ticker = KiteTicker(api_key, access_token)
        _ticker.on_ticks     = _on_ticks
        _ticker.on_connect   = _on_connect
        _ticker.on_close     = _on_close
        _ticker.on_error     = _on_error
        _ticker.on_reconnect = _on_reconnect
        _ticker.on_noreconnect = _on_noreconnect

        # Run in background thread (threaded=True keeps it non-blocking)
        t = threading.Thread(
            target=_ticker.connect,
            kwargs={"threaded": True, "disable_ssl_verification": False},
            daemon=True,
        )
        t.start()
        _running = True
        log.info("KiteTicker started in background thread [OK]")

    except ImportError:
        log.warning("KiteTicker not available — using HTTP polling fallback")
        _start_polling_fallback(kite)
    except Exception as e:
        log.error("KiteTicker start failed: %s — falling back to polling", e)
        _start_polling_fallback(kite)


def stop_ticker() -> None:
    global _ticker, _running
    if _ticker:
        try:
            _ticker.close()
        except Exception:
            pass
    _running = False

    if _zmq_socket:
        try:
            _zmq_socket.close()
        except Exception:
            pass
    if _zmq_context:
        try:
            _zmq_context.term()
        except Exception:
            pass


def _start_polling_fallback(kite) -> None:
    """5-second HTTP polling as fallback when KiteTicker is unavailable."""
    from services.market_data import get_all_ltp

    def _poll():
        while True:
            try:
                prices = get_all_ltp()
                for name, price in prices.items():
                    _publish_tick(name, price, {})
            except Exception as e:
                log.debug("Polling error: %s", e)
            time.sleep(5)

    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("HTTP polling fallback started (5s interval)")