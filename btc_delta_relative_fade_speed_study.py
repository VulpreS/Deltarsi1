"""Study normalized fading SPEED of the ORIGINAL log-mirrored DeltaRSI on BTC.

No indicator redesign. Research:
 (1) Is the current fade unusually fast relative to the preceding impulse?
 (2) Does this improve the chronological imitation of discretionary selection
     beyond the prior DeltaRSI magnitude?
 (3) Does it associate with subsequent price movement or annotated trade PnL?

Candidate signals: existing one-to-one manual matches to CLOSED 4H medium->weak
transitions. Omit post-journal events and explicitly flag signals that occurred
while the trader already had a documented open BTC position. All feature and
historical scaling inputs are strictly at/before signal-close. No live orders.
"""
import csv
import datetime as dt
import json
import math
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact, mannwhitneyu, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from btc_price_action_bb_volume_study import read, ts
from analyze_mtf_5y import indicator
from completed_candles import aggregate_completed
from btc_manual_trade_statistical_audit import bh, jret

H = 3_600_000
FEE = 0.0015
OUT = Path("reports/btc_delta_relative_fade_speed_study.json")

# Small, predeclared nested models; no post-hoc threshold optimization.
MODELS = {
    "magnitude_only": ["delta_prev_abs"],
    "historical_percentile_only": ["prior_delta_pctile"],
    "magnitude_plus_percentile": ["delta_prev_abs", "prior_delta_pctile"],
    "original_delta": ["delta_prev_abs", "delta_current_abs"],
    "speed_only": ["fade_fraction", "fade_vs_growth", "fade_acceleration_frac"],
    "magnitude_plus_relative_speed": [
        "delta_prev_abs", "delta_current_abs", "fade_vs_growth"
    ],
    "magnitude_plus_phase": [
        "delta_prev_abs", "delta_current_abs", "fade_vs_growth",
        "fade_acceleration_frac", "peak_age_bars"
    ]
}
COMPARE = [
    "delta_prev_abs", "delta_current_abs",
    "fade_absolute", "fade_fraction", "fade_log_ratio",
    "fade_acceleration_frac", "fade_vs_growth", "fade_vs_prior_motion",
    "pre_growth_mean", "pre_motion_median",
    "peak_age_bars", "pre_growth_streak", "peak_decline_fraction",
    "prior_delta_pctile", "phase_peak_is_last", "fade_gt_growth",
]
BINARY = {"phase_peak_is_last", "fade_gt_growth"}
FORWARD_HORIZONS = (3, 6, 12)  # 12h, 24h and 48h at 4H resolution

def rnd(a,decimals=5):
    return round(float(a),decimals) if a is not None and math.isfinite(float(a)) else None

def med(x):
    return rnd(np.median(x)) if len(x) else None

def feature(ind, k):
    d = ind["delta"]
    if k < 215 or not all(math.isfinite(d[j]) for j in range(k-65,k+1)):
        return None
    if d[k]*d[k-1] <= 0:
        return None
    a=[abs(x) for x in d]
    prev,cur,older=a[k-1],a[k],a[k-2]
    if prev < 1e-8 or older < 1e-8:
        return None
    fade=prev-cur  # positive = magnitude of original DeltaRSI is fading
    olderfade=a[k-2]-a[k-1]
    steps=[a[j]-a[j-1] for j in range(k-6,k)] # strictly earlier bars
    positive_steps=[max(x,0) for x in steps]
    positive_mean=float(np.mean(positive_steps))
    # Prior impulse needs a denominator floor so tiny previous advances do not
    # spuriously generate enormous ratios. The floor depends only on D_(t-1).
    growth_scale=max(positive_mean,0.05*prev,1.0)
    previous_changes=[abs(a[j]-a[j-1]) for j in range(k-10,k)]
    motion_scale=max(float(np.median(previous_changes)),0.05*prev,1.0)
    prior=[a[j] for j in range(k-8,k)]
    peak_idx=int(np.argmax(prior))
    peak=max(prior)
    streak=0
    for j in range(k-1,max(k-10,1),-1):
        if a[j]>=a[j-1]:
            streak+=1
        else:
            break
    prior60=[a[j] for j in range(k-61,k-1)] # exclude current and prior event bar
    return {
        "delta_prev_abs":prev,
        "delta_current_abs":cur,
        "fade_absolute":fade,
        "fade_fraction":fade/prev,
        "fade_log_ratio":math.log((prev+1)/(cur+1)),
        "fade_acceleration_frac":(fade-olderfade)/prev,
        "fade_vs_growth":fade/growth_scale,
        "fade_vs_prior_motion":fade/motion_scale,
        "pre_growth_mean":positive_mean,
        "pre_motion_median":float(np.median(previous_changes)),
        "peak_age_bars":7-peak_idx, # 0=bar immediately before candidate
        "pre_growth_streak":streak,
        "peak_decline_fraction":(peak-cur)/max(peak,1),
        "prior_delta_pctile":sum(z<prev for z in prior60)/len(prior60),
        "phase_peak_is_last":int(peak_idx==7),
        "fade_gt_growth":int(fade>growth_scale),
    }

