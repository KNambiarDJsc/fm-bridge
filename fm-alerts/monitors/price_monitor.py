"""
FM Trading Agency — Price Monitor
====================================
Watches live prices from fm-bridge and fires alerts when:

  1. Price enters entry zone     → ENTRY_ZONE alert
  2. Price reaches T1            → TARGET_HIT alert (exit 50%, trail SL)
  3. Price reaches T2            → TARGET_HIT alert (full exit)
  4. Price hits stop loss        → STOP_LOSS_HIT alert
  5. Iron Condor: price within
     1% of short call/put        → HEDGE_ADJUSTMENT alert
  6. Daily DD >= 1%              → KILL_SWITCH alert

Poll interval: configurable (default 5 seconds).
Uses the kill switch from fm-bridge /api/capital-shield.
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Optional

import requests

from alerts.models import ActiveTrade, Alert, AlertType, AlertPriority
from alerts.formatter import (
    fmt_entry_zone, fmt_target_hit, fmt_stop_loss_hit,
    fmt_hedge_adjustment, fmt_kill_switch,
)
from notifiers.telegram import send_alert
from config import get_settings

log = logging.getLogger("fm.alerts.price_monitor")


class PriceMonitor:
    """
    Continuously polls fm-bridge for live price and fires alerts.
    Runs in a background thread.
    """

    def __init__(self):
        self._settings       = get_settings()
        self._active_trade:  Optional[ActiveTrade] = None
        self._running        = False
        self._thread:        Optional[threading.Thread] = None
        self._last_price:    float = 0.0
        self._lock           = threading.Lock()

    # ── Trade State ────────────────────────────────────────────

    def update_trade(self, trade: ActiveTrade) -> None:
        """Call this when a new FinalVerdict arrives — updates the watched plan."""
        with self._lock:
            self._active_trade = trade
            log.info("Price monitor watching: %s %s entry=[%s-%s] SL=%s",
                     trade.symbol, trade.verdict,
                     trade.entry_low, trade.entry_high, trade.stop_loss)

    def clear_trade(self) -> None:
        """Call when position is fully closed."""
        with self._lock:
            self._active_trade = None
        log.info("Price monitor: trade cleared")

    # ── Start / Stop ───────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="price-monitor")
        self._thread.start()
        log.info("Price monitor started (poll every %ds)", self._settings.price_poll_secs)

    def stop(self) -> None:
        self._running = False
        log.info("Price monitor stopped")

    # ── Main Loop ──────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as e:
                log.error("Price monitor tick error: %s", e)
            time.sleep(self._settings.price_poll_secs)

    def _tick(self) -> None:
        s = self._settings

        # Fetch current price from bridge
        price = self._get_ltp()
        if price is None:
            return
        self._last_price = price

        # Check capital shield / kill switch first
        self._check_kill_switch()

        with self._lock:
            trade = self._active_trade

        if trade is None or not trade.verdict:
            return

        # Don't monitor WAIT verdicts (no price levels to watch)
        if trade.verdict == "WAIT":
            return

        # ── Entry Zone ────────────────────────────────────────
        if not trade.entry_alert_fired:
            buf = s.entry_zone_buffer
            lo  = trade.entry_low  * (1 - buf)
            hi  = trade.entry_high * (1 + buf)
            if lo <= price <= hi:
                self._fire_alert(
                    alert_type = AlertType.ENTRY_ZONE,
                    priority   = AlertPriority.HIGH,
                    trade      = trade,
                    message    = fmt_entry_zone(trade, price),
                    alert_key  = f"entry_{trade.symbol}",
                )
                with self._lock:
                    if self._active_trade:
                        self._active_trade.entry_alert_fired = True

        # ── Target 1 ──────────────────────────────────────────
        if not trade.t1_alert_fired and trade.target1 > 0:
            hit_t1 = (
                (trade.direction == "LONG"  and price >= trade.target1) or
                (trade.direction == "SHORT" and price <= trade.target1)
            )
            if hit_t1:
                self._fire_alert(
                    alert_type = AlertType.TARGET_HIT,
                    priority   = AlertPriority.HIGH,
                    trade      = trade,
                    message    = fmt_target_hit(trade, price, 1),
                    alert_key  = f"t1_{trade.symbol}",
                )
                with self._lock:
                    if self._active_trade:
                        self._active_trade.t1_alert_fired = True

        # ── Target 2 ──────────────────────────────────────────
        if not trade.t2_alert_fired and trade.target2 > 0:
            hit_t2 = (
                (trade.direction == "LONG"  and price >= trade.target2) or
                (trade.direction == "SHORT" and price <= trade.target2)
            )
            if hit_t2:
                self._fire_alert(
                    alert_type = AlertType.TARGET_HIT,
                    priority   = AlertPriority.HIGH,
                    trade      = trade,
                    message    = fmt_target_hit(trade, price, 2),
                    alert_key  = f"t2_{trade.symbol}",
                )
                with self._lock:
                    if self._active_trade:
                        self._active_trade.t2_alert_fired = True

        # ── Stop Loss ─────────────────────────────────────────
        if not trade.sl_alert_fired and trade.stop_loss > 0:
            hit_sl = (
                (trade.direction == "LONG"  and price <= trade.stop_loss) or
                (trade.direction == "SHORT" and price >= trade.stop_loss)
            )
            if hit_sl:
                self._fire_alert(
                    alert_type = AlertType.STOP_LOSS_HIT,
                    priority   = AlertPriority.CRITICAL,
                    trade      = trade,
                    message    = fmt_stop_loss_hit(trade, price),
                    alert_key  = f"sl_{trade.symbol}",
                )
                with self._lock:
                    if self._active_trade:
                        self._active_trade.sl_alert_fired = True

        # ── Iron Condor Hedge Adjustment ──────────────────────
        if not trade.hedge_alert_fired:
            ic_breach_pct = s.ic_breach_pct / 100
            alerts_fired  = False

            if trade.ic_short_call and price > 0:
                pct_away = (trade.ic_short_call - price) / trade.ic_short_call
                if 0 <= pct_away <= ic_breach_pct:
                    self._fire_alert(
                        alert_type = AlertType.HEDGE_ADJUSTMENT,
                        priority   = AlertPriority.HIGH,
                        trade      = trade,
                        message    = fmt_hedge_adjustment(
                            trade.symbol, price, trade.ic_short_call,
                            "CALL", pct_away * 100
                        ),
                        alert_key  = f"ic_call_{trade.symbol}",
                    )
                    alerts_fired = True

            if trade.ic_short_put and price > 0:
                pct_away = (price - trade.ic_short_put) / trade.ic_short_put
                if 0 <= pct_away <= ic_breach_pct:
                    self._fire_alert(
                        alert_type = AlertType.HEDGE_ADJUSTMENT,
                        priority   = AlertPriority.HIGH,
                        trade      = trade,
                        message    = fmt_hedge_adjustment(
                            trade.symbol, price, trade.ic_short_put,
                            "PUT", pct_away * 100
                        ),
                        alert_key  = f"ic_put_{trade.symbol}",
                    )
                    alerts_fired = True

            if alerts_fired:
                with self._lock:
                    if self._active_trade:
                        self._active_trade.hedge_alert_fired = True

    # ── Kill Switch ────────────────────────────────────────────

    def _check_kill_switch(self) -> None:
        s = self._settings
        try:
            r = requests.get(f"{s.bridge_url}/api/capital-shield", timeout=3)
            if r.status_code != 200:
                return
            data = r.json()
            kill     = data.get("kill_switch", False)
            dd_pct   = data.get("daily_dd_pct", 0.0)
            if kill or dd_pct >= s.daily_dd_limit:
                msg = fmt_kill_switch(
                    s.default_symbol, dd_pct, s.capital, s.daily_dd_limit
                )
                send_alert(
                    message    = msg,
                    token      = s.telegram_token,
                    chat_id    = s.telegram_chat_id,
                    alert_key  = "kill_switch_today",
                    alert_type = "KILL_SWITCH",
                )
        except Exception as e:
            log.debug("Kill switch check failed: %s", e)

    # ── Bridge LTP ─────────────────────────────────────────────

    def _get_ltp(self) -> Optional[float]:
        s = self._settings
        with self._lock:
            symbol = self._active_trade.symbol if self._active_trade else s.default_symbol
        try:
            r = requests.get(
                f"{s.bridge_url}/api/ltp",
                params={"symbol": symbol},
                timeout=4,
            )
            if r.status_code == 200:
                data = r.json()
                # Bridge may return {"ltp": 24350} or {"data": {"ltp": 24350}}
                return float(
                    data.get("ltp") or
                    (data.get("data") or {}).get("ltp") or 0
                )
        except Exception as e:
            log.debug("LTP fetch failed: %s", e)
        return None

    # ── Internal Fire ─────────────────────────────────────────

    def _fire_alert(
        self,
        alert_type: AlertType,
        priority:   AlertPriority,
        trade:      ActiveTrade,
        message:    str,
        alert_key:  str,
    ) -> None:
        s = self._settings
        log.info("🔔 Alert: %s for %s", alert_type.value, trade.symbol)
        send_alert(
            message    = message,
            token      = s.telegram_token,
            chat_id    = s.telegram_chat_id,
            alert_key  = alert_key,
            alert_type = alert_type.value,
            silent     = (priority == AlertPriority.LOW),
        )

    @property
    def last_price(self) -> float:
        return self._last_price

    @property
    def active_trade(self) -> Optional[ActiveTrade]:
        with self._lock:
            return self._active_trade
