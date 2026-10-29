"""Side-by-side replay of official 'новые инструкции' parameters at 16.8% vs 16.9%.

NO parameter changes: 8 tickers from canonical README, original six ATR multipliers,
TON-only trailing 3/0.5 ATR, 48h max hold for all, entry at 4h close,
ATR from bar PRIOR to signal, 1h execution/stop-first, 0.08% fee per side,
0.02% roundtrip spread, funding off. Original 5/10% approximate prop gates.

The main README's frozen 16.8% is unchanged; 16.9% is scenario-only.
"""
import sys,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_instructions_8asset_48h import backtest as base
from experiments.new_instructions_8asset_48h.backtest import (
    check_document,unit_test,simulate,SYMS,START,VALID_END,END,H)
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

OUTPUT=Path("experiments/new_instructions_8asset_48h/scenario_16p9")
BASE_ACCOUNT=5000.
PCTS=(16.8,16.9)
assert base.prop.INITIAL==BASE_ACCOUNT
assert base.prop.FEE==.0008 and base.prop.SPREAD==.0002
def summary(x):
    return {k:v for k,v in x.items() if k!="by_symbol"}

def main():
    assert base.prop.NOTIONAL==1000., "Expected fresh original prop portfolio module"
    params=check_document()  # compares to actual README and original six-coin config
    # Unit-test TON trailing under each notional, then freeze simulated market conditions.
    unit_results={}
    for pct in PCTS:
        base.prop.NOTIONAL=BASE_ACCOUNT*pct/100
        unit_test()
        unit_results[f"{pct:g}pct"]={"notional":base.prop.NOTIONAL,
            "ton_trail_check":"passed"}
    raw5,_,manifest=base.source_load()
    assert set(raw5)==set(SYMS)==set(params)
    hourly={};signal={};coverage={}
    for s in SYMS:
        rows=sorted(raw5[s].values())
        buckets=ohlc_from_5m(rows,H)
        assert buckets and buckets[0][0]<START and buckets[-1][0]==END-H
        hourly[s]={b[0]:b for b in buckets}
        signal[s]=pine_events(buckets,expanded=False,atr_basis="prior")
        coverage[s]={"1h_bars":len(buckets),"5m_bars":manifest[s]["bars_5m"],
            "year_signals":sum(START<=t<END for t in signal[s]),
            "q2_signals":sum(VALID_END<=t<END for t in signal[s])}
        print("ASSET_COVERAGE",s,json.dumps(coverage[s]),flush=True)

    results={}
    for pct in PCTS:
        base.prop.NOTIONAL=BASE_ACCOUNT*pct/100
        label=f"{pct:g}pct"
        results[label]={}
        for name,start,end,reset in (
            ("full_year_with_phase_reset",START,END,True),
            ("full_year_continuous",START,END,False),
            ("apr_jun_new_account",VALID_END,END,True)):
            value=simulate(hourly,signal,params,SYMS,start,end,reset)
            if name=="apr_jun_new_account":
                diagnostic=base.prop.run(
                    {asset:hourly[asset] for asset in SYMS},
                    {asset:signal[asset] for asset in SYMS},
                    params,list(range(start,end,H)),reset=reset,max_hours=48,
                    include_daily=True)
                assert all(diagnostic[k]==v for k,v in value.items() if k!="daily_trace")
                value["daily_trace"]=diagnostic["daily_trace"]
                key_day="2026-04-23T00:00:00+00:00"
                entry=next((d for d in diagnostic["daily_trace"] if d["time"]==key_day),None)
                if entry is None:raise AssertionError("Missing April 23 daily snapshot")
                print("PHASE_THRESHOLD_APR23",label,json.dumps({
                    "equity":entry["equity"],"day_pnl":entry["day_pnl"],
                    "phase":entry["phase"],"above_target_5250":entry["equity"]>=5250
                }),flush=True)
            assert value["max_concurrent"]<=3
            assert sum(z["trades"] for z in value["by_symbol"].values())==value["trades"]
            assert set(value["by_symbol"])==set(SYMS)
            results[label][name]=value
            print("SCENARIO_RESULT",label,name,json.dumps(value,ensure_ascii=False),flush=True)
    diffs={}
    for name in results["16.9pct"]:
        b=results["16.8pct"][name]
        v=results["16.9pct"][name]
        diffs[name]={
            "delta_closed_net_pnl_usd":round(v["closed_net_pnl"]-b["closed_net_pnl"],4),
            "delta_max_intrahour_dd_percentage_points":round(v["max_intrahour_dd"]-b["max_intrahour_dd"],5),
            "phase_days_16p8":[z["days"] for z in b["phases"]],
            "phase_days_16p9":[z["days"] for z in v["phases"]],
            "breach_16p8":b["breach"],"breach_16p9":v["breach"]}
    output={
        "source":"новые инструкции/README.md",
        "canonical_size_not_changed":"16.8% / $840 in README",
        "scenario_size":"16.9% / $845 of initial $5000",
        "account_usd":BASE_ACCOUNT,"max_positions":3,
        "max_total_notional_16p9_usd":3*845,
        "model":"experiments/max_strategy_grid/prop_portfolio.py:run",
        "signal":"pine_events(expanded=False, atr_basis=prior)",
        "execution_tf":"1h", "hold_hours":48,
        "ton_trailing_activation_atr":3,"ton_trailing_distance_atr":.5,
        "fee_per_side":.0008,"round_trip_spread":.0002,"funding":0,
        "all_symbol_params":params,"coverage":coverage,"unit_tests":unit_results,
        "results":results,"comparison":diffs,
        "limitations":[
            "All six original ATR SL/TP and TON trail plus XRP LINK added settings remain unchanged.",
            "Uses Binance futures 5m archives aggregated to 1h, not Upscale quotes or real tick fills.",
            "The original engine has approximate daily/overall drawdown gates and does not enforce 30% profit consistency.",
            "Approaching the hard 5%/10% limit is sensitive to hourly OHLC and slippage.",
            "The original 4h signal implementation uses RSI12 on SMA21 with log Delta despite older README wording RSI27.",
            "The pre-existing ETH and TON legacy live positions with different exits are not modeled; new trade configs only.",
            "100 seconds before time deadline cannot be simulated precisely using 1h candles.",
            "Profit factor does not prove tradeable prospective profitability; parameters come from prior in-sample tuning.",
            "No trade orders placed and the canonical 16.8 percent README was not changed."
        ]}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    dest=OUTPUT/"results.json"
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("REPLAY_16P9_SUCCEEDED",str(dest),dest.stat().st_size,flush=True)

if __name__=="__main__":
    main()
