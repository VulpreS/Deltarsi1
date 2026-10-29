"""Upscale Turbo: *immediate Funded* with trailing 6% of ALL-TIME equity peak.

Frozen canonical source: 'новые инструкции/README.md'; same 8 symbols,
4h Delta signal, ATR(14) from PRE-SIGNAL 4h bar, 1h TON trailing and
48h max hold. Sole size comparisons: 16.8%/16.9% of $5000 or $10000.
Turbo Crypto fees 0.06% each SIDE (not Basic's 0.008%),
funding 0.015% notional every 8h, dynamic spread proxies 0.02/0.04%.

See:
https://docs.upscale.trade/how-to-join-upscale/participation_requirements
https://docs.upscale.trade/trading-mechanics/fees
https://docs.upscale.trade/trading-mechanics/funding
https://docs.upscale.trade/how-upscale-works/withdrawal_rules

Two equity paths to bound unknown 5m intrabar order:
 CLOSE_5M: update equity HWM after 5m executions at 5m closes; checks each
   bar open and close and immediately after position entry/funding. This
   is optimistic: intrabar drawdowns and temporary equity highs missed.
 STRESS_5M: first assume all favorable extremes in a 5m bar are simultaneous,
   record peak; then ALL adverse extremes simultaneously, test 6% floor,
   BEFORE fills. This is intentionally overly conservative; cannot prove
   a real account would fail because stops may fill before adverse low and
   multi-asset extrema are asynchronous.

No payouts or manual risk reduction, even if payout eligibility achieved.
Payout would change the trailing base; MUST be modelled as a separate strategy.
"""
import sys,os,math,json,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_instructions_8asset_48h.backtest import check_document,SYMS,START,VALID_END,END,H
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

OUT=Path("experiments/new_instructions_8asset_48h/turbo_6pct")
DAY=24*H; M=5*60*1000
FEE_TURBO=.0006
FUNDING=.00015
RISK_FLOOR_FACTOR=.94
PAYOUT_DAYS=14
PROFIT_DAYS=5
CONSISTENCY=.30
MAX_POSITIONS=3
LIMIT_HOURS=48

def iso(x):return dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).isoformat()
def price_eq(cash,pos,prices,spread):
 return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-
    z["qty"]*prices[s]*(FEE_TURBO+spread/2) for s,z in pos.items())

def test_small():
 assert abs(5000*.169-845)<1e-8
 assert abs(10000*.169-1690)<1e-8
 assert abs(1000*FEE_TURBO-.6)<1e-8
 assert abs(5000*.94-4700)<1e-8
 assert abs(5500*.94-5170)<1e-8
 # In a no-withdrawal Turbo, moving the all-time high up cannot lower floor.
 peak=5000
 for equity in (5050,5230,5100,5500,5400):
  prev=peak*.94
  peak=max(peak,equity)
  assert peak*.94>=prev
 assert peak==5500
 print("TURBO_RULE_UNITS_PASS",flush=True)

