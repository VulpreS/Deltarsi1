"""Analyze DeltaRSI wave divergences from hourly ETHUSDT candles.
Uses SMA(21), Wilder RSI(12), EMA(7), and original mirrored log delta.
Signals are confirmed only on closed candles. Exploratory statistics, not a trading system.
"""
import csv
import math
from pathlib import Path

DATA = Path("data/ETHUSDT_1h.csv")
REPORT = Path("reports/eth_1h.md")

def sma(values, n):
    return [None if i < n - 1 else sum(values[i-n+1:i+1])/n for i in range(len(values))]

def ema(values, n):
    out = [None]*len(values)
    alpha = 2/(n+1)
    last = None
    for i,v in enumerate(values):
        if v is None: continue
        last = v if last is None else alpha*v+(1-alpha)*last
        out[i]=last
    return out

def rsi_rma(src, n=12):
    out=[None]*len(src)
    valid=[i for i,v in enumerate(src) if v is not None]
    if len(valid)<n+1: return out
    start=valid[0]
    gains=[];losses=[]
    for i in range(start+1,start+n+1):
        d=src[i]-src[i-1];gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains)/n; al=sum(losses)/n
    for i in range(start+n,len(src)):
        if i>start+n:
            d=src[i]-src[i-1]
            ag=(ag*(n-1)+max(d,0))/n
            al=(al*(n-1)+max(-d,0))/n
        out[i]=100 if al==0 else 0 if ag==0 else 100-100/(1+ag/al)
    return out

def main():
    with DATA.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    rows.sort(key=lambda x:x["timestamp_utc"])
    # Exclude unfinished hourly candle.
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc)
    rows=[r for r in rows if (now-datetime.fromisoformat(r["timestamp_utc"])).total_seconds()>=3600]
    closes=[float(r["close"]) for r in rows]
    highs=[float(r["high"]) for r in rows]
    lows=[float(r["low"]) for r in rows]
    dates=[r["timestamp_utc"] for r in rows]
    rsi=rsi_rma(sma(closes,21),12)
    signal=ema(rsi,7)
    delta=[]
    for a,b in zip(rsi,signal):
        if a is None or b is None: delta.append(None);continue
        am=min(a,100-a);bm=min(b,100-b)
        if am<=0 or bm<=0: delta.append(None);continue
        d=abs(math.log(am/bm)*100)
        delta.append(d if a>b else -d if a<b else 0.0)
    # Positive histogram waves: consecutive >0 segments; compare each peak
    # with previous positive wave's peak, and corresponding price highs.
    waves=[];active=[]
    for i,d in enumerate(delta+[None]):
        if d is not None and d>0:
            active.append(i)
        elif active:
            peak=max(active,key=lambda k:abs(delta[k]))
            waves.append({"peak":peak,"high":max(highs[k] for k in active),"strength":abs(delta[peak]),
                          "end":active[-1],"start":active[0]})
            active=[]
    divs=[]
    for prev,cur in zip(waves,waves[1:]):
        if cur["high"]>prev["high"] and cur["strength"]<prev["strength"]:
            # Detection only after the second wave ends, avoiding hindsight.
            k=cur["end"]
            if k+1<len(closes):
                divs.append((prev,cur,k))
    lines=["# ETHUSDT 1H — DeltaRSI exploratory report","",
           f"Closed candles: **{len(rows)}**; from {dates[0] if dates else 'N/A'} to {dates[-1] if dates else 'N/A'}.",
           "","## Method",
           "SMA(21) → Wilder RSI(12) → EMA(7), then mirrored logarithmic delta exactly as in Delta.",
           "A bearish divergence is counted when a completed positive-delta wave has a higher price high but a lower delta peak than the preceding positive wave.",
           "This is a retrospective structural study, not an executable entry strategy. Wave completion is known only after crossing zero.",
           "","## Results",f"Completed positive waves: **{len(waves)}**.",
           f"Bearish wave divergences: **{len(divs)}**.","",
           "| Wave confirmed UTC | Price high previous → current | Delta peak previous → current | Return next 6h | Return next 12h |",
           "|---|---:|---:|---:|---:|"]
    def ret(k,h):
        return f"{(closes[k+h]/closes[k]-1)*100:+.2f}%" if k+h<len(closes) else "N/A"
    for p,c,k in divs:
        lines.append(f"| {dates[k]} | {p['high']:.2f} → {c['high']:.2f} | {p['strength']:.2f} → {c['strength']:.2f} | {ret(k,6)} | {ret(k,12)} |")
    lines+=["","## Limitations",
            "- No commissions, spread, funding or slippage included.",
            "- The sample is short; results cannot establish predictive edge.",
            "- The symmetric transform may create artificial zero readings around RSI 50.",
            "- Signals at first histogram fading require a separate non-lookahead backtest."]
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {REPORT}; {len(divs)} divergences")

if __name__=="__main__":
    main()
