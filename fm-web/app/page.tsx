"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import Link from "next/link";
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
import { Play, MessageCircle, AlertCircle, BarChart2, X, BookOpen, Bell, Clock, RefreshCw } from "lucide-react";
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
    const [isWatching, setIsWatching] = useState(false);   // trader told alerts to watch this verdict
    const [watchError, setWatchError] = useState<string | null>(null);
    const [elapsedSec, setElapsedSec] = useState(0);       // pipeline elapsed timer
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

    // ── Elapsed timer while analysis runs ───────────────────────
    useEffect(() => {
        if (isAnalyzing) {
            setElapsedSec(0);
            timerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);
        } else {
            if (timerRef.current) clearInterval(timerRef.current);
        }
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, [isAnalyzing]);

    // ── "I'm watching this" — tell fm-alerts price monitor ──────
    // This is NOT trade execution. The trader places the trade themselves
    // on Zerodha. This just activates Telegram price alerts (entry zone,
    // T1/T2 hit, SL hit, hedge adjustment) for the current verdict.
    const handleWatchVerdict = useCallback(async () => {
        if (!verdict?.trade_plan) return;
        const tp = verdict.trade_plan;
        const hp = verdict.hedge_plan;
        try {
            const r = await fetch("/api/alerts/trade/set", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    symbol: verdict.best_index,
                    verdict: verdict.verdict,
                    direction: tp.direction,
                    entry_low: tp.entry_low,
                    entry_high: tp.entry_high,
                    stop_loss: tp.stop_loss,
                    target1: tp.target1,
                    target2: tp.target2,
                    target3: tp.target3 ?? null,
                    instrument: tp.instrument,
                    rr_ratio: tp.rr,
                    execution_score: verdict.execution_score,
                    confidence: verdict.confidence,
                    hedge_type: hp?.hedge_type ?? "NONE",
                    hedge_strike: hp?.strike ?? null,
                    ic_short_call: hp?.sell_ce ?? null,
                    ic_short_put: hp?.sell_pe ?? null,
                    units: 1,
                }),
            });
            if (r.ok) {
                setIsWatching(true);
                setWatchError(null);
            } else {
                setWatchError("Alerts service unavailable — check fm-alerts is running on :8005");
            }
        } catch {
            setWatchError("Could not reach alerts service (:8005)");
        }
    }, [verdict]);

    const handleClearWatch = useCallback(async () => {
        await fetch("/api/alerts/trade", { method: "DELETE" }).catch(() => { });
        setIsWatching(false);
        setWatchError(null);
    }, []);

    // Derive regime from verdict for env theming
    const regime = verdict?.regime ?? "UNKNOWN";

    return (
        <div
            className="flex flex-col h-screen overflow-hidden"
            style={{ background: "var(--bg)" }}
            data-regime={regime}
        >

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
                                    "flex items-center gap-2 px-5 py-2.5 rounded-xl font-mono text-[12px] font-black",
                                    "transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed magnetic",
                                    isAnalyzing
                                        ? "border border-bl/40 text-bl"
                                        : "border border-[var(--accent-edge)] text-[var(--accent)] hover:shadow-glow-sm active:scale-95"
                                )}
                                style={{ background: isAnalyzing ? "rgba(58,158,255,0.07)" : "var(--accent-dim)" }}
                            >
                                {isAnalyzing
                                    ? <Clock size={12} className="animate-spin" />
                                    : <Play size={12} />
                                }
                                {isAnalyzing ? `Analysing… ${elapsedSec}s` : "▶  RUN ANALYSIS"}
                            </button>

                            {/* "I'm watching this" — activates Telegram price alerts */}
                            {verdict && verdict.verdict !== "WAIT" && verdict.trade_plan && (
                                isWatching
                                    ? <button
                                        onClick={handleClearWatch}
                                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-[11px] border border-bull/40 bg-bull/10 text-bull hover:bg-bear/10 hover:border-bear/40 hover:text-bear transition-all"
                                        title="Stop watching — clears price alerts"
                                    >
                                        <Bell size={11} className="animate-pulse" />
                                        Watching — tap to stop
                                    </button>
                                    : <button
                                        onClick={handleWatchVerdict}
                                        className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl font-mono text-[11px] font-bold transition-all lift" style={{ background: "#131924", border: "1px solid #1e2d45", color: "#9dafc8" }}
                                        title="Watch this verdict — get Telegram alerts when price hits entry zone, T1, T2, or SL"
                                    >
                                        <Bell size={11} />
                                        Watch levels
                                    </button>
                            )}

                            {/* Journal link */}
                            <Link
                                href="/journal"
                                className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl font-mono text-[11px] font-bold transition-all lift ml-auto" style={{ background: "#131924", border: "1px solid #1e2d45", color: "#9dafc8" }}
                            >
                                <BookOpen size={11} />
                                Journal
                            </Link>

                            {/* Index selector */}
                            <select
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="rounded-xl px-3 py-2.5 font-mono text-[12px] font-bold text-t1 outline-none cursor-pointer" style={{ background: "#131924", border: "1px solid #1e2d45", color: "#f0f4ff" }}
                            >
                                {INDICES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>

                            {/* Chart toggle */}
                            <button
                                onClick={() => setShowChart(v => !v)}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-[11px] border transition-all",
                                    showChart ? "" : ""
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
                                    chatOpen ? "" : ""
                                )}
                            >
                                <MessageCircle size={12} />
                                Copilot
                            </button>
                        </div>

                        {/* Slow pipeline warning (>30s) */}
                        {isAnalyzing && elapsedSec >= 30 && (
                            <div className="flex items-center gap-2 px-4 py-2.5 bg-[#e8a020]/5 border border-[#e8a020]/20 rounded-lg">
                                <Clock size={12} className="text-[#e8a020] shrink-0" />
                                <span className="font-mono text-[11px] text-[#e8a020]">
                                    Pipeline is taking longer than usual ({elapsedSec}s). Gemini may be busy — wait up to 90s.
                                </span>
                            </div>
                        )}

                        {/* Watch error */}
                        {watchError && (
                            <div className="flex items-center gap-2 px-4 py-2.5 bg-bear/5 border border-bear/20 rounded-lg">
                                <AlertCircle size={12} className="text-bear shrink-0" />
                                <span className="font-mono text-[11px] text-bear flex-1">{watchError}</span>
                                <button onClick={() => setWatchError(null)} className="text-t3 hover:text-t1">
                                    <X size={12} />
                                </button>
                            </div>
                        )}

                        {/* Error — with retry */}
                        {error && (
                            <div className="flex items-center gap-2 px-4 py-2.5 bg-bear/5 border border-bear/20 rounded-lg">
                                <AlertCircle size={12} className="text-bear shrink-0" />
                                <span className="font-mono text-[11px] text-bear flex-1">{error}</span>
                                <button
                                    onClick={() => { setError(null); handleAnalyze(); }}
                                    className="flex items-center gap-1 font-mono text-[10px] text-[#3a9eff] border border-[#3a9eff]/30 rounded px-2 py-0.5 hover:bg-[#3a9eff]/10"
                                >
                                    <RefreshCw size={10} /> Retry
                                </button>
                                <button onClick={() => setError(null)} className="text-t3 hover:text-t1 ml-1">
                                    <X size={12} />
                                </button>
                            </div>
                        )}

                        {/* ── VERDICT BANNER — THE PRODUCT ─────────────── */}
                        <VerdictBanner verdict={verdict} isAnalyzing={isAnalyzing} elapsedSec={elapsedSec} />

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
