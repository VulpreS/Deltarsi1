"""MACD and momentum exhaustion study for discretionary BTC DeltaRSI entries.
Uses fully completed 4H candles and pre-existing matched manual trades.
"""
import json,csv,math,statistics,bisect
from pathlib import Path
import numpy as np
from scipy.stats import mannwhitneyu,spearmanr,fisher_exact
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score
from feature_walkforward import data
from btc_manual_trade_statistical_audit import bh
def ema(a,n):
 out=[];v=a[0];alpha=2/(n+1)
 for x in a:
  v=alpha*x+(1-alpha)*v;out.append(v)
 return np.array(out)
def features(rows):
 close=np.array([r[4] for r in rows]);high=np.array([r[2] for r in rows]);low=np.array([r[3] for r in rows]);op=np.array([r[1] for r in rows])
 fast=ema(close,11);slow=ema(close,27);line=fast-slow;sig=ema(line,22);hist=line-sig
 # Classic 12/26/9 as control, same calculations.
 classic=ema(close,12)-ema(close,26);classhist=classic-ema(classic,9)
 tr=np.maximum(high-low,np.maximum(abs(high-np.roll(close,1)),abs(low-np.roll(close,1))));tr[0]=high[0]-low[0]
 atr=ema(tr,14)
 output={}
 for i in range(60,len(rows)):
  c=close[i];a=max(atr[i],1e-10)
  p=hist[i-1];h=hist[i]
  span=max(high[i]-low[i],1e-9)
  d={
   "macd_hist_atr":h/a,
   "macd_line_atr":line[i]/a,
   "macd_hist_slope_atr":(h-p)/a,
   "macd_hist_accel_atr":(h-2*p+hist[i-2])/a,
   "macd_hist_fading":int(abs(h)<abs(p) and h*p>0),
   "macd_hist_growing":int(abs(h)>abs(p) and h*p>0),
   "macd_bull_cross_3":int(any(line[j-1]<=sig[j-1] and line[j]>sig[j] for j in range(i-2,i+1))),
   "macd_bear_cross_3":int(any(line[j-1]>=sig[j-1] and line[j]<sig[j] for j in range(i-2,i+1))),
   "macd_hist_positive":int(h>0),
   "macd_classic_hist_atr":classhist[i]/a,
   "macd_classic_slope_atr":(classhist[i]-classhist[i-1])/a,
   "atr_pct":100*a/c,
   "atr_accel_pct":100*(atr[i]/atr[i-3]-1),
   "close_location":(c-low[i])/span,
   "body_fraction":abs(c-op[i])/span,
   "efficiency_6":abs(c-close[i-6])/sum(abs(close[j]-close[j-1]) for j in range(i-5,i+1)) if sum(abs(close[j]-close[j-1]) for j in range(i-5,i+1)) else 0,
   "range_compression":(high[i]-low[i])/statistics.mean(high[j]-low[j] for j in range(i-6,i)),
   "price_new_low_6":int(low[i]<min(low[i-6:i])),
   "price_new_high_6":int(high[i]>max(high[i-6:i])),
   "bull_div_6":int(low[i]<min(low[i-6:i]) and hist[i]>min(hist[i-6:i])),
   "bear_div_6":int(high[i]>max(high[i-6:i]) and hist[i]<max(hist[i-6:i])),
   "macd_3bar_rising":int(hist[i]>hist[i-1]>hist[i-2]),
   "macd_3bar_falling":int(hist[i]<hist[i-1]<hist[i-2]),
   "hist_flip_3":int(any(hist[j]*hist[j-1]<0 for j in range(i-2,i+1)))
  }
  output[rows[i][0]+4*3600000]=d
 return output
