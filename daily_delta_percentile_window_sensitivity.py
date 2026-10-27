"""Diagnostic: daily DeltaRSI 'strong impulse' window 10 vs 20 vs 60 days.

The source 4H study used 60 * 4H = 10 calendar days. On daily candles
using 60 bars means TWO MONTHS, not ten days. Compare both definitions
without choosing an optimized winner. These are sensitivity checks designed
after inspecting earlier results and are NOT independent validation.
"""
import csv
import json
import math
import statistics
from pathlib import Path
from analyze_mtf_5y import indicator
from daily_original_delta_percentile_backtest import (
    candidates,simulate,stats,walkforward_by_entry
)
DATA=Path("data")
OUT=Path("reports/daily_delta_percentile_window_sensitivity.json")
PCTS=(.8,.9)
WINDOWS=(10,20,60)
SYMBOLS=("BTCUSDT","ETHUSDT")

def load(sym):
    with (DATA/f"{sym}_1d_binance_um.csv").open() as f:
        return [(int(r["open_ms"]),*[float(r[k]) for k in ("open","high","low","close")])
                for r in csv.DictReader(f)]

def percentile(ind,i,lookback):
    data=ind["delta"]
    if i<lookback+2 or not math.isfinite(data[i-1]):return None
    target=abs(data[i-1])
    recent=[abs(data[j]) for j in range(i-lookback-1,i-1) if math.isfinite(data[j])]
    if len(recent)<max(7,math.ceil(lookback*2/3)):return None
    return (sum(z<target for z in recent)+sum(z==target for z in recent)*.5)/len(recent)

def main():
    out={
      "research":"Same DeltaRSI signals, change ONLY historic strength lookback: 10d / 20d / 60d",
      "notes":[
        "60 x 4H candles = 10 calendar days, but 60 x 1D candles = 60 calendar days; source of timeframe sensitivity.",
        "Window comparisons were added AFTER seeing negative 60-day percentile backtests. Not pristine OOS. Report every attempted window.",
        "Same 1D cached Binance USD-M BTC and ETH bars, unchanged Pine-like DeltaRSI, 0.15% assumed costs.",
        "Entry after daily close; confirmed swing stop, next open exits, signal invalidation examined separately; no funding or real trades.",
        "Strength threshold 80th or 90th percentile pre-existing hypotheses; no optimization performed here.",
        "Historical percentile excludes current candle and the preceding impulse candle being ranked.",
        "All daily backtest limitations and data provenance are detailed in daily_original_delta_percentile_backtest.json."
      ],
      "by_asset":{}
    }
    for sym in SYMBOLS:
        rows=load(sym);ind=indicator(rows);variants={}
        for mode in ("color","first_fade"):
            original,_=candidates(rows,ind,mode)
            for lookback in WINDOWS:
                updated=[]
                for e in original:
                    p=percentile(ind,e["index"],lookback)
                    if p is not None:
                        updated.append({**e,"strength_percentile":p})
                for cutoff in PCTS:
                    for exit_mode in ("opposite_only","rebrighten_plus_opposite"):
                        key=f"{mode}_p{int(cutoff*100)}_lookback{lookback}_{exit_mode}"
                        trades,diag=simulate(rows,ind,updated,cutoff,mode,exit_mode,"confirmed_pivot")
                        dirsolo={}
                        for side,name in ((1,"LONG"),(-1,"SHORT")):
                            solotrades,_=simulate(rows,ind,updated,cutoff,mode,exit_mode,"confirmed_pivot",only_side=side)
                            dirsolo[name]={"all_history":stats(solotrades),
                                "recent_20pct":walkforward_by_entry(rows,solotrades)["recent_20pct"]["statistics"]}
                        variants[key]={"lookback_days":lookback,"cutoff":cutoff,"entry_mode":mode,"exit_mode":exit_mode,
                            "eligible_signals":sum(x["strength_percentile"]>=cutoff for x in updated),
                            "combined":{"all_history":stats(trades),
                              "recent_20pct":walkforward_by_entry(rows,trades)["recent_20pct"]["statistics"],
                              "diagnostics":diag},
                            "single_direction_only":dirsolo}
        out["by_asset"][sym]={"n_daily_bars":len(rows),"variants":variants}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    compact={}
    for sym,z in out["by_asset"].items():
        compact[sym]=[]
        for mode in ("color","first_fade"):
            for lookback in WINDOWS:
                for cutoff in PCTS:
                    key=f"{mode}_p{int(cutoff*100)}_lookback{lookback}_rebrighten_plus_opposite"
                    r=z["variants"][key]
                    compact[sym].append({"mode":mode,"window":lookback,"cutoff":cutoff,
                        "sig":r["eligible_signals"],
                        "n":r["combined"]["all_history"]["n"],
                        "mean":r["combined"]["all_history"].get("mean_net_pct"),
                        "pf":r["combined"]["all_history"].get("profit_factor"),
                        "recent_n":r["combined"]["recent_20pct"]["n"],
                        "recent_mean":r["combined"]["recent_20pct"].get("mean_net_pct"),
                        "recent_pf":r["combined"]["recent_20pct"].get("profit_factor")})
    print(json.dumps(compact,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
