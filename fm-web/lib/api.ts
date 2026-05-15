// FM Trading Agency — API Client + TanStack Query Hooks
// All calls go through Next.js /api/* proxy routes (no direct calls to localhost:8002/8003 from browser).

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
    FinalVerdict, MultiIndexHeatmap, OptionsChain,
    MacroContext, IndicatorPack, SessionContext, CapitalShield,
} from "./types";

// In production use proxy routes. In dev, can also use direct URLs.
const BRIDGE = "/api/bridge";
const AGENTS = "/api";

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
    const res = await fetch(url, {
        ...opts,
        headers: { "Content-Type": "application/json", ...opts?.headers },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as Record<string, string>).error || `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
}

// ── Session ────────────────────────────────────────────────────
export const useSessionCtx = () =>
    useQuery<SessionContext>({
        queryKey: ["session"],
        queryFn: () => apiFetch(`${BRIDGE}/api/session`),
        refetchInterval: 30_000,
        staleTime: 15_000,
    });

// ── Capital shield ─────────────────────────────────────────────
export const useCapitalShield = () =>
    useQuery<CapitalShield>({
        queryKey: ["capital-shield"],
        queryFn: () => apiFetch(`${BRIDGE}/api/capital-shield`),
        refetchInterval: 10_000,
        staleTime: 5_000,
    });

// ── Macro context ─────────────────────────────────────────────
export const useMacroContext = () =>
    useQuery<MacroContext>({
        queryKey: ["macro-context"],
        queryFn: () => apiFetch(`${BRIDGE}/api/macro-context`),
        refetchInterval: 60_000,
        staleTime: 30_000,
    });

// ── Live price ────────────────────────────────────────────────
export const useLTP = (symbol: string) =>
    useQuery<{ price: number; symbol: string }>({
        queryKey: ["ltp", symbol],
        queryFn: () => apiFetch(`${BRIDGE}/api/ltp?index=${encodeURIComponent(symbol)}`),
        refetchInterval: 3_000,
        staleTime: 1_000,
    });

// ── Multi-index heatmap ───────────────────────────────────────
export const useMultiIndexHeatmap = () =>
    useQuery<MultiIndexHeatmap>({
        queryKey: ["multi-index"],
        queryFn: () => apiFetch(`${BRIDGE}/api/multi-index`),
        refetchInterval: 300_000,
        staleTime: 180_000,
    });

// ── Options chain ─────────────────────────────────────────────
export const useOptionsChain = (symbol: string) =>
    useQuery<OptionsChain>({
        queryKey: ["options-chain", symbol],
        queryFn: () => apiFetch(`${BRIDGE}/api/options-chain?symbol=${encodeURIComponent(symbol)}`),
        refetchInterval: 900_000,
        staleTime: 600_000,
    });

// ── Indicators ────────────────────────────────────────────────
export const useIndicators = (symbol: string) =>
    useQuery<IndicatorPack>({
        queryKey: ["indicators", symbol],
        queryFn: () => apiFetch(`${BRIDGE}/api/indicators?symbol=${encodeURIComponent(symbol)}`),
        refetchInterval: 60_000,
        staleTime: 30_000,
        select: (data: unknown) => {
            // Bridge returns the pack directly or wrapped
            const d = data as Record<string, unknown>;
            return (d.symbol ? d : d.indicators ?? d) as unknown as IndicatorPack;
        },
    });

// ── Historical OHLCV ──────────────────────────────────────────
export const useHistorical = (symbol: string, interval = "day", range = "6mo") =>
    useQuery<{ data: number[][]; count: number }>({
        queryKey: ["historical", symbol, interval, range],
        queryFn: () => apiFetch(
            `${BRIDGE}/historical?symbol=${encodeURIComponent(symbol)}&interval=${interval}&range=${range}`
        ),
        staleTime: 60_000,
    });

// ── Bridge health ─────────────────────────────────────────────
export const useBridgeHealth = () =>
    useQuery<{ status: string; logged_in: boolean; token_date?: string }>({
        queryKey: ["bridge-health"],
        queryFn: () => apiFetch(`${BRIDGE}/health`),
        refetchInterval: 30_000,
        retry: false,
    });

// ── Run full pipeline analysis ────────────────────────────────
export const useAnalyze = () => {
    const qc = useQueryClient();
    return useMutation<{ status: string; data: FinalVerdict }, Error, { symbol: string }>({
        mutationFn: ({ symbol }) =>
            apiFetch(`${AGENTS}/analyze`, {
                method: "POST",
                body: JSON.stringify({ symbol }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["session"] });
            qc.invalidateQueries({ queryKey: ["capital-shield"] });
        },
    });
};

// ── Copilot chat ──────────────────────────────────────────────
export const useChatMutation = () =>
    useMutation<{ status: string; answer: string }, Error, {
        question: string;
        symbol: string;
        context?: FinalVerdict;
    }>({
        mutationFn: (payload) =>
            apiFetch(`${AGENTS}/chat`, {
                method: "POST",
                body: JSON.stringify(payload),
            }),
    });

// ── Paper positions ───────────────────────────────────────────
export const usePositions = () =>
    useQuery<{ positions: Record<string, unknown>[] }>({
        queryKey: ["positions"],
        queryFn: () => apiFetch(`${BRIDGE}/api/positions`),
    });
