"""Download Binance USD-M perpetual 4h OHLCV for the DeltaRSI 3-year study.

Uses Binance public futures klines, with an alternate futures API host.
Preserves the chronological 2026-08-01 holdout boundary.
"""
import datetime as dt
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

SYMS = ("BTCUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT")
START = int(dt.datetime(2023, 11, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
END = int(dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
CUT = int(dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
STEP = 4 * 3600 * 1000
OUT = pathlib.Path("experiments/delta_ml_3y/data")
OUT.mkdir(parents=True, exist_ok=True)
HOSTS = ("https://fapi.binance.com", "https://fapi1.binance.com")

def fetch(sym, start):
    params = urllib.parse.urlencode({
        "symbol": sym, "interval": "4h", "startTime": start,
        "endTime": END - 1, "limit": 1500,
    })
    errors = []
    for host in HOSTS:
        url = host + "/fapi/v1/klines?" + params
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DeltaMLResearch"})
                with urllib.request.urlopen(req, timeout=35) as response:
                    payload = json.load(response)
                if not isinstance(payload, list):
                    raise RuntimeError("Unexpected Binance response: " + str(payload)[:300])
                return payload
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                errors.append(f"{host}: {exc}")
                if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 451):
                    break
                time.sleep(2 ** attempt)
    raise RuntimeError("All Binance futures API hosts failed: " + "; ".join(errors[-6:]))

for sym in SYMS:
    records = {}
    cursor = START
    while cursor < END:
        page = fetch(sym, cursor)
        if not page:
            break
        last = cursor - STEP
        for row in page:
            t = int(row[0])
            if START <= t < END:
                records[t] = [t, *[float(row[k]) for k in (1, 2, 3, 4, 5)]]
            last = max(last, t)
        print(sym, "page", len(page), "total", len(records), flush=True)
        if last < cursor:
            break
        cursor = last + STEP
        time.sleep(0.18)
    rows = [records[t] for t in sorted(records)]
    if len(rows) < 1500:
        raise RuntimeError(f"Insufficient Binance candles for {sym}: {len(rows)}")
    gaps = [(a[0], b[0]) for a, b in zip(rows, rows[1:]) if b[0] - a[0] != STEP]
    if gaps:
        raise RuntimeError(f"Missing/non-4h candles for {sym}: {gaps[:5]}")
    if rows[0][0] > START + 30 * STEP:
        raise RuntimeError(f"History starts too late for {sym}: {rows[0][0]}")
    train = sum(r[0] < CUT for r in rows)
    test = len(rows) - train
    if train < 1000 or test < 100:
        raise RuntimeError(f"Insufficient train/test split for {sym}: {train}/{test}")
    (OUT / (sym + ".json")).write_text(json.dumps(rows, separators=(",", ":")))
    print("DATA_SUMMARY", json.dumps({
        "exchange": "Binance USD-M", "symbol": sym, "rows": len(rows),
        "train": train, "test": test, "first": rows[0][0], "last": rows[-1][0],
    }), flush=True)
