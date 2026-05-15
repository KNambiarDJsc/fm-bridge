"""
FM Trading Agency — Advanced Options Chain Analysis
=====================================================
The institutional options intelligence layer (document 6, gap 4).

THIS IS YOUR ACTUAL MOAT.

Computes what simple PCR/Max Pain analysis misses:
  • Gamma exposure (GEX) — dealer hedging flow prediction
  • Gamma flip level — above/below changes dealer behaviour
  • OI walls — true support/resistance from options market
  • IV percentile (IVP) — is volatility cheap or expensive vs history?
  • Unusual OI shifts — large institutional positioning changes
  • Expiry gravity — Max Pain pull strength as DTE → 0
  • Dealer positioning approximation (via put-call delta exposure)

All values are passed to L6 Options agent.
L6 READS these — it does NOT recompute them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_local import OptionsChain, OIStrike
from options.pricing import price_option, iv_from_vix

import logging
log = logging.getLogger("fm.quant.chain")


# ════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT
# ════════════════════════════════════════════════════════════════

@dataclass
class ChainIntelligence:
    """
    Full options chain intelligence output.
    Everything the AI agents need — already computed.
    """
    symbol: str = ""

    # ── Basic (re-exported from OptionsChain) ─────────────────────
    pcr:        Optional[float] = None
    max_pain:   Optional[float] = None
    call_wall:  Optional[float] = None
    put_wall:   Optional[float] = None
    opr:        Optional[float] = None
    opr_signal: Optional[str]   = None
    atm_iv:     Optional[float] = None
    dte:        int             = 0
    is_expiry:  bool            = False

    # ── IV Intelligence ───────────────────────────────────────────
    iv_percentile: Optional[float] = None  # 0-100 vs last 52 weeks
    iv_rank:       Optional[float] = None  # (current - min) / (max - min)
    iv_regime:     Optional[str]   = None  # CHEAP / FAIR / EXPENSIVE

    # ── Gamma Exposure (GEX) ──────────────────────────────────────
    # Dealer net GEX: +ve = dealers long gamma (stabilising)
    #                 -ve = dealers short gamma (amplifying moves)
    net_gex:         Optional[float] = None
    gex_per_strike:  dict[float, float] = field(default_factory=dict)  # strike → net GEX
    gamma_flip_level: Optional[float]  = None  # price where GEX changes sign
    dealer_stance:    Optional[str]    = None  # LONG_GAMMA / SHORT_GAMMA / NEUTRAL

    # ── OI Walls (true support/resistance) ────────────────────────
    call_oi_wall:    Optional[float]   = None  # strongest CE OI = resistance
    put_oi_wall:     Optional[float]   = None  # strongest PE OI = support
    call_wall_oi:    int               = 0     # OI quantity at call wall
    put_wall_oi:     int               = 0
    secondary_call_wall: Optional[float] = None
    secondary_put_wall:  Optional[float] = None

    # ── Expiry Gravity ────────────────────────────────────────────
    max_pain_gravity:  Optional[str]   = None  # STRONG / MODERATE / WEAK
    expiry_pin_risk:   Optional[str]   = None  # ACTIVE / INACTIVE
    max_pain_pull_pts: Optional[float] = None  # distance from spot to max pain

    # ── Unusual OI ────────────────────────────────────────────────
    unusual_ce_buildup: list[float] = field(default_factory=list)  # strikes with unusual CE OI
    unusual_pe_buildup: list[float] = field(default_factory=list)

    # ── Summary for AI ────────────────────────────────────────────
    options_bias:   str = "NEUTRAL"   # BULLISH / BEARISH / NEUTRAL
    conviction:     int = 50          # 0-100
    narrative:      str = ""          # 1-sentence summary for L6 agent

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        # Convert dict keys to strings for JSON
        d["gex_per_strike"] = {str(k): round(v, 2) for k, v in d["gex_per_strike"].items()}
        return d


# ════════════════════════════════════════════════════════════════
# GAMMA EXPOSURE COMPUTATION
# ════════════════════════════════════════════════════════════════

def _compute_gex(
    oi_map: list[OIStrike],
    spot:   float,
    dte_days: float,
    iv:     float,
    r:      float = 0.065,
) -> tuple[Optional[float], dict, Optional[float], str]:
    """
    Gamma Exposure (GEX) = OI × gamma × contract_size
    Dealers are assumed:
      • SHORT puts → they buy delta as price falls (amplifying down)
      • LONG calls → they sell delta as price rises (dampening up)

    Net GEX > 0: dealers are net long gamma → they dampen moves (pin-like)
    Net GEX < 0: dealers are net short gamma → they amplify moves (trending)

    Returns (net_gex, gex_by_strike, gamma_flip, dealer_stance)
    """
    if not oi_map or spot <= 0 or dte_days <= 0:
        return None, {}, None, "NEUTRAL"

    gex_by_strike: dict[float, float] = {}
    T = max(0.001, dte_days / 365.0)
    contract_size = 50   # Nifty notional multiplier approximation

    for strike_obj in oi_map:
        k = strike_obj.strike
        ce_oi = strike_obj.ce_oi or 0
        pe_oi = strike_obj.pe_oi or 0

        try:
            c_gamma = _bs_gamma(spot, k, T, r, iv)
            p_gamma = c_gamma   # same gamma for calls and puts at same strike

            # Dealer GEX: dealers hedge CE OI (they sold calls → long gamma)
            # Dealers also hedge PE OI (they sold puts → short gamma below)
            ce_gex = ce_oi * c_gamma * contract_size
            pe_gex = -pe_oi * p_gamma * contract_size   # negative = short gamma

            net_strike_gex = ce_gex + pe_gex
            gex_by_strike[k] = round(net_strike_gex, 2)
        except Exception:
            continue

    if not gex_by_strike:
        return None, {}, None, "NEUTRAL"

    net_gex = sum(gex_by_strike.values())

    # Gamma flip: the price level where net GEX changes sign
    # Approximate: interpolate between the strike with highest and lowest GEX
    strikes = sorted(gex_by_strike.keys())
    gamma_flip = None
    for i in range(len(strikes) - 1):
        g1 = gex_by_strike[strikes[i]]
        g2 = gex_by_strike[strikes[i + 1]]
        if g1 * g2 < 0:   # sign change
            # Linear interpolation
            t = -g1 / (g2 - g1)
            gamma_flip = round(strikes[i] + t * (strikes[i + 1] - strikes[i]), 0)
            break

    if net_gex > 0:
        stance = "LONG_GAMMA"    # dealers stabilise, expect range
    elif net_gex < 0:
        stance = "SHORT_GAMMA"   # dealers amplify, expect trending
    else:
        stance = "NEUTRAL"

    return round(net_gex, 2), gex_by_strike, gamma_flip, stance


def _bs_gamma(S, K, T, r, sigma) -> float:
    """Pure-Python gamma (same formula whether py_vollib available or not)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return math.exp(-0.5 * d1 ** 2) / (S * sigma * math.sqrt(2 * math.pi * T))


