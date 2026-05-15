"use client";

import { cn } from "@/lib/utils";
import type { SessionContext, CapitalShield, FinalVerdict } from "@/lib/types";
import { useEffect, useState } from "react";

interface Props {
    verdict?: FinalVerdict | null;
    session?: SessionContext | null;
    shield?: CapitalShield | null;
    symbol: string;
}

const SESSION_META: Record<string, { label: string; color: string; dot: string }> = {
    PRE_OPEN: { label: "Pre-Open", color: "text-t3", dot: "#3d4f68" },
    OPENING_VOLATILITY: { label: "Opening", color: "text-wait", dot: "#f5a623" },
    MIDDAY_CHOP: { label: "Mid-Day", color: "text-bl", dot: "#3a9eff" },
    POWER_HOUR: { label: "Power Hour", color: "text-bull", dot: "#00c896" },
    CLOSING: { label: "Closing", color: "text-wait", dot: "#f5a623" },
    POST_CLOSE: { label: "Post-Close", color: "text-t3", dot: "#3d4f68" },
    EXPIRY_MORNING: { label: "EXPIRY", color: "text-bear", dot: "#ff4d5a" },
};

const REGIME_COLOR: Record<string, string> = {
    BULL_TREND: "#00c896",
    BEAR_TREND: "#ff4d5a",
    VOLATILE: "#f5a623",
    RANGE: "#3a9eff",
    EVENT_DRIVEN: "#9d7dff",
    TRAP: "#ff4d5a",
};

