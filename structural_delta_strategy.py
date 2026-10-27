"""Structural DeltaRSI strategy, no ATR: 4H color entries/exits and confirmed price swing stops.
No funding; fixed 0.15% roundtrip fee. Independent chronological partitions.
"""
import json,statistics
from pathlib import Path
from feature_walkforward import data
from analyze_mtf_5y import indicator
from execution_core import resolve_bar
FEE=.0015
def stat(t):
 if not t:return {"n":0}
 v=[z["ret"] for z in t];p=sum(max(x,0) for x in v);l=-sum(min(x,0) for x in v)
 eq=peak=1.;dd=0
 for x in v:eq*=max(.001,1+x);peak=max(peak,eq);dd=max(dd,1-eq/peak)
 return {"n":len(v),"wr_pct":round(100*sum(x>0 for x in v)/len(v),1),"mean_net_pct":round(100*statistics.mean(v),3),"pf":round(p/l,3) if l else None,"mdd_pct":round(100*dd,2)}
def swing(rows,k,side,left,right,lookback):
 # Pivot at j is confirmed only if j+right <= k; compare with neighbors in [j-left,j+right].
 for j in range(k-right,k-lookback-1,-1):
  if j-left<0:break
  v=rows[j][3] if side==1 else rows[j][2]
  neighbors=rows[j-left:j]+rows[j+1:j+right+1]
  if all(v<z[3] for z in neighbors) if side==1 else all(v>z[2] for z in neighbors):
   return v,j
 return None,None
def run(rows,colors,lo,hi,cfg,save=False):
 left,right,lookback,buffer,exitmode,filtermode=cfg
 t=[];k=max(210,lo)
 while k<hi-2:
  p,c=colors[k-1],colors[k]
  side=1 if p=="mediumR" and c=="weakR" else -1 if p=="mediumB" and c=="weakB" else 0
  if not side:k+=1;continue
  if filtermode!="none":
   width=100*(max(x[2] for x in rows[k-11:k+1])-min(x[3] for x in rows[k-11:k+1]))/rows[k][4]
   fall=100*(rows[k][4]/rows[k-12][4]-1)
   if side==1 and not(width>=5 and fall<=-1):k+=1;continue
   if side==-1 and not(width<=5):k+=1;continue
  pivot,j=swing(rows,k,side,left,right,lookback)
  if pivot is None:k+=1;continue
  entryi=k+1;entry=rows[entryi][1];stop=pivot*(1-buffer if side==1 else 1+buffer)
  risk=side*(entry-stop)
  if risk<=0 or risk/entry>.15:k+=1;continue
  ex=min(entryi+120-1,hi-1,len(rows)-1);fill=rows[ex][4];why="timeout"
  for z in range(entryi,ex+1):
   bar=rows[z]
   touched=(bar[3]<=stop if side==1 else bar[2]>=stop)
   if touched:fill=stop;ex=z;why="stop";break
   if exitmode=="signal" and z+1<hi and z+1<len(rows):
    q,now=colors[z-1],colors[z]
    opposite=(now=="weakB" and q in ("mediumB","strongB")) if side==1 else (q=="mediumR" and now=="weakR")
    if opposite:fill=rows[z+1][1];ex=z+1;why="signal";break
  record={"entry_index":entryi,"exit_index":ex,"side":"LONG" if side==1 else "SHORT","entry":entry,"stop":stop,"exit":fill,"reason":why,"ret":side*(fill/entry-1)-FEE,"pivot_age_bars":k-j}
  t.append(record);k=ex+1
 return t
def main():
 syms=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
 ds={}
 for s in syms:
  rows,_=data(s);ds[s]=(rows,indicator(rows)["color"])
 cuts={s:(len(x[0])//2,len(x[0])*3//4) for s,x in ds.items()}
 configs=[(l,r,lb,b,e,f) for l,r,lb,b,e,f in __import__("itertools").product((2,3),(1,2),(12,24,48),(.001,.002),("signal",),("none","price_context"))]
 def evalpart(s,cfg,part):
  rows,colors=ds[s];x,y=cuts[s];lo,hi=((0,x),(x,y),(y,len(rows)))[part]
  return run(rows,colors,lo,hi,cfg)
 ranks=[]
 for cfg in configs:
  tr=[];val=[]
  for s in syms:
   tr+=evalpart(s,cfg,0);val+=evalpart(s,cfg,1)
  a=stat(tr);b=stat(val)
  if a["n"]>=30 and b["n"]>=15 and a["mean_net_pct"]>0 and b["mean_net_pct"]>0:
   ranks.append((.3*a["mean_net_pct"]+.7*b["mean_net_pct"],cfg,a,b))
 ranks.sort(reverse=True)
 baseline=(2,1,24,.001,"signal","none")
 filtered=(2,1,24,.001,"signal","price_context")
 chosen=[(x[1],x[2],x[3]) for x in ranks[:5]]
 for cfg in (baseline,filtered):
  if not any(x[0]==cfg for x in chosen):
   a=stat(sum((evalpart(s,cfg,0) for s in syms),[]))
   b=stat(sum((evalpart(s,cfg,1) for s in syms),[]))
   chosen.append((cfg,a,b))
 results=[]
 for cfg,a,b in chosen:
  by={};alltr=[]
  for s in syms:
   t=evalpart(s,cfg,2);by[s]=stat(t);alltr+=t
  results.append({"config":{"pivot_left":cfg[0],"pivot_confirmation_right":cfg[1],"pivot_lookback_4h":cfg[2],"stop_buffer_fraction":cfg[3],"exit":cfg[4],"price_filter":cfg[5]},"train":a,"validation":b,"holdout":stat(alltr),"holdout_by_asset":by})
 # Additional full-period per asset baseline diagnostics, clearly not independent.
 full={}
 for s,(rows,colors) in ds.items():
  t=run(rows,colors,0,len(rows),baseline)
  full[s]={"stats":stat(t),"trades":t}
 out={"notes":"Mechanical strategy on fully closed 4H candles, entry next 4H open. LONG mediumR->weakR, SHORT mediumB->weakB. Stop beyond most recent CONFIRMED price pivot (left 2/3, right 1/2) plus 0.1%/0.2% buffer; no ATR, no TP. Opposite DeltaRSI weak color closes at next 4H open. Max holding 120 4H bars is a data safety limit, not trader rule. 0.15% roundtrip costs, no funding. Conservative stop check before signal exit on each bar. Strict 50/25/25 per-asset split; positions forcibly end at split boundary (limitation). 48 configurations chosen on train+validation; holdout not used to select. This does NOT yet use forming 4H 1H snapshots or partial manual exits. Results do not establish true OOS on BTC since rules were inferred from BTC journal.","tested_configs":len(configs),"qualified":len(ranks),"selected_results":results,"full_history_baseline":full}
 Path("reports/structural_delta_strategy.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"tested":len(configs),"qualified":len(ranks),"selected":results,"full_baseline":{s:x["stats"] for s,x in full.items()}},indent=2))
if __name__=="__main__":main()
