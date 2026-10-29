"""DeltaRSI multi-timeframe research backtest (5m/15m/4h).
Explicit research rules, NOT a reproduction of the discretionary 5m RSI strategy.
Input: data/{BTCUSDT,ETHUSDT}_{5m,15m,4h}.csv, UTC timestamp_utc + OHLC.
Runs only when data exists. Zero lookahead: signal on close, fill next open.
"""
import csv, json, math, argparse
from pathlib import Path
from datetime import datetime, timezone
def read(path):
    with open(path,newline="") as f:
        rows=list(csv.DictReader(f))
    out=[]
    for r in rows:
        t=r.get("timestamp_utc") or r.get("timestamp") or r.get("time")
        if not t: raise ValueError("Missing timestamp")
        if t.isdigit():
            v=int(t); ts=v/1000 if v>1e12 else v
        else: ts=datetime.fromisoformat(t.replace("Z","+00:00")).timestamp()
        out.append((ts,*[float(r[k]) for k in ("open","high","low","close")]))
    out.sort()
    if len(out)<150: raise ValueError("Insufficient candles")
    if any(b[0]<=a[0] for a,b in zip(out,out[1:])): raise ValueError("Nonunique timestamps")
    return out
def delta(closes):
    gains=[];losses=[]
    for a,b in zip(closes,closes[1:]):
        gains.append(max(0,b-a));losses.append(max(0,a-b))
    n=27
    ag=sum(gains[:n])/n;al=sum(losses[:n])/n
    result=[None]*len(closes); signal=None
    for i in range(n,len(closes)):
        if i>n:
            ag=(ag*(n-1)+gains[i-1])/n;al=(al*(n-1)+losses[i-1])/n
        rsi=100 if al==0 else 100-100/(1+ag/al)
        signal=rsi if signal is None else (2/8)*rsi+(6/8)*signal
        result[i]=rsi-signal
    return result
def test(rows,tf,start_ts,fee=.0008,spread=.0004,allocation=.3,sl=.015,tp=.03):
    d=delta([r[4] for r in rows]); equity=5000.; peak=equity; dd=0.; pos=None; trades=[]; curve=[]
    # Fully specified research proxy: Delta crosses zero, long-only. No intrabar stop ambiguity ignored.
    for i in range(30,len(rows)-1):
        t,op,hi,lo,cl=rows[i]
        if pos:
            hit_sl=lo<=pos["sl"];hit_tp=hi>=pos["tp"]
            if hit_sl or hit_tp:
                exit_price=pos["sl"] if hit_sl else pos["tp"]
                exit_price*=1-spread/2
                proceeds=pos["qty"]*exit_price*(1-fee)
                pnl=proceeds-pos["cost"]
                equity+=pnl
                trades.append({"entry_utc":pos["time"],"exit_utc":datetime.fromtimestamp(t,timezone.utc).isoformat(),"pnl":round(pnl,4),"reason":"SL" if hit_sl else "TP"})
                pos=None
        if t>=start_ts and pos is None and d[i-1] is not None and d[i] is not None and d[i-1]<=0<d[i]:
            next_open=rows[i+1][1]*(1+spread/2)
            notional=equity*allocation
            qty=notional/next_open
            cost=notional*(1+fee)
            pos={"qty":qty,"cost":cost,"sl":next_open*(1-sl),"tp":next_open*(1+tp),"time":datetime.fromtimestamp(rows[i+1][0],timezone.utc).isoformat()}
        mark=equity if pos is None else equity+pos["qty"]*cl*(1-spread/2)*(1-fee)-pos["cost"]
        peak=max(peak,mark);dd=max(dd,1-mark/peak)
        curve.append({"time":datetime.fromtimestamp(t,timezone.utc).isoformat(),"equity":round(mark,4)})
    if pos:
        t,_,_,_,cl=rows[-1]; proceeds=pos["qty"]*cl*(1-spread/2)*(1-fee)
        pnl=proceeds-pos["cost"];equity+=pnl
        trades.append({"entry_utc":pos["time"],"exit_utc":datetime.fromtimestamp(t,timezone.utc).isoformat(),"pnl":round(pnl,4),"reason":"END"})
    grosswin=sum(x["pnl"] for x in trades if x["pnl"]>0)
    grossloss=-sum(x["pnl"] for x in trades if x["pnl"]<0)
    return {"tf":tf,"trades":len(trades),"win_rate":sum(x["pnl"]>0 for x in trades)/len(trades) if trades else None,"pf":grosswin/grossloss if grossloss else None,"net_pct":(equity/5000-1)*100,"max_dd_pct":dd*100},trades,curve
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data",default="data");ap.add_argument("--out",default="research/results");a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    summary=[];missing=[]
    for sym in ("BTCUSDT","ETHUSDT"):
        for tf in ("5m","15m","4h"):
            p=Path(a.data)/f"{sym}_{tf}.csv"
            if not p.exists():missing.append(str(p));continue
            rows=read(p)
            # compare last 30 complete UTC days, excluding the most recent incomplete day
            last_day=int(rows[-1][0]//86400)
            end=last_day*86400;start=end-30*86400
            sample=[r for r in rows if r[0]<end]
            if not sample or sample[0][0]>start-30*86400: missing.append(f"{p}: insufficient warmup");continue
            sample=[r for r in sample if r[0]>=start-30*86400]
            res,trades,curve=test(sample,tf,start)
            res.update(symbol=sym,eval_start=datetime.fromtimestamp(start,timezone.utc).isoformat(),eval_end=datetime.fromtimestamp(end,timezone.utc).isoformat(),note="research zero-cross proxy, no entries during warmup")
            summary.append(res)
            with open(out/f"{sym}_{tf}_trades.csv","w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["entry_utc","exit_utc","pnl","reason"]);w.writeheader();w.writerows(trades)
    (out/"summary.json").write_text(json.dumps({"results":summary,"missing":missing,"status":"incomplete" if missing else "proxy_only"},indent=2))
    print((out/"summary.json").read_text())
    if missing: raise SystemExit("Missing required input data: "+", ".join(missing))
if __name__=="__main__":main()
