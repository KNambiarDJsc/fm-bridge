"use client";
import { cn, fmtCr } from "@/lib/utils";
import type { MacroContext } from "@/lib/types";

interface Props {
    macro?: MacroContext;
    agentOutputs: Record<string, Record<string, unknown>>;
}

function NarrCard({ label, score, children }: { label: string; score?: number; children: React.ReactNode }) {
    return (
        <div className="bg-bg3 border border-b rounded-lg p-3">
            <div className="flex items-center mb-3">
                <span className="font-mono text-[9px] font-bold text-t2 uppercase tracking-[1px]">{label}</span>
                {score != null && (
                    <span className="ml-auto font-mono text-[13px] font-black text-t1">{score}/100</span>
                )}
            </div>
            <div className="space-y-1.5">{children}</div>
        </div>
    );
}

function Row({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
    return (
        <div className="flex items-baseline gap-2 font-mono text-[11px]">
            <span className="text-t3 shrink-0 w-28">{label}</span>
            <span className={cn("font-bold", tone ?? "text-t1")}>{value}</span>
            {sub && <span className="text-t3 text-[10px]">{sub}</span>}
        </div>
    );
}

function Divider() {
    return <div className="border-t border-b my-2" />;
}

export function SectionC({ macro, agentOutputs }: Props) {
    const l1 = (agentOutputs.l1 ?? {}) as Record<string, unknown>;
    const l2 = (agentOutputs.l2 ?? {}) as Record<string, unknown>;
    const l5 = (agentOutputs.l5 ?? {}) as Record<string, unknown>;
    const l6 = (agentOutputs.l6 ?? {}) as Record<string, unknown>;

    const legend = l5.legend_consensus as { bull: number; neutral: number; bear: number; total: number; summary: string } | undefined;
    const headlines = (l5.top_headlines as string[]) ?? [];
    const rationale = (l5.rationale as string) ?? "";
    const l6rat = (l6.rationale as string) ?? "";

    return (
        <div className="space-y-3 animate-fade-in">

            {/* C3 — Legend Consensus (most prominent per spec §6.1) */}
            {legend && legend.total > 0 && (
                <div className="bg-bg3 border border-b rounded-lg p-3">
                    <div className="font-mono text-[9px] font-bold text-t2 uppercase tracking-[1px] mb-3">
                        C3 · 20-Legend Advisor Consensus
                    </div>
                    <div className="flex h-9 rounded-lg overflow-hidden border border-b mb-2">
                        {legend.bull > 0 && (
                            <div className="bg-bull flex items-center justify-center font-mono text-[11px] font-black text-bg"
                                style={{ flex: legend.bull }}>
                                {legend.bull} BULL
                            </div>
                        )}
                        {legend.neutral > 0 && (
                            <div className="bg-b2 flex items-center justify-center font-mono text-[10px] font-bold text-t2"
                                style={{ flex: legend.neutral }}>
                                {legend.neutral} NEUT
                            </div>
                        )}
                        {legend.bear > 0 && (
                            <div className="bg-bear flex items-center justify-center font-mono text-[11px] font-black text-bg"
                                style={{ flex: legend.bear }}>
                                {legend.bear} BEAR
                            </div>
                        )}
                    </div>
                    <div className="font-mono text-[10px] text-t3 mb-1">
                        {legend.bull}B / {legend.neutral}N / {legend.bear}Be of {legend.total} advisors
                    </div>
                    {legend.summary && (
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{legend.summary}</div>
                    )}
                </div>
            )}

            {/* C1 — Macro */}
            <NarrCard label="C1 · Macro Environment" score={(l1.macro_score as number) ?? undefined}>
                <Row label="Risk Context" value={(l1.risk_context as string) ?? macro?.risk_context ?? "—"}
                    tone={
                        ((l1.risk_context ?? macro?.risk_context) === "RISK_ON") ? "text-bull" :
                            ((l1.risk_context ?? macro?.risk_context) === "RISK_OFF") ? "text-bear" : ""
                    }
                />
                <Row label="Oil" value={macro?.brent_oil ? `$${macro.brent_oil.toFixed(1)}` : "—"}
                    sub={macro?.oil_shock_active ? "(SHOCK — LONG blocked)" : "(CLEAR)"}
                    tone={macro?.oil_shock_active ? "text-bear" : "text-bull"}
                />
                <Row label="FII" value={fmtCr(macro?.fii_net)} tone={macro?.fii_net != null && macro.fii_net > 0 ? "text-bull" : "text-bear"} />
                <Row label="DII" value={fmtCr(macro?.dii_net)} tone={macro?.dii_net != null && macro.dii_net > 0 ? "text-bull" : "text-bear"} />
                <Row label="Dom. Floor" value={macro?.domestic_floor_active ? "ACTIVE" : "INACTIVE"}
                    tone={macro?.domestic_floor_active ? "text-bull" : "text-t3"}
                />
                {(l1.rationale as string) && (
                    <>
                        <Divider />
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{l1.rationale as string}</div>
                    </>
                )}
            </NarrCard>

            {/* C2 — Fundamentals */}
            <NarrCard label="C2 · Fundamental Health" score={(l2.fundamental_score as number) ?? undefined}>
                <Row label="Valuation" value={(l2.valuation_status as string) ?? "—"}
                    tone={(l2.valuation_status as string) === "UNDERVALUED" ? "text-bull" : (l2.valuation_status as string) === "OVERVALUED" ? "text-bear" : ""}
                />
                <Row label="Earnings" value={(l2.earnings_trend as string) ?? "—"}
                    tone={(l2.earnings_trend as string) === "ACCELERATING" ? "text-bull" : (l2.earnings_trend as string) === "DECELERATING" ? "text-bear" : ""}
                />
                <Row label="Inst. Flow" value={(l2.institutional_flow as string) ?? "—"} />
                <Row label="Sector Lead" value={(l2.sector_leadership as string) ?? "—"} />
                {(l2.rationale as string) && (
                    <>
                        <Divider />
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{l2.rationale as string}</div>
                    </>
                )}
            </NarrCard>

            {/* C4 — Sentiment + headlines */}
            <NarrCard label="C4 · News & Sentiment" score={(l5.confidence as number) ?? undefined}>
                <Row label="Narrative" value={(l5.narrative_direction as string) ?? "—"} />
                <Row label="Vol. Sent." value={(l5.volatility_sentiment as string) ?? "—"} />
                <Row label="Fear/Greed"
                    value={l5.fear_greed_label ? `${l5.fear_greed_proxy} — ${l5.fear_greed_label}` : "—"}
                    tone={(l5.fear_greed_proxy as number) > 65 ? "text-bear" : (l5.fear_greed_proxy as number) < 35 ? "text-bull" : ""}
                />
                {headlines.length > 0 && (
                    <>
                        <Divider />
                        <div className="font-mono text-[8px] text-t3 uppercase tracking-[0.5px] mb-1">Live Headlines</div>
                        {headlines.slice(0, 5).map((h, i) => (
                            <div key={i} className="font-mono text-[10px] text-t2 leading-relaxed pl-2 border-l-2 border-bl/30">
                                {h}
                            </div>
                        ))}
                    </>
                )}
                {rationale && (
                    <>
                        <Divider />
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{rationale}</div>
                    </>
                )}
            </NarrCard>

            {/* C5 — Options Flow */}
            <NarrCard label="C5 · Options Flow Intelligence" score={(l6.flow_conviction_score as number) ?? undefined}>
                <Row label="Options Bias"
                    value={(l6.options_bias as string) ?? "—"}
                    tone={(l6.options_bias as string) === "BULLISH" ? "text-bull" : (l6.options_bias as string) === "BEARISH" ? "text-bear" : ""}
                />
                <Row label="Dealer Stance"
                    value={(l6.dealer_stance as string)?.replace(/_/g, " ") ?? "—"}
                    tone={(l6.dealer_stance as string) === "LONG_GAMMA" ? "text-bull" : (l6.dealer_stance as string) === "SHORT_GAMMA" ? "text-wait" : ""}
                />
                <Row label="IV Regime"
                    value={(l6.iv_regime as string) ?? "—"}
                    tone={(l6.iv_regime as string) === "EXPENSIVE" ? "text-bear" : (l6.iv_regime as string) === "CHEAP" ? "text-bull" : ""}
                />
                <Row label="Best Vehicle" value={(l6.best_execution_vehicle as string) ?? "—"} />
                {(l6.opr_interpretation as string) && (
                    <>
                        <Divider />
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{l6.opr_interpretation as string}</div>
                    </>
                )}
                {l6rat && !l6.opr_interpretation && (
                    <>
                        <Divider />
                        <div className="font-mono text-[11px] text-t2 leading-relaxed">{l6rat}</div>
                    </>
                )}
            </NarrCard>

        </div>
    );
}
