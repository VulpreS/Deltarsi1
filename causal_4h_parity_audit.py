"""P1 #13: causal 1H-close snapshots of forming 4H DeltaRSI.
Read-only cached OHLC. Exploratory history, never independent OOS or live orders.
"""
import csv,datetime as dt,hashlib,json,math,os,random,statistics
from collections import defaultdict
from pathlib import Path
from analyze_mtf_5y import indicator
from feature_walkforward import features_for_rows
from completed_candles import aggregate_completed
from research_multiasset import atr
from execution_core import resolve_bar
from funding_timing import exposure_bounds,HOUR_MS
H=HOUR_MS; FOUR=4*H
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
COSTS=(.0015,.0025,.004)
FUNDING=(0.,.0001,.0003)
RATIO=.7; MIN_PEAK=15.
SL_ATR=2.5; TP_ATR=3.; HOLD_HOURS=48
RISK=.0025; MAX_NOTIONAL=1.
SEED=20261027
PARAMS=dict(ratio_max=RATIO,prior_peak_min=MIN_PEAK,peak_requires_previous_nonrising=True,
            sl_4h_atr=SL_ATR,tp_4h_atr=TP_ATR,hold_hours=HOLD_HOURS,
            risk_fraction=RISK,max_symbol_notional_to_equity=MAX_NOTIONAL,
            costs=COSTS,synthetic_funding=FUNDING,seed=SEED)
