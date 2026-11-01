"""XGBoost early-exit hazard model on live-updating DeltaRSI and Pine regime scores.

Compare three FEATURE SETS on EXACT same strict DeltaRSI entries and baseline:
  (1) DeltaRSI+position state only;
  (2) + original Pine REGIME numeric/context features;
  (3) + explicitly normalized HTF Pine composite/context variant.

An offline hindsight label asks whether closing at the next bar's OPEN
would outperform the *pre-existing fixed SL2.5/TP2.5/reverse-fade exit*
by 0.45 ATR. This is an imperfect SUPERVISION PROXY, not an optimal oracle.
Future data is used ONLY to CREATE historical TRAINING LABELS for BASELINE
trades COMPLETED before the train cutoff. Test-time inputs are strictly
as of the prior completed 4h bar, plus prior FULL UTC daily data.

Model exits are decisions during a live position, not a fixed exit profile
chosen at entry. No 48h time limit, no manual labels, no real orders.
No tuning on inspected Aug-Oct. TON futures censored prior to delisting.
"""
from __future__ import annotations
import collections
import datetime as dt
import hashlib
import json
import math
import os

import numpy as np
from xgboost import XGBClassifier

import dynamic_exit_regimes as dyn
from train import ROOT

CAL_END=dyn.CAL_END
VAL1_END=dyn.VAL1_END
VAL2_END=dyn.VAL2_END
FOREVER=dyn.FOREVER
INITIAL=dyn.INITIAL_USD
NOTIONAL=dyn.NOMINAL_USD
COST=dyn.COST
STRESS=dyn.COST_DOUBLE
COINS=dyn.COINS
THRESHOLDS=(.55,.70,.85)
FEATURE_SETS=("delta_only","pine_original","pine_normalized")
REGIMES=("MATURE TREND","FRESH MOVE","AGING TREND","CONFLICT","SLEEPING","NEUTRAL")


def state(base,sc,entry_signal_i,bar_j,side,feature_set):
    """At j OPEN only j-1 and earlier CLOSED candles and past entry facts."""
    entrybar=entry_signal_i+1
    prev=bar_j-1
    if prev<entrybar:
        raise ValueError("Trade must have at least one CLOSED bar before exit prediction")
    entry=float(base["op"][entrybar])
    atr=float(base["atr"][entry_signal_i])
    atr=max(1e-12,atr)
    close=float(base["close"][prev])
    close2=float(base["close"][prev-1])
    delta=float(base["dr"][prev])
    delta2=float(base["dr"][prev-1])
    delta3=float(base["dr"][prev-2])
    entry_delta=float(base["dr"][entry_signal_i])
    sampled_closes=base["close"][entrybar:bar_j]
    hi=float(np.max(sampled_closes))
    lo=float(np.min(sampled_closes))
    favorable=max(0.,side*((hi if side>0 else lo)-entry)/atr)
    adverse=min(0.,side*((lo if side>0 else hi)-entry)/atr)
    current_atr=float(base["atr"][prev])
    original_atr=max(1e-12,float(base["atr"][entry_signal_i]))
    last_bar_span=(float(base["high"][prev])-float(base["low"][prev]))/atr
    v=[
      float(side),
      float(np.log1p(prev-entrybar+1)),
      side*(close-entry)/atr,
      favorable,
      adverse,
      delta/100.,
      abs(delta)/100.,
      (delta-delta2)/100.,
      (delta-2*delta2+delta3)/100.,
      entry_delta/100.,
      abs(delta)/max(.3,abs(entry_delta)),
      abs(delta)/max(.3,abs(delta2)),
      side*(close-close2)/atr,
      (close/entry-1)*100.,
      current_atr/original_atr,
      last_bar_span,
      (float(base["high"][prev])-max(float(base["op"][prev]),close))/atr,
      (min(float(base["op"][prev]),close)-float(base["low"][prev]))/atr,
      side*float(base["ema200_dist"][prev])*100.,
      float(base["shade"][prev]),
      float(base["bear_div"][prev]),
      float(base["bull_div"][prev]),
    ]
    if feature_set!="delta_only":
        score_now=float(sc["composite"][prev])
        score_prev=float(sc["composite"][prev-1])
        score_entry=float(sc["composite"][entry_signal_i])
        score_max=float(sc["composite"][entry_signal_i:bar_j].max())
        local=str(sc["bias_short_term"][prev])
        daily=str(sc["bias_higher_tf"][prev])
        direction="UP" if side>0 else "DOWN"
        opposite="DOWN" if side>0 else "UP"
        regime=str(sc["regime"][prev])
        v.extend([
            score_now,
            score_prev,
            score_now-score_prev,
            score_entry,
            score_now-score_entry,
            score_max-score_now,
            float(sc["score_short_term"][prev]),
            float(sc["score_higher_tf"][prev]),
            float(sc["score_higher_tf"][prev])-float(sc["score_higher_tf"][entry_signal_i]),
            float(local==direction),
            float(local==opposite),
            float(daily==direction),
            float(daily==opposite),
            float(sc["aligned"][prev]),
            float(sc["conflict"][prev]),
            float(sc["nw_slope_consistency"][prev]),
            float(sc["price_structure"][prev]),
            float(sc["ema_pos"][prev]),
            float(sc["ema_dist_score"][prev]),
            float(sc["atr_expand"][prev]),
            float(sc["bb_squeeze"][prev]),
        ])
        v.extend(float(regime==name) for name in REGIMES)
    arr=np.asarray(v,dtype=np.float32)
    arr=np.nan_to_num(arr,nan=0.,posinf=0.,neginf=0.)
    return np.clip(arr,-100.,100.)


