"""BTC 4H prop challenge replay. Exploratory, 1H conservative mark-to-market."""
import json,math,datetime as dt
from pathlib import Path
from causal_4h_parity_audit import load,events,H
raw,sha=load("BTCUSDT")
ev,_=events(raw)
signals={e["entry_i"]:e for e in ev["closed"]}
DAY=24*H
START=5000.
FEE=.0015
FUND=.0003
def replay(start,leverage=1,days=30,goal=.05,min_days=3,required=.005):
 end=min(len(raw),start+24*days)
 cash=START;pos=None;day0=None;dayid=None;day_wins=0;day_log=[];trades=0;max_dd=0;peak=START
 breach=None;completed=None;fees=0.;funding=0.
 def mark(p):
  if pos is None:return cash
  return cash+pos["side"]*pos["qty"]*(p-pos["entry"])-pos["qty"]*p*FEE/2
 def finish_day():
  nonlocal day_wins
  if day0 is not None:
   last=day_log[-1] if day_log else None
   if last is not None and last["day"]==dayid and last["end"]>=day0+required*START:day_wins+=1
 for i in range(start,end):
  t,o,h,l,cl=raw[i];d=t//DAY
  if d!=dayid:
   if dayid is not None:finish_day()
   dayid=d;day0=mark(o);day_log.append(dict(day=d,start=day0,end=day0))
  if pos is None and i in signals:
   e=signals[i];a=e["atr_4h"];side=e["side"]
   if math.isfinite(a) and a>0 and o-side*3*a>0:
    qty=START*leverage/o;cost=qty*o*FEE/2
    cash-=cost;fees+=cost
    pos=dict(side=side,qty=qty,entry=o,stop=o-side*3*a,target=o+side*1.5*a,opened=i)
    trades+=1
  if pos is not None:
   side=pos["side"];stop=pos["stop"];target=pos["target"]
   hitstop=(l<=stop if side==1 else h>=stop)
   hittp=(h>=target if side==1 else l<=target)
   # Adverse low/high is checked before target and before final close.
   worst=(min(o,stop) if side==1 else max(o,stop)) if hitstop else (l if side==1 else h)
   adverse=mark(worst)
   peak=max(peak,day0)
   max_dd=max(max_dd,(peak-adverse)/peak)
   if adverse<=day0-.05*START:breach="daily"
   if adverse<=.9*START:breach="total" if breach is None else breach
   if breach:break
   if side*(o-stop)<=0:exitp=o
   elif side*(o-target)>=0:exitp=o
   elif hitstop:exitp=stop
   elif hittp:exitp=target
   else:exitp=None
   if exitp is not None:
    cash+=side*pos["qty"]*(exitp-pos["entry"])
    cost=pos["qty"]*exitp*FEE/2;cash-=cost;fees+=cost
    pos=None
   elif (t//H)%8==0:
    cost=pos["qty"]*pos["entry"]*FUND
    cash-=cost;funding+=cost
  eq=mark(cl);day_log[-1]["end"]=eq
  peak=max(peak,eq)
  if eq<=day0-.05*START:breach="daily";break
  if eq<=.9*START:breach="total";break
  # Count completed days ONLY at UTC midnight; current day cannot qualify early.
  if (t+H)//DAY>d:
   finish_day()
   if eq>=START*(1+goal) and day_wins>=min_days and (goal!=0 or i-start+1>=14*24):
    completed=i;break
   dayid=None;day0=None
 if not breach and completed is None and dayid is not None:finish_day()
 return dict(start_utc=dt.datetime.fromtimestamp(raw[start][0]/1000,dt.timezone.utc).isoformat(),status="breach_"+breach if breach else "pass" if completed is not None else "timeout",days=(i-start+1)/24,trades=trades,qualifying_days=day_wins,final_equity=round(mark(raw[i][4]),2),max_dd_pct=round(max_dd*100,2),fees=round(fees,2),funding=round(funding,2))
# Start on each UTC midnight, only with enough full history for the requested horizon.
out={"data_sha":sha,"notes":["1H intrabar extremes conservatively checked before take profit","5% daily from 00 UTC equity; 10% static from starting 5000; qualifying days at UTC day close","5000 fixed notional at 1x; 5x scenario means 25000 notional, not an assumption about user intent","No actual exchange fills, intrahour timing, prop platform mark price, or withdrawal verification"],"scenarios":{}}
for lev in (1,5):
 for goal,minimum,tag in ((.05,3,"stage1"),(.08,5,"stage2"),(0.,5,"funded_14d")):
  horizon=14 if tag=="funded_14d" else 30
  starts=[i for i,r in enumerate(raw) if r[0]%DAY==0 and i+24*horizon<=len(raw)]
  runs=[replay(i,lev,horizon,goal,minimum) for i in starts]
  statuses={s:sum(r["status"]==s for r in runs) for s in ("pass","timeout","breach_daily","breach_total")}
  passes=[r for r in runs if r["status"]=="pass"]
  out["scenarios"][f"{tag}_{lev}x"]={"count":len(runs),"status":statuses,"pass_rate_pct":round(100*len(passes)/len(runs),2),"median_pass_days":sorted(r["days"] for r in passes)[len(passes)//2] if passes else None,"sample_pass":passes[:3],"sample_fail":next((r for r in runs if r["status"].startswith("breach")),None)}
  print(tag,lev,statuses,flush=True)
Path("reports/deltarsi_prop_5000_challenge.json").write_text(json.dumps(out,indent=2))
