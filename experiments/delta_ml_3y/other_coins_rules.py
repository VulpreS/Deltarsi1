"""Per-coin DeltaRSI 4h rule discovery: BTC, BNB, XRP, TON.

Uses IMMUTABLE 3-year Binance Vision candle ZIP from GitHub Release. The
historical windows are ordered chronologically; candidate choice is made
without using Aug-Oct 2026. No manual trades. No 48-hour holding ceiling.

Selection protocol:
 A: choose using calibration only, then evaluate validation 1 (OOS to A)
 B: choose using calibration + validation 1, then evaluate validation 2 (OOS to B)
 C: final PRE-registered candidate using all three PRE-August segments
 D: report inspected Aug-Oct only as contaminated exploratory diagnostic.
Risk and PnL are per-coin $840 fixed notional with $5k initial account, not
a combined portfolio or a validated prop simulation.
"""
import collections
import hashlib
import json
import math
import os
from datetime import datetime, timezone

import numpy as np

import research_rules as rr
from train import ROOT, features

COINS=("BTCUSDT","BNBUSDT","XRPUSDT","TONUSDT")
PERIODS={
    "calibration": (int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000),rr.DATE_A),
    "validation1": (rr.DATE_A,rr.DATE_B),
    "validation2": (rr.DATE_B,rr.CUT),
    "previously_inspected": (rr.CUT,2**62),
}
COST_RT=0.0018
STRESS_RT=0.0036
CAPITAL=5000.
FIXED_NOTIONAL=840.
DIRECTIONS=("both","long_only","short_only")
MIN_COUNTS={"calibration":12, "validation1":4, "validation2":4}
DECISION_CANDLE_LAG=1


def iso(ts):
    return datetime.fromtimestamp(int(ts)/1000,timezone.utc).isoformat()


def parameter_info(p, direction):
    return dict(entry=p[0],direction_filter=direction,
                stop_atr=p[1],take_atr=p[2],
                trailing_activation_atr=p[3][0],
                trailing_distance_atr=p[3][1],exit=p[4],
                max_holding_hours=None)


def make_ledger(d,all_signals,params,direction):
    """One non-overlapping position per asset, carried across fold boundaries.

    The future is read only to simulate execution; NEVER to generate a
    signal or a feature. Future-trade results crossing a fold are never
    eligible for that fold's parameter selection.
    """
    out=[]
    next_free=-1
    for i,side in all_signals[params[0]]:
        if direction=="long_only" and side!=1:
            continue
        if direction=="short_only" and side!=-1:
            continue
        if i+1<next_free:
            continue
        event=rr.trade(d,i,side,d["n"],params)
        if event is None:
            continue
        if event["reason"]=="evaluation_boundary":
            # Open position is NOT a closed trade and not in historical scoring.
            break
        out.append(event)
        finish=int(np.searchsorted(d["t"],event["exit_ms"]))
        next_free=finish+1
    return out


def compute(trades, start, end, cost=COST_RT):
    """Closed-trade results. Do not artificially close a position at a fold."""
    selected=[z for z in trades if start<=z["entry_ms"] and z["exit_ms"]<end]
    selected.sort(key=lambda z:(z["exit_ms"],z["entry_ms"]))
    vals=[z["ret"]-(cost-COST_RT) for z in selected]
    equity=CAPITAL
    peak=CAPITAL
    dd=0.
    returns=[]
    for r in vals:
        equity+=FIXED_NOTIONAL*r
        peak=max(peak,equity)
        dd=max(dd, (peak-equity)/peak if peak>0 else 1.)
        returns.append((FIXED_NOTIONAL/CAPITAL)*r)
    gain=sum(max(r,0.) for r in vals)
    loss=-sum(min(r,0.) for r in vals)
    n=len(vals)
    longs=sum(z["side"]==1 for z in selected)
    shorts=n-longs
    return dict(trades=n,longs=longs,shorts=shorts,
       pnl_pct=round(100*(equity/CAPITAL-1),4),
       dd_closed_pct=round(100*dd,4),
       pf=round(gain/loss,4) if loss else None,
       win_rate=round(sum(r>0 for r in vals)/n,4) if n else None,
       avg_trade_nominal_pct=round(100*np.mean(vals),4) if n else None,
       median_hold_hours=round(float(np.median([z["hold_hours"] for z in selected])),1) if n else None,
       max_hold_hours=max((z["hold_hours"] for z in selected),default=None),
       total_winner_pct=round(100*gain,3),
       total_loser_pct=round(100*loss,3),
       end_cash_usd=round(equity,2),
       exit_reasons=dict(collections.Counter(z["reason"] for z in selected)))


