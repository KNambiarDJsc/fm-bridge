"use client";

import { cn, VERDICT_COLORS, fmtPrice, fmtPct } from "@/lib/utils";
import type { FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    isAnalyzing?: boolean;
    elapsedSec?: number;
}

// Confidence SVG ring — animated fill
function ConfRing({ value, color }: { value: number; color: string }) {
    const r = 32;
    const circ = 2 * Math.PI * r;
    const offset = circ - (value / 100) * circ;
    return (
        <svg width="80" height="80" className="rotate-[-90deg] shrink-0">
            <circle cx="40" cy="40" r={r} strokeWidth="3" className="conf-ring-track" />
            <circle
                cx="40" cy="40" r={r}
                strokeWidth="3"
                stroke={color}
                fill="none"
                strokeLinecap="round"
                strokeDasharray={circ}
                strokeDashoffset={offset}
                style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)" }}
            />
        </svg>
    );
}

// Waveform bars — animates faster when volatile
function VolatilityBar({ h, delay, color }: { h: number; delay: number; color: string }) {
    return (
        <div
            className="w-[3px] rounded-full"
            style={{
                height: `${h}px`,
                backgroundColor: color,
                opacity: 0.6,
                animation: `wave${(delay % 5) + 1} ${1.2 + delay * 0.15}s ease-in-out infinite`,
                animationDelay: `${delay * 0.08}s`,
            }}
        />
    );
}

