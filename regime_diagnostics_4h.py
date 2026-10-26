"""Diagnose why DeltaRSI wave-stop 4H performance changes across periods.
Descriptive regime analysis; no new optimization or orders.
"""
import json,math,statistics,datetime as dt
from pathlib import Path
from feature_walkforward import data,stats
from analyze_mtf_5y import indicator
from wave_peak_stops_4h import run_one

def mean(v):
    return round(statistics.mean(v),3) if v else None
def pct(v):
    return round(100*sum(v)/len(v),1) if v else None
def date(t):
    return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime("%Y-%m-%d")
def summary(rows,feat,ind,lo,hi):
    v=[(i,feat[i]) for i in range(max(210,lo),hi) if feat[i]]
    closes=[r[4] for r in rows[lo:hi]]
    returns=[abs(rows[i][4]/rows[i-1][4]-1)*100 for i in range(max(1,lo),hi)]
    wick=[]
    for r in rows[lo:hi]:
        _,o,h,l,c=r;span=h-l
        if span>0:wick.append(max(h-max(o,c),min(o,c)-l)/span)
    return {"start":date(rows[lo][0]),"end":date(rows[hi-1][0]),
      "bars":hi-lo,"price_change_pct":round(100*(closes[-1]/closes[0]-1),2),
      "mean_abs_bar_return_pct":mean(returns),
      "mean_atr_pct":mean([100*f["atr"]/rows[i][4] for i,f in v]),
      "mean_adx":mean([f["adx"] for _,f in v]),
      "adx_ge25_pct":pct([f["adx"]>=25 for _,f in v]),
      "price_above_ema200_pct":pct([f["trend200"] if f["side"]==1 else not f["trend200"] for _,f in v]),
      "mean_largest_wick_fraction":mean(wick),
      "medium_to_weak_signals":sum(f["late"] for _,f in v)}
def trades_by_regime(rows,feat,records):
    groups={}
    for name,fn in (("ADX>=25",lambda f:f["adx"]>=25),
                    ("ADX<25",lambda f:f["adx"]<25),
                    ("high_ATR_percentile",lambda f:f["vp"]>=.5),
                    ("low_ATR_percentile",lambda f:f["vp"]<.5),
                    ("trend_aligned_EMA200",lambda f:f["trend200"]),
                    ("countertrend_EMA200",lambda f:not f["trend200"])):
        x=[(z["entry_bar"],z["return_pct"]) for z in records if feat[z["entry_bar"]-1] and fn(feat[z["entry_bar"]-1])]
        groups[name]={"n":len(x),"mean_return_pct":mean([y for _,y in x]),"win_pct":pct([y>0 for _,y in x])}
    return groups
def main():
    out={"disclaimer":"Descriptive analysis on already inspected history, no OOS; subgroup comparisons are exploratory. Price above EMA200 metric is direct close/EMA and not trend alignment. Trade groups overlap; no statistical significance established.","assets":{}}
    for sym in ("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT"):
        rows,feat=data(sym,aggregation="strict");ind=indicator(rows)
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        periods=[]
        for i in range(3):
            lo,hi=cuts[i:i+2]
            d=summary(rows,feat,ind,lo,hi)
            cases={}
            for stop in ("peak_bar","wave"):
                tr,recs=run_one(rows,feat,ind,lo,hi,stop,"fixed48")
                cases[stop]={"stats":stats(tr),"mean_stop_distance_pct":mean([r["risk_pct"] for r in recs]),
                             "regimes":trades_by_regime(rows,feat,recs)}
            d["stop_comparison"]=cases
            periods.append(d)
        out["assets"][sym]=periods
    Path("reports/regime_diagnostics_4h.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({s:[(p["start"],p["price_change_pct"],p["mean_adx"],p["mean_atr_pct"]) for p in v] for s,v in out["assets"].items()}))
if __name__=="__main__":main()
