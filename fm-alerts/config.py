"""
FM Trading Agency — Alerts Config
====================================
All settings loaded from .env file.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class AlertSettings(BaseSettings):

    # ── Service URLs ───────────────────────────────────────────
    bridge_url:  str = "http://localhost:8002"
    agents_url:  str = "http://localhost:8003"
    journal_url: str = "http://localhost:8004"

    # ── Telegram ───────────────────────────────────────────────
    telegram_token:   str = ""          # BotFather token
    telegram_chat_id: str = ""          # Your personal chat id

    # ── Email (Resend — optional fallback) ─────────────────────
    resend_api_key:   str = ""
    email_from:       str = "alerts@fmtradingagency.com"
    email_to:         str = ""

    # ── Trading Config ─────────────────────────────────────────
    default_symbol:   str   = "NIFTY 50"
    capital:          float = 500_000
    daily_dd_limit:   float = 1.0       # % — kill switch threshold
    weekly_target:    float = 2.0       # % — weekly P&L target

    # ── Price Monitor ──────────────────────────────────────────
    price_poll_secs:  int   = 5         # how often to poll bridge for LTP
    entry_zone_buffer: float = 0.001    # 0.1% either side of entry

    # ── Iron Condor Hedge Monitor ──────────────────────────────
    ic_breach_pct:    float = 1.0       # alert when within 1% of short strike

    # ── Morning Briefing ───────────────────────────────────────
    briefing_hour:    int   = 9
    briefing_minute:  int   = 15
    briefing_tz:      str   = "Asia/Kolkata"

    class Config:
        env_file = ".env"
        extra    = "ignore"


@lru_cache
def get_settings() -> AlertSettings:
    return AlertSettings()
