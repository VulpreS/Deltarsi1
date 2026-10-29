"""Compare true 5m Delta signal vs 4h Delta signal, both with 5m fills."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.pine_vs_codex.run import pine_events,pine_shade
from causal_4h_parity_audit import CausalDelta
from research_multiasset import atr
def five_signals(rows):
 av=atr(rows);state=CausalDelta();previous=None;out={}
 for i,b in enumerate(rows):
  prior=state.delta;d,_,_=state.step(b[4],commit=True)
  shade=pine_shade(d,prior)
  if i>=210 and shade and previous and i+1<len(rows) and math.isfinite(av[i-1]) and av[i-1]>0:
   side=1 if previous=="medium_red" and shade=="weak_red" else (-1 if previous=="medium_blue" and shade=="weak_blue" else 0)
   if side:out[b[0]+e.M]=dict(side=side,atr_4h=av[i-1],entry_ms=b[0]+e.M)
  previous=shade
 return out
def main():
 raw={};sig5={};sig4={}
 for s in e.SYMS:
  rows=e.download(s);raw[s]={r[0]:r for r in rows};sig5[s]=five_signals(rows)
  hourly=[]
  for i in range(0,len(rows),12):
   c=rows[i:i+12]
   if len(c)==12 and c[0][0]%e.H==0:hourly.append((c[0][0],c[0][1],max(b[2] for b in c),min(b[3] for b in c),c[-1][4]))
  sig4[s]=pine_events(hourly)
  print("SIGNALS",s,"5m",sum(e.START<=t<e.END for t in sig5[s]),"4h",sum(e.START<=t<e.END for t in sig4[s]),flush=True)
 groups={"all":e.SYMS,"A":("BTCUSDT","ETHUSDT","TONUSDT","ZECUSDT","XRPUSDT"),"B":("ICPUSDT","BNBUSDT","LINKUSDT")}
 # ATR multiples on the native signal TF; fixed notional $1000; same execution engine.
 grids={"5m":((1.5,2.5),(2.5,5.),(3.5,5.)),"4h":((1.5,2.5),(2.5,5.),(3.5,5.))}
 out={"notes":["True 5m signal versus 4h signal, both execute on 5m bars.","Same CausalDelta and pine_shade logic; ATR calculated on signal TF, so SL/TP price distances differ.","5m signals have 210 5m warmup bars, 4h signals 210 4h warmup bars.","Same $5000 account, max 3 x $1000 notional, fee/spread/funding and prop prototype.","This is a comparison of signal speed; ATR settings are illustrative, not optimized on OOS.","5m engine approximates 60sec rule; stop-first on same bar.","90-day 2026-04-02 to 2026-06-30."],"results":{}}
 for tf,sigs in (("5m",sig5),("4h",sig4)):
  for sl,tp in grids[tf]:
   pars={s:(sl,tp,None,None) for s in e.SYMS}
   for group,g in groups.items():
    r=e.simulate(raw,sigs,g,params=pars)
    key=f"{tf}_{sl}_{tp}_{group}";out["results"][key]=r
    print("COMPARE",key,json.dumps(r),flush=True)
 # Preserve original previously published 4h per-coin baseline.
 for group,g in groups.items():
  r=e.simulate(raw,sig4,g)
  out["results"]["4h_original_"+group]=r
  print("COMPARE","4h_original_"+group,json.dumps(r),flush=True)
 Path("experiments/five_min_90d/timeframe_comparison.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
