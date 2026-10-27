"""Cycle 18 (#20/#19): two PRE-REGISTERED price/DeltaRSI interaction hypotheses.
Preregistration: issue #20 comment 6437564897 (before any backtest).
Cached 1H only. No funding, downloads, API orders or threshold search.
Reproduce: python -m unittest -v test_color_interaction_audit && python color_interaction_audit.py
"""
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from analyze_mtf_5y import indicator
from causal_4h_parity_audit import H, FOUR, load, trade, execute, metrics, events, iso
from completed_candles import aggregate_completed
from manual_trade_label_audit import normalize
from research_multiasset import atr

FEE = .0015
COSTS = (.0015, .0025, .004)
RISK = .0025
SEED = 20261027
SYMS = ("BTCUSDT", "ETHUSDT", "ICPUSDT", "HYPEUSDT")
CUTOFFS = ("2026-04-27T00:00:00+00:00", "2026-07-27T06:00:00+00:00")
OUT = Path("reports/color_interaction_audit.json")
PREREG = "https://github.com/VulpreS/Deltarsi1/issues/20#issuecomment-6437564897"
INTENSITY = {"weak": 0, "medium": 1, "strong": 2}


def utc_ms(s):
    return int(dt.datetime.fromisoformat(s).timestamp() * 1000)


def less_intense(prev_color, new_color, prev_delta, new_delta):
    """Same-sign, strictly weaker COLOR and absolute Delta; no weak->weak repeats."""
    if not all(math.isfinite(v) for v in (prev_delta, new_delta)):
        return False
    if prev_delta * new_delta <= 0 or abs(new_delta) >= abs(prev_delta):
        return False
    if not prev_color or not new_color or prev_color[-1] != new_color[-1]:
        return False
    return INTENSITY.get(new_color[:-1], -1) < INTENSITY.get(prev_color[:-1], -1)


def width(bars, denominator):
    return (max(b[2] for b in bars) - min(b[3] for b in bars)) / denominator


def price_context(bars, i, side):
    """Only bars through i are visible. P=[i-11..i-6], C=[i-5..i]."""
    if i < 12:
        return None
    p = bars[i-11:i-5]
    c = bars[i-5:i+1]
    prior6 = bars[i-6:i]
    if len(p) != 6 or len(c) != 6 or len(prior6) != 6:
        return None
    prev_close, cur_close = p[-1][4], c[-1][4]
    if prev_close <= 0 or cur_close <= 0:
        return None
    old_width = width(p, prev_close)
    new_width = width(c, cur_close)
    h6 = max(b[2] for b in prior6)
    l6 = min(b[3] for b in prior6)
    sweep = (bars[i][3] < l6 and cur_close > l6) if side == 1 else (
        bars[i][2] > h6 and cur_close < h6)
    overshoot = ((l6 - bars[i][3]) if side == 1 else (bars[i][2] - h6)) / prior6[-1][4]
    return dict(prior6_range_pct=100*old_width,
                current6_range_pct=100*new_width,
                expansion_ratio=new_width/old_width if old_width > 0 else None,
                prior_six_range_pct=100*(h6-l6)/prior6[-1][4],
                sweep_overshoot_pct=100*overshoot,
                sweep_reclaim=bool(sweep),
                feature_source_last_4h_close_utc=iso(bars[i][0]+FOUR))


def color_events(raw, bars=None):
    """Complete 4H COLOR transition census, not frozen-turn/ratio-qualified subset."""
    if bars is None:
        bars = aggregate_completed(raw, 4, asof_ms=raw[-1][0]+H)
    ind = indicator(bars)
    a = atr(bars)
    hourly = {b[0]: k for k, b in enumerate(raw)}
    out = []
    rejected = Counter()
    for i in range(210, len(bars)):
        prev, cur = ind["color"][i-1], ind["color"][i]
        if not less_intense(prev, cur, ind["delta"][i-1], ind["delta"][i]):
            continue
        side = 1 if cur.endswith("R") else -1
        decision = bars[i][0]+FOUR
        entry_i = hourly.get(decision)
        if entry_i is None:
            rejected["missing_next_hour_open"] += 1
            continue
        f = price_context(bars, i, side)
        if f is None or f["expansion_ratio"] is None or not math.isfinite(a[i]) or a[i] <= 0:
            rejected["invalid_price_context_or_ATR"] += 1
            continue
        if entry_i == 0 or raw[entry_i-1][0]+H != decision:
            rejected["last_known_1h_not_closed_at_decision"] += 1
            continue
        eid = "%s:%s:%s" % ("BTC" if False else "", "", "")  # overwritten below
        eid = iso(decision) + (":L" if side == 1 else ":S")
        out.append(dict(event_id=eid, bucket_ms=bars[i][0],
                        decision_ms=decision, decision_utc=iso(decision),
                        entry_ms=decision, entry_utc=iso(decision), entry_i=entry_i,
                        side=side, prior_color=prev, new_color=cur,
                        prior_delta=ind["delta"][i-1], delta=ind["delta"][i],
                        last_known_1h_close_utc=iso(raw[entry_i-1][0]+H),
                        atr_4h=a[i], price=f))
    return out, dict(rejected)


