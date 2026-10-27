"""Independent UTC funding-clock audit on FROZEN cached DeltaRSI ledgers.

No exchange requests, candle downloads, strategy tuning or orders. Event counts
are enumerated from UTC timestamps, never inferred from booked funding debits.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

PERIOD_MS = 8 * 60 * 60 * 1000
HOUR_MS = 60 * 60 * 1000
RATE = .0003
COST = .0015
OLD = Path("reports/portfolio_risk_audit.json")
NEW = Path("reports/causal_4h_portfolio_audit.json")
OUT = Path("reports/independent_funding_clock_audit.json")


def to_ms(value: str) -> int:
    d = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() != dt.timedelta(0):
        raise ValueError("UTC timestamp required: " + value)
    return int(d.timestamp() * 1000)


def events(entry: int, exit_at: int, include_exit: bool) -> list[int]:
    """Explicitly enumerate settlement instants strictly AFTER entry.

    An event exactly at the exit is excluded in the lower bound, included in
    the upper bound. The entry boundary is always excluded.
    """
    if not isinstance(entry, int) or not isinstance(exit_at, int):
        raise TypeError("integer UTC milliseconds required")
    if exit_at < entry:
        raise ValueError("exit precedes entry")
    out = []
    t = (entry // PERIOD_MS + 1) * PERIOD_MS
    while t <= exit_at:
        if t < exit_at or include_exit:
            out.append(t)
        t += PERIOD_MS
    return out


def bounds(entry: int, earliest: int, latest: int) -> tuple[int, int]:
    if earliest < entry or latest < earliest:
        raise ValueError("invalid feasible exit interval")
    return len(events(entry, earliest, False)), len(events(entry, latest, True))


def hourly_bounds(x: dict) -> tuple[int, int]:
    entry, end = x["entry_ms"], x["exit_ms"]
    # OHLC cannot identify the intrahour stop/TP instant. An opening gap
    # could make this interval wider than necessary, never narrower.
    earliest = max(entry, end - HOUR_MS) if x["reason"] in ("stop", "target") else end
    return bounds(entry, earliest, end)


def old_bounds(x: dict) -> tuple[int, int]:
    return bounds(to_ms(x["entry_utc"]), to_ms(x["exit_utc_earliest"]),
                  to_ms(x["exit_utc_latest"]))


def check_ledger(x: dict, lo: int, hi: int, hourly: bool) -> None:
    notional = (x["quantity"] * x["entry_price"]) if hourly else x["notional"]
    funding = x["funding"] if hourly else x["funding_max"]
    if notional <= 0 or not (0 <= lo <= hi):
        raise AssertionError("invalid notional or exposure")
    if not math.isclose(funding, notional * RATE * hi, abs_tol=1e-8, rel_tol=0):
        raise AssertionError("funding mismatch with independent UTC event clock")
    entry = x["entry_price"] if hourly else x["entry"]
    exit_price = x["exit_price"] if hourly else x["exit"]
    fees = x["fees"]
    expected_fees = x["quantity"] * (entry + exit_price) * COST / 2
    if not math.isclose(fees, expected_fees, abs_tol=1e-8, rel_tol=0):
        raise AssertionError("fees do not use actual entry and exit notionals")
    gross = x["gross"] if hourly else x["gross_pnl"]
    net = x["net"] if hourly else x["net_pnl"]
    if not math.isclose(net, gross - fees - funding, abs_tol=1e-8, rel_tol=0):
        raise AssertionError("gross - fees - funding != net")


def audit(old: dict, new: dict) -> dict:
    if old["source_hashes"] != new["source_sha256"]:
        raise AssertionError("candle hashes differ")
    four = old["full_common_history"]["baseline"]["trades"]
    one = new["full"]["frozen_turn"]["primary_trade_ledger"]
    old_ids = {(x["symbol"], x["entry_utc"]): x for x in four}
    one_ids = {(x["symbol"], dt.datetime.fromtimestamp(
        x["entry_ms"] / 1000, dt.timezone.utc).isoformat()): x for x in one}
    if len(old_ids) != len(four) or len(one_ids) != len(one) or set(old_ids) != set(one_ids):
        raise AssertionError("duplicate or unmatched frozen trade IDs")
    rows, mismatches = [], []
    per_reason = defaultdict(Counter)
    for key in sorted(old_ids):
        x, y = old_ids[key], one_ids[key]
        if x["exit_reason"] != y["reason"] or x["side"] != ("LONG" if y["side"] == 1 else "SHORT"):
            raise AssertionError("exit reason/side parity")
        if abs(x["entry"] - y["entry_price"]) > 1e-8 or abs(x["exit"] - y["exit_price"]) > 1e-8:
            raise AssertionError("entry/exit fill parity")
        l4, u4 = old_bounds(x)
        l1, u1 = hourly_bounds(y)
        check_ledger(x, l4, u4, False)
        check_ledger(y, l1, u1, True)
        if "funding_events_max" in x and x["funding_events_max"] != u4:
            raise AssertionError("4H reported upper count != independently enumerated UTC count")
        if "funding_events_min" in x and x["funding_events_min"] != l4:
            raise AssertionError("4H reported lower count != independently enumerated UTC count")
        if u4 != u1:
            mismatches.append({"symbol":key[0], "entry_utc":key[1],
                               "4h_max":u4, "1h_max":u1, "reason":x["exit_reason"]})
        per_reason[x["exit_reason"]]["n"] += 1
        per_reason[x["exit_reason"]]["4h_upper_excess"] += u4 - u1
        row = {
            "symbol":key[0], "entry_utc":key[1], "side":x["side"],
            "reason":x["exit_reason"], "4h_exit_earliest":x["exit_utc_earliest"],
            "4h_exit_latest":x["exit_utc_latest"],
            "1h_exit_latest":dt.datetime.fromtimestamp(y["exit_ms"]/1000, dt.timezone.utc).isoformat(),
            "4h_events_min":l4, "4h_events_max":u4,
            "1h_events_min":l1, "1h_events_max":u1,
            "4h_qty":x["quantity"], "1h_qty":y["quantity"],
            "4h_gross":x["gross_pnl"], "1h_gross":y["gross"],
            "4h_fees":x["fees"], "1h_fees":y["fees"],
            "4h_funding":x["funding_max"], "1h_funding":y["funding"],
            "4h_net":x["net_pnl"], "1h_net":y["net"],
            "delta_funding_4h_minus_1h":x["funding_max"]-y["funding"],
            "delta_net_4h_minus_1h":x["net_pnl"]-y["net"],
        }
        rows.append(row)
    # Independent event census on ALL three 1H modes, not just the baseline.
    modes = {}
    for mode in ("forming", "closed", "frozen_turn"):
        ledger = new["full"][mode]["primary_trade_ledger"]
        low = high = uncertain_cash = 0.
        by_reason = defaultdict(Counter)
        for x in ledger:
            l, u = hourly_bounds(x)
            check_ledger(x, l, u, True)
            low += l
            high += u
            uncertainty = (u-l)*x["quantity"]*x["entry_price"]*RATE
            uncertain_cash += uncertainty
            by_reason[x["reason"]]["n"] += 1
            by_reason[x["reason"]]["uncertain_events"] += u-l
        modes[mode] = {
            "n":len(ledger), "min_events":int(low), "max_events":int(high),
            "ambiguous_events":int(high-low),
            "upper_minus_lower_debit_pct_initial_equity_at_3bp":round(100*uncertain_cash, 8),
            "by_exit_reason":{k:dict(v) for k,v in sorted(by_reason.items())}
        }
    return {
        "title":"P0 #12 independent UTC funding boundary enumeration on cached ledgers",
        "scope":"4H vs 1H frozen 309 matched trades plus 1H forming/closed ledgers",
        "source_sha256":old["source_hashes"],
        "config_4h_sha256":old["strategy_hash"],
        "config_1h_sha256":new["config_sha256"],
        "funding_per_event":RATE, "roundtrip_cost":COST,
        "boundary":"entry timestamp excluded; exit timestamp excluded lower/included upper; stop/target intrabar interval conservatively bounded; gap not identifiable from 1H trade ledger alone",
        "matched_frozen_trades":len(rows),
        "4h_upper_excess_vs_1h":len(mismatches),
        "4h_upper_excess_examples":mismatches[:25],
        "by_exit_reason":{k:dict(v) for k,v in sorted(per_reason.items())},
        "1h_modes":modes,
        "paired_trade_rows":rows,
        "limitations":[
            "No venue funding observations; 3bp adverse funding is synthetic.",
            "Lower/upper aggregate debit difference is a fixed-size sensitivity, not a re-simulated compounded portfolio return.",
            "All cached historical periods previously inspected; no independent OOS.",
            "OHLC and trade ledgers do not identify intrabar fills or funding-versus-exit ordering.",
            "Admission-ledger and ETH-challenger full nine-cell parity are separate open #12 requirements."
        ],
    }


def main() -> None:
    old = json.loads(OLD.read_text())
    new = json.loads(NEW.read_text())
    report = audit(old, new)
    report["input_report_sha256"] = {
        str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (OLD, NEW)
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k not in
                      ("paired_trade_rows","4h_upper_excess_examples")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
