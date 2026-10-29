"""Isolated full-grid study. One full exit per trade. No production integration."""
import json,math,statistics,sys,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from execution_core import resolve_bar
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
FIXED=(.5,1.,1.5,2.,2.5)
SL_MODES=[("atr",2.5)]+[("fixed",v) for v in FIXED]
TP_MODES=[("atr",3.)]+[("fixed",v) for v in FIXED]
COST=.0015;HOLD=48

def levels(entry,atr,side,sm,tm):
 stop=entry-side*(2.5*atr if sm[0]=="atr" else entry*sm[1]/100)
 target=entry+side*(3*atr if tm[0]=="atr" else entry*tm[1]/100)
 return stop,target

def trade(raw,e,sm,tm,be):
 i=e["entry_i"]
 if i>=len(raw):return None
 entry=raw[i][1];side=e["side"];atr=e["atr_4h"]
 if not math.isfinite(atr) or atr<=0 or entry<=0:return None
 stop,target=levels(entry,atr,side,sm,tm)
 if min(stop,target)<=0:return None
 trigger=entry*(1+side*.01)
 end=min(i+HOLD-1,len(raw)-1)
 px=raw[end][4];jend=end;reason="time";active=False
 for j in range(i,end+1):
  t,o,h,l,c=raw[j]
  # Intrabar ambiguity is resolved pessimistically. Existing stop is checked first.
  fill,why=resolve_bar(raw[j],side,stop,target)
  if why:
   px=fill;jend=j;reason=str(why);break
  # If BE trigger and retest occur within same hourly candle, assume retest after trigger.
  if be and not active and (h>=trigger if side==1 else l<=trigger):
   active=True;stop=entry
   if (l<=entry if side==1 else h>=entry):
    px=entry;jend=j;reason="be_same_hour";break
  if be and active:stop=entry
 net=100*(side*(px-entry)/entry-COST/2*(1+px/entry))
 return dict(entry_i=i,exit_i=jend,entry_ms=raw[i][0],exit_ms=raw[jend][0]+H,net_pct=net,reason=reason)

def summary(trades):
 vals=[t["net_pct"] for t in trades];n=len(vals);p=sum(max(0,v) for v in vals);l=-sum(min(0,v) for v in vals)
 eq=1.;peak=1.;dd=0.
 for v in vals:
  eq*=1+v/100;peak=max(peak,eq);dd=max(dd,(peak-eq)/peak*100)
 return dict(n=n,net_compounded_pct=round((eq-1)*100,3),win_pct=round(100*sum(v>0 for v in vals)/n,2) if n else None,
   profit_factor=round(p/l,3) if l else None,closed_trade_dd_pct=round(dd,3),
   stop_count=sum("stop" in t["reason"].lower() for t in trades),
   be_count=sum("be" in t["reason"].lower() for t in trades),
   time_count=sum(t["reason"]=="time" for t in trades),
   mean_hold_hours=round(statistics.mean((t["exit_ms"]-t["entry_ms"])/H for t in trades),2) if n else None)

def main():
 out=dict(title="Fixed/ATR TP x fixed/ATR SL x breakeven at +1% grid",
   config=dict(stop_modes=SL_MODES,target_modes=TP_MODES,be=[False,True],cost_roundtrip=.0015,max_hold_hours=48),
   caveats=["All configurations apply to all valid signals; no >2.5% eligibility gate in this factorial study.",
   "Closed 4H events, 1H stop-first OHLC, same-hour BE trigger/retest conservative; no exact tick order.",
   "BE at +1% moves stop to ENTRY PRICE, not fee-adjusted break-even.",
   "No funding, no real prop challenge equity/risk replay, no independent holdout, per-symbol 1x sequential returns.",
   "48-hour time exit remains. No partial exits. No live orders."],results={})
 for sym in SYMS:
  raw,sha=load(sym);ev,_=events(raw);asset=dict(data_sha=sha,signal_count=len(ev["closed"]),runs={})
  for sm,tm,be in itertools.product(SL_MODES,TP_MODES,(False,True)):
   until=-1;trades=[]
   for e in ev["closed"]:
    if e["entry_i"]<=until:continue
    x=trade(raw,e,sm,tm,be)
    if x is None:continue
    trades.append(x);until=x["exit_i"]
   key=f"sl_{sm[0]}_{sm[1]:g}__tp_{tm[0]}_{tm[1]:g}__be_{int(be)}"
   asset["runs"][key]=summary(trades)
  out["results"][sym]=asset
  ranked=sorted(asset["runs"].items(),key=lambda kv:kv[1]["net_compounded_pct"],reverse=True)
  print(sym,"runs",len(asset["runs"]),"baseline",asset["runs"]["sl_atr_2.5__tp_atr_3__be_0"],"best5",ranked[:5],flush=True)
 p=Path("experiments/full_exit_grid/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
