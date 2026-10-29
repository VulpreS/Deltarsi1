"""MONO-ASSET 20% initial notional + one more 20% on SECOND same-direction Delta
signal while original trade is losing and original SL still intact.

8 independent symbol accounts x Basic 5k, Basic API 10k, Turbo 5k,
4 hold modes, full year + Q2, with 5m stops and TON 1h trailing.

Frozen primary per-coin instructions; no changes to 'новые инструкции'.
Initial SL and TP stay anchored to FIRST entry/its pre-signal ATR after add.
New add changes quantity/weighted-average entry only. Do NOT tighten, widen,
or rebase protective price levels. Never add on opposite signal.
Variants:
  baseline_48             single $20%, 48h since FIRST fill
  add_original_48         add $20% on 2nd same-side signal if underwater;
                          time exit 48h since FIRST fill
  add_second_signal_48    identical add; if 2nd same-side signal, reset timer
                          to 48h after that 2nd signal (even if not in loss)
  add_no_time_limit       identical add; NO time exit at all, stop/TP/trailing
                          and account breach remain operative
API rule 60s: 5m OHLC cannot resolve it; conservative profit adjustment
for positive exits in the SAME 5m candle as last opening/increase. This is
an upper bound on disallowed gains (many are actually closed >60sec).
Basic phase transitions at first qualifying UTC day-end based on realized PnL;
positions can be closed at that time (distinct from 48-hour time exit).
Turbo dynamic 6% trailing peak equity includes unrealized PnL, no daily rule.
No payouts in these comparisons; Turbo payout audit is separate.

Official platform docs:
https://docs.upscale.trade/how-to-join-upscale/participation_requirements
https://docs.upscale.trade/trading-mechanics/fees
https://docs.upscale.trade/trading-mechanics/funding
https://docs.upscale.trade/how-upscale-works/api_trading
"""
import sys,os,math,json,datetime as dt,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_instructions_8asset_48h.backtest import check_document,SYMS,START,VALID_END,END,H
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

M=5*60*1000
DAY=24*H
OUT=Path("experiments/mono_asset_addon_20pct_4h")
FUNDING=.00015
MODES=("baseline_48","add_original_48","add_second_signal_48","add_no_time_limit")
CASES={
 "Basic_5000_noAPI":dict(initial=5000.,kind="basic",api=False,fee=.00008),
 "Basic_10000_API":dict(initial=10000.,kind="basic",api=True,fee=.00008),
 "Turbo_5000":dict(initial=5000.,kind="turbo",api=False,fee=.0006)
}
SPREAD=.0002
FRAC=.20

def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()

def stats(trades):
 wins=[t["net"] for t in trades if t["net"]>0]
 losses=[t["net"] for t in trades if t["net"]<0]
 return dict(count=len(trades),
   win_rate_pct=round(100*len(wins)/len(trades),2) if trades else None,
   profit_factor=round(sum(wins)/-sum(losses),3) if losses else None,
   net_closed_usd=round(sum(t["net"] for t in trades),2),
   gross_closed_usd=round(sum(t["gross"] for t in trades),2),
   avg_duration_h=round(statistics.mean(t["hold_h"] for t in trades),2) if trades else None,
   max_duration_h=round(max((t["hold_h"] for t in trades),default=0),2),
   over_48h_trades=sum(t["hold_h"]>48.001 for t in trades),
   exits={k:sum(t["reason"]==k for t in trades)
     for k in ("stop","stop_gap","take","take_gap","trailing_stop","time","stage_transfer")},
   trades_with_add=sum(t["added"] for t in trades),
   funding_total_usd=round(sum(t["funding"] for t in trades),2),
   fees_total_usd=round(sum(t["fees"] for t in trades),2))

