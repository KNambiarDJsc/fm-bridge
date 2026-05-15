"""
FM Trading Agency — Macro Context Service
==========================================
Auto-fetches and caches macro inputs that feed L1 Macro Sieve.

Fetched at 9:00 AM IST by APScheduler:
  • Brent crude oil price
  • FII / DII net flows (Rs Cr) — from NSE
  • India VIX
  • RBI stance (static, updated quarterly)
  • DII/FII ratio → Domestic Floor detection

All values are cached for 1 hour.  Frontend shows
"data age X min" when stale so trader knows to refresh.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import requests

from models import MacroContext

import logging
log = logging.getLogger("fm.macro")

# ── In-memory cache ───────────────────────────────────────────────
_cache: Optional[MacroContext] = None
_cache_ts: float = 0

# ── RBI stance is now live from RSS (services/global_cues.py) ────
# Kept as fallback in case RSS fails
_RBI_STANCE_FALLBACK = "NEUTRAL"


# ─────────────────────────────────────────────────────────────────
# BRENT OIL
# ─────────────────────────────────────────────────────────────────

def _fetch_brent_oil() -> Optional[float]:
    """
    Fetch Brent crude via free public endpoints.
    Tries commodities-api.com equivalent → fallback to Exchange Rate host.
    """
    # Option 1: Yahoo Finance via unofficial JSON
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?range=1d&interval=1d"
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            meta = r.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            if price and price > 0:
                log.debug("Brent oil from Yahoo: $%.2f", price)
                return round(float(price), 2)
    except Exception as e:
        log.debug("Yahoo oil fetch failed: %s", e)

    # Option 2: Exchange Rate API (free, no key)
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=5,
        )
        # This doesn't give oil but confirms connectivity
    except Exception:
        pass

    log.warning("Brent oil price unavailable — manual entry required")
    return None


# ─────────────────────────────────────────────────────────────────
# FII / DII FLOWS
# ─────────────────────────────────────────────────────────────────

def _fetch_fii_dii() -> tuple[Optional[float], Optional[float]]:
    """
    Fetch FII and DII net flows from NSE.
    Returns (fii_net_rs_cr, dii_net_rs_cr).
    """
    try:
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36",
            "Referer": "https://www.nseindia.com",
        })
        sess.get("https://www.nseindia.com", timeout=5)

        r = sess.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            timeout=8,
        )
        if not r.ok:
            return None, None

        data = r.json()
        # NSE returns list; find today's or most recent entry
        if isinstance(data, list) and data:
            today = data[0]  # most recent
            fii_buy  = float(today.get("fiiBuy",  0) or 0)
            fii_sell = float(today.get("fiiSell", 0) or 0)
            dii_buy  = float(today.get("diiBuy",  0) or 0)
            dii_sell = float(today.get("diiSell", 0) or 0)
            fii_net  = round(fii_buy - fii_sell, 2)
            dii_net  = round(dii_buy - dii_sell, 2)
            log.info("FII net: ₹%.0fCr  DII net: ₹%.0fCr", fii_net, dii_net)
            return fii_net, dii_net
    except Exception as e:
        log.warning("FII/DII fetch failed: %s", e)

    return None, None


# ─────────────────────────────────────────────────────────────────
# RISK CONTEXT CLASSIFIER
# ─────────────────────────────────────────────────────────────────

def _classify_risk(
    oil:     Optional[float],
    fii_net: Optional[float],
    vix:     Optional[float],
) -> str:
    """
    Deterministic risk context classification.
    RISK_ON / RISK_OFF / TRANSITION
    This is quant logic — NOT GPT.
    """
    score = 50  # neutral baseline

    if oil is not None:
        if oil > 100:    score -= 25   # oil shock = risk-off
        elif oil < 80:   score += 10   # cheap oil = mildly bullish

    if fii_net is not None:
        if fii_net > 2000:   score += 15   # heavy FII buying
        elif fii_net > 500:  score += 8
        elif fii_net < -2000:score -= 15
        elif fii_net < -500: score -= 8

    if vix is not None:
        if vix > 25:     score -= 20   # stressed market
        elif vix > 20:   score -= 10
        elif vix < 13:   score += 10   # calm market

    if score >= 60:
        return "RISK_ON"
    elif score <= 40:
        return "RISK_OFF"
    else:
        return "TRANSITION"


def _macro_score(
    oil: Optional[float],
    fii_net: Optional[float],
    dii_net: Optional[float],
    vix: Optional[float],
) -> int:
    """0–100 macro health score. 100 = perfect RISK_ON conditions."""
    score = 50
    if oil is not None:
        if oil > 100:   score -= 20
        elif oil < 80:  score += 10
    if fii_net is not None:
        if fii_net > 2000: score += 15
        elif fii_net > 500:score += 8
        elif fii_net < -2000: score -= 15
        elif fii_net < -500:  score -= 8
    if dii_net is not None:
        if dii_net > 2000: score += 10
        elif dii_net > 500:score += 5
    if vix is not None:
        if vix < 13:  score += 10
        elif vix > 25: score -= 15
        elif vix > 20: score -= 8
    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────

def _classify_risk_enhanced(
    oil: Optional[float],
    fii_net: Optional[float],
    vix: Optional[float],
    dow_chg: Optional[float] = None,
    nasdaq_chg: Optional[float] = None,
    usd_inr: Optional[float] = None,
) -> str:
    """Enhanced risk context using global cues too."""
    score = 50
    if oil is not None:
        if oil > 100:  score -= 25
        elif oil < 80: score += 10
    if fii_net is not None:
        if fii_net > 2000:  score += 15
        elif fii_net > 500: score += 8
        elif fii_net < -2000: score -= 15
        elif fii_net < -500:  score -= 8
    if vix is not None:
        if vix > 25:   score -= 20
        elif vix > 20: score -= 10
        elif vix < 13: score += 10
    # NEW: global inputs
    if dow_chg is not None:
        if dow_chg > 0.5: score += 8
        elif dow_chg < -0.5: score -= 8
    if nasdaq_chg is not None:
        if nasdaq_chg > 0.5: score += 5
        elif nasdaq_chg < -0.5: score -= 5
    if usd_inr is not None:
        if usd_inr > 84.5: score -= 5   # INR weakness = FII outflow pressure
        elif usd_inr < 83:  score += 5
    if score >= 60: return "RISK_ON"
    elif score <= 40: return "RISK_OFF"
    return "TRANSITION"


def _macro_score_enhanced(
    oil: Optional[float],
    fii_net: Optional[float],
    dii_net: Optional[float],
    vix: Optional[float],
    dow_chg: Optional[float] = None,
    usd_inr: Optional[float] = None,
) -> int:
    """Enhanced 0-100 macro score with global inputs."""
    score = 50
    if oil is not None:
        if oil > 100:  score -= 20
        elif oil < 80: score += 10
    if fii_net is not None:
        if fii_net > 2000: score += 15
        elif fii_net > 500: score += 8
        elif fii_net < -2000: score -= 15
        elif fii_net < -500:  score -= 8
    if dii_net is not None:
        if dii_net > 2000: score += 10
        elif dii_net > 500: score += 5
    if vix is not None:
        if vix < 13:  score += 10
        elif vix > 25: score -= 15
        elif vix > 20: score -= 8
    if dow_chg is not None:
        if dow_chg > 0.5: score += 8
        elif dow_chg < -0.5: score -= 8
    if usd_inr is not None:
        if usd_inr > 84.5: score -= 5
        elif usd_inr < 83: score += 3
    return max(0, min(100, score))


def fetch_macro_context(force: bool = False, kite=None) -> MacroContext:
    """
    Fetch and cache macro context.
    Cached for 1 hour.  force=True bypasses cache (APScheduler call).
    kite: KiteConnect instance for GIFT Nifty (optional).

    Now integrates:
      - Global market cues (USD/INR, GIFT Nifty, Dow, Nasdaq) via global_cues.py
      - Live RBI stance from RSS (no longer hardcoded)
      - Event calendar (RBI MPC dates, FOMC, expiry)
      - OI change data is handled in options_chain.py
    """
    from config import get_settings
    settings = get_settings()
    ttl = settings.cache_ttl_macro

    global _cache, _cache_ts
    if _cache and not force and (time.time() - _cache_ts < ttl):
        age_min = (time.time() - _cache_ts) / 60
        _cache.data_age_minutes = round(age_min, 1)
        return _cache

    log.info("Fetching macro context ...")

    # ── Existing fetches ──────────────────────────────────────────
    oil              = _fetch_brent_oil()
    fii_net, dii_net = _fetch_fii_dii()

    from services.market_data import get_vix, _kite as _default_kite
    vix_reading = get_vix()
    vix = vix_reading.vix

    # Use provided kite or fall back to bridge singleton
    _kite_inst = kite or _default_kite

    # ── NEW: Global cues (parallel fetch) ─────────────────────────
    try:
        from services.global_cues import fetch_global_cues
        gcues = fetch_global_cues(kite=_kite_inst, force=force)
    except Exception as e:
        log.warning("Global cues fetch failed: %s", e)
        gcues = None

    # Extract global cue values
    usd_inr     = gcues.usd_inr     if gcues else None
    gift_nifty  = gcues.gift_nifty  if gcues else None
    gift_prem   = gcues.gift_premium if gcues else None
    gift_prem_pct = gcues.gift_premium_pct if gcues else None
    dow_chg     = gcues.dow_change_pct    if gcues else None
    nasdaq_chg  = gcues.nasdaq_change_pct if gcues else None
    global_risk = gcues.global_risk       if gcues else "NEUTRAL"
    rbi_stance  = gcues.rbi_stance        if gcues else _RBI_STANCE_FALLBACK
    rbi_headline= gcues.rbi_latest_headline if gcues else None
    events      = gcues.events_next_7_days  if gcues else []
    next_expiry = gcues.next_expiry         if gcues else None
    dte         = gcues.days_to_expiry      if gcues else 0
    is_rbi_week = gcues.is_rbi_week         if gcues else False
    is_fomc_week= gcues.is_fomc_week        if gcues else False
    is_result_season = gcues.is_result_season if gcues else False

    # ── Derived values ────────────────────────────────────────────
    oil_shock = oil is not None and oil > 100
    dii_fii_ratio = (
        round(abs(dii_net) / abs(fii_net), 2)
        if fii_net and fii_net != 0 and dii_net is not None
        else None
    )
    domestic_floor = (
        dii_fii_ratio is not None
        and dii_fii_ratio >= 1.5
        and fii_net is not None
        and fii_net < 0
    )

    vix_regime = None
    if vix is not None:
        if vix < 13:   vix_regime = "CALM"
        elif vix < 20: vix_regime = "NORMAL"
        else:          vix_regime = "STRESSED"

    # Enhanced risk context combines domestic + global
    risk_ctx  = _classify_risk_enhanced(oil, fii_net, vix, dow_chg, nasdaq_chg, usd_inr)
    macro_scr = _macro_score_enhanced(oil, fii_net, dii_net, vix, dow_chg, usd_inr)

    ctx = MacroContext(
        brent_oil             = oil,
        oil_shock_active      = oil_shock,
        fii_net               = fii_net,
        dii_net               = dii_net,
        dii_fii_ratio         = dii_fii_ratio,
        domestic_floor_active = domestic_floor,
        rbi_stance            = rbi_stance,
        india_vix             = vix,
        vix_regime            = vix_regime,
        inr_usd               = usd_inr,
        risk_context          = risk_ctx,
        macro_score           = macro_scr,
        # New fields — stored in extra dict for agents
        data_age_minutes      = 0.0,
    )
    # Attach extra fields as dynamic attrs (agents read via mc.get())
    ctx.__dict__["gift_nifty"]         = gift_nifty
    ctx.__dict__["gift_premium"]       = gift_prem
    ctx.__dict__["gift_premium_pct"]   = gift_prem_pct
    ctx.__dict__["dow_change_pct"]     = dow_chg
    ctx.__dict__["nasdaq_change_pct"]  = nasdaq_chg
    ctx.__dict__["global_risk"]        = global_risk
    ctx.__dict__["rbi_latest_headline"]= rbi_headline
    ctx.__dict__["events_next_7_days"] = events
    ctx.__dict__["next_expiry"]        = next_expiry
    ctx.__dict__["days_to_expiry"]     = dte
    ctx.__dict__["is_rbi_week"]        = is_rbi_week
    ctx.__dict__["is_fomc_week"]       = is_fomc_week
    ctx.__dict__["is_result_season"]   = is_result_season

    _cache    = ctx
    _cache_ts = time.time()
    log.info(
        "Macro: oil=$%.0f FII=₹%.0fCr VIX=%.1f USD/INR=%.2f GIFT=%s Dow%+.1f%% → %s (score %d)",
        oil or 0, fii_net or 0, vix or 0, usd_inr or 0,
        f"{gift_nifty:.0f}" if gift_nifty else "N/A",
        dow_chg or 0, risk_ctx, macro_scr,
    )
    return ctx


def get_cached_macro() -> Optional[MacroContext]:
    return _cache
