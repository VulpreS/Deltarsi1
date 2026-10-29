"""Individual Pine hold sweep: 4..96h step 4, train-only selection, portfolio OOS."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,H
from experiments.pine_vs_codex.run import pine_events
import experiments.max_strategy_grid.run as grid
from experiments.max_strategy_grid.prop_portfolio import run,INITIAL,SYMS,DAY,iso
HOURS=tuple(range(4,97,4))
def score(rows,signal,params,start,end,hours):
 grid.MAXH=hours
 x=grid.replay(rows,signal,params,start,end)
 valid=[z for z in x["trades"] if z["exit_ms"]<=end]
 return dict(pnl=round(sum(z["net_usd"] for z in valid),2),trades=len(valid),
  stops=sum(z["reason"].startswith("stop") for z in valid),takes=sum(z["reason"].startswith("take") for z in valid),
  time_exits=sum(z["reason"]=="time" for z in valid))
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 rows={};signals={};data={}
 for s in SYMS:
  r,_=load(s);rows[s]=r;signals[s]=pine_events(r);data[s]={x[0]:x for x in r}
 group=SYMS
 common=set.intersection(*(set(data[s]) for s in group))
 end=max(common)+H;start=max(min(common),end-365*DAY)
 split=start+int((end-start)//DAY*.7)*DAY
 results=dict(window=dict(start=iso(start),split=iso(split),end=iso(end)),hours=HOURS,by_symbol={},selected={},portfolio={},
  notes=["Individual settings selected exclusively on first 70% of six-symbol common history.",
   "Portfolio OOS starts flat at split, with initial 5000 USD. OOS only is the independent evaluation.",
   "Full-year replay uses same selected settings and overlaps selection history.",
   "Original Pine signal is a proxy and must be checked against RSI27 final rules.",
   "Prop risk engine approximate; stop-first OHLC pessimistic execution."])
 for s in SYMS:
  params=tuple(baseline[s]);sweep=[]
  for hours in HOURS:
   train=score(rows[s],signals[s],params,start,split,hours)
   test=score(rows[s],signals[s],params,split,end,hours)
   sweep.append(dict(hours=hours,train=train,test=test))
  chosen=max(sweep,key=lambda x:(x["train"]["pnl"],-x["hours"]))
  results["by_symbol"][s]=sweep;results["selected"][s]=chosen
  print("SELECT",s,json.dumps(chosen),flush=True)
 for label,group in (("six_common",SYMS),("five_year",tuple(s for s in SYMS if s!="TONUSDT"))):
  common=set.intersection(*(set(data[s]) for s in group));e=max(common)+H;st=max(min(common),e-365*DAY)
  # Independent OOS only applies to the six-symbol common period.
  windows={"full":(st,e)}
  if label=="six_common":windows["oos"]=(split,e)
  for window,(a,b) in windows.items():
   times=list(range(a,b,H))
   if any(t not in common for t in times):raise ValueError("Missing hourly candles "+label)
   subset={s:data[s] for s in group};sig={s:signals[s] for s in group};params={s:tuple(baseline[s]) for s in group}
   for mode,hours in (("selected",{s:results["selected"][s]["hours"] for s in group}),("fixed_48h",48)):
    for reset in (False,True):
     result=run(subset,sig,params,times,reset=reset,max_hours=hours)
     key="_".join((label,window,mode,"challenge" if reset else "continuous"))
     results["portfolio"][key]=result
     print("PORTFOLIO_HOLD",key,json.dumps(result),flush=True)
 p=Path("experiments/max_strategy_grid/individual_holds.json")
 p.write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
