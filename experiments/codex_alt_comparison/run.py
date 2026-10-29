"""Closed-4h Codex peak-decay signals versus Pine on identical altcoin histories."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import events,load
from experiments.mae_mfe_stops.run import ASSETS,download
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import run
from experiments.mae_mfe_stops.run import H
STOPS=(1.5,2.5,3.,5.)
TARGETS=(2.5,3.,5.)
HOLDS=(48,72,96)
def metrics(r):
 return {k:r[k] for k in ("closed_net_pnl","trades","stops","time_exits","win_rate","profit_factor","max_intrahour_dd","breach")}
def main():
 out={"method":"Codex closed 4h peak-decay signal: previous peak >=15, fading ratio <=0.7, no forming candle, next hour entry.","assumptions":"Fixed $1000 position; 0.08% fee each side; 0.02% spread roundtrip; 5000 USD account; 5% daily and 10% total limits approximated.","selection":"Choose parameter combination by TRAIN pnl subject to no TRAIN breach; evaluate only once on OOS.","per_asset":{}}
 raw={};signals={};common=None
 for s in ASSETS:
  try:
   rows=load(s)[0] if s=="ICPUSDT" else download(s)
   raw[s]={r[0]:r for r in rows}
   ev,_=events(rows)
   codex={e["entry_ms"]:dict(side=e["side"],atr_4h=e["atr_4h"]) for e in ev["closed"] if e["entry_ms"] in raw[s]}
   pine=pine_events(rows)
   signals[s]=codex
   times=sorted(raw[s]);split=len(times)*7//10;train=times[:split];test=times[split:]
   results=[]
   for sl in STOPS:
    for tp in TARGETS:
     for hold in HOLDS:
      p=(sl,tp,None,None)
      tr=run({s:raw[s]},{s:codex},{s:p},train,max_hours=hold)
      results.append(dict(sl=sl,tp=tp,hold=hold,train=metrics(tr)))
   viable=[x for x in results if x["train"]["breach"] is None]
   chosen=max(viable or results,key=lambda x:x["train"]["closed_net_pnl"])
   frozen=(2.5,3.,48)
   benchmarks={}
   for name,sig in (("codex",codex),("pine",pine)):
    for label,params,hold in (("frozen",frozen[:2],frozen[2]),("trained",(chosen["sl"],chosen["tp"]),chosen["hold"])):
     p=(params[0],params[1],None,None)
     benchmarks[name+"_"+label]=dict(train=metrics(run({s:raw[s]},{s:sig},{s:p},train,max_hours=hold)),oos=metrics(run({s:raw[s]},{s:sig},{s:p},test,max_hours=hold)))
   out["per_asset"][s]=dict(candles=len(rows),codex_signals=len(codex),pine_signals=len(pine),train_window=[train[0],train[-1]],oos_window=[test[0],test[-1]],chosen=chosen,benchmarks=benchmarks,grid=results)
   print("CODEX_ALT",s,json.dumps({k:out["per_asset"][s][k] for k in ("codex_signals","pine_signals","chosen","benchmarks")}),flush=True)
  except Exception as e:out["per_asset"][s]={"error":str(e)};print("CODEX_ALT_ERROR",s,str(e),flush=True)
 # portfolio across 5 assets: common range, params frozen and per-asset trained
 valid=[s for s in ASSETS if s in raw and s in signals]
 if len(valid)==len(ASSETS):
  common=sorted(set.intersection(*(set(raw[s]) for s in valid)))
  trainend=common[len(common)*7//10]
  for mode in ("frozen","trained"):
   params={s:(2.5,3.,None,None) if mode=="frozen" else (out["per_asset"][s]["chosen"]["sl"],out["per_asset"][s]["chosen"]["tp"],None,None) for s in valid}
   holds={s:48 if mode=="frozen" else out["per_asset"][s]["chosen"]["hold"] for s in valid}
   out.setdefault("portfolio",{})[mode]=dict(oos=metrics(run(raw,signals,params,[t for t in common if t>=trainend],max_hours=holds)),full=metrics(run(raw,signals,params,common,max_hours=holds)))
   print("CODEX_PORTFOLIO",mode,json.dumps(out["portfolio"][mode]),flush=True)
 p=Path("experiments/codex_alt_comparison/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
