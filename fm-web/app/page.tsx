"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Activity, Brain, Shield, BarChart3, Zap, Layers, Terminal, ChevronRight } from "lucide-react";

const FADE_UP = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
        opacity: 1, y: 0,
        transition: { delay: i * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
    }),
};

const PIPELINE_LAYERS = [
    { id: "L1", name: "Macro", desc: "RBI, VIX, FII/DII, oil, global cues" },
    { id: "L2", name: "Technical", desc: "EMA, RSI, MACD, ADX, Supertrend" },
    { id: "L3", name: "Options", desc: "PCR, Max Pain, OPR, Gamma walls" },
    { id: "L4", name: "Strategy", desc: "Regime detection, trade synthesis" },
    { id: "L5", name: "Sentiment", desc: "News + social signal scoring" },
    { id: "L6", name: "Options Deep", desc: "Greeks, skew, volatility surface" },
    { id: "L7", name: "Risk", desc: "Capital shield, drawdown, kill switch" },
    { id: "L8", name: "Hedge", desc: "Iron Condor, protective puts/calls" },
    { id: "L9", name: "Sovereign", desc: "Final verdict arbitration" },
];

const FEATURES = [
    {
        icon: Brain,
        title: "9-Layer AI Pipeline",
        desc: "Sequential LangGraph reasoning across macro, technical, options, and sentiment data. Not a single prompt — a multi-agent orchestration.",
    },
    {
        icon: Activity,
        title: "Live Zerodha Bridge",
        desc: "Millisecond-latency WebSocket connections. Real-time ticks, programmatic hedging, and order execution through KiteConnect.",
    },
    {
        icon: Shield,
        title: "Capital Shield",
        desc: "Automated drawdown protection with daily/weekly limits, kill switch, and intelligent recovery scaling tied to live equity.",
    },
    {
        icon: Layers,
        title: "Regime-Reactive",
        desc: "The entire system adapts to market regime — Bull, Bear, Volatile, Range, or Event-Driven. Strategy shifts with structure.",
    },
    {
        icon: BarChart3,
        title: "Options Intelligence",
        desc: "OPR analysis, gamma walls, max pain, IV percentile, and PCR — compressed into actionable verdicts, not raw data.",
    },
    {
        icon: Terminal,
        title: "Strategic Copilot",
        desc: "Context-aware AI that explains verdicts, regime shifts, and hedge rationale. Not ChatGPT — a tactical command interface.",
    },
];

