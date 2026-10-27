"""Linear close-chart and exchange volume proxy comparison for manual BTC selection.
Volume source: Binance USD-M BTCUSDT 1h archives, NOT Bybit; unavailable data omitted.
"""
import csv,json,math,statistics,datetime as dt,io,zipfile,urllib.request,bisect
from pathlib import Path
import numpy as np
from scipy.stats import mannwhitneyu,fisher_exact,spearmanr
from btc_manual_trade_statistical_audit import bh
from btc_price_action_bb_volume_study import read
H=3600000
def median(a):return round(float(np.median(a)),5) if a else None
def volume_fetch(raw):
 start=dt.datetime.fromtimestamp(raw[0][0]/1000,dt.timezone.utc);end=dt.datetime.fromtimestamp(raw[-1][0]/1000,dt.timezone.utc)
 out={};fail=[]
 months=[];y,m=start.year,start.month
 while (y,m)<=(end.year,end.month):
  months.append((y,m));m+=1
  if m>12:y+=1;m=1
 for y,m in months:
  url=f"https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{y}-{m:02d}.zip"
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
   with urllib.request.urlopen(req,timeout=18) as response:blob=response.read()
   with zipfile.ZipFile(io.BytesIO(blob)) as z:
    with z.open(z.namelist()[0]) as f:
     for row in csv.reader(io.TextIOWrapper(f)):
      try:t=int(row[0]);v=float(row[5]);q=float(row[7])
      except:continue
      if raw[0][0]<=t<=raw[-1][0]:out[t]=(v,q)
  except Exception as e:fail.append(f"{y}-{m:02d}: {type(e).__name__} {str(e)[:100]}")
 return out,fail
def feature(raw,i,volume):
 if i<50:return None
 cl=np.array([x[4] for x in raw[i-48:i+1]])
 c=cl[-1];diff=np.diff(cl)
 d={}
 for n in (3,6,12,24):
  a=cl[-n-1:];delta=np.diff(a);total=np.sum(np.abs(delta))
  d[f"close_return_{n}h_pct"]=100*(c/a[0]-1)
  d[f"close_efficiency_{n}h"]=abs(c-a[0])/total if total else 0
  d[f"close_direction_changes_{n}h"]=sum(delta[1:]*delta[:-1]<0)
  d[f"close_range_{n}h_pct"]=100*(max(a)-min(a))/c
  d[f"close_up_count_{n}h"]=sum(delta>0)
 d["close_slope_6h_pct"]=100*(c/cl[-7])/6-100/6
 d["close_slope_prev6h_pct"]=100*(cl[-7]/cl[-13]-1)/6
 d["close_acceleration_6h"]=d["close_slope_6h_pct"]-d["close_slope_prev6h_pct"]
 d["close_lower_low_6h"]=int(c<min(cl[-7:-1]))
 d["close_higher_high_6h"]=int(c>max(cl[-7:-1]))
 d["close_rebound_from_12h_low_pct"]=100*(c/min(cl[-13:])-1)
 d["close_pullback_from_12h_high_pct"]=100*(c/max(cl[-13:])-1)
 # relative volume and trend on same Binance linear perpetual contract
 vs=[volume.get(raw[j][0]) for j in range(i-24,i+1)]
 if all(v is not None for v in vs):
  units=np.array([x[0] for x in vs]);quotes=np.array([x[1] for x in vs])
  d["volume_ratio_20"]=units[-1]/np.mean(units[-21:-1])
  d["volume_4h_ratio_20"]=np.mean(units[-4:])/np.mean(units[-24:-4])
  d["quote_volume_ratio_20"]=quotes[-1]/np.mean(quotes[-21:-1])
  d["volume_trend_12h"]=np.mean(units[-6:])/np.mean(units[-12:-6])
  d["volume_price_divergence_6h"]=int((c>cl[-7] and np.mean(units[-6:])<np.mean(units[-12:-6])) or (c<cl[-7] and np.mean(units[-6:])<np.mean(units[-12:-6])))
  d["volume_climax_6h"]=int(max(units[-6:])>2*np.mean(units[-24:-6]))
  d["volume_falling_6h"]=int(np.mean(units[-6:])<np.mean(units[-12:-6]))
 else:
  for k in ("volume_ratio_20","volume_4h_ratio_20","quote_volume_ratio_20","volume_trend_12h","volume_price_divergence_6h","volume_climax_6h","volume_falling_6h"):d[k]=None
 return d
def main():
 raw=read();times=[x[0] for x in raw];volume,fail=volume_fetch(raw)
 previous=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
 samples=[]
 for selected,group in ((1,previous["matched_trades"]),(0,previous["skipped_signals"])):
  for x in group:
   t=x["signal_time"] if selected else x["time"]
   i=bisect.bisect_left(times,t)-1
   if i<50 or raw[i][0]+H!=t:continue
   f=feature(raw,i,volume)
   samples.append({"time":t,"side":x["side"],"selected":selected,"features":f})
 keys=list(samples[0]["features"])
 tests=[]
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x for x in samples if x["selected"] and x["side"]==side]
  b=[x for x in samples if not x["selected"] and x["side"]==side]
  for k in keys:
   va=[x["features"][k] for x in a if x["features"][k] is not None]
   vb=[x["features"][k] for x in b if x["features"][k] is not None]
   if len(va)<8 or len(vb)<30:continue
   binary=k.startswith("volume_") and k in ("volume_price_divergence_6h","volume_climax_6h","volume_falling_6h") or k in ("close_lower_low_6h","close_higher_high_6h")
   if binary:
    _,p=fisher_exact([[sum(va),len(va)-sum(va)],[sum(vb),len(vb)-sum(vb)]])
    vals={"selected_pct":round(100*statistics.mean(va),1),"skipped_pct":round(100*statistics.mean(vb),1)}
   else:
    _,p=mannwhitneyu(va,vb)
    vals={"selected_median":median(va),"skipped_median":median(vb)}
   tests.append({"side":label,"feature":k,"selected_n":len(va),"skipped_n":len(vb),"p":round(float(p),7),**vals})
 for t,q in zip(tests,bh([x["p"] for x in tests])):t["q_bh"]=q
 out={"notes":"Linear price chart=close-to-close features from CLOSED 1H bars, selected vs skipped completed 4H DeltaRSI fades. Volume is Binance USDT-M BTCUSDT perpetual 1H volume PROXY, not Bybit. Only exact timestamps matched, missing volume excluded. Exploratory p-values BH adjusted, samples small and serially correlated. This does not test strategy profitability.","volume_source":"Binance USD-M BTCUSDT 1h public historical klines, not Bybit" if volume else "unavailable","volume_covered_hours":len(volume),"volume_missing_months":fail,"selected":sum(x["selected"] for x in samples),"skipped":sum(not x["selected"] for x in samples),"selection_tests":sorted(tests,key=lambda x:x["p"])}
 Path("reports/btc_linear_close_volume_study.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"source":out["volume_source"],"coverage":len(volume),"errors":fail[:5],"selected":out["selected"],"skipped":out["skipped"],"top":out["selection_tests"][:15]},indent=2))
if __name__=="__main__":main()
