"""Exploratory audit of 42 user-annotated BTC trades (issue #17).

Annotations are NOT verified fills or independent outcomes. All market data is
committed 1H OHLC cache. No exchange API, funding, or orders.
Run: python -m unittest -v test_manual_trade_label_audit && python manual_trade_label_audit.py
"""
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from causal_4h_parity_audit import H, events, execute, metrics, iso, load

FEE = 0.0015  # 15bp total, half on entry and half on exit notional
RISK = 0.0025
MSK = dt.timezone(dt.timedelta(hours=3))
SOURCE = Path("data/manual_btc_trades_2025_2026.csv")
OUTPUT = Path("reports/manual_trade_label_audit.json")
CUTOFFS = ("2026-04-27T00:00:00+00:00",
           "2026-07-27T06:00:00+00:00")


def parse_msk(value):
    """Return UTC ms for an unambiguous Moscow clock time; date-only is UNKNOWN."""
    if not value or len(value.strip()) != 16:
        return None
    try:
        x = dt.datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return int(x.replace(tzinfo=MSK).timestamp() * 1000)


def asof_hour(times, decision_ms):
    """At decision/open time, only preceding CLOSED 1H candles may be observed."""
    return bisect.bisect_right(times, decision_ms - H) - 1


def in_cache(times, decision_ms):
    """Inclusive first/last cached 1H OPEN; timestamps are integer UTC ms."""
    return decision_ms is not None and bool(times) and times[0] <= decision_ms <= times[-1]


def within_hour(bar, price):
    return bar is not None and bar[3] - 1e-8 <= price <= bar[2] + 1e-8


def stop_touched_before_first(raw, entry_ms, exit_ms, side, stop):
    """Conservative static-SL falsification: omit ambiguous entry/exit hours."""
    if entry_ms is None or exit_ms is None:
        return False
    return any((b[3] <= stop if side == 1 else b[2] >= stop)
               for b in raw if entry_ms + H <= b[0] < exit_ms)


def normalize(row):
    """Preserve raw labels; never fix questionable dates or prices automatically."""
    entry = float(row["entry"])
    sl = float(row["sl"])
    if not (entry > 0 and sl > 0 and entry != sl):
        raise ValueError("invalid entry/stop")
    side = 1 if sl < entry else -1
    exit1 = float(row["exit1"])
    p1 = float(row["exit1_pct"]) / 100
    has_second = bool(row.get("exit2"))
    p2 = float(row["exit2_pct"]) / 100 if has_second else 0.
    if not (0 < p1 <= 1 and 0 <= p2 <= 1 and abs(p1+p2-1) < 1e-9):
        raise ValueError("exit weights must sum to one (50+50 already normalized)")
    x2 = float(row["exit2"]) if has_second else None
    if exit1 <= 0 or (has_second and x2 <= 0):
        raise ValueError("invalid exit price")
    weighted_exit = p1*exit1 + p2*(x2 or 0)
    fee = FEE * (entry + weighted_exit)/2
    net_pct = 100*(side*(weighted_exit-entry)-fee)/entry
    stop_pct = abs(entry-sl)/entry
    entry_ms = parse_msk(row["entry_msk"])
    x1_ms = parse_msk(row["exit1_msk"])
    x2_ms = parse_msk(row["exit2_msk"]) if has_second else None
    issues = []
    if row.get("quality", "ok") != "ok":
        issues.append(row["quality"])
    if entry_ms is None or x1_ms is None:
        issues.append("invalid_or_missing_primary_timestamp")
    if entry_ms is not None and x1_ms is not None and x1_ms < entry_ms:
        issues.append("exit_before_entry")
    if has_second and x2_ms is None:
        issues.append("missing_second_exit_time")
    if has_second and x2_ms is not None and x1_ms is not None and x2_ms < x1_ms:
        issues.append("second_exit_before_first")
    holding = None
    if entry_ms is not None and x1_ms is not None and (not has_second or x2_ms is not None):
        holding = (p1*(x1_ms-entry_ms) + (p2*(x2_ms-entry_ms) if has_second else 0))/H
    return dict(side=side, entry_ms=entry_ms, exit1_ms=x1_ms, exit2_ms=x2_ms,
                entry=entry, exit1=exit1, exit2=x2, sl=sl,
                net_pct=net_pct, net_R=net_pct/100/stop_pct,
                holding_hours=holding, issues=issues,
                entry_reason=row["entry_reason"], exit_reason=row["exit_reason"],
                stages=2 if has_second else 1)


