"""6-asset portfolio vs second-signal add, frozen canonical Delta settings.

Portfolio: BTC ETH TON BNB XRP LINK, *EXCLUDING* ICP/ZEC entirely.
Every initial leg = 20% STARTING notional, max 3 LEG SLOTS (60% nominal).
Each added tranche = 20% starting notional, consumes a slot. Add allowed
ONLY while active slots<=2; priority to a confirmed repeated same-direction
4h signal (before competing fresh signals on other coins).
Primary rule ADD_LOSS requires the first entry to be UNDERWATER at repeat
and original stop not touched. ADD_ANY is a diagnostic for ambiguous phrasing.
Original absolute SL/TP anchored to first entry+frozen prior-signal ATR
and kept UNCHANGED on add. TON 1h closed trail only. Original 48h clock
NEVER extended and no time-limit changes in either scenario.

Basic 5k no API, Basic 10k with API, Turbo 5k Funded. Exact official
rate Basic0.008pct/Turbo0.06pct per SIDE, funding0.015pct/8h, spread
proxy0.02pct roundtrip. Basic 5pct daily and 10pct total, Turbo6pct
max EQUITY trailing peak, 30pct consistency on Basic API phase promotion
and Turbo only for withdrawals. No withdrawals in primary comparison.

Two approaches to 5m risk: close5m (can MISS intrabar crossings)
and stress_stopbounded (favorable extreme first then adverse
extreme, both limited by STOP/TAKE; cross-asset simultaneous extremes
are still an unrealistic conservative bound).
OHLC from Binance futures, not Upscale quotes. Historic pine_events is
an approximation, not user RSI27 Pine parity. No real orders.
"""
import sys,os,json,math,statistics,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_instructions_8asset_48h.backtest import (
    check_document,SYMS as DOCUMENT_SYMS,START,VALID_END,END,H)
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

ASSETS=("BTCUSDT","ETHUSDT","TONUSDT","BNBUSDT","XRPUSDT","LINKUSDT")
EXCLUDE={"ICPUSDT","ZECUSDT"}
assert set(ASSETS)==set(DOCUMENT_SYMS)-EXCLUDE
M=5*60*1000
DAY=24*H
SPREAD=.0002 # 0.02% roundtrip, model proxy (not real)
FUNDING=.00015
POSITION_FRAC=.20
MAX_SLOTS=3
MODES=("baseline_48","add_loss_second_48","add_any_second_48")
ACCOUNT={
  "Basic_5000_noAPI":dict(name="Basic_5000_noAPI",initial=5000.,
       kind="basic",api=False,fee=.00008),
  "Basic_10000_API":dict(name="Basic_10000_API",initial=10000.,
       kind="basic",api=True,fee=.00008),
  "Turbo_5000":dict(name="Turbo_5000",initial=5000.,
       kind="turbo",api=False,fee=.0006),
}
OUT=Path("experiments/portfolio_six_no_icp_zec_20pct")

def iso(x):return dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).isoformat()
def nice(v):return round(float(v),4)

