"""One-year ETH 1H/4H/1D DeltaRSI multi-timeframe research; read-only exchange data."""
import csv,datetime as dt,json,math,statistics,time,urllib.parse,urllib.request
from pathlib import Path
from collections import Counter
START=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=365)
HOUR=3600000
OUT=Path("reports");OUT.mkdir(exist_ok=True)
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSIResearch/1.0"})
    with urllib.request.urlopen(req,timeout=35) as f:return json.load(f)
def candles():
    end=int((dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)-dt.timedelta(hours=1)).timestamp()*1000)
    start=int(START.timestamp()*1000)
    for host in ("https://data-api.binance.vision","https://api.binance.us"):
        try:
            rows={};cursor=start
            while cursor<=end:
                q=urllib.parse.urlencode({"symbol":"ETHUSDT","interval":"1h","startTime":cursor,"endTime":end,"limit":1000})
                batch=get(host+"/api/v3/klines?"+q)
                if not batch:raise RuntimeError("Empty response")
                for x in batch:rows[int(x[0])]=(int(x[0]),*map(float,x[1:5]))
                last=int(batch[-1][0])
                if last<cursor:raise RuntimeError("Nonprogressing API")
                cursor=last+HOUR
                time.sleep(.08)
            ordered=[rows[k] for k in sorted(rows) if k<=end]
            if len(ordered)<8000:raise RuntimeError("History unexpectedly short")
            if any(b[0]-a[0]!=HOUR for a,b in zip(ordered,ordered[1:])):raise RuntimeError("Gaps in history")
            print("Fetched",len(ordered),"hours from",host,flush=True)
            return ordered,host
        except Exception as e:print("Source failed",host,str(e),flush=True)
    raise RuntimeError("No continuous 1 year ETH 1H history available")
def aggregate(rows,h):
    groups={}
    for t,o,hi,lo,c in rows:
        bucket=t//(h*HOUR)
        if bucket not in groups:groups[bucket]=[bucket*h*HOUR,o,hi,lo,c]
        else:
            g=groups[bucket];g[2]=max(g[2],hi);g[3]=min(g[3],lo);g[4]=c
    result=[tuple(groups[k]) for k in sorted(groups)]
    return result[:-1] # discard possibly incomplete final higher-timeframe candle
def indicator(rows):
    n=len(rows);s=[math.nan]*n;r=[math.nan]*n;d=[math.nan]*n;color=[""]*n
    rolling=0;ag=al=0;ema=math.nan
    for i,bar in enumerate(rows):
        rolling+=bar[4]
        if i>=21:rolling-=rows[i-21][4]
        if i>=20:s[i]=rolling/21
        if i<32:continue
        change=s[i]-s[i-1]
        if i==32:
            for j in range(21,33):
                v=s[j]-s[j-1];ag+=max(0,v)/12;al+=max(0,-v)/12
        else:ag=(ag*11+max(0,change))/12;al=(al*11+max(0,-change))/12
        r[i]=100 if al==0 else (0 if ag==0 else 100-100/(1+ag/al))
        ema=r[i] if math.isnan(ema) else ema*0.75+r[i]*0.25
        a=100-r[i] if r[i]>50 else r[i];b=100-ema if ema>50 else ema
        if a<=0 or b<=0:continue
        d[i]=(1 if r[i]>ema else -1)*abs(math.log(a/b)*100)
        ab=abs(d[i]);prev=abs(d[i-1])
        if d[i]>0:color[i]="strongB" if ab>60 and d[i]>d[i-1] else ("mediumB" if ab>60 or ab>prev else "weakB")
        elif d[i]<0:color[i]="strongR" if ab>60 and d[i]<d[i-1] else ("mediumR" if ab>60 or ab>prev else "weakR")
    return {"rsi":r,"delta":d,"color":color}
def describe(items):
    if not items:return (0,math.nan,math.nan)
    return (len(items),sum(x>0 for x in items)/len(items)*100,statistics.mean(items))