def samples(data,model_type,cutoff,exclude=()):
    features=[]
    labels=[]
    weights=[]
    from_assets=collections.Counter()
    trades_by_asset=collections.Counter()
    n_good=n_bad=0
    sc_mode="original" if model_type!="pine_normalized" else "normalized_htf_experiment"
    for sym in COINS:
        if sym in set(exclude):
            continue
        base,scoring_by_mode,signals=data[sym]
        sc=scoring_by_mode[sc_mode]
        end=int(np.searchsorted(base["t"],cutoff))
        next_free=dyn.WARMUP
        for i,side in signals:
            entrybar=i+1
            if entrybar<dyn.WARMUP or entrybar>=end or entrybar<next_free:
                continue
            natural=dyn.one_trade(base,sc,i,side,end,dyn.POLICIES["fixed_2p5"])
            if natural is None:
                continue
            if not natural["realized"]:
                # Censored baseline trade; cannot know its true natural exit
                # using only pre-cutoff observations.
                break
            next_free=natural["exit_idx"]+1
            last=natural["exit_idx"]
            first=natural["entry_idx"]+1
            if first>last:
                continue
            atr=float(base["atr"][i])
            natural_exit=float(natural["exit"])
            states=[]
            ys=[]
            for j in range(first,last+1):
                state_j=state(base,sc,i,j,side,model_type)
                closing_now=float(base["op"][j])
                gain_if_exit_now=side*(closing_now-natural_exit)/atr
                label=int(gain_if_exit_now>=.45)
                states.append(state_j)
                ys.append(label)
            if not states:
                continue
            w=1./len(states)
            features.extend(states)
            labels.extend(ys)
            weights.extend([w]*len(states))
            n_good+=sum(ys)
            n_bad+=len(ys)-sum(ys)
            from_assets[sym]+=len(states)
            trades_by_asset[sym]+=1
    X=np.asarray(features,dtype=np.float32)
    y=np.asarray(labels,dtype=np.int8)
    w=np.asarray(weights,dtype=float)
    if len(X)<250 or min(np.bincount(y,minlength=2))<30:
        raise RuntimeError(f"{model_type}: inadequate supervised evidence n={len(X)} y={np.bincount(y,minlength=2)}")
    # Trade-balanced weighting; modest positive-class correction.
    positive=max(.03,float(np.sum(w[y==1])/np.sum(w)))
    w[y==1]*=min(3.,(1-positive)/positive)
    return X,y,w,dict(rows=len(y),positive_rate=float(y.mean()),
                       class_counts=np.bincount(y,minlength=2).tolist(),
                       signal_trades=sum(trades_by_asset.values()),
                       rows_by_asset=dict(from_assets),
                       trades_by_asset=dict(trades_by_asset))


def fit(data,model_type,cutoff,exclude=()):
    X,y,w,diagnostics=samples(data,model_type,cutoff,exclude=exclude)
    model=XGBClassifier(n_estimators=140,max_depth=3,learning_rate=.055,
       subsample=.85,colsample_bytree=.8,min_child_weight=4.,
       reg_lambda=4.,random_state=20261031,n_jobs=2,
       tree_method="hist",eval_metric="logloss")
    model.fit(X,y,sample_weight=w)
    diagnostics["in_sample_auc_not_oos"]=None
    return model,diagnostics


