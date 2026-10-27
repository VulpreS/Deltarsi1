"""Predeclared daily context gates for 4H DeltaRSI strategy; strict chronological holdout.
No optimized thresholds; compare same structural-stop/invalidation strategy with daily context.
"""
import json,statistics
from pathlib import Path
from feature_walkforward import data
from analyze_mtf_5y import indicator
from structural_delta_strategy import swing,stat,FEE
DAY=86400000
def daily_features(rows):
 groups={}
 for i,r in enumerate(rows):
  d=r[0]//DAY*DAY
  groups.setdefault(d,[]).append(r)
 ds=[]
 for d,rs in sorted(groups.items()):
  # 4H candles, six contiguous bars for UTC day
  if len(rs)!=6 or rs[0][0]!=d or rs[-1][0]!=d+20*3600000:continue
  ds.append((d,rs[0][1],max(x[2] for x in rs),min(x[3] for x in rs),rs[-1][4]))
 result={}
 for i in range(50,len(ds)):
  d,o,h,l,c=ds[i];prev=ds[i-1];cl=[x[4] for x in ds[:i+1]]
  sma50=statistics.mean(cl[-50:]);sma20=statistics.mean(cl[-20:])
  result[d+DAY]={"ret3":100*(c/ds[i-3][4]-1),"ret10":100*(c/ds[i-10][4]-1),"sma50":100*(c/sma50-1),"sma20":100*(c/sma20-1),"prev_bear":c<o,"upper_wick":(h-max(o,c))/max(h-l,1e-9),"range5":100*(max(x[2] for x in ds[i-4:i+1])-min(x[3] for x in ds[i-4:i+1]))/c}
 return result
def run(rows,colors,lo,hi,mode,context):
 t=[];k=max(lo,210)
 keys=sorted(context)
 import bisect
 while k<hi-2:
  p,c=colors[k-1],colors[k]
  side=1 if p=="mediumR" and c=="weakR" else -1 if p=="mediumB" and c=="weakB" else 0
  if not side:k+=1;continue
  at=rows[k][0]+4*3600000
  pos=bisect.bisect_right(keys,at)-1
  daily=context[keys[pos]] if pos>=0 else None
  if mode!="none":
   if daily is None:k+=1;continue
   # All values are broad predeclared directional gates, not optimized.
   if mode=="trend":
    eligible=(daily["ret3"]<0 and daily["sma50"]<0) if side==1 else (daily["ret10"]>0 and daily["sma50"]>0)
   elif mode=="stretch":
    eligible=(daily["ret3"]<=-2 and daily["sma50"]<=-3) if side==1 else (daily["ret10"]>=2 and daily["sma50"]>=0)
   elif mode=="candles":
    eligible=(daily["ret3"]<0 and daily["prev_bear"]) if side==1 else (daily["ret10"]>0 and daily["upper_wick"]>=.4)
   elif mode=="daily_or":
    eligible=(daily["ret3"]<=-2 or daily["sma50"]<=-3) if side==1 else (daily["ret10"]>=2 or daily["upper_wick"]>=.4)
   else:raise ValueError(mode)
   if not eligible:k+=1;continue
  pivot,j=swing(rows,k,side,2,2,12)
  if pivot is None:k+=1;continue
  ei=k+1;entry=rows[ei][1];stop=pivot*(.999 if side==1 else 1.001)
  if side*(entry-stop)<=0 or abs(entry-stop)/entry>.15:k+=1;continue
  end=min(ei+119,hi-1,len(rows)-1);price=rows[end][4];why="safety_timeout";ex=end
  for z in range(ei,end+1):
   if (rows[z][3]<=stop if side==1 else rows[z][2]>=stop):
    price=stop;why="stop";ex=z;break
   if z+1>=hi or z+1>=len(rows):continue
   a,b=colors[z-1],colors[z]
   invalid=(b in ("mediumR","strongR") and a=="weakR") if side==1 else (b in ("mediumB","strongB") and a=="weakB")
   opposite=(b=="weakB" and a in ("mediumB","strongB")) if side==1 else (b=="weakR" and a in ("mediumR","strongR"))
   if invalid or opposite:
    price=rows[z+1][1];why="invalidation" if invalid else "opposite";ex=z+1;break
  t.append({"entry_i":ei,"exit_i":ex,"side":"LONG" if side==1 else "SHORT","reason":why,"ret":side*(price/entry-1)-FEE})
  k=ex+1
 return t
def main():
 modes=("none","trend","stretch","candles","daily_or")
 out={"notes":"4H fully closed DeltaRSI entry, next open. Daily context computed ONLY from completed UTC days, 50-day SMA warmup. Structural confirmed pivot stop; original impulse rebrightening exits; opposite fade exits. 0.15% roundtrip, no funding. Fixed four daily filters motivated by journal, no optimization on test. Each asset's last 25% is evaluation; hypotheses were informed by BTC manual journal, so BTC is not pristine unseen OOS. Split positions forced closed at boundary. Daily filter is evaluated at entry signal time. Results are descriptive.","assets":{},"pooled":{}}
 for s in ("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT"):
  rows,_=data(s);colors=indicator(rows)["color"];context=daily_features(rows);cut=len(rows)*3//4
  out["assets"][s]={}
  for mode in modes:
   trades=run(rows,colors,cut,len(rows),mode,context)
   out["assets"][s][mode]={"stats":stat(trades),"long":stat([x for x in trades if x["side"]=="LONG"]),"short":stat([x for x in trades if x["side"]=="SHORT"]),"trades":trades}
 for mode in modes:
  alltr=[t for a in out["assets"].values() for t in a[mode]["trades"]]
  out["pooled"][mode]=stat(alltr)
 Path("reports/daily_context_strategy_test.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"pooled":out["pooled"],"assets":{s:{m:v["stats"] for m,v in a.items()} for s,a in out["assets"].items()}},indent=2))
if __name__=="__main__":main()