# ════════════════════════════════════════════════════════════════
# IV PERCENTILE
# ════════════════════════════════════════════════════════════════

def _compute_iv_percentile(atm_iv: Optional[float]) -> tuple[Optional[float], Optional[float], str]:
    """
    IV Percentile (IVP) and IV Rank.
    Requires historical IV data. Until we have 52-week IV history from the
    bridge (Phase 5), we use India VIX proxy ranges:
      <13 = CHEAP, 13-20 = FAIR, >20 = EXPENSIVE
    Returns (ivp, ivr, regime)
    """
    if atm_iv is None:
        return None, None, "UNKNOWN"

    # Historical range approximation for Nifty ATM IV (2022–2026)
    IV_52W_LOW  = 10.0   # % (VIX low)
    IV_52W_HIGH = 35.0   # % (VIX high)

    iv_pct = atm_iv  # atm_iv is already in percentage from NSE

    ivr = round((iv_pct - IV_52W_LOW) / (IV_52W_HIGH - IV_52W_LOW) * 100, 1)
    ivr = max(0, min(100, ivr))

    # Percentile (simplified — same as rank without actual history)
    ivp = ivr

    if iv_pct < 13:
        regime = "CHEAP"
    elif iv_pct < 20:
        regime = "FAIR"
    else:
        regime = "EXPENSIVE"

    return ivp, ivr, regime


# ════════════════════════════════════════════════════════════════
# OI WALL DETECTION
# ════════════════════════════════════════════════════════════════

