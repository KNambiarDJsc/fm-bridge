"use client";

import { cn, fmtPrice, fmtPct } from "@/lib/utils";
import type { IndexScore } from "@/lib/types";
import { RefreshCw, Zap } from "lucide-react";

interface Props {
    indices: IndexScore[];
    best?: IndexScore | null;
    currentSymbol: string;
    onSwitch: (name: string) => void;
    onRefresh: () => void;
    isLoading?: boolean;
}

const REGIME_GRADIENT: Record<string, string> = {
    BULL: "from-[#00c896]/[0.12] to-transparent",
    BEAR: "from-[#ff4d5a]/[0.10] to-transparent",
    SIDE: "from-transparent to-transparent",
};

const REGIME_COLOR: Record<string, string> = {
    BULL: "#00c896",
    BEAR: "#ff4d5a",
    SIDE: "#3d4f68",
};

function scoreColor(s: number) {
    if (s >= 72) return "#00c896";
    if (s >= 55) return "#e8edf8";
    if (s >= 40) return "#f5a623";
    return "#ff4d5a";
}

export function IndexHeatmap({ indices, best, currentSymbol, onSwitch, onRefresh, isLoading }: Props) {
    const switchGap = best && currentSymbol !== best.name
        ? (indices.find(i => i.name === currentSymbol)?.score ?? 0) : 0;
    const suggestSwitch = best && switchGap > 0 && (best.score - switchGap) >= 15;

    return (
        <div
            className="overflow-hidden rounded-2xl"
            style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.055)",
                backdropFilter: "blur(20px)",
            }}
        >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/[0.045]">
                <div className="flex items-center gap-2">
                    <div className="w-[5px] h-[5px] rounded-full bg-t3" />
                    <span className="font-mono text-[9px] font-bold text-t3 uppercase tracking-[2.5px]">
                        Index Intelligence Field
                    </span>
                </div>
                <button
                    onClick={onRefresh}
                    disabled={isLoading}
                    className="ml-auto p-1.5 rounded-lg transition-all hover:bg-white/[0.05] text-t3 hover:text-t1 disabled:opacity-40"
                >
                    <RefreshCw size={11} className={isLoading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Opportunity alert */}
            {suggestSwitch && best && (
                <div
                    className="flex items-center gap-3 px-4 py-2 border-b"
                    style={{
                        background: "rgba(0,200,150,0.05)",
                        borderColor: "rgba(0,200,150,0.18)",
                    }}
                >
                    <Zap size={11} className="text-bull shrink-0" />
                    <span className="font-mono text-[10px] text-t2 flex-1">
                        <b className="text-bull">{best.name}</b> shows strongest setup today —{" "}
                        {best.score} vs {switchGap}
                    </span>
                    <button
                        onClick={() => onSwitch(best.name)}
                        className="font-mono text-[9px] font-black text-bull border border-bull/30 rounded-lg px-2.5 py-1 hover:bg-bull/10 transition-colors shrink-0"
                    >
                        Analyse →
                    </button>
                </div>
            )}

            {/* Intelligence grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                {indices.map((idx, i) => (
                    <IndexCell
                        key={idx.name}
                        index={idx}
                        isCurrent={idx.name === currentSymbol}
                        isBest={idx.name === best?.name}
                        position={i}
                        onClick={() => !idx.error && onSwitch(idx.name)}
                    />
                ))}
                {isLoading && indices.length === 0 &&
                    Array.from({ length: 10 }).map((_, i) => (
                        <div
                            key={i}
                            className="h-[76px] animate-pulse"
                            style={{ background: "rgba(255,255,255,0.015)" }}
                        />
                    ))
                }
            </div>
        </div>
    );
}

function IndexCell({ index, isCurrent, isBest, position, onClick }: {
    index: IndexScore; isCurrent: boolean; isBest: boolean; position: number; onClick: () => void;
}) {
    const sc = scoreColor(index.score);
    const rColor = REGIME_COLOR[index.regime] ?? "#3d4f68";
    const isActive = isCurrent || isBest;

    return (
        <button
            onClick={onClick}
            className={cn(
                "relative text-left transition-all duration-200 group overflow-hidden",
                "border-r border-b border-white/[0.04]",
                index.error && "opacity-40 cursor-default",
            )}
            style={{
                padding: "10px 12px",
                background: isCurrent
                    ? "rgba(58,158,255,0.06)"
                    : isBest
                        ? "rgba(0,200,150,0.05)"
                        : "transparent",
            }}
        >
            {/* Hover fill */}
            <div
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
                style={{ background: `${rColor}08` }}
            />

            {/* Active indicator line */}
            {isActive && (
                <div
                    className="absolute top-0 left-0 right-0 h-[1.5px]"
                    style={{ backgroundColor: isCurrent ? "#3a9eff" : "#00c896" }}
                />
            )}

            <div className="relative">
                {/* Name */}
                <div className="flex items-center gap-1 mb-1.5">
                    <span
                        className="font-mono text-[8.5px] font-bold uppercase tracking-[0.5px] truncate"
                        style={{ color: isCurrent ? "#3a9eff" : isBest ? "#00c896" : "#7d8ea8" }}
                    >
                        {index.name.replace("NIFTY ", "").replace(" 50", "50")}
                    </span>
                    {isCurrent && (
                        <span className="text-[6px] text-bl ml-auto shrink-0">●</span>
                    )}
                    {isBest && !isCurrent && (
                        <span className="text-[7px] text-bull ml-auto shrink-0">★</span>
                    )}
                </div>

                {/* Score — dominant number */}
                <div
                    className="font-mono font-black leading-none tabular-nums"
                    style={{
                        fontSize: "20px",
                        color: index.error ? "#3d4f68" : sc,
                        textShadow: !index.error && index.score >= 70
                            ? `0 0 16px ${sc}50` : "none",
                    }}
                >
                    {index.error ? "—" : index.score}
                </div>

                {/* Regime + price */}
                <div className="flex items-center justify-between mt-1">
                    <span
                        className="font-mono text-[8px] font-bold uppercase tracking-[0.3px]"
                        style={{ color: rColor, opacity: 0.8 }}
                    >
                        {index.error ? "ERR" : index.regime}
                    </span>
                    {!index.error && (
                        <span
                            className="font-mono text-[8px] tabular-nums"
                            style={{ color: index.change_pct >= 0 ? "#00c896" : "#ff4d5a", opacity: 0.9 }}
                        >
                            {fmtPct(index.change_pct)}
                        </span>
                    )}
                </div>

                {/* Mini score bar */}
                {!index.error && (
                    <div
                        className="mt-1.5 h-[2px] rounded-full overflow-hidden"
                        style={{ background: "rgba(255,255,255,0.05)" }}
                    >
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${index.score}%`, backgroundColor: sc }}
                        />
                    </div>
                )}
            </div>
        </button>
    );
}
