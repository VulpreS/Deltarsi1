"""Audit whether actual manual stops correspond to prior swing extrema.
Closed 1H and 4H history only; never use future bars to choose stops.
"""
import csv,datetime as dt,json,bisect,statistics
from pathlib import Path
from analyze_mtf_5y import aggregate
H=3600000;TZ=dt.timezone(dt.timedelta(hours=3))
def parse(x):
 try:return int(dt.datetime.strptime(x,"%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp()*1000)
 except:return None
def main():
 with open("data/BTCUSDT_1h.csv") as f:raw=list(csv.DictReader(f))
 h=[(int(dt.datetime.fromisoformat(x["timestamp_utc"]).timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]) for x in raw]
 four=aggregate(h,4);ht=[x[0] for x in h];ft=[x[0] for x in four]
 with open("data/manual_btc_trades_2025_2026.csv") as f:trades=list(csv.DictReader(f))
 out=[]
 for t in trades:
  moment=parse(t["entry_msk"]);side=1 if float(t["sl"])<float(t["entry"]) else -1
  item={"entry_msk":t["entry_msk"],"side":"LONG" if side>0 else "SHORT","entry":float(t["entry"]),"actual_stop":float(t["sl"]),"quality":t["quality"]}
  if moment is None or moment<ht[0]+48*H or moment>ht[-1]+H:item["status"]="outside_cache";out.append(item);continue
  hi=bisect.bisect_left(ht,moment);fi=bisect.bisect_right(ft,moment-4*H)
  candidates={}
  for label,rows,k,periods in (("1h",h,hi,(4,8,12,24,48,72)),("4h",four,fi,(2,3,4,6,8,12,18))):
   for n in periods:
    if k<n:continue
    prev=rows[k-n:k]
    extreme=min(z[3] for z in prev) if side==1 else max(z[2] for z in prev)
    candidates[f"{label}_{n}"]=round(extreme,2)
  # A stop beyond a previous extreme: measure how far stop is outside the extreme in % price.
  margins={k:round(100*side*(v-float(t["sl"]))/float(t["entry"]),3) for k,v in candidates.items()}
  valid={k:abs(v) for k,v in margins.items() if v>=0}
  closest=min(valid,key=valid.get) if valid else None
  item.update(status="analyzed",candidates=candidates,stop_margin_pct=margins,nearest_beyond_extreme=closest,nearest_margin_pct=margins.get(closest))
  out.append(item)
 analyzed=[x for x in out if x["status"]=="analyzed"]
 summary={}
 for side in ("LONG","SHORT"):
  a=[x for x in analyzed if x["side"]==side]
  summary[side]={"n":len(a),"nearest_extreme_counts":{k:sum(x["nearest_beyond_extreme"]==k for x in a) for k in sorted(set(x["nearest_beyond_extreme"] for x in a)) if k},"median_nearest_margin_pct":round(statistics.median(x["nearest_margin_pct"] for x in a if x["nearest_margin_pct"] is not None),3) if any(x["nearest_margin_pct"] is not None for x in a) else None,"no_extreme_beyond_stop":sum(x["nearest_beyond_extreme"] is None for x in a)}
 result={"notes":"Compare actual stops to rolling previous high/low at entry; no ATR. Negative margin means actual stop is INSIDE rather than beyond that window's extreme. Nearest lookback is descriptive, not proof of trader swing choice. 1H bars must have closed before entry, 4H must be fully closed. No orders.","summary":summary,"trades":out}
 Path("reports/manual_stop_swing_audit.json").write_text(json.dumps(result,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