def train_thresholds(events_long, cutoff):
    train = [e for e in events_long if e["entry_ms"] < cutoff]
    if not train:
        raise ValueError("No TRAIN LONG color transitions; no calibration")
    return dict(prior6_range_pct_median=statistics.median(
                    e["price"]["prior6_range_pct"] for e in train),
                expansion_ratio_median=statistics.median(
                    e["price"]["expansion_ratio"] for e in train),
                n_train=len(train))


def admissible(e, rule, threshold):
    if rule == "baseline":
        return True
    if rule == "H1_LONG_expansion":
        return (e["side"] == 1 and
                e["price"]["prior6_range_pct"] <= threshold["prior6_range_pct_median"] and
                e["price"]["expansion_ratio"] >= threshold["expansion_ratio_median"] and
                e["price"]["expansion_ratio"] > 1)
    if rule == "H2_SHORT_upper_sweep":
        return e["side"] == -1 and e["price"]["sweep_reclaim"]
    raise ValueError(rule)


def one_to_one_matches(event_list, label_list, tolerance_ms=4*H):
    """Closest UTC same-side candidates, greedy globally; never duplicate a label/event."""
    pairs = []
    for j, lab in enumerate(label_list):
        if lab["entry_ms"] is None:
            continue
        for k, e in enumerate(event_list):
            if lab["side"] != e["side"]:
                continue
            gap = abs(lab["entry_ms"] - e["entry_ms"])
            if gap <= tolerance_ms:
                pairs.append((gap, j, k))
    used_labels, used_events, matched = set(), set(), {}
    for gap, j, k in sorted(pairs):
        if j in used_labels or k in used_events:
            continue
        used_labels.add(j)
        used_events.add(k)
        matched[event_list[k]["event_id"]] = dict(label_id=label_list[j]["row_id"],
                                                    gap_hours=gap/H)
    return matched, dict(labels=len(label_list), labels_matched=len(used_labels),
                         events_matched=len(used_events),
                         labels_unmatched=len(label_list)-len(used_labels),
                         events_unmatched=len(event_list)-len(used_events),
                         candidate_edges_within_4h=len(pairs),
                         duplicate_edges_discarded=len(pairs)-len(used_labels))


