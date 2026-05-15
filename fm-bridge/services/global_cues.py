"""
FM Trading Agency — Global Market Cues Service
================================================
Fetches all global market inputs that L1 Macro needs but didn't have:

  FREE (Yahoo Finance — no API key needed):
    • USD/INR live rate
    • Dow Jones close / change
    • S&P 500 Futures
    • Nasdaq Futures
    • Gold Futures (GC=F)
    • WTI Crude (backup for Brent)

  FREE (Zerodha kite.ltp — already authenticated):
    • GIFT Nifty futures price (NFO:NIFTYIFSC25{MON}FUT)
    • Nifty near-month futures (for premium/discount calc)

  FREE (RBI RSS — public):
    • Live RBI policy announcements (replaces hardcoded stance)
    • MPC meeting headlines

  STATIC (hardcoded calendar, updated yearly):
    • RBI MPC dates, NSE expiry (every Thursday), FOMC, Budget
    • Tells agents what key events are coming in next 7 days

Cached for 15 minutes. Called at 9:00 AM by APScheduler
and on every analysis call if cache is stale.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
import calendar
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
import pytz

import logging
log = logging.getLogger("fm.global_cues")

IST = pytz.timezone("Asia/Kolkata")

# ── Cache ─────────────────────────────────────────────────────────
_cache: Optional["GlobalCues"] = None
_cache_ts: float = 0
_CACHE_TTL = 900  # 15 min


# ════════════════════════════════════════════════════════════════
# OUTPUT DATACLASS
# ════════════════════════════════════════════════════════════════

class GlobalCues:
    """All global market inputs for L1 Macro Sieve."""

    def __init__(self):
        # ── USD/INR ───────────────────────────────────────────────
        self.usd_inr:           Optional[float] = None
        self.inr_weak:          bool            = False   # > 84 = FII selling signal

        # ── GIFT Nifty ────────────────────────────────────────────
        self.gift_nifty:        Optional[float] = None
        self.nifty_spot:        Optional[float] = None
        self.gift_premium:      Optional[float] = None   # GIFT - spot (+ = bullish gap-up)
        self.gift_premium_pct:  Optional[float] = None   # as % of spot

        # ── Global Equity Futures ─────────────────────────────────
        self.dow_last:          Optional[float] = None
        self.dow_change_pct:    Optional[float] = None
        self.sp500_fut:         Optional[float] = None
        self.sp500_change_pct:  Optional[float] = None
        self.nasdaq_fut:        Optional[float] = None
        self.nasdaq_change_pct: Optional[float] = None

        # ── Commodities ───────────────────────────────────────────
        self.gold:              Optional[float] = None
        self.wti_crude:         Optional[float] = None   # WTI backup if Brent fails

        # ── Global Risk Signal ────────────────────────────────────
        self.global_risk:       str             = "NEUTRAL"   # RISK_ON / RISK_OFF / NEUTRAL
        self.global_cue_summary: str            = ""          # 1-line for agent prompt

        # ── RBI Policy ────────────────────────────────────────────
        self.rbi_stance:        str             = "NEUTRAL"   # HAWKISH / NEUTRAL / DOVISH
        self.rbi_latest_headline: Optional[str] = None
        self.rbi_headline_date:   Optional[str] = None

        # ── Event Calendar ────────────────────────────────────────
        self.events_next_7_days: list[dict]     = []   # [{date, event, impact}]
        self.next_expiry:        Optional[str]  = None
        self.days_to_expiry:     int            = 0
        self.is_rbi_week:        bool           = False
        self.is_fomc_week:       bool           = False
        self.is_result_season:   bool           = False

        # ── Meta ──────────────────────────────────────────────────
        self.fetched_at:         str            = datetime.now(IST).isoformat()
        self.data_age_minutes:   float          = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ════════════════════════════════════════════════════════════════
# YAHOO FINANCE FETCHER
# ════════════════════════════════════════════════════════════════

_YF_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def _yf_price(symbol: str) -> tuple[Optional[float], Optional[float]]:
    """Return (price, change_pct) from Yahoo Finance. No API key needed."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
        r = requests.get(url, headers=_YF_HEADERS, timeout=6)
        if r.status_code != 200:
            return None, None
        meta = r.json()["chart"]["result"][0]["meta"]
        price   = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        chg_pct = float(meta.get("regularMarketChangePercent") or 0)
        return (round(price, 2) if price else None, round(chg_pct, 3))
    except Exception as e:
        log.debug("YF %s failed: %s", symbol, e)
        return None, None


