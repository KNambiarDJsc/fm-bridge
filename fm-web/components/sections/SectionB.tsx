"use client";

import { cn, fmtPrice } from "@/lib/utils";
import type { IndicatorPack, FinalVerdict } from "@/lib/types";

interface Props {
    indicators?: IndicatorPack;
    verdict?: FinalVerdict | null;
    agentOutputs: Record<string, Record<string, unknown>>;
}

export function SectionB({ indicators: ind, agentOutputs }: Props) {
    const l3 = (agentOutputs.l3 ?? {}) as Record<string, unknown>;
    const l4 = (agentOutputs.l4 ?? {}) as Record<string, unknown>;

    // Build signal badges from live indicator data
    const signals: { name: string; dir: "bull" | "bear" | "neut" }[] = [];
    if (ind) {
        if (ind.ema_stack === "BULL") signals.push({ name: "EMA Stack", dir: "bull" });
        else if (ind.ema_stack === "BEAR") signals.push({ name: "EMA Stack", dir: "bear" });
        else signals.push({ name: "EMA Stack", dir: "neut" });

        if (ind.rsi != null) {
            const dir = ind.rsi > 50 && ind.rsi <= 70 ? "bull"
                : ind.rsi > 70 ? "bear"
                    : ind.rsi < 30 ? "bull" : "neut";
            signals.push({ name: `RSI ${ind.rsi.toFixed(0)}`, dir });
        }
        if (ind.macd_dir) signals.push({ name: "MACD", dir: ind.macd_dir === "BULL" ? "bull" : "bear" });
        if (ind.supertrend_dir) signals.push({ name: "Supertrend", dir: ind.supertrend_dir === "LONG" ? "bull" : "bear" });
        if (ind.vwap && ind.spot) signals.push({ name: "VWAP", dir: ind.spot > ind.vwap ? "bull" : "bear" });
        if (ind.adx != null) signals.push({ name: `ADX ${ind.adx.toFixed(0)}`, dir: ind.adx > 25 ? "bull" : "neut" });
        if (ind.stoch_k != null && ind.stoch_d != null)
            signals.push({ name: "Stoch", dir: ind.stoch_k > ind.stoch_d && ind.stoch_k < 80 ? "bull" : "bear" });
        if (ind.cci != null) signals.push({ name: "CCI", dir: ind.cci > 0 ? "bull" : "bear" });
        if (ind.cmf != null) signals.push({ name: "CMF", dir: ind.cmf > 0 ? "bull" : "bear" });
        if (ind.obv_dir) signals.push({ name: "OBV", dir: ind.obv_dir === "UP" ? "bull" : "bear" });
    }

    const bullCount = signals.filter(s => s.dir === "bull").length;
    const bearCount = signals.filter(s => s.dir === "bear").length;
    const neutCount = signals.filter(s => s.dir === "neut").length;

    const patternName = (l4.primary_pattern as string) || "NO_PATTERN";
    const patternState = (l4.pattern_state as string) || "NONE";
    const patternDir = (l4.direction as string) || "NEUTRAL";
    const bullTrap = !!(l4.bull_trap_detected as boolean);
    const bearPivot = l4.bear_pivot_entry as Record<string, unknown> | undefined;

    const mtiAlignment = (l3.multi_tf_alignment as Record<string, string>) || {};
    const mtiSummary = (mtiAlignment.summary as string) || "";

    return (
        <div className="space-y-5 animate-fade-in">

            {/* B1 — Indicator consensus */}
            <div>
                <div className="font-mono text-[11px] font-bold text-t3 uppercase tracking-[1px] mb-2 pb-1.5 border-b border-[#1e2d45]">
                    B1 · Indicator Consensus ({signals.length} signals)
                </div>
                {signals.length > 0 ? (
                    <>
                        <div className="flex h-7 rounded-lg overflow-hidden border border-[#1e2d45] mb-3">
                            {bullCount > 0 && (
                                <div
                                    className="bg-bull flex items-center justify-center font-mono text-[11px] font-black text-bg transition-all"
                                    style={{ flex: bullCount }}
                                >
                                    {bullCount} BULL
                                </div>
                            )}
                            {neutCount > 0 && (
                                <div
                                    className="bg-b2 flex items-center justify-center font-mono text-[11px] font-bold text-t2"
                                    style={{ flex: neutCount }}
                                >
                                    {neutCount} NEUT
                                </div>
                            )}
                            {bearCount > 0 && (
                                <div
                                    className="bg-bear flex items-center justify-center font-mono text-[11px] font-black text-bg transition-all"
                                    style={{ flex: bearCount }}
                                >
                                    {bearCount} BEAR
                                </div>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            {signals.map((s, i) => (
                                <span
                                    key={i}
                                    className={cn(
                                        "font-mono text-[11px] px-2 py-0.5 rounded-md border font-bold",
                                        s.dir === "bull" ? "bg-bull/10 border-bull/30 text-bull" :
                                            s.dir === "bear" ? "bg-bear/10 border-bear/30 text-bear" :
                                                "bg-[#131924] border-b text-t3"
                                    )}
                                >
                                    {s.name}
                                </span>
                            ))}
                        </div>
                    </>
                ) : (
                    <div className="font-mono text-[11px] text-t3">No indicator data — run analysis or connect bridge.</div>
                )}
            </div>

            {/* B2 — Pattern card */}
            <div>
                <div className="font-mono text-[11px] font-bold text-t3 uppercase tracking-[1px] mb-2 pb-1.5 border-b border-[#1e2d45]">
                    B2 · Pattern Verdict
                </div>
                <div className="bg-[#131924] border border-[#1e2d45] rounded-lg p-3 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn(
                            "font-mono text-[11px] font-black px-2 py-0.5 rounded uppercase tracking-[0.5px]",
                            patternState === "CONFIRMED" ? "bg-bull/15 text-bull" :
                                patternState === "TRAP" ? "bg-bear/20 text-bear border border-[#1e2d45]ear/40" :
                                    patternState === "FAILED" ? "bg-bear/15 text-bear" :
                                        patternState === "FORMING" ? "bg-wait/15 text-wait" :
                                            "bg-bg text-t3"
                        )}>
                            {patternState}
                        </span>
                        <span className="font-mono text-[13px] font-bold text-t1">{patternName}</span>
                        <span className={cn(
                            "font-mono text-[11px] font-bold ml-auto",
                            patternDir === "LONG" ? "text-bull" : patternDir === "SHORT" ? "text-bear" : "text-t3"
                        )}>
                            {patternDir}
                        </span>
                    </div>

                    {bullTrap && (
                        <div className="flex items-center gap-2 bg-bear/5 border border-[#1e2d45]ear/25 rounded p-2">
                            <span className="font-mono text-[11px] font-black text-bear">⚠ BULL TRAP — SHORT_SELL_SEARCH active</span>
                        </div>
                    )}

                    {(l4.rationale as string) && (
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">
                            {l4.rationale as string}
                        </div>
                    )}

                    {/* Bear pivot entry if trap detected */}
                    {bullTrap && bearPivot && (
                        <div className="mt-2 p-2.5 rounded-lg bg-bear/5 border border-[#1e2d45]ear/20 space-y-1">
                            <div className="font-mono text-[11px] font-bold text-bear uppercase tracking-[0.5px]">Bear Pivot Entry Plan</div>
                            <div className="grid grid-cols-3 gap-2">
                                <div><div className="font-mono text-[11px] text-t3">Entry</div><div className="font-mono text-[12px] font-bold text-t1">{fmtPrice(bearPivot.entry_level as number)}</div></div>
                                <div><div className="font-mono text-[11px] text-t3">Stop</div><div className="font-mono text-[12px] font-bold text-bear">{fmtPrice(bearPivot.stop_level as number)}</div></div>
                                <div><div className="font-mono text-[11px] text-t3">Target</div><div className="font-mono text-[12px] font-bold text-bull">{fmtPrice(bearPivot.target as number)}</div></div>
                            </div>
                            {bearPivot.condition && (
                                <div className="font-mono text-[11px] text-t3">{bearPivot.condition as string}</div>
                            )}
                        </div>
                    )}

                    {/* Targets */}
                    {((l4.measured_move_target1 as number) || (l4.invalidation_level as number)) && (
                        <div className="grid grid-cols-3 gap-2 pt-1">
                            {l4.measured_move_target1 && (
                                <div className="bg-bg border border-[#1e2d45] rounded p-2">
                                    <div className="font-mono text-[11px] text-t3 uppercase">Target 1</div>
                                    <div className="font-mono text-[12px] font-bold text-bull">{fmtPrice(l4.measured_move_target1 as number)}</div>
                                </div>
                            )}
                            {l4.measured_move_target2 && (
                                <div className="bg-bg border border-[#1e2d45] rounded p-2">
                                    <div className="font-mono text-[11px] text-t3 uppercase">Target 2</div>
                                    <div className="font-mono text-[12px] font-bold text-bull">{fmtPrice(l4.measured_move_target2 as number)}</div>
                                </div>
                            )}
                            {l4.invalidation_level && (
                                <div className="bg-bg border border-[#1e2d45] rounded p-2">
                                    <div className="font-mono text-[11px] text-t3 uppercase">Invalidation</div>
                                    <div className="font-mono text-[12px] font-bold text-bear">{fmtPrice(l4.invalidation_level as number)}</div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* B3 — Multi-TF grid */}
            <div>
                <div className="font-mono text-[11px] font-bold text-t3 uppercase tracking-[1px] mb-2 pb-1.5 border-b border-[#1e2d45]">
                    B3 · Multi-Timeframe Alignment
                    {mtiSummary && (
                        <span className={cn(
                            "ml-2 px-1.5 py-0.5 rounded text-[11px]",
                            mtiSummary === "BULL_ALIGNED" ? "bg-bull/15 text-bull" :
                                mtiSummary === "BEAR_ALIGNED" ? "bg-bear/15 text-bear" : "bg-bg3 text-t3"
                        )}>
                            {mtiSummary.replace(/_/g, " ")}
                        </span>
                    )}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {(["daily", "hourly", "intraday", "scalp"] as const).map((tf) => {
                        const label = { daily: "1D Daily", hourly: "1H Hourly", intraday: "15M Intraday", scalp: "5M Scalp" }[tf];
                        const val = mtiAlignment[tf] as string || "—";
                        return (
                            <div key={tf} className="bg-[#131924] border border-[#1e2d45] rounded-lg p-2.5">
                                <div className="font-mono text-[11px] text-t3 uppercase tracking-[0.5px] mb-1">{label}</div>
                                <div className={cn(
                                    "font-mono text-[11px] font-bold",
                                    val.toLowerCase().includes("bull") ? "text-bull" :
                                        val.toLowerCase().includes("bear") ? "text-bear" : "text-t2"
                                )}>
                                    {val}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

        </div>
    );
}
