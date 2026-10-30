"""Same-budget $120 personal compounding vs $120 fee for $10,000 Upscale Basic.

Reuses unmodified six-asset, 4h, ATR, TON trailing and 48h criteria from
portfolio_six_no_icp_zec_20pct/compare_add_second_signal.py.
Personal 1x Bybit linear futures (VIP0 taker 0.055% each side), 20% of
CURRENT equity PER NEW ORDER; three slots at maximum. Re-invest gains.
Prop: 20% of FIXED $10k/phase, Basic 0.008% per side; after passing both
phases, 80% trader payout, only when full 14d + 5 qualifying 0.5%
days + best-day <30% total profit on API.
Both: spread proxy roundtrip 0.02%; funding 0.015% every 8h is shared
conservative proxy. Additional own zero-funding sensitivity.
No payout or stage without due eligibility. No actual orders.

This is HISTORICAL not live; Pine parity not certified.
Official sources: docs.upscale.trade/how-to-join-upscale/participation_requirements
docs.upscale.trade/how-upscale-works/api_trading
docs.upscale.trade/how-upscale-works/withdrawal_rules
bybitglobal.com/en/help-center/article/Trading-Fee-Structure
"""
import sys,json,math,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.portfolio_six_no_icp_zec_20pct.compare_add_second_signal import (
 ASSETS,ACCOUNT,MAX_SLOTS,MODES,SPREAD,FUNDING,POSITION_FRAC,
 H,DAY,M,START,VALID_END,END,iso,nice)
from experiments.new_instructions_8asset_48h.backtest import check_document
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events
DEST=Path("experiments/personal_120_vs_upscale_10k")

def sim_capital(raw,signals,params,assets,account,start,end,mode,payouts_enabled=False,details=False):
 assert mode in MODES
 assert account["kind"] in ("basic","personal")
 assert not payouts_enabled or account["kind"]=="basic"
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
  hard_floor=(.90*initial if account["kind"]=="basic" else 0.)
  day_floor=daybase*.95 if account["kind"]=="basic" else None
  if v<=hard_floor+1e-10 or (day_floor is not None and v<=day_floor+1e-10):
   typ=("personal_bankruptcy" if compound else
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
  actual_committed=sum(p["committed_notional_usd"] for p in positions.values())
  max_nominal=max(max_nominal,actual_committed)
  if eq(opens)>0 and actual_committed>0:
   max_exposure_eq_pct=max(max_exposure_eq_pct,100*actual_committed/eq(opens))
  assert slots()<=MAX_SLOTS
  if not compound:assert actual_committed<=initial*.6000000001
  # Risk at OPEN before intrabar stop/take.
  if risk_check(t,opens,"five_min_open_after_entries_funding"):break
  if False and positions:
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
  # Turbo only: user's earliest available fortnightly withdrawal.
  # Requires >=14 days since account/start of last successful cycle,
  # >=5 qualifying 0.5%-of-initial USD-equity UTC days, best positive
  # day <30% of this cycle's realized profit; flat portfolio only.
  # Instant simulated settlement, not verified real venue availability.
  if (account["kind"]=="basic" and phase==3):
   now=t+M
   gross_profit=cash-payout_baseline
   available_cash=max(0.,cash-initial)
   best=max(positive_daily,default=0.)
   ratio=(best/gross_profit if gross_profit>0 else None)
   if (now-payout_start>=14*DAY and funded_days>=5
       and not positions and gross_profit>0 and available_cash>=1):
    if best_consistency_at_payout_window is None or ratio<best_consistency_at_payout_window:
     best_consistency_at_payout_window=ratio
    if ((not api) or ratio<.30):
     if first_payout_eligible is None:
      first_payout_eligible=dict(at=iso(now),gross_cash_available=nice(available_cash),
         consistency_pct=nice(100*ratio),qualified_days=funded_days)
     if payouts_enabled:
      gross=min(available_cash,.4*initial)
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
   turbo_purchase_price_usd=None,
   net_wallet_after_turbo_purchase_usd=None,
   minimum_30pct_ratio_in_cashout_window_pct=nice(100*best_consistency_at_payout_window) if best_consistency_at_payout_window is not None else None)
 if details:return summary,dict(trades=ledger,adds=adds,daily=daily)
 return summary,None


