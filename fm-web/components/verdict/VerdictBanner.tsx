"use client";

import { cn, VERDICT_COLORS, fmtPrice } from "@/lib/utils";
import type { FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    isAnalyzing?: boolean;
    elapsedSec?: number;
}

function WaveBar({ h, i, color }: { h: number; i: number; color: string }) {
    return (
        <div
            className="w-[3px] rounded-full"
            style={{
                height: `${h}px`,
                backgroundColor: color,
                opacity: 0.5,
                animation: `wave${(i % 5) + 1} ${1.1 + i * 0.13}s ease-in-out infinite`,
                animationDelay: `${i * 0.07}s`,
            }}
        />
    );
}

function ConfRing({ value, color }: { value: number; color: string }) {
    const r = 30;
    const circ = 2 * Math.PI * r;
    const offset = circ - (value / 100) * circ;
    return (
        <div className="relative w-[80px] h-[80px] shrink-0">
            <svg width="80" height="80" className="rotate-[-90deg]">
                <circle cx="40" cy="40" r={r} strokeWidth="4" className="conf-ring-track" />
                <circle
                    cx="40" cy="40" r={r}
                    strokeWidth="4"
                    stroke={color}
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray={circ}
                    strokeDashoffset={offset}
                    style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(0.4,0,0.2,1)", filter: `drop-shadow(0 0 4px ${color}60)` }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-mono text-[20px] font-black leading-none" style={{ color }}>
                    {value}
                </span>
                <span className="font-mono text-[10px] text-t3 tracking-widest mt-0.5">CONF</span>
            </div>
        </div>
    );
}

