"""No-optimization robustness audit for the frozen DeltaPulse v1 daily strategy.

Uses exact committed trade log. Bootstrap resamples trades (optimistic if
serially dependent); yearly partitions and worst-top-trade removal accompany
all positive and negative results. Fee-stress subtracts additional 0.15%
per trade (doubling 0.15% assumed cost). No threshold fitting.
"""
import csv
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

DATA=Path("reports/deltapulse_daily_v1_trades.csv")
OUT=Path("reports/deltapulse_daily_v1_robustness.json")
RNGSEED=777
BOOTSTRAPS=5000
KEYS=("pulse_crest_fast_invalidation_confirmed_pivot_LONG",
      "pulse_confirm_fast_invalidation_confirmed_pivot_LONG",
      "plain_color_fast_invalidation_confirmed_pivot_LONG",
      "pulse_crest_persistent_invalidation_confirmed_pivot_LONG",
      "pulse_crest_fast_invalidation_recent_5d_extreme_LONG")

def percentile(arr,p):
    v=sorted(arr)
    if not v:return None
    i=(len(v)-1)*p;a=int(i);b=min(a+1,len(v)-1)
    return v[a]+(v[b]-v[a])*(i-a)

def pf(rows):
    wins=sum(max(0,x) for x in rows);loss=-sum(min(0,x) for x in rows)
    return round(wins/loss,4) if loss else None

def summarise(xs,seed):
    if not xs:return {"n":0}
    vals=[float(x["net_pct"]) for x in xs];n=len(vals)
    rng=random.Random(seed)
    boots=[]
    for _ in range(BOOTSTRAPS):
        boots.append(sum(vals[rng.randrange(n)] for j in range(n))/n)
    gross=sum(max(0,x) for x in vals)
    best=max(vals);srt=sorted(vals,reverse=True)
    stressed=[x-.15 for x in vals]
    return {"n":n,"win_rate_pct":round(100*sum(x>0 for x in vals)/n,2),
      "mean_net_pct":round(statistics.mean(vals),4),
      "median_net_pct":round(statistics.median(vals),4),
      "profit_factor":pf(vals),
      "bootstrap_trade_resample_95pct_mean_interval":[round(percentile(boots,.025),4),round(percentile(boots,.975),4)],
      "mean_without_best_trade":round(statistics.mean(sorted(vals)[:-1]),4) if n>=2 else None,
      "mean_without_two_best_trades":round(statistics.mean(sorted(vals)[:-2]),4) if n>=3 else None,
      "best_trade_net_pct":round(best,4),
      "share_of_total_positive_pnl_from_best_pct":round(100*max(0,best)/gross,2) if gross else None,
      "double_roundtrip_cost_mean_pct":round(statistics.mean(stressed),4),
      "double_roundtrip_cost_profit_factor":pf(stressed),
      "stop_count":sum(x["exit_reason"]=="structural_stop" for x in xs),
      "stop_fraction_pct":round(100*sum(x["exit_reason"]=="structural_stop" for x in xs)/n,2),
      "mean_initial_risk_pct":round(statistics.mean(float(x["initial_risk_pct"]) for x in xs),3),
      "median_days_in_position":statistics.median(float(x["days_held"]) for x in xs),
    }

def main():
    with DATA.open() as f:records=list(csv.DictReader(f))
    seen=set()
    for row in records:
        assert row["signal_date"]<=row["entry_date"]<=row["exit_date"],"entry/exit calendar chronology"
        assert row["direction"] in ("LONG","SHORT")
        assert row["exit_reason"] in ("rebrightening","opposite_delta_fade","two_bar_reacceleration","structural_stop","safety_timeout","end_of_data")
        assert float(row["initial_risk_pct"])>0
        if row["config"].endswith("_LONG"):assert row["direction"]=="LONG"
        key=(row["asset"],row["config"],row["entry_date"])
        assert key not in seen, "duplicate entries";seen.add(key)
    out={"audit":"Frozen DeltaPulse daily strategy stress test",
      "notes":[
       "All markets retained, including failed SOL. No filtering assets after seeing returns.",
       "Bootstrap resamples whole trades; ignores serial dependence and shared crypto market risk. Indicative uncertainty only.",
       "Removing the top two trades exposes outlier dependence, not a realistic executed alternative.",
       "Double fee assumes 0.30% roundtrip notional total; no funding, liquidations or variable slippage.",
       "This historical data was previously inspected. Neither stress test nor earlier chronological splits are independently prospective.",
       "Variant comparisons are descriptive only. Do not select the best-performing asset, timeframe, stop or exit using this report.",
       "No trade automation, exchange keys or positions were opened.",
      ],
      "trade_rows":len(records),"by_asset":{},"pooled":{}}
    for symbol in sorted(set(x["asset"] for x in records)):
        configs={}
        for ix,cfg in enumerate(KEYS):
            arr=[x for x in records if x["asset"]==symbol and x["config"]==cfg]
            configs[cfg]={
               "all":summarise(arr,10000+ix),
               "2020_2023":summarise([x for x in arr if x["entry_date"]<"2024-01-01"],20000+ix),
               "2024":summarise([x for x in arr if "2024-01-01"<=x["entry_date"]<"2025-01-01"],30000+ix),
               "2025_plus":summarise([x for x in arr if x["entry_date"]>="2025-01-01"],40000+ix),
            }
        out["by_asset"][symbol]=configs
    for cfg in KEYS:
        # Equal weight PER TRADE, not per asset or calendar portfolio.
        arr=[x for x in records if x["config"]==cfg]
        out["pooled"][cfg]=summarise(arr,60000+KEYS.index(cfg))
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    key=KEYS[0]
    print(json.dumps({"primary_config":key,
        "by_asset":{a:z[key] for a,z in out["by_asset"].items()},
        "pooled_primary":out["pooled"][key]},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
