"""Find robust, auditable DeltaRSI entry and exit rules, using cached 4h candles ONLY.

This script is a RULE SEARCH, not a promise of profitability. It never uses
Aug-Oct 2026 to rank policies, and uses no 48h exit. 4h entries are at the
next open after the CLOSED signal bar; intrabar SL/TP use stop-first priority.
"""
import itertools
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from train import ASSETS, ROOT, CUT, features

UTC = timezone.utc
DATE_A = int(datetime(2025, 7, 1, tzinfo=UTC).timestamp() * 1000)
DATE_B = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp() * 1000)
COST_RT = 0.0018  # fee .08% per side + spread .02% roundtrip
ENTRY_MODES = ("strict", "expanded", "strict_trend", "strict_bright", "strict_divergence")
EXIT_MODES = ("reverse_fade", "zero_cross", "momentum_rollover", "risk_only")
STOPS = (1.5, 2.5, 4.0)
TAKES = (0.0, 2.5, 5.0)
TRAILS = ((0.0, 0.0), (2.0, 1.0), (3.0, 1.5))
CODES = {1: "bright_blue", 2: "medium_blue", 3: "midweak_blue",
         4: "weak_blue", 5: "bright_red", 6: "medium_red",
         7: "midweak_red", 8: "weak_red"}


def iso(t):
    return datetime.fromtimestamp(int(t) / 1000, UTC).isoformat()


def make_arrays(df):
    price = df.close.to_numpy()
    high = df.high.to_numpy()
    low = df.low.to_numpy()
    prevclose = np.r_[np.nan, price[:-1]]
    tr = np.maximum(high-low, np.maximum(np.abs(high-prevclose), np.abs(low-prevclose)))
    atr = pd.Series(tr).ewm(alpha=1/14, adjust=False, min_periods=14).mean().to_numpy()
    return dict(t=df.t.to_numpy(), op=df.open.to_numpy(), high=high,
                low=low, close=price, shade=df.shade.to_numpy(),
                dr=df.dr.to_numpy(), atr=atr,
                ema200_dist=df.ema200_dist.to_numpy(),
                bear_div=df.bear_div_proxy.to_numpy(),
                bull_div=df.bull_div_proxy.to_numpy(),
                n=len(df))


def candidates(d, mode):
    sh = d["shade"]
    dr = d["dr"]
    out = []
    n = d["n"]
    for i in range(220, n-2):
        old, new = int(sh[i-1]), int(sh[i])
        side = (1 if old in (6,7) and new == 8 else
                -1 if old in (2,3) and new == 4 else 0)
        if not side:
            continue
        if mode != "expanded" and old in (3,7):
            continue
        if mode == "strict_trend" and side*d["ema200_dist"][i] <= 0:
            continue
        if mode == "strict_bright":
            j = i-1
            seen_bright = False
            while j>=220 and math.isfinite(dr[j]) and dr[j]*dr[i]>0:
                if int(sh[j]) == (5 if side==1 else 1):
                    seen_bright = True
                    break
                j-=1
            if not seen_bright:
                continue
        if mode == "strict_divergence" and not (d["bull_div"][i] if side==1 else d["bear_div"][i]):
            continue
        if not math.isfinite(d["atr"][i]) or d["atr"][i] <= 0:
            continue
        out.append((i,side))
    return out


def should_exit(d, j, side, rule):
    if rule == "risk_only" or j < 2:
        return False
    sh = d["shade"]
    prev, now = int(sh[j-2]), int(sh[j-1])
    if rule == "reverse_fade":
        return (prev in (2,3) and now==4) if side == 1 else (prev in (6,7) and now==8)
    v0, v1 = d["dr"][j-2], d["dr"][j-1]
    if not(math.isfinite(v0) and math.isfinite(v1)):
        return False
    if rule == "zero_cross":
        return v0 >= 0 and v1 < 0 if side==1 else v0 <= 0 and v1 > 0
    if rule == "momentum_rollover":
        return v1>0 and v1<v0 if side==1 else v1<0 and v1>v0
    return False


