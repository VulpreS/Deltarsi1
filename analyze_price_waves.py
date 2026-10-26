"""Price-wave divergence vs DeltaRSI histogram peaks; one-year ETH, no lookahead."""
import csv,datetime as dt,math,statistics
from pathlib import Path
from analyze_mtf_5y import indicator,aggregate
DATA=Path("data/ETHUSDT_1h.csv"); OUT=Path("reports");OUT.mkdir(exist_ok=True)
def load():
    with DATA.open(newline="") as f:
        a=list(csv.DictReader(f))
    cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=365)
    rows=[]
    for x in a:
        t=dt.datetime.fromisoformat(x["timestamp_utc"])
        if t>=cutoff:rows.append((int(t.timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]))
    if len(rows)<8000:raise RuntimeError("Need one year of 1h candles; run fetch_eth.py first")
    return rows
def pivots(rows,lag=3):
    # Only know pivot at i+lag. Alternating confirmed price highs/lows.
    raw=[]
    for i in range(lag,len(rows)-lag):
        high=all(rows[i][2]>rows[j][2] for j in range(i-lag,i+lag+1) if j!=i)
        low=all(rows[i][3]<rows[j][3] for j in range(i-lag,i+lag+1) if j!=i)
        if high and not low:raw.append((i,"H",rows[i][2],i+lag))
        if low and not high:raw.append((i,"L",rows[i][3],i+lag))
    result=[]
    for p in raw:
        if result and p[1]==result[-1][1]:
            if (p[1]=="H" and p[2]>result[-1][2]) or (p[1]=="L" and p[2]<result[-1][2]):result[-1]=p
        else:result.append(p)
    return result
def main():
    rows=load();a=indicator(rows);r4=aggregate(rows,4);rd=aggregate(rows,24);i4=indicator(r4);id=indicator(rd)
    ps=pivots(rows);peaks=[]
    # A wave is a completed price leg ending at a confirmed price pivot;
    # histogram peak measured during that price leg, no zero crossing needed.
    for n in range(1,len(ps)):
        start,end=ps[n-1],ps[n];typ=end[1]
        vals=[a["delta"][j] for j in range(start[0]+1,end[0]+1) if math.isfinite(a["delta"][j])]
        vals=[v for v in vals if v>0] if typ=="H" else [-v for v in vals if v<0]
        if vals:peaks.append({"idx":end[0],"confirm":end[3],"type":typ,"price":end[2],"strength":max(vals)})
    events=[];last_by_type={"H":[],"L":[]}
    # At every 1H bar, only consider price pivots that are already confirmed.
    cursor=0
    for k in range(200,len(rows)-122):
        while cursor<len(peaks) and peaks[cursor]["confirm"]<=k:
            p=peaks[cursor];last_by_type[p["type"]].append(p);cursor+=1
        side=1 if a["color"][k-1]=="mediumR" and a["color"][k]=="weakR" else (-1 if a["color"][k-1]=="mediumB" and a["color"][k]=="weakB" else 0)
        if not side:continue
        typ="L" if side==1 else "H"
        candidates=last_by_type[typ]
        if len(candidates)<2:continue
        # Require latest pivot confirmation within the past 18 bars, to avoid stale divergence.
        latest=candidates[-1]
        if k-latest["confirm"]>18:continue
        def div(p,q):
            return (q["price"]<p["price"] if typ=="L" else q["price"]>p["price"]) and q["strength"]<p["strength"]
        wave2=div(candidates[-2],candidates[-1])
        wave3=len(candidates)>=3 and div(candidates[-3],candidates[-2]) and div(candidates[-2],candidates[-1])
        if not wave2:continue
        # last completed higher-timeframe bars at signal close
        t=rows[k][0]
        def htf(h,series,ind):
            close=t+3600000;bucket=(close//(h*3600000))-1
            j=bucket-series[0][0]//(h*3600000)
            return ind["rsi"][j] if 0<=j<len(series) else math.nan
        rsi4=htf(4,r4,i4);rsi1d=htf(24,rd,id)
        entry=rows[k+1][1]
        e={"timestamp_utc":dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),"side":"LONG" if side==1 else "SHORT","wave_count":3 if wave3 else 2,"pivot1_price":candidates[-2]["price"],"pivot2_price":latest["price"],"hist_peak1":candidates[-2]["strength"],"hist_peak2":latest["strength"],"rsi_4h":rsi4,"rsi_1d":rsi1d}
        for h in (4,12,24,48,72,120):e[f"return_{h}h_pct"]=side*(rows[k+1+h][4]/entry-1)*100
        events.append(e)
    if not events:raise RuntimeError("No divergence events found")
    with (OUT/"eth_price_wave_divergence_events.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=events[0].keys());w.writeheader();w.writerows(events)
    groups={"2+ waves":lambda e:True,"3+ waves":lambda e:e["wave_count"]==3,"2+ waves and 4H RSI near extreme":lambda e:e["rsi_4h"]<=40 if e["side"]=="LONG" else e["rsi_4h"]>=60,"2+ waves and 1D RSI near extreme":lambda e:e["rsi_1d"]<=40 if e["side"]=="LONG" else e["rsi_1d"]>=60,"2+ waves and both HTFs near extreme":lambda e:(e["rsi_4h"]<=40 and e["rsi_1d"]<=40) if e["side"]=="LONG" else (e["rsi_4h"]>=60 and e["rsi_1d"]>=60),"LONG only":lambda e:e["side"]=="LONG","SHORT only":lambda e:e["side"]=="SHORT"}
    lines=["# ETH 1H price-wave / DeltaRSI histogram divergence","",f"One-year saved candles: {len(rows)}; divergence events: {len(events)}.","","**Algorithm**: 3-left/3-right confirmed swing price pivots, alternating highs/lows; compare successive price highs/lows with histogram strength peaks over corresponding price legs. A 2-wave divergence requires higher price high and lower positive histogram peak (SHORT), or lower price low and smaller-magnitude negative peak (LONG). A 3-wave divergence requires two consecutive comparisons. Confirmation lag 3 bars; entry next 1H open on exact medium-to-weak color transition within 18h after confirmed last pivot. No histogram zero crossing requirement.","","**Limitations:** pivot definition is an approximation of visual wave counting. The 3-wave condition is strict and exploratory. Event-study, not sequential trades; overlapping signals possible; returns exclude fees, funding, slippage and stops. 4H/1D RSI uses fully closed bars only.","","| Filter | N | 12h win % | 12h mean % | 24h mean % | 48h mean % | 72h mean % | 120h mean % |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name,filterfn in groups.items():
        v=[e for e in events if filterfn(e)]
        if not v:continue
        m=lambda h:statistics.mean(e[f"return_{h}h_pct"] for e in v)
        w=sum(e["return_12h_pct"]>0 for e in v)/len(v)*100
        lines.append(f"| {name} | {len(v)} | {w:.1f} | {m(12):+.3f} | {m(24):+.3f} | {m(48):+.3f} | {m(72):+.3f} | {m(120):+.3f} |")
    (OUT/"eth_price_wave_divergence.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)
if __name__=="__main__":main()