def enhanced_trade(base,sc,i,side,end,model,kind,threshold):
    natural=dyn.one_trade(base,sc,i,side,end,dyn.POLICIES["fixed_2p5"])
    if natural is None:
        return None
    first=natural["entry_idx"]+1
    last=natural["exit_idx"]
    if first>last:
        return natural
    X=np.vstack([state(base,sc,i,j,side,kind) for j in range(first,last+1)])
    probs=model.predict_proba(X)[:,1]
    hits=np.flatnonzero(probs>=threshold)
    if not len(hits):
        return natural
    idx=first+int(hits[0])
    clone=dict(natural)
    clone["exit_idx"]=idx
    clone["exit_ms"]=int(base["t"][idx])
    clone["exit"]=float(base["op"][idx])
    clone["net"]=float(side*(clone["exit"]/clone["entry"]-1)-COST)
    clone["hold_hours"]=4*(idx-clone["entry_idx"])
    clone["reason"]="model_early_exit"
    clone["realized"]=True
    clone["exit_prob"]=round(float(probs[hits[0]]),3)
    return clone


def simulate(data,kind,model,threshold,start,end,assets=COINS,cost=COST,ledger=False):
    by={}
    alltrades=[]
    reasons=collections.Counter()
    for sym in assets:
        base,scoring_by_mode,signals=data[sym]
        mode="normalized_htf_experiment" if kind=="pine_normalized" else "original"
        sc=scoring_by_mode[mode]
        first=max(dyn.WARMUP,int(np.searchsorted(base["t"],start)))
        stop=min(base["n"],int(np.searchsorted(base["t"],end)))
        next_free=first
        cash=INITIAL
        peak=cash
        dd=0.
        closed=0
        marked=0
        exits_ml=0
        for i,side in signals:
            k=i+1
            if k<first or k>=stop or k<next_free:
                continue
            z=enhanced_trade(base,sc,i,side,stop,model,kind,threshold)
            if z is None:
                continue
            ret=z["net"]-(cost-COST)
            cash+=NOTIONAL*ret
            peak=max(peak,cash)
            dd=max(dd,1-cash/peak)
            next_free=z["exit_idx"]+1
            reasons[z["reason"]]+=1
            if z["realized"]:
                closed+=1
            else:
                marked+=1
            exits_ml+=int(z["reason"]=="model_early_exit")
            if ledger:
                alltrades.append(dict(symbol=sym,entry_utc=dyn.iso(z["entry_ms"]),
                    exit_utc=dyn.iso(z["exit_ms"]),side=side,
                    net_nominal_pct=round(100*ret,4),cash_pnl=round(NOTIONAL*ret,2),
                    status="realized" if z["realized"] else "unrealized_fold_boundary",
                    reason=z["reason"],exit_probability=z.get("exit_prob"),
                    hold_hours=z["hold_hours"]))
            if not z["realized"]:
                break
        by[sym]=dict(closed=closed,boundary_marks=marked,ml_exits=exits_ml,
            return_pct=round(100*(cash/INITIAL-1),4),
            drawdown_closed_and_boundary_pct=round(100*dd,4))
    vals=[z["return_pct"] for z in by.values()]
    result=dict(summary=dict(assets=len(by),closed_trades=sum(v["closed"] for v in by.values()),
       model_early_exits=sum(v["ml_exits"] for v in by.values()),
       boundary_marks=sum(v["boundary_marks"] for v in by.values()),
       mean_pct=round(float(np.mean(vals)),4),
       median_pct=round(float(np.median(vals)),4),
       worst_pct=round(float(min(vals)),4),
       positive_assets=sum(v>0 for v in vals),
       average_closed_and_boundary_dd_pct=round(float(np.mean([
          v["drawdown_closed_and_boundary_pct"] for v in by.values()])),4)),
       by_coin=by,reason_counts=dict(reasons))
    if ledger:
        result["trades"]=alltrades
    return result


def quality(res):
    m=res["summary"]
    if m["closed_trades"]<48:
        return -1000.+m["closed_trades"]*.01
    return .50*m["mean_pct"]+.28*m["worst_pct"]+.17*m["median_pct"]-.16*m["average_closed_and_boundary_dd_pct"]


