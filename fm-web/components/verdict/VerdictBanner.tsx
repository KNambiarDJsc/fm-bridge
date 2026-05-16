"use client";

import { cn, VERDICT_COLORS, fmtPrice } from "@/lib/utils";
import type { FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    isAnalyzing?: boolean;
    elapsedSec?: number;
}

const VERDICT_HEX: Record<string, string> = {
    BULL_TRADE:  "#34d399",
    BEAR_TRADE:  "#f87171",
    HEDGE_TRADE: "#a78bfa",
    WAIT:        "#fbbf24",
};

const LABEL: Record<string, string> = {
    BULL_TRADE: "BULL TRADE",
    BEAR_TRADE: "BEAR TRADE",
    HEDGE_TRADE: "HEDGE TRADE",
    WAIT: "WAIT",
};

function WaveBar({ h, i, color }: { h: number; i: number; color: string }) {
    return (
        <div className="w-[2px] rounded-full"
            style={{
                height: `${h}px`, backgroundColor: color, opacity: 0.4,
                animation: `wave${(i % 5) + 1} ${1.1 + i * 0.13}s ease-in-out infinite`,
                animationDelay: `${i * 0.07}s`,
            }} />
    );
}

function ConfRing({ value, color }: { value: number; color: string }) {
    const r = 28;
    const circ = 2 * Math.PI * r;
    const offset = circ - (value / 100) * circ;
    return (
        <div className="relative w-[72px] h-[72px] shrink-0">
            <svg width="72" height="72" className="rotate-[-90deg]">
                <circle cx="36" cy="36" r={r} strokeWidth="3" className="conf-ring-track" />
                <circle cx="36" cy="36" r={r} strokeWidth="3" stroke={color} fill="none"
                    strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
                    className="conf-ring-fill"
                    style={{ filter: `drop-shadow(0 0 3px ${color}40)` }} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-mono text-[18px] font-bold leading-none tabular-nums" style={{ color }}>{value}</span>
                <span className="font-mono text-[9px] text-t3 tracking-widest mt-0.5">CONF</span>
            </div>
        </div>
    );
}

