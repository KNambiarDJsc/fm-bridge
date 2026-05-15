"use client";
import { cn, fmtPrice, fmtRs } from "@/lib/utils";
import type { FinalVerdict, CapitalShield } from "@/lib/types";

interface Props {
    verdict?: FinalVerdict | null;
    shield?: CapitalShield;
}

export function SectionD({ verdict, shield }: Props) {
    const hp = verdict?.hedge_plan;
    const tp = verdict?.trade_plan;
    const ws = verdict?.wait_signal;

    return (
        <div className="space-y-4 animate-fade-in">

            {/* Trade Plan summary (if active trade) */}
            {tp && verdict?.verdict !== "WAIT" && (
                <div className="bg-bg3 border border-b rounded-lg p-3">
                    <div className="font-mono text-[9px] font-bold text-t2 uppercase tracking-[1px] mb-3">
                        D0 · Active Trade Plan
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                        <PriceBlock label="Entry Low" value={fmtPrice(tp.entry_low)} tone="text-t1" />
                        <PriceBlock label="Entry High" value={fmtPrice(tp.entry_high)} tone="text-t1" />
                        <PriceBlock label="Stop Loss" value={fmtPrice(tp.stop_loss)} tone="text-bear" />
                        <PriceBlock label="R:R Ratio" value={`1:${tp.rr.toFixed(1)}`} tone="text-bl" />
                    </div>
                    <div className="grid grid-cols-3 gap-2 mb-3">
                        <PriceBlock label="Target 1" value={fmtPrice(tp.target1)} tone="text-bull" />
                        <PriceBlock label="Target 2" value={fmtPrice(tp.target2)} tone="text-bull" />
                        {tp.target3 && <PriceBlock label="Target 3" value={fmtPrice(tp.target3)} tone="text-bull" />}
                    </div>
                    {tp.entry_trigger && (
                        <div className="p-2 rounded bg-bl/5 border border-bl/20 mb-2">
                            <div className="font-mono text-[9px] text-bl font-bold uppercase mb-0.5">Entry Trigger</div>
                            <div className="font-mono text-[10px] text-t2">{tp.entry_trigger}</div>
                        </div>
                    )}
                    {tp.invalidation && (
                        <div className="p-2 rounded bg-bear/5 border border-bear/20">
                            <div className="font-mono text-[9px] text-bear font-bold uppercase mb-0.5">Invalidation</div>
                            <div className="font-mono text-[10px] text-t2">{tp.invalidation}</div>
                        </div>
                    )}
                </div>
            )}

            {/* Wait signal */}
            {ws && verdict?.verdict === "WAIT" && (
                <div className="bg-wait/5 border border-wait/30 rounded-lg p-3">
                    <div className="font-mono text-[9px] font-bold text-wait uppercase tracking-[1px] mb-2">D0 · WAIT Signal</div>
                    <div className="font-mono text-[12px] text-t1 font-bold mb-2">{ws.reason}</div>
                    <div className="space-y-1.5">
                        <Row k="Re-entry Trigger" v={ws.re_entry_trigger} tone="text-t1" />
                        <Row k="Condition" v={ws.re_entry_condition} />
                        <Row k="Window" v={`${ws.re_entry_window_minutes} minutes`} tone="text-wait" />
                        <Row k="Pivot Plan" v={ws.pivot_plan} />
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Hedge Structure */}
                <div className="bg-bg3 border border-b rounded-lg p-3">
                    <div className="font-mono text-[9px] font-bold text-t2 uppercase tracking-[1px] mb-3">D1 · Hedge Structure</div>
                    {!hp || hp.hedge_type === "NONE" || !verdict || verdict.verdict === "WAIT" ? (
                        <div className="font-mono text-[11px] text-t3">
                            {verdict?.verdict === "WAIT"
                                ? "No trade — hedge activates on next BULL / BEAR / HEDGE verdict."
                                : "Run analysis to compute hedge recommendation."}
                        </div>
                    ) : hp.hedge_type === "IRON_CONDOR" ? (
                        <IronCondorCard hp={hp} />
                    ) : (
                        <DirectionalHedge hp={hp} />
                    )}
                </div>

                {/* Capital shield */}
                <div className="bg-bg3 border border-b rounded-lg p-3">
                    <div className="font-mono text-[9px] font-bold text-t2 uppercase tracking-[1px] mb-3">D2 · Capital Shield</div>
                    {!shield ? (
                        <div className="font-mono text-[11px] text-t3">Bridge not connected — capital shield unavailable.</div>
                    ) : (
                        <CapitalDash shield={shield} />
                    )}
                </div>
            </div>

        </div>
    );
}

// ── Sub-components ────────────────────────────────────────────

function PriceBlock({ label, value, tone }: { label: string; value: string; tone?: string }) {
    return (
        <div className="bg-bg border border-b rounded-md p-2">
            <div className="font-mono text-[8px] text-t3 uppercase mb-1">{label}</div>
            <div className={cn("font-mono text-[13px] font-black", tone ?? "text-t1")}>{value}</div>
        </div>
    );
}

function Row({ k, v, tone }: { k: string; v: string; tone?: string }) {
    return (
        <div className="flex justify-between items-start gap-2 py-1 border-b border-b/40">
            <span className="font-mono text-[10px] text-t3 shrink-0">{k}</span>
            <span className={cn("font-mono text-[10px] font-bold text-right", tone ?? "text-t1")}>{v}</span>
        </div>
    );
}

function DirectionalHedge({ hp }: { hp: NonNullable<FinalVerdict["hedge_plan"]> }) {
    const isBull = hp.hedge_type === "BUY_PE_HEDGE";
    return (
        <div className="space-y-2">
            <div className="font-mono text-[12px] font-bold text-t1">
                {isBull ? "Protective Put" : "Protective Call"}
            </div>
            <Row k="Strike" v={fmtPrice(hp.strike)} />
            <Row k="Premium / unit" v={hp.premium_per_unit ? `₹${hp.premium_per_unit.toFixed(2)}` : "—"} />
            <Row k="Cost / lot" v={fmtRs(hp.premium_per_lot)} />
            <Row k="Cost % position" v={hp.cost_pct_position ? `${hp.cost_pct_position.toFixed(2)}%` : "—"}
                tone={hp.cost_pct_position && hp.cost_pct_position > 2 ? "text-bear" : ""} />
            <Row k="Protects below" v={hp.protection_range ?? "—"} />
            {hp.exit_rule && (
                <div className="mt-2 p-2 rounded bg-wait/5 border border-wait/20">
                    <div className="font-mono text-[9px] text-wait font-bold uppercase mb-1">Exit Rule</div>
                    <div className="font-mono text-[10px] text-t2 leading-relaxed">{hp.exit_rule}</div>
                </div>
            )}
            {hp.disclaimer && (
                <div className="font-mono text-[9px] text-t3 italic mt-1">{hp.disclaimer}</div>
            )}
        </div>
    );
}

function IronCondorCard({ hp }: { hp: NonNullable<FinalVerdict["hedge_plan"]> }) {
    return (
        <div className="space-y-2">
            <div className="font-mono text-[12px] font-bold text-hedge">Iron Condor</div>
            <div className="grid grid-cols-2 gap-2">
                <PriceBlock label="Sell CE" value={fmtPrice(hp.sell_ce)} tone="text-bear" />
                <PriceBlock label="Sell PE" value={fmtPrice(hp.sell_pe)} tone="text-bear" />
                <PriceBlock label="Buy CE Wing" value={fmtPrice(hp.buy_ce)} tone="text-t2" />
                <PriceBlock label="Buy PE Wing" value={fmtPrice(hp.buy_pe)} tone="text-t2" />
            </div>
            <Row k="Net Credit / lot" v={fmtRs(hp.net_credit_per_lot)} tone="text-bull" />
            <Row k="Max Loss / lot" v={fmtRs(hp.max_loss_per_lot)} tone="text-bear" />
            {hp.protection_range && <Row k="Profit Zone" v={hp.protection_range} />}
            {hp.exit_rule && (
                <div className="mt-2 p-2 rounded bg-wait/5 border border-wait/20">
                    <div className="font-mono text-[9px] text-wait font-bold uppercase mb-1">Exit / Adjust Rule</div>
                    <div className="font-mono text-[10px] text-t2 leading-relaxed">{hp.exit_rule}</div>
                </div>
            )}
            {hp.disclaimer && (
                <div className="font-mono text-[9px] text-t3 italic mt-1">{hp.disclaimer}</div>
            )}
        </div>
    );
}

function CapitalDash({ shield }: { shield: CapitalShield }) {
    const ddPct = shield.daily_dd_limit > 0 ? (shield.daily_dd_pct / shield.daily_dd_limit) * 100 : 0;
    const wkPct = shield.weekly_dd_limit > 0 ? (shield.weekly_dd_pct / shield.weekly_dd_limit) * 100 : 0;

    return (
        <div className="space-y-2">
            {/* Kill switch */}
            <div className="flex justify-between items-center py-1 border-b border-b/40">
                <span className="font-mono text-[10px] text-t3">Kill Switch</span>
                <span className={cn(
                    "font-mono text-[10px] font-black px-2 py-0.5 rounded",
                    shield.kill_switch
                        ? "bg-bear/20 text-bear border border-bear/40 animate-pulse-slow"
                        : "bg-bull/10 text-bull border border-bull/20"
                )}>
                    {shield.kill_switch ? "🔴 ACTIVE" : "OFF"}
                </span>
            </div>

            {/* Daily DD bar */}
            <div>
                <div className="flex justify-between font-mono text-[10px] text-t3 mb-1">
                    <span>Daily DD</span>
                    <span className={ddPct > 70 ? "text-bear" : "text-t2"}>
                        {shield.daily_dd_pct.toFixed(2)}% / {shield.daily_dd_limit}%
                    </span>
                </div>
                <div className="h-1.5 bg-b2 rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full transition-all", ddPct > 70 ? "bg-bear" : ddPct > 40 ? "bg-wait" : "bg-bull")}
                        style={{ width: `${Math.min(100, ddPct)}%` }}
                    />
                </div>
            </div>

            {/* Weekly DD bar */}
            <div>
                <div className="flex justify-between font-mono text-[10px] text-t3 mb-1">
                    <span>Weekly DD</span>
                    <span className={wkPct > 70 ? "text-bear" : "text-t2"}>
                        {shield.weekly_dd_pct.toFixed(2)}% / {shield.weekly_dd_limit}%
                    </span>
                </div>
                <div className="h-1.5 bg-b2 rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full", wkPct > 70 ? "bg-bear" : wkPct > 40 ? "bg-wait" : "bg-bull")}
                        style={{ width: `${Math.min(100, wkPct)}%` }}
                    />
                </div>
            </div>

            <Row k="Risk State" v={shield.risk_state}
                tone={shield.risk_state === "LOW" ? "text-bull" : shield.risk_state === "CRITICAL" ? "text-bear" : "text-wait"} />
            <Row k="Open Risk" v={`${shield.open_risk_pct.toFixed(2)}% / ${shield.max_open_risk_pct}%`}
                tone={shield.open_risk_pct >= shield.max_open_risk_pct ? "text-bear" : ""} />
            <Row k="Loss Streak" v={`${shield.loss_streak} consecutive`}
                tone={shield.loss_streak >= 3 ? "text-wait" : ""} />
            <Row k="Max Risk / Trade" v={fmtRs(shield.max_risk_per_trade)} />
            <Row k="Units Auth." v={shield.unit_count > 0 ? `${shield.unit_count} lots` : "BLOCKED"}
                tone={shield.unit_count > 0 ? "text-bull" : "text-bear"} />
            <Row k="Cash Reserve" v={`${shield.cash_reserve_pct}%`} tone="text-bl" />
        </div>
    );
}
