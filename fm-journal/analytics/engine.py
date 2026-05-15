"""
FM Trading Agency — Analytics Engine
======================================
Computes all performance intelligence from the trade journal.

7 analytics (all deterministic, no LLM):
  1. Weekly P&L vs 2% target tracker
  2. Agent accuracy scorecard (L1-L9)
  3. Time-of-day win rate analysis
  4. Drawdown analysis + kill switch history
  5. Hedge effectiveness tracker
  6. Verdict type breakdown (BULL/BEAR/HEDGE win rates)
  7. Streak analysis
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from collections import defaultdict
from typing import Optional

from db.models import (
    TradeEntry, TradeOutcome, WeeklySummary, AgentAccuracy,
    HourStats, HedgeEffectiveness, DrawdownEvent,
)
from db.store import get_closed_trades, get_capital_history

log = logging.getLogger("fm.journal.analytics")


# ═══════════════════════════════════════════════════════════════
# 1. WEEKLY TARGET TRACKER (2% weekly target)
# ═══════════════════════════════════════════════════════════════

def compute_weekly_summaries(
    trades: list[TradeEntry] | None = None,
    capital: float = 500_000,
    target_pct: float = 2.0,
) -> list[WeeklySummary]:
    """Group closed trades by ISO week, compute P&L vs 2% target."""
    if trades is None:
        trades = get_closed_trades(limit=1000)

    weeks: dict[tuple, list[TradeEntry]] = defaultdict(list)
    for t in trades:
        if t.outcome == TradeOutcome.PENDING:
            continue
        iso = t.trade_date.isocalendar()
        week_key = (iso.year, iso.week)
        weeks[week_key].append(t)

    summaries = []
    for (yr, wk), wk_trades in sorted(weeks.items()):
        # Week boundaries
        week_start = date.fromisocalendar(yr, wk, 1)
        week_end   = date.fromisocalendar(yr, wk, 5)  # Friday

        wins   = [t for t in wk_trades if t.outcome == TradeOutcome.WIN]
        losses = [t for t in wk_trades if t.outcome == TradeOutcome.LOSS]
        beven  = [t for t in wk_trades if t.outcome == TradeOutcome.BREAKEVEN]

        gross = sum(t.gross_pnl or 0 for t in wk_trades)
        hedge = sum(t.hedge_pnl or 0 for t in wk_trades)
        net   = sum(t.net_pnl   or 0 for t in wk_trades)
        net_pct = (net / capital * 100) if capital > 0 else 0

        total = len(wk_trades)
        wr = (len(wins) / total * 100) if total > 0 else 0

        # Pace
        if net_pct >= target_pct:
            pace = "EXCEEDED"
        elif net_pct >= target_pct * 0.6:
            pace = "ON_TRACK"
        elif net_pct >= 0:
            pace = "BEHIND"
        else:
            pace = "AT_RISK"

        # Intra-week drawdown
        running = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in sorted(wk_trades, key=lambda x: x.created_at):
            running += (t.net_pnl or 0)
            peak = max(peak, running)
            dd = peak - running
            max_dd = max(max_dd, dd)
        max_dd_pct = (max_dd / capital * 100) if capital > 0 else 0

        pnls = [t.net_pnl or 0 for t in wk_trades]
        rrs  = [t.rr_ratio or 0 for t in wk_trades if t.rr_ratio]

        summaries.append(WeeklySummary(
            week_start      = week_start,
            week_end        = week_end,
            total_trades    = total,
            wins            = len(wins),
            losses          = len(losses),
            breakevens      = len(beven),
            win_rate        = round(wr, 1),
            gross_pnl       = round(gross, 2),
            hedge_pnl       = round(hedge, 2),
            net_pnl         = round(net, 2),
            net_pnl_pct     = round(net_pct, 3),
            target_pct      = target_pct,
            pace            = pace,
            max_drawdown_pct= round(max_dd_pct, 3),
            best_trade_pnl  = round(max(pnls, default=0), 2),
            worst_trade_pnl = round(min(pnls, default=0), 2),
            avg_rr_achieved = round(sum(rrs) / len(rrs), 2) if rrs else 0,
        ))

    return summaries


# ═══════════════════════════════════════════════════════════════
# 2. AGENT ACCURACY SCORECARD
# ═══════════════════════════════════════════════════════════════

def compute_agent_accuracy(trades: list[TradeEntry] | None = None) -> list[AgentAccuracy]:
    """For each L1-L9, compute how often a high score correlated with a WIN."""
    if trades is None:
        trades = get_closed_trades(limit=500)

    resolved = [t for t in trades if t.outcome in (TradeOutcome.WIN, TradeOutcome.LOSS)]
    if not resolved:
        return []

    agents = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"]
    results = []

    for agent in agents:
        scores_outcomes = []
        for t in resolved:
            score = t.layer_scores.get(agent)
            if score is None:
                continue
            is_win = 1 if t.outcome == TradeOutcome.WIN else 0
            scores_outcomes.append((score, is_win))

        if not scores_outcomes:
            results.append(AgentAccuracy(agent=agent))
            continue

        total = len(scores_outcomes)
        # "Correct" = score >= 65 and trade won, or score < 65 and trade lost
        correct = sum(
            1 for s, w in scores_outcomes
            if (s >= 65 and w == 1) or (s < 65 and w == 0)
        )
        accuracy = correct / total * 100 if total > 0 else 0
        avg_score = sum(s for s, _ in scores_outcomes) / total

        # Simple correlation: Pearson between score and outcome (0/1)
        corr = 0.0
        if total >= 5:
            ss = [s for s, _ in scores_outcomes]
            ww = [w for _, w in scores_outcomes]
            mean_s = sum(ss) / total
            mean_w = sum(ww) / total
            cov = sum((s - mean_s) * (w - mean_w) for s, w in scores_outcomes) / total
            std_s = (sum((s - mean_s)**2 for s in ss) / total) ** 0.5
            std_w = (sum((w - mean_w)**2 for w in ww) / total) ** 0.5
            if std_s > 0 and std_w > 0:
                corr = cov / (std_s * std_w)

        results.append(AgentAccuracy(
            agent=agent, total=total, correct=correct,
            accuracy=round(accuracy, 1), avg_score=round(avg_score, 1),
            correlation=round(corr, 3),
        ))

    return sorted(results, key=lambda x: x.accuracy, reverse=True)


# ═══════════════════════════════════════════════════════════════
# 3. TIME-OF-DAY ANALYSIS
# ═══════════════════════════════════════════════════════════════

def compute_time_of_day(trades: list[TradeEntry] | None = None) -> list[HourStats]:
    """Win rate and avg P&L by hour of entry (IST)."""
    if trades is None:
        trades = get_closed_trades(limit=500)

    hours: dict[int, list[TradeEntry]] = defaultdict(list)
    for t in trades:
        if t.entry_hour is not None and t.outcome != TradeOutcome.PENDING:
            hours[t.entry_hour].append(t)

    results = []
    for hour in sorted(hours.keys()):
        ht = hours[hour]
        total = len(ht)
        wins   = sum(1 for t in ht if t.outcome == TradeOutcome.WIN)
        losses = sum(1 for t in ht if t.outcome == TradeOutcome.LOSS)
        pnls   = [t.net_pnl or 0 for t in ht]
        results.append(HourStats(
            hour     = hour,
            total    = total,
            wins     = wins,
            losses   = losses,
            win_rate = round(wins / total * 100, 1) if total > 0 else 0,
            avg_pnl  = round(sum(pnls) / total, 2) if total > 0 else 0,
            best_pnl = round(max(pnls, default=0), 2),
            worst_pnl= round(min(pnls, default=0), 2),
        ))

    return results


# ═══════════════════════════════════════════════════════════════
# 4. DRAWDOWN ANALYSIS
# ═══════════════════════════════════════════════════════════════

def compute_drawdowns(
    trades: list[TradeEntry] | None = None,
    capital: float = 500_000,
) -> list[DrawdownEvent]:
    """Identify drawdown events from equity curve."""
    if trades is None:
        trades = get_closed_trades(limit=1000)

    sorted_trades = sorted(
        [t for t in trades if t.outcome != TradeOutcome.PENDING],
        key=lambda x: x.created_at,
    )
    if not sorted_trades:
        return []

    equity = capital
    peak   = capital
    events: list[DrawdownEvent] = []
    current_dd: Optional[DrawdownEvent] = None

    for t in sorted_trades:
        equity += (t.net_pnl or 0)
        if equity > peak:
            peak = equity
            if current_dd and current_dd.dd_pct >= 0.5:
                current_dd.end_date = t.trade_date
                events.append(current_dd)
            current_dd = None
        else:
            dd_pct = (peak - equity) / peak * 100
            if current_dd is None:
                current_dd = DrawdownEvent(
                    start_date   = t.trade_date,
                    peak_capital = round(peak, 2),
                    trough       = round(equity, 2),
                    dd_pct       = round(dd_pct, 3),
                )
            else:
                current_dd.trough = round(min(current_dd.trough, equity), 2)
                current_dd.dd_pct = round(max(current_dd.dd_pct, dd_pct), 3)

    if current_dd and current_dd.dd_pct >= 0.5:
        events.append(current_dd)

    return events


# ═══════════════════════════════════════════════════════════════
# 5. HEDGE EFFECTIVENESS
# ═══════════════════════════════════════════════════════════════

def compute_hedge_effectiveness(trades: list[TradeEntry] | None = None) -> HedgeEffectiveness:
    """Aggregate hedge performance across all trades."""
    if trades is None:
        trades = get_closed_trades(limit=500)

    hedged = [t for t in trades if t.hedge_type != "NONE" and t.outcome != TradeOutcome.PENDING]
    if not hedged:
        return HedgeEffectiveness()

    total_cost     = sum(abs(t.hedge_premium or 0) for t in hedged)
    total_recovery = sum(t.hedge_pnl or 0 for t in hedged)
    positive_count = sum(1 for t in hedged if (t.hedge_pnl or 0) > 0)
    cost_pcts      = [t.hedge_cost_pct or 0 for t in hedged if t.hedge_cost_pct]

    # Recovery ratio = how much of the primary loss was offset by hedge
    recovery_pcts = []
    for t in hedged:
        if (t.gross_pnl or 0) < 0 and (t.hedge_pnl or 0) > 0:
            recovery_pcts.append(abs(t.hedge_pnl) / abs(t.gross_pnl) * 100)

    return HedgeEffectiveness(
        total_hedged         = len(hedged),
        total_hedge_cost     = round(total_cost, 2),
        total_hedge_recovery = round(total_recovery, 2),
        avg_recovery_pct     = round(sum(recovery_pcts) / len(recovery_pcts), 1) if recovery_pcts else 0,
        hedge_positive_count = positive_count,
        avg_cost_pct         = round(sum(cost_pcts) / len(cost_pcts), 2) if cost_pcts else 0,
        worth_it             = total_recovery > total_cost,
    )


# ═══════════════════════════════════════════════════════════════
# 6. VERDICT TYPE BREAKDOWN
# ═══════════════════════════════════════════════════════════════

def compute_verdict_breakdown(trades: list[TradeEntry] | None = None) -> dict:
    """Win rate by verdict type."""
    if trades is None:
        trades = get_closed_trades(limit=500)

    breakdown = {}
    by_verdict = defaultdict(list)
    for t in trades:
        if t.outcome != TradeOutcome.PENDING:
            by_verdict[t.verdict.value].append(t)

    for vt, vt_trades in by_verdict.items():
        total = len(vt_trades)
        wins  = sum(1 for t in vt_trades if t.outcome == TradeOutcome.WIN)
        net   = sum(t.net_pnl or 0 for t in vt_trades)
        breakdown[vt] = {
            "total":    total,
            "wins":     wins,
            "losses":   total - wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "net_pnl":  round(net, 2),
        }

    return breakdown


# ═══════════════════════════════════════════════════════════════
# 7. STREAK ANALYSIS
# ═══════════════════════════════════════════════════════════════

def compute_streaks(trades: list[TradeEntry] | None = None) -> dict:
    """Current and max win/loss streaks."""
    if trades is None:
        trades = get_closed_trades(limit=500)

    resolved = sorted(
        [t for t in trades if t.outcome in (TradeOutcome.WIN, TradeOutcome.LOSS)],
        key=lambda x: x.created_at,
    )
    if not resolved:
        return {"current_streak": 0, "current_type": "NONE", "max_win_streak": 0, "max_loss_streak": 0}

    max_win = max_loss = 0
    cur = 0
    cur_type = ""

    for t in resolved:
        if t.outcome == TradeOutcome.WIN:
            if cur_type == "WIN":
                cur += 1
            else:
                cur = 1
                cur_type = "WIN"
            max_win = max(max_win, cur)
        else:
            if cur_type == "LOSS":
                cur += 1
            else:
                cur = 1
                cur_type = "LOSS"
            max_loss = max(max_loss, cur)

    return {
        "current_streak":  cur,
        "current_type":    cur_type,
        "max_win_streak":  max_win,
        "max_loss_streak": max_loss,
    }


# ═══════════════════════════════════════════════════════════════
# FULL DASHBOARD (all analytics in one call)
# ═══════════════════════════════════════════════════════════════

def compute_full_dashboard(capital: float = 500_000) -> dict:
    """Compute all analytics for the journal dashboard."""
    trades = get_closed_trades(limit=1000)
    log.info("Computing dashboard analytics for %d closed trades", len(trades))

    weekly  = compute_weekly_summaries(trades, capital)
    agents  = compute_agent_accuracy(trades)
    tod     = compute_time_of_day(trades)
    dd      = compute_drawdowns(trades, capital)
    hedge   = compute_hedge_effectiveness(trades)
    verdicts= compute_verdict_breakdown(trades)
    streaks = compute_streaks(trades)

    # Overall stats
    total   = len(trades)
    wins    = sum(1 for t in trades if t.outcome == TradeOutcome.WIN)
    net_pnl = sum(t.net_pnl or 0 for t in trades)

    return {
        "total_trades":    total,
        "win_rate":        round(wins / total * 100, 1) if total > 0 else 0,
        "net_pnl":         round(net_pnl, 2),
        "net_pnl_pct":     round(net_pnl / capital * 100, 3) if capital > 0 else 0,
        "weekly":          [w.model_dump() for w in weekly],
        "agent_accuracy":  [a.model_dump() for a in agents],
        "time_of_day":     [h.model_dump() for h in tod],
        "drawdowns":       [d.model_dump() for d in dd],
        "hedge":           hedge.model_dump(),
        "verdict_breakdown": verdicts,
        "streaks":         streaks,
    }
