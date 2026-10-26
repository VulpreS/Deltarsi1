"""Strict, causal UTC-aligned aggregation of cached hourly OHLC bars.

No network or order execution. The asof_ms argument is the observation cutoff:
a 1H source bar is eligible only when its close <= asof_ms. Historical callers
without a receipt timestamp may explicitly infer asof from the last cached 1H
open + 1H, which is NOT evidence of real-time receipt/provenance.
"""
import math

HOUR_MS = 3_600_000

def aggregate_completed(raw, hours=4, asof_ms=None):
    if not isinstance(hours, int) or hours <= 0:
        raise ValueError("hours must be a positive integer")
    if not raw:
        return []
    previous = None
    for row in raw:
        if len(row) < 5:
            raise ValueError("Each bar needs UTC open ms, open, high, low, close")
        ts = row[0]
        if not isinstance(ts, int) or ts % HOUR_MS:
            raise ValueError("Hourly timestamps must be integer UTC hour-open milliseconds")
        if previous is not None and ts <= previous:
            raise ValueError("Hourly timestamps must be strictly increasing, no duplicates")
        previous = ts
        o, hi, lo, c = row[1:5]
        if not all(math.isfinite(v) and v > 0 for v in (o, hi, lo, c)):
            raise ValueError("Invalid hourly OHLC")
        if lo > min(o, c) or hi < max(o, c):
            raise ValueError("Invalid hourly OHLC envelope")
    if asof_ms is None:
        # Only appropriate for historical caches assumed to contain closed 1H bars.
        asof_ms = raw[-1][0] + HOUR_MS
    if not isinstance(asof_ms, (int, float)) or not math.isfinite(asof_ms):
        raise ValueError("asof_ms must be a finite UTC timestamp")
    width = hours * HOUR_MS
    result = []
    group = []
    current = None
    for row in raw:
        ts = row[0]
        if ts + HOUR_MS > asof_ms:
            break  # the source hour has not closed yet; never peek beyond asof
        bucket = ts // width * width
        if bucket != current:
            if group:
                result.extend(_completed(group, current, hours, width, asof_ms))
            current = bucket
            group = []
        group.append(row)
    if group:
        result.extend(_completed(group, current, hours, width, asof_ms))
    return result

def _completed(group, start, hours, width, asof_ms):
    if len(group) != hours or start + width > asof_ms:
        return []
    if any(row[0] != start + k * HOUR_MS for k, row in enumerate(group)):
        return []
    return [(start, group[0][1], max(x[2] for x in group),
             min(x[3] for x in group), group[-1][4])]

def aggregate_completed_4h(raw, asof_ms=None):
    return aggregate_completed(raw, 4, asof_ms)
