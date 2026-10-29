"""Counterfactual account closures under 5/10 vs 3/6 risk and 20/15/10% allocation.
Each breach terminates a simulated account; restarting with $5000 is a NEW account,
not a continuation or valid funded challenge. Uses frozen Pine baseline and 48h hold.
"""
import sys,json,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
BASE=Path("experiments/max_strategy_grid/prop_portfolio.py").read_text()
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
def engine(share,daily,total):
 source=BASE.replace("NOTIONAL=1000.","NOTIONAL="+str(5000*share))
 source=source.replace("daybase*.95","daybase*"+str(1-daily))
 source=source.replace("INITIAL*.9","INITIAL*"+str(1-total))
 module=types.ModuleType("risk_variant")
 module.__file__="experiments/max_strategy_grid/prop_portfolio.py"
 exec(compile(source,module.__file__,"exec"),module.__dict__)
 return module.run
def cycle(run,raw,sig,params,times):
 closures=[];segments=[];remaining=times;limit=30
 while remaining and len(segments)<limit:
  r=run(raw,sig,params,remaining,max_hours=48)
  segments.append(dict(start=r["start"],end=r["end"],closed_pnl=r["closed_net_pnl"],trades=r["trades"],maxdd=r["max_intrahour_dd"],breach=r["breach"]))
  if not r["breach"]:break
  closures.append(r["breach"])
  # Account liquidation occurs at first breach; restart fresh on NEXT hourly candle.
  import datetime as dt
  breach_ms=int(dt.datetime.fromisoformat(r["breach"]["time"]).timestamp()*1000)
  remaining=[t for t in remaining if t>breach_ms]
  if not remaining:break
 return dict(closed_accounts=len(closures),closures=closures,segments=segments,total_closed_pnl=sum(x["closed_pnl"] for x in segments),total_trades=sum(x["trades"] for x in segments))
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s);raw[s]={x[0]:x for x in rows};sig[s]=pine_events(rows)
 groups={"five_year":tuple(s for s in SYMS if s!="TONUSDT"),"six_common":SYMS}
 out=dict(method="Pine frozen baseline, 48h max hold, $5000 initial, 3 max simultaneous positions, 0.08% fees per side, 0.02% roundtrip spread",note="Closures counted by restarting a NEW hypothetical account after each breach; simulator is an approximation, not audited Upscale enforcement.",results={})
 for group,syms in groups.items():
  common=set.intersection(*(set(raw[s]) for s in syms));end=max(common)+H;start=max(min(common),end-365*DAY)
  times=list(range(start,end,H))
  if any(t not in common for t in times):raise ValueError("Noncontiguous "+group)
  for daily,total in ((.05,.10),(.03,.06)):
   for share in (.20,.15,.10):
    key=f"{group}_daily{int(daily*100)}_total{int(total*100)}_share{int(share*100)}"
    data={s:raw[s] for s in syms};signals={s:sig[s] for s in syms};params={s:tuple(baseline[s]) for s in syms}
    run=engine(share,daily,total)
    first=run(data,signals,params,times,max_hours=48)
    repeat=cycle(run,data,signals,params,times)
    result=dict(first=dict(breach=first["breach"],closed_pnl=first["closed_net_pnl"],trades=first["trades"],maxdd=first["max_intrahour_dd"],equity=first["equity"]),restarts=repeat)
    out["results"][key]=result
    print("RISK_SCENARIO",key,json.dumps(result),flush=True)
 p=Path("experiments/prop_tighter_limits/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
