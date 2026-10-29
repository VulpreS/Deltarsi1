"""Independent hourly equity audit of baseline portfolio with combined adverse marks."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
INITIAL=5000.;FEE=.0008;HALF_SPREAD=.0001
def replay(raw,sig,params,times,share):
 cash=INITIAL;pos={};day=None;daybase=None;minimum=(float("inf"),None);worstday=(-float("inf"),None,None);closesttotal=(float("inf"),None)
 daily=[];breaches=[];events=[];maxpositions=0
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+HALF_SPREAD) for s,z in pos.items())
 for t in times:
  bars={s:raw[s][t] for s in raw};opens={s:b[1] for s,b in bars.items()};closes={s:b[4] for s,b in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(opens)
  for s in sorted(raw):
   if t not in sig[s] or s in pos or len(pos)>=3:continue
   e=sig[s][t];a=e["atr_4h"];side=e["side"];o=opens[s];sl,tp,activation,distance=params[s]
   if a<=0:continue
   stop=o-side*sl*a;target=o+side*tp*a
   if min(stop,target)<=0:continue
   qty=INITIAL*share/o;cash-=INITIAL*share*(FEE+HALF_SPREAD)
   pos[s]=dict(side=side,qty=qty,entry=o,atr=a,stop=stop,target=target,activation=activation,distance=distance,best=o,active=False,entry_t=t)
  maxpositions=max(maxpositions,len(pos))
  adverse={s:(min(opens[s],bars[s][3]) if pos[s]["side"]==1 else max(opens[s],bars[s][2])) if s in pos else closes[s] for s in raw}
  worst=equity(adverse)
  if worst<minimum[0]:minimum=(worst,t)
  daily_loss=(daybase-worst)/daybase*100
  if worstday[1] is None or daily_loss>worstday[0]:worstday=(daily_loss,t,daybase-worst)
  total_margin=worst-INITIAL*.94
  if total_margin<closesttotal[0]:closesttotal=(total_margin,t)
  if worst<=daybase*.97 or worst<=INITIAL*.94:
   breaches.append(dict(time=iso(t),daily_pct=round(daily_loss,3),equity=round(worst,2),daily_base=round(daybase,2),open_positions=list(pos)))
  for s in list(pos):
   z=pos[s];side=z["side"];o,h,l,c=bars[s][1:];stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o
   elif side*(o-target)>=0:price=o
   elif (l<=stop if side==1 else h>=stop):price=stop
   elif (h>=target if side==1 else l<=target):price=target
   elif t-z["entry_t"]>=47*H:price=c
   else:price=None
   if price is not None:
    cash+=side*z["qty"]*(price-z["entry"])-z["qty"]*price*(FEE+HALF_SPREAD);del pos[s]
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  if (t+H)%DAY==0:daily.append(dict(date=iso(t),start_equity=round(daybase,2),end_equity=round(equity(closes),2)))
 return dict(min_equity=round(minimum[0],2),min_equity_at=iso(minimum[1]),max_daily_drawdown_pct=round(worstday[0],3),max_daily_drawdown_at=iso(worstday[1]),max_daily_drawdown_usd=round(worstday[2],2),closest_total_6pct_margin_usd=round(closesttotal[0],2),closest_total_at=iso(closesttotal[1]),hours_breaching_3_6=len(breaches),first_breaches=breaches[:8],max_positions=maxpositions,final_equity=round(equity({s:raw[s][times[-1]][4] for s in raw}),2))
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s);raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows)
 out={"note":"Conservative simultaneous intrahour adverse price marks; not a tick-exact reachable joint low. Replays positions after breaches to diagnose risk, not an actual continuing prop account.","results":{}}
 for group,syms in (("five_year",tuple(s for s in SYMS if s!="TONUSDT")),("six_common",SYMS)):
  common=set.intersection(*(set(raw[s]) for s in syms));end=max(common)+H;start=max(min(common),end-365*DAY)
  times=list(range(start,end,H))
  if any(t not in common for t in times):raise ValueError("Gap "+group)
  for share in (.2,.15,.1):
   key=f"{group}_{int(share*100)}pct"
   res=replay({s:raw[s] for s in syms},{s:sig[s] for s in syms},{s:baseline[s] for s in syms},times,share)
   out["results"][key]=res;print("EQUITY_AUDIT",key,json.dumps(res),flush=True)
 p=Path("experiments/prop_equity_audit/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
