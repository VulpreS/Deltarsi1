"""Diagnose why 4H DeltaPulse profits differ from discretionary BTC trades.

Two distinct controlled comparisons:
 A) identical algorithmic entry signals/stops, change ONLY exit logic:
    - immediate fade invalidation
    - opposite medium->weak transition
    - first opposite weak-color appearance
 B) identical 38 quality-ok manual BTC entry timestamp/entry price/initial stop,
    replay ONLY alternative DeltaRSI exit rules on cached Binance 4H OHLC
    and compare holding times with manual journal's partial-exit-weighted PnL.

B is a counterfactual sensitivity test, not an executable copy of the user's
trades. The manual price and stop are supplied; actual exchange is Binance
USD-M whereas user's positions are Bybit; stop amendments and partial exits
not available. The original 4H indicator remains unchanged. Only 4H CLOSES
determine signals; an exit signal fills next 4H open. Initial structural
stop has intrabar priority (gap-aware).
"""
import bisect
import csv
import datetime as dt
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from analyze_mtf_5y import indicator
from deltapulse_4h_archive import read_cache,H4
from deltapulse_4h_strategy_v1 import candidates,replay,metrics,signal_exit,utc
from btc_manual_trade_statistical_audit import jret
from btc_price_action_bb_volume_study import ts

OUT=Path("reports/deltapulse_4h_exit_horizon_diagnostic.json")
CASES=Path("reports/deltapulse_4h_manual_exit_counterfactual.csv")
FEE=.0015
MAX_BARS=180
SIGNAL_MODELS=(
    ("color_all","color",60,None),
    ("color_p80_60","color",60,.8),
    ("firstfade_p80_60","firstfade",60,.8),
    ("crest_p80_60","crest",60,.8),
)
EXIT_MODES=("fast_invalidation","opposite_only","opposite_weak")

def median(seq):
    return round(statistics.median(seq),4) if seq else None

def mean(seq):
    return round(statistics.mean(seq),4) if seq else None

def journal_rows():
    with Path("data/manual_btc_trades_2025_2026.csv").open() as f:
        data=list(csv.DictReader(f))
    records=[]
    for row in data:
        r=jret(row)
        if row["quality"]!="ok" or r is None:continue
        start=ts(row["entry_msk"])
        exits=[ts(row["exit"+str(i)+"_msk"]) for i in (1,2) if row.get("exit"+str(i)+"_msk")]
        if start is None or not exits or any(x is None for x in exits):continue
        stop=float(row["sl"])
        entry=float(row["entry"])
        side=1 if stop<entry else -1
        last=max(exits)
        records.append({
            "date":row["entry_msk"],"start":start,"last":last,
            "side":side,"entry":entry,"stop":stop,
            "manual_hold_hours":(last-start)/3600000,
            "manual_net_pct":100*r,
            "entry_reason":row["entry_reason"],"exit_reason":row["exit_reason"],
            "risk_pct":100*abs(entry-stop)/entry,
        })
    return records

def manual_anchored_exit(bars,ind,entry_i,entry,stop,side,mode):
    # Start from supplied real entry clock and price; hard original manual
    # stop is left unchanged (no manual stop-management records available).
    max_i=min(entry_i+MAX_BARS-1,len(bars)-1)
    out=bars[max_i][4];index=max_i
    reason="administrative_max_hold" if index<len(bars)-1 else "data_end"
    for j in range(entry_i,max_i+1):
        _,opening,high,low,close=bars[j]
        if (low<=stop if side==1 else high>=stop):
            out=min(opening,stop) if side==1 else max(opening,stop)
            index=j;reason="initial_manual_stop_touched";break
        if j+1<=max_i:
            why=signal_exit(ind,j,side,mode)
            if why:
                out=bars[j+1][1]
                index=j+1;reason=why;break
    result=100*(side*(out/entry-1)-FEE)
    # Signal bar is j when 4H has CLOSED; 4H bucket j+1 starts at its close.
    end_ms=bars[index][0]
    return {
        "counterfactual_exit_utc":utc(end_ms),
        "counterfactual_hold_hours":(end_ms-bars[entry_i][0])/3600000,
        "counterfactual_net_pct":round(result,5),
        "counterfactual_exit_price":round(out,6),
        "counterfactual_reason":reason,
    }

