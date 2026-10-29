"""Three Upscale account risk models; historical, conservative hourly OHLC audit."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
INITIAL=5000.;FEE=.0008;SPREAD=.0001
MODES={"basic":(.05,.10,False),"accelerated":(.03,.06,False),"turbo":(None,.06,True)}
def replay(raw,sig,params,times,share,mode):
 daily_limit,total_limit,trailing=MODES[mode]
 cash=INITIAL;positions={};day=None;daybase=INITIAL;peak=INITIAL
 min_equity=(float("inf"),None);worst_day=(-float("inf"),None,None);closest=(float("inf"),None,None)
 breaches=[];trades=0;max_positions=0
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+SPREAD) for s,z in positions.items())
 for t in times:
  bars={s:raw[s][t] for s in raw};opens={s:b[1] for s,b in bars.items()};closes={s:b[4] for s,b in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(opens)
  # Record a conservative high-water mark from prior hour closes, not a fictional simultaneous favorable high.
  peak=max(peak,equity(opens))
  for s in sorted(raw):
   if s in positions or len(positions)>=3 or t not in sig[s]:continue
   e=sig[s][t];a=e["atr_4h"];side=e["side"];o=opens[s]
   sl,tp,activation,distance=params[s]
   if a<=0:continue
   stop=o-side*sl*a;target=o+side*tp*a
   if min(stop,target)<=0:continue
   qty=INITIAL*share/o
   cash-=qty*o*(FEE+SPREAD)
   positions[s]=dict(side=side,qty=qty,entry=o,atr=a,stop=stop,target=target,activation=activation,distance=distance,best=o,active=False,entry_t=t)
  max_positions=max(max_positions,len(positions))
  adverse={s:(bars[s][3] if positions[s]["side"]==1 else bars[s][2]) if s in positions else closes[s] for s in raw}
  worst=equity(adverse)
  if worst<min_equity[0]:min_equity=(worst,t)
  day_loss=(daybase-worst)/daybase*100
  if day_loss>worst_day[0]:worst_day=(day_loss,t,daybase-worst)
  floor=(peak if trailing else INITIAL)*(1-total_limit)
  buffer=worst-floor
  if buffer<closest[0]:closest=(buffer,t,floor)
  violation=worst<=floor or (daily_limit is not None and worst<=daybase*(1-daily_limit))
  if violation and not breaches:
   breaches.append(dict(time=iso(t),equity=round(worst,2),floor=round(floor,2),daily_base=round(daybase,2),daily_loss_pct=round(day_loss,3),positions=list(positions)))
  # Intrabar stop-first fills, gap-aware, same as prior equity audit.
  for s in list(positions):
   z=positions[s];side=z["side"];o,h,l,c=bars[s][1:]
   stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o
   elif side*(o-target)>=0:price=o
   elif (l<=stop if side==1 else h>=stop):price=stop
   elif (h>=target if side==1 else l<=target):price=target
   elif t-z["entry_t"]>=47*H:price=c
   else:price=None
   if price is not None:
    cash+=side*z["qty"]*(price-z["entry"])-z["qty"]*price*(FEE+SPREAD)
    del positions[s];trades+=1
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  peak=max(peak,equity(closes))
 return dict(first_breach=breaches[0] if breaches else None,min_equity=round(min_equity[0],2),min_equity_at=iso(min_equity[1]),worst_daily_pct=round(worst_day[0],3),worst_daily_usd=round(worst_day[2],2),worst_daily_at=iso(worst_day[1]),min_total_buffer_usd=round(closest[0],2),min_total_buffer_at=iso(closest[1]),floor_at_min_buffer=round(closest[2],2),peak_equity=round(peak,2),final_equity=round(equity({s:raw[s][times[-1]][4] for s in raw}),2),trades=trades,max_positions=max_positions)
def main():
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 raw={};sig={}
 for s in SYMS:
  rows,_=load(s);raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows)
 out=dict(method="Historical Pine baseline; max 3 simultaneous positions; $5000 initial; fee 0.08% each side and 0.02% total spread; conservative simultaneous adverse hourly marks.",warning="Hourly OHLC cannot establish true tick-level breaches. Peak for Turbo sampled at hourly open/close; trailing high watermark may be understated. Simulation continues after breach solely to measure hypothetical risk.",results={})
 for group,syms in (("five_year",tuple(s for s in SYMS if s!="TONUSDT")),("six_common",SYMS)):
  common=set.intersection(*(set(raw[s]) for s in syms))
  end=max(common)+H;start=max(min(common),end-365*DAY)
  times=list(range(start,end,H))
  if any(t not in common for t in times):raise ValueError("Missing hourly bar in "+group)
  for share in (.20,.175,.15,.10):
   for mode in MODES:
    key=f"{group}_{share*100:g}pct_{mode}"
    result=replay({s:raw[s] for s in syms},{s:sig[s] for s in syms},{s:baseline[s] for s in syms},times,share,mode)
    out["results"][key]=result
    print("ACCOUNT_TEST",key,json.dumps(result),flush=True)
 p=Path("experiments/three_account_models/results.json")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