def label_overlap(events_btc, first_ms, last_ms):
    path = Path("data/manual_btc_trades_2025_2026.csv")
    with path.open(newline="") as f:
        labels = []
        flags = Counter()
        for idx, row in enumerate(csv.DictReader(f), start=1):
            n = normalize(row)
            if n["issues"]:
                flags.update(n["issues"])
            if n["entry_ms"] is not None and first_ms <= n["entry_ms"] < last_ms and not n["issues"]:
                labels.append(dict(row_id="T%03d" % idx, entry_ms=n["entry_ms"], side=n["side"]))
    matched, summary = one_to_one_matches(events_btc, labels)
    summary["unreconciled_transcription_flags"] = dict(flags)
    summary["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary["notes"] = "One-to-one ±4h proximity of clean cached labels, NOT verified fill or discretionary rule."
    return matched, summary


def trade_summary(raw, subset, cost, start, end):
    terminal = raw[end-1][0]+H
    ts = [trade(raw, e, cost, 0., terminal=terminal) for e in subset]
    rs = [t["net_R"] for t in ts if t is not None]
    pos = sum(max(0, r) for r in rs)
    neg = -sum(min(0, r) for r in rs)
    return dict(n=len(rs), mean_R=round(statistics.mean(rs), 5) if rs else None,
                win_pct=round(100*sum(r>0 for r in rs)/len(rs), 2) if rs else None,
                pf_R=round(pos/neg, 4) if neg else None)


def block_ci(trades, seed=SEED, draws=1200):
    groups = defaultdict(list)
    for t in trades:
        block = t["entry_ms"] // (30*24*H)
        groups[block].append(t["net_R"])
    keys = sorted(groups)
    if len(keys) < 3:
        return dict(effective_30d_blocks=len(keys), ci95_mean_R=None)
    rng = random.Random(seed)
    means = []
    for _ in range(draws):
        sample = [r for __ in keys for r in groups[rng.choice(keys)]]
        means.append(statistics.mean(sample))
    means.sort()
    return dict(effective_30d_blocks=len(keys),
                ci95_mean_R=[round(means[int(.025*draws)], 5),
                             round(means[int(.975*draws)-1], 5)])


def full_metrics(run):
    m = metrics(run)
    v = [t["net_R"] for t in run["trades"]]
    wins = [r for r in v if r > 0]
    losses = [r for r in v if r < 0]
    m["avg_win_R"] = round(statistics.mean(wins), 5) if wins else None
    m["avg_loss_R"] = round(statistics.mean(losses), 5) if losses else None
    m["ci_30d"] = block_ci(run["trades"])
    return m


def run_asset(sym):
    raw, sha = load(sym)
    bars = aggregate_completed(raw, 4, asof_ms=raw[-1][0]+H)
    es, rejected = color_events(raw, bars)
    times = [r[0] for r in raw]
    if sym == "HYPEUSDT":
        cut = [0, len(raw)//2, 3*len(raw)//4, len(raw)]
        method = "HYPE-specific chronological 50/25/25; not common BTC/ETH/ICP UTC calendar"
    else:
        cut = [0] + [bisect.bisect_left(times, utc_ms(c)) for c in CUTOFFS] + [len(raw)]
        method = "BTC/ETH/ICP shared UTC train/validation/diagnostic cutoffs"
    if cut != sorted(cut) or any(cut[k] == cut[k+1] for k in range(3)):
        raise ValueError("Empty/invalid split: " + sym)
    threshold = train_thresholds([e for e in es if e["side"] == 1], times[cut[1]])
    label_map, label_stats = label_overlap(es, raw[0][0], raw[-1][0]+H) if sym == "BTCUSDT" else ({}, None)
    for e in es:
        e["matched_manual_row_id"] = label_map.get(e["event_id"], {}).get("label_id")
        e["matched_gap_hours"] = label_map.get(e["event_id"], {}).get("gap_hours")
        e["H1_eligible"] = admissible(e, "H1_LONG_expansion", threshold)
        e["H2_eligible"] = admissible(e, "H2_SHORT_upper_sweep", threshold)
    windows = {}
    for w, (a, b) in enumerate(zip(cut[:-1], cut[1:])):
        name = ("train", "validation", "inspected_diagnostic")[w]
        byside = {}
        for side, label, rule in ((1, "LONG", "H1_LONG_expansion"), (-1, "SHORT", "H2_SHORT_upper_sweep")):
            subset = [e for e in es if a <= e["entry_i"] < b and e["side"] == side]
            passed = [e for e in subset if admissible(e, rule, threshold)]
            rejected_events = [e for e in subset if not admissible(e, rule, threshold)]
            base_run = execute(raw, subset, FEE, 0., a, b)
            rule_run = execute(raw, passed, FEE, 0., a, b)
            byside[label] = dict(rule=rule, n_all_eligible_events=len(subset),
                n_admitted=len(passed), n_rejected=len(rejected_events),
                baseline=full_metrics(base_run), candidate=full_metrics(rule_run),
                matched_opportunities_pass=trade_summary(raw, passed, FEE, a, b),
                matched_opportunities_reject=trade_summary(raw, rejected_events, FEE, a, b),
                fee_sensitivity={
                    str(round(cost*10000))+"bp": dict(
                        baseline=full_metrics(execute(raw, subset, cost, 0., a, b)),
                        candidate=full_metrics(execute(raw, passed, cost, 0., a, b)))
                    for cost in COSTS},
                overlap_skipped_baseline=base_run["skips"],
                overlap_skipped_candidate=rule_run["skips"])
        # Frozen-turn is a distinct prior baseline; NOT the eligible color-transition universe.
        frozen_events, _ = events(raw)
        frozen = [e for e in frozen_events["frozen_turn"] if a <= e["entry_i"] < b]
        windows[name] = dict(start_utc=iso(raw[a][0]),
            end_exclusive_utc=iso(raw[b][0]) if b<len(raw) else iso(raw[-1][0]+H),
            sides=byside,
            frozen_turn_reference=full_metrics(execute(raw, frozen, FEE, 0., a, b)),
            cash_baseline_return_pct=0.0)
    # Event-level causal census, including rejected and unmatched signals; no raw label positions.
    catalog = [dict(event_id=sym+":"+e["event_id"], side="LONG" if e["side"]==1 else "SHORT",
        decision_utc=e["decision_utc"], entry_utc=e["entry_utc"],
        last_known_1h_close_utc=e["last_known_1h_close_utc"],
        feature_source_last_4h_close_utc=e["price"]["feature_source_last_4h_close_utc"],
        prior_color=e["prior_color"], new_color=e["new_color"],
        prior_delta=round(e["prior_delta"], 5), delta=round(e["delta"], 5),
        price=e["price"], H1_eligible=e["H1_eligible"], H2_eligible=e["H2_eligible"],
        matched_manual_row_id=e["matched_manual_row_id"],
        matched_gap_hours=e["matched_gap_hours"]) for e in es]
    return dict(source_sha256=sha, n_hours=len(raw), n_4h=len(bars),
        first_utc=iso(raw[0][0]), last_hour_open_utc=iso(raw[-1][0]),
        split_method=method, train_only_H1_thresholds=threshold,
        n_all_color_transitions=len(es), n_long=sum(e["side"]==1 for e in es),
        n_short=sum(e["side"]==-1 for e in es),
        rejected_before_catalog=rejected, manual_label_matching=label_stats,
        windows=windows, event_catalog=catalog)


def main():
    report = dict(title="Pre-registered TWO price-range × DeltaRSI closed-4H color-transition interactions",
        preregistration=PREREG, generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        producer_sha=os.environ.get("GITHUB_SHA", "local"),
        ci_run=os.environ.get("GITHUB_RUN_ID", "local"),
        fee_roundtrip_primary=FEE, fee_sensitivity=COSTS,
        funding="EXCLUDED by owner instruction; not zero realized exchange funding",
        fixed_stop_ATR=2.5, fixed_target_ATR=3.0, max_hold_hours=48,
        risk_fraction_per_trade=RISK, calendar_cutoffs_utc=CUTOFFS, bootstrap_seed=SEED,
        event_definition="Fully closed 4H same-sign color strong->medium/weak or medium->weak AND |delta| declines; no weak->weak repeat; next 1H open",
        hypotheses={
            "H1_LONG_expansion":"P=prior nonoverlapping 6x4H width/last P close, C=current 6x4H width/current close; P<=TRAIN LONG median P; C/P>=TRAIN LONG median C/P and C>P",
            "H2_SHORT_upper_sweep":"current completed 4H high>max high of six prior completed 4H bars and close<that high; no tuned threshold"},
        limitations=[
            "ALL historical train/validation/diagnostic periods were previously inspected; no untouched OOS or independent strategy validation.",
            "No rule selection on inspected diagnostic. Exactly two candidates preregistered; failure is an admissible result.",
            "15bp assumed roundtrip fees, 25/40bp stress, funding intentionally excluded. Unknown venue, mark prices and real spreads.",
            "Matched-opportunity trades overlap and are NOT executable portfolios; separately scheduled side-only trades are NOT a shared-capital multiasset portfolio.",
            "Per-symbol closed-trade DD can understate hourly mark-to-market portfolio DD; no simultaneous cross-asset risk budget in this study.",
            "HYPE uses its own calendar and is negative control, not pooled with BTC/ETH/ICP common calendar.",
            "BTC manual labels are complete self-reported trade history, not all market opportunities; proximity matching does not verify fills.",
            "No real or paper orders. No prospective receipts."] ,assets={})
    for sym in SYMS:
        report["assets"][sym] = run_asset(sym)
        print(sym, "color_events", report["assets"][sym]["n_all_color_transitions"],
              "validation", {s: (x["baseline"]["mean_R"], x["candidate"]["mean_R"],
                                x["candidate"]["n"]) for s,x in
                            report["assets"][sym]["windows"]["validation"]["sides"].items()}, flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print("WROTE", OUT)
    return report


if __name__ == "__main__":
    main()
