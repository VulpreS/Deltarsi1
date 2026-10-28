"""Causal DeltaRSI cross-timeframe event study: independent forward MFE/MAE and audit."""
import csv,datetime as dt,json,math,statistics
from pathlib import Path
from causal_4h_parity_audit import CausalDelta,qualifying
from research_multiasset import atr
TFS=(1,4,6,8);SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
H=3600000;WINDOW=24;HORIZONS=(1,4,8,12,24,48)
START=int(dt.datetime(2025,10,28,tzinfo=dt.timezone.utc).timestamp()*1000)
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def median(a):return round(statistics.median(a),5) if a else None
def quant(a,p):
 if not a:return None
 a=sorted(a);j=(len(a)-1)*p;lo=int(j);hi=min(lo+1,len(a)-1)
 return round(a[lo]+(a[hi]-a[lo])*(j-lo),5)
def describe(a):return dict(n=len(a),mean=round(statistics.mean(a),5) if a else None,median=median(a),p10=quant(a,.1),p25=quant(a,.25),p75=quant(a,.75),p90=quant(a,.9))
bars={};events={};audit=[];ends=[]
for sym in SYMS:
 for tf in TFS:
  with (Path("data")/f"{sym}_{tf}h.csv").open() as f:
   rr=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
  if not rr:raise ValueError(f"Empty {sym} {tf}")
  gaps=sum(y[0]-x[0]!=tf*H for x,y in zip(rr,rr[1:]))
  if gaps:raise ValueError(f"Data gaps {sym} {tf}: {gaps}")
  state=CausalDelta();aa=atr(rr);ev={}
  for i,r in enumerate(rr):
   p=state.delta;pp=state.prev_delta;c,_,_=state.step(r[4],commit=False)
   if i>=210 and qualifying(p,pp,c) and i+1<len(rr) and math.isfinite(aa[i-1]) and aa[i-1]>0:
    # At r[i+1] open, r[i] is the last fully closed signal candle.
    ev[rr[i+1][0]]=dict(side=1 if p<0 else -1,atr=aa[i-1],strength=abs(p),signal_close=rr[i][0]+tf*H)
   state.step(r[4],commit=True)
  bars[sym,tf]={r[0]:r[1:] for r in rr};events[sym,tf]=ev
  ends.append(rr[-1][0]+tf*H)
  audit.append(dict(symbol=sym,tf=tf,rows=len(rr),gaps=gaps,events=len(ev),signal_timing_violations=sum(e["signal_close"]>t for t,e in ev.items())))
END=min(ends)-48*H
if END<=START:raise ValueError("Insufficient common evaluation window")
# Audit aggregation alignment and OHLC consistency for shared timestamps.
for sym in SYMS:
 for tf in (4,6,8):
  mismatch=0;checked=0
  for t,(o,hi,lo,c) in bars[sym,tf].items():
   if t<START or t+tf*H>END:continue
   small=[bars[sym,1].get(t+j*H) for j in range(tf)]
   if any(v is None for v in small):continue
   checked+=1
   expected=(small[0][0],max(v[1] for v in small),min(v[2] for v in small),small[-1][3])
   if any(abs(x-y)>max(1e-7,abs(x)*1e-7) for x,y in zip((o,hi,lo,c),expected)):mismatch+=1
  audit.append(dict(symbol=sym,tf=tf,aggregation_checks=checked,aggregation_mismatches=mismatch))
records=[];summary={}
for sym in SYMS:
 hourly=bars[sym,1]
 for base_tf in TFS:
  for t,base in events[sym,base_tf].items():
   if not START<=t<=END:continue
   for other_tf in TFS:
    if base_tf==other_tf:continue
    for u,other in events[sym,other_tf].items():
     if not t<=u<=min(t+WINDOW*H,END):continue
     # Study at the open where the second event becomes tradable; never at its prior close.
     initial=hourly.get(u)
     if initial is None:continue
     px=initial[0];direction=base["side"];same=direction==other["side"]
     item=dict(symbol=sym,base_tf=base_tf,other_tf=other_tf,base_time=iso(t),event_time=iso(u),delay_h=(u-t)//H,relation="confirm" if same else "conflict",direction=direction,base_strength=round(base["strength"],5),other_strength=round(other["strength"],5),base_age_h=(u-t)//H,entry=px,horizons={})
     for h in HORIZONS:
      candles=[hourly.get(u+j*H) for j in range(h)]
      if any(v is None for v in candles):continue
      favourable=max(direction*(v[1]-px) if direction==1 else direction*(v[2]-px) for v in candles)
      adverse=min(direction*(v[2]-px) if direction==1 else direction*(v[1]-px) for v in candles)
      close=candles[-1][3];ret=direction*(close/px-1)*100
      mfe=max(0,favourable/px*100);mae=max(0,-adverse/px*100)
      item["horizons"][str(h)]=dict(return_pct=round(ret,5),mfe_pct=round(mfe,5),mae_pct=round(mae,5))
     # descriptive outcomes, NOT predictions; use 24h forward data only for labels.
     h24=item["horizons"].get("24")
     if h24:
      if h24["return_pct"]<=-1 and h24["mae_pct"]>=1:item["outcome_24h"]="reversal"
      elif h24["return_pct"]>=1:item["outcome_24h"]="continuation"
      else:item["outcome_24h"]="mixed"
     records.append(item)
for a in TFS:
 for b in TFS:
  if a==b:continue
  for rel in ("confirm","conflict"):
   rr=[r for r in records if r["base_tf"]==a and r["other_tf"]==b and r["relation"]==rel]
   if not rr:continue
   by_h={}
   for h in HORIZONS:
    samples=[r["horizons"][str(h)] for r in rr if str(h) in r["horizons"]]
    by_h[str(h)]=dict(return_pct=describe([v["return_pct"] for v in samples]),mfe_pct=describe([v["mfe_pct"] for v in samples]),mae_pct=describe([v["mae_pct"] for v in samples]),positive_rate_pct=round(100*sum(v["return_pct"]>0 for v in samples)/len(samples),2) if samples else None)
   labels={label:sum(r.get("outcome_24h")==label for r in rr) for label in ("reversal","continuation","mixed")}
   summary[f"{a}>{b}:{rel}"]=dict(n=len(rr),delay_h=describe([r["delay_h"] for r in rr]),outcomes_24h=labels,horizons=by_h)
out=dict(period=dict(start=iso(START),last_event=iso(END),horizons_h=HORIZONS),audit=audit,summary=summary,events=records,method="Signals computed from fully closed candles, actionable next candle open. Second event is study anchor. Forward 1h OHLC paths measure signed MFE/MAE and close returns. Outcomes are ex-post descriptive, not usable as features. Overlapping events correlated; no fees or prop execution in event study. Validate 1h/HTF OHLC aggregation before interpreting results.")
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_transition_events.json").write_text(json.dumps(out,ensure_ascii=False))
print("AUDIT",json.dumps(audit))
print("EVENT_STUDY",json.dumps(dict(total_events=len(records),summary=summary)),flush=True)
