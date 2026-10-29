"""Conditional entry: require a BRIGHT HISTOGRAM BAR in the CURRENT signed Delta wave.

Side-by-side with previous 6-asset (BTC ETH TON BNB XRP LINK) canonical
portfolio, 20%-per-slot, three slots (60%), optional loss-only 20% add on
second SAME-direction signal, ATR/SL/TP from frozen "новые инструкции",
48h original-entry timer, TON 1h trailing. Both Basic and Turbo, annual
and quarter, with 5m close/stress risk. Turbo earliest eligible fortnightly
payouts included separately, with 30% rule only on withdrawal.

Bright wave is precise and reproducible:
- iterate ONLY completed 4H candles of existing canonical CausalDelta,
- wave is a MAXIMAL continuous run with Delta>0 (blue) or Delta<0 (red),
  reset bright flag on ZERO or sign change;
- Bright for blue = pine_shade(delta, prior_delta)=='bright_blue';
  bright for red = corresponding 'bright_red'. This is a rising histogram
  momentum + >60 abs(delta), NOT just abs(delta)>60 or any earlier color.
- On original medium -> weak candle, REQUIRE at least one bright bar of
  SAME SIGN on a strictly PREVIOUS 4H candle within the current wave.
  Do not count a bright bar from a preceding opposite-color wave or
  a future bar. No entries on the bright candle itself.
- Any repeated confirmed signal used to add must also pass bright filter.
- Reference baseline pine_events is unmodified. We assert exact
  sign/direction/ATR mapping for every reference signal, then subset it.

Historical only; original pine from code SMA21 RSI12 EMA7 mirror logarithm,
not proven exact parity to prose RSI27 EMA7. Uses previously verified code.
"""
import sys,os,json,math,collections,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.portfolio_six_no_icp_zec_20pct.compare_add_second_signal import (
    sim,synthetic_unit,ASSETS,ACCOUNT,MODES,MAX_SLOTS,OUT as PRIOR_DIR,
    SPREAD,FUNDING,POSITION_FRAC,START,VALID_END,END,H,DAY,iso)
from experiments.new_instructions_8asset_48h.backtest import check_document
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events,pine_shade
from causal_4h_parity_audit import CausalDelta
from completed_candles import aggregate_completed

OUT=Path("experiments/portfolio_six_no_icp_zec_20pct/bright_wave_filter")
FILTERS=("no_wave_filter","bright_current_wave")
PERIODS={"annual":(START,END),"q2":(VALID_END,END)}

