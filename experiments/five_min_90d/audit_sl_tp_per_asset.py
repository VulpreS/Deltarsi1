"""Forensic exact SL/TP implementation audit on 4h Delta, 5m execution.

One account, 8 instruments, $750 and $875, same costs/stop/BE as published.
Compare actual lag-one ATR source vs signal-closed ATR alternative, not a
parameter optimization. Report every asset's actual executed 4h positions,
stop clamping, realized SL/TP, ATR age and eligibility for year vs Q2.
"""
import os,sys,json,math,datetime as dt,collections,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.optimize_partial_take_4h import (
    source_load,START,VALID_END,END,COST_PER_SIDE,SPREAD_ROUNDTRIP)
from experiments.five_min_90d.compare_three_timeframes import SELECTED,ohlc_from_5m
from research_multiasset import atr
from experiments.pine_vs_codex.run import pine_events
FOUR=4*e.H
SYMS=tuple(e.SYMS)
OUT=Path("experiments/five_min_90d/sl_tp_per_asset_audit")
def rounded(n):return round(n,6) if isinstance(n,(int,float)) and math.isfinite(n) else None
def slim(r):
 return {k:r[k] for k in ("phases","breach","max_dd_pct","trades",
   "win_rate_pct","profit_factor","fees","funding","skipped","equity","cumulative_phase_profit_usd")}
def calc(data,signals,params,exits,notional,start,end):
 return e.simulate(data,signals,SYMS,params=params,exit_by_symbol=exits,
    start=start,end=end,step=e.M,entry_profit_policy="defer",
    cap_price_stop=True,stop_cap_mode="clamp",partials=(),
    collect_trades=True,position_notional=notional)
def summarize_trades(trades,params):
 by={}
 for sym in SYMS:
  s=[z for z in trades if z["symbol"]==sym]
  caps=[z for z in s if abs(z["initial_stop"]-z["original_atr_stop"])>1e-8*max(1,z["entry_price"])]
  true_stop=[z for z in s if z["reason"].startswith("stop") and not z["stop_updates"]]
  be_stop=[z for z in s if z["reason"].startswith("stop") and z["stop_updates"]]
  tp=[z for z in s if z["reason"].startswith("take")]
  time=[z for z in s if z["reason"]=="time"]
  sl,tp_atr,be,hold=params[sym]
  by[sym]={"configured":{"sl_atr4h":sl,"tp_atr4h":tp_atr,
      "be_trigger_price_pct":None if be is None else 100*be,"max_hold_h":hold},
    "closed_trades":len(s),"clamped_stop_trades":len(caps),
    "clamp_fraction_pct":rounded(100*len(caps)/len(s)) if s else None,
    "true_stop_exits":len(true_stop),"moved_stop_exits":len(be_stop),
    "take_exits":len(tp),"time_exits":len(time),
    "median_initial_stop_distance_pct":rounded(statistics.median(z["initial_risk_price_pct"] for z in s)) if s else None,
    "median_original_atr_sl_distance_pct":rounded(statistics.median(100*abs(z["entry_price"]-z["original_atr_stop"])/z["entry_price"] for z in s)) if s else None,
    "median_original_tp_distance_pct":rounded(statistics.median(100*abs(z["entry_price"]-z["target"])/z["entry_price"] for z in s)) if s else None,
    "realized_usd_net_ex_funding":rounded(sum(z["pnl_usd"] for z in s)),
    "sample_clamped_trades":[{"entry_utc":z["entry_utc"],"entry":z["entry_price"],
      "raw_stop":z["original_atr_stop"],"actual_stop":z["initial_stop"],"target":z["target"],
      "reason":z["reason"]} for z in caps[:3]]}
 return by
