"""Reproducible multi-asset DeltaRSI research. No exchange orders."""
import csv,datetime as dt,json,math,statistics,time,urllib.parse,urllib.request
from pathlib import Path
from execution_core import resolve_bar
from analyze_mtf_5y import indicator,aggregate
ROOT=Path("data");ROOT.mkdir(exist_ok=True);OUT=Path("reports");OUT.mkdir(exist_ok=True)
H=3600000; FEE=0.0015 # round trip taker 0.11% + 0.04% total slippage
SYMS=["ETHUSDT","BTCUSDT","ICPUSDT","HYPEUSDT"]
def fetch(sym):
    path=ROOT/(sym+"_1h.csv")
    if path.exists():
        with path.open() as f: rr=list(csv.DictReader(f))
        if len(rr)>=5000:
            print("CACHED",sym,len(rr),flush=True)
            return [(int(dt.datetime.fromisoformat(x["timestamp_utc"]).timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]) for x in rr]
    end=int((dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)-dt.timedelta(hours=1)).timestamp()*1000)
    start=end-365*24*H
    errors=[]
    for host in ("https://data-api.binance.vision","https://api.binance.com","https://api.binance.us"):
        try:
            found={};cursor=start
            while cursor<=end:
                q=urllib.parse.urlencode({"symbol":sym,"interval":"1h","startTime":cursor,"endTime":end,"limit":1000})
                req=urllib.request.Request(host+"/api/v3/klines?"+q,headers={"User-Agent":"Research/1.0"})
                with urllib.request.urlopen(req,timeout=35) as res:batch=json.load(res)
                if not batch:break
                for x in batch:found[int(x[0])]=(int(x[0]),*map(float,x[1:5]))
                nxt=int(batch[-1][0])+H
                if nxt<=cursor:break
                cursor=nxt;time.sleep(.07)
            rows=[found[k] for k in sorted(found)]
            if len(rows)<5000:raise ValueError("Too few candles "+str(len(rows)))
            if any(b[0]-a[0]!=H for a,b in zip(rows,rows[1:])):raise ValueError("Gap")
            save(path,rows);print("DOWNLOADED",sym,len(rows),host,flush=True)
            return rows
        except Exception as e:errors.append(host+":"+str(e)[:120])
    # Bybit fallback, read backwards; HYPE listing can differ.
    try:
        found={};cursor=end
        while cursor>=start:
            q=urllib.parse.urlencode({"category":"linear","symbol":sym,"interval":"60","end":cursor,"limit":1000})
            req=urllib.request.Request("https://api.bybit.com/v5/market/kline?"+q,headers={"User-Agent":"Research/1.0"})
            with urllib.request.urlopen(req,timeout=35) as res:obj=json.load(res)
            batch=obj["result"]["list"]
            if not batch:break
            for x in batch:
                t=int(x[0])
                if start<=t<=end:found[t]=(t,*map(float,x[1:5]))
            nxt=min(int(x[0]) for x in batch)-H
            if nxt>=cursor:break
            cursor=nxt;time.sleep(.07)
        rows=[found[k] for k in sorted(found)]
        if len(rows)<5000:raise ValueError("Too few candles "+str(len(rows)))
        if any(b[0]-a[0]!=H for a,b in zip(rows,rows[1:])):raise ValueError("Gap")
        save(path,rows);print("DOWNLOADED",sym,len(rows),"Bybit",flush=True)
        return rows
    except Exception as e:errors.append("Bybit:"+str(e)[:120])
    if sym=="HYPEUSDT":
        try:
            found={}
            for lo in range(start,end+1,3000*H):
                hi=min(end,lo+3000*H-H)
                payload=json.dumps({"type":"candleSnapshot","req":{"coin":"HYPE","interval":"1h","startTime":lo,"endTime":hi}}).encode()
                req=urllib.request.Request("https://api.hyperliquid.xyz/info",data=payload,headers={"Content-Type":"application/json","User-Agent":"Research/1.0"})
                with urllib.request.urlopen(req,timeout=45) as res:batch=json.load(res)
                for x in batch:
                    t=int(x["t"])
                    if start<=t<=end:found[t]=(t,float(x["o"]),float(x["h"]),float(x["l"]),float(x["c"]))
                time.sleep(.1)
            rows=[found[k] for k in sorted(found)]
            if len(rows)<5000:raise ValueError("Too few Hyperliquid candles "+str(len(rows)))
            if any(b[0]-a[0]!=H for a,b in zip(rows,rows[1:])):raise ValueError("Hyperliquid gap")
            save(path,rows);print("DOWNLOADED",sym,len(rows),"Hyperliquid",flush=True)
            return rows
        except Exception as e:errors.append("Hyperliquid:"+str(e)[:150])
    raise RuntimeError(sym+" "+repr(errors))