def _find_oi_walls(
    oi_map: list[OIStrike],
    spot:   float,
) -> tuple[Optional[float], int, Optional[float], int, Optional[float], Optional[float]]:
    """
    Find primary and secondary OI walls.
    Call Wall: highest CE OI above spot → resistance
    Put Wall:  highest PE OI below spot → support
    Returns: (call_wall, call_oi, put_wall, put_oi, sec_call, sec_pe)
    """
    call_strikes = [(s.strike, s.ce_oi) for s in oi_map if s.strike > spot and s.ce_oi > 0]
    put_strikes  = [(s.strike, s.pe_oi) for s in oi_map if s.strike < spot and s.pe_oi > 0]

    call_wall = put_wall = None
    call_oi = put_oi = 0
    sec_call = sec_put = None

    if call_strikes:
        sorted_ce = sorted(call_strikes, key=lambda x: x[1], reverse=True)
        call_wall, call_oi = sorted_ce[0]
        if len(sorted_ce) > 1:
            sec_call = sorted_ce[1][0]

    if put_strikes:
        sorted_pe = sorted(put_strikes, key=lambda x: x[1], reverse=True)
        put_wall, put_oi = sorted_pe[0]
        if len(sorted_pe) > 1:
            sec_put = sorted_pe[1][0]

    return call_wall, int(call_oi), put_wall, int(put_oi), sec_call, sec_put


# ════════════════════════════════════════════════════════════════
# EXPIRY GRAVITY
# ════════════════════════════════════════════════════════════════

def _expiry_gravity(
    spot:     float,
    max_pain: Optional[float],
    dte:      int,
    total_oi: int,
) -> tuple[str, str, Optional[float]]:
    """
    Max Pain gravity:
    - Stronger as DTE approaches 0
    - Stronger when spot is far from Max Pain
    Returns (gravity_strength, pin_risk, pull_pts)
    """
    if max_pain is None:
        return "WEAK", "INACTIVE", None

    pull_pts = max_pain - spot
    abs_pull = abs(pull_pts)

    # Gravity increases as DTE decreases
    dte_factor = max(0, (7 - dte) / 7)   # 0 at DTE=7, 1 at DTE=0
    distance_factor = min(1.0, abs_pull / 200)   # normalise to 200 pts

    gravity_score = (dte_factor * 0.6 + distance_factor * 0.4) * 100

    if gravity_score > 60:
        gravity = "STRONG"
        pin_risk = "ACTIVE" if dte <= 1 else "MODERATE"
    elif gravity_score > 30:
        gravity = "MODERATE"
        pin_risk = "INACTIVE"
    else:
        gravity = "WEAK"
        pin_risk = "INACTIVE"

    return gravity, pin_risk, round(pull_pts, 0)


# ════════════════════════════════════════════════════════════════
# UNUSUAL OI DETECTION
# ════════════════════════════════════════════════════════════════

def _find_unusual_oi(
    oi_map:      list[OIStrike],
    spot:        float,
    threshold_x: float = 2.0,   # flag if OI > mean × threshold
) -> tuple[list[float], list[float]]:
    """
    Detect unusual OI concentrations — potential institutional positioning.
    Returns (unusual_ce_strikes, unusual_pe_strikes)
    """
    if not oi_map:
        return [], []

    ce_ois = [s.ce_oi for s in oi_map if s.ce_oi > 0]
    pe_ois = [s.pe_oi for s in oi_map if s.pe_oi > 0]

    mean_ce = sum(ce_ois) / len(ce_ois) if ce_ois else 0
    mean_pe = sum(pe_ois) / len(pe_ois) if pe_ois else 0

    unusual_ce = [s.strike for s in oi_map if s.ce_oi > mean_ce * threshold_x]
    unusual_pe = [s.strike for s in oi_map if s.pe_oi > mean_pe * threshold_x]

    return unusual_ce, unusual_pe


# ════════════════════════════════════════════════════════════════
# OPTIONS BIAS SYNTHESIS
# ════════════════════════════════════════════════════════════════