def quality(metrics, minimums):
    if any(metrics[k]["trades"]<minimums.get(k,0) for k in metrics):
        return False
    return True


def score(metrics):
    """Risk-aware, pre-defined, never sees Aug-Oct period."""
    m=list(metrics.values())
    if not m or any(v["trades"]<4 for v in m):
        return -1e6
    pnl=[v["pnl_pct"] for v in m]
    dd=[v["dd_closed_pct"] for v in m]
    # Worst-regime reward and capped outlier gains.
    s=0.58*min(pnl)+0.27*np.mean([max(-60.,min(60.,v)) for v in pnl])
    s-=0.33*max(dd)+0.10*np.mean(dd)
    # Favor genuine dispersion rather than one lucky short-lived trend.
    if len(m)>1:
        s-=0.12*np.std(pnl)
    # A pre-defined small evidence bonus, not a bonus for many churn trades.
    s+=min(1.5,0.015*sum(v["trades"] for v in m))
    if all(v["pnl_pct"]>0 for v in m):
        s+=5.
    return round(float(s),4)


def stable_preaug(met,stress):
    names=("calibration","validation1","validation2")
    return bool(all(met[n]["trades"]>=MIN_COUNTS[n] and
            met[n]["pnl_pct"]>0 and met[n]["dd_closed_pct"]<=15.
            for n in names) and
            all(stress[n]["pnl_pct"]>0 for n in names))


def evaluate_coin(symbol):
    file=ROOT/"data"/(symbol+".json")
    if not file.is_file():
        raise FileNotFoundError(f"Restore cached snapshot; missing {file}")
    raw=file.read_bytes()
    rows=json.loads(raw)
    d=rr.make_arrays(features(rows,symbol))
    assert len(d["t"])==len(rows)
    assert all(int(d["t"][i+1])-int(d["t"][i])==4*3600000 for i in range(len(rows)-1))
    rr.COST_RT=COST_RT
    modes={mode:rr.candidates(d,mode) for mode in rr.ENTRY_MODES}
    records=[]
    for params in rr.grid():
        if params[0]=="strict_divergence":
            # Divergence here means one-bar price high/low breakout; it has
            # NOT been confirmed as a faithful proxy for discretionary divergences.
            continue
        for direction in DIRECTIONS:
            ledger=make_ledger(d,modes,params,direction)
            mets={k:compute(ledger,*period) for k,period in PERIODS.items()}
            stress={k:compute(ledger,*period,cost=STRESS_RT) for k,period in PERIODS.items()
                    if k!="previously_inspected"}
            records.append(dict(params=params,direction=direction,metrics=mets,
                                stress=stress,ledger=ledger))
    pre=[x for x in records if
         x["metrics"]["calibration"]["trades"]>=MIN_COUNTS["calibration"]]
    if not pre:
        raise RuntimeError(f"{symbol}: no sufficient calibration sample")
    def rank_candidate(x,folds):
        mt={fold:x["metrics"][fold] for fold in folds}
        ranks=score(mt)
        insufficient=sum(x["metrics"][fold]["trades"]<MIN_COUNTS[fold] for fold in folds)
        return (ranks-1000*insufficient,
                -int(x["direction"]!="both"),
                -int(x["params"][0]!="strict"),
                -int(x["params"][3][0]>0),
                -int(x["params"][2]==0))
    a=max(pre,key=lambda x:rank_candidate(x,("calibration",)))
    # Second fold is genuinely independent to A's selection.
    b=max(pre,key=lambda x:rank_candidate(x,("calibration","validation1")))
    # Final selection uses all PRE-August folds, never the previously viewed period.
    final=max(pre,key=lambda x:rank_candidate(x,("calibration","validation1","validation2")))
    all_stable=[x for x in pre if stable_preaug(x["metrics"],x["stress"])]
    final_stable=stable_preaug(final["metrics"],final["stress"])
    # If a passed-regime candidate exists, pick best among passing candidates,
    # but mark selection bias (not a virgin OOS proof).
    recommended=(max(all_stable,key=lambda x:rank_candidate(x,
                   ("calibration","validation1","validation2")))
                 if all_stable else final)
    # Conservative benchmark from previously frozen ETH/LINK candidate.
    baseline=next((r for r in records if r["params"]==
       ("strict_trend",2.5,2.5,(0.,0.),"reverse_fade")
       and r["direction"]=="both"),None)
    if not baseline:
        raise RuntimeError("Expected frozen baseline missing")
    def compact(x):
        return dict(rule=parameter_info(x["params"],x["direction"]),
           folds=x["metrics"],double_cost_preaug=x["stress"],
           stable_preaug=stable_preaug(x["metrics"],x["stress"]),
           rank_calibration=score({"calibration":x["metrics"]["calibration"]}),
           rank_first_two=score({k:x["metrics"][k] for k in ("calibration","validation1")}),
           rank_three=score({k:x["metrics"][k] for k in ("calibration","validation1","validation2")}))
    oos_val1=a["metrics"]["validation1"]
    oos_val2=b["metrics"]["validation2"]
    data_quality=dict(rows=len(rows),first=iso(rows[0][0]),last=iso(rows[-1][0]),
       sha256=hashlib.sha256(raw).hexdigest(),preaug_count_eligible=len(pre),
       strict_transition_signals=len(modes["strict"]),
       trend_filtered_signals=len(modes["strict_trend"]))
    eligible={
       "calibration_selection":compact(a),
       "val1_of_calibration_selected":oos_val1,
       "second_selection":compact(b),
       "val2_of_second_selection":oos_val2,
       "final_preaug":compact(final),
       "recommended_preaug":compact(recommended),
       "frozen_eth_link_baseline":compact(baseline),
       "passing_three_folds_double_fee_candidates":len(all_stable),
       "candidate_count_total":len(records),
    }
    # candidate perturbation check: same model and direction, nearby SL/TP grid
    near=[x for x in pre if x["direction"]==recommended["direction"] and
          x["params"][0]==recommended["params"][0] and
          x["params"][4]==recommended["params"][4] and
          x["params"][3]==recommended["params"][3]]
    near.sort(key=lambda x:abs(x["params"][1]-recommended["params"][1])+
                            abs(x["params"][2]-recommended["params"][2]))
    eligible["nearby_stops_takes"]=[dict(rule=parameter_info(x["params"],x["direction"]),
                     calib=x["metrics"]["calibration"]["pnl_pct"],
                     val1=x["metrics"]["validation1"]["pnl_pct"],
                     val2=x["metrics"]["validation2"]["pnl_pct"]) for x in near[:9]]
    eligible["quality_control"]=data_quality
    eligible["candidate_preview"]=[dict(rule=parameter_info(x["params"],x["direction"]),
       calibration=x["metrics"]["calibration"]["pnl_pct"],
       val1=x["metrics"]["validation1"]["pnl_pct"],
       val2=x["metrics"]["validation2"]["pnl_pct"],
       trades=[x["metrics"][v]["trades"] for v in ("calibration","validation1","validation2")],
       score=score({k:x["metrics"][k] for k in ("calibration","validation1","validation2")}))
       for x in sorted(pre,key=lambda x:rank_candidate(x,
                   ("calibration","validation1","validation2")),reverse=True)[:12]]
    eligible["recommended_ledger"]=recommended["ledger"]
    return eligible