def stats(rows):
    if not rows:
        return dict(n=0)
    v=[r["net_pct"] for r in rows]
    rs=[r["net_R"] for r in rows]
    gains=[x for x in v if x>0]
    losses=[x for x in v if x<=0]
    eq=peak=1.
    dd=0.
    streak=worst_streak=0
    for r in sorted(rows,key=lambda x:x["entry_ms"] or -1):
        eq*=max(1e-9,1+RISK*r["net_R"])
        peak=max(peak,eq)
        dd=max(dd,1-eq/peak)
        streak=streak+1 if r["net_pct"]<=0 else 0
        worst_streak=max(worst_streak,streak)
    holds=[r["holding_hours"] for r in rows if r["holding_hours"] is not None]
    return dict(n=len(rows),win_pct=round(100*len(gains)/len(rows),2),
                mean_net_pct=round(statistics.mean(v),5),
                median_net_pct=round(statistics.median(v),5),
                mean_net_R=round(statistics.mean(rs),5),
                profit_factor=round(sum(gains)/-sum(losses),4) if sum(losses)<0 else None,
                avg_win_pct=round(statistics.mean(gains),5) if gains else None,
                avg_loss_pct=round(statistics.mean(losses),5) if losses else None,
                median_holding_hours=round(statistics.median(holds),2) if holds else None,
                hypothetical_sequential_risk_sized_return_pct=round(100*(eq-1),4),
                hypothetical_closed_trade_dd_pct=round(100*dd,4),
                max_consecutive_losses=worst_streak)


def aggregate(rows, key):
    d=defaultdict(list)
    for r in rows:
        d[key(r)].append(r)
    return {k:stats(v) for k,v in sorted(d.items())}