def trade(d, i, side, end_exclusive, params):
    mode, sl_atr, tp_atr, trail, exit_mode = params
    entrybar = i+1
    if entrybar>=end_exclusive-1:
        return None
    entry=float(d["op"][entrybar])
    a=float(d["atr"][i])
    if entry<=0 or a<=0:
        return None
    stop=entry-side*sl_atr*a
    take=entry+side*tp_atr*a if tp_atr else None
    if stop<=0 or (take is not None and take<=0):
        return None
    active_trail=False
    extreme=entry
    exit_price=None
    reason=None
    finish=entrybar
    for j in range(entrybar,end_exclusive):
        op=float(d["op"][j])
        hi=float(d["high"][j])
        lo=float(d["low"][j])
        if j>entrybar and should_exit(d,j,side,exit_mode):
            exit_price=op
            reason=exit_mode
        if exit_price is None:
            if (side==1 and op<=stop) or (side==-1 and op>=stop):
                exit_price=op  # adverse opening gap: never award the stop price
                reason="stop_gap"
            elif take is not None and ((side==1 and op>=take) or (side==-1 and op<=take)):
                exit_price=take  # conservative, no price improvement for favorable gap
                reason="target_gap"
            else:
                sl_hit = (lo<=stop if side==1 else hi>=stop)
                tp_hit = (hi>=take if side==1 else lo<=take) if take is not None else False
                if sl_hit:  # conservative stop-first when both touched
                    exit_price=stop
                    reason="stop"
                elif tp_hit:
                    exit_price=take
                    reason="target"
        if exit_price is not None:
            finish=j
            break
        # Trail updated using only closed bar, effective NEXT candle.
        if trail[0] > 0:
            close=float(d["close"][j])
            if side==1:
                extreme=max(extreme, close)
                if extreme-entry >= trail[0]*a:
                    active_trail=True
                if active_trail:
                    stop=max(stop, extreme-trail[1]*a)
            else:
                extreme=min(extreme, close)
                if entry-extreme >= trail[0]*a:
                    active_trail=True
                if active_trail:
                    stop=min(stop, extreme+trail[1]*a)
    if exit_price is None:
        finish=end_exclusive-1
        exit_price=float(d["close"][finish])
        reason="evaluation_boundary"  # book valuation; NOT a trading time-exit rule
    ret=side*(exit_price/entry-1)-COST_RT
    return dict(symbol=mode, signal_i=i, entry_ms=int(d["t"][entrybar]),
                exit_ms=int(d["t"][finish]), side=side, entry=entry,
                exit=exit_price, ret=float(ret), hold_hours=4*(finish-entrybar),
                reason=reason, atr=a, entry_delta=float(d["dr"][i]))


def evaluate(datas, entrysets, params, start, end, include_ledger=False):
    mode=params[0]
    totals=[]
    trades=[]
    by_asset={}
    all_returns=[]
    all_reasons=defaultdict(int)
    for sym,d in datas.items():
        idxstart=int(np.searchsorted(d["t"],start))
        idxend=int(np.searchsorted(d["t"],end))
        next_free=idxstart
        equity=1.
        peak=1.
        dd=0.
        count=0
        wins=0
        asset_ret=[]
        for i,side in entrysets[(sym,mode)]:
            if i+1<idxstart or i+1>=idxend-1 or i+1<next_free:
                continue
            result=trade(d,i,side,idxend,params)
            if result is None:
                continue
            result["symbol"]=sym
            equity*=max(0.0001,1+result["ret"])
            peak=max(peak,equity)
            dd=max(dd,1-equity/peak)
            count+=1
            wins+=int(result["ret"]>0)
            asset_ret.append(result["ret"])
            all_returns.append(result["ret"])
            all_reasons[result["reason"]]+=1
            next_free=int(np.searchsorted(d["t"],result["exit_ms"]))+1
            if include_ledger:
                trades.append(result)
        by_asset[sym]=dict(trades=count, return_pct=round(100*(equity-1),3),
                           closed_trade_dd_pct=round(100*dd,3),
                           win_rate=round(wins/count,3) if count else None)
        totals.append((equity-1, dd, count))
    num=sum(x[2] for x in totals)
    gain=sum(max(0.,r) for r in all_returns)
    loss=-sum(min(0.,r) for r in all_returns)
    summary=dict(trades=num, mean_asset_return_pct=round(100*np.mean([x[0] for x in totals]),3),
        median_asset_return_pct=round(100*np.median([x[0] for x in totals]),3),
        worst_asset_return_pct=round(100*min(x[0] for x in totals),3),
        assets_profitable=sum(x[0]>0 for x in totals),
        mean_closed_trade_dd_pct=round(100*np.mean([x[1] for x in totals]),3),
        profit_factor=round(gain/loss,3) if loss else None,
        win_rate=round(sum(r>0 for r in all_returns)/num,3) if num else None)
    return dict(summary=summary, by_asset=by_asset, exit_reasons=dict(all_reasons), ledger=trades)


