"""Test explicit user-derived DeltaRSI + visual price-range filters on cached 4H OHLC."""
import json,math,statistics
from pathlib import Path
from feature_walkforward import data,FEE
from analyze_mtf_5y import indicator
from execution_core import resolve_bar
from research_multiasset import atr
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
def metric(t):
 if not t:return {"n":0}
 v=[x[1] for x in t];p=sum(max(x,0) for x in v);loss=-sum(min(x,0) for x in v)
 eq=1.;peak=1.;dd=0
 for x in v:
  eq*=1+x;peak=max(peak,eq);dd=max(dd,1-eq/peak)
 return {"n":len(v),"wr":round(100*sum(x>0 for x in v)/len(v),1),"avg_pct":round(100*statistics.mean(v),3),"pf":round(p/loss,3) if loss else None,"mdd_pct":round(100*dd,2)}
def test(rows,ind,atrv,lo,hi,rule,sidefilter,stopmode,exitmode):
 colors=ind["color"];tr=[];k=max(210,lo)
 while k<hi-2:
  prev,cur=colors[k-1],colors[k]
  side=1 if prev=="mediumR" and cur=="weakR" else (-1 if cur=="weakB" and prev!="weakB" else 0)
  if not side or (sidefilter and side!=sidefilter):k+=1;continue
  if rule!="none":
   n=12 if "12" in rule else 24
   width=(max(x[2] for x in rows[k-n+1:k+1])-min(x[3] for x in rows[k-n+1:k+1]))/rows[k][4]
   if rule.startswith("range") and width<float(rule.split("_")[-1]):k+=1;continue
   if rule.startswith("atr"):
    recent=[atrv[j]/rows[j][4] for j in range(k-100,k)]
    rank=sum(z<atrv[k]/rows[k][4] for z in recent)/len(recent)
    if rank<float(rule.split("_")[-1]):k+=1;continue
  ei=k+1;entry=rows[ei][1];a=atrv[k]
  if stopmode=="2atr":stop=entry-side*2*a
  else:
   segment=rows[max(0,k-11):k+1]
   stop=(min(x[3] for x in segment) if side==1 else max(x[2] for x in segment))-side*.05*a
  risk=side*(entry-stop)
  if risk<=0 or risk/entry>.12:k+=1;continue
  end=min(ei+24-1,hi-1,len(rows)-1);out=rows[end][4];ex=end
  # stop always active; opposite color transition exits next bar open (if inside split)
  for j in range(ei,end+1):
   fill,reason=resolve_bar(rows[j],side,stop,entry+side*3*risk)
   if reason:out=fill;ex=j;break
   if exitmode=="opposite" and j+1<hi and j+1<len(rows):
    c=colors[j]
    opposite=(c=="weakB" and colors[j-1]!="weakB") if side==1 else (colors[j-1]=="mediumR" and c=="weakR")
    if opposite:out=rows[j+1][1];ex=j+1;break
  ret=side*(out/entry-1)-FEE;tr.append((k,ret,side));k=ex+1
 return tr
def main():
 rules=["none","range12_0.025","range12_0.05","range12_0.075","range24_0.05","range24_0.08","range24_0.12","atr_0.5","atr_0.7"]
 configs=[(r,s,st,ex) for r in rules for s in (0,1,-1) for st in ("2atr","swing12") for ex in ("opposite","time")]
 ds={}
 for sym in SYMS:
  rows,_=data(sym,aggregation="strict");ds[sym]=(rows,indicator(rows),atr(rows))
 cuts={s:(len(d[0])//2,len(d[0])*3//4) for s,d in ds.items()}
 def evalcfg(cfg,segment):
  r,s,st,ex=cfg;by={};alltr=[]
  for sym,(rows,ind,a) in ds.items():
   c=cuts[sym];lo,hi=((0,c[0]),(c[0],c[1]),(c[1],len(rows)))[segment]
   t=test(rows,ind,a,lo,hi,r,s,st,ex);by[sym]=metric(t);alltr+=t
  return metric(alltr),by
 ranked=[]
 for cfg in configs:
  train,_=evalcfg(cfg,0)
  if train["n"]<25 or train.get("pf") is None or train["pf"]<=1:continue
  val,_=evalcfg(cfg,1)
  if val["n"]<12 or val.get("pf") is None:continue
  score=min(train["pf"],3)*.3+min(val["pf"],3)*.7
  ranked.append((score,cfg,train,val))
 ranked.sort(reverse=True,key=lambda x:x[0])
 selected=ranked[:8]
 baseline=[("none",0,"2atr","time"),("none",0,"2atr","opposite"),("range12_0.05",0,"2atr","opposite")]
 result=[]
 for _,cfg,train,val in selected+[(0,c,None,None) for c in baseline]:
  hold,by=evalcfg(cfg,2)
  result.append({"rule":cfg,"train":train,"validation":val,"holdout":hold,"holdout_by_asset":by})
 out={"method":"Closed 4H DeltaRSI. LONG mediumR->weakR, SHORT newly weakB. Price range high-low / current close on last 12 or 24 completed 4H bars, thresholds 2.5%-12%; 4H ATR rank as comparison. Next 4H open fills. 3R TP, 2 ATR or prior 12-bar swing stop, stop-first, opposite signal or 24-bar timeout. 0.15% roundtrip cost, no funding. 50/25/25 per-asset chronological splits. Best 8 selected train+validation only; last 25% holdout. Note BTC trade journal already seen so this is not genuinely untouched research.","candidate_count":len(configs),"qualified":len(ranked),"results":result}
 Path("reports/price_range_rule_backtest.json").write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2),flush=True)
if __name__=="__main__":main()