def main():
    rows,source=candles();r4=aggregate(rows,4);rd=aggregate(rows,24)
    i1=indicator(rows);i4=indicator(r4);id=indicator(rd)
    # Map hourly close to last fully closed 4H/1D candle: their close timestamp must be <= signal close.
    def lookup(t,h,series):
        # signal hourly bar opens at t; its close at t+1h; HTF bar closes at bucket_start+h hours
        idx=(t//(h*HOUR))-1
        if (t+HOUR)%(h*HOUR)==0:idx+=1
        base=series[0][0]//(h*HOUR)
        j=idx-base
        return j if 0<=j<len(series) else -1
    events=[]
    for k in range(200,len(rows)-122):
        prev,cur=i1["color"][k-1],i1["color"][k]
        side=1 if prev=="mediumR" and cur=="weakR" else (-1 if prev=="mediumB" and cur=="weakB" else 0)
        if not side:continue
        t=rows[k][0];a=lookup(t,4,r4);b=lookup(t,24,rd)
        if a<40 or b<40:continue
        entry=rows[k+1][1]
        e={"timestamp_utc":dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),"side":"LONG" if side>0 else "SHORT","rsi_1h":i1["rsi"][k],"rsi_4h":i4["rsi"][a],"rsi_1d":id["rsi"][b],"delta_4h":i4["delta"][a],"delta_1d":id["delta"][b]}
        # Separate approaches to context: extreme / approaching extremes on either or both HTFs
        extreme=lambda v:(v<=30 if side>0 else v>=70)
        near=lambda v:(v<=40 if side>0 else v>=60)
        e["extreme_4h"]=extreme(e["rsi_4h"]);e["extreme_1d"]=extreme(e["rsi_1d"])
        e["near_4h"]=near(e["rsi_4h"]);e["near_1d"]=near(e["rsi_1d"])
        for horizon in (4,12,24,48,72,120):
            e["return_"+str(horizon)+"h_pct"]=side*(rows[k+1+horizon][4]/entry-1)*100
        events.append(e)
    with (OUT/"eth_mtf_events.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(events[0]));w.writeheader();w.writerows(events)
    groups={
        "All color transitions":lambda x:True,
        "4H near extreme (<=40/>=60)":lambda x:x["near_4h"],
        "1D near extreme (<=40/>=60)":lambda x:x["near_1d"],
        "Either 4H or 1D near extreme":lambda x:x["near_4h"] or x["near_1d"],
        "Both 4H and 1D near extreme":lambda x:x["near_4h"] and x["near_1d"],
        "4H extreme (<=30/>=70)":lambda x:x["extreme_4h"],
        "1D extreme (<=30/>=70)":lambda x:x["extreme_1d"],
        "Both 4H and 1D extreme":lambda x:x["extreme_4h"] and x["extreme_1d"],
    }
    lines=["# ETH DeltaRSI MTF exploratory backtest","",f"Source: {source}; hourly candles: {len(rows)}; UTC {dt.datetime.fromtimestamp(rows[0][0]/1000,dt.timezone.utc).date()} to {dt.datetime.fromtimestamp(rows[-1][0]/1000,dt.timezone.utc).date()}.",f"Signals: {len(events)}. Only completed HTF bars. Enter at next 1H open.","", "**Caution:** no fees/funding/slippage; overlapping signals are NOT an executable portfolio; horizons are event-study returns. MTF thresholds are exploratory and not optimized. No forward-looking HTF data.","","| Context | N | 12h win % | 12h mean % | 24h mean % | 48h mean % | 72h mean % | 120h mean % |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for label,condition in groups.items():
        es=[x for x in events if condition(x)]
        if not es:continue
        n,w,m=describe([x["return_12h_pct"] for x in es])
        av=lambda h:statistics.mean(x["return_"+str(h)+"h_pct"] for x in es)
        lines.append(f"| {label} | {n} | {w:.1f} | {m:+.3f} | {av(24):+.3f} | {av(48):+.3f} | {av(72):+.3f} | {av(120):+.3f} |")
    lines+=["","## Split by direction and period","","| Side | Period | N | 12h win % | 12h mean % | 48h mean % |","|---|---|---:|---:|---:|---:|"]
    for side in ("LONG","SHORT"):
        for period,lo,hi in (("2021–2023","2021","2024"),("2024–2026","2024","2027")):
            es=[x for x in events if x["side"]==side and lo<=x["timestamp_utc"][:4]<hi]
            if es:
                n,w,m=describe([x["return_12h_pct"] for x in es])
                lines.append(f"| {side} | {period} | {n} | {w:.1f} | {m:+.3f} | {statistics.mean(x['return_48h_pct'] for x in es):+.3f} |")
    lines+=["","## Reproducibility","","RSI uses SMA(close,21), RSI RMA(12), EMA(RSI,7), signed symmetric log DeltaRSI, threshold 60, exact medium-to-weak color transition. Signals only from closed hourly bars. HTF close must precede or equal signal close. Dataset and events are attached as workflow artifacts. No claim that these filters fully reproduce discretionary trading."]
    (OUT/"eth_mtf_5y.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)
if __name__=="__main__":main()
