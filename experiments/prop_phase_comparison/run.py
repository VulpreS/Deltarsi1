import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.pine_vs_codex.run import pine_events,MODE,SYMS,DAY
import experiments.upscale_year_portfolio.run as engine
raw={};signals={}
for s in SYMS:
 rows,_=load(s);raw[s]={r[0]:r for r in rows}
 ev,_=events(rows)
 signals[s]={"codex":{x["entry_ms"]:x for x in ev["closed"]},"pine":pine_events(rows)}
results=[]
for group in (SYMS[:3],SYMS):
 common=set.intersection(*(set(raw[s]) for s in group))
 end=max(common);start=max(min(common),end-365*DAY+H)
 times=list(range(start,end+H,H))
 engine.SYMS=group
 for name in ("codex","pine"):
  sig={s:signals[s][name] for s in group}
  data={s:raw[s] for s in group}
  mode={s:MODE for s in group}
  full=engine.simulate(data,sig,times,mode,reset_phases=False)
  phases=engine.simulate(data,sig,times,mode,reset_phases=True)
  row={"group":group,"signal":name,"full":{k:v for k,v in full.items() if k not in ("trades","daily")},"phases":{k:v for k,v in phases.items() if k not in ("trades","daily")}}
  results.append(row)
  print("PROP_RESULT",json.dumps(row),flush=True)
p=Path("experiments/prop_phase_comparison/results.json")
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(results,indent=2))
