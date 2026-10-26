"""Fetch 30 days of completed ETHUSDT 1h spot candles with provider fallback."""
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

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def bybit(start_ms, end_ms):
    url = "https://api.bybit.com/v5/market/kline?" + urllib.parse.urlencode({
        "category": "spot", "symbol": "ETHUSDT", "interval": "60",
        "start": start_ms, "end": end_ms, "limit": 1000})
    data = get(url)
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit: {data.get('retMsg')}")
    return [(int(c[0]), *map(float, c[1:7])) for c in data["result"]["list"]]

def binance(start_ms, end_ms, host):
    url = host + "/api/v3/klines?" + urllib.parse.urlencode({
        "symbol": "ETHUSDT", "interval": "1h", "startTime": start_ms,
        "endTime": end_ms, "limit": 1000})
    data = get(url)
    return [(int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]),
             float(c[5]), float(c[7])) for c in data]

def main():
    now = dt.datetime.now(dt.timezone.utc)
    end_ms = int(now.replace(minute=0, second=0, microsecond=0).timestamp() * 1000) - 1
    start_ms = end_ms - 30 * 86400000
    providers = [
        ("Binance Data API", lambda: binance(start_ms, end_ms, "https://data-api.binance.vision")),
        ("Binance US", lambda: binance(start_ms, end_ms, "https://api.binance.us")),
        ("Bybit", lambda: bybit(start_ms, end_ms)),
    ]
    errors = []
    for name, fetch in providers:
        try:
            print(f"Trying {name}...", flush=True)
            rows = fetch()
            rows = sorted({r[0]: r for r in rows if start_ms <= r[0] <= end_ms}.values())
            if len(rows) < 600:
                raise RuntimeError(f"Only {len(rows)} candles (expected approximately 720)")
            # Reject gaps: do not silently generate misleading indicator results.
            gaps = [(a[0], b[0]) for a, b in zip(rows, rows[1:]) if b[0]-a[0] != 3600000]
            if gaps:
                raise RuntimeError(f"{len(gaps)} missing-hour gaps in returned candles")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            with OUT.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp_utc", "open", "high", "low", "close", "volume", "turnover"])
                for ts, op, hi, lo, cl, vol, turnover in rows:
                    stamp = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).isoformat()
                    w.writerow([stamp, op, hi, lo, cl, vol, turnover])
            print(f"Saved {len(rows)} complete hourly candles from {name} to {OUT}", flush=True)
            return
        except (urllib.error.URLError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            errors.append(f"{name}: {exc}")
            print(f"{name} failed: {exc}", flush=True)
            time.sleep(1)
    raise RuntimeError("All providers failed:\n" + "\n".join(errors))

if __name__ == "__main__":
    main()