def main():
    out=dict(title="Per-coin separate BTC BNB XRP TON exact Pine 4h rule search",
       run_id=os.environ.get("GITHUB_RUN_ID","local"),
       code_sha=os.environ.get("GITHUB_SHA","local"),
       asset_list=COINS,preselected_eth_link_excluded=True,
       manual_trades_used=False,live_orders=False,
       source="Immutable GitHub Release delta-ml-3y-cache-2026-10-27",
       indicator="Executable root Pine Delta: SMA21 -> RSI12/RMA -> EMA7 -> signed log-symmetric Delta",
       temporal_windows={key:[iso(a),iso(b) if b<2**62 else "archive end"]
                         for key,(a,b) in PERIODS.items()},
       nested_selection="calibration only -> val1, calibration+val1 -> val2, all 3 PRE-August -> final",
       fixed_nominal_usd=FIXED_NOTIONAL,initial_equity_usd=CAPITAL,
       fee_roundtrip=COST_RT,stress_fee_roundtrip=STRESS_RT,
       selected_risk_ceiling_on_closed_trades_pct=15.,
       results={},
       caveats=[
          "Candidate search over hundreds of rule combinations per coin creates multiple-testing selection bias",
          "Two historical validation folds were already observed in previous explorations; nested step is temporally honest but NOT virgin discovery OOS",
          "Aug-Oct has been viewed repeatedly, only diagnostic, never used to rank or choose",
          "Only completely closed trades counted per fold; positions crossing fold boundary are excluded from fold results (not forcibly liquidated)",
          "Signals causal on closed 4h and filled next open; OHLC stop-first; no 48h time limit",
          "Fixed $840 nominal per trade from $5000 starting account; no leverage; never claim this is 16.8% at 5x leverage",
          "Closed-trade DD is not intrabar DD, and not platform risk compliance",
          "No funding or real slippage; two fee scenarios approximate 0.18 and 0.36% roundtrip",
          "Actual root Pine header RSI27 is misleading; executable source uses RSI12 of SMA21 with symmetric Delta",
          "Strict bright and price divergence filters are experimental proxies, not user's full discretion",
          "No trade commands; research only. Next genuine OOS starts Nov 2026",
       ])
    for symbol in COINS:
        result=evaluate_coin(symbol)
        out["results"][symbol]=result
        digest={k:result["recommended_preaug"]["folds"][k]["pnl_pct"]
                 for k in PERIODS}
        print("COIN_RULE",json.dumps(dict(symbol=symbol,
           selected=result["recommended_preaug"]["rule"],
           preaug_stable=result["recommended_preaug"]["stable_preaug"],
           passing_candidates=result["passing_three_folds_double_fee_candidates"],
           calibration_selected_val1=result["val1_of_calibration_selected"],
           updated_selected_val2=result["val2_of_second_selection"],
           pnl_by_fold=digest,
           double_cost={k:v["pnl_pct"] for k,v in result["recommended_preaug"]["double_cost_preaug"].items()},
           trades={k:v["trades"] for k,v in result["recommended_preaug"]["folds"].items()}),
           ensure_ascii=False),flush=True)
    (ROOT/"OTHER_COINS_RESEARCH.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
    lines=["# DeltaRSI: отдельный поиск правил для BTC, BNB, XRP, TON","",
       f"GH run: {out['run_id']} / SHA {out['code_sha']}","",
       "Сигналы из исполняемого тела оригинального Pine, закрытая 4H, вход по следующему открытию.",
       "Выбор правил строго по истории до 1 августа 2026; август—октябрь *уже просмотрены*, не новый OOS.",
       "Нет принудительного закрытия по 48ч. Обязательная проверка комиссий и достаточности числа сделок.",
       "Правила для ETH/LINK оставлены без изменений.","",
       "| Монета | Вариант входа | SL ATR | TP ATR | Трейлинг активация / дистанция ATR | Выход | Калибровка | Вал1 | Вал2 | Авг–окт | Надёжность |",
       "|---|---|---:|---:|---|---|---:|---:|---:|---:|---|"]
    for sym,z in out["results"].items():
        obj=z["recommended_preaug"]
        p=obj["rule"]
        m=obj["folds"]
        strategy=f"{p['trailing_activation_atr']}/{p['trailing_distance_atr']}" if p["trailing_activation_atr"] else "нет"
        direction=p["direction_filter"]
        lines.append(f"| {sym.replace('USDT','')} | {p['entry']} ({direction}) | {p['stop_atr']} | {p['take_atr'] or '—'} | {strategy} | {p['exit']} | "
           f"{m['calibration']['pnl_pct']:+.2f}% | {m['validation1']['pnl_pct']:+.2f}% | "
           f"{m['validation2']['pnl_pct']:+.2f}% | {m['previously_inspected']['pnl_pct']:+.2f}% | "
           f"{'кандидат, нужен будущий форвард' if obj['stable_preaug'] else 'НЕ ПОДТВЕРЖДЕНО'} |")
    lines+=["","## Nested selection (строго прошлая история)","",
       "Первый кандидат выбран по калибровке, его оценка на validation1 не использовалась для выбора.",
       "Второй кандидат выбран по калибровке + validation1, проверен на validation2.",
       "Финальный кандидат выбрали по трём историческим отрезкам без август—октябрьских метрик.",
       "Два прежних исторических валидационных периода уже известны исследователю, поэтому это лишь временная проверка и диагностика. Нужен настоящий форвард после 1 ноября.",
       "В отчёте JSON сохранены входы и выходы, полный рейтинг, контрольная ETH/LINK конфигурация, двойные издержки и журнал всех выбранных сделок.","",
       "Никаких живых ордеров. Нет подтверждённой полной симуляции Upscale prop/risk. Портфельная конкуренция сигналов не моделировалась. Результаты по фиксированному номиналу $840, а не 1x на весь капитал."]
    (ROOT/"OTHER_COINS_RESEARCH.md").write_text("\n".join(lines)+"\n")
    print("OTHER_COINS_SUMMARY",json.dumps({sym:dict(
        stable=z["recommended_preaug"]["stable_preaug"],
        pass_count=z["passing_three_folds_double_fee_candidates"],
        selected=z["recommended_preaug"]["rule"])
        for sym,z in out["results"].items()},ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
