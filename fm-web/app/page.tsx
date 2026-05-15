"use client";

import { useCallback, useState } from "react";
import { TopHUD } from "@/components/hud/TopHUD";
import { VerdictBanner } from "@/components/verdict/VerdictBanner";
import { IndexHeatmap } from "@/components/heatmap/IndexHeatmap";
import { SectionTabs } from "@/components/sections/SectionTabs";
import { CopilotChat } from "@/components/chat/CopilotChat";
import { PriceChart } from "@/components/chart/PriceChart";

import { useAnalysisStore, useCapitalStore, useUIStore } from "@/store/trading";
import {
    useAnalyze, useMultiIndexHeatmap, useMacroContext,
    useIndicators, useOptionsChain, useBridgeHealth,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Play, MessageCircle, AlertCircle, BarChart2, X } from "lucide-react";
import type { FinalVerdict } from "@/lib/types";

const INDICES = [
    "NIFTY 50", "BANK NIFTY", "NIFTY IT", "NIFTY AUTO", "NIFTY METAL",
    "NIFTY PHARMA", "NIFTY FMCG", "NIFTY MIDCAP 100", "NIFTY NEXT 50", "NIFTY FINANCIAL",
];

export default function Dashboard() {
    const {
        symbol, verdict, isAnalyzing, lastAnalyzed, error,
        agentOutputs, setSymbol, setAnalyzing, setVerdict, setError,
    } = useAnalysisStore();
    const { shield, session } = useCapitalStore();
    const { chatOpen, toggleChat } = useUIStore();
    const [showChart, setShowChart] = useState(false);

    // ── Queries ───────────────────────────────────────────────────
    const { mutate: runAnalysis } = useAnalyze();
    const { data: heatmapData, refetch: refreshHeatmap, isFetching: heatmapLoading } = useMultiIndexHeatmap();
    const { data: macroData } = useMacroContext();
    const { data: indicatorsData } = useIndicators(symbol);
    const { data: optionsData } = useOptionsChain(symbol);
    const { data: health } = useBridgeHealth();

    const bridgeOnline = health?.logged_in ?? false;

    // ── Run analysis ──────────────────────────────────────────────
    const handleAnalyze = useCallback(() => {
        if (isAnalyzing) return;
        setAnalyzing(true);
        runAnalysis(
            { symbol },
            {
                onSuccess: (data) => {
                    // Agent sub-outputs may be embedded in future pipeline versions
                    const raw = data as unknown as Record<string, unknown>;
                    setVerdict(data.data as FinalVerdict, {
                        l1: (raw.l1 ?? {}) as Record<string, unknown>,
                        l2: (raw.l2 ?? {}) as Record<string, unknown>,
                        l3: (raw.l3 ?? {}) as Record<string, unknown>,
                        l4: (raw.l4 ?? {}) as Record<string, unknown>,
                        l5: (raw.l5 ?? {}) as Record<string, unknown>,
                        l6: (raw.l6 ?? {}) as Record<string, unknown>,
                    });
                },
                onError: (e) => setError(e.message),
            }
        );
    }, [symbol, isAnalyzing, runAnalysis, setAnalyzing, setVerdict, setError]);

    // ── Switch index ──────────────────────────────────────────────
    const handleSwitch = useCallback((name: string) => {
        setSymbol(name);
        // If a verdict exists, patch the best_index; otherwise just switch symbol
        if (verdict) {
            setVerdict({ ...verdict, best_index: name }, agentOutputs);
        }
    }, [setSymbol, setVerdict, verdict, agentOutputs]);

    return (
        <div className="flex flex-col h-screen overflow-hidden bg-bg">

            {/* ── TOP HUD ───────────────────────────────────────────── */}
            <TopHUD verdict={verdict} session={session} shield={shield} symbol={symbol} />

            {/* ── MAIN SCROLL AREA ──────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-[1600px] mx-auto px-3 sm:px-4 py-4 space-y-4">

                    {/* Bridge offline banner */}
                    {health && !bridgeOnline && (
                        <div className="flex items-center gap-2 px-4 py-2.5 bg-bear/5 border border-bear/20 rounded-lg">
                            <AlertCircle size={12} className="text-bear shrink-0" />
                            <span className="font-mono text-[11px] text-t2">
                                Bridge offline — run{" "}
                                <code className="text-t1 bg-bg3 px-1 rounded">python fm-bridge/app.py</code>
                                {" "}for live data. Analysis runs in limited mode.
                            </span>
                        </div>
                    )}

                    {/* ── INDEX HEATMAP ─────────────────────────────────── */}
                    <IndexHeatmap
                        indices={heatmapData?.indices ?? []}
                        best={heatmapData?.best}
                        currentSymbol={symbol}
                        onSwitch={handleSwitch}
                        onRefresh={() => refreshHeatmap()}
                        isLoading={heatmapLoading}
                    />

                    {/* ── CONTROL ROW + VERDICT BANNER ─────────────────── */}
                    <div className="space-y-3">

                        {/* Controls */}
                        <div className="flex items-center gap-2 flex-wrap">

                            {/* Run button */}
                            <button
                                onClick={handleAnalyze}
                                disabled={isAnalyzing}
                                className={cn(
                                    "flex items-center gap-2 px-5 py-2.5 rounded-lg font-mono text-[12px] font-black",
                                    "border transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed",
                                    isAnalyzing
                                        ? "bg-bl/10 border-bl/40 text-bl"
                                        : "bg-bull/10 border-bull/40 text-bull hover:bg-bull/15 active:scale-95"
                                )}
                            >
                                <Play size={12} className={isAnalyzing ? "animate-spin" : ""} />
                                {isAnalyzing ? "Analysing…" : "▶  RUN ANALYSIS"}
                            </button>

                            {/* Index selector */}
                            <select
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="bg-bg3 border border-b rounded-lg px-3 py-2 font-mono text-[11px] text-t1 outline-none focus:border-bl/50 cursor-pointer"
                            >
                                {INDICES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>

                            {/* Chart toggle */}
                            <button
                                onClick={() => setShowChart(v => !v)}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-[11px] border transition-all",
                                    showChart ? "bg-bl/10 border-bl/30 text-bl" : "bg-bg3 border-b text-t3 hover:text-t1"
                                )}
                            >
                                <BarChart2 size={12} />
                                Chart
                            </button>

                            {/* Last run */}
                            {lastAnalyzed && !isAnalyzing && (
                                <span className="font-mono text-[10px] text-t3 ml-auto hidden sm:block">
                                    {new Date(lastAnalyzed).toLocaleTimeString("en-IN")}
                                    {verdict?.pipeline_ms != null && ` · ${(verdict.pipeline_ms / 1000).toFixed(1)}s`}
                                </span>
                            )}

                            {/* Copilot toggle */}
                            <button
                                onClick={toggleChat}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-[11px] border transition-all",
                                    chatOpen ? "bg-bl/10 border-bl/30 text-bl" : "bg-bg3 border-b text-t3 hover:text-t1"
                                )}
                            >
                                <MessageCircle size={12} />
                                Copilot
                            </button>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="flex items-center gap-2 px-4 py-2.5 bg-bear/5 border border-bear/20 rounded-lg">
                                <AlertCircle size={12} className="text-bear shrink-0" />
                                <span className="font-mono text-[11px] text-bear flex-1">{error}</span>
                                <button onClick={() => setError(null)} className="text-t3 hover:text-t1 ml-auto">
                                    <X size={12} />
                                </button>
                            </div>
                        )}

                        {/* ── VERDICT BANNER — THE PRODUCT ─────────────── */}
                        <VerdictBanner verdict={verdict} isAnalyzing={isAnalyzing} />

                    </div>

                    {/* ── PRICE CHART (collapsible) ─────────────────────── */}
                    {showChart && (
                        <PriceChart symbol={symbol} interval="day" range="6mo" height={260} />
                    )}

                    {/* ── 4-SECTION ANALYSIS PANEL ─────────────────────── */}
                    <SectionTabs
                        verdict={verdict}
                        indicators={indicatorsData}
                        options={optionsData}
                        macro={macroData}
                        shield={shield ?? undefined}
                        agentOutputs={agentOutputs}
                        symbol={symbol}
                    />

                    <div className="h-6" />
                </div>
            </div>

            {/* ── COPILOT CHAT DRAWER ───────────────────────────────── */}
            {chatOpen && (
                <div className="h-[320px] shrink-0 border-t border-b animate-slide-up">
                    <CopilotChat onClose={toggleChat} />
                </div>
            )}

        </div>
    );
}
