"""
FM Trading Agency — Alert Message Formatter
=============================================
Formats every alert type as a clean Telegram HTML message.

Telegram spec:
  - BULL alerts → 🟢
  - BEAR alerts → 🔴
  - HEDGE alerts → 🟣
  - WAIT alerts → 🟡
  - KILL SWITCH → 🚨
  - ENTRY ZONE → 🎯
  - TARGET HIT → ✅ / 💰
  - SL HIT → 🛑
  - HEDGE ADJ → ⚠️

Format: clean, scannable on a phone screen.
Max 4-5 lines per alert — trade plan first, rationale last.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from alerts.models import ActiveTrade


def _ist_now() -> str:
    from pytz import timezone
    return datetime.now(timezone("Asia/Kolkata")).strftime("%I:%M %p IST")


def _verdict_emoji(verdict: str) -> str:
    return {
        "BULL_TRADE":  "🟢",
        "BEAR_TRADE":  "🔴",
        "HEDGE_TRADE": "🟣",
        "WAIT":        "🟡",
    }.get(verdict, "⚪")


def _direction_word(direction: str) -> str:
    return {"LONG": "LONG", "SHORT": "SHORT", "NEUTRAL": "HEDGE"}.get(direction, direction)


def _fmt_price(p: Optional[float]) -> str:
    if p is None: return "—"
    return f"₹{p:,.0f}"


# ═══════════════════════════════════════════════════════════════
# 1. MORNING BRIEFING (9:15 AM)
# ═══════════════════════════════════════════════════════════════

def fmt_morning_briefing(verdict: dict, symbol: str = "NIFTY 50") -> str:
    """
    Format the 9:15 AM morning briefing Telegram message.
    Based on the FinalVerdict dict from fm-agents.

    Example output:
    ━━━━━━━━━━━━━━━━━━━━━━━━
    🟢 FM MORNING BRIEFING
    BULL TRADE — NIFTY 50
    ━━━━━━━━━━━━━━━━━━━━━━━━
    Entry: ₹24,350 – ₹24,400
    SL: ₹24,150 | T1: ₹24,600 | T2: ₹24,850
    R:R 1:2.3 | 1 unit | ATM CE

    🧠 Score: 78/100 | Regime: BULL_TREND
    🛡️ Hedge: Buy 24,000 PE @ ₹950

    📊 8/9 agents bullish
    └ L3 Tech: LONG | L6 OPR: PUT_DOMINANT
    └ Macro: RISK_ON | FII: +₹2,400Cr

    ⏰ 9:15 AM IST — Market Open
    """
    v = verdict
    verdict_type = v.get("verdict", "WAIT")
    emoji = _verdict_emoji(verdict_type)
    direction = v.get("direction", "LONG")
    entry = v.get("entry_zone", {})
    entry_low  = entry.get("low",  v.get("entry_low",  0))
    entry_high = entry.get("high", v.get("entry_high", 0))

    # Score + regime
    score    = v.get("execution_score", v.get("confidence_score", 0))
    regime   = v.get("market_regime", v.get("regime", "—"))
    rationale= v.get("rationale", "")[:120]

    # Trade plan
    sl  = v.get("stop_loss",  0)
    t1  = v.get("target1",    0)
    t2  = v.get("target2",    0)
    rr  = v.get("rr_ratio",   0.0)
    ins = v.get("instrument", "—")
    sz  = v.get("position_sizing", "1 unit")

    # Hedge
    hedge = v.get("hedge_plan", {}) or {}
    hedge_type    = hedge.get("hedge_type", "NONE")
    hedge_strike  = hedge.get("strike", 0)
    hedge_premium = hedge.get("premium", 0)

    # Layer summary
    l1 = v.get("l1_result", {}) or {}
    l3 = v.get("l3_result", {}) or {}
    l6 = v.get("l6_result", {}) or {}
    mc = v.get("macro_context", {}) or {}

    # Agent agreement count
    agent_scores = v.get("layer_scores", {}) or {}
    high_conf = sum(1 for s in agent_scores.values() if isinstance(s, (int, float)) and s >= 65)

    lines = [
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} <b>FM MORNING BRIEFING</b>",
        f"<b>{verdict_type.replace('_', ' ')} — {symbol}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if verdict_type == "WAIT":
        re_trigger = v.get("wait_details", {}).get("re_entry_trigger", "—")
        re_window  = v.get("wait_details", {}).get("re_entry_window_minutes", 30)
        lines += [
            f"🟡 <b>WAIT — Market not ready</b>",
            f"Re-entry: {re_trigger} (within {re_window} min)",
            f"Regime: {regime} | Score: {score}/100",
        ]
    else:
        lines += [
            f"<b>Entry:</b> {_fmt_price(entry_low)} – {_fmt_price(entry_high)}",
            f"<b>SL:</b> {_fmt_price(sl)} | <b>T1:</b> {_fmt_price(t1)} | <b>T2:</b> {_fmt_price(t2)}",
            f"<b>R:R</b> 1:{rr:.1f} | {sz} | {ins}",
            f"",
            f"🧠 <b>Score:</b> {score}/100 | Regime: {regime}",
        ]

        if hedge_type not in ("NONE", "none", "", None) and hedge_strike:
            hedge_emoji = "🛡️" if verdict_type == "BULL_TRADE" else "🛡️"
            lines.append(
                f"{hedge_emoji} <b>Hedge:</b> {hedge_type.replace('_',' ')} "
                f"@ {_fmt_price(hedge_strike)} (₹{hedge_premium:,.0f} premium)"
            )

    # Layer intel
    lines += [
        f"",
        f"📊 <b>{high_conf}/9 agents agree</b>",
    ]

    if l3:
        lines.append(f"└ L3 Tech: {l3.get('direction','—')} | EMA: {l3.get('ema_stack','—')}")
    if l6:
        lines.append(f"└ L6 OPR: {l6.get('options_bias','—')} | {l6.get('best_execution_vehicle','—')}")
    if mc:
        fii = mc.get("fii_net", 0)
        fii_str = f"+₹{fii:,.0f}Cr" if fii >= 0 else f"-₹{abs(fii):,.0f}Cr"
        lines.append(f"└ Macro: {l1.get('risk_context', '—')} | FII: {fii_str}")

    if rationale:
        lines += [f"", f"💬 {rationale}"]

    lines += [f"", f"⏰ {_ist_now()} — Market Open"]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 2. ENTRY ZONE ALERT
# ═══════════════════════════════════════════════════════════════

def fmt_entry_zone(trade: ActiveTrade, current_price: float) -> str:
    emoji = _verdict_emoji(trade.verdict)
    return (
        f"{emoji} <b>ENTRY ZONE REACHED</b>\n"
        f"<b>{trade.symbol}</b> — {trade.verdict.replace('_', ' ')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Current:</b> {_fmt_price(current_price)}\n"
        f"<b>Entry zone:</b> {_fmt_price(trade.entry_low)} – {_fmt_price(trade.entry_high)}\n"
        f"<b>SL:</b> {_fmt_price(trade.stop_loss)} | "
        f"<b>T1:</b> {_fmt_price(trade.target1)} | "
        f"<b>T2:</b> {_fmt_price(trade.target2)}\n"
        f"<b>Instrument:</b> {trade.instrument} | R:R 1:{trade.rr_ratio:.1f}\n"
        f"\n"
        f"⚡ <b>Act now</b> — score {trade.execution_score}/100\n"
        f"⏰ {_ist_now()}"
    )


# ═══════════════════════════════════════════════════════════════
# 3. TARGET HIT ALERTS (T1 / T2)
# ═══════════════════════════════════════════════════════════════

def fmt_target_hit(trade: ActiveTrade, current_price: float, target_num: int) -> str:
    target = trade.target1 if target_num == 1 else trade.target2
    if target_num == 1:
        action = "Exit 50% position here. Trail SL to entry (breakeven)."
    else:
        action = "Exit remaining position. Full target achieved!"

    return (
        f"💰 <b>TARGET {target_num} HIT!</b>\n"
        f"<b>{trade.symbol}</b> — {trade.verdict.replace('_', ' ')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ T{target_num}: {_fmt_price(target)} reached\n"
        f"<b>Current:</b> {_fmt_price(current_price)}\n"
        f"\n"
        f"📋 <b>Action:</b> {action}\n"
        f"⏰ {_ist_now()}"
    )


# ═══════════════════════════════════════════════════════════════
# 4. STOP LOSS HIT
# ═══════════════════════════════════════════════════════════════

def fmt_stop_loss_hit(trade: ActiveTrade, current_price: float) -> str:
    return (
        f"🛑 <b>STOP LOSS HIT</b>\n"
        f"<b>{trade.symbol}</b> — {trade.verdict.replace('_', ' ')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"SL: {_fmt_price(trade.stop_loss)} | Current: {_fmt_price(current_price)}\n"
        f"\n"
        f"📋 <b>Exit ALL positions immediately.</b>\n"
        f"Check hedge leg for any recovery.\n"
        f"⏰ {_ist_now()}"
    )


# ═══════════════════════════════════════════════════════════════
# 5. HEDGE ADJUSTMENT ALERT (Iron Condor short strike breach)
# ═══════════════════════════════════════════════════════════════

def fmt_hedge_adjustment(
    symbol: str,
    current_price: float,
    short_strike: float,
    side: str,          # "CALL" or "PUT"
    pct_away: float,    # % away from short strike
) -> str:
    action_map = {
        "CALL": "Roll short call UP or close the position.",
        "PUT":  "Roll short put DOWN or close the position.",
    }
    action = action_map.get(side, "Adjust the Iron Condor immediately.")
    return (
        f"⚠️ <b>HEDGE ADJUSTMENT REQUIRED</b>\n"
        f"<b>{symbol}</b> — Iron Condor Under Pressure\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Current: {_fmt_price(current_price)}\n"
        f"Short {side}: {_fmt_price(short_strike)} ({pct_away:.2f}% away)\n"
        f"\n"
        f"📋 <b>Action:</b> {action}\n"
        f"⚠️ Risk of max loss if breach continues.\n"
        f"⏰ {_ist_now()}"
    )


# ═══════════════════════════════════════════════════════════════
# 6. KILL SWITCH ALERT (1% daily DD breach)
# ═══════════════════════════════════════════════════════════════

def fmt_kill_switch(
    symbol: str,
    daily_dd_pct: float,
    capital: float,
    dd_limit: float = 1.0,
) -> str:
    loss_amount = capital * daily_dd_pct / 100
    return (
        f"🚨 <b>KILL SWITCH ACTIVATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Daily drawdown: <b>{daily_dd_pct:.2f}%</b> (limit {dd_limit}%)\n"
        f"Loss today: <b>₹{loss_amount:,.0f}</b>\n"
        f"\n"
        f"🛑 <b>STOP ALL TRADING FOR TODAY.</b>\n"
        f"Close all open positions immediately.\n"
        f"No new entries until tomorrow 9:15 AM.\n"
        f"⏰ {_ist_now()}"
    )


# ═══════════════════════════════════════════════════════════════
# 7. RE-ENTRY WINDOW ALERT (WAIT → trigger approaching)
# ═══════════════════════════════════════════════════════════════

def fmt_re_entry_window(
    trade: ActiveTrade,
    current_price: float,
    minutes_elapsed: int,
) -> str:
    return (
        f"🟡 <b>RE-ENTRY WINDOW APPROACHING</b>\n"
        f"<b>{trade.symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Wait window: {minutes_elapsed}/{trade.re_entry_window} min elapsed\n"
        f"Trigger: {trade.re_entry_trigger}\n"
        f"Current price: {_fmt_price(current_price)}\n"
        f"\n"
        f"📋 <b>Watch for trigger. Window closes soon.</b>\n"
        f"⏰ {_ist_now()}"
    )
