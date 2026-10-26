"""Predeclared matched-entry exit audit (cached OHLC only; never sends orders).

Historical candles/slices have been inspected before. These are descriptive
paired comparisons, NOT independent out-of-sample evidence.
"""
import datetime as dt
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

from execution_core import resolve_bar
from feature_walkforward import data
from pattern_confluence import flags
from p0_gap_audit import simulate as frozen_cohort_simulate

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
COSTS=(0.0015,0.0025,0.004)
FUNDING_STRESS=(0.0,0.0001,0.0003)  # adverse assumed cost per 8h; not actual funding
BLOCK_MS=30*24*3600*1000
BOOTSTRAPS=2500
SEED=20261026
FREEZE_UTC="2026-10-26T16:00:00Z"

def selected_entries(rows,features,lo,hi,sl,tp):
    """Entry cohort from frozen fixed-exit scheduling, not challenger scheduling."""
    return frozen_cohort_simulate(rows,features,lo,hi,sl,tp,12,"corrected")

def exit_one(rows,raw,trade,sl,tp,mode,segment_hi):
    i=trade["entry_index"];side=trade["side"];signal=trade["signal_index"]
    entry=rows[i][1];atr=raw[signal]["atr"]
    stop=entry-side*sl*atr;target=entry+side*tp*atr
    last=min(i+11,segment_hi-1,len(rows)-1)
    out=rows[last][4];end=last;why="time"
    for j in range(i,last+1):
        fill,reason=resolve_bar(rows[j],side,stop,target)
        if reason:
            out=fill;end=j;why=reason;break
        close=rows[j][4]
        # The signal at j is available only after the j close; exit at j+1 open.
        if j<last and mode in ("reverse","structure"):
            reverse=raw[j] is not None and raw[j]["turn"] and raw[j]["side"]==-side
            structure=j>=3 and (close<min(x[3] for x in rows[j-3:j]) if side==1 else close>max(x[2] for x in rows[j-3:j]))
            if (mode=="reverse" and reverse) or (mode=="structure" and structure):
                out=rows[j+1][1];end=j+1;why=mode;break
        if mode=="trail3" and side*(close-entry)>=2*atr:
            proposed=close-side*3*atr
            # stop can only tighten; it becomes effective NEXT bar.
            stop=max(stop,proposed) if side==1 else min(stop,proposed)
            # Defensive clamp for validity in canonical fill engine.
            if side==1:stop=min(stop,math.nextafter(target,0))
            else:stop=max(stop,math.nextafter(target,math.inf))
    return {"signal_index":signal,"entry_index":i,"exit_index":end,"side":side,
            "signal_utc":dt.datetime.fromtimestamp(rows[signal][0]/1000,dt.timezone.utc).isoformat(),
            "gross":side*(out/entry-1),"hours":(rows[end][0]-rows[i][0])/3600000,
            "reason":why,"entry_price":entry,"exit_price":out}

def metric(returns):
    if not returns:return {"n":0}
    p=sum(max(0,x) for x in returns);l=-sum(min(0,x) for x in returns)
    eq=peak=1.0;dd=0
    for r in returns:
        eq*=max(0.001,1+r);peak=max(peak,eq);dd=max(dd,1-eq/peak)
    return {"n":len(returns),"win_pct":round(100*sum(x>0 for x in returns)/len(returns),2),
            "mean_pct":round(100*statistics.mean(returns),4),
            "pf":round(p/l,4) if l else None,
            "pseudo_compound_pct":round(100*(eq-1),3),
            "pseudo_max_dd_pct":round(100*dd,3)}

def net(t,cost,funding):
    # Use elapsed UTC hours rather than bars; 8h events approximated conservatively.
    return t["gross"]-cost-math.ceil(t["hours"]/8)*funding

def bootstrap_delta(base,challenger,rows,seed=SEED):
    """30-calendar-day cluster bootstrap on *paired* return deltas, no iid trade CI."""
    assert len(base)==len(challenger)
    if not base:return None
    groups={}
    for b,c in zip(base,challenger):
        assert b["signal_index"]==c["signal_index"]
        bucket=rows[b["signal_index"]][0]//BLOCK_MS
        groups.setdefault(bucket,[]).append(c["gross"]-b["gross"])
    blocks=list(groups.values())
    if len(blocks)<4:return {"ci95_mean_delta_pct":None,"calendar_blocks":len(blocks),"reason":"<4 time blocks"}
    rng=random.Random(seed);draws=[]
    for _ in range(BOOTSTRAPS):
        sampled=[blocks[rng.randrange(len(blocks))] for __ in blocks]
        vals=[v for block in sampled for v in block]
        draws.append(statistics.mean(vals))
    draws.sort()
    return {"calendar_blocks":len(blocks),"bootstrap_reps":BOOTSTRAPS,
            "mean_delta_pct":round(100*statistics.mean(c["gross"]-b["gross"] for b,c in zip(base,challenger)),4),
            "ci95_mean_delta_pct":[round(100*draws[int(.025*(BOOTSTRAPS-1))],4),
                                   round(100*draws[int(.975*(BOOTSTRAPS-1))],4)]}

