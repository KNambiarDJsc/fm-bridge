"use client";

import { cn, fmtPrice, fmtPct } from "@/lib/utils";
import type { IndexScore } from "@/lib/types";
import { RefreshCw, TrendingUp } from "lucide-react";

interface Props {
    indices: IndexScore[];
    best?: IndexScore | null;
    currentSymbol: string;
    onSwitch: (name: string) => void;
    onRefresh: () => void;
    isLoading?: boolean;
}

function scoreColor(s: number): string {
    if (s >= 72) return "var(--bull)";
    if (s >= 55) return "var(--t1)";
    if (s >= 40) return "var(--wait)";
    return "var(--bear)";
}

const REGIME_COLOR: Record<string, string> = {
    BULL: "var(--bull)", BEAR: "var(--bear)", SIDE: "var(--t3)",
};

export function IndexHeatmap({ indices, best, currentSymbol, onSwitch, onRefresh, isLoading }: Props) {
    const cur = indices.find(i => i.name === currentSymbol);
    const bestScore = best?.score ?? 0;
    const curScore = cur?.score ?? 0;
    const suggest = best && currentSymbol !== best.name && (bestScore - curScore) >= 15;

    return (
        <div
            className="overflow-hidden rounded-2xl"
            style={{ background: "var(--bg2)", border: "1px solid var(--b)" }}
        >
            {/* Header */}
            <div
                className="flex items-center gap-3 px-5 py-3 border-b"
                style={{ borderColor: "var(--b)", background: "var(--bg)" }}
            >
                <span className="font-mono text-[10px] font-bold text-t2 uppercase tracking-[0.1em]">
                    Index Intelligence
                </span>
                <span className="font-mono text-[10px] text-t3">— {indices.length} indices tracked</span>
                <button
                    onClick={onRefresh}
                    disabled={isLoading}
                    className="ml-auto p-1.5 rounded-lg transition-all"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--b)" }}
                >
                    <RefreshCw size={12} className={cn("text-t2", isLoading && "animate-spin")} />
                </button>
            </div>

            {/* Opportunity bar */}
            {suggest && best && (
                <div
                    className="flex items-center gap-3 px-5 py-2.5 border-b"
                    style={{ background: "rgba(18,232,158,0.05)", borderColor: "rgba(18,232,158,0.18)" }}
                >
                    <TrendingUp size={13} className="text-[var(--bull)] shrink-0" />
                    <span className="font-mono text-[11px] text-t2">
                        <b className="text-[var(--bull)]">{best.name}</b> shows strongest setup today — {best.score} vs {curScore}
                    </span>
                    <button
                        onClick={() => onSwitch(best.name)}
                        className="ml-auto font-mono text-[10px] font-black px-3 py-1 rounded-lg shrink-0 transition-all hover:opacity-80"
                        style={{ background: "rgba(18,232,158,0.12)", border: "1px solid rgba(18,232,158,0.3)", color: "var(--bull)" }}
                    >
                        Analyse →
                    </button>
                </div>
            )}

            {/* Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5">
                {indices.map((idx) => (
                    <IndexCell
                        key={idx.name}
                        index={idx}
                        isCurrent={idx.name === currentSymbol}
                        isBest={idx.name === best?.name}
                        onClick={() => !idx.error && onSwitch(idx.name)}
                    />
                ))}
                {isLoading && indices.length === 0 &&
                    Array.from({ length: 10 }).map((_, i) => (
                        <div key={i} className="h-[76px] animate-pulse-slow" style={{ background: "var(--bg3)" }} />
                    ))
                }
            </div>
        </div>
    );
}

function IndexCell({ index, isCurrent, isBest, onClick }: {
    index: IndexScore; isCurrent: boolean; isBest: boolean; onClick: () => void;
}) {
    const sc = scoreColor(index.score);
    const rColor = REGIME_COLOR[index.regime] ?? "var(--t3)";

    return (
        <button
            onClick={onClick}
            className="relative text-left transition-all duration-150 group overflow-hidden"
            style={{
                padding: "12px 14px",
                background: isCurrent ? "rgba(96,165,250,0.06)" : isBest ? "rgba(18,232,158,0.04)" : "transparent",
                borderRight: "1px solid var(--b)",
                borderBottom: "1px solid var(--b)",
            }}
        >
            {/* Hover */}
            <div
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: `${rColor}06` }}
            />

            {/* Active top border */}
            {(isCurrent || isBest) && (
                <div
                    className="absolute top-0 left-0 right-0 h-[2px]"
                    style={{ backgroundColor: isCurrent ? "var(--bl)" : "var(--bull)" }}
                />
            )}

            <div className="relative">
                {/* Name */}
                <div className="flex items-center justify-between mb-2">
                    <span
                        className="font-mono text-[10px] font-bold uppercase tracking-[0.06em] truncate"
                        style={{ color: isCurrent ? "var(--bl)" : isBest ? "var(--bull)" : "var(--t2)" }}
                    >
                        {index.name.replace("NIFTY ", "").replace(" 50", "50")}
                    </span>
                    {isCurrent && <span style={{ color: "var(--bl)", fontSize: "8px" }}>●</span>}
                    {isBest && !isCurrent && <span style={{ color: "var(--bull)", fontSize: "9px" }}>★</span>}
                </div>

                {/* Score — dominant */}
                <div
                    className="font-mono font-black leading-none tabular-nums"
                    style={{
                        fontSize: "22px",
                        color: index.error ? "var(--t3)" : sc,
                        textShadow: !index.error && index.score >= 70 ? `0 0 12px ${sc}50` : "none",
                    }}
                >
                    {index.error ? "—" : index.score}
                </div>

                {/* Regime + change */}
                <div className="flex items-center justify-between mt-1.5">
                    <span className="font-mono text-[10px] font-bold uppercase" style={{ color: rColor, opacity: 0.85 }}>
                        {index.error ? "ERR" : index.regime}
                    </span>
                    {!index.error && (
                        <span
                            className="font-mono text-[10px] font-bold tabular-nums"
                            style={{ color: index.change_pct >= 0 ? "var(--bull)" : "var(--bear)" }}
                        >
                            {fmtPct(index.change_pct)}
                        </span>
                    )}
                </div>

                {/* Score bar */}
                {!index.error && (
                    <div className="mt-2 h-[2px] rounded-full overflow-hidden" style={{ background: "var(--b)" }}>
                        <div
                            className="h-full rounded-full"
                            style={{ width: `${index.score}%`, backgroundColor: sc, transition: "width 0.6s ease" }}
                        />
                    </div>
                )}
            </div>
        </button>
    );
}