def main():
 raw,base_sig,manifest=source_load()
 params= {s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exits={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 assert set(params)==set(SYMS)==set(base_sig),("Mismatched symbols",params,SYMS)
 audit={"symbols":list(SYMS),"sizing_notional_usd":[750,875],
   "frozen_parameters":SELECTED,
   "methods":{"actual":"pine_events() saves ATR4h at index signal-1",
              "counterfactual":"identical 4h signal timestamps and directions; stop and target based on ATR of the JUST CLOSED signal 4h bar"},
   "data_provenance":manifest,"atr_entry_comparison":{},"simulations":{},
   "limitations":[
    "ATR correction counterfactual is a sensitivity test; not silently replacing earlier baseline.",
    "Configured SL is ATR multiple, capped to max 5 percent ENTRY price by clamp; TP not price capped.",
    "In baseline Pine handler av[i-1] is previous full 4h bar, not the just-closed signal bar av[i].",
    "5m OHLC cannot resolve whether SL or TP hit first within a candle; stop wins in same candle.",
    "BE stop may update from high/low in same bar and only be checked from next bar.",
    "The model does NOT set initial SL by bright histogram-area price extreme or use liquidity/wick/wave confirmations.",
    "Parameters optimized on 2026 Apr-May 4h signal data are applied retroactively into 2025 annual research (in-sample/hindsight parameter design for earlier history).",
    "Executed Pine formula in Delta file differs from natural-language RSI27 title; currently using actual SMA21 RSI12 EMA7 symmetric log implementation.",
    "Risk and phase pass approximate Upscale requirements; never interpret exact equity breach boundary as real platform outcome."
   ]}
 corrected={}
 for sym in SYMS:
  rows=list(raw[sym].values())
  bars=ohlc_from_5m(rows,FOUR)
  av=atr(bars)
  by_entry={b[0]+FOUR:(i,a) for i,(b,a) in enumerate(zip(bars,av))}
  corrected[sym]={}
  comparisons=[]
  for entry,old in base_sig[sym].items():
   if entry not in by_entry:raise AssertionError(f"missing signal-close 4h for {sym} {entry}")
   idx,newatr=by_entry[entry]
   if idx<1:raise AssertionError("not warm")
   oldatr=av[idx-1]
   if abs(old["atr_4h"]-oldatr)>1e-9*max(1,oldatr):
    raise AssertionError(f"ATR in original signals not av[i-1] for {sym}: {old['atr_4h']} != {oldatr}")
   corrected[sym][entry]={**old,"atr_4h":newatr}
   if START<=entry<END:
    comparisons.append({"entry_ms":entry,
      "lagged_atr":oldatr,"closed_signal_atr":newatr,
      "pct_difference":100*(newatr/oldatr-1)})
  hourly=ohlc_from_5m(rows,e.H)
  exact_correct=pine_events(hourly,atr_basis="signal_close")
  assert corrected[sym]==exact_correct, f"Explicit closed-signal ATR does not match manual correction for {sym}"
  audit["atr_entry_comparison"][sym]={
   "signal_count_year":len(comparisons),
   "avg_abs_atr_change_pct":rounded(statistics.mean(abs(x["pct_difference"]) for x in comparisons)) if comparisons else None,
   "max_abs_atr_change_pct":rounded(max(abs(x["pct_difference"]) for x in comparisons)) if comparisons else None,
   "sample":comparisons[:3]}
  print("EXPLICIT_SIGNAL_CLOSED_ATR_API_VALIDATED",sym,len(exact_correct),flush=True)
  print("ATR_SOURCE_VERIFIED",sym,json.dumps(audit["atr_entry_comparison"][sym]),flush=True)
 prev=(e.FEE,e.SPREAD);e.FEE=COST_PER_SIDE;e.SPREAD=SPREAD_ROUNDTRIP
 try:
  for notional in (750,875):
   for name,sign in (("previous_4h_atr",base_sig),("signal_closed_4h_atr",corrected)):
    for span,(start,end) in (("annual",(START,END)),("apr_jun",(VALID_END,END))):
     r=calc(raw,sign,params,exits,notional,start,end)
     group=f"{notional}/{name}/{span}"
     audit["simulations"][group]={"summary":slim(r),
        "per_asset":summarize_trades(r["trade_details"],SELECTED)}
     print("SLTP_AUDIT",group,json.dumps(audit["simulations"][group],ensure_ascii=False),flush=True)
 finally:e.FEE,e.SPREAD=prev
 O=OUT;O.mkdir(parents=True,exist_ok=True)
 path=O/"audit.json";path.write_text(json.dumps(audit,ensure_ascii=False,indent=2))
 print("SLTP_AUDIT_COMPLETED",str(path),path.stat().st_size,flush=True)
if __name__=="__main__":main()
