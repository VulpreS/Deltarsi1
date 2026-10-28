"""One-year native 6H/8H conservative OHLC comparison."""
import sys
TF=int(sys.argv[1]);assert TF in (6,8)
import csv,datetime as dt,hashlib,json,math
from pathlib import Path
from causal_4h_parity_audit import CausalDelta,qualifying
from research_multiasset import atr
H=TF*3600000; DAY=24*3600000
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
PARAM={"BTCUSDT":(2.,.5),"ETHUSDT":(3.,.5),"ICPUSDT":(None,None),"TONUSDT":(2.,1.),"BNBUSDT":(None,None),"ZECUSDT":(None,None)}
FEE=.0008+.0003/2
START=int(dt.datetime(2025,10,28,tzinfo=dt.timezone.utc).timestamp()*1000)
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
data={};signals={};sources={}
for sym in SYMS:
 p=Path("data")/(sym+f"_{TF}h.csv")
 with p.open() as f:
  rows=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
 gaps=[(a[0],b[0]) for a,b in zip(rows,rows[1:]) if b[0]-a[0]!=H]
 if gaps:raise ValueError(f"{sym} has {len(gaps)} TF gaps; first {gaps[:3]}")
 av=atr(rows);state=CausalDelta();ev={}
 for i,r in enumerate(rows):
  prev=state.delta;prevprev=state.prev_delta
  cur,_,_=state.step(r[4],commit=False)
  if i>=210 and qualifying(prev,prevprev,cur) and i+1<len(rows) and math.isfinite(av[i-1]):
   ev[rows[i+1][0]]=(1 if prev<0 else -1,av[i-1])
  state.step(r[4],commit=True)
 data[sym]={r[0]:r[1:] for r in rows};signals[sym]=ev
 sources[sym]={"first":iso(rows[0][0]),"last":iso(rows[-1][0]),"bars":len(rows),"signals":len(ev),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
 print(sym,sources[sym],flush=True)
end=min(max(x) for x in data.values());start=max(START,min(min(x) for x in data.values()))
# A single continuous account: assets become eligible only once their own history exists.
cash=5000.;positions={};peak=5000.;maxdd=0.;min_eq=5000.;day=None;daybase=5000.;daily_breaches=set();total_breach=False;first_breach=None
trades=[];skipped=0;daily=[];ambiguous=0;max_open=0;worst_daily=0.
def equity(prices):
 return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*FEE for s,z in positions.items())
for t in range(start,end+H,H):
 bars={s:data[s][t] for s in SYMS if t in data[s]}
 if not bars:continue
 opens={s:v[0] for s,v in bars.items()};closes={s:v[3] for s,v in bars.items()}
 if t//DAY!=day:
  day=t//DAY
  # The new day starts at the open; positions are marked at the new day's opening price.
  daybase=equity({s:opens.get(s,closes.get(s,z["entry"])) for s,z in positions.items()})
 for sym in SYMS:
  if sym not in bars or sym in positions or t not in signals[sym]:continue
  if len(positions)>=3:skipped+=1;continue
  side,a=signals[sym][t];o=opens[sym]
  if a<=0 or o-side*5*a<=0:continue
  qty=1000/o;cash-=1000*FEE;act,dist=PARAM[sym]
  positions[sym]=dict(side=side,qty=qty,entry=o,stop=o-side*5*a,target=o+side*5*a,atr=a,best=o,act=act,dist=dist,active=False,fee=1000*FEE,entry_ms=t)
 max_open=max(max_open,len(positions))
 adverse={}
 for sym,b in bars.items():
  o,h,l,c=b
  if sym not in positions:adverse[sym]=c;continue
  z=positions[sym];stop=z["stop"];hit=l<=stop if z["side"]==1 else h>=stop
  adverse[sym]=(min(o,stop) if z["side"]==1 else max(o,stop)) if hit else (l if z["side"]==1 else h)
 worst=equity(adverse)
 maxdd=max(maxdd,(peak-worst)/peak*100);min_eq=min(min_eq,worst);worst_daily=max(worst_daily,daybase-worst)
 if worst<=daybase*.95:
  daily_breaches.add(day)
  if first_breach is None:first_breach=dict(time=iso(t),type="daily")
 if worst<=4500:
  total_breach=True
  if first_breach is None:first_breach=dict(time=iso(t),type="total")
 for sym in list(positions):
  if sym not in bars:continue
  o,h,l,c=bars[sym];z=positions[sym];side=z["side"];stop=z["stop"];target=z["target"]
  stophit=l<=stop if side==1 else h>=stop
  takehit=h>=target if side==1 else l<=target
  if stophit and takehit:ambiguous+=1
  price=o if side*(o-stop)<=0 or side*(o-target)>=0 else stop if stophit else target if takehit else None
  if price is not None:
   pnl=side*z["qty"]*(price-z["entry"])-z["fee"]-z["qty"]*price*FEE
   cash+=side*z["qty"]*(price-z["entry"])-z["qty"]*price*FEE
   trades.append(dict(symbol=sym,entry=iso(z["entry_ms"]),exit=iso(t+H),pnl=round(pnl,4),reason="stop" if stophit else "take",ambiguous=bool(stophit and takehit)))
   del positions[sym]
  elif z["act"] is not None:
   favorable=h if side==1 else l
   z["best"]=max(z["best"],favorable) if side==1 else min(z["best"],favorable)
   if side*(z["best"]-z["entry"])>=z["act"]*z["atr"]:z["active"]=True
   if z["active"]:
    trail=z["best"]-side*z["dist"]*z["atr"]
    z["stop"]=max(z["stop"],trail) if side==1 else min(z["stop"],trail)
 now=equity({s:closes.get(s,z["entry"]) for s,z in positions.items()});peak=max(peak,now)
 if (t+H)%DAY==0:daily.append([iso(t+H),round(now,2)])
final=equity({s:data[s][end][3] if end in data[s] else z["entry"] for s,z in positions.items()})
gains=sum(max(0,x["pnl"]) for x in trades);losses=-sum(min(0,x["pnl"]) for x in trades)
out=dict(description=f"Native {TF}H closed-bar DeltaRSI; {TF}H stop-first conservative fills; trail updates after current bar; 5ATR stop/take; $1000 nominal, max 3 positions; 0.08% fee per side + 0.03% full spread; no funding/slippage; continuous $5000; assets eligible after their own data starts; approximate daily/intrabar risk on {TF}H OHLC; in-sample.",start=iso(start),end=iso(end+H),initial=5000,final=round(final,2),return_pct=round((final/5000-1)*100,3),max_dd_pct=round(maxdd,3),min_intrabar_equity=round(min_eq,2),max_intrabar_daily_loss=round(worst_daily,2),daily_breach_days=len(daily_breaches),total_breach=total_breach,first_breach=first_breach,closed_trades=len(trades),win_pct=round(100*sum(x["pnl"]>0 for x in trades)/len(trades),2) if trades else None,pf=round(gains/losses,3) if losses else None,ambiguous_stop_take_bars=ambiguous,skipped_signals=skipped,max_open=max_open,open_positions_end=list(positions),sources=sources,by_symbol={s:{"trades":sum(x["symbol"]==s for x in trades),"pnl":round(sum(x["pnl"] for x in trades if x["symbol"]==s),2)} for s in SYMS},trades=trades,daily_equity=daily)
Path("reports").mkdir(exist_ok=True)
Path(f"reports/deltarsi_prop_one_year_{TF}h.json").write_text(json.dumps(out,indent=2))
print("RESULT",json.dumps({k:v for k,v in out.items() if k not in ("trades","daily_equity","sources")}),flush=True)
