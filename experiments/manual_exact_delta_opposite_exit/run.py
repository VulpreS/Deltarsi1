"""Exact manual DeltaRSI color transitions on closed 4h, reverse signal exits.
Research: same 5m OHLC engine as previous stop/TTL grid, but NO time exit.
On opposite medium->weak signal close current position at 5m bar open.
Same symbol reversal does NOT open new position on same timestamp.
Fixed SL N5/10/15/20, no TP, no BE; all other account rules unchanged.
"""
"""40-grid no-take study: fixed extreme SL from last N closed 4h bars,
N=5,10,15,20; forced close at H=12,16,20,24,32,40,48,52,56,60 hours.

Six assets BTC ETH TON BNB XRP LINK, ICP/ZEC excluded. Max three 20%
nominal slots. NO average/add, TP, break-even, or TON trailing.
Original closed 4h Delta signal remains unchanged. End-of-signal closed
4h candle INCLUDED among N for initial extreme; stops fixed at entry.
Long SL = 0.9998 * minimum low; short SL = 1.0002 * maximum high.
This fixed 0.02% buffer is a user-unspecified research choice, not tick
size. At most 3 open positions, 20% initial equity prop, own $120
compounds 20% CURRENT equity per new position.

Historical engine uses 5m OHLC stops, no precise intrabar sequence, and
official-approximate Basic and Turbo account rules. User's final RSI27
is NOT yet validated as equal to historic SMA21 RSI12-based signals.
NO real transactions; base README untouched. No out-of-sample guarantee.
"""
import sys,json,os,math,datetime as dt,argparse,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.portfolio_six_no_icp_zec_20pct.compare_add_second_signal import (
 ASSETS,MAX_SLOTS,MODES,SPREAD,FUNDING,POSITION_FRAC,
 H,DAY,M,START,VALID_END,END,iso,nice)
from experiments.new_instructions_8asset_48h.backtest import check_document
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

BASE=Path("experiments/manual_exact_delta_opposite_exit")
STOPS=(5,10,15,20)
HOURS=(60,) # dummy unused; NO TTL
BUFFER=.0002
ACCOUNTS={
  "personal_120":dict(name="personal_120",kind="personal",initial=120.,api=False,fee=.00055,funding_rate=.00015),
  "basic_10k_api":dict(name="basic_10k_api",kind="basic",initial=10000.,api=True,fee=.00008,funding_rate=.00015),
  "basic_10k_manual_noapi":dict(name="basic_10k_manual_noapi",kind="basic",initial=10000.,api=False,fee=.00008,funding_rate=.00015),
  "turbo_5k":dict(name="turbo_5k",kind="turbo",initial=5000.,api=False,fee=.0006,funding_rate=.00015)
}

