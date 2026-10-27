"""#20/#19: frozen, causal PRICE-RANGE gate ablation on 4H DeltaRSI turn signals.
Cached 1H candles only. No network, funding or orders.
Reproduce: python -m unittest -v test_price_range_gate_audit && python price_range_gate_audit.py
"""
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from causal_4h_parity_audit import H, FOUR, events, execute, iso, load, metrics, trade
from manual_trade_label_audit import normalize

FEE = .0015
CUTOFFS = ("2026-04-27T00:00:00+00:00", "2026-07-27T06:00:00+00:00")
SYMS = ("BTCUSDT", "ETHUSDT", "ICPUSDT", "HYPEUSDT")
GATES = ("range6_pct", "range24_pct", "bb_width20")
LABELS = Path("data/manual_btc_trades_2025_2026.csv")
OUT = Path("reports/price_range_gate_audit.json")
RULES = {
    "range6_pct": "prior 6 completed 4H high-low width / latest completed close >= TRAIN median",
    "range24_pct": "prior 24 completed 4H high-low width / latest completed close >= TRAIN median",
    "bb_width20": "4 * population stddev(last 20 completed 4H closes) / mean >= TRAIN median",
}

def utc_ms(value):
    return int(dt.datetime.fromisoformat(value).timestamp() * 1000)

def range_features(rows, decision_ms):
    """Every included 4H candle must CLOSE by decision_ms, never use forming future."""
    ends = [r[0] + FOUR for r in rows]
    i = bisect.bisect_right(ends, decision_ms)
    if i < 24:
        return None
    closed = rows[:i]
    last_close = closed[-1][4]
    if last_close <= 0:
        return None
    def width(n):
        v = closed[-n:]
        return (max(x[2] for x in v) - min(x[3] for x in v)) / last_close
    closes = [x[4] for x in closed[-20:]]
    bb = 4 * statistics.pstdev(closes) / statistics.mean(closes)
    return dict(range6_pct=width(6), range24_pct=width(24), bb_width20=bb,
                asof_last_4h_close_utc=iso(closed[-1][0] + FOUR))

def add_features(raw, signal_events, rows):
    out = []
    for e in signal_events:
        f = range_features(rows, e["decision_ms"])
        if f is not None and all(math.isfinite(f[g]) for g in GATES):
            out.append(dict(e, price_range=f))
    return out

def summarize_opportunities(raw, es):
    vals = []
    for e in es:
        t = trade(raw, e, FEE, 0.)
        if t is not None:
            vals.append(t["net_R"])
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    return dict(n=len(vals),
                win_pct=round(100 * len(wins) / len(vals), 2) if vals else None,
                mean_net_R=round(statistics.mean(vals), 5) if vals else None,
                pf_R=round(sum(wins) / -sum(losses), 4) if losses else None)

def split_events(raw, es, start, end):
    return [e for e in es if start <= e["entry_i"] < end]

def train_medians(es, cutoff):
    train = [e for e in es if e["entry_ms"] < cutoff]
    if not train:
        raise ValueError("No train events; cannot calibrate price range")
    return {g: statistics.median(e["price_range"][g] for e in train) for g in GATES}

def label_comparison(rows, es, cache_start, cache_end):
    with LABELS.open(newline="") as f:
        labels = [normalize(r) for r in csv.DictReader(f)]
    clean = [r for r in labels if not r["issues"] and
             r["entry_ms"] is not None and cache_start <= r["entry_ms"] < cache_end]
    labelled = []
    matched = []
    for r in clean:
        f = range_features(rows, r["entry_ms"])
        if f is None:
            continue
        labelled.append(f)
        nearby = [e for e in es if e["side"] == r["side"] and
                  abs(e["entry_ms"] - r["entry_ms"]) <= 4 * H]
        if nearby:
            matched.append(min(nearby, key=lambda e: abs(e["entry_ms"] - r["entry_ms"])))
    # This is not a case-control causal estimate: labels may be decision annotations,
    # while the control catalog is an automatic, narrower signal family.
    def med(items, key):
        return round(statistics.median(x[key] for x in items), 6) if items else None
    return dict(n_clean_cached=len(clean), n_with_causal_features=len(labelled),
                n_near_frozen_turn_same_side=len(matched),
                label_median={g: med(labelled, g) for g in GATES},
                all_candidate_median={g: med([e["price_range"] for e in es], g) for g in GATES},
                matched_candidate_median={g: med([e["price_range"] for e in matched], g) for g in GATES},
                notes=["The 42 BTC rows are the complete owner journal, but 4 have unreconciled transcription issues.",
                       "Near-match <=4h is a diagnostic, NOT proof of identical fill or timing.",
                       "This frozen-turn control family is narrower than all visual histogram color transitions."])