def _fetch_global_equities() -> dict:
    """Fetch all global equity/commodity prices in parallel."""
    symbols = {
        "usd_inr":   "USDINR=X",
        "dow":       "^DJI",
        "sp500_fut": "ES=F",
        "nasdaq_fut":"NQ=F",
        "gold":      "GC=F",
        "wti":       "CL=F",
    }
    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_yf_price, sym): key for key, sym in symbols.items()}
        for fut in as_completed(futs, timeout=10):
            key = futs[fut]
            try:
                price, chg = fut.result()
                results[key] = (price, chg)
            except Exception:
                results[key] = (None, None)
    return results


# ════════════════════════════════════════════════════════════════
# GIFT NIFTY VIA ZERODHA
# ════════════════════════════════════════════════════════════════

def _get_gift_nifty_symbol() -> str:
    """
    Returns current near-month GIFT Nifty futures symbol for Zerodha.
    Format: NFO:NIFTYIFSC{YY}{MON}FUT  e.g. NFO:NIFTYIFSC25MAYFUT
    Rolls to next month after 3rd Thursday.
    """
    now  = datetime.now(IST)
    # Find 3rd Thursday of current month
    year, month = now.year, now.month
    thursdays = [
        date(year, month, d)
        for d in range(1, calendar.monthrange(year, month)[1] + 1)
        if date(year, month, d).weekday() == 3  # Thursday
    ]
    third_thursday = thursdays[2] if len(thursdays) >= 3 else thursdays[-1]

    # If past 3rd Thursday, use next month
    if now.date() > third_thursday:
        month = month + 1 if month < 12 else 1
        year  = year + 1 if month == 1 else year

    mon_str = date(year, month, 1).strftime("%b").upper()[:3]   # MAY, JUN, etc.
    yy      = str(year)[-2:]
    return f"NFO:NIFTYIFSC{yy}{mon_str}FUT"


def _fetch_gift_nifty(kite) -> tuple[Optional[float], Optional[float]]:
    """
    Fetch GIFT Nifty and Nifty spot via Zerodha kite.ltp().
    Returns (gift_price, nifty_spot).
    kite is the KiteConnect instance from services/market_data.py.
    """
    if kite is None:
        return None, None
    try:
        gift_sym   = _get_gift_nifty_symbol()
        nifty_sym  = "NSE:NIFTY 50"
        data = kite.ltp([gift_sym, nifty_sym])
        gift  = data.get(gift_sym, {}).get("last_price")
        spot  = data.get(nifty_sym, {}).get("last_price")
        if gift:
            log.debug("GIFT Nifty (%s): %.2f", gift_sym, gift)
        return (
            round(float(gift), 2) if gift else None,
            round(float(spot), 2) if spot else None,
        )
    except Exception as e:
        log.debug("GIFT Nifty fetch failed: %s", e)
        return None, None


# ════════════════════════════════════════════════════════════════
# RBI RSS — LIVE POLICY STANCE
# ════════════════════════════════════════════════════════════════

# RBI RSS feeds (confirmed working)
_RBI_PRESS_RSS = "https://www.rbi.org.in/scripts/RSS.aspx?Id=2"
_RBI_MPC_RSS   = "https://www.rbi.org.in/scripts/RSS.aspx?Id=31"

# Keywords to detect policy stance from headlines
_HAWKISH_KW  = ["rate hike", "increased repo", "tightening", "inflation concern",
                "withdrawal of accommodation", "hawkish", "raise rate"]
_DOVISH_KW   = ["rate cut", "reduced repo", "easing", "accommodative",
                "stimulus", "dovish", "cut rate", "lower rate"]
