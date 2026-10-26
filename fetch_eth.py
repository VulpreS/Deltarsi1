"""Fetch last 30 days of ETHUSDT 1h spot candles from Bybit public API.
Run: python fetch_eth.py
No external Python packages required.
"""
import csv
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://api.bybit.com/v5/market/kline"
OUT = Path("data/ETHUSDT_1h.csv")

def main():
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    candles_by_time = {}
    cursor = end_ms
    while cursor >= start_ms:
        query = urllib.parse.urlencode({"category": "spot", "symbol": "ETHUSDT",
            "interval": "60", "start": start_ms, "end": cursor, "limit": 1000})
        req = urllib.request.Request(URL + "?" + query, headers={"User-Agent": "DeltaRSI-research/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
        if payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {payload.get('retMsg')}")
        candles = payload["result"]["list"]
        if not candles:
            break
        for c in candles:
            timestamp = int(c[0])
            if start_ms <= timestamp <= end_ms:
                candles_by_time[timestamp] = c
        oldest = min(int(c[0]) for c in candles)
        if oldest <= start_ms:
            break
        cursor = oldest - 1
    if not candles_by_time:
        raise RuntimeError("No candles received; output was not created")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp_utc", "open", "high", "low", "close", "volume", "turnover"])
        for timestamp, c in sorted(candles_by_time.items()):
            date = dt.datetime.fromtimestamp(timestamp / 1000, dt.timezone.utc).isoformat()
            writer.writerow([date, *c[1:7]])
    print(f"Saved {len(candles_by_time)} candles to {OUT}")

if __name__ == "__main__":
    main()
