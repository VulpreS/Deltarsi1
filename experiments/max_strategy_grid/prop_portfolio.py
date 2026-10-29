"""Full portfolio replay with per-symbol trained exits, 1H trailing, prop equity limits. Research only."""
import sys,json,math,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.pine_vs_codex.run import pine_events
DAY=24*H;INITIAL=5000.;NOTIONAL=1000.;FEE=.0008;SPREAD=.0002
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
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
   if pending or s in positions or len(positions)>=3:skipped+=1;continue
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
 # Reuse frozen Pine configurations; do not re-optimize for different holding periods.
 raw={};sig={};sha={}
 for s in SYMS:
  rows,sha[s]=load(s);raw[s]={x[0]:x for x in rows}
  sig[s]=dict(pine=pine_events(rows))
 out=dict(title="Prop portfolio selected exits",config=dict(initial=INITIAL,notional=NOTIONAL,max_positions=3,
  daily_limit_pct=5,overall_limit_pct=10,fee_side=FEE,spread_roundtrip=SPREAD),
  warnings=["Frozen configurations were selected on original 48H training; longer holds are sensitivity tests.",
   "Full-year five-symbol run uses settings trained on common shorter window; TON excluded where history ends early.",
   "Prop phase bookkeeping approximates Upscale; no live orders, funding or tick-level path."],results={})
 groups={"five_year":tuple(s for s in SYMS if s!="TONUSDT"),"six_common":SYMS}
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 for group_name,group in groups.items():
  common=set.intersection(*(set(raw[s]) for s in group));end=max(common)+H;start=max(min(common),end-365*DAY)
  times=list(range(start,end,H))
  if any(t not in common for t in times):raise ValueError("Noncontiguous "+group_name)
  data={s:raw[s] for s in group}
  params={s:tuple(baseline[s]) for s in group}
  signals={s:sig[s]["pine"] for s in group}
  for hours in (24,36,48,60,72):
   label=str(hours)+"h" if hours is not None else "unlimited"
   continuous=run(data,signals,params,times,max_hours=hours)
   phases=run(data,signals,params,times,reset=True,max_hours=hours)
   key=group_name+"_pine_"+label
   out["results"][key]=dict(params=params,continuous=continuous,challenge=phases)
   print("PROP_FINAL",key,json.dumps(out["results"][key]),flush=True)
 p=Path("experiments/max_strategy_grid/prop_portfolio.json");p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
