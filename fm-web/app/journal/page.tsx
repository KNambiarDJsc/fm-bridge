"use client";

/**
 * FM Trading Agency — Journal & Analytics Page
 * =============================================
 * Pulls from fm-journal :8004 via /api/journal/* proxy.
 *
 * Panels:
 *  1. Weekly P&L vs 2% target (bar chart + pace badge)
 *  2. Agent accuracy scorecard (horizontal bar chart)
 *  3. Time-of-day win rate (bar chart by hour)
 *  4. Drawdown curve (area chart)
 *  5. Verdict type breakdown (BULL/BEAR/HEDGE win rates)
 *  6. Streaks + hedge effectiveness summary tiles
 */

import { useEffect, useState } from "react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, Cell, ReferenceLine,
} from "recharts";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";

// ── Colours matching the design system ────────────────────────
const C = {
    bull: "#0db37a",
    bear: "#f04f4f",
    hedge: "#8b5cf6",
    wait: "#e8a020",
    blue: "#3a9eff",
    bg3: "#101520",
    t2: "#8a9ab5",
    t3: "#48566a",
    border: "#1a2232",
};

// ── Data fetcher ───────────────────────────────────────────────
async function fetchDashboard(capital = 500000) {
    const r = await fetch(`/api/journal/analytics/dashboard?capital=${capital}`);
    if (!r.ok) throw new Error(`Journal unavailable (${r.status})`);
    return r.json();
}

// ── Shared KV tile ─────────────────────────────────────────────
function Tile({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
    return (
        <div className="bg-[#101520] border border-[#1a2232] rounded-lg p-3">
            <div className="font-mono text-[8px] font-bold uppercase tracking-widest text-[#48566a] mb-1">{label}</div>
            <div className="font-mono text-[15px] font-bold leading-none" style={{ color: color || "#ecf0f8" }}>{value}</div>
            {sub && <div className="font-mono text-[9px] text-[#48566a] mt-1">{sub}</div>}
        </div>
    );
}

// ── Section header ─────────────────────────────────────────────
function SectionHead({ title, sub }: { title: string; sub?: string }) {
    return (
        <div className="mb-4">
            <div className="font-mono text-[9px] font-bold uppercase tracking-[2px] text-[#48566a] mb-1">Performance Intelligence</div>
            <div className="text-[17px] font-bold tracking-tight" style={{ fontFamily: "Syne, sans-serif" }}>{title}</div>
            {sub && <div className="font-mono text-[10px] text-[#8a9ab5] mt-1">{sub}</div>}
        </div>
    );
}

const PACE_COLOR: Record<string, string> = {
    EXCEEDED: C.bull,
    ON_TRACK: C.blue,
    BEHIND: C.wait,
    AT_RISK: C.bear,
};

const VERDICT_COLOR: Record<string, string> = {
    BULL_TRADE: C.bull,
    BEAR_TRADE: C.bear,
    HEDGE_TRADE: C.hedge,
    WAIT: C.wait,
};

// ── Tooltip ────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-[#0b0f17] border border-[#1a2232] rounded p-2 text-[10px] font-mono text-[#8a9ab5]">
            <div className="text-[#ecf0f8] font-bold mb-1">{label}</div>
            {payload.map((p: any) => (
                <div key={p.name} style={{ color: p.fill || p.stroke }}>
                    {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
                </div>
            ))}
        </div>
    );
}