def filter_bright_in_current_wave(hourly,original):
 """Returns strict subset plus per-event forensic classification.

 State is updated AFTER evaluating each signal. All original event
 timestamps must appear in iterated 4h candles; asserts remain valid.
 """
 bars=aggregate_completed(hourly,4,asof_ms=hourly[-1][0]+H)
 state=CausalDelta();previous_shade=None;last_wave_sign=0
 wave_start_ms=None;wave_bright_seen=False;wave_bright_count=0
 wave_bright_first=None;wave_bright_last=None
 examined=set();accepted={};denied={}
 transitions=[];wave_count=0;bright_waves=0
 for i,bar in enumerate(bars):
  prev=state.delta
  d,_,_=state.step(bar[4],commit=True)
  shade=pine_shade(d,prev)
  sign=1 if d>0 else -1 if d<0 else 0
  if sign!=last_wave_sign:
   if last_wave_sign!=0 and wave_bright_count:bright_waves+=1
   if sign:wave_count+=1
   wave_start_ms=bar[0] if sign else None
   wave_bright_seen=False;wave_bright_count=0
   wave_bright_first=None;wave_bright_last=None
   last_wave_sign=sign
  entry=bar[0]+4*H
  if entry in original:
   ev=original[entry]
   # Original signals must be weak-red after medium-red, weak-blue after medium-blue.
   expected=1 if previous_shade=="medium_red" and shade=="weak_red" else (
      -1 if previous_shade=="medium_blue" and shade=="weak_blue" else 0)
   assert expected==ev["side"] and sign==(-1 if ev["side"]==1 else 1), (
       "reference event does not match reconstructed closed bar",entry,ev,previous_shade,shade)
   assert i>=210 and math.isfinite(d),("warmup mismatch",i,d)
   meta=dict(entry_ms=entry,entry_utc=iso(entry),direction="LONG" if ev["side"]==1 else "SHORT",
      current_shade=shade,previous_shade=previous_shade,delta=d,
      delta_prev=prev,wave_sign="blue" if sign>0 else "red",
      wave_start_utc=iso(wave_start_ms),
      previous_bright_bars=wave_bright_count,
      first_bright_utc=iso(wave_bright_first) if wave_bright_first is not None else None,
      latest_bright_utc=iso(wave_bright_last) if wave_bright_last is not None else None,
      accepted=bool(wave_bright_seen))
   examined.add(entry)
   if wave_bright_seen:
    accepted[entry]=ev
   else:
    denied[entry]=meta
   transitions.append(meta)
  if shade==("bright_blue" if sign>0 else "bright_red") and sign:
   wave_bright_seen=True;wave_bright_count+=1
   if wave_bright_first is None:wave_bright_first=bar[0]
   wave_bright_last=bar[0]
  previous_shade=shade
 if last_wave_sign!=0 and wave_bright_count:bright_waves+=1
 assert examined==set(original),("unmatched original signals",
      sorted(set(original)-examined)[:5],sorted(examined-set(original))[:5])
 assert set(accepted).isdisjoint(denied)
 assert len(accepted)+len(denied)==len(original)
 assert all(x["previous_bright_bars"]>0 for x in transitions if x["accepted"])
 assert all(x["previous_bright_bars"]==0 for x in transitions if not x["accepted"])
 return accepted,dict(original_signals=len(original),
    filtered_signals=len(accepted),blocked_missing_bright=len(denied),
    pct_retained=round(100*len(accepted)/len(original),2) if original else None,
    signed_waves=wave_count,waves_with_bright=bright_waves,
    classified_entries=transitions,
    blocked_samples=list(denied.values())[:15],
    accepted_samples=[x for x in transitions if x["accepted"]][:15])

def test_filter_synthetic():
 # Need test the *wave gate* separately from CausalDelta: sign boundary,
 # zero reset, actual 'bright' shade classification and timing.
 samples=[
  (-90.,-70.,"bright_red"),
  (-80.,-90.,"medium_red"),
  (-50.,-80.,"weak_red"),
  (90.,70.,"bright_blue"),
  (80.,90.,"medium_blue"),
  (50.,80.,"weak_blue"),
  (-50.,-80.,"weak_red"),
  (0.,-90.,None)]
 for d,prev,expected in samples:
  assert pine_shade(d,prev)==expected,(d,prev,expected,pine_shade(d,prev))
 def gate_sequence(seq):
  last=0;bright=False;allowed=[]
  for d,prev,entry in seq:
   side=1 if d>0 else -1 if d<0 else 0
   if side!=last:bright=False;last=side
   allowed.append((entry,bright))
   if pine_shade(d,prev) in ("bright_blue","bright_red") and side:bright=True
  return dict(allowed)
 # Bright red followed by weak red in SAME sign is allowed;
 # blue after red must reset regardless of previous red bright.
 a=gate_sequence([(-90.,-70.,"red_bright"),(-80.,-90.,"red_medium"),
                  (-50.,-80.,"red_entry"),(50.,40.,"blue_entry")])
 assert a["red_entry"] and not a["blue_entry"],a
 b=gate_sequence([(-90.,-70.,"red_bright"),(0.,-90.,"zero"),
                  (-50.,-80.,"new_red_no_bright")])
 assert not b["new_red_no_bright"],b
 assert MAX_SLOTS==3 and abs(POSITION_FRAC-.2)<1e-9
 print("BRIGHT_WAVE_UNIT_TEST_PASSED",flush=True)

