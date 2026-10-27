"""Exploratory statistical audit of BTC manual trade selection and realized returns.
No invented volumes; one-to-one signal matching from prior reports; descriptive inference only.
"""
import json,csv,math,statistics,datetime as dt
from pathlib import Path
import numpy as np
from scipy.stats import fisher_exact,mannwhitneyu,spearmanr
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from btc_price_action_bb_volume_study import ts
FEE=.0015
def jret(r):
 try:
  entry=float(r["entry"]);stop=float(r["sl"]);side=1 if stop<entry else -1
  legs=[]
  for ix in (1,2):
   price=r.get("exit"+str(ix));pct=r.get("exit"+str(ix)+"_pct")
   if price and pct:legs.append((float(price),float(pct)))
  if not legs:return None
  weight=sum(p for _,p in legs)
  if not 99<=weight<=101:return None
  return side*(sum(p*price for price,p in legs)/weight/entry-1)-FEE
 except:return None
def median(x):return round(float(np.median(x)),4) if len(x) else None
def bh(ps):
 n=len(ps);order=np.argsort(ps);q=[None]*n;v=1.
 for rank in range(n-1,-1,-1):
  ix=int(order[rank]);v=min(v,ps[ix]*n/(rank+1));q[ix]=round(v,5)
 return q
