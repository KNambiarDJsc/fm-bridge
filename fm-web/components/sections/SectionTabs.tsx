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
    { id: "A" as const, label: "Numbers" },
    { id: "B" as const, label: "Indicators" },
    { id: "C" as const, label: "Macro & Sentiment" },
    { id: "D" as const, label: "Hedge System" },
];

export function SectionTabs(props: SectionTabsProps) {
    const { activeSection, setSection } = useUIStore();

    return (
        <div className="bg-bg2 border border-b rounded-xl overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-b bg-bg3">
                {TABS.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setSection(tab.id)}
                        className={cn(
                            "flex-1 py-3 px-2 font-mono text-[11px] font-bold transition-all border-b-2",
                            activeSection === tab.id
                                ? "text-t1 border-bl bg-bl/5"
                                : "text-t3 border-transparent hover:text-t2 hover:bg-b/40"
                        )}
                    >
                        <span className={cn(
                            "inline-flex items-center justify-center w-[18px] h-[18px] rounded text-[9px] mr-1.5 font-black",
                            activeSection === tab.id ? "bg-bl text-bg" : "bg-bg text-t3"
                        )}>{tab.id}</span>
                        <span className="hidden sm:inline">{tab.label}</span>
                    </button>
                ))}
            </div>

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