def select_threshold(data,kind,model,trainend,assets=COINS):
    results=[]
    for th in THRESHOLDS:
        res=simulate(data,kind,model,th,0,trainend,assets=assets)
        results.append(dict(threshold=th,score=round(quality(res),4),summary=res["summary"]))
    results.sort(key=lambda z:z["score"],reverse=True)
    return float(results[0]["threshold"]),results


def paired(a,b):
    names=list(a["by_coin"])
    diffs={sym:round(a["by_coin"][sym]["return_pct"]-
                     b["by_symbol"][sym]["return_pct"],4)
           for sym in names}
    return dict(mean_gain_pp=round(float(np.mean(list(diffs.values()))),4),
                better_assets=sum(v>0 for v in diffs.values()),
                differences=diffs)


def evaluate_feature_set(data,kind,exclude_loo=False):
    baseline_original=dyn.simulate(data,"original","fixed_2p5",CAL_END,VAL1_END)
    model_a,diag_a=fit(data,kind,CAL_END)
    th_a,th_a_rank=select_threshold(data,kind,model_a,CAL_END)
    val1=simulate(data,kind,model_a,th_a,CAL_END,VAL1_END,ledger=True)
    base1=dyn.simulate(data,"original","fixed_2p5",CAL_END,VAL1_END)
    model_b,diag_b=fit(data,kind,VAL1_END)
    th_b,th_b_rank=select_threshold(data,kind,model_b,VAL1_END)
    val2=simulate(data,kind,model_b,th_b,VAL1_END,VAL2_END,ledger=True)
    base2=dyn.simulate(data,"original","fixed_2p5",VAL1_END,VAL2_END)
    stressed=simulate(data,kind,model_b,th_b,VAL1_END,VAL2_END,cost=STRESS)
    inspected=simulate(data,kind,model_b,th_b,VAL2_END,FOREVER)
    transfer={}
    if not exclude_loo:
        for sym in COINS:
            held=(sym,)
            mdl,diag=fit(data,kind,VAL1_END,exclude=held)
            trainco=tuple(s for s in COINS if s!=sym)
            threshold,ranks=select_threshold(data,kind,mdl,VAL1_END,assets=trainco)
            v=simulate(data,kind,mdl,threshold,VAL1_END,VAL2_END,assets=held)
            baseline=dyn.simulate(data,"original","fixed_2p5",VAL1_END,VAL2_END,coins=held)
            transfer[sym]=dict(threshold=threshold,
                model=v["summary"],control=baseline["summary"],
                difference=paired(v,baseline))
    return dict(features=kind,
        phase_A=dict(train_cutoff=dyn.iso(CAL_END),train=diag_a,
           chosen_probability_threshold=th_a,threshold_search_on_train=th_a_rank,
           next_validation=val1,control=base1,improvement=paired(val1,base1)),
        phase_B=dict(train_cutoff=dyn.iso(VAL1_END),train=diag_b,
           chosen_probability_threshold=th_b,threshold_search_on_train=th_b_rank,
           next_validation=val2,control=base2,double_cost=stressed,
           improvement=paired(val2,base2)),
        leave_one_asset_out=transfer,
        inspected_aug_oct_diagnostic=inspected["summary"])


