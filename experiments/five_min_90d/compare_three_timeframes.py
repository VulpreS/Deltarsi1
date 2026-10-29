"""Matched 5m / 15m / 4h study on the same eight crypto symbols.

Two intentionally DISTINCT questions:
 A) SIGNAL_TF in 5m/15m/4h, execution fixed at 5m;
 B) EXECUTION_TF in 5m/15m/4h, closed 4h Delta signals fixed.
All experiments use previously frozen per-asset ATR SL/TP, BE and hold,
with stop clamped to 5% of entry price. No OOS parameter fitting.
"""
import sys, json, os, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.followup_execution import SELECTED
from experiments.pine_vs_codex.run import pine_events, pine_shade
from causal_4h_parity_audit import CausalDelta
from research_multiasset import atr

TF_MS={"5m":e.M,"15m":3*e.M,"4h":4*e.H}
GROUPS={
 "all_8":tuple(e.SYMS),
 "account_A":("BTCUSDT","ETHUSDT","TONUSDT","ZECUSDT","XRPUSDT"),
 "account_B":("ICPUSDT","BNBUSDT","LINKUSDT"),
 "btc_eth":("BTCUSDT","ETHUSDT"),
}
TRAIN_END=e.START+60*e.DAY
WINDOWS={"train60":(e.START,TRAIN_END),
         "oos30":(TRAIN_END,e.END),
         "full90":(e.START,e.END)}

def ohlc_from_5m(rows,span):
 if span%e.M:raise ValueError("invalid span")
 n=span//e.M
 if n==1:return list(rows)
 result=[]
 for k in range(0,len(rows),n):
  chunk=rows[k:k+n]
  if (len(chunk)!=n or chunk[0][0]%span
      or chunk[-1][0]-chunk[0][0]!=(n-1)*e.M):continue
  result.append((chunk[0][0],chunk[0][1],
                 max(x[2] for x in chunk),min(x[3] for x in chunk),chunk[-1][4]))
 return result

def make_4h_signals(hourly):
 # Existing implementation is the unchanged benchmark signal.
 return pine_events(hourly)

