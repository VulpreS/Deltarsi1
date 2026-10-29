"""Accumulative qualifying trading days payout simulation, 14-day minimum between withdrawals."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.three_account_models.run import SYMS,INITIAL,DAY,H,FEE,SPREAD
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
def simulate(raw,sig,params,times,share,day_mode):
 cash=INITIAL;pos={};day=None;daybase=INITIAL;daycash=INITIAL;days=[];peak=INITIAL
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+SPREAD) for s,z in pos.items())
 for t in times:
  bars={s:raw[s][t] for s in raw};opens={s:b[1] for s,b in bars.items()};closes={s:b[4] for s,b in bars.items()}
  if day!=t//DAY:day=t//DAY;daybase=equity(opens);daycash=cash
  for s in sorted(raw):
   if s in pos or len(pos)>=3 or t not in sig[s]:continue
   e=sig[s][t];a=e["atr_4h"];side=e["side"];o=opens[s];sl,tp,activation,distance=params[s]
   if a<=0:continue
   stop=o-side*sl*a;target=o+side*tp*a
   if min(stop,target)<=0:continue
   qty=INITIAL*share/o;cash-=qty*o*(FEE+SPREAD)
   pos[s]=dict(side=side,qty=qty,entry=o,atr=a,stop=stop,target=target,activation=activation,distance=distance,best=o,active=False,entry_t=t)
  for s in list(pos):
   z=pos[s];side=z["side"];o,h,l,c=bars[s][1:];stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o
   elif side*(o-target)>=0:price=o
   elif (l<=stop if side==1 else h>=stop):price=stop
   elif (h>=target if side==1 else l<=target):price=target
   elif t-z["entry_t"]>=47*H:price=c
   else:price=None
   if price is not None:
    cash+=side*z["qty"]*(price-z["entry"])-z["qty"]*price*(FEE+SPREAD);del pos[s]
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  if (t+H)%DAY==0:
   end=equity(closes)
   qualifying=(end-daybase>=daybase*.005) if day_mode=="equity" else (cash-daycash>=daybase*.005)
   days.append(dict(day=t//DAY,qualifying=qualifying,eq=end,cash=cash))
 # Account remains unchanged by withdrawals in this screening pass.
 eligible_days=0;last_payout_day=None;first_payout_day=None;payouts=[];last_paid_cash=INITIAL
 for d in days:
  if d["qualifying"]:eligible_days+=1
  if eligible_days>=5 and (last_payout_day is None or d["day"]-last_payout_day>=14) and d["cash"]>last_paid_cash:
   amount=d["cash"]-last_paid_cash
   payouts.append(dict(day=d["day"],days_from_start=d["day"]-days[0]["day"]+1,qualifying_days_accumulated=eligible_days,profit_available=round(amount,2)))
   last_payout_day=d["day"];last_paid_cash=d["cash"];eligible_days=0
 return dict(qualifying_days=sum(x["qualifying"] for x in days),total_days=len(days),first_payout_after_days=payouts[0]["days_from_start"] if payouts else None,payout_count=len(payouts),avg_days_between_payouts=round(sum(payouts[i]["day"]-payouts[i-1]["day"] for i in range(1,len(payouts)))/(len(payouts)-1),1) if len(payouts)>1 else None,mean_payout=round(sum(x["profit_available"] for x in payouts)/len(payouts),2) if payouts else None,total_payout=round(sum(x["profit_available"] for x in payouts),2),payouts=payouts,unpaid_closed_profit=round(cash-last_paid_cash,2),final_equity=round(days[-1]["eq"],2))
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s);raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows)
 out=dict(note="Five qualifying days accumulate without time limit. At least 14 days between payouts. Payout is positive incremental realized PnL. Withdrawals NOT subtracted from trading balance or turbo high-water mark: estimates are screening, not a true payout-adjusted prop account.",results={})
 for group,syms in (("five_year",tuple(s for s in SYMS if s!="TONUSDT")),("six_common",SYMS)):
  common=set.intersection(*(set(raw[s]) for s in syms));end=max(common)+H;start=max(min(common),end-365*DAY)
  times=list(range(start,end,H))
  if any(t not in common for t in times):raise ValueError("Missing bar")
  for share in (.175,.15,.2,.1):
   for method in ("closed","equity"):
    key=f"{group}_{share*100:g}pct_{method}"
    res=simulate({s:raw[s] for s in syms},{s:sig[s] for s in syms},{s:baseline[s] for s in syms},times,share,method)
    out["results"][key]=res
    print("ACCUMULATIVE_PAYOUT",key,json.dumps(res),flush=True)
 p=Path("experiments/accumulative_payouts/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
