"""Isolated five full-position fixed-SL runs, never production. Baseline: causal_4h_parity_audit closed events, 2.5 ATR SL, 3 ATR TP, 48h time exit."""
import json, math, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load, events, H
from execution_core import resolve_bar

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
STOPS=(None,.5,1.,1.5,2.,2.5)
COST=.0015
HOLD=48

def trade(raw,e,stop_pct):
 i=e["entry_i"]
 if i>=len(raw):return None
 side=e["side"];entry=raw[i][1];atr=e["atr_4h"]
 if not math.isfinite(atr) or atr<=0:return None
 baseline_stop=entry-side*2.5*atr
 baseline_target=entry+side*3*atr
 if min(baseline_stop,baseline_target)<=0:return None
 eligible=2.5*atr/entry*100>2.5
 stop=entry-side*entry*stop_pct/100 if eligible and stop_pct is not None else baseline_stop
 target=baseline_target
 end=min(i+HOLD-1,len(raw)-1)
 exitprice=raw[end][4];exit_i=end;reason="time"
 for j in range(i,end+1):
  price,why=resolve_bar(raw[j],side,stop,target)
  if why:
   exitprice=price;exit_i=j;reason=why;break
 net_pct=100*(side*(exitprice-entry)/entry-COST/2*(1+exitprice/entry))
 return dict(entry_i=i,exit_i=exit_i,net_pct=net_pct,reason=reason,eligible=eligible,entry_ms=raw[i][0])

def summarize(trades,eligible_count):
 vals=[x["net_pct"] for x in trades];win=sum(x>0 for x in vals)
 gains=sum(max(0,x) for x in vals);loss=-sum(min(0,x) for x in vals)
 eq=1.;peak=1.;dd=0.
 for x in vals:
  eq*=1+x/100;peak=max(peak,eq);dd=max(dd,(peak-eq)/peak*100)
 return dict(n=len(trades),eligible_executed=eligible_count,net_compounded_pct=round((eq-1)*100,3),
             mean_net_pct=round(statistics.mean(vals),4) if vals else None,
             win_pct=round(win/len(vals)*100,2) if vals else None,
             profit_factor=round(gains/loss,3) if loss else None,
             closed_trade_max_dd_pct=round(dd,3),
             stops=sum("stop" in str(x["reason"]).lower() for x in trades),
             time_exits=sum(x["reason"]=="time" for x in trades))

def main():
 out=dict(title="Isolated fixed SL single-exit five-run test",baseline="causal_4h_parity_audit: closed events, 2.5 ATR stop, 3 ATR target, 48 hourly bars",
          policy="Replace baseline stop only when baseline 2.5 ATR > 2.5% of entry. Original 3 ATR TP unchanged. One full-position SL, no partials.",
          assumptions="1H stop-first via resolve_bar; 0.15% round-trip assumed costs; no funding; no BE in this baseline; per-symbol independent sequential replay; no official prop challenge simulation; no independent OOS.",
          results={})
 for sym in SYMS:
  raw,sha=load(sym);es,_=events(raw)
  d=dict(data_sha=sha,signal_count=len(es),runs={})
  for stop_pct in STOPS:
   until=-1;tr=[];eligible=0
   for e in es["closed"]:
    if e["entry_i"]<=until:continue
    x=trade(raw,e,stop_pct)
    if x is None:continue
    tr.append(x);until=x["exit_i"];eligible+=x["eligible"]
   key="baseline" if stop_pct is None else f"sl_{stop_pct:.1f}pct"
   d["runs"][key]=summarize(tr,eligible)
  out["results"][sym]=d
  print(sym,json.dumps(d["runs"],ensure_ascii=False),flush=True)
 p=Path("experiments/fixed_sl_grid/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
