"""Causal OHLCV liquidity heatmap proxy + DeltaRSI fade interaction study.
NOT CoinGlass liquidation data. Levels are prior confirmed swing extrema.
No future information is used for signal or level construction.
"""
import csv, math, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SRC=Path("data/ETHUSDT_1h.csv")
OUT=Path("reports/eth_liquidity_proxy.md")
LEVELS=Path("reports/eth_liquidity_zones.csv")
HORIZONS=(6,12,24,48,72,120,168)
PIVOT=3
MAX_AGE=24*30
MERGE_PCT=0.0035
NEAR_PCT=0.005
MIN_WARMUP=21+12+7+24*7

def rsi_delta(close):
    n=len(close)
    ma=[None]*n
    for i in range(20,n):
        ma[i]=sum(close[i-20:i+1])/21
    rs=[None]*n; avgg=avgl=None
    for i in range(21,n):
        diff=ma[i]-ma[i-1];g=max(diff,0);l=max(-diff,0)
        if i==32:
            avgg=sum(max(ma[k]-ma[k-1],0) for k in range(21,33))/12
            avgl=sum(max(ma[k-1]-ma[k],0) for k in range(21,33))/12
        elif i>32:
            avgg=(avgg*11+g)/12;avgl=(avgl*11+l)/12
        if i>=32:rs[i]=100 if avgl==0 else 0 if avgg==0 else 100-100/(1+avgg/avgl)
    em=[None]*n;last=None
    for i,r in enumerate(rs):
        if r is None:continue
        last=r if last is None else .25*r+.75*last
        em[i]=last
    delta=[None]*n
    for i,(r,e) in enumerate(zip(rs,em)):
        if r is None:continue
        a=min(r,100-r);b=min(e,100-e)
        if a>0 and b>0:
            v=abs(math.log(a/b)*100)
            delta[i]=v if r>e else -v if r<e else 0
    return delta

def report_events(events,high,low,close):
    lines=["| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |",
           "|---|---:|---:|---:|---:|---:|"]
    for horizon in HORIZONS:
        obs=[]
        for i,side in events:
            if i+horizon>=len(close):continue
            entry=close[i]
            if side==-1:
                ret=(entry-close[i+horizon])/entry*100
                mfe=(entry-min(low[i+1:i+horizon+1]))/entry*100
                mae=(entry-max(high[i+1:i+horizon+1]))/entry*100
            else:
                ret=(close[i+horizon]-entry)/entry*100
                mfe=(max(high[i+1:i+horizon+1])-entry)/entry*100
                mae=(min(low[i+1:i+horizon+1])-entry)/entry*100
            obs.append((ret,mfe,mae))
        if not obs:continue
        mean=lambda k:statistics.fmean(x[k] for x in obs)
        win=sum(x[0]>0 for x in obs)/len(obs)*100
        lines.append(f"| {horizon}h | {len(obs)} | {win:.1f}% | {mean(0):+.3f}% | {mean(1):+.3f}% | {mean(2):+.3f}% |")
    return lines

