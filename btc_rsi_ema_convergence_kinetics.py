"""BTC RSI/signal convergence kinetics: discretionary selection and outcomes.

Purpose: test trader's central hypothesis, NOT maximize in-sample strategy PnL.
Strictly completed 4H candles for all signal candidates; separate entry-time
1H-closed reconstruction for actual manual timestamps. No network, orders or
external indicators. All features are determined no later than their timestamp.
"""
import bisect
import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, fisher_exact, mannwhitneyu, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from analyze_mtf_5y import indicator
from btc_manual_trade_statistical_audit import bh, jret
from btc_price_action_bb_volume_study import read, ts
from completed_candles import aggregate_completed

H = 3_600_000
ALPHA = 2 / (7 + 1)  # Pine EMA7; verify in parity audit if inputs change.
EPS = 1e-6
OUT = Path("reports/btc_rsi_ema_convergence_kinetics.json")

# Frozen exploratory feature groups. No post-hoc feature search for CV models.
MODELS = {
    "legacy_delta": ["delta_abs", "delta_fade_abs", "delta_prev_abs"],
    "raw_gap": ["gap_abs", "gap_closure_abs", "gap_accel_abs"],
    "relative_gap": ["gap_abs", "gap_closure_fraction", "gap_accel_fraction"],
    "excess_over_ema": ["gap_abs", "ema_excess_fraction", "gap_accel_fraction"],
    "legacy_plus_kinetics": [
        "delta_abs", "delta_fade_abs", "gap_closure_fraction",
        "gap_accel_fraction", "ema_excess_fraction"
    ],
}
TEST_KEYS = [
    "gap_abs", "gap_prev_abs", "gap_closure_abs", "gap_closure_fraction",
    "gap_accel_abs", "gap_accel_fraction", "ema_excess_abs",
    "ema_excess_fraction", "gap_closure_streak", "gap_fade_after_peak",
    "gap_peak_to_now_frac", "gap_prev_percentile",
    "delta_abs", "delta_prev_abs", "delta_fade_abs",
    "delta_fade_fraction", "delta_accel_abs", "delta_peak_to_now_frac",
    "rsi_prev", "rsi_move_signed_to_zero", "rsi_extremity",
]
BOOL_KEYS = {"gap_fade_after_peak"}
OUTCOME_KEYS = [
    "gap_abs", "gap_closure_abs", "gap_closure_fraction",
    "gap_accel_abs", "gap_accel_fraction", "ema_excess_fraction",
    "gap_peak_to_now_frac", "gap_prev_percentile", "delta_abs",
    "delta_fade_abs", "delta_accel_abs", "rsi_extremity",
]

def finite(x):
    return x is not None and math.isfinite(float(x))

def rnd(x, n=5):
    return round(float(x), n) if finite(x) else None

def med(x):
    return rnd(np.median(x)) if x else None

