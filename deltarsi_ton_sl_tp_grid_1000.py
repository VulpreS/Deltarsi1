"""TON closed-4H DeltaRSI SL/TP grid, continuous single account, cached candles."""
import json,math,statistics,datetime as dt
from pathlib import Path
from causal_4h_parity_audit import load,events,H
DAY=24*H
raw,sha=load("TONUSDT")
ev,_=events(raw)
signals={x["entry_ms"]:x for x in ev["closed"]}
start=raw[0][0];end=raw[-1][0]+H
SL=[1.,1.5,2.,2.5,3.,3.5,4.,5.]
TP=[.5,1.,1.5,2.,2.5,3.,4.,5.,6.]
# Two fee models: prior simulator and published Basic candidate (verify terms).
COSTS={"prior":(.00075,.0003),"upscale_basic":(.00008,.00015)}
def replay(slm,tpm,fee,funding):
 cash=5000.;p=None;peak=5000.;dd=0.;day=None;daybase=5000.;last=5000.;tr=[];firstbreach=None;breach_days=set();total=False
 equity_daily=[];fundpaid=0.
 for i,(t,o,h,l,c) in enumerate(raw):
  def equity(price):
   return cash if p is None else cash+p["side"]*p["qty"]*(price-p["entry"])-p["qty"]*price*fee
  today=t//DAY
  if today!=day:
   day=today;daybase=equity(o)
  if p is None and t in signals:
   e=signals[t];a=e["atr_4h"];side=e["side"]
   if math.isfinite(a) and a>0 and o-side*slm*a>0:
    q=1000/o;cash-=q*o*fee
    p=dict(side=side,qty=q,entry=o,stop=o-side*slm*a,target=o+side*tpm*a,entry_ms=t,fee=q*o*fee,funding=0.)
  adverse=c
  if p:
   side=p["side"];stop=p["stop"]
   hit=l<=stop if side==1 else h>=stop
   adverse=(min(o,stop) if side==1 else max(o,stop)) if hit else (l if side==1 else h)
  worst=equity(adverse)
  dd=max(dd,(peak-worst)/peak*100)
  if worst<=daybase-250:
   breach_days.add(today)
   if firstbreach is None:firstbreach=dict(day=round((t-start)/DAY,2),type="daily")
  if worst<=4500:
   total=True
   if firstbreach is None:firstbreach=dict(day=round((t-start)/DAY,2),type="total")
  if p:
   side=p["side"];stop=p["stop"];target=p["target"]
   stophit=l<=stop if side==1 else h>=stop
   takehit=h>=target if side==1 else l<=target
   price=o if side*(o-stop)<=0 or side*(o-target)>=0 else stop if stophit else target if takehit else None
   if price is not None:
    gross=side*p["qty"]*(price-p["entry"])
    exitfee=p["qty"]*price*fee
    cash+=gross-exitfee
    tr.append(dict(entry_ms=p["entry_ms"],exit_ms=t+H,side=side,pnl=gross-p["fee"]-exitfee-p["funding"],reason="stop" if stophit else "take"))
    p=None
   elif t%(8*H)==0:
    cost=p["qty"]*p["entry"]*funding;cash-=cost;p["funding"]+=cost;fundpaid+=cost
  last=equity(c);peak=max(peak,last)
  if (t+H)%DAY==0:equity_daily.append(last)
 if p:
  last=equity(raw[-1][4])
  # Mark-to-market final position, do not count as closed trade.
 gains=sum(max(0,x["pnl"]) for x in tr);losses=-sum(min(0,x["pnl"]) for x in tr)
 return dict(equity=round(last,2),return_pct=round((last/5000-1)*100,3),max_dd_pct=round(dd,3),trades=len(tr),win_pct=round(100*sum(x["pnl"]>0 for x in tr)/len(tr),2) if tr else None,pf=round(gains/losses,3) if losses else None,breach_daily_days=len(breach_days),breach_total=total,first_breach=firstbreach,half1_pct=round((equity_daily[len(equity_daily)//2-1]/5000-1)*100,2) if equity_daily else None,half2_pct=round((last/equity_daily[len(equity_daily)//2-1]-1)*100,2) if equity_daily else None,funding_paid=round(fundpaid,2))
out=dict(source_sha256=sha,window=[start,end],symbol="TONUSDT",signal="strict closed 4H DeltaRSI",capital=5000,notional=1000,stop_atr=SL,take_atr=TP,notes="Exploratory full-period parameter grid, no stage resets, one position, 1H stop-first. Continue after violations for diagnosis; half-period performance is not independent out-of-sample. Fees/funding scenarios are modeled, not verified executions. Funding at 00/08/16 UTC on still-open positions. No slippage or TON spread.",grid={},leaders={})
for name,(fee,funding) in COSTS.items():
 rows=[]
 for sl in SL:
  for tp in TP:
   r=replay(sl,tp,fee,funding)
   rows.append(dict(sl_atr=sl,tp_atr=tp,**r))
 valid=[x for x in rows if not x["breach_daily_days"] and not x["breach_total"]]
 ranked=sorted(valid,key=lambda x:(x["return_pct"],-x["max_dd_pct"]),reverse=True)
 out["grid"][name]=rows
 out["leaders"][name]=dict(safe_count=len(valid),total_count=len(rows),best_safe=ranked[:12],best_all=sorted(rows,key=lambda x:x["return_pct"],reverse=True)[:5])
 print(name,"safe",len(valid),"top",ranked[:3],flush=True)
Path("reports/deltarsi_ton_sl_tp_grid_1000.json").write_text(json.dumps(out,indent=2))
