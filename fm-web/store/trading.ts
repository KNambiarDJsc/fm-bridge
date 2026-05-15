"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FinalVerdict, IndexScore, CapitalShield, SessionContext } from "@/lib/types";

// ── Analysis store ────────────────────────────────────────────

interface AnalysisStore {
    symbol: string;
    verdict: FinalVerdict | null;
    isAnalyzing: boolean;
    lastAnalyzed: string | null;
    error: string | null;
    agentOutputs: Record<string, Record<string, unknown>>;
    setSymbol: (s: string) => void;
    setAnalyzing: (v: boolean) => void;
    setVerdict: (v: FinalVerdict, agents?: Record<string, Record<string, unknown>>) => void;
    setError: (e: string | null) => void;
    clearVerdict: () => void;
}

export const useAnalysisStore = create<AnalysisStore>()(
    persist(
        (set) => ({
            symbol: "NIFTY 50",
            verdict: null,
            isAnalyzing: false,
            lastAnalyzed: null,
            error: null,
            agentOutputs: {},
            setSymbol: (s) => set({ symbol: s }),
            setAnalyzing: (v) => set({ isAnalyzing: v, error: null }),
            setVerdict: (v, agents = {}) => set({
                verdict: v, isAnalyzing: false, error: null,
                lastAnalyzed: new Date().toISOString(), agentOutputs: agents,
            }),
            setError: (e) => set({ error: e, isAnalyzing: false }),
            clearVerdict: () => set({ verdict: null, lastAnalyzed: null, agentOutputs: {} }),
        }),
        { name: "fm-analysis", partialize: (s) => ({ symbol: s.symbol }) }
    )
);

// ── Capital store ─────────────────────────────────────────────

interface CapitalStore {
    shield: CapitalShield | null;
    session: SessionContext | null;
    setShield: (s: CapitalShield) => void;
    setSession: (s: SessionContext) => void;
}

export const useCapitalStore = create<CapitalStore>()((set) => ({
    shield: null, session: null,
    setShield: (s) => set({ shield: s }),
    setSession: (s) => set({ session: s }),
}));

// ── Heatmap store ─────────────────────────────────────────────

interface HeatmapStore {
    indices: IndexScore[];
    best: IndexScore | null;
    lastFetch: number;
    setHeatmap: (indices: IndexScore[], best?: IndexScore) => void;
}

export const useHeatmapStore = create<HeatmapStore>()((set) => ({
    indices: [], best: null, lastFetch: 0,
    setHeatmap: (indices, best) => set({ indices, best: best ?? null, lastFetch: Date.now() }),
}));

// ── UI store ──────────────────────────────────────────────────

type ActiveSection = "A" | "B" | "C" | "D";

interface UIStore {
    activeSection: ActiveSection;
    chatOpen: boolean;
    setSection: (s: ActiveSection) => void;
    toggleChat: () => void;
}

export const useUIStore = create<UIStore>()(
    persist(
        (set) => ({
            activeSection: "A",
            chatOpen: false,
            setSection: (s) => set({ activeSection: s }),
            toggleChat: () => set((st) => ({ chatOpen: !st.chatOpen })),
        }),
        { name: "fm-ui" }
    )
);