export function VerdictBanner({ verdict, isAnalyzing, elapsedSec = 0 }: Props) {
    // ── Analysing ──────────────────────────────────────────────
    if (isAnalyzing) {
        return (
            <div
                className="w-full relative overflow-hidden rounded-2xl px-6 py-5"
                style={{
                    background: "linear-gradient(135deg, rgba(96,165,250,0.08) 0%, #0d1117 60%)",
                    border: "1px solid rgba(96,165,250,0.2)",
                }}
            >
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background: "linear-gradient(90deg, transparent 0%, rgba(96,165,250,0.05) 50%, transparent 100%)",
                        animation: "shimmerScan 2.2s ease infinite",
                    }}
                />
                <div className="relative flex items-center gap-5">
                    <div className="relative w-14 h-14 shrink-0">
                        <svg className="w-14 h-14 animate-spin-slow" viewBox="0 0 56 56">
                            <circle cx="28" cy="28" r="22" strokeWidth="2.5" fill="none" stroke="rgba(96,165,250,0.12)" />
                            <circle cx="28" cy="28" r="22" strokeWidth="2.5" fill="none" stroke="#60a5fa"
                                strokeDasharray="90 48" strokeLinecap="round"
                                style={{ filter: "drop-shadow(0 0 4px #60a5fa60)" }}
                            />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="font-mono text-[13px] font-black text-[#60a5fa] tabular-nums">{elapsedSec}s</span>
                        </div>
                    </div>
                    <div className="flex-1">
                        <div className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.12em] mb-2">
                            Running 9-Layer Intelligence Pipeline
                        </div>
                        <div className="font-head text-[24px] font-black text-t1 leading-tight">
                            L1 → L9 Analysis
                        </div>
                        <div className="font-mono text-[11px] text-t2 mt-1.5">
                            {elapsedSec < 30
                                ? "Macro → Technical → Options → Strategy → Sovereign"
                                : `Deep model processing — up to 90s (${elapsedSec}s elapsed)`
                            }
                        </div>
                    </div>
                    <div className="hidden sm:flex items-center gap-[4px] h-10">
                        {[6, 12, 18, 8, 22, 10, 16, 20, 7, 14].map((h, i) => (
                            <WaveBar key={i} h={h} i={i} color="#60a5fa" />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // ── Empty ─────────────────────────────────────────────────
    if (!verdict) {
        return (
            <div
                className="w-full rounded-2xl px-6 py-6"
                style={{ background: "#0d1117", border: "1px solid #1e2d45" }}
            >
                <div className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.1em] mb-3">
                    FM Trading Agency v5.0 · Intelligence Ready
                </div>
                <div
                    className="font-head font-black text-t1 mb-2"
                    style={{ fontSize: "clamp(20px, 3vw, 30px)" }}
                >
                    Run Analysis to Generate Today's Verdict
                </div>
                <div className="font-mono text-[11px] text-t2">
                    BULL TRADE · BEAR TRADE · HEDGE TRADE · WAIT — always a plan, never NO_TRADE
                </div>
            </div>
        );
    }

    const vt = verdict.verdict;
    const vc = VERDICT_COLORS[vt];
    const hex = vc.hex;

    const LABEL: Record<string, string> = {
        BULL_TRADE: "BULL TRADE", BEAR_TRADE: "BEAR TRADE",
        HEDGE_TRADE: "HEDGE TRADE", WAIT: "WAIT",
    };

    return (
        <div
            className="w-full relative overflow-hidden rounded-2xl verdict-enter"
            style={{
                background: `linear-gradient(135deg, ${hex}12 0%, #0d1117 55%)`,
                border: `1px solid ${hex}35`,
                boxShadow: `0 0 60px ${hex}18, 0 0 120px ${hex}08`,
            }}
        >
            {/* Left glow */}
            <div
                className="absolute left-0 top-0 w-64 h-full pointer-events-none"
                style={{ background: `radial-gradient(ellipse at 0% 50%, ${hex}15, transparent 70%)` }}
            />
            {/* Left accent bar */}
            <div
                className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-2xl"
                style={{ background: `linear-gradient(to bottom, ${hex}cc, ${hex}22)` }}
            />

            <div className="relative px-7 py-5 flex items-center gap-6">

                {/* ── Main content ─────────────────────────────────── */}
                <div className="flex-1 min-w-0">
                    {/* Eyebrow */}
                    <div className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.1em] mb-2 flex items-center gap-2 flex-wrap">
                        <span>{verdict.best_index}</span>
                        <span className="text-[#1e2d45]">·</span>
                        <span style={{ color: `${hex}90` }}>{verdict.regime?.replace(/_/g, " ")}</span>
                        <span className="text-[#1e2d45]">·</span>
                        <span>Score {verdict.execution_score}/100</span>
                    </div>

                    {/* Verdict type — LARGE */}
                    <div
                        className="font-head font-black leading-none tracking-tight mb-4"
                        style={{
                            fontSize: "clamp(30px, 5vw, 48px)",
                            color: hex,
                            textShadow: `0 0 24px ${hex}40`,
                        }}
                    >
                        {LABEL[vt]}
                    </div>

                    {/* Details */}
                    <TradeDetails verdict={verdict} hex={hex} />
                </div>

                {/* ── Waveform ─────────────────────────────────────── */}
                <div className="hidden lg:flex items-center gap-[4px] h-12 shrink-0">
                    {[7, 14, 20, 10, 26, 8, 18, 24, 6, 16, 22, 9].map((h, i) => (
                        <WaveBar key={i} h={h} i={i} color={hex} />
                    ))}
                </div>

                {/* ── Confidence ring ──────────────────────────────── */}
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
                <Pill label="SL" value={fmtPrice(tp.stop_loss)} color="#ff5561" />
                <Pill label="T1" value={fmtPrice(tp.target1)} color="#12e89e" />
                <Pill label="T2" value={fmtPrice(tp.target2)} color="#22d3ee" />
                <Pill label="R:R" value={`1:${tp.rr.toFixed(1)}`} />
                {tp.instrument && (
                    <span
                        className="font-mono text-[11px] px-2.5 py-1 rounded-md"
                        style={{ background: `${hex}10`, border: `1px solid ${hex}25`, color: "#9dafc8" }}
                    >
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
                        <Pill label="Credit" value={fmtPrice(hp.net_credit_per_lot)} color="#12e89e" />
                        <Pill label="MaxLoss" value={fmtPrice(hp.max_loss_per_lot)} color="#ff5561" />
                    </>
                ) : (
                    <span className="font-mono text-[12px] text-t2">{hp.protection_range}</span>
                )}
            </div>
        );
    }
    const ws = verdict.wait_signal;
    if (!ws) return null;
    return (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
            <span className="font-mono text-[12px] text-t2">{ws.reason}</span>
            <Pill label="Re-entry" value={ws.re_entry_trigger} />
            <Pill label="Window" value={`${ws.re_entry_window_minutes}m`} color="#fbbf24" />
        </div>
    );
}

function Pill({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <span className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] font-bold text-t3 uppercase tracking-wide">{label}</span>
            <span className="font-mono text-[13px] font-bold" style={{ color: color ?? "#f0f4ff" }}>
                {value}
            </span>
        </span>
    );
}