def run():
    out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "freeze_utc":FREEZE_UTC,
         "hypothesis":"Raw opposite-DeltaRSI exit increases ETH OB-proxy fixed-cohort net expectancy over fixed 48h exit.",
         "predeclared_primary":"ETHUSDT selected OHLC OB proxy; 2.5ATR stop, 6ATR TP, 12x4H maximum; raw reverse versus fixed, same baseline-scheduled entry IDs.",
         "exploratory_secondary":"Frozen 2.5ATR/3ATR/12x4H baseline on all four assets, same-cohort raw reverse, structure and 3ATR trail as diagnostics only.",
         "warning":"ALL history reused/previously examined; NOT independent OOS. Paired pseudo-equity/DD assumes sequential trades although challenger exits may overlap other cohort trades. No production recommendation.",
         "costs":"0.15/0.25/0.40% total assumed round-trip fees+slippage; funding 0/0.01/0.03% adverse per 8h stress, NOT venue funding. No mark price, spread, liquidation, impact, correlated risk.",
         "assets":{}}
    for sym in SYMS:
        source=Path("data")/(sym+"_1h.csv")
        rows,raw=data(sym)
        cuts=[0]+[len(rows)*k//5 for k in range(1,5)]+[len(rows)]
        specs=[("frozen_baseline",raw,2.5,3.0)]
        if sym=="ETHUSDT":
            filt=[({**f,"turn":f["turn"] and flags(rows,raw,i).get("ob_proxy",False)} if f else None) for i,f in enumerate(raw)]
            specs.append(("selected_eth_ob",filt,2.5,6.0))
        configs={}
        for name,features,sl,tp in specs:
            all_by_mode={mode:[] for mode in ("fixed","reverse","structure","trail3")}
            per=[]
            for k in range(5):
                lo,hi=cuts[k],cuts[k+1]
                cohort=selected_entries(rows,features,lo,hi,sl,tp)
                bymode={mode:[exit_one(rows,raw,t,sl,tp,mode,hi) for t in cohort]
                        for mode in ("fixed","reverse","structure","trail3")}
                for mode in all_by_mode:all_by_mode[mode].extend(bymode[mode])
                assert all([t["signal_index"] for t in bymode["fixed"]]==
                           [t["signal_index"] for t in bymode[mode]] for mode in bymode)
                assert all(x["gross"]==t["gross"] for x,t in zip(bymode["fixed"],cohort))
                per.append({"slice":k+1,"bar_edges":[lo,hi],
                    "modes":{mode:{"15bp":metric([net(t,.0015,0) for t in ts]),
                                   "25bp":metric([net(t,.0025,0) for t in ts]),
                                   "40bp":metric([net(t,.004,0) for t in ts]),
                                   "15bp_funding_1bp_8h":metric([net(t,.0015,.0001) for t in ts]),
                                   "15bp_funding_3bp_8h":metric([net(t,.0015,.0003) for t in ts])}
                             for mode,ts in bymode.items()},
                    "paired_vs_fixed":{mode:bootstrap_delta(bymode["fixed"],bymode[mode],rows,SEED+k)
                                        for mode in ("reverse","structure","trail3")}})
            configs[name]={"stop_atr":sl,"target_atr":tp,"hold_bars":12,"slices":per,
              "all_reused_history":{"modes":{
                 mode:{"15bp":metric([net(t,.0015,0) for t in ts]),
                       "25bp":metric([net(t,.0025,0) for t in ts]),
                       "40bp":metric([net(t,.004,0) for t in ts]),
                       "15bp_funding_1bp_8h":metric([net(t,.0015,.0001) for t in ts]),
                       "15bp_funding_3bp_8h":metric([net(t,.0015,.0003) for t in ts])}
                 for mode,ts in all_by_mode.items()},
                "paired_vs_fixed":{mode:bootstrap_delta(all_by_mode["fixed"],all_by_mode[mode],rows)
                     for mode in ("reverse","structure","trail3")}}}
        out["assets"][sym]={"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                            "four_hour_bars":len(rows),"configs":configs}
    path=Path("reports/matched_exit_audit.json");path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps({s:{name:[(x["slice"],x["modes"]["fixed"]["15bp"]["n"],
                  x["paired_vs_fixed"]["reverse"]) for x in c["slices"]]
                 for name,c in a["configs"].items()} for s,a in out["assets"].items()}))
if __name__=="__main__":run()
