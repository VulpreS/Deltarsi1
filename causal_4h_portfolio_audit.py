"""P1 #13 cross-asset portfolio of frozen causal forming/closed 4H fade signals.
Cached 1H OHLC only. No API, no orders. All historical windows previously inspected.
"""
import datetime as dt, hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path
from causal_4h_parity_audit import load,events,H,SL_ATR,TP_ATR,HOLD_HOURS,PARAM_HASH
from execution_core import resolve_bar
from funding_timing import exposure_bounds
from portfolio_risk_audit import resolve_open_gap

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT")
COSTS=(.0015,.0025,.004)
FUNDING=(0.,.0001,.0003)
RISK=.0025
PORT_RISK=.005
MAX_POS=2
MAX_SYMBOL_NOTIONAL=1.
MAX_GROSS=2.
CONFIG={"symbols":SYMS,"signal_modes":["forming","closed","frozen_turn"],"causal_signal_hash":PARAM_HASH,
 "stop_atr_4h":SL_ATR,"target_atr_4h":TP_ATR,"hold_1h_bars":HOLD_HOURS,
 "risk":RISK,"aggregate_risk":PORT_RISK,"max_positions":MAX_POS,
 "max_symbol_notional":MAX_SYMBOL_NOTIONAL,"max_gross_notional":MAX_GROSS,
 "tie_priority":SYMS,"costs":COSTS,"synthetic_funding":FUNDING,
 "mark":"hourly_close","gap":"resting_first","entry":"next_1h_open"}
CONFIG_HASH=hashlib.sha256(json.dumps(CONFIG,sort_keys=True).encode()).hexdigest()
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()

def prepare():
 data={}; hashes={}
 for sym in SYMS:
  raw,sha=load(sym);ev,_=events(raw)
  data[sym]={"rows":{r[0]:r for r in raw},"events":{mode:{e["entry_ms"]:e for e in es} for mode,es in ev.items()}}
  hashes[sym]=sha
 common=sorted(set.intersection(*(set(d["rows"]) for d in data.values())))
 if not common or any(b-a!=H for a,b in zip(common,common[1:])):raise ValueError("Missing common hourly data")
 return data,common,hashes

def funding(p,earliest,latest,rate):
 return p["entry_notional"]*rate*exposure_bounds(p["entry_ms"],earliest,latest)["funding_events_max"]

def equity_at(data,active,cash,t,rate,at_close):
 eq=cash
 for s,p in active.items():
  row=data[s]["rows"][t]
  mark=row[4] if at_close else row[1]
  when=t+H if at_close else t
  eq+=p["side"]*p["qty"]*(mark-p["entry"])-funding(p,when,when,rate)
 return eq

def simulate(data,times,mode,cost=.0015,rate=.0003,starting_cash=1.):
 if mode not in ("forming","closed","frozen_turn"):raise ValueError("mode")
 cash=starting_cash;active={};ledger=[];curve=[];skips=defaultdict(int);attempts=defaultdict(int)
 def settle(s,price,reason,t,latest):
  nonlocal cash
  p=active.pop(s)
  earliest=t if reason in ("stop","target") else latest
  f=funding(p,earliest,latest,rate)
  exit_fee=p["qty"]*price*cost/2
  gross=p["side"]*p["qty"]*(price-p["entry"])
  net=gross-p["entry_fee"]-exit_fee-f
  cash+=gross-exit_fee-f
  ledger.append({"symbol":s,"side":p["side"],"entry_ms":p["entry_ms"],"exit_ms":latest,
   "reason":reason,"gross":gross,"fees":p["entry_fee"]+exit_fee,
   "funding":f,"net":net,"R":net/p["risk"],"risk":p["risk"],
   "signal_ms":p["signal_ms"],"stop":p["stop"],"target":p["target"]})
 for t in times:
  # Only OPEN prices are visible before admission; no current high/low leakage.
  for s in tuple(active):
   p=active[s];o=data[s]["rows"][t][1]
   fill,reason=resolve_open_gap(o,p["side"],p["stop"],p["target"])
   if reason:settle(s,fill,reason,t,t)
  for s in SYMS:
   e=data[s]["events"][mode].get(t)
   if e is None:continue
   attempts[s]+=1
   if e["decision_ms"]>t or e["entry_ms"]!=t:raise AssertionError("Future signal")
   if s in active:skips["same_symbol"]+=1;continue
   if len(active)>=MAX_POS:skips["max_positions"]+=1;continue
   row=data[s]["rows"][t];price=row[1];a=e["atr_4h"];side=e["side"]
   if not (math.isfinite(a) and a>0 and price>0 and side in (-1,1)):
    skips["invalid_input"]+=1;continue
   stop=price-side*SL_ATR*a;target=price+side*TP_ATR*a
   if stop<=0 or target<=0 or side*(price-stop)<=0:
    skips["invalid_stop"]+=1;continue
   eq=equity_at(data,active,cash,t,rate,False)
   risk_budget=min(RISK*eq,PORT_RISK*eq-sum(p["risk"] for p in active.values()))
   if eq<=0 or risk_budget<=0:skips["risk_budget"]+=1;continue
   qty=risk_budget/abs(price-stop);notional=qty*price
   if notional>MAX_SYMBOL_NOTIONAL*eq or notional+sum(p["entry_notional"] for p in active.values())>MAX_GROSS*eq:
    skips["notional_cap"]+=1;continue
   fee=notional*cost/2
   if fee>=eq or fee>=cash:skips["fee_affordability"]+=1;continue
   cash-=fee
   active[s]={"entry_ms":t,"signal_ms":e["decision_ms"],"side":side,"qty":qty,
    "entry":price,"stop":stop,"target":target,"risk":risk_budget,
    "entry_notional":notional,"entry_fee":fee}
  # OHLC resolution AFTER admissions; intrabar stop wins ambiguous bars.
  for s in tuple(active):
   p=active[s];row=data[s]["rows"][t]
   fill,reason=resolve_bar(row,p["side"],p["stop"],p["target"])
   if reason:
    settle(s,fill,reason,t,t+H);continue
   if t-p["entry_ms"]>= (HOLD_HOURS-1)*H or t==times[-1]:
    settle(s,row[4],"time" if t!=times[-1] else "terminal",t+H,t+H)
  eq=equity_at(data,active,cash,t,rate,True)
  if not math.isfinite(eq) or eq<=0:raise AssertionError("Nonpositive portfolio equity")
  curve.append((t+H,eq,len(active)))
 if active:raise AssertionError("Positions left after terminal")
 return {"trades":ledger,"curve":curve,"skips":dict(skips),"attempts":dict(attempts),
  "start_cash":starting_cash,"final_cash":cash}