export function VerdictBanner({ verdict, isAnalyzing, elapsedSec = 0 }: Props) {

    // ── Analysing state ──────────────────────────────────
    if (isAnalyzing) {
        return (
            <div className="w-full relative overflow-hidden rounded-xl px-6 py-5"
                style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                {/* Shimmer */}
                <div className="absolute inset-0 pointer-events-none"
                    style={{
                        background: "linear-gradient(90deg, transparent, rgba(96,165,250,0.04), transparent)",
                        animation: "shimmerScan 2.5s ease infinite",
                    }} />
                <div className="relative flex items-center gap-5">
                    {/* Spinner */}
                    <div className="relative w-12 h-12 shrink-0">
                        <svg className="w-12 h-12 animate-spin-slow" viewBox="0 0 48 48">
                            <circle cx="24" cy="24" r="19" strokeWidth="2" fill="none" stroke="rgba(96,165,250,0.1)" />
                            <circle cx="24" cy="24" r="19" strokeWidth="2" fill="none" stroke="var(--blue)"
                                strokeDasharray="80 40" strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="font-mono text-12 font-bold text-[var(--blue)] tabular-nums">{elapsedSec}s</span>
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="type-label mb-1">Running 9-Layer Intelligence Pipeline</div>
                        <div className="type-title text-xl">L1 → L9 Analysis</div>
                        <div className="font-mono text-11 text-t3 mt-1">
                            {elapsedSec < 30
                                ? "Macro → Technical → Options → Strategy → Sovereign"
                                : `Deep processing — up to 90s (${elapsedSec}s elapsed)`}
                        </div>
                    </div>
                    <div className="hidden sm:flex items-center gap-[3px] h-8">
                        {[6, 12, 18, 8, 22, 10, 16, 20, 7, 14].map((h, i) => (
                            <WaveBar key={i} h={h} i={i} color="var(--blue)" />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // ── Empty state ──────────────────────────────────────
    if (!verdict) {
        return (
            <div className="w-full rounded-xl px-6 py-6"
                style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                <div className="type-label mb-2">FM Sovereign v6.0 · Intelligence Ready</div>
                <div className="type-headline text-2xl sm:text-3xl mb-2">
                    Run Analysis to Generate Verdict
                </div>
                <div className="font-mono text-12 text-t3">
                    BULL · BEAR · HEDGE · WAIT — always a plan, never silent
                </div>
            </div>
        );
    }

    // ── Verdict state ────────────────────────────────────
    const vt = verdict.verdict;
    const hex = VERDICT_HEX[vt] ?? "#60a5fa";

    return (
        <div className="w-full relative overflow-hidden rounded-xl verdict-enter"
            style={{
                background: `linear-gradient(135deg, ${hex}08, var(--bg-s) 60%)`,
                border: `1px solid ${hex}20`,
                boxShadow: `0 4px 40px ${hex}10`,
            }}>
            {/* Left accent bar */}
            <div className="absolute left-0 top-0 bottom-0 w-[2px]"
                style={{ background: `linear-gradient(to bottom, ${hex}cc, ${hex}15)` }} />

            <div className="relative px-7 py-5 flex items-center gap-6">
                <div className="flex-1 min-w-0">
                    {/* Eyebrow */}
                    <div className="flex items-center gap-2 flex-wrap mb-2 font-mono text-10 text-t3 tracking-wider">
                        <span>{verdict.best_index}</span>
                        <span className="text-[var(--b)]">·</span>
                        <span style={{ color: `${hex}80` }}>{verdict.regime?.replace(/_/g, " ")}</span>
                        <span className="text-[var(--b)]">·</span>
                        <span>Score {verdict.execution_score}/100</span>
                    </div>

                    {/* Verdict type — the hero */}
                    <div className="type-headline leading-none tracking-tight mb-4"
                        style={{
                            fontSize: "clamp(28px, 4.5vw, 44px)",
                            color: hex,
                        }}>
                        {LABEL[vt]}
                    </div>

                    {/* Trade details */}
                    <TradeDetails verdict={verdict} hex={hex} />
                </div>

                {/* Waveform */}
                <div className="hidden lg:flex items-center gap-[3px] h-10 shrink-0">
                    {[7, 14, 20, 10, 26, 8, 18, 24, 6, 16, 22, 9].map((h, i) => (
                        <WaveBar key={i} h={h} i={i} color={hex} />
                    ))}
                </div>

                {/* Confidence ring */}
                <ConfRing value={verdict.confidence} color={hex} />
            </div>
        </div>
    );
}

function TradeDetails({ verdict, hex }: { verdict: FinalVerdict; hex: string }) {
    const vt = verdict.verdict;

    if (vt === "BULL_TRADE" || vt === "BEAR_TRADE") {
        const tp = verdict.trade_plan;
        if (!tp) return null;
        return (
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
                <Pill label="Entry" value={`${fmtPrice(tp.entry_low)} – ${fmtPrice(tp.entry_high)}`} />
                <Pill label="SL" value={fmtPrice(tp.stop_loss)} color="var(--bear)" />
                <Pill label="T1" value={fmtPrice(tp.target1)} color="var(--bull)" />
                <Pill label="T2" value={fmtPrice(tp.target2)} color="var(--cyan)" />
                <Pill label="R:R" value={`1:${tp.rr.toFixed(1)}`} />
                {tp.instrument && (
                    <span className="font-mono text-11 px-2 py-0.5 rounded"
                        style={{ background: `${hex}08`, border: `1px solid ${hex}18`, color: "var(--t2)" }}>
                        {tp.instrument}
                    </span>
                )}
            </div>
        );
    }

    if (vt === "HEDGE_TRADE") {
        const hp = verdict.hedge_plan;
        if (!hp) return null;
        return (
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
                {hp.hedge_type === "IRON_CONDOR" ? (
                    <>
                        <Pill label="Sell CE" value={fmtPrice(hp.sell_ce)} />
                        <Pill label="Sell PE" value={fmtPrice(hp.sell_pe)} />
                        <Pill label="Credit" value={fmtPrice(hp.net_credit_per_lot)} color="var(--bull)" />
                        <Pill label="MaxLoss" value={fmtPrice(hp.max_loss_per_lot)} color="var(--bear)" />
                    </>
                ) : (
                    <span className="font-mono text-12 text-t2">{hp.protection_range}</span>
                )}
            </div>
        );
    }

    const ws = verdict.wait_signal;
    if (!ws) return null;
    return (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
            <span className="font-mono text-12 text-t2">{ws.reason}</span>
            <Pill label="Re-entry" value={ws.re_entry_trigger} />
            <Pill label="Window" value={`${ws.re_entry_window_minutes}m`} color="var(--wait)" />
        </div>
    );
}

function Pill({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <span className="flex items-center gap-1.5">
            <span className="font-mono text-10 text-t3 tracking-wider">{label}</span>
            <span className="font-mono text-13 font-semibold tabular-nums" style={{ color: color ?? "var(--t1)" }}>
                {value}
            </span>
        </span>
    );
}
