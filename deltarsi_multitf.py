"""DeltaRSI ATR exit grid, 1H/4H/6H/8H. Research only, strict prop first-breach stop."""
import csv,datetime as dt,itertools,json,math,sys
from pathlib import Path
from causal_4h_parity_audit import CausalDelta,qualifying
from research_multiasset import atr
TF=1
H=TF*3600000;DAY=86400000;SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
COST=.00095;START=5000.;NOTIONAL=1000.
GRID={1:dict(sl=[1.5,2,2.5,3],tp=[2,3,4,5],act=[1,1.5,2],dist=[.5,1],hold=[24,48,72]),
4:dict(sl=[1.5,2,2.5,3,3.5,4,5],tp=[2,3,4,5,6,7],act=[1.5,2,3],dist=[.5,1,1.5],hold=[48,72,120]),
6:dict(sl=[1.5,2,2.5,3],tp=[2,3,4,5],act=[1.5,2,3],dist=[.5,1,1.5],hold=[48,72,120]),
8:dict(sl=[1.5,2,2.5,3.5],tp=[2.5,4,5,6],act=[2,3,4],dist=[.75,1.5,2],hold=[72,120,168])}[TF]
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
data={};signals={};first=[];last=[];higher={};higher_bars={}
for sym in SYMS:
 with (Path("data")/f"{sym}_{TF}h.csv").open() as f:
  rr=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
 if any(b[0]-a[0]!=H for a,b in zip(rr,rr[1:])):raise ValueError("Gaps "+sym)
 state=CausalDelta();a=atr(rr);ev={}
 for i,r in enumerate(rr):
  p=state.delta;pp=state.prev_delta;c,_,_=state.step(r[4],commit=False)
  if i>=210 and qualifying(p,pp,c) and i+1<len(rr) and math.isfinite(a[i-1]) and a[i-1]>0:ev[rr[i+1][0]]=(1 if p<0 else -1,a[i-1])
  state.step(r[4],commit=True)
 data[sym]={r[0]:r[1:] for r in rr};signals[sym]=ev;first.append(rr[0][0]);last.append(rr[-1][0])
 with (Path("data")/f"{sym}_4h.csv").open() as f:
  r4=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
 st4=CausalDelta();a4=atr(r4);ev4={}
 for i,r in enumerate(r4):
  p=st4.delta;pp=st4.prev_delta;c,_,_=st4.step(r[4],commit=False)
  if i>=210 and qualifying(p,pp,c) and i+1<len(r4) and math.isfinite(a4[i-1]) and a4[i-1]>0:ev4[r4[i+1][0]]=(1 if p<0 else -1,a4[i-1])
  st4.step(r[4],commit=True)
 higher[sym]=ev4;higher_bars[sym]={r[0]:r[1:] for r in r4};last.append(r4[-1][0])
