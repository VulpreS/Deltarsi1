"""Explain discretionary BTC trade selection using price action, Bollinger, MAs and public Bybit volume.
Strictly use only CLOSED 1H candles before entry; compare to unselected DeltaRSI transitions.
"""
import csv,datetime as dt,json,statistics,math,time,urllib.request,urllib.parse,bisect
from pathlib import Path
from analyze_mtf_5y import indicator
from completed_candles import aggregate_completed
H=3600000;TZ=dt.timezone(dt.timedelta(hours=3))
def ts(s):
 try:return int(dt.datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp()*1000)
 except:return None
def med(v):return round(statistics.median(v),4) if v else None
def read():
 with open("data/BTCUSDT_1h.csv") as f:return [(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
def volumes(raw):
 path=Path("data/BTCUSDT_1h_volume_bybit.csv")
 if path.exists():
  with path.open() as f: return {int(x["timestamp_ms"]):float(x["volume"]) for x in csv.DictReader(f)},"cached"
 end=raw[-1][0];start=raw[0][0];res={};cursor=start;err=None
 try:
  while cursor<=end:
   params=urllib.parse.urlencode({"category":"linear","symbol":"BTCUSDT","interval":"60","start":cursor,"end":min(cursor+999*H,end),"limit":1000})
   req=urllib.request.Request("https://api.bybit.com/v5/market/kline?"+params,headers={"User-Agent":"DeltaRSIResearch/1.0"})
   with urllib.request.urlopen(req,timeout=18) as resp:payload=json.load(resp)
   if payload.get("retCode")!=0:raise RuntimeError(str(payload.get("retMsg")))
   for x in payload["result"]["list"]:
    t=int(x[0])
    if start<=t<=end:res[t]=float(x[5])
   cursor+=1000*H
   time.sleep(.08)
  if len(res)<.85*len(raw):raise RuntimeError("volume coverage below 85 percent")
  path.parent.mkdir(exist_ok=True)
  with path.open("w") as f:
   w=csv.writer(f);w.writerow(["timestamp_ms","volume"]);w.writerows(sorted(res.items()))
  return res,"Bybit USDT linear public API"
 except Exception as e:return res,"unavailable: "+str(e)
def feat(raw,vol,i):
 if i<201:return None
 r=raw[i];o,h,l,c=r[1:];history=raw[:i+1]
 closes=[x[4] for x in history];d={}
 for n in (20,50,100,200):
  ma=statistics.mean(closes[-n:]);d["sma"+str(n)+"_dist_pct"]=100*(c/ma-1)
 for n in (20,50,100,200):
  alpha=2/(n+1);v=closes[0]
  for z in closes[1:]:v=alpha*z+(1-alpha)*v
  d["ema"+str(n)+"_dist_pct"]=100*(c/v-1)
 mid=statistics.mean(closes[-20:]);sd=statistics.pstdev(closes[-20:]);up=mid+2*sd;low=mid-2*sd
 d["bb_percent_b"]=(c-low)/(up-low) if up>low else None
 d["bb_width_pct"]=100*(up-low)/mid
 d["bb_below_lower"]=int(c<low);d["bb_above_upper"]=int(c>up)
 d["bb_low_reentry"]=int(closes[-2]<statistics.mean(closes[-21:-1])-2*statistics.pstdev(closes[-21:-1]) and c>=low)
 d["bb_high_reentry"]=int(closes[-2]>statistics.mean(closes[-21:-1])+2*statistics.pstdev(closes[-21:-1]) and c<=up)
 span=max(h-l,1e-10);body=abs(c-o)/span
 d["body_fraction"]=body;d["lower_wick_fraction"]=(min(c,o)-l)/span;d["upper_wick_fraction"]=(h-max(c,o))/span
 d["bullish"]=int(c>o);d["bearish"]=int(c<o)
 d["bull_engulf"]=int(c>o and raw[i-1][4]<raw[i-1][1] and c>=raw[i-1][1] and o<=raw[i-1][4])
 d["bear_engulf"]=int(c<o and raw[i-1][4]>raw[i-1][1] and c<=raw[i-1][1] and o>=raw[i-1][4])
 d["lower_rejection"]=int(d["lower_wick_fraction"]>=.45 and d["lower_wick_fraction"]>=2*body)
 d["upper_rejection"]=int(d["upper_wick_fraction"]>=.45 and d["upper_wick_fraction"]>=2*body)
 for n in (6,12,24):
  seg=raw[i-n+1:i+1];d["range"+str(n)+"_pct"]=100*(max(x[2] for x in seg)-min(x[3] for x in seg))/c
 d["prior12_return_pct"]=100*(c/raw[i-12][4]-1)
 d["prior24_return_pct"]=100*(c/raw[i-24][4]-1)
 d["higher_high_3"]=int(h>max(x[2] for x in raw[i-3:i]))
 d["lower_low_3"]=int(l<min(x[3] for x in raw[i-3:i]))
 v=[vol.get(x[0]) for x in raw[i-20:i+1]]
 if all(x is not None for x in v):
  d["volume_ratio_20"]=v[-1]/statistics.mean(v[:-1]) if statistics.mean(v[:-1]) else None
  d["volume_4h_ratio_20"]=sum(v[-4:])/(4*statistics.mean(v[:-1])) if statistics.mean(v[:-1]) else None
 else:
  d["volume_ratio_20"]=None;d["volume_4h_ratio_20"]=None
 return d
def main():
 raw=read();vol,source=volumes(raw);times=[x[0] for x in raw]
 with open("data/manual_btc_trades_2025_2026.csv") as f:journal=list(csv.DictReader(f))
 # A signal at the end of completed 4H candle, corresponding to first hour of next candle.
 four=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H);colors=indicator(four)["color"]
 signal=[]
 for j in range(210,len(four)):
  p,c=colors[j-1],colors[j]
  side=1 if p=="mediumR" and c=="weakR" else -1 if p=="mediumB" and c=="weakB" else 0
  if side:
   cutoff=four[j][0]+4*H;idx=bisect.bisect_left(times,cutoff)-1
   if idx>=201 and raw[idx][0]+H==cutoff:signal.append({"time":cutoff,"side":side,"features":feat(raw,vol,idx)})
 manual=[]
 for t in journal:
  moment=ts(t["entry_msk"]);side=1 if float(t["sl"])<float(t["entry"]) else -1
  if moment is None:continue
  idx=bisect.bisect_left(times,moment)-1
  if idx<201 or idx>=len(raw) or raw[idx][0]+H!=moment:continue
  manual.append({"time":moment,"side":side,"quality":t["quality"],"features":feat(raw,vol,idx)})
 # One-to-one nearest signal matching, within +/- 4h, avoid claiming exact alignment.
 used=set();matched=[]
 for m in manual:
  options=[(abs(s["time"]-m["time"]),j) for j,s in enumerate(signal) if j not in used and s["side"]==m["side"] and abs(s["time"]-m["time"])<=4*H]
  if options:
   _,j=min(options);used.add(j);matched.append({"manual_time":m["time"],"signal_time":signal[j]["time"],"side":m["side"],"features":signal[j]["features"]})
 skipped=[s for j,s in enumerate(signal) if j not in used]
 keys=list(manual[0]["features"]) if manual else []
 comparison={}
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x["features"] for x in matched if x["side"]==side]
  b=[x["features"] for x in skipped if x["side"]==side]
  comparison[label]={"matched":len(a),"skipped":len(b),"features":{key:{"matched_median":med([x[key] for x in a if x[key] is not None]),"skipped_median":med([x[key] for x in b if x[key] is not None]),"matched_true_pct":round(100*statistics.mean(x[key] for x in a),1) if a and key in ("lower_rejection","upper_rejection","bull_engulf","bear_engulf","bb_low_reentry","bb_high_reentry") else None,"skipped_true_pct":round(100*statistics.mean(x[key] for x in b),1) if b and key in ("lower_rejection","upper_rejection","bull_engulf","bear_engulf","bb_low_reentry","bb_high_reentry") else None} for key in keys}}
 out={"notes":"Only fully closed 1H candles as of trade entry or completed 4H signal. BTC manual journal matched one-to-one to completed 4H DeltaRSI transition within 4 hours, descriptive selection analysis, not out-of-sample proof. Features use 1H close prior to event, no future data. Volume public Bybit linear contract, if available, otherwise null. All comparisons exploratory and correlated; no significance claims. Signals before warmup excluded.","volume_source":source,"volume_coverage_hours":len(vol),"matched_manual":len(matched),"manual_with_features":len(manual),"signal_count":len(signal),"comparison":comparison,"matched_trades":matched,"skipped_signals":skipped}
 Path("reports/btc_price_action_bb_volume_study.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"volume":source,"volume_coverage":len(vol),"manual":len(manual),"matched":len(matched),"comparison":comparison},indent=2))
if __name__=="__main__":main()