def main():
 params_all=check_document()
 params={s:params_all[s] for s in ASSETS}
 raw,_,manifest=source_load()
 events={}
 for s in ASSETS:
  hrs=ohlc_from_5m(sorted(raw[s].values()),H)
  events[s]=pine_events(hrs,expanded=False,atr_basis="prior")
  print("OWN_VS_PROP_INPUT",s,len(hrs),flush=True)
 modes=("baseline_48","add_loss_second_48")
 variants={
  "own_120_bybit_taker_funding_015":dict(name="own_120_bybit_taker_funding_015",
        kind="personal",initial=120.,api=False,fee=.00055,funding_rate=.00015),
  "own_120_bybit_taker_no_funding":dict(name="own_120_bybit_taker_no_funding",
        kind="personal",initial=120.,api=False,fee=.00055,funding_rate=0.),
  "own_120_bybit_maker_funding_015":dict(name="own_120_bybit_maker_funding_015",
        kind="personal",initial=120.,api=False,fee=.0002,funding_rate=.00015),
  "prop_10k_api":dict(name="prop_10k_api",
        kind="basic",initial=10000.,api=True,fee=.00008,funding_rate=.00015),
  "prop_10k_manual_noapi":dict(name="prop_10k_manual_noapi",
        kind="basic",initial=10000.,api=False,fee=.00008,funding_rate=.00015)
 }
 scenarios={}
 for window,begin,finish in (("annual",START,END),("q2",VALID_END,END)):
  for mode in modes:
   for name,case in variants.items():
    if window=="q2" and name.endswith("maker_funding_015"):continue
    if window=="q2" and name.endswith("taker_no_funding"):continue
    run_payout=case["kind"]=="basic"
    summary,detail=sim_capital(raw,events,params,ASSETS,case,begin,finish,
       mode,payouts_enabled=run_payout,details=True)
    key="/".join((window,mode,name))
    scenarios[key]=dict(summary=summary,details=detail)
    print("OWN_VS_PROP_CASE",key,json.dumps(dict(
       equity=summary["final_equity_usd"],cash=summary["final_cash_usd"],
       total_trading_pnl=summary["closed_pnl_usd"],
       phase=summary["phase_now"],phases=summary["phases"],
       funded_realized=summary["funded_profit_realized_usd"],
       withdraws=summary["payouts"],wallet=summary["wallet_received_usd"],
       first_payout_candidate=summary["first_cashout_eligible_if_requested"],
       n=summary["number_closed"],winrate=summary["win_rate_pct"],
       risk=summary["max_peak_to_trough_dd_pct"],
       max_invested_pct_current_equity=summary["max_invested_pct_of_current_equity"],
       breach=summary["breach"],adds=summary["actual_adds"],
       fees=summary["fees_spread_usd"],funding=summary["funding_usd"],
       still_open=summary["current_open_positions"]),ensure_ascii=False),flush=True)
 # Regression: original fixed-prop 20% model must match previous historical
 # stage dates before any new payout scenario's influence.
 # The stage-transition mechanism is unchanged by funded payouts.
 ref=scenarios["annual/baseline_48/prop_10k_api"]["summary"]
 assert abs(ref["closed_pnl_usd"]-4091.2968)<.05, ref["closed_pnl_usd"]
 assert len(ref["phases"])==2 and abs(sum(z["days"] for z in ref["phases"])-314.1666)<.03,ref["phases"]
 assert ref["breach"] is None and ref["max_slots_occupied"]==3
 # Own position amount should actually change: notional is 20% of equity
 # at entry and must not be mistakenly frozen at original $24.
 own=scenarios["annual/baseline_48/own_120_bybit_taker_funding_015"]
 assert own["summary"]["max_nominal_used_usd"]!=72.0,own["summary"]
 # No withdrawal on challenge phase.
 for key,case in scenarios.items():
  x=case["summary"]
  if "prop_10k" in key:
   assert x["payout_count"]==len(x["payouts"])
   assert all(z["at"]>x["phases"][-1]["completed"] for z in x["payouts"]) if x["phases"] else x["payout_count"]==0
 DEST.mkdir(parents=True,exist_ok=True)
 result=dict(source="новые инструкции/README.md; unchanged",
    compare="own $120 compounding versus $120 non-refundable price for Upscale $10,000 Basic",
    six_assets=ASSETS,initial_outlay_usd=120.,
    assumptions=[
     "Own account uses 1x USDT-M linear positions and 20% CURRENT marked equity at each new order; add also recomputed from CURRENT marked equity.",
     "Personal account has no imposed prop 5pct daily /10pct total; it can suffer ordinary trading losses and loses full $120 if exhausted.",
     "Own Bybit USDT perpetual VIP0 taker fee 0.055% per side (0.02% maker alternative); actual user fee may vary by region/VIP.",
     "OWN FUNDING 0.015pct/8h scenario is a COMMON EXPENSE PROXY, NOT verified Bybit history; no-funding sensitivity also run.",
     "If own account uses spot rather than perpetual this is NOT a matching comparison; perpetual shorts and funding assumed.",
     "Prop Basic $10000 nominal is not withdrawable money; user pays $120 non-refundable fee and keeps 80% of payouts IF funded and eligible.",
     "Prop API option active means 30pct consistency at each phase and funded payout; noAPI manual sensitivity only, not permission for browser automation.",
     "Funded payouts at EARLIEST 5m flat mark after first 14 days, >=5 UTC equity positive days each >=0.5pct of $10000, and API best day strictly <30% of period realized profit. 80/20 split; 40pct cap per request. Instant approval is optimistic.",
     "Prop account initial position $2000 each and max3 slots; own initial $24 and max3 slots; notional sizes freeze at execution; existing opens are not retroactively resized as equity changes.",
     "Both are same 6-asset portfolio BTC ETH TON BNB XRP LINK, no ICP/ZEC, same closed 4h signals and original ATR SL/TP 48h, TON trailing after closed 1h.",
     "For identical execution after costs, '$120 fee' prop payout must exceed $120 to be profitable; nonwithdrawn model funded PNL is not a cash payout.",
     "0.02pct roundtrip spread proxy, 5m OHLC Binance USDT-M, no exact real Upscale mark and no Bybit funding history or live slippage.",
     "Exactly 20pct nominal per trade (not 20pct of account at risk) and no margin leverage above 1x on own.",
     "Research data Jul2025–Jun2026 plus Apr-Jun2026; repeatedly explored historical sample, not robust independent forward track.",
     "Original Pine historical signal differs from final prose user's RSI27 EMA7 Delta; cannot claim identical live signals.",
     "No real trading or payouts; changes are isolated under experiments/"
    ],
    price_source="User assumes about $120 Basic 10k; NOT verified as current Upscale price incl options, discounts",
    market_manifest={s:manifest[s] for s in ASSETS},
    scenarios=scenarios)
 path=DEST/"results.json"
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
 print("OWN_VS_PROP_COMPLETE",str(path),path.stat().st_size,flush=True)
if __name__=="__main__":main()
