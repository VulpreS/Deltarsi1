"""One-year isolated Upscale-style portfolio test; NO orders, NO API.
Three symbols, one position per symbol, 20% of initial phase balance per position.
1H stop-first, 4H closed signal, 00 UTC day equity limits.
"""
import sys,json,math,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from execution_core import resolve_bar
from experiments.full_exit_grid.run import levels
DAY=24*H
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT")
INITIAL=5000.;NOTIONAL=1000.;FEE=.0008;SPREAD=.0002
HOLD=48
MODES={
 "atr_all_no_be":{"BTCUSDT":(("atr",2.5),("atr",3.),False),"ETHUSDT":(("atr",2.5),("atr",3.),False),"ICPUSDT":(("atr",2.5),("atr",3.),False)},
 "best_by_asset_no_be":{"BTCUSDT":(("atr",2.5),("atr",3.),False),"ETHUSDT":(("atr",2.5),("atr",3.),False),"ICPUSDT":(("fixed",1.),("atr",3.),False)},
 "best_by_asset_be1":{"BTCUSDT":(("atr",2.5),("atr",3.),True),"ETHUSDT":(("atr",2.5),("atr",3.),True),"ICPUSDT":(("fixed",1.),("atr",3.),True)},
 "fixed_2pct_no_be":{s:(("fixed",2.),("fixed",2.),False) for s in SYMS},
 "fixed_2pct_be1":{s:(("fixed",2.),("fixed",2.),True) for s in SYMS},
 "fixed_1sl_2tp_no_be":{s:(("fixed",1.),("fixed",2.),False) for s in SYMS},
 "fixed_1sl_2tp_be1":{s:(("fixed",1.),("fixed",2.),True) for s in SYMS},
 "atr_sl_fixed_tp2_no_be":{s:(("atr",2.5),("fixed",2.),False) for s in SYMS},
 "atr_sl_fixed_tp2_be1":{s:(("atr",2.5),("fixed",2.),True) for s in SYMS},
 "fixed_sl2_atr_tp_no_be":{s:(("fixed",2.),("atr",3.),False) for s in SYMS},
 "fixed_sl2_atr_tp_be1":{s:(("fixed",2.),("atr",3.),True) for s in SYMS}
}
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def simulate(data,signals,times,mode,reset_phases=True):
 cash=INITIAL;pos={};day=None;daybase=INITIAL;peak=INITIAL;maxdd=0.;worstday=0.
 closed=[];daily=[];breach=None;qual_days=0;phase=1;phase_start=times[0];phases=[];maxopen=0
 skipped=0;consecutive=0;maxconsecutive=0;last=INITIAL;funding=0.
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*FEE for s,z in pos.items())
 for t in times:
  bars={s:data[s][t] for s in SYMS}
  op={s:b[1] for s,b in bars.items()};cl={s:b[4] for s,b in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(op)
  # Evaluate risk of existing positions before new entries; day baseline already fixed.
  for s in SYMS:
   if t not in signals[s]:continue
   if s in pos or len(pos)>=3:
    skipped+=1;continue
   e=signals[s][t];side=e["side"];atr=e["atr_4h"]
   if not math.isfinite(atr) or atr<=0:continue
   sm,tm,be=mode[s];o=op[s]
   stop,target=levels(o,atr,side,sm,tm)
   if min(stop,target)<=0:continue
   # Fixed $1000 notional, fees and half spread paid each side.
   q=NOTIONAL/o;cash-=NOTIONAL*(FEE+SPREAD/2)
   pos[s]=dict(side=side,qty=q,entry=o,stop=stop,target=target,be=be,active=False,
    trigger=o*(1+side*.01),entry_t=t,entry_fee=NOTIONAL*(FEE+SPREAD/2),entry_i=t//H)
  maxopen=max(maxopen,len(pos))
  # Intrahour conservative adverse stress; may overstate excursion if TP was earlier.
  adverse=dict(cl)
  for s,z in pos.items():
   o,h,l,c=bars[s][1:5];adverse[s]=min(o,l) if z["side"]==1 else max(o,h)
  worst=equity(adverse)
  maxdd=max(maxdd,(peak-worst)/peak*100)
  worstday=max(worstday,daybase-worst)
  if worst<=daybase*.95 or worst<=INITIAL*.90:
   breach=dict(time=iso(t),kind="daily" if worst<=daybase*.95 else "overall",equity=round(worst,2),daybase=round(daybase,2));break
  for s in list(pos):
   z=pos[s];bar=bars[s];side=z["side"]
   price,reason=resolve_bar(bar,side,z["stop"],z["target"])
   if reason is None and z["be"] and not z["active"]:
    triggered=bar[2]>=z["trigger"] if side==1 else bar[3]<=z["trigger"]
    if triggered:
     z["active"]=True;z["stop"]=z["entry"]
     if bar[3]<=z["entry"] if side==1 else bar[2]>=z["entry"]:
      price=z["entry"];reason="be_same_hour"
   if reason is None and (t-z["entry_t"])//H>=HOLD-1:
    price=bar[4];reason="time"
   if reason is not None:
    gross=side*z["qty"]*(price-z["entry"])
    exitcost=z["qty"]*price*(FEE+SPREAD/2)
    net=gross-z["entry_fee"]-exitcost
    cash+=gross-exitcost
    closed.append(dict(symbol=s,entry=iso(z["entry_t"]),exit=iso(t+H),reason=reason,net_usd=round(net,4),phase=phase))
    if net<0:consecutive+=1;maxconsecutive=max(maxconsecutive,consecutive)
    else:consecutive=0
    del pos[s]
  last=equity(cl);peak=max(peak,last)
  if last<=daybase*.95 or last<=INITIAL*.90:
   breach=dict(time=iso(t+H),kind="daily" if last<=daybase*.95 else "overall",equity=round(last,2),daybase=round(daybase,2));break
  if (t+H)%DAY==0:
   dayprofit=last-daybase
   if dayprofit>=INITIAL*.005:qual_days+=1
   daily.append(dict(utc=iso(t+H),equity=round(last,2),day_pnl=round(dayprofit,2),phase=phase))
   # Phase objectives: phase 1 +5% and 3 qualifying days; phase 2 +8% and 5 days.
   threshold=1.05 if phase==1 else 1.08
   required=3 if phase==1 else 5
   if phase<=2 and last>=INITIAL*threshold and qual_days>=required:
    phases.append(dict(phase=phase,completed=iso(t+H),days=round((t+H-phase_start)/DAY,2),qualifying_days=qual_days,equity=round(last,2)))
    if phase==1:
     # Separate virtual challenge phase with fresh $5k; flat only, defer reset if position open.
     if not pos:
      phase=2;phase_start=t+H;qual_days=0
      if reset_phases:
       cash=INITIAL;peak=INITIAL;day=None
    else:phase=3
 # Report both challenge status and continuous cash PnL; phase resets make PnL non-annualized.
 if not breach:
  last=equity({s:data[s][times[-1]][4] for s in SYMS})
 wins=sum(x["net_usd"]>0 for x in closed);loss=-sum(min(0,x["net_usd"]) for x in closed)
 gain=sum(max(0,x["net_usd"]) for x in closed)
 return dict(start=iso(times[0]),end=iso(times[-1]+H),days=len(times)/24,
  balance_or_equity_usd=round(last,2),return_since_last_phase_reset_pct=round((last/INITIAL-1)*100,3),
  phase_completed=phases,phase_now=phase,breach=breach,closed_trades=len(closed),
  win_rate_pct=round(100*wins/len(closed),2) if closed else None,
  profit_factor=round(gain/loss,3) if loss else None,
  max_intrahour_dd_pct=round(maxdd,3),worst_day_equity_drop_usd=round(worstday,2),
  max_losing_streak=maxconsecutive,max_concurrent=maxopen,skipped_signals=skipped,
  by_symbol={s:dict(trades=sum(x["symbol"]==s for x in closed),pnl_usd=round(sum(x["net_usd"] for x in closed if x["symbol"]==s),2)) for s in SYMS},
  closed_net_pnl_usd=round(sum(x["net_usd"] for x in closed),2),
  trades=closed,daily=daily)
def main():
 raw={};sig={};sha={}
 for s in SYMS:
  rows,sha[s]=load(s);raw[s]={x[0]:x for x in rows}
  ev,_=events(rows);sig[s]={e["entry_ms"]:e for e in ev["closed"]}
 common=set.intersection(*(set(v) for v in raw.values()))
 end=max(common);start=max(min(common),end-365*DAY+H)
 times=list(range(start,end+H,H))
 if any(t not in common for t in times):raise ValueError("Noncontiguous common cached hourly history")
 out=dict(title="Upscale 3-asset one-year portfolio research",source_sha=sha,
  config=dict(start=iso(times[0]),end=iso(times[-1]+H),days=len(times)/24,
   initial_usd=INITIAL,position_notional_usd=NOTIONAL,max_positions=3,
   fee_per_side=FEE,spread_roundtrip=SPREAD,
   daily_limit_pct=5,overall_limit_pct=10,day_reset="00 UTC",
   stages=[dict(target_pct=5,qualifying_days=3),dict(target_pct=8,qualifying_days=5)]),
  caveats=["Not a verified Upscale contract model; 5% day-start equity and static 10% original equity assumed.",
   "Phase 1 virtual reset occurs only if flat at checkpoint; otherwise phase 1 remains until a later eligible checkpoint.",
   "No leverage, fixed $1000 per trade, one trade per symbol, max three concurrent.",
   "No funding, slippage beyond synthetic 0.02% spread, mark-price or orderbook modeling.",
   "Hourly stop-first and conservative simultaneous adverse extrema; not exact intrahour order.",
   "Historical data previously inspected, no independent out-of-sample.",
   "Annual continuous return cannot be inferred from phase-reset equity; closed PnL across phases is provided.",
   "No live/demo orders."],scenarios={})
 for name,mode in MODES.items():
  result=simulate(raw,sig,times,mode,reset_phases=True)
  continuous=simulate(raw,sig,times,mode,reset_phases=False)
  result["continuous_annual"]=dict(end_equity_usd=continuous["balance_or_equity_usd"],return_pct=continuous["return_since_last_phase_reset_pct"],breach=continuous["breach"],closed_trades=continuous["closed_trades"],max_intrahour_dd_pct=continuous["max_intrahour_dd_pct"])
  out["scenarios"][name]=result
  print(name,json.dumps({k:v for k,v in result.items() if k not in ("trades","daily")}),flush=True)
 p=Path("experiments/upscale_year_portfolio/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
