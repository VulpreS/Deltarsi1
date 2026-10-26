"""Multi-feature walk-forward research, cached OHLC only, no orders."""
import csv,datetime as dt,json,math,statistics
from pathlib import Path
from itertools import product
from analyze_mtf_5y import indicator,aggregate
from research_multiasset import atr,ema
from execution_core import resolve_bar
SYMS=["ETHUSDT","BTCUSDT","ICPUSDT","HYPEUSDT"];FEE=.0015
def data(sym):
 p=Path("data")/(sym+"_1h.csv")
 with p.open() as f: raw=list(csv.DictReader(f))
 r=[(int(dt.datetime.fromisoformat(x["timestamp_utc"]).timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]) for x in raw]
 rows=aggregate(r,4);ind=indicator(rows);a=atr(rows);cl=[x[4] for x in rows];e20=ema(cl,20);e50=ema(cl,50);e200=ema(cl,200)
 # Wilder ADX
 plus=minus=tr=0.;adx=20.;adxs=[]
 for i,x in enumerate(rows):
  if i:
   up=x[2]-rows[i-1][2];down=rows[i-1][3]-x[3]
   plus=(plus*13+(up if up>down and up>0 else 0))/14
   minus=(minus*13+(down if down>up and down>0 else 0))/14
   tr=(tr*13+max(x[2]-x[3],abs(x[2]-rows[i-1][4]),abs(x[3]-rows[i-1][4])))/14
   pd=100*plus/tr if tr else 0;md=100*minus/tr if tr else 0
   dx=100*abs(pd-md)/(pd+md) if pd+md else 0
   adx=(adx*13+dx)/14
  adxs.append(adx)
 features=[]
 for i in range(len(rows)):
  d=ind["delta"];c=ind["color"]
  if i<210 or not all(math.isfinite(d[j]) for j in (i,i-1,i-2)):features.append(None);continue
  side=1 if d[i]<0 else -1
  if d[i]*d[i-1]<=0:features.append(None);continue
  turn=abs(d[i])<abs(d[i-1]) and abs(d[i-1])>=abs(d[i-2]) and abs(d[i-1])>=15
  late=(c[i-1]=="mediumR" and c[i]=="weakR") if side==1 else (c[i-1]=="mediumB" and c[i]=="weakB")
  early=(c[i-1]=="strongR" and c[i]=="mediumR" and abs(d[i])<abs(d[i-1])) if side==1 else (c[i-1]=="strongB" and c[i]=="mediumB" and abs(d[i])<abs(d[i-1]))
  vol=a[i]/cl[i];recent=[a[j]/cl[j] for j in range(i-100,i)]
  vp=sum(v<vol for v in recent)/len(recent)
  mean=statistics.mean(cl[i-19:i+1]);std=statistics.pstdev(cl[i-19:i+1])
  z=(cl[i]-mean)/std if std else 0
  features.append(dict(side=side,turn=turn,late=late,early=early,trend50=side*(cl[i]-e50[i])>0,trend200=side*(cl[i]-e200[i])>0,trend20=side*(e20[i]-e50[i])>0,adx=adxs[i],vp=vp,z=z,rsi=ind["rsi"][i],atr=a[i]))
 return rows,features
def sim(rows,feats,cfg,lo,hi):
 mode,trend,regime,sl,tp,hold,direction=cfg
 eq=1.;peak=1.;dd=0.;trades=[];k=max(210,lo)
 while k<min(hi-1,len(rows)-2):
  f=feats[k]
  if not f or not f[mode] or (direction=="long" and f["side"]<0) or (direction=="short" and f["side"]>0):k+=1;continue
  if trend=="follow50" and not f["trend50"]:k+=1;continue
  if trend=="fade50" and f["trend50"]:k+=1;continue
  if trend=="follow200" and not f["trend200"]:k+=1;continue
  if trend=="rsi" and not (f["rsi"]<=40 if f["side"]==1 else f["rsi"]>=60):k+=1;continue
  if regime=="lowadx" and f["adx"]>=25:k+=1;continue
  if regime=="highadx" and f["adx"]<25:k+=1;continue
  if regime=="lowvol" and f["vp"]>=.5:k+=1;continue
  if regime=="highvol" and f["vp"]<.5:k+=1;continue
  if regime=="bbextreme" and not (f["z"]< -1 if f["side"]==1 else f["z"]>1):k+=1;continue
  entryi=k+1
  if entryi>=hi:break  # Entry must be inside the non-overlapping split.
  entry=rows[entryi][1];side=f["side"];stop=entry-side*sl*f["atr"];target=entry+side*tp*f["atr"]
  end=min(entryi+hold-1,hi-1,len(rows)-1);out=rows[end][4]
  for j in range(entryi,end+1):
   fill,reason=resolve_bar(rows[j],side,stop,target)
   if reason:
    out=fill;end=j;break
  ret=side*(out/entry-1)-FEE
  trades.append((k,ret,side));eq*=max(.001,1+ret);peak=max(peak,eq);dd=max(dd,1-eq/peak)
  k=end+1
 return trades,dd