# Match exactly the previous 1H/4H/6H/8H portfolio window, excluding unpriced post-TON candles.
start=max(int(dt.datetime(2025,10,28,tzinfo=dt.timezone.utc).timestamp()*1000),min(first))
end=min(last)
times=range(start,end+H,H)
def run(policy):\n sl=2.5;tp=5;mode="time";act=None;dist=None;hold=72;confirm=0;opp=0;switch=0
 cash=START;pos={};peak=START;min_eq=START;maxdd=0.;day=None;daybase=START;trades=[];breach=None;amb=0;skipped=0
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices.get(s,z["entry"])-z["entry"])-z["qty"]*prices.get(s,z["entry"])*COST for s,z in pos.items())
 for t in times:
  bars={s:data[s][t] for s in SYMS if t in data[s]}
  if not bars:continue
  opens={s:b[0] for s,b in bars.items()};closes={s:b[3] for s,b in bars.items()}
  if day!=t//DAY:
   day=t//DAY;daybase=equity(opens)
  for sym in SYMS:
   if sym in pos or sym not in bars or t not in signals[sym]:continue
   if len(pos)>=3:skipped+=1;continue
   side,a=signals[sym][t];o=opens[sym]\n   if policy=="filter" and not any(v[0]==side and 0<=t-k<=8*H for k,v in higher[sym].items()):continue
   if o-side*sl*a<=0:continue
   q=NOTIONAL/o;cash-=NOTIONAL*COST
   pos[sym]=dict(side=side,qty=q,entry=o,stop=o-side*sl*a,target=o+side*tp*a,atr=a,best=o,fee=NOTIONAL*COST,entry_ms=t,active=False,confirmed=False,hold=hold)
  for sym,z in list(pos.items()):
   if t in higher[sym]:
    direction,atr4=higher[sym][t]
    if direction==z["side"] and not z["confirmed"]:
     z["confirmed"]=True;confirm+=1
     if policy in ("switch_target","switch_full"):
      z["target"]=z["entry"]+z["side"]*7*atr4
      z["hold"]=120
      if policy=="switch_full":
       proposed=z["entry"]-z["side"]*3*atr4
       z["stop"]=max(z["stop"],proposed) if z["side"]==1 else min(z["stop"],proposed)
      switch+=1
    elif direction!=z["side"] and policy=="close_4h_opposite":
     # Exit at open, since 4H signal is known only after prior 4H close.
     px=opens.get(sym)
     if px is not None:
      pnl=z["side"]*z["qty"]*(px-z["entry"])-z["fee"]-z["qty"]*px*COST
      cash+=z["side"]*z["qty"]*(px-z["entry"])-z["qty"]*px*COST
      trades.append((sym,pnl,"4h_opposite"));del pos[sym];opp+=1
   elif policy in ("close_1h_opposite","breakeven_1h_opposite","half_risk_1h_opposite") and t in signals[sym] and signals[sym][t][0]!=z["side"]:
    opp+=1
    if policy=="close_1h_opposite":
     px=opens[sym];pnl=z["side"]*z["qty"]*(px-z["entry"])-z["fee"]-z["qty"]*px*COST
     cash+=z["side"]*z["qty"]*(px-z["entry"])-z["qty"]*px*COST;trades.append((sym,pnl,"1h_opposite"));del pos[sym]
    elif policy=="breakeven_1h_opposite":
     proposed=z["entry"]+z["side"]*z["entry"]*2*COST
     z["stop"]=max(z["stop"],proposed) if z["side"]==1 else min(z["stop"],proposed)
    else:
     px=opens[sym];q=z["qty"]/2
     pnl=z["side"]*q*(px-z["entry"])-z["fee"]/2-q*px*COST
     cash+=z["side"]*q*(px-z["entry"])-q*px*COST;trades.append((sym,pnl,"half_exit"))
     z["qty"]-=q;z["fee"]/=2
  # Conservative portfolio adverse snapshot. If threshold is touched, challenge stops permanently.
  adverse={}
  for sym,b in bars.items():
   o,h,l,c=b
   if sym not in pos:adverse[sym]=c;continue
   z=pos[sym];stop=z["stop"];hit=l<=stop if z["side"]==1 else h>=stop
   adverse[sym]=(min(o,stop) if z["side"]==1 else max(o,stop)) if hit else (l if z["side"]==1 else h)
  worst=equity(adverse)
  min_eq=min(min_eq,worst);maxdd=max(maxdd,100*(peak-worst)/peak)
  if worst<=daybase*.95 or worst<=4500:
   breach=dict(time=iso(t),type="daily" if worst<=daybase*.95 else "total",equity=round(worst,2));break
  for sym in list(pos):
   if sym not in bars:continue
   o,h,l,c=bars[sym];z=pos[sym];side=z["side"];stop=z["stop"];target=z["target"]
   sh=l<=stop if side==1 else h>=stop
   th=h>=target if side==1 else l<=target
   if sh and th:amb+=1
   price=o if side*(o-stop)<=0 or side*(o-target)>=0 else stop if sh else target if th else None
   reason="stop" if sh else "take" if th else None
   if price is None and mode=="trail":
    fav=h if side==1 else l
    z["best"]=max(z["best"],fav) if side==1 else min(z["best"],fav)
    if side*(z["best"]-z["entry"])>=act*z["atr"]:z["active"]=True
    if z["active"]:
     trail=z["best"]-side*dist*z["atr"]
     z["stop"]=max(z["stop"],trail) if side==1 else min(z["stop"],trail)
   if price is None and mode=="time" and t+H-z["entry_ms"]>=z.get("hold",hold)*3600000:price=c;reason="time"
   if price is not None:
    pnl=side*z["qty"]*(price-z["entry"])-z["fee"]-z["qty"]*price*COST
    cash+=side*z["qty"]*(price-z["entry"])-z["qty"]*price*COST
    trades.append((sym,pnl,reason));del pos[sym]
  now=equity(closes);peak=max(peak,now)
 final=equity({s:data[s][min(end,max(data[s]))][3] if min(end,max(data[s])) in data[s] else z["entry"] for s,z in pos.items()})
 gains=sum(max(0,p) for _,p,_ in trades);losses=-sum(min(0,p) for _,p,_ in trades)
 return dict(policy=policy,confirmations=confirm,opposite_events=opp,switches=switch,final=round(final,2),return_pct=round(100*(final/START-1),3),max_dd_pct=round(maxdd,3),min_equity=round(min_eq,2),trades=len(trades),win_pct=round(100*sum(p>0 for _,p,_ in trades)/len(trades),2) if trades else None,pf=round(gains/losses,3) if losses else None,breach=breach,ambiguous=amb,skipped=skipped)
policies=("baseline","filter","switch_target","switch_full","close_4h_opposite","close_1h_opposite","breakeven_1h_opposite","half_risk_1h_opposite")
results=[run(p) for p in policies]
out=dict(start=iso(start),end=iso(end+H),results=results,description="1H native entries, 4H closed-candle confirmation; 1H base SL2.5 TP5 ATR hold72h; 4H TP7 ATR hold120h; conservative prop checks.")
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_multitf_1h4h.json").write_text(json.dumps(out,indent=2))
print("MULTITF_RESULT",json.dumps(out),flush=True)