def kinetics(ind, i):
    rsi, delta = ind["rsi"], ind["delta"]
    # Indicator implementation does not return EMA. Recover E from the exact
    # EMA7 recursion used in indicator(): E_t = alpha RSI_t + (1-alpha) E_{t-1}.
    # Its initializer sets E=RSI on the first valid RSI bar.
    # Recompute signal EMA for all RSI values; avoid look-ahead / prefix drift.
    if i < 65 or not all(finite(rsi[j]) and finite(delta[j]) for j in range(i-4, i+1)):
        return None
    ema = ind["signal_ema"]
    gap = [rsi[j] - ema[j] for j in range(i-4, i+1)]
    d = [abs(z) for z in gap]
    if d[-2] <= EPS or d[-3] <= EPS:
        return None
    if gap[-1]*gap[-2] <= 0:
        return None  # exclude a sign-changing RSI/EMA crossing, distinct event
    clos = d[-2]-d[-1]
    previous_clos = d[-3]-d[-2]
    delta_ab=[abs(delta[j]) for j in range(i-4,i+1)]
    prev_delta=delta_ab[-2]
    prev_window=[abs(rsi[j]-ema[j]) for j in range(max(33,i-60),i)]
    percent=sum(x<d[-2] for x in prev_window)/len(prev_window) if prev_window else None
    # With constant RSI, EMA closes fraction alpha of prior RSI-EMA distance
    # per bar. Extra convergence isolates the RSI-change contribution.
    exp_mech=ALPHA*d[-2]
    # From G_t=(1-alpha)*(G_prev+(RSI_t-RSI_prev)),
    # excess=(1-alpha)*Gprev-Gcur in sign-consistent coordinates.
    excess=clos-exp_mech
    peak=max(d[-4:-1])
    delta_peak=max(delta_ab[-4:-1])
    # Feature names are in 4H BAR units, not per real-time hour.
    return {
        "gap_abs":d[-1],
        "gap_prev_abs":d[-2],
        "gap_closure_abs":clos,
        "gap_closure_fraction":clos/d[-2],
        "gap_accel_abs":clos-previous_clos,
        "gap_accel_fraction":clos/d[-2]-previous_clos/d[-3],
        "ema_excess_abs":excess,
        "ema_excess_fraction":excess/d[-2],
        "gap_closure_streak":sum(d[-j-1]>d[-j] for j in (1,2,3)),
        "gap_fade_after_peak":int(d[-2]>=d[-3] and d[-1]<d[-2]),
        "gap_peak_to_now_frac":(peak-d[-1])/peak if peak>EPS else None,
        "gap_prev_percentile":percent,
        "delta_abs":delta_ab[-1],
        "delta_prev_abs":prev_delta,
        "delta_fade_abs":prev_delta-delta_ab[-1],
        "delta_fade_fraction":(prev_delta-delta_ab[-1])/prev_delta if prev_delta>EPS else None,
        "delta_accel_abs":(prev_delta-delta_ab[-1])-(delta_ab[-3]-prev_delta),
        "delta_peak_to_now_frac":(delta_peak-delta_ab[-1])/delta_peak if delta_peak>EPS else None,
        "rsi_prev":rsi[i-1],
        "rsi_move_signed_to_zero":-(1 if gap[-2]>0 else -1)*(rsi[i]-rsi[i-1]),
        "rsi_extremity":abs(rsi[i]-50),
    }

def indicator_plus(rows):
    ind=indicator(rows)
    alpha=ALPHA
    val=None
    em=[]
    for x in ind["rsi"]:
        if not finite(x):
            em.append(float("nan"))
        else:
            val=x if val is None else alpha*x+(1-alpha)*val
            em.append(val)
    ind["signal_ema"]=em
    return ind

def asof_manual(raw, cut):
    """Construct latest (possibly partial) 4H only from fully closed hourly bars."""
    idx=bisect.bisect_right([x[0] for x in raw],cut-H)
    eligible=raw[:idx]
    if not eligible:return None
    bars=aggregate_completed(eligible,4,asof_ms=cut)
    if len(bars)<120:return None
    end=bars[-1][0]+4*H
    partial=[r for r in eligible if end<=r[0]<end+4*H]
    if partial:
        bars.append((end, partial[0][1], max(x[2] for x in partial),
                     min(x[3] for x in partial),partial[-1][4]))
    ind=indicator_plus(bars)
    f=kinetics(ind,len(bars)-1)
    if f is None:return None
    return {"partial_hours":len(partial),"color":ind["color"][-1],
            "delta":rnd(ind["delta"][-1]),"rsi":rnd(ind["rsi"][-1]),
            "signal_ema":rnd(ind["signal_ema"][-1]),"features":f}

def chronology(samples, modelkeys):
    X=np.asarray([[x["features"][k] for k in modelkeys] for x in samples],float)
    y=np.asarray([x["selected"] for x in samples],int)
    folds=[]
    if len(samples)<70:return folds
    for train,test in TimeSeriesSplit(n_splits=4).split(X):
        if len(np.unique(y[train]))<2 or len(np.unique(y[test]))<2:
            folds.append({"train_n":len(train),"test_n":len(test),
                          "test_selected":int(sum(y[test])),"skipped":"single class"})
            continue
        clf=make_pipeline(StandardScaler(),
            LogisticRegression(C=0.3,class_weight="balanced",max_iter=2000))
        clf.fit(X[train],y[train])
        probs=clf.predict_proba(X[test])[:,1]
        top_n=max(1,round(len(test)*.1))
        chosen=np.argsort(probs)[-top_n:]
        folds.append({
            "train_n":len(train),"train_selected":int(sum(y[train])),
            "test_n":len(test),"test_selected":int(sum(y[test])),
            "auc":rnd(roc_auc_score(y[test],probs),4),
            "average_precision":rnd(average_precision_score(y[test],probs),4),
            "precision_top_decile":rnd(np.mean(y[test][chosen]),4),
            "test_base_rate":rnd(np.mean(y[test]),4),
        })
    return folds

