"""Exploratory multi-timeframe DeltaRSI state-transition study. Closed bars only."""
import csv,datetime as dt,json,math
from pathlib import Path
from causal_4h_parity_audit import CausalDelta,qualifying
from research_multiasset import atr
TFS=(1,4,6,8)
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
H=3600000;DAY=24*H;START=5000.;COST=.00095;NOTIONAL=1000.
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
bars={};events={};limits=[]
for sym in SYMS:
 for tf in TFS:
  with (Path("data")/f"{sym}_{tf}h.csv").open() as f:
   rr=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
  if any(b[0]-a[0]!=tf*H for a,b in zip(rr,rr[1:])):raise ValueError(f"Gap {sym} {tf}h")
  state=CausalDelta();aa=atr(rr);ev={}
  for i,r in enumerate(rr):
   p=state.delta;pp=state.prev_delta;c,_,_=state.step(r[4],commit=False)
   if i>=210 and qualifying(p,pp,c) and i+1<len(rr) and math.isfinite(aa[i-1]) and aa[i-1]>0:
    ev[rr[i+1][0]]=(1 if p<0 else -1,aa[i-1],abs(p))
   state.step(r[4],commit=True)
  bars[sym,tf]={r[0]:r[1:] for r in rr};events[sym,tf]=ev
  limits.append(rr[-1][0]+tf*H)
start=int(dt.datetime(2025,10,28,tzinfo=dt.timezone.utc).timestamp()*1000)
end=min(limits)-H
# Full chronological event transitions, including those that do not occur while a position is open.
transition={}
for sym in SYMS:
 for a in TFS:
  for b in TFS:
   if a==b:continue
   for t,(side,_,_) in events[sym,a].items():
    if t<start or t>end:continue
    for u,(side2,_,_) in events[sym,b].items():
     if t<=u<=t+24*H:
      key=f"{a}>{b}:{'agree' if side==side2 else 'oppose'}"
      v=transition.setdefault(key,dict(n=0,delay_hours=[]))
      v["n"]+=1;v["delay_hours"].append(round((u-t)/H,2))