export default function HomePage() {
    return (
        <div className="min-h-screen flex flex-col">

            {/* ── NAV ──────────────────────────────────────────── */}
            <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-14"
                style={{ background: "rgba(5,5,7,0.8)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--b)" }}>
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-[var(--regime)] live-dot" />
                    <span className="font-mono text-13 font-bold tracking-[0.15em] text-t1">SOVEREIGN</span>
                </div>
                <div className="flex items-center gap-6">
                    <span className="hidden sm:block font-mono text-11 text-t3">v6.0</span>
                    <Link href="/dashboard" className="flex items-center gap-2 px-4 py-1.5 rounded-md font-mono text-11 font-bold text-t0 transition-colors"
                        style={{ background: "var(--regime-mid)", border: "1px solid var(--regime-edge)" }}>
                        OPEN COPILOT <ArrowRight size={12} />
                    </Link>
                </div>
            </nav>

            {/* ── HERO ─────────────────────────────────────────── */}
            <section className="relative flex flex-col items-center justify-center min-h-screen px-6 pt-20">

                {/* Regime halo */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] pointer-events-none"
                    style={{ background: "radial-gradient(ellipse at 50% 0%, var(--regime-glow), transparent 70%)" }} />

                <motion.div className="relative z-10 max-w-3xl text-center" initial="hidden" animate="visible">

                    <motion.div variants={FADE_UP} custom={0}
                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md mb-8 font-mono text-11 text-t2"
                        style={{ background: "var(--glass)", border: "1px solid var(--b)" }}>
                        <Zap size={11} className="text-[var(--regime)]" />
                        AI-NATIVE DERIVATIVES INTELLIGENCE
                    </motion.div>

                    <motion.h1 variants={FADE_UP} custom={1}
                        className="type-headline text-5xl sm:text-6xl md:text-7xl mb-6">
                        Trade Market Structure,{" "}
                        <span className="text-t3">Not Noise</span>
                    </motion.h1>

                    <motion.p variants={FADE_UP} custom={2}
                        className="type-body text-base sm:text-lg max-w-xl mx-auto mb-10">
                        FM Sovereign runs a 9-layer LangGraph pipeline across macro, technical, options, and sentiment data — then delivers a single, institutional-grade verdict.
                    </motion.p>

                    <motion.div variants={FADE_UP} custom={3}
                        className="flex flex-col sm:flex-row items-center justify-center gap-3">
                        <Link href="/dashboard"
                            className="flex items-center gap-2 px-6 py-3 rounded-lg font-sans text-sm font-semibold bg-t0 text-bg transition-transform active:scale-[0.97]">
                            Launch Mission Control <ArrowRight size={14} />
                        </Link>
                        <a href="https://github.com/KNambiarDJsc/fm-bridge" target="_blank" rel="noreferrer"
                            className="flex items-center gap-2 px-6 py-3 rounded-lg font-sans text-sm font-medium text-t2 transition-colors hover:text-t1"
                            style={{ border: "1px solid var(--b)" }}>
                            Documentation
                        </a>
                    </motion.div>

                </motion.div>

                {/* Scroll indicator */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }}
                    className="absolute bottom-8 font-mono text-10 text-t3 tracking-widest">
                    SCROLL
                </motion.div>
            </section>

            {/* ── PIPELINE SHOWCASE ────────────────────────────── */}
            <section className="relative px-6 py-24 max-w-5xl mx-auto w-full">
                <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }}>
                    <motion.div variants={FADE_UP} custom={0} className="mb-12">
                        <div className="type-label mb-3">THE PIPELINE</div>
                        <h2 className="type-headline text-3xl sm:text-4xl mb-4">
                            9 Agents. One Verdict.
                        </h2>
                        <p className="type-body max-w-lg">
                            Each layer contributes an independent signal. The Sovereign agent arbitrates conflicts and produces a single, executable trade plan.
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-[1px] rounded-xl overflow-hidden" style={{ background: "var(--b)" }}>
                        {PIPELINE_LAYERS.map((l, i) => (
                            <motion.div key={l.id} variants={FADE_UP} custom={i * 0.5}
                                className="px-5 py-4 transition-colors hover:bg-[var(--glass-hover)]"
                                style={{ background: "var(--bg-s)" }}>
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="font-mono text-10 font-bold text-[var(--regime)]">{l.id}</span>
                                    <span className="font-sans text-13 font-semibold text-t1">{l.name}</span>
                                </div>
                                <p className="font-mono text-11 text-t3">{l.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            </section>

            {/* ── FEATURES ─────────────────────────────────────── */}
            <section className="relative px-6 py-24 max-w-5xl mx-auto w-full">
                <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }}>
                    <motion.div variants={FADE_UP} custom={0} className="mb-12">
                        <div className="type-label mb-3">CAPABILITIES</div>
                        <h2 className="type-headline text-3xl sm:text-4xl">
                            Institutional Intelligence,<br />Discretionary Execution
                        </h2>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {FEATURES.map((f, i) => (
                            <motion.div key={f.title} variants={FADE_UP} custom={i}
                                className="surface-e p-6 group transition-colors hover:border-[var(--b-h)]">
                                <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-4 text-[var(--regime)]"
                                    style={{ background: "var(--regime-dim)", border: "1px solid var(--regime-edge)" }}>
                                    <f.icon size={18} strokeWidth={1.5} />
                                </div>
                                <h3 className="type-title text-15 mb-2">{f.title}</h3>
                                <p className="type-body text-13 leading-relaxed">{f.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            </section>

            {/* ── VERDICT SHOWCASE ─────────────────────────────── */}
            <section className="relative px-6 py-24 max-w-5xl mx-auto w-full">
                <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }}>
                    <motion.div variants={FADE_UP} custom={0} className="text-center mb-12">
                        <div className="type-label mb-3">VERDICT FIRST</div>
                        <h2 className="type-headline text-3xl sm:text-4xl mb-4">
                            One Signal. Not Fifty Widgets.
                        </h2>
                        <p className="type-body max-w-lg mx-auto">
                            Every morning, the system delivers a single verdict: BULL, BEAR, HEDGE, or WAIT — with entry, stop, targets, and hedge already calculated.
                        </p>
                    </motion.div>

                    {/* Mock verdict */}
                    <motion.div variants={FADE_UP} custom={1}
                        className="surface-regime p-6 sm:p-8 max-w-2xl mx-auto">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="w-1.5 h-1.5 rounded-full bg-[var(--bull)] live-dot" />
                            <span className="font-mono text-10 text-t3 tracking-widest">NIFTY 50 · BULL TREND · SCORE 87/100</span>
                        </div>
                        <div className="type-headline text-4xl sm:text-5xl mb-6" style={{ color: "var(--bull)" }}>
                            BULL TRADE
                        </div>
                        <div className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-13">
                            <span><span className="text-t3 text-11">Entry</span> <span className="text-t1 font-semibold">24,180 – 24,220</span></span>
                            <span><span className="text-t3 text-11">SL</span> <span className="text-bear font-semibold">24,050</span></span>
                            <span><span className="text-t3 text-11">T1</span> <span className="text-bull font-semibold">24,420</span></span>
                            <span><span className="text-t3 text-11">T2</span> <span className="text-[var(--cyan)] font-semibold">24,580</span></span>
                            <span><span className="text-t3 text-11">R:R</span> <span className="text-t1 font-semibold">1:2.4</span></span>
                        </div>
                    </motion.div>
                </motion.div>
            </section>

            {/* ── CTA ──────────────────────────────────────────── */}
            <section className="relative px-6 py-32">
                <div className="absolute inset-0 pointer-events-none"
                    style={{ background: "radial-gradient(ellipse at 50% 100%, var(--regime-glow), transparent 60%)" }} />
                <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }}
                    className="relative z-10 max-w-2xl mx-auto text-center">
                    <motion.h2 variants={FADE_UP} custom={0}
                        className="type-headline text-4xl sm:text-5xl mb-6">
                        Ready to Trade Structure
                    </motion.h2>
                    <motion.div variants={FADE_UP} custom={1}>
                        <Link href="/dashboard"
                            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg font-sans text-sm font-bold bg-t0 text-bg transition-transform active:scale-[0.97]">
                            Enter Mission Control <ChevronRight size={16} />
                        </Link>
                    </motion.div>
                </motion.div>
            </section>

            {/* ── FOOTER ───────────────────────────────────────── */}
            <footer className="px-6 py-8 flex items-center justify-between" style={{ borderTop: "1px solid var(--b)" }}>
                <span className="font-mono text-11 text-t3 tracking-wider">FM SOVEREIGN v6.0</span>
                <span className="font-mono text-10 text-t3">AI-NATIVE DERIVATIVES INTELLIGENCE</span>
            </footer>
        </div>
    );
}