def sim(raw,signals,params,assets,account,start,end,mode,stress=False,details=False):
 assert mode in MODES
 assert account["kind"] in ("basic","turbo")
 initial=account["initial"];fee=account["fee"];api=account["api"]
 cash=initial;positions={};peak=initial
 max_dd=0.;max_cash_gain=0.;worst_day_loss=0.
 breach=None;phases=[];daily=[];ledger=[];adds=[]
 phase=1 if account["kind"]=="basic" else 3
 phase_start=start;stage_pending=False
 profitable_days=0;positive_daily=[];funded_days=0
 daybase=initial
 phase_realized_gains=[]
 fees=0.;funding=0.;disallowed_60=0.;ambiguous_60=0
 max_slots=0;max_open_assets=0;max_nominal=0.
 opened=0;second_seen=0;repeat_underwater=0;attempts=0
 adds_blocked_full=0;adds_not_underwater=0;adds_touched_stop=0
 missing_slots_new=0;opposite_signals=0;subsequent_repeat=0
 add_replacement_new=0;no_add_against_stop=0
 best_cash_profit=0.
 first_payout_candidate=None;last_t=start;last_close={s:raw[s][start][1] for s in assets}
 fund_since=None
 daily_fee=0.;day_checks=0
 assert (end-start)%M==0
 def slots():return sum(p["legs"] for p in positions.values())
 def eq(prices):
  return cash+sum(p["side"]*p["qty"]*(prices[s]-p["avg"])-
     p["qty"]*prices[s]*(fee+SPREAD/2) for s,p in positions.items())
 def risk_check(t,prices,source):
  nonlocal peak,max_dd,breach,worst_day_loss
  v=eq(prices)
  if v>peak:peak=v
  max_dd=max(max_dd,100*max(0,peak-v)/peak)
  worst_day_loss=max(worst_day_loss,daybase-v)
  hard_floor=(.94*peak if account["kind"]=="turbo" else .90*initial)
  day_floor=daybase*.95 if account["kind"]=="basic" else None
  if v<=hard_floor+1e-10 or (day_floor is not None and v<=day_floor+1e-10):
   typ=("turbo_trailing_6pct" if account["kind"]=="turbo" else
       ("basic_daily_5pct" if v<=day_floor else "basic_total_10pct"))
   breach=dict(at=iso(t),reason=typ,source=source,phase=phase,
       equity=nice(v),peak_equity=nice(peak),hard_floor=nice(hard_floor),
       daily_floor=nice(day_floor) if day_floor is not None else None,
       occupied_slots=slots(),active_assets=list(positions),
       deficit_usd=nice(max(hard_floor-v,
         day_floor-v if day_floor is not None else 0)))
   return True
  return False
 def close_position(s,t,price,reason):
  nonlocal cash,fees,ambiguous_60,disallowed_60
  p=positions[s]
  gross=p["side"]*p["qty"]*(price-p["avg"])
  cost=p["qty"]*price*(fee+SPREAD/2)
  # API opt-in: profitable close earlier than 60sec after last increase is
  # removed; 5m OHLC cannot resolve exact second. Conservative same-bar.
  adjusted=gross
  if api and gross>0 and t-p["last_increase_t"]<M:
   ambiguous_60+=1;disallowed_60+=gross;adjusted=0.
  cash+=adjusted-cost;fees+=cost
  ledger.append(dict(asset=s,phase=phase,entry=iso(p["entry_t"]),
     exit=iso(t+M),reason=reason,side=p["side"],legs=p["legs"],
     added=p["legs"]==2,initial_price=nice(p["first_entry"]),
     average_entry=nice(p["avg"]),stop_original=nice(p["initial_stop"]),
     stop_final=nice(p["stop"]),take_original=nice(p["take"]),
     exit_price=nice(price),holding_hours=nice((t+M-p["entry_t"])/H),
     net=round(adjusted-cost-p["entry_fee"]-p["funding"],6),
     gross=nice(adjusted),pre_api_gross=nice(gross),
     costs=nice(cost+p["entry_fee"]),funding=nice(p["funding"])))
  del positions[s]
 def new_position(s,t,price,event):
  nonlocal cash,fees,opened
  if slots()>=MAX_SLOTS:return False
  side=event["side"];atr=event["atr_4h"]
  if not(math.isfinite(atr) and atr>0 and price>0):return False
  sl,tp,activate,distance=params[s]
  stop=price-side*sl*atr
  take=price+side*tp*atr
  if stop<=0 or take<=0:return False
  usd=initial*POSITION_FRAC
  qty=usd/price
  cost=usd*(fee+SPREAD/2)
  cash-=cost;fees+=cost
  positions[s]=dict(side=side,avg=price,first_entry=price,
    qty=qty,legs=1,initial_notional_usd=usd,
    entry_t=t,last_increase_t=t,stop=stop,initial_stop=stop,
    take=take,atr=atr,activate=activate,distance=distance,
    activated=False,best=price,hour_best=price,
    entry_fee=cost,funding=0.,second_seen=False,second_t=None)
  opened+=1
  return True
 def inspect_repeat(s,t,price,event):
  nonlocal cash,fees,second_seen,repeat_underwater,attempts
  nonlocal adds_blocked_full,adds_not_underwater,adds_touched_stop
  p=positions[s]
  if event["side"]!=p["side"]:return False
  if p["second_seen"]:return False
  p["second_seen"]=True;p["second_t"]=t
  second_seen+=1
  underwater=p["side"]*(price-p["first_entry"])<0
  before_stop=p["side"]*(price-p["stop"])>0
  if underwater:repeat_underwater+=1
  if not before_stop:
   adds_touched_stop+=1
   return False
  if mode=="baseline_48":return False
  if mode=="add_loss_second_48" and not underwater:
   adds_not_underwater+=1
   return False
  attempts+=1
  if slots()>=MAX_SLOTS:
   adds_blocked_full+=1
   return False
  oldstop=p["stop"];oldtake=p["take"];orig=p["first_entry"]
  usd=initial*POSITION_FRAC
  qty=usd/price
  cost=usd*(fee+SPREAD/2)
  p["avg"]=(p["avg"]*p["qty"]+price*qty)/(p["qty"]+qty)
  p["qty"]+=qty;p["legs"]+=1;p["entry_fee"]+=cost
  p["last_increase_t"]=t
  cash-=cost;fees+=cost
  assert p["stop"]==oldstop and p["take"]==oldtake
  assert p["initial_stop"]==oldstop if p["activate"] is None else True
  adds.append(dict(asset=s,at=iso(t),underwater=underwater,
    original_entry=nice(orig),second_price=nice(price),
    average_after=nice(p["avg"]),sl_price=nice(p["stop"]),
    tp_price=nice(p["take"]),slots_after=slots(),
    nominal_added_usd=usd))
  return True
 def transfer_if_eligible(t,prices):
  nonlocal phase,phase_start,cash,profitable_days,positive_daily,peak,funded_days
  if account["kind"]!="basic" or phase>=3 or positions:return False
  required=3 if phase==1 else 5
  goal=initial*(.05 if phase==1 else .08)
  profit=cash-initial
  best=max(positive_daily,default=0.)
  if profitable_days<required or profit<goal:return False
  if api and not (profit>0 and best<.30*profit):return False
  phases.append(dict(phase=phase,completed=iso(t),
    days=nice((t-phase_start)/DAY),
    qualified_days=profitable_days,realized_profit=nice(profit),
    max_positive_day=nice(best),
    consistency_pct=nice(best/max(profit,1e-12)*100)))
  phase_realized_gains.append(profit)
  phase+=1;phase_start=t;cash=initial;peak=initial
  profitable_days=0;positive_daily=[];funded_days=0
  return True
 firstday=start//DAY
 for t in range(start,end,M):
  last_t=t
  assert t>=start and t<end
  bars={s:raw[s][t] for s in assets}
  opens={s:v[1] for s,v in bars.items()}
  closes={s:v[4] for s,v in bars.items()}
  last_close=dict(opens)
  # Transition between Basic stages only on a FLAT portfolio, when both
  # realized profit and UTC qualified days already satisfy phase rules.
  if account["kind"]=="basic" and phase<3 and not positions:
   transfer_if_eligible(t,opens)
  if t%DAY==0:
   daybase=eq(opens)
  # Funding for EXISTING exposure only at 00:00/08:00/16:00 UTC
  if t%(8*H)==0:
   for s,p in positions.items():
    charge=p["qty"]*opens[s]*FUNDING
    cash-=charge;funding+=charge;p["funding"]+=charge
  # Stop-gap / take-gap at first price of 5m. A close at the open may
  # preempt a same-timestamp signal, which is skipped for this coin.
  closed_at_open=set()
  for s,p in list(positions.items()):
   o=opens[s]
   if p["side"]*(o-p["stop"])<=0:
    close_position(s,t,o,"stop_gap");closed_at_open.add(s)
   elif p["side"]*(o-p["take"])>=0:
    close_position(s,t,o,"take_gap");closed_at_open.add(s)
  # Critical ordering for simultaneous 4h signals: existing repeat
  # signals are considered FIRST, then fresh positions. Same order every
  # backtest, deterministic, not dependent on future profitability.
  fresh=[]
  for s in assets:
   event=signals[s].get(t)
   if event is None:continue
   if s in positions:
    p=positions[s]
    if event["side"]==p["side"]:
     if not p["second_seen"]:inspect_repeat(s,t,opens[s],event)
     else:subsequent_repeat+=1
    else:opposite_signals+=1
   elif s not in closed_at_open:
    fresh.append((s,event))
  for s,event in fresh:
   if slots()<MAX_SLOTS:new_position(s,t,opens[s],event)
   else:missing_slots_new+=1
  max_slots=max(max_slots,slots())
  max_open_assets=max(max_open_assets,len(positions))
  max_nominal=max(max_nominal,slots()*initial*POSITION_FRAC)
  assert slots()<=MAX_SLOTS and max_nominal<=initial*.6000000001
  # Risk at OPEN before intrabar stop/take.
  if risk_check(t,opens,"five_min_open_after_entries_funding"):break
  if stress and positions:
   favorable=dict(opens);adverse=dict(opens)
   for s,p in positions.items():
    _,o,hi,lo,c=bars[s]
    if p["side"]==1:
     favorable[s]=min(hi,p["take"])
     adverse[s]=max(lo,p["stop"])
    else:
     favorable[s]=max(lo,p["take"])
     adverse[s]=min(hi,p["stop"])
   # Across assets, the extrema are NOT synchronous. This path is stress.
   if risk_check(t,favorable,"stress_favorable_5m_bounded_by_target"):break
   if risk_check(t,adverse,"stress_adverse_5m_bounded_by_stop"):break
  # Stop-first OHLC fills.
  for s,p in list(positions.items()):
   _,o,hi,lo,c=bars[s]
   direction=p["side"]
   if (lo<=p["stop"] if direction==1 else hi>=p["stop"]):
    close_position(s,t,p["stop"],"stop")
   elif (hi>=p["take"] if direction==1 else lo<=p["take"]):
    close_position(s,t,p["take"],"take")
   else:
    p["hour_best"]=max(p["hour_best"],hi) if direction==1 else min(p["hour_best"],lo)
    if t+M>=p["entry_t"]+48*H:
     close_position(s,t,c,"time")
  last_close=dict(closes)
  if risk_check(t+M,closes,"five_min_close_after_exits"):break
  # TON trailing updates ONLY at end of each completed 1h.
  if (t+M)%H==0:
   for s,p in positions.items():
    direction=p["side"]
    p["best"]=(max(p["best"],p["hour_best"]) if direction==1
       else min(p["best"],p["hour_best"]))
    if p["activate"] is not None:
     if direction*(p["best"]-p["first_entry"])>=p["activate"]*p["atr"]:
      p["activated"]=True
     if p["activated"]:
      next_stop=p["best"]-direction*p["distance"]*p["atr"]
      p["stop"]=(max(p["stop"],next_stop) if direction==1
         else min(p["stop"],next_stop))
    p["hour_best"]=closes[s]
  # The UTC close yields profit-day qualification.
  if (t+M)%DAY==0:
   gain=eq(closes)-daybase
   if gain>0:positive_daily.append(gain)
   if gain>=initial*.005:
    if phase<3:profitable_days+=1
    else:funded_days+=1
   daily.append(dict(date=iso(t+M)[:10],phase=phase,
     equity=nice(eq(closes)),realized=nice(cash-initial),
     day_pnl=nice(gain),occupied_slots=slots(),
     qualified_days=profitable_days if phase<3 else funded_days,
     stage_target_pct=(5 if phase==1 else 8 if phase==2 else 0),
     turbo_floor=nice(peak*.94) if account["kind"]=="turbo" else None))
  max_cash_gain=max(max_cash_gain,cash-initial)
 # Attempt a flat portfolio phase transfer at period end if already qualified.
 if breach is None and account["kind"]=="basic" and not positions:
  transfer_if_eligible(end,last_close)
 mark=eq(last_close)
 summed_win=sum(max(0,r["net"]) for r in ledger)
 summed_loss=-sum(min(0,r["net"]) for r in ledger)
 per_asset={}
 for s in assets:
  x=[r for r in ledger if r["asset"]==s]
  per_asset[s]=dict(closed=len(x),win=sum(r["net"]>0 for r in x),
    net_closed=nice(sum(r["net"] for r in x)),
    additions=sum(r["added"] for r in x),
    stops=sum(r["reason"].startswith("stop") for r in x),
    takes=sum(r["reason"].startswith("take") for r in x),
    time_exits=sum(r["reason"]=="time" for r in x))
 latest_open={s:dict(side=p["side"],legs=p["legs"],
     opened=iso(p["entry_t"]),average_price=nice(p["avg"]),
     unrealized_usd=nice(p["side"]*p["qty"]*(last_close[s]-p["avg"])),
     original_stop=nice(p["initial_stop"]),
     live_stop=nice(p["stop"]),take=nice(p["take"]))
   for s,p in positions.items()}
 n=len(ledger)
 summary=dict(account=account["name"],mode=mode,
   period_start=iso(start),period_end=iso(end),actually_tested_until=iso(last_t+M),
   survived_full_period=breach is None,breach=breach,
   assets=list(assets),
   number_closed=n,win_rate_pct=nice(sum(r["net"]>0 for r in ledger)*100/n) if n else None,
   profit_factor=nice(summed_win/summed_loss) if summed_loss else None,
   closed_pnl_usd=nice(sum(r["net"] for r in ledger)),
   profit_of_closed_by_phase=per_asset,
   final_equity_usd=nice(mark),final_cash_usd=nice(cash),
   phase_now=phase,phases=phases,phase_realized_gains_usd=[nice(x) for x in phase_realized_gains],
   funded_profit_realized_usd=nice(cash-initial) if phase==3 else None,
   funded_profit_marked_usd=nice(mark-initial) if phase==3 else None,
   max_equity_usd=nice(peak),max_peak_to_trough_dd_pct=nice(max_dd),
   max_daily_loss_proxy_usd=nice(worst_day_loss),
   fees_spread_usd=nice(fees),funding_usd=nice(funding),
   worst_fund_pnl_conservative=nice(disallowed_60),
   ambiguous_api_close_60s=ambiguous_60,
   fresh_entries=opened,
   confirmed_repeat_signals=second_seen,repeat_while_loss=repeat_underwater,
   add_eligible_attempts=attempts,actual_adds=len(adds),
   add_rejected_full_slots=adds_blocked_full,
   repeat_skipped_favorable=adds_not_underwater,
   repeat_after_stop=adds_touched_stop,
   opposite_signals_ignored=opposite_signals,
   repeat_after_second_ignored=subsequent_repeat,
   fresh_signals_blocked_max_slots=missing_slots_new,
   max_slots_occupied=max_slots,max_open_assets=max_open_assets,
   max_nominal_used_usd=nice(max_nominal),
   max_notional_used_pct=nice(max_nominal/initial*100),
   current_open_positions=latest_open,
   end_unrealized_estimate_usd=nice(mark-cash),
   max_single_closed_hold_hours=nice(max((r["holding_hours"] for r in ledger),default=0)),
   max_realized_profit_unreset_phase_usd=nice(max_cash_gain),
   total_funded_qualified_days=funded_days,
   no_payouts=True)
 if details:return summary,dict(trades=ledger,adds=adds,daily=daily)
 return summary,None

