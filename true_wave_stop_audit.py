"""Issue #16: causal true DeltaRSI wave/peak stop comparison on frozen entry IDs.

Exploratory historical cohort, not independent OOS or executable shared-capital
portfolio. Run: python -m unittest -v test_true_wave_stop_audit &&
python true_wave_stop_audit.py. No network or orders.
"""
import bisect
import datetime as dt
import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from analyze_mtf_5y import indicator
from causal_4h_parity_audit import H, events, iso, load
from execution_core import resolve_bar

FEE = 0.0015  # fixed round-trip, split between entry/exit notionals
RISK = 0.0025
TP_R = 1.2
HOLD_H = 48
BUFFER_ATR = 0.05
SYMS = ("BTCUSDT", "ETHUSDT", "ICPUSDT", "HYPEUSDT")
CORE = SYMS[:3]
MODES = ("frozen_turn", "forming", "closed")
STOPS = ("atr2.5", "true_peak_bar", "true_whole_wave")
WINDOWS = ("train", "validation", "inspected_diagnostic")


def wave_snapshot(bars, deltas, bucket_index, side, partial_hours):
    """Wave strictly opposite the proposed trade, using only completed 4H bars.

    At a 4H close the current bucket is known; on an incomplete 4H bucket it
    is NOT known. A completed same-side sign flip excludes that bar, leaving
    the preceding opposite-sign wave. A sign-zero/NaN wave is rejected.
    """
    if side not in (-1, 1) or partial_hours not in (1, 2, 3, 4):
        raise ValueError("invalid side/partial hours")
    if not (0 <= bucket_index < len(bars)) or len(deltas) != len(bars):
        raise ValueError("invalid bucket/delta history")
    last_known = bucket_index if partial_hours == 4 else bucket_index - 1
    end = last_known
    if end >= 0 and math.isfinite(deltas[end]) and deltas[end] * side >= 0:
        end -= 1  # just-closed sign flip; previous opposite wave is eligible
    if end < 0 or not math.isfinite(deltas[end]) or deltas[end] * side >= 0:
        return None
    start = end
    while start > 0 and math.isfinite(deltas[start - 1]) and deltas[start - 1] * side < 0:
        start -= 1
    peak = max(range(start, end + 1), key=lambda k: abs(deltas[k]))
    segment = bars[start:end + 1]
    return dict(start_i=start, end_i=end, peak_i=peak,
                start_utc=iso(bars[start][0]), end_utc=iso(bars[end][0]),
                peak_utc=iso(bars[peak][0]), wave_length=end - start + 1,
                peak_delta=deltas[peak], peak_low=bars[peak][3],
                peak_high=bars[peak][2],
                wave_low=min(b[3] for b in segment),
                wave_high=max(b[2] for b in segment),
                last_known_4h_utc=iso(bars[last_known][0]))


def stop_price(entry, side, atr, stop_kind, wave):
    if not math.isfinite(atr) or atr <= 0:
        return None
    if stop_kind == "atr2.5":
        return entry - side * 2.5 * atr
    if wave is None:
        return None
    if stop_kind == "true_peak_bar":
        return (wave["peak_low"] - BUFFER_ATR * atr if side == 1
                else wave["peak_high"] + BUFFER_ATR * atr)
    if stop_kind == "true_whole_wave":
        return (wave["wave_low"] - BUFFER_ATR * atr if side == 1
                else wave["wave_high"] + BUFFER_ATR * atr)
    raise ValueError(stop_kind)


def trade_one(raw, entry_i, side, stop, end_i, tp_r=TP_R):
    """Matched next-hour-open fill, stop-first OHLC, adverse open gaps."""
    if not (0 <= entry_i <= end_i < len(raw)):
        return None, "terminal"
    entry = raw[entry_i][1]
    if stop is None or entry <= 0:
        return None, "missing_stop"
    distance = side * (entry - stop)
    if not (0.001 <= distance / entry <= 0.12):
        return None, "invalid_stop_geometry"
    target = entry + side * tp_r * distance
    terminal = min(end_i, entry_i + HOLD_H - 1)
    exit_i = terminal
    out = raw[terminal][4]
    reason = "time"
    for k in range(entry_i, terminal + 1):
        fill, why = resolve_bar(raw[k], side, stop, target)
        if why:
            out, exit_i, reason = fill, k, why
            break
    gross = side * (out - entry)
    fees = (entry + out) * FEE / 2
    return dict(entry_i=entry_i, exit_i=exit_i,
                exit_utc=iso(raw[exit_i][0] + H), exit_reason=reason,
                entry=entry, exit=out, stop=stop, target=target,
                stop_distance_pct=100 * distance / entry,
                gross_R=gross / distance, fee_R=fees / distance,
                net_R=(gross - fees) / distance,
                net_pct=100 * (gross - fees) / entry), None


