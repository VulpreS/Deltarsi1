"""DeltaPulse 4H: closed-candle lifecycle strategy, frozen variants & stress tests.

A causal transfer of the existing DAILY DeltaPulse design to FOUR-hour bars.
100% signal indicators from original DeltaRSI: SMA21(close) RSI12 Wilder
EMA7 and signed mirror-log, no MACD/BB/volume. OHLC only for structural stops.
Historical futures Binance USD-M != user's Bybit fills or discretionary trades.

Primary: 60 4H candles (~10 days), rank >= 80th historical percentile,
2/3 preceding gains, first post-peak fade, one signal per Delta-sign episode.
Variants prelisted for sensitivity, not optimized on 4H outcome.
"""
import csv
import datetime as dt
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from analyze_mtf_5y import indicator
from deltapulse_4h_archive import load,STARTS,H4,dt_of
from structural_delta_strategy import swing

OUT=Path("reports/deltapulse_4h_v1.json")
TRADES=Path("reports/deltapulse_4h_v1_primary_trades.csv")
FEE=.0015
MAX_BARS=180  # 30 days administrative limit; NOT a trading criterion
STOP_BUFFER=.001
MAX_INITIAL_STOP_PCT=15.0
PIVOT_LEFT=2
PIVOT_RIGHT=1
PIVOT_LOOKBACK=24
RECENT_EXTREME_BARS=6
WARMUP=230

# Predeclared, report all. Strength window is 4H BARS.
# 60 bars = 10 days; 120 bars = 20 days.
CONFIGS=[
    ("color_all","color",60,None),
    ("firstfade_all","firstfade",60,None),
    ("color_p80_60","color",60,.8),
    ("firstfade_p80_60","firstfade",60,.8),
    ("crest_p80_60","crest",60,.8),
    ("confirm_p80_60","confirm",60,.8),
    ("crest_p80_120","crest",120,.8),
    ("crest_p90_60","crest",60,.9),
    ("color_p80_120","color",120,.8),
]
EXITS=("fast_invalidation","two_bar_reacceleration")
STOPS=("confirmed_pivot","recent_6bar_extreme")
DIRECTIONS=("LONG","SHORT","BOTH")

def utc(ms):
    return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sign(d):
    if not math.isfinite(d):return 0
    return 1 if d>0 else (-1 if d<0 else 0)

def rank_at_peak(d,peak_i,lookback):
    # Historical values are strictly OLDER than the preceding impulse peak.
    if peak_i<lookback:return None
    hist=d[peak_i-lookback:peak_i]
    if len(hist)!=lookback or not all(math.isfinite(x) for x in hist):
        return None
    amp=abs(d[peak_i])
    return (sum(abs(z)<amp for z in hist)+.5*sum(abs(z)==amp for z in hist))/lookback

def candidates(ind,mode,lookback,threshold):
    d=ind["delta"];color=ind["color"];n=len(d)
    events=[];excluded=Counter();prior_side=0;used=False
    for k in range(max(WARMUP,lookback+70),n-2):
        current=d[k]
        if not math.isfinite(current):
            prior_side=0;used=False;continue
        sg=sign(current)
        if sg != prior_side:
            used=False;prior_side=sg
        if sg==0:continue
        if any(not math.isfinite(d[k-j]) for j in (1,2,3,4)):continue
        a=[abs(d[k-j]) for j in range(5)]
        peak=None
        if mode=="color":
            if (color[k-1]=="mediumR" and color[k]=="weakR") or (
                color[k-1]=="mediumB" and color[k]=="weakB"):
                peak=k-1
        elif mode=="firstfade":
            if sg==sign(d[k-1])==sign(d[k-2]) and a[0]<a[1] and a[1]>=a[2]:
                peak=k-1
        elif mode=="crest":
            if sg==sign(d[k-1])==sign(d[k-2]) and a[0]<a[1] and a[1]>=a[2]:
                preceding=sum(a[j]<a[j+1] for j in (1,2,3))
                if preceding>=2:peak=k-1
        elif mode=="confirm":
            if sg==sign(d[k-1])==sign(d[k-2])==sign(d[k-3]) and a[0]<a[1]<a[2]:
                preceding=sum(a[j]<a[j+1] for j in (2,3))
                # Second fade after at least two rising increments requires
                # reading bar k-5 as well (all already CLOSED).
                if k>=5 and math.isfinite(d[k-5]):
                    growth=sum(abs(d[j])>abs(d[j-1]) for j in range(k-4,k-1))
                    if growth>=2:peak=k-2
        else:raise ValueError(mode)
        if peak is None:continue
        rank=rank_at_peak(d,peak,lookback)
        if rank is None:excluded["unwarmed"]+=1;continue
        if threshold is not None and rank<threshold:
            excluded["below_strength_threshold"]+=1;continue
        if mode in ("crest","confirm") and used:
            excluded["repeat_in_same_signed_impulse"]+=1;continue
        if mode in ("crest","confirm"):used=True
        side=1 if sg<0 else -1
        events.append({
            "i":k,"side":side,"peak_i":peak,"pctl":rank,
            "prev_amp":abs(d[peak]),"current_amp":a[0],
            "relative_fade":(abs(d[peak])-a[0])/max(abs(d[peak]),1e-12)
        })
    return events,dict(excluded)

