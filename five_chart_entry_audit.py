"""Audit five user-marked BTC 4H entries against cached UTC candles.
Chart timezone unknown; scan UTC offsets -12..+14h in 1h steps.
Never claim chart drawings are fills; rank by entry price proximity.
"""
import json,datetime as dt,math
from pathlib import Path
from feature_walkforward import data
from analyze_mtf_5y import indicator
CASES=[
 ("L1","2026-09-25 23:00",1,83982.00),
 ("L2","2026-10-01 15:00",1,83897.79),
 ("L3","2026-09-18 15:00",1,78793.30),
 ("S1","2026-09-22 07:00",-1,85668.69),
 ("S2","2026-10-05 15:00",-1,86192.72),
]
def iso(ms):return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).isoformat()
def detail(rows,ind,i,side):
    d=ind["delta"];c=ind["color"]
    history=[]
    for j in range(max(0,i-12),i+5):
        if j>=len(rows):break
        r=rows[j]
        history.append({"utc":iso(r[0]),"ohlc":[round(v,2) for v in r[1:]],"delta":round(d[j],2) if math.isfinite(d[j]) else None,"color":c[j]})
    preceding=[j for j in range(max(0,i-24),i+1) if math.isfinite(d[j]) and side*d[j]<0]
    peak=max(preceding,key=lambda j:abs(d[j])) if preceding else None
    return {"utc":iso(rows[i][0]),"ohlc":[round(v,2) for v in rows[i][1:]],
            "delta":round(d[i],2),"color":c[i],
            "peak_opposite_bar_24":iso(rows[peak][0]) if peak is not None else None,
            "peak_opposite_delta":round(d[peak],2) if peak is not None else None,
            "recent_bars":history}
def main():
    rows,_=data("BTCUSDT",aggregation="strict");ind=indicator(rows)
    out={"note":"Chart tool left-edge times read visually, not exchange fills. Screenshot timezone unknown. Price entry need not equal candle open; rank using candle low-high inclusion and distance to OHLC. 4H UTC bars are fully closed. 1h hourly offset scan, no future indicators used for entries.","cases":[]}
    for name,when,side,entry in CASES:
        local=dt.datetime.strptime(when,"%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
        matches=[]
        for offset in range(-12,15):
            t=(local-dt.timedelta(hours=offset)).timestamp()*1000
            for i,r in enumerate(rows):
                if abs(r[0]-t)>4*3600000:continue
                o,h,l,c=r[1:]
                dist=0 if l<=entry<=h else min(abs(entry-l),abs(entry-h))
                # Penalize timestamp mismatch; timezone unknown so display both.
                score=100*dist/entry+abs(r[0]-t)/3600000*.03
                matches.append({"offset_chart_minus_utc_h":offset,"time_delta_h":round((r[0]-t)/3600000,2),"price_distance_pct":round(100*dist/entry,3),"score":round(score,3),"bar":detail(rows,ind,i,side)})
        matches.sort(key=lambda x:(x["score"],abs(x["offset_chart_minus_utc_h"]-3),abs(x["time_delta_h"])))
        # Capture candidates for common UTC offsets +3,0,+4 and best fit.
        fixed={}
        for off in (0,3,4):
            sub=[m for m in matches if m["offset_chart_minus_utc_h"]==off]
            if sub:fixed[str(off)]=min(sub,key=lambda x:x["score"])
        out["cases"].append({"id":name,"chart_time":when,"side":"LONG" if side==1 else "SHORT","entry_price":entry,"best_8":matches[:8],"offset_examples":fixed})
    # Shared timezone scoring based on whether the entry price lies in the 4h candle range
    offset_rank=[]
    for off in range(-12,15):
        a=[min((m for m in case["best_8"]+list(case["offset_examples"].values()) if m["offset_chart_minus_utc_h"]==off),key=lambda m:m["score"],default=None) for case in out["cases"]]
        if all(a):offset_rank.append({"offset":off,"total_score":round(sum(x["score"] for x in a),3)})
    out["offset_rank_partial"]=sorted(offset_rank,key=lambda x:x["total_score"])
    Path("reports/five_chart_entry_audit.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps([{"id":x["id"],"best":[{"offset":y["offset_chart_minus_utc_h"],"utc":y["bar"]["utc"],"distance":y["price_distance_pct"],"delta":y["bar"]["delta"],"color":y["bar"]["color"]} for y in x["best_8"][:3]]} for x in out["cases"]],ensure_ascii=False))
if __name__=="__main__":main()
