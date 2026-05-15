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
    {
        id: "A" as const,
        label: "Market Structure",
        sub: "Regime · Indicators",
        icon: "◈",
    },
    {
        id: "B" as const,
        label: "Options Pressure",
        sub: "OI · PCR · GEX",
        icon: "⬡",
    },
    {
        id: "C" as const,
        label: "Intelligence",
        sub: "Macro · Sentiment · Events",
        icon: "◎",
    },
    {
        id: "D" as const,
        label: "Risk Matrix",
        sub: "Hedge · Position · Shield",
        icon: "⬟",
    },
];

export function SectionTabs(props: SectionTabsProps) {
    const { activeSection, setSection } = useUIStore();
    const activeTab = TABS.find(t => t.id === activeSection);

    return (
        <div
            className="overflow-hidden rounded-2xl"
            style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.055)",
                backdropFilter: "blur(20px)",
            }}
        >
            {/* Tab bar */}
            <div
                className="flex border-b"
                style={{ borderColor: "rgba(255,255,255,0.045)", background: "rgba(0,0,0,0.2)" }}
            >
                {TABS.map((tab) => {
                    const isActive = activeSection === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setSection(tab.id)}
                            className={cn(
                                "flex-1 relative py-3 px-3 transition-all duration-200",
                                "border-b-[1.5px]",
                                isActive
                                    ? "border-[var(--accent)]"
                                    : "border-transparent hover:border-white/[0.1]",
                            )}
                            style={{
                                background: isActive ? "var(--accent-dim)" : "transparent",
                            }}
                        >
                            {/* Accent glow on active */}
                            {isActive && (
                                <div
                                    className="absolute inset-x-0 bottom-0 h-[30px] pointer-events-none"
                                    style={{
                                        background: "linear-gradient(to top, var(--accent-glow), transparent)",
                                    }}
                                />
                            )}
                            <div className="relative flex flex-col items-start gap-0.5">
                                {/* Icon + label */}
                                <div className="flex items-center gap-1.5">
                                    <span
                                        className="font-mono text-[11px]"
                                        style={{ color: isActive ? "var(--accent)" : "#3d4f68" }}
                                    >
                                        {tab.icon}
                                    </span>
                                    <span
                                        className="font-head text-[11px] font-bold hidden sm:block"
                                        style={{ color: isActive ? "#e8edf8" : "#7d8ea8" }}
                                    >
                                        {tab.label}
                                    </span>
                                    {/* Mobile: just letter */}
                                    <span
                                        className="font-mono text-[11px] font-black sm:hidden"
                                        style={{ color: isActive ? "var(--accent)" : "#7d8ea8" }}
                                    >
                                        {tab.id}
                                    </span>
                                </div>
                                {/* Sub-label */}
                                <span
                                    className="font-mono text-[8px] hidden lg:block"
                                    style={{ color: isActive ? "rgba(232,237,248,0.4)" : "#3d4f68" }}
                                >
                                    {tab.sub}
                                </span>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Active module label */}
            {activeTab && (
                <div
                    className="px-4 py-2 border-b flex items-center gap-2"
                    style={{ borderColor: "rgba(255,255,255,0.03)", background: "rgba(0,0,0,0.12)" }}
                >
                    <span
                        className="font-mono text-[8px] font-bold uppercase tracking-[2px]"
                        style={{ color: "var(--accent)", opacity: 0.7 }}
                    >
                        {activeTab.icon} {activeTab.label}
                    </span>
                    <span className="font-mono text-[8px] text-t3">· {activeTab.sub}</span>
                </div>
            )}

            {/* Panel body */}
            <div className="p-4 min-h-[200px]">
                {activeSection === "A" && <SectionA {...props} />}
                {activeSection === "B" && <SectionB {...props} />}
                {activeSection === "C" && <SectionC {...props} />}
                {activeSection === "D" && <SectionD {...props} />}
            </div>
        </div>
    );
}
