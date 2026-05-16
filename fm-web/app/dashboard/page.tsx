"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
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
import { Play, Terminal, AlertCircle, BarChart2, X, BookOpen, Bell, Clock, RefreshCw } from "lucide-react";
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
    const [isWatching, setIsWatching] = useState(false);
    const [watchError, setWatchError] = useState<string | null>(null);
    const [elapsedSec, setElapsedSec] = useState(0);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // ── Queries ───────────────────────────────────────────
    const { mutate: runAnalysis } = useAnalyze();
    const { data: heatmapData, refetch: refreshHeatmap, isFetching: heatmapLoading } = useMultiIndexHeatmap();
    const { data: macroData } = useMacroContext();
    const { data: indicatorsData } = useIndicators(symbol);
    const { data: optionsData } = useOptionsChain(symbol);
    const { data: health } = useBridgeHealth();

    const bridgeOnline = health?.logged_in ?? false;

    // ── Run analysis ──────────────────────────────────────
    const handleAnalyze = useCallback(() => {
        if (isAnalyzing) return;
        setAnalyzing(true);
        runAnalysis(
            { symbol },
            {
                onSuccess: (data) => {
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

    // ── Switch index ──────────────────────────────────────
    const handleSwitch = useCallback((name: string) => {
        setSymbol(name);
        if (verdict) {
            setVerdict({ ...verdict, best_index: name }, agentOutputs);
        }
    }, [setSymbol, setVerdict, verdict, agentOutputs]);

    // ── Elapsed timer ─────────────────────────────────────
    useEffect(() => {
        if (isAnalyzing) {
            setElapsedSec(0);
            timerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);
        } else {
            if (timerRef.current) clearInterval(timerRef.current);
        }
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, [isAnalyzing]);

    // ── Watch verdict (Telegram alerts) ───────────────────
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
                    entry_low: tp.entry_low, entry_high: tp.entry_high,
                    stop_loss: tp.stop_loss,
                    target1: tp.target1, target2: tp.target2,
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
            if (r.ok) { setIsWatching(true); setWatchError(null); }
            else { setWatchError("Alerts service unavailable"); }
        } catch { setWatchError("Could not reach alerts service"); }
    }, [verdict]);

    const handleClearWatch = useCallback(async () => {
        await fetch("/api/alerts/trade", { method: "DELETE" }).catch(() => {});
        setIsWatching(false); setWatchError(null);
    }, []);

    const regime = verdict?.regime ?? "UNKNOWN";

    return (
        <div className="flex flex-col h-screen overflow-hidden" data-regime={regime}
            style={{ background: "var(--bg)" }}>

            {/* ── TOP HUD ──────────────────────────────────── */}
            <TopHUD verdict={verdict} session={session} shield={shield} symbol={symbol} />

            {/* ── MAIN ─────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-[1600px] mx-auto px-4 py-4 space-y-3">

                    {/* Bridge offline */}
                    {health && !bridgeOnline && (
                        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-11 text-t2"
                            style={{ background: "rgba(248,113,113,0.04)", border: "1px solid rgba(248,113,113,0.12)" }}>
                            <AlertCircle size={12} className="text-bear shrink-0" />
                            Bridge offline — run <code className="text-t1 px-1 rounded" style={{ background: "var(--bg-e)" }}>python fm-bridge/app.py</code> for live data.
                        </motion.div>
                    )}

                    {/* ── HEATMAP ───────────────────────────────── */}
                    <IndexHeatmap
                        indices={heatmapData?.indices ?? []}
                        best={heatmapData?.best}
                        currentSymbol={symbol}
                        onSwitch={handleSwitch}
                        onRefresh={() => refreshHeatmap()}
                        isLoading={heatmapLoading}
                    />

                    {/* ── CONTROLS + VERDICT ────────────────────── */}
                    <div className="space-y-3">

                        {/* Controls */}
                        <div className="flex items-center gap-2 flex-wrap">

                            {/* Run button */}
                            <button onClick={handleAnalyze} disabled={isAnalyzing}
                                className={cn(
                                    "flex items-center gap-2 px-5 py-2 rounded-lg font-mono text-12 font-bold",
                                    "transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed",
                                )}
                                style={{
                                    background: isAnalyzing ? "rgba(96,165,250,0.06)" : "var(--regime-dim)",
                                    border: isAnalyzing ? "1px solid rgba(96,165,250,0.2)" : "1px solid var(--regime-edge)",
                                    color: isAnalyzing ? "var(--blue)" : "var(--regime)",
                                }}>
                                {isAnalyzing
                                    ? <Clock size={12} className="animate-spin" />
                                    : <Play size={12} />}
                                {isAnalyzing ? `Analysing… ${elapsedSec}s` : "RUN ANALYSIS"}
                            </button>

                            {/* Watch toggle */}
                            {verdict && verdict.verdict !== "WAIT" && verdict.trade_plan && (
                                isWatching
                                    ? <button onClick={handleClearWatch}
                                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-11 transition-all"
                                        style={{ background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.2)", color: "var(--bull)" }}>
                                        <Bell size={11} className="animate-pulse" /> Watching
                                    </button>
                                    : <button onClick={handleWatchVerdict}
                                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-11 text-t2 transition-all hover:text-t1"
                                        style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                                        <Bell size={11} /> Watch
                                    </button>
                            )}

                            {/* Journal */}
                            <Link href="/journal"
                                className="flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-11 text-t2 transition-all hover:text-t1 ml-auto"
                                style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                                <BookOpen size={11} /> Journal
                            </Link>

                            {/* Index selector */}
                            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
                                className="rounded-lg px-3 py-2 font-mono text-12 font-semibold text-t1 outline-none cursor-pointer"
                                style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                                {INDICES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>

                            {/* Chart toggle */}
                            <button onClick={() => setShowChart(v => !v)}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-11 transition-all",
                                    showChart ? "text-[var(--regime)]" : "text-t3 hover:text-t1"
                                )}
                                style={{
                                    background: showChart ? "var(--regime-dim)" : "var(--bg-s)",
                                    border: showChart ? "1px solid var(--regime-edge)" : "1px solid var(--b)",
                                }}>
                                <BarChart2 size={12} /> Chart
                            </button>

                            {/* Last run timestamp */}
                            {lastAnalyzed && !isAnalyzing && (
                                <span className="font-mono text-10 text-t3 hidden sm:block">
                                    {new Date(lastAnalyzed).toLocaleTimeString("en-IN")}
                                    {verdict?.pipeline_ms != null && ` · ${(verdict.pipeline_ms / 1000).toFixed(1)}s`}
                                </span>
                            )}

                            {/* Copilot toggle */}
                            <button onClick={toggleChat}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-2 rounded-lg font-mono text-11 transition-all",
                                    chatOpen ? "text-[var(--regime)]" : "text-t3 hover:text-t1"
                                )}
                                style={{
                                    background: chatOpen ? "var(--regime-dim)" : "var(--bg-s)",
                                    border: chatOpen ? "1px solid var(--regime-edge)" : "1px solid var(--b)",
                                }}>
                                <Terminal size={12} /> Command
                            </button>
                        </div>

                        {/* Pipeline warning */}
                        {isAnalyzing && elapsedSec >= 30 && (
                            <div className="flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-11"
                                style={{ background: "rgba(251,191,36,0.04)", border: "1px solid rgba(251,191,36,0.12)", color: "var(--wait)" }}>
                                <Clock size={12} className="shrink-0" />
                                Pipeline is taking longer than usual ({elapsedSec}s).
                            </div>
                        )}

                        {/* Watch error */}
                        {watchError && (
                            <div className="flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-11"
                                style={{ background: "rgba(248,113,113,0.04)", border: "1px solid rgba(248,113,113,0.12)", color: "var(--bear)" }}>
                                <AlertCircle size={12} className="shrink-0" />
                                <span className="flex-1">{watchError}</span>
                                <button onClick={() => setWatchError(null)} className="text-t3 hover:text-t1"><X size={12} /></button>
                            </div>
                        )}

                        {/* Error with retry */}
                        {error && (
                            <div className="flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-11"
                                style={{ background: "rgba(248,113,113,0.04)", border: "1px solid rgba(248,113,113,0.12)", color: "var(--bear)" }}>
                                <AlertCircle size={12} className="shrink-0" />
                                <span className="flex-1">{error}</span>
                                <button onClick={() => { setError(null); handleAnalyze(); }}
                                    className="flex items-center gap-1 font-mono text-10 text-[var(--blue)] rounded px-2 py-0.5"
                                    style={{ border: "1px solid rgba(96,165,250,0.2)" }}>
                                    <RefreshCw size={10} /> Retry
                                </button>
                                <button onClick={() => setError(null)} className="text-t3 hover:text-t1 ml-1"><X size={12} /></button>
                            </div>
                        )}

                        {/* ── VERDICT BANNER — THE PRODUCT ─────── */}
                        <VerdictBanner verdict={verdict} isAnalyzing={isAnalyzing} elapsedSec={elapsedSec} />
                    </div>

                    {/* ── PRICE CHART ───────────────────────────── */}
                    <AnimatePresence>
                        {showChart && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>
                                <PriceChart symbol={symbol} interval="day" range="6mo" height={260} />
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* ── ANALYSIS PANEL ────────────────────────── */}
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

            {/* ── COMMAND LAYER ─────────────────────────────── */}
            <AnimatePresence>
                {chatOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }} animate={{ height: 320, opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                        className="shrink-0 overflow-hidden">
                        <CopilotChat onClose={toggleChat} />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