def main():
    with SRC.open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f))
    rows.sort(key=lambda r:r["timestamp_utc"])
    # Exclude still-forming hourly candles
    now=datetime.now(timezone.utc)
    rows=[r for r in rows if (now-datetime.fromisoformat(r["timestamp_utc"])).total_seconds()>=3600]
    n=len(rows)
    close=[float(r["close"]) for r in rows]
    high=[float(r["high"]) for r in rows]
    low=[float(r["low"]) for r in rows]
    vol=[float(r["volume"]) for r in rows]
    delta=rsi_delta(close)
    zones=[];events=defaultdict(list);snap=[]
    # Candidate zones are only confirmed at time pivot_index+PIVOT.
    # At each bar, signal uses zones already known BEFORE current bar.
    for i in range(MIN_WARMUP,n):
        zones=[z for z in zones if i-z["last"]<=MAX_AGE]
        before=[z.copy() for z in zones]
        d0,d1,d2=delta[i],delta[i-1],delta[i-2]
        fade=(None not in (d0,d1,d2) and d0*d1>0 and abs(d0)<abs(d1) and abs(d1)>abs(d2))
        if fade:
            side=-1 if d0>0 else 1
            relevant=[z for z in before if z["side"]==("high" if side==-1 else "low")]
            # Nearest active level within 0.5% of the current bar close
            near=[z for z in relevant if abs(close[i]/z["price"]-1)<=NEAR_PCT]
            # A wick crosses an existing level and closes back on the prior side.
            swept=[z for z in relevant if (
                high[i]>z["price"] and close[i]<z["price"] and close[i-1]<=z["price"]
                if side==-1 else
                low[i]<z["price"] and close[i]>z["price"] and close[i-1]>=z["price"])]
            events["baseline"].append((i,side))
            if near:events["near"].append((i,side))
            if swept:events["sweep"].append((i,side))
            if not near and not swept:events["away"].append((i,side))
            if near or swept:events["near_or_sweep"].append((i,side))
        # Confirm a pivot PIVOT bars later; do not let it affect earlier signals.
        p=i-PIVOT
        if p>=PIVOT:
            med=statistics.median(vol[max(0,p-24):p+1]) or 1
            for typ,values,is_peak in (("high",high,True),("low",low,False)):
                window=values[p-PIVOT:p+PIVOT+1]
                candidate=values[p]
                confirmed=(candidate==max(window) and window.count(candidate)==1) if is_peak else (candidate==min(window) and window.count(candidate)==1)
                if not confirmed:continue
                weight=min(4.,max(.25,vol[p]/med))
                match=min((z for z in zones if z["side"]==typ and abs(z["price"]/candidate-1)<MERGE_PCT),
                          key=lambda z:abs(z["price"]-candidate),default=None)
                if match is None:
                    zones.append({"side":typ,"price":candidate,"score":weight,"last":i,"touches":1})
                else:
                    match["price"]=(match["price"]*match["score"]+candidate*weight)/(match["score"]+weight)
                    match["score"]+=weight;match["last"]=i;match["touches"]+=1
        if i==n-1:
            snap=sorted(zones,key=lambda z:z["score"],reverse=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with LEVELS.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["side","level_usdt","relative_strength","confirmed_pivots","age_hours","distance_to_close_pct"])
        for z in snap[:100]:
            w.writerow([z["side"],round(z["price"],2),round(z["score"],2),z["touches"],n-1-z["last"],round((z["price"]/close[-1]-1)*100,3)])
    lines=["# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI","",
        f"Period: {rows[0]['timestamp_utc']} to {rows[-1]['timestamp_utc']}; **{n}** closed candles.","",
        "## What the proxy means","",
        "This is **NOT CoinGlass liquidation heatmap**. It uses confirmed local swing highs/lows as potential stop-liquidity clusters, weights them by relative candle volume, merges levels within 0.35%, and expires zones after 30 days without a new confirmed pivot. There is no open-interest, leverage, or actual liquidation-position data.",
        "Swing pivots are confirmed only **3 hours later**; all signals use zones known before the signal candle. A level's strength is a heuristic, not an estimated dollar amount of liquidations.",
        "",
        "## Signal definitions","",
        "- DeltaRSI: SMA21 → RSI12 Wilder → EMA7 → mirrored signed log delta.",
        "- Entry event: first reduction in absolute histogram magnitude after an increase, with same delta sign on both latest bars. This corresponds to fading, not a separately audited exact RGB/color transition.",
        "- Positive delta implies hypothetical short, negative delta hypothetical long.",
        "- Near: relevant prior high (for short) / low (for long) is within 0.5% of signal candle close.",
        "- Sweep: signal candle wicks beyond a pre-existing relevant level, but closes back inside; preceding close must have been on the inside.",
        "- Entry price: signal candle close. MFE/MAE from subsequent candle high/low; intrabar ordering not modeled.",
        "",
        "## Groups"]
    for key,label in (("baseline","All first fades"),("near","First fades near liquidity"),("sweep","First fades with liquidity sweep"),("near_or_sweep","Near or swept"),("away","Away from liquidity")):
        lines+=["",f"### {label} — {len(events[key])} events",""]
        lines+=report_events(events[key],high,low,close)
    lines+=["","## Current strongest heuristic zones","",
            "| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |",
            "|---|---:|---:|---:|---:|"]
    for z in snap[:15]:
        lines.append(f"| {z['side']} | {z['price']:.2f} | {z['score']:.1f} | {z['touches']} | {(z['price']/close[-1]-1)*100:+.2f}% |")
    lines+=["","## Caveats","",
        "- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.",
        "- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.",
        "- MFE/MAE are separate maxima and minima; the ordering is unknown.",
        "- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.",
        "- The mirrored-log RSI delta can have discontinuities around RSI 50.",
        "- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.",
        "- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap."]
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {OUT}, {LEVELS}; "+", ".join(f"{k}={len(v)}" for k,v in events.items()))

if __name__=="__main__":main()