def main():
 base=json.loads(Path("reports/btc_4h_bollinger_sigma_study.json").read_text())
 rows,_=data("BTCUSDT");f=features(rows);times=sorted(f)
 selected=[];skipped=[]
 for group,dest in ((base["selected_trades"],selected),):
  for x in group:
   i=bisect.bisect_right(times,x["time"])-1
   if i>=0 and times[i]==x["time"]:dest.append({**x,"extra":f[times[i]]})
 # Unselected from original prior study (identical time alignment)
 orig=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
 for x in orig["skipped_signals"]:
  i=bisect.bisect_right(times,x["time"])-1
  if i>=0 and times[i]==x["time"]:skipped.append({**x,"extra":f[times[i]]})
 keys=list(next(iter(f.values())).keys())
 tests=[]
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x for x in selected if x["side"]==side];b=[x for x in skipped if x["side"]==side]
  for key in keys:
   va=[x["extra"][key] for x in a];vb=[x["extra"][key] for x in b]
   binary=key in ("macd_hist_fading","macd_hist_growing","macd_bull_cross_3","macd_bear_cross_3","macd_hist_positive","price_new_low_6","price_new_high_6","bull_div_6","bear_div_6","macd_3bar_rising","macd_3bar_falling","hist_flip_3")
   if binary:
    yes_a=sum(va);yes_b=sum(vb);_,p=fisher_exact([[yes_a,len(va)-yes_a],[yes_b,len(vb)-yes_b]])
    effect={"selected_pct":round(100*yes_a/len(va),1),"skipped_pct":round(100*yes_b/len(vb),1)}
   else:
    _,p=mannwhitneyu(va,vb)
    effect={"selected_median":round(float(np.median(va)),5),"skipped_median":round(float(np.median(vb)),5)}
   tests.append({"side":label,"feature":key,"p":round(float(p),7),**effect})
 for t,q in zip(tests,bh([x["p"] for x in tests])):t["q_bh"]=q
 outcomes=[]
 for side,label in ((None,"ALL"),(1,"LONG"),(-1,"SHORT")):
  a=[x for x in selected if x.get("ret") is not None and (side is None or x["side"]==side)]
  for key in keys:
   if len(a)<8 or len(set(x["extra"][key] for x in a))<3:continue
   rho,p=spearmanr([x["extra"][key] for x in a],[x["ret"] for x in a])
   if math.isfinite(float(p)):outcomes.append({"side":label,"feature":key,"n":len(a),"rho":round(float(rho),4),"p":round(float(p),7)})
 for t,q in zip(outcomes,bh([x["p"] for x in outcomes])):t["q_bh"]=q
 # modest 4-feature incremental model vs 4H BB width and price range baseline
 models={}
 for side,label in ((1,"LONG"),(-1,"SHORT")):
  a=[x for x in selected if x["side"]==side];b=[x for x in skipped if x["side"]==side]
  samples=sorted([(x["time"],int(x in a),x) for x in a+b],key=lambda x:x[0])
  for variant,cols in (("baseline",["bb2_width_pct","range12_pct"]),("plus_macd",["bb2_width_pct","range12_pct","macd_hist_slope_atr","macd_hist_accel_atr"])):
   X=np.array([[z["features"].get(k) if k.startswith("bb") or k=="range12_pct" else z["extra"][k] for k in cols] for _,_,z in samples],dtype=float)
   y=np.array([lab for _,lab,_ in samples])
   # Missing range12_pct in BB report selected? selected has only BB features; derive range from original 1h report
   if not np.all(np.isfinite(X)):continue
   folds=[]
   for train,test in TimeSeriesSplit(n_splits=4).split(X):
    if len(set(y[train]))<2 or len(set(y[test]))<2:continue
    model=make_pipeline(StandardScaler(),LogisticRegression(C=.3,class_weight="balanced",max_iter=1000))
    model.fit(X[train],y[train]);auc=roc_auc_score(y[test],model.predict_proba(X[test])[:,1])
    folds.append({"n":len(test),"positives":int(y[test].sum()),"auc":round(float(auc),4)})
   models[label+"_"+variant]={"folds":folds,"mean_auc":round(float(np.mean([x["auc"] for x in folds])),4) if folds else None}
 out={"notes":"Exploratory BTC manual selection. MACD 11/27/22 matching user's indicator, classic 12/26/9 control, 4H closed bars. ATR used only as normalization, NOT stop. Divergence proxy compares new price extreme to six-bar histogram extrema, not a fully validated swing divergence. 4H signal time matched to manual entry within 4 hours. All features computed without future candles. Fisher/Mann Whitney and BH over feature tests; outcomes are small and post hoc. No volume data. Do not infer profitability from selection tests.","selected":len(selected),"skipped":len(skipped),"selection_tests":sorted(tests,key=lambda x:x["p"]),"outcome_tests":sorted(outcomes,key=lambda x:x["p"]),"models":models}
 Path("reports/btc_macd_momentum_statistical_study.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"selected":len(selected),"skipped":len(skipped),"top_selection":out["selection_tests"][:12],"top_outcomes":out["outcome_tests"][:10],"models":models},indent=2))
if __name__=="__main__":main()
