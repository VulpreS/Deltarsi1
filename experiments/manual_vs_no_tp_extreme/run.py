"""Paired MANUAL BTC trade entry/exit audit, 40 extreme-stop/TTL alternatives.
No lookahead, no order execution, read-only. 1h BTC cache begins 2025-10-26;
September/October trades outside cache cannot be backtested honestly.
"""
import csv,datetime as dt,json,math,statistics,bisect,collections
from pathlib import Path
from causal_4h_parity_audit import load,events,H,FOUR
from manual_trade_label_audit import normalize
MSK=dt.timezone(dt.timedelta(hours=3))
NS=(5,10,15,20); HOURS=(12,16,20,24,32,40,48,52,56,60)
COST=.0015; BUFFER=.0002
def stamp(x):return dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).isoformat()
def med(x):return round(statistics.median(x),4) if x else None
def avg(x):return round(statistics.mean(x),4) if x else None
def stat(x):
 if not x:return dict(n=0)
 p=sum(max(0,v) for v in x);l=-sum(min(0,v) for v in x)
 return dict(n=len(x),mean_pct=avg(x),median_pct=med(x),
  total_pct_sum=round(sum(x),4),win_rate_pct=round(100*sum(v>0 for v in x)/len(x),2),
  profit_factor=round(p/l,4) if l else None)
def eval_counterfactual(raw,times,h4,entry_ms,side,entry_px,n,hold):
 # Last fully closed 4h candle: bar end <= entry. Bars are UTC 4h aligned.
 bars=[b for b in h4 if b[0]+FOUR<=entry_ms]
 if len(bars)<n:return None
 extreme=(min(b[3] for b in bars[-n:])*(1-BUFFER) if side==1 else
          max(b[2] for b in bars[-n:])*(1+BUFFER))
 if side*(entry_px-extreme)<=0:return dict(status="stop_invalid_at_entry",stop=extreme)
 ix=bisect.bisect_left(times,entry_ms)
 if ix>=len(raw) or times[ix]!=entry_ms:return None
 until=entry_ms+hold*H
 if until>times[-1]+H:return None
 price=None;why=None;exit_time=None
 for j in range(ix,len(raw)):
  b=raw[j];t=b[0]
  if t>=until:break
  if side*(b[1]-extreme)<=0:price=b[1];why="stop_gap";exit_time=t;break
  if (b[3]<=extreme if side==1 else b[2]>=extreme):
   price=extreme;why="stop";exit_time=t;break
  if t+H>=until:
   price=b[4];why="time";exit_time=t+H;break
 if price is None:return None
 net=100*(side*(price-entry_px)/entry_px-COST)
 return dict(status="ok",stop=round(extreme,4),stop_distance_pct=round(100*abs(entry_px-extreme)/entry_px,4),
  exit=round(price,4),exit_utc=stamp(exit_time),reason=why,holding_hours=round((exit_time-entry_ms)/H,2),
  net_pct=round(net,5))
