"""Market Regime Signal Scoring Pine -> DeltaRSI cross-asset entry/exit ablation.

Compare: original REGIME scale vs explicitly normalized higher-timeframe
variant (the original HTF score <= 2.0 cannot reach the 2.6 threshold).
No rewrites of DeltaRSI, frozen individual policies, or previous reports.

All decisions use CLOSED 4h signals, previous FULL daily bar, next 4h open.
Training uses completed trades before cutoffs; validation never trains on
future labels. 2026 Aug-Oct already inspected: diagnostic ONLY.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import itertools
import json
import os
from pathlib import Path

import numpy as np

import research_rules as rr
import pine_market_scoring_features as scoring
from train import ROOT,features

ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT",
        "ICPUSDT","ZECUSDT","TONUSDT")
TON_END=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
CAL_END=rr.DATE_A
VAL1_END=rr.DATE_B
VAL2_END=rr.CUT
FOREVER=2**62
REGIMES=scoring.REGIME_LABELS
ENTRY_GATES=("all","local_align","daily_align","dual_align",
    "score_2p5","score_3p2","fresh_or_mature","no_conflict_sleeping",
    "conflict_or_aging")
EXIT_PROFILES={
    "equal_atr":("strict",2.5,2.5,(0.,0.),"reverse_fade"),
    "tight_atr":("strict",1.5,2.5,(0.,0.),"reverse_fade"),
    "wide_atr":("strict",4.0,5.0,(0.,0.),"reverse_fade"),
    "zero_trail":("strict",2.5,0.,(3.,1.5),"zero_cross"),
    "wide_zero":("strict",4.0,5.0,(3.,1.5),"zero_cross"),
    "risk_only_trail":("strict",2.5,2.5,(3.,1.5),"risk_only"),
}
INITIAL_USD=5000.
NOTIONAL_USD=840.
COST_RT=.0018
COST_STRESS=.0036


def iso(t):
    return dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).isoformat()


def load():
    assets={}
    audits={}
    for sym in ASSETS:
        p=ROOT/"data"/(sym+".json")
        if not p.is_file():
            raise FileNotFoundError(f"Missing immutable market cache: {p}")
        raw=p.read_bytes()
        rows=json.loads(raw)
        removed=0
        if sym=="TONUSDT":
            removed=sum(r[0]>=TON_END for r in rows)
            if removed<700:
                raise RuntimeError("Expected old TON delisting placeholders absent; inspect data")
            rows=[r for r in rows if r[0]<TON_END]
        if len(rows)<3000 or any(b[0]-a[0]!=4*3600000 for a,b in zip(rows,rows[1:])):
            raise RuntimeError(f"{sym}: too few or non-contiguous 4h bars")
        rr_arrays=rr.make_arrays(features(rows,sym))
        # Audit score prefix stability for no future leakage.
        scoring.audit_no_future(rows,spots=(1100,2450,3850))
        variants={
            "original":scoring.scoring_features(rows,False),
            "normalized_htf_experiment":scoring.scoring_features(rows,True),
        }
        assets[sym]=(rows,rr_arrays,variants)
        audits[sym]=dict(first=iso(rows[0][0]),last=iso(rows[-1][0]),
            bars=len(rows),removed_delisted_ton_rows=removed,
            source_sha256=hashlib.sha256(raw).hexdigest())
    return assets,audits


def records(assets,variant):
    all_events={}
    occupancy={}
    for sym,(rows,d,variants) in assets.items():
        sc=variants[variant]
        signals=rr.candidates(d,"strict")  # user-defined medium -> weak only
        res=[]
        states=collections.Counter(sc.regime)
        occupancy[sym]=dict(total=len(sc),count=dict(states),
            unreachable_labels=[x for x in ("MATURE TREND","AGING TREND") if states.get(x,0)==0],
            raw_higher_tf_max=round(float(variants["original"].score_higher_tf.max()),4),
            observed_higher_tf_max=round(float(sc.score_higher_tf.max()),4))
        for i,side in signals:
            if i+1>=d["n"]-1:
                continue
            v=sc.iloc[i]
            outcomes={}
            for style,params in EXIT_PROFILES.items():
                trade=rr.trade(d,i,side,d["n"],params)
                if trade is None or trade["reason"]=="evaluation_boundary":
                    continue
                outcomes[style]=dict(entry_ms=int(trade["entry_ms"]),
                   exit_ms=int(trade["exit_ms"]),net=float(trade["ret"]),
                   hold_h=trade["hold_hours"],reason=trade["reason"])
            res.append(dict(symbol=sym,side=int(side),i=i,
               entry_ms=int(d["t"][i+1]),regime=str(v.regime),
               short_term_bias=str(v.bias_short_term),daily_bias=str(v.bias_higher_tf),
               score=float(v.composite),short_score=float(v.score_short_term),
               daily_score=float(v.score_higher_tf),outcomes=outcomes))
        all_events[sym]=res
    return all_events,occupancy


def gate(event,name):
    direction="UP" if event["side"]==1 else "DOWN"
    local=event["short_term_bias"]==direction
    daily=event["daily_bias"]==direction
    regime=event["regime"]
    if name=="all":return True
    if name=="local_align":return local
    if name=="daily_align":return daily
    if name=="dual_align":return local and daily
    if name=="score_2p5":return event["score"]>=2.5
    if name=="score_3p2":return event["score"]>=3.2
    if name=="fresh_or_mature":return regime in ("FRESH MOVE","MATURE TREND")
    if name=="no_conflict_sleeping":return regime not in ("CONFLICT","SLEEPING")
    if name=="conflict_or_aging":return regime in ("CONFLICT","AGING TREND")
    raise ValueError(name)


def fit_exit(events,until,excluded=()):
    excluded=set(excluded)
    result={}
    diagnostics={}
    for r,side in itertools.product(REGIMES,(-1,1)):
        cohort=[e for sym,evs in events.items() if sym not in excluded
                for e in evs if e["regime"]==r and e["side"]==side
                and e["entry_ms"]<until]
        entries=[]
        for name in EXIT_PROFILES:
            finished=[(e,e["outcomes"][name]) for e in cohort
                 if name in e["outcomes"] and e["outcomes"][name]["exit_ms"]<until]
            source_coins=set(e["symbol"] for e,_ in finished)
            if len(finished)<15 or len(source_coins)<3:
                continue
            values=np.array([z["net"] for _,z in finished],dtype=float)
            n=len(values)
            coverage=n/max(1,len(cohort))
            # Do not select exit profiles that improve their mean by
            # leaving most signals open at training fold boundary.
            score=(.55*np.mean(values)+.35*np.quantile(values,.20)+
                   .10*np.median(values))*100-2*(1-coverage)
            score-=.0004*np.median([z["hold_h"] for _,z in finished])
            if name=="equal_atr":score+=.10
            entries.append(dict(name=name,score=round(float(score),5),
              trades=n,distinct_coins=len(source_coins),
              mean_pct=round(100*float(np.mean(values)),3),
              loss_tail_p20=round(100*float(np.quantile(values,.2)),3),
              coverage=round(coverage,3)))
        entries.sort(key=lambda v:v["score"],reverse=True)
        chosen=entries[0]["name"] if entries else "equal_atr"
        result[(r,side)]=chosen
        diagnostics[f"{r}:{'LONG' if side>0 else 'SHORT'}"]=dict(
            profile=chosen,events=len(cohort),eligible=entries)
    return result,diagnostics


def simulate(events,gate_name,exit_map,start,end,assets=None,cost=COST_RT,
             with_ledger=False):
    coins=assets or ASSETS
    by={}
    regimes=collections.defaultdict(lambda:dict(trades=0,profit=0.))
    ledger=[]
    for sym in coins:
        cash=INITIAL_USD
        peak=INITIAL_USD
        maxdd=0.
        next_free=start
        trades=0
        censored=0
        for e in events.get(sym,()):
            if not(start<=e["entry_ms"]<end):
                continue
            if e["entry_ms"]<next_free or not gate(e,gate_name):
                continue
            style=exit_map[(e["regime"],e["side"])]
            x=e["outcomes"].get(style)
            if x is None:
                censored+=1
                continue
            if x["exit_ms"]>=end:
                # Trade spans boundary. It remains open and consumes the
                # slot. Do not count unknown future realized PnL.
                next_free=x["exit_ms"]+1
                censored+=1
                continue
            ret=x["net"]-(cost-COST_RT)
            cash+=NOTIONAL_USD*ret
            peak=max(peak,cash)
            maxdd=max(maxdd,1-cash/peak)
            trades+=1
            next_free=x["exit_ms"]+1
            bucket=e["regime"]+(" LONG" if e["side"]>0 else " SHORT")
            regimes[bucket]["trades"]+=1
            regimes[bucket]["profit"]+=NOTIONAL_USD*ret
            if with_ledger:
                ledger.append(dict(symbol=sym,entry_utc=iso(e["entry_ms"]),
                    exit_utc=iso(x["exit_ms"]),side=e["side"],regime=e["regime"],
                    local_bias=e["short_term_bias"],daily_bias=e["daily_bias"],
                    composite=round(e["score"],3),exit_profile=style,
                    pnl_usd=round(NOTIONAL_USD*ret,2),pnl_nominal_pct=round(100*ret,3),
                    hold_hours=x["hold_h"],reason=x["reason"]))
        by[sym]=dict(trades=trades,censored_boundary=censored,
            return_pct=round(100*(cash/INITIAL_USD-1),3),
            realized_dd_pct=round(100*maxdd,3))
    allreturns=[v["return_pct"] for v in by.values()]
    ntrades=sum(v["trades"] for v in by.values())
    out=dict(summary=dict(assets=len(by),trades=ntrades,
        mean_asset_return_pct=round(float(np.mean(allreturns)),3),
        median_asset_return_pct=round(float(np.median(allreturns)),3),
        worst_asset_return_pct=round(float(min(allreturns)),3),
        assets_profitable=sum(v>0 for v in allreturns),
        mean_realized_dd_pct=round(float(np.mean([v["realized_dd_pct"] for v in by.values()])),3)),
        by_asset=by,
        by_regime={k:dict(trades=z["trades"],account_cash_pnl_usd=round(z["profit"],2))
                  for k,z in regimes.items()})
    if with_ledger:out["trades"]=ledger
    return out


def choose_gate(events,exit_map,start,end,excluded=()):
    selected=[sym for sym in ASSETS if sym not in set(excluded)]
    trials=[]
    for name in ENTRY_GATES:
        result=simulate(events,name,exit_map,start,end,assets=selected)
        z=result["summary"]
        if z["trades"]<55 or sum(v["trades"]>=4 for v in result["by_asset"].values())<5:
            score=-1000+z["trades"]*.001
        else:
            score=(.45*z["mean_asset_return_pct"]+
                .3*z["median_asset_return_pct"]+
                .30*z["worst_asset_return_pct"]-
                .15*z["mean_realized_dd_pct"])
            if name=="all":score+=.4
        trials.append(dict(name=name,score=round(float(score),4),metrics=z))
    trials.sort(key=lambda x:x["score"],reverse=True)
    return trials[0]["name"],trials


def evaluate_variant(events,name):
    a,stats_a=fit_exit(events,CAL_END)
    gate_a,rank_a=choose_gate(events,a,0,CAL_END)
    val_a=simulate(events,gate_a,a,CAL_END,VAL1_END,with_ledger=True)
    fixed_map={(r,s):"equal_atr" for r,s in itertools.product(REGIMES,(-1,1))}
    fixed_a=simulate(events,"all",fixed_map,CAL_END,VAL1_END)
    gated_fixed_a=simulate(events,gate_a,fixed_map,CAL_END,VAL1_END)

    b,stats_b=fit_exit(events,VAL1_END)
    gate_b,rank_b=choose_gate(events,b,0,VAL1_END)
    val_b=simulate(events,gate_b,b,VAL1_END,VAL2_END,with_ledger=True)
    fixed_b=simulate(events,"all",fixed_map,VAL1_END,VAL2_END)
    gated_fixed_b=simulate(events,gate_b,fixed_map,VAL1_END,VAL2_END)
    adapt_all_b=simulate(events,"all",b,VAL1_END,VAL2_END)
    stress_b=simulate(events,gate_b,b,VAL1_END,VAL2_END,cost=COST_STRESS)

    loo={}
    for sym in ASSETS:
        cross,exit_diag=fit_exit(events,VAL1_END,excluded=(sym,))
        cross_gate,cross_trials=choose_gate(events,cross,0,VAL1_END,excluded=(sym,))
        outcome=simulate(events,cross_gate,cross,VAL1_END,VAL2_END,assets=[sym])
        benchmark=simulate(events,"all",fixed_map,VAL1_END,VAL2_END,assets=[sym])
        loo[sym]=dict(gate=cross_gate,profile_by_regime={
            f"{r}:{'L' if s>0 else 'S'}":style for (r,s),style in cross.items()},
            model=outcome["summary"],baseline=benchmark["summary"])
    inspected=simulate(events,gate_b,b,VAL2_END,FOREVER,with_ledger=True)
    inspected_fixed=simulate(events,"all",fixed_map,VAL2_END,FOREVER)
    return dict(mode=name,
        phase_A=dict(train_through=iso(CAL_END),selected_gate=gate_a,
            ranked_gates=rank_a,exits=stats_a,
            validation=dict(model=val_a,ungated_fixed=fixed_a,gated_fixed=gated_fixed_a)),
        phase_B=dict(train_through=iso(VAL1_END),selected_gate=gate_b,
            ranked_gates=rank_b,exits=stats_b,
            validation=dict(model=val_b,ungated_fixed=fixed_b,
                gated_fixed=gated_fixed_b,adaptive_exits_all=adapt_all_b,
                double_cost_model=stress_b)),
        leave_one_asset_out=loo,
        inspected_aug_oct=dict(model=inspected,ungated_fixed=inspected_fixed))


def main():
    rr.COST_RT=COST_RT
    assets,audits=load()
    results={}
    regime_counts={}
    sample_sizes={}
    for mode in ("original","normalized_htf_experiment"):
        events,occupancy=records(assets,mode)
        regime_counts[mode]=occupancy
        sample_sizes[mode]={k:len(v) for k,v in events.items()}
        results[mode]=evaluate_variant(events,mode)
        a=results[mode]["phase_A"]
        b=results[mode]["phase_B"]
        print("PINE_SCORING_RESULT",json.dumps(dict(mode=mode,
            scoring_max_on_4h=max(v["observed_higher_tf_max"] for v in occupancy.values()),
            used_regimes={s:sum(v["count"].get(s,0) for v in occupancy.values()) for s in REGIMES},
            chosen_gate_A=a["selected_gate"],chosen_gate_B=b["selected_gate"],
            first_validation={k:v["summary"] for k,v in a["validation"].items()},
            second_validation={k:v["summary"] for k,v in b["validation"].items()},
            transfer={k:v["model"] for k,v in results[mode]["leave_one_asset_out"].items()}),
            ensure_ascii=False),flush=True)
    output=dict(title="Original user Pine Market Regime scoring vs normalized-scale counterfactual on DeltaRSI",
      run_id=os.environ.get("GITHUB_RUN_ID","local"),
      sha=os.environ.get("GITHUB_SHA","local"),
      sources=audits,
      pine_source=scoring.PINE_REF,
      pine_blob_sha=scoring.PINE_BLOB_SHA,
      pine_mode="REGIME only; default SCALP mode not part of this experiment",
      indicator_signal="ORIGINAL DeltaRSI strict medium→weak from existing train.py; do not replace",
      financial_costs=dict(per_round_trip=COST_RT,stress_per_round_trip=COST_STRESS,
                           initial_account_usd=INITIAL_USD,fixed_nominal_usd=NOTIONAL_USD),
      temporal=dict(calibration_end=iso(CAL_END),validation1_end=iso(VAL1_END),
                    validation2_end=iso(VAL2_END),aug_oct_already_inspected=True),
      methodology=dict(
          previous_completed_daily_bars_only=True,
          original_regime_mode_daily_max=2.0,
          original_regime_hi_l_threshold=2.6,
          mature_and_aging_unreachable_in_original=True,
          normalized_htf_scale=2.5,
          labels=REGIMES,
          exit_profile_candidates=list(EXIT_PROFILES),
          entry_gate_candidates=list(ENTRY_GATES),
          entry_gate_selected_from_earlier_period_only=True,
          exit_profiles_fitted_only_to_completed_trade_exits_before_cutoff=True,
          leave_one_asset_out=True,
          manually_executed_trades_included=False,
          lookahead_prefix_tests=True,
          no_48_hour_cap=True,
          intraday_fill="next 4h open; stop-first OHLC",
      ),
      event_counts=sample_sizes,regime_occupancy=regime_counts,
      results=results,
      caveats=[
        "Pine REGIME scoring source's daily maximum 2.0 vs MATURE/AGING threshold 2.6 makes both labels unreachable; normalized variant is explicitly NOT literal Pine",
        "Python Wilder RMA initialization uses EWM min-periods, may differ from Pine SMA-seeded ta.rma; exact numerical parity NOT claimed",
        "HTF value uses prior fully closed UTC daily candle even on current day's final 4h candle; conservatively avoids partial daily leakage",
        "Only original Pine REGIME branch ported; default SCALP and separate RSI/MACD signal stack NOT part of this analysis",
        "Historical cross-validation and asset choice previously seen, not virgin OOS; no threshold tuning on Aug-Oct",
        "Exit profile learning from overlapping hypothetical events can overfit; only deployed sequentially in out-of-sample simulation",
        "No shared multi-position account, no 1h/tick execution or full Upscale prop-risk compliance",
        "TONUSDT delisted 2026-06-23, future placeholder bars stripped. GRAMUSDT not used to train due to short history",
        "Fees 0.18% roundtrip, double stress 0.36%; no funding",
        "Neither ML nor regime score is a live trading recommendation; retain previously frozen individual strategies",
      ])
    (ROOT/"PINE_MARKET_SCORING_STUDY.json").write_text(json.dumps(output,ensure_ascii=False,indent=2))
    lines=["# DeltaRSI + твой оригинальный Market Regime Signal Scoring Model","",
        f"Исходный Pine: {output['pine_source']} (blob SHA {output['pine_blob_sha']})",
        "Сравниваем original REGIME и явно нормализованный HTF вариант (2.5× для HTF 0..2).",
        "По умолчанию оригинальный индикатор работает в SCALP; здесь портирован только режим REGIME.",
        "Промежуточная незакрытая дневная свеча исключена: для 4h решений используется предыдущий завершённый день.",
        "DeltaRSI medium→weak и исполнение без lookahead и 48-часового ограничения сохранены.","",
        "## Критическая ошибка диапазона в исходном Pine","",
        "score_long_regime=0.6*slope_cons+0.8*ema_pos+0.6*atr_exp, максимум 2.0.",
        "Условие hi_l=score_long>=2.6 невыполнимо, состояния MATURE TREND и AGING TREND в REGIME недостижимы.",
        "Второй вариант — ИССЛЕДОВАТЕЛЬСКОЕ масштабирование, а не незаметное изменение Pine.","",
        "## Хронологические валидации","",
        "| Вариант | Вход в 1-й тест | Regime 1-й тест | Fixed 1-й тест | Вход во 2-й тест | Regime 2-й тест | Fixed 2-й тест |",
        "|---|---|---:|---:|---|---:|---:|"]
    for mode,z in results.items():
        x=z["phase_A"];y=z["phase_B"]
        v1=x["validation"];v2=y["validation"]
        lines.append(f"| {mode} | {x['selected_gate']} | "
           f"{v1['model']['summary']['mean_asset_return_pct']:+.3f}% | "
           f"{v1['ungated_fixed']['summary']['mean_asset_return_pct']:+.3f}% | "
           f"{y['selected_gate']} | "
           f"{v2['model']['summary']['mean_asset_return_pct']:+.3f}% | "
           f"{v2['ungated_fixed']['summary']['mean_asset_return_pct']:+.3f}% |")
    lines+=["","В JSON отдельно сохранены gated fixed exit, adaptive exit with all entries и double-cost stress.",
        "Полные карты выходов по контексту, сделкам и монетам — в JSON; эти результаты нельзя оптимизировать по просмотренным август—октябрь.",
        "Для проверки переноса каждая монета последовательно исключалась из выбора и обучения правил.",
        "Этот тест пока не подтверждает проп-лимиты, funding или реальное исполнение.",
        "### Исследовательские ограничения","",
        "Exact Pine parity не доказана: отличаются SMA-seed RMA и консервативное использование предыдущего дня для HTF.",
        "Выходы определяются режимом на СИГНАЛЬНОЙ свече, а не динамической сменой режима внутри позиции. Это отдельный следующий эксперимент.",
        "Новых торговых ордеров не было."]
    (ROOT/"PINE_MARKET_SCORING_STUDY.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
