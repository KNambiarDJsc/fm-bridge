"use client";

import { cn } from "@/lib/utils";
import type { FinalVerdict, IndicatorPack, OptionsChain, MacroContext, CapitalShield } from "@/lib/types";
import { useUIStore } from "@/store/trading";
import { SectionA } from "./SectionA";
import { SectionB } from "./SectionB";
import { SectionC } from "./SectionC";
import { SectionD } from "./SectionD";

export interface SectionTabsProps {
    verdict?: FinalVerdict | null;
    indicators?: IndicatorPack;
    options?: OptionsChain;
    macro?: MacroContext;
    shield?: CapitalShield;
    agentOutputs: Record<string, Record<string, unknown>>;
    symbol: string;
}

const TABS = [
    { id: "A" as const, label: "Market Structure", sub: "Regime · Indicators", icon: "◈" },
    { id: "B" as const, label: "Options Pressure", sub: "OI · PCR · GEX", icon: "⬡" },
    { id: "C" as const, label: "Intelligence", sub: "Macro · Sentiment", icon: "◎" },
    { id: "D" as const, label: "Risk Matrix", sub: "Hedge · Shield", icon: "⬟" },
];

export function SectionTabs(props: SectionTabsProps) {
    const { activeSection, setSection } = useUIStore();

    return (
        <div
            className="overflow-hidden rounded-2xl"
            style={{ background: "var(--bg2)", border: "1px solid var(--b)" }}
        >
            {/* Tab bar */}
            <div
                className="flex border-b"
                style={{ borderColor: "var(--b)", background: "var(--bg)" }}
            >
                {TABS.map((tab) => {
                    const active = activeSection === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setSection(tab.id)}
                            className="flex-1 relative py-3.5 px-3 transition-all duration-150"
                            style={{
                                borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                                background: active ? "var(--accent-dim)" : "transparent",
                            }}
                        >
                            {/* Glow bloom on active */}
                            {active && (
                                <div
                                    className="absolute inset-x-0 bottom-0 h-8 pointer-events-none"
                                    style={{ background: "linear-gradient(to top, var(--accent-glow), transparent)" }}
                                />
                            )}
                            <div className="relative flex flex-col items-start">
                                <div className="flex items-center gap-1.5 mb-0.5">
                                    <span
                                        className="font-mono text-[12px]"
                                        style={{ color: active ? "var(--accent)" : "var(--t3)" }}
                                    >
                                        {tab.icon}
                                    </span>
                                    <span
                                        className="font-head font-bold hidden sm:block"
                                        style={{ fontSize: "12px", color: active ? "var(--t1)" : "var(--t2)" }}
                                    >
                                        {tab.label}
                                    </span>
                                    {/* Mobile: letter only */}
                                    <span
                                        className="font-mono text-[12px] font-black sm:hidden"
                                        style={{ color: active ? "var(--accent)" : "var(--t2)" }}
                                    >
                                        {tab.id}
                                    </span>
                                </div>
                                <span
                                    className="font-mono text-[10px] hidden lg:block leading-none"
                                    style={{ color: active ? "rgba(240,244,255,0.4)" : "var(--t3)" }}
                                >
                                    {tab.sub}
                                </span>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Active label strip */}
            {(() => {
                const t = TABS.find(t => t.id === activeSection);
                return t ? (
                    <div
                        className="px-5 py-2 flex items-center gap-2 border-b"
                        style={{ borderColor: "var(--b)", background: "rgba(0,0,0,0.15)" }}
                    >
                        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.1em]" style={{ color: "var(--accent)", opacity: 0.75 }}>
                            {t.icon} {t.label}
                        </span>
                        <span className="font-mono text-[10px] text-t3">· {t.sub}</span>
                    </div>
                ) : null;
            })()}

            {/* Content */}
            <div className="p-5 min-h-[220px]">
                {activeSection === "A" && <SectionA {...props} />}
                {activeSection === "B" && <SectionB {...props} />}
                {activeSection === "C" && <SectionC {...props} />}
                {activeSection === "D" && <SectionD {...props} />}
            </div>
        </div>
    );
}
