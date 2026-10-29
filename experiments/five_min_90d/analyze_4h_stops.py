"""Explain every protective stop of the existing 4h Delta portfolio.

Replays SAME 4h pine_events, 8 symbols, per-coin SL/TP/BE/hold,
$1000 notional, 5m execution, 5%-price clamp and stressed trading costs.
Produces an exact optional execution ledger, detailed stop timeline with
4h Delta values at entry, last available before stop, post-stop +1..+12
completed 4h candles, 4h closes/wicks and recovery metrics, descriptive
cross-cohort comparisons and precommitted diagnostic classifications.

No future indicator state is used as an ENTRY predictor.
"""
import sys, math, csv, json, bisect, os, statistics, hashlib, datetime as dt
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.compare_three_timeframes import SELECTED,ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events,pine_shade
from causal_4h_parity_audit import CausalDelta
from research_multiasset import atr

OUT=Path("experiments/five_min_90d/stops_4h")
FOUR=4*e.H
HORIZONS=[1,2,3,4,5,6,8,10,12]
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def r(x,n=3):
 if x is None or not isinstance(x,(float,int)) or not math.isfinite(x):return None
 return round(float(x),n)
def pct(x):
 return r(100*x)
def med(values):
 x=[z for z in values if z is not None and math.isfinite(z)]
 return r(statistics.median(x)) if x else None
def avg(values):
 x=[z for z in values if z is not None and math.isfinite(z)]
 return r(statistics.mean(x)) if x else None
def json_file(path,v):
 path.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def csv_file(path,records):
 if not records:return
 fields=list(dict.fromkeys(k for rec in records for k in rec))
 with path.open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for rec in records:w.writerow(rec)
def info(c):
 if c is None:return None
 return dict(time_utc=iso(c["close_ms"]),delta=r(c["delta"],4),
    color=c["color"],rsi=r(c["rsi"],3),
    close=r(c["close"],6),high=r(c["high"],6),low=r(c["low"],6),
    atr4=r(c["atr4"],6))
def history(rows):
 state=CausalDelta();ret=[];av=atr(rows)
 for i,b in enumerate(rows):
  d_prev=state.delta
  d,_,rsi=state.step(b[4],commit=True)
  color=pine_shade(d,d_prev)
  ret.append({"open_ms":b[0],"close_ms":b[0]+FOUR,
    "open":b[1],"high":b[2],"low":b[3],"close":b[4],
    "delta":d,"color":color,"rsi":rsi,"atr4":av[i]})
 return ret
def get_last(hist,ends,t):
 j=bisect.bisect_right(ends,t)-1
 return (hist[j],j) if j>=0 else (None,-1)
def category(z):
 if z["reason"] in ("stop","stop_gap"):
  return "breakeven_stop" if z["is_breakeven_stop"] else "initial_stop"
 return z["reason"]
def entry_metrics(trade,hist,ends):
 c,j=get_last(hist,ends,trade["entry_ms"])
 previous=hist[j-1] if j>0 else None
 previous2=hist[j-2] if j>1 else None
 d=c["delta"] if c else None
 prev_d=previous["delta"] if previous else None
 prev2_d=previous2["delta"] if previous2 else None
 candle_range=c["high"]-c["low"] if c else 0
 wick_buy=(min(c["open"],c["close"])-c["low"])/candle_range if candle_range else None
 wick_sell=(c["high"]-max(c["open"],c["close"]))/candle_range if candle_range else None
 # Diagnostic only; does not activate a new trading filter.
 return {
  "entry_hist":info(c),"entry_previous_hist":info(previous),
  "entry_previous2_hist":info(previous2),
  "entry_hist_abs_delta":r(abs(d) if d is not None else None,4),
  "entry_hist_change_abs":r(abs(d)-abs(prev_d) if d is not None and prev_d is not None else None,4),
  "prior_hist_change_abs":r(abs(prev_d)-abs(prev2_d) if prev_d is not None and prev2_d is not None else None,4),
  "entry_signal_bar_lower_wick_fraction":r(wick_buy,4),
  "entry_signal_bar_upper_wick_fraction":r(wick_sell,4),
  "entry_signal_bar_range_pct":r(100*candle_range/c["close"] if c else None),
  "entry_stop_distance_pct":r(trade["initial_risk_price_pct"]),
  "atr4_pct_of_entry":r(100*c["atr4"]/trade["entry_price"] if c else None),
  "entry_candle_index":j
 }