def save(path,rows):
    with path.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["timestamp_utc","open","high","low","close"])
        for t,*v in rows:w.writerow([dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),*v])
def ema(vals,n):
    out=[];v=None
    for x in vals:
        v=x if v is None else v+(x-v)*2/(n+1);out.append(v)
    return out
def atr(rows,n=14):
    out=[];v=None
    for k,x in enumerate(rows):
        tr=max(x[2]-x[3],abs(x[2]-rows[k-1][4]),abs(x[3]-rows[k-1][4])) if k else x[2]-x[3]
        v=tr if v is None else (v*(n-1)+tr)/n;out.append(v)
    return out
def waves(rows,delta,lag=2):
    # Each price pivot becomes known only lag bars AFTER the extreme.
    states=[(0,0)]*len(rows);low=[];high=[];events={}
    for k in range(lag,len(rows)-lag):
        l=all(rows[k][3]<rows[j][3] for j in range(k-lag,k+lag+1) if j!=k)
        h=all(rows[k][2]>rows[j][2] for j in range(k-lag,k+lag+1) if j!=k)
        if l!=h:events.setdefault(k+lag,[]).append((k,"L" if l else "H"))
    for k in range(len(rows)):
        for idx,typ in events.get(k,[]):
            hist=low if typ=="L" else high
            # Histogram wave strength measured between consecutive opposite price pivots.
            prior=next((p for p in reversed(high if typ=="L" else low) if p[0]<idx),None)
            if prior is None:continue
            vals=[delta[j] for j in range(prior[0]+1,idx+1) if math.isfinite(delta[j])]
            vals=[-v for v in vals if v<0] if typ=="L" else [v for v in vals if v>0]
            if not vals:continue
            price=rows[idx][3 if typ=="L" else 2]
            hist.append((idx,price,max(vals),k))
        def div(hist,typ):
            if len(hist)<2:return 0
            a,b=hist[-2:]
            more=lambda x,y:y[1]<x[1] if typ=="L" else y[1]>x[1]
            two=more(a,b) and b[2]<a[2]
            three=len(hist)>=3 and more(hist[-3],b) and more(a,b) and b[2]<hist[-3][2]
            if k-b[3]>8:return 0
            return 3 if three else (2 if two else 0)
        states[k]=(div(low,"L"),div(high,"H"))
    return states
def prepare(sym,tf,raw):
    rows=aggregate(raw,tf)
    if len(rows)<100:return None
    ind=indicator(rows);close=[x[4] for x in rows];d=ind["delta"];colors=ind["color"]
    av=atr(rows);fast=ema(close,20);slow=ema(close,50)
    w=waves(rows,d)
    signals=[]
    for k in range(70,len(rows)-1):
        if not math.isfinite(d[k]) or not math.isfinite(d[k-1]):continue
        side=1 if d[k]<0 else -1
        if d[k]*d[k-1]<=0:continue
        early=(colors[k-1]=="strongR" and colors[k]=="mediumR") if side==1 else (colors[k-1]=="strongB" and colors[k]=="mediumB")
        late=(colors[k-1]=="mediumR" and colors[k]=="weakR") if side==1 else (colors[k-1]=="mediumB" and colors[k]=="weakB")
        turn=abs(d[k])<abs(d[k-1]) and abs(d[k-1])>=abs(d[k-2]) and abs(d[k-1])>=15
        early=early and abs(d[k])<abs(d[k-1])
        if not (early or late or turn):continue
        signals.append((k,side,early,late,turn,w[k][0 if side==1 else 1],(close[k]>slow[k] if side==1 else close[k]<slow[k]),(fast[k]>slow[k] if side==1 else fast[k]<slow[k]),ind["rsi"][k],av[k]))
    return rows,signals
def simulate(data,config,cut,start=0):
    rows,sigs=data
    mode,div,trend,stop,target,hold,side_mode=config
    equity=1.;peak=1.;dd=0.;trades=[];until=-1
    for k,side,early,late,turn,w,t1,t2,rsi,a in sigs:
        if k<=until or k<70 or k<start:continue
        # Embargo the last 'hold' signal bars in train: no test-period
        # prices may influence a training trade's realized PnL.
        if cut>0 and k+hold>=cut:continue
        if side_mode=="long" and side!=1:continue
        if side_mode=="short" and side!=-1:continue
        if mode=="early" and not early:continue
        if mode=="late" and not late:continue
        if mode=="turn" and not turn:continue
        if w<div:continue
        if trend=="slow" and not t1:continue
        if trend=="both" and not t2:continue
        if trend=="extreme" and not (rsi<=40 if side==1 else rsi>=60):continue
        entry_i=k+1
        if entry_i>=len(rows):continue
        entry=rows[entry_i][1];sl=entry-side*stop*a;tp=entry+side*target*a
        end=min(entry_i+hold-1,len(rows)-1);exit_price=rows[end][4];reason="time"
        for j in range(entry_i,end+1):
            fill,fill_reason=resolve_bar(rows[j],side,sl,tp)
            if fill_reason:
                exit_price=fill;reason=fill_reason
                end=j;break
        ret=side*(exit_price/entry-1)-FEE
        trades.append((k,ret,reason,side))
        equity*=max(.001,1+ret);peak=max(peak,equity);dd=max(dd,1-equity/peak)
        until=end
    return trades,dd
