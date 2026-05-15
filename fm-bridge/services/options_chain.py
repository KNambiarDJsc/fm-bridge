"""
FM Trading Agency — Options Chain Service
==========================================
Fetches NSE option chain and computes all derived intelligence
that the AI agents must NEVER compute themselves:

  • PCR (Put/Call OI ratio)
  • Max Pain
  • Call Wall / Put Wall
  • OPR (Options Premium Ratio) — THE institutional sentiment detector
  • Gamma zones (approximate — requires IV data for full calc)
  • ATM IV + IV Percentile

Results are cached for options_chain_ttl seconds (default 900 = 15 min).
APScheduler pre-warms the cache at 7:00 AM IST so it's ready before market open.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import requests

from config import NSE_OC_SYMBOL_MAP, get_settings
from models import OptionsChain, OIStrike

import logging
log = logging.getLogger("fm.options")


# ── In-memory cache ───────────────────────────────────────────────
_cache:    dict[str, OptionsChain] = {}
_cache_ts: dict[str, float]        = {}

# Shared NSE session (cookie-warm once, reuse)
_nse_session: Optional[requests.Session] = None
_nse_session_ts: float = 0
_NSE_SESSION_TTL = 600  # re-warm every 10 min


def _get_nse_session() -> requests.Session:
    global _nse_session, _nse_session_ts
    if _nse_session and (time.time() - _nse_session_ts < _NSE_SESSION_TTL):
        return _nse_session

    s = requests.Session()
    s.headers.update({
        "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer":         "https://www.nseindia.com/option-chain",
        "Connection":      "keep-alive",
    })
    try:
        s.get("https://www.nseindia.com", timeout=6)
        s.get("https://www.nseindia.com/option-chain", timeout=6)
    except Exception as e:
        log.debug("NSE session warm-up error (non-fatal): %s", e)

    _nse_session    = s
    _nse_session_ts = time.time()
    log.debug("NSE session warmed")
    return s


# ─────────────────────────────────────────────────────────────────
# MAX PAIN COMPUTATION
# ─────────────────────────────────────────────────────────────────

def _compute_max_pain(strike_data: dict[float, dict]) -> Optional[float]:
    """
    Max Pain = the strike price at which option writers' total pain is minimised.
    Total pain = sum of (ITM intrinsic value × OI) for all strikes.
    """
    if not strike_data:
        return None
    strikes = sorted(strike_data.keys())
    min_pain  = float("inf")
    max_pain_strike = None
    for candidate in strikes:
        pain = 0.0
        for k, d in strike_data.items():
            # CE writer pain: (candidate - k) if candidate > k
            pain += max(0, candidate - k) * d["ce_oi"]
            # PE writer pain: (k - candidate) if k > candidate
            pain += max(0, k - candidate) * d["pe_oi"]
        if pain < min_pain:
            min_pain       = pain
            max_pain_strike = candidate
    return max_pain_strike


# ─────────────────────────────────────────────────────────────────
# OPR ENGINE (Options Premium Ratio)
# ─────────────────────────────────────────────────────────────────

def _compute_opr(
    rows: list[dict],
    spot: Optional[float],
    nearest_expiry: str,
) -> tuple[Optional[float], str]:
    """
    OPR = Total Put Premium (ATM ±5 strikes) / Total Call Premium

    OPR > 1.2  → PUT_DOMINANT  (more put premium paid = bullish hedging = bullish signal)
    OPR < 0.8  → CALL_DOMINANT (more call premium paid = bearish hedging = bearish signal)
    Else       → NEUTRAL

    Uses last price of near-ATM options to approximate total premium.
    """
    if not spot:
        return None, "NEUTRAL"

    total_call_premium = 0.0
    total_put_premium  = 0.0
    band = 10  # strikes above/below ATM

    for row in rows:
        if row.get("expiryDate") != nearest_expiry:
            continue
        strike = row.get("strikePrice", 0)
        if abs(strike - spot) > band * 50:  # rough ATM band
            continue

        ce = row.get("CE", {})
        pe = row.get("PE", {})
        # OI × last price ≈ total premium paid
        total_call_premium += (ce.get("openInterest", 0) or 0) * (ce.get("lastPrice", 0) or 0)
        total_put_premium  += (pe.get("openInterest", 0) or 0) * (pe.get("lastPrice", 0) or 0)

    if total_call_premium == 0:
        return None, "NEUTRAL"

    opr = round(total_put_premium / total_call_premium, 3)
    if opr > 1.2:
        signal = "PUT_DOMINANT"    # bullish
    elif opr < 0.8:
        signal = "CALL_DOMINANT"   # bearish
    else:
        signal = "NEUTRAL"

    return opr, signal


# ─────────────────────────────────────────────────────────────────
# MAIN FETCH
# ─────────────────────────────────────────────────────────────────

def _analyse_oi_change(
    strike_data: dict[float, dict],
    spot: Optional[float],
    prev_spot: Optional[float],
) -> dict:
    """
    Classify OI change patterns across all strikes.
    Returns summary dict with buildup/unwinding signals.

    Patterns:
      LONG_BUILDUP:   CE OI increasing at strikes above spot = bulls adding
      SHORT_BUILDUP:  PE OI increasing at strikes below spot = bears adding
      LONG_UNWINDING: CE OI decreasing at ATM = bulls exiting
      SHORT_COVERING: PE OI decreasing at ATM = bears exiting
      NEUTRAL:        No dominant pattern
    """
    if not strike_data or not spot:
        return {"pattern": "NEUTRAL", "ce_oi_added": 0, "pe_oi_added": 0, "dominant_side": "NEUTRAL"}

    atm_range = spot * 0.02  # strikes within 2% of spot
    ce_added_atm = 0
    pe_added_atm = 0
    ce_removed_atm = 0
    pe_removed_atm = 0
    total_ce_added = sum(max(0, d["ce_oi_chg"]) for d in strike_data.values())
    total_pe_added = sum(max(0, d["pe_oi_chg"]) for d in strike_data.values())

    for strike, d in strike_data.items():
        if abs(strike - spot) <= atm_range:
            ce_chg = d.get("ce_oi_chg", 0)
            pe_chg = d.get("pe_oi_chg", 0)
            if ce_chg > 0: ce_added_atm += ce_chg
            else:          ce_removed_atm += abs(ce_chg)
            if pe_chg > 0: pe_added_atm += pe_chg
            else:          pe_removed_atm += abs(pe_chg)

    # Determine dominant pattern
    if total_ce_added > total_pe_added * 1.5 and ce_added_atm > 0:
        pattern = "LONG_BUILDUP"
        dominant = "BULLISH"
    elif total_pe_added > total_ce_added * 1.5 and pe_added_atm > 0:
        pattern = "SHORT_BUILDUP"
        dominant = "BEARISH"
    elif ce_removed_atm > ce_added_atm and ce_removed_atm > 0:
        pattern = "LONG_UNWINDING"
        dominant = "BEARISH"
    elif pe_removed_atm > pe_added_atm and pe_removed_atm > 0:
        pattern = "SHORT_COVERING"
        dominant = "BULLISH"
    else:
        pattern = "NEUTRAL"
        dominant = "NEUTRAL"

    return {
        "pattern":       pattern,       # OI pattern type
        "dominant_side": dominant,      # BULLISH / BEARISH / NEUTRAL
        "ce_oi_added":   total_ce_added,
        "pe_oi_added":   total_pe_added,
        "ce_atm_added":  ce_added_atm,
        "pe_atm_added":  pe_added_atm,
        "narrative":     _oi_narrative(pattern, total_ce_added, total_pe_added),
    }


def _oi_narrative(pattern: str, ce_added: int, pe_added: int) -> str:
    """One-line narrative for agents."""
    p = pattern
    if p == "LONG_BUILDUP":
        return f"OI: Long buildup — CE writers adding {ce_added:,} contracts. Bullish new positions."
    elif p == "SHORT_BUILDUP":
        return f"OI: Short buildup — PE writers adding {pe_added:,} contracts. Bearish new positions."
    elif p == "LONG_UNWINDING":
        return "OI: Long unwinding — bulls exiting positions. Bearish signal."
    elif p == "SHORT_COVERING":
        return "OI: Short covering — bears exiting. Rally may be short-lived."
    return "OI: No dominant buildup/unwinding pattern. Mixed positioning."


# ── IV History Storage for Real IV Rank ──────────────────────────
_IV_HISTORY_FILE = None

def _store_iv_snapshot(symbol: str, atm_iv: Optional[float]) -> None:
    """
    Store daily ATM IV snapshot to a JSON file.
    After 30+ days this builds a real IV rank (IVP) instead of using
    fixed bounds IV_52W_LOW=10, IV_52W_HIGH=35.
    """
    if atm_iv is None or atm_iv <= 0:
        return
    try:
        import json
        from pathlib import Path
        from datetime import date as dt_date

        hist_file = Path.home() / ".fm_iv_history.json"
        today_str = dt_date.today().isoformat()

        data: dict = {}
        if hist_file.exists():
            try:
                data = json.loads(hist_file.read_text())
            except Exception:
                data = {}

        if symbol not in data:
            data[symbol] = {}

        data[symbol][today_str] = round(atm_iv, 2)

        # Keep last 365 days only
        sym_data = data[symbol]
        if len(sym_data) > 365:
            sorted_dates = sorted(sym_data.keys())
            for old in sorted_dates[:-365]:
                del sym_data[old]

        hist_file.write_text(json.dumps(data, indent=2))
    except Exception as e:
        log.debug("IV snapshot store failed: %s", e)


def get_iv_rank(symbol: str, current_iv: Optional[float]) -> tuple[Optional[float], Optional[float], str]:
    """
    Compute real IV rank and IV percentile from stored history.
    Returns (iv_rank, iv_percentile, iv_regime).
    Falls back to fixed bounds if < 20 data points.
    """
    if current_iv is None:
        return None, None, "UNKNOWN"
    try:
        import json
        from pathlib import Path
        hist_file = Path.home() / ".fm_iv_history.json"
        if not hist_file.exists():
            return _iv_rank_fallback(current_iv)
        data = json.loads(hist_file.read_text())
        sym_ivs = list(data.get(symbol, {}).values())
        if len(sym_ivs) < 20:
            return _iv_rank_fallback(current_iv)
        iv_min = min(sym_ivs)
        iv_max = max(sym_ivs)
        iv_rank = round((current_iv - iv_min) / (iv_max - iv_min) * 100, 1) if iv_max > iv_min else 50.0
        iv_pct  = round(sum(1 for x in sym_ivs if x < current_iv) / len(sym_ivs) * 100, 1)
        regime  = "CHEAP" if iv_pct < 30 else ("EXPENSIVE" if iv_pct > 70 else "FAIR")
        log.debug("IV rank for %s: rank=%.1f%% pct=%.1f%% (%d days history)", symbol, iv_rank, iv_pct, len(sym_ivs))
        return iv_rank, iv_pct, regime
    except Exception as e:
        log.debug("IV rank computation failed: %s", e)
        return _iv_rank_fallback(current_iv)


def _iv_rank_fallback(iv: float) -> tuple[float, float, str]:
    """Fallback using approximate VIX-based bounds when history < 20 days."""
    IV_MIN, IV_MAX = 10.0, 35.0
    rank = round((iv - IV_MIN) / (IV_MAX - IV_MIN) * 100, 1)
    pct  = rank  # same as rank with linear scale
    regime = "CHEAP" if pct < 30 else ("EXPENSIVE" if pct > 70 else "FAIR")
    return rank, pct, regime


def fetch_options_chain(symbol: str = "NIFTY 50") -> OptionsChain:
    """
    Fetch NSE option chain for one index.
    Returns cached data if < options_chain_ttl seconds old.
    """
    settings = get_settings()
    ttl = settings.cache_ttl_options

    # ── Cache hit ─────────────────────────────────────────────────
    if symbol in _cache and (time.time() - _cache_ts.get(symbol, 0)) < ttl:
        log.debug("Options chain cache hit for %s", symbol)
        return _cache[symbol]

    # ── Map index name to NSE symbol ──────────────────────────────
    nse_sym = NSE_OC_SYMBOL_MAP.get(symbol, "NIFTY")
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={nse_sym}"

    try:
        sess = _get_nse_session()
        resp = sess.get(url, timeout=10)
        if not resp.ok:
            log.error("NSE option chain returned %s for %s", resp.status_code, symbol)
            return OptionsChain(symbol=symbol)
        data = resp.json()
    except Exception as e:
        log.error("Options chain fetch error for %s: %s", symbol, e)
        return OptionsChain(symbol=symbol)

    records = data.get("records", {})
    rows    = records.get("data", [])
    spot    = records.get("underlyingValue")
    expiry_dates  = records.get("expiryDates", [])
    nearest_expiry = expiry_dates[0] if expiry_dates else None

    # ── Aggregate OI by strike (nearest expiry only) ──────────────
    total_ce_oi = 0
    total_pe_oi = 0
    strike_data: dict[float, dict] = {}
    ce_oi_by_strike: dict[float, int] = {}
    pe_oi_by_strike: dict[float, int] = {}
    atm_iv_samples: list[float]  = []

    for row in rows:
        if row.get("expiryDate") != nearest_expiry:
            continue
        strike = float(row.get("strikePrice", 0))
        ce  = row.get("CE", {})
        pe  = row.get("PE", {})
        ce_oi = int(ce.get("openInterest", 0) or 0)
        pe_oi = int(pe.get("openInterest", 0) or 0)
        # ── NEW: OI Change (changeInOpenInterest = today vs yesterday) ──
        ce_oi_chg = int(ce.get("changeInOpenInterest", 0) or 0)
        pe_oi_chg = int(pe.get("changeInOpenInterest", 0) or 0)
        total_ce_oi += ce_oi
        total_pe_oi += pe_oi
        strike_data[strike] = {
            "ce_oi": ce_oi, "pe_oi": pe_oi,
            "ce_oi_chg": ce_oi_chg, "pe_oi_chg": pe_oi_chg,
        }
        ce_oi_by_strike[strike] = ce_oi
        pe_oi_by_strike[strike] = pe_oi

        # ATM IV sample
        if spot and abs(strike - spot) < 200:
            for iv_key in ("impliedVolatility", "iv"):
                ce_iv = ce.get(iv_key)
                pe_iv = pe.get(iv_key)
                if ce_iv and ce_iv > 0:
                    atm_iv_samples.append(float(ce_iv))
                if pe_iv and pe_iv > 0:
                    atm_iv_samples.append(float(pe_iv))

    # ── Derived metrics ───────────────────────────────────────────
    pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else None
    max_pain = _compute_max_pain(strike_data)
    call_wall = max(ce_oi_by_strike, key=ce_oi_by_strike.get) if ce_oi_by_strike else None
    put_wall  = max(pe_oi_by_strike, key=pe_oi_by_strike.get) if pe_oi_by_strike else None
    opr, opr_signal = _compute_opr(rows, spot, nearest_expiry)
    atm_iv = round(sum(atm_iv_samples) / len(atm_iv_samples), 2) if atm_iv_samples else None

    # ── OI Change Buildup Analysis ───────────────────────────────
    # Long Buildup:  price UP + OI UP on CE = bullish new positions
    # Short Buildup: price DOWN + OI UP on PE = bearish new positions
    # Long Unwinding: price DOWN + OI DOWN on CE = bulls exiting
    # Short Covering: price UP + OI DOWN on PE = bears covering
    oi_change_analysis = _analyse_oi_change(strike_data, spot, spot)

    # ── OI map (5 strikes around ATM) ─────────────────────────────
    strikes_sorted = sorted(strike_data.keys())
    oi_map: list[OIStrike] = []
    if spot and strikes_sorted:
        atm = min(strikes_sorted, key=lambda x: abs(x - spot))
        idx = strikes_sorted.index(atm)
        nearby = strikes_sorted[max(0, idx - 5): idx + 6]
        for k in nearby:
            d = strike_data[k]
            oi_map.append(OIStrike(
                strike = k,
                ce_oi  = d["ce_oi"],
                pe_oi  = d["pe_oi"],
            ))

    # ── Expiry info ───────────────────────────────────────────────
    import pytz
    from datetime import date as dt_date
    ist  = pytz.timezone("Asia/Kolkata")
    now  = datetime.now(ist)
    is_expiry_day = now.weekday() == 3  # Thursday
    dte  = 0
    if nearest_expiry:
        try:
            exp_dt = datetime.strptime(nearest_expiry, "%d-%b-%Y")
            dte    = max(0, (exp_dt.date() - now.date()).days)
        except Exception:
            pass

    result = OptionsChain(
        symbol        = symbol,
        spot          = spot,
        expiry        = nearest_expiry,
        pcr           = pcr,
        max_pain      = max_pain,
        call_wall     = call_wall,
        put_wall      = put_wall,
        opr           = opr,
        opr_signal    = opr_signal,
        atm_iv        = atm_iv,
        oi_map        = oi_map,
        total_ce_oi   = total_ce_oi,
        total_pe_oi   = total_pe_oi,
        dte           = dte,
        is_expiry_day = is_expiry_day,
    )
    # Attach OI change analysis as dynamic attribute
    result.__dict__["oi_change"] = oi_change_analysis
    # Store ATM IV snapshot to journal for rolling IV rank
    _store_iv_snapshot(symbol, atm_iv)

    _cache[symbol]    = result
    _cache_ts[symbol] = time.time()
    log.info(
        "Options chain updated for %s: PCR=%.2f, MaxPain=%.0f, OPR=%.2f (%s)",
        symbol, pcr or 0, max_pain or 0, opr or 0, opr_signal,
    )
    return result


def prefetch_all() -> None:
    """Pre-warm cache for all supported indices — called by APScheduler at 7 AM."""
    for sym in NSE_OC_SYMBOL_MAP:
        try:
            fetch_options_chain(sym)
        except Exception as e:
            log.error("Prefetch failed for %s: %s", sym, e)