def synthetic_unit():
 start=0;end=50*H
 names=("A","B","C")
 def data(x):
  out={}
  for t in range(start,end,M):
   v=99. if x=="A" and t>=4*H else 100.
   out[t]=(t,v,v+.001,v-.001,v)
  return out
 raw={s:data(s) for s in names}
 params={s:(10.,20.,None,None) for s in names}
 ev={
   "A":{0:dict(side=1,atr_4h=1.),4*H:dict(side=1,atr_4h=1.),
        8*H:dict(side=1,atr_4h=1.)},
   "B":{0:dict(side=1,atr_4h=1.)},
   "C":{4*H:dict(side=1,atr_4h=1.)}
 }
 account=dict(ACCOUNT["Basic_5000_noAPI"])
 base,logs=sim(raw,ev,params,names,account,start,end,"baseline_48",False,True)
 add,logadd=sim(raw,ev,params,names,account,start,end,"add_loss_second_48",False,True)
 anyv,logany=sim(raw,ev,params,names,account,start,end,"add_any_second_48",False,True)
 assert base["actual_adds"]==0 and base["max_slots_occupied"]==3,base
 assert add["actual_adds"]==1 and add["max_slots_occupied"]==3,add
 assert add["fresh_signals_blocked_max_slots"]==1,add
 assert add["confirmed_repeat_signals"]==1,add
 assert add["repeat_after_second_ignored"]==1,add
 assert anyv["actual_adds"]==1,anyv
 assert len(logadd["adds"])==1 and logadd["adds"][0]["asset"]=="A"
 assert logadd["adds"][0]["sl_price"]==90. and logadd["adds"][0]["tp_price"]==120.
 assert add["max_nominal_used_usd"]==3000 and base["max_nominal_used_usd"]==3000
 assert all(r["holding_hours"]<=48.001 for r in logadd["trades"]),logadd["trades"]
 # Three pre-existing slots must BLOCK repeat add, not create 80% leverage.
 ev2={"A":ev["A"],"B":ev["B"],"C":{0:dict(side=1,atr_4h=1.)}}
 block,_=sim(raw,ev2,params,names,account,start,end,"add_loss_second_48",False,True)
 assert block["actual_adds"]==0 and block["add_rejected_full_slots"]==1,block
 # On a positive repeat, ADD_ANY adds but ADD_LOSS does not.
 raw_positive={s:dict(values) for s,values in raw.items()}
 for t in range(4*H,end,M):
  raw_positive["A"][t]=(t,101.,101.001,100.999,101.)
 neg,_=sim(raw_positive,ev,params,names,account,start,end,"add_loss_second_48")
 pos,_=sim(raw_positive,ev,params,names,account,start,end,"add_any_second_48")
 assert neg["actual_adds"]==0 and pos["actual_adds"]==1,(neg,pos)
 print("PORTFOLIO_SLOT_PRIORITY_AND_FROZEN_SLTP_UNIT_PASSED",
     json.dumps(dict(baseline=base["max_slots_occupied"],
       add=add["actual_adds"],blocked=block["add_rejected_full_slots"],
       all_slots=add["max_nominal_used_usd"],positive_repeat_add_any=pos["actual_adds"])),flush=True)

