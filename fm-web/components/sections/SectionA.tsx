"use client";

import { cn, fmtPrice, fmtPct, fmtCr, fmtScore, scoreColor } from "@/lib/utils";
import type { FinalVerdict, IndicatorPack, OptionsChain, MacroContext } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    indicators?: IndicatorPack;
    options?: OptionsChain;
    macro?: MacroContext;
}

function SectionHead({ children }: { children: React.ReactNode }) {
    return (
        <div className="font-mono text-[11px] font-bold text-t3 uppercase tracking-[1px] mb-2 pb-1.5 border-b border-[#1e2d45]">
            {children}
        </div>
    );
}

function KV({ k, v, sub, tone }: { k: string; v: string; sub?: string; tone?: string }) {
    return (
        <div className="kv">
            <div className="kv-key">{k}</div>
            <div className={cn("kv-val", tone ?? "text-t1")}>{v}</div>
            {sub && <div className="kv-sub">{sub}</div>}
        </div>
    );
}

export function SectionA({ verdict, indicators: ind, options: oc, macro }: Props) {
    const spot = ind?.spot ?? 0;

    return (
        <div className="space-y-5 animate-fade-in">

            {/* Layer Scores */}
            {verdict && Object.keys(verdict.layer_scores).length > 0 && (
                <div>
                    <SectionHead>Layer Scores (L1 → L9)</SectionHead>
                    <div className="grid grid-cols-9 gap-1.5">
                        {(["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"] as const).map((l) => {
                            const s = verdict.layer_scores[l] ?? 0;
                            return (
                                <div key={l} className={cn(
                                    "bg-[#131924] border rounded-md p-2 text-center",
                                    s >= 70 ? "border-bull/30" : s < 40 ? "border-bear/30" : "border-b"
                                )}>
                                    <div className="font-mono text-[11px] text-t3 font-bold">{l}</div>
                                    <div className={cn("font-mono text-[16px] font-black mt-0.5", scoreColor(s))}>
                                        {s || "—"}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Verdict composite */}
            {verdict && (
                <div>
                    <SectionHead>Composite</SectionHead>
                    <div className="kv-grid">
                        <KV k="Execution Score" v={fmtScore(verdict.execution_score)} tone={scoreColor(verdict.execution_score)} />
                        <KV k="Confidence" v={fmtScore(verdict.confidence)} tone={scoreColor(verdict.confidence)} />
                        <KV k="Verdict"
                            v={verdict.verdict.replace("_TRADE", "").replace("_", " ")}
                            tone={
                                verdict.verdict === "BULL_TRADE" ? "text-bull" :
                                    verdict.verdict === "BEAR_TRADE" ? "text-bear" :
                                        verdict.verdict === "HEDGE_TRADE" ? "text-hedge" : "text-wait"
                            }
                        />
                        <KV k="Risk State" v={verdict.risk_state}
                            tone={
                                verdict.risk_state === "LOW" ? "text-bull" :
                                    verdict.risk_state === "CRITICAL" ? "text-bear" : "text-wait"
                            }
                        />
                    </div>
                </div>
            )}

            {/* Price levels */}
            {ind && (
                <div>
                    <SectionHead>Price Levels</SectionHead>
                    <div className="kv-grid">
                        <KV k="Spot" v={fmtPrice(ind.spot)} />
                        <KV k="VWAP"
                            v={fmtPrice(ind.vwap)}
                            sub={ind.vwap && spot ? (spot > ind.vwap ? "Above VWAP ↑" : "Below VWAP ↓") : undefined}
                            tone={ind.vwap && spot > ind.vwap ? "text-bull" : "text-bear"}
                        />
                        <KV k="ATR(14)" v={fmtPrice(ind.atr)} sub={ind.atr_pct ? `${ind.atr_pct.toFixed(2)}%` : undefined} />
                        <KV k="BB Width" v={ind.bb_width?.toFixed(2) ?? "—"} />
                    </div>
                </div>
            )}

            {/* Moving averages */}
            {ind && (
                <div>
                    <SectionHead>Moving Averages</SectionHead>
                    <div className="kv-grid">
                        {([
                            ["EMA 9", ind.ema9],
                            ["EMA 20", ind.ema20],
                            ["EMA 50", ind.ema50],
                            ["SMA 200", ind.sma200],
                        ] as [string, number | undefined][]).map(([label, val]) => (
                            <KV
                                key={label}
                                k={label}
                                v={fmtPrice(val)}
                                sub={val && spot ? fmtPct(((spot - val) / val) * 100) : undefined}
                                tone={val && spot ? (spot > val ? "text-bull" : "text-bear") : undefined}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Momentum */}
            {ind && (
                <div>
                    <SectionHead>Momentum Indicators</SectionHead>
                    <div className="kv-grid">
                        <KV k="RSI(14)" v={ind.rsi?.toFixed(1) ?? "—"} sub={ind.rsi_zone?.replace(/_/g, " ")}
                            tone={
                                ind.rsi && ind.rsi >= 70 ? "text-bear" :
                                    ind.rsi && ind.rsi <= 30 ? "text-bull" :
                                        ind.rsi && ind.rsi >= 50 && ind.rsi <= 65 ? "text-bull" : ""
                            }
                        />
                        <KV k="MACD" v={ind.macd?.toFixed(2) ?? "—"} sub={ind.macd_dir}
                            tone={ind.macd_dir === "BULL" ? "text-bull" : ind.macd_dir === "BEAR" ? "text-bear" : ""}
                        />
                        <KV k="ADX" v={ind.adx?.toFixed(1) ?? "—"} sub={ind.adx_strength} />
                        <KV k="Stoch %K" v={ind.stoch_k?.toFixed(1) ?? "—"} sub={ind.stoch_d ? `%D ${ind.stoch_d.toFixed(1)}` : undefined} />
                        <KV k="CCI" v={ind.cci?.toFixed(1) ?? "—"} />
                        <KV k="Williams%R" v={ind.williams_r?.toFixed(1) ?? "—"} />
                        <KV k="CMF" v={ind.cmf?.toFixed(3) ?? "—"} />
                        <KV k="OBV Dir" v={ind.obv_dir ?? "—"} tone={ind.obv_dir === "UP" ? "text-bull" : ind.obv_dir === "DOWN" ? "text-bear" : ""} />
                    </div>
                </div>
            )}

            {/* Options flow */}
            {oc && (
                <div>
                    <SectionHead>Options Intelligence</SectionHead>
                    <div className="kv-grid">
                        <KV k="PCR" v={oc.pcr?.toFixed(3) ?? "—"}
                            tone={oc.pcr && oc.pcr >= 1.3 ? "text-bull" : oc.pcr && oc.pcr <= 0.7 ? "text-bear" : ""}
                        />
                        <KV k="Max Pain" v={fmtPrice(oc.max_pain)}
                            sub={oc.max_pain && oc.spot ? (oc.spot < oc.max_pain ? "Pull UP ↑" : "Pull DOWN ↓") : undefined}
                        />
                        <KV k="Call Wall" v={fmtPrice(oc.call_wall)} />
                        <KV k="Put Wall" v={fmtPrice(oc.put_wall)} />
                        <KV k="OPR" v={oc.opr?.toFixed(3) ?? "—"} sub={oc.opr_signal?.replace(/_/g, " ")}
                            tone={oc.opr_signal === "PUT_DOMINANT" ? "text-bull" : oc.opr_signal === "CALL_DOMINANT" ? "text-bear" : ""}
                        />
                        <KV k="ATM IV" v={oc.atm_iv ? `${oc.atm_iv.toFixed(1)}%` : "—"} />
                        <KV k="IV %ile" v={oc.iv_percentile ? `${oc.iv_percentile.toFixed(0)}%ile` : "—"} />
                        <KV k="DTE" v={oc.dte ? `${oc.dte}d` : "—"}
                            sub={oc.is_expiry_day ? "EXPIRY TODAY" : undefined}
                            tone={oc.is_expiry_day ? "text-bear" : ""}
                        />
                    </div>
                </div>
            )}

            {/* Macro */}
            {macro && (
                <div>
                    <SectionHead>Macro Context</SectionHead>
                    <div className="kv-grid">
                        <KV k="Brent Oil" v={macro.brent_oil ? `$${macro.brent_oil.toFixed(1)}` : "—"}
                            sub={macro.oil_shock_active ? "SHOCK — LONG vetoed" : "CLEAR"}
                            tone={macro.oil_shock_active ? "text-bear" : "text-bull"}
                        />
                        <KV k="FII Flow" v={fmtCr(macro.fii_net)} tone={macro.fii_net != null && macro.fii_net > 0 ? "text-bull" : "text-bear"} />
                        <KV k="DII Flow" v={fmtCr(macro.dii_net)} tone={macro.dii_net != null && macro.dii_net > 0 ? "text-bull" : "text-bear"} />
                        <KV k="Dom. Floor" v={macro.domestic_floor_active ? "ACTIVE" : "INACTIVE"}
                            tone={macro.domestic_floor_active ? "text-bull" : "text-t3"}
                        />
                        <KV k="VIX" v={macro.india_vix?.toFixed(1) ?? "—"} sub={macro.vix_regime}
                            tone={macro.india_vix && macro.india_vix > 22 ? "text-bear" : macro.india_vix && macro.india_vix < 13 ? "text-bull" : ""}
                        />
                        <KV k="Risk Context" v={macro.risk_context}
                            tone={macro.risk_context === "RISK_ON" ? "text-bull" : macro.risk_context === "RISK_OFF" ? "text-bear" : ""}
                        />
                        <KV k="RBI Stance" v={macro.rbi_stance ?? "—"} />
                        {macro.data_age_minutes != null && macro.data_age_minutes > 30 && (
                            <KV k="Data Age" v={`${macro.data_age_minutes.toFixed(0)}min`} tone="text-wait" sub="Consider refreshing" />
                        )}
                    </div>
                </div>
            )}

        </div>
    );
}
