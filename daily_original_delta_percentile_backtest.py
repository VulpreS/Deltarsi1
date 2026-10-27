"""Daily (1D) application of the trader's ORIGINAL DeltaRSI and percentile idea.

Uses BTCUSDT/ETHUSDT Binance USD-M futures archives since 2019 (exchange proxy
for user's Bybit trades). Downloads calendar-complete daily bars; rejects
interior gaps. No exchange keys, trading, training-set optimization or orders.
The original Pine formula is calculated by analyze_mtf_5y.indicator unchanged.

Daily signal variants:
  color: mediumR->weakR LONG / mediumB->weakB SHORT
  first_fade: first decline in |Delta| after a non-declining bar, same sign.
Fixed historical strength percentiles: none / prior60 percentile>=.80 / >=.90.
One-position sequential mechanical test, next-day open, price-structure stop,
opposite Delta fading exit, optional same-impulse rebrightening invalidation,
0.15% notional roundtrip cost. Results are not user-replicating real trades.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
import csv
import datetime as dt
import io
import json
import math
import statistics
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from analyze_mtf_5y import indicator
from structural_delta_strategy import swing

UTC=dt.timezone.utc
DAY_MS=86_400_000
FEE=.0015
SYMBOLS=("BTCUSDT","ETHUSDT")
FIRST_MONTH={"BTCUSDT":(2019,9),"ETHUSDT":(2019,11)}
OUT=Path("reports/daily_original_delta_percentile_backtest.json")
CACHE=Path("data")
WINDOW=60
MIN_HISTORY=40
SAFETY_DAYS=90
PIVOT_LEFT=2
PIVOT_RIGHT=1
PIVOT_LOOKBACK=20
MAX_STOP_PCT=15.
BUFFER=.001
EVENT_MODES=("color","first_fade")
PCTS=(None,.8,.9)
EXIT_MODES=("opposite_only","rebrighten_plus_opposite")
STOP_MODES=("confirmed_pivot","recent_5d_extreme")
HORIZONS=(3,7,14,30)

def iso(ms):
    return dt.datetime.fromtimestamp(ms/1000,UTC).strftime("%Y-%m-%d")

def monthiter(y,m,until_y,until_m):
    while (y,m)<=(until_y,until_m):
        yield y,m
        if m==12:y+=1;m=1
        else:m+=1

def data_links(symbol,last_closed):
    y0,m0=FIRST_MONTH[symbol]
    current_month=(last_closed.year,last_closed.month)
    tasks=[]
    for y,m in monthiter(y0,m0,last_closed.year,last_closed.month):
        if (y,m)==current_month:break
        file=f"{symbol}-1d-{y}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/1d/{file}"
        tasks.append(("month",f"{y}-{m:02d}",url))
    month_begin=dt.date(last_closed.year,last_closed.month,1)
    day=month_begin
    while day<=last_closed:
        # Archive publishing may lag 1-2 days. Treat only terminal omissions
        # as incomplete (and explicitly disclose them).
        daycode=day.strftime("%Y-%m-%d")
        file=f"{symbol}-1d-{daycode}.zip"
        url=f"https://data.binance.vision/data/futures/um/daily/klines/{symbol}/1d/{file}"
        tasks.append(("day",daycode,url))
        day+=dt.timedelta(days=1)
    return tasks

def fetch_archive(task):
    _,label,url=task
    last_err=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSIHistoricalStudy/1.0"})
            with urllib.request.urlopen(req,timeout=22) as stream:
                payload=stream.read()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names=[x for x in archive.namelist() if x.endswith(".csv")]
                if len(names)!=1:raise RuntimeError("archive CSV count != 1")
                with archive.open(names[0]) as f:
                    lines=csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig"))
                    rows=[]
                    for row in lines:
                        try:
                            t=int(row[0])
                            if t>10**14:t//=1000
                            open_,hi,low,close=map(float,row[1:5])
                            if t%DAY_MS or not 0<low<=min(open_,close)<=max(open_,close)<=hi:
                                raise RuntimeError(f"bad OHLC {label} {row[:5]}")
                            rows.append((t,open_,hi,low,close))
                        except ValueError:
                            if row and row[0].lower() in ("open_time","open time"):continue
                            raise
            return label,rows,None
        except urllib.error.HTTPError as e:
            last_err=f"HTTP {e.code}"
            if e.code==404:break
        except Exception as e:
            last_err=f"{type(e).__name__}: {str(e)[:100]}"
        if attempt<2:time.sleep(.4*(attempt+1))
    return label,[],last_err

def load_market(symbol):
    path=CACHE/f"{symbol}_1d_binance_um.csv"
    today=dt.datetime.now(UTC).date()
    last_closed=today-dt.timedelta(days=1)
    # Archive publication is delayed. Accept fresh cached data to avoid
    # relying on a changing public endpoint for repeated audits.
    if path.exists():
        with path.open() as f:
            cached=[(int(r["open_ms"]),*[float(r[z]) for z in ("open","high","low","close")])
                    for r in csv.DictReader(f)]
        if cached and dt.date.fromtimestamp(cached[-1][0]/1000)>=last_closed-dt.timedelta(days=3):
            return cached,{"source":"cached Binance USD-M 1D archives","cached":True,
                "first":iso(cached[0][0]),"last":iso(cached[-1][0]),"rows":len(cached)}
    tasks=data_links(symbol,last_closed)
    rows_by_time={}
    errors=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        work={pool.submit(fetch_archive,task):task for task in tasks}
        for job in as_completed(work):
            label,rows,err=job.result()
            if err:errors.append((label,err))
            for r in rows:
                if r[0] in rows_by_time and rows_by_time[r[0]]!=r:
                    raise RuntimeError(f"conflicting OHLC at {label} {r[0]}")
                if r[0]<=int(dt.datetime.combine(last_closed,dt.time(),UTC).timestamp()*1000):
                    rows_by_time[r[0]]=r
    rows=[rows_by_time[k] for k in sorted(rows_by_time)]
    if len(rows)<1000:raise RuntimeError(f"{symbol}: only {len(rows)} daily bars; errors: {errors[:8]}")
    gaps=[(iso(a[0]),iso(b[0]),round((b[0]-a[0])/DAY_MS))
          for a,b in zip(rows,rows[1:]) if b[0]-a[0]!=DAY_MS]
    if gaps:raise RuntimeError(f"{symbol}: internal historical daily data gaps {gaps[:10]}, archive errors {errors[:10]}")
    if rows[-1][0]<int(dt.datetime.combine(last_closed-dt.timedelta(days=5),dt.time(),UTC).timestamp()*1000):
        raise RuntimeError(f"{symbol}: recent archives missing beyond 5 days, last {iso(rows[-1][0])}, errors {errors[-10:]}")
    CACHE.mkdir(exist_ok=True)
    with path.open("w") as f:
        writer=csv.writer(f)
        writer.writerow(["open_ms","open","high","low","close"])
        writer.writerows(rows)
    return rows,{"source":"Binance USD-M BTC/ETH perpetual daily archival klines, not Bybit",
        "archive_url_pattern":"https://data.binance.vision/data/futures/um/monthly/klines/<SYMBOL>/1d/",
        "cached":False,"first":iso(rows[0][0]),"last":iso(rows[-1][0]),"rows":len(rows),
        "archive_errors":errors,"unavailable_archive_count":len(errors)}

def delta_event(ind,i,mode):
    d=ind["delta"];colors=ind["color"]
    if i<3 or not all(math.isfinite(d[j]) for j in (i-2,i-1,i)):
        return 0
    if mode=="color":
        if colors[i-1]=="mediumR" and colors[i]=="weakR":return 1
        if colors[i-1]=="mediumB" and colors[i]=="weakB":return -1
        return 0
    if mode=="first_fade":
        if d[i]*d[i-1]<=0 or d[i-1]*d[i-2]<=0:return 0
        if abs(d[i])<abs(d[i-1]) and abs(d[i-1])>=abs(d[i-2]):
            return 1 if d[i]<0 else -1
        return 0
    raise ValueError(mode)

def past_percentile(ind,i):
    # Candidate magnitude is value on bar i-1. Compare ONLY against
    # bars i-61..i-2; do not include current bar or target in history.
    d=ind["delta"]
    if i<WINDOW+2 or not math.isfinite(d[i-1]):return None
    historical=[abs(d[j]) for j in range(i-WINDOW-1,i-1) if math.isfinite(d[j])]
    if len(historical)<MIN_HISTORY:return None
    target=abs(d[i-1])
    return (sum(x<target for x in historical)+.5*sum(x==target for x in historical))/len(historical)

def candidates(rows,ind,mode):
    out=[]
    excluded=Counter()
    for i in range(110,len(rows)-2):
        side=delta_event(ind,i,mode)
        if not side:continue
        p=past_percentile(ind,i)
        if p is None:
            excluded["no_60day_strength_history"]+=1
            continue
        out.append({"index":i,"utc_signal_date":iso(rows[i][0]),
            "side":side,"strength_percentile":p,
            "prev_delta_abs":abs(ind["delta"][i-1]),
            "signal_delta_abs":abs(ind["delta"][i])})
    return out,dict(excluded)

def structural_stop(rows,signal_i,entry,side,mode):
    if mode=="confirmed_pivot":
        level,pivot_index=swing(rows,signal_i,side,
                                 PIVOT_LEFT,PIVOT_RIGHT,PIVOT_LOOKBACK)
    elif mode=="recent_5d_extreme":
        recent=rows[signal_i-4:signal_i+1]
        level=min(x[3] for x in recent) if side==1 else max(x[2] for x in recent)
        pivot_index=None
    else:raise ValueError(mode)
    if level is None:return None,"no_confirmed_pivot"
    stop=level*(1-BUFFER if side==1 else 1+BUFFER)
    risk=side*(entry-stop)
    if risk<=0:return None,"stop_on_wrong_side"
    if risk/entry*100>MAX_STOP_PCT:return None,"risk_gt_15pct"
    return {"stop":stop,"risk_pct":100*risk/entry,"pivot_i":pivot_index},None

def exit_signal(ind,i,side,event_mode,exit_mode):
    """Only past CLOSED bar state; return a reason or None."""
    c=ind["color"];d=ind["delta"]
    if i<2:return None
    if exit_mode=="rebrighten_plus_opposite":
        if event_mode=="color":
            invalid=(c[i-1]=="weakR" and c[i] in ("mediumR","strongR")) if side==1 else (
                     c[i-1]=="weakB" and c[i] in ("mediumB","strongB"))
        else:
            invalid=(d[i]<0 and d[i-1]<0 and abs(d[i])>abs(d[i-1])) if side==1 else (
                     d[i]>0 and d[i-1]>0 and abs(d[i])>abs(d[i-1]))
        if invalid:return "rebrightening"
    opposite=delta_event(ind,i,event_mode)==-side
    if opposite:return "opposite_fade"
    return None

def simulate(rows,ind,events,percentile,mode,exit_mode,stop_mode,only_side=None):
    allowed=[x for x in events if (percentile is None or x["strength_percentile"]>=percentile)
             and (only_side is None or x["side"]==only_side)]
    by_index={x["index"]:x for x in allowed}
    n=len(rows);k=110;trades=[];issues=Counter()
    while k<n-1:
        event=by_index.get(k)
        if event is None:
            k+=1;continue
        side=event["side"]
        entry_i=k+1
        entry=rows[entry_i][1]
        risk,err=structural_stop(rows,k,entry,side,stop_mode)
        if err:
            issues[err]+=1;k+=1;continue
        stop=risk["stop"]
        # Exits may occur on last available closed day or administrative cap.
        end_i=min(entry_i+SAFETY_DAYS-1,n-1)
        exit_i=end_i;exit_price=rows[end_i][4]
        why="safety_timeout" if end_i< n-1 else "end_of_data"
        for j in range(entry_i,end_i+1):
            o,h,l,c=rows[j][1:5]
            breached=(l<=stop if side==1 else h>=stop)
            if breached:
                # If price GAPS through stop overnight, fill at worse open.
                exit_price=min(o,stop) if side==1 else max(o,stop)
                exit_i=j;why="structural_stop";break
            if j+1<n and j+1<=end_i:
                signal=exit_signal(ind,j,side,mode,exit_mode)
                if signal:
                    exit_price=rows[j+1][1]
                    exit_i=j+1;why=signal;break
        ret=side*(exit_price/entry-1)-FEE
        duration=exit_i-entry_i+ (1 if why in ("structural_stop","safety_timeout","end_of_data") else 0)
        trades.append({"signal_i":k,"entry_i":entry_i,"exit_i":exit_i,
            "signal_date_utc":iso(rows[k][0]),"entry_date_utc":iso(rows[entry_i][0]),
            "exit_date_utc":iso(rows[exit_i][0]),
            "direction":"LONG" if side==1 else "SHORT",
            "entry":round(entry,2),"stop":round(stop,2),"exit":round(exit_price,2),
            "initial_risk_pct":round(risk["risk_pct"],3),
            "net_pct":round(ret*100,4),"net_r":round(ret*100/risk["risk_pct"],4),
            "bars_held":duration,"reason":why,
            "strength_percentile":round(100*event["strength_percentile"],2),
            "delta_prev_abs":round(event["prev_delta_abs"],3),
            "delta_signal_abs":round(event["signal_delta_abs"],3)})
        k=exit_i+1  # never open overlapping positions; exit-bar entry avoided
    issues["eligible_signal_events"]=len(allowed)
    issues["not_taken_due_to_held_position"]=max(0,len(allowed)-len(trades)-sum(v for key,v in issues.items() if key not in ("eligible_signal_events",)))
    return trades,dict(issues)

def stats(trades):
    if not trades:return {"n":0}
    r=[z["net_pct"]/100 for z in trades]
    a=[x for x in r if x>0];b=[x for x in r if x<=0]
    gross=sum(a);loss=-sum(b)
    capital=peak=1.;maxdd=0.
    for x in r:
        capital*=max(.0001,1+x)
        peak=max(peak,capital)
        maxdd=max(maxdd,1-capital/peak)
    return {"n":len(trades),"win_rate_pct":round(100*len(a)/len(r),2),
       "mean_net_pct":round(100*statistics.mean(r),3),
       "median_net_pct":round(100*statistics.median(r),3),
       "profit_factor":round(gross/loss,3) if loss else None,
       "avg_win_pct":round(100*statistics.mean(a),3) if a else None,
       "avg_loss_pct":round(100*statistics.mean(b),3) if b else None,
       "median_initial_risk_pct":round(statistics.median(t["initial_risk_pct"] for t in trades),3),
       "mean_R":round(statistics.mean(t["net_r"] for t in trades),3),
       "median_days_held":round(statistics.median(t["bars_held"] for t in trades),1),
       "hypothetical_sequential_full_notional_compound_pct":round(100*(capital-1),2),
       "hypothetical_closed_trade_mdd_pct":round(100*maxdd,2),
       "exit_reasons":dict(Counter(x["reason"] for x in trades)),
       "by_side":{side:{"n":len(v),
                  "mean_net_pct":round(statistics.mean(x["net_pct"] for x in v),3),
                  "win_rate_pct":round(100*sum(x["net_pct"]>0 for x in v)/len(v),2),
                  "profit_factor":round(sum(max(x["net_pct"],0) for x in v)/(-sum(min(x["net_pct"],0) for x in v)),3)
                           if any(x["net_pct"]<0 for x in v) else None}
                  for side in ("LONG","SHORT") if (v:=[x for x in trades if x["direction"]==side])}}

def walkforward_by_entry(rows,trades):
    # Break at 60%/80% of calendar bars; trades assigned on ENTRY day.
    # All parameters are frozen in advance; no fit/optimization.
    n=len(rows);cuts=[0,int(.6*n),int(.8*n),n]
    result={}
    for i,label in enumerate(("early_60pct","middle_20pct","recent_20pct")):
        seg=[x for x in trades if cuts[i]<=x["entry_i"]<cuts[i+1]]
        result[label]={"from_date":iso(rows[cuts[i]][0]),
            "to_date":iso(rows[cuts[i+1]-1][0]),"statistics":stats(seg)}
    return result

def forwards(rows,events,percentile):
    group=[e for e in events if percentile is None or e["strength_percentile"]>=percentile]
    out={}
    for horizon in HORIZONS:
        gains=[100*(e["side"]*(rows[e["index"]+horizon][4]/rows[e["index"]+1][1]-1)-FEE)
               for e in group if e["index"]+horizon < len(rows)]
        out[f"forward_{horizon}d_net_pct"]={"n":len(gains),
            "mean":round(statistics.mean(gains),4) if gains else None,
            "median":round(statistics.median(gains),4) if gains else None,
            "positive_pct":round(100*sum(x>0 for x in gains)/len(gains),2) if gains else None}
    return out

def main():
    output={
      "notes":[
       "1D original DeltaRSI: SMA21(close), RSI12(RMA), EMA7, mirrored log, color threshold 60, unchanged.",
       "Binance USDT-M BTC/ETH daily perpetual bars, not user's Bybit BTCUSDT candles. Exchange-specific daily boundaries and historical price paths may change signals.",
       "Daily candles close 00:00 UTC (03:00 Moscow), not at 11:00 MSK like the user's 4H reference.",
       "Entry next 1D bar open after confirmed close; strictly point-in-time prior-60 daily Delta magnitudes.",
       "Percentile 80/90 thresholds are exploratory prior hypotheses from 4H and have NOT been optimized on this data. 1D and 4H behavior may differ.",
       "Confirmed price pivot left2 right1 within last20 daily bars, stop beyond pivot by 0.1% price; recent5-day low/high alternate structural sensitivity. No ATR stops.",
       "Stop checked first on every daily OHLC bar, including gap-through fill at adverse open. OHLC cannot know exact intraday crossing order; stop-first conservative.",
       "Exit next-day open on opposite fading Delta or optional early original-impulse rebrightening. 90d administrative maximum, not user trading instruction.",
       "Closed-trade returns apply fixed 0.15% notional roundtrip fees+slippage. Funding omitted, mark-price stops and execution not independently verified.",
       "Trade-level full-notional compounding and MDD illustrative only, NOT true leveraged portfolio MDD. No simultaneous positions within one asset. Separate LONG-only and SHORT-only replays recompute eligibility without opposite positions blocking signals.",
       "Assign trades to chronological segments by entry timestamp; positions may close after segment boundary. All prior BTC history previously analyzed; no pristine OOS.",
       "Mechanical results do not reconstruct trader's visual discretion, intraday partial daily bars, moving stop changes or partial exit fills."
      ],
      "fee_roundtrip_pct":.15,"safety_hold_days":SAFETY_DAYS,
      "signal_modes":{"color":"mediumR->weakR LONG / mediumB->weakB SHORT",
                      "first_fade":"first decrease of abs(log-Delta) following a nondecreasing impulse, same sign"},
      "assets":{},"headline_configs":{},
    }
    for symbol in SYMBOLS:
        rows,provenance=load_market(symbol)
        ind=indicator(rows)
        missing=sum(not math.isfinite(x) for x in ind["delta"][110:])
        asset={"data":provenance,"n_nan_indicator_after_110_bars":missing,
               "signal_counts":{},"configurations":{},
               "selected_trades":{}}
        for event_mode in EVENT_MODES:
            events,excluded=candidates(rows,ind,event_mode)
            asset["signal_counts"][event_mode]={"all":len(events),
                  "at_or_above_p80":sum(x["strength_percentile"]>=.8 for x in events),
                  "at_or_above_p90":sum(x["strength_percentile"]>=.9 for x in events),
                  "by_side":dict(Counter("LONG" if x["side"]>0 else "SHORT" for x in events)),
                  "excluded":excluded}
            for pct in PCTS:
                for stop_mode in STOP_MODES:
                    for exit_mode in EXIT_MODES:
                        label=f"{event_mode}_p{int(pct*100) if pct is not None else 0}_{stop_mode}_{exit_mode}"
                        trade,skips=simulate(rows,ind,events,pct,event_mode,exit_mode,stop_mode)
                        record={"parameters":{"entry_signal":event_mode,"min_percentile":pct,
                            "structural_stop":stop_mode,"exit":exit_mode},
                            "entry_signal_diagnostics":skips,
                            "all_history":stats(trade),
                            "chronological":walkforward_by_entry(rows,trade),
                            "future_returns_at_all_signals":forwards(rows,events,pct)}
                        if stop_mode=="confirmed_pivot":
                            solo={}
                            for direction,dname in ((1,"LONG"),(-1,"SHORT")):
                                solo_trades,solo_issues=simulate(rows,ind,events,pct,event_mode,exit_mode,stop_mode,only_side=direction)
                                solo[dname]={"all_history":stats(solo_trades),
                                    "chronological":walkforward_by_entry(rows,solo_trades),
                                    "signal_diagnostics":solo_issues}
                            record["direction_only_replays"]=solo
                        asset["configurations"][label]=record
                        # Preserve all trades for primary structural stop, plus recent
                        # 5d sensitivity of the main 80th-percentile model only.
                        if stop_mode=="confirmed_pivot" or (pct==.8 and stop_mode=="recent_5d_extreme" and exit_mode=="rebrighten_plus_opposite"):
                            asset["selected_trades"][label]=trade
        output["assets"][symbol]=asset
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2,ensure_ascii=False))
    # Compact machine-readable stdout only; all raw data in report.
    names=[
      "color_p0_confirmed_pivot_opposite_only",
      "color_p80_confirmed_pivot_rebrighten_plus_opposite",
      "first_fade_p0_confirmed_pivot_rebrighten_plus_opposite",
      "first_fade_p80_confirmed_pivot_rebrighten_plus_opposite",
      "first_fade_p90_confirmed_pivot_rebrighten_plus_opposite",
      "first_fade_p80_recent_5d_extreme_rebrighten_plus_opposite",
    ]
    compact={}
    for symbol,asset in output["assets"].items():
        compact[symbol]={"data":asset["data"],"signals":asset["signal_counts"],
           "rows_missing_delta":asset["n_nan_indicator_after_110_bars"],
           "configs":{name:{"all":asset["configurations"][name]["all_history"],
                             "recent":asset["configurations"][name]["chronological"]["recent_20pct"]["statistics"]}
                         for name in names}}
    print(json.dumps(compact,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
