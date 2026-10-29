"""Out-of-sample validation of train-only selected asset subsets.

Frozen from Actions run 40885930656 (first 60 days), not selected on OOS.
For each TF, two prespecified train-only eligibility rules:
  quality = positive per-asset training PNL + PF>=1 + max DD<=5%;
  top3 = top 3 per-coin training objective scores (may include high DD).
Use same 5m execution engine, same risk/cost assumptions, same signal generation.
"""
import sys, json, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.compare_three_timeframes import (
 TF_MS,WINDOWS,ohlc_from_5m,make_lower_tf_signals,make_4h_signals)
from research_multiasset import atr

# Freeze values from completed training optimization. All SL/TP are *ATR(4h)*.
CHOICES={
 "5m":{
 "BTCUSDT":(1,2,None,12),"ETHUSDT":(2,2,.015,48),
 "ICPUSDT":(2,1,.015,48),"TONUSDT":(.5,2,None,12),
 "BNBUSDT":(2,2,.01,24),"ZECUSDT":(1,2,None,24),
 "XRPUSDT":(2,2,.015,48),"LINKUSDT":(2,2,.015,48)},
 "15m":{
 "BTCUSDT":(2,2,None,24),"ETHUSDT":(2,2,None,24),
 "ICPUSDT":(2,1,.015,48),"TONUSDT":(1,2,None,4),
 "BNBUSDT":(1,2,.015,48),"ZECUSDT":(.25,2,None,24),
 "XRPUSDT":(2,1,None,24),"LINKUSDT":(2,2,None,24)}
}
# Training metrics from prior run (never OOS). Eligibility based on TRAIN only.
QUALITY={
 "5m":("ETHUSDT","ICPUSDT","XRPUSDT","LINKUSDT"),
 "15m":("ETHUSDT","TONUSDT","BNBUSDT","XRPUSDT")}
TOP3={
 "5m":("ICPUSDT","ZECUSDT","ETHUSDT"),
 "15m":("ETHUSDT","TONUSDT","XRPUSDT")}

def main():
 raw={};signals={"5m":{},"15m":{}}
 for sym in e.SYMS:
  rows=e.download(sym)
  raw[sym]={x[0]:x for x in rows}
  four=ohlc_from_5m(rows,4*e.H)
  amap={r[0]:a for r,a in zip(four,atr(four))}
  for tf in ("5m","15m"):
   sampled=ohlc_from_5m(rows,TF_MS[tf])
   signals[tf][sym],_=make_lower_tf_signals(sampled,tf,amap)
 prev=e.FEE,e.SPREAD;e.FEE,e.SPREAD=.0008,.0004
 out={"run_sha":os.getenv("GITHUB_SHA"),"run_id":os.getenv("GITHUB_RUN_ID"),
  "source_optimization_run":40885930656,"choices":CHOICES,
  "train_only_rules":{"quality":"training per-asset PNL positive and PF >= 1 and maxDD <=5%; no OOS selection","top3":"training objective top3 per TF"},
  "groups":{"quality":QUALITY,"top3":TOP3},"results":{},"limitations":[
  "OOS has been examined in separate earlier experiments but not used for asset selection.",
  "Signal source same project CausalDelta, sampled at 5m/15m; all execution on 5m.",
  "Stop price clamped at 5%; cost fee .08% each side, .04% roundtrip spread, funding .015%/8h.",
  "One $5000 account per group, $1000 notional per position, max three positions.",
  "Small training samples and cross-coin coupling make selected portfolio strongly uncertain.",
  "Same-bar profit held to next candle; no tick-level Upscale 60-sec proof." ]}
 try:
  for tf in ("5m","15m"):
   p={sym:(sl,tp,None,None) for sym,(sl,tp,be,hold) in CHOICES[tf].items()}
   ex={sym:{"be":be,"hold":hold} for sym,(sl,tp,be,hold) in CHOICES[tf].items()}
   out["results"][tf]={}
   for selection,g in (("all_8",tuple(e.SYMS)),("quality",QUALITY[tf]),("top3",TOP3[tf])):
    out["results"][tf][selection]={}
    for w,(start,end) in WINDOWS.items():
     r=e.simulate(raw,signals[tf],g,start=start,end=end,params=p,exit_by_symbol=ex,
                  cap_price_stop=True,stop_cap_mode="clamp",entry_profit_policy="defer")
     out["results"][tf][selection][w]=r
     brief={k:r[k] for k in ("phases","cumulative_phase_profit_usd","breach","max_dd_pct","trades","win_rate_pct","profit_factor","fees","funding")}
     print("SUBSET",tf,selection,w,json.dumps(brief,ensure_ascii=False),flush=True)
 finally:
  e.FEE,e.SPREAD=prev
 p=Path("experiments/five_min_90d/lower_tf_subsets_results.json")
 p.write_text(json.dumps(out,indent=2,ensure_ascii=False))
 print("RESULT_FILE",str(p),flush=True)
if __name__=="__main__":main()
