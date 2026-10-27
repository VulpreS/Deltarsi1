"""Frozen DeltaPulse 4H robustness: outliers, costs, periods, stops.

Trade-level bootstrap ignores dependence between BTC/ETH etc. No model fit,
no new filtering, no strategy parameter changes. Data from exact audit CSV.
"""
import csv
import json
import random
import statistics
from collections import Counter
from pathlib import Path

CSV=Path("reports/deltapulse_4h_v1_primary_trades.csv")
OUT=Path("reports/deltapulse_4h_v1_robustness.json")
ASSETS=("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT")
MODES=("color_all","color_p80_60","crest_p80_60","confirm_p80_60")
DIRECTIONS=("LONG","SHORT")
B=2500

def q(v,percentile):
    w=sorted(v)
    if not w:return None
    k=(len(w)-1)*percentile;a=int(k);b=min(a+1,len(w)-1)
    return w[a]+(w[b]-w[a])*(k-a)

def mean(v):
    return round(statistics.mean(v),4) if v else None

def profit_factor(vals):
    pos=sum(max(x,0) for x in vals)
    neg=-sum(min(x,0) for x in vals)
    return round(pos/neg,4) if neg>0 else None

def describe(rows,seed):
    if not rows:return {"n":0}
    returns=[float(x["net_pct"]) for x in rows]
    n=len(returns);rng=random.Random(seed)
    simulations=[statistics.mean([returns[rng.randrange(n)] for j in range(n)]) for k in range(B)]
    worstcost=[r-.15 for r in returns]
    sortedr=sorted(returns,reverse=True)
    return {
        "n":n,
        "mean_net_pct":mean(returns),
        "median_net_pct":round(statistics.median(returns),4),
        "profit_factor":profit_factor(returns),
        "pct_profitable":round(100*sum(x>0 for x in returns)/n,2),
        "95pct_bootstrap_mean_ci_pct":[round(q(simulations,.025),4),round(q(simulations,.975),4)],
        "mean_after_removing_top_one_trade_pct":mean(sortedr[1:]),
        "mean_after_removing_top_two_trades_pct":mean(sortedr[2:]),
        "double_roundtrip_fee_mean_pct":mean(worstcost),
        "double_roundtrip_fee_pf":profit_factor(worstcost),
        "n_structural_stops":sum(x["exit_reason"]=="structural_stop" for x in rows),
        "pct_structural_stop":round(100*sum(x["exit_reason"]=="structural_stop" for x in rows)/n,2),
        "mean_initial_stop_distance_pct":round(statistics.mean(float(x["initial_risk_pct"]) for x in rows),3),
        "median_holding_hours":statistics.median(float(x["bars_held"])*4 for x in rows),
        "max_win_pct":max(returns),
        "min_loss_pct":min(returns),
        "exit_reasons":dict(Counter(x["exit_reason"] for x in rows)),
    }

def main():
    with CSV.open() as stream:
        allrows=list(csv.DictReader(stream))
    for x in allrows:
        assert x["signal_time"]<=x["entry_time"]<=x["exit_time"]
        assert x["direction"] in DIRECTIONS
        assert float(x["initial_risk_pct"])>0
    out={
        "status":"exploratory stress test using previously researched futures OHLC, not independent holdout",
        "cost_base_pct":.15,
        "cost_stress_pct":.30,
        "bootstrap_draws_per_case":B,
        "limitations":[
            "Trade bootstrap assumes independent identical distributions. Signals cluster in correlated crypto markets; intervals understate uncertainty.",
            "Small-sample 4H crest strategies often have fewer than 10 trades per asset in the recent slice.",
            "No funding, Bybit transaction execution, margin liquidation, partial exits, leverage or variable commission.",
            "No artificial removal of negative assets. All existing configured variants are included.",
            "Forward chronological splits refer to known historical market data, not fresh prospective validation."
        ],
        "assets":{},"pooled":{},
    }
    for si,asset in enumerate(ASSETS):
        details={}
        for mi,mode in enumerate(MODES):
            for di,direction in enumerate(DIRECTIONS):
                key=f"{mode}_fast_invalidation_confirmed_pivot_{direction}"
                sub=[x for x in allrows if x["asset"]==asset and x["configuration"]==key]
                seed=12200+1000*si+10*mi+di
                details[key]={
                    "full":describe(sub,seed),
                    "2020_2023":describe([x for x in sub if x["entry_time"]<"2024-01-01"],seed+100),
                    "2024":describe([x for x in sub if "2024-01-01"<=x["entry_time"]<"2025-01-01"],seed+200),
                    "2025_2026":describe([x for x in sub if x["entry_time"]>="2025-01-01"],seed+300),
                }
        out["assets"][asset]=details
    for mode in MODES:
        for direction in DIRECTIONS:
            key=f"{mode}_fast_invalidation_confirmed_pivot_{direction}"
            sub=[x for x in allrows if x["configuration"]==key]
            out["pooled"][key]=describe(sub,11111+len(sub))
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    name="crest_p80_60_fast_invalidation_confirmed_pivot_LONG"
    print(json.dumps({"asset":{a:{k:v[name][k] for k in ("full","2025_2026")} for a,v in out["assets"].items()},
        "pooled_main":out["pooled"][name]},indent=2,ensure_ascii=False))
if __name__=="__main__":
    main()
