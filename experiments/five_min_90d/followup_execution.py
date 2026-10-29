"""Follow-up: same 4h Delta signals, 8 assets, 5m versus 15m execution.

Selected per-asset SL/TP/BE/hold frozen from previous 60-day TRAIN. Last 30d
is OOS and never used to reselect. 15m OHLC is aggregated from the exact same
5m Binance UM source, not from a second venue. All fills are approximations.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from collections import defaultdict
from experiments.five_min_90d import run as e
from experiments.pine_vs_codex.run import pine_events

SELECTED={
 "BTCUSDT": (2.5,2.5,None,48),
 "ETHUSDT": (1.5,2.5,None,48),
 "ICPUSDT": (2.5,2.5,.015,72),
 "TONUSDT": (1.0,1.5,None,48),
 "BNBUSDT": (3.5,5.0,None,48),
 "ZECUSDT": (1.5,2.5,.015,72),
 "XRPUSDT": (1.5,2.5,None,48),
 "LINKUSDT": (2.5,2.5,.01,48),
}
GROUPS={
 "all_8":e.SYMS,
 "account_A":("BTCUSDT","ETHUSDT","TONUSDT","ZECUSDT","XRPUSDT"),
 "account_B":("ICPUSDT","BNBUSDT","LINKUSDT"),
 "btc_eth":("BTCUSDT","ETHUSDT"),
}
M15=e.M*3

def resample_15m(raw5):
 out={}
 for t in sorted(raw5):
  if t%M15:continue
  if t+2*e.M not in raw5 or t+e.M not in raw5:continue
  a,b,c=(raw5[t+i*e.M] for i in range(3))
  out[t]=(t,a[1],max(a[2],b[2],c[2]),min(a[3],b[3],c[3]),c[4])
 return out

def sanity():
 raw={"BTCUSDT":{0:(0,100.,103.,99.,101.),e.M:(e.M,101.,103.,100.,102.)}}
 sig={"BTCUSDT":{0:{"side":1,"atr_4h":1}}}
 par={"BTCUSDT":(10.,2.,None,None)}
 old=e.simulate(raw,sig,("BTCUSDT",),params=par,start=0,end=2*e.M,entry_profit_policy="zero")
 new=e.simulate(raw,sig,("BTCUSDT",),params=par,start=0,end=2*e.M,entry_profit_policy="defer")
 assert old["trades"]==new["trades"]==1, (old,new)
 assert old["net_pnl"]<new["net_pnl"],(old,new)
 print("SANITY same-bar take deferral",old["net_pnl"],new["net_pnl"],flush=True)

def run():
 sanity()
 raw5={}; raw15={}; signals={};manifest={}
 for s in e.SYMS:
  rows=e.download(s)
  raw5[s]={r[0]:r for r in rows}
  raw15[s]=resample_15m(raw5[s])
  hourly=[]
  for i in range(0,len(rows),12):
   chunk=rows[i:i+12]
   if len(chunk)==12 and chunk[0][0]%e.H==0 and chunk[-1][0]-chunk[0][0]==11*e.M:
    hourly.append((chunk[0][0],chunk[0][1],max(b[2] for b in chunk),min(b[3] for b in chunk),chunk[-1][4]))
  signals[s]=pine_events(hourly)
  assert all(k%e.H==0 for k in signals[s])
  assert all(k in raw5[s] and k in raw15[s] for k in signals[s] if e.START<=k<e.END)
  manifest[s]={"rows_5m":len(raw5[s]),"rows_15m":len(raw15[s]),
               "4h_signals_90d":sum(e.START<=t<e.END for t in signals[s])}
  print("INPUT",s,json.dumps(manifest[s]),flush=True)
 n5=90*288; n15=90*96
 for tf,raw,n,step in (("5m",raw5,n5,e.M),("15m",raw15,n15,M15)):
  common=set.intersection(*(set(raw[s]) for s in e.SYMS))
  got=sum(t in common for t in range(e.START,e.END,step))
  if got!=n:raise ValueError(f"{tf} incomplete 90d: {got} vs {n}")
 print("INPUT_VALIDATED",json.dumps(manifest),flush=True)
 selected={s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exit_by_symbol={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 windows={"train60":(e.START,e.START+60*e.DAY),
          "oos30":(e.START+60*e.DAY,e.END),
          "full90":(e.START,e.END)}
 scenarios={
  "legacy_5m_baseline":dict(tf="5m",params=e.PARAMS,be_trigger=None,max_hold=48,entry_profit_policy="zero"),
  "corrected_5m_baseline":dict(tf="5m",params=e.PARAMS,be_trigger=None,max_hold=48,entry_profit_policy="defer"),
  "corrected_5m_uniform":dict(tf="5m",params=selected,be_trigger=.01,max_hold=48,entry_profit_policy="defer"),
  "corrected_5m_per_asset":dict(tf="5m",params=selected,be_trigger=None,max_hold=48,exit_by_symbol=exit_by_symbol,entry_profit_policy="defer"),
  "corrected_15m_baseline":dict(tf="15m",params=e.PARAMS,be_trigger=None,max_hold=48,entry_profit_policy="defer"),
  "corrected_15m_uniform":dict(tf="15m",params=selected,be_trigger=.01,max_hold=48,entry_profit_policy="defer"),
  "corrected_15m_per_asset":dict(tf="15m",params=selected,be_trigger=None,max_hold=48,exit_by_symbol=exit_by_symbol,entry_profit_policy="defer"),
 }
 output={"source":"Binance USD-M monthly 5m; 15m aggregated from source 5m",
         "signal_implementation":"experiments.pine_vs_codex.run.pine_events (unchanged)",
         "selected_parameters":SELECTED,"manifest":manifest,
         "windows_utc":{"train60":["2026-04-02","2026-06-01"],
                        "oos30":["2026-06-01","2026-07-01"],
                        "full90":["2026-04-02","2026-07-01"]},
         "scenarios":{},"tests":{},
         "assumptions":["All scenarios share closed-4h signal timestamps, same coin data and $5000 initial per account.",
           "Selected parameters frozen from prior 60-day train, OOS not fitted.",
           "Fixed $1000 notional/trade, max three positions; not margin 10/15% sizing.",
           "New defer policy disallows positive take in the entry candle but is NOT verified Upscale 60-second compliance.",
           "Stop-first for both SL and TP in same candle; 15m misses more intrabar ordering than 5m.",
           "Daily 5%, total 10%, 30% consistency and phase resets approximated by legacy engine.",
           "All adverse cross-coin wick extremes are treated as simultaneous, conservative.",
           "FEE=.00008 per side; SPREAD=.0002 roundtrip; FUNDING=.00015 charge each 8h; no independent slippage.",
           "Phase cumulative profit is sum of completed phase ledger profit plus final current phase NAV difference.",
           "Open positions at the end mark equity but do not enter realized-trade PNL; challenge stages not broker-verified.",
           "15m execution is comparison of execution resolution, NOT 15m Delta signals.",
           "Does not implement wick, wave counting, divergence, actual Upscale mark price/60s, or exact tariff rules."],
         "compliance_matrix":{"4h_closed_signal":"implemented","5m_15m_next_bar_execution":"implemented",
          "8_assets":"implemented","daily_loss_5pct":"approximated","total_loss_10pct":"approximated",
          "30pct_consistency":"approximated","60s_rule":"unverified","exact_funding":"unverified",
          "phase_reset":"approximated","divergence_wick_wave":"not_implemented"}}
 for mode,config in scenarios.items():
  tf=config["tf"];bars=raw5 if tf=="5m" else raw15
  kwargs={k:v for k,v in config.items() if k!="tf"}
  step=e.M if tf=="5m" else M15
  output["scenarios"][mode]={"execution_tf":tf,
        "same_bar_profit_exit":kwargs["entry_profit_policy"],
        "be_policy": "per-asset" if kwargs.get("exit_by_symbol") else str(kwargs["be_trigger"])}
  output["tests"][mode]={}
  for window,(start,end) in windows.items():
   output["tests"][mode][window]={}
   for group,g in GROUPS.items():
    r=e.simulate(bars,signals,g,start=start,end=end,step=step,**kwargs)
    output["tests"][mode][window][group]=r
    summary={k:r.get(k) for k in ("phases","equity","cumulative_phase_profit_usd","breach",
      "max_dd_pct","trades","win_rate_pct","profit_factor","fees","funding","skipped")}
    print("COMPARE",mode,window,group,json.dumps(summary,ensure_ascii=False),flush=True)
 # Prespecified sensitivity: hard <=5% price stop and 10x fee / wider spread.
 # No OOS tuning or re-selection; selected asset parameters stay frozen.
 output["stress"]={}
 prev_fee,prev_spread=e.FEE,e.SPREAD
 try:
  for costs,fee,spread in (("documented",.00008,.0002),("high_cost",.0008,.0004)):
   e.FEE,e.SPREAD=fee,spread
   for capped in (False,True):
    for tf in ("5m","15m"):
     key=f"{tf}_{costs}_{'price_stop_cap5pct' if capped else 'uncapped'}"
     output["stress"][key]={"fee_per_side":fee,"spread_roundtrip":spread,
                            "cap_price_stop":capped,"groups":{}}
     bars=raw5 if tf=="5m" else raw15
     step=e.M if tf=="5m" else M15
     for window in ("full90","oos30"):
      start,end=windows[window]
      output["stress"][key]["groups"][window]={}
      for group in ("all_8","btc_eth"):
       r=e.simulate(bars,signals,GROUPS[group],start=start,end=end,step=step,
         params=selected,exit_by_symbol=exit_by_symbol,
         entry_profit_policy="defer",cap_price_stop=capped)
       output["stress"][key]["groups"][window][group]=r
       result={k:r[k] for k in ("phases","cumulative_phase_profit_usd","breach",
         "max_dd_pct","trades","win_rate_pct","profit_factor","fees","funding")}
       print("STRESS",key,window,group,json.dumps(result,ensure_ascii=False),flush=True)
 finally:
  e.FEE,e.SPREAD=prev_fee,prev_spread
 p=Path("experiments/five_min_90d/followup_execution_results.json")
 p.write_text(json.dumps(output,indent=2,ensure_ascii=False))
 print("RESULT_FILE",str(p),p.stat().st_size,flush=True)

if __name__=="__main__":run()
