"""Hourly close-only profit-day lock backtest. Three policies, challenge and payout counters."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
INITIAL=5000.; SHARE=.175;FEE=.0008;HALF_SPREAD=.0001
STAGES=((.05,3),(.08,5))
POLICIES=("baseline","challenge_target","payout_target","always_daily")
def run(raw,sig,params,times,policy,target=.0055):
 cash=INITIAL;pos={};day=None;daybase=INITIAL;daycash=INITIAL;locked=False
 stage=0;stage_start=INITIAL;stage_start_day=times[0]//DAY;stage_days=0
 payout_days=0;last_payout_day=None;last_paid_cash=INITIAL
 transitions=[];payouts=[];qual_days=0;lock_days=0;forced_closes=0;trades=0
 peak=INITIAL;max_dd=0.;max_day_dd=0.;breaches_basic=0;breaches_accel=0
 daily=[];first_day=times[0]//DAY
 def eq(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+HALF_SPREAD) for s,z in pos.items())
 def close(s,price):
  nonlocal cash,trades
  z=pos.pop(s);cash+=z["side"]*z["qty"]*(price-z["entry"])-z["qty"]*price*(FEE+HALF_SPREAD);trades+=1
 for t in times:
  d=t//DAY;bars={s:raw[s][t] for s in raw};opens={s:b[1] for s,b in bars.items()};closes={s:b[4] for s,b in bars.items()}
  if day!=d:
   day=d;daybase=eq(opens);daycash=cash;locked=False
  if not locked:
   for s in sorted(raw):
    if s in pos or len(pos)>=3 or t not in sig[s]:continue
    e=sig[s][t];a=e["atr_4h"];side=e["side"];o=opens[s];sl,tp,activation,distance=params[s]
    if a<=0:continue
    stop=o-side*sl*a;tp_price=o+side*tp*a
    if min(stop,tp_price)<=0:continue
    qty=INITIAL*SHARE/o;cash-=qty*o*(FEE+HALF_SPREAD)
    pos[s]=dict(side=side,qty=qty,entry=o,atr=a,stop=stop,tp=tp_price,activation=activation,distance=distance,best=o,active=False,entry_t=t)
  adverse={s:(bars[s][3] if pos[s]["side"]==1 else bars[s][2]) if s in pos else closes[s] for s in raw}
  worst=eq(adverse);peak=max(peak,eq(opens))
  max_dd=max(max_dd,(peak-worst)/peak*100)
  max_day_dd=max(max_day_dd,(daybase-worst)/daybase*100)
  breaches_basic+=int(worst<=INITIAL*.90 or worst<=daybase*.95)
  breaches_accel+=int(worst<=INITIAL*.94 or worst<=daybase*.97)
  for s in list(pos):
   z=pos[s];side=z["side"];o,h,l,c=bars[s][1:];stop=z["stop"];tp=z["tp"]
   if side*(o-stop)<=0:price=o
   elif side*(o-tp)>=0:price=o
   elif (l<=stop if side==1 else h>=stop):price=stop
   elif (h>=tp if side==1 else l<=tp):price=tp
   elif t-z["entry_t"]>=47*H:price=c
   else:price=None
   if price is not None:close(s,price)
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  # Evaluate at known hourly close; require REALIZED PNL after forced exit to exceed threshold.
  if not locked and policy!="baseline" and pos:
   estimated=eq(closes);enough=estimated>=daybase*(1+target)
   challenge_need=stage<2 and cash>=stage_start*(1+STAGES[stage][0]) and stage_days<STAGES[stage][1]
   payout_need=payout_days<5
   should_lock=policy=="always_daily" or (policy=="challenge_target" and challenge_need) or (policy=="payout_target" and payout_need)
   if enough and should_lock:
    # Verify projected liquidation is sufficient; eq already includes exit fee.
    for s in list(pos):close(s,closes[s]);forced_closes+=1
    if cash>=daybase*(1+.005):
     locked=True;lock_days+=1
  if (t+H)%DAY==0:
   end=eq(closes);good=(cash-daycash)>=daybase*.005
   if good:
    qual_days+=1;payout_days+=1
    if stage<2:stage_days+=1
   if stage<2 and cash>=stage_start*(1+STAGES[stage][0]) and stage_days>=STAGES[stage][1]:
    transitions.append(dict(stage=stage+1,day=d-first_day+1,date=iso(t)[:10],cash=round(cash,2),qualified_days=stage_days))
    stage+=1;stage_start=cash;stage_start_day=d+1;stage_days=0
   if payout_days>=5 and (last_payout_day is None or d-last_payout_day>=14) and cash>last_paid_cash:
    payouts.append(dict(day=d-first_day+1,amount=round(cash-last_paid_cash,2)))
    last_payout_day=d;last_paid_cash=cash;payout_days=0
   daily.append(dict(day=d-first_day+1,qualified=good,locked=locked,closed_pnl=round(cash-daycash,2),end_equity=round(end,2)))
   peak=max(peak,end)
 return dict(days=len(daily),stage1_day=next((x["day"] for x in transitions if x["stage"]==1),None),stage2_day=next((x["day"] for x in transitions if x["stage"]==2),None),qualifying_days=qual_days,locked_days=lock_days,forced_closes=forced_closes,trades=trades,final_equity=round(eq({s:raw[s][times[-1]][4] for s in raw}),2),return_pct=round((eq({s:raw[s][times[-1]][4] for s in raw})/INITIAL-1)*100,2),max_peak_drawdown_pct=round(max_dd,2),max_daily_drawdown_pct=round(max_day_dd,2),hours_basic_breach=breaches_basic,hours_accel_breach=breaches_accel,payout_count=len(payouts),first_payout_day=payouts[0]["day"] if payouts else None,mean_payout=round(sum(p["amount"] for p in payouts)/len(payouts),2) if payouts else None,payouts=payouts,daily=daily)
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s);raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows)
 out=dict(note="17.5% per position, 3 max; hourly close triggers at +0.55%, verified realized +0.5%; phase1 +5% 3 days, phase2 +8% 5 days. Payout days accumulate; 14d cooldown. Baseline proxy is NOT user RSI27 DeltaRSI. Payouts not debited, challenge phases modeled as continuous account; no prop account restart. In-sample parameters.",results={})
 for group,syms in (("five",tuple(s for s in SYMS if s!="TONUSDT")),("six",SYMS)):
  common=set.intersection(*(set(raw[s]) for s in syms));end=max(common)+H;start=max(min(common),end-365*DAY)
  full=list(range(start,end,H))
  if any(t not in common for t in full):raise ValueError("Gap")
  for window in (30,60,90,180,365):
   if window*DAY>end-start:continue
   for segment,begin in (("first",0),("last",len(full)-window*24)):
    if window==365 and segment=="last":continue
    times=full[begin:begin+window*24]
    for policy in POLICIES:
     result=run({s:raw[s] for s in syms},{s:sig[s] for s in syms},{s:baseline[s] for s in syms},times,policy)
     key=f"{group}_{window}d_{segment}_{policy}"
     out["results"][key]={k:v for k,v in result.items() if k!="daily"}
     print("DAYLOCK",key,json.dumps(out["results"][key]),flush=True)
 p=Path("experiments/daily_profit_lock/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
