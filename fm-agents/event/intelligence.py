"""FM Trading Agency — Event Intelligence Engine (v2)"""
from __future__ import annotations
from dataclasses import dataclass, field
import logging
log = logging.getLogger("fm.agents.event")

_KEYWORD_RULES = [
    (["ICICI Bank","HDFC Bank","SBI","Axis Bank","Kotak Bank","IndusInd","Yes Bank"], "BANK NIFTY", 18.0, "BANKING_STRESS"),
    (["NPA","NPL","bad loans","stressed assets","GNPA","NNPA"], "BANK NIFTY", 20.0, "BANKING_STRESS"),
    (["banking sector","bank stocks","PSU banks","NBFC stress"], "BANK NIFTY", 14.0, "BANKING_STRESS"),
    (["Infosys","TCS","Wipro","HCL Tech","Tech Mahindra","Mphasis"], "NIFTY IT", 15.0, "SECTOR_ROTATION"),
    (["IT sector","tech sector","software exports","H-1B","NASSCOM"], "NIFTY IT", 12.0, "SECTOR_ROTATION"),
    (["oil surge","crude spike","$100","$110","$120","oil above 100"], "NIFTY 50", 20.0, "OIL_SHOCK"),
    (["oil falls","crude drops","crude below 80"], "NIFTY 50", -8.0, "NONE"),
    (["RBI rate hike","repo rate hike","hawkish RBI"], "NIFTY 50", 12.0, "RBI_ACTION"),
    (["RBI rate cut","repo rate cut","dovish RBI","accommodative"], "NIFTY 50", -10.0, "RBI_ACTION"),
    (["RBI pause","RBI holds","repo unchanged"], "NIFTY 50", -3.0, "RBI_ACTION"),
    (["Fed rate hike","FOMC hike","Powell hawkish"], "NIFTY 50", 10.0, "MACRO_RISK"),
    (["Fed rate cut","FOMC cut","Powell dovish"], "NIFTY 50", -8.0, "MACRO_RISK"),
    (["FII selling","FII outflow","foreign selling","FPI selling"], "NIFTY 50", 14.0, "FII_SELLING"),
    (["FII buying","FII inflow","foreign buying"], "NIFTY 50", -8.0, "NONE"),
    (["VIX spike","circuit breaker","market crash","selloff","panic selling"], "NIFTY 50", 28.0, "VOLATILITY_EXPANSION"),
    (["US market crash","Dow falls","global selloff","risk-off","recession fears"], "NIFTY 50", 15.0, "GLOBAL_RISK_OFF"),
    (["India CPI","India inflation","IIP data"], "NIFTY 50", 6.0, "MACRO_RISK"),
    (["US CPI","US inflation","GDP data"], "NIFTY 50", 8.0, "MACRO_RISK"),
    (["rupee crash","INR weakness","INR falls"], "NIFTY 50", 12.0, "MACRO_RISK"),
    (["rupee strengthens","INR gains"], "NIFTY 50", -4.0, "NONE"),
    (["FDA warning","FDA import alert","drug recall"], "NIFTY PHARMA", 18.0, "SECTOR_ROTATION"),
    (["FDA approval","drug approval","USFDA approval"], "NIFTY PHARMA", -10.0, "EARNINGS_SURPRISE"),
    (["Sun Pharma","Dr Reddy","Cipla","Lupin","Aurobindo"], "NIFTY PHARMA", 12.0, "SECTOR_ROTATION"),
    (["auto sales miss","vehicle sales decline","chip shortage"], "NIFTY AUTO", 12.0, "SECTOR_ROTATION"),
    (["Maruti","Tata Motors","M&M","Hero MotoCorp"], "NIFTY AUTO", 10.0, "SECTOR_ROTATION"),
    (["steel demand falls","metal prices crash","China slowdown"], "NIFTY METAL", 15.0, "SECTOR_ROTATION"),
    (["expiry day","weekly expiry","F&O expiry"], "NIFTY 50", 8.0, "EXPIRY_PRESSURE"),
    (["earnings miss","revenue miss","guidance cut","profit warning"], "NIFTY 50", 10.0, "EARNINGS_SURPRISE"),
    (["earnings beat","record profit","guidance raised"], "NIFTY 50", -5.0, "EARNINGS_SURPRISE"),
]

