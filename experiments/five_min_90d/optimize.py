"""Train on first 60 days, evaluate untouched last 30 days, same 4h Delta signals."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.pine_vs_codex.run import pine_events
def main():
 raw={};sig={}
 for s in e.SYMS:
  rows=e.download(s);raw[s]={r[0]:r for r in rows}
  hourly=[]
  for i in range(0,len(rows),12):
   c=rows[i:i+12]
   if len(c)==12 and c[0][0]%e.H==0:hourly.append((c[0][0],c[0][1],max(b[2] for b in c),min(b[3] for b in c),c[-1][4]))
  sig[s]=pine_events(hourly)
 train_end=e.START+60*e.DAY
 candidates=[(sl,tp,be,hold) for sl,tp in ((1.,1.5),(1.5,2.5),(1.5,5.),(2.5,2.5),(2.5,5.),(3.5,5.),(5.,2.5),(5.,5.)) for be,hold in ((None,48),(.01,48),(.015,72))]
 selected={};report={}
 for s in e.SYMS:
  tests=[]
  for sl,tp,be,hold in candidates:
   par={s:(sl,tp,None,None)}
   r=e.simulate(raw,sig,(s,),params=par,start=e.START,end=train_end,be_trigger=be,max_hold=hold)
   tests.append((r,sl,tp,be,hold))
  # Do not select challenge pass alone; penalize drawdown and hard violations.
  tests.sort(key=lambda v:(v[0]["breach"] is None,len(v[0]["phases"]),v[0]["net_pnl"]-20*v[0]["max_dd_pct"]),reverse=True)
  r,sl,tp,be,hold=tests[0]
  selected[s]=dict(sl=sl,tp=tp,be=be,hold=hold)
  report[s]=dict(train=r,parameters=selected[s])
  print("SELECT",s,json.dumps(report[s]),flush=True)
 def portfolio(group,start,end,optimized):
  # Mixed symbol-specific BE and hold cannot be represented by single global scalar;
  # compare global exit policy and optimized symbol-specific SL/TP fairly.
  pars={s:(selected[s]["sl"],selected[s]["tp"],None,None) for s in group} if optimized else {s:e.PARAMS[s] for s in group}
  return e.simulate(raw,sig,group,params=pars,start=start,end=end,be_trigger=.01 if optimized else None,max_hold=48)
 results={"selected":report,"comparison":{},"notes":["60-day train, last 30 days untouched test; same historical RSI12 SMA21 EMA7 4h signals.","Per-symbol candidate SL/TP and BE/hold evaluated in train; portfolio uses selected SL/TP plus uniform 1% BE and 48h hold.","Training selection is in-sample; OOS comparison is last 30 days.","5m conservative stop-first, 60sec approximation, funding, fees, risk caps, consistency rule."]}
 for name,g in {"all":e.SYMS,"A":("BTCUSDT","ETHUSDT","TONUSDT","ZECUSDT","XRPUSDT"),"B":("ICPUSDT","BNBUSDT","LINKUSDT")}.items():
  results["comparison"][name]={}
  for period,start,end in (("train",e.START,train_end),("test",train_end,e.END),("full",e.START,e.END)):
   for mode in ("baseline","optimized"):
    r=portfolio(g,start,end,mode=="optimized")
    results["comparison"][name][period+"_"+mode]=r
    print("COMPARE",name,period,mode,json.dumps(r),flush=True)
 Path("experiments/five_min_90d/optimized_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