def main():
 raw,_=load("BTCUSDT");times=[x[0] for x in raw]
 h4=[];by={x[0]:x for x in raw}
 # UTC 4h candles, only complete; raw starts at non-4h aligned.
 for start in range((times[0]//FOUR+1)*FOUR,times[-1]-3*H+1,FOUR):
  parts=[by.get(start+k*H) for k in range(4)]
  if any(x is None for x in parts):continue
  h4.append((start,parts[0][1],max(x[2] for x in parts),min(x[3] for x in parts),parts[-1][4]))
 signals, _ = events(raw)
 sig=signals["closed"];sigtimes=[e["entry_ms"] for e in sig]
 with open("data/manual_btc_trades_2025_2026.csv") as f:source=list(csv.DictReader(f))
 rows=[];valid=[]
 for i,r in enumerate(source,1):
  z=normalize(r);side=z["side"];entry_ms=z["entry_ms"]
  base=dict(id=f"R{i:02d}",entry_msk=r["entry_msk"],side="LONG" if side==1 else "SHORT",
   manual_entry=float(r["entry"]),manual_stop=float(r["sl"]),manual_exit1=float(r["exit1"]),
   manual_exit2=float(r["exit2"]) if r["exit2"] else None,
   manual_net_pct=round(z["net_pct"],5),manual_hold_hours=z["holding_hours"],
   manual_exit_reason=r["exit_reason"],entry_reason=r["entry_reason"],
   quality=r["quality"],issues=z["issues"])
  if entry_ms is None or entry_ms<times[0] or entry_ms>times[-1]:
   base["status"]="outside_cached_1h";rows.append(base);continue
  if z["issues"]:
   base["status"]="flagged_annotation";rows.append(base);continue
  idx=bisect.bisect_left(times,entry_ms)
  if idx>=len(times) or times[idx]!=entry_ms:
   base["status"]="not_hour_boundary";rows.append(base);continue
  # Annotated price must be within marked or preceding hour to support comparison.
  now=raw[idx];prior=raw[idx-1] if idx>0 else None
  contained=lambda b:b is not None and b[3]<=z["entry"]<=b[2]
  if not (contained(now) or contained(prior)):
   base["status"]="entry_price_ohlc_mismatch";rows.append(base);continue
  # Do not silently accept manual exits that are incompatible with OHLC.
  exit_ok=True
  for k in (1,2):
   ex_ms=z["exit1_ms"] if k==1 else z["exit2_ms"]
   px=z["exit1"] if k==1 else z["exit2"]
   if ex_ms is None:continue
   j=bisect.bisect_left(times,ex_ms)
   if j>=len(raw) or j==0 or not (contained_exit(raw[j],px) or contained_exit(raw[j-1],px)):
    exit_ok=False
  base["exit_price_ohlc_match"]=exit_ok
  # Per-signal matching: SAME SIDE within 4h; do not assume 42 manual == 42 algorithmic.
  same=[e for e in sig if e["side"]==side and abs(e["entry_ms"]-entry_ms)<=4*H]
  base["signal_within_4h"]=bool(same)
  base["nearest_signal_offset_hours"]=round((min(same,key=lambda e:abs(e["entry_ms"]-entry_ms))["entry_ms"]-entry_ms)/H,1) if same else None
  cf={}
  for n in NS:
   for hold in HOURS:
    cf[f"N{n}_H{hold}"]=eval_counterfactual(raw,times,h4,entry_ms,side,z["entry"],n,hold)
  base["alternatives"]=cf
  base["status"]="usable" if exit_ok else "exit_price_ohlc_mismatch"
  rows.append(base)
  if exit_ok:valid.append(base)
 # Strict paired: identical human entry, compare only exit mechanism, clean exit annotation.
 grid=[]
 for n in NS:
  for h in HOURS:
   k=f"N{n}_H{h}"
   paired=[r for r in valid if r["alternatives"][k] and r["alternatives"][k]["status"]=="ok"]
   alt=[r["alternatives"][k]["net_pct"] for r in paired]
   hum=[r["manual_net_pct"] for r in paired]
   dif=[a-b for a,b in zip(alt,hum)]
   grid.append(dict(stop_n=n,hold_hours=h,paired=len(paired),
    algo=stat(alt),human=stat(hum),delta_mean_pct=avg(dif),
    human_better=sum(d<0 for d in dif),algo_better=sum(d>0 for d in dif),
    algo_stop=sum(r["alternatives"][k]["reason"]!="time" for r in paired),
    algo_time=sum(r["alternatives"][k]["reason"]=="time" for r in paired)))
 grid.sort(key=lambda x:x["algo"]["mean_pct"] if x["algo"]["n"] else -999,reverse=True)
 # Select strict common cohort for all grid comparisons.
 common=[r for r in valid if all(r["alternatives"][f"N{n}_H{h}"] and
    r["alternatives"][f"N{n}_H{h}"]["status"]=="ok" for n in NS for h in HOURS)]
 by_human=sorted(common,key=lambda r:r["manual_net_pct"],reverse=True)
 best=grid[0]
 diffs=[]
 for r in common:
  k=f"N{best['stop_n']}_H{best['hold_hours']}"
  x=r["alternatives"][k]
  diffs.append(dict(id=r["id"],entry_msk=r["entry_msk"],side=r["side"],
    human_net_pct=r["manual_net_pct"],algo_net_pct=x["net_pct"],
    human_minus_algo_pct=round(r["manual_net_pct"]-x["net_pct"],4),
    human_hold_hours=r["manual_hold_hours"],algo_hold_hours=x["holding_hours"],
    algo_exit_reason=x["reason"],algo_stop_distance_pct=x["stop_distance_pct"],
    manual_stop_distance_pct=round(100*abs(r["manual_entry"]-r["manual_stop"])/r["manual_entry"],4),
    signal_within_4h=r["signal_within_4h"],nearest_signal_offset_hours=r["nearest_signal_offset_hours"]))
 diffs.sort(key=lambda x:x["human_minus_algo_pct"],reverse=True)
 # Entry selectivity: compare human dates with closed signal times within 4h; report unmatched only.
 summary=dict(total_manual=len(rows),outside_cache=sum(r["status"]=="outside_cached_1h" for r in rows),
  flagged=sum(r["status"]=="flagged_annotation" for r in rows),
  entry_mismatch=sum(r["status"]=="entry_price_ohlc_mismatch" for r in rows),
  exit_mismatch=sum(r["status"]=="exit_price_ohlc_mismatch" for r in rows),
  valid_clean_paired=len(valid),common_cohort=len(common),
  manual_signal_within4h=sum(r["signal_within_4h"] for r in valid),
  closed_algo_signals_in_cache=len(sig),common_human_stats=stat([r["manual_net_pct"] for r in common]),
  best_grid=best,top_human_advantage=diffs[:10],top_algo_advantage=diffs[-10:],
  entry_side_groups={side:stat([r["manual_net_pct"] for r in common if r["side"]==side]) for side in ("LONG","SHORT")})
 output=dict(summary=summary,grid=grid,paired_diffs=diffs,rows=rows,
  caveats=["1h BTC cache starts 2025-10-26; early manual trades excluded",
   "No future 4h bars in stops; closed signal 4h included only when complete at entry",
   "Entry is fixed at annotated human price; this isolates EXIT differences only",
   "Manual outcomes with missing times, questionable prices, mismatched entry/exit OHLC are excluded from strict paired set",
   "All return percentages per position, not compounded portfolio or prop payout",
   "0.15pct roundtrip cost both sides; 1h bars not 5m, gap open before stop, stop first, time at 1h close",
   "Some annotated initial stops may have moved; manual exits are annotations, not independently verified fills",
   "Signal matching within +/-4h only; cannot claim same signal or entry quality without separate opportunity-level matching",
   "No 2025-09 to 2025-10-26 market data for BTC in 1h cache; no guessing",
   "Multiple testing 40 alternatives in-sample; no out-of-sample claims"])
 out=Path("experiments/manual_vs_no_tp_extreme")
 out.mkdir(parents=True,exist_ok=True)
 (out/"results.json").write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print("MANUAL_VS_EXTREME_RESULT",json.dumps(summary,ensure_ascii=False),flush=True)
 print("MANUAL_VS_EXTREME_GRID",json.dumps(grid[:12],ensure_ascii=False),flush=True)
 print("MANUAL_VS_EXTREME_DIFFS",json.dumps(diffs,ensure_ascii=False),flush=True)
def contained_exit(bar,price):
 return bar[3]-1e-7<=price<=bar[2]+1e-7
if __name__=="__main__":main()
