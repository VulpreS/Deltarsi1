"""Two independent $5000 accounts and 3 exit policies on 8 assets. Research only."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,CausalDelta
from completed_candles import aggregate_completed
from experiments.new_assets_2026.run import download
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import H,DAY,iso
INITIAL=5000.;FEE=.0008;SPREAD=.0002;MAX_POS=3;NOTIONAL=1000.
OLD=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
NEW=("XRPUSDT","LINKUSDT")
GROUPS={"account_A":("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT"),"account_B":("ICPUSDT","TONUSDT","ZECUSDT","LINKUSDT")}
def delta_at_decision(rows):
 bars=aggregate_completed(rows,4,asof_ms=rows[-1][0]+H);state=CausalDelta();out={}
 for b in bars:
  d,_,_=state.step(b[4],commit=True)
  if math.isfinite(d):out[b[0]+4*H]=d
 return out
def run(raw,sig,params,times,reset=False,max_hours=48,mode='baseline',deltas=None):
 cash=INITIAL;positions={};closed=[];breach=None;peak=INITIAL;maxdd=0.;maxdayloss=0.;day=None;daybase=INITIAL
 phase=1;phase_start=times[0];qual=0;phases=[];pending=False;daily=[];maxpos=0;skipped=0;opposite_exits=0;confirm_exits=0;waiting={}
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
  exited=set()
  if mode!='baseline':
   for s in list(positions):
    z=positions[s];op=sig[s].get(t);is_op=op is not None and op["side"]==-z["side"]
    should=False;why=None
    if mode=='immediate' and is_op:should=True;why='opposite'
    if mode=='confirm':
     if s in waiting and t>=waiting[s]+4*H:
      d0=deltas[s].get(waiting[s]);d1=deltas[s].get(t)
      if d0 is not None and d1 is not None and d0*d1>0 and abs(d1)<=abs(d0):
       should=True;why='confirm'
      waiting.pop(s,None)
     if is_op:waiting[s]=t
    if should:
     price=opens[s];gross=z["side"]*z["qty"]*(price-z["entry"]);fee=z["qty"]*price*(FEE+SPREAD/2)
     cash+=gross-fee
     closed.append(dict(symbol=s,entry=iso(z["entry_t"]),exit=iso(t),net_usd=round(gross-z["entrycost"]-fee,5),reason=why,phase=phase))
     del positions[s];exited.add(s)
     if why=='opposite':opposite_exits+=1
     else:confirm_exits+=1
  for s in sorted(raw):
   if s in exited or t not in sig[s]:continue
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
  breach=breach,phases=phases,phase_now=phase,max_concurrent=maxpos,skipped=skipped,opposite_exits=opposite_exits,confirm_exits=confirm_exits,
  by_symbol={s:dict(trades=sum(z["symbol"]==s for z in closed),stops=sum(z["symbol"]==s and z["reason"].startswith("stop") for z in closed),
   pnl=round(sum(z["net_usd"] for z in closed if z["symbol"]==s),2)) for s in raw})
def main():
 raw={};sig={};delta={}
 for s in OLD+NEW:
  rows,_=load(s) if s in OLD else (download(s),None)
  raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows);delta[s]=delta_at_decision(rows)
  print("DATA",s,len(rows),flush=True)
 params={s:tuple(v) for s,v in json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"].items()}
 params.update({"XRPUSDT":(5.,2.5,None,None),"LINKUSDT":(5.,5.,None,None)})
 common=set.intersection(*(set(raw[s]) for s in OLD+NEW));ts=sorted(common)
 if len(ts)<720 or any(b-a!=H for a,b in zip(ts,ts[1:])):raise ValueError("Common timeline gap")
 out=dict(groups=GROUPS,alias={"TONUSDT":"GRAM display name; TONUSDT historical candles"},notes=["Each account has independent $5000 equity, max 3 x $1000 positions; combined starting capital $10000.","Opposite signal uses original closed-4h pine_events, exit at next hourly open.","Confirmation compares Delta magnitude at next completed 4h candle and exits at its next open if same sign and not stronger.","Stop/take and 48h exit retain priority within previous hours; account simulations use same calendar dates.","No out-of-sample validation of all parameters, approximate prop constraints."],results={})
 for period,times in (("common",ts),("last_90d",ts[-2160:]),("last_30d",ts[-720:])):
  for mode in ("baseline","immediate","confirm"):
   accounts={}
   for label,group in GROUPS.items():
    a=run({s:raw[s] for s in group},{s:sig[s] for s in group},{s:params[s] for s in group},times,mode=mode,deltas=delta)
    accounts[label]=a
   combined=dict(starting_capital=10000,ending_equity=round(sum(a["equity"] for a in accounts.values()),2),combined_pnl=round(sum(a["equity"]-5000 for a in accounts.values()),2),combined_return_pct=round(sum(a["equity"]-5000 for a in accounts.values())/100,3),trades=sum(a["trades"] for a in accounts.values()),skipped=sum(a["skipped"] for a in accounts.values()),opposite_exits=sum(a["opposite_exits"] for a in accounts.values()),confirm_exits=sum(a["confirm_exits"] for a in accounts.values()),breaches={k:v["breach"] for k,v in accounts.items()},phase_dates={k:v["phases"] for k,v in accounts.items()})
   out["results"][period+"_"+mode]=dict(accounts=accounts,combined=combined)
   print("TWO_ACCOUNTS",period,mode,json.dumps(combined),flush=True)
 p=Path("experiments/two_accounts_opposite_exit/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