def main():
 allparams=check_document()
 assert set(allparams)==set(DOCUMENT_SYMS)
 params={s:allparams[s] for s in ASSETS}
 assert set(params)==set(ASSETS)
 synthetic_unit()
 data,_,manifest=source_load()
 assert set(data)==set(DOCUMENT_SYMS)
 signals={}
 for s in ASSETS:
  rows=sorted(data[s].values())
  hourly=ohlc_from_5m(rows,H)
  signals[s]=pine_events(hourly,expanded=False,atr_basis="prior")
  print("PORTFOLIO_INPUT",s,"bars5m",len(rows),
   "annual4hSignals",sum(START<=t<END for t in signals[s]),flush=True)
 output=dict(
   source_of_parameters="новые инструкции/README.md (READ-ONLY)",
   assets=list(ASSETS),excluded_assets=sorted(EXCLUDE),
   original_params=params,
   methodological_replay_periods={"annual":(iso(START),iso(END)),
       "q2":(iso(VALID_END),iso(END))},
   settings=dict(starting_trade_nominal_pct=20,add_nominal_pct=20,
     max_simultaneous_legs=3,max_total_nominal_pct=60,
     reentry_on_second_signal_only=True,
     same_direction_required=True,underwater_required_for_primary=True,
     add_only_if_slots_before_at_most=2,
     add_same_direction_priority_over_fresh_competing_entries=True,
     exactly_one_add_on_first_repeat_signal=True,
     hold_from_initial_entry_hours=48,stop_tp_anchored_to_original=True,
     ton_trailing_updated_only_at_closed_1h=True,
     fees_basic_one_way_pct=.008,fees_turbo_one_way_pct=.06,
     funding_per8h_pct=.015,spread_proxy_roundtrip_pct=.02,
     no_turbo_withdrawals=True),
   caveats=[
     "Same testable historical signal pine_events (SMA21 RSI12 EMA7), NOT exact user's RSI27 real Pine. No visual wick/wave/divergence.",
     "Second signal means first new confirmed closed-4h SAME SIDE indicator event during open position; no additions on opposite events.",
     "Default primary add requires losing initial leg at SECOND signal; alternate any-directional repeat tests without loss filter.",
     "All seven? NO: exactly SIX BTC ETH TON BNB XRP LINK, ICP/ZEC excluded.",
     "A fresh signal might be displaced when a repeated-signal add consumes final slot. Position slot limit exactly three of 20percent initial notional.",
     "Basic noAPI 5k modeled for trade-comparison although not an API-enabled new Basic purchase; API Basic10k modeled separately.",
     "Basic target phase transfer only when FLAT and required realized gains and UTC days met, at earliest next 5-minute check, never force closing open positions to promote. Real Upscale may differ.",
     "Two profit-day targets and 30pct on Basic API phases; 60-sec profitable exit after API increase conservatively assumed only if SAME 5m bar, cannot know exact seconds.",
     "Turbo no challenge; 6pct peak EQUITY including floating results; no daily limit. 30pct payout rule only, no payouts executed.",
     "Risk 5m close may miss intrabar breach; stop-bounded high-before-low path is conservative and may falsely assume synchronous coin extrema.",
     "Funding 0.015pct per 8h charged at bar start against CURRENT quote nominal of already-open positions; costs proxy, not exact Upscale.",
     "No 100-second early close order for 48h, close by 5m bar end exactly at 48h instead.",
     "Pending/unfilled API orders, slippage, true spreads, exact price oracle or Upscale transaction log not available.",
     "No live orders; frozen actual trade settings in README unchanged.",
     "No actual ETH/TON inherited live positions recreated.",
     "Total closed PNL across phases != funded-only earnings or available withdrawal.",
     "Research includes Q2 as diagnostic, not evidence of robust future returns.",
   ],
   data_source_manifest={s:manifest[s] for s in ASSETS},
   scenarios={})
 for period,start,end in (("annual",START,END),("q2",VALID_END,END)):
  for ac_name,cfg in ACCOUNT.items():
   for mode in MODES:
    for stress in (False,True):
     key="/".join((period,ac_name,mode,
       "stress_stopbounded" if stress else "observed_5m_close"))
     summary,detail=sim(data,signals,params,ASSETS,cfg,start,end,mode,stress,True)
     output["scenarios"][key]=dict(summary=summary,details=detail)
     print("SIX_ASSET_PORTFOLIO_RESULT",key,json.dumps(summary,ensure_ascii=False),flush=True)
 OUT.mkdir(parents=True,exist_ok=True)
 p=OUT/"results.json"
 p.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
 print("SIX_ASSET_PORTFOLIO_COMPLETE",str(p),p.stat().st_size,
       len(output["scenarios"]),flush=True)
if __name__=="__main__":main()
