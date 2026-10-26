"""Exit-on-opposite-DeltaRSI and structure-break experiment. Research only."""
import json
from pathlib import Path
from feature_walkforward import data,stats
from pattern_confluence import flags
from dynamic_exit_research import SETUPS,FEE
from execution_core import resolve_bar

def sim(rows,features,lo,hi,sl,tp,mode,raw_features=None):
    if raw_features is None:
        raw_features=features
    trades=[];k=max(210,lo)
    while k<min(hi-1,len(rows)-1):
        f=features[k]
        if not f or not f["turn"]:k+=1;continue
        start=k+1
        if start>=hi:break
        side=f["side"];entry=rows[start][1];stop=entry-side*sl*f["atr"];target=entry+side*tp*f["atr"]
        end=min(start+11,hi-1,len(rows)-1);out=rows[end][4]
        for j in range(start,end+1):
            _,op,high,low,close=rows[j]
            fill,reason=resolve_bar(rows[j],side,stop,target)
            if reason:
                out=fill;end=j;break
            # At the close of bar j, decide whether to exit at bar j+1 OPEN.
            if j+1<=end:
                rev=raw_features[j] and raw_features[j]["turn"] and raw_features[j]["side"]==-side
                structural=(close<min(x[3] for x in rows[j-3:j]) if side==1 else close>max(x[2] for x in rows[j-3:j]))
                if (mode=="reverse" and rev) or (mode=="structure" and structural) or (mode=="both" and (rev or structural)):
                    out=rows[j+1][1];end=j+1;break
        trades.append((k,side*(out/entry-1)-FEE,side))
        k=end+1
    return trades

def main():
    output={"caution":"Exploratory reused historical data, not independent OOS; no funding; raw opposite DeltaRSI signal confirmed at close and executed next open. One trade per asset. No real orders.","assets":{}}
    for sym,(name,sl,tp) in SETUPS.items():
        rows,features=data(sym)
        filtered=[({**f,"turn":f["turn"] and flags(rows,features,i).get(name,False)} if f else None) for i,f in enumerate(features)]
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        results=[]
        for mode in ("fixed","reverse","structure","both"):
            segments=[stats(sim(rows,filtered,cuts[i],cuts[i+1],sl,tp,mode,raw_features=features)) for i in range(3)]
            results.append({"exit":mode,"segments":segments})
        output["assets"][sym]=results
    Path("reports/structural_exits.json").write_text(json.dumps(output,indent=2))
    print(json.dumps({s:[(x["exit"],[v.get("mean") for v in x["segments"]]) for x in a] for s,a in output["assets"].items()}))
if __name__=="__main__":main()
