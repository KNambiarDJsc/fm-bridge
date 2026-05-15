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

const SESSION_META: Record<string, { label: string; color: string }> = {
    PRE_OPEN: { label: "Pre-Open", color: "var(--t3)" },
    OPENING_VOLATILITY: { label: "Opening ⚡", color: "var(--wait)" },
    MIDDAY_CHOP: { label: "Mid-Day", color: "var(--bl)" },
    POWER_HOUR: { label: "Power Hour", color: "var(--bull)" },
    CLOSING: { label: "Closing", color: "var(--wait)" },
    POST_CLOSE: { label: "Post-Close", color: "var(--t3)" },
    EXPIRY_MORNING: { label: "EXPIRY ⚠", color: "var(--bear)" },
};

const REGIME_COLOR: Record<string, string> = {
    BULL_TREND: "var(--bull)",
    BEAR_TREND: "var(--bear)",
    VOLATILE: "var(--wait)",
    RANGE: "var(--bl)",
    EVENT_DRIVEN: "var(--hedge)",
    TRAP: "var(--bear)",
};

function LiveClock({ istTime }: { istTime?: string }) {
    const [t, setT] = useState(istTime ?? "");
    useEffect(() => {
        if (istTime) { setT(istTime); return; }
        const tick = () => setT(
            new Date().toLocaleTimeString("en-IN", {
                hour: "2-digit", minute: "2-digit", second: "2-digit",
                timeZone: "Asia/Kolkata",
            })
        );
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [istTime]);
    return <>{t} IST</>;
}

export function TopHUD({ verdict, session, shield, symbol }: Props) {
    const sess = SESSION_META[session?.session ?? ""] ?? { label: "—", color: "var(--t3)" };
    const regime = verdict?.regime ?? "";
    const regimeColor = REGIME_COLOR[regime] ?? "var(--t3)";
    const score = verdict?.execution_score ?? 0;
    const ddUsed = shield && shield.daily_dd_limit > 0
        ? (shield.daily_dd_pct / shield.daily_dd_limit) * 100
        : 0;
    const verdictColor =
        verdict?.verdict === "BULL_TRADE" ? "var(--bull)" :
            verdict?.verdict === "BEAR_TRADE" ? "var(--bear)" :
                verdict?.verdict === "HEDGE_TRADE" ? "var(--hedge)" :
                    verdict?.verdict === "WAIT" ? "var(--wait)" : "var(--t3)";

    return (
        <div
            className="w-full h-[48px] flex items-stretch shrink-0 overflow-x-auto"
            style={{
                background: "var(--bg2)",
                borderBottom: "1px solid var(--b)",
            }}
        >
            {/* Regime accent line across the very top */}
            <div
                className="absolute top-0 left-0 right-0 h-[2px] pointer-events-none"
                style={{
                    background: `linear-gradient(90deg, transparent 0%, ${regimeColor}70 40%, ${regimeColor}70 60%, transparent 100%)`,
                    zIndex: 2,
                }}
            />

            {/* LOGO */}
            <div className="px-4 flex items-center gap-2 border-r border-[var(--b)] shrink-0">
                <div
                    className="w-2 h-2 rounded-full live-dot"
                    style={{ backgroundColor: regimeColor, boxShadow: `0 0 6px ${regimeColor}` }}
                />
                <span className="font-mono text-[13px] font-black tracking-[3px]" style={{ color: regimeColor }}>
                    FM
                </span>
                <span className="font-mono text-[13px] font-black text-t3 tracking-[2px]">·TA</span>
            </div>

            {/* INDEX */}
            <Cell
                label="INDEX"
                value={symbol.replace("NIFTY ", "N·")}
                valueColor="var(--t1)"
            />

            {/* SESSION */}
            <Cell label="SESSION" value={sess.label} valueColor={sess.color} />

            {/* REGIME */}
            <Cell
                label="REGIME"
                value={regime.replace(/_/g, " ") || "—"}
                valueColor={regimeColor}
            />

            {/* SCORE */}
            <div className="px-4 flex flex-col justify-center border-r border-[var(--b)] shrink-0 min-w-[88px]">
                <div className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.08em] mb-[3px]">SCORE</div>
                <div className="flex items-baseline gap-1">
                    <span
                        className="font-mono text-[15px] font-black tabular-nums"
                        style={{
                            color: score >= 80 ? "var(--bull)" : score >= 65 ? "var(--bl)" : score > 0 ? "var(--t2)" : "var(--t3)",
                        }}
                    >
                        {score > 0 ? score : "—"}
                    </span>
                    {score > 0 && (
                        <span className="font-mono text-[10px] text-t3">/100</span>
                    )}
                </div>
                {score > 0 && (
                    <div className="mt-1 h-[2px] bg-[var(--b)] rounded-full overflow-hidden" style={{ width: "52px" }}>
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                                width: `${score}%`,
                                backgroundColor: score >= 80 ? "var(--bull)" : score >= 65 ? "var(--bl)" : "var(--wait)",
                            }}
                        />
                    </div>
                )}
            </div>

            {/* VERDICT */}
            {verdict && (
                <Cell
                    label="VERDICT"
                    value={verdict.verdict.replace("_TRADE", "").replace("_", " ")}
                    valueColor={verdictColor}
                />
            )}

            {/* RISK */}
            <Cell
                label="RISK"
                value={shield?.risk_state ?? "—"}
                valueColor={
                    shield?.risk_state === "LOW" ? "var(--bull)" :
                        shield?.risk_state === "MODERATE" ? "var(--wait)" : "var(--bear)"
                }
            />

            <div className="flex-1" />

            {/* KILL SWITCH */}
            {shield?.kill_switch && (
                <div
                    className="flex items-center px-4 shrink-0 border-l border-[var(--bear)]/30 animate-pulse-slow"
                    style={{ background: "rgba(255,85,97,0.1)" }}
                >
                    <span className="font-mono text-[11px] font-black text-[var(--bear)] tracking-wide">
                        ⬛ KILL SWITCH
                    </span>
                </div>
            )}

            {/* DD */}
            {shield && !shield.kill_switch && (
                <div className="flex items-center gap-2.5 px-4 border-l border-[var(--b)] shrink-0">
                    <span className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.08em]">DD</span>
                    <div className="w-[52px] h-[3px] bg-[var(--b)] rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all"
                            style={{
                                width: `${Math.min(100, ddUsed)}%`,
                                backgroundColor: ddUsed > 70 ? "var(--bear)" : ddUsed > 40 ? "var(--wait)" : "var(--bull)",
                            }}
                        />
                    </div>
                    <span
                        className="font-mono text-[11px] font-bold tabular-nums"
                        style={{ color: ddUsed > 70 ? "var(--bear)" : "var(--t2)" }}
                    >
                        {shield.daily_dd_pct.toFixed(2)}%
                    </span>
                </div>
            )}

            {/* CLOCK */}
            <div className="flex items-center px-4 border-l border-[var(--b)] shrink-0">
                <span className="font-mono text-[11px] text-t2 tabular-nums">
                    <LiveClock istTime={session?.ist_time} />
                </span>
            </div>
        </div>
    );
}

function Cell({ label, value, valueColor }: {
    label: string; value: string; valueColor: string;
}) {
    return (
        <div className="px-4 flex flex-col justify-center border-r border-[var(--b)] shrink-0 min-w-[80px]">
            <div className="font-mono text-[10px] font-bold text-t3 uppercase tracking-[0.08em] mb-[3px] leading-none">
                {label}
            </div>
            <div
                className="font-mono text-[13px] font-bold leading-none"
                style={{ color: valueColor }}
            >
                {value}
            </div>
        </div>
    );
}