export function VerdictBanner({ verdict, isAnalyzing, elapsedSec = 0 }: Props) {
    // ── Analysing state ──────────────────────────────────────────
    if (isAnalyzing) {
        return (
            <div className="w-full relative overflow-hidden rounded-2xl glass-accent px-6 py-5">
                {/* Scanning shimmer */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background: "linear-gradient(90deg, transparent, rgba(58,158,255,0.06), transparent)",
                        animation: "shimmerScan 2s ease infinite",
                    }}
                />
                <div className="relative flex items-center gap-5">
                    {/* Spinner ring */}
                    <div className="shrink-0 relative w-14 h-14">
                        <svg className="w-14 h-14 animate-spin-slow" viewBox="0 0 56 56">
                            <circle cx="28" cy="28" r="24" strokeWidth="2" fill="none" stroke="rgba(58,158,255,0.12)" />
                            <circle cx="28" cy="28" r="24" strokeWidth="2" fill="none" stroke="#3a9eff"
                                strokeDasharray="100 51" strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="font-mono text-[11px] font-black text-bl">{elapsedSec}s</span>
                        </div>
                    </div>
                    <div>
                        <div className="font-mono text-[9px] font-bold tracking-[3px] text-t3 uppercase mb-2">
                            Running 9-Layer Pipeline
                        </div>
                        <div className="font-head text-[22px] font-black text-t1 tracking-tight leading-none">
                            L1 → L9 Intelligence
                        </div>
                        {elapsedSec >= 30 && (
                            <div className="font-mono text-[10px] text-wait mt-2">
                                Gemini processing deep analysis — up to 90s
                            </div>
                        )}
                    </div>
                    {/* Waveform */}
                    <div className="ml-auto hidden sm:flex items-center gap-[3px] h-8">
                        {[14, 22, 8, 18, 6, 20, 12, 24, 9, 16].map((h, i) => (
                            <VolatilityBar key={i} h={h} delay={i} color="#3a9eff" />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // ── Empty state ────────────────────────────────────────────
    if (!verdict) {
        return (
            <div className="w-full rounded-2xl border border-white/[0.05] bg-white/[0.015] px-6 py-5 backdrop-blur-xl">
                <div className="font-mono text-[9px] font-bold tracking-[3px] text-t3 uppercase mb-3">
                    FM Trading Agency v5.0 · Intelligence Ready
                </div>
                <div className="font-head text-[26px] font-black text-t2 tracking-tight leading-none mb-2">
                    Run Analysis to Generate Today's Verdict
                </div>
                <div className="font-mono text-[10px] text-t3">
                    BULL TRADE · BEAR TRADE · HEDGE TRADE · WAIT — always a plan, never NO_TRADE
                </div>
            </div>
        );
    }

    const vt = verdict.verdict;
    const vc = VERDICT_COLORS[vt];
    const score = verdict.execution_score;
    const conf = verdict.confidence;

    // Verdict-specific shadow
    const shadowMap: Record<string, string> = {
        BULL_TRADE: "shadow-verdict-bull",
        BEAR_TRADE: "shadow-verdict-bear",
        HEDGE_TRADE: "shadow-verdict-hedge",
        WAIT: "shadow-verdict-wait",
    };

    // Gradient accent per verdict
    const gradientMap: Record<string, string> = {
        BULL_TRADE: "from-[#00c896]/[0.12] via-transparent to-transparent",
        BEAR_TRADE: "from-[#ff4d5a]/[0.12] via-transparent to-transparent",
        HEDGE_TRADE: "from-[#9d7dff]/[0.12] via-transparent to-transparent",
        WAIT: "from-[#f5a623]/[0.08] via-transparent to-transparent",
    };

    // Waveform color
    const waveColor = vc.hex;

    return (
        <div
            className={cn(
                "w-full relative overflow-hidden rounded-2xl verdict-enter",
                shadowMap[vt],
            )}
            style={{
                background: `linear-gradient(135deg, ${vc.hex}10 0%, rgba(10,14,26,0.95) 60%)`,
                border: `1px solid ${vc.hex}30`,
            }}
        >
            {/* Radial glow from left edge */}
            <div
                className="absolute left-0 top-0 w-[280px] h-full pointer-events-none"
                style={{
                    background: `radial-gradient(ellipse at 0% 50%, ${vc.hex}18, transparent 70%)`,
                }}
            />
            {/* Edge accent line */}
            <div
                className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-2xl"
                style={{ background: `linear-gradient(to bottom, ${vc.hex}90, ${vc.hex}20)` }}
            />

            <div className="relative px-6 py-5 flex items-center gap-6">

                {/* ── Left: main verdict content ────────────────────── */}
                <div className="flex-1 min-w-0">
                    {/* Eyebrow */}
                    <div className="font-mono text-[9px] font-bold tracking-[3px] text-t3 uppercase mb-2 flex items-center gap-2">
                        <span>{verdict.best_index}</span>
                        <span className="text-[#1a2232]">·</span>
                        <span className={cn(vc.text, "opacity-70")}>
                            {verdict.regime?.replace(/_/g, " ")}
                        </span>
                        <span className="text-[#1a2232]">·</span>
                        <span>Score {score}/100</span>
                    </div>

                    {/* Main verdict type — the dominant element */}
                    <div
                        className={cn("font-head font-black leading-none tracking-tight mb-3", vc.text)}
                        style={{ fontSize: "clamp(28px, 4vw, 42px)" }}
                    >
                        {vt === "BULL_TRADE" && "BULL TRADE"}
                        {vt === "BEAR_TRADE" && "BEAR TRADE"}
                        {vt === "HEDGE_TRADE" && "HEDGE TRADE"}
                        {vt === "WAIT" && "WAIT"}
                    </div>

                    {/* Trade details */}
                    <SubLine verdict={verdict} vc={vc} />
                </div>

                {/* ── Center: waveform (hidden on mobile) ────────────── */}
                <div className="hidden lg:flex items-center gap-[3px] h-10 shrink-0">
                    {[8, 14, 20, 12, 26, 10, 18, 24, 8, 16, 22, 10].map((h, i) => (
                        <VolatilityBar key={i} h={h} delay={i} color={waveColor} />
                    ))}
                </div>

                {/* ── Right: confidence ring ─────────────────────────── */}
                <div className="shrink-0 flex flex-col items-center gap-1 relative">
                    <ConfRing value={conf} color={vc.hex} />
                    {/* Center number overlay */}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span
                            className={cn("font-mono font-black leading-none", vc.text)}
                            style={{ fontSize: conf >= 100 ? "18px" : "22px" }}
                        >
                            {conf}
                        </span>
                    </div>
                    <div className="font-mono text-[8px] text-t3 tracking-[1.5px] uppercase -mt-1">
                        CONF
                    </div>
                </div>
            </div>
        </div>
    );
}

function SubLine({ verdict, vc }: { verdict: FinalVerdict; vc: { hex: string; text: string } }) {
    const vt = verdict.verdict;

    if (vt === "BULL_TRADE" || vt === "BEAR_TRADE") {
        const tp = verdict.trade_plan;
        if (!tp) return null;
        return (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <SubPill label="Entry" value={`${fmtPrice(tp.entry_low)} – ${fmtPrice(tp.entry_high)}`} />
                <SubPill label="SL" value={fmtPrice(tp.stop_loss)} color="#ff4d5a" />
                <SubPill label="T1" value={fmtPrice(tp.target1)} color="#00c896" />
                <SubPill label="T2" value={fmtPrice(tp.target2)} color="#4cffb2" />
                <SubPill label="R:R" value={`1:${tp.rr.toFixed(1)}`} />
                {tp.instrument && (
                    <span className="font-mono text-[10px] text-t3 bg-white/[0.04] px-2 py-0.5 rounded-full border border-white/[0.06]">
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
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                {hp.hedge_type === "IRON_CONDOR" ? (
                    <>
                        <SubPill label="Sell CE" value={fmtPrice(hp.sell_ce)} />
                        <SubPill label="Sell PE" value={fmtPrice(hp.sell_pe)} />
                        <SubPill label="Credit" value={fmtPrice(hp.net_credit_per_lot)} color="#00c896" />
                        <SubPill label="Max Loss" value={fmtPrice(hp.max_loss_per_lot)} color="#ff4d5a" />
                    </>
                ) : (
                    <span className="font-mono text-[11px] text-t2">{hp.protection_range}</span>
                )}
            </div>
        );
    }
    // WAIT
    const ws = verdict.wait_signal;
    if (!ws) return null;
    return (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-mono text-[11px] text-t2">{ws.reason}</span>
            <SubPill label="Re-entry" value={ws.re_entry_trigger} />
            <SubPill label="Window" value={`${ws.re_entry_window_minutes}min`} color="#f5a623" />
        </div>
    );
}

function SubPill({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <span className="flex items-center gap-1.5">
            <span className="font-mono text-[9px] text-t3 uppercase tracking-wider">{label}</span>
            <span
                className="font-mono text-[12px] font-bold"
                style={{ color: color ?? "#e8edf8" }}
            >
                {value}
            </span>
        </span>
    );
}
