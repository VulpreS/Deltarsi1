"""Upscale official-rules sensitivity on canonical 8-coin 4h Delta RSI.

Verified rules 2026-10-29:
docs.upscale.trade/how-to-join-upscale/participation_requirements
docs.upscale.trade/how-upscale-works/api_trading
docs.upscale.trade/trading-mechanics/fees
docs.upscale.trade/trading-mechanics/funding
docs.upscale.trade/how-upscale-works/withdrawal_rules

NOT exact certification: source Binance 1h candles, not Upscale mark/fills;
spread proxied as flat 0.02%/0.04% roundtrip, 60s early fills unknown.
"""
import os,sys,json,math,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_instructions_8asset_48h.backtest import check_document,SYMS,START,VALID_END,END,H
from experiments.five_min_90d.optimize_partial_take_4h import source_load
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

OUT=Path("experiments/new_instructions_8asset_48h/official_rules_sensitivity")
DAY=24*H; FEE=.00008; FUNDING=.00015; POSITION_PCT=.169
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def consistency(maxday,profit,api):return not api or (profit>0 and maxday/profit<.3)

def sim(raw,signals,params,initial,start,end,api,spread,conservative):
 if api and initial<10000:raise ValueError("API requires >= $10000")
 cash=initial;pos={};phase=1;phase_start=start;pending=False
 day=None;daybase=initial;qual=0;positive_days=[];phases=[]
 fees=0.;fund=0.;peak=initial;maxdd=0.;breach=None;worst_day=0.
 ledger=[];daily=[];skipped=0;ambig=0;adjusted=0.;maxpos=0
 funded_start=None
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-
                   z["qty"]*prices[s]*(FEE+spread/2) for s,z in pos.items())
 for t in range(start,end,H):
  if pending and not pos:
   phase+=1;phase_start=t;cash=initial;qual=0;positive_days=[]
   daybase=initial;peak=initial;pending=False
   if phase==3:funded_start=t
  bars={s:raw[s][t] for s in SYMS}
  opens={s:v[1] for s,v in bars.items()}
  closes={s:v[4] for s,v in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(opens)
  if (t//H)%8==0:
   for z in pos.values():
    v=z["notional"]*FUNDING
    cash-=v;fund+=v;z["funding"]+=v
  for s in sorted(SYMS):
   ev=signals[s].get(t)
   if ev is None:continue
   if pending or s in pos or len(pos)>=3:skipped+=1;continue
   a=ev["atr_4h"];side=ev["side"];o=opens[s]
   if not math.isfinite(a) or a<=0 or o<=0:continue
   sl,tp,act,dist=params[s]
   stop=o-side*sl*a;target=o+side*tp*a
   if min(stop,target)<=0:continue
   notional=initial*POSITION_PCT;qty=notional/o
   fee=notional*(FEE+spread/2);fees+=fee;cash-=fee
   pos[s]=dict(side=side,qty=qty,notional=notional,entry=o,
       entry_t=t,stop=stop,target=target,atr=a,activation=act,
       distance=dist,best=o,active=False,entry_fee=fee,funding=0.)
  maxpos=max(maxpos,len(pos))
  bad=dict(closes)
  for s,z in pos.items():
   bad[s]=min(opens[s],bars[s][3]) if z["side"]==1 else max(opens[s],bars[s][2])
  worst=equity(bad)
  maxdd=max(maxdd,100*max(0,peak-worst)/peak)
  worst_day=max(worst_day,daybase-worst)
  if worst<=daybase*.95 or worst<=initial*.9:
   breach=dict(time=iso(t),phase=phase,kind="daily" if worst<=daybase*.95 else "total",
      equity=round(worst,2),daily_base=round(daybase,2))
   break
  for s in list(pos):
   z=pos[s];side=z["side"];_,o,h,l,c=bars[s]
   stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o;reason="stop_gap"
   elif side*(o-target)>=0:price=o;reason="take_gap"
   elif (l<=stop if side==1 else h>=stop):price=stop;reason="stop"
   elif (h>=target if side==1 else l<=target):price=target;reason="take"
   elif t-z["entry_t"]>=47*H:price=c;reason="time"
   else:price=None
   if price is not None:
    gross=side*z["qty"]*(price-z["entry"])
    cost=z["qty"]*price*(FEE+spread/2)
    unknown=api and t==z["entry_t"] and gross>0
    if unknown:ambig+=1
    counted=0. if unknown and conservative else gross
    if unknown and conservative:adjusted+=gross
    fees+=cost;cash+=counted-cost
    ledger.append(dict(symbol=s,phase=phase,entry=iso(z["entry_t"]),
      exit=iso(t+H),reason=reason,
      pnl=round(counted-cost-z["entry_fee"]-z["funding"],6),
      original_gross=round(gross,6),excluded=round(gross-counted,6)))
    del pos[s]
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  last=equity(closes);peak=max(peak,last)
  if last<=daybase*.95 or last<=initial*.9:
   breach=dict(time=iso(t+H),phase=phase,
     kind="daily" if last<=daybase*.95 else "total",
     equity=round(last,2),daily_base=round(daybase,2))
   break
  if (t+H)%DAY==0:
   dp=last-daybase
   if dp>0:positive_days.append(dp)
   if dp>=initial*.005:qual+=1
   best=max(positive_days,default=0.)
   realized=cash-initial
   target=.05 if phase==1 else (.08 if phase==2 else None)
   days_ok=qual>=(3 if phase==1 else 5)
   cons=consistency(best,realized,api)
   meets=bool(phase<=2 and realized>=initial*target
       and days_ok and cons and not pos)
   daily.append(dict(day=iso(t+H)[:10],phase=phase,
     equity=round(last,2),cash=round(cash,2),
     day_delta=round(dp,2),days_qualified=qual,
     max_profit_day=round(best,2),
     realized_profit=round(realized,2),
     consistency_ok=cons,eligible=meets))
   if meets and not pending:
    phases.append(dict(phase=phase,date=iso(t+H),
      days=round((t+H-phase_start)/DAY,2),
      qualifying_days=qual,realized_profit=round(realized,2),
      best_day=round(best,2),
      ratio_best_day=round(best/realized*100,2)))
    pending=True
 last=equity({s:raw[s][min(t,end-H)][4] for s in SYMS}) if "t" in locals() else initial
 fund_realized=cash-initial if phase==3 else None
 fund_mark=last-initial if phase==3 else None
 days_funded=sum(d["phase"]==3 and d["day_delta"]>=initial*.005 for d in daily)
 best_funded=max((d["day_delta"] for d in daily if d["phase"]==3),default=0.)
 payable=(phase==3 and not breach and funded_start is not None and
    end-funded_start>=14*DAY and days_funded>=5 and
    fund_realized>0 and consistency(best_funded,fund_realized,api))
 profit=sum(max(0,z["pnl"]) for z in ledger)
 loss=-sum(min(0,z["pnl"]) for z in ledger)
 summary=dict(start=iso(start),end=iso(end),account_usd=initial,
   api=api,notional_per_position=round(initial*POSITION_PCT,2),
   spread_roundtrip_pct=round(spread*100,4),
   conservative_60s=conservative,phase_now=phase,
   phases=phases,breach=breach,closed_trades=len(ledger),
   win_rate_pct=round(sum(z["pnl"]>0 for z in ledger)/len(ledger)*100,2) if ledger else None,
   profit_factor=round(profit/loss,3) if loss else None,
   closed_pnl_usd=round(sum(z["pnl"] for z in ledger),2),
   equity_end=round(last,2),cash_end=round(cash,2),
   max_dd_pct=round(maxdd,3),max_intrahour_day_loss_usd=round(worst_day,2),
   funded_profit_realized_usd=round(fund_realized,2) if fund_realized is not None else None,
   funded_profit_marked_usd=round(fund_mark,2) if fund_mark is not None else None,
   funded_profit_days=days_funded,possible_payout_eligibility=bool(payable),
   funded_consistency_ratio_pct=round(best_funded/fund_realized*100,2) if fund_realized and fund_realized>0 else None,
   total_fee_spread_usd=round(fees,2),total_funding_usd=round(fund,2),
   same_entry_hour_profitable_exits_60s_ambiguous=ambig,
   conservative_60s_disallowed_gross=round(adjusted,2),
   max_concurrent=maxpos,skipped_signals=skipped,
   by_symbol={s:dict(trades=sum(z["symbol"]==s for z in ledger),
      pnl=round(sum(z["pnl"] for z in ledger if z["symbol"]==s),2))
       for s in SYMS})
 return summary,daily,ledger

def main():
 assert abs(1000*FEE-.08)<1e-9
 assert abs(1000*FUNDING-.15)<1e-9
 assert not consistency(150,500,True)
 assert consistency(149.99,500,True)
 params=check_document()
 raw5,_,manifest=source_load()
 hour={};signal={}
 for s in SYMS:
  v=ohlc_from_5m(sorted(raw5[s].values()),H)
  hour[s]={x[0]:x for x in v}
  signal[s]=pine_events(v,expanded=False,atr_basis="prior")
  print("SOURCE_MATCHED",s,len(v),flush=True)
 variants=[
  ("basic_5k_spread002",5000,False,.0002,False),
  ("basic_5k_spread004",5000,False,.0004,False),
  ("api_10k_spread002_optimistic60",10000,True,.0002,False),
  ("api_10k_spread002_conservative60",10000,True,.0002,True),
  ("api_10k_spread004_conservative60",10000,True,.0004,True)]
 out=dict(strategy="новые инструкции",sizing_pct=16.9,
   params=params,market_sources=manifest,
   rules=dict(commission_per_side_pct=.008,
     funding_per_eight_hours_pct=.015,
     api_account_minimum_usd=10000,
     api_consistency_requires_less_than_pct=30,
     profit_hold_adjustment_seconds=60,
     payout_wait_days=14,payout_profit_days=5,
     phase1_profit_realized_pct=5,phase2_profit_realized_pct=8),
   caveats=[
     "Not exact exchange replay; flat proxy spreads while Upscale spread is dynamic and BTC/ETH can be zero",
     "1h OHLC cannot distinguish closes before versus after 60s; optimistic and conservative bounds",
     "Per-coin hourly worst adverse extremes assumed simultaneous, may overestimate drawdown",
     "Profit target based on realized cash; stage transitions only at UTC checkpoints while flat, rather than user-selected transfer",
     "Phase consistency approximated by max positive equity day / realized profit, may differ from platform's precise metric",
     "10k API scenario scales each position to $1690 and uses current rules; old 5k API not available in official docs",
     "No historical withdrawals or reset of payout period",
     "Existing older ETH/TON live positions excluded",
     "Binance OHLC source not Upscale mark quotes; market impact/real slippage not simulated",
     "No exact time request 100s before 48h; hour-close assumed",
     "Original single Delta Python backtest parity with current TradingView code not independently certified",
     "No live trade placement or proof of actual Upscale approval"],experiments={})
 for label,initial,api,spread,conservative in variants:
  out["experiments"][label]={}
  for key,st,en in (("year",START,END),("q2",VALID_END,END)):
   summary,daily,ledger=sim(hour,signal,params,initial,st,en,api,spread,conservative)
   out["experiments"][label][key]=dict(summary=summary,daily=daily,trades=ledger)
   print("OFFICIAL_COMPLIANCE_RESULT",label,key,json.dumps(summary,ensure_ascii=False),flush=True)
 OUT.mkdir(parents=True,exist_ok=True)
 p=OUT/"results.json";p.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
 print("OFFICIAL_COMPLIANCE_FINISHED",str(p),p.stat().st_size,flush=True)
if __name__=="__main__":main()
