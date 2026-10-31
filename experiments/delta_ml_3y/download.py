"""Binance Vision public USD-M perpetual archives, 4h candles, no REST trading API.

Monthly ZIPs are used through September 2026; daily ZIPs for October 2026
(the October monthly archive is not published until the following month).
Timestamps stay in milliseconds and candles are strictly chronological.
"""
import calendar
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

SYMS = ("BTCUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT")
START = dt.date(2023, 11, 1)
LAST_COMPLETE_DAY = dt.date(2026, 10, 30)  # 2026-10-31 daily archive not yet published
CUT = int(dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
STEP = 4 * 3600 * 1000
OUT = pathlib.Path("experiments/delta_ml_3y/data")
OUT.mkdir(parents=True, exist_ok=True)
BASES = (
    "https://data.binance.vision/",
    "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/",
)

def monthly_dates():
    year, month = START.year, START.month
    while (year, month) < (2026, 10):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1

def sources(sym):
    stem = f"data/futures/um/{{period}}/klines/{sym}/4h/{sym}-4h-{{date}}.zip"
    for date in monthly_dates():
        yield ("monthly", date, stem.format(period="monthly", date=date))
    d = dt.date(2026, 10, 1)
    while d <= LAST_COMPLETE_DAY:
        yield ("daily", d.isoformat(), stem.format(period="daily", date=d.isoformat()))
        d += dt.timedelta(days=1)

def download(path):
    errors = []
    not_found = 0
    for base in BASES:
        url = base + path
        for retry in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "DeltaRSI-historical-research/2.0"})
                with urllib.request.urlopen(req, timeout=35) as response:
                    body = response.read()
                if not body.startswith(b"PK"):
                    raise RuntimeError(f"ZIP missing at {url}; response={body[:100]!r}")
                return body
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    not_found += 1
                    break
                errors.append(f"{url}: HTTP {exc.code}")
                if exc.code in (403, 451):
                    break
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                errors.append(f"{url}: {exc}")
            if retry < 2:
                time.sleep(1 + retry)
    if not_found == len(BASES):
        return None
    raise RuntimeError("Binance Vision download failed: " + "; ".join(errors[-6:]))

def decode_zip(body, path):
    rows = []
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"Unexpected CSV files in {path}: {names}")
        with archive.open(names[0]) as src:
            reader = csv.reader(io.TextIOWrapper(src, encoding="utf-8-sig"))
            for values in reader:
                if not values or not values[0].strip().isdigit():
                    continue  # Some Binance futures archives include a CSV header
                ts = int(values[0])
                # Binance USD-M futures archive timestamps are milliseconds.
                if ts > 10**14:
                    ts //= 1000
                if ts % STEP:
                    raise RuntimeError(f"Unexpected candle alignment in {path}: {ts}")
                rows.append([ts, *[float(values[k]) for k in (1, 2, 3, 4, 5)]])
    return rows

def process_symbol(sym):
    records = {}
    first_archive = None
    missing_after_start = []
    for period, date, path in sources(sym):
        body = download(path)
        if body is None:
            if first_archive is not None:
                missing_after_start.append(date)
            continue
        if first_archive is None:
            first_archive = date
        rows = decode_zip(body, path)
        for row in rows:
            records[row[0]] = row
        print(sym, period, date, "rows", len(rows), "total", len(records), flush=True)
    if missing_after_start:
        raise RuntimeError(f"{sym}: missing archive(s) after listing: {missing_after_start[:8]}")
    rows = [records[k] for k in sorted(records)]
    if not rows:
        raise RuntimeError(f"{sym}: Binance Vision archive returned no candles")
    gaps = [(a[0], b[0]) for a, b in zip(rows, rows[1:]) if b[0] - a[0] != STEP]
    if gaps:
        raise RuntimeError(f"{sym}: missing 4h bars: {gaps[:5]}")
    first = rows[0][0]
    last = rows[-1][0]
    # TON started trading later than November 2023; do not invent its earlier bars.
    min_start = int(dt.datetime(2024, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000) if sym == "TONUSDT" else int(dt.datetime(2023, 11, 3, tzinfo=dt.timezone.utc).timestamp() * 1000)
    if first > min_start:
        raise RuntimeError(f"{sym}: history begins unexpectedly late ({first_archive})")
    latest_allowed = int(dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc).timestamp() * 1000)
    if last < latest_allowed:
        raise RuntimeError(f"{sym}: recent history ends unexpectedly early: {last}")
    train = sum(r[0] < CUT for r in rows)
    test = len(rows) - train
    if train < 1000 or test < 100:
        raise RuntimeError(f"{sym}: inadequate temporal split {train}/{test}")
    output = OUT / (sym + ".json")
    output.write_text(json.dumps(rows, separators=(",", ":")))
    result = dict(source="Binance Vision USD-M futures", symbol=sym, rows=len(rows),
                  train=train, test=test, first=first, last=last,
                  missing_archives=0, output=str(output))
    print("DATA_SUMMARY", json.dumps(result), flush=True)
    return result

def main():
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(process_symbol, sym): sym for sym in SYMS}
        failed = []
        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as exc:
                failed.append(f"{tasks[future]}: {exc}")
        if failed:
            raise RuntimeError("Archive retrieval incomplete: " + " | ".join(failed))

if __name__ == "__main__":
    main()
