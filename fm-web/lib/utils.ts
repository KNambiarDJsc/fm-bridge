import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { VerdictType, RiskState } from "./types";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const VERDICT_COLORS: Record<VerdictType, {
    bg: string; border: string; text: string; glow: string; hex: string;
}> = {
    BULL_TRADE: { bg: "bg-bull/10", border: "border-bull", text: "text-bull", glow: "shadow-verdict-bull", hex: "var(--bull)" },
    BEAR_TRADE: { bg: "bg-bear/10", border: "border-bear", text: "text-bear", glow: "shadow-verdict-bear", hex: "var(--bear)" },
    HEDGE_TRADE: { bg: "bg-hedge/10", border: "border-hedge", text: "text-hedge", glow: "shadow-verdict-hedge", hex: "var(--hedge)" },
    WAIT: { bg: "bg-wait/10", border: "border-wait", text: "text-wait", glow: "shadow-verdict-wait", hex: "var(--wait)" },
};

export const VERDICT_LABELS: Record<VerdictType, string> = {
    BULL_TRADE: "BULL TRADE", BEAR_TRADE: "BEAR TRADE",
    HEDGE_TRADE: "HEDGE TRADE", WAIT: "WAIT",
};

export const RISK_COLORS: Record<RiskState, string> = {
    LOW: "text-bull", MODERATE: "text-wait", HIGH: "text-bear", CRITICAL: "text-bear",
};

export const REGIME_LABELS: Record<string, string> = {
    BULL_TREND: "Bull Trend", BEAR_TREND: "Bear Trend", RANGE: "Range",
    VOLATILE: "Volatile", TRAP: "Trap", EVENT_DRIVEN: "Event Driven", UNKNOWN: "Unknown",
};

export const fmtPrice = (n?: number | null): string =>
    n == null ? "—" : new Intl.NumberFormat("en-IN").format(Math.round(n));

export const fmtPct = (n?: number | null, decimals = 2): string =>
    n == null ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(decimals)}%`;

export const fmtCr = (n?: number | null): string =>
    n == null ? "—" : `${n >= 0 ? "+" : ""}₹${Math.abs(n).toLocaleString("en-IN")}Cr`;

export const fmtRs = (n?: number | null): string =>
    n == null ? "—" : `₹${Math.round(n).toLocaleString("en-IN")}`;

export const fmtScore = (n?: number | null): string =>
    n == null ? "—" : `${n}/100`;

export function scoreColor(n: number): string {
    if (n >= 80) return "text-bull";
    if (n >= 65) return "text-bl";
    if (n >= 50) return "text-wait";
    return "text-bear";
}

export function timeSince(iso?: string | null): string {
    if (!iso) return "—";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return `${Math.round(diff)}s ago`;
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    return `${Math.round(diff / 3600)}h ago`;
}
