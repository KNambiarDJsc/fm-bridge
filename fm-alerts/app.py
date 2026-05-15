"""
FM Trading Agency — Alerts & Morning Briefing Server
======================================================
FastAPI service for Phase 6: Proactive Intelligence.

Features:
  ● 9:15 AM IST morning briefing (Telegram + Email)
  ● 9:00 AM IST pre-market check
  ● 3:30 PM IST end-of-day summary
  ● Live price monitor watching entry zone / T1 / T2 / SL / IC
  ● Kill switch alert (1% daily DD)
  ● Manual trigger endpoints

Endpoints:
  GET  /health                    — service health
  POST /api/alerts/briefing/now   — trigger morning briefing immediately
  POST /api/alerts/trade/set      — update active trade plan from frontend
  DELETE /api/alerts/trade        — clear active trade
  GET  /api/alerts/trade          — current active trade state
  POST /api/alerts/test           — send a test Telegram message
  GET  /api/alerts/status         — scheduler + monitor status

Run:
  python app.py
  # or:
  uvicorn app:app --port 8005 --reload
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from alerts.models import ActiveTrade
from monitors.price_monitor import PriceMonitor
from scheduler.jobs import build_scheduler, morning_briefing
from notifiers.telegram import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fm.alerts.app")

# ── Global singletons ──────────────────────────────────────────
_price_monitor: Optional[PriceMonitor] = None
_scheduler     = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _price_monitor, _scheduler

    s = get_settings()
    log.info("Starting FM Alerts service ...")

    # Start price monitor
    _price_monitor = PriceMonitor()
    _price_monitor.start()

    # Build + start scheduler
    _scheduler = build_scheduler(_price_monitor)
    _scheduler.start()

    log.info("✅ Alerts service ready — Telegram: %s",
             "configured" if s.telegram_token else "NOT CONFIGURED")
    yield

    # Shutdown
    if _scheduler:
        _scheduler.shutdown(wait=False)
    if _price_monitor:
        _price_monitor.stop()
    log.info("Alerts service shut down")


app = FastAPI(
    title       = "FM Trading Agency — Alerts",
    description = "Morning briefing, price alerts, kill switch",
    version     = "6.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    s = get_settings()
    return {
        "status":     "ok",
        "service":    "fm-alerts",
        "version":    "6.0.0",
        "telegram":   bool(s.telegram_token and s.telegram_chat_id),
        "email":      bool(s.resend_api_key and s.email_to),
        "scheduler":  _scheduler.running if _scheduler else False,
        "monitor":    _price_monitor._running if _price_monitor else False,
        "ts":         int(time.time() * 1000),
    }


@app.post("/api/alerts/briefing/now")
def trigger_briefing():
    """Manually trigger the morning briefing right now (useful for testing)."""
    try:
        morning_briefing()
        return {"status": "ok", "message": "Morning briefing sent"}
    except Exception as e:
        raise HTTPException(500, f"Briefing failed: {e}")


@app.post("/api/alerts/trade/set")
def set_active_trade(trade: ActiveTrade):
    """
    Update the active trade plan. Call this from fm-web when
    the trader clicks 'Execute' on a verdict.
    """
    if not _price_monitor:
        raise HTTPException(503, "Price monitor not running")
    _price_monitor.update_trade(trade)
    return {"status": "ok", "trade": trade.model_dump(mode="json")}


@app.delete("/api/alerts/trade")
def clear_active_trade():
    """Clear the active trade — stop watching price levels."""
    if _price_monitor:
        _price_monitor.clear_trade()
    return {"status": "ok"}


@app.get("/api/alerts/trade")
def get_active_trade():
    """Return current active trade being monitored."""
    if not _price_monitor:
        raise HTTPException(503, "Monitor not running")
    trade = _price_monitor.active_trade
    return {
        "trade":       trade.model_dump(mode="json") if trade else None,
        "last_price":  _price_monitor.last_price,
    }


class TestAlertRequest(BaseModel):
    message: str = "🔔 FM Trading Agency — Test Alert\nAll systems nominal ✅"


@app.post("/api/alerts/test")
def send_test_alert(req: TestAlertRequest):
    """Send a test message to Telegram to verify configuration."""
    s = get_settings()
    ok = send_alert(
        message    = req.message,
        token      = s.telegram_token,
        chat_id    = s.telegram_chat_id,
        alert_key  = f"test_{int(time.time())}",
        alert_type = "MORNING_BRIEFING",
    )
    if not ok:
        raise HTTPException(500, "Telegram send failed — check TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env")
    return {"status": "ok", "sent": True}


@app.get("/api/alerts/status")
def get_status():
    """Return full status of scheduler jobs + monitor."""
    s    = get_settings()
    jobs = []
    if _scheduler:
        for job in _scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id":       job.id,
                "name":     job.name,
                "next_run": next_run.isoformat() if next_run else None,
            })

    return {
        "scheduler_running": _scheduler.running if _scheduler else False,
        "monitor_running":   _price_monitor._running if _price_monitor else False,
        "jobs":              jobs,
        "active_trade":      _price_monitor.active_trade.symbol
                             if _price_monitor and _price_monitor.active_trade else None,
        "last_price":        _price_monitor.last_price if _price_monitor else 0,
        "telegram_ok":       bool(s.telegram_token and s.telegram_chat_id),
        "email_ok":          bool(s.resend_api_key and s.email_to),
    }


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    s = get_settings()
    print(f"\n  FM Trading Agency — Alerts & Morning Briefing v6.0")
    print(f"  Port:     8005")
    print(f"  Telegram: {'✓ configured' if s.telegram_token else '✗ NOT CONFIGURED — add TELEGRAM_TOKEN to .env'}")
    print(f"  Email:    {'✓ configured' if s.resend_api_key else '— disabled'}")
    print(f"  Bridge:   {s.bridge_url}")
    print(f"  Agents:   {s.agents_url}\n")

    uvicorn.run("app:app", host="0.0.0.0", port=8005, log_level="warning", reload=False)