def main():
    with SOURCE.open(newline="") as f:
        labels=[normalize(r) for r in csv.DictReader(f)]
    raw, source_sha=load("BTCUSDT")
    times=[r[0] for r in raw]
    bars_by_ms={r[0]:r for r in raw}
    event_sets, _=events(raw)
    by_mode={mode:sorted(e["entry_ms"] for e in es)
             for mode,es in event_sets.items()}
    event_keys={mode:{(e["entry_ms"],e["side"]) for e in es}
                for mode,es in event_sets.items()}
    funnel=Counter()
    matches={mode:Counter() for mode in event_sets}
    joined=[]
    for r in labels:
        ms=r["entry_ms"]
        if not in_cache(times, ms):
            funnel["outside_cache"]+=1
            continue
        funnel["inside_cache"]+=1
        i=asof_hour(times,ms)
        assert i<0 or times[i]+H<=ms, "future candle leaked into decision"
        bar=bars_by_ms.get(ms)
        previous=bars_by_ms.get(ms-H)
        p=r["entry"]
        in_current=within_hour(bar,p)
        in_previous=within_hour(previous,p)
        if in_current:funnel["entry_price_inside_marked_hour"]+=1
        if in_previous:funnel["entry_price_inside_prior_hour"]+=1
        if not in_current and not in_previous:
            funnel["entry_price_outside_both_hours"]+=1
        if not r["issues"]:
            if stop_touched_before_first(raw, ms, r["exit1_ms"], r["side"], r["sl"]):
                funnel["clean_static_stop_touched_before_first_exit"]+=1
            x1=bars_by_ms.get(r["exit1_ms"])
            x1prev=bars_by_ms.get(r["exit1_ms"]-H)
            if not within_hour(x1,r["exit1"]) and not within_hour(x1prev,r["exit1"]):
                funnel["clean_exit1_price_outside_marked_and_prior_hour"]+=1
        if not r["issues"]:funnel["clean_label_inside_cache"]+=1
        if r["issues"]:funnel["quality_flagged_inside_cache"]+=1
        for mode, keys in event_keys.items():
            if (ms,r["side"]) in keys:
                matches[mode]["exact_entry_time_and_side"]+=1
            es=event_sets[mode]
            if any(e["side"]==r["side"] and abs(e["entry_ms"]-ms)<=4*H for e in es):
                matches[mode]["within_4h_same_side"]+=1
        joined.append(dict(label=r, entry_in_marked_hour=in_current,
                           entry_in_prior_hour=in_previous,
                           last_closed_hour_utc=iso(times[i]) if i>=0 else None))
    clean=[r for r in labels if not r["issues"]]
    valid_cached=[j["label"] for j in joined if not j["label"]["issues"]]
    # Frozen existing baseline; no fitting to the 42 selected annotations.
    # Distinct signal families have different admissions; compare descriptively,
    # not as a matched-opportunity causal improvement.
    bounds=[0]
    for cutoff in CUTOFFS:
        bounds.append(bisect.bisect_left(times,int(dt.datetime.fromisoformat(cutoff).timestamp()*1000)))
    bounds.append(len(raw))
    backtest={}
    for mode,es in event_sets.items():
        backtest[mode]={}
        for name,start,end in zip(("earlier_inspected_train","earlier_inspected_validation",
                                   "earlier_inspected_diagnostic"),bounds[:-1],bounds[1:]):
            backtest[mode][name]=metrics(execute(raw,es,FEE,0.,start,end))
    flags=Counter(x for r in labels for x in r["issues"])
    windows=aggregate(valid_cached,lambda r:
       "earlier_inspected_train" if iso(r["entry_ms"])<CUTOFFS[0] else
       ("earlier_inspected_validation" if iso(r["entry_ms"])<CUTOFFS[1]
        else "earlier_inspected_diagnostic"))
    report=dict(title="42 manually annotated BTC trades: descriptive label and as-of 1H audit",
      generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
      source_files={"manual_labels":str(SOURCE),"cached_btc_1h":"data/BTCUSDT_1h.csv"},
      source_sha256={"manual_labels":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                     "cached_btc_1h":source_sha},
      fee_roundtrip=FEE,funding="excluded per owner instruction",
      cache_utc={"first":iso(times[0]),"last_hour_open":iso(times[-1]),
                 "n_hours":len(raw)},
      n_labels=len(labels),quality_flags=dict(flags),
      n_clean_labels=len(clean),
      annotated_all_including_suspect=stats(labels),
      annotated_clean_only=stats(clean),
      annotated_clean_in_cached_period=stats(valid_cached),
      clean_by_side=aggregate(clean,lambda r:"LONG" if r["side"]==1 else "SHORT"),
      clean_by_entry_reason=aggregate(clean,lambda r:r["entry_reason"]),
      clean_by_exit_reason=aggregate(clean,lambda r:r["exit_reason"]),
      clean_by_month=aggregate(clean,lambda r:iso(r["entry_ms"])[:7]),
      clean_by_stages=aggregate(clean,lambda r:str(r["stages"])),
      cached_clean_by_previously_inspected_calendar=windows,
      asof_join_funnel=dict(funnel),
      candidate_signal_counts={k:len(v) for k,v in event_sets.items()},
      same_side_signal_matches={k:dict(v) for k,v in matches.items()},
      frozen_2p5ATR_3ATR_48h_btc_backtest_by_mode_and_calendar=backtest,
      notes=[
       "User annotations are selected winners/losers, not independently observed executable fills; statistics are descriptive only.",
       "All four non-ok quality labels are excluded from clean results without silently repairing price/date/time.",
       "The 15bp fee is a fixed assumed round-trip cost charged half on entry notional and half on weighted exit notional.",
       "The 50+50 two-stage exits are already normalized shares of original notional, NOT 50+100.",
       "No funding by owner instruction; no real orders, exchange access, or new candle downloads.",
       "OHLC containment in the marked/prior hour is only a plausibility check; not proof of actual fill or execution.",
       "Hourly OHLC cannot establish intrabar chronology or stop hit before annotated exits; no executable trade-PnL claim.",
       "Static-stop breach test ignores entry and first-exit hours; a breach is a conflict only if the annotated initial SL remained active.",
       "Hypothetical sequential risk-sized DD/return assume no overlapping trades, perfect annotated fills and fixed 0.25% initial stop risk; NOT executable portfolio DD.",
       "All historical train/validation/diagnostic windows have been previously inspected and cannot support independent OOS claims.",
       "Exact candidate matches are an overlap census, NOT proof that the annotated discretionary rule is the automated DeltaRSI rule.",
       "Full negative/control candidate event streams are from existing causal_4h_parity_audit.events; no filter fitted to 42 labels.",
       "BTC frozen baseline and forming/closed signal families are independently scheduled, not paired and not comparable to selected manual annotation fills.",
       "Backtests use next-hour-open entries, 2.5 ATR stop, 3 ATR target, 48h timeout, fixed 15bp fee, zero funding, and sequential per-symbol risk sizing; closed-trade DD is not hourly MTM DD."
      ])
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:report[k] for k in ("n_labels","n_clean_labels","quality_flags",
          "annotated_clean_only","asof_join_funnel","same_side_signal_matches")},indent=2))
    return report


if __name__=="__main__":
    main()
