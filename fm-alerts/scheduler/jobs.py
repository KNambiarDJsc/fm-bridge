"""
FM Trading Agency — Scheduled Jobs
=====================================
APScheduler jobs for the alerts service.

Jobs:
  1. morning_briefing()  — 9:15 AM IST every trading day
     → Calls fm-agents POST /api/analyze
     → Formats full briefing Telegram message
     → Fires Telegram + Email

  2. pre_market_check()  — 9:00 AM IST
     → Check capital shield / kill switch status
     → Validate bridge is live
     → Fire warning if bridge offline

  3. eod_summary()       — 3:30 PM IST
     → Pull today's trades from fm-journal
     → Send end-of-day P&L summary

APScheduler pattern: BackgroundScheduler with IST timezone.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from alerts.formatter import fmt_morning_briefing, fmt_kill_switch
from notifiers.telegram import send_alert
from notifiers.email import send_email_alert
from config import get_settings

log = logging.getLogger("fm.alerts.scheduler")

IST = pytz.timezone("Asia/Kolkata")


# ═══════════════════════════════════════════════════════════════
# JOB 1: MORNING BRIEFING (9:15 AM IST)
# ═══════════════════════════════════════════════════════════════

def morning_briefing() -> None:
    """
    Triggered at 9:15 AM IST.
    1. Call fm-agents /api/analyze for the default symbol
    2. Format the result as a Telegram briefing
    3. Send Telegram + optional Email
    4. Update the price monitor with the new active trade
    """
    s = get_settings()
    log.info("🌅 Morning briefing job started at %s",
             datetime.now(IST).strftime("%H:%M IST"))

    # ── Step 1: Run full analysis ─────────────────────────────
    verdict = _run_analysis(s.default_symbol, s.agents_url, s.bridge_url)
    if verdict is None:
        _send_error_alert("Morning analysis failed — check fm-agents service", s)
        return

    # ── Step 2: Format message ────────────────────────────────
    message = fmt_morning_briefing(verdict, symbol=s.default_symbol)

    # ── Step 3: Send Telegram ─────────────────────────────────
    ok = send_alert(
        message    = message,
        token      = s.telegram_token,
        chat_id    = s.telegram_chat_id,
        alert_key  = f"morning_{datetime.now(IST).date()}",
        alert_type = "MORNING_BRIEFING",
    )

    # ── Step 4: Send email fallback ───────────────────────────
    if s.resend_api_key and s.email_to:
        verdict_type = verdict.get("verdict", "ANALYSIS")
        send_email_alert(
            subject  = f"FM Trading Agency — {verdict_type} | {s.default_symbol} | {datetime.now(IST).strftime('%d %b %Y')}",
            body     = message,
            api_key  = s.resend_api_key,
            from_addr= s.email_from,
            to_addr  = s.email_to,
        )

    # ── Step 5: Update price monitor ─────────────────────────
    _update_price_monitor(verdict, s)

    log.info("✅ Morning briefing sent | verdict=%s", verdict.get("verdict", "?"))


# ═══════════════════════════════════════════════════════════════
# JOB 2: PRE-MARKET CHECK (9:00 AM IST)
# ═══════════════════════════════════════════════════════════════

def pre_market_check() -> None:
    """Check bridge health and capital shield before market open."""
    s = get_settings()
    log.info("🔍 Pre-market check at %s", datetime.now(IST).strftime("%H:%M IST"))

    # Check bridge health
    try:
        r = requests.get(f"{s.bridge_url}/health", timeout=5)
        if r.status_code != 200:
            _send_error_alert(
                f"⚠️ fm-bridge health check FAILED\n{r.status_code}: {r.text[:100]}", s
            )
            return
    except Exception as e:
        _send_error_alert(f"⚠️ fm-bridge OFFLINE: {e}", s)
        return

    # Check capital shield
    try:
        r = requests.get(f"{s.bridge_url}/api/capital-shield", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("kill_switch"):
                msg = fmt_kill_switch(
                    s.default_symbol,
                    data.get("daily_dd_pct", 0),
                    s.capital,
                    s.daily_dd_limit,
                )
                send_alert(
                    message=msg, token=s.telegram_token, chat_id=s.telegram_chat_id,
                    alert_key="pre_market_kill_switch", alert_type="KILL_SWITCH",
                )
                return
    except Exception as e:
        log.warning("Capital shield check failed: %s", e)

    log.info("✅ Pre-market check passed — bridge live, capital OK")

    # Send a quiet pre-market ready notification
    if s.telegram_token and s.telegram_chat_id:
        send_alert(
            message    = "🔔 <b>FM Trading Agency</b>\nPre-market check ✅ — Bridge live. Morning briefing in 15 min.",
            token      = s.telegram_token,
            chat_id    = s.telegram_chat_id,
            alert_key  = f"premarket_{datetime.now(IST).date()}",
            alert_type = "MORNING_BRIEFING",
            silent     = True,
        )


# ═══════════════════════════════════════════════════════════════
# JOB 3: END-OF-DAY SUMMARY (3:30 PM IST)
# ═══════════════════════════════════════════════════════════════

def eod_summary() -> None:
    """Send end-of-day P&L summary from fm-journal."""
    s = get_settings()
    log.info("📊 EOD summary job at %s", datetime.now(IST).strftime("%H:%M IST"))

    try:
        r = requests.get(
            f"{s.journal_url}/api/analytics/weekly",
            params={"capital": s.capital},
            timeout=10,
        )
        if r.status_code != 200:
            log.warning("Journal unavailable for EOD summary")
            return

        data = r.json()
        weeks = data.get("weeks", [])
        if not weeks:
            return

        latest = weeks[-1]
        net_pnl  = latest.get("net_pnl", 0)
        net_pct  = latest.get("net_pnl_pct", 0)
        wins     = latest.get("wins", 0)
        losses   = latest.get("losses", 0)
        pace     = latest.get("pace", "—")
        target   = latest.get("target_pct", s.weekly_target)

        pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"
        pace_emoji = {"EXCEEDED": "🏆", "ON_TRACK": "✅", "BEHIND": "⚠️", "AT_RISK": "🚨"}.get(pace, "—")

        msg = (
            f"📊 <b>FM EOD Summary</b>\n"
            f"{datetime.now(IST).strftime('%d %b %Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{pnl_emoji} Week P&L: <b>₹{net_pnl:+,.0f}</b> ({net_pct:+.2f}%)\n"
            f"Target: {target}% | {pace_emoji} {pace}\n"
            f"W/L: {wins}/{losses}\n"
            f"⏰ {datetime.now(IST).strftime('%I:%M %p IST')}"
        )

        send_alert(
            message=msg, token=s.telegram_token, chat_id=s.telegram_chat_id,
            alert_key=f"eod_{datetime.now(IST).date()}", alert_type="MORNING_BRIEFING",
            silent=True,
        )

    except Exception as e:
        log.error("EOD summary failed: %s", e)


# ═══════════════════════════════════════════════════════════════
# SCHEDULER FACTORY
# ═══════════════════════════════════════════════════════════════

def build_scheduler(price_monitor=None) -> BackgroundScheduler:
    """Build and return the APScheduler instance with all jobs registered.
    
    Pass price_monitor so morning_briefing can update it after analysis
    without a circular import (scheduler → app → scheduler).
    """
    global _monitor_ref
    if price_monitor is not None:
        _monitor_ref = price_monitor
    scheduler = BackgroundScheduler(timezone=IST)

    # 9:00 AM IST — pre-market check
    scheduler.add_job(
        pre_market_check,
        trigger  = CronTrigger(hour=9, minute=0, timezone=IST),
        id       = "pre_market_check",
        name     = "Pre-market health check",
        replace_existing = True,
    )

    # 9:15 AM IST — morning briefing
    scheduler.add_job(
        morning_briefing,
        trigger  = CronTrigger(hour=9, minute=15, timezone=IST),
        id       = "morning_briefing",
        name     = "Morning briefing + analysis",
        replace_existing = True,
    )

    # 3:30 PM IST — end-of-day summary
    scheduler.add_job(
        eod_summary,
        trigger  = CronTrigger(hour=15, minute=30, timezone=IST),
        id       = "eod_summary",
        name     = "End-of-day P&L summary",
        replace_existing = True,
    )

    log.info(
        "Scheduler built: 3 jobs (pre-market 9:00, briefing 9:15, EOD 15:30 IST)"
    )
    return scheduler


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _run_analysis(symbol: str, agents_url: str, bridge_url: str) -> dict | None:
    """Call fm-agents /api/analyze. Returns verdict dict or None on failure."""
    try:
        r = requests.post(
            f"{agents_url}/api/analyze",
            json={"symbol": symbol, "bridge_url": bridge_url},
            timeout=90,    # pipeline can take up to 90s
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("data", data)
        else:
            log.error("Analysis failed %d: %s", r.status_code, r.text[:200])
            return None
    except Exception as e:
        log.error("Analysis request failed: %s", e)
        return None


def _send_error_alert(message: str, s) -> None:
    """Send an error/warning alert to Telegram."""
    if not s.telegram_token or not s.telegram_chat_id:
        log.warning("No Telegram config — can't send error: %s", message)
        return
    send_alert(
        message    = f"⚠️ <b>FM Trading Agency Alert</b>\n{message}",
        token      = s.telegram_token,
        chat_id    = s.telegram_chat_id,
        alert_key  = f"error_{int(time.time())}",
        alert_type = "KILL_SWITCH",
    )


# Module-level monitor reference — set by build_scheduler(price_monitor=...)
# This avoids the circular import: scheduler/jobs.py → app.py → scheduler/jobs.py
_monitor_ref = None


def _update_price_monitor(verdict: dict, s) -> None:
    """Parse FinalVerdict and push ActiveTrade to the price monitor.
    Uses _monitor_ref injected at startup — no circular import.
    """
    global _monitor_ref
    if _monitor_ref is None:
        log.debug("No price monitor registered — skipping trade update")
        return
    try:
        from alerts.models import ActiveTrade

        entry = verdict.get("entry_zone", {}) or {}
        hedge = verdict.get("hedge_plan", {}) or {}

        sz_raw = verdict.get("position_sizing", "1") or "1"
        try:
            units = int(str(sz_raw).split()[0])
        except (ValueError, IndexError):
            units = 1

        trade = ActiveTrade(
            symbol          = s.default_symbol,
            verdict         = verdict.get("verdict", "WAIT"),
            direction       = verdict.get("direction", "LONG"),
            entry_low       = float(entry.get("low",  verdict.get("entry_low",  0))),
            entry_high      = float(entry.get("high", verdict.get("entry_high", 0))),
            stop_loss       = float(verdict.get("stop_loss",  0)),
            target1         = float(verdict.get("target1",    0)),
            target2         = float(verdict.get("target2",    0)),
            target3         = verdict.get("target3"),
            instrument      = verdict.get("instrument", ""),
            hedge_type      = hedge.get("hedge_type", "NONE"),
            hedge_strike    = hedge.get("strike"),
            ic_short_call   = hedge.get("ic_short_call"),
            ic_short_put    = hedge.get("ic_short_put"),
            units           = units,
            rr_ratio        = float(verdict.get("rr_ratio", 0)),
            execution_score = int(verdict.get("execution_score", 0)),
            confidence      = int(verdict.get("confidence_score", 0)),
            regime          = verdict.get("market_regime", ""),
            rationale       = verdict.get("rationale", ""),
            re_entry_trigger= (verdict.get("wait_details") or {}).get("re_entry_trigger", ""),
            re_entry_window = int((verdict.get("wait_details") or {}).get("re_entry_window_minutes", 30)),
        )

        _monitor_ref.update_trade(trade)
        log.info("Price monitor updated: %s %s", trade.symbol, trade.verdict)

    except Exception as e:
        log.warning("Could not update price monitor: %s", e)