def _synthesise_bias(
    pcr:         Optional[float],
    opr_signal:  Optional[str],
    dealer_stance: Optional[str],
    iv_regime:   Optional[str],
    max_pain_pull: Optional[float],
    spot:        float,
) -> tuple[str, int, str]:
    """
    Synthesise all signals into one options bias + conviction score.
    Returns (bias, conviction_0_100, narrative_sentence)
    """
    bull_score = 0
    notes = []

    # PCR
    if pcr is not None:
        if pcr > 1.3:
            bull_score += 20
            notes.append(f"PCR {pcr:.2f} bullish")
        elif pcr < 0.7:
            bull_score -= 20
            notes.append(f"PCR {pcr:.2f} bearish")

    # OPR
    if opr_signal == "PUT_DOMINANT":
        bull_score += 15
        notes.append("OPR PUT_DOMINANT")
    elif opr_signal == "CALL_DOMINANT":
        bull_score -= 15
        notes.append("OPR CALL_DOMINANT")

    # Dealer stance
    if dealer_stance == "LONG_GAMMA":
        notes.append("dealers LONG_GAMMA — expect range")
    elif dealer_stance == "SHORT_GAMMA":
        notes.append("dealers SHORT_GAMMA — expect trending")

    # IV regime
    if iv_regime == "CHEAP":
        notes.append("IV cheap — option buying favoured")
    elif iv_regime == "EXPENSIVE":
        notes.append("IV expensive — premium selling favoured")

    # Max Pain pull
    if max_pain_pull is not None:
        if max_pain_pull > 100:
            bull_score += 10
            notes.append(f"Max Pain pull UP {abs(max_pain_pull):.0f}pts")
        elif max_pain_pull < -100:
            bull_score -= 10
            notes.append(f"Max Pain pull DOWN {abs(max_pain_pull):.0f}pts")

    # Classify bias
    if bull_score >= 20:
        bias = "BULLISH"
    elif bull_score <= -20:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    conviction = min(95, 50 + abs(bull_score))
    narrative = f"Options flow: {bias} — " + ", ".join(notes[:3]) if notes else f"Options flow: {bias}"

    return bias, conviction, narrative


# ════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════

def analyse_chain(oc: OptionsChain) -> ChainIntelligence:
    """
    Full options chain analysis from an OptionsChain object.
    Returns ChainIntelligence — this is what L6 agent reads.
    """
    spot = oc.spot or 0
    intel = ChainIntelligence(symbol=oc.symbol)

    # Re-export basics
    intel.pcr        = oc.pcr
    intel.max_pain   = oc.max_pain
    intel.call_wall  = oc.call_wall
    intel.put_wall   = oc.put_wall
    intel.opr        = oc.opr
    intel.opr_signal = oc.opr_signal
    intel.atm_iv     = oc.atm_iv
    intel.dte        = oc.dte
    intel.is_expiry  = oc.is_expiry_day

    if not oc.oi_map or spot <= 0:
        intel.narrative = "Insufficient options data for full analysis."
        return intel

    iv = iv_from_vix((oc.atm_iv or 15.0))

    # ── IV Percentile ─────────────────────────────────────────────
    intel.iv_percentile, intel.iv_rank, intel.iv_regime = _compute_iv_percentile(oc.atm_iv)

    # ── Gamma Exposure ────────────────────────────────────────────
    (intel.net_gex,
     intel.gex_per_strike,
     intel.gamma_flip_level,
     intel.dealer_stance) = _compute_gex(oc.oi_map, spot, oc.dte, iv)

    # ── OI Walls ──────────────────────────────────────────────────
    (intel.call_oi_wall,
     intel.call_wall_oi,
     intel.put_oi_wall,
     intel.put_wall_oi,
     intel.secondary_call_wall,
     intel.secondary_put_wall) = _find_oi_walls(oc.oi_map, spot)

    # ── Expiry Gravity ────────────────────────────────────────────
    total_oi = oc.total_ce_oi + oc.total_pe_oi
    (intel.max_pain_gravity,
     intel.expiry_pin_risk,
     intel.max_pain_pull_pts) = _expiry_gravity(spot, oc.max_pain, oc.dte, total_oi)

    # ── Unusual OI ────────────────────────────────────────────────
    intel.unusual_ce_buildup, intel.unusual_pe_buildup = _find_unusual_oi(oc.oi_map, spot)

    # ── Synthesis ─────────────────────────────────────────────────
    (intel.options_bias,
     intel.conviction,
     intel.narrative) = _synthesise_bias(
        oc.pcr, oc.opr_signal, intel.dealer_stance,
        intel.iv_regime, intel.max_pain_pull_pts, spot,
    )

    log.debug(
        "Chain intelligence for %s: %s (conv %d) | GEX %s | IV %s%%  %s",
        oc.symbol, intel.options_bias, intel.conviction,
        intel.dealer_stance, oc.atm_iv, intel.iv_regime,
    )
    return intel
