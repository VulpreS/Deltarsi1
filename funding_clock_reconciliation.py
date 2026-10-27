"""P0 #12: decompose 4H-vs-1H frozen-turn funding/equity mismatch.

Reads already committed reports derived from cached 1H OHLC; no data download,
exchange connection, orders, strategy tuning or new sample selection.
"""
import datetime as dt
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

RATE = 0.0003
OLD = Path("reports/portfolio_risk_audit.json")
NEW = Path("reports/causal_4h_portfolio_audit.json")
OUT = Path("reports/funding_clock_reconciliation.json")


def key4(x):
    return x["symbol"], x["entry_utc"]


def key1(x):
    return x["symbol"], dt.datetime.fromtimestamp(x["entry_ms"] / 1000, dt.timezone.utc).isoformat()


def event_count_1h(x, rate=RATE):
    """Recover integer adverse funding event count from exact 1H ledger cash debit."""
    notional = x["quantity"] * x["entry_price"]
    if notional <= 0 or rate <= 0:
        raise ValueError("Nonpositive notional/rate")
    n = x["funding"] / (notional * rate)
    if not math.isfinite(n) or abs(n - round(n)) > 1e-6 or n < -1e-8:
        raise AssertionError("1H funding not an integer UTC event count: " + str(n))
    return int(round(n))


def check_cash(trades, final_cash, initial=1., one_hour=False):
    field = "net" if one_hour else "net_pnl"
    discrepancy = final_cash - initial - sum(x[field] for x in trades)
    if abs(discrepancy) > 1e-8:
        raise AssertionError("Cash conservation failure " + str(discrepancy))
    return discrepancy