def simulate(data,events,parameters,mode,case,start,end,stress=False,details=False):
 assert mode in MODES
 assert case["kind"] in ("basic","turbo")
 sym=case["symbol"]
 initial=case["initial"];fee=case["fee"];api=case["api"]
 sl, tp, trail_a, trail_d=parameters
 cash=initial;position=None
 peak=initial;maxdd=0.;breach=None
 stage=1 if case["kind"]=="basic" else 3
 stage_start=start;phases=[];phase_reset_pending=False
 qualifying=0;positive_days=[];profit_days_funded=0
 last_daily_base=initial
 balance_start_day=initial
 trades=[];adds=[];second_signal_events=[]
 signal_count=sum(start<=t<end for t in events)
 missed_signals=0;opened=0
 max_notional=0.;max_time_in_market=0
 exits_time=0;stage_autocloses=0
 funding_total=0.;fees_total=0.;disallowed_60=0.;ambiguous_60=0
 phase_cash_gains=[];daily=[];last_utc_day=None
 entry_peak_date=None;end_t=start
 # 5m OHLC full timeline from Binance continuous archive
 assert (end-start)%M==0
 def eq(price):
  if position is None:return cash
  p=position
  return cash+p["side"]*p["qty"]*(price-p["avg"])-p["qty"]*price*(fee+SPREAD/2)
 def floor():
  return peak*.94 if case["kind"]=="turbo" else initial*.90
 def breach_check(t,price,label,mark_peak=True):
  nonlocal peak,maxdd,breach,entry_peak_date
  current=eq(price)
  if case["kind"]=="turbo" and mark_peak and current>peak:
   peak=current;entry_peak_date=iso(t)
  maxdd=max(maxdd,100*max(0,peak-current)/peak)
  lim=floor()
  if current<=lim+1e-10 or (case["kind"]=="basic" and current<=balance_start_day*.95+1e-10):
   kind="turbo_6pct_trailing" if case["kind"]=="turbo" else ("basic_daily_5pct" if current<=balance_start_day*.95 else "basic_total_10pct")
   breach=dict(time=iso(t),kind=kind,mark=label,stage=stage,
    equity=round(current,4),peak_equity=round(peak,4),
    overall_floor=round(lim,4),
    daily_floor=round(balance_start_day*.95,4) if case["kind"]=="basic" else None,
    deficit=round(max(lim-current,(balance_start_day*.95-current) if case["kind"]=="basic" else 0),4),
    active_qty=round(position["qty"],6) if position else 0,
    open_price_avg=round(position["avg"],6) if position else None,
    open_stop=round(position["stop"],6) if position else None)
   return True
  return False
 def close(t,price,reason):
  nonlocal position,cash,fees_total,disallowed_60,ambiguous_60,exits_time,stage_autocloses
  p=position
  if p is None:raise AssertionError("close called empty")
  gross=p["side"]*p["qty"]*(price-p["avg"])
  cost=p["qty"]*price*(fee+SPREAD/2)
  counted_gross=gross
  # Account with API: cannot resolve whether profitable fill within 60s
  # of last increase from 5m OHLC. Conservatively zero SAME-BAR wins.
  if api and gross>0 and t-p["last_increase_t"]<M:
   ambiguous_60+=1;disallowed_60+=gross;counted_gross=0.
  cash+=counted_gross-cost;fees_total+=cost
  holding=(t+M-p["entry_t"])/H
  row=dict(start=iso(p["entry_t"]),exit=iso(t+M),
     first_entry=p["first_entry"],avg_entry=p["avg"],qty=p["qty"],
     original_stop=p["initial_stop"],final_stop=p["stop"],
     original_take=p["take"],last_price=price,reason=reason,
     gross=round(counted_gross,5),gross_before_api_adjustment=round(gross,5),
     net=round(counted_gross-cost-p["entry_fees"]-p["funding"],5),
     fees=round(cost+p["entry_fees"],5),
     funding=round(p["funding"],5),hold_h=round(holding,4),
     added=p["added"],second_seen=p["second_seen"],
     extra_qty=p["extra_qty"],open_hours_after_add=round((t+M-p["second_time"])/H,3) if p["second_time"] is not None else None,
     phase=stage)
  trades.append(row)
  if reason=="time":exits_time+=1
  if reason=="stage_transfer":stage_autocloses+=1
  position=None
 def open_pos(t,price,ev):
  nonlocal position,cash,fees_total,opened,max_notional
  side=ev["side"];atr=ev["atr_4h"]
  if not (math.isfinite(atr) and atr>0 and price>0):return
  slv,tpv,act,dist=parameters
  stop=price-side*slv*atr;take=price+side*tpv*atr
  if min(stop,take)<=0:return
  notional=initial*FRAC;qty=notional/price
  cost=notional*(fee+SPREAD/2)
  cash-=cost;fees_total+=cost
  position=dict(side=side,qty=qty,avg=price,first_entry=price,
   entry_t=t,last_increase_t=t,deadline=t+48*H,stop=stop,initial_stop=stop,
   take=take,atr=atr,act=act,dist=dist,active=False,
   best=price,hour_best=price,
   current_notional=notional,entry_fees=cost,funding=0.,
   added=False,extra_qty=0.,second_seen=False,second_time=None)
  opened+=1;max_notional=max(max_notional,notional)
 def process_event(t,price,ev):
  nonlocal cash,fees_total,max_notional,missed_signals
  p=position
  if p is None:
   open_pos(t,price,ev);return
  if ev["side"]!=p["side"]:
   missed_signals+=1;return
  if p["second_seen"]:
   missed_signals+=1;return
  # FIRST subsequent same-side 4h confirmed signal, never a late 3rd signal
  p["second_seen"]=True;p["second_time"]=t
  signloss=p["side"]*(price-p["first_entry"])<0.
  safe_before_stop=p["side"]*(price-p["stop"])>0
  second_signal_events.append(dict(when=iso(t),stage=stage,
    in_loss=signloss,inside_stop=safe_before_stop,
    seconds_from_first=(t-p["entry_t"])/1000))
  if mode=="add_second_signal_48":
   p["deadline"]=t+48*H
  if mode=="baseline_48" or not signloss or not safe_before_stop:
   return
  # At most ONE add of $20% of original nominal on this second signal.
  assert not p["added"]
  add_notional=initial*FRAC;extra_qty=add_notional/price
  add_cost=add_notional*(fee+SPREAD/2)
  p["avg"]=(p["avg"]*p["qty"]+price*extra_qty)/(p["qty"]+extra_qty)
  p["qty"]+=extra_qty;p["extra_qty"]=extra_qty;p["current_notional"]+=add_notional
  p["entry_fees"]+=add_cost;p["added"]=True;p["last_increase_t"]=t
  cash-=add_cost;fees_total+=add_cost
  max_notional=max(max_notional,p["current_notional"])
  adds.append(dict(when=iso(t),price=price,prior_entry=p["first_entry"],
    avg_after=p["avg"],added_nominal=add_notional,
    unchanged_stop=p["stop"],unchanged_tp=p["take"]))
 def phase_move(t,mark):
  nonlocal stage,stage_start,cash,qualifying,positive_days,phase_reset_pending
  nonlocal last_daily_base,balance_start_day,peak,profit_days_funded
  if phase_reset_pending:
   assert position is None
   stage+=1;stage_start=t;cash=initial;qualifying=0;positive_days=[]
   last_daily_base=initial;balance_start_day=initial
   peak=initial;phase_reset_pending=False;profit_days_funded=0
  return
 # Initial unit sanity
 assert case["kind"]!="turbo" or (stage==3 and not api)
 full_start_index=(start-data[0][0])//M
 full_end_index=(end-data[0][0])//M
 assert full_start_index>=0 and full_end_index<=len(data)
 assert data[full_start_index][0]==start
 assert data[full_end_index-1][0]==end-M
 lastclose=data[full_start_index][1]
 for i in range(full_start_index,full_end_index):
  bar=data[i];t,o,hi,lo,c=bar
  end_t=t+M
  assert t==start+(i-full_start_index)*M
  # midnight stage reset must precede new entries
  if phase_reset_pending and position is None:phase_move(t,o)
  if t%DAY==0:
   balance_start_day=eq(o)
   last_daily_base=balance_start_day
  # Funding charged on already open effective NOTIONAL at funding UTC ticks.
  if t%(8*H)==0 and position is not None:
   funded_notional=position["qty"]*o
   charge=funded_notional*FUNDING
   cash-=charge;funding_total+=charge;position["funding"]+=charge
  # EXIT first on gap through SL/TP (no adding to already stopped trade).
  if position is not None:
   p=position
   if p["side"]*(o-p["stop"])<=0:close(t,o,"stop_gap")
   elif p["side"]*(o-p["take"])>=0:close(t,o,"take_gap")
  # New signals appear at close of 4h and execute on 5m bar OPEN.
  # If gap-closed position this bar, do NOT re-enter same bar.
  ev=events.get(t)
  if ev is not None:
   if position is None and len(trades)>0 and trades[-1]["exit"]==iso(t+M):
    missed_signals+=1
   else:process_event(t,o,ev)
  if position is not None:
   max_time_in_market=max(max_time_in_market,(t-position["entry_t"])/H)
  if breach_check(t,o,"five_min_open_after_fees_funding"):break
  if stress and position is not None:
   p=position
   good=hi if p["side"]==1 else lo
   bad=lo if p["side"]==1 else hi
   if breach_check(t,good,"hypothetical_high_favorable"):break
   if breach_check(t,bad,"hypothetical_low_adverse",mark_peak=False):break
  # 5m stop-first; TON trailing only on 1h completed candle.
  if position is not None:
   p=position;side=p["side"]
   if (lo<=p["stop"] if side==1 else hi>=p["stop"]):
    close(t,p["stop"],"stop")
   elif (hi>=p["take"] if side==1 else lo<=p["take"]):
    close(t,p["take"],"take")
   else:
    p["hour_best"]=max(p["hour_best"],hi) if side==1 else min(p["hour_best"],lo)
    if mode!="add_no_time_limit" and t+M>=p["deadline"]:
     close(t,c,"time")
  if breach_check(t+M,c,"five_min_close_after_exits"):break
  if position is not None and (t+M)%H==0:
   p=position;side=p["side"]
   p["best"]=max(p["best"],p["hour_best"]) if side==1 else min(p["best"],p["hour_best"])
   if p["act"] is not None:
    if side*(p["best"]-p["first_entry"])>=p["act"]*p["atr"]:p["active"]=True
    if p["active"]:
     newstop=p["best"]-side*p["dist"]*p["atr"]
     p["stop"]=max(p["stop"],newstop) if side==1 else min(p["stop"],newstop)
   p["hour_best"]=c
  if (t+M)%DAY==0:
   daydelta=eq(c)-last_daily_base
   if daydelta>0:positive_days.append(daydelta)
   if daydelta>=initial*.005:
    if stage in (1,2):qualifying+=1
    elif stage==3:profit_days_funded+=1
   realized_profit=cash-initial
   req_days=3 if stage==1 else 5
   desired=initial*(.05 if stage==1 else .08)
   consistent=(not api or (realized_profit>0 and
        max(positive_days,default=0.)<.30*realized_profit))
   can_promote=(case["kind"]=="basic" and stage<=2 and
      qualifying>=req_days and realized_profit>=desired and consistent)
   if can_promote:
    if position is not None:
     # Upscale closes open positions on phase transition.
     close(t,c,"stage_transfer")
    if cash-initial>=desired and (not api or
       max(positive_days,default=0.)<.30*(cash-initial)):
     phases.append(dict(phase=stage,at=iso(t+M),
       days=round((t+M-stage_start)/DAY,2),
       profit_days=qualifying,realized_pnl=round(cash-initial,2),
       best_day=round(max(positive_days,default=0.),2)))
     phase_cash_gains.append(round(cash-initial,2))
     phase_reset_pending=True
   daily.append(dict(date=iso(t+M)[:10],phase=stage,
      equity=round(eq(c),3),realized=round(cash-initial,3),
      qualified_days=qualifying if stage<=2 else profit_days_funded,
      max_profit_day=round(max(positive_days,default=0.),3),
      turbo_floor=round(peak*.94,3) if case["kind"]=="turbo" else None))
  lastclose=c
 # Need terminal mark using actual last observed price when stopped.
 markprice=lastclose
 equity_end=eq(markprice)
 summary=stats(trades)
 summary.update(symbol=sym,account=case["name"],mode=mode,
  risk_approximation="stress_5m_hl" if stress else "5m_close",
  start=iso(start),requested_end=iso(end),actual_end=iso(end_t),
  survived_full_window=breach is None,breach=breach,
  cash_balance=round(cash,2),equity_end=round(equity_end,2),
  unclosed_position=dict(entry=round(position["first_entry"],5),
      avg=round(position["avg"],5),added=position["added"],
      qty=position["qty"],stop=position["stop"],take=position["take"],
      holding_hours=round((end_t-position["entry_t"])/H,1),
      unrealized_including_exit_estimate=round(equity_end-cash,2)) if position is not None else None,
  peak_equity=round(peak,2),max_peak_to_worst_dd_pct=round(maxdd,3),
  notional_per_initial_leg=round(initial*FRAC,2),
  notional_if_added=round(initial*FRAC*2,2),
  max_notional_observed=round(max_notional,2),
  first_entries=opened,
  repeated_same_side_signals=len(second_signal_events),
  repeat_while_underwater=sum(x["in_loss"] for x in second_signal_events),
  actual_adds=len(adds),percentage_of_trades_added=round(100*len(adds)/opened,2) if opened else 0,
  skipped_other_signals=missed_signals,
  max_time_in_market_hours=round(max_time_in_market,2),
  funded_profit_days=profit_days_funded,
  stage_autocloses=stage_autocloses,
  phases=phases,phase_now=stage,
  phase_gains_usd=phase_cash_gains,
  total_fees_paid=round(fees_total,2),
  total_funding_paid=round(funding_total,2),
  early_api_5m_adjustments=ambiguous_60,
  disallowed_gross_usd_conservative=round(disallowed_60,2),
  last_equity_to_initial_pct=round(100*(equity_end/initial-1),3),
  model_horizon_end_remaining=position is not None and breach is None)
 if details:
  return summary,dict(trades=trades,adds=adds,second_signals=second_signal_events,daily=daily)
 return summary,None

