"""Counterfactual isolate effect of Upscale's 30% API consistency on stage passing.

SAME initial $10000, SAME size $2000/leg, SAME 6 coins, SAME 5m
candles, SL/TP, trailing and 48h, 3 slots; only API-enabled flag
changes (so phase consistency applies) and the unobserved 60s correction.
No-API account is an illustrative regular Basic with HUMAN-CONFIRMED manual
orders, NOT approval for browser UI automation. This makes the
previous $5000/232d vs $10000API/314d comparison controlled.

Original code from experiments/portfolio_six_no_icp_zec_20pct,
2026-10-29. All modeled rules are approximation, NOT Upscale statement.
"""
import sys,json,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.portfolio_six_no_icp_zec_20pct.compare_add_second_signal import (
 sim,ASSETS,ACCOUNT,MODES,START,VALID_END,END,H)
from experiments.new_instructions_8asset_48h.backtest import check_document
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

DEST=Path("experiments/portfolio_six_no_icp_zec_20pct/counterfactual_10k")
def compact(z):
 return dict(closed_trades=z["number_closed"],winrate=z["win_rate_pct"],
    pf=z["profit_factor"],closed_pnl_all_phases=z["closed_pnl_usd"],
    equity=z["final_equity_usd"],breach=z["breach"],
    stage_days=[v["days"] for v in z["phases"]],
    stage_dates=[v["completed"] for v in z["phases"]],
    phase_realized_gains=[v["realized_profit"] for v in z["phases"]],
    funded_realized=z["funded_profit_realized_usd"],
    trade_adds=z["actual_adds"],
    api60s_gross_excluded=z["worst_fund_pnl_conservative"],
    API60s_events=z["ambiguous_api_close_60s"])

def main():
 params={s:check_document()[s] for s in ASSETS}
 full,_,manifest=source_load()
 events={}
 for s in ASSETS:
  hrs=ohlc_from_5m(sorted(full[s].values()),H)
  events[s]=pine_events(hrs,expanded=False,atr_basis="prior")
 cases={
  "Basic_10000_without_API_manual":dict(ACCOUNT["Basic_10000_API"],name="Basic_10000_without_API_manual",api=False),
  "Basic_10000_with_API":dict(ACCOUNT["Basic_10000_API"])}
 d=dict(title="10k Basic manual/no API vs 10k Basic API (causal trade replay same $20% each)",
   disclaimer="Browser-based programmed trading NOT endorsed: this is a mathematical manual counterfactual; require direct written Upscale permission before automating UI.",
   configs=dict(assets=ASSETS, initial=10000,slot_usd=2000,slots=3),
   source_manifest={s:manifest[s] for s in ASSETS},results={},comparisons={})
 for period,st,en in (("annual",START,END),("quarter",VALID_END,END)):
  for mode in ("baseline_48","add_loss_second_48"):
   curr={}
   for c_name,cfg in cases.items():
    r,details=sim(full,events,params,ASSETS,cfg,st,en,mode,False,True)
    key=f"{period}/{mode}/{c_name}"
    d["results"][key]=dict(summary=r,details=details)
    curr[c_name]=r
    print("CONTROLLED_API_COUNTERFACTUAL",key,json.dumps(compact(r),ensure_ascii=False),flush=True)
   a=curr["Basic_10000_without_API_manual"];b=curr["Basic_10000_with_API"]
   if len(a["phases"])==2 and len(b["phases"])==2:
    comparison=dict(
     manual_stage1_days=a["phases"][0]["days"],api_stage1_days=b["phases"][0]["days"],
     manual_total_to_funded_days=sum(z["days"] for z in a["phases"]),
     api_total_to_funded_days=sum(z["days"] for z in b["phases"]),
     stage1_days_saved=b["phases"][0]["days"]-a["phases"][0]["days"],
     days_saved_to_funded=sum(z["days"] for z in b["phases"])-sum(z["days"] for z in a["phases"]),
     same_trades=a["number_closed"]==b["number_closed"],
     same_wr=a["win_rate_pct"]==b["win_rate_pct"],
     gross_disallowed_60s=b["worst_fund_pnl_conservative"])
   else:comparison=dict(manual_phases=len(a["phases"]),api_phases=len(b["phases"]))
   d["comparisons"][f"{period}/{mode}"]=comparison
   print("CONTROLLED_API_DIFFERENCE",period,mode,json.dumps(comparison,ensure_ascii=False),flush=True)
 # validate same exact engine API reference from verified previous run
 x=d["results"]["annual/baseline_48/Basic_10000_with_API"]["summary"]
 assert abs(x["closed_pnl_usd"]-4091.2968)<.03 and x["number_closed"]==177, (x["closed_pnl_usd"],x["number_closed"])
 assert len(x["phases"])==2 and abs(sum(p["days"] for p in x["phases"])-314.1666)<.02
 assert x["breach"] is None
 DEST.mkdir(parents=True,exist_ok=True)
 f=DEST/"results.json";f.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
 print("CONTROLLED_10K_API_COMPARISON_COMPLETE",str(f),f.stat().st_size,flush=True)
if __name__=="__main__":main()
