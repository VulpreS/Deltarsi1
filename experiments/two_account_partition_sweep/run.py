"""Upscale API-constrained 127 two-account partitions versus one competing 8-asset account."""
import sys,json,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.new_assets_2026.run import download
from experiments.pine_vs_codex.run import pine_events
import experiments.two_accounts_opposite_exit.run as engine
SYMS=engine.OLD+engine.NEW
def main():
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s) if s in engine.OLD else (download(s),None)
  raw[s]={x[0]:x for x in rows};sig[s]=pine_events(rows)
  print("DATA",s,len(rows),flush=True)
 params={s:tuple(v) for s,v in json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"].items()}
 params.update({"XRPUSDT":(5.,2.5,None,None),"LINKUSDT":(5.,5.,None,None)})
 common=set.intersection(*(set(raw[s]) for s in SYMS));times=sorted(common)
 if any(b-a!=engine.H for a,b in zip(times,times[1:])):raise ValueError("Timeline not contiguous")
 output={"notes":["All 127 unique two-account partitions of eight assets (A contains BTC), plus single account.","Each account has independent $5000 initial capital, 3 slots, $1000 notional per trade, stage resets, no withdrawal of challenge profits.","Single account uses $5000 initial, not $10000. Compare completion, not raw PnL.","Historical TONUSDT labeled GRAM; not a verified ticker migration.","Upscale API 30% rule, 0.008% fee per operation and 0.015% eight-hour funding; hourly candle approximation for 60-second rule.","Best grouping selected in sample: requires independent validation."],"results":{}}
 for period,ts in (("common",times),("last_90d",times[-2160:]),("last_30d",times[-720:])):
  cache={}
  def simulate(group):
   key=tuple(sorted(group))
   if key not in cache:
    cache[key]=engine.run({s:raw[s] for s in key},{s:sig[s] for s in key},{s:params[s] for s in key},ts,reset=True)
   return cache[key]
  single=simulate(SYMS);records=[]
  for mask in range(128):
   a=tuple(SYMS[i] for i in range(8) if i==0 or mask & (1<<(i-1)))
   if len(a)==8:continue
   b=tuple(s for s in SYMS if s not in a)
   x,y=simulate(a),simulate(b)
   phases=(len(x["phases"]),len(y["phases"]))
   funded=sum(p>=2 for p in phases)
   dates=[v["phases"][1]["completed"] if len(v["phases"])>=2 else None for v in (x,y)]
   records.append(dict(A=a,B=b,split=f"{min(len(a),len(b))}+{max(len(a),len(b))}",completed=phases,funded_accounts=funded,funded_dates=dates,phase_now=(x["phase_now"],y["phase_now"]),equity=(x["equity"],y["equity"]),current_phase_equity_sum=round(x["equity"]+y["equity"],2),skipped=x["skipped"]+y["skipped"],breaches=(x["breach"],y["breach"])))
  records.sort(key=lambda z:(-z["funded_accounts"],max(z["funded_dates"]) if z["funded_accounts"]==2 else "9999",-sum(z["completed"]),z["skipped"]))
  output["results"][period]={"single":single,"partitions":records,"best":records[:15],"counts":{str(n):sum(r["funded_accounts"]==n for r in records) for n in range(3)}}
  print("SWEEP_SUMMARY",period,json.dumps(dict(single_phases=single["phases"],single_equity=single["equity"],counts=output["results"][period]["counts"],top=records[:8]),ensure_ascii=False),flush=True)
 p=Path("experiments/two_account_partition_sweep/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(output,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
