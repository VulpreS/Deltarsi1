"""Reproduce redacted BTC trade/1H discrepancy ledger (#17). No orders/network.

Usage: python manual_trade_discrepancy_ledger.py
Only public cached OHLC and opaque row IDs are emitted. Never emit annotated
entry/exit/stop prices or silently repair a user's original 42-row journal.
"""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

LABELS = Path("data/manual_btc_trades_2025_2026.csv")
CANDLES = Path("data/BTCUSDT_1h.csv")
OUTPUT = Path("reports/manual_trade_discrepancy_ledger.json")
H = dt.timedelta(hours=1)
UTC = dt.timezone.utc
MSK = dt.timezone(dt.timedelta(hours=3))
QUALITY = {
    "exit2_time_missing": "second_exit_time_incomplete",
    "exit1_price_suspect_842300": "suspect_first_exit_price",
    "exit_before_entry_suspect_month": "exit_before_entry_suspect_month",
    "entry_date_suspect_month": "entry_date_suspect_month",
}

def parse_msk(s):
    if not s or len(s) != 16:
        return None
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=MSK).astimezone(UTC)
    except ValueError:
        return None

def iso(t):
    return t.isoformat().replace("+00:00", "Z") if t is not None else None

def git_blob_sha(raw):
    return hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()