def replay(data,signals,params,initial,start,end,pct,spread,stress):
 cash=initial;pos={};peak=initial;breach=None;maxdd=0.
 last_prices={s:data[s][start][1] for s in SYMS}
 fees=0.;funding=0.;trades=[];daily=[];skipped=0
 max_conc=0;max_hour_hold=0.;funding_events=0
 hour_peaks={};mark_samples=0
 first_eligible=None;last_day_equity=initial;gain_days=0;positive_days=[]
 alltime_equity_max_event=None
 final_t=start
 def eq(prices):return price_eq(cash,pos,prices,spread)
 def breach_obj(t,equity,kind,details=None):
  return dict(at=iso(t),kind=kind,equity=round(equity,4),
    trailing_peak_equity=round(peak,4),
    trailing_floor_equity=round(peak*RISK_FLOOR_FACTOR,4),
    deficit_usd=round(peak*RISK_FLOOR_FACTOR-equity,4),
    drawdown_pct=round(100*(peak-equity)/peak,4),
    trades_closed_before_breach=len(trades),open_positions=list(pos),
    details=details or {})
 def observe(t,cur,kind,mark_peak=True):
  nonlocal peak,breach,maxdd,alltime_equity_max_event,mark_samples
  mark_samples+=1
  # The current equity can first increase high-water mark, then be compared
  # to that peak. Use exact <= per challenge rules.
  if mark_peak and cur>peak:
   peak=cur;alltime_equity_max_event=iso(t)
  maxdd=max(maxdd,100*max(0,peak-cur)/peak)
  if cur<=peak*RISK_FLOOR_FACTOR+1e-10:
   breach=breach_obj(t,cur,kind)
   return True
  return False
 for t in range(start,end,M):
  final_t=t
  b={s:data[s][t] for s in SYMS}
  opens={s:v[1] for s,v in b.items()}
  closes={s:v[4] for s,v in b.items()}
  last_prices.update(opens)
  # The account starts funded, so NO phase reset and no daily 5% rule.
  # Funding on positions already opened BEFORE the scheduled timestamp.
  if t%(8*H)==0 and pos:
   for z in pos.values():
    f=z["notional"]*FUNDING
    cash-=f;funding+=f;z["funding"]+=f
    funding_events+=1
  # Signals from the closed 4h only. Intrabar 5m fills follow fixed stops.
  for s in SYMS:
   ev=signals[s].get(t)
   if ev is None:continue
   if s in pos or len(pos)>=MAX_POSITIONS:
    skipped+=1
    continue
   side=ev["side"];atr=ev["atr_4h"];entry=opens[s]
   if not (atr>0 and math.isfinite(atr) and entry>0):continue
   sl,tp,act,dist=params[s]
   stop=entry-side*sl*atr
   target=entry+side*tp*atr
   if min(stop,target)<=0:continue
   notional=initial*pct
   qty=notional/entry
   cost=notional*(FEE_TURBO+spread/2)
   cash-=cost;fees+=cost
   pos[s]=dict(side=side,entry=entry,qty=qty,notional=notional,
       stop=stop,target=target,entry_t=t,
       atr=atr,activation=act,distance=dist,
       best=entry,active=False,fees=cost,funding=0.,qty_closed=0.,
       peak_hour_high=entry,peak_hour_low=entry)
  max_conc=max(max_conc,len(pos))
  if observe(t,eq(opens),"opening_equity"):
   break
  if stress and pos:
   # Deliberately worst-case path: asynchronous multi-asset price extremes
   # treated simultaneous, and all highs assumed before all lows.
   good=dict(opens);bad=dict(opens)
   for s,z in pos.items():
    good[s]=b[s][2] if z["side"]==1 else b[s][3]
    bad[s]=b[s][3] if z["side"]==1 else b[s][2]
   if observe(t,eq(good),"hypothetical_5m_favorable_high"):
    break
   if observe(t,eq(bad),"hypothetical_5m_adverse_low",False):
    break
  # Fill the stop/TP as soon as a 5m bar hits it; stop priority on ties.
  # Trailing changes only at 1h bar CLOSE (after this 5m fills).
  for s in list(pos):
   z=pos[s];side=z["side"];_,o,h,l,c=b[s]
   stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o;reason="stop_gap"
   elif side*(o-target)>=0:price=o;reason="take_gap"
   elif (l<=stop if side==1 else h>=stop):price=stop;reason="stop"
   elif (h>=target if side==1 else l<=target):price=target;reason="take"
   elif t+M>=z["entry_t"]+LIMIT_HOURS*H:
    price=c;reason="time"
   else:price=None
   if price is not None:
    gross=side*z["qty"]*(price-z["entry"])
    cost=z["qty"]*price*(FEE_TURBO+spread/2)
    cash+=gross-cost;fees+=cost
    held=(t+M-z["entry_t"])/H
    max_hour_hold=max(max_hour_hold,held)
    trades.append(dict(symbol=s,entered=iso(z["entry_t"]),
     exited=iso(t+M),holding_hours=round(held,3),reason=reason,
     gross_usd=round(gross,4),net_usd=round(gross-z["fees"]-cost-z["funding"],4),
     fees_usd=round(z["fees"]+cost,4),funding_usd=round(z["funding"],4)))
    del pos[s]
   else:
    z["peak_hour_high"]=max(z["peak_hour_high"],h)
    z["peak_hour_low"]=min(z["peak_hour_low"],l)
  # After processed trades, evaluate observed 5m CLOSE. Genuine BTC spot
  # mark is UNKNOWN; Binance 5m close proxy, not Upscale oracle.
  last_prices.update(closes)
  if observe(t+M,eq(closes),"five_min_close"):
   break
  # Update trailing ONLY on closed 1H candle, with that hour's extremes.
  if (t+M)%H==0:
   for z in pos.values():
    side=z["side"]
    new_ext=z["peak_hour_high"] if side==1 else z["peak_hour_low"]
    z["best"]=max(z["best"],new_ext) if side==1 else min(z["best"],new_ext)
    if z["activation"] is not None:
     if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:
      z["active"]=True
     if z["active"]:
      candidate=z["best"]-side*z["distance"]*z["atr"]
      z["stop"]=max(z["stop"],candidate) if side==1 else min(z["stop"],candidate)
    z["peak_hour_high"]=z["peak_hour_low"]=closes[next(s for s,x in pos.items() if x is z)]
  if (t+M)%DAY==0:
   day_eq=eq(closes)
   daily_profit=day_eq-last_day_equity
   if daily_profit>=initial*.005:gain_days+=1
   if daily_profit>0:positive_days.append(daily_profit)
   last_day_equity=day_eq
   max_day=max(positive_days,default=0.)
   realized_profit=cash-initial
   ratio=max_day/realized_profit if realized_profit>0 else None
   # No payouts are performed, so this is a prospective right to request
   # first payout only, not proven available margin (use flat as conservative).
   eligible=(t+M-start>=PAYOUT_DAYS*DAY and gain_days>=PROFIT_DAYS
     and realized_profit>0 and ratio is not None and ratio<CONSISTENCY
     and not pos)
   snapshot=dict(date=iso(t+M)[:10],equity=round(day_eq,2),realized=round(realized_profit,2),
     hwm=round(peak,2),floor=round(peak*RISK_FLOOR_FACTOR,2),
     current_buffer=round(day_eq-peak*RISK_FLOOR_FACTOR,2),
     profit_days=gain_days,max_positive_day=round(max_day,2),
     consistency_ratio_pct=round(ratio*100,2) if ratio else None,
     consistency_ok=ratio is not None and ratio<CONSISTENCY,
     eligible_if_flat=eligible,flat=not bool(pos))
   daily.append(snapshot)
   if eligible and first_eligible is None:
    first_eligible=dict(snapshot)
    print("TURBO_FIRST_WITHDRAWABLE_DATE",initial,pct,spread,stress,
       json.dumps(first_eligible),flush=True)
 ending_equity=eq(last_prices)
 real_gain=cash-initial
 sum_wins=sum(max(z["net_usd"],0.) for z in trades)
 sum_losses=-sum(min(z["net_usd"],0.) for z in trades)
 result=dict(initial_usd=initial,allocation_pct=100*pct,
    nominal_per_position_usd=round(initial*pct,2),max_simultaneous_positions=MAX_POSITIONS,
    spread_proxy_pct_roundtrip=spread*100,
    intrabar_mode="stress_high_then_low_5m" if stress else "observed_5m_close_only",
    no_withdrawals=True,
    start=iso(start),requested_end=iso(end),tested_to=iso(final_t+M),
    account_survived_to_end=breach is None,
    breach=breach,
    final_equity_usd=round(ending_equity,2),
    end_realized_balance_usd=round(cash,2),
    high_water_mark_usd=round(peak,2),
    final_drawdown_floor_usd=round(peak*RISK_FLOOR_FACTOR,2),
    remaining_risk_buffer_usd=round(ending_equity-peak*RISK_FLOOR_FACTOR,2),
    max_peak_drawdown_pct=round(maxdd,3),
    first_hwm_peak_time=alltime_equity_max_event,
    gross_closed_profit_usd=round(sum(z["gross_usd"] for z in trades),2),
    net_closed_pnl_after_costs_usd=round(sum(z["net_usd"] for z in trades),2),
    commission_and_spread_usd=round(fees,2),funding_usd=round(funding,2),
    funding_events=funding_events,mark_samples=mark_samples,
    trades_closed=len(trades),win_rate_pct=round(sum(z["net_usd"]>0 for z in trades)/len(trades)*100,2) if trades else None,
    profit_factor=round(sum_wins/sum_losses,3) if sum_losses else None,
    exits=dict(stop=sum(z["reason"].startswith("stop") for z in trades),
       take=sum(z["reason"].startswith("take") for z in trades),
       time=sum(z["reason"]=="time" for z in trades)),
    max_holding_hours=round(max_hour_hold,2),max_open_positions_observed=max_conc,
    missed_signals=skipped,
    num_profit_days=gain_days,
    first_withdrawal_eligible_without_reset=first_eligible,
    time_until_failure_days=round((final_t+M-start)/DAY,3) if breach is not None else None,
    by_symbol={s:dict(closed_trades=sum(z["symbol"]==s for z in trades),
       net_usd=round(sum(z["net_usd"] for z in trades if z["symbol"]==s),2))
       for s in SYMS})
 return result,daily,trades

