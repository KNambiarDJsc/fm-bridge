"use client";

import { cn, fmtCr } from "@/lib/utils";
import type { MacroContext } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { BRIDGE } from "@/lib/api";

interface Props {
  macro?:       MacroContext;
  agentOutputs: Record<string, Record<string, unknown>>;
}

// ── Shared sub-components ─────────────────────────────────────

function Card({ label, badge, score, children }: {
  label: string; badge?: { text: string; color: string }; score?: number; children: React.ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-[#1e2d45]/60 bg-[#0d121c]/80 backdrop-blur-md p-4 transition-all duration-500 hover:border-[#2a3f5f] hover:bg-[#131924]/90 hover:shadow-[0_0_20px_rgba(30,45,69,0.3)] group">
      {/* Subtle top gradient accent */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#2a3f5f] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      <div className="flex items-center mb-4 gap-3">
        <span className="font-mono text-[11px] font-bold text-[#8ba3c7] uppercase tracking-[0.12em]">{label}</span>
        {badge && (
          <span className="font-mono text-[10px] font-bold px-2.5 py-1 rounded-md shadow-sm transition-transform group-hover:scale-105"
            style={{ color: badge.color, background:`${badge.color}15`, border:`1px solid ${badge.color}30` }}>
            {badge.text}
          </span>
        )}
        {score != null && (
          <span className="ml-auto font-mono text-[15px] font-black bg-clip-text text-transparent bg-gradient-to-r from-white to-[#8ba3c7] drop-shadow-md">
            {score}
          </span>
        )}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Row({ label, value, sub, color }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="flex items-baseline gap-3 p-1.5 rounded-lg transition-colors hover:bg-white/[0.02]">
      <span className="font-mono text-[11px] text-[#647b9e] shrink-0 w-28 uppercase tracking-wider">{label}</span>
      <span className="font-mono text-[13px] font-bold tracking-tight drop-shadow-sm" style={{ color: color ?? "#f0f4ff" }}>{value}</span>
      {sub && <span className="font-mono text-[10px] text-[#556987] ml-1">{sub}</span>}
    </div>
  );
}

function Divider() {
  return <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-[#1e2d45] to-transparent my-4 opacity-50" />;
}

function pctColor(v: number | null | undefined) {
  if (v == null) return "#9dafc8";
  return v > 0 ? "#12e89e" : v < -0.5 ? "#ff5561" : "#9dafc8";
}
function pctStr(v: number | null | undefined) {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

// ── Fear & Greed Gauge ────────────────────────────────────────

function FearGreedGauge({ value, label }: { value: number; label: string }) {
  const color =
    value <= 25 ? "#ff5561" :
    value <= 40 ? "#fbbf24" :
    value <= 60 ? "#9dafc8" :
    value <= 75 ? "#12e89e" : "#00ff88";

  return (
    <div className="flex items-center gap-4 group cursor-default p-2 rounded-lg hover:bg-white/[0.02] transition-colors">
      {/* Arc gauge bar */}
      <div className="flex-1 h-2.5 rounded-full overflow-hidden bg-[#1a2235] shadow-inner relative">
        <div
          className="absolute top-0 bottom-0 left-0 rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(255,255,255,0.2)]"
          style={{ width:`${value}%`, background:`linear-gradient(90deg, #ff5561, #fbbf24 40%, #12e89e 70%, #00ff88)` }}
        />
      </div>
      <span className="font-mono text-[22px] font-black shrink-0 drop-shadow-[0_0_8px_rgba(255,255,255,0.15)] transition-transform group-hover:scale-110" style={{ color }}>{value}</span>
    </div>
  );
}

// ── External Intelligence Panel ───────────────────────────────

function ExternalIntelPanel() {
  const { data, isLoading } = useQuery({
    queryKey:       ["external-intel"],
    queryFn:        () => fetch(`${BRIDGE}/api/external-intel`).then(r => r.json()),
    refetchInterval: 5 * 60 * 1000,
    staleTime:       3 * 60 * 1000,
  });

  const intel = data as Record<string, unknown> | undefined;

  if (isLoading) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-[#1e2d45]/60 bg-[#0d121c]/80 backdrop-blur-md p-6">
        <div className="font-mono text-[11px] text-[#647b9e] animate-pulse flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#647b9e] animate-ping" />
          Synchronizing global intelligence network...
        </div>
      </div>
    );
  }
  if (!intel) return null;

  const fg       = intel.fear_greed_value    as number | null;
  const fgLabel  = intel.fear_greed_label    as string | null;
  const risk     = intel.global_risk         as string | null;
  const dow      = intel.dow_chg             as number | null;
  const nq       = intel.nasdaq_chg          as number | null;
  const sp       = intel.sp500_chg           as number | null;
  const vix      = intel.vix_level           as number | null;
  const dxy      = intel.dxy_chg             as number | null;
  const wti      = intel.wti_crude           as number | null;
  const gold     = intel.gold_price          as number | null;
  const usd_inr  = intel.usd_inr             as number | null;
  const infy     = intel.infy_adr_chg        as number | null;
  const hdb      = intel.hdb_adr_chg         as number | null;
  const ibn      = intel.ibn_adr_chg         as number | null;
  const wit      = intel.wit_adr_chg         as number | null;
  const nseOpen  = intel.nse_is_open         as boolean | null;
  const nseTime  = intel.nse_time_to_open    as string | null;

  const riskColor =
    risk === "RISK_ON"  ? "#12e89e" :
    risk === "RISK_OFF" ? "#ff5561" : "#9dafc8";

  const vixColor =
    vix == null ? "#9dafc8" : vix > 25 ? "#ff5561" : vix > 18 ? "#fbbf24" : "#12e89e";

  const hasADRs = infy != null || hdb != null || ibn != null;

  return (
    <div className="space-y-4">
      {/* Global Risk + Fear & Greed */}
      <Card
        label="C0 · Global Sentiment"
        badge={risk ? { text: risk.replace("_"," "), color: riskColor } : undefined}
      >
        {fg != null && (
          <div className="mb-2">
            <div className="flex items-center justify-between mb-1.5 px-2">
              <span className="font-mono text-[10px] text-[#647b9e] uppercase tracking-widest font-semibold">Fear & Greed Index</span>
              <span className="font-mono text-[10px] text-[#8ba3c7] font-bold">{fgLabel}</span>
            </div>
            <FearGreedGauge value={fg} label={fgLabel ?? ""} />
            <Divider />
          </div>
        )}
        {/* NSE status */}
        <Row
          label="NSE Status"
          value={nseOpen ? "OPEN" : "CLOSED"}
          sub={!nseOpen && nseTime ? `opens in ${nseTime}` : undefined}
          color={nseOpen ? "#12e89e" : "#9dafc8"}
        />
      </Card>

      {/* US Markets + Commodities */}
      <Card label="C0b · US Markets & Commodities">
        <Row label="S&P 500"   value={pctStr(sp)}  color={pctColor(sp)} />
        <Row label="Dow Jones" value={pctStr(dow)} color={pctColor(dow)} />
        <Row label="Nasdaq"    value={pctStr(nq)}  color={pctColor(nq)} />
        {vix != null && (
          <Row label="VIX"     value={vix.toFixed(2)} color={vixColor}
            sub={vix > 25 ? "elevated" : vix > 18 ? "moderate" : "calm"} />
        )}
        {dxy != null && (
          <Row label="DXY ($)" value={pctStr(dxy)} color={pctColor(dxy)}
            sub={dxy > 0.5 ? "dollar strong" : dxy < -0.5 ? "dollar weak" : undefined} />
        )}
        <Divider />
        {wti  != null && <Row label="WTI Crude" value={`$${wti.toFixed(1)}`}
          color={wti > 95 ? "#ff5561" : "#9dafc8"} sub={wti > 95 ? "above $95" : undefined} />}
        {gold != null && <Row label="Gold"      value={`$${gold.toFixed(0)}`} />}
        {usd_inr != null && (
          <Row label="USD/INR" value={usd_inr.toFixed(2)}
            color={usd_inr > 84 ? "#ff5561" : "#12e89e"}
            sub={usd_inr > 86 ? "rupee very weak" : usd_inr > 84 ? "rupee weak" : "rupee stable"} />
        )}
      </Card>

      {/* India ADRs — real-time US market signals */}
      {hasADRs && (
        <Card label="C0c · India ADRs (US Market Signal)">
          <div className="font-mono text-[11px] text-[#647b9e] mb-3 leading-relaxed italic bg-[#1a2235]/30 p-2 rounded-lg border border-[#1e2d45]/40">
            US-listed Indian stocks. Market moves tonight = NSE gap predictions tomorrow.
          </div>
          <div className="grid grid-cols-1 gap-0.5">
            {infy != null && <Row label="Infosys (INFY)"  value={pctStr(infy)} color={pctColor(infy)} />}
            {hdb  != null && <Row label="HDFC Bank (HDB)" value={pctStr(hdb)}  color={pctColor(hdb)} />}
            {ibn  != null && <Row label="ICICI (IBN)"     value={pctStr(ibn)}  color={pctColor(ibn)} />}
            {wit  != null && <Row label="Wipro (WIT)"     value={pctStr(wit)}  color={pctColor(wit)} />}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Event Calendar ────────────────────────────────────────────

function EventCalendarPanel() {
  const { data } = useQuery({
    queryKey: ["event-calendar"],
    queryFn:  () => fetch(`${BRIDGE}/api/event-calendar`).then(r => r.json()),
    staleTime: 30 * 60 * 1000,
  });

  const events = (data?.upcoming ?? []) as Array<{
    name: string; date: string; days_away: number; type: string;
  }>;

  if (!events.length) return null;

  const typeColor = (t: string) =>
    t === "RBI_MPC" ? "#a78bfa" : t === "FOMC" ? "#60a5fa" :
    t === "EXPIRY"  ? "#fbbf24" : t === "BUDGET" ? "#12e89e" : "#9dafc8";

  return (
    <Card label="C5 · Upcoming Events">
      <div className="space-y-1.5 mt-1">
        {events.slice(0, 6).map((ev, i) => (
          <div key={i} className="flex items-center gap-3 p-1.5 rounded-lg hover:bg-white/[0.02] transition-colors group">
            <span className="font-mono text-[10px] font-bold px-2 py-1 rounded-md shrink-0 shadow-sm transition-transform group-hover:scale-105"
              style={{ color: typeColor(ev.type), background:`${typeColor(ev.type)}15`, border:`1px solid ${typeColor(ev.type)}25` }}>
              {ev.days_away === 0 ? "TODAY" : ev.days_away === 1 ? "TMRW" : `${ev.days_away}d`}
            </span>
            <span className="font-mono text-[12px] text-[#e2e8f0] font-medium tracking-tight truncate">{ev.name}</span>
            <span className="font-mono text-[10px] text-[#647b9e] ml-auto shrink-0">{ev.date}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Main SectionC ─────────────────────────────────────────────

export function SectionC({ macro, agentOutputs }: Props) {
  const l1 = (agentOutputs.l1 ?? {}) as Record<string, unknown>;
  const l2 = (agentOutputs.l2 ?? {}) as Record<string, unknown>;
  const l5 = (agentOutputs.l5 ?? {}) as Record<string, unknown>;
  const l6 = (agentOutputs.l6 ?? {}) as Record<string, unknown>;

  const legend    = l5.legend_consensus as { bull:number; neutral:number; bear:number; total:number; summary:string } | undefined;
  const headlines = (l5.top_headlines as string[]) ?? [];
  const l1rat     = (l1.rationale as string) ?? "";
  const l6rat     = (l6.rationale as string) ?? "";

  return (
    <div className="space-y-4 animate-fade-in pb-8">

      {/* Always-live external intelligence (no analysis needed) */}
      <ExternalIntelPanel />

      {/* Legend Consensus bar — from analysis */}
      {legend && legend.total > 0 && (
        <Card label="C3 · 20-Legend Advisor Consensus">
          <div className="flex h-10 rounded-xl overflow-hidden border border-[#1e2d45]/80 mb-3 shadow-[0_0_15px_rgba(0,0,0,0.2)]">
            {legend.bull > 0 && (
              <div className="flex items-center justify-center font-mono text-[12px] font-black transition-all duration-500 hover:brightness-110"
                style={{ flex:legend.bull, background:"linear-gradient(135deg, #00ff88, #12e89e)", color:"#042f1f" }}>
                {legend.bull}B
              </div>
            )}
            {legend.neutral > 0 && (
              <div className="flex items-center justify-center font-mono text-[12px] font-bold text-[#8ba3c7] transition-all duration-500 hover:brightness-125"
                style={{ flex:legend.neutral, background:"#1a2235" }}>
                {legend.neutral}N
              </div>
            )}
            {legend.bear > 0 && (
              <div className="flex items-center justify-center font-mono text-[12px] font-black transition-all duration-500 hover:brightness-110"
                style={{ flex:legend.bear, background:"linear-gradient(135deg, #ff5561, #ff2a3a)", color:"#3f0005" }}>
                {legend.bear}Be
              </div>
            )}
          </div>
          {legend.summary && (
            <div className="bg-[#1a2235]/40 rounded-lg p-3 border border-[#1e2d45]/30">
              <p className="font-mono text-[12px] text-[#8ba3c7] leading-relaxed">{legend.summary}</p>
            </div>
          )}
        </Card>
      )}

      {/* C1 — Macro (from analysis) */}
      {(l1.macro_score || macro?.fii_net) && (
        <Card label="C1 · Macro Environment" score={(l1.macro_score as number) ?? undefined}>
          <Row label="Risk Context"
            value={(l1.risk_context as string) ?? macro?.risk_context ?? "—"}
            color={(l1.risk_context ?? macro?.risk_context) === "RISK_ON" ? "#12e89e" :
                   (l1.risk_context ?? macro?.risk_context) === "RISK_OFF"? "#ff5561" : undefined}
          />
          {macro?.brent_oil && (
            <Row label="Brent Oil" value={`$${macro.brent_oil.toFixed(1)}`}
              sub={macro.oil_shock_active ? "SHOCK" : ""}
              color={macro.oil_shock_active ? "#ff5561" : "#9dafc8"}
            />
          )}
          <Row label="FII Net" value={fmtCr(macro?.fii_net)}
            color={macro?.fii_net != null && macro.fii_net > 0 ? "#12e89e" : "#ff5561"} />
          <Row label="DII Net" value={fmtCr(macro?.dii_net)}
            color={macro?.dii_net != null && macro.dii_net > 0 ? "#12e89e" : "#9dafc8"} />
          {l1rat && (
            <>
              <Divider />
              <div className="bg-[#1a2235]/40 rounded-lg p-3 border border-[#1e2d45]/30">
                <p className="font-mono text-[12px] text-[#8ba3c7] leading-relaxed">{l1rat}</p>
              </div>
            </>
          )}
        </Card>
      )}

      {/* C2 — Fundamentals */}
      {(l2.valuation_status || l2.earnings_trend) && (
        <Card label="C2 · Fundamental Health" score={(l2.fundamental_score as number) ?? undefined}>
          <Row label="Valuation" value={(l2.valuation_status as string) ?? "—"}
            color={(l2.valuation_status as string) === "UNDERVALUED" ? "#12e89e" :
                   (l2.valuation_status as string) === "OVERVALUED" ? "#ff5561" : undefined} />
          <Row label="Earnings" value={(l2.earnings_trend as string) ?? "—"}
            color={(l2.earnings_trend as string) === "ACCELERATING" ? "#12e89e" :
                   (l2.earnings_trend as string) === "DECELERATING" ? "#ff5561" : undefined} />
          <Row label="Inst. Flow" value={(l2.institutional_flow as string) ?? "—"} />
        </Card>
      )}

      {/* C4 — Live headlines */}
      {headlines.length > 0 && (
        <Card label="C4 · Live Market Headlines">
          <div className="space-y-2 mt-1">
            {headlines.slice(0, 8).map((h, i) => (
              <div key={i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/[0.02] transition-colors group">
                <span className="font-mono text-[10px] font-bold text-[#647b9e] shrink-0 mt-0.5 bg-[#1a2235] w-5 h-5 rounded flex items-center justify-center border border-[#1e2d45]/50 group-hover:border-[#647b9e]/50 transition-colors">{i+1}</span>
                <span className="font-mono text-[12px] text-[#e2e8f0] leading-relaxed">{h}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* C6 — Event intelligence narrative */}
      {l6rat && (
        <Card label="C6 · Event Intelligence">
          <div className="bg-gradient-to-br from-[#1a2235]/60 to-[#0d121c]/80 rounded-lg p-3.5 border border-[#1e2d45]/40 shadow-inner">
            <p className="font-mono text-[12px] text-[#8ba3c7] leading-relaxed tracking-wide">{l6rat}</p>
          </div>
        </Card>
      )}

      {/* C5 — Event calendar — always visible */}
      <EventCalendarPanel />
    </div>
  );
}
