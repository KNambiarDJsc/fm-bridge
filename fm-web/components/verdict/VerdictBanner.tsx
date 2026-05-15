"use client";

import { cn, VERDICT_COLORS, VERDICT_LABELS, fmtPrice, fmtPct } from "@/lib/utils";
import type { FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    isAnalyzing?: boolean;
}

export function VerdictBanner({ verdict, isAnalyzing }: Props) {
    // ── Loading state ────────────────────────────────────────────
    if (isAnalyzing) {
        return (
            <div className="w-full min-h-[80px] flex items-center gap-4 px-5 py-4 rounded-xl border border-bl/30 bg-bl/5 animate-pulse-slow">
                <div className="flex-1">
                    <div className="font-mono text-[11px] text-t3 uppercase tracking-[2px] mb-1">Analysing Pipeline</div>
                    <div className="font-mono text-[28px] font-black text-t2 tracking-tight">
                        Running L1 → L9 …
                    </div>
                </div>
                <div className="w-[72px] h-[72px] rounded-full border-4 border-bl/20 flex items-center justify-center">
                    <div className="w-8 h-8 border-2 border-bl border-t-transparent rounded-full animate-spin" />
                </div>
            </div>
        );
    }

    // ── Empty state ───────────────────────────────────────────────
    if (!verdict) {
        return (
            <div className="w-full min-h-[80px] flex items-center gap-4 px-5 py-4 rounded-xl border border-b bg-bg2">
                <div className="flex-1">
                    <div className="font-mono text-[11px] text-t3 uppercase tracking-[2px] mb-1">FM Trading Agency v5.0</div>
                    <div className="font-mono text-[22px] font-black text-t3">
                        Click <span className="text-bl">▶ RUN ANALYSIS</span> to generate today's verdict
                    </div>
                    <div className="font-mono text-[11px] text-t3 mt-1">
                        BULL TRADE · BEAR TRADE · HEDGE TRADE · WAIT — always a plan, never NO_TRADE
                    </div>
                </div>
            </div>
        );
    }

    const vt = verdict.verdict;
    const vc = VERDICT_COLORS[vt];

    // ── Sub-line content per verdict type ─────────────────────────
    const subLine = () => {
        if (vt === "BULL_TRADE" || vt === "BEAR_TRADE") {
            const tp = verdict.trade_plan;
            if (!tp) return null;
            return (
                <div className="font-mono text-[11px] text-t2 mt-[5px] flex flex-wrap gap-x-3 gap-y-1">
                    <span>Entry <b className="text-t1">{fmtPrice(tp.entry_low)}–{fmtPrice(tp.entry_high)}</b></span>
                    <span className="text-t3">·</span>
                    <span>SL <b className="text-bear">{fmtPrice(tp.stop_loss)}</b></span>
                    <span className="text-t3">·</span>
                    <span>T1 <b className="text-bull">{fmtPrice(tp.target1)}</b></span>
                    <span>T2 <b className="text-bull">{fmtPrice(tp.target2)}</b></span>
                    <span className="text-t3">·</span>
                    <span>R:R <b className="text-t1">1:{tp.rr.toFixed(1)}</b></span>
                    <span className="text-t3">·</span>
                    <span className="text-t2">{tp.instrument}</span>
                    {tp.holding_period && (
                        <>
                            <span className="text-t3">·</span>
                            <span className="text-t2">{tp.holding_period}</span>
                        </>
                    )}
                </div>
            );
        }
        if (vt === "HEDGE_TRADE") {
            const hp = verdict.hedge_plan;
            return (
                <div className="font-mono text-[11px] text-t2 mt-[5px] flex flex-wrap gap-x-3 gap-y-1">
                    {hp?.hedge_type === "IRON_CONDOR" ? (
                        <>
                            <span>Sell CE <b className="text-t1">{fmtPrice(hp.sell_ce)}</b></span>
                            <span className="text-t3">·</span>
                            <span>Sell PE <b className="text-t1">{fmtPrice(hp.sell_pe)}</b></span>
                            <span className="text-t3">·</span>
                            <span>Credit <b className="text-bull">{fmtPrice(hp.net_credit_per_lot)}</b>/lot</span>
                            <span className="text-t3">·</span>
                            <span>MaxLoss <b className="text-bear">{fmtPrice(hp.max_loss_per_lot)}</b>/lot</span>
                        </>
                    ) : (
                        <span>{hp?.protection_range}</span>
                    )}
                </div>
            );
        }
        // WAIT
        const ws = verdict.wait_signal;
        if (!ws) return null;
        return (
            <div className="font-mono text-[11px] text-t2 mt-[5px] flex flex-wrap gap-x-3 gap-y-1">
                <span>{ws.reason}</span>
                <span className="text-t3">·</span>
                <span>Re-entry: <b className="text-t1">{ws.re_entry_trigger}</b></span>
                <span className="text-t3">·</span>
                <span>Window <b className="text-wait">{ws.re_entry_window_minutes}min</b></span>
            </div>
        );
    };

    return (
        <div
            className={cn(
                "w-full min-h-[80px] flex items-center gap-4 px-5 py-4 rounded-xl",
                "border-l-[6px] border-r border-t border-b transition-all duration-300",
                "animate-verdict-in",
                vc.bg,
                vc.border,
                vt === "BULL_TRADE" && "verdict-bull"
            )}
            style={{ borderLeftColor: vc.hex }}
        >
            <div className="flex-1 min-w-0">
                {/* Top eyebrow */}
                <div className="font-mono text-[10px] font-bold tracking-[2px] uppercase text-t3 mb-1">
                    {verdict.best_index} · Score {verdict.execution_score}/100 · {verdict.regime.replace("_", " ")}
                </div>

                {/* Main verdict label */}
                <div className={cn("font-mono text-[28px] font-black leading-none tracking-tight", vc.text)}>
                    {VERDICT_LABELS[vt]}
                </div>

                {/* Sub-line */}
                {subLine()}
            </div>

            {/* Score ring */}
            <div
                className={cn(
                    "flex-shrink-0 w-[72px] h-[72px] rounded-full flex items-center justify-center",
                    "border-4 font-mono font-black text-[22px]",
                    vc.text
                )}
                style={{ borderColor: `${vc.hex}40` }}
            >
                {verdict.confidence}
            </div>
        </div>
    );
}