def simple(r):
 return dict(survived=r["survived_full_period"],
   breach=r["breach"],closed=r["number_closed"],wr=r["win_rate_pct"],
   pf=r["profit_factor"],net=r["closed_pnl_usd"],equity=r["final_equity_usd"],
   dd=r["max_peak_to_trough_dd_pct"],phases=r["phases"],
   funded_pnl=r["funded_profit_realized_usd"],
   repeat=r["confirmed_repeat_signals"],repeats_underwater=r["repeat_while_loss"],
   addons=r["actual_adds"],blocked_slots_add=r["add_rejected_full_slots"],
   blocked_slots_fresh=r["fresh_signals_blocked_max_slots"],
   missed_60s=r["ambiguous_api_close_60s"],
   trades_per_asset=r["profit_of_closed_by_phase"],
   payout_count=r["payout_count"],wallet=r["wallet_received_usd"],
   net_wallet_after_purchase=r["net_wallet_after_turbo_purchase_usd"],
   payouts=r["payouts"],
   first_cashout=r["first_cashout_eligible_if_requested"],
   max_slots=r["max_slots_occupied"],fees=r["fees_spread_usd"],
   funding=r["funding_usd"])

def main():
 test_filter_synthetic()
 synthetic_unit()
 allparams=check_document()
 params={s:allparams[s] for s in ASSETS}
 candles,_,manifest=source_load()
 assert set(ASSETS).issubset(candles)
 raw={};raw_events={};filtered={};counts={}
 for asset in ASSETS:
  raw[asset]=candles[asset]
  rows=sorted(raw[asset].values())
  hours=ohlc_from_5m(rows,H)
  ev=pine_events(hours,expanded=False,atr_basis="prior")
  kept,meta=filter_bright_in_current_wave(hours,ev)
  for period,(start,end) in PERIODS.items():
   a={t:e for t,e in ev.items() if start<=t<end}
   b={t:e for t,e in kept.items() if start<=t<end}
   assert set(b).issubset(a)
   ratio=round(100*len(b)/len(a),2) if a else 0.
   print("BRIGHT_COVERAGE",asset,period,json.dumps({
      "reference":len(a),"bright_qualified":len(b),
      "rejected":len(a)-len(b),"kept_pct":ratio},ensure_ascii=False),flush=True)
  raw_events[asset]=ev;filtered[asset]=kept;counts[asset]=meta
  print("BRIGHT_ASSET_CHECK",asset,json.dumps({
   "signals":meta["original_signals"],
   "passed":meta["filtered_signals"],
   "blocked":meta["blocked_missing_bright"],
   "pct_kept":meta["pct_retained"],
   "waves":meta["signed_waves"],
   "bright_waves":meta["waves_with_bright"]},ensure_ascii=False),flush=True)
 out=dict(version="2026-10-29",
   purpose="Causal bright-previous-bar-in-current-histogram-wave filter, unchanged medium-to-weak entry, six-asset portfolio",
   owner_document="новые инструкции/README.md (not modified)",
   assets=list(ASSETS),excluded_assets=["ICPUSDT","ZECUSDT"],
   parameter_source=params,
   size_initial_usd_leg_pct=20,add_second_signal_usd_leg_pct=20,
   max_open_legs=3,max_nominal_pct=60,ATR_reference="prior 4h before signal",
   bright_definition="pine_shade==bright_red/bright_blue (|Delta|>60 AND increasing intensity of same sign), strictly earlier bar of SAME contiguous sign wave",
   wave_boundary="sign crossing of closed 4h Delta or zero",
   trading_signal="exact same medium_red->weak_red LONG, medium_blue->weak_blue SHORT",
   study_periods={k:(iso(a),iso(b)) for k,(a,b) in PERIODS.items()},
   account_types=["Basic_5000_noAPI","Basic_10000_API","Turbo_5000"],
   status="Causal backtest: no actual orders",
   limitations=[
    "Six exact symbols only; ICP/ZEC removed before signal generation. Same universe as prior 6-coin comparison.",
    "Uses historical CausalDelta/ pine_shade signal from executable SMA(close,21), RMA RSI12, EMA7, signed log; user prose RSI27/EMA7 not parity-certified.",
    "A 'wave' means uninterrupted signed Delta 4h histogram, NOT heuristic multiple subwaves separated only by weak/medium color. Definition fixed before tests.",
    "Bright means actual Pine shade bright_blue/red; threshold |Delta|>60 alone is NOT sufficient. A qualifying bright is strictly before the medium->weak entry candle.",
    "Require bright filter for ALL new position events including candidate second-signal adds. Raw 48h stops/TP, frozen ATR, TON 1h trailing, 3x20% slots retained.",
    "No diversification added; original 6-asset signal priority and second-signal position-slot allocation unchanged.",
    "Basic phase target 5% and 8% REALIZED plus 3/5 winning days and API phase consistency <30%; close stops modelled 5m, not true Upscale mark ticks.",
    "Turbo is direct Funded, 6% max EQUITY trailing, 30% rule only on possible payouts; modelled cashouts first eligible at >=14 days with 5 >=0.5% days and <30% max-day ratio on 5m flat position snapshot.",
    "Dynamic per-pair market spreads NOT reconstructed, use flat 0.02% roundtrip proxy and official rates Basic0.008% side/Turbo0.06% side, funding0.015%/8h.",
    "One-year period and favorable Q2 involve previously studied historical data; no new genuine OOS.",
    "Two older live ETH/TON positions with legacy stop/take excluded, only new-entry rules.",
    "Withdrawals assumed instant when modeled; request 100s before 48h not simulated precisely.",
    "5m highs/lows within bar don't have known ordering; stress path may be overly conservative, close-only may miss intrabar threshold.",
   ],
   asset_filter_stats=counts,
   results={})
 for period,(start,end) in PERIODS.items():
  for filter_name,events in (("no_wave_filter",raw_events),("bright_current_wave",filtered)):
   for account_name,account in ACCOUNT.items():
    for mode in MODES:
     for stress in (False,True):
      k="/".join((period,filter_name,account_name,mode,
       "stress_stopbounded" if stress else "observed_5m_close"))
      summary,details=sim(raw,events,params,ASSETS,account,start,end,mode,stress,True)
      out["results"][k]=dict(summary=summary,details=details)
      print("BRIGHT_PORTFOLIO_RESULT",k,json.dumps(simple(summary),ensure_ascii=False),flush=True)
      if account_name=="Turbo_5000":
       ck="/".join((period,filter_name,account_name,mode,"fortnightly_payouts",
           "stress_stopbounded" if stress else "observed_5m_close"))
       cr,cd=sim(raw,events,params,ASSETS,account,start,end,mode,stress,True,
        payouts_enabled=True)
       out["results"][ck]=dict(summary=cr,details=cd)
       print("BRIGHT_PORTFOLIO_RESULT",ck,json.dumps(simple(cr),ensure_ascii=False),flush=True)
 # Numerical identity of current no-filter baseline vs last generated
 # original report at several stable cases is part of the regression.
 for k in ("annual/no_wave_filter/Basic_5000_noAPI/baseline_48/observed_5m_close",
           "annual/no_wave_filter/Basic_5000_noAPI/add_loss_second_48/observed_5m_close",
           "annual/no_wave_filter/Turbo_5000/baseline_48/observed_5m_close",
           "q2/no_wave_filter/Basic_5000_noAPI/baseline_48/observed_5m_close"):
  r=out["results"][k]["summary"]
  expected={
   "annual/no_wave_filter/Basic_5000_noAPI/baseline_48/observed_5m_close":(2045.65,177),
   "annual/no_wave_filter/Basic_5000_noAPI/add_loss_second_48/observed_5m_close":(2036.94,177),
   "annual/no_wave_filter/Turbo_5000/baseline_48/observed_5m_close":(-160.01,10),
   "q2/no_wave_filter/Basic_5000_noAPI/baseline_48/observed_5m_close":(927.92,44)}
  wanted_pnl,wanted_n=expected[k]
  assert abs(r["closed_pnl_usd"]-wanted_pnl)<.025 and r["number_closed"]==wanted_n,(
   "historical baseline regression mismatch",k,r["closed_pnl_usd"],r["number_closed"])
 print("BRIGHT_NO_FILTER_HISTORICAL_REGRESSION_PASSED",flush=True)
 OUT.mkdir(parents=True,exist_ok=True)
 dest=OUT/"results.json"
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
 print("BRIGHT_WAVE_FILTER_RESEARCH_COMPLETED",str(dest),dest.stat().st_size,
       len(out["results"]),flush=True)
if __name__=="__main__":main()