def sim_extrema(raw,signals,assets,account,start,end,stop_bars,exit_hours,payouts_enabled=False,details=False,stress=False):
 assert stop_bars in (5,10,15,20) and exit_hours in (12,16,20,24,32,40,48,52,56,60)
 assert account["kind"] in ("basic","personal","turbo")
 assert not payouts_enabled or account["kind"] in ("basic","turbo")
 mode="baseline_48"
 initial=account["initial"];fee=account["fee"];api=account["api"]
 funding_rate=account.get("funding_rate",FUNDING)
 compound=account["kind"]=="personal"
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
 payout_start=start;payout_baseline=initial;payout_log=[]
 max_exposure_eq_pct=0.;min_equity=initial
 trader_wallet=0.;first_payout_eligible=None
 best_consistency_at_payout_window=None
 assert (end-start)%M==0
 def slots():return sum(p["legs"] for p in positions.values())
 def eq(prices):
  return cash+sum(p["side"]*p["qty"]*(prices[s]-p["avg"])-
     p["qty"]*prices[s]*(fee+SPREAD/2) for s,p in positions.items())
 def risk_check(t,prices,source):
  nonlocal peak,max_dd,breach,worst_day_loss,min_equity
  v=eq(prices)
  min_equity=min(min_equity,v)
  if v>peak:peak=v
  max_dd=max(max_dd,100*max(0,peak-v)/peak)
  worst_day_loss=max(worst_day_loss,daybase-v)
  hard_floor=(.90*initial if account["kind"]=="basic" else (.94*peak if account["kind"]=="turbo" else 0.))
  day_floor=daybase*.95 if account["kind"]=="basic" else None
  if v<=hard_floor+1e-10 or (day_floor is not None and v<=day_floor+1e-10):
   typ=("personal_bankruptcy" if compound else
       ("turbo_trailing_6pct" if account["kind"]=="turbo" else
       ("basic_daily_5pct" if v<=day_floor else "basic_total_10pct")))
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
     stop_final=nice(p["stop"]),take_original=None,
     exit_price=nice(price),holding_hours=nice((t+M-p["entry_t"])/H),
     net=round(adjusted-cost-p["entry_fee"]-p["funding"],6),
     gross=nice(adjusted),pre_api_gross=nice(gross),
     costs=nice(cost+p["entry_fee"]),funding=nice(p["funding"])))
  del positions[s]
 def new_position(s,t,price,event):
  nonlocal cash,fees,opened
  if slots()>=MAX_SLOTS:return False
  side=event["side"]
  stop=event["extreme_stops"][stop_bars]
  if stop<=0 or price<=0 or side*(price-stop)<=0:return False
  take=None;activate=None;distance=None;atr=event["atr_4h"]
  assert abs(stop-event["extreme_stops"][stop_bars])<1e-12
  usd=(max(0.,eq(opens))*POSITION_FRAC if compound else initial*POSITION_FRAC)
  if usd<=0:return False
  qty=usd/price
  cost=usd*(fee+SPREAD/2)
  cash-=cost;fees+=cost
  positions[s]=dict(side=side,avg=price,first_entry=price,
    qty=qty,legs=1,initial_notional_usd=usd,committed_notional_usd=usd,
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
  usd=(max(0.,eq(opens))*POSITION_FRAC if compound else initial*POSITION_FRAC)
  if usd<=0:return False
  qty=usd/price
  cost=usd*(fee+SPREAD/2)
  p["avg"]=(p["avg"]*p["qty"]+price*qty)/(p["qty"]+qty)
  p["qty"]+=qty;p["legs"]+=1;p["entry_fee"]+=cost
  p["committed_notional_usd"]+=usd
  p["last_increase_t"]=t
  cash-=cost;fees+=cost
  assert p["stop"]==oldstop and p["take"]==oldtake
  assert p["initial_stop"]==oldstop or p["activate"] is not None
  adds.append(dict(asset=s,at=iso(t),underwater=underwater,
    original_entry=nice(orig),second_price=nice(price),
    average_after=nice(p["avg"]),sl_price=nice(p["stop"]),
    tp_price=nice(p["take"]),slots_after=slots(),
    nominal_added_usd=usd))
  return True
 def transfer_if_eligible(t,prices):
  nonlocal phase,phase_start,cash,profitable_days,positive_daily,peak,funded_days,payout_start,payout_baseline
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
  if phase==3:
   payout_start=t;payout_baseline=initial
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
   if transfer_if_eligible(t,opens):
    # Phase reset can happen mid-UTC-day at first flat moment. Discard
    # pre-transfer day profit in the NEW stage accounting baseline.
    daybase=eq(opens)
  if t%DAY==0:
   daybase=eq(opens)
  # Funding for EXISTING exposure only at 00:00/08:00/16:00 UTC
  if t%(8*H)==0:
   for s,p in positions.items():
    charge=p["qty"]*opens[s]*funding_rate
    cash-=charge;funding+=charge;p["funding"]+=charge
  # Stop-gap / take-gap at first price of 5m. A close at the open may
  # preempt a same-timestamp signal, which is skipped for this coin.
  closed_at_open=set()
  for s,p in list(positions.items()):
   o=opens[s]
   if p["side"]*(o-p["stop"])<=0:
    close_position(s,t,o,"stop_gap");closed_at_open.add(s)
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
     close_position(s,t,opens[s],"opposite_delta_signal")
   elif s not in closed_at_open:
    fresh.append((s,event))
  for s,event in fresh:
   if slots()<MAX_SLOTS:new_position(s,t,opens[s],event)
   else:missing_slots_new+=1
  max_slots=max(max_slots,slots())
  max_open_assets=max(max_open_assets,len(positions))
  actual_committed=sum(p["committed_notional_usd"] for p in positions.values())
  max_nominal=max(max_nominal,actual_committed)
  if eq(opens)>0 and actual_committed>0:
   max_exposure_eq_pct=max(max_exposure_eq_pct,100*actual_committed/eq(opens))
  assert slots()<=MAX_SLOTS
  if not compound:assert actual_committed<=initial*.6000000001
  # Risk at OPEN before intrabar stop/take.
  if risk_check(t,opens,"five_min_open_after_entries_funding"):break
  if stress and positions:
   favorable=dict(opens);adverse=dict(opens)
   for s,p in positions.items():
    _,o,hi,lo,c=bars[s]
    if p["side"]==1:
     favorable[s]=hi
     adverse[s]=max(lo,p["stop"])
    else:
     favorable[s]=lo
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
   else:
    p["hour_best"]=max(p["hour_best"],hi) if direction==1 else min(p["hour_best"],lo)
    if False: # NO forced time exit; opposite Delta closes at next 4h opening
     close_position(s,t,c,"time")
  last_close=dict(closes)
  if risk_check(t+M,closes,"five_min_close_after_exits"):break
  # TON trailing disabled in this isolated fixed extreme stop experiment.
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
  # Turbo only: user's earliest available fortnightly withdrawal.
  # Requires >=14 days since account/start of last successful cycle,
  # >=5 qualifying 0.5%-of-initial USD-equity UTC days, best positive
  # day <30% of this cycle's realized profit; flat portfolio only.
  # Instant simulated settlement, not verified real venue availability.
  if ((account["kind"]=="basic" and phase==3) or account["kind"]=="turbo"):
   now=t+M
   gross_profit=cash-payout_baseline
   available_cash=max(0.,cash-initial)
   best=max(positive_daily,default=0.)
   ratio=(best/gross_profit if gross_profit>0 else None)
   if (now-payout_start>=14*DAY and funded_days>=5
       and not positions and gross_profit>0 and available_cash>=1):
    if best_consistency_at_payout_window is None or ratio<best_consistency_at_payout_window:
     best_consistency_at_payout_window=ratio
    if ((not api and account["kind"]!="turbo") or ratio<.30):
     if first_payout_eligible is None:
      first_payout_eligible=dict(at=iso(now),gross_cash_available=nice(available_cash),
         consistency_pct=nice(100*ratio),qualified_days=funded_days)
     if payouts_enabled:
      gross=min(available_cash,initial*(.5 if account["kind"]=="turbo" else .4))
      before_peak=peak
      before_equity=eq(closes)
      cash-=gross
      to_wallet=.80*gross
      trader_wallet+=to_wallet
      peak=eq(closes)
      assert abs(peak-cash)<1e-7
      payout_log.append(dict(at=iso(now),gross_requested=nice(gross),
        net_to_wallet=nice(to_wallet),best_day_ratio_pct=nice(100*ratio),
        qualifying_days=funded_days,old_peak=nice(before_peak),
        equity_before=nice(before_equity),equity_after=nice(peak),
        fresh_floor_94pct=nice(peak*.94)))
      payout_start=now;payout_baseline=cash
      funded_days=0;positive_daily=[];daybase=eq(closes)
      print("SIX_ASSET_TURBO_FORTNIGHT_PAYOUT",mode,iso(start),
       json.dumps(payout_log[-1],ensure_ascii=False),flush=True)
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
     live_stop=nice(p["stop"]),take=None)
   for s,p in positions.items()}
 n=len(ledger)
 summary=dict(account=account["name"],mode=mode,
   period_start=iso(start),period_end=iso(end),actually_tested_until=iso(last_t+M),
   stop_lookback_4h_bars=stop_bars,forced_close_hours=exit_hours,
   no_take_profit=True,no_trailing_stop=True,
   survived_full_period=breach is None,breach=breach,
   assets=list(assets),
   number_closed=n,win_rate_pct=nice(sum(r["net"]>0 for r in ledger)*100/n) if n else None,
   profit_factor=nice(summed_win/summed_loss) if summed_loss else None,
   closed_pnl_usd=nice(sum(r["net"] for r in ledger)),
   profit_of_closed_by_phase=per_asset,
   final_equity_usd=nice(mark),final_cash_usd=nice(cash),
   phase_now=phase,phases=phases,phase_realized_gains_usd=[nice(x) for x in phase_realized_gains],
   max_invested_pct_of_current_equity=nice(max_exposure_eq_pct),
   min_marked_equity_usd=nice(min_equity),
   fee_one_side_pct=fee*100,funding_one_period_pct=funding_rate*100,
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
   no_payouts=not payouts_enabled,
   payout_policy="first permitted >=14d >=5 gain days <30pct ratio, flat-only" if payouts_enabled else "no real payouts; eligibility monitor",
   payout_count=len(payout_log),payouts=payout_log,
   first_cashout_eligible_if_requested=first_payout_eligible,
   wallet_received_usd=nice(trader_wallet),
   turbo_purchase_price_usd=229 if account["kind"]=="turbo" else None,
   net_wallet_after_turbo_purchase_usd=nice(trader_wallet-229) if account["kind"]=="turbo" else None,
   minimum_30pct_ratio_in_cashout_window_pct=nice(100*best_consistency_at_payout_window) if best_consistency_at_payout_window is not None else None)
 if details:return summary,dict(trades=ledger,adds=adds,daily=daily)
 return summary,None




