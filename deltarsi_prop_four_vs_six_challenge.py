"""Compare 4-asset baseline against 6 assets on identical history and challenge windows.
New BNB/ZEC use untuned 5 ATR SL/TP with no trailing; max 3 concurrent positions.
"""
import json,datetime as dt
from pathlib import Path
import deltarsi_prop_four_assets_challenge_windows as base
from causal_4h_parity_audit import load,events,H
DAY=24*H
FOUR=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT")
SIX=FOUR+("BNBUSDT","ZECUSDT")
for sym in ("BNBUSDT","ZECUSDT"):
 raw,sha=load(sym)
 base.DATA[sym]={r[0]:r[1:] for r in raw}
 base.HASHES[sym]=sha
 ev,_=events(raw)
 base.SIGNALS[sym]={e["entry_ms"]:e for e in ev["closed"]}
base.PARAM.update({"BNBUSDT":(None,None),"ZECUSDT":(None,None)})
shared=set.intersection(*(set(base.DATA[sym]) for sym in SIX))
if not shared:raise ValueError("No common six-asset hourly history")
start=min(shared);end=max(shared)
if any(t not in shared for t in range(start,end+H,H)):raise ValueError("Six-asset history has gaps")
out=dict(description="Research: same historical start windows; BNB/ZEC default no trailing, SL/TP 5 ATR; 3 concurrent positions; no slippage; weekly rolling overlapping windows; targets 5/8%; 14/30 days.",shared_start=dt.datetime.fromtimestamp(start/1000,dt.timezone.utc).isoformat(),shared_end=dt.datetime.fromtimestamp((end+H)/1000,dt.timezone.utc).isoformat(),models={})
for fee_name,fee,funding in [("upscale_basic",.00008,.00015),("prior",.00075,.0003)]:
 out["models"][fee_name]={}
 for days in (14,30):
  for target in (5,8):
   result={}
   for label,syms in [("four",FOUR),("six",SIX)]:
    base.SYMS=syms
    base.COMMON=set.intersection(*(set(base.DATA[sym]) for sym in syms))
    trials=[]
    for t in range(start,end-days*DAY+2*H,7*DAY):
     if any(x not in shared for x in range(t,t+days*DAY,H)):continue
     r=base.simulate(t,t+days*DAY-H,target,fee,funding)
     trials.append({k:r[k] for k in ("start_utc","outcome","days_elapsed","return_pct","max_dd_pct","closed_trades","first_breach")})
    counts={k:sum(r["outcome"]==k for r in trials) for k in ("pass","breach","timeout")}
    result[label]={"trials":len(trials),"counts":counts,"pass_rate_pct":round(100*counts["pass"]/len(trials),2) if trials else None,"results":trials}
   out["models"][fee_name][f"{days}d_target_{target}pct"]=result
   print(fee_name,days,target,[(x,result[x]["counts"]) for x in ("four","six")],flush=True)
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_prop_four_vs_six_challenge.json").write_text(json.dumps(out,indent=2))
