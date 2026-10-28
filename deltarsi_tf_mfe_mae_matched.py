"""Matched-calendar signal MFE/MAE study; every timeframe executed on 1H candles."""
import csv,datetime as dt,hashlib,json,math,statistics,sys
from pathlib import Path
from causal_4h_parity_audit import CausalDelta,qualifying
from research_multiasset import atr
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
TFS=(1,4,6,8);H=3600000
START=int(dt.datetime(2025,10,28,tzinfo=dt.timezone.utc).timestamp()*1000)
END=int(dt.datetime(2026,10,28,tzinfo=dt.timezone.utc).timestamp()*1000)
HORIZONS=(24,48,72,120)
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def load(sym,tf):
 p=Path("data")/f"{sym}_{tf}h.csv"
 with p.open() as f:
  rows=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
 if any(b[0]-a[0]!=tf*H for a,b in zip(rows,rows[1:])):raise ValueError(f"Gap in {p}")
 return rows
data={};limits=[]
for sym in SYMS:
 data[sym]={tf:load(sym,tf) for tf in TFS}
 limits.append(max(data[sym][tf][0][0] for tf in TFS))
 limits.append(min(data[sym][tf][-1][0]+tf*H for tf in TFS))
start=max(START,max(x for x in limits[::2]));end=min(END,min(x for x in limits[1::2]))
if end-start<90*24*H:raise ValueError("Less than 90d matched coverage")
print("MATCHED WINDOW",iso(start),iso(end),flush=True)
results={}
for tf in TFS:
 events=[];by_sym={}
 for sym in SYMS:
  rows=data[sym][tf];hourly=data[sym][1];idx={r[0]:i for i,r in enumerate(hourly)}
  av=atr(rows);state=CausalDelta();found=[]
  for i,r in enumerate(rows):
   prev=state.delta;prevprev=state.prev_delta
   cur,_,_=state.step(r[4],commit=False)
   entry=r[0]+tf*H
   if i>=210 and start<=entry<end and qualifying(prev,prevprev,cur) and math.isfinite(av[i-1]) and av[i-1]>0 and entry in idx:
    side=1 if prev<0 else -1
    o=hourly[idx[entry]][1];a=av[i-1]
    if o-side*5*a>0:
     for horizon in HORIZONS:
      stop_at=min(idx[entry]+horizon,len(hourly))
      # Strictly within matched study window; use complete horizons only.
      if stop_at>len(hourly) or hourly[stop_at-1][0]+H>end:continue
      path=hourly[idx[entry]:stop_at]
      favorable=[side*(b[2]-o) if side==1 else side*(b[3]-o) for b in path]
      adverse=[side*(b[3]-o) if side==1 else side*(b[2]-o) for b in path]
      mfe=max(favorable);mae=min(adverse)
      imax=favorable.index(mfe)+1;imin=adverse.index(mae)+1
      events.append(dict(symbol=sym,tf=tf,entry=iso(entry),horizon_h=horizon,side=side,atr=a,mfe_pct=100*mfe/o,mae_pct=100*mae/o,mfe_atr=mfe/a,mae_atr=mae/a,hours_to_mfe=imax,hours_to_mae=imin,terminal_pct=100*side*(path[-1][4]-o)/o))
     found.append(entry)
   state.step(r[4],commit=True)
  by_sym[sym]=len(found)
 print("TF",tf,"signals",by_sym,flush=True)
 summaries={}
 for horizon in HORIZONS:
  sub=[x for x in events if x["horizon_h"]==horizon]
  def med(key):return round(statistics.median(x[key] for x in sub),4) if sub else None
  summaries[str(horizon)]=dict(n=len(sub),median_mfe_pct=med("mfe_pct"),median_mae_pct=med("mae_pct"),median_mfe_atr=med("mfe_atr"),median_mae_atr=med("mae_atr"),median_hours_to_mfe=med("hours_to_mfe"),median_terminal_pct=med("terminal_pct"),positive_terminal_pct=round(100*sum(x["terminal_pct"]>0 for x in sub)/len(sub),2) if sub else None)
 results[str(tf)]=dict(signals_by_symbol=by_sym,horizons=summaries,events=events)
out=dict(description="Matched 1H execution across 1H,4H,6H,8H DeltaRSI closed-bar signals. No overlapping-position constraints; independent signal excursions, not prop PnL. MFE/MAE use 1H extremes, no fees. Identical 21SMA/12RSI/EMA4 and absolute delta threshold, 210 bar warmup; bar-based indicator lookback represents different wall-clock time. Fixed horizons 24/48/72/120h.",start=iso(start),end=iso(end),results=results)
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_tf_mfe_mae_matched.json").write_text(json.dumps(out,indent=2))
print("SUMMARY",json.dumps({k:v["horizons"] for k,v in results.items()}),flush=True)
