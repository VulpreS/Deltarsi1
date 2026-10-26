"""Extended ETH DeltaRSI histogram fading study. Run after fetch_eth.py.
Exact signed mirrored-log formula from Delta, with TradingView-like Wilder RSI seed.
Signals at CLOSED bars only. Event study, not an executable backtest.
"""
import csv
import math
from pathlib import Path

DATA=Path("data/ETHUSDT_1h.csv")
OUT=Path("reports/eth_extended.md")
HORIZONS=(6,12,24,48,72,120,168)

def sma(v,n):
    s=0.;out=[]
    for i,x in enumerate(v):
        s+=x
        if i>=n:s-=v[i-n]
        out.append(s/n if i>=n-1 else None)
    return out

def rma_rsi(src,n=12):
    out=[None]*len(src)
    first=next(i for i,v in enumerate(src) if v is not None)
    gains=[];losses=[]
    for i in range(first+1,first+n+1):
        d=src[i]-src[i-1];gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains)/n;al=sum(losses)/n
    for i in range(first+n,len(src)):
        if i>first+n:
            d=src[i]-src[i-1]
            ag=(ag*(n-1)+max(d,0))/n;al=(al*(n-1)+max(-d,0))/n
        out[i]=100 if al==0 else 0 if ag==0 else 100-100/(1+ag/al)
    return out

def ema(v,n=7):
    out=[None]*len(v);last=None;a=2/(n+1)
    for i,x in enumerate(v):
        if x is None:continue
        last=x if last is None else a*x+(1-a)*last
        out[i]=last
    return out

def summarize(events,close,high,low):
    lines=["| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |",
           "|---|---:|---:|---:|---:|---:|"]
    for h in HORIZONS:
        obs=[]
        for i,side in events:
            if i+h>=len(close):continue
            entry=close[i]
            # short for positive delta, long for negative
            direction=-1 if side>0 else 1
            ret=direction*(close[i+h]/entry-1)*100
            if direction==1:
                mfe=(max(high[i+1:i+h+1])/entry-1)*100
                mae=(min(low[i+1:i+h+1])/entry-1)*100
            else:
                mfe=(1-min(low[i+1:i+h+1])/entry)*100
                mae=(1-max(high[i+1:i+h+1])/entry)*100
            obs.append((ret,mfe,mae))
        if not obs:continue
        avg=lambda k:sum(x[k] for x in obs)/len(obs)
        win=sum(x[0]>0 for x in obs)/len(obs)*100
        lines.append(f"| {h}h | {len(obs)} | {win:.1f}% | {avg(0):+.3f}% | {avg(1):+.3f}% | {avg(2):+.3f}% |")
    return lines

def main():
    with DATA.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    rows.sort(key=lambda r:r["timestamp_utc"])
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc)
    rows=[r for r in rows if (now-datetime.fromisoformat(r["timestamp_utc"])).total_seconds()>=3600]
    close=[float(r["close"]) for r in rows]
    high=[float(r["high"]) for r in rows]
    low=[float(r["low"]) for r in rows]
    rsi=rma_rsi(sma(close,21))
    sig=ema(rsi)
    delta=[]
    for a,b in zip(rsi,sig):
        if a is None or b is None:delta.append(None);continue
        ma=min(a,100-a);mb=min(b,100-b)
        if ma<=0 or mb<=0:delta.append(None);continue
        mag=abs(math.log(ma/mb)*100)
        delta.append(mag if a>b else -mag if a<b else 0.)
    first=[];all_fading=[];color_transitions=[]
    def intensity(v,prev):
        # original Pine uses strong bright >60 when growing; medium if fading
        if v is None or prev is None or v==0:return None
        mag=abs(v)
        if mag>60:return 0 if mag>abs(prev) else 45
        return (55 if v>0 else 60) if mag>abs(prev) else 80
    for i in range(2,len(delta)):
        a,b,c=delta[i-2:i+1]
        if None in (a,b,c) or c==0 or b==0:continue
        if math.copysign(1,b)!=math.copysign(1,c):continue
        faded=abs(c)<abs(b)
        if faded:
            all_fading.append((i,c))
            if abs(b)>abs(a):first.append((i,c))
            if intensity(c,b)>intensity(b,a):color_transitions.append((i,c))
    lines=["# ETHUSDT 1H — extended DeltaRSI study","",
        f"Period: {rows[0]['timestamp_utc']} to {rows[-1]['timestamp_utc']}; **{len(rows)}** closed candles.","",
        "Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.",
        "For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.",
        "Entry is the close of the fading candle; returns are directional close-to-close.",
        "MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.",
        "","## First fading bar after a growing bar",f"Events: **{len(first)}**.",""]
    lines+=summarize(first,close,high,low)
    lines+=["","## All fading bars",f"Events: **{len(all_fading)}**.",""]+summarize(all_fading,close,high,low)
    lines+=["","## Actual Pine color transitions to less intense shades",
            f"Events: **{len(color_transitions)}**.",""]+summarize(color_transitions,close,high,low)
    lines+=["","## Important limitations",
        "- Event study, not trade-by-trade PnL: events can overlap and cluster.",
        "- No commissions, spread, funding, slippage or liquidation.",
        "- Mean MFE and mean MAE are separate extrema; their ordering is unknown.",
        "- No wave-number stratification yet; color transitions and fading are evaluated separately.",
        "- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.",
        "- A 365-day sample still requires out-of-sample testing before drawing trading conclusions."]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {OUT}; first={len(first)}, all={len(all_fading)}, colors={len(color_transitions)}")

if __name__=="__main__":main()