// Live clock
function LiveTime({ istTime }: { istTime?: string }) {
    const [t, setT] = useState(istTime ?? "");
    useEffect(() => {
        if (istTime) { setT(istTime); return; }
        const tick = () => {
            const now = new Date();
            setT(now.toLocaleTimeString("en-IN", {
                hour: "2-digit", minute: "2-digit", second: "2-digit",
                timeZone: "Asia/Kolkata"
            }));
        };
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [istTime]);
    return <span>{t} IST</span>;
}

export function TopHUD({ verdict, session, shield, symbol }: Props) {
    const sess = SESSION_META[session?.session ?? ""] ?? { label: "—", color: "text-t3", dot: "#3d4f68" };
    const regime = verdict?.regime ?? "";
    const regimeColor = REGIME_COLOR[regime] ?? "#7d8ea8";
    const score = verdict?.execution_score ?? 0;
    const ddUsed = shield && shield.daily_dd_limit > 0
        ? (shield.daily_dd_pct / shield.daily_dd_limit) * 100
        : 0;

    return (
        <div
            className="w-full h-[44px] flex items-stretch overflow-x-auto shrink-0 relative"
            style={{
                background: "rgba(10,14,26,0.92)",
                borderBottom: "1px solid rgba(255,255,255,0.055)",
                backdropFilter: "blur(20px)",
            }}
        >
            {/* Regime-colored top edge accent */}
            <div
                className="absolute top-0 left-0 right-0 h-[1px]"
                style={{ background: `linear-gradient(90deg, transparent, ${regimeColor}60, transparent)` }}
            />

            {/* Logo */}
            <div className="px-4 flex items-center border-r border-white/[0.06] shrink-0 gap-2">
                <div className="w-[6px] h-[6px] rounded-full live-dot" style={{ backgroundColor: regimeColor }} />
                <span className="font-mono text-[11px] font-black tracking-[3px]" style={{ color: regimeColor }}>
                    FM
                </span>
                <span className="font-mono text-[11px] font-black text-t3 tracking-[2px]">·TA</span>
            </div>

            {/* INDEX */}
            <HudCell label="INDEX" value={symbol.replace("NIFTY ", "N·")} valueClass="text-t1" />

            {/* SESSION */}
            <HudCell label="SESSION" value={sess.label} valueClass={sess.color} dotColor={sess.dot} />

            {/* REGIME */}
            <HudCell
                label="REGIME"
                value={regime.replace(/_/g, " ") || "—"}
                valueStyle={{ color: regimeColor }}
            />

            {/* SCORE with mini bar */}
            <div className="px-3 flex flex-col justify-center border-r border-white/[0.05] shrink-0 min-w-[72px]">
                <div className="font-mono text-[7.5px] text-t3 uppercase tracking-[1px] leading-none mb-[3px]">SCORE</div>
                <div className={cn(
                    "font-mono text-[11px] font-bold leading-none",
                    score >= 80 ? "text-bull" : score >= 65 ? "text-bl" : "text-t2"
                )}>
                    {score > 0 ? `${score}` : "—"}
                    <span className="text-t3 text-[9px]">/100</span>
                </div>
                {score > 0 && (
                    <div className="mt-1 w-full h-[2px] bg-white/[0.05] rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                                width: `${score}%`,
                                backgroundColor: score >= 80 ? "#00c896" : score >= 65 ? "#3a9eff" : "#f5a623",
                            }}
                        />
                    </div>
                )}
            </div>

            {/* RISK STATE */}
            <HudCell
                label="RISK"
                value={shield?.risk_state ?? "—"}
                valueClass={
                    shield?.risk_state === "LOW" ? "text-bull" :
                        shield?.risk_state === "MODERATE" ? "text-wait" : "text-bear"
                }
            />

            {/* VERDICT mini */}
            {verdict && (
                <HudCell
                    label="VERDICT"
                    value={verdict.verdict.replace("_TRADE", "").replace("_", " ")}
                    valueClass={
                        verdict.verdict === "BULL_TRADE" ? "text-bull" :
                            verdict.verdict === "BEAR_TRADE" ? "text-bear" :
                                verdict.verdict === "HEDGE_TRADE" ? "text-hedge" : "text-wait"
                    }
                />
            )}

            {/* Spacer */}
            <div className="flex-1" />

            {/* KILL SWITCH */}
            {shield?.kill_switch && (
                <div className="flex items-center px-3 border-l border-bear/30 bg-bear/10 shrink-0">
                    <span className="font-mono text-[10px] font-black text-bear animate-pulse-slow">
                        ⬛ KILL SWITCH
                    </span>
                </div>
            )}

            {/* DD bar */}
            {shield && !shield.kill_switch && (
                <div className="flex items-center gap-2 px-3 border-l border-white/[0.05] shrink-0">
                    <span className="font-mono text-[8px] text-t3 uppercase tracking-[1px]">DD</span>
                    <div className="w-[48px] h-[3px] bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                                width: `${Math.min(100, ddUsed)}%`,
                                backgroundColor: ddUsed > 70 ? "#ff4d5a" : ddUsed > 40 ? "#f5a623" : "#00c896",
                            }}
                        />
                    </div>
                    <span className={cn(
                        "font-mono text-[9px] font-bold tabular-nums",
                        ddUsed > 70 ? "text-bear" : "text-t3"
                    )}>
                        {shield.daily_dd_pct.toFixed(2)}%
                    </span>
                </div>
            )}

            {/* Clock */}
            <div className="px-3 flex items-center border-l border-white/[0.05] shrink-0">
                <span className="font-mono text-[10px] text-t3 tabular-nums">
                    <LiveTime istTime={session?.ist_time} />
                </span>
            </div>
        </div>
    );
}

function HudCell({
    label, value, valueClass, valueStyle, dotColor,
}: {
    label: string;
    value: string;
    valueClass?: string;
    valueStyle?: React.CSSProperties;
    dotColor?: string;
}) {
    return (
        <div className="px-3 flex flex-col justify-center border-r border-white/[0.05] shrink-0 min-w-[72px]">
            <div className="font-mono text-[7.5px] text-t3 uppercase tracking-[1px] leading-none mb-[4px]">
                {label}
            </div>
            <div
                className={cn("font-mono text-[11px] font-bold leading-none flex items-center gap-1.5", valueClass)}
                style={valueStyle}
            >
                {dotColor && (
                    <div className="w-[5px] h-[5px] rounded-full shrink-0" style={{ backgroundColor: dotColor }} />
                )}
                {value}
            </div>
        </div>
    );
}
