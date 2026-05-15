"""
FM Trading Agency — Scheduler Jobs
=====================================
APScheduler jobs that pre-warm data caches so the trader
opens the dashboard at 9:15 AM with everything already populated.

Schedule:
  07:00 IST  — options chain batch pull (all supported indices)
  09:00 IST  — macro context (oil + FII/DII + VIX)
  09:00 IST  — multi-index heatmap pre-warm
  00:01 IST  — daily capital shield reset (new trading day)

The scheduler runs inside the bridge process.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import logging
log = logging.getLogger("fm.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_options_chain() -> None:
    log.info("⏰  [7:00 AM] Scheduled options chain fetch starting ...")
    try:
        from services.options_chain import prefetch_all
        prefetch_all()
        log.info("✓  Options chain pre-warmed for all indices")
    except Exception as e:
        log.error("Options chain scheduled fetch failed: %s", e)


def _job_global_cues() -> None:
    """Pre-warm global cues: GIFT Nifty, USD/INR, Dow, Nasdaq, RBI RSS, event calendar."""
    log.info("⏰  [8:55 AM] Global cues pre-fetch ...")
    try:
        from services.market_data import _kite
        from services.global_cues import fetch_global_cues
        cues = fetch_global_cues(kite=_kite, force=True)
        log.info(
            "✓  Global cues: USD/INR=%.2f | GIFT=%s (%+.0f pts) | Dow%+.1f%% | RBI=%s | GlobalRisk=%s",
            cues.usd_inr or 0,
            f"{cues.gift_nifty:.0f}" if cues.gift_nifty else "N/A",
            cues.gift_premium or 0,
            cues.dow_change_pct or 0,
            cues.rbi_stance,
            cues.global_risk,
        )
    except Exception as e:
        log.error("Global cues scheduled fetch failed: %s", e)


def _job_iv_snapshot() -> None:
    """Store daily ATM IV snapshot for rolling IV rank computation."""
    log.info("⏰  [9:30 AM] IV snapshot store ...")
    try:
        from services.options_chain import _cache as oc_cache, get_iv_rank
        for symbol, oc in oc_cache.items():
            if oc.atm_iv and oc.atm_iv > 0:
                rank, pct, regime = get_iv_rank(symbol, oc.atm_iv)
                log.info("  IV snapshot %s: ATM=%.1f%% | Rank=%.0f | Pct=%.0f | %s",
                         symbol, oc.atm_iv, rank or 0, pct or 0, regime)
    except Exception as e:
        log.error("IV snapshot job failed: %s", e)


def _job_macro_context() -> None:
    log.info("⏰  [9:00 AM] Scheduled macro context fetch ...")
    try:
        from services.market_data import _kite
        from services.macro_context import fetch_macro_context
        ctx = fetch_macro_context(force=True, kite=_kite)
        log.info(
            "✓  Macro: oil=$%.0f FII=₹%.0fCr VIX=%.1f USD/INR=%.2f GIFT=%s → %s (score %d)",
            ctx.brent_oil or 0, ctx.fii_net or 0, ctx.india_vix or 0,
            ctx.inr_usd or 0,
            f"{ctx.__dict__.get('gift_nifty', 0):.0f}" if ctx.__dict__.get('gift_nifty') else "N/A",
            ctx.risk_context, ctx.macro_score or 0,
        )
    except Exception as e:
        log.error("Macro context scheduled fetch failed: %s", e)


def _job_heatmap_prewarm() -> None:
    log.info("⏰  [9:00 AM] Heatmap pre-warm ...")
    try:
        from services.multi_index import get_multi_index_heatmap
        hm = get_multi_index_heatmap(force=True)
        best = hm.best
        log.info(
            "✓  Heatmap ready — best: %s (%d/100)",
            best.name if best else "N/A", best.score if best else 0,
        )
    except Exception as e:
        log.error("Heatmap pre-warm failed: %s", e)


def _job_daily_reset() -> None:
    """Midnight: reset daily drawdown counters in capital shield."""
    log.info("⏰  [00:01] Daily capital shield reset ...")
    try:
        # The shield auto-detects new day on next load.
        # Explicitly reload to reset the in-memory singleton.
        import services.capital_shield as cs
        cs._shield = None
        cs.get_shield()
        log.info("✓  Capital shield daily reset done")
    except Exception as e:
        log.error("Daily reset failed: %s", e)


def start_scheduler() -> None:
    """Start the APScheduler with all registered jobs."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Options chain — 7:00 AM IST daily (Mon-Fri)
    _scheduler.add_job(
        _job_options_chain,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=0, timezone="Asia/Kolkata"),
        id="options_chain",
        name="Options Chain Batch",
        replace_existing=True,
        misfire_grace_time=300,   # allow up to 5 min late
    )

    # Global cues — 8:55 AM IST (before macro, to feed GIFT Nifty into it)
    _scheduler.add_job(
        _job_global_cues,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=55, timezone="Asia/Kolkata"),
        id="global_cues",
        name="Global Cues (GIFT Nifty, USD/INR, Dow, RBI RSS)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Macro context — 9:00 AM IST daily
    _scheduler.add_job(
        _job_macro_context,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone="Asia/Kolkata"),
        id="macro_context",
        name="Macro Context",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # IV snapshot — 9:30 AM IST (after options chain is loaded)
    _scheduler.add_job(
        _job_iv_snapshot,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=30, timezone="Asia/Kolkata"),
        id="iv_snapshot",
        name="Daily ATM IV Snapshot (rolling IV rank)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Heatmap — 9:05 AM IST (5 min after macro to allow VIX to load)
    _scheduler.add_job(
        _job_heatmap_prewarm,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=5, timezone="Asia/Kolkata"),
        id="heatmap_prewarm",
        name="Heatmap Pre-warm",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Daily reset — 00:01 AM IST
    _scheduler.add_job(
        _job_daily_reset,
        CronTrigger(hour=0, minute=1, timezone="Asia/Kolkata"),
        id="daily_reset",
        name="Daily Capital Shield Reset",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("APScheduler started. Jobs: options(7AM), global_cues(8:55AM), macro(9AM), heatmap(9:05AM), iv_snapshot(9:30AM), reset(00:01)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("APScheduler stopped.")