def stop_features(trade,hist,ends):
 last,last_j=get_last(hist,ends,trade["exit_bar_open_ms"])  # 4h COMPLETED strictly before stop bar open
 ent,ent_j=get_last(hist,ends,trade["entry_ms"])
 sign= -trade["side"] # negative Delta for long-red impulse, positive Delta for short-blue impulse
 known_d=last["delta"] if last else None
 ent_d=ent["delta"] if ent else None
 available_between=hist[ent_j+1:last_j+1] if last_j>ent_j else []
 relapse=sum(1 for c in available_between if
     math.isfinite(c["delta"]) and math.isfinite(ent_d)
     and c["delta"]*ent_d>0 and abs(c["delta"])>abs(ent_d))
 flipped_before=any(math.isfinite(c["delta"]) and c["delta"]*trade["side"]>0
    for c in available_between)
 prior=hist[last_j-1] if last_j>0 else None
 strengthened_since_entry=bool(math.isfinite(known_d) and math.isfinite(ent_d) and
  known_d*ent_d>0 and abs(known_d)>abs(ent_d)) if known_d is not None else None
 strengthened_last=bool(prior and math.isfinite(known_d) and math.isfinite(prior["delta"]) and
  known_d*prior["delta"]>0 and abs(known_d)>abs(prior["delta"])) if known_d is not None else None
 return {
  "stop_last_visible_hist":info(last),
  "complete_4h_bars_between_entry_and_stop":max(last_j-ent_j,0),
  "hist_reacceleration_before_stop_any":bool(relapse),
  "hist_opposite_sign_seen_before_stop":bool(flipped_before),
  "hist_abs_stronger_than_entry_before_stop":strengthened_since_entry,
  "hist_abs_stronger_than_previous_before_stop":strengthened_last,
  "entry_hist_index":ent_j,
  "stop_last_visible_index":last_j
 }
def after_stop(trade,hist,ends):
 # All future data in this function is POST-EVENT EXPLANATION, not candidate input.
 j=bisect.bisect_right(ends,trade["exit_known_ms"])
 entry=trade["entry_price"];stop=trade["exit_price"];target=trade["target"];side=trade["side"]
 rows=[];recovered=None;target_hit=None;hist_flip=None;hist_reacc=None
 entry_d=next((h["delta"] for h in hist if h["close_ms"]==trade["entry_ms"]),None)
 close_ref=trade["exit_price"]
 for k in range(1,13):
  if j+k-1>=len(hist):break
  c=hist[j+k-1]
  high=c["high"];low=c["low"];end=c["close"]
  # Direction-adjusted: + means favorable direction for original trade.
  close_move_pct=100*side*(end/entry-1)
  stop_to_close_pct=100*side*(end/stop-1)
  entry_recovered=(high>=entry if side==1 else low<=entry)
  target_reached=(high>=target if side==1 else low<=target)
  original_trend_renewed=math.isfinite(c["delta"]) and c["delta"]*(-side)>0
  has_flipped=math.isfinite(c["delta"]) and c["delta"]*side>0
  rows.append({"k":k,"time_utc":iso(c["close_ms"]),"hist_delta":r(c["delta"],4),"color":c["color"],
   "hist_sign_favorable":bool(has_flipped),
   "hist_still_original_impulse":bool(original_trend_renewed),
   "close_move_from_entry_pct":r(close_move_pct),
   "close_move_from_stop_pct":r(stop_to_close_pct),
   "bar_favorable_extreme_from_entry_pct":r(100*side*((high if side==1 else low)/entry-1)),
   "bar_adverse_extreme_from_entry_pct":r(-100*side*((low if side==1 else high)/entry-1)),
   "recovers_entry_intrabar":bool(entry_recovered),"touches_original_tp_intrabar":bool(target_reached),
   "high":r(high,6),"low":r(low,6),"close":r(end,6)})
  if entry_recovered and recovered is None:recovered=k
  if target_reached and target_hit is None:target_hit=k
  if has_flipped and hist_flip is None:hist_flip=k
  if original_trend_renewed and hist_reacc is None:hist_reacc=k
 return rows,dict(recover_entry_first_k=recovered,reach_original_tp_first_k=target_hit,
     favorable_delta_sign_first_k=hist_flip,
     original_direction_delta_first_k=hist_reacc,
     measured_post_bars=len(rows))
