import json, math, statistics
from pathlib import Path
from causal_4h_parity_audit import load, events, H
DAY=24*H
S=("BTCUSDT","ETHUSDT")
D={}
for s in S:
 r,sha=load(s);e,_=events(r)
 D[s]=(dict((x[0],x) for x in r),dict((x["entry_ms"],x) for x in e["closed"]),sha)
start=(max(min(v[0]) for v in D.values())+DAY-1)//DAY*DAY
end=min(max(v[0])+H for v in D.values())
def run(begin,mode):
 cash=5000.;positions={};phase=0;phase_start=begin;day=None;daybase=5000.;last=5000.;good=set();done=[];peak=5000.;dd=0.;n=0;failure=None
 def equity(prices):
  return cash+sum(p["side"]*p["qty"]*(prices[s]-p["entry"])-p["qty"]*prices[s]*.00075 for s,p in positions.items())
 for t in range(begin,end,H):
  bars={s:D[s][0].get(t) for s in S}
  if any(v is None for v in bars.values()):continue
  opens={s:v[1] for s,v in bars.items()};closes={s:v[4] for s,v in bars.items()}
  today=t//DAY
  if today!=day:
   if day is not None and last-daybase>=25:good.add(day)
   day=today;daybase=equity(opens)
  for s in S:
   if s in positions or (mode=="mono" and positions):continue
   ev=D[s][1].get(t)
   if not ev:continue
   atr=ev["atr_4h"];o=opens[s];side=ev["side"]
   if not math.isfinite(atr) or atr<=0 or o-side*3*atr<=0:continue
   qty=(1500 if mode=="split" else 3000)/o
   cash-=qty*o*.00075
   positions[s]=dict(side=side,qty=qty,entry=o,sl=o-side*3*atr,tp=o+side*1.5*atr)
   n+=1
  # Portfolio-level adverse excursion aggregates simultaneous adverse wicks conservatively.
  adverse=dict(closes)
  for s,p in positions.items():
   o,h,l,c=bars[s][1:5];side=p["side"];sl=p["sl"]
   hit=l<=sl if side==1 else h>=sl
   adverse[s]=(min(o,sl) if side==1 else max(o,sl)) if hit else (l if side==1 else h)
  worst=equity(adverse)
  dd=max(dd,(peak-worst)/peak)
  if worst<=daybase-250:failure="daily";break
  if worst<=4500:failure="total";break
  for s,p in list(positions.items()):
   o,h,l,c=bars[s][1:5];side=p["side"];sl=p["sl"];tp=p["tp"]
   stop=l<=sl if side==1 else h>=sl
   take=h>=tp if side==1 else l<=tp
   price=o if side*(o-sl)<=0 or side*(o-tp)>=0 else sl if stop else tp if take else None
   if price is not None:
    cash+=side*p["qty"]*(price-p["entry"])-p["qty"]*price*.00075
    del positions[s]
   elif (t//H)%8==0:cash-=p["qty"]*p["entry"]*.0003
  last=equity(closes);peak=max(peak,last)
  if last<=daybase-250:failure="daily";break
  if last<=4500:failure="total";break
  if (t+H)//DAY>today:
   if last-daybase>=25:good.add(today)
   if len(good)>=(3,5,5)[phase] and last>=5000*(1+(.05,.08,0)[phase]) and (phase<2 or t+H-phase_start>=14*DAY):
    done.append(dict(phase=phase+1,days=round((t+H-phase_start)/DAY,1),equity=round(last,2),days_ge_25=len(good)))
    if phase==2:break
    phase+=1;phase_start=t+H;cash=5000.;positions.clear();good=set();peak=5000.
   day=None
 return dict(status="breach_"+failure if failure else "funded_eligible" if len(done)==3 else "censored",completed=done,trades=n,max_dd_pct=round(dd*100,2))
out=dict(notes="One account $5000. split: BTC $1500 + ETH $1500 simultaneous; mono: one $3000 position, BTC priority. 1x. 1h conservative simultaneous adverse excursion, fixed day limit $250 and total $500. Stages reset; censored at history end; overlapping windows not independent.",window=[start,end],results={})
starts=range(start,end-14*DAY,DAY)
for mode in ("split","mono"):
 runs=[run(t,mode) for t in starts]
 counts={k:sum(r["status"]==k for r in runs) for k in ("funded_eligible","censored","breach_daily","breach_total")}
 stages={str(i):sum(len(r["completed"])>=i for r in runs) for i in (1,2,3)}
 med={str(i):round(statistics.median(r["completed"][i-1]["days"] for r in runs if len(r["completed"])>=i),1) if stages[str(i)] else None for i in (1,2,3)}
 out["results"][mode]=dict(windows=len(runs),counts=counts,stage_passes=stages,median_stage_days=med,max_dd_pct=max(r["max_dd_pct"] for r in runs))
 print(mode,counts,stages,flush=True)
Path("reports/deltarsi_prop_btc_eth_split_vs_mono.json").write_text(json.dumps(out,indent=2))
