import json
from pathlib import Path
from analyze_mtf_5y import indicator
from causal_4h_parity_audit import load,H,FOUR
from completed_candles import aggregate_completed
raw,sha=load("BTCUSDT")
bars=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
ind=indicator(bars)
lookup={b[0]:i for i,b in enumerate(raw)}
events=[]
for i in range(210,len(bars)):
 p,c=ind["color"][i-1:i+1]
 side=1 if (p,c)==("mediumR","weakR") else -1 if (p,c)==("mediumB","weakB") else 0
 if not side:continue
 # No bright-phase prerequisite. Price extreme is observed over recent completed 4H candles.
 region=bars[max(0,i-12):i+1]
 extreme=min(b[3] for b in region) if side==1 else max(b[2] for b in region)
 wick=False
 for b in bars[max(0,i-12):i+1]:
  o,h,l,cl=b[1:];tail=min(o,cl)-l if side==1 else h-max(o,cl)
  near=abs((l if side==1 else h)/extreme-1)<=.005
  if near and h>l and tail/(h-l)>=.35 and tail>=abs(cl-o):wick=True
 k=lookup.get(bars[i][0]+FOUR)
 if k is not None:events.append((k,side,extreme,wick))
def run(wicks,exit_mode,tp_pct):
 trades=[];until=-1
 for k,side,extreme,wick in events:
  if k<=until or (wicks and not wick):continue
  entry=raw[k][1];stop=extreme*(.999 if side==1 else 1.001)
  if side*(entry-stop)<=0:continue
  be=False
  for z in range(k,len(raw)):
   t,o,h,l,c=raw[z]
   if (o<=stop if side==1 else o>=stop):
    exit=o;reason="gap";break
   if (l<=stop if side==1 else h>=stop):
    exit=stop;reason="BE" if be else "SL";break
   # Stop-first if target and stop share an hourly bar; never assume favorable intrabar ordering.
   target=entry*(1+side*tp_pct/100) if tp_pct else None
   if target is not None and (h>=target if side==1 else l<=target):
    exit=target;reason="TP";break
   trigger=entry*(1.01 if side==1 else .99)
   if not be and (h>trigger if side==1 else l<trigger):
    be=True;stop=entry
    if (l<=stop if side==1 else h>=stop):
     exit=stop;reason="BE_same_hour";break
   if (t+H)%FOUR==0:
    bi=(t+H-bars[0][0])//FOUR-1
    if 1<=bi<len(bars):
     pc,cc=ind["color"][bi-1:bi+1]
     reverse=("mediumB","weakB") if side==1 else ("mediumR","weakR")
     same=(("weakR","mediumR") if side==1 else ("weakB","mediumB"))
     should_exit=(pc,cc)==reverse if exit_mode=="opposite" else (pc,cc)==same
     if should_exit and z+1<len(raw):
      z+=1;exit=raw[z][1];reason=exit_mode;break
  else:continue
  until=z
  trades.append(dict(entry_ms=raw[k][0],exit_ms=raw[z][0],side=side,pnl_pct=100*side*(exit/entry-1),reason=reason,wick=wick))
 return trades
def stats(t):
 p=[v["pnl_pct"] for v in t];w=[x for x in p if x>0];l=[x for x in p if x<0]
 return dict(n=len(p),win_rate_pct=100*len(w)/len(p) if p else None,mean_pct=sum(p)/len(p) if p else None,profit_factor=sum(w)/-sum(l) if l else None,BE=sum(x["reason"].startswith("BE") for x in t),SL=sum(x["reason"]=="SL" for x in t))
result=dict(data_sha=sha,hours=len(raw),event_count=len(events),note="Research proxy: wick 35% range and >=body within 0.5% extreme, no bright-phase gate, recent 12-bar price extreme, stop buffer 0.1%, TP 1.5/2% and no TP, no fees/slippage, 1H stop-first",runs={})
for flag in (False,True):
 for exit_mode in ("opposite","same_color_medium"):
  for tp in (None,1.5,2.0):
   t=run(flag,exit_mode,tp);key=("with_wicks" if flag else "all_signals")+"_"+exit_mode+"_"+("no_tp" if tp is None else "tp_"+str(tp))
   result["runs"][key]=dict(stats=stats(t),trades=t)
   print(key,stats(t),flush=True)
Path("reports/deltarsi_exit_tp_grid.json").write_text(json.dumps(result,indent=2))