def main():
 h=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
 d=json.loads(Path("reports/btc_daily_context_study.json").read_text())
 with open("data/manual_btc_trades_2025_2026.csv") as f:journal=list(csv.DictReader(f))
 manual=[]
 for r in journal:
  val=jret(r)
  if val is not None and r["quality"]=="ok":
   manual.append({"time":ts(r["entry_msk"]),"ret":val,"side":1 if float(r["sl"])<float(r["entry"]) else -1})
 manual=[x for x in manual if x["time"] is not None]
 # Daily context for selected entries is mapped by matched signal time; link journal within +/-4h and same side.
 daily={(x["time"],x["side"]):x["features"] for x in d["selected_details"]}
 selected=[]
 for s in h["matched_trades"]:
  f={**s["features"],**daily.get((s["signal_time"],s["side"]),{})}
  opts=[m for m in manual if m["side"]==s["side"] and abs(m["time"]-s["manual_time"])<=3600000]
  selected.append({"time":s["signal_time"],"side":s["side"],"features":f,"ret":opts[0]["ret"] if opts else None})
 # For skipped signals, daily feature extraction directly from cached 4H and strict prior completed UTC day.
 from btc_daily_context_study import daily,features,read,DAY
 import bisect
 ds=daily(read());days=[x[0] for x in ds]
 skipped=[]
 for s in h["skipped_signals"]:
  i=bisect.bisect_right(days,s["time"]-DAY)-1
  df=features(ds,i,s["side"]) if i>=20 and days[i]+DAY<=s["time"] else {}
  skipped.append({"time":s["time"],"side":s["side"],"features":{**s["features"],**(df or {})}})
 # Predeclared, nonredundant subset to mitigate p-hacking, report all tests and BH correction.
 keys=["range12_pct","bb_width_pct","bb_percent_b","sma50_dist_pct","sma200_dist_pct","lower_wick_fraction","upper_wick_fraction","body_fraction","prior12_return_pct","daily_3d_return_pct","daily_10d_return_pct","daily_sma20_dist_pct","daily_sma50_dist_pct","daily_bb_percent_b","daily_bb_width_pct","daily_range5_pct","daily_lower_rejection","daily_upper_rejection","daily_bullish"]
 tests=[];regression={}
 for side,name in ((1,"LONG"),(-1,"SHORT")):
  a=[x for x in selected if x["side"]==side];b=[x for x in skipped if x["side"]==side]
  for k in keys:
   va=[x["features"].get(k) for x in a];vb=[x["features"].get(k) for x in b]
   va=[float(x) for x in va if x is not None and math.isfinite(float(x))]
   vb=[float(x) for x in vb if x is not None and math.isfinite(float(x))]
   if len(va)<5 or len(vb)<15:continue
   binary=k in ("daily_lower_rejection","daily_upper_rejection","daily_bullish")
   if binary:
    aa=sum(x>0 for x in va);bb=sum(x>0 for x in vb)
    odds,p=fisher_exact([[aa,len(va)-aa],[bb,len(vb)-bb]])
    method="Fisher exact (2x2)";effect=round(float(odds),4) if math.isfinite(odds) else None
   else:
    _,p=mannwhitneyu(va,vb,alternative="two-sided")
    method="Mann-Whitney U";effect=round(median(va)-median(vb),4)
   tests.append({"side":name,"feature":k,"n_selected":len(va),"n_skipped":len(vb),"selected_median":median(va),"skipped_median":median(vb),"p_raw":round(float(p),6),"method":method,"effect":effect})
  # Time series split: selection classification, avoid leakage by grouping timestamps in time.
  modelkeys=["range12_pct","bb_width_pct","sma200_dist_pct","daily_3d_return_pct","daily_sma50_dist_pct","lower_wick_fraction"]
  sample=sorted([(x["time"],1 if x in a else 0,[x["features"].get(k) for k in modelkeys]) for x in a+b],key=lambda x:x[0])
  sample=[x for x in sample if all(v is not None and math.isfinite(float(v)) for v in x[2])]
  X=np.array([x[2] for x in sample]);y=np.array([x[1] for x in sample])
  folds=[]
  if len(sample)>=70 and y.sum()>=8:
   for train,test in TimeSeriesSplit(n_splits=4).split(X):
    if len(set(y[train]))<2 or len(set(y[test]))<2:continue
    clf=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,class_weight="balanced",C=.3))
    clf.fit(X[train],y[train]);pred=clf.predict_proba(X[test])[:,1]
    folds.append({"n_test":len(test),"positives":int(y[test].sum()),"auc":round(float(roc_auc_score(y[test],pred)),4)})
  regression[name]={"features":modelkeys,"samples":len(sample),"selected":int(y.sum()),"chronological_folds":folds,"mean_auc":round(float(np.mean([f["auc"] for f in folds])),4) if folds else None}
 qs=bh([t["p_raw"] for t in tests])
 for t,q in zip(tests,qs):t["q_bh"]=q
 # Manual realized outcome correlations. Deliberately avoid multiple regression with ~26 trades.
 outcome=[]
 for k in keys:
  x=[(float(s["features"][k]),s["ret"]) for s in selected if s["ret"] is not None and s["features"].get(k) is not None]
  if len(x)>=12 and len(set(a for a,b in x))>2:
   rho,p=spearmanr([a for a,b in x],[b for a,b in x])
   if math.isfinite(float(rho)):outcome.append({"feature":k,"n":len(x),"spearman_rho":round(float(rho),4),"p_raw":round(float(p),6)})
 if outcome:
  for r,q in zip(outcome,bh([x["p_raw"] for x in outcome])):r["q_bh"]=q
 net=[m["ret"] for m in manual];selected_net=[s["ret"] for s in selected if s["ret"] is not None]
 out={"notes":"Exploratory BTC only. Historical journal quality=ok for full-journal return calculations, partial exits weighted by percent; 0.15% roundtrip. Matched selection signals +/-4h (not exact trade entry) compared to skipped, independent selected/skipped labels but temporally correlated signals. 19 prespecified comparisons per direction, BH false discovery rate across all tests. Fisher exact for binary, Mann Whitney for continuous; NOT chi-square for sparse counts. Selection regression chronological TimeSeriesSplit, not a trading backtest. Outcome correlations exploratory, BH-adjusted; journal returns and entry indicator timestamps may differ. Daily features only fully closed prior UTC day, hourly features only completed bars. No volume available. Avoid causal claims.","journal":{"total_rows":len(journal),"quality_ok_usable":len(manual),"win_rate_pct":round(100*sum(x>0 for x in net)/len(net),2) if net else None,"mean_net_pct":round(100*statistics.mean(net),3) if net else None,"median_net_pct":round(100*statistics.median(net),3) if net else None},"selected_signals":len(selected),"selected_with_outcome":len(selected_net),"skipped_signals":len(skipped),"selection_tests":sorted(tests,key=lambda x:x["p_raw"]),"selection_regression":regression,"outcome_correlations":sorted(outcome,key=lambda x:x["p_raw"])}
 Path("reports/btc_manual_trade_statistical_audit.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"journal":out["journal"],"matched":len(selected),"outcome_matched":len(selected_net),"regression":regression,"selection_top":out["selection_tests"][:12],"outcome_top":out["outcome_correlations"][:8]},indent=2))
if __name__=="__main__":main()