def initial_stop(bars,k,entry,side,mode):
    if mode=="confirmed_pivot":
        value,j=swing(bars,k,side,PIVOT_LEFT,PIVOT_RIGHT,PIVOT_LOOKBACK)
    elif mode=="recent_6bar_extreme":
        data=bars[max(0,k-RECENT_EXTREME_BARS+1):k+1]
        value=min(z[3] for z in data) if side==1 else max(z[2] for z in data)
        j=None
    else:raise ValueError(mode)
    if value is None:return None,"no_confirmed_pivot"
    level=value*(1-STOP_BUFFER if side==1 else 1+STOP_BUFFER)
    risk=100*side*(entry-level)/entry
    if risk<=0:return None,"stop_wrong_side"
    if risk>MAX_INITIAL_STOP_PCT:return None,"stop_over_15pct"
    return (level,risk,j),None

def signal_exit(ind,k,side,exitmode):
    d=ind["delta"];colors=ind["color"]
    if k<2 or any(not math.isfinite(d[k-j]) for j in (0,1,2)):
        return None
    if side==1:
        opposite=colors[k-1]=="mediumB" and colors[k]=="weakB"
        invalid=colors[k-1]=="weakR" and colors[k] in ("mediumR","strongR")
        accel=d[k]<0 and d[k-1]<0 and d[k-2]<0 and abs(d[k])>abs(d[k-1])>abs(d[k-2])
    else:
        opposite=colors[k-1]=="mediumR" and colors[k]=="weakR"
        invalid=colors[k-1]=="weakB" and colors[k] in ("mediumB","strongB")
        accel=d[k]>0 and d[k-1]>0 and d[k-2]>0 and abs(d[k])>abs(d[k-1])>abs(d[k-2])
    if opposite:return "opposite_delta_fade"
    if exitmode=="opposite_weak":
        weak_opposite=(colors[k]=="weakB") if side==1 else (colors[k]=="weakR")
        if weak_opposite:return "opposite_weak"
        return None
    if exitmode=="opposite_only":return None
    if exitmode=="fast_invalidation" and invalid:return "rebrightening"
    if exitmode=="two_bar_reacceleration" and accel:return "two_bar_reacceleration"
    return None

