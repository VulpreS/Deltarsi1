"""DeltaPulse v1: a fully specified DeltaRSI-only IMPULSE LIFECYCLE strategy.

Signals derive only from the user's original Pine-style symmetric logarithmic
DeltaRSI histogram: peak strength, history-relative intensity, phase change.
Price used ONLY to place confirmed structural stops and realize fills.

No training optimization. BTC and ETH development/diagnostic; SOL BNB XRP
external-market transfer. All historical data are observational, not pristine
holdouts after strategy development. Closed 1D UTC candles, next daily open.
"""
import csv
import datetime as dt
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from analyze_mtf_5y import indicator
from daily_original_delta_percentile_backtest import (
    load_market, FIRST_MONTH, iso, structural_stop, FEE
)
from daily_delta_percentile_window_sensitivity import percentile
from structural_delta_strategy import swing

# Fixed before running new transfer assets; users may change for future tests.
FIRST_MONTH.update({
    # Use the same 2023-01 start on ALL external-transfer assets; early SOL
    # Binance archive has real missing daily bars in Feb/Apr 2022. Never
    # interpolate candles or calculate DeltaRSI across holes.
    "SOLUSDT": (2023,1),
    "BNBUSDT": (2023,1),
    "XRPUSDT": (2023,1)
})
ASSETS=("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT")
STRENGTH_LOOKBACK=20
STRENGTH_MIN=.80
STOP_BUFFER=.001
MAX_RISK_PCT=15
MAX_HOLD_DAYS=90
OUT=Path("reports/deltapulse_daily_v1.json")
TRADE_CSV=Path("reports/deltapulse_daily_v1_trades.csv")
# All candidate strategies frozen for reporting; no ranking/selection by results.
MODES=("plain_color","plain_firstfade","pulse_crest","pulse_confirm")
EXITS=("fast_invalidation","persistent_invalidation")
STOPS=("confirmed_pivot","recent_5d_extreme")
HOLDOUT_START="2025-01-01"

def strength(ind,peak_i,lookback=STRENGTH_LOOKBACK):
    d=ind["delta"]
    hist=[abs(d[k]) for k in range(peak_i-lookback,peak_i)
          if k>=0 and math.isfinite(d[k])]
    if len(hist)<lookback:return None
    magnitude=abs(d[peak_i])
    return (sum(z<magnitude for z in hist)+.5*sum(z==magnitude for z in hist))/len(hist)

def sign(v):return 1 if v>0 else -1 if v<0 else 0

def lifecycle_candidates(ind,mode):
    d=ind["delta"];colors=ind["color"];events=[];ignored=Counter()
    state_side=0;used=False;min_i=130
    for i in range(min_i,len(d)-2):
        if not math.isfinite(d[i]):continue
        sg=sign(d[i])
        if sg!=state_side:
            state_side=sg;used=False
        if sg==0:continue
        peak_i=None
        if mode=="plain_color":
            if (colors[i-1]=="mediumR" and colors[i]=="weakR") or (colors[i-1]=="mediumB" and colors[i]=="weakB"):
                peak_i=i-1
        elif mode=="plain_firstfade":
            if sign(d[i-1])==sg and sign(d[i-2])==sg and abs(d[i])<abs(d[i-1]) and abs(d[i-1])>=abs(d[i-2]):
                peak_i=i-1
        elif mode=="pulse_crest":
            if sign(d[i-1])==sg and sign(d[i-2])==sg and abs(d[i])<abs(d[i-1]) and abs(d[i-1])>=abs(d[i-2]):
                prior_increases=sum(abs(d[j])>abs(d[j-1]) for j in range(i-3,i))
                if prior_increases>=2:peak_i=i-1
        elif mode=="pulse_confirm":
            if sign(d[i-1])==sg and sign(d[i-2])==sg and sign(d[i-3])==sg and abs(d[i])<abs(d[i-1])<abs(d[i-2]):
                prior_increases=sum(abs(d[j])>abs(d[j-1]) for j in range(i-4,i-1))
                if prior_increases>=2:peak_i=i-2
        else:raise ValueError(mode)
        if peak_i is None:continue
        p=strength(ind,peak_i)
        if p is None:ignored["unwarmed"]+=1;continue
        if p<STRENGTH_MIN:
            ignored["not_unusual"]+=1;continue
        if used and mode in ("pulse_crest","pulse_confirm"):
            ignored["same_signed_impulse_already_used"]+=1;continue
        if mode in ("pulse_crest","pulse_confirm"):used=True
        # Delta positive = seller-exhaustion SHORT; negative = LONG.
        side=1 if sg<0 else -1
        events.append({"i":i,"side":side,"peak_i":peak_i,"percentile":p,
                       "delta_peak":abs(d[peak_i]),"delta_signal":abs(d[i]),
                       "phase_velocity":abs(d[peak_i])-abs(d[i]),
                       "delta_sign":sg,"time":iso(ind["timestamps"][i])})
    return events,dict(ignored)