def metric(trades):
    x=[t[1] for t in trades]
    if not x:return {"n":0,"win":None,"avg":None,"pf":None,"net":None}
    p=sum(max(0,z) for z in x);l=-sum(min(0,z) for z in x)
    return {"n":len(x),"win":round(100*sum(z>0 for z in x)/len(x),1),"avg":round(100*statistics.mean(x),3),"pf":round(p/l,3) if l else None,"net":round(100*(math.prod(1+z for z in x)-1),2)}
def main():
    datasets={};status={}
    for sym in SYMS:
        try:
            raw=fetch(sym);status[sym]={"hours":len(raw),"first":dt.datetime.fromtimestamp(raw[0][0]/1000,dt.timezone.utc).date().isoformat(),"last":dt.datetime.fromtimestamp(raw[-1][0]/1000,dt.timezone.utc).date().isoformat()}
            for tf in (4,24):
                d=prepare(sym,tf,raw)
                if d:datasets[(sym,tf)]=d
        except Exception as e:status[sym]={"error":str(e)}
    if len(datasets)<4:raise RuntimeError("Insufficient market data "+str(status))
    from itertools import product
    configs=list(product(("early","late","turn"),(0,2,3),("none","slow","extreme"),(1.5,2.5),(2.,4.),(6,12),("both","long")))
    # Two-stage selection: optimize on first 70%, report untouched last 30%.
    results={}
    for tf in (4,24):
        ds={sym:d for (sym,t),d in datasets.items() if t==tf}
        cuts={sym:int(len(d[0])*.7) for sym,d in ds.items()}
        ranks=[]
        for cfg in configs:
            ts=[]
            for sym,d in ds.items():ts.extend(simulate(d,cfg,cuts[sym])[0])
            m=metric(ts)
            if m["n"]<25 or m["pf"] is None:continue
            # discourage tiny samples and optimize risk-adjusted profit factor and expectancy
            score=(min(m["pf"],3)-1)*math.sqrt(m["n"])+m["avg"]*.5
            ranks.append((score,cfg,m))
        ranks.sort(reverse=True,key=lambda x:x[0])
        choices=[]
        for score,cfg,train in ranks[:5]:
            tests=[];by={}
            for sym,d in ds.items():
                # Test only signals at/after 70% split.
                trades,dd=simulate(d,cfg,0,start=cuts[sym])
                # The test engine starts at the held-out boundary and uses no training trades.
                by[sym]=metric(trades);tests.extend(trades)
            choices.append({"config":cfg,"train":train,"test":metric(tests),"by_asset":by})
        # Baseline unfiltered early and late
        baselines=[]
        for mode in ("early","late","turn"):
            cfg=(mode,0,"none",2.5,3.,12,"both")
            tr=[];te=[]
            for sym,d in ds.items():
                tr.extend(simulate(d,cfg,cuts[sym])[0])
                te.extend(simulate(d,cfg,0,start=cuts[sym])[0])
            baselines.append({"config":cfg,"train":metric(tr),"test":metric(te),"test_by_asset":{sym:metric(simulate(d,cfg,0,start=cuts[sym])[0]) for sym,d in ds.items()},"test_max_drawdown_by_asset":{sym:round(100*simulate(d,cfg,0,start=cuts[sym])[1],2) for sym,d in ds.items()}})
        divergences=[]
        for mode in ("early","late","turn"):
            for divergence in (2,3):
                cfg=(mode,divergence,"none",2.5,3.,12,"both")
                tr=[];te=[]
                for sym,d in ds.items():
                    tr.extend(simulate(d,cfg,cuts[sym])[0])
                    te.extend(simulate(d,cfg,0,start=cuts[sym])[0])
                divergences.append({"config":cfg,"train":metric(tr),"test":metric(te)})
        results[str(tf)+"h"]={"assets":list(ds),"top_train_configs":choices,"baselines":baselines,"divergence_ablation":divergences,"candidate_count":len(ranks)}
    output={"method":"1H downloaded once; 4H and 1D resampled; first 70% optimization (embargo last hold bars), last 30% simulated independently; 0.15% round-trip costs; entry next open; stop prioritized when stop and target touch same bar; one position per symbol; no leverage/funding; unadjusted price series; pivot confirmed after 2 bars","data":status,"results":results}
    (OUT/"multiasset_4h_1d_results.json").write_text(json.dumps(output,indent=2,ensure_ascii=False))
    print(json.dumps(output,indent=2,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