def grid():
    for mode,sl,tp,trail,exit_type in itertools.product(
            ENTRY_MODES,STOPS,TAKES,TRAILS,EXIT_MODES):
        yield (mode,sl,tp,trail,exit_type)


def rank(cal,v1,v2):
    a,b,c=cal["summary"],v1["summary"],v2["summary"]
    if a["trades"] < 30 or b["trades"] < 15 or c["trades"] < 15:
        return -1e6 + a["trades"] + b["trades"] + c["trades"]
    returns=[p["mean_asset_return_pct"] for p in (a,b,c)]
    draws=[p["mean_closed_trade_dd_pct"] for p in (a,b,c)]
    profits=[p["assets_profitable"] for p in (a,b,c)]
    # Penalize worst regime most; protect against one lucky window.
    score=(.80*min(returns)+.18*sum(returns)
           -.13*sum(draws)+.15*sum(profits))
    # Hard requirement for selecting genuinely all-regime profitable candidate.
    if min(returns) > 0 and min(profits) >= 3:
        score+=15.
    return round(score,4)


def obj(params):
    mode,sl,tp,trail,x=params
    return dict(entry=mode,stop_atr=sl,take_atr=tp,
                trail_activation_atr=trail[0],trail_distance_atr=trail[1],
                indicator_exit=x)


