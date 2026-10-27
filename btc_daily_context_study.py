"""Daily candle context for manually traded versus skipped BTC 4H DeltaRSI signals.
Only complete UTC daily candles strictly prior to event, no lookahead.
"""
import json,csv,datetime as dt,statistics,bisect
from pathlib import Path
from btc_price_action_bb_volume_study import read,med
DAY=86400000
def daily(raw):
 groups={}
 for t,o,h,l,c in raw:
  day=t//DAY*DAY
  groups.setdefault(day,[]).append((t,o,h,l,c))
 out=[]
 for day,rows in sorted(groups.items()):
  if len(rows)!=24 or rows[0][0]!=day or rows[-1][0]!=day+23*3600000:continue
  out.append((day,rows[0][1],max(x[2] for x in rows),min(x[3] for x in rows),rows[-1][4]))
 return out
def features(ds,i,side):
 if i<20:return None
 day,o,h,l,c=ds[i];previous=ds[i-1];span=max(h-l,1e-9)
 close=[r[4] for r in ds[:i+1]]
 d={"daily_body_frac":abs(c-o)/span,"daily_lower_wick_frac":(min(o,c)-l)/span,"daily_upper_wick_frac":(h-max(o,c))/span,"daily_close_location":(c-l)/span,"daily_range_pct":100*(h-l)/c,"daily_return_pct":100*(c/o-1),"daily_3d_return_pct":100*(c/ds[i-3][4]-1),"daily_5d_return_pct":100*(c/ds[i-5][4]-1),"daily_10d_return_pct":100*(c/ds[i-10][4]-1),"daily_bullish":int(c>o),"daily_lower_rejection":int((min(o,c)-l)/span>.4),"daily_upper_rejection":int((h-max(o,c))/span>.4),"daily_bull_engulf":int(c>o and previous[4]<previous[1] and c>=previous[1] and o<=previous[4]),"daily_bear_engulf":int(c<o and previous[4]>previous[1] and c<=previous[1] and o>=previous[4]),"daily_inside":int(h<previous[2] and l>previous[3]),"daily_outside":int(h>previous[2] and l<previous[3])}
 for n in (3,5,10):
  d["daily_range"+str(n)+"_pct"]=100*(max(x[2] for x in ds[i-n+1:i+1])-min(x[3] for x in ds[i-n+1:i+1]))/c
  d["daily_up_count"+str(n)]=sum(x[4]>x[1] for x in ds[i-n+1:i+1])
 for n in (20,50,100,200):
  if len(close)>=n:
   sma=statistics.mean(close[-n:]);d["daily_sma"+str(n)+"_dist_pct"]=100*(c/sma-1)
  else:d["daily_sma"+str(n)+"_dist_pct"]=None
 if len(close)>=20:
  m=statistics.mean(close[-20:]);s=statistics.pstdev(close[-20:]);d["daily_bb_percent_b"]=(c-(m-2*s))/(4*s) if s else None;d["daily_bb_width_pct"]=400*s/m
 else:d["daily_bb_percent_b"]=None;d["daily_bb_width_pct"]=None
 d["daily_3d_lower_wick_max"]=max((min(x[1],x[4])-x[3])/max(x[2]-x[3],1e-9) for x in ds[i-2:i+1])
 d["daily_3d_upper_wick_max"]=max((x[2]-max(x[1],x[4]))/max(x[2]-x[3],1e-9) for x in ds[i-2:i+1])
 return d
def main():
 raw=read();ds=daily(raw);days=[x[0] for x in ds]
 original=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
 # Use matched signal timestamps (not journal timestamps) for apples-to-apples controls.
 def add(x):
  t=x["signal_time"] if "signal_time" in x else x["time"]
  i=bisect.bisect_right(days,t-DAY)-1
  # daily bar day+24h must end at or before event
  if i<0 or days[i]+DAY>t: return None
  f=features(ds,i,x["side"])
  return {"time":t,"side":x["side"],"daily_date_utc":dt.datetime.fromtimestamp(days[i]/1000,dt.timezone.utc).date().isoformat(),"features":f} if f else None
 selected=[y for x in original["matched_trades"] if (y:=add(x))]
 skipped=[y for x in original["skipped_signals"] if (y:=add(x))]
 keys=list(selected[0]["features"]) if selected else []
 compare={}
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x["features"] for x in selected if x["side"]==side]
  b=[x["features"] for x in skipped if x["side"]==side]
  compare[label]={"selected":len(a),"skipped":len(b),"features":{k:{"selected_median":med([x[k] for x in a if x[k] is not None]),"skipped_median":med([x[k] for x in b if x[k] is not None]),"selected_rate_pct":round(100*statistics.mean(x[k] for x in a),1) if a and k in ("daily_lower_rejection","daily_upper_rejection","daily_bull_engulf","daily_bear_engulf","daily_inside","daily_outside","daily_bullish") else None,"skipped_rate_pct":round(100*statistics.mean(x[k] for x in b),1) if b and k in ("daily_lower_rejection","daily_upper_rejection","daily_bull_engulf","daily_bear_engulf","daily_inside","daily_outside","daily_bullish") else None} for k in keys}}
 out={"notes":"BTC 1D candle context for matched manual entries versus skipped closed-4H DeltaRSI signals. UTC daily candles, only fully closed before event; incomplete edge days discarded. Strict 20-day warmup, 50/100/200d MAs only where history available. Selected events are 4H signals matched to manual trades within 4 hours, not exact manual execution timestamps. Descriptive, no significance or causality claims. No daily volume in cached data.","daily_bars":len(ds),"selected_count":len(selected),"skipped_count":len(skipped),"comparison":compare,"selected_details":selected}
 Path("reports/btc_daily_context_study.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"daily_bars":len(ds),"selected":len(selected),"skipped":len(skipped),"comparison":compare},indent=2))
if __name__=="__main__":main()
