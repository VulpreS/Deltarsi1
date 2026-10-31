"""Independent DeltaRSI ML entry/exit policy research (closed 4h, next-open fills).

Two independently trained models: entry (FLAT/LONG/SHORT) and exit (HOLD/EXIT).
Historical DP oracle supplies FUTURE-BASED TRAINING LABELS ONLY; observations are
strictly past/closed-bar features. Neither model receives its oracle at inference.
No 48h cap, no manual-trade supervision, no preprogrammed opposite-signal exit.
The final Aug-Oct 2026 period is used only once for walk-forward evaluation.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

ROOT = Path("experiments/delta_ml_3y")
START = int(dt.datetime(2023, 11, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
VALID_START = int(dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
CUT = int(dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
FEE_SIDE = 0.0009  # 0.08% per side plus half of 0.02% round-trip spread
ORACLE_EXTRA_TURN_COST = 0.002  # in-sample regularization, NOT an execution fee
WARMUP = 220
ASSETS = ("BTCUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT")
COLORS = {0: "none", 1: "bright_blue", 2: "medium_blue", 3: "midweak_blue",
          4: "weak_blue", 5: "bright_red", 6: "medium_red",
          7: "midweak_red", 8: "weak_red"}

def iso(t):
    return dt.datetime.fromtimestamp(int(t) / 1000, dt.timezone.utc).isoformat()

def pine_indicator(close):
    """Literal numeric core of repository's root 'Delta' Pine file.
    Note: misleading Pine comment says RSI27; executable code is SMA21 -> RSI12
    -> EMA7 -> signed symmetric log delta. Colors use threshold 60.
    """
    src = pd.Series(close).rolling(21).mean().to_numpy()
    n = len(close)
    rsi = np.full(n, np.nan)
    delta = np.full(n, np.nan)
    shades = np.zeros(n, dtype=np.int8)
    avg_gain = avg_loss = 0.
    ema = np.nan
    for i in range(32, n):
        change = src[i] - src[i - 1]
        if i == 32:
            past = np.diff(src[20:33])
            avg_gain = float(np.maximum(past, 0).mean())
            avg_loss = float(np.maximum(-past, 0).mean())
        else:
            avg_gain = (avg_gain * 11 + max(change, 0)) / 12
            avg_loss = (avg_loss * 11 + max(-change, 0)) / 12
        r = (100. if avg_loss == 0 else
             (0. if avg_gain == 0 else 100 - 100 / (1 + avg_gain / avg_loss)))
        ema = r if not np.isfinite(ema) else ema * .75 + r * .25
        a, b = (100 - r if r > 50 else r), (100 - ema if ema > 50 else ema)
        if a <= 0 or b <= 0:
            rsi[i] = r
            continue
        raw = math.log(a / b) * 100
        d = (1 if r > ema else -1) * abs(raw)
        previous = delta[i - 1]
        if np.isfinite(previous) and d > 0:
            shades[i] = (1 if abs(d) > 60 and d > previous else
                         2 if abs(d) > 60 and d < previous else
                         3 if abs(d) <= 60 and abs(d) > abs(previous) else
                         4 if abs(d) <= 60 and abs(d) < abs(previous) else 0)
        elif np.isfinite(previous) and d < 0:
            shades[i] = (5 if abs(d) > 60 and d < previous else
                         6 if abs(d) > 60 and d > previous else
                         7 if abs(d) <= 60 and abs(d) > abs(previous) else
                         8 if abs(d) <= 60 and abs(d) < abs(previous) else 0)
        rsi[i], delta[i] = r, d
    return rsi, delta, shades

def features(rows, sym):
    d = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"])
    c = d.close
    rsi, dr, shade = pine_indicator(c.to_numpy())
    d["rsi"], d["dr"], d["shade"] = rsi, dr, shade
    s = pd.Series(dr)
    a = s.abs()
    d["dr_abs"] = a
    d["dr_change"] = s.diff()
    d["dr_accel"] = s.diff().diff()
    d["fade_ratio"] = a / a.shift(1).replace(0, np.nan)
    d["dr_relative_peak"] = a / a.rolling(24).max().replace(0, np.nan)
    d["dr_rising"] = (a > a.shift(1)).astype(int)
    d["weak_red_transition"] = ((pd.Series(shade).shift(1) == 6) & (shade == 8)).astype(int)
    d["weak_blue_transition"] = ((pd.Series(shade).shift(1) == 2) & (shade == 4)).astype(int)
    d["bright_red"] = (shade == 5).astype(int)
    d["bright_blue"] = (shade == 1).astype(int)
    wave = np.zeros(len(d))
    for i in range(1, len(d)):
        wave[i] = wave[i - 1] + 1 if np.isfinite(dr[i]) and np.isfinite(dr[i - 1]) and dr[i] * dr[i - 1] > 0 else 0
    d["wave_age"] = np.minimum(wave, 100)
    for k in (1, 2, 3, 4, 6, 12, 24):
        d[f"dr_lag{k}"] = s.shift(k)
        d[f"dr_velocity{k}"] = s - s.shift(k)
        d[f"return{k}"] = c.pct_change(k)
    tr = pd.concat((d.high - d.low, (d.high - c.shift()).abs(),
                    (d.low - c.shift()).abs()), axis=1).max(axis=1)
    d["atr_pct"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / c
    d["range_pct"] = (d.high - d.low) / c
    d["upper_wick"] = (d.high - d[["open", "close"]].max(axis=1)) / c
    d["lower_wick"] = (d[["open", "close"]].min(axis=1) - d.low) / c
    d["body_pct"] = (d.close - d.open) / c
    d["vol_ratio"] = d.volume / d.volume.rolling(30).mean()
    d["ema50_dist"] = c / c.ewm(span=50, adjust=False).mean() - 1
    d["ema200_dist"] = c / c.ewm(span=200, adjust=False).mean() - 1
    d["high_break20"] = (d.high > d.high.shift(1).rolling(20).max()).astype(int)
    d["low_break20"] = (d.low < d.low.shift(1).rolling(20).min()).astype(int)
    d["dr_high_break20"] = (s > s.shift(1).rolling(20).max()).astype(int)
    d["dr_low_break20"] = (s < s.shift(1).rolling(20).min()).astype(int)
    d["bear_div_proxy"] = d.high_break20 * (1 - d.dr_high_break20)
    d["bull_div_proxy"] = d.low_break20 * (1 - d.dr_low_break20)
    for asset in ASSETS:
        d["asset_" + asset] = int(sym == asset)
    d["symbol"] = sym
    return d

def oracle_positions(d, start, stop):
    """Offline hindsight oracle for training labels only; no hold-time ceiling.
    It chooses when to be flat, long or short over the given segment,
    with explicit trading costs and a churn penalty. Never used on OOS bars.
    """
    states = (-1, 0, 1)
    dp = np.array([-1e30, 0., -1e30])
    parents = []
    opens = d.open.to_numpy()
    for t in range(start, stop - 1):
        nxt = np.full(3, -1e30)
        parent = np.zeros(3, dtype=int)
        terminal = t == stop - 2
        ret = 0. if terminal else math.log(opens[t + 2] / opens[t + 1])
        for j, position in enumerate(states):
            if terminal and position:
                continue
            for k, old in enumerate(states):
                cost = (FEE_SIDE + ORACLE_EXTRA_TURN_COST) * abs(position - old)
                reward = position * ret - (0.05 * abs(ret) if position else 0) - cost
                val = dp[k] + reward
                if val > nxt[j]:
                    nxt[j], parent[j] = val, k
        dp = nxt
        parents.append(parent)
    path = {}
    index = 1  # forced flat at the final decision candle
    for t in range(stop - 2, start - 1, -1):
        path[t] = states[index]
        index = int(parents[t - start][index])
    return path

def context(d, t, side, entry_i, entry_price):
    if entry_i < 0:
        return [0.] * 8
    current = float(d.close.iloc[t])
    if t >= entry_i + 1:
        part = d.iloc[entry_i + 1:t + 1]
        hi = float(part.high.max())
        lo = float(part.low.min())
    else:
        hi = lo = entry_price
    best = hi / entry_price - 1 if side > 0 else 1 - lo / entry_price
    worst = lo / entry_price - 1 if side > 0 else 1 - hi / entry_price
    pnl = side * (current / entry_price - 1)
    dr_entry = float(d.dr.iloc[entry_i])
    dr_now = float(d.dr.iloc[t])
    return [float(side), min(t - entry_i, 1000), pnl, best, worst,
            dr_entry, dr_now - dr_entry, float(abs(dr_now) / max(abs(dr_entry), 1e-9))]

CONTEXT_COLS = ["position_side", "holding_bars", "unrealized_pct", "mfe_pct",
                "mae_pct", "entry_delta", "delta_since_entry", "delta_vs_entry"]

def matrix(d, cols, t):
    x = d.iloc[t][cols].to_numpy(dtype=float)
    return np.nan_to_num(x, nan=0., posinf=0., neginf=0.)

def training_samples(all_data, cols, first, last):
    entries_x, entries_y, exits_x, exits_y = [], [], [], []
    counts = {}
    for sym, d in all_data.items():
        begin = max(WARMUP, int(np.searchsorted(d.t.to_numpy(), first)))
        end = int(np.searchsorted(d.t.to_numpy(), last))
        if end - begin < 100:
            continue
        oracle = oracle_positions(d, begin, end)
        previous, entry_idx, entry_price = 0, -1, 0.
        for t in range(begin, end - 1):
            new = oracle[t]
            row = matrix(d, cols, t)
            if previous == 0:
                entries_x.append(row)
                entries_y.append(1 if new == 1 else 2 if new == -1 else 0)
            else:
                exits_x.append(np.r_[row, context(d, t, previous, entry_idx, entry_price)])
                exits_y.append(int(new != previous))
            if new != previous:
                entry_idx = t if new else -1
                entry_price = float(d.open.iloc[t + 1]) if new else 0.
            previous = new
        counts[sym] = dict(entry_samples=sum(1 for _ in oracle), first=iso(d.t.iloc[begin]),
                           last=iso(d.t.iloc[end - 1]))
    return (np.asarray(entries_x, dtype=float), np.asarray(entries_y, dtype=int),
            np.asarray(exits_x, dtype=float), np.asarray(exits_y, dtype=int), counts)

def fit_models(all_data, cols, first, last):
    ex, ey, xx, xy, counts = training_samples(all_data, cols, first, last)
    if min(len(ex), len(xx)) < 100 or len(set(ey)) != 3 or len(set(xy)) != 2:
        raise RuntimeError(f"Insufficient oracle labels: entry={np.unique(ey, return_counts=True)}, exit={np.unique(xy, return_counts=True)}")
    base = dict(n_estimators=180, max_depth=3, learning_rate=.045,
                subsample=.85, colsample_bytree=.85, tree_method="hist",
                random_state=42, n_jobs=2)
    entry = XGBClassifier(objective="multi:softprob", num_class=3, eval_metric="mlogloss", **base)
    exit_model = XGBClassifier(objective="binary:logistic", eval_metric="logloss", **base)
    entry.fit(ex, ey, sample_weight=np.where(ey == 0, 1., 2.5))
    exit_model.fit(xx, xy, sample_weight=np.where(xy == 0, 1., 3.))
    stats = dict(entries=dict(samples=len(ey), flat=int((ey == 0).sum()),
                              long=int((ey == 1).sum()), short=int((ey == 2).sum())),
                 exits=dict(samples=len(xy), hold=int((xy == 0).sum()),
                            close=int((xy == 1).sum())))
    return entry, exit_model, stats

def simulate(d, cols, entry_model, exit_model, start, end, entry_threshold, exit_threshold):
    begin = max(WARMUP, int(np.searchsorted(d.t.to_numpy(), start)))
    stop = int(np.searchsorted(d.t.to_numpy(), end))
    if stop - begin < 10:
        return None
    p, entry_idx, entry_px = 0, -1, 0.
    eq = 1.
    trade_eq = 1.
    trades = []
    peak = 1.
    drawdown = 0.
    curve = []
    opens = d.open.to_numpy()
    for t in range(begin, stop - 1):
        old = p
        if t == stop - 2:
            p = 0
        elif p == 0:
            prob = entry_model.predict_proba(matrix(d, cols, t).reshape(1, -1))[0]
            candidate = 1 if prob[1] >= prob[2] else -1
            conf = max(float(prob[1]), float(prob[2]))
            p = candidate if conf >= entry_threshold else 0
        else:
            values = np.r_[matrix(d, cols, t), context(d, t, p, entry_idx, entry_px)]
            conf = float(exit_model.predict_proba(values.reshape(1, -1))[0, 1])
            if conf >= exit_threshold:
                p = 0
        if p != old:
            before_cost = eq
            eq *= math.exp(-FEE_SIDE * abs(p - old))
            if old != 0:
                trades.append(dict(symbol=d.symbol.iloc[0], direction="LONG" if old == 1 else "SHORT",
                    entry_utc=iso(d.t.iloc[entry_idx + 1]),
                    exit_utc=iso(d.t.iloc[t + 1]),
                    entry_price=entry_px, exit_price=float(opens[t + 1]),
                    hold_hours=4 * (t - entry_idx), net_return_pct=100 * (eq / trade_eq - 1)))
            if p != 0:
                entry_idx, entry_px, trade_eq = t, float(opens[t + 1]), before_cost
            else:
                entry_idx, entry_px = -1, 0.
        if t + 2 < stop:
            eq *= math.exp(p * math.log(float(opens[t + 2]) / float(opens[t + 1])))
        peak = max(peak, eq)
        drawdown = max(drawdown, 1 - eq / peak)
        curve.append([int(d.t.iloc[t + 1]), round(eq, 8)])
    profits = [z["net_return_pct"] for z in trades]
    gross_profit = sum(max(v, 0) for v in profits)
    gross_loss = -sum(min(v, 0) for v in profits)
    metrics = dict(symbol=d.symbol.iloc[0], first=iso(d.t.iloc[begin]),
        last=iso(d.t.iloc[stop - 1]), bars=stop - begin, trades=len(trades),
        return_pct=100 * (eq - 1), max_drawdown_pct=100 * drawdown,
        win_rate_pct=100 * sum(v > 0 for v in profits) / len(profits) if profits else None,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else None,
        avg_trade_pct=float(np.mean(profits)) if profits else None,
        median_hold_hours=float(np.median([z["hold_hours"] for z in trades])) if trades else None,
        exact_pine_fade_long=int(d.weak_red_transition.iloc[begin:stop].sum()),
        exact_pine_fade_short=int(d.weak_blue_transition.iloc[begin:stop].sum()))
    return metrics, trades, curve

def assess(all_data, cols, entry, exits, start, end, th_entry, th_exit):
    result, ledger, curves = {}, [], {}
    for sym, d in all_data.items():
        out = simulate(d, cols, entry, exits, start, end, th_entry, th_exit)
        if out:
            m, trades, curve = out
            result[sym], curves[sym] = m, curve
            ledger.extend(trades)
    summary = dict(assets=len(result), trades=sum(x["trades"] for x in result.values()),
        mean_asset_return_pct=float(np.mean([x["return_pct"] for x in result.values()])),
        mean_asset_max_drawdown_pct=float(np.mean([x["max_drawdown_pct"] for x in result.values()])),
        assets_profitable=sum(x["return_pct"] > 0 for x in result.values()))
    return dict(summary=summary, by_symbol=result), ledger, curves

def feature_importance(model, names):
    return sorted(([name, float(value)] for name, value in zip(names, model.feature_importances_)),
                  key=lambda x: x[1], reverse=True)[:20]

def main():
    all_data = {}
    for sym in ASSETS:
        file = ROOT / "data" / (sym + ".json")
        if not file.exists():
            raise FileNotFoundError("Missing downloaded Binance archive: " + str(file))
        all_data[sym] = features(json.loads(file.read_text()), sym)
    exclude = {"t", "open", "high", "low", "close", "volume", "symbol"}
    cols = [c for c in all_data[ASSETS[0]] if c not in exclude]
    # Search entry and exit confidence thresholds using validation ONLY.
    entry_v, exit_v, fit_counts = fit_models(all_data, cols, START, VALID_START)
    trials = []
    for a in (.45, .55, .65):
        for b in (.45, .55, .65):
            val, _, _ = assess(all_data, cols, entry_v, exit_v, VALID_START, CUT, a, b)
            score = val["summary"]["mean_asset_return_pct"] - .35 * val["summary"]["mean_asset_max_drawdown_pct"]
            if val["summary"]["trades"] < 6:
                score -= 50
            trials.append((score, a, b, val))
    best = max(trials, key=lambda z: z[0])
    _, a, b, validation = best
    print("ML_VALIDATION", json.dumps(dict(entry_threshold=a, exit_threshold=b, evaluation=validation["summary"])), flush=True)
    # Refit on ALL 33 pre-test months, with no held-out future labels.
    entry_f, exit_f, final_counts = fit_models(all_data, cols, START, CUT)
    test, ledger, curve = assess(all_data, cols, entry_f, exit_f, CUT, 4102444800000, a, b)
    # END above is a distant upper bound; each asset's available dataset ends Oct 27.
    entry_f.save_model(str(ROOT / "entry_model.json"))
    exit_f.save_model(str(ROOT / "exit_model.json"))
    (ROOT / "test_trades.json").write_text(json.dumps(ledger, indent=2))
    (ROOT / "test_equity.json").write_text(json.dumps(curve, separators=(",", ":")))
    report = dict(title="DeltaRSI causal ML independent entry and exit; no 48h hold limit",
        experiment="train33m-val6m-final_holdout_Aug_Oct2026",
        code_sha=os.environ.get("GITHUB_SHA", "local"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        train_dates=dict(start=iso(START), internal_validation_start=iso(VALID_START),
                         independent_test_start=iso(CUT)),
        actual_test_end={k: v["last"] for k, v in test["by_symbol"].items()},
        indicator="Pine root Delta executable SMA21 -> RSI12/RMA -> EMA7 -> signed symmetric log delta; threshold 60; full color transitions",
        entry_actions=["FLAT", "LONG", "SHORT"], exit_actions=["HOLD", "EXIT"],
        supervised_labels="Offline cost-penalized full-path DP hindsight policy on TRAIN ONLY; no maximum holding period",
        validation_selection=dict(entry_probability=a, exit_probability=b,
                                  score=float(best[0]), grid_trials=len(trials)),
        train_fit_counts=fit_counts, final_fit_counts=final_counts,
        validation=validation, test=test,
        top_entry_features=feature_importance(entry_f, cols),
        top_exit_features=feature_importance(exit_f, cols + CONTEXT_COLS),
        fees=dict(per_side=FEE_SIDE, oracle_regularization_per_side=ORACLE_EXTRA_TURN_COST),
        caveats=[
            "Independent ML models choose LONG/SHORT/FLAT and HOLD/EXIT on EVERY closed 4h candle; no opposite-color forced exit",
            "Pine code has misleading RSI27 heading: executable script actually computes RSI12 of SMA21 with EMA7 and symmetric log",
            "Training hindsight oracle knows future ONLY for label generation; no future information in model features or validation/test execution",
            "Validation thresholds selected Feb-Jul 2026 only; Aug-Oct test not used for threshold choice",
            "October 28 Binance archives missing; all symbols end on Oct 27; test is shorter than 3 full calendar months",
            "Individual per-asset independent 1x equity curves, NOT a combined prop account; no liquidation/SL/intrabar/funding",
            "Open-to-open next-bar fills with 0.08%/side fee and 0.02% round-trip spread proxy; actual Upscale execution may differ",
            "Oracle is a strong hindsight benchmark, not a deployable optimal policy. ML performance must be judged only on unseen validation/test",
            "Manual trades are completely excluded, reserved for separate experiment",
            "Test period has already been viewed in preceding baseline research; additional iterations require fresh future data for a pristine final OOS",
        ])
    (ROOT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("ML_REPORT", json.dumps(dict(
        validation=validation["summary"], test=test["summary"],
        selected_thresholds=dict(entry=a, exit=b),
        top_entry_features=report["top_entry_features"][:8],
        top_exit_features=report["top_exit_features"][:8],
        assets=test["by_symbol"],
    ), ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