def exited(ind,j,side,mode):
    d=ind["delta"];col=ind["color"]
    if j<2 or not math.isfinite(d[j]):return None
    # Opposite blue-fading for LONG, red-fading for SHORT.
    opposite=(col[j-1]=="mediumB" and col[j]=="weakB") if side==1 else (
              col[j-1]=="mediumR" and col[j]=="weakR")
    if opposite:return "opposite_delta_fade"
    own_red=side==1
    rising=(d[j]<0 and d[j-1]<0 and abs(d[j])>abs(d[j-1])) if own_red else (
            d[j]>0 and d[j-1]>0 and abs(d[j])>abs(d[j-1]))
    if mode=="fast_invalidation":
        # Exit only if faded indicator has visibly brightened again.
        invalid=(col[j-1]=="weakR" and col[j] in ("mediumR","strongR")) if own_red else (
                 col[j-1]=="weakB" and col[j] in ("mediumB","strongB"))
        if invalid:return "rebrightening"
    elif mode=="persistent_invalidation":
        if j>=2 and rising and math.isfinite(d[j-2]) and sign(d[j-2])==sign(d[j-1]) and abs(d[j-1])>abs(d[j-2]):
            return "two_bar_reacceleration"
    else:raise ValueError(mode)
    return None

def stop_level(rows,i,entry,side,mode):
    if mode=="confirmed_pivot":
        p,idx=swing(rows,i,side,2,1,20)
    elif mode=="recent_5d_extreme":
        last=rows[i-4:i+1]
        p=min(x[3] for x in last) if side==1 else max(x[2] for x in last)
    else:raise ValueError(mode)
    if p is None:return None,"missing_structure"
    stop=p*(1-STOP_BUFFER if side>0 else 1+STOP_BUFFER)
    risk=side*(entry-stop)/entry*100
    if risk<=0:return None,"structural_stop_wrong_side"
    if risk>MAX_RISK_PCT:return None,"risk_over_15pct"
    return (stop,risk),None

def simulate(rows,ind,events,exitmode,stopmode,only_long=False):
    if only_long:events=[e for e in events if e["side"]==1]
    indexed={e["i"]:e for e in events}
    output=[];skips=Counter();k=130;n=len(rows)
    while k<n-1:
        ev=indexed.get(k)
        if ev is None:k+=1;continue
        side=ev["side"];ei=k+1;entry=rows[ei][1]
        level,err=stop_level(rows,k,entry,side,stopmode)
        if err:skips[err]+=1;k+=1;continue
        stop,risk_pct=level
        exit_i=min(n-1,ei+MAX_HOLD_DAYS-1)
        price=rows[exit_i][4];reason="safety_timeout" if exit_i<n-1 else "end_of_data"
        for j in range(ei,exit_i+1):
            _,op,hi,lo,cl=rows[j]
            if (lo<=stop if side==1 else hi>=stop):
                price=min(op,stop) if side==1 else max(op,stop)
                exit_i=j;reason="structural_stop";break
            if j+1<n and j+1<=exit_i:
                signal=exited(ind,j,side,exitmode)
                if signal:
                    exit_i=j+1;price=rows[j+1][1];reason=signal;break
        ret=side*(price/entry-1)-FEE
        output.append({
            "signal_i":k,"entry_i":ei,"exit_i":exit_i,
            "signal_date":iso(rows[k][0]),"entry_date":iso(rows[ei][0]),
            "exit_date":iso(rows[exit_i][0]),"direction":"LONG" if side>0 else "SHORT",
            "entry_price":round(entry,3),"stop":round(stop,3),
            "exit_price":round(price,3),"initial_risk_pct":round(risk_pct,4),
            "net_pct":round(ret*100,5),"net_R":round(ret*100/risk_pct,5),
            "exit_reason":reason,"days_held":exit_i-ei+1,
            "strength_percentile":round(ev["percentile"]*100,3),
            "delta_peak":round(ev["delta_peak"],4),
            "delta_entry":round(ev["delta_signal"],4),
            "peak_date":iso(rows[ev["peak_i"]][0]),
        })
        k=exit_i+1
    return output,dict(skips)