def active_intervals():
    """Known open manual positions; do not label signals inside them as skipped."""
    intervals=[]
    with open("data/manual_btc_trades_2025_2026.csv") as stream:
        journal=list(csv.DictReader(stream))
    for x in journal:
        if x["quality"]!="ok":continue
        start=ts(x["entry_msk"])
        end_times=[ts(x.get(z,"")) for z in ("exit1_msk","exit2_msk")]
        if start is None or end_times[0] is None:continue
        end=max(t for t in end_times if t is not None)
        if end>=start:intervals.append((start,end,x["entry_msk"]))
    return intervals,journal

def signal_forward(bars, k,side):
    """Diagnostic forward holding-period return; NOT a strategy backtest."""
    result={}
    if k+12>=len(bars):return result
    entry=bars[k+1][1] # first next 4H open AFTER signal closes
    for h in FORWARD_HORIZONS:
        value=side*(bars[k+h][4]/entry-1)*100
        result[f"forward_{h*4}h_net_pct"]=value-100*FEE
    hi=max(bars[j][2] for j in range(k+1,k+13))
    lo=min(bars[j][3] for j in range(k+1,k+13))
    result["mfe_48h_pct"]=100*(hi/entry-1) if side==1 else 100*(1-lo/entry)
    result["mae_48h_pct"]=100*(lo/entry-1) if side==1 else 100*(1-hi/entry)
    return result

def split_test(data,keys):
    """Every model evaluated on the SAME admissible timestamps per direction."""
    X=np.array([[x["features"][key] for key in keys] for x in data],float)
    y=np.array([x["selected"] for x in data],int)
    folds=[]
    if len(y)<40:return folds
    for train,test in TimeSeriesSplit(n_splits=4).split(X):
        if len(set(y[train]))<2 or len(set(y[test]))<2:
            folds.append({"train_n":len(train),"test_n":len(test),
                          "test_positives":int(y[test].sum()),"skipped":"single class"})
            continue
        mod=make_pipeline(StandardScaler(),
            LogisticRegression(C=0.3,class_weight="balanced",max_iter=1000))
        mod.fit(X[train],y[train])
        pred=mod.predict_proba(X[test])[:,1]
        top=max(1,int(round(0.1*len(test))))
        high=np.argsort(pred)[-top:]
        folds.append({"train_n":len(train),"train_positives":int(y[train].sum()),
                      "test_n":len(test),"test_positives":int(y[test].sum()),
                      "auc":rnd(roc_auc_score(y[test],pred),4),
                      "average_precision":rnd(average_precision_score(y[test],pred),4),
                      "top_decile_precision":rnd(np.mean(y[test][high]),4),
                      "test_positive_rate":rnd(np.mean(y[test]),4)})
    return folds