def replay(bars,ind,events,exitmode,stopmode,direction):
    assert direction in DIRECTIONS
    enabled=[x for x in events if direction=="BOTH" or
             (direction=="LONG" and x["side"]==1) or
             (direction=="SHORT" and x["side"]==-1)]
    byindex={z["i"]:z for z in enabled}
    n=len(bars);k=WARMUP
    completed=[];open_position=[];why_skip=Counter()
    while k<n-1:
        ev=byindex.get(k)
        if not ev:k+=1;continue
        ei=k+1;side=ev["side"];entry=bars[ei][1]
        stoprec,reason=initial_stop(bars,k,entry,side,stopmode)
        if reason:
            why_skip[reason]+=1;k+=1;continue
        stop,risk,pivot_i=stoprec
        end=min(ei+MAX_BARS-1,n-1)
        price=bars[end][4];last=end
        closed_reason="safety_timeout" if end<n-1 else "open_at_data_end"
        for j in range(ei,end+1):
            _,op,hi,lo,cl=bars[j]
            if (lo<=stop if side==1 else hi>=stop):
                price=min(op,stop) if side==1 else max(op,stop)
                last=j;closed_reason="structural_stop";break
            if j+1<=end:
                event=signal_exit(ind,j,side,exitmode)
                if event:
                    price=bars[j+1][1]
                    last=j+1;closed_reason=event;break
        record={
            "signal_index":k,"entry_index":ei,"exit_index":last,
            "signal_time":utc(bars[k][0]+H4),
            "entry_time":utc(bars[ei][0]),
            "exit_time":utc(bars[last][0]),
            "direction":"LONG" if side==1 else "SHORT",
            "entry_price":round(entry,6),"stop_price":round(stop,6),
            "exit_price":round(price,6),"initial_risk_pct":round(risk,5),
            "net_pct":round(100*(side*(price/entry-1)-FEE),6),
            "net_r":round(100*(side*(price/entry-1)-FEE)/risk,6),
            "bars_held":last-ei+1,
            "exit_reason":closed_reason,
            "peak_delta_abs":round(ev["prev_amp"],4),
            "entry_delta_abs":round(ev["current_amp"],4),
            "peak_percentile":round(ev["pctl"]*100,3),
            "peak_age_bars":k-ev["peak_i"],
            "fade_fraction":round(ev["relative_fade"],5),
        }
        if closed_reason=="open_at_data_end":
            open_position.append(record)
        else:
            completed.append(record)
        k=last+1
    why_skip["eligible_events_all"]=len(enabled)
    why_skip["occupied_while_previous_trade_open"]=max(0,len(enabled)-len(completed)-len(open_position)
      -sum(v for name,v in why_skip.items() if name not in ("eligible_events_all",)))
    return completed,open_position,dict(why_skip)

def metrics(trades):
    if not trades:return {"n":0}
    r=[t["net_pct"] for t in trades]
    wins=[x for x in r if x>0]
    losses=[x for x in r if x<0]
    profit=sum(wins);gross_loss=-sum(losses)
    eq=peak=1.;dd=0;eq_risk=peak_risk=1.;dd_risk=0.
    for t in trades:
        eq*=max(.001,1+t["net_pct"]/100)
        peak=max(eq,peak);dd=max(dd,1-eq/peak)
        eq_risk*=max(.001,1+t["net_r"]*.005)
        peak_risk=max(peak_risk,eq_risk);dd_risk=max(dd_risk,1-eq_risk/peak_risk)
    return {
        "n":len(trades),
        "win_rate_pct":round(100*len(wins)/len(r),2),
        "mean_net_pct":round(statistics.mean(r),4),
        "median_net_pct":round(statistics.median(r),4),
        "profit_factor":round(profit/gross_loss,4) if gross_loss else None,
        "mean_r":round(statistics.mean(t["net_r"] for t in trades),4),
        "median_initial_stop_pct":round(statistics.median(t["initial_risk_pct"] for t in trades),3),
        "median_hold_hours":statistics.median(4*t["bars_held"] for t in trades),
        "stops":sum(t["exit_reason"]=="structural_stop" for t in trades),
        "exit_reasons":dict(Counter(x["exit_reason"] for x in trades)),
        "hypothetical_full_notional_compound_pct":round((eq-1)*100,2),
        "hypothetical_closed_trade_maxdd_pct":round(dd*100,2),
        "illustrative_half_percent_initial_risk_compound_pct":round(100*(eq_risk-1),2),
        "illustrative_half_percent_initial_risk_closed_maxdd_pct":round(100*dd_risk,2),
    }

def split_metrics(trades):
    def date(t):return t["entry_time"][:10]
    return {
        "2020_to_2023":metrics([x for x in trades if date(x)<"2024-01-01"]),
        "2024":metrics([x for x in trades if "2024-01-01"<=date(x)<"2025-01-01"]),
        "2025_to_2026":metrics([x for x in trades if date(x)>="2025-01-01"]),
    }

