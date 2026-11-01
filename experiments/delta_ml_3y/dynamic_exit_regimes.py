"""Dynamic DeltaRSI exits responding to CHANGING market conditions during trades.

Controlled experiment: fixed strict DeltaRSI entry (same color medium->weak),
same 2.5 ATR initial stop; compare predeclared live-updated exit policies.
The user's Pine Market Regime REGIME numeric scores are recomputed after
EVERY fully closed 4h bar, with ONLY the PREVIOUS FULL UTC daily bar.

Causal execution: entry next bar OPEN; exit from previously closed bar next
OPEN; OHLC stop-first when both stop and target touched. Dynamic trailing
updates after CLOSE and only affects the NEXT bar. No 48h time exit.
Separate original and normalized (experimental) Pine score variants.
Train rules on 2023-11..2025-06, test July2025..Jan2026; reselect using
pre-Feb2026, test Feb..July2026. Aug..Oct2026 ALREADY INSPECTED: diagnose only.
Retired TONUSDT is censored before 2026-06-23 08:00 UTC.
No real orders, no model retraining or live prop compliance.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

import research_rules as rules
import pine_market_scoring_features as scoring
from train import ROOT, features

COINS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT","ICPUSDT","ZECUSDT","TONUSDT")
TON_END=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
CAL_END=rules.DATE_A
VAL1_END=rules.DATE_B
VAL2_END=rules.CUT
FOREVER=2**62
WARMUP=1250
COST=0.0018
COST_DOUBLE=0.0036
INITIAL_USD=5000.
NOMINAL_USD=840.
STEP=4*3600000
MODES=("original","normalized_htf_experiment")
POLICIES={
 "fixed_2p5":dict(tp=2.5,signal=True,score=False,bias=False,conflict=False,shock=False,trail=False),
 "fixed_5":dict(tp=5.,signal=True,score=False,bias=False,conflict=False,shock=False,trail=False),
 "score_profit":dict(tp=2.5,signal=True,score=True,bias=False,conflict=False,shock=False,trail=False),
 "bias_flip":dict(tp=2.5,signal=True,score=False,bias=True,conflict=False,shock=False,trail=False),
 "conflict_protect":dict(tp=2.5,signal=True,score=False,bias=False,conflict=True,shock=False,trail=False),
 "shock_protect":dict(tp=2.5,signal=True,score=False,bias=False,conflict=False,shock=True,trail=False),
 "adaptive_trailing":dict(tp=5.,signal=True,score=False,bias=False,conflict=False,shock=False,trail=True),
 "score_plus_trail":dict(tp=5.,signal=True,score=True,bias=False,conflict=False,shock=False,trail=True),
 "hybrid":dict(tp=5.,signal=True,score=True,bias=True,conflict=True,shock=True,trail=True),
 "runner_no_tp":dict(tp=0.,signal=True,score=True,bias=True,conflict=False,shock=True,trail=True),
}
SIMPLE_CONTROLS=("fixed_2p5","fixed_5")


def iso(t):
    return dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).isoformat()


def load():
    data={}
    sources={}
    for sym in COINS:
        f=ROOT/"data"/(sym+".json")
        if not f.is_file():
            raise FileNotFoundError("Missing historic immutable cached candles: "+str(f))
        raw=f.read_bytes()
        rows=json.loads(raw)
        removed=0
        if sym=="TONUSDT":
            removed=sum(r[0]>=TON_END for r in rows)
            if removed<700:
                raise RuntimeError("TONUSDT missing expected delisted placeholder tail; audit first")
            rows=[r for r in rows if r[0]<TON_END]
        if len(rows)<1500 or any(b[0]-a[0]!=STEP for a,b in zip(rows,rows[1:])):
            raise RuntimeError(sym+" data noncontiguous / too short")
        base=rules.make_arrays(features(rows,sym))
        base["time_index"]={int(t):i for i,t in enumerate(base["t"])}
        scs={mode:scoring.scoring_features(rows,normalize_higher_tf=(mode!="original"))
             for mode in MODES}
        for mode,sc in scs.items():
            if len(sc)!=len(rows):
                raise RuntimeError("Score alignment differs from OHLC data")
        scoring.audit_no_future(rows,spots=(1250,1650,2600,3950))
        signal=rules.candidates(base,"strict")
        data[sym]=(base,scs,signal)
        sources[sym]=dict(rows=len(rows),first=iso(rows[0][0]),last=iso(rows[-1][0]),
                          discarded_ton_placeholder_bars=removed,
                          source_sha256=hashlib.sha256(raw).hexdigest(),
                          strict_signal_count=len(signal))
    return data,sources


def score_exit_trigger(p,base,sc,idx,side,entry_price,atr,entry_regime,entry_score,
                       peak_score,entry_atr_pct):
    """At OPEN of idx use information only through idx-1 (fully closed)."""
    if idx<3:
        return None
    prev=idx-1
    prev2=idx-2
    score_now=float(sc["composite"][prev])
    score_prev=float(sc["composite"][prev2])
    px=float(base["close"][prev])
    profit_at_last_close=side*(px-entry_price)/atr
    opp="DOWN" if side>0 else "UP"
    local=str(sc["bias_short_term"][prev])
    older_local=str(sc["bias_short_term"][prev2])
    daily=str(sc["bias_higher_tf"][prev])
    reg=str(sc["regime"][prev])
    score_fall=max(0.,peak_score-score_now)
    if p["score"] and profit_at_last_close>=0.45 and score_fall>=0.70 and score_now<score_prev-0.10:
        return "market_score_peak_decay"
    if p["bias"] and (local==opp and older_local==opp and score_now>=2.15 or
                      daily==opp and local==opp and score_now>=2.5):
        return "confirmed_direction_flip"
    if p["conflict"] and entry_regime in ("FRESH MOVE","MATURE TREND") and (
            reg in ("CONFLICT","SLEEPING")) and profit_at_last_close>0.30 and (
            score_now+0.20<entry_score):
        return "regime_mature_to_conflict"
    if p["shock"] and entry_atr_pct>0 and prev>=2:
        current_atr_pct=float(base["atr"][prev]/base["close"][prev])
        signed_last_candle=side*(float(base["close"][prev])/
                                float(base["close"][prev2])-1)
        if (current_atr_pct>=1.6*entry_atr_pct and
            signed_last_candle < -0.50*entry_atr_pct and
            (local==opp or daily==opp)):
            return "volatility_shock_against_position"
    if p["signal"] and rules.should_exit(base,idx,side,"reverse_fade"):
        return "opposite_delta_fade"
    return None


def one_trade(base,sc,signal_idx,side,last_exclusive,policy):
    """Exact chronological OHLC state machine. No trade data is used to tune exits."""
    open_idx=signal_idx+1
    n=base["n"]
    if open_idx>=last_exclusive or open_idx>=n:
        return None
    entry=float(base["op"][open_idx])
    atr=float(base["atr"][signal_idx])
    if not(math.isfinite(entry) and entry>0 and math.isfinite(atr) and atr>0):
        return None
    init_stop=entry-side*2.5*atr
    target=entry+side*policy["tp"]*atr if policy["tp"] else None
    if init_stop<=0 or target is not None and target<=0:
        return None
    stop=init_stop
    entry_atr_pct=float(atr/float(base["close"][signal_idx]))
    entry_score=float(sc["composite"][signal_idx])
    entry_regime=str(sc["regime"][signal_idx])
    score_high_water=entry_score
    favorable_closed=entry
    mae=0.
    mfe=0.
    exit_at=None
    reason=None
    exit_idx=None
    trail_activated=False
    changes=0
    for j in range(open_idx,last_exclusive):
        baropen=float(base["op"][j])
        low=float(base["low"][j])
        high=float(base["high"][j])
        # Decision at opening of bar j reads ONLY bar j-1 (already closed).
        # Do not include this bar's future high/low in the trade's MAE/MFE
        # if the position exits immediately at the bar OPEN.
        if j>open_idx:
            reason=score_exit_trigger(policy,base,sc,j,side,entry,atr,
                 entry_regime,entry_score,score_high_water,entry_atr_pct)
            if reason is not None:
                exit_at=baropen
                exit_idx=j
                mae=min(mae,side*(baropen-entry)/atr)
                mfe=max(mfe,side*(baropen-entry)/atr)
                break
        mae=min(mae,side*((low if side>0 else high)-entry)/atr)
        mfe=max(mfe,side*((high if side>0 else low)-entry)/atr)
        # Gap checks happen before this bar's high/low are consulted.
        if (side>0 and baropen<=stop) or (side<0 and baropen>=stop):
            exit_at=baropen
            reason="stop_open_gap"
        elif target is not None and (
                (side>0 and baropen>=target) or (side<0 and baropen<=target)):
            exit_at=target
            reason="target_open_gap_conservative"
        elif ((side>0 and low<=stop) or (side<0 and high>=stop)):
            exit_at=stop
            reason="stop_or_conservative_stop_first"
        elif target is not None and (
                (side>0 and high>=target) or (side<0 and low<=target)):
            exit_at=target
            reason="target"
        if exit_at is not None:
            exit_idx=j
            break
        # After entire bar j has closed we can update score and STOP for bar j+1.
        score_high_water=max(score_high_water,float(sc["composite"][j]))
        if policy["trail"]:
            last_close=float(base["close"][j])
            favorable_closed=max(favorable_closed,last_close) if side>0 else min(favorable_closed,last_close)
            favorable_atr=side*(favorable_closed-entry)/atr
            if favorable_atr>=1.50:
                trail_activated=True
            if trail_activated:
                state=str(sc["regime"][j])
                score_dropped=score_high_water-float(sc["composite"][j])>=0.5
                against=(str(sc["bias_short_term"][j])==("DOWN" if side>0 else "UP"))
                # Loose 2.5 ATR only when strong and aligned; tight 1.0 ATR
                # when trend weakens, with 1.65 ATR intermediate distance.
                if score_dropped or against or state in ("CONFLICT","SLEEPING"):
                    dist=1.0
                elif state in ("FRESH MOVE","MATURE TREND"):
                    dist=2.5
                else:
                    dist=1.65
                proposed=favorable_closed-side*dist*atr
                newstop=max(stop,proposed) if side>0 else min(stop,proposed)
                if newstop!=stop:
                    stop=newstop
                    changes+=1
    if exit_at is None:
        # Boundary mark is NOT executed. It is separately identified as
        # unrealized valuation for comparable episode returns.
        exit_idx=min(last_exclusive,n-1)
        exit_at=float(base["op"][last_exclusive]) if last_exclusive<n else float(base["close"][n-1])
        reason="unrealized_mark_at_fold_boundary"
    net=side*(exit_at/entry-1)-COST
    return dict(entry_idx=open_idx,exit_idx=exit_idx,
        entry_ms=int(base["t"][open_idx]),
        exit_ms=int(base["t"][exit_idx]),side=side,
        entry=entry,exit=float(exit_at),net=float(net),
        gross_atr=round(float(side*(exit_at-entry)/atr),4),
        mae_atr=round(float(mae),3),mfe_atr=round(float(mfe),3),
        hold_hours=4*(exit_idx-open_idx),
        entry_regime=entry_regime,entry_score=round(entry_score,3),
        # Execution at bar OPEN cannot know this bar's closing market score.
        exit_score=round(float(sc["composite"][max(0,min(exit_idx-1,sc.shape[0]-1))]),3),
        score_change=round(float(sc["composite"][max(0,min(exit_idx-1,sc.shape[0]-1))])-entry_score,3),
        stop_updates=changes,reason=reason,
        realized=reason!="unrealized_mark_at_fold_boundary")


def simulate(data,mode,policy_name,start,end,coins=COINS,cost=COST,ledger=False):
    by={}
    reasons=collections.Counter()
    state_flips=collections.Counter()
    trades_all=[]
    for sym in coins:
        base,scs,signals=data[sym]
        sc=scs[mode]
        first=max(WARMUP,int(np.searchsorted(base["t"],start,side="left")))
        finish=int(np.searchsorted(base["t"],end,side="left"))
        finish=min(finish,base["n"])
        next_free=first
        equity=INITIAL_USD
        peak=equity
        dd=0.
        live_mark=0.
        count=0
        marked=0
        for i,side in signals:
            k=i+1
            if k<first or k>=finish or k<next_free:
                continue
            t=one_trade(base,sc,i,side,finish,POLICIES[policy_name])
            if t is None:
                continue
            adjusted=t["net"]-(cost-COST)
            equity+=NOMINAL_USD*adjusted
            peak=max(peak,equity)
            dd=max(dd,1-equity/peak)
            reasons[t["reason"]]+=1
            next_free=t["exit_idx"]+1
            if t["realized"]:
                count+=1
            else:
                marked+=1
                live_mark=NOMINAL_USD*adjusted
            if ledger:
                trades_all.append(dict(symbol=sym,policy=policy_name,
                    entry=iso(t["entry_ms"]),exit=iso(t["exit_ms"]),
                    direction="LONG" if side>0 else "SHORT",
                    return_nominal_pct=round(100*adjusted,4),
                    account_pnl_usd=round(NOMINAL_USD*adjusted,3),
                    realized=t["realized"],exit_reason=t["reason"],
                    entry_regime=t["entry_regime"],entry_score=t["entry_score"],
                    exit_score=t["exit_score"],score_delta=t["score_change"],
                    holding_h=t["hold_hours"],mae_atr=t["mae_atr"],mfe_atr=t["mfe_atr"],
                    trailing_adjustments=t["stop_updates"]))
            if not t["realized"]:
                break
        by[sym]=dict(closed_trades=count,unrealized_at_boundary=marked,
            return_pct=round(100*(equity/INITIAL_USD-1),4),
            realized_closed_and_boundary_mark_dd_pct=round(100*dd,4),
            unrealized_boundary_usd=round(live_mark,3))
    returns=[v["return_pct"] for v in by.values()]
    summary=dict(assets=len(by),closed_trades=sum(v["closed_trades"] for v in by.values()),
       boundary_marks=sum(v["unrealized_at_boundary"] for v in by.values()),
       average_asset_pct=round(float(np.mean(returns)),4),
       median_asset_pct=round(float(np.median(returns)),4),
       worst_asset_pct=round(float(min(returns)),4),
       profitable_assets=sum(v>0 for v in returns),
       average_realized_and_mark_dd_pct=round(float(np.mean([
           z["realized_closed_and_boundary_mark_dd_pct"] for z in by.values()])),4))
    return dict(summary=summary,by_symbol=by,exit_reasons=dict(reasons),
                trades=trades_all if ledger else None)


def measure(stat):
    x=stat["summary"]
    if x["closed_trades"]<48 or sum(v["closed_trades"]>=4 for v in stat["by_symbol"].values())<5:
        return -1000.+0.01*x["closed_trades"]
    return (.46*x["average_asset_pct"]+.21*x["median_asset_pct"]+
            .32*x["worst_asset_pct"]-.14*x["average_realized_and_mark_dd_pct"]+
            (.22 if x["profitable_assets"]>=6 else 0.))


def rank_train(data,mode,training_spans,excluded=()):
    allowed=tuple(s for s in COINS if s not in set(excluded))
    trials=[]
    for policy in POLICIES:
        evaluations=[simulate(data,mode,policy,a,b,coins=allowed) for a,b in training_spans]
        scores=[measure(r) for r in evaluations]
        if min(scores)<=-100:
            value=min(scores)
        else:
            value=.45*min(scores)+.55*float(np.mean(scores))
        if policy in SIMPLE_CONTROLS:
            value+=0.10  # predeclared parsimony preference
        if policy=="hybrid":
            value-=0.05
        trials.append(dict(name=policy,rank=round(value,4),
                     training=[r["summary"] for r in evaluations]))
    trials.sort(key=lambda a:a["rank"],reverse=True)
    return trials[0]["name"],trials


def paired_comparison(model,base):
    x=model["by_symbol"]
    y=base["by_symbol"]
    diffs={sym:round(x[sym]["return_pct"]-y[sym]["return_pct"],4) for sym in x}
    return dict(mean_difference_pp=round(float(np.mean(list(diffs.values()))),4),
      wins_over_baseline=sum(v>0 for v in diffs.values()),
      per_asset_difference_pp=diffs)


def full_ablation(data,mode):
    cal=(0,CAL_END)
    val1=(CAL_END,VAL1_END)
    val2=(VAL1_END,VAL2_END)
    inspected=(VAL2_END,FOREVER)
    chosen_a,ranked_a=rank_train(data,mode,[cal])
    first=simulate(data,mode,chosen_a,*val1,ledger=True)
    baseline1=simulate(data,mode,"fixed_2p5",*val1,ledger=True)
    chosen_b,ranked_b=rank_train(data,mode,[cal,val1])
    second=simulate(data,mode,chosen_b,*val2,ledger=True)
    baseline2=simulate(data,mode,"fixed_2p5",*val2,ledger=True)
    stressed=simulate(data,mode,chosen_b,*val2,cost=COST_DOUBLE)
    # Prespecified isolated differences (on same observed signal sequence,
    # but trade counts may differ due to different exits).
    alternatives={policy:simulate(data,mode,policy,*val2) for policy in POLICIES}
    loo={}
    for excluded in COINS:
        candidate,ranked=rank_train(data,mode,[cal,val1],excluded=(excluded,))
        candidate_result=simulate(data,mode,candidate,*val2,coins=(excluded,))
        control=simulate(data,mode,"fixed_2p5",*val2,coins=(excluded,))
        loo[excluded]=dict(fitted_without_asset=excluded,selected_policy=candidate,
            outcome=candidate_result["summary"],control=control["summary"],
            difference=paired_comparison(candidate_result,control))
    inspected_selected=simulate(data,mode,chosen_b,*inspected)
    inspected_base=simulate(data,mode,"fixed_2p5",*inspected)
    return dict(
        calibration_choice=dict(policy=chosen_a,candidate_ranking=ranked_a),
        first_validation=dict(policy=chosen_a,model=first,
            fixed_baseline=baseline1,
            comparison=paired_comparison(first,baseline1)),
        expanding_choice=dict(policy=chosen_b,candidate_ranking=ranked_b),
        second_validation=dict(policy=chosen_b,model=second,
            fixed_baseline=baseline2,twice_fees=stressed,
            comparison=paired_comparison(second,baseline2),
            all_predeclared_policies={k:v["summary"] for k,v in alternatives.items()}),
        held_out_coin_transfer=loo,
        already_inspected_diagnostic=dict(policy=chosen_b,
            candidate=inspected_selected["summary"],
            fixed_control=inspected_base["summary"]))


def main():
    data,sources=load()
    out=dict(
       title="DeltaRSI dynamic intra-position exit from user's Pine market scoring",
       run_id=os.environ.get("GITHUB_RUN_ID","local"),
       source_sha=os.environ.get("GITHUB_SHA","local"),
       indicator="Executable root Delta Pine: SMA21 of close, Wilder RSI12, EMA7 of RSI, symmetric log Delta; strict medium->weak",
       pine_score_source=scoring.PINE_REF,pine_score_blob_sha=scoring.PINE_BLOB_SHA,
       scoring_methods=MODES,symbols=COINS,source_files=sources,
       starting_equity_usd=INITIAL_USD,nominal_per_position_usd=NOMINAL_USD,
       normal_roundtrip_cost=COST,double_roundtrip_cost=COST_DOUBLE,
       predeclared_policies=POLICIES,
       time_boundaries=dict(calibration_end=iso(CAL_END),
                            validation1_end=iso(VAL1_END),
                            validation2_end=iso(VAL2_END),
                            august_october_previously_inspected=True),
       protocol=dict(
         fixed_entry="strict same-color medium to weak on 4h, no entry gate",
         realtime_features="4h bar CLOSE, plus previous FULL UTC daily bar",
         order_simulation="next 4h OPEN after signal, OHLC stop first, trailing after closed candle",
         initial_stop_atr=2.5,
         no_maximum_holding_hours=True,
         dynamic_exit="evaluate on EVERY completed 4h bar while a position is open",
         evaluation="choose calibration, forward validate 1; reselect calibration+val1, forward validate 2",
         boundary="mark unrealized only, not a real close, no artificial time exit",
         manual_trade_supervision=False,
         future_market_data_used_for_policy_decision=False,
         previously_inspected_aug_oct_used_for_selection=False,
         per_asset_independent=True),
       results={},caveats=[
           "Scores derived from partial Python Pine REGIME port: RMA seed may differ from ta.rma; Daily uses previous fully closed day conservatively",
           "Normalized HTF score is an EXPLICIT experimental change, original HTF max 2.0 makes MATURE and AGING unreachable",
           "Regime mode is not Pine's default SCALP mode, which is NOT used here",
           "Many candidate exit policies were tested; selected rules are exploratory and subject to multiple comparison bias",
           "Backtest may differ from exchange fills, funding and intrabar position equity, NOT verified for Upscale prop limits",
           "All histories except unseen future after Nov 1 already examined in prior research; two chronological folds are not pristine discovery OOS",
           "TONUSDT delisted in June 2026, so its zero-volume archive tail is excluded; GRAM separate and not fit with three-year assets",
           "Closed trades plus marked unrealized ending exposure are included in episode return, tracked separately",
           "Run uses $840 NOTIONAL on $5000 account, one position per asset, not a pooled 3-slot account",
           "No real orders, no live account modifications, no manual trades",
       ])
    for mode in MODES:
        report=full_ablation(data,mode)
        out["results"][mode]=report
        print("DYNAMIC_EXIT_RESULT",json.dumps(dict(mode=mode,
           calibration_policy=report["calibration_choice"]["policy"],
           first_validation=report["first_validation"]["model"]["summary"],
           first_fixed=report["first_validation"]["fixed_baseline"]["summary"],
           first_edge=report["first_validation"]["comparison"],
           expanding_policy=report["expanding_choice"]["policy"],
           second_validation=report["second_validation"]["model"]["summary"],
           second_fixed=report["second_validation"]["fixed_baseline"]["summary"],
           second_edge=report["second_validation"]["comparison"],
           second_double_fee=report["second_validation"]["twice_fees"]["summary"],
           loo={sym:item["difference"]["mean_difference_pp"]
                  for sym,item in report["held_out_coin_transfer"].items()},
           inspected=report["already_inspected_diagnostic"]),ensure_ascii=False),flush=True)
    (ROOT/"DYNAMIC_EXIT_REGIME_REPORT.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
    lines=["# DeltaRSI: динамическое изменение режима во время сделки","",
       "Это отдельный контролируемый эксперимент, не обновление боевого бота или прежних зафиксированных стратегий.",
       "Pine Market Regime Signal Scoring Model: original REGIME и нормализованный HTF-контроль.",
       "Каждая закрытая 4h повторно вычисляет score, конфликт направления и состояние тренда. Результирующие ордера — следующая открытая 4h.",
       "Входы строго DeltaRSI medium→weak, ATR-стоп 2.5; нет лимита 48ч и никаких будущих данных в решениях.",
       "Исторические датасеты взяты из двух GitHub Releases; TON до делистинга.",
       "",
       "| Скоринг | Выбранный на калибровке | Вал1 динамический | Вал1 фиксированный | Выбранный на расширенной истории | Вал2 динамический | Вал2 фиксированный |",
       "|---|---|---:|---:|---|---:|---:|"]
    for mode,r in out["results"].items():
        v1=r["first_validation"];v2=r["second_validation"]
        lines.append(f"| {mode} | {v1['policy']} | {v1['model']['summary']['average_asset_pct']:+.3f}% | "
          f"{v1['fixed_baseline']['summary']['average_asset_pct']:+.3f}% | "
          f"{v2['policy']} | {v2['model']['summary']['average_asset_pct']:+.3f}% | "
          f"{v2['fixed_baseline']['summary']['average_asset_pct']:+.3f}% |")
    lines+=["","## Не считать доказательством без проверки","",
      "Отдельные пробеги без пересекающегося будущего выбираются по калибровке, а затем по калибровке+первой валидации.",
      "Август–октябрь уже просмотрен ранее; не используется для выбора правил.",
      "Для оценки результата надо смотреть ЧИСЛО сделок, перевес по монетам, worst coin и двойные комиссии, не только среднее.",
      "Это тест ДИНАМИЧЕСКИХ ПРАВИЛ, не обучение ML-классификатора. Цифровые признаки и PnL-траектории сохраняются в JSON для следующего ML-исследования.",
      "Выход по режиму считается каждый 4h. Если позиция открыта на конце фолда, она оценивается по рынку и НЕ записывается как фактический выход.",
      "Трейлинг рассчитывается по закрытию 4h и срабатывает не раньше следующей свечи.",
      "Внутрисвечной профиль риска, деньги Upscale, funding и реальные исполнения пока не моделировались.",
      "Все старые результаты и гипотезы сохранены. Никаких живых ордеров нет."]
    (ROOT/"DYNAMIC_EXIT_REGIME_REPORT.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
