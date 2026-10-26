"""Compare two causal DeltaRSI wave-extreme stop placements on strict 4H bars.
One: extreme OHLC of single bar at peak histogram magnitude.
Two: extreme OHLC across whole histogram wave up to signal close.
Entry: medium->weak (late) DeltaRSI; next open.
Stop determined only by bars observed before entry; conservative stop-first.
Exit: 48h with 6 ATR TP OR bright same-direction histogram + rejection wick, max 10d.
"""
import json,math
from pathlib import Path
from feature_walkforward import data,stats,FEE
from analyze_mtf_5y import indicator
from execution_core import resolve_bar
from fade_bright_wick_4h import wick_rejection

def wave_stop(rows,ind,k,side,variant):
    d=ind["delta"]
    if not math.isfinite(d[k]) or d[k]*side>=0:return None
    start=k
    # Restrict current wave to last 60 bars; never inspect future bars.
    while start>0 and k-start<59 and math.isfinite(d[start-1]) and d[start-1]*side<0:
        start-=1
    peak=max(range(start,k+1),key=lambda i:abs(d[i]))
    idx=[peak] if variant=="peak_bar" else list(range(start,k+1))
    raw=min(rows[i][3] for i in idx) if side==1 else max(rows[i][2] for i in idx)
    return raw,peak,start

def run_one(rows,feat,ind,lo,hi,stopmode,exitmode):
    tr=[];records=[];k=max(210,lo)
    while k<min(hi-1,len(rows)-2):
        f=feat[k]
        if not f or not f["late"]:k+=1;continue
        side=f["side"];ei=k+1
        if ei>=hi:break
        w=wave_stop(rows,ind,k,side,stopmode)
        if not w:k+=1;continue
        raw,peak,start=w
        entry=rows[ei][1];atr=f["atr"]
        stop=raw-side*.05*atr
        if (side==1 and stop>=entry) or (side==-1 and stop<=entry):
            k+=1;continue
        risk=abs(entry-stop)/entry
        if risk>.12 or risk<.0005:k+=1;continue
        target=entry+side*6*atr if exitmode=="fixed48" else (1e12 if side==1 else .000001)
        end=min(ei+(12 if exitmode=="fixed48" else 60)-1,hi-1,len(rows)-2)
        out=rows[end][4];ex=end;reason="time"
        for j in range(ei,end+1):
            fill,why=resolve_bar(rows[j],side,stop,target)
            if why:out=fill;ex=j;reason=why;break
            if exitmode=="bright_wick" and j+1<hi and j+1<len(rows):
                col=ind["color"][j]
                bright=col=="strongB" if side==1 else col=="strongR"
                if bright and wick_rejection(rows[j],side,.5):
                    out=rows[j+1][1];ex=j+1;reason="signal";break
        ret=side*(out/entry-1)-FEE
        tr.append((k,ret,side))
        records.append({"entry_bar":ei,"exit_bar":ex,"peak_bar":peak,"wave_start":start,"risk_pct":round(100*risk,3),"return_pct":round(100*ret,3),"reason":reason})
        k=ex+1
    return tr,records

def main():
    out={"notes":"Exploratory historical 4H tests, not untouched OOS. Medium-to-weak DeltaRSI entries at next bar open. Peak-bar stop versus full same-sign wave high/low through signal bar; 0.05 ATR stop buffer, reject risk >12% or <0.05%. Stop-first, 0.15% friction, funding omitted. 48h fixed TP=6 ATR or 10-day bright+50% rejection wick exit.","assets":{}}
    for sym in ("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT"):
        rows,feat=data(sym,aggregation="strict");ind=indicator(rows)
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        cases=[]
        for ex in ("fixed48","bright_wick"):
            for stop in ("peak_bar","wave"):
                splits=[run_one(rows,feat,ind,cuts[i],cuts[i+1],stop,ex) for i in range(3)]
                cases.append({"stop":stop,"exit":ex,"segments":[stats(x[0]) for x in splits],
                              "avg_risk_pct":[round(sum(y["risk_pct"] for y in x[1])/len(x[1]),3) if x[1] else None for x in splits],
                              "sample_trade_records":[x[1][:3] for x in splits]})
        out["assets"][sym]=cases
    Path("reports/wave_peak_stops_4h.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({s:[(x["stop"],x["exit"],[z["mean"] for z in x["segments"]]) for x in a] for s,a in out["assets"].items()}))
if __name__=="__main__":main()
