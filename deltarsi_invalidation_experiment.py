"""Test trader's hypothesis invalidation: original impulse re-brightens after entry.
Fixed causal 4H signal and structural swing stop; compare exit with/without invalidation.
"""
import json
from pathlib import Path
from feature_walkforward import data
from analyze_mtf_5y import indicator
from structural_delta_strategy import swing,stat,FEE
def run(rows,colors,lo,hi,invalidate):
 trades=[];k=max(210,lo)
 while k<hi-2:
  prev,cur=colors[k-1],colors[k]
  side=1 if prev=="mediumR" and cur=="weakR" else -1 if prev=="mediumB" and cur=="weakB" else 0
  if not side:k+=1;continue
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
   if (invalidate and invalid) or opposite:
    price=rows[z+1][1];why="invalidation" if invalid and invalidate else "opposite";ex=z+1;break
  trades.append({"entry_i":ei,"exit_i":ex,"side":"LONG" if side==1 else "SHORT","entry":entry,"exit":price,"stop":stop,"reason":why,"ret":side*(price/entry-1)-FEE})
  k=ex+1
 return trades
def main():
 syms=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
 out={"notes":"Causal closed-4H experiment. Entry mediumR->weakR LONG, mediumB->weakB SHORT, next open. Structural confirmed 4H pivot stop, 0.1% buffer. New invalidation: weakR->mediumR/strongR while LONG or weakB->mediumB/strongB while SHORT; exit next 4H open. Opposite fade remains exit. 0.15% roundtrip fee, no funding. Stop-first, one position per asset, no overlapping. Safety cap 120 bars. Strict last-25% test, but trader rules are inferred from BTC history, not pristine BTC holdout. Does not model forming 4H snapshots or discretionary candle-pattern selection.","assets":{}}
 for s in syms:
  rows,_=data(s);colors=indicator(rows)["color"];n=len(rows);cut=n*3//4
  before=run(rows,colors,cut,n,False);after=run(rows,colors,cut,n,True)
  fullbefore=run(rows,colors,0,n,False);fullafter=run(rows,colors,0,n,True)
  out["assets"][s]={"last25_baseline":stat(before),"last25_invalidation":stat(after),"last25_exit_reasons":{r:sum(t["reason"]==r for t in after) for r in ("invalidation","opposite","stop","safety_timeout")},"full_baseline":stat(fullbefore),"full_invalidation":stat(fullafter),"trades_last25_invalidation":after}
 Path("reports/deltarsi_invalidation_experiment.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({s:{k:v for k,v in a.items() if k!="trades_last25_invalidation"} for s,a in out["assets"].items()},indent=2))
if __name__=="__main__":main()
