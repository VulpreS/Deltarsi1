import json, math, statistics, datetime as dt
from pathlib import Path
from causal_4h_parity_audit import load, events, H
DAY=24*H
S=("BTCUSDT","ETHUSDT","ICPUSDT")
D={}
for s in S:
 r,sha=load(s)
 e,_=events(r)
 D[s]=(dict((x[0],x) for x in r),dict((x["entry_ms"],x) for x in e["closed"]),sha)
start=max(min(v[0]) for v in D.values())
end=min(max(v[0])+H for v in D.values())
start=(start+DAY-1)//DAY*DAY
def run(begin,coins):
 cash=5000.;pos=None;phase=0;phase_start=begin;day=None;daybase=5000.;last=5000.;good=set();done=[];peak=5000.;dd=0.;n=0;failure=None
 for t in range(begin,end,H):
  bars={s:D[s][0].get(t) for s in coins}
  if any(x is None for x in bars.values()):continue
  op={s:x[1] for s,x in bars.items()}
  cl={s:x[4] for s,x in bars.items()}
  def equity(prices):
   if pos is None:return cash
   s,side,qty,entry,sl,tp=pos
   return cash+side*qty*(prices[s]-entry)-qty*prices[s]*0.00075
  today=t//DAY
  if today!=day:
   if day is not None and last-daybase>=25:good.add(day)
   day=today;daybase=equity(op)
  if pos is None:
   for s in coins:
    ev=D[s][1].get(t)
    if ev is None:continue
    atr=ev["atr_4h"];o=op[s];side=ev["side"]
    if not math.isfinite(atr) or atr<=0 or o-side*3*atr<=0:continue
    qty=5000/o;cash-=qty*o*0.00075
    pos=(s,side,qty,o,o-side*3*atr,o+side*1.5*atr);n+=1;break
  if pos:
   s,side,qty,entry,sl,tp=pos
   o,h,l,c=bars[s][1:5]
   stop_hit=l<=sl if side==1 else h>=sl
   tp_hit=h>=tp if side==1 else l<=tp
   adverse=(min(o,sl) if side==1 else max(o,sl)) if stop_hit else (l if side==1 else h)
   prices=dict(cl);prices[s]=adverse;worst=equity(prices)
   dd=max(dd,(peak-worst)/peak)
   if worst<=daybase-250:failure="daily";break
   if worst<=4500:failure="total";break
   exitprice=o if side*(o-sl)<=0 or side*(o-tp)>=0 else sl if stop_hit else tp if tp_hit else None
   if exitprice is not None:
    cash+=side*qty*(exitprice-entry)-qty*exitprice*0.00075;pos=None
   elif (t//H)%8==0:cash-=qty*entry*0.0003
  last=equity(cl);peak=max(peak,last)
  if last<=daybase-250:failure="daily";break
  if last<=4500:failure="total";break
  if (t+H)//DAY>today:
   if last-daybase>=25:good.add(today)
   targets=(.05,.08,0.)
   required=(3,5,5)
   if len(good)>=required[phase] and last>=5000*(1+targets[phase]) and (phase<2 or t+H-phase_start>=14*DAY):
    done.append(dict(phase=phase+1,days=round((t+H-phase_start)/DAY,1),equity=round(last,2),days_ge_25=len(good)))
    if phase==2:break
    phase+=1;phase_start=t+H;cash=5000.;pos=None;good=set();peak=5000.
   day=None
 status="breach_"+failure if failure else "funded_eligible" if len(done)==3 else "censored"
 return dict(status=status,completed=done,days=round((t+H-begin)/DAY,1),trades=n,max_dd_pct=round(dd*100,2))
starts=range(start,end-14*DAY,DAY)
out=dict(notes="Exploratory, 1x $5000 fixed notional, single position; 1H stop-first, synthetic fees/funding; 00 UTC daily 5% and static total 10%; sequential reset stages; no 30-day deadline; right-censored at data end; overlapping starts not independent.",window=[start,end],sha={s:D[s][2] for s in S},results={})
for name,coins in (("BTC",S[:1]),("ETH",S[1:2]),("ICP",S[2:]),("ALL",S)):
 runs=[run(t,coins) for t in starts]
 counts={k:sum(r["status"]==k for r in runs) for k in ("funded_eligible","censored","breach_daily","breach_total")}
 stages={str(i):sum(len(r["completed"])>=i for r in runs) for i in (1,2,3)}
 med={str(i):round(statistics.median(r["completed"][i-1]["days"] for r in runs if len(r["completed"])>=i),1) if stages[str(i)] else None for i in (1,2,3)}
 out["results"][name]=dict(windows=len(runs),counts=counts,stage_passes=stages,median_stage_days=med,max_dd_pct=max(r["max_dd_pct"] for r in runs),example=next((r for r in runs if len(r["completed"])==3),None))
 print(name,counts,stages,flush=True)
Path("reports/deltarsi_prop_multiasset_no_deadline.json").write_text(json.dumps(out,indent=2))
