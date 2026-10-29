"""Research-only: 2 signals x per-symbol SL/TP/trailing grids; chronological OOS, portfolio prop replay."""
import sys,json,math,itertools,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.pine_vs_codex.run import pine_events
from research_multiasset import atr
from completed_candles import aggregate_completed
import experiments.upscale_year_portfolio.run as prop
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
SL=(1.5,2.5,3.5,5.)
TP=(1.5,2.5,3.5,5.)
TRAIL=((None,None),(1.,.5),(2.,.5),(2.,1.),(3.,.5),(3.,1.))
FEE=.0008;SPREAD=.0002;NOTIONAL=1000.;MAXH=48;DAY=24*H
def trade(raw,i,side,a,sl,tp,activation,distance):
 if i>=len(raw) or not math.isfinite(a) or a<=0:return None
 entry=raw[i][1];stop=entry-side*sl*a;target=entry+side*tp*a
 if min(stop,target)<=0:return None
 best=entry;active=False;last=min(i+MAXH-1,len(raw)-1)
 for j in range(i,last+1):
  t,o,h,l,c=raw[j]
  # Stop-first with gap at opening price; trailing updates only after hourly candle.
  if side*(o-stop)<=0:exit_px=o;reason="stop_gap"
  elif side*(o-target)>=0:exit_px=o;reason="take_gap"
  elif (l<=stop if side==1 else h>=stop):exit_px=stop;reason="stop"
  elif (h>=target if side==1 else l<=target):exit_px=target;reason="take"
  elif j==last:exit_px=c;reason="time"
  else:exit_px=None
  if exit_px is not None:
   net=side*(exit_px-entry)/entry-(FEE+SPREAD/2)*(1+exit_px/entry)
   return dict(entry_ms=raw[i][0],exit_ms=t+H,net_pct=100*net,net_usd=NOTIONAL*net,reason=reason)
  if activation is not None:
   best=max(best,h) if side==1 else min(best,l)
   if side*(best-entry)>=activation*a:active=True
   if active:
    new=best-side*distance*a
    stop=max(stop,new) if side==1 else min(stop,new)
 return None
def replay(raw,signal,params,start,end):
 sl,tp,act,dist=params;times={x[0]:i for i,x in enumerate(raw)}
 trades=[];until=-1
 for t,e in sorted(signal.items()):
  if not(start<=t<end) or t not in times or times[t]<=until:continue
  i=times[t];z=trade(raw,i,e["side"],e["atr_4h"],sl,tp,act,dist)
  if z:
   trades.append(z);until=times.get(z["exit_ms"]-H,i)
 wins=sum(x["net_usd"]>0 for x in trades);g=sum(max(0,x["net_usd"]) for x in trades);l=-sum(min(0,x["net_usd"]) for x in trades)
 return dict(n=len(trades),pnl=round(sum(x["net_usd"] for x in trades),2),wr=round(100*wins/len(trades),2) if trades else 0,pf=round(g/l,3) if l else None,trades=trades)
def main():
 raw={};sigs={};sha={}
 for s in SYMS:
  rows,sha[s]=load(s);raw[s]=rows
  e,_=events(rows)
  sigs[s]={"codex":{x["entry_ms"]:x for x in e["closed"]},"pine":pine_events(rows)}
 common=set.intersection(*(set(r[0] for r in rows) for rows in raw.values()))
 end=max(common)+H;start=max(min(common),end-365*DAY)
 if any(t not in common for t in range(start,end,H)):raise ValueError("Noncontiguous common hourly window")
 split=start+((end-start)//DAY*7//10)*DAY
 options=list(itertools.product(SL,TP,TRAIL))
 report=dict(source_sha=sha,window=dict(start=start,split=split,end=end),parameters=dict(sl=SL,tp=TP,trailing=TRAIL,fees=FEE,spread=SPREAD,hold=MAXH),
  warnings=["In-sample grid selection; OOS is chronological holdout, not forward live.",
   "Signal parity on historical 4H closes; trailing effective following 1H candle.",
   "Stop-first hourly ambiguity; no funding; prop reset engine is approximate.",
   "Common period for six assets may be shorter than one year."],by_symbol={},portfolios={})
 for s in SYMS:
  report["by_symbol"][s]={}
  for name,signal in sigs[s].items():
   ranked=[]
   for sl,tp,(act,dist) in options:
    p=(sl,tp,act,dist);train=replay(raw[s],signal,p,start,split)
    ranked.append((train["pnl"],train["n"],p))
   ranked.sort(reverse=True,key=lambda x:(x[0],x[1]))
   top=[]
   for pnl,n,p in ranked[:10]:
    test=replay(raw[s],signal,p,split,end)
    top.append(dict(params=p,train_pnl=pnl,train_trades=n,test_pnl=test["pnl"],test_trades=test["n"],test_pf=test["pf"],test_wr=test["wr"]))
   report["by_symbol"][s][name]=top
   print("GRID",s,name,json.dumps(top[:3]),flush=True)
 # Portfolio comparison uses same common timeline and fixed per-asset top TRAIN params.
 # Existing engine supports no trailing: separately evaluate common 5/5 and best fixed-only configs.
 times=list(range(start,end,H));data={s:{x[0]:x for x in raw[s]} for s in SYMS}
 prop.SYMS=SYMS
 for name in ("codex","pine"):
  for setting in ("atr5","best_fixed_train"):
   mode={}
   for s in SYMS:
    if setting=="atr5":sl=tp=5.
    else:
     candidates=[x for x in report["by_symbol"][s][name] if x["params"][2] is None]
     if candidates:sl,tp=candidates[0]["params"][:2]
     else:
      ranks=[]
      for a,b in itertools.product(SL,TP):
       q=replay(raw[s],sigs[s][name],(a,b,None,None),start,split)
       ranks.append((q["pnl"],a,b))
      _,sl,tp=max(ranks)
    mode[s]=(("atr",sl),("atr",tp),False)
   signals={s:sigs[s][name] for s in SYMS}
   full=prop.simulate(data,signals,times,mode,reset_phases=False)
   phases=prop.simulate(data,signals,times,mode,reset_phases=True)
   report["portfolios"][name+"_"+setting]=dict(mode=mode,continuous={k:v for k,v in full.items() if k not in ("trades","daily")},phase={k:v for k,v in phases.items() if k not in ("trades","daily")})
   print("PORTFOLIO",name,setting,json.dumps(report["portfolios"][name+"_"+setting]),flush=True)
 path=Path("experiments/max_strategy_grid/results.json");path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
