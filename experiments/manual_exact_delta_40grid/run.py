"""True manual DeltaRSI entry color transitions; reuse frozen 40-grid exit/account engine.
On CLOSED 4h candles: medium red -> weak red LONG; medium blue -> weak blue SHORT.
Optional bright->weak observed in 1/30 manual entries, separately switchable.
No min amplitude, ratio, local max, volume, wave, 1h confirmation or lookahead.
"""
import sys,argparse,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from analyze_mtf_5y import indicator
from experiments.no_take_extreme_stop_ttl_grid.run import (
 ASSETS,ACCOUNTS,STOPS,HOURS,START,VALID_END,END,H,source_load,
 ohlc_from_5m,make_extreme_signals,sim_extrema,concise,iso,synthetic_units)
from experiments.new_instructions_8asset_48h.backtest import check_document
BASE=Path("experiments/manual_exact_delta_40grid")
def manual_color_events(hourly,include_bright=False):
 bars=ohlc_from_5m(hourly,4*H) if isinstance(hourly,dict) else hourly
 ind=indicator(bars)
 colors=ind["color"];delta=ind["delta"]
 ev={}
 for i in range(210,len(bars)):
  prev=colors[i-1];cur=colors[i]
  side=(1 if cur=="weakR" and prev in (("mediumR","strongR") if include_bright else ("mediumR",))
        else -1 if cur=="weakB" and prev in (("mediumB","strongB") if include_bright else ("mediumB",)) else None)
  if side is None:continue
  assert math.isfinite(delta[i]) and math.isfinite(delta[i-1])
  t=bars[i][0]+4*H
  ev[t]=dict(side=side,atr_4h=0.,delta=delta[i],prior_delta=delta[i-1],
             color=cur,prior_color=prev,signal_kind="bright_to_weak" if prev.startswith("strong") else "medium_to_weak")
 return ev
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--account",required=True,choices=sorted(ACCOUNTS))
 p.add_argument("--period",default="annual",choices=("annual","q2"))
 p.add_argument("--include-bright-to-weak",action="store_true")
 a=p.parse_args()
 synthetic_units();check_document()
 raw,_,manifest=source_load()
 signals={}
 for asset in ASSETS:
  bars=ohlc_from_5m(sorted(raw[asset].values()),4*H)
  basic=manual_color_events(bars,a.include_bright_to_weak)
  signals[asset]=make_extreme_signals(raw[asset],basic)
  print("MANUAL_EXACT_INPUT",asset,len(basic),flush=True)
 start,end=(START,END) if a.period=="annual" else (VALID_END,END)
 acc=ACCOUNTS[a.account]
 results={}
 for n in STOPS:
  for h in HOURS:
   s,details=sim_extrema(raw,signals,ASSETS,acc,start,end,n,h,
     payouts_enabled=acc["kind"]!="personal",details=True)
   key=f"stop{n}_hold{h}"
   results[key]=dict(summary=s,details=details)
   print("MANUAL_EXACT_GRID",a.account,a.period,key,json.dumps(concise(s),ensure_ascii=False),flush=True)
 out=dict(account=a.account,period=a.period,start=iso(start),end=iso(end),
  signal_rule="strict mediumR->weakR LONG, mediumB->weakB SHORT on fully closed 4h" + (" plus strong->weak direct transition" if a.include_bright_to_weak else ""),
  no_extra_signal_filters=True,include_bright_to_weak=a.include_bright_to_weak,
  input_events={s:len(v) for s,v in signals.items()},results=results,
  caveats=["Actual repo Pine executable uses SMA21 RSI12 EMA7 symmetric log; textual RSI27 is inconsistent. No independent TV parity certified.",
   "Manual trades 28/30 medium->weak; 1/30 bright->weak; 1/30 medium color in forensic check.",
   "Historical selection includes all signals when slots available; manual user trades intermittently, so number of bot trades differs.",
   "40-grid uses same six assets, 5m candles, account and fee model as previous test.",
   "In-sample grid; not forward-tested; no real trades."])
 dest=BASE/a.account/a.period/("bright_allowed" if a.include_bright_to_weak else "strict")/"results.json"
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
 print("MANUAL_EXACT_FINISHED",a.account,a.period,len(results),str(dest),flush=True)
if __name__=="__main__":main()
