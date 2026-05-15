"""
FM Trading Agency — Market Session Engine
==========================================
Indian markets behave differently across sessions.
This engine detects the current session and produces:
  • Session type (OPENING_VOLATILITY / MIDDAY_CHOP / POWER_HOUR etc.)
  • Expiry day detection
  • Days to next Thursday expiry
  • Manipulation risk level (HIGH on expiry morning)
  • Session-based confidence multiplier for L9 Sovereign
  • Recommended action (WAIT_FOR_SETTLE / TRADE / REDUCE_SIZE)

This is deterministic quant logic — NOT GPT.
Referenced by every agent as a context modifier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytz

from models import MarketSession, SessionContext

IST = pytz.timezone("Asia/Kolkata")


def _days_to_thursday() -> int:
    """Days until the next Thursday (NSE weekly expiry)."""
    now = datetime.now(IST)
    dow = now.weekday()    # 0 = Monday, 3 = Thursday
    diff = (3 - dow) % 7
    # If today IS Thursday but market is open → expiry is today (0 days)
    return diff


def _minutes_to_close() -> int:
    """Minutes remaining until market close (15:30 IST)."""
    now = datetime.now(IST)
    close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now >= close:
        return 0
    return max(0, int((close - now).total_seconds() / 60))


def get_session_context() -> SessionContext:
    """
    Detect current market session and return a full SessionContext.
    Called by the bridge at every analysis cycle.
    """
    now     = datetime.now(IST)
    hhmm    = now.strftime("%H:%M")
    hh, mm  = now.hour, now.minute
    t_mins  = hh * 60 + mm   # minutes since midnight

    is_thursday = now.weekday() == 3
    dte         = _days_to_thursday()

    # ── Session detection ─────────────────────────────────────────
    if t_mins < 9 * 60 + 15:
        session  = MarketSession.PRE_OPEN
        action   = "WAIT_FOR_SETTLE"
        vol_bias = "UNKNOWN"
        manip    = "LOW"
        mult     = 0.8

    elif t_mins <= 10 * 60 + 30:
        # 09:15 – 10:30: Opening volatility
        # On expiry day, this window has extreme manipulation risk
        session  = MarketSession.OPENING_VOLATILITY
        if is_thursday and t_mins < 10 * 60:
            session  = MarketSession.EXPIRY_MORNING
            action   = "REDUCE_SIZE"
            vol_bias = "HIGH"
            manip    = "HIGH"
            mult     = 0.6   # very low conviction — max pain manipulation active
        else:
            action   = "WAIT_FOR_SETTLE"
            vol_bias = "HIGH"
            manip    = "MODERATE"
            mult     = 0.75  # reduce conviction during opening chop

    elif t_mins <= 14 * 60:
        # 10:30 – 14:00: Midday chop
        session  = MarketSession.MIDDAY_CHOP
        action   = "TRADE"
        vol_bias = "LOW"
        manip    = "LOW"
        mult     = 1.0   # full conviction, cleanest signals

    elif t_mins <= 15 * 60:
        # 14:00 – 15:00: Power hour
        session  = MarketSession.POWER_HOUR
        action   = "TRADE"
        vol_bias = "MODERATE"
        manip    = "LOW"
        mult     = 1.05  # slightly elevated on momentum continuation

    elif t_mins <= 15 * 60 + 30:
        # 15:00 – 15:30: Closing
        session  = MarketSession.CLOSING
        action   = "REDUCE_SIZE"
        vol_bias = "HIGH"
        manip    = "MODERATE"
        mult     = 0.7   # closing auction effects, reduce new positions

    else:
        # Post close
        session  = MarketSession.POST_CLOSE
        action   = "WAIT_FOR_SETTLE"
        vol_bias = "LOW"
        manip    = "LOW"
        mult     = 0.5

    return SessionContext(
        session                        = session,
        ist_time                       = hhmm,
        is_expiry_day                  = is_thursday,
        days_to_expiry                 = dte,
        minutes_to_close               = _minutes_to_close(),
        volatility_bias                = vol_bias,
        manipulation_risk              = manip,
        recommended_action             = action,
        session_confidence_multiplier  = mult,
    )