"""Cache contiguous 4H Binance USD-M OHLCV archives for DeltaPulse research.

No secrets, no exchange account, no orders. Monthly ZIPs up through the previous
month; daily ZIPs for the current month. Every returned 4H candle is complete.
Archive publication may lag the current UTC calendar day; report and reject
large stale tails. Internal gaps always fail; never synthesize OHLC.
"""
import csv
import datetime as dt
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UTC=dt.timezone.utc
H4=4*3_600_000
CACHE=Path("data")
STARTS={"BTCUSDT":(2020,1),"ETHUSDT":(2020,1),
        "SOLUSDT":(2023,1),"BNBUSDT":(2023,1),"XRPUSDT":(2023,1)}

def dt_of(ms):
    return dt.datetime.fromtimestamp(ms/1000,UTC).strftime("%Y-%m-%d %H:%M UTC")

def tasks(symbol,last_closed_utc):
    y,m=STARTS[symbol]
    out=[]
    while (y,m)<(last_closed_utc.year,last_closed_utc.month):
        key=f"{y}-{m:02d}"
        fn=f"{symbol}-4h-{key}.zip"
        url=f"https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/4h/{fn}"
        out.append((key,url))
        y,m=(y+1,1) if m==12 else (y,m+1)
    day=dt.date(last_closed_utc.year,last_closed_utc.month,1)
    while day<=last_closed_utc.date():
        key=day.isoformat()
        fn=f"{symbol}-4h-{key}.zip"
        url=f"https://data.binance.vision/data/futures/um/daily/klines/{symbol}/4h/{fn}"
        out.append((key,url))
        day+=dt.timedelta(days=1)
    return out

def fetch_one(job):
    key,url=job
    error=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"DeltaPulse4HResearch/1.0"})
            with urllib.request.urlopen(req,timeout=24) as f:
                b=f.read()
            with zipfile.ZipFile(io.BytesIO(b)) as archive:
                names=[n for n in archive.namelist() if n.endswith(".csv")]
                if len(names)!=1:raise ValueError("unexpected number of CSV entries")
                with archive.open(names[0]) as f:
                    rows=[]
                    for x in csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")):
                        try:
                            t=int(x[0]);t=t//1000 if t>10**14 else t
                            o,hi,lo,c=map(float,x[1:5])
                            if t%H4!=0 or not(0<lo<=min(o,c)<=max(o,c)<=hi):
                                raise ValueError(f"invalid 4H candle at {key}")
                            rows.append((t,o,hi,lo,c))
                        except ValueError:
                            if x and x[0].lower() in ("open_time","open time"):continue
                            raise
            return key,rows,None
        except urllib.error.HTTPError as ex:
            error=f"HTTP {ex.code}"
            if ex.code==404:break
        except Exception as ex:
            error=f"{type(ex).__name__}: {str(ex)[:120]}"
        if attempt<2:time.sleep(.4*(attempt+1))
    return key,[],error

def read_cache(symbol):
    path=CACHE/f"{symbol}_4h_binance_um.csv"
    if not path.exists():return []
    with path.open() as f:
        return [(int(x["open_ms"]),*[float(x[k]) for k in ("open","high","low","close")])
                for x in csv.DictReader(f)]

def validate(symbol,rows,asof):
    if len(rows)<1300:raise ValueError(f"{symbol}: too few 4H bars {len(rows)}")
    for left,right in zip(rows,rows[1:]):
        if right[0]-left[0]!=H4:
            raise ValueError(f"{symbol}: interior OHLC gap {dt_of(left[0])} -> {dt_of(right[0])}")
    if any(x[0]+H4>asof for x in rows):
        raise ValueError(f"{symbol}: future/unclosed 4H bar")
    if rows[-1][0]<asof-7*24*3_600_000:
        raise ValueError(f"{symbol}: historical archive stale {dt_of(rows[-1][0])}")

def load(symbol):
    if symbol not in STARTS:raise ValueError(symbol)
    now=dt.datetime.now(UTC)
    asof=int((now.replace(hour=0,minute=0,second=0,microsecond=0)-dt.timedelta(days=1)).timestamp()*1000)
    # Use at most the completed previous UTC day; current data archives may lag.
    rows=read_cache(symbol)
    if rows and rows[-1][0]>=asof-3*24*3_600_000:
        validate(symbol,rows,asof)
        return rows,{"provider":"Binance USD-M perpetual OHLC, not Bybit",
                     "source":"previously cached ZIP archives","cached":True,
                     "n":len(rows),"first":dt_of(rows[0][0]),
                     "last":dt_of(rows[-1][0])}
    jobs=tasks(symbol,dt.datetime.fromtimestamp(asof/1000,UTC))
    by_ts={};failures=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures=[ex.submit(fetch_one,job) for job in jobs]
        for future in as_completed(futures):
            key,data,error=future.result()
            if error:failures.append({"period":key,"error":error})
            for row in data:
                if row[0]+H4>asof+24*3_600_000:continue
                existing=by_ts.get(row[0])
                if existing is not None and existing!=row:
                    raise ValueError(f"{symbol}: conflicting provider values {dt_of(row[0])}")
                by_ts[row[0]]=row
    rows=[by_ts[t] for t in sorted(by_ts)]
    # Last daily archives can be partially missing, but NO interior holes.
    validate(symbol,rows,asof)
    CACHE.mkdir(exist_ok=True)
    p=CACHE/f"{symbol}_4h_binance_um.csv"
    with p.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["open_ms","open","high","low","close"]);w.writerows(rows)
    return rows,{"provider":"Binance USD-M perpetual OHLC, not Bybit",
                 "source":"data.binance.vision monthly/daily ZIP OHLC",
                 "cached":False,"n":len(rows),"first":dt_of(rows[0][0]),
                 "last":dt_of(rows[-1][0]),"archive_errors":sorted(failures,key=lambda z:z["period"])}

if __name__=="__main__":
    for s in STARTS:
        rows,src=load(s)
        print(json.dumps({"asset":s,**src}))
