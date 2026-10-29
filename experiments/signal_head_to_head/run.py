"""Apples-to-apples two-signal portfolio test, same history, costs, stops, and risk rules."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.canonical_delta_portfolio.run import canonical
import experiments.upscale_year_portfolio.run as engine
DAY=24*H
GROUPS=[("BTCUSDT","ETHUSDT","ICPUSDT"),("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT"),("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","HYPEUSDT")]
MODES={
 "atr25_tp3":(("atr",2.5),("atr",3.),False),
 "sl1_tp_atr":(("fixed",1.),("atr",3.),False),
 "sl2_tp_atr":(("fixed",2.),("atr",3.),False),
 "sl2_tp2":(("fixed",2.),("fixed",2.),False),
 "atr25_tp3_be1":(("atr",2.5),("atr",3.),True)
}
def main():
 raw={};old={};new={};sha={}
 for s in GROUPS[-1]:
  rows,sha[s]=load(s);raw[s]={r[0]:r for r in rows}
  e,_=events(rows);old[s]={x["entry_ms"]:x for x in e["closed"]}
  new[s]={ratio:canonical(rows,ratio) for ratio in (.65,.8,.95)}
 out=dict(description="Matched-horizon comparison: old surrogate vs canonical DeltaRSI weakening proxies",
  limitations=["Canonical entry is an intensity proxy; wick/wave/divergence and higher-timeframe rules not implemented.",
  "Risk model conservative hourly stop-first and adverse excursion; no funding or real execution.",
  "Selection uses historical data; not an independent out-of-sample.",
  "Only 1H-cache symbols; BNB/SOL/XRP 4H-only excluded.",
  "Stage accounting in inherited simulator is approximate; compare continuous returns and breach first."],
  capital_usd=5000,position_usd=1000,max_open=3,results={})
 for group in GROUPS:
  common=set.intersection(*(set(raw[s]) for s in group))
  end=max(common);start=max(min(common),end-365*DAY+H)
  times=list(range(start,end+H,H))
  if any(t not in common for t in times):raise ValueError("Noncontiguous hourly history "+str(group))
  engine.SYMS=group
  dataset={s:raw[s] for s in group}
  for sigtype in ("surrogate","delta065","delta080","delta095"):
   sig={s:old[s] if sigtype=="surrogate" else new[s][{"delta065":.65,"delta080":.8,"delta095":.95}[sigtype]] for s in group}
   for mode_name,mode in MODES.items():
    key=f"{len(group)}assets_{sigtype}_{mode_name}"
    result=engine.simulate(dataset,sig,times,{s:mode for s in group},reset_phases=False)
    out["results"][key]={k:v for k,v in result.items() if k not in ("trades","daily")}
    print(key,json.dumps(out["results"][key]),flush=True)
 p=Path("experiments/signal_head_to_head/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
