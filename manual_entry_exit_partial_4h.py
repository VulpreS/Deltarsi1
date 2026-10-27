"""Reconstruct trader's ACTUAL manual DeltaRSI entry/exit logic, not ATR targets.
Closed 1H snapshots of forming 4H histogram, both before/after real timestamps.
"""
import csv,datetime as dt,json,math,bisect
from pathlib import Path
from five_entries_partial_4h import load,observe,H
TZ=dt.timezone(dt.timedelta(hours=3))
def parse(s):
 try:return int(dt.datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp()*1000)
 except:return None
def compact(o):
 if o is None:return None
 t=o["tail"];return {"asof_utc":o["asof_utc"],"partial_hours":o["partial_hours"],"last":t[-1] if t else None,"prev":t[-2] if len(t)>1 else None}
def main():
 raw=load();times=[r[0] for r in raw];first=times[0]+H;last=times[-1]+H
 with open("data/manual_btc_trades_2025_2026.csv") as f:trades=list(csv.DictReader(f))
 snapshots={};results=[]
 def snap(t):
  if t not in snapshots:snapshots[t]=compact(observe(raw,t)) if first<=t<=last else None
  return snapshots[t]
 for t in trades:
  ent=parse(t["entry_msk"]);e1=parse(t["exit1_msk"]);e2=parse(t["exit2_msk"])
  side=1 if float(t["sl"])<float(t["entry"]) else -1
  rec={"entry_msk":t["entry_msk"],"side":"LONG" if side==1 else "SHORT","entry_reason":t["entry_reason"],"exit_reason":t["exit_reason"],"quality":t["quality"],"entry":float(t["entry"]),"sl":float(t["sl"])}
  for name,moment in (("entry",ent),("exit1",e1),("exit2",e2)):
   if moment is None:continue
   rec[name+"_snapshots"]={str(offset):snap(moment+offset*H) for offset in (-4,-2,-1,0,1,2,4)}
   rec[name+"_utc"]=dt.datetime.fromtimestamp(moment/1000,dt.timezone.utc).isoformat()
  if ent and e1 and e1>=ent and ent>=first and e1<=last:
   end=e2 if e2 and e2>=e1 else e1
   ix=bisect.bisect_left(times,ent);jx=bisect.bisect_left(times,end)
   seg=raw[ix:jx];stop=float(t["sl"])
   rec["stop_touched_before_last_exit"]=any(x[3]<=stop if side>0 else x[2]>=stop for x in seg)
   rec["mfe_pct"]=round(100*(max(x[2] for x in seg)/float(t["entry"])-1) if side>0 else 100*(1-min(x[3] for x in seg)/float(t["entry"])),3) if seg else None
   rec["mae_pct"]=round(100*(min(x[3] for x in seg)/float(t["entry"])-1) if side>0 else 100*(1-max(x[2] for x in seg)/float(t["entry"])),3) if seg else None
  results.append(rec)
 summary={}
 for kind in ("entry","exit1"):
  group={}
  for side in ("LONG","SHORT"):
   vals=[x for x in results if x["side"]==side and x.get(kind+"_snapshots",{}).get("0")]
   patterns={}
   for x in vals:
    o=x[kind+"_snapshots"]["0"];p=o["prev"]["color"] if o["prev"] else "";c=o["last"]["color"] if o["last"] else ""
    key=p+">"+c;patterns[key]=patterns.get(key,0)+1
   group[side]={"n":len(vals),"snapshot_colors":patterns,"examples":[{"date":x["entry_msk"],"state":x[kind+"_snapshots"]["0"]["last"]} for x in vals[:3]]}
  summary[kind]=group
 out={"notes":"Exact trader entries/exits in Moscow UTC+3; as-of hourly CLOSED snapshot, forming 4H computed with 1-3 closed 1H candles; no lookahead. Snapshot at event time cannot reconstruct trader intrahour indicator movement. Full OHLC history begins 26 Oct 2025; invalid manual timestamps retained. No ATR-based exit assumptions, no funding or simulated orders. MFE/MAE from 1H bars strictly between entry and exit; partial exits analyzed separately.","summary":summary,"trades":results}
 Path("reports/manual_entry_exit_partial_4h.json").write_text(json.dumps(out,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
