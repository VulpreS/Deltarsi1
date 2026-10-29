"""Compare original Delta impulse-extreme stop with ATR stops; summarize 96h MAE/MFE."""
import sys,json,math,statistics as st
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.mae_mfe_stops.run import ASSETS,download,load,pine_events,H,iso,paths
from experiments.max_strategy_grid.prop_portfolio import run
from completed_candles import aggregate_completed
from experiments.pine_vs_codex.run import pine_shade
from causal_4h_parity_audit import CausalDelta
def delta_extreme_stops(rows,events):
 bars=aggregate_completed(rows,4,asof_ms=rows[-1][0]+H)
 state=CausalDelta();prev=None;run_peak=None;active=None;stops={}
 for b in bars:
  old=state.delta;d,_,_=state.step(b[4],commit=True);shade=pine_shade(d,old)
  color="red" if d<0 else "blue" if d>0 else None
  if color!=active:active=color;run_peak=None
  if color and math.isfinite(d):
   if run_peak is None or abs(d)>run_peak[0]:run_peak=(abs(d),b[3] if color=="red" else b[2],b[0])
  t=b[0]+4*H
  if t in events and run_peak is not None:
   side=events[t]["side"]
   if (side==1 and color=="red") or (side==-1 and color=="blue"):
    # Candle extreme of strongest Delta bar within current color wave.
    stops[t]=run_peak[1]
  prev=shade
 return stops
def replay(rows,events,stops,hold,tp_atr=5):
 data={r[0]:r for r in rows};ts=sorted(data);split=ts[len(ts)*7//10];cash=5000.;trade=[];occupied=-1
 for t,e in sorted(events.items()):
  if t<split or t<=occupied or t not in data or t not in stops:continue
  side=e["side"];atr=e["atr_4h"];entry=data[t][1];stop=stops[t];target=entry+side*tp_atr*atr
  if side*(entry-stop)<=0 or stop<=0:continue
  qty=1000/entry;fee=1000*.0009;exit_t=None
  for j in range(hold):
   q=t+j*H
   if q not in data:break
   _,o,h,l,c=data[q]
   if side*(o-stop)<=0:price=o;reason="stop_gap"
   elif side*(o-target)>=0:price=o;reason="take_gap"
   elif (l<=stop if side==1 else h>=stop):price=stop;reason="stop"
   elif (h>=target if side==1 else l<=target):price=target;reason="take"
   elif j==hold-1:price=c;reason="time"
   else:continue
   exit_t=q;net=side*qty*(price-entry)-fee-qty*price*.0009
   trade.append(dict(entry=iso(t),net=round(net,3),reason=reason,stop_atr=round(abs(entry-stop)/atr,3)))
   cash+=net;occupied=q;break
 return dict(pnl=round(sum(x["net"] for x in trade),2),trades=len(trade),stops=sum(x["reason"].startswith("stop") for x in trade),win_rate=round(100*sum(x["net"]>0 for x in trade)/len(trade),1) if trade else None,mean_stop_atr=round(st.mean(x["stop_atr"] for x in trade),2) if trade else None)
def main():
 output={}
 for s in ASSETS:
  try:
   rows=load(s)[0] if s=="ICPUSDT" else download(s);events=pine_events(rows);pp=paths(rows,events)
   t0=rows[len(rows)*7//10][0];sets={"all":pp,"oos":[p for p in pp if p["entry"]>=iso(t0)]}
   summary={}
   for name,part in sets.items():
    if not part:continue
    summary[name]=dict(n=len(part),mae_median=round(st.median(x["mae_atr"] for x in part),2),mfe_median=round(st.median(x["mfe_atr"] for x in part),2),mae_over_2_5=sum(x["mae_atr"]>=2.5 for x in part),mae_over_5=sum(x["mae_atr"]>=5 for x in part),mfe_over_2_5=sum(x["mfe_atr"]>=2.5 for x in part),adverse_then_recovery=sum(x["adverse_then_recovery"] for x in part))
   stops=delta_extreme_stops(rows,events)
   result=dict(summary=summary,delta_stop_48h=replay(rows,events,stops,48),delta_stop_72h=replay(rows,events,stops,72),delta_stop_96h=replay(rows,events,stops,96),stop_count=len(stops))
   output[s]=result;print("DELTA_EXTREME",s,json.dumps(result),flush=True)
  except Exception as ex:output[s]={"error":str(ex)};print("DELTA_EXTREME_ERROR",s,str(ex),flush=True)
 p=Path("experiments/delta_extreme_stops/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(output,indent=2))
if __name__=="__main__":main()
