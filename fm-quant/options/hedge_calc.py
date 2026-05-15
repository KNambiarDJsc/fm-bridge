"""
FM Trading Agency — Hedge Calculator
======================================
Per-trade hedge recommendation engine.
Every trade — BULL, BEAR, or HEDGE — gets a computed hedge structure.

Rule: CODE computes the hedge. The LLM selects the strategy TYPE
      (e.g. "protective put" vs "bear put spread"). The code computes
      the exact strike, premium, and P&L impact.

Primary trade → Recommended hedge (from spec §D1):
  BULL Long Futures  → Buy 1 OTM PE (1% below entry)
  BULL Buy CE        → Natural risk limited; add BE Put Spread if swing >3d
  BEAR Short Futures → Buy 1 OTM CE (1% above entry)
  BEAR Buy PE        → Natural risk limited; add CE spread if swing >3d
  HEDGE Iron Condor  → Wings already defined; show adjustment triggers clearly

For HEDGE_TRADE: Iron Condor at Max Pain (or best available if Max Pain unknown)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import HedgePlan, LOT_SIZES, STRIKE_STEP
from options.pricing import price_option, price_iron_condor, iv_from_vix, RISK_FREE_RATE

import logging
log = logging.getLogger("fm.quant.hedge")


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _round_strike(price: float, symbol: str) -> float:
    """Round to nearest valid strike for the index."""
    step = STRIKE_STEP.get(symbol, STRIKE_STEP.get("_default", 50))
    return round(round(price / step) * step, 0)


def _lot_size(symbol: str) -> int:
    return LOT_SIZES.get(symbol, LOT_SIZES.get("_default", 25))


# ════════════════════════════════════════════════════════════════
# BULL TRADE HEDGE — Buy OTM Put
# ════════════════════════════════════════════════════════════════

def hedge_for_bull(
    entry_price: float,
    stop_loss:   float,
    spot:        float,
    dte_days:    float,
    iv:          float,           # decimal
    symbol:      str = "NIFTY 50",
    capital:     float = 1_000_000,
) -> HedgePlan:
    """
    Bull trade hedge: Buy 1 OTM PE ~1% below entry.
    This caps the loss if price gaps below stop.
    """
    lot  = _lot_size(symbol)
    step = STRIKE_STEP.get(symbol, 50)

    # Strike: 1% below spot (or below stop if stop is already nearby)
    hedge_strike = _round_strike(spot * 0.99, symbol)

    opt = price_option(
        flag="p", spot=spot, strike=hedge_strike,
        dte_days=dte_days, iv=iv, r=RISK_FREE_RATE, lot_size=lot,
    )

    # P&L impact analysis
    stop_pts     = abs(entry_price - stop_loss)
    loss_no_hdg  = round(stop_pts * lot, 0)
    # At SL, the PE will be ~0.4–0.6 ITM depending on distance
    itm_pct      = max(0, (hedge_strike - stop_loss) / max(1, hedge_strike)) * 100
    recovery_est = round(max(0, itm_pct * 0.5) * lot, 0)
    loss_hedged  = round(max(0, loss_no_hdg - recovery_est + opt.cost_per_lot), 0)

    cost_pct = round(opt.cost_per_lot / capital * 100, 3) if capital > 0 else 0.0
    pos_cost_pct = round(opt.cost_per_lot / (spot * lot) * 100, 2) if (spot * lot) > 0 else 0.0

    return HedgePlan(
        hedge_type        = "BUY_PE_HEDGE",
        strike            = hedge_strike,
        premium_per_unit  = opt.price,
        premium_per_lot   = opt.cost_per_lot,
        cost_pct_position = pos_cost_pct,
        protection_range  = f"≤ {hedge_strike:.0f} (PE becomes ITM)",
        exit_rule         = (
            f"Exit PE hedge at 80% premium decay (≈₹{round(opt.cost_per_lot * 0.8, 0):.0f}), "
            "or when T1 is hit (no longer needed), or at expiry."
        ),
        disclaimer = (
            f"BSM estimate — IV={iv*100:.1f}%, DTE={dte_days:.0f}d. "
            f"Lot-level cost ₹{opt.cost_per_lot:.0f}. Verify live quote before placing."
        ),
    )


# ════════════════════════════════════════════════════════════════
# BEAR TRADE HEDGE — Buy OTM Call
# ════════════════════════════════════════════════════════════════

def hedge_for_bear(
    entry_price: float,
    stop_loss:   float,
    spot:        float,
    dte_days:    float,
    iv:          float,
    symbol:      str = "NIFTY 50",
    capital:     float = 1_000_000,
) -> HedgePlan:
    """
    Bear trade hedge: Buy 1 OTM CE ~1% above entry.
    Protects against gap-up or short-squeeze.
    """
    lot  = _lot_size(symbol)
    hedge_strike = _round_strike(spot * 1.01, symbol)

    opt = price_option(
        flag="c", spot=spot, strike=hedge_strike,
        dte_days=dte_days, iv=iv, r=RISK_FREE_RATE, lot_size=lot,
    )

    stop_pts    = abs(stop_loss - entry_price)
    loss_no_hdg = round(stop_pts * lot, 0)
    itm_pct     = max(0, (stop_loss - hedge_strike) / max(1, hedge_strike)) * 100
    recovery_est= round(max(0, itm_pct * 0.5) * lot, 0)
    loss_hedged = round(max(0, loss_no_hdg - recovery_est + opt.cost_per_lot), 0)
    cost_pct    = round(opt.cost_per_lot / (spot * lot) * 100, 2) if (spot * lot) > 0 else 0.0

    return HedgePlan(
        hedge_type        = "BUY_CE_HEDGE",
        strike            = hedge_strike,
        premium_per_unit  = opt.price,
        premium_per_lot   = opt.cost_per_lot,
        cost_pct_position = cost_pct,
        protection_range  = f"≥ {hedge_strike:.0f} (CE becomes ITM)",
        exit_rule         = (
            f"Exit CE hedge at 80% premium decay (≈₹{round(opt.cost_per_lot * 0.8, 0):.0f}), "
            "or when T1 (put profit) is realised, or at expiry."
        ),
        disclaimer = (
            f"BSM estimate — IV={iv*100:.1f}%, DTE={dte_days:.0f}d. "
            f"Lot-level cost ₹{opt.cost_per_lot:.0f}. Verify live quote."
        ),
    )


# ════════════════════════════════════════════════════════════════
# HEDGE TRADE — Iron Condor at Max Pain
# ════════════════════════════════════════════════════════════════

def hedge_iron_condor(
    spot:      float,
    max_pain:  Optional[float],
    call_wall: Optional[float],
    put_wall:  Optional[float],
    dte_days:  float,
    iv:        float,
    symbol:    str = "NIFTY 50",
) -> HedgePlan:
    """
    Iron Condor at Max Pain — for HEDGE_TRADE verdict.
    Sell CE near Call Wall, Sell PE near Put Wall.
    Buy wings 2 strikes further out for capital protection.
    """
    lot  = _lot_size(symbol)
    step = STRIKE_STEP.get(symbol, 50)
    anchor = max_pain or spot

    # Sell strikes: 1–2 steps beyond Max Pain (use walls if available)
    sell_ce = _round_strike(
        call_wall if (call_wall and call_wall > anchor) else (anchor + 2 * step),
        symbol
    )
    sell_pe = _round_strike(
        put_wall if (put_wall and put_wall < anchor) else (anchor - 2 * step),
        symbol
    )

    # Buy wings 2 steps beyond sold strikes (defines max loss)
    buy_ce = sell_ce + 2 * step
    buy_pe = sell_pe - 2 * step

    # Ensure ordering
    if sell_pe >= sell_ce or buy_pe >= sell_pe or buy_ce <= sell_ce:
        log.warning("Iron condor strike ordering issue — using default offsets")
        sell_ce = _round_strike(anchor + 2 * step, symbol)
        sell_pe = _round_strike(anchor - 2 * step, symbol)
        buy_ce  = sell_ce + 2 * step
        buy_pe  = sell_pe - 2 * step

    ic = price_iron_condor(
        spot=spot, sell_ce=sell_ce, sell_pe=sell_pe,
        buy_ce=buy_ce, buy_pe=buy_pe,
        dte_days=dte_days, iv=iv, r=RISK_FREE_RATE, lot_size=lot,
    )

    return HedgePlan(
        hedge_type          = "IRON_CONDOR",
        sell_ce             = sell_ce,
        sell_pe             = sell_pe,
        buy_ce              = buy_ce,
        buy_pe              = buy_pe,
        net_credit_per_lot  = ic["net_credit_per_lot"],
        max_loss_per_lot    = ic["max_loss_per_lot"],
        premium_per_lot     = ic["net_credit_per_lot"],  # positive = credit received
        protection_range    = f"Profitable zone: {ic['breakeven_lower']}–{ic['breakeven_upper']}",
        exit_rule           = (
            "Exit at 50% of credit collected. Adjust if price within 1% of sold strikes. "
            f"Adjustment trigger: CE side if price > {sell_ce - step:.0f}, PE side if price < {sell_pe + step:.0f}."
        ),
        disclaimer = ic["disclaimer"],
    )


# ════════════════════════════════════════════════════════════════
# PUBLIC API — compute hedge for any trade
# ════════════════════════════════════════════════════════════════

def compute_hedge(
    verdict:     str,           # "BULL_TRADE" / "BEAR_TRADE" / "HEDGE_TRADE"
    entry_price: float,
    stop_loss:   float,
    spot:        float,
    vix:         Optional[float],
    dte_days:    float,
    symbol:      str    = "NIFTY 50",
    capital:     float  = 1_000_000,
    max_pain:    Optional[float] = None,
    call_wall:   Optional[float] = None,
    put_wall:    Optional[float] = None,
) -> HedgePlan:
    """
    Compute the optimal hedge for any trade verdict.
    This is the single entry point called by fm-agents and the frontend.

    Always returns a HedgePlan.  For WAIT verdict, returns NONE type.
    """
    iv = iv_from_vix(vix)

    if verdict == "BULL_TRADE":
        return hedge_for_bull(
            entry_price=entry_price, stop_loss=stop_loss,
            spot=spot, dte_days=dte_days, iv=iv,
            symbol=symbol, capital=capital,
        )
    elif verdict == "BEAR_TRADE":
        return hedge_for_bear(
            entry_price=entry_price, stop_loss=stop_loss,
            spot=spot, dte_days=dte_days, iv=iv,
            symbol=symbol, capital=capital,
        )
    elif verdict == "HEDGE_TRADE":
        return hedge_iron_condor(
            spot=spot, max_pain=max_pain,
            call_wall=call_wall, put_wall=put_wall,
            dte_days=dte_days, iv=iv, symbol=symbol,
        )
    else:
        return HedgePlan(
            hedge_type = "NONE",
            exit_rule  = "No active trade — no hedge required.",
            disclaimer = "",
        )