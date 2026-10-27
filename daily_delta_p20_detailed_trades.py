"""Export fully reproducible 1D DeltaRSI trades with 20-day strength lookback.

Detailed post-hoc diagnostics for the daily follow-up, NOT independently
verified OOS or a live trading recommendation. Binance USD-M futures daily
data, 0.15% cost, structural stop, no funding. All entries after candle close.
"""
import csv
import json
from pathlib import Path
from analyze_mtf_5y import indicator
from daily_delta_percentile_window_sensitivity import load,percentile
from daily_original_delta_percentile_backtest import candidates,simulate,stats,walkforward_by_entry

OUT=Path("reports")
COLUMNS=[
    "symbol","signal_mode","exit_mode","position_mode","strength_window_days",
    "strength_percentile_cutoff","signal_date_utc","entry_date_utc","exit_date_utc",
    "direction","entry","stop","exit","initial_risk_pct","net_pct","net_r",
    "bars_held","reason","strength_percentile","delta_prev_abs","delta_signal_abs"
]

def main():
    logs=[];summary=[]
    for symbol in ("BTCUSDT","ETHUSDT"):
        bars=load(symbol);ind=indicator(bars)
        for mode in ("color","first_fade"):
            raw,_=candidates(bars,ind,mode)
            signals=[]
            for event in raw:
                rank=percentile(ind,event["index"],20)
                if rank is not None:signals.append({**event,"strength_percentile":rank})
            for exitmode in ("opposite_only","rebrighten_plus_opposite"):
                for direction,name in ((None,"both"),(1,"long_only"),(-1,"short_only")):
                    trades,issues=simulate(bars,ind,signals,.8,mode,exitmode,
                                           "confirmed_pivot",only_side=direction)
                    for t in trades:
                        logs.append({
                            "symbol":symbol,"signal_mode":mode,
                            "exit_mode":exitmode,"position_mode":name,
                            "strength_window_days":20,
                            "strength_percentile_cutoff":80,
                            **t})
                    summary.append({
                        "symbol":symbol,"signal_mode":mode,"exit_mode":exitmode,
                        "position_mode":name,
                        "all_history":stats(trades),
                        "chronological":walkforward_by_entry(bars,trades),
                        "diagnostics":issues,
                    })
    OUT.mkdir(exist_ok=True)
    path=OUT/"daily_delta_p20_detailed_trades.csv"
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS,extrasaction="ignore")
        w.writeheader()
        w.writerows(logs)
    meta={"description":"Selected diagnostic daily DeltaRSI trade logs with 20-day percentile>=80.",
          "research_status":"Exploratory, parameter/lookback chosen after earlier results were inspected. Not independent OOS.",
          "data":"Binance USD-M futures 1D BTCUSDT/ETHUSDT, daily candles 00 UTC. Previous-month archives cached in data/.",
          "entry":"Next daily open after completed DeltaRSI medium->weak OR first fading impulse, as shown in signal_mode.",
          "exit":"Next-day open on opposite fade or optionally impulse rebrightening; initial confirmed swing pivot with 0.1% buffer and gap-aware stop; 90d safety timeout.",
          "assumed_fee_pct":.15,"funding_included":False,
          "trade_rows":len(logs),"summary":summary}
    (OUT/"daily_delta_p20_detailed_trades_summary.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps({"rows":len(logs),"summary":[{"symbol":x["symbol"],
            "signal_mode":x["signal_mode"],"exit_mode":x["exit_mode"],
            "position_mode":x["position_mode"],"n":x["all_history"]["n"],
            "mean":x["all_history"].get("mean_net_pct"),
            "pf":x["all_history"].get("profit_factor")}
            for x in summary]},indent=2))

if __name__=="__main__":
    main()