_NEUTRAL_KW  = ["on hold", "unchanged", "status quo", "neutral stance",
                "pause", "calibrated"]


def _parse_rbi_rss(url: str, max_items: int = 3) -> list[tuple[str, str]]:
    """Parse RBI RSS feed → list of (title, pubDate) tuples."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "")
            pub   = item.findtext("pubDate", "")
            # Decode HTML entities
            title = title.replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"')
            items.append((title.strip(), pub.strip()))
        return items
    except Exception as e:
        log.debug("RBI RSS parse failed (%s): %s", url, e)
        return []


def _detect_rbi_stance(headlines: list[str]) -> str:
    """
    Classify RBI stance from recent headlines.
    Returns HAWKISH / DOVISH / NEUTRAL.
    """
    combined = " ".join(headlines).lower()
    h_score = sum(1 for kw in _HAWKISH_KW if kw in combined)
    d_score = sum(1 for kw in _DOVISH_KW   if kw in combined)
    n_score = sum(1 for kw in _NEUTRAL_KW  if kw in combined)

    if h_score > d_score and h_score > 0:
        return "HAWKISH"
    elif d_score > h_score and d_score > 0:
        return "DOVISH"
    elif n_score > 0 or (h_score == d_score == 0):
        return "NEUTRAL"
    return "NEUTRAL"


def _fetch_rbi_stance() -> tuple[str, Optional[str], Optional[str]]:
    """
    Fetch RBI stance from live RSS. Returns (stance, latest_headline, date).
    Falls back to NEUTRAL if RSS fails.
    """
    all_headlines = []

    # Try MPC feed first (most policy-relevant)
    mpc_items = _parse_rbi_rss(_RBI_MPC_RSS, max_items=3)
    all_headlines += [t for t, _ in mpc_items]

    # Then press releases
    press_items = _parse_rbi_rss(_RBI_PRESS_RSS, max_items=5)
    all_headlines += [t for t, _ in press_items]

    if not all_headlines:
        log.debug("RBI RSS unavailable — using hardcoded NEUTRAL stance")
        return "NEUTRAL", None, None

    stance = _detect_rbi_stance(all_headlines)
    latest_headline = all_headlines[0] if all_headlines else None
    latest_date     = mpc_items[0][1] if mpc_items else (press_items[0][1] if press_items else None)

    log.info("RBI stance from RSS: %s | Latest: %s", stance, (latest_headline or "")[:60])
    return stance, latest_headline, latest_date


# ════════════════════════════════════════════════════════════════
# ECONOMIC EVENT CALENDAR (STATIC — UPDATED YEARLY)
# ════════════════════════════════════════════════════════════════

# RBI MPC meeting dates for FY 2025-26
# Source: rbi.org.in — updated annually
_RBI_MPC_DATES_2025_26 = [
    date(2025, 4,  9),
    date(2025, 6,  6),
    date(2025, 8,  8),
    date(2025, 10, 8),
    date(2025, 12, 5),
    date(2026, 2,  6),
]

# US FOMC meeting dates for 2025-26
_FOMC_DATES = [
    date(2025, 3, 19), date(2025, 5, 7), date(2025, 6, 18),
    date(2025, 7, 30), date(2025, 9, 17), date(2025, 11, 5),
    date(2025, 12, 17), date(2026, 1, 28), date(2026, 3, 18),
    date(2026, 4, 29), date(2026, 6, 17), date(2026, 7, 29),
]

# NSE result seasons (approximate)
_RESULT_SEASONS = [
    (date(2025, 4, 15), date(2025, 5, 31)),   # Q4 FY25
    (date(2025, 7, 15), date(2025, 8, 31)),   # Q1 FY26
    (date(2025, 10, 15), date(2025, 11, 30)), # Q2 FY26
    (date(2026, 1, 15), date(2026, 2, 28)),   # Q3 FY26
    (date(2026, 4, 15), date(2026, 5, 31)),   # Q4 FY26
]

# Key annual events
_ANNUAL_EVENTS = {
    date(2026, 2, 1): ("Union Budget 2026", "VERY_HIGH"),
    date(2025, 2, 1): ("Union Budget 2025", "VERY_HIGH"),
}


def _next_thursday(from_date: date) -> date:
    """Returns the next Thursday (NSE weekly expiry)."""
    days_ahead = 3 - from_date.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def get_upcoming_events(days_ahead: int = 7) -> dict:
    """
    Returns upcoming market-moving events in the next N days.
    Used by L5 Event agent to know what's coming.
    """
    today   = date.today()
    horizon = today + timedelta(days=days_ahead)
    events  = []

    # NSE weekly expiry (every Thursday)
    next_exp = _next_thursday(today)
    if next_exp <= horizon:
        dte = (next_exp - today).days
        events.append({
            "date":   next_exp.isoformat(),
            "event":  "NSE Weekly Expiry (NIFTY/BANKNIFTY)",
            "impact": "HIGH",
            "days_away": dte,
        })

    # RBI MPC
    for d in _RBI_MPC_DATES_2025_26:
        if today <= d <= horizon:
            events.append({
                "date":   d.isoformat(),
                "event":  "RBI MPC Meeting",
                "impact": "VERY_HIGH",
                "days_away": (d - today).days,
            })

    # FOMC
    for d in _FOMC_DATES:
        if today <= d <= horizon:
            events.append({
                "date":   d.isoformat(),
                "event":  "US FOMC Meeting",
                "impact": "HIGH",
                "days_away": (d - today).days,
            })

    # Annual events
    for d, (name, impact) in _ANNUAL_EVENTS.items():
        if today <= d <= horizon:
            events.append({
                "date":    d.isoformat(),
                "event":   name,
                "impact":  impact,
                "days_away": (d - today).days,
            })

    events.sort(key=lambda x: x["days_away"])

    # Derived flags
    next_expiry      = _next_thursday(today)
    days_to_expiry   = (next_expiry - today).days
    is_rbi_week      = any(e["event"] == "RBI MPC Meeting" for e in events)
    is_fomc_week     = any("FOMC" in e["event"] for e in events)
    is_result_season = any(s <= today <= e for s, e in _RESULT_SEASONS)

    return {
        "events_next_7_days": events,
        "next_expiry":        next_expiry.isoformat(),
        "days_to_expiry":     days_to_expiry,
        "is_rbi_week":        is_rbi_week,
        "is_fomc_week":       is_fomc_week,
        "is_result_season":   is_result_season,
    }


# ════════════════════════════════════════════════════════════════
# GLOBAL RISK CLASSIFIER
# ════════════════════════════════════════════════════════════════

def _classify_global_risk(
    dow_chg:     Optional[float],
    nasdaq_chg:  Optional[float],
    sp500_chg:   Optional[float],
    usd_inr:     Optional[float],
    gold:        Optional[float],
) -> tuple[str, str]:
    """
    Classify overnight global risk as RISK_ON / RISK_OFF / NEUTRAL.
    Returns (risk_level, one_line_summary).
    """
    score = 0
    signals = []

    if dow_chg is not None:
        if dow_chg > 0.5:
            score += 2; signals.append(f"Dow +{dow_chg:.1f}%")
        elif dow_chg < -0.5:
            score -= 2; signals.append(f"Dow {dow_chg:.1f}%")

    if nasdaq_chg is not None:
        if nasdaq_chg > 0.5:
            score += 2; signals.append(f"Nasdaq +{nasdaq_chg:.1f}%")
        elif nasdaq_chg < -0.5:
            score -= 2; signals.append(f"Nasdaq {nasdaq_chg:.1f}%")

    if usd_inr is not None:
        if usd_inr > 84.5:
            score -= 1; signals.append(f"INR weak ({usd_inr:.2f})")
        elif usd_inr < 83.0:
            score += 1; signals.append(f"INR strong ({usd_inr:.2f})")

    if score >= 2:
        risk = "RISK_ON"
    elif score <= -2:
        risk = "RISK_OFF"
    else:
        risk = "NEUTRAL"

    summary = f"Global: {risk} | " + " | ".join(signals[:3]) if signals else f"Global: {risk}"
    return risk, summary


# ════════════════════════════════════════════════════════════════
# MAIN PUBLIC API
# ════════════════════════════════════════════════════════════════

def fetch_global_cues(kite=None, force: bool = False) -> GlobalCues:
    """
    Fetch all global market cues. Cached for 15 minutes.
    kite: KiteConnect instance (optional, for GIFT Nifty).
    """
    global _cache, _cache_ts

    if _cache and not force and (time.time() - _cache_ts < _CACHE_TTL):
        _cache.data_age_minutes = round((time.time() - _cache_ts) / 60, 1)
        return _cache

    log.info("Fetching global cues ...")
    cues = GlobalCues()

    # ── 1. Global equities (parallel Yahoo Finance) ───────────────
    eq = _fetch_global_equities()

    usd_inr_p, _         = eq.get("usd_inr",   (None, None))
    dow_p, dow_chg       = eq.get("dow",        (None, None))
    sp_p, sp_chg         = eq.get("sp500_fut",  (None, None))
    nq_p, nq_chg         = eq.get("nasdaq_fut", (None, None))
    gold_p, _            = eq.get("gold",        (None, None))
    wti_p, _             = eq.get("wti",         (None, None))

    cues.usd_inr           = usd_inr_p
    cues.inr_weak          = (usd_inr_p or 0) > 84.0
    cues.dow_last          = dow_p
    cues.dow_change_pct    = dow_chg
    cues.sp500_fut         = sp_p
    cues.sp500_change_pct  = sp_chg
    cues.nasdaq_fut        = nq_p
    cues.nasdaq_change_pct = nq_chg
    cues.gold              = gold_p
    cues.wti_crude         = wti_p

    # ── 2. GIFT Nifty via Zerodha ─────────────────────────────────
    if kite is not None:
        gift, spot = _fetch_gift_nifty(kite)
        cues.gift_nifty = gift
        cues.nifty_spot = spot
        if gift and spot and spot > 0:
            prem = round(gift - spot, 2)
            cues.gift_premium     = prem
            cues.gift_premium_pct = round(prem / spot * 100, 3)
            log.info(
                "GIFT Nifty: %.0f | Spot: %.0f | Premium: %+.0f pts (%+.2f%%)",
                gift, spot, prem, cues.gift_premium_pct,
            )

    # ── 3. Global risk classification ─────────────────────────────
    cues.global_risk, cues.global_cue_summary = _classify_global_risk(
        dow_chg, nq_chg, sp_chg, usd_inr_p, gold_p,
    )

    # ── 4. RBI stance from live RSS ───────────────────────────────
    stance, headline, hdate = _fetch_rbi_stance()
    cues.rbi_stance           = stance
    cues.rbi_latest_headline  = headline
    cues.rbi_headline_date    = hdate

    # ── 5. Event calendar ─────────────────────────────────────────
    cal = get_upcoming_events(days_ahead=7)
    cues.events_next_7_days = cal["events_next_7_days"]
    cues.next_expiry        = cal["next_expiry"]
    cues.days_to_expiry     = cal["days_to_expiry"]
    cues.is_rbi_week        = cal["is_rbi_week"]
    cues.is_fomc_week       = cal["is_fomc_week"]
    cues.is_result_season   = cal["is_result_season"]

    cues.fetched_at = datetime.now(IST).isoformat()
    _cache    = cues
    _cache_ts = time.time()

    log.info(
        "Global cues: USD/INR=%.2f | GIFT=%s | Dow%+.1f%% | Nasdaq%+.1f%% | RBI=%s | %s",
        usd_inr_p or 0,
        f"{cues.gift_nifty:.0f}" if cues.gift_nifty else "N/A",
        dow_chg or 0, nq_chg or 0,
        stance, cues.global_risk,
    )
    return cues


def get_cached_cues() -> Optional[GlobalCues]:
    return _cache