def main():
    data,sources=dyn.load()
    report=dict(title="XGBoost dynamic early exit during trade: does original Pine scoring improve DeltaRSI only model?",
       run_id=os.environ.get("GITHUB_RUN_ID","local"),
       sha=os.environ.get("GITHUB_SHA","local"),
       coins=COINS,raw_sources=sources,
       baseline="Original fixed 2.5 ATR SL/TP + opposite DeltaRSI medium->weak signal, next-open orders",
       entry="All original strict DeltaRSI medium->weak signals, never fitted or filtered",
       supervision=dict(label="At each next OPEN, would exit beat eventual fixed-baseline exit by >=0.45 entry ATR?",
         hindsight_labels_train_only=True,exclude_censored_baseline_trades=True,
         exclude_any_trade_exiting_after_train_cut=True,
         labels_not_realized_exit_strategy="baseline trade counterfactual, heuristic, not optimal stopping oracle",
         trade_balanced_weight=True),
       decision_inputs="Only past CLOSED 4h and previous completed daily Pine REGIME features",
       scoring_source=dyn.scoring.PINE_REF,
       feature_sets=FEATURE_SETS,
       chronological_train=[dyn.iso(CAL_END),dyn.iso(VAL1_END)],
       forward_validation=[dyn.iso(VAL1_END),dyn.iso(VAL2_END)],
       fee_roundtrip=COST,double_fee=STRESS,
       position_notional=NOTIONAL,starting_equity=INITIAL,
       no_48h_holding_limit=True,real_orders=False,
       inspected_aug_oct_not_used_for_model_selection=True,
       results={},
       caveats=[
         "ML label is a hindsight advantage versus baseline exit, not an unbiased optimal exit or a guarantee of profits",
         "Baseline trajectories are used for supervision; policy distribution shift arises when ML exits earlier and allows new entries",
         "Train and threshold selection only use dates before chronological cutoff; Aug-Oct already inspected and diagnostic only",
         "XGB probabilities are NOT calibrated event probabilities; tested thresholds selected on earlier TRAINING equity",
         "Trades/bars share data, class weights and multiple feature experiments create selection bias; future genuine OOS still required",
         "Conservative daily context is last fully closed UTC day; exact Pine numerical parity not verified",
         "Original Pine REGIME mode has unreachable MATURE/AGING categories; normalized mode is an explicit research counterfactual",
         "No intrabar/tick equity for Upscale, fees approximated, funding and slippage excluded, all accounts per-coin",
         "Retired TONUSDT censored before 2026-06-23, not mixed with separately listed GRAMUSDT",
         "Manual trades excluded, no live order execution",
       ])
    for kind in FEATURE_SETS:
        res=evaluate_feature_set(data,kind,exclude_loo=(kind!="pine_normalized"))
        report["results"][kind]=res
        print("DYNAMIC_EXIT_ML",json.dumps(dict(features=kind,
            training_A=res["phase_A"]["train"],
            training_B=res["phase_B"]["train"],
            threshold_a=res["phase_A"]["chosen_probability_threshold"],
            threshold_b=res["phase_B"]["chosen_probability_threshold"],
            val_a=res["phase_A"]["next_validation"]["summary"],
            control_a=res["phase_A"]["control"]["summary"],
            gain_a=res["phase_A"]["improvement"],
            val_b=res["phase_B"]["next_validation"]["summary"],
            control_b=res["phase_B"]["control"]["summary"],
            gain_b=res["phase_B"]["improvement"],
            cost_b=res["phase_B"]["double_cost"]["summary"],
            transfer={sym:z["difference"] for sym,z in res["leave_one_asset_out"].items()}),
            ensure_ascii=False),flush=True)
    (ROOT/"DYNAMIC_EXIT_XGB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    lines=["# XGBoost: когда закрывать DeltaRSI-позицию по меняющемуся рынку","",
       "Только исследование, реальные ордера не отправляются. GitHub run: "+report["run_id"],
       "Входы строго medium→weak; начальный стоп и тейк по 2.5 ATR, противоположный сигнал сохраняется.",
       "XGBoost может досрочно закрыть позицию только на следующем открытии 4h после закрытого бара.",
       "Нет ограничения удержания 48 часов. Дневные признаки берутся из уже завершённого предыдущего дня.",
       "Обучение использует hindsight-метку: лучше ли выйти сейчас, чем дождаться БАЗОВОГО выхода (+0.45 ATR).",
       "Это НЕ оптимальная policy, а проверяемая конкретная гипотеза об exits.",
       "",
       "| Набор признаков | Вал1 ML | Контроль | Вал2 ML | Контроль |",
       "|---|---:|---:|---:|---:|"]
    for kind,z in report["results"].items():
        a=z["phase_A"];b=z["phase_B"]
        lines.append(f"| {kind} | {a['next_validation']['summary']['mean_pct']:+.3f}% | "
          f"{a['control']['summary']['average_asset_pct']:+.3f}% | "
          f"{b['next_validation']['summary']['mean_pct']:+.3f}% | "
          f"{b['control']['summary']['average_asset_pct']:+.3f}% |")
    lines+=["","## Что важно","",
       "Сравнение delta_only vs pine_original vs pine_normalized изолирует добавочную ценность рыночного скоринга при одинаковых DeltaRSI входах.",
       "В JSON сохранены признаки обучения, числа положительных/отрицательных меток, пороги, все решения в валидациях, двойная комиссия и перенос на исключаемые монеты.",
       "Результаты август–октябрь НЕ используются для выбора модели (период давно просмотрен).",
       "Тест не доказывает пригодность для Upscale: нет полной equity DD и tick-level исполнения.",
       "Ни один скоринговый фильтр/ML-выход не заменяет старые зафиксированные форвард-правила без нового независимого теста."]
    (ROOT/"DYNAMIC_EXIT_XGB_REPORT.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
