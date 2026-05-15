"use client";

import { cn } from "@/lib/utils";
import type { SessionContext, CapitalShield, FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    session?: SessionContext | null;
    shield?: CapitalShield | null;
    symbol: string;
}

const SESSION_LABELS: Record<string, { label: string; color: string }> = {
    PRE_OPEN: { label: "Pre-Open", color: "text-t3" },
    OPENING_VOLATILITY: { label: "Opening ⚡", color: "text-wait" },
    MIDDAY_CHOP: { label: "Mid-Day", color: "text-bl" },
    POWER_HOUR: { label: "Power Hour 🔥", color: "text-bull" },
    CLOSING: { label: "Closing", color: "text-wait" },
    POST_CLOSE: { label: "Post-Close", color: "text-t3" },
    EXPIRY_MORNING: { label: "EXPIRY ⚠", color: "text-bear" },
};

export function TopHUD({ verdict, session, shield, symbol }: Props) {
    const sess = SESSION_LABELS[session?.session ?? ""] ?? { label: session?.session ?? "—", color: "text-t3" };
    const ddUsed = shield && shield.daily_dd_limit > 0
        ? (shield.daily_dd_pct / shield.daily_dd_limit) * 100
        : 0;

    return (
        <div className="w-full flex items-center gap-0 px-0 h-[44px] border-b border-b bg-bg2 overflow-x-auto">
            {/* Logo */}
            <div className="px-4 h-full flex items-center border-r border-b shrink-0">
                <span className="font-mono text-[11px] font-black text-bull tracking-[3px]">FM·TA</span>
            </div>

            {/* Chips */}
            <HudChip label="INDEX" value={symbol} mono />
            <HudChip label="SESSION" value={sess.label} valueClass={sess.color} />
            <HudChip
                label="REGIME"
                value={verdict?.regime?.replace(/_/g, " ") ?? "—"}
                valueClass={
                    verdict?.regime === "BULL_TREND" ? "text-bull" :
                        verdict?.regime === "BEAR_TREND" ? "text-bear" :
                            verdict?.regime === "VOLATILE" ? "text-wait" : "text-t2"
                }
            />
            <HudChip
                label="RISK"
                value={shield?.risk_state ?? "—"}
                valueClass={
                    shield?.risk_state === "LOW" ? "text-bull" :
                        shield?.risk_state === "MODERATE" ? "text-wait" :
                            shield?.risk_state === "HIGH" ? "text-bear" : "text-bear"
                }
            />
            <HudChip
                label="SCORE"
                value={verdict ? `${verdict.execution_score}/100` : "—"}
                valueClass={
                    (verdict?.execution_score ?? 0) >= 80 ? "text-bull" :
                        (verdict?.execution_score ?? 0) >= 65 ? "text-bl" : "text-t2"
                }
                mono
            />
            <HudChip
                label="HEDGE"
                value={verdict?.hedge_active ? "ACTIVE" : "NONE"}
                valueClass={verdict?.hedge_active ? "text-hedge" : "text-t3"}
            />

            {/* Kill switch warning */}
            {shield?.kill_switch && (
                <div className="ml-auto px-3 h-full flex items-center bg-bear/10 border-l border-bear/40 shrink-0">
                    <span className="font-mono text-[10px] font-black text-bear animate-pulse-slow">
                        🔴 KILL SWITCH ACTIVE
                    </span>
                </div>
            )}

            {/* Daily DD bar */}
            {shield && !shield.kill_switch && (
                <div className="ml-auto px-3 h-full flex items-center gap-2 border-l border-b shrink-0">
                    <span className="font-mono text-[9px] text-t3 uppercase tracking-[1px]">Daily DD</span>
                    <div className="w-[60px] h-[4px] bg-b2 rounded-full overflow-hidden">
                        <div
                            className={cn("h-full rounded-full transition-all", ddUsed > 70 ? "bg-bear" : ddUsed > 40 ? "bg-wait" : "bg-bull")}
                            style={{ width: `${Math.min(100, ddUsed)}%` }}
                        />
                    </div>
                    <span className={cn("font-mono text-[10px] font-bold", ddUsed > 70 ? "text-bear" : "text-t3")}>
                        {shield.daily_dd_pct.toFixed(2)}%
                    </span>
                </div>
            )}

            {/* IST time */}
            {session?.ist_time && (
                <div className="px-3 h-full flex items-center border-l border-b shrink-0">
                    <span className="font-mono text-[11px] text-t3">{session.ist_time} IST</span>
                </div>
            )}
        </div>
    );
}

function HudChip({ label, value, valueClass, mono }: {
    label: string; value: string; valueClass?: string; mono?: boolean;
}) {
    return (
        <div className="px-3 h-full flex flex-col justify-center border-r border-b shrink-0 min-w-[80px]">
            <div className="font-mono text-[8px] text-t3 uppercase tracking-[1px] leading-none mb-[3px]">{label}</div>
            <div className={cn("font-mono text-[11px] font-bold leading-none", valueClass ?? "text-t1")}>
                {value}
            </div>
        </div>
    );
}