@dataclass
class EventContext:
    index_stress:         dict  = field(default_factory=dict)
    market_stress:        float = 0.0
    banking_risk:         float = 0.0
    tech_risk:            float = 0.0
    macro_risk:           float = 0.0
    volatility_risk:      float = 0.0
    global_risk:          float = 0.0
    detected_events:      list  = field(default_factory=list)
    event_severity:       str   = "NONE"
    triggering_headlines: list  = field(default_factory=list)
    quant_drivers:        list  = field(default_factory=list)
    narrative:            str   = "No significant market events detected."

    def get_stress(self, index):
        return min(100.0, self.index_stress.get(index, self.market_stress * 0.5))

    def to_dict(self):
        return {
            "index_stress":        {k: round(v,1) for k,v in self.index_stress.items()},
            "market_stress":       round(self.market_stress,1),
            "banking_risk":        round(self.banking_risk,1),
            "tech_risk":           round(self.tech_risk,1),
            "macro_risk":          round(self.macro_risk,1),
            "volatility_risk":     round(self.volatility_risk,1),
            "global_risk":         round(self.global_risk,1),
            "detected_events":     self.detected_events,
            "event_severity":      self.event_severity,
            "triggering_headlines":self.triggering_headlines,
            "quant_drivers":       self.quant_drivers,
            "narrative":           self.narrative,
        }


def _quantitative_baseline(quant):
    stress = {"NIFTY 50":0.0,"BANK NIFTY":0.0,"NIFTY IT":0.0,"NIFTY PHARMA":0.0,"NIFTY AUTO":0.0,"NIFTY METAL":0.0}
    drivers = []
    vix = float(quant.get("india_vix") or 0)
    if vix > 20:
        d = min(30.0,(vix-20)*3); stress["NIFTY 50"]+=d; drivers.append(f"VIX {vix:.1f} (+{d:.0f})")
    elif vix > 17:
        d=(vix-17)*2; stress["NIFTY 50"]+=d; drivers.append(f"VIX elevated {vix:.1f} (+{d:.0f})")
    elif 0<vix<13:
        for k in stress: stress[k]-=5.0
        drivers.append(f"VIX calm {vix:.1f} (-5)")
    fii = float(quant.get("fii_net") or 0)
    if fii < -4000: stress["NIFTY 50"]+=25.0; stress["BANK NIFTY"]+=20.0; drivers.append(f"FII heavy sell Rs{fii:,.0f}Cr (+25)")
    elif fii < -2000: stress["NIFTY 50"]+=15.0; stress["BANK NIFTY"]+=10.0; drivers.append(f"FII selling Rs{fii:,.0f}Cr (+15)")
    elif fii < -500: stress["NIFTY 50"]+=8.0; drivers.append(f"FII mild sell Rs{fii:,.0f}Cr (+8)")
    elif fii > 4000: stress["NIFTY 50"]-=12.0; stress["BANK NIFTY"]-=8.0; drivers.append(f"FII heavy buy Rs{fii:,.0f}Cr (-12)")
    elif fii > 2000: stress["NIFTY 50"]-=8.0; drivers.append(f"FII buying Rs{fii:,.0f}Cr (-8)")
    oil = float(quant.get("brent_oil") or 0)
    if oil>110: stress["NIFTY 50"]+=20.0; drivers.append(f"Brent ${oil:.0f} (+20)")
    elif oil>100: stress["NIFTY 50"]+=12.0; drivers.append(f"Brent ${oil:.0f} (+12)")
    elif 0<oil<75: stress["NIFTY 50"]-=6.0; drivers.append(f"Brent ${oil:.0f} cheap (-6)")
    dow=float(quant.get("dow_change_pct") or 0); nq=float(quant.get("nasdaq_change_pct") or 0)
    if dow<-1.5 or nq<-2.0:
        d=min(25.0,abs(min(dow,nq))*5); stress["NIFTY 50"]+=d; stress["NIFTY IT"]+=d*1.2
        drivers.append(f"US Dow{dow:+.1f}% NQ{nq:+.1f}% (+{d:.0f})")
    elif dow>1.0 or nq>1.5:
        d=min(12.0,max(dow,nq)*3); stress["NIFTY 50"]-=d; stress["NIFTY IT"]-=d*1.1
        drivers.append(f"US Dow{dow:+.1f}% NQ{nq:+.1f}% (-{d:.0f})")
    inr=float(quant.get("usd_inr") or 0)
    if inr>85: stress["NIFTY 50"]+=10.0; stress["NIFTY IT"]-=6.0; drivers.append(f"USD/INR {inr:.2f} weak (+10,-6 IT)")
    elif inr>84: stress["NIFTY 50"]+=5.0; stress["NIFTY IT"]-=3.0
    elif 0<inr<82.5: stress["NIFTY IT"]+=8.0; stress["NIFTY 50"]-=3.0; drivers.append(f"USD/INR {inr:.2f} strong (+8 IT)")
    rbi=(quant.get("rbi_stance") or "NEUTRAL").upper()
    if rbi=="HAWKISH": stress["NIFTY 50"]+=8.0; stress["BANK NIFTY"]+=12.0; drivers.append("RBI HAWKISH (+8 Nifty +12 Bank)")
    elif rbi=="DOVISH": stress["NIFTY 50"]-=8.0; stress["BANK NIFTY"]-=6.0; drivers.append("RBI DOVISH (-8 Nifty -6 Bank)")
    oi=(quant.get("oi_change_pattern") or "NEUTRAL").upper()
    if oi=="SHORT_BUILDUP": stress["NIFTY 50"]+=8.0; drivers.append("OI Short buildup (+8)")
    elif oi=="LONG_UNWINDING": stress["NIFTY 50"]+=10.0; drivers.append("OI Long unwinding (+10)")
    elif oi=="LONG_BUILDUP": stress["NIFTY 50"]-=5.0; drivers.append("OI Long buildup (-5)")
    elif oi=="SHORT_COVERING": stress["NIFTY 50"]-=3.0; drivers.append("OI Short covering (-3)")
    gr=(quant.get("global_risk") or "NEUTRAL").upper()
    if gr=="RISK_OFF": stress["NIFTY 50"]+=8.0; drivers.append("Global RISK_OFF (+8)")
    elif gr=="RISK_ON": stress["NIFTY 50"]-=5.0; drivers.append("Global RISK_ON (-5)")
    stress={k:max(0.0,min(60.0,v)) for k,v in stress.items()}
    return stress, drivers


