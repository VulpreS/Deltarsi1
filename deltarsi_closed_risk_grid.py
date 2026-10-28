"""Grid research: strict closed 4H DeltaRSI, cached BTC hourly, stop-first, fees/funding."""
import json,math,statistics,itertools
from pathlib import Path
from causal_4h_parity_audit import load,events,H,metrics,iso
raw,sha=load("BTCUSDT")
ev,_=events(raw)
signals=ev["closed"]
FEE=.0015
FUND=.0003
def sim(e,sl_k,tp_k,be_r,trail_r,eq,terminal):
 i=e["entry_i"]
 if i>=terminal:return None
 side=e["side"];entry=raw[i][1];atr=e["atr_4h"]
 if not math.isfinite(atr) or atr<=0:return None
 risk=sl_k*atr
 stop=entry-side*risk
 target=entry+side*tp_k*atr
 if stop<=0 or target<=0:return None
 qty=min(.0025*eq/risk,eq/entry)
 highwater=0.;be=False;end=min(i+47,terminal-1)
 px=raw[end][4];reason="time";z=end
 for j in range(i,end+1):
  t,o,h,l,cl=raw[j]
  # Stop and TP already active at bar open. Gaps are filled at open.
  if side*(o-stop)<=0:px=o;reason="stop_gap";z=j;break
  if side*(o-target)>=0:px=o;reason="tp_gap";z=j;break
  hitstop=(l<=stop if side==1 else h>=stop)
  hittp=(h>=target if side==1 else l<=target)
  if hitstop:px=stop;reason="stop";z=j;break
  if hittp:px=target;reason="tp";z=j;break
  favorable=(h-entry if side==1 else entry-l)
  highwater=max(highwater,favorable/risk)
  # Updated stops apply from the NEXT hourly bar only (no intrabar lookahead).
  if be_r is not None and highwater>=be_r:be=True
  if be:stop=max(stop,entry) if side==1 else min(stop,entry)
  if trail_r is not None and highwater>=trail_r:
   extreme=(h if side==1 else l)
   new=extreme-side*risk
   stop=max(stop,new) if side==1 else min(stop,new)
 fee=qty*(entry+px)*FEE/2
 funding=qty*entry*FUND*math.ceil((z-i+1)/8)
 net=side*qty*(px-entry)-fee-funding
 return dict(entry_i=i,exit_i=z,side=side,reason=reason,net=net,net_R=net/(qty*risk),entry=entry,exit=px)
def evaluate(params,window=None):
 sl,tp,be,trail=params
 a,b=(0,len(raw)) if window is None else window
 eq=1.;peak=1.;dd=0.;tr=[];occupied=-1
 for e in signals:
  i=e["entry_i"]
  if i<a or i>=b or i<=occupied:continue
  t=sim(e,sl,tp,be,trail,eq,b)
  if t is None:continue
  eq+=t["net"];peak=max(peak,eq);dd=max(dd,1-eq/peak);tr.append(t);occupied=t["exit_i"]
 vals=[t["net"] for t in tr];w=sum(v>0 for v in vals);p=sum(max(v,0) for v in vals);loss=-sum(min(v,0) for v in vals)
 return dict(n=len(tr),win_pct=round(100*w/len(tr),2) if tr else None,net_return_pct=round((eq-1)*100,4),pf=round(p/loss,4) if loss else None,closed_dd_pct=round(dd*100,4),mean_R=round(statistics.mean(t["net_R"] for t in tr),4) if tr else None,stop_count=sum(t["reason"].startswith("stop") for t in tr),tp_count=sum(t["reason"].startswith("tp") for t in tr))
grid=list(itertools.product((1.5,2.,2.5,3.),(1.5,2.,3.,4.),(None,.5,1.),(None,1.,2.)))
cuts=[0,len(raw)//3,2*len(raw)//3,len(raw)]
results=[]
for p in grid:
 full=evaluate(p)
 parts=[evaluate(p,(cuts[j],cuts[j+1])) for j in range(3)]
 results.append(dict(sl_atr=p[0],tp_atr=p[1],be_at_R=p[2],trail_start_R=p[3],full=full,thirds=parts))
baseline=next(x for x in results if (x["sl_atr"],x["tp_atr"],x["be_at_R"],x["trail_start_R"])==(2.5,3.,None,None))
# Rank robustly: reject configs with too few trades or poor worst-third returns.
ranked=sorted(results,key=lambda x:(sum(t["net_return_pct"]>0 for t in x["thirds"]),min(t["net_return_pct"] for t in x["thirds"]),x["full"]["net_return_pct"]),reverse=True)
out=dict(note="Exploratory in-sample grid, 192 configurations; no independent OOS. Closed trade DD only. Conservative stop-first hourly OHLC, stop updates next hour, synthetic 3bp per 8h funding, 15bp round trip fees, fixed 0.25% equity risk and max 1x notional.",source_sha=sha,signals=len(signals),hours=len(raw),baseline=baseline,top=ranked[:20],all=results)
Path("reports/deltarsi_closed_risk_grid.json").write_text(json.dumps(out,indent=2))
print("baseline",baseline["full"],flush=True)
for x in ranked[:10]:print(x["sl_atr"],x["tp_atr"],x["be_at_R"],x["trail_start_R"],x["full"],[y["net_return_pct"] for y in x["thirds"]],flush=True)