def make_extreme_signals(five,base_events):
 """Sidecar fixed stops from strictly completed 4h candles only."""
 bars=ohlc_from_5m(sorted(five.values()),4*H)
 assert len(bars)>210
 roll={}
 for index,b in enumerate(bars):
  e=b[0]+4*H
  if e not in base_events:continue
  orig=base_events[e]
  side=orig["side"]
  stops={}
  for n in STOPS:
   assert index+1>=n
   recent=bars[index-n+1:index+1]
   assert recent[-1][0]+4*H==e
   if side==1:
    rawlow=min(x[3] for x in recent)
    sl=rawlow*(1-BUFFER)
   else:
    rawhigh=max(x[2] for x in recent)
    sl=rawhigh*(1+BUFFER)
   stops[n]=sl
  roll[e]=dict(orig,extreme_stops=stops)
 assert set(roll)==set(base_events),(
  "signal-to-stop mapping mismatch",len(roll),len(base_events))
 return roll

def synthetic_units():
 # Gap through stop: must close worse than original stop at 5m open;
 # no TP even if price doubles; forced close exactly at selected horizon.
 begin=0;end=64*H
 data={}
 for t in range(begin,end,M):
  price=100. if t<12*H else 180.
  data[t]=(t,price,price+.01,price-.01,price)
 sig={0:dict(side=1,atr_4h=2,extreme_stops={n:90. for n in STOPS})}
 account=dict(ACCOUNTS["personal_120"])
 c,l=sim_extrema({"BTCUSDT":data},{"BTCUSDT":sig},
  ("BTCUSDT",),account,begin,end,5,12,details=True)
 assert c["number_closed"]==1 and c["breach"] is None,c
 assert l["trades"][0]["reason"]=="time" and l["trades"][0]["holding_hours"]==12.,l
 # More extreme stop but 60h time: a high price at 12h cannot
 # create TP; instead only time closes at 60h.
 c,l=sim_extrema({"BTCUSDT":data},{"BTCUSDT":sig},
  ("BTCUSDT",),account,begin,end,20,60,details=True)
 assert l["trades"][0]["reason"]=="time" and l["trades"][0]["holding_hours"]==60.,l
 # Hit fixed stop once, no moving average/trail.
 down={}
 for t in range(begin,end,M):
  px=100. if t<5*H else 89.
  down[t]=(t,px,px+.01,px-.01,px)
 c,l=sim_extrema({"BTCUSDT":down},{"BTCUSDT":sig},
  ("BTCUSDT",),account,begin,end,10,32,details=True)
 assert l["trades"][0]["reason"]=="stop_gap" and abs(l["trades"][0]["exit_price"]-89.)<1e-5,l
 assert c["max_slots_occupied"]<=3
 print("EXTREME_FIXED_SL_NO_TP_UNIT_PASS",flush=True)