def test_synthetic():
 # Exact repeated signal 4h later while $100->99, add $1,000, both SL/TP
 # remain anchored to first entry despite the weighted average changing.
 start=0;end=65*H
 rows=[]
 for t in range(start,end,M):
  o=100. if t<4*H else (99. if t<56*H else 105.)
  h=o+.01;l=o-.01
  rows.append((t,o,h,l,o))
 ev={0:dict(side=1,atr_4h=1.),4*H:dict(side=1,atr_4h=1.)}
 p=(10.,5.,None,None)
 case=dict(initial=5000.,kind="basic",api=False,fee=.00008,
           name="unit")
 a,_=simulate(rows,ev,p,"add_original_48",case,start,end,False,True)
 b,_=simulate(rows,ev,p,"add_second_signal_48",case,start,end,False,True)
 c,_=simulate(rows,ev,p,"add_no_time_limit",case,start,end,False,True)
 d,_=simulate(rows,ev,p,"baseline_48",case,start,end,False,True)
 assert a["actual_adds"]==b["actual_adds"]==c["actual_adds"]==1,(a,b,c)
 assert a["max_notional_observed"]==2000.,a
 assert a["trades_with_add"]==1
 assert a["max_duration_h"]==48, a
 assert b["max_duration_h"]==52, b
 assert c["max_duration_h"]>55 and c["exits"]["take"]+c["exits"]["take_gap"]==1,c
 assert d["actual_adds"]==0 and d["max_notional_observed"]==1000.,d
 print("MONO_SYNTHETIC_ADD_AND_HOLD_TESTS_PASSED",
       json.dumps({k:v["max_duration_h"] for k,v in
         [("original_48",a),("reset_48",b),("no_time",c),("baseline",d)]}),flush=True)

