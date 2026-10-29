"""Compare 3/4/5 positions at constant 60% initial capital; research only.
GRAM is a display alias for historical TONUSDT; never assume GRAMUSDT is equivalent.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.new_assets_2026.run import download
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
import math
INITIAL=5000.;FEE=.0008;SPREAD=.0002
OLD=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
NEW=("XRPUSDT","LINKUSDT")
MAX_POS=3;NOTIONAL=1000.
def run(raw,sig,params,times,reset=False,max_hours=48):
 cash=INITIAL;positions={};closed=[];breach=None;peak=INITIAL;maxdd=0.;maxdayloss=0.;day=None;daybase=INITIAL
 phase=1;phase_start=times[0];qual=0;phases=[];pending=False;daily=[];maxpos=0;skipped=0
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+SPREAD/2) for s,z in positions.items())
 for t in times:
  bars={s:raw[s][t] for s in raw};opens={s:v[1] for s,v in bars.items()};closes={s:v[4] for s,v in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(opens)
  # Phase transitions must occur only flat, never repeatedly register completion.
  if pending and not positions:
   phase+=1;phase_start=t;qual=0;pending=False
   if reset:
    cash=INITIAL;peak=INITIAL;daybase=INITIAL
  for s in sorted(raw):
   if t not in sig[s]:continue
   if pending or s in positions or len(positions)>=MAX_POS:skipped+=1;continue
   e=sig[s][t];a=e["atr_4h"];side=e["side"];o=opens[s]
   if not math.isfinite(a) or a<=0:continue
   sl,tp,activation,distance=params[s];stop=o-side*sl*a;target=o+side*tp*a
   if min(stop,target)<=0:continue
   qty=NOTIONAL/o;entrycost=NOTIONAL*(FEE+SPREAD/2);cash-=entrycost
   positions[s]=dict(side=side,qty=qty,entry=o,atr=a,stop=stop,target=target,
    activation=activation,distance=distance,best=o,active=False,entry_t=t,entrycost=entrycost)
  maxpos=max(maxpos,len(positions))
  adverse=dict(closes)
  for s,z in positions.items():
   adverse[s]=min(opens[s],bars[s][3]) if z["side"]==1 else max(opens[s],bars[s][2])
  worst=equity(adverse);maxdd=max(maxdd,(peak-worst)/peak*100);maxdayloss=max(maxdayloss,daybase-worst)
  if worst<=daybase*.95 or worst<=INITIAL*.9:
   breach=dict(time=iso(t),kind="daily" if worst<=daybase*.95 else "total",equity=round(worst,2));break
  for s in list(positions):
   z=positions[s];side=z["side"];o,h,l,c=bars[s][1:];stop=z["stop"];target=z["target"]
   if side*(o-stop)<=0:price=o;reason="stop_gap"
   elif side*(o-target)>=0:price=o;reason="take_gap"
   elif (l<=stop if side==1 else h>=stop):price=stop;reason="stop"
   elif (h>=target if side==1 else l<=target):price=target;reason="take"
   elif (max_hours[s] if isinstance(max_hours,dict) else max_hours) is not None and t-z["entry_t"]>=((max_hours[s] if isinstance(max_hours,dict) else max_hours)-1)*H:price=c;reason="time"
   else:price=None
   if price is not None:
    gross=side*z["qty"]*(price-z["entry"]);exitfee=z["qty"]*price*(FEE+SPREAD/2)
    cash+=gross-exitfee
    closed.append(dict(symbol=s,entry=iso(z["entry_t"]),exit=iso(t+H),net_usd=round(gross-z["entrycost"]-exitfee,5),reason=reason,phase=phase))
    del positions[s]
   elif z["activation"] is not None:
    z["best"]=max(z["best"],h) if side==1 else min(z["best"],l)
    if side*(z["best"]-z["entry"])>=z["activation"]*z["atr"]:z["active"]=True
    if z["active"]:
     new=z["best"]-side*z["distance"]*z["atr"]
     z["stop"]=max(stop,new) if side==1 else min(stop,new)
  last=equity(closes);peak=max(peak,last)
  if last<=daybase*.95 or last<=INITIAL*.9:
   breach=dict(time=iso(t+H),kind="daily" if last<=daybase*.95 else "total",equity=round(last,2));break
  if (t+H)%DAY==0:
   daypnl=last-daybase
   if phase<=2 and daypnl>=INITIAL*.005:qual+=1
   daily.append(dict(time=iso(t+H),equity=round(last,2),day_pnl=round(daypnl,2),phase=phase))
   if phase<=2 and not pending and last>=INITIAL*(1.05 if phase==1 else 1.08) and qual>=(3 if phase==1 else 5):
    if not positions:
     phases.append(dict(phase=phase,completed=iso(t+H),days=round((t+H-phase_start)/DAY,2),qualifying_days=qual))
     pending=True
    # If open, re-evaluate at the next UTC checkpoint without double-counting.
 if not breach:last=equity({s:raw[s][times[-1]][4] for s in raw})
 wins=sum(z["net_usd"]>0 for z in closed);g=sum(max(0,z["net_usd"]) for z in closed);loss=-sum(min(0,z["net_usd"]) for z in closed)
 return dict(start=iso(times[0]),end=iso(times[-1]+H),days=len(times)/24,equity=round(last,2),
  return_pct=round((last/INITIAL-1)*100,3),closed_net_pnl=round(sum(z["net_usd"] for z in closed),2),
  trades=len(closed),stops=sum(z["reason"].startswith("stop") for z in closed),
  takes=sum(z["reason"].startswith("take") for z in closed),time_exits=sum(z["reason"]=="time" for z in closed),
  win_rate=round(100*wins/len(closed),2) if closed else None,profit_factor=round(g/loss,3) if loss else None,
  max_intrahour_dd=round(maxdd,3),worst_day_drop_usd=round(maxdayloss,2),
  breach=breach,phases=phases,phase_now=phase,max_concurrent=maxpos,skipped=skipped,
  by_symbol={s:dict(trades=sum(z["symbol"]==s for z in closed),stops=sum(z["symbol"]==s and z["reason"].startswith("stop") for z in closed),
   pnl=round(sum(z["net_usd"] for z in closed if z["symbol"]==s),2)) for s in raw})
def main():
 global MAX_POS,NOTIONAL
 raw={};sig={};errors={}
 for s in OLD+NEW:
  try:
   rows,_=load(s) if s in OLD else (download(s),None)
   raw[s]={x[0]:x for x in rows};sig[s]=pine_events(rows)
   print("DATA",s,len(rows),flush=True)
  except Exception as e:
   errors[s]=str(e);print("DATA_ERROR",s,str(e),flush=True)
 if errors:raise RuntimeError("Missing assets: "+str(errors))
 params={s:tuple(v) for s,v in json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"].items()}
 params.update({"XRPUSDT":(5.,2.5,None,None),"LINKUSDT":(5.,5.,None,None)})
 common=set.intersection(*(set(raw[s]) for s in OLD+NEW))
 times=sorted(common)
 if len(times)<720 or any(b-a!=H for a,b in zip(times,times[1:])):raise ValueError("Insufficient continuous common history")
 output=dict(symbol_alias={"TONUSDT":"GRAM (display alias only)"},dates=(iso(times[0]),iso(times[-1]+H)),errors=errors,results={},notes=["Identical signals, same dates and total margin 60% of $5000 for 3/4/5 variants.","Priority is alphabetical as in baseline; not ranked by signal strength.","Existing prop risk model is approximate; no live trades."])
 for period,ts in (("common",times),("last_90d",times[-2160:]),("last_30d",times[-720:])):
  for n in (3,4,5):
   MAX_POS=n;NOTIONAL=3000./n
   r=run(raw,sig,params,ts,max_hours=48)
   output["results"][period+"_"+str(n)]=r
   print("CAPACITY_COMPARE",period,n,json.dumps(r),flush=True)
 p=Path("experiments/capacity_8_assets/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(output,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