def main():
    datas={}
    for symbol in ASSETS:
        path=ROOT/"data"/(symbol+".json")
        if not path.exists():
            raise RuntimeError(f"Cached candles missing: {path}. Never redownload here.")
        df=features(json.loads(path.read_text()),symbol)
        datas[symbol]=make_arrays(df)
    entrysets={(sym,mode):candidates(d,mode)
               for sym,d in datas.items() for mode in ENTRY_MODES}
    ranges=dict(calibration=(min(d["t"][0] for d in datas.values()),DATE_A),
                val1=(DATE_A,DATE_B),val2=(DATE_B,CUT),
                inspected_test=(CUT,2**62))
    sample_counts={sym:{mode:len(entrysets[(sym,mode)]) for mode in ENTRY_MODES}
                   for sym in datas}
    scores=[]
    total=0
    for p in grid():
        cal0=evaluate(datas,entrysets,p,*ranges["calibration"])
        v1=evaluate(datas,entrysets,p,*ranges["val1"])
        v2=evaluate(datas,entrysets,p,*ranges["val2"])
        scores.append((rank(cal0,v1,v2),p,v1["summary"],v2["summary"],cal0["summary"]))
        total+=1
    scores.sort(key=lambda v:v[0],reverse=True)
    # Chosen using ONLY 2025-07..2026-07 internal validation.
    best=scores[0]
    p=best[1]
    cal=evaluate(datas,entrysets,p,*ranges["calibration"])
    v1=evaluate(datas,entrysets,p,*ranges["val1"],include_ledger=True)
    v2=evaluate(datas,entrysets,p,*ranges["val2"],include_ledger=True)
    test=evaluate(datas,entrysets,p,*ranges["inspected_test"],include_ledger=True)
    top=[dict(rank=i+1,score=z[0],rules=obj(z[1]),val1=z[2],val2=z[3],calibration=z[4])
         for i,z in enumerate(scores[:20])]
    best_validation_positive=bool(v1["summary"]["mean_asset_return_pct"]>0
            and v2["summary"]["mean_asset_return_pct"]>0
            and v1["summary"]["assets_profitable"]>=3
            and v2["summary"]["assets_profitable"]>=3)
    all_three_positive=all(q["summary"]["mean_asset_return_pct"]>0 and q["summary"]["assets_profitable"]>=3 for q in (cal,v1,v2))
    report=dict(experiment="DeltaRSI 4h strict all-regime robust rule selection",
        run_id=os.environ.get("GITHUB_RUN_ID","local"),
        github_sha=os.environ.get("GITHUB_SHA","local"),
        source="CACHED historical Binance Vision USD-M data from previous successful Actions artifact",
        data={k:dict(candles=v["n"],first=iso(v["t"][0]),last=iso(v["t"][-1]))
              for k,v in datas.items()},
        indicator="Executable original Pine root Delta: SMA21->RSI12 RMA->EMA7->signed symmetric log delta; exact medium-to-weak color codes",
        manual_trades="excluded completely",
        scheme=dict(calibration_end=iso(DATE_A),validation1_end=iso(DATE_B),
                    validation2_end=iso(CUT),holdout_start=iso(CUT),
                    holdout_already_inspected=True),
        candidate_count=total, entry_counts=sample_counts,
        selected_rules=obj(p), val_score=best[0],
        calibration=cal,validation1={k:v for k,v in v1.items() if k!="ledger"},
        validation2={k:v for k,v in v2.items() if k!="ledger"},
        holdout={k:v for k,v in test.items() if k!="ledger"},
        validates_on_both_folds=best_validation_positive, all_three_positive=all_three_positive, top20=top,
        cost_round_trip=COST_RT,
        caveats=[
            "DO NOT tune on Aug-Oct 2026: already viewed in earlier experiment; future data needed for truly virgin OOS",
            "Policy chosen using the full 2023-11..2026-07 calibration and two validation periods; searching many candidates inflates selection bias",
            "All orders at following open after completed 4h signal; OHLC stop-first if SL/TP both hit",
            "No imposed maximum hold duration; closes only on SL/TP/trailing/indicator or evaluation boundary",
            "Trailing stop updated only after full bar close, effective next bar",
            "Book equity curves mark realized trade results, not intrabar mark-to-market risk",
            "Separate one-asset notional strategies, NOT a prop-compliant common portfolio; no funding",
            "Script does not claim learning a per-candle ML exit model; it discovers rules via systematic search",
            "Strict-bright/divergence filters are exploratory mathematical proxies, not discretionary manual labels",
        ])
    ledger=dict(calibration=cal["ledger"],validation1=v1["ledger"],
                validation2=v2["ledger"],inspected_test=test["ledger"])
    (ROOT/"stability_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (ROOT/"stability_trades.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2))
    lines=["# DeltaRSI: поиск объяснимых правил (без лимита 48 часов)","",
           f"GitHub run {report['run_id']} / SHA {report['github_sha']}","",
           "Данные загружены из ранее сохранённого артефакта GitHub Actions; Binance API не вызывался.","",
           "## Выбранная конфигурация (все три исторических периода до теста)","",
           "~~~json",json.dumps(obj(p),ensure_ascii=False,indent=2),"~~~","",
           "| Период | Сделок | Среднее по активам | Средняя закрытая DD | Прибыльных активов |",
           "|---|---:|---:|---:|---:|"]
    for label,item in [("Калибровка",cal),("Валидация A",v1),
                       ("Валидация B",v2),("Просмотренный август—октябрь",test)]:
        m=item["summary"]
        lines.append(f"| {label} | {m['trades']} | {m['mean_asset_return_pct']:.2f}% | {m['mean_closed_trade_dd_pct']:.2f}% | {m['assets_profitable']}/6 |")
    lines += ["","Устойчивость на трёх периодах: "+("выполнена" if all_three_positive else "**НЕ ПОДТВЕРЖДЕНА**"),
         "", "## Диагностика", "", "Финальный период уже просматривался в предыдущих экспериментах.",
         "Его результаты являются исследовательскими, не новым независимым доказательством.",
         "Сравнение 540 конфигураций создаёт риск подгонки на валидации; нужен последующий форвард-тест.",
         "Отсутствует полноценная общая модель проп-счёта и внутрисвечная equity DD.",
         "", "## Лучшие 10 кандидатов (только внутренние проверки)", ""]
    for i,z in enumerate(top[:10]):
        lines.append(f"{i+1}. Score {z['score']:.3f}, {z['rules']}; "
                     f"V1 {z['val1']['mean_asset_return_pct']:.2f}%, V2 {z['val2']['mean_asset_return_pct']:.2f}%")
    (ROOT/"STABILITY_RESEARCH_REPORT.md").write_text("\n".join(lines)+"\n")
    print("STABILITY_RESEARCH",json.dumps(dict(candidate_count=total,chosen=obj(p),
          calibration=cal["summary"],validation1=v1["summary"],
          validation2=v2["summary"],test=test["summary"],
          passes_validation=best_validation_positive,all_three_positive=all_three_positive,top3=top[:3]),ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
