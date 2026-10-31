"""Add ICP and ZEC to the *existing* 6-asset 3-year Binance Vision 4h cache.

Downloads ONLY ICPUSDT and ZECUSDT monthly 4h ZIPs (2023-11..2026-09),
then October 2026 daily ZIPs. Does not redownload existing six symbols.
Never interpolate or bridge a missing candle. Missing a recent daily ZIP
truncates the 4h contiguous prefix, with an explicit data warning.
"""
import csv
import datetime as dt
import io
import json
import pathlib
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

SYMS = ("ICPUSDT", "ZECUSDT")
START = dt.date(2023,11,1)
END_DAY = dt.date(2026,10,30)
CUT = int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()*1000)
STEP = 4*3600000
OUT = pathlib.Path("experiments/delta_ml_3y/data")
OUT.mkdir(parents=True,exist_ok=True)
HOSTS=("https://data.binance.vision/",
       "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/")


def paths(sym):
    year,month=2023,11
    while (year,month)<(2026,10):
        tag=f"{year:04d}-{month:02d}"
        yield ("monthly",tag,f"data/futures/um/monthly/klines/{sym}/4h/{sym}-4h-{tag}.zip")
        year,month=(year+1,1) if month==12 else (year,month+1)
    day=dt.date(2026,10,1)
    while day<=END_DAY:
        tag=day.isoformat()
        yield ("daily",tag,f"data/futures/um/daily/klines/{sym}/4h/{sym}-4h-{tag}.zip")
        day+=dt.timedelta(days=1)


def download(path):
    errors=[];missing=0
    for host in HOSTS:
        url=host+path
        for retry in range(3):
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSI-eight-assets-research/1.0"})
                with urllib.request.urlopen(req,timeout=35) as response:
                    payload=response.read()
                if not payload.startswith(b"PK"):
                    raise ValueError(f"Nonzip data: {payload[:70]!r}")
                return payload
            except urllib.error.HTTPError as e:
                if e.code==404:
                    missing+=1
                    break
                errors.append(f"{url}: HTTP {e.code}")
                if e.code in (403,451):
                    break
            except (urllib.error.URLError,ValueError,TimeoutError) as e:
                errors.append(f"{url}: {e}")
            if retry<2:
                time.sleep(1+retry)
    if missing==len(HOSTS):
        return None
    raise RuntimeError(f"Cannot read {path}: "+ "; ".join(errors[-4:]))


def decode(content,path):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        csv_files=[p for p in archive.namelist() if p.endswith(".csv")]
        if len(csv_files)!=1:
            raise RuntimeError(f"Bad archive {path}, CSV files {csv_files}")
        rows=[]
        with archive.open(csv_files[0]) as f:
            for v in csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")):
                if not v or not v[0].isdigit():
                    continue
                ts=int(v[0])
                if ts>10**14:
                    ts//=1000
                if ts%STEP:
                    raise RuntimeError(f"Invalid 4h timestamp {ts} in {path}")
                rows.append([ts,*[float(v[k]) for k in (1,2,3,4,5)]])
    return rows


def run_one(sym):
    records={}
    started=False
    missing_history=[]
    missing_days=[]
    for period,tag,path in paths(sym):
        z=download(path)
        if z is None:
            if period=="monthly":
                if started:
                    missing_history.append(tag)
            else:
                missing_days.append(tag)
            continue
        started=True
        bars=decode(z,path)
        records.update({int(row[0]):row for row in bars})
        print("ARCHIVE",sym,period,tag,len(bars),len(records),flush=True)
    if missing_history:
        raise RuntimeError(f"{sym}: missing monthly archives after listings: {missing_history[:10]}")
    if not records:
        raise RuntimeError(f"{sym}: no Binance futures archives")
    first_missing=min(missing_days) if missing_days else None
    if first_missing:
        if first_missing<"2026-10-25":
            raise RuntimeError(f"{sym}: unexpected missing October archive {first_missing}")
        stop=int(dt.datetime.fromisoformat(first_missing).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
        records={ts:row for ts,row in records.items() if ts<stop}
        print("ARCHIVE_WARNING",sym,"trim after missing",first_missing,flush=True)
    rows=[records[t] for t in sorted(records)]
    gaps=[(a[0],b[0]) for a,b in zip(rows,rows[1:]) if b[0]-a[0]!=STEP]
    if gaps:
        raise RuntimeError(f"{sym}: gaps inside series (no interpolation): {gaps[:5]}")
    start=int(dt.datetime(2023,11,4,tzinfo=dt.timezone.utc).timestamp()*1000)
    latest=int(dt.datetime(2026,10,24,tzinfo=dt.timezone.utc).timestamp()*1000)
    if rows[0][0]>start or rows[-1][0]<latest:
        raise RuntimeError(f"{sym}: insufficient historical coverage first={rows[0][0]} last={rows[-1][0]}")
    train=sum(v[0]<CUT for v in rows)
    test=len(rows)-train
    if train<5000 or test<450:
        raise RuntimeError(f"{sym}: insufficient 4h candles pretest={train},test={test}")
    (OUT/(sym+".json")).write_text(json.dumps(rows,separators=(",",":")))
    summary=dict(source="Binance Vision USD-M futures",asset=sym,
        first_ms=rows[0][0],last_ms=rows[-1][0],
        train=train,test=test,rows=len(rows),
        missing_recent_daily_zip=missing_days,
        gap_count=0)
    print("NEW_COIN_DATA",json.dumps(summary),flush=True)
    return summary


def main():
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(run_one,s):s for s in SYMS}
        errors=[]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as err:
                errors.append(f"{futures[fut]}: {err}")
        if errors:
            raise RuntimeError("Additional assets not ready: " + " | ".join(errors))


if __name__=="__main__":
    main()
