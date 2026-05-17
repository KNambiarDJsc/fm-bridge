"""
FM Trading Agency — Indicator Service
========================================
Computes the full 12+ indicator pack using pandas-ta.
All indicators are vectorized over the OHLCV DataFrame in a single pass.
No manual loops.  Follows VectorBT's "compute everything at once" philosophy.

Multi-timeframe support: fetches 1D/1H/15M/5M bars and computes indicators
for each, returning a MultiTFIndicators object for L3 Technical agent.

Critical rule: These numbers are the GROUND TRUTH.
LLMs in fm-agents MUST NOT compute or re-derive these values.
They READ and INTERPRET them.
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from models import IndicatorPack, MultiTFIndicators

import logging
log = logging.getLogger("fm.indicators")

try:
    import pandas_ta as ta
    _PTA = True
    log.info("pandas-ta loaded [OK]")
except ImportError:
    _PTA = False
    log.warning("pandas-ta not installed — using fallback indicators. Run: pip install pandas-ta")


# ─────────────────────────────────────────────────────────────────
# CORE COMPUTATION
# ─────────────────────────────────────────────────────────────────

def _nan_to_none(v) -> Optional[float]:
    if v is None:
        return None
    try:
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def compute_indicators(
    df: pd.DataFrame,
    symbol: str = "",
    interval: str = "day",
) -> IndicatorPack:
    """
    Compute full indicator pack from an OHLCV DataFrame.

    df must have columns: open, high, low, close, volume (lowercase).
    Returns an IndicatorPack with all fields filled where data is sufficient.
    """
    if df is None or len(df) < 20:
        return IndicatorPack(symbol=symbol, interval=interval, spot=0)

    # Ensure lowercase columns
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    spot = float(df["close"].iloc[-1])
    pack = IndicatorPack(symbol=symbol, interval=interval, spot=spot)

    if _PTA and len(df) >= 50:
        # ── pandas-ta: compute everything in one pass ─────────────
        try:
            df.ta.ema(length=9,   append=True)
            df.ta.ema(length=20,  append=True)
            df.ta.ema(length=50,  append=True)
            df.ta.sma(length=200, append=True)
            df.ta.rsi(length=14,  append=True)
            df.ta.macd(append=True)
            df.ta.atr(length=14,  append=True)
            df.ta.adx(length=14,  append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.stoch(append=True)
            df.ta.cci(length=20,  append=True)
            df.ta.willr(length=14, append=True)
            df.ta.cmf(length=20,  append=True)
            df.ta.obv(append=True)
            # VWAP only on intraday (needs volume and it resets daily)
            if interval in ("5minute", "15minute", "60minute"):
                df.ta.vwap(append=True)
            # Supertrend (ATR-based)
            df.ta.supertrend(length=10, multiplier=3, append=True)

            row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else row

            def g(k: str) -> Optional[float]:
                """Get column value by partial match, return None if missing/NaN."""
                matches = [c for c in df.columns if k.lower() in c.lower()]
                if not matches:
                    return None
                return _nan_to_none(row.get(matches[0]))

            pack.ema9    = g("EMA_9")
            pack.ema20   = g("EMA_20")
            pack.ema50   = g("EMA_50")
            pack.sma200  = g("SMA_200")
            pack.rsi     = g("RSI_14")
            pack.macd    = g("MACD_12_26_9")
            pack.macd_signal = g("MACDs_12_26_9")
            pack.macd_hist   = g("MACDh_12_26_9")
            pack.atr     = g("ATRr_14")
            pack.adx     = g("ADX_14")
            pack.bb_upper = g("BBU_20_2.0")
            pack.bb_lower = g("BBL_20_2.0")
            pack.bb_mid   = g("BBM_20_2.0")
            pack.bb_width = g("BBB_20_2.0")
            pack.stoch_k  = g("STOCHk_14")
            pack.stoch_d  = g("STOCHd_14")
            pack.cci      = g("CCI_20_0.015")
            pack.williams_r = g("WILLR_14")
            pack.cmf      = g("CMF_20")
            pack.vwap     = g("VWAP_D") or g("VWAP")
            pack.computed_by = "pandas-ta"

            # OBV direction
            obv_col = [c for c in df.columns if "OBV" in c.upper()]
            if obv_col and len(df) >= 5:
                obv_now = df[obv_col[0]].iloc[-1]
                obv_5   = df[obv_col[0]].iloc[-5]
                if not (math.isnan(obv_now) or math.isnan(obv_5)):
                    pack.obv_dir = "UP" if obv_now > obv_5 else "DOWN"

            # Supertrend direction
            st_dir_cols = [c for c in df.columns if "SUPERTd" in c]
            if st_dir_cols:
                st_dir = row.get(st_dir_cols[0])
                if not (st_dir is None or (isinstance(st_dir, float) and math.isnan(st_dir))):
                    pack.supertrend_dir = "LONG" if int(st_dir) == 1 else "SHORT"
            st_val_cols = [c for c in df.columns if "SUPERT_" in c and "d" not in c and "l" not in c and "s" not in c]
            if st_val_cols:
                pack.supertrend = _nan_to_none(row.get(st_val_cols[0]))

        except Exception as e:
            log.error("pandas-ta computation error: %s", e)

    else:
        # ── Pure-Python fallback ───────────────────────────────────
        closes  = df["close"].tolist()
        highs   = df["high"].tolist()
        lows    = df["low"].tolist()
        volumes = df["volume"].tolist()

        def _ema(arr, n):
            k = 2 / (n + 1)
            e = arr[0]
            for v in arr[1:]:
                e = v * k + e * (1 - k)
            return e

        if len(closes) >= 9:   pack.ema9   = round(_ema(closes, 9),  2)
        if len(closes) >= 20:  pack.ema20  = round(_ema(closes, 20), 2)
        if len(closes) >= 50:  pack.ema50  = round(_ema(closes, 50), 2)
        if len(closes) >= 200: pack.sma200 = round(sum(closes[-200:]) / 200, 2)

        # RSI (14)
        if len(closes) >= 15:
            gains = losses = 0.0
            for i in range(len(closes) - 14, len(closes)):
                d = closes[i] - closes[i - 1]
                if d > 0: gains += d
                else: losses -= d
            avg_g = gains / 14
            avg_l = losses / 14
            rs = avg_g / avg_l if avg_l > 0 else 99
            pack.rsi = round(100 - 100 / (1 + rs), 1)

        # ATR (14)
        if len(closes) >= 15:
            trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                   for i in range(-14, 0)]
            pack.atr = round(sum(trs) / 14, 2)

        # VWAP (session)
        cum_pv = sum(c * v for c, v in zip(closes, volumes))
        cum_v  = sum(volumes)
        pack.vwap = round(cum_pv / cum_v, 2) if cum_v > 0 else None
        pack.computed_by = "fallback"

    # ── Derived labels ─────────────────────────────────────────────
    _add_derived(pack, spot)
    return pack


def _add_derived(pack: IndicatorPack, spot: float) -> None:
    """Add human-readable labels and derived fields to the pack."""
    # RSI zone
    if pack.rsi is not None:
        if pack.rsi < 30:
            pack.rsi_zone = "OVERSOLD"
        elif pack.rsi > 70:
            pack.rsi_zone = "OVERBOUGHT"
        elif 50 <= pack.rsi <= 65:
            pack.rsi_zone = "SWEET_SPOT"
        else:
            pack.rsi_zone = "NEUTRAL"

    # MACD direction
    if pack.macd is not None and pack.macd_signal is not None:
        pack.macd_dir = "BULL" if pack.macd > pack.macd_signal else "BEAR"

    # ATR %
    if pack.atr is not None and spot > 0:
        pack.atr_pct = round(pack.atr / spot * 100, 2)

    # ADX strength
    if pack.adx is not None:
        if pack.adx > 25:
            pack.adx_strength = "STRONG"
        elif pack.adx > 20:
            pack.adx_strength = "MODERATE"
        else:
            pack.adx_strength = "WEAK"

    # Volume ratio (last bar vs 20-bar avg)
    # NOTE: computed separately when full DataFrame is available

    # EMA stack
    if all(v is not None for v in [pack.ema9, pack.ema20, pack.ema50]):
        if pack.ema9 > pack.ema20 > pack.ema50:
            pack.ema_stack = "BULL"
        elif pack.ema9 < pack.ema20 < pack.ema50:
            pack.ema_stack = "BEAR"
        else:
            pack.ema_stack = "MIXED"


# ─────────────────────────────────────────────────────────────────
# MULTI-TIMEFRAME
# ─────────────────────────────────────────────────────────────────

def compute_multi_tf(
    symbol: str,
    kite,
) -> MultiTFIndicators:
    """
    Fetch bars for 1D / 1H / 15M / 5M and compute indicators for all four.
    Returns MultiTFIndicators with alignment string.
    """
    from config import INSTRUMENT_MAP
    from datetime import datetime, timedelta

    tf_config = [
        ("daily",    "day",       365, 1),
        ("hourly",   "60minute",  60,  1),
        ("intraday", "15minute",  5,   1),
        ("scalp",    "5minute",   3,   1),
    ]

    result = MultiTFIndicators(symbol=symbol)

    for attr, interval, days, _pad in tf_config:
        try:
            token = INSTRUMENT_MAP.get(symbol, 256265)
            to_dt = datetime.now()
            fr_dt = to_dt - timedelta(days=days)
            data  = kite.historical_data(
                instrument_token = token,
                from_date        = fr_dt.strftime("%Y-%m-%d %H:%M:%S"),
                to_date          = to_dt.strftime("%Y-%m-%d %H:%M:%S"),
                interval         = interval,
                continuous       = False,
                oi               = False,
            )
            if not data:
                continue
            df = pd.DataFrame(data)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
            df = df[["open", "high", "low", "close", "volume"]]
            pack = compute_indicators(df, symbol, interval)
            setattr(result, attr, pack)
        except Exception as e:
            log.warning("Multi-TF %s/%s fetch error: %s", symbol, interval, e)

    # ── Alignment detection ────────────────────────────────────────
    result.alignment = _detect_alignment(result)
    return result


def _detect_alignment(mti: MultiTFIndicators) -> str:
    """
    BULL_ALIGNED   — all available TFs have EMA stack BULL or RSI > 50
    BEAR_ALIGNED   — all BEAR or RSI < 50
    MIXED          — conflicting
    INSUFFICIENT   — not enough data
    """
    available = [p for p in [mti.daily, mti.hourly, mti.intraday, mti.scalp] if p is not None]
    if len(available) < 2:
        return "INSUFFICIENT"

    bull_count = sum(1 for p in available if (
        (p.ema_stack == "BULL") or
        (p.rsi is not None and p.rsi > 55)
    ))
    bear_count = sum(1 for p in available if (
        (p.ema_stack == "BEAR") or
        (p.rsi is not None and p.rsi < 45)
    ))
    n = len(available)
    if bull_count >= n - 1: return "BULL_ALIGNED"
    if bear_count >= n - 1: return "BEAR_ALIGNED"
    return "MIXED"