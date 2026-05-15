"""
FM Trading Agency — Telegram Notifier
=======================================
Sends all alerts via Telegram Bot API.

Features:
  - HTML-formatted messages
  - Retry with backoff on failures
  - Deduplication: won't re-fire same alert within cooldown period
  - Synchronous send (for use from scheduler threads)
  - Works without python-telegram-bot (falls back to direct HTTP)
"""
from __future__ import annotations

import logging
import time
from typing import Optional
import requests

log = logging.getLogger("fm.alerts.telegram")

# Cooldown tracking: {alert_key → last_fired_ts}
_fired_at: dict[str, float] = {}

# Default cooldown per alert type (seconds)
COOLDOWN = {
    "MORNING_BRIEFING":  3600,   # once per day
    "ENTRY_ZONE":         120,   # 2 min cooldown
    "TARGET_HIT":          60,   # 1 min cooldown
    "STOP_LOSS_HIT":       30,
    "HEDGE_ADJUSTMENT":   180,   # 3 min cooldown
    "KILL_SWITCH":         60,
    "RE_ENTRY_WINDOW":    300,
}


def send_alert(
    message: str,
    token: str,
    chat_id: str,
    alert_key: str = "",
    alert_type: str = "",
    parse_mode: str = "HTML",
    silent: bool = False,
) -> bool:
    """
    Send a Telegram message. Returns True on success.

    alert_key:  unique key for deduplication (e.g. "entry_zone_NIFTY_50")
    alert_type: for cooldown lookup
    silent:     send without notification sound (useful for non-urgent alerts)
    """
    if not token or not chat_id:
        log.warning("Telegram not configured (token or chat_id missing) — skipping")
        return False

    # Deduplication check
    if alert_key:
        cooldown = COOLDOWN.get(alert_type, 60)
        last = _fired_at.get(alert_key, 0)
        if time.time() - last < cooldown:
            log.debug("Alert %s suppressed (cooldown %ds)", alert_key, cooldown)
            return True   # Not an error — just deduplicated

    # Send via Telegram Bot API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id":                  chat_id,
        "text":                     message,
        "parse_mode":               parse_mode,
        "disable_notification":     silent,
        "disable_web_page_preview": True,
    }

    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                if alert_key:
                    _fired_at[alert_key] = time.time()
                log.info("✈ Telegram sent: %s [%.60s...]", alert_type, message.replace("\n", " "))
                return True
            elif r.status_code == 429:
                # Rate limited
                retry_after = int(r.json().get("parameters", {}).get("retry_after", 5))
                log.warning("Telegram rate limit — waiting %ds", retry_after)
                time.sleep(retry_after)
            else:
                log.error("Telegram error %d: %s", r.status_code, r.text[:200])
                break
        except requests.RequestException as e:
            log.error("Telegram request failed (attempt %d): %s", attempt + 1, e)
            time.sleep(2 ** attempt)

    return False


def send_photo_alert(
    caption: str,
    photo_path: str,
    token: str,
    chat_id: str,
) -> bool:
    """Send a photo (e.g. chart screenshot) with caption."""
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            r = requests.post(url, data={"chat_id": chat_id, "caption": caption,
                                          "parse_mode": "HTML"}, files={"photo": f}, timeout=15)
        return r.status_code == 200
    except Exception as e:
        log.error("Photo send failed: %s", e)
        return False
