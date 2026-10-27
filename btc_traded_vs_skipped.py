"""Compare executed BTC entries against every eligible 4H DeltaRSI transition.
Descriptive feature discovery, not a profitable backtest or an OOS validation.
"""
import csv,datetime as dt,json,math,statistics,bisect
from pathlib import Path
from analyze_mtf_5y import aggregate,indicator
from research_multiasset import atr
H=3600000;MSK=dt.timezone(dt.timedelta(hours=3))
def pctile(a,x):
 return 100*sum(z<x for z in a)/len(a) if a else None
def med(a):
 a=[x for x in a if x is not None and math.isfinite(x)]
 return round(statistics.median(a),3) if a else None
def avg(a):
 a=[x for x in a if x is not None and math.isfinite(x)]
 return round(statistics.mean(a),3) if a else None
def parse(t):
 try:return int(dt.datetime.strptime(t,"%Y-%m-%d %H:%M").replace(tzinfo=MSK).timestamp()*1000)
 except:return None
def main():
 with open("data/BTCUSDT_1h.csv") as f:raw=list(csv.DictReader(f))
 hr=[(int(dt.datetime.fromisoformat(x["timestamp_utc"]).timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]) for x in raw]
 r=aggregate(hr,4);ind=indicator(r);a=atr(r)
 with open("data/manual_btc_trades_2025_2026.csv") as f:manual=list(csv.DictReader(f))
 entries=[]
 for x in manual:
  t=parse(x["entry_msk"])
  if t is None or x["quality"]=="entry_date_suspect_month":continue
  side=1 if float(x["sl"])<float(x["entry"]) else -1
  entries.append((t,side,x["entry_msk"]))
 ev=[]
 for k in range(210,len(r)-26):
  prev,cur=ind["color"][k-1],ind["color"][k]
  side=1 if prev=="mediumR" and cur=="weakR" else -1 if prev=="mediumB" and cur=="weakB" else 0
  if not side:continue
  # entry at next 4H open, as-of previous closed bar.
  tm=r[k][0]+4*H;close=r[k][4];recent=r[k-11:k+1];longer=r[k-23:k+1]
  width12=(max(x[2] for x in recent)-min(x[3] for x in recent))/close*100
  width24=(max(x[2] for x in longer)-min(x[3] for x in longer))/close*100
  atrpct=a[k]/close*100
  ap=pctile([a[j]/r[j][4]*100 for j in range(k-100,k)],atrpct)
  highs=[x[2] for x in recent];lows=[x[3] for x in recent]
  location=(close-min(lows))/(max(highs)-min(lows)) if max(highs)>min(lows) else .5
  prior12=(close/r[k-3][4]-1)*100
  prior48=(close/r[k-12][4]-1)*100
  candle=(r[k][4]-r[k][1])/(r[k][2]-r[k][3]) if r[k][2]>r[k][3] else 0
  # 20 bar Bollinger width.
  cs=[x[4] for x in r[k-19:k+1]];bb=400*statistics.pstdev(cs)/statistics.mean(cs)
  # close position relative to preceding 12 bar swing; expected low for LONG, high for SHORT
  dist_extreme=(close-min(lows) if side==1 else max(highs)-close)/close*100
  # match a user entry in [signal close -4h, signal close +8h], but no duplicate assignment.
  matches=[(abs(t-tm),label,t) for t,s,label in entries if s==side and abs(t-tm)<=8*H]
  match=min(matches) if matches else None
  # 48h next-close forward return, diagnostic only, no stop, costs not applied
  future=side*(r[k+12][4]/r[k+1][1]-1)*100
  ev.append(dict(t_utc=dt.datetime.fromtimestamp(tm/1000,dt.timezone.utc).isoformat(),side="LONG" if side==1 else "SHORT",traded=bool(match),matched_entry_msk=match[1] if match else None,match_offset_hours=round((match[2]-tm)/H,1) if match else None,range12_pct=width12,range24_pct=width24,atr_pct=atrpct,atr_percentile=ap,bb_width_pct=bb,close_location_12=location,prior12h_pct=prior12,prior48h_pct=prior48,body_ratio=candle,dist_extreme_pct=dist_extreme,forward48h_pct=future))
 # Keep only exact/near matches and show whether multiple events matched same trade
 features=("range12_pct","range24_pct","atr_pct","atr_percentile","bb_width_pct","close_location_12","prior12h_pct","prior48h_pct","body_ratio","dist_extreme_pct")
 summary={}
 for side in ("LONG","SHORT"):
  subset=[x for x in ev if x["side"]==side]
  yes=[x for x in subset if x["traded"]];no=[x for x in subset if not x["traded"]]
  summary[side]={"candidate_count":len(subset),"matched_count":len(yes),"skipped_count":len(no),"matched_unique_manual":len(set(x["matched_entry_msk"] for x in yes)),"features":{f:{"traded_median":med([x[f] for x in yes]),"skipped_median":med([x[f] for x in no]),"traded_mean":avg([x[f] for x in yes]),"skipped_mean":avg([x[f] for x in no])} for f in features},"forward48h_mean_traded":avg([x["forward48h_pct"] for x in yes]),"forward48h_mean_skipped":avg([x["forward48h_pct"] for x in no])}
 # Quantify simple single-feature separability without optimization.
 for side in ("LONG","SHORT"):
  yes=[x for x in ev if x["side"]==side and x["traded"]]
  no=[x for x in ev if x["side"]==side and not x["traded"]]
  sep=[]
  for f in features:
   v=[x[f] for x in yes+no];sd=statistics.pstdev(v) if len(v)>1 else 0
   if sd:sep.append({"feature":f,"standardized_mean_difference":round((statistics.mean(x[f] for x in yes)-statistics.mean(x[f] for x in no))/sd,3)})
  summary[side]["feature_separation"]=sorted(sep,key=lambda z:abs(z["standardized_mean_difference"]),reverse=True)
 matched=set(x["matched_entry_msk"] for x in ev if x["traded"])
 unmatched=[{"entry_msk":label,"side":"LONG" if s==1 else "SHORT"} for t,s,label in entries if label not in matched and t>=r[210][0] and t<=r[-1][0]]
 out={"notes":"4H closed candle transitions mediumR->weakR and mediumB->weakB. Compare trader-selected entries with skipped candidates; matching within +/-8h can cause ambiguous many-to-one matches, and manual entry labels are not independently verified. Feature values use only bars closed at signal. Forward 48h return is descriptive and not a backtest; no fees applied. No funding. Cache starts Oct 26 2025, warmup reduces usable period. This is in-sample exploratory selection research; no causal claim from feature differences alone.","summary":summary,"unmatched_manual_entries":unmatched,"events":ev}
 Path("reports/btc_traded_vs_skipped.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"summary":summary,"unmatched_manual_entries":unmatched},indent=2))
if __name__=="__main__":main()
