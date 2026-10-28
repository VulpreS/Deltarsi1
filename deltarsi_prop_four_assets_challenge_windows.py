"""One continuous $5k Upscale research account across BTC ETH ICP TON.
Closed 4h DeltaRSI; 1h stop-first; max three positions; $1000 notional each.
No challenge resets; synthetic funding; no slippage. Single common date intersection.
"""
import json,math,datetime as dt
from pathlib import Path
from causal_4h_parity_audit import load,events,H
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT")
PARAM={"BTCUSDT":(2.,.5),"ETHUSDT":(3.,.5),"ICPUSDT":(None,None),"TONUSDT":(2.,1.)}
DAY=24*H
# Precompute signals once for reproducible weekly-start challenge trials.
DATA={};SIGNALS={};HASHES={}
for sym in SYMS:
 raw,sha=load(sym);DATA[sym]={r[0]:r[1:] for r in raw};HASHES[sym]=sha
 ev,_=events(raw);SIGNALS[sym]={e["entry_ms"]:e for e in ev["closed"]}
COMMON=set.intersection(*(set(v) for v in DATA.values()))
BASE_START=min(COMMON);BASE_END=max(COMMON)
def simulate(start,end,target_pct,fee=.00008,funding=.00015,max_positions=3,priority='baseline'):
 data=DATA;signals=SIGNALS;hashes=HASHES
 times=list(range(start,end+H,H))
 if any(t not in COMMON for t in times):raise ValueError("Noncontinuous common history")
 cash=5000.;p={};peak=5000.;dd=0.;day=None;daybase=5000.;firstbreach=None;breachdays=set();totalbreach=False
 trades=[];fundpaid=0.;maxopen=0;skipped=0;daily=[];min_equity=5000.;worst_daily=0.;outcome="timeout";finish=t if False else start
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[sym]-z["entry"])-z["qty"]*prices[sym]*fee for sym,z in p.items())
 for t in times:
  bars={sym:data[sym][t] for sym in SYMS}
  opens={sym:b[0] for sym,b in bars.items()}
  closes={sym:b[3] for sym,b in bars.items()}
  if t//DAY!=day:
   day=t//DAY;daybase=equity(opens)
  candidates=[sym for sym in SYMS if sym not in p and t in signals[sym]]
  if priority!='baseline':
   def score(sym):
    e=signals[sym][t];peak=abs(e['prior_4h_delta']);ratio=e['ratio'];decay=max(0.,1.-ratio)
    if priority=='peak':return peak
    if priority=='decay':return decay
    if priority=='combined':return math.log1p(peak)*decay
    raise ValueError('Unknown priority '+priority)
   candidates.sort(key=lambda sym:(-score(sym),sym))
  for sym in candidates:
   if len(p)>=max_positions:
    skipped+=1;continue
   e=signals[sym][t];a=e["atr_4h"];side=e["side"];o=opens[sym]
   if not math.isfinite(a) or a<=0 or o-side*5*a<=0:continue
   q=1000/o;cash-=q*o*fee
   act,dist=PARAM[sym]
   p[sym]=dict(side=side,qty=q,entry=o,stop=o-side*5*a,target=o+side*5*a,atr=a,best=o,act=act,dist=dist,active=False,fee=q*o*fee,funding=0.,entry_ms=t)
  maxopen=max(maxopen,len(p))
  adverse={}
  for sym,b in bars.items():
   o,h,l,c=b
   if sym not in p:adverse[sym]=c;continue
   z=p[sym];side=z["side"];stop=z["stop"]
   hit=l<=stop if side==1 else h>=stop
   adverse[sym]=(min(o,stop) if side==1 else max(o,stop)) if hit else (l if side==1 else h)
  worst=equity(adverse)
  dd=max(dd,(peak-worst)/peak*100);min_equity=min(min_equity,worst)
  worst_daily=max(worst_daily,daybase-worst)
  if worst<=daybase-250:
   breachdays.add(day)
   if firstbreach is None:firstbreach={"utc":dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),"type":"daily"}
  if worst<=4500:
   totalbreach=True
   if firstbreach is None:firstbreach={"utc":dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),"type":"total"}
  if worst<=4500 or worst<=daybase-250:
   outcome="breach";finish=t;break
  for sym in list(p):
   o,h,l,c=bars[sym];z=p[sym];side=z["side"];stop=z["stop"];target=z["target"]
   stophit=l<=stop if side==1 else h>=stop
   takehit=h>=target if side==1 else l<=target
   price=o if side*(o-stop)<=0 or side*(o-target)>=0 else stop if stophit else target if takehit else None
   if price is not None:
    gross=side*z["qty"]*(price-z["entry"]);exitfee=z["qty"]*price*fee
    cash+=gross-exitfee
    trades.append(dict(symbol=sym,entry_ms=z["entry_ms"],exit_ms=t+H,side=side,pnl=round(gross-z["fee"]-exitfee-z["funding"],4),reason="stop" if stophit else "take"))
    del p[sym]
   else:
    if z["act"] is not None:
     favorable=h if side==1 else l
     z["best"]=max(z["best"],favorable) if side==1 else min(z["best"],favorable)
     if side*(z["best"]-z["entry"])>=z["act"]*z["atr"]:z["active"]=True
     if z["active"]:
      trail=z["best"]-side*z["dist"]*z["atr"]
      z["stop"]=max(z["stop"],trail) if side==1 else min(z["stop"],trail)
    if t%(8*H)==0:
     cost=z["qty"]*z["entry"]*funding;cash-=cost;z["funding"]+=cost;fundpaid+=cost
  now=equity(closes);peak=max(peak,now)
  if (t+H)%DAY==0:daily.append([t+H,round(now,2)])
  if now>=5000*(1+target_pct/100):
   outcome="pass";finish=t+H;break
 final=equity({sym:data[sym][min(finish if outcome=="breach" else (finish-H if outcome=="pass" else end),end)][3] for sym in SYMS})
 gains=sum(max(0,x["pnl"]) for x in trades);losses=-sum(min(0,x["pnl"]) for x in trades)
 mid=daily[len(daily)//2-1][1] if daily else 5000
 return dict(outcome=outcome,days_elapsed=round((finish-start)/DAY,2) if outcome!="timeout" else round((end-start+H)/DAY,2),start_utc=dt.datetime.fromtimestamp(start/1000,dt.timezone.utc).isoformat(),end_utc=dt.datetime.fromtimestamp((end+H)/1000,dt.timezone.utc).isoformat(),initial=5000,final=round(final,2),return_pct=round((final/5000-1)*100,3),max_dd_pct=round(dd,3),min_intrabar_equity=round(min_equity,2),max_intrabar_daily_loss=round(worst_daily,2),daily_breach_days=len(breachdays),total_breach=totalbreach,first_breach=firstbreach,closed_trades=len(trades),win_pct=round(100*sum(x["pnl"]>0 for x in trades)/len(trades),2) if trades else None,pf=round(gains/losses,3) if losses else None,open_positions_end=list(p),max_concurrent=maxopen,skipped_signals=skipped,funding_paid=round(fundpaid,2),half1_pct=round((mid/5000-1)*100,2),half2_pct=round((final/mid-1)*100,2),by_symbol={sym:dict(trades=sum(x["symbol"]==sym for x in trades),realized_pnl=round(sum(x["pnl"] for x in trades if x["symbol"]==sym),2)) for sym in SYMS},daily_equity=daily,source_sha256=hashes)

if __name__=="__main__":
 out={"description":"Independent weekly rolling starts; each trial resets to $5000, 0 positions; 14/30 calendar days; pass at hourly close; breach checked first on hourly adverse OHLC; not official Upscale evaluation. All targets independent, not sequential stages.","parameters":PARAM,"start_step_days":7,"models":{}}
 for name,fee,funding in [("upscale_basic",.00008,.00015),("prior",.00075,.0003)]:
  out["models"][name]={}
  for days in (14,30):
   for target in (5,8):
    trials=[]
    for start in range(BASE_START,BASE_END-(days*DAY)+H,7*DAY):
     if any(t not in COMMON for t in range(start,start+days*DAY,H)):continue
     r=simulate(start,start+days*DAY-H,target,fee,funding)
     trials.append({k:r[k] for k in ("start_utc","outcome","days_elapsed","return_pct","max_dd_pct","closed_trades","first_breach")})
    counts={x:sum(r["outcome"]==x for r in trials) for x in ("pass","breach","timeout")}
    out["models"][name][f"{days}d_target_{target}pct"]={"trials":len(trials),"counts":counts,"pass_rate_pct":round(100*counts["pass"]/len(trials),2) if trials else None,"results":trials}
    print(name,days,target,counts,flush=True)
 Path("reports").mkdir(exist_ok=True)
 Path("reports/deltarsi_prop_four_assets_challenge_windows.json").write_text(json.dumps(out,indent=2))
