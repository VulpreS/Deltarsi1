"""Download ONLY GRAMUSDT USD-M 4h futures after Binance TON rebranding.

TONUSDT was delisted June 23, 2026; GRAMUSDT listed July 2, 2026.
They are separate contracts. DO NOT interpolate missing June 23—July 2 bars,
DO NOT stitch into one contiguous tradable contract without a reset.
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

SYMBOL="GRAMUSDT"
STEP=4*3600000
START=int(dt.datetime(2026,7,2,8,tzinfo=dt.timezone.utc).timestamp()*1000)
END=dt.date(2026,10,27)
ROOT=pathlib.Path("experiments/delta_ml_3y/data")
ROOT.mkdir(parents=True,exist_ok=True)
HOSTS=("https://data.binance.vision/",
       "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/")

def get_zip(path):
    errors=[];n404=0
    for host in HOSTS:
        for retry in range(3):
            url=host+path
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSI-GRAM-history/1.0"})
                with urllib.request.urlopen(req,timeout=35) as f:
                    b=f.read()
                if not b.startswith(b"PK"):
                    raise ValueError(f"Not ZIP: {b[:70]!r}")
                return b
            except urllib.error.HTTPError as e:
                if e.code==404:
                    n404+=1;break
                if e.code in (403,451):
                    errors.append(f"{url}: HTTP{e.code}");break
                errors.append(f"{url}: HTTP{e.code}")
            except Exception as e:
                errors.append(f"{url}: {e}")
            time.sleep(retry+1)
    if n404==len(HOSTS):
        return None
    raise RuntimeError("GRAM archive retrieval failed: "+" | ".join(errors[-4:]))

def rows_from_zip(zipbytes,path):
    with zipfile.ZipFile(io.BytesIO(zipbytes)) as z:
        files=[n for n in z.namelist() if n.endswith(".csv")]
        if len(files)!=1:raise ValueError(f"Bad ZIP {path}: {files}")
        out={}
        with z.open(files[0]) as f:
            for v in csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")):
                if not v or not v[0].isdigit():continue
                t=int(v[0])
                if t>10**14:t//=1000
                if t%STEP:raise RuntimeError(f"Invalid 4h time {t} in {path}")
                if t>=START:
                    out[t]=[t,*[float(v[k]) for k in (1,2,3,4,5)]]
        return out

def source_path(kind,tag):
    return f"data/futures/um/{kind}/klines/{SYMBOL}/4h/{SYMBOL}-4h-{tag}.zip"

def main():
    allrows={}
    for tag in ("2026-07","2026-08","2026-09"):
        p=source_path("monthly",tag)
        z=get_zip(p)
        if z is None:
            raise RuntimeError(f"GRAM {tag} monthly archive absent; no fabricated observations")
        rows=rows_from_zip(z,p)
        allrows.update(rows)
        print("GRAM_ARCHIVE",tag,len(rows),flush=True)
    today=dt.date(2026,10,1)
    first_missing=None
    while today<=END:
        p=source_path("daily",today.isoformat())
        z=get_zip(p)
        if z is None:
            first_missing=today.isoformat()
            print("GRAM_WARNING",first_missing,"archive absent; truncate",flush=True)
            break
        rows=rows_from_zip(z,p)
        if len(rows)!=6:raise RuntimeError(f"Missing GRAM 4h candles in {p}: {len(rows)}")
        allrows.update(rows)
        print("GRAM_ARCHIVE",today.isoformat(),len(rows),flush=True)
        today+=dt.timedelta(days=1)
    candles=[allrows[t] for t in sorted(allrows)]
    if any(b[0]-a[0]!=STEP for a,b in zip(candles,candles[1:])):
        raise RuntimeError("GRAM 4h gap inside new contract; no synthetic joins")
    if candles[0][0]!=START or candles[-1][0]<int(dt.datetime(2026,10,20,tzinfo=dt.timezone.utc).timestamp()*1000):
        raise RuntimeError(f"GRAM insufficient valid start or tail: {candles[0][0]}..{candles[-1][0]}")
    if any(row[5]<=0 for row in candles[-100:]):
        raise RuntimeError("GRAM has zero volume in recent candles; check contract")
    (ROOT/(SYMBOL+".json")).write_text(json.dumps(candles,separators=(",",":")))
    summary=dict(symbol=SYMBOL,contract_started_utc="2026-07-02T08:00:00Z",
        rows=len(candles),first=candles[0][0],last=candles[-1][0],
        separate_from_delisted_TON=True,missing_recent=first_missing)
    print("GRAM_DATA_SUMMARY",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
