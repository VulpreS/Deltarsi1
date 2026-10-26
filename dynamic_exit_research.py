"""Research dynamic exits for fixed DeltaRSI+structure entries. No orders."""
import json,statistics
from pathlib import Path
from feature_walkforward import data,stats
from pattern_confluence import flags

SETUPS={"BTCUSDT":("ob_proxy",2.5,4.),"ETHUSDT":("ob_proxy",2.5,6.),"ICPUSDT":("ema200",2.5,4.),"HYPEUSDT":("baseline",2.5,6.)}
FEE=.0015
def simulate(rows,features,lo,hi,sl,tp,method,hold=12):
    trades=[];k=max(210,lo)
    while k<min(hi-1,len(rows)-1):
        f=features[k]
        if not f or not f["turn"]:k+=1;continue
        entryi=k+1
        if entryi>=hi:break
        entry=rows[entryi][1];side=f["side"];atr=f["atr"]
        stop=entry-side*sl*atr;target=entry+side*tp*atr
        end=min(entryi+hold-1,hi-1,len(rows)-1)
        exitprice=rows[end][4]
        for j in range(entryi,end+1):
            _,op,high,low,close=rows[j]
            # Stop/target checks use levels fixed before this bar; stop first.
            if (low<=stop if side==1 else high>=stop):
                exitprice=min(op,stop) if side==1 else max(op,stop)
                end=j;break
            if (high>=target if side==1 else low<=target):
                exitprice=target;end=j;break
            # Trailing and break-even updates only after bar close, for next bar.
            favorable=side*(close-entry)
            if method=="breakeven1" and favorable>=atr:
                stop=max(stop,entry) if side==1 else min(stop,entry)
            elif method=="trail2" and favorable>=atr:
                proposed=close-side*2*atr
                stop=max(stop,proposed) if side==1 else min(stop,proposed)
            elif method=="trail3" and favorable>=2*atr:
                proposed=close-side*3*atr
                stop=max(stop,proposed) if side==1 else min(stop,proposed)
        ret=side*(exitprice/entry-1)-FEE
        trades.append((k,ret,side))
        k=end+1
    return trades

def main():
    out={"notes":"Exploratory historical reuse, not independent OOS. Same fixed entries for exit comparison. Stops evaluated before targets; trailing updated only after close. Conservative gap-through-stop fill. 0.15% fixed costs; no funding.","assets":{}}
    for sym,(pattern,sl,tp) in SETUPS.items():
        rows,features=data(sym)
        ff=[({**f,"turn":f["turn"] and flags(rows,features,i).get(pattern,False)} if f else None) for i,f in enumerate(features)]
        cuts=[0,len(rows)//2,3*len(rows)//4,len(rows)]
        cases=[]
        for method in ("fixed","breakeven1","trail2","trail3"):
            for hold in (12,18,30):
                parts=[stats(simulate(rows,ff,cuts[i],cuts[i+1],sl,tp,method,hold)) for i in range(3)]
                cases.append({"method":method,"hours":hold*4,"segments":parts})
        out["assets"][sym]=cases
    Path("reports/dynamic_exits.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({s:len(v) for s,v in out["assets"].items()}))
if __name__=="__main__":main()
