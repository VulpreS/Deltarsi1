"""4H Bollinger band 2σ/2.5σ/3σ contact and rejection near manual BTC entries.
Compare matched journal entries to unselected 4H DeltaRSI signals; all candles fully closed.
"""
import json,statistics,math,bisect
from pathlib import Path
from feature_walkforward import data
from btc_price_action_bb_volume_study import ts
from scipy.stats import fisher_exact,mannwhitneyu,spearmanr
from btc_manual_trade_statistical_audit import jret,bh
import csv
def med(a):return round(statistics.median(a),4) if a else None
def features(rows,k,side):
 if k<25:return None
 result={}
 for sigma in (2,2.5,3):
  name=str(sigma).replace(".","_")
  closes=[r[4] for r in rows[k-19:k+1]]
  mid=statistics.mean(closes);std=statistics.pstdev(closes)
  lower=mid-sigma*std;upper=mid+sigma*std
  o,h,l,c=rows[k][1:5]
  result[f"bb{name}_percent_b"]=(c-lower)/(upper-lower) if upper>lower else None
  result[f"bb{name}_width_pct"]=100*(upper-lower)/mid
  result[f"bb{name}_lower_touch"]=int(l<=lower)
  result[f"bb{name}_upper_touch"]=int(h>=upper)
  result[f"bb{name}_lower_close_outside"]=int(c<lower)
  result[f"bb{name}_upper_close_outside"]=int(c>upper)
  result[f"bb{name}_lower_wick_reject"]=int(l<=lower and c>lower)
  result[f"bb{name}_upper_wick_reject"]=int(h>=upper and c<upper)
  # Previous 3 closed 4H candles: each uses its OWN contemporaneous band.
  past=[]
  for j in range(k-2,k+1):
   cs=[r[4] for r in rows[j-19:j+1]]
   m=statistics.mean(cs);sd=statistics.pstdev(cs)
   past.append((rows[j][3]<=m-sigma*sd,rows[j][2]>=m+sigma*sd,rows[j][4]<m-sigma*sd,rows[j][4]>m+sigma*sd))
  result[f"bb{name}_lower_touch_3"]=int(any(x[0] for x in past))
  result[f"bb{name}_upper_touch_3"]=int(any(x[1] for x in past))
  result[f"bb{name}_lower_outside_3"]=int(any(x[2] for x in past))
  result[f"bb{name}_upper_outside_3"]=int(any(x[3] for x in past))
  result[f"bb{name}_directional_touch_3"]=result[f"bb{name}_lower_touch_3"] if side==1 else result[f"bb{name}_upper_touch_3"]
  result[f"bb{name}_directional_reject"]=result[f"bb{name}_lower_wick_reject"] if side==1 else result[f"bb{name}_upper_wick_reject"]
 return result
def main():
 from analyze_mtf_5y import indicator
 from completed_candles import aggregate_completed
 from btc_price_action_bb_volume_study import read
 raw=read();rows=aggregate_completed(raw,4,asof_ms=raw[-1][0]+3600000)
 colors=indicator(rows)["color"];times=[x[0]+4*3600000 for x in rows]
 with open("data/manual_btc_trades_2025_2026.csv") as f:journal=list(csv.DictReader(f))
 manual=[]
 for r in journal:
  t=ts(r["entry_msk"])
  if t is None:continue
  side=1 if float(r["sl"])<float(r["entry"]) else -1
  manual.append({"time":t,"side":side,"ret":jret(r) if r["quality"]=="ok" else None})
 signals=[]
 for k in range(210,len(rows)):
  p,c=colors[k-1],colors[k]
  side=1 if p=="mediumR" and c=="weakR" else -1 if p=="mediumB" and c=="weakB" else 0
  if side:signals.append({"time":times[k],"side":side,"features":features(rows,k,side)})
 selected=[];used=set()
 for m in manual:
  matches=[(abs(s["time"]-m["time"]),j) for j,s in enumerate(signals) if j not in used and s["side"]==m["side"] and abs(s["time"]-m["time"])<=4*3600000]
  if matches:
   _,j=min(matches);used.add(j);selected.append({**signals[j],"ret":m["ret"],"manual_time":m["time"]})
 skipped=[s for j,s in enumerate(signals) if j not in used]
 tests=[];outcomes=[]
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x for x in selected if x["side"]==side];b=[x for x in skipped if x["side"]==side]
  for sigma in (2,2.5,3):
   name=str(sigma).replace(".","_")
   for suffix in ("directional_touch_3","directional_reject","lower_touch","upper_touch","lower_wick_reject","upper_wick_reject","lower_close_outside","upper_close_outside"):
    key=f"bb{name}_{suffix}";va=[x["features"][key] for x in a];vb=[x["features"][key] for x in b]
    yes_a=sum(va);yes_b=sum(vb);odds,p=fisher_exact([[yes_a,len(va)-yes_a],[yes_b,len(vb)-yes_b]])
    tests.append({"side":label,"feature":key,"selected_yes":yes_a,"selected_n":len(va),"skipped_yes":yes_b,"skipped_n":len(vb),"selected_pct":round(100*yes_a/len(va),1),"skipped_pct":round(100*yes_b/len(vb),1),"p":round(float(p),6)})
   for suffix in ("percent_b","width_pct"):
    key=f"bb{name}_{suffix}";va=[x["features"][key] for x in a if x["features"][key] is not None];vb=[x["features"][key] for x in b if x["features"][key] is not None]
    _,p=mannwhitneyu(va,vb)
    tests.append({"side":label,"feature":key,"selected_median":med(va),"skipped_median":med(vb),"selected_n":len(va),"skipped_n":len(vb),"p":round(float(p),6)})
 # Correlate continuous BB widths and %B with realized returns; outcomes from journal only.
 for sigma in (2,2.5,3):
  name=str(sigma).replace(".","_")
  for suffix in ("width_pct","percent_b"):
   key=f"bb{name}_{suffix}"
   for side,label in ((None,"ALL"),(1,"LONG"),(-1,"SHORT")):
    vals=[(s["features"][key],s["ret"]) for s in selected if s["ret"] is not None and (side is None or s["side"]==side)]
    if len(vals)<8:continue
    rho,p=spearmanr([x for x,y in vals],[y for x,y in vals])
    outcomes.append({"side":label,"feature":key,"n":len(vals),"rho":round(float(rho),4),"p":round(float(p),6)})
 for t,q in zip(tests,bh([x["p"] for x in tests])):t["q_bh"]=q
 for t,q in zip(outcomes,bh([x["p"] for x in outcomes])):t["q_bh"]=q
 out={"notes":"BTC 4H Bollinger Bands 20-period SMA, population std, multipliers 2, 2.5, 3. Touch=4H high/low reaches contemporaneous band, rejection=touch and close back inside; prior 3 closed 4H bars evaluated with their own band. Only completed 4H candles, signals matched to journal within +/-4h. Entry timestamp may differ; no partial 4H. No volume. Multiple tests BH adjusted, repeated sigma features highly correlated. Small selected sample. Selection is not proof of profitable trading.","selected":len(selected),"skipped":len(skipped),"selection_tests":sorted(tests,key=lambda x:x["p"]),"outcome_correlations":sorted(outcomes,key=lambda x:x["p"]),"selected_trades":selected}
 Path("reports/btc_4h_bollinger_sigma_study.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"selected":len(selected),"skipped":len(skipped),"top_selection":out["selection_tests"][:12],"outcomes":out["outcome_correlations"]},indent=2))
if __name__=="__main__":main()