# State transitions: the position retains its original entry TF, while newer TF signals may change exits.
profiles=("baseline","confirm_target","confirm_time","confirm_both","opp_close","opp_breakeven","opp_half","opp_tighten","hybrid")
base_sl={1:2.5,4:3,6:1.5,8:2.5};base_tp={1:5,4:7,6:5,8:2.5};base_hold={1:72,4:72,6:72,8:120}
def simulate(entry_tf,profile):
 cash=START;pos={};trades=[];day=None;daybase=START;peak=START;dd=0.;breach=None
 counts=dict(confirmed=0,opposed=0,switched=0,stops=0,takes=0,timed=0,skipped=0)
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices.get(s,z["entry"])-z["entry"])-z["qty"]*prices.get(s,z["entry"])*COST for s,z in pos.items())
 for t in range(start,end+1,H):
  market={s:bars[s,1].get(t) for s in SYMS}
  market={s:v for s,v in market.items() if v is not None}
  if not market:continue
  op={s:v[0] for s,v in market.items()};cl={s:v[3] for s,v in market.items()}
  if day!=t//DAY:day=t//DAY;daybase=equity(op)
  # Existing positions respond to signals at this bar open, before intrabar movement.
  for sym,z in list(pos.items()):
   for tf in TFS:
    if tf==entry_tf or t not in events[sym,tf]:continue
    direction,a,strength=events[sym,tf][t]
    if direction==z["side"]:
     counts["confirmed"]+=1
     if tf>z["manager_tf"] and profile in ("confirm_target","confirm_time","confirm_both","hybrid"):
      if profile in ("confirm_target","confirm_both","hybrid"):
       z["target"]=z["entry"]+direction*base_tp[tf]*a
      if profile in ("confirm_time","confirm_both","hybrid"):
       z["expiry"]=max(z["expiry"],t+base_hold[tf]*H)
      z["manager_tf"]=tf;counts["switched"]+=1
    else:
     counts["opposed"]+=1
     if profile=="opp_close":
      px=op[sym];pnl=direction*(-1)*z["qty"]*(px-z["entry"])-z["fee"]-z["qty"]*px*COST
      cash+=z["side"]*z["qty"]*(px-z["entry"])-z["qty"]*px*COST
      trades.append(pnl);del pos[sym];break
     if profile in ("opp_breakeven","hybrid"):
      proposed=z["entry"]+z["side"]*z["entry"]*2*COST
      z["stop"]=max(z["stop"],proposed) if z["side"]==1 else min(z["stop"],proposed)
     elif profile=="opp_tighten":
      proposed=op[sym]-z["side"]*max(a,z["atr"])*.75
      z["stop"]=max(z["stop"],proposed) if z["side"]==1 else min(z["stop"],proposed)
     elif profile=="opp_half" and not z["halved"]:
      px=op[sym];q=z["qty"]/2
      pnl=z["side"]*q*(px-z["entry"])-z["fee"]/2-q*px*COST
      cash+=z["side"]*q*(px-z["entry"])-q*px*COST;trades.append(pnl)
      z["qty"]-=q;z["fee"]/=2;z["halved"]=True
  # Entry signal is available at next bar open, never at the signal bar close.
  for sym in SYMS:
   if sym not in market or sym in pos or t not in events[sym,entry_tf]:continue
   if len(pos)>=3:counts["skipped"]+=1;continue
   direction,a,strength=events[sym,entry_tf][t];price=op[sym]
   stop=price-direction*base_sl[entry_tf]*a
   if stop<=0:continue
   q=NOTIONAL/price;cash-=NOTIONAL*COST
   pos[sym]=dict(side=direction,qty=q,entry=price,stop=stop,target=price+direction*base_tp[entry_tf]*a,expiry=t+base_hold[entry_tf]*H,atr=a,manager_tf=entry_tf,fee=NOTIONAL*COST,halved=False)
  # Worst intrabar simultaneous adverse equity before exit. Same prop convention as earlier tests.
  adverse={}
  for sym,(o,hi,lo,c) in market.items():
   if sym not in pos:adverse[sym]=c;continue
   z=pos[sym];hit=lo<=z["stop"] if z["side"]==1 else hi>=z["stop"]
   adverse[sym]=(min(o,z["stop"]) if z["side"]==1 else max(o,z["stop"])) if hit else (lo if z["side"]==1 else hi)
  worst=equity(adverse);dd=max(dd,100*(peak-worst)/peak)
  if worst<=daybase*.95 or worst<=4500:
   breach=dict(time=iso(t),type="daily" if worst<=daybase*.95 else "total",equity=round(worst,2));break
  for sym,z in list(pos.items()):
   if sym not in market:continue
   o,hi,lo,c=market[sym];side=z["side"]
   sh=lo<=z["stop"] if side==1 else hi>=z["stop"]
   th=hi>=z["target"] if side==1 else lo<=z["target"]
   if side*(o-z["stop"])<=0:px=o;reason="stops"
   elif side*(o-z["target"])>=0:px=o;reason="takes"
   elif sh:px=z["stop"];reason="stops"
   elif th:px=z["target"];reason="takes"
   elif t+H>=z["expiry"]:px=c;reason="timed"
   else:continue
   pnl=side*z["qty"]*(px-z["entry"])-z["fee"]-z["qty"]*px*COST
   cash+=side*z["qty"]*(px-z["entry"])-z["qty"]*px*COST
   trades.append(pnl);counts[reason]+=1;del pos[sym]
  peak=max(peak,equity(cl))
 final=equity({s:bars[s,1].get(end,[z["entry"]]*4)[3] for s,z in pos.items()})
 gain=sum(max(0,x) for x in trades);loss=-sum(min(0,x) for x in trades)
 return dict(entry_tf=entry_tf,profile=profile,final=round(final,2),return_pct=round((final/START-1)*100,3),max_dd_pct=round(dd,3),pf=round(gain/loss,3) if loss else None,trades=len(trades),win_pct=round(100*sum(x>0 for x in trades)/len(trades),2) if trades else None,breach=breach,counts=counts)
results=[simulate(tf,p) for tf in TFS for p in profiles]
out=dict(start=iso(start),end=iso(end+H),results=results,transitions={k:dict(n=v["n"],mean_delay_h=round(sum(v["delay_hours"])/v["n"],2)) for k,v in transition.items()},notes="Exploratory in-sample. All signals effective at following candle open. No future bars. 1h OHLC execution, stop first, UTC prop limits, fees .095% per side. No funding/slippage. Compare with baseline within same entry TF.")
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_multitf_research.json").write_text(json.dumps(out,indent=2))
print("RESEARCH_RESULT",json.dumps(dict(start=out["start"],end=out["end"],results=results)),flush=True)
