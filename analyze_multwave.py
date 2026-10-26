"""Causal 2–4 DeltaRSI momentum-wave divergence and liquidity-proxy study.
Waves are confirmed on their first fading bar, never using future pivots.
"""
import csv, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from analyze_liquidity import rsi_delta, report_events, PIVOT, MAX_AGE, MERGE_PCT, NEAR_PCT, MIN_WARMUP

SOURCE=Path("data/ETHUSDT_1h.csv")
OUT=Path("reports/eth_multwave_liquidity.md")
MAX_WAVE_GAP=72
MIN_TROUGH=0.15
MIN_DELTA_DROP=0.08

def main():
    with SOURCE.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    rows=[r for r in rows if (datetime.now(timezone.utc)-datetime.fromisoformat(r["timestamp_utc"])).total_seconds()>=3600]
    close=[float(r["close"]) for r in rows];high=[float(r["high"]) for r in rows]
    low=[float(r["low"]) for r in rows];volume=[float(r["volume"]) for r in rows]
    delta=rsi_delta(close);zones=[];events=defaultdict(list);records=[]
    waves={1:[], -1:[]}
    for i in range(MIN_WARMUP,len(rows)):
        zones=[z for z in zones if i-z["last"]<=MAX_AGE]
        a,b,c=delta[i],delta[i-1],delta[i-2]
        # A wave peak is recognized at first confirmed histogram fading.
        if None not in (a,b,c) and a*b>0 and abs(a)<abs(b) and abs(b)>abs(c):
            sign=1 if a>0 else -1
            side=-1 if sign==1 else 1
            peak=abs(b);peak_i=i-1
            prior=[w for w in waves[sign] if i-w["signal"]<=MAX_WAVE_GAP]
            # Require a meaningful retracement between consecutive momentum peaks.
            qualifying=[]
            for w in reversed(prior):
                if w["peak_i"]>=peak_i-2:continue
                trough=min(abs(delta[k]) for k in range(w["peak_i"]+1,peak_i) if delta[k] is not None)
                if trough <= min(w["peak"],peak)*(1-MIN_TROUGH):
                    qualifying.append(w)
                    break
            last=qualifying[0] if qualifying else None
            price=high[peak_i] if side==-1 else low[peak_i]
            if last is None:
                count=1;div=False
            else:
                count=min(last["count"]+1,5)
                new_extreme=(price>last["price"] if side==-1 else price<last["price"])
                div=new_extreme and peak<=last["peak"]*(1-MIN_DELTA_DROP)
            wave={"signal":i,"peak_i":peak_i,"peak":peak,"price":price,"count":count,"div":div}
            waves[sign].append(wave)
            waves[sign]=[w for w in waves[sign] if i-w["signal"]<=MAX_WAVE_GAP]
            if count in (2,3,4) and div:
                relevant=[z for z in zones if z["side"]==("high" if side==-1 else "low")]
                near=any(abs(close[i]/z["price"]-1)<=NEAR_PCT for z in relevant)
                sweep=any((high[i]>z["price"] and close[i]<z["price"] and close[i-1]<=z["price"]) if side==-1
                    else (low[i]<z["price"] and close[i]>z["price"] and close[i-1]>=z["price"]) for z in relevant)
                events["divergence"].append((i,side))
                events[f"wave_{count}"].append((i,side))
                if near:events["near"].append((i,side))
                if sweep:events["sweep"].append((i,side))
                if near or sweep:events["near_or_sweep"].append((i,side))
                else:events["away"].append((i,side))
                records.append((rows[i]["timestamp_utc"],"short" if side==-1 else "long",count,round(close[i],2),round(peak,3),near,sweep))
        # Add a confirmed pivot only AFTER processing this candle's signal.
        p=i-PIVOT
        if p>=PIVOT:
            med=statistics.median(volume[max(0,p-24):p+1]) or 1
            for typ,values,is_high in (("high",high,True),("low",low,False)):
                window=values[p-PIVOT:p+PIVOT+1];candidate=values[p]
                ok=(candidate==max(window) and window.count(candidate)==1) if is_high else (candidate==min(window) and window.count(candidate)==1)
                if not ok:continue
                weight=min(4.,max(.25,volume[p]/med))
                match=min((z for z in zones if z["side"]==typ and abs(z["price"]/candidate-1)<MERGE_PCT),key=lambda z:abs(z["price"]-candidate),default=None)
                if match is None:zones.append({"side":typ,"price":candidate,"score":weight,"last":i})
                else:
                    match["price"]=(match["price"]*match["score"]+candidate*weight)/(match["score"]+weight)
                    match["score"]+=weight;match["last"]=i
    lines=["# ETHUSDT 1H — multi-wave DeltaRSI divergence × liquidity proxy","",
      f"Dataset: {len(rows)} closed candles, {rows[0]['timestamp_utc']} to {rows[-1]['timestamp_utc']}.","",
      "## Causal wave rule","",
      "- Momentum wave peak is confirmed at the **first fading histogram bar**; entry at that candle close.",
      "- A subsequent same-sign wave must be within 72 hours and separated by a trough at least 15% below the smaller peak.",
      "- Bearish divergence: a higher candle high at momentum peak but a DeltaRSI peak at least 8% lower. Bullish is symmetric using candle lows.",
      "- Waves 2, 3 and 4 are counted from the last qualified same-sign wave. A wave-2 divergence is allowed even if a wave-3/4 divergence does not follow.",
      "- Liquidity proximity: a confirmed historical high/low zone within 0.5% of entry close; sweep: wick crosses zone and closes back inside.",
      "- Zone pivots require three right-hand confirmation candles. Current signals cannot use newly confirmed zones until the following candle.",
      "",
      "## Results by group (directional close-to-close, before fees)"]
    for key,title in (("divergence","All 2–4 wave divergences"),("wave_2","Wave 2 divergences"),("wave_3","Wave 3 divergences"),("wave_4","Wave 4 divergences"),("near","Divergences near liquidity"),("sweep","Divergences with sweep"),("near_or_sweep","Divergences near or swept"),("away","Divergences away from liquidity")):
        lines+=["",f"### {title}: {len(events[key])} signals",""]
        if events[key]:lines+=report_events(events[key],high,low,close)
        else:lines+=["No qualifying events."]
    lines+=["","## Most recent qualifying events","",
            "| UTC | Direction | Wave | Entry USDT | Delta peak | Near zone | Sweep |",
            "|---|---|---:|---:|---:|---|---|"]
    for ts,side,count,price,peak,near,sweep in records[-20:]:
        lines.append(f"| {ts} | {side} | {count} | {price} | {peak} | {'yes' if near else 'no'} | {'yes' if sweep else 'no'} |")
    lines+=["","## Limitations","",
        "- This is a defined, exploratory 2–4-wave interpretation, not a claim that the user's visual wave counting is identical.",
        "- These are stop-liquidity proxies based on historical OHLCV, **not** actual CoinGlass liquidation clusters.",
        "- No commissions, slippage, funding, stop/TP, or intrabar execution-order modeling.",
        "- Overlapping event horizons violate independent-trial assumptions; small groups are unstable.",
        "- Parameters were chosen heuristically and have not been validated out of sample.",
        "- This uses first absolute-magnitude fading, not an exact comparison of Pine rendered RGB shades."]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {OUT}; "+", ".join(f"{k}={len(v)}" for k,v in events.items()))
if __name__=="__main__":main()