PARAM_HASH=hashlib.sha256(json.dumps(PARAMS,sort_keys=True).encode()).hexdigest()
def iso(ms):return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).isoformat()
def load(sym):
 p=Path("data")/(sym+"_1h.csv")
 if not p.exists():raise FileNotFoundError("Cached 1H missing: "+str(p))
 with p.open() as f:
  rows=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),
         *[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
 if any(b[0]-a[0]!=H for a,b in zip(rows,rows[1:])):raise ValueError("Gap or duplicate 1H: "+sym)
 return rows,hashlib.sha256(p.read_bytes()).hexdigest()
class CausalDelta:
 """Exact streaming implementation of canonical indicator; partial observations do not commit."""
 def __init__(self):
  self.closes=[];self.smas=[];self.rolling=0.;self.ag=0.;self.al=0.
  self.ema=math.nan;self.delta=math.nan;self.prev_delta=math.nan
 def step(self,close,commit=False):
  i=len(self.closes);rolling=self.rolling+close
  if i>=21:rolling-=self.closes[i-21]
  s=rolling/21 if i>=20 else math.nan
  ag=self.ag;al=self.al;ema=self.ema;d=math.nan;r=math.nan;color=""
  if i>=32:
   change=s-self.smas[-1]
   if i==32:
    ag=al=0.
    for j in range(21,32):
     v=self.smas[j]-self.smas[j-1];ag+=max(0,v)/12;al+=max(0,-v)/12
    ag+=max(0,change)/12;al+=max(0,-change)/12
   else:
    ag=(ag*11+max(0,change))/12;al=(al*11+max(0,-change))/12
   r=100 if al==0 else (0 if ag==0 else 100-100/(1+ag/al))
   ema=r if math.isnan(ema) else ema*.75+r*.25
   a=100-r if r>50 else r;b=100-ema if ema>50 else ema
   if a>0 and b>0:
    d=(1 if r>ema else -1)*abs(math.log(a/b)*100)
    ab=abs(d);prev=abs(self.delta)
    if d>0:color="strongB" if ab>60 and d>self.delta else ("mediumB" if ab>60 or ab>prev else "weakB")
    elif d<0:color="strongR" if ab>60 and d<self.delta else ("mediumR" if ab>60 or ab>prev else "weakR")
  if commit:
   self.closes.append(close);self.smas.append(s);self.rolling=rolling
   self.ag=ag;self.al=al;self.ema=ema;self.prev_delta=self.delta;self.delta=d
  return d,color,r
def qualifying(prev,prevprev,cur):
 if not all(math.isfinite(x) for x in (prev,prevprev,cur)):return False
 return prev*cur>0 and abs(prev)>=MIN_PEAK and abs(prev)>=abs(prevprev) and abs(cur)<=RATIO*abs(prev)
def events(raw):
 rows=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
 f=features_for_rows(rows);av=atr(rows)
 hourly={r[0]:j for j,r in enumerate(raw)}
 state=CausalDelta();out={"forming":[],"closed":[],"frozen_turn":[]}
 for i,b in enumerate(rows):
  start=b[0];parts=[raw[hourly[start+h*H]] for h in range(4) if start+h*H in hourly]
  if len(parts)!=4:raise ValueError("Incomplete 4H bucket "+iso(start))
  prev=state.delta;prevprev=state.prev_delta
  if i>=210:
   early=None
   for h in range(1,5):
    part=parts[:h]
    d,color,rsi=state.step(part[-1][4],commit=False)
    if not qualifying(prev,prevprev,d):continue
    j=hourly[start+(h-1)*H];decision=start+h*H
    event=dict(bucket_utc=iso(start),bucket_ms=start,decision_utc=iso(decision),
      decision_ms=decision,entry_utc=iso(decision),entry_ms=decision,
      entry_i=j+1,partial_hours=h,prior_4h_delta=prev,
      prior_prior_4h_delta=prevprev,forming_delta=d,color=color,
      ratio=abs(d)/abs(prev),side=1 if prev<0 else -1,
      atr_4h=av[i-1],atr_asof_utc=iso(start),
      prior_complete_4h_close_utc=iso(start),mode="forming" if h<4 else "closed")
    if h<4 and early is None:early=event
    if h==4:out["closed"].append(event)
   if early:out["forming"].append(early)
   if f[i] and f[i]["turn"]:
    out["frozen_turn"].append(dict(bucket_utc=iso(start),bucket_ms=start,
      decision_utc=iso(start+FOUR),decision_ms=start+FOUR,
      entry_utc=iso(start+FOUR),entry_ms=start+FOUR,
      entry_i=hourly[start+3*H]+1,partial_hours=4,
      side=f[i]["side"],atr_4h=f[i]["atr"],mode="frozen_turn"))
  state.step(b[4],commit=True)
 return out,rows
def trade(raw,e,cost,rate,eq=1.,reverse=False,terminal=None):
 i=e["entry_i"]
 if i>=len(raw) or (terminal is not None and raw[i][0]>=terminal):return None
 side=-e["side"] if reverse else e["side"]
 entry=raw[i][1];a=e["atr_4h"]
 if not math.isfinite(a) or a<=0 or entry<=0:return None
 stop=entry-side*SL_ATR*a;target=entry+side*TP_ATR*a
 if stop<=0 or target<=0:return None
 qty=min(RISK*eq/abs(entry-stop),MAX_NOTIONAL*eq/entry)
 if qty<=0:return None
 fee_in=qty*entry*cost/2
 end=min(i+HOLD_HOURS-1,len(raw)-1)
 if terminal is not None:
  while end>=i and raw[end][0]>=terminal:end-=1
 if end<i:return None
 exit_price=raw[end][4];exit_i=end;reason="time"
 for j in range(i,end+1):
  fill,why=resolve_bar(raw[j],side,stop,target)
  if why:exit_price=fill;exit_i=j;reason=why;break
 earliest=raw[exit_i][0] if reason!="time" else raw[exit_i][0]+H
 latest=raw[exit_i][0]+H
 funding=qty*entry*rate*exposure_bounds(raw[i][0],earliest,latest)["funding_events_max"]
 gross=side*qty*(exit_price-entry);fees=fee_in+qty*exit_price*cost/2
 net=gross-fees-funding
 return dict(bucket_ms=e["bucket_ms"],entry_ms=raw[i][0],entry_i=i,exit_i=exit_i,
   exit_utc=iso(latest),side=side,reason=reason,entry=entry,exit=exit_price,
   risk_cash=qty*abs(entry-stop),gross=gross,fees=fees,funding=funding,
   net=net,net_R=net/(qty*abs(entry-stop)),net_pct_equity=100*net/eq)
def execute(raw,es,cost,rate,start=0,end=None,reverse=False):
 end=len(raw) if end is None else end
 # Separate chronological windows with equity reset; signals must originate inside window.
 eq=1.;trades=[];until=-1;skipped=defaultdict(int)
 for e in es:
  i=e["entry_i"]
  if i<start or i>=end:continue
  if i<=until:skipped["occupied_or_exit_bar"]+=1;continue
  t=trade(raw,e,cost,rate,eq,reverse,raw[end-1][0]+H)
  if t is None:skipped["invalid_or_terminal"]+=1;continue
  eq+=t["net"];trades.append(t);until=t["exit_i"]
 return dict(trades=trades,equity=eq,skips=dict(skipped))
def metrics(run):
 tr=run["trades"];vals=[x["net"] for x in tr];p=sum(max(0,v) for v in vals);l=-sum(min(0,v) for v in vals)
 # Closed-trade equity DD, NOT intrabar mark-to-market DD.
 equity=1.;peak=1.;dd=0.
 for x in tr:
  equity+=x["net"];peak=max(peak,equity);dd=max(dd,1-equity/peak)
 return dict(n=len(tr),net_return_pct=round(100*(run["equity"]-1),4),
   pf=round(p/l,4) if l else None,
   win_pct=round(100*sum(v>0 for v in vals)/len(vals),2) if vals else None,
   mean_R=round(statistics.mean(x["net_R"] for x in tr),4) if tr else None,
   closed_trade_dd_pct=round(100*dd,4),skips=run["skips"])
def matched(raw,forming,closed,cost=.0015,rate=.0003):
 by={(e["bucket_ms"],e["side"]):e for e in closed}
 pairs=[]
 for e in forming:
  c=by.get((e["bucket_ms"],e["side"]))
  if c is None:continue
  x=trade(raw,e,cost,rate);y=trade(raw,c,cost,rate)
  if x and y:pairs.append(dict(bucket_ms=e["bucket_ms"],side=e["side"],
   forming=x["net_pct_equity"],closed=y["net_pct_equity"],
   diff_pp=x["net_pct_equity"]-y["net_pct_equity"],
   early_decision_utc=e["decision_utc"],closed_decision_utc=c["decision_utc"]))
 return pairs
def block_ci(pairs):
 if not pairs:return None
 groups=defaultdict(list)
 for p in pairs:groups[p["bucket_ms"]//(30*24*H)].append(p["diff_pp"])
 keys=sorted(groups)
 if len(keys)<3:return dict(blocks=len(keys),ci_95_pp=None)
 rng=random.Random(SEED);draw=[]
 for _ in range(1200):
  sample=[v for _ in keys for v in groups[rng.choice(keys)]]
  draw.append(statistics.mean(sample))
 draw.sort()
 return dict(blocks=len(keys),ci_95_pp=[round(draw[30],5),round(draw[1169],5)])
def main():
 report=dict(title="P1 #13 causal forming-vs-closed 4H, cached-only exploratory",
   generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
   producer_sha=os.environ.get("GITHUB_SHA","local"),ci_run=os.environ.get("GITHUB_RUN_ID","local"),
   config=PARAMS,config_sha256=PARAM_HASH,assets={},
   warnings=["All historical periods previously inspected; NO independent OOS.",
     "OHLC 1H stop-first; adverse gap at open; unknown intrahour execution and real funding.",
     "Funding adverse synthetic 00/08/16 UTC upper bound; costs 15/25/40bp assumed.",
     "Independent per-asset schedules, NOT a portfolio with cross-asset capital competition.",
     "Closed-trade DD understates possible intrabar/mark-to-market DD.",
     "Forming and closed signal cohorts differ; matched pairs overlap and are NOT executable portfolio.",
     "Forming/closed fade uses previous COMPLETED 4H ATR for exact causal parity; frozen turn uses signal-bar completed 4H ATR.",
     "Frozen turn baseline uses 1H execution, 48h hold and no same-exit-hour reentry; may differ from 4H portfolio engine."])
 for sym in SYMS:
  raw,sha=load(sym);ev,rows=events(raw)
  # strict chronological thirds, reset and terminal close per window.
  cuts=[0,len(raw)//3,2*len(raw)//3,len(raw)]
  asset=dict(source_sha256=sha,hourly_n=len(raw),complete_4h_n=len(rows),
    start_utc=iso(raw[0][0]),end_utc=iso(raw[-1][0]+H),
    signal_counts={k:len(v) for k,v in ev.items()},first_event_samples={k:v[:3] for k,v in ev.items()},
    regimes=[],primary={},cost_funding_grid={},matched={})
  for mode in ("forming","closed","frozen_turn"):
   es=ev[mode];grid={}
   for c in COSTS:
    for f in FUNDING:
     key=f"{round(c*10000)}bp_cost_{round(f*10000)}bp_funding"
     grid[key]=metrics(execute(raw,es,c,f))
   asset["cost_funding_grid"][mode]=grid
   asset["primary"][mode]=grid["15bp_cost_3bp_funding"]
  for j in range(3):
   window=dict(window=j+1,start_utc=iso(raw[cuts[j]][0]),end_utc=iso(raw[cuts[j+1]-1][0]+H),modes={})
   for mode in ("forming","closed","frozen_turn"):
    window["modes"][mode]=metrics(execute(raw,ev[mode],.0015,.0003,cuts[j],cuts[j+1]))
    window["modes"][mode]["by_side"]={}
    for side,label in ((1,"LONG"),(-1,"SHORT")):
     # Side-only schedule is diagnostic, not the executable all-side schedule.
     side_events=[e for e in ev[mode] if e["side"]==side]
     window["modes"][mode]["by_side"][label]=metrics(execute(raw,side_events,.0015,.0003,cuts[j],cuts[j+1]))
   asset["regimes"].append(window)
  pairs=matched(raw,ev["forming"],ev["closed"])
  asset["matched"]={"n":len(pairs),"mean_early_minus_closed_pp":round(statistics.mean(x["diff_pp"] for x in pairs),5) if pairs else None,
    "bootstrap":block_ci(pairs),"by_side":{label:{"n":len([x for x in pairs if x["side"]==side]),
      "mean_diff_pp":round(statistics.mean(x["diff_pp"] for x in pairs if x["side"]==side),5) if any(x["side"]==side for x in pairs) else None}
      for side,label in ((1,"LONG"),(-1,"SHORT"))},
    "sample_pairs":pairs[:5]}
  # Negative control: invert the side on exactly the same forming signal timestamps.
  asset["negative_control_reversed_forming"]=metrics(execute(raw,ev["forming"],.0015,.0003,reverse=True))
  # 0% cash baseline. Buy/hold not risk-matched; only contextual.
  first=raw[0][1];last=raw[-1][4]
  asset["cash_return_pct"]=0.
  asset["buyhold_price_only_15bp_pct"]=round(100*((last/first)*(1-.0015/2)**2-1),4)
  report["assets"][sym]=asset
  print(sym,asset["signal_counts"],{k:v["net_return_pct"] for k,v in asset["primary"].items()},
        "matched",asset["matched"]["n"],flush=True)
 path=Path("reports/causal_4h_parity_audit.json")
 path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("WROTE",path,PARAM_HASH,flush=True)
if __name__=="__main__":main()
