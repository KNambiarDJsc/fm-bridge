"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { SessionContext, CapitalShield, FinalVerdict } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    session?: SessionContext | null;
    shield?: CapitalShield | null;
    symbol: string;
}

const SESSION_META: Record<string, { label: string; color: string }> = {
    PRE_OPEN:            { label: "Pre-Open",     color: "var(--t3)" },
    OPENING_VOLATILITY:  { label: "Opening",      color: "var(--wait)" },
    MIDDAY_CHOP:         { label: "Mid-Day",      color: "var(--blue)" },
    POWER_HOUR:          { label: "Power Hour",   color: "var(--bull)" },
    CLOSING:             { label: "Closing",       color: "var(--wait)" },
    POST_CLOSE:          { label: "Post-Close",   color: "var(--t3)" },
    EXPIRY_MORNING:      { label: "Expiry",       color: "var(--bear)" },
};

const REGIME_COLOR: Record<string, string> = {
    BULL_TREND:    "var(--bull)",
    BEAR_TREND:    "var(--bear)",
    VOLATILE:      "var(--wait)",
    RANGE:         "var(--blue)",
    EVENT_DRIVEN:  "var(--hedge)",
    TRAP:          "var(--bear)",
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
    return <>{t}</>;
}

export function TopHUD({ verdict, session, shield, symbol }: Props) {
    const sess = SESSION_META[session?.session ?? ""] ?? { label: "—", color: "var(--t3)" };
    const regime = verdict?.regime ?? "";
    const regimeColor = REGIME_COLOR[regime] ?? "var(--t3)";
    const score = verdict?.execution_score ?? 0;
    const ddUsed = shield && shield.daily_dd_limit > 0
        ? (shield.daily_dd_pct / shield.daily_dd_limit) * 100
        : 0;

    return (
        <header className="w-full h-11 flex items-stretch shrink-0 relative"
            style={{ background: "var(--bg-s)", borderBottom: "1px solid var(--b)" }}>

            {/* Regime accent — thin top line */}
            <div className="absolute top-0 inset-x-0 h-px pointer-events-none"
                style={{ background: `linear-gradient(90deg, transparent, ${regimeColor}50, transparent)` }} />

            {/* Brand */}
            <div className="px-4 flex items-center gap-2 shrink-0" style={{ borderRight: "1px solid var(--b)" }}>
                <div className="w-1.5 h-1.5 rounded-full live-dot" style={{ backgroundColor: regimeColor }} />
                <Link href="/" className="font-mono text-12 font-bold tracking-[0.15em] text-t1 hover:text-t0 transition-colors">
                    SOVEREIGN
                </Link>
            </div>

            {/* Cells */}
            <Cell label="INDEX" value={symbol.replace("NIFTY ", "N·")} color="var(--t1)" />
            <Cell label="SESSION" value={sess.label} color={sess.color} />
            <Cell label="REGIME" value={regime.replace(/_/g, " ") || "—"} color={regimeColor} />

            {/* Score with micro-bar */}
            <div className="px-3 flex flex-col justify-center shrink-0" style={{ borderRight: "1px solid var(--b)" }}>
                <div className="font-mono text-10 text-t3 tracking-wider mb-0.5">SCORE</div>
                <div className="flex items-baseline gap-1">
                    <span className="font-mono text-13 font-bold tabular-nums"
                        style={{ color: score >= 80 ? "var(--bull)" : score >= 65 ? "var(--blue)" : score > 0 ? "var(--t2)" : "var(--t3)" }}>
                        {score > 0 ? score : "—"}
                    </span>
                    {score > 0 && <span className="font-mono text-10 text-t3">/100</span>}
                </div>
            </div>

            {/* Verdict */}
            {verdict && (
                <Cell
                    label="VERDICT"
                    value={verdict.verdict.replace("_TRADE", "").replace("_", " ")}
                    color={REGIME_COLOR[regime] ?? "var(--t3)"}
                />
            )}

            {/* Risk */}
            <Cell
                label="RISK"
                value={shield?.risk_state ?? "—"}
                color={
                    shield?.risk_state === "LOW" ? "var(--bull)" :
                    shield?.risk_state === "MODERATE" ? "var(--wait)" : "var(--bear)"
                }
            />

            <div className="flex-1" />

            {/* Kill switch */}
            {shield?.kill_switch && (
                <div className="flex items-center px-3 shrink-0 animate-pulse-slow"
                    style={{ background: "rgba(248,113,113,0.06)", borderLeft: "1px solid rgba(248,113,113,0.2)" }}>
                    <span className="font-mono text-10 font-bold text-bear tracking-wider">KILL SWITCH</span>
                </div>
            )}

            {/* Drawdown */}
            {shield && !shield.kill_switch && (
                <div className="flex items-center gap-2 px-3 shrink-0" style={{ borderLeft: "1px solid var(--b)" }}>
                    <span className="font-mono text-10 text-t3">DD</span>
                    <div className="w-10 h-[3px] rounded-full overflow-hidden" style={{ background: "var(--b)" }}>
                        <div className="h-full rounded-full transition-all duration-700"
                            style={{
                                width: `${Math.min(100, ddUsed)}%`,
                                backgroundColor: ddUsed > 70 ? "var(--bear)" : ddUsed > 40 ? "var(--wait)" : "var(--bull)",
                            }} />
                    </div>
                    <span className="font-mono text-11 tabular-nums"
                        style={{ color: ddUsed > 70 ? "var(--bear)" : "var(--t2)" }}>
                        {shield.daily_dd_pct.toFixed(1)}%
                    </span>
                </div>
            )}

            {/* Clock */}
            <div className="flex items-center px-4 shrink-0" style={{ borderLeft: "1px solid var(--b)" }}>
                <span className="font-mono text-11 text-t2 tabular-nums">
                    <LiveClock istTime={session?.ist_time} />
                </span>
            </div>
        </header>
    );
}

function Cell({ label, value, color }: { label: string; value: string; color: string }) {
    return (
        <div className="px-3 flex flex-col justify-center shrink-0 min-w-[72px]"
            style={{ borderRight: "1px solid var(--b)" }}>
            <div className="font-mono text-10 text-t3 tracking-wider leading-none mb-0.5">{label}</div>
            <div className="font-mono text-12 font-semibold leading-none truncate" style={{ color }}>{value}</div>
        </div>
    );
}