def stats(x):
 ret=[v[1] for v in x]
 if not ret:return dict(n=0)
 p=sum(max(v,0) for v in ret);l=-sum(min(v,0) for v in ret)
 return dict(n=len(ret),win=round(100*sum(v>0 for v in ret)/len(ret),1),mean=round(100*statistics.mean(ret),3),pf=round(p/l,3) if l else None,compound=round(100*(math.prod(1+v for v in ret)-1),2))
def main():
 ds={s:data(s) for s in SYMS}
 # No resampling leak: each asset split into train, validation, holdout based on its own bars.
 splits={s:(int(len(d[0])*.5),int(len(d[0])*.75)) for s,d in ds.items()}
 configs=list(product(("turn","late","early"),("none","follow50","fade50","follow200","rsi"),("none","lowadx","highadx","lowvol","highvol","bbextreme"),(1.5,2.5),(2.,3.,4.),(6,12),("both","long","short")))
 # Stage 1: train must have >= 35 signals; stage 2: validation >= 15, profit factor >=1.15
 trainrank=[]
 for cfg in configs:
  t=[]
  for s,(rows,f) in ds.items():t.extend(sim(rows,f,cfg,0,splits[s][0])[0])
  m=stats(t)
  if m["n"]<35 or m["pf"] is None or m["pf"]<=1:continue
  trainrank.append((m["pf"],cfg,m))
 trainrank.sort(key=lambda x:x[0],reverse=True)
 valid=[]
 for pf,cfg,train in trainrank:
  t=[]
  for s,(rows,f) in ds.items():t.extend(sim(rows,f,cfg,*splits[s])[0])
  m=stats(t)
  if m["n"]<15 or m["pf"] is None:continue
  score=(min(train["pf"],2)-1)*.3+(min(m["pf"],2)-1)*.7
  valid.append((score,cfg,train,m))
 valid.sort(key=lambda x:x[0],reverse=True)
 # Freeze candidates BEFORE evaluating final 25%.
 chosen=valid[:5]
 baselines=[("turn","none","none",2.5,3.,12,"both"),("late","none","none",2.5,3.,12,"both")]
 evaluations=[]
 for _,cfg,train,val in chosen+[(0,cfg,None,None) for cfg in baselines]:
  per={};alltr=[]
  for s,(rows,f) in ds.items():
   t,dd=sim(rows,f,cfg,splits[s][1],len(rows))
   per[s]={"stats":stats(t),"max_drawdown_full_notional_pct":round(100*dd,2)}
   alltr.extend(t)
  evaluations.append({"config":cfg,"train":train,"validation":val,"final_holdout":stats(alltr),"by_asset":per})
 output={"notes":"OHLC only; volume is NOT present for all symbols and not used. Four-hour candles aggregated from cached 1h. Indicators on completed bars. Stop wins when both touched. 0.15% round-trip fees+slippage, funding excluded. Separate 50/25/25 chronological per-symbol split; HYPE shorter. Best candidates frozen using train+validation before final holdout. Selection of model after seeing final results invalidates its independence.","candidates_searched":len(configs),"training_qualified":len(trainrank),"validation_qualified":len(valid),"evaluations":evaluations}
 Path("reports/feature_walkforward.json").write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print(json.dumps(output,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