def concise(s):
 return dict(survived=s["survived_full_period"],
    breach=s["breach"],closed=s["number_closed"],
    net_closed=s["closed_pnl_usd"],cash=s["final_cash_usd"],
    equity=s["final_equity_usd"],wr=s["win_rate_pct"],
    pf=s["profit_factor"],dd=s["max_peak_to_trough_dd_pct"],
    stage_count=len(s["phases"]),stages=s["phases"],
    profit_after_reset=s["funded_profit_realized_usd"],
    wallet=s["wallet_received_usd"],payout_count=s["payout_count"],
    exits_stop=sum(x["stops"] for x in s["profit_of_closed_by_phase"].values()),
    exits_time=sum(x["time_exits"] for x in s["profit_of_closed_by_phase"].values()),
    max_hold=s["max_single_closed_hold_hours"],
    fund=s["funding_usd"],fees=s["fees_spread_usd"],
    skipped=s["fresh_signals_blocked_max_slots"],
    open=s["current_open_positions"])


def main():
 import argparse
 from analyze_mtf_5y import indicator
 from experiments.manual_exact_delta_40grid.run import manual_color_events
 ap=argparse.ArgumentParser()
 ap.add_argument("--account",required=True,choices=sorted(ACCOUNTS))
 ap.add_argument("--period",required=True,choices=("annual","q2"))
 a=ap.parse_args()
 synthetic_units();check_document()
 raw,_,manifest=source_load()
 signals={}
 for asset in ASSETS:
  bars=ohlc_from_5m(sorted(raw[asset].values()),4*H)
  ev=manual_color_events(bars)
  signals[asset]=make_extreme_signals(raw[asset],ev)
  print("OPPOSITE_INPUT",asset,len(ev),flush=True)
 start,end=(START,END) if a.period=="annual" else (VALID_END,END)
 acc=ACCOUNTS[a.account]
 result={}
 for n in STOPS:
  s,details=sim_extrema(raw,signals,ASSETS,acc,start,end,n,60,
    payouts_enabled=acc["kind"]!="personal",details=True)
  result["stop"+str(n)]=dict(summary=s,details=details)
  print("OPPOSITE_RESULT",a.account,a.period,"stop"+str(n),json.dumps(concise(s),ensure_ascii=False),flush=True)
 dest=BASE/a.account/a.period/"results.json"
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(dict(account=a.account,period=a.period,stop_variants=list(STOPS),
  entry="medium->weak closed 4h, no extra filters",exit="opposite medium->weak closed 4h",
  stop="fixed 5/10/15/20 fully closed 4h candles, 0.02% buffer",no_ttl=True,
  no_take=True,no_break_even=True,results=result),ensure_ascii=False,indent=2))
 print("OPPOSITE_DONE",dest,flush=True)
if __name__=="__main__":main()
