"""Exploratory confluence tests: DeltaRSI + EMA, sweep, engulfing and OB proxy.
All patterns use completed 4H candles. Entry on next open; fixed exits.
Order-block proxy is not exchange orderflow. Historical splits are contaminated
by previous strategy selection; results are exploratory only. No orders.
"""
import json
from pathlib import Path
from feature_walkforward import data,sim,stats

ASSETS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
EXITS=((2.5,6.,12),(1.5,6.,12),(2.5,4.,12),(1.5,6.,60))
FILTERS=("baseline","ema20_50","ema200","sweep5","sweep10","engulf","ob_proxy","sweep5_ema","ob_ema")

def flags(rows,feats,i):
    if i<25 or not feats[i]:return {}
    side=feats[i]["side"]
    o,h,l,c=rows[i][1:]
    po,ph,pl,pc=rows[i-1][1:]
    prevlo=min(x[3] for x in rows[i-5:i])
    prevhi=max(x[2] for x in rows[i-5:i])
    lo10=min(x[3] for x in rows[i-10:i])
    hi10=max(x[2] for x in rows[i-10:i])
    sweep5=(l<prevlo and c>prevlo) if side==1 else (h>prevhi and c<prevhi)
    sweep10=(l<lo10 and c>lo10) if side==1 else (h>hi10 and c<hi10)
    engulf=(c>o and pc<po and c>=po and o<=pc) if side==1 else (c<o and pc>po and c<=po and o>=pc)
    # Operationalized order block: last opposite-color candle before displacement
    # and retest within last 6 bars. Only known candles, no future pivots.
    ob=False
    for j in range(i-6,i-1):
        oo,hh,ll,cc=rows[j][1:]
        if (cc<oo if side==1 else cc>oo):
            following=rows[j+1:i]
            displacement=(max(x[4] for x in following)>hh if side==1 else min(x[4] for x in following)<ll)
            retest=(l<=hh and c>ll) if side==1 else (h>=ll and c<hh)
            if displacement and retest:
                ob=True
                break
    e=feats[i]
    trend=e["trend20"]
    return {"baseline":True,"ema20_50":trend,"ema200":e["trend200"],
            "sweep5":sweep5,"sweep10":sweep10,"engulf":engulf,
            "ob_proxy":ob,"sweep5_ema":sweep5 and trend,"ob_ema":ob and trend}

def main():
    report={"disclaimer":"EXPLORATORY ONLY: all 50/25/25 segments previously observed in other research. Pattern definitions are OHLC proxies; order block is NOT observed orderbook liquidity. 0.15% round-trip costs, funding omitted.","assets":{}}
    for sym in ASSETS:
        rows,base=data(sym)
        allflags=[flags(rows,base,i) for i in range(len(rows))]
        cuts=(0,len(rows)//2,3*len(rows)//4,len(rows))
        cases=[]
        for name in FILTERS:
            ff=[({**f,"turn":f["turn"] and allflags[i].get(name,False)} if f else None) for i,f in enumerate(base)]
            for sl,tp,hold in EXITS:
                cfg=("turn","none","none",sl,tp,hold,"both")
                seg=[stats(sim(rows,ff,cfg,cuts[k],cuts[k+1])[0]) for k in range(3)]
                cases.append({"filter":name,"sl":sl,"tp":tp,"hold_hours":hold*4,"segments":seg})
        report["assets"][sym]=cases
    Path("reports/pattern_confluence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({s:{"variants":len(v),"signals":sum(x["segments"][0]["n"] for x in v)} for s,v in report["assets"].items()}))
if __name__=="__main__":main()