def stats(trades):
    if not trades:return {"n":0}
    rets=[x["net_pct"] for x in trades]
    wins=[x for x in rets if x>0]
    losses=[x for x in rets if x<0]
    gp=sum(wins);gl=-sum(losses)
    eq=peak=1.;dd=0;eq_risk=peak_risk=1.;dd_risk=0.
    for t in trades:
        eq*=max(1e-9,1+t["net_pct"]/100)
        peak=max(peak,eq);dd=max(dd,1-eq/peak)
        # Illustrative fixed initial 0.5% capital risk per trade
        eq_risk*=max(1e-9,1+.005*t["net_R"])
        peak_risk=max(peak_risk,eq_risk);dd_risk=max(dd_risk,1-eq_risk/peak_risk)
    return {"n":len(trades),"win_rate_pct":round(100*len(wins)/len(trades),2),
       "mean_net_pct":round(statistics.mean(rets),3),
       "median_net_pct":round(statistics.median(rets),3),
       "profit_factor":round(gp/gl,3) if gl else None,
       "mean_R":round(statistics.mean(x["net_R"] for x in trades),3),
       "median_risk_pct":round(statistics.median(x["initial_risk_pct"] for x in trades),3),
       "median_days_held":statistics.median(x["days_held"] for x in trades),
       "closed_trade_full_notional_compound_pct":round(100*(eq-1),2),
       "closed_trade_full_notional_maxdd_pct":round(100*dd,2),
       "illustrative_risk_half_percent_compound_pct":round(100*(eq_risk-1),2),
       "illustrative_risk_half_percent_maxdd_pct":round(100*dd_risk,2),
       "exit_reasons":dict(Counter(x["exit_reason"] for x in trades))}

def partitions(rows,trades):
    cuts=(("2020-2023",lambda t:t["entry_date"]<"2024-01-01"),
          ("2024",lambda t:"2024-01-01"<=t["entry_date"]<"2025-01-01"),
          ("2025-2026",lambda t:t["entry_date"]>="2025-01-01"))
    return {name:stats([t for t in trades if fn(t)]) for name,fn in cuts}

def buy_and_hold(rows,lo="2025-01-01"):
    candidates=[z for z in rows if iso(z[0])>=lo]
    if len(candidates)<2:return None
    return round(100*(candidates[-1][4]/candidates[0][1]-1),2)

