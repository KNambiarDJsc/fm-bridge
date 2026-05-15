"use client";

import { cn, fmtPrice, fmtPct } from "@/lib/utils";
import type { IndexScore } from "@/lib/types";
import { RefreshCw } from "lucide-react";

interface Props {
    indices: IndexScore[];
    best?: IndexScore | null;
    currentSymbol: string;
    onSwitch: (name: string) => void;
    onRefresh: () => void;
    isLoading?: boolean;
}

const REGIME_STYLE: Record<string, string> = {
    BULL: "text-bull",
    BEAR: "text-bear",
    SIDE: "text-t3",
};

export function IndexHeatmap({ indices, best, currentSymbol, onSwitch, onRefresh, isLoading }: Props) {
    const switchGap = best && currentSymbol !== best.name
        ? (indices.find(i => i.name === currentSymbol)?.score ?? 0)
        : 0;
    const shouldSuggestSwitch = best && switchGap > 0 && (best.score - switchGap) >= 15;

    return (
        <div className="bg-bg2 border border-b rounded-xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-b">
                <span className="font-mono text-[10px] font-bold text-t2 uppercase tracking-[2px]">
                    INDEX OPPORTUNITY HEATMAP
                </span>
                <button
                    onClick={onRefresh}
                    disabled={isLoading}
                    className="ml-auto p-1.5 rounded-md bg-bl/10 border border-bl/20 text-bl hover:bg-bl/20 transition-colors disabled:opacity-40"
                >
                    <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Switch suggestion */}
            {shouldSuggestSwitch && best && (
                <div className="px-4 py-2.5 bg-bull/5 border-b border-bull/20 flex items-center gap-2">
                    <span className="text-[10px] font-mono text-t2">🎯</span>
                    <span className="font-mono text-[11px] text-t2">
                        <b className="text-bull">{best.name}</b> scores {best.score}/100 vs {currentSymbol}'s {switchGap}/100
                        {" "}— consider switching today.
                    </span>
                    <button
                        onClick={() => onSwitch(best.name)}
                        className="ml-auto font-mono text-[10px] font-bold text-bull border border-bull/40 rounded px-2 py-0.5 hover:bg-bull/10 transition-colors"
                    >
                        Switch →
                    </button>
                </div>
            )}

            {/* Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-0 divide-x divide-y divide-b">
                {indices.map((idx) => (
                    <IndexCell
                        key={idx.name}
                        index={idx}
                        isCurrent={idx.name === currentSymbol}
                        isBest={idx.name === best?.name}
                        onClick={() => !idx.error && onSwitch(idx.name)}
                    />
                ))}

                {/* Loading skeleton */}
                {isLoading && indices.length === 0 &&
                    Array.from({ length: 10 }).map((_, i) => (
                        <div key={i} className="p-3 h-[72px] animate-pulse bg-bg3" />
                    ))
                }
            </div>
        </div>
    );
}

function IndexCell({ index, isCurrent, isBest, onClick }: {
    index: IndexScore; isCurrent: boolean; isBest: boolean; onClick: () => void;
}) {
    const regimeStyle = REGIME_STYLE[index.regime] ?? "text-t3";

    return (
        <button
            onClick={onClick}
            className={cn(
                "text-left p-3 transition-all duration-150 group",
                "hover:bg-b2/60",
                isCurrent && "bg-bl/5",
                isBest && !isCurrent && "bg-bull/5",
                index.error && "opacity-40 cursor-default",
            )}
        >
            {/* Name */}
            <div className={cn(
                "font-mono text-[9px] font-bold uppercase tracking-[0.5px] mb-1 truncate",
                isCurrent ? "text-bl" : "text-t2"
            )}>
                {index.name.replace("NIFTY ", "").replace(" 50", " 50")}
                {isCurrent && <span className="ml-1 text-bl">●</span>}
                {isBest && !isCurrent && <span className="ml-1 text-bull">★</span>}
            </div>

            {/* Score + regime */}
            <div className="flex items-baseline gap-2">
                <span className={cn(
                    "font-mono text-[18px] font-black leading-none",
                    index.error ? "text-t3" :
                        index.score >= 70 ? "text-bull" :
                            index.score >= 50 ? "text-t1" : "text-bear"
                )}>
                    {index.error ? "—" : index.score}
                </span>
                <span className={cn("font-mono text-[9px] font-bold uppercase", regimeStyle)}>
                    {index.error ? "ERR" : index.regime}
                </span>
            </div>

            {/* Price + change */}
            {!index.error && (
                <div className="font-mono text-[9px] text-t3 mt-1 flex items-center gap-1">
                    <span>{fmtPrice(index.price)}</span>
                    <span className={index.change_pct >= 0 ? "text-bull" : "text-bear"}>
                        {fmtPct(index.change_pct)}
                    </span>
                </div>
            )}
        </button>
    );
}