def metrics(run):
 tr=run["trades"];vals=[p["net"] for p in tr]
 pos=sum(max(0,x) for x in vals);neg=-sum(min(0,x) for x in vals)
 peak=run["start_cash"];dd=0.;worst=0.
 for _,eq,_ in run["curve"]:
  peak=max(peak,eq);dd=max(dd,1-eq/peak)
 ret=100*(run["final_cash"]/run["start_cash"]-1)
 return {"n":len(tr),"net_return_pct":round(ret,4),
  "pf":round(pos/neg,4) if neg else None,
  "win_pct":round(100*sum(v>0 for v in vals)/len(vals),2) if vals else None,
  "mean_R":round(statistics.mean(p["R"] for p in tr),4) if tr else None,
  "max_hourly_close_mtm_dd_pct":round(100*dd,4),
  "return_over_dd":round(ret/(100*dd),4) if dd else None,
  "fee_total":round(sum(p["fees"] for p in tr),6),
  "funding_total":round(sum(p["funding"] for p in tr),6),
  "exposure_pct":round(100*sum(c>0 for _,_,c in run["curve"])/len(run["curve"]),2),
  "by_asset":{s:{"n":len([p for p in tr if p["symbol"]==s]),
    "net_pnl":round(sum(p["net"] for p in tr if p["symbol"]==s),6),
    "mean_R":round(statistics.mean([p["R"] for p in tr if p["symbol"]==s]),4)
      if any(p["symbol"]==s for p in tr) else None} for s in SYMS},
  "skips":run["skips"],"attempts":run["attempts"]}

def main():
 data,times,hashes=prepare()
 cuts=[0,len(times)//3,2*len(times)//3,len(times)]
 out={"title":"P1 #13 shared 1H portfolio: forming vs closed fade vs frozen turn",
  "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
  "producer_sha":os.environ.get("GITHUB_SHA","local"),
  "source_sha256":hashes,"config":CONFIG,"config_sha256":CONFIG_HASH,
  "caveats":["ALL cached history previously inspected: no independent OOS",
   "Synthetic adverse funding 00/08/16 UTC, not venue rates",
   "Hourly close MTM DD, not tick/intrahour DD",
   "Identical entry/exit/risk mechanics; frozen_turn signal has completed-signal ATR while fade uses previous completed ATR",
   "No venue-provenance, order-book spread, mark-price liquidation, actual fills or market impact",
   "Shared portfolio excludes HYPE; HYPE remains separate negative control in causal_4h_parity_audit.json"],
  "full":{},"windows":[]}
 for mode in ("forming","closed","frozen_turn"):
  grid={}
  for c in COSTS:
   for f in FUNDING:
    key=f"{round(c*10000)}bp_cost_{round(f*10000)}bp_funding"
    grid[key]=metrics(simulate(data,times,mode,c,f))
  out["full"][mode]={"primary":grid["15bp_cost_3bp_funding"],"stress":grid}
 for j in range(3):
  chunk=times[cuts[j]:cuts[j+1]]
  w={"index":j+1,"start_utc":iso(chunk[0]),"end_utc":iso(chunk[-1]+H),
   "modes":{}}
  for mode in ("forming","closed","frozen_turn"):
   w["modes"][mode]=metrics(simulate(data,chunk,mode,.0015,.0003))
  out["windows"].append(w)
 path=Path("reports/causal_4h_portfolio_audit.json")
 path.write_text(json.dumps(out,indent=2,ensure_ascii=False))
 print(json.dumps({"config_sha":CONFIG_HASH,
  "full":{k:v["primary"] for k,v in out["full"].items()},
  "windows":[{"index":w["index"],"returns":{m:v["net_return_pct"] for m,v in w["modes"].items()}} for w in out["windows"]]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