export default function JournalPage() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const d = await fetchDashboard();
            setData(d);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    // ── Loading ──────────────────────────────────────────────────
    if (loading) return (
        <div className="min-h-screen bg-[#07090d] flex items-center justify-center">
            <div className="font-mono text-[11px] text-[#48566a] animate-pulse">Loading journal analytics…</div>
        </div>
    );

    // ── Error ────────────────────────────────────────────────────
    if (error) return (
        <div className="min-h-screen bg-[#07090d] flex items-center justify-center">
            <div className="text-center">
                <div className="font-mono text-[11px] text-[#f04f4f] mb-3">{error}</div>
                <div className="font-mono text-[10px] text-[#48566a]">Make sure fm-journal is running on :8004</div>
                <button onClick={load} className="mt-4 font-mono text-[10px] text-[#3a9eff] border border-[#1a2232] rounded px-3 py-1 hover:bg-[#1a2232]">
                    Retry
                </button>
            </div>
        </div>
    );

    // ── Empty state ───────────────────────────────────────────────
    const totalTrades = data?.total_trades ?? 0;
    if (totalTrades === 0) return (
        <div className="min-h-screen bg-[#07090d] flex items-center justify-center flex-col gap-3">
            <div className="font-mono text-[11px] text-[#48566a]">No closed trades yet.</div>
            <div className="font-mono text-[10px] text-[#48566a]">Log trades from the main dashboard once you&apos;ve placed them on Zerodha.</div>
            <Link href="/" className="mt-2 font-mono text-[10px] text-[#3a9eff] underline">← Back to dashboard</Link>
        </div>
    );

    const weekly = data?.weekly ?? [];
    const agents = data?.agent_accuracy ?? [];
    const tod = data?.time_of_day ?? [];
    const drawdowns = data?.drawdowns ?? [];
    const streaks = data?.streaks ?? {};
    const hedge = data?.hedge ?? {};
    const verdicts = data?.verdict_breakdown ?? {};
    const winRate = data?.win_rate ?? 0;
    const netPnl = data?.net_pnl ?? 0;

    // ── Weekly chart data ─────────────────────────────────────────
    const weeklyChartData = weekly.map((w: any) => ({
        label: `W${w.week_start?.slice(5, 10)}`,
        net_pct: parseFloat(w.net_pnl_pct?.toFixed(2) ?? "0"),
        target: 2.0,
        pace: w.pace,
    }));

    // ── Drawdown equity curve ─────────────────────────────────────
    const ddData = drawdowns.map((d: any, i: number) => ({
        name: d.start_date,
        dd: -(d.dd_pct ?? 0),
    }));

    // ── Verdict breakdown ─────────────────────────────────────────
    const verdictData = Object.entries(verdicts).map(([k, v]: any) => ({
        name: k.replace("_TRADE", "").replace("_", " "),
        win_rate: v.win_rate,
        total: v.total,
        color: VERDICT_COLOR[k] || C.blue,
    }));

    return (
        <div className="min-h-screen bg-[#07090d] text-[#ecf0f8]" style={{ fontFamily: "JetBrains Mono, monospace" }}>

            {/* Nav */}
            <nav className="sticky top-0 z-10 bg-[rgba(7,9,13,0.94)] backdrop-blur border-b border-[#1a2232] px-6 h-[44px] flex items-center gap-4">
                <Link href="/" className="flex items-center gap-2 text-[#48566a] hover:text-[#ecf0f8] transition-colors">
                    <ArrowLeft size={13} />
                    <span className="font-mono text-[10px] font-bold">Dashboard</span>
                </Link>
                <span className="text-[#1a2232]">|</span>
                <span className="font-mono text-[10px] font-bold text-[#0db37a] tracking-[2px]">JOURNAL</span>
                <button onClick={load} className="ml-auto text-[#48566a] hover:text-[#ecf0f8] transition-colors">
                    <RefreshCw size={12} />
                </button>
            </nav>

            <div className="max-w-[1200px] mx-auto px-6 py-8 space-y-10">

                {/* ── Overview tiles ────────────────────────────────────── */}
                <div>
                    <SectionHead title="Performance Overview" sub={`${totalTrades} closed trades analysed`} />
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <Tile label="Win Rate" value={`${winRate.toFixed(1)}%`} color={winRate >= 55 ? C.bull : winRate >= 45 ? C.wait : C.bear} />
                        <Tile label="Net P&L" value={`₹${netPnl.toLocaleString("en-IN")}`} color={netPnl >= 0 ? C.bull : C.bear} />
                        <Tile label="Win Streak" value={streaks.current_type === "WIN" ? streaks.current_streak : streaks.max_win_streak} sub="current / max" color={C.bull} />
                        <Tile label="Loss Streak" value={streaks.current_type === "LOSS" ? streaks.current_streak : streaks.max_loss_streak} sub="current / max" color={C.bear} />
                    </div>
                </div>

                {/* ── 1. Weekly P&L vs 2% target ─────────────────────────── */}
                <div>
                    <SectionHead title="Weekly P&L vs 2% Target" sub="Each bar = net P&L% for that week. Red line = 2% target." />
                    {weeklyChartData.length === 0
                        ? <div className="font-mono text-[10px] text-[#48566a]">No weekly data yet</div>
                        : <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={weeklyChartData} barSize={28}>
                                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                                <XAxis dataKey="label" tick={{ fill: C.t3, fontSize: 10, fontFamily: "JetBrains Mono" }} />
                                <YAxis tick={{ fill: C.t3, fontSize: 10, fontFamily: "JetBrains Mono" }} tickFormatter={(v) => `${v}%`} />
                                <Tooltip content={<CustomTooltip />} />
                                <ReferenceLine y={2} stroke={C.bear} strokeDasharray="4 2" label={{ value: "2% target", fill: C.bear, fontSize: 9 }} />
                                <Bar dataKey="net_pct" name="Net P&L%">
                                    {weeklyChartData.map((entry: any, idx: number) => (
                                        <Cell key={idx} fill={entry.net_pct >= 2 ? C.bull : entry.net_pct >= 0 ? C.blue : C.bear} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    }
                    {/* Pace badges */}
                    {weekly.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                            {weekly.slice(-4).map((w: any, i: number) => (
                                <div key={i} className="border rounded px-2 py-1 text-[9px] font-bold"
                                    style={{ borderColor: PACE_COLOR[w.pace] || C.border, color: PACE_COLOR[w.pace] || C.t3 }}>
                                    {w.week_start?.slice(5)} · {w.pace} · {w.net_pnl_pct?.toFixed(2)}%
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ── 2. Agent Accuracy Scorecard ─────────────────────────── */}
                <div>
                    <SectionHead title="Agent Accuracy Scorecard" sub="Which of the 9 layers predicted the right direction most often." />
                    {agents.length === 0
                        ? <div className="font-mono text-[10px] text-[#48566a]">Need 5+ trades to compute agent accuracy</div>
                        : <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={agents} layout="vertical" barSize={16} margin={{ left: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke={C.border} horizontal={false} />
                                <XAxis type="number" domain={[0, 100]} tick={{ fill: C.t3, fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                                <YAxis type="category" dataKey="agent" tick={{ fill: C.t3, fontSize: 11, fontFamily: "JetBrains Mono" }} width={30} />
                                <Tooltip content={<CustomTooltip />} />
                                <Bar dataKey="accuracy" name="Accuracy %">
                                    {agents.map((a: any, i: number) => (
                                        <Cell key={i} fill={a.accuracy >= 70 ? C.bull : a.accuracy >= 55 ? C.blue : C.bear} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    }
                </div>

                {/* ── 3. Time-of-Day Analysis ──────────────────────────────── */}
                <div>
                    <SectionHead title="Time-of-Day Win Rate" sub="Best hours to enter trades based on your trade history." />
                    {tod.length === 0
                        ? <div className="font-mono text-[10px] text-[#48566a]">No hourly data yet</div>
                        : <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={tod.map((h: any) => ({ ...h, label: `${h.hour}:00` }))} barSize={32}>
                                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                                <XAxis dataKey="label" tick={{ fill: C.t3, fontSize: 10 }} />
                                <YAxis domain={[0, 100]} tick={{ fill: C.t3, fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                                <Tooltip content={<CustomTooltip />} />
                                <ReferenceLine y={50} stroke={C.t3} strokeDasharray="3 3" />
                                <Bar dataKey="win_rate" name="Win Rate %">
                                    {tod.map((h: any, i: number) => (
                                        <Cell key={i} fill={h.win_rate >= 60 ? C.bull : h.win_rate >= 45 ? C.blue : C.bear} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    }
                </div>

                {/* ── 4. Drawdown ──────────────────────────────────────────── */}
                <div>
                    <SectionHead title="Drawdown Events" sub="Equity curve drawdown events. Each event = peak to trough." />
                    {ddData.length === 0
                        ? <div className="font-mono text-[10px] text-[#48566a]">No significant drawdown events detected</div>
                        : <ResponsiveContainer width="100%" height={180}>
                            <AreaChart data={ddData}>
                                <defs>
                                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={C.bear} stopOpacity={0.3} />
                                        <stop offset="95%" stopColor={C.bear} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                                <XAxis dataKey="name" tick={{ fill: C.t3, fontSize: 9 }} />
                                <YAxis tick={{ fill: C.t3, fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                                <Tooltip content={<CustomTooltip />} />
                                <Area type="monotone" dataKey="dd" name="Drawdown%" stroke={C.bear} fill="url(#ddGrad)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    }
                </div>

                {/* ── 5. Verdict Breakdown ─────────────────────────────────── */}
                <div>
                    <SectionHead title="Verdict Type Win Rates" sub="How often each verdict type resulted in a win." />
                    {verdictData.length === 0
                        ? <div className="font-mono text-[10px] text-[#48566a]">No verdict breakdown yet</div>
                        : <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {verdictData.map((v: any) => (
                                <div key={v.name} className="bg-[#101520] border border-[#1a2232] rounded-lg p-3">
                                    <div className="font-mono text-[9px] font-bold uppercase tracking-widest mb-2" style={{ color: v.color }}>{v.name}</div>
                                    <div className="font-mono text-[22px] font-bold" style={{ color: v.color }}>{v.win_rate.toFixed(1)}%</div>
                                    <div className="font-mono text-[9px] text-[#48566a] mt-1">{v.total} trades</div>
                                    <div className="mt-2 h-1.5 bg-[#1a2232] rounded-full overflow-hidden">
                                        <div className="h-full rounded-full" style={{ width: `${v.win_rate}%`, backgroundColor: v.color }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    }
                </div>

                {/* ── 6. Hedge + Streaks summary ───────────────────────────── */}
                <div>
                    <SectionHead title="Hedge Effectiveness & Streaks" />
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <Tile label="Hedge Total" value={hedge.total_hedged ?? 0} sub="hedged trades" />
                        <Tile label="Hedge Recovery" value={`${(hedge.avg_recovery_pct ?? 0).toFixed(1)}%`} sub="avg loss recovered" color={hedge.worth_it ? C.bull : C.wait} />
                        <Tile label="Hedge Cost" value={`${(hedge.avg_cost_pct ?? 0).toFixed(2)}%`} sub="avg % of position" color={C.t2} />
                        <Tile label="Worth It?" value={hedge.worth_it ? "YES ✓" : "NO ✗"} color={hedge.worth_it ? C.bull : C.bear} sub="recovery > cost" />
                    </div>
                </div>

            </div>
        </div>
    );
}
