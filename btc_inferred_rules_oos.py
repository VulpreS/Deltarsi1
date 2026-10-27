"""Out-of-sample tests of hypotheses from actual-vs-skipped BTC signals.
All inputs as-of last closed 4H bar; next open entry; stop-first.
"""
import json,statistics
from pathlib import Path
from feature_walkforward import data
from analyze_mtf_5y import indicator
from research_multiasset import atr
from execution_core import resolve_bar
FEE=.0015
def stat(x):
 if not x:return {"n":0}
 v=[t[1] for t in x];p=sum(max(z,0) for z in v);l=-sum(min(z,0) for z in v)
 eq=1.;peak=1.;dd=0.
 for z in v:
  eq*=max(.001,1+z);peak=max(peak,eq);dd=max(dd,1-eq/peak)
 return {"n":len(v),"wr":round(100*sum(z>0 for z in v)/len(v),1),"mean_net_pct":round(100*statistics.mean(v),3),"pf":round(p/l,3) if l else None,"mdd_pct":round(100*dd,2)}
def features(r,a,i):
 f=[None]*len(r)
 for k in range(210,len(r)):
  c=r[k][4];last=r[k-11:k+1];old=r[k-23:k+1]
  f[k]={"range12":100*(max(z[2] for z in last)-min(z[3] for z in last))/c,
        "range24":100*(max(z[2] for z in old)-min(z[3] for z in old))/c,
        "atrpct":100*a[k]/c,
        "bb":400*statistics.pstdev([z[4] for z in r[k-19:k+1]])/statistics.mean([z[4] for z in r[k-19:k+1]]),
        "prior48":100*(c/r[k-12][4]-1),
        "prior12":100*(c/r[k-3][4]-1)}
 return f
def eligible(f,side,rule):
 if rule=="baseline":return True
 if side==1:
  if rule=="long_range":return f["range12"]>=5
  if rule=="long_bb":return f["bb"]>=6
  if rule=="long_fall":return f["prior48"]<=-1.5
  if rule=="long_joint":return f["range12"]>=5 and f["prior48"]<=-1
  if rule=="long_atr":return f["atrpct"]>=1.4
  return False
 if rule=="short_weak":return f["prior12"]<=0 and f["range12"]<=5
 if rule=="short_range":return f["range12"]<=4
 if rule=="short_atr":return f["atrpct"]<=1.2
 if rule=="short_fall":return f["prior12"]<=-.4
 if rule=="short_joint":return f["range12"]<=4 and f["prior12"]<=0
 return False
def sim(r,i,a,f,lo,hi,sidewanted,rule,exitmethod):
 out=[];k=max(lo,210)
 while k<min(hi-2,len(r)-2):
  p,c=i["color"][k-1],i["color"][k]
  side=1 if p=="mediumR" and c=="weakR" else -1 if p=="mediumB" and c=="weakB" else 0
  if side!=sidewanted or not eligible(f[k],side,rule):k+=1;continue
  ei=k+1;entry=r[ei][1];stop=entry-side*2*a[k];risk=abs(entry-stop);target=entry+side*3*risk
  end=min(ei+23,hi-1,len(r)-1);fill=r[end][4];ex=end
  for j in range(ei,end+1):
   z,why=resolve_bar(r[j],side,stop,target)
   if why:fill=z;ex=j;break
   if exitmethod=="opposite" and j+1<hi:
    q,b=i["color"][j-1],i["color"][j]
    opposite=(q=="mediumB" and b=="weakB") if side==1 else (q=="mediumR" and b=="weakR")
    if opposite:fill=r[j+1][1];ex=j+1;break
  out.append((k,side*(fill/entry-1)-FEE));k=ex+1
 return out
def main():
 syms=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
 ds={}
 for s in syms:
  r,_=data(s);i=indicator(r);a=atr(r);ds[s]=(r,i,a,features(r,a,i))
 cuts={s:(len(x[0])//2,len(x[0])*3//4) for s,x in ds.items()}
 def evaluate(s,side,rule,exitmethod,part):
  r,i,a,f=ds[s];x,y=cuts[s];lo,hi=((0,x),(x,y),(y,len(r)))[part]
  return sim(r,i,a,f,lo,hi,side,rule,exitmethod)
 configs=[]
 for side,rules in ((1,("baseline","long_range","long_bb","long_fall","long_joint","long_atr")),(-1,("baseline","short_weak","short_range","short_atr","short_fall","short_joint"))):
  for rule in rules:
   for exitmethod in ("opposite","timeout"):
    configs.append((side,rule,exitmethod))
 results=[]
 # Selection only BTC train + validation; independent assets reported as transfer tests.
 for cfg in configs:
  side,rule,ex=cfg
  train=stat(evaluate("BTCUSDT",side,rule,ex,0));val=stat(evaluate("BTCUSDT",side,rule,ex,1))
  hold=stat(evaluate("BTCUSDT",side,rule,ex,2))
  transfer={s:stat(evaluate(s,side,rule,ex,2)) for s in syms if s!="BTCUSDT"}
  results.append({"side":"LONG" if side==1 else "SHORT","filter":rule,"exit":ex,"btc_train":train,"btc_validation":val,"btc_holdout":hold,"other_asset_holdouts":transfer})
 # Rank without looking at holdout: positive mean both periods, >= 4 validation and >= 8 training.
 qualified=[x for x in results if x["btc_train"]["n"]>=8 and x["btc_validation"]["n"]>=4 and x["btc_train"].get("mean_net_pct",0)>0 and x["btc_validation"].get("mean_net_pct",0)>0]
 qualified.sort(key=lambda x:(x["btc_validation"]["mean_net_pct"]+x["btc_train"]["mean_net_pct"])/2,reverse=True)
 out={"notes":"24 prespecified candidate configurations: LONG and SHORT independently, fixed 2ATR stop, 3R target, 24*4H max hold, opposite signal exit alternative. 0.15% roundtrip fee, no funding. Chronological 50/25/25 per asset, closed 4H signals and next open fills, stop first. BTC hypotheses were informed by all BTC real trades and therefore BTC holdout is NOT truly untouched. Other assets are exploratory transfer tests, not manual trade replication. No leverage. No simultaneous positions per direction per asset; directions tested separately.","qualified_btc_train_validation":len(qualified),"ranked_qualified":qualified,"all_results":results}
 Path("reports/btc_inferred_rules_oos.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"qualified":len(qualified),"ranked":qualified[:6],"all_btc":[{k:v for k,v in x.items() if k!="other_asset_holdouts"} for x in results]},indent=2))
if __name__=="__main__":main()
