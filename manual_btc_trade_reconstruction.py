"""Reconstruct every manual BTC trade from cached hourly candles, including pre/post windows."""
import csv,datetime as dt,json,math,statistics,bisect
from pathlib import Path
from analyze_mtf_5y import indicator,aggregate
from research_multiasset import atr
MSK=dt.timezone(dt.timedelta(hours=3));UTC=dt.timezone.utc;H=3600000
def ts(s):
 try:return int(dt.datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=MSK).timestamp()*1000)
 except:return None
def rnd(x,n=3):return round(x,n) if x is not None and math.isfinite(x) else None
def main():
 with open("data/BTCUSDT_1h.csv") as f:
  raw=list(csv.DictReader(f))
 rows=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in raw]
 hours=[r[0] for r in rows];h4=aggregate(rows,4);i4=indicator(h4);a4=atr(h4);h4ts=[x[0] for x in h4];out=[]
 with open("data/manual_btc_trades_2025_2026.csv") as f: trades=list(csv.DictReader(f))
 for t in trades:
  ent=ts(t["entry_msk"]);end=ts(t["exit2_msk"] or t["exit1_msk"]);side=1 if float(t["sl"])<float(t["entry"]) else -1
  record={"entry_msk":t["entry_msk"],"side":"LONG" if side>0 else "SHORT","entry":float(t["entry"]),"stop":float(t["sl"]),"quality":t["quality"],"entry_reason":t["entry_reason"],"exit_reason":t["exit_reason"]}
  if ent is None or end is None or end<ent:record["status"]="bad_or_incomplete_time";out.append(record);continue
  ix=bisect.bisect_right(hours,ent)-1
  if ix<0 or end>hours[-1]+H:record["status"]="outside_cache";out.append(record);continue
  ex=bisect.bisect_right(hours,end)-1
  if ix<0 or ex<ix:record["status"]="invalid_index";out.append(record);continue
  # Entry is at a timestamp boundary, so the prior hourly bar is the last known closed one.
  closed=bisect.bisect_right(hours,ent-H)-1
  four=bisect.bisect_right(h4ts,ent-4*H)-1
  if four<101:record["status"]="insufficient_4h_history";out.append(record);continue
  pre=rows[max(0,ix-24):ix];during=rows[ix:ex+1];post=rows[ex+1:min(len(rows),ex+1+24)]
  pre12=h4[max(0,four-11):four+1];pre24=h4[max(0,four-23):four+1]
  r12=(max(x[2] for x in pre12)-min(x[3] for x in pre12))/h4[four][4]*100
  r24=(max(x[2] for x in pre24)-min(x[3] for x in pre24))/h4[four][4]*100
  atrpct=a4[four]/h4[four][4]*100
  atrhistory=[a4[j]/h4[j][4] for j in range(four-100,four)]
  rank=sum(x<atrpct/100 for x in atrhistory)/len(atrhistory)*100
  closings=[x[4] for x in pre24[-20:]];avg=statistics.mean(closings);std=statistics.pstdev(closings);bb=4*std/avg*100
  ema50=sum(x[4] for x in h4[max(0,four-49):four+1])/50
  entrypx=float(t["entry"]);stop=float(t["sl"]);risk=abs(entrypx-stop)
  low=min(x[3] for x in during);high=max(x[2] for x in during)
  stop_hit=(low<=stop if side>0 else high>=stop)
  best=(high-entrypx if side>0 else entrypx-low)/entrypx*100
  worst=(low-entrypx if side>0 else entrypx-high)/entrypx*100
  actual_bar=rows[ix]
  mismatch=abs(actual_bar[1]-entrypx)/entrypx*100
  deltas=[rnd(i4["delta"][j],1) for j in range(four-3,four+1)]
  colors=[i4["color"][j] for j in range(four-3,four+1)]
  last_exit=float(t["exit2"] or t["exit1"])
  record.update(status="analyzed",entry_4h_closed_utc=dt.datetime.fromtimestamp(h4[four][0]/1000,UTC).isoformat(),colors_last_4h=colors,deltas_last_4h=deltas,range12_pct=rnd(r12),range24_pct=rnd(r24),atr_pct=rnd(atrpct),atr_percentile=rnd(rank,1),bb_width_pct=rnd(bb),price_vs_sma50_pct=rnd((h4[four][4]/ema50-1)*100),prior24h_range_pct=rnd((max(x[2] for x in pre)-min(x[3] for x in pre))/entrypx*100) if pre else None,entry_vs_1h_open_pct=rnd(mismatch),entry_hour_open=actual_bar[1],entry_hour_low=actual_bar[3],entry_hour_high=actual_bar[2],stop_touched_during_trade=stop_hit,mfe_pct=rnd(best),mae_pct=rnd(worst),hours_held=rnd((end-ent)/H,1),post24h_directional_pct=rnd(side*(post[-1][4]/last_exit-1)*100) if post else None,exit1_pct=t["exit1_pct"],exit2_pct=t["exit2_pct"])
  out.append(record)
 analyzed=[x for x in out if x["status"]=="analyzed"]
 groups={}
 for side in ("LONG","SHORT"):
  rr=[x for x in analyzed if x["side"]==side]
  groups[side]={"n":len(rr),"median_range12_pct":rnd(statistics.median(x["range12_pct"] for x in rr)) if rr else None,"median_atr_pct":rnd(statistics.median(x["atr_pct"] for x in rr)) if rr else None,"stop_touched":sum(x["stop_touched_during_trade"] for x in rr),"entry_price_mismatch_gt_1pct":sum(x["entry_vs_1h_open_pct"]>1 for x in rr),"median_atr_percentile":rnd(statistics.median(x["atr_percentile"] for x in rr)) if rr else None}
 result={"source":"BTC cached 1h OHLC; UTC timestamps; manual MSK UTC+3; last fully closed 4h at entry; 24h pre/post; full in-trade 1h extremes; no funding; stop-touch is NOT ordered execution simulation and may include exit hour after the reported exit timestamp.","cache_start_utc":raw[0]["timestamp_utc"],"cache_end_utc":raw[-1]["timestamp_utc"],"count":len(out),"analyzed":len(analyzed),"summary":groups,"trades":out}
 Path("reports/manual_btc_trade_reconstruction.json").write_text(json.dumps(result,indent=2))
 print(json.dumps({"analyzed":len(analyzed),"statuses":{s:sum(x["status"]==s for x in out) for s in set(x["status"] for x in out)},"summary":groups,"examples":analyzed[:4]},indent=2))
if __name__=="__main__":main()