def main():
    out={"strategy":"DeltaPulse v1 — original DeltaRSI impulse crest then first or confirmed fading",
         "frozen_parameters":{
             "delta":"SMA21(close), RSI12 Wilder, EMA7 of RSI, original symmetric signed mirrored log",
             "timeframe":"UTC daily completed candles",
             "strength_lookback_days":STRENGTH_LOOKBACK,"strength_percentile_min":STRENGTH_MIN,
             "pulse_growth_requirement":"2 of preceding 3 delta-magnitude increments positive",
             "pulse_crest":"first reduction in |D| after impulse peak",
             "pulse_confirm":"second consecutive reduction in |D| after impulse peak",
             "rearm":"one signal per same-signed DeltaRSI episode for pulse modes",
             "entry":"next UTC daily candle open",
             "structural_stop":"latest confirmed 2-left 1-right price pivot within last20d, 0.1% buffer",
             "risk_limit":"skip stops >15% away or wrong side",
             "invalidation":"fast color rebrightening or 2 consecutive magnitude re-accelerations",
             "exit":"opposite DeltaRSI medium-to-weak or initial stop; 90d max",
             "fees":"0.15% roundtrip; funding excluded"
         },
         "limitations":[
             "Historical research only; not an executable-bybit live bot or user's exact manual strategy.",
             "Original indicator unchanged; candles fully completed before signals; stops confirmed before entry.",
             "All signal rules predeclared before inspecting transfer asset results, but BTC/ETH historical results informed the design: neither a pristine holdout.",
             "Calendar-date partitions are stress tests, not independent train/test for historically inspected assets.",
             "Use of Binance USD-M perpetual 1D OHLC instead of user's Bybit OHLC; no funding.",
             "Stop filled adversely at daily open when price gaps past it. Intraday sequence unknown; stop checked before signal exit.",
             "No concurrent positions per asset; LONG-only run recomputes decisions without SHORT occupation.",
             "Stop level fixed for trade life. User may dynamically move a structural stop; not reproduced.",
             "Only structural levels use OHLC price; no MACD, BB, volume, external signals.",
             "Risk-sized compounding illustrative; no portfolio overlap across assets, leverage, margin liquidation or taxes.",
             "SOL BNB XRP external-transfer bars begin January 2023 for a common contiguous historical interval. Earlier SOL archives had missing February/April 2022 daily candles; no candles interpolated.",
             "Alt-market transfer tests explore generality but cannot be considered independent confirmatory after viewing results."
         ],"assets":{},"overview":[]}
    logs=[]
    for symbol in ASSETS:
        rows,source=load_market(symbol)
        idx=indicator(rows);idx["timestamps"]=[x[0] for x in rows]
        a={"source":source,"rows":len(rows),"buy_and_hold_2025_plus_pct":buy_and_hold(rows),
           "signals":{},"backtests":{}}
        for mode in MODES:
            events,issues=lifecycle_candidates(idx,mode)
            a["signals"][mode]={"n":len(events),"long":sum(z["side"]==1 for z in events),
                                 "short":sum(z["side"]==-1 for z in events),
                                 "excluded":issues}
            for exitmode in EXITS:
                for stopmode in STOPS:
                    for long_only in (False,True):
                        key=f"{mode}_{exitmode}_{stopmode}_{'LONG' if long_only else 'BOTH'}"
                        trades,skip=simulate(rows,idx,events,exitmode,stopmode,long_only)
                        record={"mode":mode,"exit":exitmode,"stop":stopmode,"long_only":long_only,
                                "all":stats(trades),"by_period":partitions(rows,trades),
                                "skips":skip}
                        a["backtests"][key]=record
                        out["overview"].append({
                            "asset":symbol,"mode":mode,"exit":exitmode,
                            "stop":stopmode,"long_only":long_only,
                            "all":record["all"],"latest":record["by_period"]["2025-2026"]})
                        for t in trades:logs.append({"asset":symbol,"config":key,**t})
        out["assets"][symbol]=a
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    columns=list(logs[0]) if logs else []
    with TRADE_CSV.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader();writer.writerows(logs)
    relevant=[]
    for symbol in ASSETS:
        a=out["assets"][symbol]
        for mode in ("plain_color","plain_firstfade","pulse_crest","pulse_confirm"):
            for long_only in (True,False):
                key=f"{mode}_fast_invalidation_confirmed_pivot_{'LONG' if long_only else 'BOTH'}"
                x=a["backtests"][key]
                relevant.append({"asset":symbol,"mode":mode,"long_only":long_only,
                    "all":{k:x["all"].get(k) for k in ("n","win_rate_pct","mean_net_pct","profit_factor","mean_R")},
                    "2025_plus":{k:x["by_period"]["2025-2026"].get(k)
                                 for k in ("n","win_rate_pct","mean_net_pct","profit_factor","mean_R")}})
    print(json.dumps({"assets":{k:v["source"] for k,v in out["assets"].items()},
       "primary_fixed":relevant,"trade_rows":len(logs)},indent=2))

if __name__=="__main__":
    main()
