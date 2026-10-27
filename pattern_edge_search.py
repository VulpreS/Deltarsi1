"""DeltaRSI exploratory pattern/stop/exit grid; cached candles only; no orders.
Issue #10 priority (2026-10-27). All three historical slices were previously inspected.
Never label the last slice untouched OOS. Fee fixed at 15bp round trip.
Reproduce: python -m unittest -v test_pattern_edge_search && python pattern_edge_search.py
"""
import csv, datetime as dt, hashlib, json, math, statistics
from pathlib import Path
from itertools import product
from collections import defaultdict
from causal_4h_parity_audit import load, events, H
from completed_candles import aggregate_completed
from execution_core import resolve_bar
FEE = 0.0015
RISK = 0.0025
SYMS = ("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
MODES = ("forming","closed","turn")
FILTERS = ("all","follow_ema50","counter_ema50","follow_ema200","wick_reject","sweep20")
STOPS = ("atr2.5","prior_peak4h","prior_wave6x4h")
TPS = (1.5,3.0)
HOLDS = (12,24,48)
CONFIGS = list(product(MODES,FILTERS,STOPS,TPS,HOLDS))
SEED = 20261027
def ema(values,n):
    a=2/(n+1); out=[];v=None
    for x in values:
        v=x if v is None else a*x+(1-a)*v
        out.append(v)
    return out
def asof_features(raw,bars,ev):
    """Every feature timestamp is strictly before next-open entry."""
    index={b[0]:i for i,b in enumerate(bars)}
    c=[b[4] for b in bars];e50=ema(c,50);e200=ema(c,200)
    out=[]
    for e in ev:
        j=index.get(e["bucket_ms"]);k=e["entry_i"]-1
        if j is None or j<210 or k<21 or k>=len(raw):continue
        # Previous 4H bar is completed for every mode, including h=1 forming.
        ref=bars[j-1];side=e["side"];trend=side*(ref[4]-e50[j-1])>0
        trend200=side*(ref[4]-e200[j-1])>0
        b=raw[k];o,hi,lo,close=b[1:]
        rng=max(hi-lo,1e-12);body=abs(close-o)
        wick=(min(o,close)-lo) if side==1 else (hi-max(o,close))
        wick_ok=wick>=0.35*rng and wick>=1.5*body
        prev=raw[k-20:k]
        prev_low=min(x[3] for x in prev);prev_high=max(x[2] for x in prev)
        sweep=(lo<prev_low and close>prev_low) if side==1 else (hi>prev_high and close<prev_high)
        z=dict(e,asof_i=k,asof_utc=dt.datetime.fromtimestamp((b[0]+H)/1000,dt.timezone.utc).isoformat(),
               trend50=trend,trend200=trend200,wick_reject=wick_ok,sweep20=sweep,
               peak_low=bars[j-1][3],peak_high=bars[j-1][2],
               wave_low=min(x[3] for x in bars[j-6:j]),
               wave_high=max(x[2] for x in bars[j-6:j]))
        out.append(z)
    return out
def allowed(e,filt):
    return (filt=="all" or
        (filt=="follow_ema50" and e["trend50"]) or
        (filt=="counter_ema50" and not e["trend50"]) or
        (filt=="follow_ema200" and e["trend200"]) or
        (filt=="wick_reject" and e["wick_reject"]) or
        (filt=="sweep20" and e["sweep20"]))
def stop_for(e,entry,side,mode):
    a=e["atr_4h"]
    if not math.isfinite(a) or a<=0:return None
    if mode=="atr2.5":return entry-side*2.5*a
    if mode=="prior_peak4h":
        return (e["peak_low"]-.05*a) if side==1 else (e["peak_high"]+.05*a)
    if mode=="prior_wave6x4h":
        return (e["wave_low"]-.05*a) if side==1 else (e["wave_high"]+.05*a)
    raise ValueError(mode)
def one(raw,e,stopmode,tp,hold,terminal):
    i=e["entry_i"]
    if i>=terminal:return None
    side=e["side"];entry=raw[i][1];stop=stop_for(e,entry,side,stopmode)
    if stop is None or entry<=0:return None
    distance=side*(entry-stop)
    if not (0.001<=distance/entry<=0.12):return None
    target=entry+side*tp*distance
    end=min(i+hold-1,terminal-1)
    out=raw[end][4];exit_i=end;reason="time"
    for k in range(i,end+1):
        fill,why=resolve_bar(raw[k],side,stop,target)
        if why:
            out=fill;exit_i=k;reason=why;break
    # Exact entry/exit-notional half-cost. No funding by manager instruction.
    gross_R=side*(out-entry)/distance
    cost_R=(entry+out)*FEE/(2*distance)
    net_R=gross_R-cost_R
    return dict(entry_i=i,exit_i=exit_i,side=side,entry_utc=e["entry_utc"],
                exit_reason=reason,net_R=net_R,net_pct=100*(side*(out-entry)-(entry+out)*FEE/2)/entry,
                symbol=e["symbol"],mode=e["mode"],asof_utc=e["asof_utc"])
def simulate(raw,ev,cfg,start,end):
    mode,filt,stop,tp,hold=cfg;until=-1;tr=[];reject=defaultdict(int)
    for e in ev:
        if e["mode"]!=mode:continue
        i=e["entry_i"]
        if i<start or i>=end:continue
        if not allowed(e,filt):reject["filter"]+=1;continue
        if i<=until:reject["occupied"]+=1;continue
        t=one(raw,e,stop,tp,hold,end)
        if t is None:reject["stop_geometry_or_terminal"]+=1;continue
        tr.append(t);until=t["exit_i"]
    return tr,dict(reject)
def stats(tr):
    if not tr:return dict(n=0,win_pct=None,mean_R=None,mean_net_pct=None,pf=None,pseudo_dd_pct=None)
    v=[x["net_R"] for x in tr];pos=sum(max(0,x) for x in v);neg=-sum(min(0,x) for x in v)
    eq=peak=1.;dd=0.
    for r in v:
        eq*=max(.000001,1+RISK*r)
        peak=max(peak,eq);dd=max(dd,1-eq/peak)
    return dict(n=len(v),win_pct=round(100*sum(x>0 for x in v)/len(v),2),
       mean_R=round(statistics.mean(v),5),mean_net_pct=round(statistics.mean(x["net_pct"] for x in tr),5),
       pf=round(pos/neg,4) if neg else None,pseudo_dd_pct=round(100*dd,4))
def main():
    cache={};hashes={}
    for sym in SYMS:
        raw,sha=load(sym);hashes[sym]=sha
        es,bars=events(raw)
        ev=[]
        for mode,key in (("forming","forming"),("closed","closed"),("turn","frozen_turn")):
            for e in es[key]:ev.append(dict(e,mode=mode,symbol=sym))
        ev=asof_features(raw,bars,ev)
        ev.sort(key=lambda x:(x["entry_i"],x["symbol"],x["mode"]))
        cut=(0,len(raw)//2,len(raw)*3//4,len(raw))
        cache[sym]=(raw,ev,cut)
    results=[]
    for cfg in CONFIGS:
        periods=[];byasset={}
        for w in range(3):
            t=[];asset={}
            for sym,(raw,ev,cut) in cache.items():
                trades,rej=simulate(raw,ev,cfg,cut[w],cut[w+1])
                t.extend(trades);asset[sym]=dict(stats=stats(trades),rejections=rej)
            periods.append(stats(t));byasset["train_validation_test"[0:0] or ("train","validation","diagnostic_test")[w]]=asset
        train,val=periods[:2]
        gate=train["n"]>=30 and val["n"]>=12 and train["mean_R"]>0 and val["mean_R"]>0 and (train["pf"] or 0)>1 and (val["pf"] or 0)>1
        score=min(train["mean_R"],val["mean_R"]) if gate else -1e6
        results.append(dict(config=dict(zip(("mode","filter","stop","tp_R","hold_h"),cfg)),
            train=train,validation=val,diagnostic_test=periods[2],gate_pass=gate,
            score=score,by_asset=byasset))
    # Ranking uses TRAIN+VALIDATION only. Diagnostic test is NEVER part of score.
    eligible=sorted((x for x in results if x["gate_pass"]),key=lambda x:(-x["score"],-x["validation"]["n"],str(x["config"])))
    baseline=next(x for x in results if x["config"]==dict(mode="turn",filter="all",stop="atr2.5",tp_R=3.,hold_h=48))
    top=eligible[:10]
    for x in top:
        cfg=x["config"];side={}
        for w in ("train","validation","diagnostic_test"):
            tr=[]
            for sym,(raw,ev,cut) in cache.items():
                idx=("train","validation","diagnostic_test").index(w)
                tx,_=simulate(raw,ev,tuple(cfg[k] for k in ("mode","filter","stop","tp_R","hold_h")),cut[idx],cut[idx+1])
                tr.extend(tx)
            side[w]={"LONG":stats([t for t in tr if t["side"]==1]),
                     "SHORT":stats([t for t in tr if t["side"]==-1])}
        x["by_side"]=side
    out=dict(title="Exploratory causal DeltaRSI entry-stop-exit pattern grid",
       generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),source_sha256=hashes,
       fixed_fee_roundtrip=FEE,assumed_risk_fraction=RISK,
       notes=["CACHED 1H OHLC ONLY; NO EXCHANGE CALLS OR ORDERS.",
        "All 50/25/25 chronological windows were inspected in earlier research; diagnostic_test is NOT independent OOS.",
        "Ranking only train+validation. 3rd window reported for diagnosis, never used in scoring.",
        "All as-of features are from prior completed 4H and/or last completed 1H, entry at next 1H open.",
        "Stops known at entry; adverse gap and same-bar stop-first via execution_core.resolve_bar.",
        "0.15% round-trip fixed, exit notional included; funding excluded per latest manager issue.",
        "Per-symbol non-overlap, no shared-capital competition; pseudo DD from ordered 0.25%-risk R series is NOT executable portfolio MTM DD.",
        "Entry modes are separate causal signal families; differing trade counts and schedules prevent paired inference.",
        "All configurations and failures included; selecting winners after seeing diagnostic_test would invalidate any test claim."],
       splits="per-symbol 50% / 25% / 25%, earlier examined",
       configs_total=len(CONFIGS),eligible_train_validation=len(eligible),
       event_counts={s:{m:sum(e["mode"]==m for e in c[1]) for m in MODES} for s,c in cache.items()},
       baseline=baseline,top10=top,all_configs=[{k:x[k] for k in ("config","train","validation","diagnostic_test","gate_pass","score")} for x in results])
    path=Path("reports/pattern_edge_search.json");path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(configs=len(CONFIGS),eligible=len(eligible),baseline={k:baseline[k] for k in ("train","validation","diagnostic_test")},
      top3=[dict(config=x["config"],train=x["train"],validation=x["validation"],diagnostic_test=x["diagnostic_test"]) for x in top[:3]]),indent=2))
if __name__=="__main__":main()
