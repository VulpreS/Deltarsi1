"""Research ML: direction and exit rules from 4h DeltaRSI. No 48h cap.
Labels use first future opposite Delta color transition, capped ONLY by dataset boundary;
train samples whose outcome crosses 2026-08-01 are purged. Final 3 months untouched.
"""
import json, pathlib, datetime as dt, math
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score,accuracy_score
ROOT=pathlib.Path("experiments/delta_ml_3y")
CUT=int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()*1000)
END=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
def rma(x,n):return x.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
def features(rows,sym):
 d=pd.DataFrame(rows,columns=["t","open","high","low","close","volume"])
 c=d.close;delta=c.diff();up=rma(delta.clip(lower=0),27);down=rma((-delta).clip(lower=0),27)
 rs=up/down.replace(0,np.nan);rsi=100-100/(1+rs)
 sig=rsi.ewm(span=7,adjust=False,min_periods=7).mean();dr=rsi-sig
 tr=pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1)
 atr=rma(tr,14)
 d["dr"]=dr;d["rsi"]=rsi;d["atr"]=atr
 for k in [1,2,3,4,6,12]:
  d[f"dr_lag{k}"]=dr.shift(k);d[f"dr_velocity{k}"]=dr-dr.shift(k)
  d[f"return{k}"]=c.pct_change(k)
 d["dr_accel"]=dr-2*dr.shift(1)+dr.shift(2)
 d["atr_pct"]=atr/c
 d["range_pct"]=(d.high-d.low)/c
 d["upper_wick"]=(d.high-d[["open","close"]].max(axis=1))/c
 d["lower_wick"]=(d[["open","close"]].min(axis=1)-d.low)/c
 d["body"]=(d.close-d.open)/c
 d["vol_ratio"]=d.volume/d.volume.rolling(30).mean()
 d["ema50_dist"]=c/c.ewm(span=50,adjust=False).mean()-1
 d["ema200_dist"]=c/c.ewm(span=200,adjust=False).mean()-1
 d["asset"]=sym
 return d
def events(d):
 # Medium->weak transition via causal relative delta magnitudes, not yet certified TradingView color parity.
 x=d.dr.to_numpy();out=[]
 for i in range(210,len(d)-1):
  a,b=x[i-1],x[i]
  if not(np.isfinite(a) and np.isfinite(b)):continue
  if a<0 and b<0 and abs(b)<abs(a)*.7:out.append((i,1))
  if a>0 and b>0 and abs(b)<abs(a)*.7:out.append((i,-1))
 return out
def build():
 all_rows=[];last={}
 for f in sorted((ROOT/"data").glob("*.json")):
  d=features(json.loads(f.read_text()),f.stem);ev=events(d)
  for j,(i,side) in enumerate(ev):
   future=next((k for k,s in ev[j+1:] if s==-side),None)
   if future is None:continue
   start=int(d.t.iloc[i])+4*3600000;finish=int(d.t.iloc[future])+4*3600000
   if start>=END or (start<CUT and finish>=CUT):continue
   entry=float(d.open.iloc[i+1]);exit=float(d.open.iloc[future+1])
   net=side*(exit/entry-1)-.0016
   rec=d.iloc[i].to_dict();rec.update(start=start,finish=finish,side=side,net=net,win=int(net>0),hold_hours=(finish-start)/3600000)
   all_rows.append(rec)
  last[f.stem]=dict(candles=len(d),events=len(ev))
 if not all_rows:raise RuntimeError("No labelled events")
 return pd.DataFrame(all_rows),last
def main():
 df,counts=build()
 excluded={"t","open","high","low","close","volume","asset","start","finish","side","net","win","hold_hours"}
 cols=[c for c in df if c not in excluded and pd.api.types.is_numeric_dtype(df[c])]
 df[cols]=df[cols].replace([np.inf,-np.inf],np.nan)
 train=df[df.start<CUT].copy();test=df[df.start>=CUT].copy()
 if len(train)<100 or len(test)<10:raise RuntimeError(f"Insufficient train/test events {len(train)}/{len(test)}")
 # Temporal internal validation, never use final holdout for parameter choice.
 split=train.start.quantile(.8);tr=train[train.start<split];val=train[train.start>=split]
 model=XGBClassifier(n_estimators=180,max_depth=3,learning_rate=.035,subsample=.8,colsample_bytree=.8,objective="binary:logistic",eval_metric="logloss",random_state=42,n_jobs=2)
 model.fit(tr[cols],tr.win)
 def metrics(part):
  p=model.predict_proba(part[cols])[:,1];keep=p>=.6
  return dict(n=len(part),base_win_rate=float(part.win.mean()),auc=float(roc_auc_score(part.win,p)) if part.win.nunique()>1 else None,selected=int(keep.sum()),selected_win_rate=float(part.win.to_numpy()[keep].mean()) if keep.sum() else None,selected_mean_net_pct=float(part.net.to_numpy()[keep].mean()*100) if keep.sum() else None)
 ranking=sorted(zip(cols,model.feature_importances_.tolist()),key=lambda z:z[1],reverse=True)
 # Exit descriptions: empirical distributions, not future-known exit instructions.
 report=dict(caveats=["PROXY event colors based on 30% delta weakening, not verified exact Pine colors","Exit label is NEXT OPPOSITE signal, not ML-optimized exit","No fixed 48h horizon; boundary-crossing training labels purged","No intrabar stop or prop replay; final 3 months held out"],symbols=counts,train=metrics(tr),validation=metrics(val),test=metrics(test),top_features=ranking[:20],exit_hold_hours=dict(median=float(train.hold_hours.median()),p25=float(train.hold_hours.quantile(.25)),p75=float(train.hold_hours.quantile(.75))),counts=dict(train=len(train),test=len(test)))
 out=ROOT/"report.json";out.write_text(json.dumps(report,indent=2,ensure_ascii=False));print("ML_REPORT",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