def run_asset(sym):
    raw, sha = load(sym)
    event_sets, rows = events(raw)
    es = add_features(raw, event_sets["frozen_turn"], rows)
    # HYPE history starts AFTER the BTC/ETH/ICP common training cutoff.
    # Never pretend that it shares their UTC train/validation calendar.
    if sym == "HYPEUSDT":
        cut = [0, len(raw)//2, 3*len(raw)//4, len(raw)]
        train_cutoff = raw[cut[1]][0]
        split_method = "HYPE-only 50/25/25 chronological negative control; NOT common calendar"
    else:
        cut = [0] + [bisect.bisect_left([r[0] for r in raw], utc_ms(c)) for c in CUTOFFS] + [len(raw)]
        train_cutoff = utc_ms(CUTOFFS[0])
        split_method = "BTC/ETH/ICP aligned UTC cutoffs"
    if cut != sorted(cut):
        raise ValueError("UTC split boundaries outside chronological cache")
    thresholds = train_medians(es, train_cutoff)
    windows = {}
    for k, (a, b) in enumerate(zip(cut[:-1], cut[1:])):
        name = ("train", "validation", "inspected_diagnostic")[k]
        subset = split_events(raw, es, a, b)
        base = metrics(execute(raw, subset, FEE, 0., a, b))
        filters = {}
        for g in GATES:
            passed = [e for e in subset if e["price_range"][g] >= thresholds[g]]
            rejected = [e for e in subset if e["price_range"][g] < thresholds[g]]
            filters[g] = dict(threshold=round(thresholds[g], 8),
                              admitted_candidates=len(passed),
                              rejected_candidates=len(rejected),
                              independently_scheduled=metrics(execute(raw, passed, FEE, 0., a, b)),
                              paired_opportunity_pass=summarize_opportunities(raw, passed),
                              paired_opportunity_reject=summarize_opportunities(raw, rejected),
                              by_side={
                                  label: dict(admitted=sum(e["side"] == side for e in passed),
                                              rejected=sum(e["side"] == side for e in rejected))
                                  for side, label in ((1, "LONG"), (-1, "SHORT"))})
        windows[name] = dict(start_utc=iso(raw[a][0]) if a < len(raw) else None,
                             end_exclusive_utc=iso(raw[b][0]) if b < len(raw) else iso(raw[-1][0] + H),
                             baseline=base, n_candidates=len(subset), gates=filters)
    return dict(source_sha256=sha, split_method=split_method, n_hours=len(raw), n_4h=len(rows),
                first_utc=iso(raw[0][0]), last_utc=iso(raw[-1][0]),
                n_frozen_turn_events=len(es), train_only_thresholds=thresholds,
                windows=windows,
                labels=label_comparison(rows, es, raw[0][0], raw[-1][0]+H) if sym == "BTCUSDT" else None)

def main():
    report = dict(title="Causal price-range volatility eligibility gates on frozen DeltaRSI turns",
                  generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  fee_roundtrip=FEE, funding="excluded by owner instruction",
                  gates=RULES, thresholds="per-symbol median of eligible train events ONLY; never selected on validation/diagnostic outcomes",
                  split_cutoffs_utc=CUTOFFS, assets={},
                  limitations=[
                      "ALL cached chronological periods have been previously inspected: NOT untouched OOS.",
                      "Frozen 4H turn is a narrow signal subset, not every discretionary histogram color transition.",
                      "Price-range features are computed from 4H candles closed by decision; no future candles.",
                      "Per-symbol medians calibrate eligibility without labels or outcome optimization; not portable fixed thresholds.",
                      "Filtered and baseline schedules have different admissions/reentries: do not interpret return differences as paired causal effects.",
                      "Matched opportunity summaries ignore scheduling/capital competition; portfolio DD is only closed-trade pseudo DD.",
                      "No direct venue provenance, no real fills, 1H OHLC stop-first and adverse-gap model.",
                      "HYPE begins after the shared train cutoff and uses its own separate 50/25/25 negative-control splits.",
                      "No cross-asset shared capital or hourly MTM drawdown. No real orders."])
    for sym in SYMS:
        report["assets"][sym] = run_asset(sym)
        print(sym, {w: {g: x["independently_scheduled"]["mean_R"]
                         for g, x in r["gates"].items()}
                    for w, r in report["assets"][sym]["windows"].items()}, flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("WROTE", OUT, flush=True)
    return report

if __name__ == "__main__":
    main()