def main():
    raw=read()
    bars=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
    ind=indicator_plus(bars)
    # Parity test: signal EMA reconstructed at each bar must return the same
    # signed mirrored log delta as historical indicator, within machine error.
    for i in range(80,len(bars)):
        r,e=ind["rsi"][i],ind["signal_ema"][i]
        a=min(r,100-r);b=min(e,100-e)
        if a<=0 or b<=0:continue
        expected=(1 if r>e else -1)*abs(math.log(a/b)*100)
        if abs(ind["delta"][i]-expected)>1e-7:
            raise AssertionError(f"EMA reconstruction mismatch at {i}")
    complete_time_to_idx={x[0]+4*H:i for i,x in enumerate(bars)}
    prev=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
    bb=json.loads(Path("reports/btc_4h_bollinger_sigma_study.json").read_text())
    selected_return={(x["time"],x["side"]):x.get("ret") for x in bb["selected_trades"]}
    matched_entries={(x["signal_time"],x["side"]):x["manual_time"] for x in prev["matched_trades"]}
    # Signals after the final annotated manual entry are right-censored:
    # no evidence the trader reviewed or skipped them.
    with open("data/manual_btc_trades_2025_2026.csv") as stream:
        journal_rows=list(csv.DictReader(stream))
    last_manual_entry=max(ts(x["entry_msk"]) for x in journal_rows
                          if x["quality"]=="ok" and ts(x["entry_msk"]) is not None)
    samples=[];invalid=[];outside_journal=0
    for select,source in ((1,prev["matched_trades"]),(0,prev["skipped_signals"])):
        for s in source:
            tm=s["signal_time"] if select else s["time"]
            if tm>last_manual_entry:
                outside_journal+=1
                continue
            side=s["side"]
            k=complete_time_to_idx.get(tm)
            if k is None:
                invalid.append({"time":tm,"reason":"no completed 4h timestamp"})
                continue
            f=kinetics(ind,k)
            if f is None or any(not finite(f.get(key)) for key in TEST_KEYS):
                invalid.append({"time":tm,"reason":"missing feature or RSI sign cross"})
                continue
            samples.append({"time":tm,"side":side,"selected":select,
                 "manual_time":matched_entries.get((tm,side)),
                 "manual_net_pct":rnd(100*selected_return.get((tm,side)) if selected_return.get((tm,side)) is not None else None),
                 "features":f})
    samples.sort(key=lambda x:x["time"])
    tests=[];outcomes=[];models={};time_matched=[]
    for side,label in ((1,"LONG"),(-1,"SHORT")):
        side_rows=[x for x in samples if x["side"]==side]
        a=[x for x in side_rows if x["selected"]]
        b=[x for x in side_rows if not x["selected"]]
        for key in TEST_KEYS:
            va=[x["features"][key] for x in a];vb=[x["features"][key] for x in b]
            if len(va)<6 or len(vb)<20:continue
            if key in BOOL_KEYS:
                _,p=fisher_exact([[sum(va),len(va)-sum(va)],[sum(vb),len(vb)-sum(vb)]])
                effect={"selected_pct":rnd(100*np.mean(va),2),
                        "skipped_pct":rnd(100*np.mean(vb),2)}
            else:
                _,p=mannwhitneyu(va,vb,alternative="two-sided")
                effect={"selected_median":med(va),"skipped_median":med(vb)}
            tests.append({"side":label,"feature":key,"selected_n":len(va),
                    "skipped_n":len(vb),"p_raw":rnd(p,7),**effect})
            # Slow regime control: each selected compared to median skipped
            # same side within +/-30d, descriptive signed count only.
            if key in ("gap_closure_fraction","gap_accel_fraction",
                       "ema_excess_fraction","delta_fade_abs"):
                signed=[]
                for sel in a:
                    near=[x["features"][key] for x in b if abs(x["time"]-sel["time"])<=30*24*H]
                    if len(near)>=3:
                        signed.append(sel["features"][key]-np.median(near))
                if len(signed)>=7:
                    time_matched.append({"side":label,"feature":key,"n":len(signed),
                       "positive_diffs":int(sum(x>0 for x in signed)),
                       "median_local_difference":med(signed),
                       "sign_test_p":rnd(binomtest(sum(x>0 for x in signed),
                               sum(x!=0 for x in signed),.5).pvalue,6)})
        for mname,keys in MODELS.items():
            good=[x for x in side_rows if all(finite(x["features"][k]) for k in keys)]
            folds=chronology(good,keys)
            valid=[x for x in folds if "auc" in x]
            models[label+"_"+mname]={"n":len(good),"selected":sum(x["selected"] for x in good),
                "features":keys,"folds":folds,
                "mean_auc":rnd(np.mean([x["auc"] for x in valid]),4) if valid else None,
                "mean_average_precision":rnd(np.mean([x["average_precision"] for x in valid]),4) if valid else None,
                "mean_precision_top_decile":rnd(np.mean([x["precision_top_decile"] for x in valid]),4) if valid else None}
    for test,q in zip(tests,bh([x["p_raw"] for x in tests])):
        test["q_bh"]=q
    for side,label in ((None,"ALL"),(1,"LONG"),(-1,"SHORT")):
        a=[x for x in samples if x["selected"] and x["manual_net_pct"] is not None
           and (side is None or x["side"]==side)]
        for key in OUTCOME_KEYS:
            if len(a)<8 or len({x["features"][key] for x in a})<=2:continue
            rho,p=spearmanr([x["features"][key] for x in a],
                            [x["manual_net_pct"] for x in a])
            if finite(rho) and finite(p):
                outcomes.append({"side":label,"feature":key,"n":len(a),
                        "rho":rnd(rho,5),"p_raw":rnd(p,7)})
    for row,q in zip(outcomes,bh([x["p_raw"] for x in outcomes])):
        row["q_bh"]=q
    manual=[]
    with open("data/manual_btc_trades_2025_2026.csv") as stream:
        rows=list(csv.DictReader(stream))
    for row in rows:
        tm=ts(row["entry_msk"])
        if tm is None or tm<raw[0][0]+240*H or tm>raw[-1][0]+H:continue
        snap=asof_manual(raw,tm)
        if snap:
            manual.append({"time_msk":row["entry_msk"],
                "side":"LONG" if float(row["sl"])<float(row["entry"]) else "SHORT",
                "quality":row["quality"],"entry_reason":row["entry_reason"],
                "net_pct":rnd(100*jret(row)) if row["quality"]=="ok" and jret(row) is not None else None,
                **snap})
    partial_summary={}
    for side in ("LONG","SHORT"):
        group=[x for x in manual if x["side"]==side]
        partial_summary[side]={
            "n":len(group),
            "incomplete_4h_entries":sum(x["partial_hours"]>0 for x in group),
            "median_gap_closure_fraction":med([x["features"]["gap_closure_fraction"] for x in group]),
            "median_ema_excess_fraction":med([x["features"]["ema_excess_fraction"] for x in group]),
            "median_delta_fade_abs":med([x["features"]["delta_fade_abs"] for x in group]),
            "fraction_positive_actual_convergence":rnd(np.mean([x["features"]["gap_closure_abs"]>0 for x in group]),4) if group else None,
            "fraction_excess_over_ema":rnd(np.mean([x["features"]["ema_excess_abs"]>0 for x in group]),4) if group else None,
        }
    # Diagnostic: the mirrored logarithmic DeltaRSI may fade even when the
    # literal |RSI-EMA| gap is still widening. These are distinct quantities.
    divergence_diagnostic={}
    mismatch_examples=[]
    for side,label in ((1,"LONG"),(-1,"SHORT")):
        for chosen,name in ((1,"selected"),(0,"skipped")):
            subset=[x for x in samples if x["side"]==side and x["selected"]==chosen]
            fading=[x for x in subset if x["features"]["delta_fade_abs"]>0]
            contradictory=[x for x in fading if x["features"]["gap_closure_abs"]<=0]
            divergence_diagnostic[label+"_"+name]={
                "n":len(subset),
                "delta_fading_n":len(fading),
                "delta_fades_but_gap_not_converging":len(contradictory),
                "fraction_of_delta_fades_without_gap_convergence":rnd(
                    len(contradictory)/len(fading)) if fading else None,
            }
            for x in contradictory[:2]:
                if chosen:
                    mismatch_examples.append({
                        "time_utc":dt.datetime.fromtimestamp(x["time"]/1000,dt.timezone.utc).isoformat(),
                        "side":label,"delta_prev_abs":rnd(x["features"]["delta_prev_abs"]),
                        "delta_abs":rnd(x["features"]["delta_abs"]),
                        "gap_closure_fraction":rnd(x["features"]["gap_closure_fraction"]),
                    })
    out={
        "description":"Test distance/velocity/acceleration of RSI12(SMA21) versus EMA7(RSI), with original signed symmetric log-DeltaRSI retained as control.",
        "mathematical_identity":"G_t=(1-alpha)*(G_(t-1)+(RSI_t-RSI_(t-1))); alpha=.25, so flat RSI mechanically shrinks |G| by 25% per closed 4H candle if same sign. Excess=(|G_prev|-|G_current|)-.25*|G_prev|.",
        "selected_vs_skipped_notes":"Selection labels are trader's journal proximity-matched within 4h to mediumR->weakR and mediumB->weakB 4H transitions. This subset is NOT all visible DeltaRSI opportunities. Post-journal signals are censored, never silently labeled skipped. Label provenance and serially correlated signals limit inference. Compare LONG and SHORT independently. Candidate features strictly from closed 4H candles; no lookahead.",
        "partial_notes":"Manual entry-time snapshots constructed using only 1H candles already closed by marked entry hour. Forming 4H is reconstructed as-of that hour; intrahour changes not observable. Rows with RSI/EMA crossing or missing data excluded. Do not extrapolate 4H-close selection results to partial intrabar readings.",
        "cv_notes":"Chronological TimeSeriesSplit(4) expanding training, no tuning on folds; skip folds lacking both classes. Metrics measure imitation of journal selection, NOT profitable trading. All historic BTC data was previously inspected; no untouched holdout.",
        "outcome_notes":"Manual net outcomes from weighted journal exits with 0.15% roundtrip assumed. Returns NOT independently verified trades. Multiple outcome correlations BH-adjusted, tiny selected sample.",
        "raw_complete_4h_bars":len(bars),
        "source_candidate_events":len(prev["matched_trades"])+len(prev["skipped_signals"]),
        "last_journal_entry_utc":dt.datetime.fromtimestamp(last_manual_entry/1000,dt.timezone.utc).isoformat(),
        "post_journal_events_excluded":outside_journal,
        "accepted_candidate_events":len(samples),
        "selected_events":sum(x["selected"] for x in samples),
        "skipped_events":sum(not x["selected"] for x in samples),
        "skipped_feature_events":invalid,
        "selection_tests":sorted(tests,key=lambda x:x["p_raw"]),
        "mirrored_delta_vs_literal_gap_diagnostics":divergence_diagnostic,
        "selected_mismatch_examples":mismatch_examples,
        "local_time_matched_checks":time_matched,
        "selection_cv":models,
        "return_correlations":sorted(outcomes,key=lambda x:x["p_raw"]),
        "manual_entry_hour_snapshots_summary":partial_summary,
        "manual_entry_hour_snapshots":manual,
        "selected_4h_examples":[
            {"time":x["time"],"side":x["side"],"manual_time":x["manual_time"],
             "features":{k:rnd(v) for k,v in x["features"].items()},
             "journal_net_pct":x["manual_net_pct"]}
            for x in samples if x["selected"]
        ],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps({
        "signals":{"selected":out["selected_events"],"skipped":out["skipped_events"],"invalid":len(invalid)},
        "manual_entry_summary":partial_summary,
        "selection_top":out["selection_tests"][:14],
        "local_controls":time_matched,
        "outcomes_top":out["return_correlations"][:12],
        "CV":{k:{"auc":v["mean_auc"],"ap":v["mean_average_precision"],
                 "folds_valid":sum("auc" in x for x in v["folds"])}
              for k,v in models.items()},
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