def load_candles(path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        t = dt.datetime.fromisoformat(r["timestamp_utc"].replace("Z", "+00:00"))
        if t in out:
            raise ValueError("duplicate hourly candle")
        out[t] = {k: float(r[k]) for k in ("open", "high", "low", "close")}
    return out

def location(bar, price):
    if bar is None:
        return "no_candle"
    if price > bar["high"]:
        return "above_high"
    if price < bar["low"]:
        return "below_low"
    return "inside"

def distance_pct(bar, price):
    if bar is None:
        return None
    if price > bar["high"]:
        return round(100 * (price - bar["high"]) / bar["high"], 4)
    if price < bar["low"]:
        return round(100 * (bar["low"] - price) / bar["low"], 4)
    return 0.0

def candidates(bars, marked, price):
    if marked is None:
        return []
    matches = []
    for offset in range(-12, 13):
        t = marked + offset * H
        bar = bars.get(t)
        if location(bar, price) == "inside":
            matches.append({"utc": iso(t), "offset_hours": offset,
                            "market_ohlc": bar})
    matches.sort(key=lambda x: (abs(x["offset_hours"]), x["offset_hours"]))
    return matches[:3]

def market_window(bars, marked, price):
    current = bars.get(marked)
    previous = bars.get(marked - H) if marked is not None else None
    distances = [distance_pct(b, price) for b in (current, previous) if b is not None]
    return {
        "marked_utc": iso(marked),
        "marked_market_ohlc": current,
        "previous_market_ohlc": previous,
        "annotated_price_vs_marked": location(current, price),
        "annotated_price_vs_previous": location(previous, price),
        "min_outside_distance_pct": round(min(distances), 4) if distances else None,
        "plausible_nearby_hours_within_12h": candidates(bars, marked, price),
    }

def first_stop_touch(bars, start, end, stop, side):
    if start is None or end is None:
        return None
    t = start + H  # omit ambiguous entry hour
    while t < end:  # omit ambiguous first exit hour
        b = bars.get(t)
        if b is not None and (b["low"] <= stop if side == "LONG" else b["high"] >= stop):
            return t
        t += H
    return None

def make_report(labels_path=LABELS, candles_path=CANDLES):
    with labels_path.open(newline="") as f:
        labels = list(csv.DictReader(f))
    bars = load_candles(candles_path)
    times = sorted(bars)
    if not times:
        raise ValueError("empty cached 1H history")
    counts = dict(n_source_trades=len(labels), n_inside_cache=0,
                  n_clean_inside_cache=0, n_outside_cache=0,
                  n_entry_price_outside_marked_and_prior_hour=0,
                  n_clean_exit1_price_outside_marked_and_prior_hour=0,
                  n_clean_static_stop_touch_before_exit=0,
                  n_source_quality_flags=0, n_distinct_flagged_ledger_rows=0)
    quality_counts = {}
    ledger = []
    for i, row in enumerate(labels, 1):
        rid = "R%02d" % i
        entry_t, exit_t = parse_msk(row["entry_msk"]), parse_msk(row["exit1_msk"])
        price, exit_price, stop = float(row["entry"]), float(row["exit1"]), float(row["sl"])
        side = "LONG" if stop < price else "SHORT"
        clean = row["quality"] == "ok"
        if not clean:
            counts["n_source_quality_flags"] += 1
            category = QUALITY.get(row["quality"], "other_original_flag")
            quality_counts[category] = quality_counts.get(category, 0) + 1
        inside = entry_t is not None and times[0] <= entry_t <= times[-1]
        if not inside:
            counts["n_outside_cache"] += 1
            if not clean:
                ledger.append({
                    "opaque_id": rid, "side": side,
                    "flags": ["original_source_quality_flag", "outside_cached_1h_coverage"],
                    "quality_category": category,
                    "quality_time_fields": {
                        "entry_utc": iso(entry_t), "exit1_utc": iso(exit_t),
                        "exit2_utc": iso(parse_msk(row["exit2_msk"])),
                        "exit2_time_status": ("missing_or_date_only" if row["exit2"] and
                                              parse_msk(row["exit2_msk"]) is None else
                                              "present_or_not_applicable"),
                    },
                    "market_ohlc": None,
                    "uncertainty": "Before cached coverage; no observed 1H OHLC or execution inference.",
                })
            continue
        counts["n_inside_cache"] += 1
        if clean:
            counts["n_clean_inside_cache"] += 1
        flags, details = [], {}
        entry = market_window(bars, entry_t, price)
        if entry["annotated_price_vs_marked"] != "inside" and entry["annotated_price_vs_previous"] != "inside":
            flags.append("entry_price_not_in_marked_or_prior_1h")
            counts["n_entry_price_outside_marked_and_prior_hour"] += 1
            details["entry"] = entry
        if clean and exit_t is not None:
            first_exit = market_window(bars, exit_t, exit_price)
            if first_exit["annotated_price_vs_marked"] != "inside" and first_exit["annotated_price_vs_previous"] != "inside":
                flags.append("first_exit_price_not_in_marked_or_prior_1h")
                counts["n_clean_exit1_price_outside_marked_and_prior_hour"] += 1
                details["first_exit"] = first_exit
            touched = first_stop_touch(bars, entry_t, exit_t, stop, side)
            if touched is not None:
                flags.append("initial_static_stop_touched_before_annotated_exit")
                counts["n_clean_static_stop_touch_before_exit"] += 1
                details["stop"] = {
                    "first_touch_hour_utc": iso(touched),
                    "market_ohlc": bars[touched],
                    "assumption": "initial stop remained active and OHLC touch implies execution; unverified",
                }
        if not clean:
            flags.append("original_source_quality_flag")
            details["quality_category"] = category
            details["quality_time_fields"] = {
                "entry_utc": iso(entry_t), "exit1_utc": iso(exit_t),
                "exit2_utc": iso(parse_msk(row["exit2_msk"])),
                "exit2_time_status": ("missing_or_date_only" if row["exit2"] and
                                      parse_msk(row["exit2_msk"]) is None else
                                      "present_or_not_applicable"),
            }
        if flags:
            ledger.append({"opaque_id": rid, "side": side, "flags": flags, **details})
    counts["n_distinct_flagged_ledger_rows"] = len(ledger)
    raw_labels, raw_candles = labels_path.read_bytes(), candles_path.read_bytes()
    return {
        "title": "Redacted 42-trade BTC 1H execution discrepancy ledger — observational QA only",
        "schema_version": "1.0.0",
        "scope": "all 42 complete self-reported BTC trades; never assert that all market opportunities were traded",
        "source": {
            "trade_labels": str(labels_path), "labels_git_blob_sha": git_blob_sha(raw_labels),
            "cached_1h": str(candles_path), "cached_1h_git_blob_sha": git_blob_sha(raw_candles),
            "cached_1h_sha256": hashlib.sha256(raw_candles).hexdigest(),
            "labels_sha256": hashlib.sha256(raw_labels).hexdigest(),
            "first_utc": iso(times[0]), "last_utc": iso(times[-1]), "n_1h": len(times),
        },
        "rules": {
            "timezone": "MSK UTC+03:00; timestamps are user annotations, not verified exchange fills",
            "price_containment": "annotated price inside [low,high] in marked or preceding 1H candle; exact equality allowed",
            "nearby_candidate": "up to three nearest containing 1H bars within ±12h; not evidence of actual fill",
            "static_stop": "test only clean records, on whole 1H bars strictly after entry hour and strictly before first exit hour; assume initial SL never revised",
            "privacy": "only opaque row IDs, public cached market OHLC, relative distance and source-quality category; no original annotated entry/exit/stop prices; outside-cache flagged records retained with missing market data.",
        },
        "summary": counts,
        "quality_counts": quality_counts,
        "discrepancies": ledger,
        "provenance_gaps": [
            "Venue, instrument type, contract, mark/last trigger, chart timezone, order fill IDs and stop modifications are not evidenced by the cache.",
            "Original source values remain unchanged; a nearby containing candle is only a candidate timing explanation.",
            "Eight pre-cache annotations cannot be tested; no cross-venue splicing or backfilling.",
            "The complete journal is not a random sample of all market signal opportunities; all historical periods have been inspected.",
        ],
        "decisions": {
            "reconciled": 0, "unresolved_ledger_rows": len(ledger),
            "live_or_paper_orders": 0, "funding": "excluded by owner research instruction",
            "roundtrip_cost_assumption": "0.15% used for annotated PnL elsewhere; no PnL recomputed here",
            "strategy_promotion": "NONE",
        },
    }

def main():
    report = make_report()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    assert report["summary"]["n_source_trades"] == 42
    assert report["summary"]["n_inside_cache"] == 34
    assert report["summary"]["n_clean_inside_cache"] == 31
    assert report["summary"]["n_entry_price_outside_marked_and_prior_hour"] == 5
    assert report["summary"]["n_clean_exit1_price_outside_marked_and_prior_hour"] == 8
    assert report["summary"]["n_clean_static_stop_touch_before_exit"] == 1
    assert report["summary"]["n_source_quality_flags"] == 4
    assert report["summary"]["n_distinct_flagged_ledger_rows"] == 14
    print(json.dumps(report["summary"], indent=2))

if __name__ == "__main__":
    main()