def main():
    raw=read()
    bars=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
    ind=indicator(bars)
    history={r[0]+4*H:i for i,r in enumerate(bars)}
    matches=json.loads(Path("reports/btc_price_action_bb_volume_study.json").read_text())
    annotated=json.loads(Path("reports/btc_4h_bollinger_sigma_study.json").read_text())
    intervals,journal=active_intervals()
    last_entry=max(ts(x["entry_msk"]) for x in journal if x["quality"]=="ok" and ts(x["entry_msk"]) is not None)
    manual_returns={(x["time"],x["side"]):rnd(x["ret"]*100) if x["ret"] is not None else None
                    for x in annotated["selected_trades"]}
    candidates=[];counters=Counter()
    for chosen,source in ((1,matches["matched_trades"]),(0,matches["skipped_signals"])):
        for row in source:
            time=row["signal_time"] if chosen else row["time"]
            side=row["side"]
            if time>last_entry:
                counters["right_censored_after_journal"]+=1
                continue
            k=history.get(time)
            if k is None:
                counters["no_closed_4h"]+=1
                continue
            f=feature(ind,k)
            if f is None:
                counters["nonfinite_or_crossing"]+=1
                continue
            # User cannot make a second independent entry while holding an open
            # manual BTC trade. Keep observed entries, but exclude "skipped"
            # signals during a held trade for the main opportunity universe.
            within_open=[p for start,end,p in intervals if start<time<end]
            in_position=bool(within_open)
            if not chosen and in_position:
                counters["skipped_while_manual_position_open"]+=1
            if chosen and in_position:
                counters["selected_while_manual_position_open"]+=1
            previous_trace=[rnd(abs(ind["delta"][j]),3) for j in range(k-6,k+1)]
            candidates.append({
                "time_utc":dt.datetime.fromtimestamp(time/1000,dt.timezone.utc).isoformat(),
                "time_ms":time,
                "side":"LONG" if side==1 else "SHORT",
                "direction":side,
                "selected":chosen,
                "manual_time_utc":dt.datetime.fromtimestamp(row["manual_time"]/1000,dt.timezone.utc).isoformat() if chosen else None,
                "in_existing_manual_position":in_position,
                "features":{key:rnd(value,8) for key,value in f.items()},
                "delta_last_seven":previous_trace,
                "manual_net_pct":manual_returns.get((time,side)),
                "future":{key:rnd(val) for key,val in signal_forward(bars,k,side).items()},
            })
    candidates.sort(key=lambda x:x["time_ms"])
    main=[x for x in candidates if x["selected"] or not x["in_existing_manual_position"]]
    summary={};tests=[];models={};correlations=[];forward=[]
    for side in ("LONG","SHORT"):
        subset=[x for x in main if x["side"]==side]
        selected=[x for x in subset if x["selected"]]
        skipped=[x for x in subset if not x["selected"]]
        summary[side]={"n":len(subset),"selected":len(selected),"skipped":len(skipped),
            "selected_rate":rnd(len(selected)/len(subset)) if subset else None}
        for key in COMPARE:
            a=[x["features"][key] for x in selected]
            b=[x["features"][key] for x in skipped]
            if len(a)<5 or len(b)<10:continue
            if key in BINARY:
                _,p=fisher_exact([[sum(a),len(a)-sum(a)],[sum(b),len(b)-sum(b)]])
                result={"selected_rate":rnd(np.mean(a)),"skipped_rate":rnd(np.mean(b))}
            else:
                _,p=mannwhitneyu(a,b,alternative="two-sided")
                result={"selected_median":med(a),"skipped_median":med(b)}
            tests.append({"direction":side,"feature":key,
                "n_selected":len(a),"n_skipped":len(b),
                "p":rnd(p,7),**result})
        for modelname,keys in MODELS.items():
            folds=split_test(subset,keys)
            valid=[x for x in folds if "auc" in x]
            models[f"{side}_{modelname}"]={
                "features":keys,
                "folds":folds,
                "mean_auc":rnd(np.mean([x["auc"] for x in valid]),4) if valid else None,
                "mean_average_precision":rnd(np.mean([x["average_precision"] for x in valid]),4) if valid else None,
                "mean_top_decile_precision":rnd(np.mean([x["top_decile_precision"] for x in valid]),4) if valid else None,
            }
        for outcome in ("manual_net_pct",):
            eligible=[x for x in selected if x[outcome] is not None]
            for key in ("delta_prev_abs","fade_fraction","fade_vs_growth",
                        "fade_acceleration_frac","peak_age_bars"):
                if len(eligible)<8 or len(set(x["features"][key] for x in eligible))<=2:continue
                rho,p=spearmanr([x["features"][key] for x in eligible],[x[outcome] for x in eligible])
                if math.isfinite(rho) and math.isfinite(p):
                    correlations.append({"direction":side,"outcome":outcome,"feature":key,
                        "n":len(eligible),"rho":rnd(rho,5),"p":rnd(p,7)})
        for horizon in FORWARD_HORIZONS:
            key=f"forward_{horizon*4}h_net_pct"
            usable=[x for x in subset if key in x["future"]]
            # This correlation is DIAGNOSTIC ONLY; overlapping future windows
            # and serial signal clusters violate independent-sample inference.
            if len(usable)>=20:
                for feat in ("fade_fraction","fade_vs_growth","delta_prev_abs"):
                    rho,p=spearmanr([x["features"][feat] for x in usable],
                                    [x["future"][key] for x in usable])
                    forward.append({"direction":side,"future_window_hours":4*horizon,
                                    "feature":feat,"n":len(usable),"rho":rnd(rho,5),
                                    "p_exploratory":rnd(p,7)})
    if tests:
        for t,q in zip(tests,bh([x["p"] for x in tests])):t["q_bh"]=q
    if correlations:
        for t,q in zip(correlations,bh([x["p"] for x in correlations])):t["q_bh"]=q
    if forward:
        for t,q in zip(forward,bh([x["p_exploratory"] for x in forward])):t["q_bh_exploratory"]=q
    # Prespecified strength strata: native Pine color cutoff at |Delta|=60
    # and 45 as an intermediate diagnostic, not a fitted optimization.
    strength_strata={}
    for side in ("LONG","SHORT"):
        side_events=[x for x in main if x["side"]==side]
        for name,selector in (
                ("at_or_above_60",lambda d:d>=60),
                ("from_45_to_under_60",lambda d:45<=d<60),
                ("under_45",lambda d:d<45),
                ("at_or_above_45",lambda d:d>=45)):
            sub=[x for x in side_events if selector(x["features"]["delta_prev_abs"])]
            a=[x for x in sub if x["selected"]]
            b=[x for x in sub if not x["selected"]]
            row={"n":len(sub),"selected":len(a),"skipped":len(b),
                 "selection_rate":rnd(len(a)/len(sub)) if sub else None}
            for feat in ("fade_fraction","fade_vs_growth","fade_acceleration_frac"):
                if len(a)>=4 and len(b)>=8:
                    _,p=mannwhitneyu([x["features"][feat] for x in a],
                                     [x["features"][feat] for x in b])
                    row[feat]={"selected_median":med([x["features"][feat] for x in a]),
                               "skipped_median":med([x["features"][feat] for x in b]),
                               "p_exploratory":rnd(p,6)}
            strength_strata[side+"_"+name]=row
    # Robustness: include signals during open manual positions as skipped
    # (previous studies' more permissive universe) but NOT post-journal events.
    sensitivity={}
    for side in ("LONG","SHORT"):
        a=[x for x in candidates if x["side"]==side and x["selected"]]
        b=[x for x in candidates if x["side"]==side and not x["selected"]]
        s={}
        for feat in ("delta_prev_abs","fade_fraction","fade_vs_growth","fade_acceleration_frac"):
            if len(a)>=5 and len(b)>=10:
                _,p=mannwhitneyu([x["features"][feat] for x in a],
                                 [x["features"][feat] for x in b])
                s[feat]={"selected_median":med([x["features"][feat] for x in a]),
                         "skipped_median":med([x["features"][feat] for x in b]),
                         "p":rnd(p,6)}
        sensitivity[side]={"selected":len(a),"skipped":len(b),"results":s}
    output={
      "study":"Original mirrored logarithmic DeltaRSI: fade speed vs preceding impulse speed",
      "indicator":"SMA21(close), RSI12(RMA), EMA7(RSI), sign-preserving mirrored log delta",
      "mathematics":{
        "amplitude":"D_t=abs(original signed log DeltaRSI_t)",
        "fade_velocity":"F_t=D_(t-1)-D_t; positive signifies decreasing magnitude",
        "fade_fraction":"F_t / D_(t-1)",
        "acceleration":"(F_t-F_(t-1))/D_(t-1), where F_(t-1)=D_(t-2)-D_(t-1)",
        "pre_growth_mean":"mean(max(D_j-D_(j-1),0)) over previous 6 closed 4H bars, j=t-6..t-1",
        "fade_vs_growth":"F_t / max(previous_positive_growth_mean, 0.05*D_(t-1), 1)",
        "fade_vs_prior_motion":"F_t / max(previous_median_abs_delta_change_10bars, 0.05*D_(t-1), 1)"
      },
      "limitations":[
        "No indicator or trading-rule changes. No actual orders.",
        "Manual-entry matches are approximate, but report records exact match offsets.",
        "The only eligible signals are completed 4H medium-to-weak COLOR transitions, not every intrabar signal the trader saw.",
        "Selection labels inferred from journal, not a verified exhaustive record of opportunities. Signals after last journal entry right-censored.",
        "Main universe excludes unselected signals during documented open manual BTC positions. Sensitivity includes them.",
        "Previously explored BTC history means chronological checks are NOT untouched independent validation.",
        "Features use data available at 4H signal close, without subsequent candles.",
        "Candidate futures can overlap and 12/24/48H returns omit structural stops, user exits, funding. Costs 0.15% roundtrip only.",
        "Manual PnL self-reported and journal reconstruction may be inconsistent with executable fills.",
        "Exploratory many features + small positive sample; apply BH separately to selection and realized-outcome comparisons."
      ],
      "raw_4h_bars":len(bars),
      "first_signal_utc":main[0]["time_utc"] if main else None,
      "last_annotated_entry_utc":dt.datetime.fromtimestamp(last_entry/1000,dt.timezone.utc).isoformat(),
      "source_candidate_count":len(matches["matched_trades"])+len(matches["skipped_signals"]),
      "considered_before_open_position_mask":len(candidates),
      "eligible_candidate_count":len(main),
      "excluded_counts":dict(counters),
      "counts":summary,
      "selection_tests":sorted(tests,key=lambda x:x["p"]),
      "selection_models":models,
      "realized_return_correlations":sorted(correlations,key=lambda x:x["p"]),
      "forward_return_correlations_exploratory":sorted(forward,key=lambda x:x["p_exploratory"]),
      "position_eligibility_sensitivity":sensitivity,
      "delta_strength_strata":strength_strata,
      "selected_trajectories":[x for x in main if x["selected"]],
      "all_event_rows":main
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2,ensure_ascii=False))
    print(json.dumps({
        "counts":summary,
        "excluded":dict(counters),
        "top_selection":output["selection_tests"][:12],
        "models":{k:{"AUC":v["mean_auc"],"AP":v["mean_average_precision"],
                       "folds":[{"n":x["test_n"],"pos":x["test_positives"],
                                  "auc":x.get("auc")} for x in v["folds"]]}
                  for k,v in models.items()},
        "realized":output["realized_return_correlations"],
        "top_forward":output["forward_return_correlations_exploratory"][:8],
        "sensitivity":sensitivity,
        "strength_strata":strength_strata
    },indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
