"""Research-only peak vs area wave divergence; completed 1H candles, no trading."""
import csv,datetime as dt,json,math,statistics
from pathlib import Path
from analyze_mtf_5y import indicator,aggregate
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT")
TFS=(1,4)
OUT=Path("reports/deltarsi_wave_peak_area.json")
def med(x):return round(statistics.median(x),5) if x else None
def rate(x):return round(100*sum(x)/len(x),2) if x else None
def load(sym):
 with (Path("data")/f"{sym}_1h.csv").open() as f:
  return [(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
def evaluate(rows,tf):
 ind=indicator(rows);d=ind["delta"];segments=[];active=None
 for i,x in enumerate(d):
  sign=1 if math.isfinite(x) and x>0 else (-1 if math.isfinite(x) and x<0 else 0)
  if active is not None and sign!=active["sign"]:
   if active["end"]-active["start"]+1>=2:segments.append(active)
   active=None
  if sign and active is None:active=dict(sign=sign,start=i,end=i,peak=abs(x),area=abs(x))
  elif sign:active["end"]=i;active["peak"]=max(active["peak"],abs(x));active["area"]+=abs(x)
 # Only completed segments. Three consecutive same-side waves, separated by opposite signed segments.
 events=[]
 for j in range(4,len(segments)):
  a,b,c=segments[j-4],segments[j-2],segments[j]
  if a["sign"]!=b["sign"] or b["sign"]!=c["sign"]:continue
  side=c["sign"];end=c["end"]
  if end+1>=len(rows):continue
  # Downtrend: lower price lows, uptrend: higher highs, measured within wave intervals.
  extrem=lambda z: min(rows[k][3] for k in range(z["start"],z["end"]+1)) if side<0 else max(rows[k][2] for k in range(z["start"],z["end"]+1))
  pa,pb,pc=map(extrem,(a,b,c))
  if not (pa>pb>pc if side<0 else pa<pb<pc):continue
  fade=a["peak"]>b["peak"]>c["peak"]
  third_rebound=c["peak"]>b["peak"] and c["peak"]<a["peak"]
  if not(fade or third_rebound):continue
  # A wave is only known at the FIRST following opposite-sign closed candle.
  signal=end+1
  if signal+1>=len(rows):continue
  entry=rows[signal+1][1]
  if entry<=0:continue
  horizons=(12,24,48,72,120) if tf==1 else (6,12,24,42,60)
  outcomes={}
  for horizon in horizons:
   if signal+1+horizon>len(rows):continue
   future=rows[signal+1:signal+1+horizon]
   rev=max(((r[2]/entry-1) if side<0 else (1-r[3]/entry)) for r in future)
   cont=max(((1-r[3]/entry) if side<0 else (r[2]/entry-1)) for r in future)
   for threshold in (1,2,3,4,5,7,10):
    first=None
    for r in future:
     hit_rev=(r[2]>=entry*(1+threshold/100) if side<0 else r[3]<=entry*(1-threshold/100))
     hit_cont=(r[3]<=entry*(1-threshold/100) if side<0 else r[2]>=entry*(1+threshold/100))
     if hit_rev or hit_cont:
      first=bool(hit_rev and not hit_cont)
      break
    outcomes[f"{horizon*tf}h_{threshold}pct"]=first
  if not outcomes:continue
  horizon=horizons[0]
  rev=max(((r[2]/entry-1) if side<0 else (1-r[3]/entry)) for r in rows[signal+1:signal+1+horizon])
  cont=max(((1-r[3]/entry) if side<0 else (r[2]/entry-1)) for r in rows[signal+1:signal+1+horizon])
  reversal_first=outcomes.get(f"{horizon*tf}h_1pct")
  # Fourth same-side wave is defined only after the next opposite wave has closed.
  fourth=False
  if j+2<len(segments):
   z=segments[j+2]
   fourth=z["sign"]==side and z["start"]<=signal+1+horizon
  events.append(dict(time=rows[signal][0],side=side,group="fade" if fade else "third_rebound",area_fade=a["area"]>b["area"]>c["area"],peak=[round(z["peak"],4) for z in (a,b,c)],area=[round(z["area"],4) for z in (a,b,c)],reversal_first=reversal_first,rev_mfe_pct=round(100*rev,4),cont_mfe_pct=round(100*cont,4),fourth_wave=fourth,outcomes=outcomes))
 return events
def summarize(es):
 result={}
 for group in ("fade","third_rebound"):
  for area in ("all","area_fade","area_not_fade"):
   subset=[e for e in es if e["group"]==group and (area=="all" or e["area_fade"]==(area=="area_fade"))]
   decided=[e["reversal_first"] for e in subset if e["reversal_first"] is not None]
   result[group+":"+area]=dict(n=len(subset),resolved=len(decided),reversal_first_rate_pct=rate(decided),fourth_wave_rate_pct=rate([e["fourth_wave"] for e in subset]),median_reversal_mfe_pct=med([e["rev_mfe_pct"] for e in subset]))
 for key in sorted({k for e in es for k in e["outcomes"]}):
  vals=[e["outcomes"][key] for e in es if e["group"]=="fade" and e["outcomes"][key] is not None]
  result["fade_threshold:"+key]=dict(resolved=len(vals),reversal_first_rate_pct=rate(vals))
 return result
all_events=[];by_market={}
for sym in SYMS:
 raw=load(sym)
 if any(b[0]-a[0]!=3600000 for a,b in zip(raw,raw[1:])):raise ValueError("1h candle gap "+sym)
 for tf in TFS:
  rows=raw if tf==1 else aggregate(raw,4)
  events=evaluate(rows,tf)
  for e in events:e.update(symbol=sym,tf=tf)
  all_events+=events;by_market[f"{sym}_{tf}h"]=summarize(events)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(dict(summary=summarize(all_events),by_market=by_market,events=all_events,method="Exploratory wave-divergence study. 3 same-sign DeltaRSI segments separated by opposite-sign segments; consecutive price extremes required. Peak vs area fade. Entry after first opposite closed candle, next open. Reversal vs continuation 1% first touch over 12h/24h. Ambiguous same-bar touches excluded. Fourth wave proxy within horizon; noncausal descriptive label. Overlapping events and multiple symbols not independent; no fees, no actual trades."),ensure_ascii=False,indent=2))
print(json.dumps(dict(total_events=len(all_events),summary=summarize(all_events),report=str(OUT)),ensure_ascii=False))