def reconcile(old, new, rate=RATE):
    if old["source_hashes"] != new["source_sha256"]:
        raise AssertionError("Source candle SHA256 mismatch")
    a = old["full_common_history"]["baseline"]["trades"]
    b = new["full"]["frozen_turn"]["primary_trade_ledger"]
    aa, bb = {key4(x): x for x in a}, {key1(x): x for x in b}
    if len(aa) != len(a) or len(bb) != len(b):
        raise AssertionError("Duplicate trade IDs")
    if set(aa) != set(bb):
        raise AssertionError("Different trade IDs: 4h_only=%d 1h_only=%d" %
                             (len(set(aa) - set(bb)), len(set(bb) - set(aa))))
    if not a:
        raise AssertionError("Empty ledger")
    by_asset = defaultdict(lambda: Counter())
    by_reason = defaultdict(lambda: Counter())
    events = Counter()
    differences = []
    totals = Counter()
    for k in sorted(aa):
        x, y = aa[k], bb[k]
        if x["side"] != ("LONG" if y["side"] == 1 else "SHORT"):
            raise AssertionError("Side mismatch " + str(k))
        if x["exit_reason"] != y["reason"] or abs(x["entry"] - y["entry_price"]) > 1e-8 or abs(x["exit"] - y["exit_price"]) > 1e-8:
            raise AssertionError("Fill/reason mismatch " + str(k))
        n4, n1 = int(x["funding_events_max"]), event_count_1h(y, rate)
        p4, p1 = x["notional"], y["quantity"] * y["entry_price"]
        if abs(x["funding_max"] - p4 * rate * n4) > 1e-8:
            raise AssertionError("4H funding accounting mismatch " + str(k))
        # Algebraic decomposition of funding difference at fixed 4H notional,
        # then due to compounded sizing change at the 1H event count.
        timing = rate * p4 * (n4 - n1)
        sizing = rate * (p4 - p1) * n1
        fdelta = x["funding_max"] - y["funding"]
        if abs(fdelta - timing - sizing) > 1e-8:
            raise AssertionError("Funding decomposition mismatch " + str(k))
        grossdelta = x["gross_pnl"] - y["gross"]
        feedelta = x["fees"] - y["fees"]
        netdelta = x["net_pnl"] - y["net"]
        if abs(netdelta - (grossdelta - feedelta - fdelta)) > 1e-8:
            raise AssertionError("Net trade accounting mismatch " + str(k))
        events["4h_" + str(n4)] += 1
        events["1h_" + str(n1)] += 1
        events["4h_more"] += n4 > n1
        events["1h_more"] += n1 > n4
        events["equal"] += n1 == n4
        for group in (by_asset[k[0]], by_reason[x["exit_reason"]]):
            group["n"] += 1
            group["4h_more"] += n4 > n1
            group["1h_more"] += n1 > n4
            group["equal"] += n4 == n1
            group["timing_funding_delta"] += timing
            group["sizing_funding_delta"] += sizing
        for field, value in (("gross_delta", grossdelta), ("fee_delta", feedelta),
                             ("funding_delta", fdelta), ("timing_funding_delta", timing),
                             ("sizing_funding_delta", sizing), ("net_delta", netdelta)):
            totals[field] += value
        if n4 != n1:
            differences.append({"symbol":k[0], "entry_utc":k[1],
                                "exit_reason":x["exit_reason"],
                                "4h_events_max":n4, "1h_events_max":n1,
                                "4h_exit_earliest":x["exit_utc_earliest"],
                                "4h_exit_latest":x["exit_utc_latest"],
                                "1h_exit_latest":dt.datetime.fromtimestamp(y["exit_ms"] / 1000, dt.timezone.utc).isoformat(),
                                "funding_delta_at_fixed_4h_notional":round(timing, 10)})
    cash4 = old["full_common_history"]["baseline"]["metrics"]["net_return_pct"] / 100
    cash1 = new["full"]["frozen_turn"]["primary"]["net_return_pct"] / 100
    # Return percentages are rounded to 4 decimals; test each engine separately,
    # not just their difference (which could hide offsetting accounting errors).
    if abs(sum(x["net_pnl"] for x in a) - cash4) > 5.1e-7:
        raise AssertionError("4H net ledger does not conserve reported equity")
    if abs(sum(x["net"] for x in b) - cash1) > 5.1e-7:
        raise AssertionError("1H net ledger does not conserve reported equity")
    if abs(totals["net_delta"] - (cash4 - cash1)) > 1.1e-6:
        raise AssertionError("Net return vs ledger mismatch")
    grid = {}
    for cost in (15, 25, 40):
        for f in (0, 1, 3):
            oldkey = f"{cost}bp_fee_{f}bp_funding"
            newkey = f"{cost}bp_cost_{f}bp_funding"
            om = old["full_common_history"]["baseline"]["stress_grid"][oldkey]
            nm = new["full"]["frozen_turn"]["stress"][newkey]
            if om["n"] != nm["n"]:
                raise AssertionError("Different cohort in stress grid " + oldkey)
            grid[f"{cost}bp_cost_{f}bp_funding"] = {
                "n":om["n"],
                "4h_return_pct":om["net_return_pct"],
                "1h_return_pct":nm["net_return_pct"],
                "delta_1h_minus_4h_pp":round(nm["net_return_pct"] - om["net_return_pct"], 4),
                "4h_pf":om["net_pf"], "1h_pf":nm["pf"],
                "4h_dd_pct":om["max_close_to_close_mtm_dd_pct"],
                "1h_hourly_close_dd_pct":nm["max_hourly_close_mtm_dd_pct"],
            }
    return {
        "title":"P0 #12 funding-clock decomposition of matched frozen 4H turn trades",
        "producer_sha":os.environ.get("GITHUB_SHA", "local"),
        "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_sha256":old["source_hashes"],
        "source_report_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (OLD, NEW) if p.is_file()},
        "old_config_hash":old["strategy_hash"], "new_config_hash":new["config_sha256"],
        "assumption":"Both models charge synthetic adverse 3bp per 00/08/16 UTC event, upper-bound OHLC timing. 1H tighter bounds are not observed fills.",
        "matched_trade_ids":len(a), "event_counts":dict(events),
        "by_asset":{k:dict(v) for k,v in by_asset.items()},
        "by_exit_reason":{k:dict(v) for k,v in by_reason.items()},
        "sum_4h_minus_1h":{k:round(v,10) for k,v in totals.items()},
        "cash_reconciliation_4h_minus_1h":round(cash4 - cash1, 8),
        "funding_clock_different_trades":len(differences),
        "funding_clock_examples":differences[:25],
        "cost_funding_grid":grid,
        "limitations":[
            "All historical data previously inspected; this is not independent OOS.",
            "Funding is synthetic, not exchange funding; event ordering at exact boundary unknown.",
            "4H intrabar upper-bound exit window is wider than 1H; neither identifies actual fill time.",
            "Quantities compound from prior cash differences; this is an accounting decomposition, not an executable re-optimized strategy.",
            "1H vs 4H mark-to-market drawdowns use different clock frequencies and are not directly comparable.",
            "Venue, market type, mark-price stop triggering and actual spread/slippage remain unknown.",
            "No real orders or trading API calls."
        ],
        "conclusion":"Do not attribute 1H/4H PnL gap to alpha. Freeze 1H upper-bound clock as the more granular synthetic convention for future comparisons, pending observed venue funding."
    }


def main():
    old = json.loads(OLD.read_text())
    new = json.loads(NEW.read_text())
    report = reconcile(old, new)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"matched_trade_ids":report["matched_trade_ids"],
                      "event_counts":report["event_counts"],
                      "sum_4h_minus_1h":report["sum_4h_minus_1h"]}))


if __name__ == "__main__":
    main()