def main():
    output={
        "name":"DeltaPulse 4H research v1 (original symmetric logarithmic DeltaRSI)",
        "research_design":{
            "prespecified_primary":"crest_p80_60_fast_invalidation_confirmed_pivot_LONG",
            "baseline":"color_all_fast_invalidation_confirmed_pivot_LONG",
            "timeframe":"fully closed UTC 4H candle; next 4H open",
            "4h_close_Moscow_clock":"03:00 07:00 11:00 15:00 19:00 23:00 MSK",
            "pulse_strength_window_4h_bars":60,
            "strength_percentile_min":80,
            "impulse_growth":"2 of prior 3 DeltaRSI-magnitude increments positive",
            "pulse_fade":"first magnitude decline after a local peak, same sign",
            "pulse_rearm":"one eligible pulse per continuous signed DeltaRSI episode",
            "direction":"LONG when negative red Delta fades, SHORT when positive blue Delta fades",
            "stop":"confirmed 2-left/1-right local 4H price pivot in preceding 24 bars, 0.1% buffer",
            "max_risk_stop_pct":MAX_INITIAL_STOP_PCT,
            "fee_roundtrip_pct":FEE*100,
            "max_holding_4h_bars":MAX_BARS,
            "volume_or_other_indicators":"none"
        },
        "limitations":[
            "This is an autonomous fixed-rule approximation of user visual trading, not literal replication.",
            "Signals are on completed 4H candles only; no forming 4H / 1H intrabar snapshots.",
            "Market data: Binance USD-M historical 4H perpetual, NOT user's Bybit market. Exchange deviations may change signals.",
            "No indicators besides original signed mirrored-log DeltaRSI; OHLC used solely for structural stops.",
            "Original 60-bar 4H percentile reused from discretionary-selection research; other variants are exploratory and not fitted by search.",
            "BTC 4H history heavily studied already; period splits are descriptive, not pristine OOS.",
            "Only one position per asset, no overlapping trades, no ATR exits or stop, stop fixed for trade lifetime.",
            "Worst-side execution assumed when stop touched; gap through stop filled at adverse 4H open.",
            "Fees+slippage assumed 0.15% roundtrip, funding/liquidation/variable slippage omitted.",
            "Stops 15% away are allowed in simulation; leveraged live use requires much tighter risk sizing and margin monitoring.",
            "Trades that remain open on final history bar are separately marked, not artificially booked.",
            "Portfolio results are illustrative (no overlapping-asset portfolio, funding, or liquidation).",
            "Historical studies at 4H/1D and current market research mean no 100% untouched evaluation data."
        ],
        "assets":{},"comparisons":[]
    }
    primary_log=[]
    for symbol in STARTS:
        bars,source=load(symbol)
        if any(b[0]-a[0]!=H4 for a,b in zip(bars,bars[1:])):
            raise RuntimeError("gap in 4H archive")
        ind=indicator(bars)
        asset={"provenance":source,
               "bars":len(bars),
               "first":utc(bars[0][0]),
               "last_completed":utc(bars[-1][0]+H4),
               "signals":{},"tests":{}}
        for label,mode,lookback,pct in CONFIGS:
            events,drop=candidates(ind,mode,lookback,pct)
            asset["signals"][label]={"n":len(events),
                "long":sum(z["side"]==1 for z in events),
                "short":sum(z["side"]==-1 for z in events),
                "not_eligible":drop}
            for exitmode in EXITS:
                for stopmode in STOPS:
                    for direction in DIRECTIONS:
                        testid=f"{label}_{exitmode}_{stopmode}_{direction}"
                        trades,open_trades,skips=replay(
                            bars,ind,events,exitmode,stopmode,direction)
                        overview=metrics(trades)
                        rec={
                            "config":{"signal":label,"exit":exitmode,
                                "stop":stopmode,"direction":direction},
                            "whole":overview,
                            "by_calendar_period":split_metrics(trades),
                            "skipped":skips,
                            "open_positions_at_archive_end":open_trades
                        }
                        asset["tests"][testid]=rec
                        if (exitmode=="fast_invalidation" and stopmode=="confirmed_pivot" and
                                label in ("color_all","color_p80_60","crest_p80_60","confirm_p80_60") and
                                direction in ("LONG","SHORT")):
                            for t in trades:
                                primary_log.append({"asset":symbol,"configuration":testid,**t})
                        if exitmode=="fast_invalidation" and stopmode=="confirmed_pivot" and direction=="LONG":
                            output["comparisons"].append({"asset":symbol,"signal":label,
                                "whole":overview,
                                "recent":rec["by_calendar_period"]["2025_to_2026"]})
        output["assets"][symbol]=asset
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2))
    with TRADES.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(primary_log[0]))
        writer.writeheader();writer.writerows(primary_log)
    print(json.dumps({
        "asset_provenance":{s:z["provenance"] for s,z in output["assets"].items()},
        "comparisons":output["comparisons"],
        "trade_rows":len(primary_log)
    },indent=2))

if __name__=="__main__":
    main()
