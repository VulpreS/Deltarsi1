"""Independent forensic decomposition of 'pretty 90d' vs slow 365d challenge.

Identical data, eight 4h Delta signals, 5m execution and frozen per-coin
SL/TP/BE/hold; compare date windows and position sizing without optimization.
Never silently change Delta math, phase rules or portfolio membership.
"""
import os,sys,json,collections,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.optimize_partial_take_4h import (
  source_load,START,TRAIN_END,VALID_END,END,SELECTED,
  COST_PER_SIDE,SPREAD_ROUNDTRIP,TZ,ms)
SYMS=tuple(e.SYMS)
O=Path("experiments/five_min_90d/year_vs_quarter_audit")
def phase_summary(r):
 return {"breach":r["breach"],"max_dd_pct":r["max_dd_pct"],
  "phase_passed":len(r["phases"]),"phase_completions":r["phases"],
  "profit_factor":r["profit_factor"],"win_rate_pct":r["win_rate_pct"],
  "closed_trades":r["trades"],"skipped_signals":r["skipped"],
  "fees_usd":r["fees"],"funding_usd":r["funding"],
  "equity_usd":r["equity"],"phase_profit_ledger_usd":r["cumulative_phase_profit_usd"]}
def by_asset(trades):
 d={s:{"closed":0,"net_realized_usd":0., "initial_stops":0,
       "moved_stops":0, "take":0,"time":0,"longs":0,"shorts":0}
    for s in SYMS}
 for t in trades:
  z=d[t["symbol"]];z["closed"]+=1;z["net_realized_usd"]+=t["pnl_usd"]
  z["longs"]+=t["side"]==1;z["shorts"]+=t["side"]==-1
  if t["reason"].startswith("stop"):
   z["moved_stops" if t["stop_updates"] else "initial_stops"]+=1
  elif t["reason"].startswith("take"):z["take"]+=1
  elif t["reason"]=="time":z["time"]+=1
 for z in d.values():z["net_realized_usd"]=round(z["net_realized_usd"],2)
 return d
def monthly(trades):
 buckets=collections.defaultdict(lambda:{"trades":0,"net_realized_usd":0.})
 for t in trades:
  key=t["exit_utc"][:7]
  b=buckets[key];b["trades"]+=1;b["net_realized_usd"]+=t["pnl_usd"]
 for b in buckets.values():b["net_realized_usd"]=round(b["net_realized_usd"],2)
 return dict(sorted(buckets.items()))
def sim(data,signals,params,exits,start,end,notional):
 return e.simulate(data,signals,SYMS,start=start,end=end,params=params,
   exit_by_symbol=exits,step=e.M,entry_profit_policy="defer",
   cap_price_stop=True,stop_cap_mode="clamp",
   collect_trades=True,collect_daily=True,partials=(),position_notional=notional)
def phase_gates(daily):
 first=[x for x in daily if x["phase"]==1]
 rules={"goal_reached":"target_met","qualification_reached":"min_qualifying_days_met",
       "consistency_passed":"30pct_consistency_met","positions_flat":"all_positions_closed",
       "new_phase_pass":"phase_1_completed"}
 out={}
 for field,key in rules.items():
  match=next((x for x in first if x[field]),None)
  out[key]=match["time"] if match else None
 # First time both goal+min days are satisfied, to discover which rule delayed passage
 enough=[x for x in first if x["goal_reached"] and x["qualification_reached"]]
 out["first_target_and_min_days"]=enough[0] if enough else None
 out["first_target_and_min_days_and_flat"]=next((x for x in enough if x["positions_flat"]),None)
 out["first_all_except_flat"]=next((x for x in enough if x["consistency_passed"]),None)
 out["first_all_except_consistency"]=next((x for x in enough if x["positions_flat"]),None)
 out["first_all_requirements"]=next((x for x in enough if x["positions_flat"] and x["consistency_passed"]),None)
 # Days when profit target reached but 30pct formula would reject, after target.
 out["goal_met_consistency_rejected_dates"]=[{
   "date":x["time"][:10],"equity":x["equity_usd"],"best_day":x["best_day_usd"],
   "ratio_pct":x["consistency_ratio_pct"],"flat":x["positions_flat"]
  } for x in enough if not x["consistency_passed"]]
 out["goal_met_positions_open_dates"]=[x["time"][:10] for x in enough
   if x["consistency_passed"] and not x["positions_flat"]]
 return out
def main():
 data,signals,manifest=source_load()
 assert len(data)==8 and set(data)==set(SYMS)
 params={s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exits={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 windows={"annual":(START,END),"jul_dec":(START,TRAIN_END),
          "jan_mar":(TRAIN_END,VALID_END),"apr_jun":(VALID_END,END)}
 result={"sources":manifest,"eight_assets":list(SYMS),
  "signal_counts_by_symbol_annual":{s:sum(START<=t<END for t in signals[s]) for s in SYMS},
  "windows":{},"notes":[
   "All calendar windows use same eight symbols, same signal routine, same 5m execution and 0.08pct per-side fee, 0.04pct roundtrip spread.",
   "Annual is one continuous initial $5000 portfolio, with virtual phase resets when completed.",
   "Each shorter window starts a SEPARATE new $5000 challenge; cannot add their phase days to infer annual challenge completion.",
   "Total closed-trade PnL by asset excludes end mark and funding, while phase/equity metrics include funding and virtual resets.",
   "Stops and take ordering stop-first; model Upscale rules not contract-verified.",
   "The user Pine source file is 'Delta', whose CODE uses SMA21->RMA RSI12->EMA7 and symmetric log Delta, despite labels claiming RSI27; CausalDelta matches its executed formula.",
   "The user discretionary wick/volume/liquidity confirmations and divergences are NOT in this signal backtest."
  ]}
 old=(e.FEE,e.SPREAD);e.FEE=COST_PER_SIDE;e.SPREAD=SPREAD_ROUNDTRIP
 try:
  for notional in (750.,875.):
   label=f"{100*notional/e.INITIAL:g}pct"
   result["windows"][label]={}
   for name,(start,end) in windows.items():
    r=sim(data,signals,params,exits,start,end,notional)
    daily=r["daily_snapshots"]
    a=by_asset(r["trade_details"])
    assert sum(v["closed"] for v in a.values())==r["trades"],(name,notional)
    assert all(v["closed"]>0 for v in a.values()),(name,notional,a)
    item={"account":phase_summary(r),"by_symbol":a,
          "monthly_realized_ex_funding":monthly(r["trade_details"]),
          "phase_gate_audit":phase_gates(daily),"daily_snapshots":daily}
    result["windows"][label][name]=item
    slim={k:v for k,v in item.items() if k!="daily_snapshots"}
    print("WINDOW_AUDIT",label,name,json.dumps(slim,ensure_ascii=False),flush=True)
 finally:e.FEE,e.SPREAD=old
 O.mkdir(parents=True,exist_ok=True)
 p=O/"audit.json";p.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print("YEAR_VS_QUARTER_COMPLETE",str(p),p.stat().st_size,flush=True)
if __name__=="__main__":main()