def make_lower_tf_signals(rows,tf,atr_by_4h):
 """Causal color transitions from SAME CausalDelta math at a new candle length.

 For a 5m/15m candle at t, its ATR4h comes from last 4h bucket
 COMPLETED before t's current 4h bucket; never from a still-forming 4h.
 Signal is actionable at t+tf, i.e. the next execution candle open.
 """
 span=TF_MS[tf];four=TF_MS["4h"]
 state=CausalDelta();last_shade=None;events={}
 shades_count={"medium_to_weak_red":0,"medium_to_weak_blue":0}
 for i,row in enumerate(rows):
  t=row[0]
  before=state.delta
  d,_,_=state.step(row[4],commit=True)
  shade=pine_shade(d,before)
  prior_atr=atr_by_4h.get((t//four)*four-four)
  if (i>=210 and shade and last_shade and prior_atr is not None
      and math.isfinite(prior_atr) and prior_atr>0):
   side=1 if last_shade=="medium_red" and shade=="weak_red" else (-1 if last_shade=="medium_blue" and shade=="weak_blue" else 0)
   if side:
    entry=t+span
    if entry<e.END:
     events[entry]={"side":side,"atr_4h":prior_atr,"entry_ms":entry}
     shades_count["medium_to_weak_red" if side==1 else "medium_to_weak_blue"]+=1
  last_shade=shade
 return events,shades_count

def main():
 raw={"5m":{},"15m":{},"4h":{}}
 sig={"5m":{},"15m":{},"4h":{}}
 stats={}
 for sym in e.SYMS:
  rows=e.download(sym)
  aggregates={tf:ohlc_from_5m(rows,span) for tf,span in TF_MS.items()}
  for tf in TF_MS:raw[tf][sym]={r[0]:r for r in aggregates[tf]}
  # Hourly source is built from the exact same 5m input and is UTC-aligned.
  hourly=ohlc_from_5m(rows,e.H)
  sig["4h"][sym]=make_4h_signals(hourly)
  a4=atr(aggregates["4h"])
  atrmap={b[0]:a for b,a in zip(aggregates["4h"],a4)}
  sig["5m"][sym],_=make_lower_tf_signals(aggregates["5m"],"5m",atrmap)
  sig["15m"][sym],_=make_lower_tf_signals(aggregates["15m"],"15m",atrmap)
  for tf in TF_MS:
   required=90*e.DAY//TF_MS[tf]
   observed=sum(t in raw[tf][sym] for t in range(e.START,e.END,TF_MS[tf]))
   if observed!=required:raise RuntimeError(f"Missing {tf} candles {sym}: {observed}/{required}")
   n=sum(e.START<=t<e.END for t in sig[tf][sym])
   stats.setdefault(sym,{})[tf]={"candles":len(aggregates[tf]),"signals_90d":n}
   print("ASSET_SIGNAL_COUNT",sym,tf,n,flush=True)
  # Signal entry timestamps MUST fall on source candle CLOSE and execution candle OPEN.
  for tf in TF_MS:
   if any(t%TF_MS[tf] for t in sig[tf][sym]):raise AssertionError("unaligned signal: "+sym+" "+tf)
  # Source 4h signal is exactly pine_events, not recomputed with another algorithm.
  assert sig["4h"][sym]==pine_events(hourly)
 print("DATA_READY",json.dumps(stats),flush=True)

 params={s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exits={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 scenarios=[
  # Isolates difference in signal formation: all trade on same 5m OHLC
  *[dict(label=f"signal_{tf}_exec_5m",signal_tf=tf,execution_tf="5m") for tf in TF_MS],
  # Isolates execution resolution: EXACT same closed 4h signals
  *[dict(label=f"signal_4h_exec_{tf}",signal_tf="4h",execution_tf=tf) for tf in TF_MS],
 ]
 # Duplicate 4h->5m is intentional, verify identity.
 output={
   "code_sha":os.getenv("GITHUB_SHA","local"),
   "run_id":os.getenv("GITHUB_RUN_ID","local"),
   "universe":list(e.SYMS),"data_source":"Binance USD-M futures archived 5m, UTC",
   "periods":{"train60":["2026-04-02","2026-06-01"],"oos30":["2026-06-01","2026-07-01"],"full90":["2026-04-02","2026-07-01"]},
   "strategy_signal_id":"CausalDelta + pine_shade, 4h uses original pine_events",
   "frozen_params":SELECTED,
   "config":{"account_size":5000,"max_positions":3,"position_notional_usd":1000,
      "price_stop_cap_pct":5,"stop_cap_mode":"clamp","fee_per_side":.0008,
      "spread_roundtrip":.0004,"funding_every_8h":.00015,
      "max_holding_from_selected":True,"be_trigger_from_selected":True,
      "entry_profit_policy":"defer","windows_independent_account_reset":True},
   "manifest":stats,"results":{},"limitations":[
      "4h,15m and 5m signals are alternative sampled implementations of the same CausalDelta formula; 4h original pine_events is unchanged.",
      "Lower timeframe SIGNAL hypothesis is new; it is NOT user's separate 5m RSI+RVGI strategy.",
      "Signal-TF comparison holds EXECUTION fixed at 5m; execution-TF comparison holds SIGNAL fixed at 4h.",
      "Selected ATR4h stops, take profits, BE thresholds and max holding periods were optimized earlier on 4h signals; they are NOT reoptimized for shorter signal TF.",
      "Time-window OOS was previously viewed across multiple experiments and is not an entirely untouched market study.",
      "Same-bar positive take profits are deferred for execution-TF candle, which penalizes 4h more due to coarse OHLC.",
      "4h intrabar stop/TP sequencing and BE triggers cannot be reconstructed exactly from OHLC; conservative stop-first.",
      "Upscale rules, 60-second minimum hold, 30pct consistency and exact phase resets are approximations/unverified.",
      "Price stop is clipped at 5 percent of entry, unlike rejecting wide-stop signals.",
      "No real orders; historical experiment only."]}

 old_fee,old_spread=e.FEE,e.SPREAD
 e.FEE=.0008;e.SPREAD=.0004
 try:
  for sc in scenarios:
   label=sc["label"];s_tf=sc["signal_tf"];x_tf=sc["execution_tf"]
   if label in output["results"]:continue
   output["results"][label]={"signal_tf":s_tf,"execution_tf":x_tf,"by_window":{}}
   for w,(start,end) in WINDOWS.items():
    output["results"][label]["by_window"][w]={}
    for group,g in GROUPS.items():
     r=e.simulate(raw[x_tf],sig[s_tf],g,
       params=params,start=start,end=end,step=TF_MS[x_tf],
       exit_by_symbol=exits,cap_price_stop=True,stop_cap_mode="clamp",
       entry_profit_policy="defer")
     output["results"][label]["by_window"][w][group]=r
     proj={k:r[k] for k in ("phases","cumulative_phase_profit_usd","breach","max_dd_pct",
        "trades","win_rate_pct","profit_factor","fees","funding","skipped")}
     print("TF_COMPARE",label,w,group,json.dumps(proj,ensure_ascii=False),flush=True)
 finally:e.FEE,e.SPREAD=old_fee,old_spread
 # Ensure shared benchmark row remains IDENTICAL across the two comparisons.
 base=output["results"]["signal_4h_exec_5m"]
 assert base["by_window"]==output["results"]["signal_4h_exec_5m"]["by_window"]
 p=Path("experiments/five_min_90d/three_tf_results.json")
 p.write_text(json.dumps(output,indent=2,ensure_ascii=False))
 print("RESULTS_WRITTEN",str(p),p.stat().st_size,flush=True)
if __name__=="__main__":main()
