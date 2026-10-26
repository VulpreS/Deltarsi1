"""DeltaRSI fade-to-bright with wick rejection, 4H research, no orders.
Signal confirmed at 4H close; next 4H open entry/conditional exit.
OHLC intrabar stop-first; fixed fee 0.15% roundtrip; funding excluded.
"""
import json,math
from pathlib import Path
from feature_walkforward import data,stats,FEE
from analyze_mtf_5y import indicator
from execution_core import resolve_bar
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
MODES=("fixed48","bright","bright_wick","bright_fade","wick_only")
def wick_rejection(bar,side,ratio):
    _,o,h,l,c=bar
    span=h-l
    if span<=0:return False
    body=abs(c-o)
    wick=(h-max(o,c)) if side==1 else (min(o,c)-l)
    opposite=(min(o,c)-l) if side==1 else (h-max(o,c))
    return wick/span>=ratio and wick>=max(body*.75,opposite*1.5)
def simulate(rows,feats,ind,lo,hi,mode,ratio,maxhold):
    trades=[];k=max(lo,210)
    while k<min(hi-1,len(rows)-2):
        f=feats[k]
        # User's medium-to-weak transition, rather than generic turn.
        if not f or not f["late"]:k+=1;continue
        side=f["side"];ei=k+1
        if ei>=hi:break
        entry=rows[ei][1];atr=f["atr"]
        stop=entry-side*2.5*atr
        # Hard catastrophe stop, no fixed target for signal exit variants.
        target=entry+side*6*atr if mode=="fixed48" else (1e12 if side==1 else 0.000001)
        end=min(ei+(12 if mode=="fixed48" else maxhold)-1,hi-1,len(rows)-2)
        out=rows[end][4];reason="time";ex=end
        for j in range(ei,end+1):
            fill,why=resolve_bar(rows[j],side,stop,target)
            if why:
                out=fill;ex=j;reason=why;break
            if mode=="fixed48" or j+1>=hi or j+1>=len(rows):continue
            # A bright impulse in trade direction, not the initial opposite impulse.
            col=ind["color"][j];d=ind["delta"][j]
            bright=(col=="strongB" if side==1 else col=="strongR")
            # Reversal candle needs long wick in direction of profit.
            reject=wick_rejection(rows[j],side,ratio)
            prev=ind["delta"][j-1]
            fade=(math.isfinite(d) and math.isfinite(prev) and side*d>0 and side*prev>0 and abs(d)<abs(prev))
            signal=(bright if mode=="bright" else bright and reject if mode=="bright_wick" else fade and abs(prev)>=60 if mode=="bright_fade" else reject and side*d>0)
            if signal:
                # Only know close at j, execute next OPEN.
                out=rows[j+1][1];ex=j+1;reason="signal";break
        trades.append((k,side*(out/entry-1)-FEE,side))
        k=ex+1
    return trades
def main():
    result={"method":"4H closed-candle medium-to-weak DeltaRSI entry. Conditional exits next 4H open; stop-first conservative, 0.15% roundtrip, no funding. Historical 50/25/25 reused: exploratory, not untouched OOS. Signal exits capped at 10 days; no fixed TP except fixed48 baseline.","assets":{}}
    for sym in SYMS:
        rows,feats=data(sym,aggregation="strict")
        ind=indicator(rows)
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        tests=[]
        for mode in MODES:
            for ratio in ((.35,.50) if mode in ("bright_wick","wick_only") else (.35,)):
                seg=[stats(simulate(rows,feats,ind,cuts[i],cuts[i+1],mode,ratio,60)) for i in range(3)]
                tests.append({"mode":mode,"wick_ratio":ratio if "wick" in mode else None,"segments":seg})
        result["assets"][sym]=tests
    Path("reports/fade_bright_wick_4h.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({s:[(x["mode"],x["wick_ratio"],[v.get("mean") for v in x["segments"]]) for x in a] for s,a in result["assets"].items()}))
if __name__=="__main__":main()
