"""Preflight for reproducible 5m / 15m / 4h research.
Fails loudly if OHLCV is absent. No fabricated strategy performance.
"""
import csv, json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT=Path("data")
SYMBOLS=("BTCUSDT","ETHUSDT")
TFS={"5m":300,"15m":900,"4h":14400}
def parse_ts(s):
    s=str(s).strip()
    try:
        n=float(s)
        if n>1e12: n/=1000
        if n>1e9: return int(n)
    except ValueError: pass
    return int(datetime.fromisoformat(s.replace("Z","+00:00")).replace(tzinfo=timezone.utc).timestamp()) if "+" not in s and "Z" not in s else int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp())
def inspect(path,seconds):
    with path.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        cols=reader.fieldnames or []
        tscol=next((x for x in cols if x.lower() in ("timestamp_utc","timestamp","time","datetime","date","open_time")),None)
        if not tscol or not all(x in cols for x in ("open","high","low","close")):
            return {"file":str(path),"error":"missing timestamp or OHLC columns","columns":cols}
        times=[]
        for r in reader:
            try: times.append(parse_ts(r[tscol]))
            except (ValueError,TypeError): pass
    times=sorted(set(times))
    gaps=sum(max(0,round((b-a)/seconds)-1) for a,b in zip(times,times[1:]) if b-a>seconds)
    return {"file":str(path),"rows":len(times),"start":datetime.fromtimestamp(times[0],timezone.utc).isoformat() if times else None,"end":datetime.fromtimestamp(times[-1],timezone.utc).isoformat() if times else None,"missing_intervals":gaps}
def main():
    result={}
    for sym in SYMBOLS:
        result[sym]={}
        for tf,secs in TFS.items():
            names=[ROOT/f"{sym}_{tf}.csv",ROOT/f"{sym}-{tf}.csv",ROOT/f"{sym}_{tf.replace('m','min')}.csv"]
            p=next((x for x in names if x.exists()),None)
            result[sym][tf]=inspect(p,secs) if p else {"status":"MISSING","expected":[str(x) for x in names]}
    Path("research").mkdir(exist_ok=True)
    Path("research/benchmark_data_audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    if any("status" in result[s][tf] or "error" in result[s][tf] for s in SYMBOLS for tf in TFS):
        print("DATA INCOMPLETE: do not report benchmark results until missing candles are supplied.")
if __name__=="__main__":main()