def main():
 test_small()
 params=check_document()
 raw5,_,manifest=source_load()
 assert set(raw5)==set(SYMS)
 signals={}
 for s in SYMS:
  hr=ohlc_from_5m(sorted(raw5[s].values()),H)
  signals[s]=pine_events(hr,expanded=False,atr_basis="prior")
  print("TURBO_DATA_CHECK",s,len(raw5[s]),len(hr),
    sum(START<=t<END for t in signals[s]),flush=True)
 output=dict(source_of_truth="новые инструкции/README.md",
   source_market="Binance USD-M 5m archives May 2025 through Jun 2026",
   parameters=params,market_manifest=manifest,
   official_rules=dict(turbo_direct_funded=True,no_daily_limit=True,
      peak_equity_risk_limit_pct=6,commission_turbo_crypto_per_side_pct=.06,
      funding_crypto_every_8h_pct=.015,
      min_profit_days_for_payout=5,min_days_before_payout=14,
      consistency_pct_applies_only_to_payout=30,
      payouts_not_executed=True,standard_profit_share_pct=80),
   caveats=[
      "5m OHLC execution differs from earlier 1h execution; signal/SL/TP/TON trailing only at 1h remain frozen.",
      "The stress path assumes ALL favorable 5m extrema across symbols simultaneously precede ALL adverse extrema; unrealistically conservative.",
      "5m closes are observational lower-frequency proxy, cannot guarantee absence of 6% breaches within any 5m bar.",
      "NO payouts simulated. Turbo trailing high watermark resets after payouts; real-life survival can differ if payouts are requested.",
      "Payout eligibility uses UTC daily equity changes, >=0.5% original nominal, max positive day <30% realized profit; official platform exact accounting/mark unverified.",
      "Turbo dynamic drawdown uses peak EQUITY with unrealized pnl, not initial account and not max closed cash balance.",
      "Costs include official 0.06% side fee and 0.015% / 8h; market spread approximated flat 0.02% or 0.04% round trip; real variable.",
      "No exact 100-second pre-48h time exit; close of 5m candle ending at 48h.",
      "5m OHLC stop-first if both stop and TP touched; no millisecond chronology.",
      "Position size fixed % of starting notional, up to three, no leverage applied.",
      "No observed Upscale price oracle equity ticks, no realistic external fill slippage.",
      "Pre-existing live ETH/TON positions excluded, test all NEW entries only.",
      "TradingView indicator parity not fully certified, no user discretionary wick/wave/divergence confirmations.",
      "Historical choices of ATR stop multipliers may overlap evaluation windows; no robust OOS guarantee.",
      "This backtest does NOT place any orders or certify real Upscale funded availability."],
   experiments={})
 cases=[
   ("turbo_5k_16p9_sp002",5000,.169,.0002),
   ("turbo_5k_16p9_sp004",5000,.169,.0004),
   ("turbo_5k_16p8_sp002",5000,.168,.0002),
   ("turbo_5k_16p0_sp002",5000,.160,.0002),
   ("turbo_5k_15p0_sp002",5000,.150,.0002),
   ("turbo_5k_14p0_sp002",5000,.140,.0002),
   ("turbo_5k_12p0_sp002",5000,.120,.0002),
   ("turbo_5k_10p0_sp002",5000,.100,.0002),
   ("turbo_10k_16p9_sp002",10000,.169,.0002)]
 for label,initial,pct,spread in cases:
  output["experiments"][label]={}
  periods=(("annual",START,END),) if label in {"turbo_5k_16p0_sp002","turbo_5k_15p0_sp002","turbo_5k_14p0_sp002","turbo_5k_12p0_sp002","turbo_5k_10p0_sp002"} else (("annual",START,END),("quarter_apr_jun",VALID_END,END))
  for period,start,end in periods:
   output["experiments"][label][period]={}
   for stress in (False,True):
    r,days,trades=replay(raw5,signals,params,initial,start,end,pct,spread,stress)
    key="stress_high_low" if stress else "observed_5m_close"
    output["experiments"][label][period][key]=dict(summary=r,daily=days,trade_log=trades)
    print("TURBO_RESULT",label,period,key,json.dumps(r,ensure_ascii=False),flush=True)
 OUT.mkdir(parents=True,exist_ok=True)
 path=OUT/"results.json"
 path.write_text(json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
 print("TURBO_BACKTEST_COMPLETED",str(path),path.stat().st_size,flush=True)
if __name__=="__main__":main()
