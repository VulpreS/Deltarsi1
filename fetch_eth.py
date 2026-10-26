"""Incrementally append completed ETHUSDT hourly candles; retain historical CSV."""
import csv
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("data/ETHUSDT_1h.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DeltaRSIResearch/1.0)", "Accept": "application/json"}
HOUR = 3600000

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as response:
        return json.load(response)

def fetch_page(source, start_ms, end_ms):
    if source == "Bybit":
        q = urllib.parse.urlencode({"category":"spot","symbol":"ETHUSDT","interval":"60","start":start_ms,"end":end_ms,"limit":1000})
        data = get("https://api.bybit.com/v5/market/kline?" + q)
        if data.get("retCode") != 0: raise RuntimeError(data.get("retMsg"))
        return [(int(c[0]),*map(float,c[1:7])) for c in data["result"]["list"]]
    host = "https://data-api.binance.vision" if source == "Binance Data API" else "https://api.binance.us"
    q = urllib.parse.urlencode({"symbol":"ETHUSDT","interval":"1h","startTime":start_ms,"endTime":end_ms,"limit":1000})
    data = get(host + "/api/v3/klines?" + q)
    return [(int(c[0]),float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[7])) for c in data]

def fetch_history(source, start_ms, end_ms):
    result = {}
    cursor = start_ms
    while cursor <= end_ms:
        chunk_end = min(end_ms, cursor + 900*HOUR)
        page = fetch_page(source,cursor,chunk_end)
        for row in page:
            if cursor <= row[0] <= chunk_end: result[row[0]] = row
        if not page: raise RuntimeError(f"Empty page at {cursor}")
        cursor = chunk_end + HOUR
        time.sleep(.12)
    rows = sorted(result.values())
    expected = (end_ms-start_ms)//HOUR + 1
    if len(rows) != expected: raise RuntimeError(f"Only {len(rows)} of {expected} expected candles")
    if any(b[0]-a[0]!=HOUR for a,b in zip(rows,rows[1:])):
        raise RuntimeError("Hourly gaps detected")
    return rows

def read_existing():
    if not OUT.exists(): return {}
    with OUT.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    saved={}
    for r in rows:
        ts=int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000)
        saved[ts]=(ts,*[float(r[k]) for k in ("open","high","low","close","volume","turnover")])
    return saved

def main():
    import os
    now=dt.datetime.now(dt.timezone.utc)
    end_ms=int(now.replace(minute=0,second=0,microsecond=0).timestamp()*1000)-HOUR
    existing=read_existing()
    if os.getenv("FULL_REFRESH")=="1":
        existing={}
    # Keep the complete existing dataset; fetch only missing candles.
    start_ms=max(existing)+HOUR if existing else end_ms-(365*24-1)*HOUR
    if start_ms>end_ms:
        print(f"Already up to date: {len(existing)} candles; no API calls",flush=True)
        return
    errors=[]
    for source in ("Binance Data API","Binance US","Bybit"):
        try:
            print(f"Trying {source} for {(end_ms-start_ms)//HOUR+1} new candles...",flush=True)
            rows=fetch_history(source,start_ms,end_ms)
            existing.update({r[0]:r for r in rows})
            rows=sorted(existing.values())
            if any(b[0]-a[0]!=HOUR for a,b in zip(rows,rows[1:])):
                raise RuntimeError("Gap in merged hourly dataset")
            OUT.parent.mkdir(parents=True,exist_ok=True)
            with OUT.open("w",newline="",encoding="utf-8") as f:
                w=csv.writer(f);w.writerow(["timestamp_utc","open","high","low","close","volume","turnover"])
                for ts,op,hi,lo,cl,vol,turnover in rows:
                    w.writerow([dt.datetime.fromtimestamp(ts/1000,dt.timezone.utc).isoformat(),op,hi,lo,cl,vol,turnover])
            print(f"Saved {len(rows)} total candles; added new candles from {source}",flush=True)
            return
        except (urllib.error.URLError,ValueError,KeyError,TypeError,RuntimeError) as exc:
            errors.append(f"{source}: {exc}")
            print(f"{source} failed: {exc}",flush=True)
    raise RuntimeError("All providers failed:\n"+"\n".join(errors))

if __name__=="__main__": main()