def after_entry(trade,hist,ends):
 j=bisect.bisect_right(ends,trade["entry_ms"])
 rows=[]
 for k in range(1,13):
  if j+k-1>=len(hist):break
  c=hist[j+k-1]
  # Mark whether this candle was closed and therefore known BEFORE stop.
  known_before_stop=c["close_ms"]<=trade["exit_bar_open_ms"]
  rows.append({"k":k,"time_utc":iso(c["close_ms"]),
    "delta":r(c["delta"],4),"color":c["color"],
    "close_dir_pct":r(100*trade["side"]*(c["close"]/trade["entry_price"]-1)),
    "known_before_stop":known_before_stop,
    "after_stop":c["close_ms"]>trade["exit_known_ms"]})
 return rows
def counts(group):
 return {k:sum(z.get(k) is True for z in group) for k in
   ("hist_reacceleration_before_stop_any","hist_opposite_sign_seen_before_stop",
    "hist_abs_stronger_than_entry_before_stop","hist_abs_stronger_than_previous_before_stop")}
def report_aggregates(records):
 stop=[z for z in records if z["category"]=="initial_stop"]
 be=[z for z in records if z["category"]=="breakeven_stop"]
 control=[z for z in records if z["category"] not in ("initial_stop","breakeven_stop")]
 by_symbol={}
 for symbol in e.SYMS:
  sub=[z for z in records if z["symbol"]==symbol]
  by_symbol[symbol]={"total":len(sub),
   "initial_stop":sum(z["category"]=="initial_stop" for z in sub),
   "breakeven_stop":sum(z["category"]=="breakeven_stop" for z in sub),
   "other":sum(z["category"] not in ("initial_stop","breakeven_stop") for z in sub)}
 def group_metrics(g):
  return {
   "n":len(g),
   "avg_hold_hours":avg(z["hold_hours"] for z in g),
   "median_hold_hours":med(z["hold_hours"] for z in g),
   "avg_net_trade_pnl_usd":avg(z["pnl_usd"] for z in g),
   "median_mfe_pct":med(z["mfe_pct"] for z in g),
   "median_mae_pct":med(z["mae_pct"] for z in g),
   "entry_hist_abs_median":med(z.get("entry_hist_abs_delta") for z in g),
   "entry_atr4_pct_median":med(z.get("atr4_pct_of_entry") for z in g),
   "signal_bar_lower_wick_median":med(z.get("entry_signal_bar_lower_wick_fraction") for z in g),
   "signal_bar_upper_wick_median":med(z.get("entry_signal_bar_upper_wick_fraction") for z in g),
   "stop_visible_hist_change_counts":counts(g),
   "stopped_with_no_new_closed_4h_candle":sum(z.get("complete_4h_bars_between_entry_and_stop")==0 for z in g)
  }
 recovery={}
 stop_group=stop+be
 for N in HORIZONS:
  eligible=[z for z in stop_group if z["measured_post_bars"]>=N]
  initial_eligible=[z for z in stop if z["measured_post_bars"]>=N]
  def stat(g,attr):
   return {"count":sum(z.get(attr) is not None and z[attr]<=N for z in g),
           "denominator":len(g),
           "percent":r(100*sum(z.get(attr) is not None and z[attr]<=N for z in g)/len(g),1) if g else None}
  recovery[str(N)]={"all_stops_recover_entry":stat(eligible,"recover_entry_first_k"),
    "all_stops_touch_original_tp":stat(eligible,"reach_original_tp_first_k"),
    "initial_stops_recover_entry":stat(initial_eligible,"recover_entry_first_k"),
    "all_stops_delta_favorable_sign":stat(eligible,"favorable_delta_sign_first_k")}
 # histogram changes by first N post-4h candles (even if the signal isn't executable now)
 hist_avg_by_k={}
 for k in range(1,13):
  sub=[z["post_stop_bars"][k-1] for z in stop_group if len(z["post_stop_bars"])>=k]
  hist_avg_by_k[str(k)]={
   "n":len(sub),
   "mean_delta_abs":avg(abs(x["hist_delta"]) for x in sub if x["hist_delta"] is not None),
   "new_color":dict(Counter(x["color"] for x in sub)),
   "original_trend_delta_count":sum(x["hist_still_original_impulse"] for x in sub),
   "favorable_sign_delta_count":sum(x["hist_sign_favorable"] for x in sub),
   "median_directional_close_from_stop_pct":med(x["close_move_from_stop_pct"] for x in sub),
   "median_directional_close_from_entry_pct":med(x["close_move_from_entry_pct"] for x in sub)}
 return {"total_trades":len(records),"stop_loss":len(stop),"breakeven_stops":len(be),
         "other_exits":dict(Counter(z["reason"] for z in control)),
         "by_symbol":by_symbol,
         "initial_stop_metrics":group_metrics(stop),
         "breakeven_stop_metrics":group_metrics(be),
         "non_stop_metrics":group_metrics(control),
         "stop_recovery_by_horizon_4h_candles":recovery,
         "post_stop_histogram_by_k":hist_avg_by_k,
         "complete_4h_coverage":dict(Counter(z["measured_post_bars"] for z in stop_group))}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 raw={};sig={};history_by_sym={};end_by_sym={};data_manifest={}
 for sym in e.SYMS:
  rows=e.download(sym)
  raw[sym]={b[0]:b for b in rows}
  hourly=ohlc_from_5m(rows,e.H)
  bars4=ohlc_from_5m(rows,FOUR)
  sig[sym]=pine_events(hourly)
  hs=history(bars4)
  history_by_sym[sym]=hs;end_by_sym[sym]=[x["close_ms"] for x in hs]
  data_manifest[sym]={"rows_5m":len(rows),"complete_4h":len(hs),
   "signals_last90":sum(e.START<=t<e.END for t in sig[sym]),
   "source_monthly_archive":"Binance futures USDT-M 2026-02..06",
   "source_5m_sha256":hashlib.sha256("".join(f"{x[0]}|{x[1]}|{x[2]}|{x[3]}|{x[4]};" for x in rows).encode()).hexdigest()}
  print("DATA",sym,json.dumps(data_manifest[sym]),flush=True)
 params={s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exits={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 prev_fee,prev_spread=e.FEE,e.SPREAD
 try:
  e.FEE,e.SPREAD=.0008,.0004
  simulation=e.simulate(raw,sig,tuple(e.SYMS),start=e.START,end=e.END,
        params=params,exit_by_symbol=exits,step=e.M,entry_profit_policy="defer",
        cap_price_stop=True,stop_cap_mode="clamp",collect_trades=True)
 finally:
  e.FEE,e.SPREAD=prev_fee,prev_spread
 details=simulation.pop("trade_details")
 print("REPLAY_SUMMARY",json.dumps({k:simulation[k] for k in
   ("trades","phases","max_dd_pct","breach","win_rate_pct","profit_factor","cumulative_phase_profit_usd")},ensure_ascii=False),flush=True)
 if simulation["trades"]!=64 or len(details)!=64 or abs(simulation["max_dd_pct"]-3.689)>.02:
  raise AssertionError("4h replay not identical to published 40884942989 reference: "+
   str((simulation["trades"],len(details),simulation["max_dd_pct"])))
 records=[];stops=[];csvwide=[];long_rows=[];entrypath=[]
 for i,t in enumerate(details,1):
  sym=t["symbol"];hs=history_by_sym[sym];ends=end_by_sym[sym]
  ent=entry_metrics(t,hs,ends)
  stopfeat=stop_features(t,hs,ends)
  post,postmeta=after_stop(t,hs,ends)
  entrybars=after_entry(t,hs,ends)
  cat=category(t)
  z={**t,**{k:v for k,v in ent.items() if k!="entry_candle_index"},
   **{k:v for k,v in stopfeat.items() if k not in ("entry_hist_index","stop_last_visible_index")},
   **postmeta,"category":cat,"id":f"T{i:03d}","post_stop_bars":post,
   "post_entry_bars":entrybars}
  records.append(z)
  if cat not in ("initial_stop","breakeven_stop"):continue
  stops.append(z)
  flat={k:z[k] for k in (
   "id","symbol","side","phase","entry_utc","exit_utc","reason","category",
   "entry_price","exit_price","initial_stop","target","initial_risk_price_pct",
   "hold_hours","pnl_usd","mfe_pct","mae_pct","entry_hist_abs_delta",
   "entry_hist_change_abs","atr4_pct_of_entry",
   "complete_4h_bars_between_entry_and_stop",
   "hist_reacceleration_before_stop_any","hist_opposite_sign_seen_before_stop",
   "hist_abs_stronger_than_entry_before_stop","hist_abs_stronger_than_previous_before_stop",
   "recover_entry_first_k","reach_original_tp_first_k",
   "favorable_delta_sign_first_k","measured_post_bars")}
  for label,key in (("at_entry","entry_hist"),("last_known_before_stop","stop_last_visible_hist")):
   c=z.get(key)
   flat[label+"_delta"]=c["delta"] if c else None
   flat[label+"_color"]=c["color"] if c else None
  for k in HORIZONS:
   c=next((bar for bar in post if bar["k"]==k),None)
   flat[f"after_stop_{k}_delta"]=c["hist_delta"] if c else None
   flat[f"after_stop_{k}_color"]=c["color"] if c else None
   flat[f"after_stop_{k}_close_from_entry_pct"]=c["close_move_from_entry_pct"] if c else None
   flat[f"after_stop_{k}_entry_recovered"]=c["recovers_entry_intrabar"] if c else None
  csvwide.append(flat)
  for b in post:
   long_rows.append({"id":z["id"],"symbol":sym,"side":t["side"],"category":cat,
     "entry_utc":z["entry_utc"],"stop_exit_utc":z["exit_utc"],**b})
  for b in entrybars:
   entrypath.append({"id":z["id"],"symbol":sym,"side":t["side"],"category":cat,**b})
 aggregate=report_aggregates(records)
 json_file(OUT/"all_trades.json",records)
 json_file(OUT/"all_stop_trades.json",stops)
 csv_file(OUT/"stop_trades_wide.csv",csvwide)
 csv_file(OUT/"post_stop_4h_path.csv",long_rows)
 csv_file(OUT/"post_entry_4h_path.csv",entrypath)
 manifest={"code_sha":os.getenv("GITHUB_SHA","local"),"run_id":os.getenv("GITHUB_RUN_ID","local"),
  "source_comparison_run":40884942989,"signal_implementation":"pine_events/CausalDelta (unchanged)",
  "assets":list(e.SYMS),
  "data_manifest":data_manifest,
  "period":"2026-04-02 (UTC) to 2026-07-01 (UTC) 90 days",
  "stop_definition":"initial stop and stop_gap on original/clamped price SL; BE categorized separately if trailing stop moved to entry",
  "post_candles":"1..12 fully completed 4h candles strictly AFTER the 5m stop exit candle closes (excludes ambiguous candle at stop time)",
  "price_recovery":"for original long, post-stop 4h high >= original entry price; for short 4h low <= entry price",
  "histogram_causality":"entry_hist and stop_last_visible_hist use only 4h bars closed by entry or start of 5m stop bar; post-stop data never used as entry filter",
  "parameters":SELECTED,
  "fee_per_side":.0008,"spread_roundtrip":.0004,"funding_8h":e.FUNDING,
  "stop_price_cap":"5% clamp", "execution_timeframe":"5m","signal_timeframe":"4h",
  "account_size":e.INITIAL,"notional_per_position":1000,
  "max_positions":3,
  "full_90d_backtest_summary":simulation,
  "aggregate":aggregate,
  "limitations":[
   "All post-stop features descriptive, may not be knowable before entry or stop.",
   "Histogram one-code Python model CausalDelta is not yet verified against actual Pine body.",
   "No divergences, wave count, or discretionary wick confirmation implemented.",
   "5m OHLC cannot resolve exactly when within a candle a stop was touched; stop is assigned 5m candle close for post-event study.",
   "A 4h bar that spans stop time is excluded from post stop study; next fully later 4h candle begins at the next 4h boundary.",
   "Recovering entry price after stop does not mean entry would have profitably survived without its SL; hypothetical counterfactual needs complete risk simulation.",
   "Price can both hit entry and original TP in same 4h bar; OHLC order unknown and metrics do not imply tradability.",
   "Profit-factor and challenge pass taken from approximate Upscale simulator; unresolved exact 60s, mark-price equity, funding sign, and official tariff compliance.",
   "No independent OOS filter optimization; these are diagnosis and testable hypotheses only.",
   "Near end of data, some stops have fewer than 12 fully completed 4h follow-up bars; per-horizon denominators adjust."]
 }
 json_file(OUT/"summary.json",manifest)
 # Lightweight textual report remains self-contained in Actions logs.
 print("STOP_COUNTS",json.dumps({k:aggregate[k] for k in ("total_trades","stop_loss","breakeven_stops","other_exits","by_symbol")},ensure_ascii=False),flush=True)
 print("ENTRY_CONTRAST",json.dumps({k:aggregate[k] for k in ("initial_stop_metrics","breakeven_stop_metrics","non_stop_metrics")},ensure_ascii=False),flush=True)
 print("RECOVERY",json.dumps(aggregate["stop_recovery_by_horizon_4h_candles"],ensure_ascii=False),flush=True)
 print("POST_HIST_BY_K",json.dumps(aggregate["post_stop_histogram_by_k"],ensure_ascii=False),flush=True)
 for z in stops:
  brief={"id":z["id"],"symbol":z["symbol"],"side":"LONG" if z["side"]==1 else "SHORT",
   "entry":z["entry_utc"],"stop":z["exit_utc"],"pnl":z["pnl_usd"],
   "reason":z["category"],"hold_hours":z["hold_hours"],"mfe_pct":r(z["mfe_pct"]),
   "entry_hist":z["entry_hist"],"last_visible":z["stop_last_visible_hist"],
   "prior_hist_reaccelerated":z["hist_reacceleration_before_stop_any"],
   "future_4h":[{k:b[k] for k in ("k","hist_delta","color","close_move_from_entry_pct","recovers_entry_intrabar")} for b in z["post_stop_bars"][:8]]}
  print("STOP_CASE",json.dumps(brief,ensure_ascii=False),flush=True)
 print("ARTIFACT_FILES",json.dumps({p.name:p.stat().st_size for p in OUT.iterdir()}),flush=True)
if __name__=="__main__":main()