def main():
    out={
       "purpose":"Explain manual 3-4% mean vs near-zero 4H robot: controlled exits, manual same-entry same-stop counterfactuals",
       "notes":[
          "A: signal universe and static structural stop identical within a configuration; only exit timing changes.",
          "B: journal supplies real entry/initial stop. Counterfactual EXIT only uses Binance futures 4H quotes and original DeltaRSI, strictly as-of each closed bar.",
          "Manual journal outcomes are partial-exit-weighted, with assumed 0.15% cost, no leverage. Quality-ok rows only.",
          "Unlike journal, counterfactual hard stops are immutable; journal records do not document intratrade amendments, partial position protection or funding.",
          "Counterfactual is not same population as autonomous bot; do not infer that the bot reproduced user's entry selection.",
          "Near-exchange OHLC can still cross a stop that differs from Bybit; report stop-related disagreements separately.",
          "The 'opposite_weak' rule considers first available closed 4H bar with weak opposite signed DeltaRSI, instead of requiring medium->weak transition; not guaranteed to match trader's manual decision.",
          "Existing fully studied historical period; no untouched test data and no optimal exit-mode selection justified."
       ],"method_A_algorithmic_entry_same_stop":{},"method_B_same_manual_entry_same_initial_stop":{}}
    data=journal_rows()
    out["journal_overview"]={
        "quality_ok_complete":len(data),
        "manual_average_net_pct":mean([x["manual_net_pct"] for x in data]),
        "manual_median_net_pct":median([x["manual_net_pct"] for x in data]),
        "manual_mean_holding_hours":mean([x["manual_hold_hours"] for x in data]),
        "manual_median_holding_hours":median([x["manual_hold_hours"] for x in data]),
        "manual_average_initial_stop_distance_pct":mean([x["risk_pct"] for x in data]),
        "manual_stops_recorded":sum(x["exit_reason"]=="SL" for x in data),
        "manual_win_rate":round(100*sum(x["manual_net_pct"]>0 for x in data)/len(data),2),
        "manual_long":sum(x["side"]==1 for x in data),
        "manual_short":sum(x["side"]==-1 for x in data),
    }
    cases=[]
    for symbol in ("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"):
        bars=read_cache(symbol)
        ind=indicator(bars)
        runs={}
        for label,mode,window,pctl in SIGNAL_MODELS:
            events,discard=candidates(ind,mode,window,pctl)
            run={}
            for direction in ("LONG","SHORT"):
                for exitmode in EXIT_MODES:
                    trades,unfinished,skips=replay(bars,ind,events,
                        exitmode,"confirmed_pivot",direction)
                    m=metrics(trades)
                    run[direction+"_"+exitmode]={
                       "n":m["n"],
                       "mean_net_pct":m.get("mean_net_pct"),
                       "median_net_pct":m.get("median_net_pct"),
                       "profit_factor":m.get("profit_factor"),
                       "median_hold_hours":m.get("median_hold_hours"),
                       "median_initial_stop_pct":m.get("median_initial_stop_pct"),
                       "structural_stops":m.get("stops"),
                       "exit_reasons":m.get("exit_reasons"),
                       "recent_2025plus":{
                           "n":len(v:=[x for x in trades if x["entry_time"]>="2025-01-01"]),
                           "mean_net_pct":mean([x["net_pct"] for x in v]),
                           "median_hold_hours":median([x["bars_held"]*4 for x in v]),
                           "structural_stops":sum(x["exit_reason"]=="structural_stop" for x in v),
                       },
                       "unfinished_at_end":len(unfinished),
                    }
            runs[label]={"eligible_events":len(events),"runs":run}
        out["method_A_algorithmic_entry_same_stop"][symbol]=runs
        if symbol!="BTCUSDT":continue
        lookup={row[0]:i for i,row in enumerate(bars)}
        saved_signals={}
        for label,mode,window,pctl in SIGNAL_MODELS:
            ev,_=candidates(ind,mode,window,pctl)
            saved_signals[label]=ev
        for manual in data:
            index=lookup.get(manual["start"])
            if index is None:
                cases.append({"manual_entry_msk":manual["date"],
                    "diagnostic_error":"entry not exactly at 4H candle boundary"})
                continue
            record={"manual_entry_msk":manual["date"],
                "direction":"LONG" if manual["side"]==1 else "SHORT",
                "manual_net_pct":round(manual["manual_net_pct"],5),
                "manual_hours":manual["manual_hold_hours"],
                "manual_exit_reason":manual["exit_reason"],
                "manual_entry":manual["entry"],
                "manual_stop":manual["stop"],
            }
            for label,events in saved_signals.items():
                eligible=[e for e in events if e["side"]==manual["side"]
                    and abs(bars[e["i"]][0]+H4-manual["start"])<=H4]
                record[label+"_matching_event_near_manual_entry"]=int(bool(eligible))
            for exitmode in EXIT_MODES:
                counter=manual_anchored_exit(
                    bars,ind,index,manual["entry"],manual["stop"],manual["side"],exitmode)
                record[exitmode+"_hours"]=counter["counterfactual_hold_hours"]
                record[exitmode+"_net_pct"]=counter["counterfactual_net_pct"]
                record[exitmode+"_reason"]=counter["counterfactual_reason"]
                record[exitmode+"_exit_utc"]=counter["counterfactual_exit_utc"]
                record[exitmode+"_before_manual_exit"]=int(
                    (dt.datetime.fromisoformat(counter["counterfactual_exit_utc"].replace("Z","+00:00")).timestamp()*1000)
                    <manual["last"])
            cases.append(record)
    # Do not interpret a flagged source mismatch as a real customer stop touch.
    valid=[x for x in cases if "diagnostic_error" not in x]
    grouped={}
    for direction in ("ALL","LONG","SHORT"):
        samples=[x for x in valid if direction=="ALL" or x["direction"]==direction]
        strategies={}
        for mode in EXIT_MODES:
            strategies[mode]={
                "counterfactual_n":len(samples),
                "mean_net_pct":mean([x[mode+"_net_pct"] for x in samples]),
                "median_net_pct":median([x[mode+"_net_pct"] for x in samples]),
                "mean_holding_hours":mean([x[mode+"_hours"] for x in samples]),
                "median_holding_hours":median([x[mode+"_hours"] for x in samples]),
                "pct_closed_before_actual_manual_exit":round(
                    100*sum(x[mode+"_before_manual_exit"] for x in samples)/len(samples),2) if samples else None,
                "hard_manual_stop_touches":sum(x[mode+"_reason"]=="initial_manual_stop_touched" for x in samples),
                "exit_reasons":dict(Counter(x[mode+"_reason"] for x in samples))
            }
        grouped[direction]=strategies
    out["method_B_same_manual_entry_same_initial_stop"]={
        "matched_btc_manual_entries":len(valid),
        "event_match_counts":{
            label:sum(x[label+"_matching_event_near_manual_entry"] for x in valid)
            for label,_,_,_ in SIGNAL_MODELS
        },
        "replayed_manual_entries":grouped,
        "individual_trade_rows":valid
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    if valid:
        cols=list(valid[0])
        with CASES.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore")
            writer.writeheader();writer.writerows(valid)
    print(json.dumps({
        "manual":out["journal_overview"],
        "counterfactual":out["method_B_same_manual_entry_same_initial_stop"],
        "BTC_autonomous":{
            k:v["runs"] for k,v in out["method_A_algorithmic_entry_same_stop"]["BTCUSDT"].items()
        }
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
