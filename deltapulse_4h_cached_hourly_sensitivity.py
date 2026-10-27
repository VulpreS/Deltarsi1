"""DeltaPulse 4H sensitivity to cached 1H source candles, including HYPE/ICP.

Inputs are the repository's already cached hourly OHLC, with no guarantee
their exchange provenance is documented in the CSV itself. Each 4H candle is
built from four fully closed consecutive UTC hours. Compare BTC/ETH with the
fresh Binance USD-M 4H archive on overlapping timestamps, including indicator
sign/color differences and strategy returns. Never fill missing data holes.
"""
import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path

from completed_candles import aggregate_completed
from analyze_mtf_5y import indicator
from deltapulse_4h_archive import read_cache,H4
from deltapulse_4h_strategy_v1 import candidates,replay,metrics,utc

OUT=Path("reports/deltapulse_4h_cached_hourly_sensitivity.json")
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
H=3_600_000

def load_hourly(symbol):
    with (Path("data")/f"{symbol}_1h.csv").open() as f:
        rows=[(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),
            *[float(r[k]) for k in ("open","high","low","close")])
            for r in csv.DictReader(f)]
    if len(rows)<1500:raise ValueError(symbol)
    if any(x[0]%H for x in rows):raise ValueError("non UTC hour")
    if any(b[0]<=a[0] for a,b in zip(rows,rows[1:])):raise ValueError("out of order hourly data")
    asof=rows[-1][0]+H
    bars=aggregate_completed(rows,4,asof_ms=asof)
    # Never compute indicator across noncontiguous 4H candles. Retain the
    # most recent sufficiently long continuous segment only.
    segments=[];current=[]
    for b in bars:
        if current and b[0]-current[-1][0]!=H4:
            segments.append(current);current=[]
        current.append(b)
    if current:segments.append(current)
    good=[z for z in segments if len(z)>=350]
    if not good:raise RuntimeError(f"{symbol}: no 4H contiguous segment with 350+ bars")
    chosen=good[-1]
    return chosen,{"n_hourly":len(rows),"n_4h_completed":len(bars),
        "segments":len(segments),"longest_segment":max(map(len,segments)),
        "selected_latest_segment_bars":len(chosen),
        "selected_start":utc(chosen[0][0]),
        "selected_last_close":utc(chosen[-1][0]+H4),
        "data_source":"existing hourly OHLC CSV; provider not explicitly recorded in CSV"}

def compare(binance,cached):
    bi={z[0]:z for z in binance}
    hits=[(bi[z[0]],z) for z in cached if z[0] in bi]
    if len(hits)<400:return {"n_matched":len(hits)}
    idx_b=indicator(binance);idx_c=indicator(cached)
    db={z[0]:(idx_b["delta"][i],idx_b["color"][i])
        for i,z in enumerate(binance)}
    count=0;color_same=0;sign_same=0;price_diff=[];delta_diff=[];same_sign=[]
    for i,c in enumerate(cached):
        if i<270 or c[0] not in db:continue
        delta_a,color_a=db[c[0]]
        delta_b,color_b=idx_c["delta"][i],idx_c["color"][i]
        if not(math.isfinite(delta_a) and math.isfinite(delta_b)):continue
        count+=1
        color_same+=int(color_a==color_b)
        sign_same+=int((delta_a>0)==(delta_b>0))
        price_diff.append(100*abs(bi[c[0]][4]/c[4]-1))
        delta_diff.append(abs(delta_a-delta_b))
    return {"overlap_4h_candles":len(hits),"comparison_after_270_4h_warmup":count,
            "color_agreement_pct":round(100*color_same/count,2) if count else None,
            "delta_sign_agreement_pct":round(100*sign_same/count,2) if count else None,
            "median_abs_close_difference_pct":round(statistics.median(price_diff),5) if price_diff else None,
            "median_abs_DeltaRSI_difference":round(statistics.median(delta_diff),5) if delta_diff else None}

def main():
    out={"purpose":"4H source sensitivity: cached 1H OHLC -> closed four-hour, plus BTC/ETH Binance archive price and Delta parity",
         "notes":[
            "Cached repository 1H CSV exchange provenance is not guaranteed; do not identify it as Bybit without separate validation.",
            "4H only from FOUR complete 1H candles; missing hours omitted and no bridging across missing 4H candles.",
            "Exclude 270 early bars for BTC/ETH cross-source indicator parity to avoid different EMA starting histories.",
            "Signals from original log-mirrored DeltaRSI, frozen 60-bar 80th-percentile crest, next 4H open, confirmed local price swing stop.",
            "1-year data available for BTC ETH ICP and about 7 months HYPE. Not an out-of-sample model selection or user's manual trades.",
            "Market quotes/source and partial archive coverage may change signals and PnL versus full-history strategy."
          ],
         "assets":{}}
    for sym in SYMS:
        bars,meta=load_hourly(sym)
        ind=indicator(bars)
        variants={}
        for name,mode,win,threshold in (
            ("color_unfiltered","color",60,None),
            ("color_p80_60","color",60,.8),
            ("crest_p80_60","crest",60,.8),
            ("confirm_p80_60","confirm",60,.8)):
            events,drop=candidates(ind,mode,win,threshold)
            v={"all_signal_count":len(events),"rejected_events":drop}
            for direction in ("LONG","SHORT","BOTH"):
                trades,opens,exclusions=replay(bars,ind,events,
                    "fast_invalidation","confirmed_pivot",direction)
                v[direction]={"metrics":metrics(trades),"open_at_end":len(opens),
                    "skips":exclusions,
                    "last_ten_exits":[{k:z[k] for k in ("entry_time","direction","net_pct","exit_reason")}
                                     for z in trades[-10:]]}
            variants[name]=v
        archive=read_cache(sym) if sym in ("BTCUSDT","ETHUSDT") else None
        out["assets"][sym]={"cached_data":meta,
                           "parity":compare(archive,bars) if archive else None,
                           "variants":variants}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps({"assets":{s:{
        "period":z["cached_data"],"parity":z["parity"],
        "LONG":{k:{"n":x["LONG"]["metrics"]["n"],
                   "mean":x["LONG"]["metrics"].get("mean_net_pct"),
                   "pf":x["LONG"]["metrics"].get("profit_factor")}
                for k,x in z["variants"].items()}}
        for s,z in out["assets"].items()}},indent=2))
if __name__=="__main__":
    main()
