"""Large matched two-signal exit grid; cached candles only; research, never orders."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.canonical_delta_portfolio.run import canonical
import experiments.upscale_year_portfolio.run as engine
DAY=24*H
GROUPS=[("BTCUSDT","ETHUSDT","ICPUSDT"),("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT"),("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","HYPEUSDT")]
SL=[("atr",2.5)]+[("fixed",v) for v in (.5,1,1.5,2,2.5)]
TP=[("atr",3)]+[("fixed",v) for v in (.5,1,1.5,2,2.5)]
def main():
 raw={};old={};new={};sha={}
 for s in GROUPS[-1]:
  rows,sha[s]=load(s);raw[s]={r[0]:r for r in rows}
  ev,_=events(rows);old[s]={e["entry_ms"]:e for e in ev["closed"]}
  new[s]={r:canonical(rows,r) for r in (.65,.8,.95)}
 out=dict(title="Full matched signal and exits sweep",source_sha=sha,starting_balance_usd=5000,
  trade_notional_usd=1000,max_simultaneous=3,commission_per_side=.0008,spread_roundtrip=.0002,
  caveats=["Canonical DeltaRSI uses a proxy intensity weakening entry, not all manual wick/wave/divergence rules.",
   "Stop-first hourly execution; conservative intrahour equity risk; no funding or independent OOS.",
   "Group windows vary; compare signal types only within the same group.",
   "Stage transition accounting inherited from earlier prototype; challenge completion not independently verified.",
   "No actual orders; BNB SOL XRP excluded without hourly data."],groups={},rows=[],best_by_group={})
 for group in GROUPS:
  common=set.intersection(*(set(raw[s]) for s in group))
  end=max(common);start=max(min(common),end-365*DAY+H)
  times=list(range(start,end+H,H))
  if any(t not in common for t in times):raise ValueError("noncontiguous common history "+str(group))
  engine.SYMS=group
  data={s:raw[s] for s in group}
  gname="+".join(s.replace("USDT","") for s in group)
  out["groups"][gname]=dict(start=engine.iso(times[0]),end=engine.iso(times[-1]+H),days=len(times)/24)
  for sigtype in ("surrogate","delta065","delta080","delta095"):
   sig={s:old[s] if sigtype=="surrogate" else new[s][{"delta065":.65,"delta080":.8,"delta095":.95}[sigtype]] for s in group}
   for sm in SL:
    for tm in TP:
     for be in (False,True):
      mode={s:(sm,tm,be) for s in group}
      r=engine.simulate(data,sig,times,mode,reset_phases=False)
      row=dict(group=gname,signal=sigtype,sl=f"{sm[0]}_{sm[1]}",tp=f"{tm[0]}_{tm[1]}",be1=be,
       days=r["days"],return_pct=r["return_since_last_phase_reset_pct"],equity_usd=r["balance_or_equity_usd"],
       trades=r["closed_trades"],win_pct=r["win_rate_pct"],pf=r["profit_factor"],max_dd_pct=r["max_intrahour_dd_pct"],
       worst_day_usd=r["worst_day_equity_drop_usd"],max_losing_streak=r["max_losing_streak"],
       breach=r["breach"],max_concurrent=r["max_concurrent"],by_symbol=r["by_symbol"],
       phase_completed=r["phase_completed"][:2])
      out["rows"].append(row)
   subset=[x for x in out["rows"] if x["group"]==gname and x["signal"]==sigtype]
   survivors=[x for x in subset if x["breach"] is None]
   best=sorted(survivors,key=lambda x:x["return_pct"],reverse=True)[:12]
   out["best_by_group"][gname+"_"+sigtype]=best
   print("SUMMARY",gname,sigtype,"tested",len(subset),"survived",len(survivors),"best",json.dumps(best[:5]),flush=True)
 p=Path("experiments/mega_signal_grid/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2))
 print("TOTAL_VARIANTS",len(out["rows"]),flush=True)
if __name__=="__main__":main()
