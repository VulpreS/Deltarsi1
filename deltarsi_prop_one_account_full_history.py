import json,math,datetime as dt
from pathlib import Path
from causal_4h_parity_audit import load,events,H
DAY=24*H
S=("BTCUSDT","ETHUSDT")
D={}
for s in S:
 r,sha=load(s);ev,_=events(r)
 D[s]=(dict((x[0],x) for x in r),dict((x["entry_ms"],x) for x in ev["closed"]),sha)
start=(max(min(x[0]) for x in D.values())+DAY-1)//DAY*DAY
end=min(max(x[0])+H for x in D.values())
def run(mode):
 cash=5000.;pos={};day=None;daybase=5000.;peak=5000.;maxdd=0.;trades=[];violations=[];qual=set();milestones={};equity_curve=[];last=5000.
 coins=("BTCUSDT",) if mode=="btc" else ("ETHUSDT",) if mode=="eth" else S
 for t in range(start,end,H):
  bars={s:D[s][0].get(t) for s in coins}
  if any(x is None for x in bars.values()):continue
  opens={s:x[1] for s,x in bars.items()};closes={s:x[4] for s,x in bars.items()}
  def eq(prices):
   return cash+sum(p["side"]*p["qty"]*(prices[s]-p["entry"])-p["qty"]*prices[s]*.00075 for s,p in pos.items())
  today=t//DAY
  if day!=today:
   day=today;daybase=eq(opens)
  for s in coins:
   if s in pos or (mode=="mono" and pos):continue
   e=D[s][1].get(t)
   if e is None:continue
   atr=e["atr_4h"];side=e["side"];o=opens[s]
   if not math.isfinite(atr) or atr<=0 or o-side*3*atr<=0:continue
   nominal=1500 if mode=="split" else 3000
   q=nominal/o;cash-=nominal*.00075
   pos[s]=dict(side=side,qty=q,entry=o,sl=o-side*3*atr,tp=o+side*1.5*atr,at=t,fees=nominal*.00075)
  adverse=dict(closes)
  for s,p in pos.items():
   o,h,l,c=bars[s][1:5];side=p["side"];sl=p["sl"]
   hit=l<=sl if side==1 else h>=sl
   adverse[s]=(min(o,sl) if side==1 else max(o,sl)) if hit else (l if side==1 else h)
  worst=eq(adverse)
  maxdd=max(maxdd,(peak-worst)/peak*100)
  if worst<=daybase*.95 and not any(v[0]==today and v[1]=='daily' for v in violations):
   violations.append((today,"daily"))
  if worst<=4500 and not any(v[1]=="total" for v in violations):
   violations.append((today,"total"))
  for s,p in list(pos.items()):
   o,h,l,c=bars[s][1:5];side=p["side"];sl=p["sl"];tp=p["tp"]
   stop=l<=sl if side==1 else h>=sl
   take=h>=tp if side==1 else l<=tp
   price=o if side*(o-sl)<=0 or side*(o-tp)>=0 else sl if stop else tp if take else None
   if price is not None:
    pnl=side*p["qty"]*(price-p["entry"])-p["qty"]*price*.00075-p["fees"]
    cash+=side*p["qty"]*(price-p["entry"])-p["qty"]*price*.00075
    trades.append(dict(symbol=s,entry_ms=p["at"],exit_ms=t+H,pnl=round(pnl,4),side=side))
    del pos[s]
   elif (t//H)%8==0:cash-=p["qty"]*p["entry"]*.0003
  last=eq(closes);peak=max(peak,last)
  if (t+H)//DAY>today:
   if last-daybase>=25:qual.add(today)
   for label,target in (("plus5",5250),("plus8",5400)):
    if label not in milestones and last>=target:milestones[label]=dict(days=round((t+H-start)/DAY,1),equity=round(last,2),qualifying_days=len(qual))
   equity_curve.append(dict(day=today,equity=round(last,2)))
 if pos:
  prices={s:D[s][0][end-H][4] for s in coins if end-H in D[s][0]}
  if len(prices)==len(coins):last=eq(prices)
 wins=sum(x["pnl"]>0 for x in trades);losses=sum(x["pnl"]<0 for x in trades)
 return dict(start_equity=5000,end_equity=round(last,2),return_pct=round((last/5000-1)*100,2),max_drawdown_pct=round(maxdd,2),closed_trades=len(trades),wins=wins,losses=losses,win_rate_pct=round(100*wins/len(trades),2) if trades else None,profit_factor=round(sum(max(0,x["pnl"]) for x in trades)/(-sum(min(0,x["pnl"]) for x in trades)),3) if losses else None,daily_breach_days=sum(x[1]=="daily" for x in violations),total_breach=any(x[1]=="total" for x in violations),first_breach=next((dict(day=round((v[0]*DAY-start)/DAY,1),kind=v[1]) for v in violations),None),milestones=milestones,qualifying_days=len(qual),equity_curve=equity_curve,trades=trades)
out=dict(notes="Single chronological account, no stage resets, 1x fixed notional, 1h conservative adverse excursion; daily threshold 5% of actual day-start equity and static $4500 total; continue trading after breach for diagnostic purposes. Milestones are NOT formal challenge stage passes. Synthetic funding and 15bp roundtrip fees; overlapping candles of two assets treated as simultaneous adverse, conservative.",window=[start,end],results={})
for mode in ("btc","eth","split","mono"):
 out["results"][mode]=run(mode)
 print(mode,{k:v for k,v in out["results"][mode].items() if k not in ("trades","equity_curve")},flush=True)
Path("reports/deltarsi_prop_one_account_full_history.json").write_text(json.dumps(out,indent=2))