def main():
 params=check_document()
 test_synthetic()
 data,_,manifest=source_load()
 assert set(data)==set(SYMS)
 all_results=dict(description="Separate mono-asset portfolio per symbol, one $20pct initial and optional second $20pct on 2nd same-side losing signal before original stop",
  parameter_source="новые инструкции/README.md (read-only)",
  data_manifest=manifest,
  published_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
  config=dict(position_fraction_initial=.20,one_add_max_fraction=.20,
    max_exposure_fraction_initial=.40,
    entry_trigger="medium_color to weak_color confirmed 4h",
    add_trigger="FIRST repeat same-direction 4h signal while position at adverse price to ORIGINAL entry, and before stop",
    second_signal_timer_reset_if_profitable=True,
    stop_and_tp_anchor="UNCHANGED first entry ATR and stop/target price (no rebase on average price)",
    fund_rate_8h=.00015,spread_roundtrip=.0002,
    basic_fee_per_side=.00008,turbo_fee_per_side=.0006,
    position_time_exit_options=["48h from first","48h from second same-side event","no time limit"],
    ton_trailing_update="on completed 1h", 
    no_forced_exit="no time exit; SL/TP/trailing and account risk still apply",
    accounts=dict(Basic_5000_noAPI="5/10pct",Basic_10000_API="5/10pct + 30pct phase / 60s conservative same 5m candle",Turbo_5000="6pct trailing HWM from unrealized peak"),
    payout_policy="no payout in these scenarios"),
  caveats=[
    "The user phrase 'second signal' is defined strictly as FIRST repeated SAME-DIRECTION confirmed 4h Delta event. No add at every red candle; no add on opposite signals.",
    "Stop and TP are anchored to first signal price/ATR; on add the stop is NOT moved or widened, and second lot shares same absolute protective prices.",
    "No optimization, all 8 SL/TP/trailing params remain from primary document; per-symbol mono accounts traded INDEPENDENTLY.",
    "No price clamp or BE; time reset on second signal even if add skipped because currently profitable.",
    "Basic stages require realized target and profit day counts, transition modeled at next UTC midnight; discretionary phase transfer timing differs.",
    "API 60s conservatively disallows same 5m bar profitable closes, cannot measure true seconds; no 60s restriction on regular Basic/Turbo as modeled.",
    "5m close risk optimistic, 5m high-before-low path conservative; neither matches real Upscale mark tick sequence.",
    "No Turbo payouts and trailing reset are modeled; user intends first eligible fortnight withdrawal, to be tested separately for candidate mono scenarios.",
    "Long no-time holding accumulates full funding charges every 8 hours; open horizon positions are marked but NOT booked as realized gains.",
    "Funding charged on current qty*market price (not static initial notional) at scheduled UTC settlement.",
    "TP/stop checked on 5m OHLC stop-first; unknown order inside 5m. TON trailing updated at completed 1h only.",
    "Fee Basic0.008pct side, Turbo0.06pct side, funding0.015pct/8h, constant 0.02pct proxy roundtrip spread, no exchange price impact.",
    "Binance USDT-M data not actual Upscale price oracle or execution, so a backtest breach is modeled not official.",
    "User's manually described RSI27 headings may not match executable Pine SMA21 RSI12 EMA7; code uses historical tested pine_events and requires parity check.",
    "No additional wave/divergence/wick confirmation included; do not extrapolate manual 2-week strategy results.",
    "Existing two legacy open ETH/TON live positions with old settings not included.",
    "20pct is NOMINAL exposure per tranche; with Turbo max x2 leverage margin would differ; this is NOT 20pct of deposit risk per stop.",
    "No live/demo orders have been placed."
  ],results={},asset_counts={})
 periods={"year":(START,END),"q2":(VALID_END,END)}
 for sym in SYMS:
  rows=[r for _,r in sorted(data[sym].items())]
  hourly=ohlc_from_5m(rows,H)
  events=pine_events(hourly,expanded=False,atr_basis="prior")
  all_results["asset_counts"][sym]=dict(rows_5m=len(rows),
    year_signals=sum(START<=t<END for t in events),
    q2_signals=sum(VALID_END<=t<END for t in events))
  for cname,cfg in CASES.items():
   for period,(start,end) in periods.items():
    for mode in MODES:
     for stress in (False,True):
      case=dict(**cfg,symbol=sym,name=cname)
      summary,details=simulate(rows,events,params[sym],mode,case,start,end,stress,True)
      key="/".join((sym,cname,period,mode,"stress" if stress else "close5m"))
      all_results["results"][key]=dict(summary=summary,details=details)
      print("MONO_RESULT",key,json.dumps(summary,ensure_ascii=False),flush=True)
  print("MONO_ASSET_COMPLETED",sym,flush=True)
 OUT.mkdir(parents=True,exist_ok=True)
 path=OUT/"results.json"
 path.write_text(json.dumps(all_results,ensure_ascii=False,indent=2,allow_nan=False))
 print("MONO_ANNUAL_RESEARCH_FINISHED",path,path.stat().st_size,
       len(all_results["results"]),flush=True)

if __name__=="__main__":main()
