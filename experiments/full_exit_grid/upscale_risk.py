"""Independent Upscale-style risk audit for full_exit_grid; research only.
Single-asset scenarios with $1500/$3000 fixed notional; NOT multi-asset portfolio.
Hourly adverse equity check, daily reset 00:00 UTC; stop-first fills.
"""
import sys,json,math,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H
from experiments.full_exit_grid.run import SYMS,SL_MODES,TP_MODES,COST,HOLD,levels
DAY=24*H;INITIAL=5000.
def audit(raw,signals,sm,tm,be,notional):
 cash=INITIAL;peak=INITIAL;maxdd=0.;day=None;daybase=INITIAL;daily_worst=0.;pos=None
 count=0;wins=0;losses=0;streak=0;maxstreak=0;stops=0;breach=None;first_breach=None
 signals={e["entry_ms"]:e for e in signals}
 for i,(t,o,h,l,c) in enumerate(raw):
  if t//DAY!=day:
   day=t//DAY
   daybase=cash+(pos["side"]*pos["qty"]*(o-pos["entry"])-pos["qty"]*o*COST/2 if pos else 0)
  if pos is None and t in signals:
   e=signals[t];atr=e["atr_4h"];side=e["side"]
   if math.isfinite(atr) and atr>0 and o>0:
    sl,tp=levels(o,atr,side,sm,tm)
    if min(sl,tp)>0:
     qty=notional/o
     cash-=notional*COST/2
     pos=dict(entry=o,side=side,qty=qty,stop=sl,tp=tp,trigger=o*(1+side*.01),
              activated=False,entry_i=i,entry_fee=notional*COST/2)
  if pos:
   z=pos;side=z["side"];qty=z["qty"];entry=z["entry"];sl=z["stop"];tp=z["tp"]
   # Adverse extreme before a possible exit. Conservative equity risk stress.
   adverse=min(o,l) if side==1 else max(o,h)
   if (l<=sl if side==1 else h>=sl):
    adverse=min(adverse,sl) if side==1 else max(adverse,sl)
   worst=cash+side*qty*(adverse-entry)-qty*adverse*COST/2
   maxdd=max(maxdd,(peak-worst)/peak*100)
   daily_worst=max(daily_worst,daybase-worst)
   if worst<=daybase*.95 or worst<=INITIAL*.90:
    breach="daily" if worst<=daybase*.95 else "total"
    first_breach=t
    break
   stop_gap=(o<=sl if side==1 else o>=sl)
   tp_gap=(o>=tp if side==1 else o<=tp)
   stop_hit=(l<=sl if side==1 else h>=sl)
   tp_hit=(h>=tp if side==1 else l<=tp)
   px=None;reason=None
   if stop_gap: px=o;reason="stop"
   elif tp_gap: px=o;reason="target"
   elif stop_hit: px=sl;reason="stop"
   elif tp_hit: px=tp;reason="target"
   elif be and not z["activated"] and (h>=z["trigger"] if side==1 else l<=z["trigger"]):
    z["activated"]=True;z["stop"]=entry
    if l<=entry if side==1 else h>=entry: px=entry;reason="be"
   if px is None and i-z["entry_i"]>=HOLD-1: px=c;reason="time"
   if px is not None:
    net=side*qty*(px-entry)-qty*px*COST/2-z["entry_fee"]
    cash+=side*qty*(px-entry)-qty*px*COST/2
    count+=1
    if net>0: wins+=1;streak=0
    else: losses+=1;streak+=1;maxstreak=max(maxstreak,streak)
    if reason=="stop":stops+=1
    pos=None
  closeeq=cash+(pos["side"]*pos["qty"]*(c-pos["entry"])-pos["qty"]*c*COST/2 if pos else 0)
  peak=max(peak,closeeq)
  if closeeq<=daybase*.95 or closeeq<=INITIAL*.90:
   breach="daily" if closeeq<=daybase*.95 else "total";first_breach=t;break
 return dict(trades=count,wins=wins,losses=losses,stop_count=stops,max_losing_streak=maxstreak,
   return_pct=round((cash/INITIAL-1)*100,3),max_intrabar_dd_pct=round(maxdd,3),
   max_daily_equity_loss_usd=round(daily_worst,2),breach=breach,breach_utc_ms=first_breach,
   survived=breach is None,position_open_at_end=pos is not None)

def main():
 out=dict(title="Upscale-style 5% daily / 10% total stop-on-breach audit",
  rules=dict(initial_usd=5000,daily_pct=5,total_pct=10,reset="00:00 UTC",
    daily_reference="equity at first hourly open of UTC day",total_reference="initial balance",
    notional_per_trade_usd=[1500,3000]),
  limitations=["Single asset per independent account; BTC/ETH concurrent portfolio not yet simulated.",
    "Hourly OHLC adverse mark and stop-first, not tick-accurate or broker mark-price.",
    "Risk check uses hourly worst extreme even if TP might have filled earlier: conservative.",
    "Daily and total drawdown bases are assumptions pending Upscale rule verification.",
    "No stage resets, payouts, qualifying day targets or funding; no independent holdout.",
    "Research only; no real orders."],results={})
 for sym in SYMS:
  raw,sha=load(sym);es,_=events(raw)
  d=dict(data_sha=sha,variants={})
  for sm,tm,be,notional in itertools.product(SL_MODES,TP_MODES,(False,True),(1500,3000)):
   key=f"sl_{sm[0]}_{sm[1]:g}__tp_{tm[0]}_{tm[1]:g}__be_{int(be)}__size_{notional}"
   d["variants"][key]=audit(raw,es["closed"],sm,tm,be,notional)
  out["results"][sym]=d
  for size in (1500,3000):
   pairs=[(k,v) for k,v in d["variants"].items() if k.endswith(f"size_{size}")]
   survived=sum(v["survived"] for k,v in pairs)
   print(sym,"notional",size,"survived",survived,"of",len(pairs),
         "top_survivors",sorted([(k,v["return_pct"]) for k,v in pairs if v["survived"]],key=lambda z:z[1],reverse=True)[:5],flush=True)
 p=Path("experiments/full_exit_grid/upscale_risk_results.json");p.write_text(json.dumps(out,indent=2))
if __name__=="__main__":main()