def _scale_delta(base, quant, index, event_type):
    if base < 0:
        vix=float(quant.get("india_vix") or 15)
        return base*(0.5 if vix>20 else 1.0)
    scale=1.0
    if event_type=="FII_SELLING":
        fii=abs(float(quant.get("fii_net") or 0))
        scale=1.5 if fii>5000 else(1.2 if fii>2000 else(0.4 if fii<500 else 1.0))
    elif event_type=="VOLATILITY_EXPANSION":
        vix=float(quant.get("india_vix") or 15)
        scale=1.4 if vix>22 else(1.1 if vix>18 else(0.5 if vix<15 else 1.0))
    elif event_type=="OIL_SHOCK":
        oil=float(quant.get("brent_oil") or 80)
        scale=1.5 if oil>110 else(1.2 if oil>100 else(0.5 if oil<90 else 1.0))
    elif event_type=="GLOBAL_RISK_OFF":
        dow=float(quant.get("dow_change_pct") or 0)
        scale=1.4 if dow<-2.0 else(1.1 if dow<-1.0 else(0.3 if dow>0 else 1.0))
    elif event_type=="BANKING_STRESS":
        rbi=(quant.get("rbi_stance") or "NEUTRAL").upper()
        scale=1.3 if rbi=="HAWKISH" else(0.7 if rbi=="DOVISH" else 1.0)
    if index=="NIFTY IT":
        inr=float(quant.get("usd_inr") or 83)
        scale*=(0.7 if inr>84 else(1.3 if inr<82 else 1.0))
    return round(base*scale,1)


def _apply_keywords(headlines, stress, quant):
    combined=" ".join(headlines).lower()
    events,triggers,applied=[],[],[]
    for keywords,index,base_delta,event_type in _KEYWORD_RULES:
        for kw in keywords:
            if kw.lower() in combined:
                delta=_scale_delta(base_delta,quant,index,event_type)
                stress[index]=stress.get(index,0)+delta
                if event_type!="NONE" and event_type not in events: events.append(event_type)
                for h in headlines:
                    if kw.lower() in h.lower() and h not in triggers: triggers.append(h); break
                applied.append(f"{index} {delta:+.0f} ({event_type})")
                break
    stress={k:max(0.0,min(100.0,v)) for k,v in stress.items()}
    return stress,events,triggers[:4],applied


def _derive_levels(stress, events):
    market=min(100.0,max(stress.values()) if stress else 0.0)
    banking=stress.get("BANK NIFTY",0.0); tech=stress.get("NIFTY IT",0.0)
    vol=30.0 if "VOLATILITY_EXPANSION" in events else 0.0
    glob=25.0 if "GLOBAL_RISK_OFF" in events else 0.0
    macro=max(stress.get("NIFTY 50",0)*0.6,
              25.0 if any(e in events for e in ("MACRO_RISK","OIL_SHOCK","RBI_ACTION")) else 0.0)
    return market,banking,tech,macro,vol,glob


