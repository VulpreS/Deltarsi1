"""Out-of-sample joint-feature study: 4H BB width, MACD fading and 1H volume.
Chronological expanding splits, base-rate-aware top-decile precision, train-only scaling.
"""
import json,bisect,math
from pathlib import Path
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score
from btc_price_action_bb_volume_study import read
from btc_linear_close_volume_study import volume_fetch,feature as linear_features
from btc_macd_momentum_statistical_study import features as macd_features
from feature_walkforward import data
H=3600000
def main():
 raw=read();times=[x[0] for x in raw];vol,errors=volume_fetch(raw)
 rows,_=data("BTCUSDT");macd=macd_features(rows)
 bb=json.loads(Path("reports/btc_4h_bollinger_sigma_study.json").read_text())
 prior=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
 chosen={(x["time"],x["side"]):x for x in bb["selected_trades"]}
 from btc_4h_bollinger_sigma_study import features as bb_features
 fourtimes=[x[0]+4*H for x in rows];fouridx={t:i for i,t in enumerate(fourtimes)}
 items=[]
 for s in prior["matched_trades"]+prior["skipped_signals"]:
  t=s.get("signal_time",s.get("time"));side=s["side"];is_selected=int("manual_time" in s)
  j=fouridx.get(t)
  i=bisect.bisect_left(times,t)-1
  if j is None or i<50 or raw[i][0]+H!=t or t not in macd:continue
  b=bb_features(rows,j,side);l=linear_features(raw,i,vol);m=macd[t]
  if not b or not l:continue
  x={"bb_width":b["bb2_width_pct"],"bb_directional_touch_3":b["bb2_directional_touch_3"],
     "macd_fading":m["macd_hist_fading"],"macd_slope":m["macd_hist_slope_atr"],
     "macd_accel":m["macd_hist_accel_atr"],"atr_pct":m["atr_pct"],
     "close_efficiency":l["close_efficiency_12h"],"close_range":l["close_range_12h_pct"],
     "volume_ratio":l["volume_ratio_20"],"volume_4h_ratio":l["volume_4h_ratio_20"],
     "volume_falling":l["volume_falling_6h"]}
  items.append({"time":t,"side":side,"selected":is_selected,"features":x})
 items.sort(key=lambda z:z["time"])
 # Compare same rows per side, common sample with actual volume; no imputation.
 modelsets={"bb_only":["bb_width"],"bb_macd":["bb_width","macd_fading","macd_slope"],
 "bb_macd_volume":["bb_width","macd_fading","macd_slope","volume_ratio"],
 "all_context":["bb_width","bb_directional_touch_3","macd_fading","macd_slope","atr_pct","close_efficiency","volume_ratio"]}
 out={"notes":"Exploratory, not a strategy backtest. BTC completed 4H DeltaRSI signals matched to 26 manual trades within 4h; 1H Binance USDT-M volume proxy (not Bybit). 4H BB20 2σ, MACD 11/27/22, 1H closes. Only strictly completed candles. Common complete-case volume subset across models. Expanding chronological TimeSeriesSplit; tiny positives and serial dependence make results unstable. Top-decile precision is based on each test fold; AUC/AP only if test has both classes. No hyperparameter tuning on test; no probability calibration; comparisons are exploratory.","volume_hours":len(vol),"volume_errors":errors,"models":{},"counts":{}}
 for side,name in ((1,"LONG"),(-1,"SHORT")):
  samples=[z for z in items if z["side"]==side and all(z["features"][k] is not None and math.isfinite(float(z["features"][k])) for k in modelsets["all_context"])]
  y=np.array([z["selected"] for z in samples]);out["counts"][name]={"n":len(samples),"selected":int(sum(y)),"base_rate":round(float(np.mean(y)),4) if len(y) else None}
  if len(samples)<50:continue
  splits=list(TimeSeriesSplit(n_splits=4).split(y))
  for modelname,keys in modelsets.items():
   X=np.array([[z["features"][k] for k in keys] for z in samples],float)
   folds=[]
   for train,test in splits:
    if len(set(y[train]))<2 or len(set(y[test]))<2:continue
    clf=make_pipeline(StandardScaler(),LogisticRegression(C=.3,class_weight="balanced",max_iter=2000))
    clf.fit(X[train],y[train]);p=clf.predict_proba(X[test])[:,1]
    top=max(1,round(len(test)*.1));chosen=np.argsort(p)[-top:]
    folds.append({"train_n":len(train),"test_n":len(test),"test_positives":int(y[test].sum()),
                  "auc":round(float(roc_auc_score(y[test],p)),4),
                  "average_precision":round(float(average_precision_score(y[test],p)),4),
                  "precision_top_10pct":round(float(np.mean(y[test][chosen])),4),
                  "base_rate":round(float(np.mean(y[test])),4)})
   out["models"][name+"_"+modelname]={"features":keys,"folds":folds,"mean_auc":round(float(np.mean([f["auc"] for f in folds])),4) if folds else None,
    "mean_ap":round(float(np.mean([f["average_precision"] for f in folds])),4) if folds else None,
    "mean_precision_top_10pct":round(float(np.mean([f["precision_top_10pct"] for f in folds])),4) if folds else None}
 Path("reports/btc_joint_bb_macd_volume_oos.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"counts":out["counts"],"models":{k:{"auc":v["mean_auc"],"ap":v["mean_ap"],"top10":v["mean_precision_top_10pct"],"folds":v["folds"]} for k,v in out["models"].items()}},indent=2))
if __name__=="__main__":main()