def stats(trades):
    v = [t["net_R"] for t in trades]
    if not v:
        return dict(n=0, win_pct=None, mean_R=None, pf=None, avg_win_R=None,
                    avg_loss_R=None, pseudo_dd_pct=None)
    wins = [x for x in v if x > 0]
    losses = [x for x in v if x <= 0]
    eq = peak = 1.0
    dd = 0.0
    for r in v:
        eq *= max(1e-8, 1 + RISK * r)
        peak = max(peak, eq)
        dd = max(dd, 1 - eq / peak)
    return dict(n=len(v), win_pct=round(100 * len(wins) / len(v), 2),
                mean_R=round(statistics.mean(v), 5),
                pf=round(sum(wins) / -sum(losses), 4) if losses and sum(losses) < 0 else None,
                avg_win_R=round(statistics.mean(wins), 5) if wins else None,
                avg_loss_R=round(statistics.mean(losses), 5) if losses else None,
                median_stop_pct=round(statistics.median(t["stop_distance_pct"] for t in trades), 4),
                median_fee_R=round(statistics.median(t["fee_R"] for t in trades), 4),
                pseudo_dd_pct=round(100 * dd, 4))


def build():
    cache = {}
    for sym in SYMS:
        raw, sha = load(sym)
        ev, bars = events(raw)
        delta = indicator(bars)["delta"]
        lookup = {b[0]: j for j, b in enumerate(bars)}
        cache[sym] = dict(raw=raw, sha=sha, ev=ev, bars=bars,
                          delta=delta, lookup=lookup,
                          first=raw[0][0], last=raw[-1][0] + H)
    start = max(cache[s]["first"] for s in CORE)
    end = min(cache[s]["last"] for s in CORE)
    hours = (end - start) // H
    if hours < 1000:
        raise ValueError("Insufficient aligned BTC/ETH/ICP calendar")
    cuts = (start, start + hours // 2 * H, start + (3 * hours // 4) * H, end)
    return cache, cuts


def research():
    cache, cuts = build()
    buckets = {w: defaultdict(lambda: defaultdict(list)) for w in WINDOWS}
    rejected = Counter()
    catalog = []
    pairs = {w: defaultdict(lambda: defaultdict(list)) for w in WINDOWS}
    for sym, c in cache.items():
        raw, bars, delta = c["raw"], c["bars"], c["delta"]
        timestamps = [r[0] for r in raw]
        for mode in MODES:
            for e in c["ev"][mode]:
                i = e["entry_i"]
                if i >= len(raw):
                    continue
                when = raw[i][0]
                if not (cuts[0] <= when < cuts[-1]):
                    continue  # common UTC calendar; HYPE is a shorter-history control
                w_index = bisect.bisect_right(cuts, when) - 1
                if w_index not in (0, 1, 2):
                    continue
                window = WINDOWS[w_index]
                end_i = bisect.bisect_left(timestamps, cuts[w_index + 1]) - 1
                j = c["lookup"].get(e["bucket_ms"])
                if j is None:
                    raise AssertionError("Event missing 4H bucket")
                wave = wave_snapshot(bars, delta, j, e["side"], e["partial_hours"])
                entry = raw[i][1]
                identity = f"{sym}:{mode}:{when}:{e['side']}"
                row = dict(id=identity, symbol=sym, mode=mode, side=e["side"],
                           window=window, decision_utc=e["decision_utc"],
                           entry_utc=iso(when), entry_price=entry,
                           atr_4h=e["atr_4h"], wave=wave, outcomes={})
                all_valid = {}
                for kind in STOPS:
                    stop = stop_price(entry, e["side"], e["atr_4h"], kind, wave)
                    t, why = trade_one(raw, i, e["side"], stop, end_i)
                    if why:
                        rejected[(window, sym, mode, kind, why)] += 1
                        row["outcomes"][kind] = dict(rejected=why)
                    else:
                        t.update(id=identity, symbol=sym, mode=mode, side=e["side"],
                                 entry_utc=iso(when), window=window)
                        buckets[window][mode][kind].append(t)
                        row["outcomes"][kind] = dict(net_R=round(t["net_R"], 6),
                             stop=t["stop"], exit=t["exit"], exit_utc=t["exit_utc"],
                             exit_reason=t["exit_reason"])
                        all_valid[kind] = t
                # Pairwise cohorts: a valid whole-wave stop must not be dropped
                # merely because the peak-bar stop was geometrically invalid.
                for challenger in STOPS[1:]:
                    if "atr2.5" in all_valid and challenger in all_valid:
                        pairs[window][mode][challenger].append(dict(
                            id=identity, symbol=sym, side=e["side"],
                            entry_utc=iso(when),
                            baseline=all_valid["atr2.5"],
                            challenger=all_valid[challenger]))
                catalog.append(row)
    summary = {}
    for w in WINDOWS:
        summary[w] = {}
        for mode in MODES:
            per = {}
            for kind in STOPS:
                trades = sorted(buckets[w][mode][kind], key=lambda x:(x["entry_utc"], x["symbol"]))
                per[kind] = dict(all=stats(trades),
                    core=stats([t for t in trades if t["symbol"] in CORE]),
                    by_asset={s:stats([t for t in trades if t["symbol"] == s]) for s in SYMS},
                    by_side={label:stats([t for t in trades if t["side"] == side])
                             for label, side in (("LONG",1),("SHORT",-1))})
            diffs = {}
            for challenger in STOPS[1:]:
                cohort = [x for x in pairs[w][mode][challenger] if x["symbol"] in CORE]
                values = [x["challenger"]["net_R"] - x["baseline"]["net_R"] for x in cohort]
                diffs[challenger] = dict(matched_core_n=len(values),
                    mean_delta_R=round(statistics.mean(values), 6) if values else None,
                    win_fraction=round(sum(v > 0 for v in values) / len(values), 4) if values else None,
                    matched_baseline=stats([x["baseline"] for x in cohort]),
                    matched_challenger=stats([x["challenger"] for x in cohort]),
                    by_asset={sym:dict(n=sum(x["symbol"] == sym for x in cohort),
                        mean_delta_R=round(statistics.mean(
                            x["challenger"]["net_R"] - x["baseline"]["net_R"]
                            for x in cohort if x["symbol"] == sym), 6)
                        if any(x["symbol"] == sym for x in cohort) else None)
                        for sym in CORE},
                    by_side={label:dict(n=sum(x["side"] == side for x in cohort),
                        mean_delta_R=round(statistics.mean(
                            x["challenger"]["net_R"] - x["baseline"]["net_R"]
                            for x in cohort if x["side"] == side), 6)
                        if any(x["side"] == side for x in cohort) else None)
                        for label, side in (("LONG", 1), ("SHORT", -1))})
            summary[w][mode] = dict(stops=per, paired_vs_atr=diffs)
    return dict(title="Causal true-wave vs peak-bar vs ATR stop: matched-entry exploratory audit",
       generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
       producer_sha=os.environ.get("GITHUB_SHA", "local"),
       ci_run=os.environ.get("GITHUB_RUN_ID", "local"),
       source_sha256={s:c["sha"] for s,c in cache.items()},
       fixed_fee_roundtrip=FEE, risk_fraction_for_pseudo_dd=RISK,
       tp_r=TP_R, timeout_h=HOLD_H, buffer_atr=BUFFER_ATR,
       aligned_core_calendar_utc={w:dict(start=iso(cuts[i]),end_exclusive=iso(cuts[i+1]))
                                  for i,w in enumerate(WINDOWS)},
       raw_source_calendar_utc={s:dict(start=iso(c["first"]),end_exclusive=iso(c["last"]))
                                for s,c in cache.items()},
       notes=["Only cached 1H candles; no exchange requests or real orders.",
          "Historical windows all previously inspected; last window is diagnostic, NOT independent OOS.",
          "Exactly 3 preregistered stop definitions, fixed 1.2R TP/48h timeout; no stop/exit tuning.",
          "Current completed 4H bucket is available at its close; incomplete 4H bucket is never used.",
          "The stop wave is the last contiguous opposite-sign fully completed 4H DeltaRSI wave.",
          "Matched entries compare stop geometry but may overlap; NOT an executable shared-capital portfolio.",
          "0.25%-risk pseudo DD is NOT hourly MTM portfolio drawdown; no admission competition.",
          "Stop/TP ambiguous within 1H uses stop-first; adverse gaps fill at worse open.",
          "15bp fixed round-trip trading friction; funding excluded from this pattern experiment.",
          "No selection or promotion using inspected diagnostic results."],
       summary=summary,
       rejection_counts=[dict(window=w,symbol=s,mode=m,stop=k,reason=r,count=n)
                         for (w,s,m,k,r),n in sorted(rejected.items())],
       catalog=catalog)


def main():
    report = research()
    path = Path("reports/true_wave_stop_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print("WROTE", path, "catalog", len(report["catalog"]))
    for w in WINDOWS:
        print(w, "turn-core",
              {k:report["summary"][w]["frozen_turn"]["stops"][k]["core"]
               for k in STOPS}, flush=True)


if __name__ == "__main__":
    main()