def _severity(market, events):
    if "VOLATILITY_EXPANSION" in events or market>=65: return "CRITICAL"
    if market>=45: return "HIGH"
    if market>=25: return "MEDIUM"
    if market>=10: return "LOW"
    return "NONE"


def _fallback_narrative(ctx):
    if ctx.banking_risk>40: return f"Banking sector under significant pressure — {ctx.event_severity.lower()} risk."
    if "GLOBAL_RISK_OFF" in ctx.detected_events: return "Global risk-off overnight — watch gap-down and FII flows at open."
    if "OIL_SHOCK" in ctx.detected_events: return "Brent crude above $100 — macro stress elevated, avoid long side."
    if "VOLATILITY_EXPANSION" in ctx.detected_events: return f"Volatility expanding — {ctx.event_severity.lower()} conditions."
    if ctx.macro_risk>30:
        evs=", ".join(ctx.detected_events[:2]).lower().replace("_"," ")
        return f"Macro risk elevated — {evs} in focus."
    return f"Market events detected ({ctx.event_severity.lower()}) — elevated caution advised."


def _generate_narrative(ctx, llm):
    if ctx.event_severity=="NONE" or ctx.detected_events==["NONE"]:
        return "No significant market events detected — standard technical signals apply."
    stress_str=", ".join(f"{k.replace('NIFTY ','')}: {v:.0f}" for k,v in ctx.index_stress.items() if v>15)
    prompt=(
        "You are a senior NSE derivatives trader. "
        "In EXACTLY ONE sentence (max 20 words), state the key market event risk.\n\n"
        f"Events: {', '.join(ctx.detected_events[:4])}\n"
        f"Drivers: {' | '.join(ctx.quant_drivers[:3])}\n"
        f"Stress: {stress_str}\n"
        f"Headlines: {' | '.join(ctx.triggering_headlines[:2])}\n\n"
        "One crisp sentence. No disclaimer."
    )
    try:
        response=llm.invoke(prompt)
        text=response.content if hasattr(response,"content") else str(response)
        sentence=text.split(".")[0].strip()+"."
        return sentence if len(sentence)>15 else _fallback_narrative(ctx)
    except Exception as e:
        log.warning("Event narrative LLM failed: %s",e)
        return _fallback_narrative(ctx)


def analyse_events(headlines, quant=None, llm=None):
    """
    Full event intelligence pipeline v2.
    Problem 1: Called from context_builder step 10 (was dead code).
    Problem 2: NSE-specific keyword routing.
    Problem 3: Quantitative signals scale stress deltas.
    """
    _q=quant or {}
    stress,quant_drivers=_quantitative_baseline(_q)
    keyword_events,triggers,applied=[],[],[]
    if headlines:
        stress,keyword_events,triggers,applied=_apply_keywords(headlines,stress,_q)
    qe=[]
    if float(_q.get("fii_net") or 0)<-2000: qe.append("FII_SELLING")
    if float(_q.get("india_vix") or 0)>18:  qe.append("VOLATILITY_EXPANSION")
    if float(_q.get("brent_oil") or 0)>100: qe.append("OIL_SHOCK")
    if float(_q.get("dow_change_pct") or 0)<-1.5: qe.append("GLOBAL_RISK_OFF")
    if (_q.get("rbi_stance") or "").upper() in ("HAWKISH","DOVISH"): qe.append("RBI_ACTION")
    all_events=list(dict.fromkeys(qe+keyword_events))
    if not all_events: all_events=["NONE"]
    market,banking,tech,macro,vol,glob=_derive_levels(stress,all_events)
    severity=_severity(market,all_events)
    ctx=EventContext(
        index_stress={k:round(v,1) for k,v in stress.items()},
        market_stress=round(market,1), banking_risk=round(banking,1),
        tech_risk=round(tech,1), macro_risk=round(macro,1),
        volatility_risk=round(vol,1), global_risk=round(glob,1),
        detected_events=all_events, event_severity=severity,
        triggering_headlines=triggers, quant_drivers=quant_drivers, narrative="",
    )
    ctx.narrative=_generate_narrative(ctx,llm) if llm else _fallback_narrative(ctx)
    log.info("EventIntel v2: severity=%s market=%.0f banking=%.0f events=%s drivers=%d",
             severity,market,banking,all_events[:3],len(quant_drivers))
    return ctx