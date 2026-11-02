"""48-hour horizon sensitivity using KNOWN historical per-coin ATR settings.

Keeps original research unchanged. Trading baseline:
- BTC SL 2.5 ATR, TP 5 ATR, no trailing
- ETH SL 1.5 ATR, TP 5 ATR, no trailing
- BNB SL 1.5 ATR, TP 2.5 ATR, no trailing
- ICP SL 5 ATR, TP 2.5 ATR, no trailing
- ZEC SL 1.5 ATR, TP 1.5 ATR, no trailing
- TON old contract SL 2.5 ATR, TP 5 ATR, trail after +3 ATR / 0.5 ATR

XRP/LINK excluded from per-coin prop control because final SL/TP settings
are not established in the historical handoff. Prior TONUSDT delisted June23;
GRAMUSDT is a DISTINCT short-history contract, not glued to TON.

ATR14 is anchored at bar i-1, i being the CLOSED entry signal, matching
the user's documented prior ATR rule. Entries are next 4H OPEN. Trailing
updated only on 4H closed bars, so TON is a PROXY, NOT an exact 1H
trailing implementation. Separate parallel NO-OPPOSITE and OPPOSITE exit.
All limits measured from ACTUAL entry open and executed at first 4H OPEN
with t>=open + limit; the older 100min early-close variant is not modelled.

No reoptimization on inspected Aug-Oct, no forced liquidation at fold end.
No real orders, no 3-slot prop portfolio, no 1H risk test.
"""
import collections
import datetime as dt
import json
import math
import os

import numpy as np

import cycle_48h_analysis as study
import research_rules as rr
from train import ROOT

COIN_SPECS={
    "BTCUSDT":(2.5,5.0,0.0,0.0),
    "ETHUSDT":(1.5,5.0,0.0,0.0),
    "BNBUSDT":(1.5,2.5,0.0,0.0),
    "ICPUSDT":(5.0,2.5,0.0,0.0),
    "ZECUSDT":(1.5,1.5,0.0,0.0),
    "TONUSDT":(2.5,5.0,3.0,0.5)
}
CAPS=tuple(range(4,97,4))+(None,)
MODES=("sl_tp_only","sl_tp_and_opposite")
COST=study.COST_RT
ACCOUNT=study.CAPITAL
POSITION=study.NOTIONAL
SPLITS=study.SPLITS


def cap_name(h):
    return ("uncapped" if h is None else str(h)+"h")


def run_trade(d,signal_i,side,stop_at,cap,mode,params):
    j0=signal_i+1
    if j0>=stop_at or signal_i<1:
        return None
    sl_mult,tp_mult,trail_activate,trail_distance=params
    atr=float(d["atr"][signal_i-1])  # previous fully closed before signal
    entry=float(d["op"][j0])
    if not(math.isfinite(atr) and atr>0 and entry>0):
        return None
    stop=entry-side*sl_mult*atr
    target=entry+side*tp_mult*atr
    if stop<=0 or target<=0:
        return None
    peak_close=entry
    trailing=False
    exit_price=float(d["close"][stop_at-1])
    reason="boundary_mark_unrealized"
    exit_i=stop_at-1
    cap_bar=j0+cap//4 if cap is not None else None
    for j in range(j0,stop_at):
        price=float(d["op"][j])
        # A previous completed candle controls stop, TP and indicator;
        # no future bar high/low is examined before an OPEN fill.
        if cap_bar is not None and j>=cap_bar:
            exit_i=j;exit_price=price;reason="time_cap"
            break
        if mode=="sl_tp_and_opposite" and j>j0 and rr.should_exit(d,j,side,"reverse_fade"):
            exit_i=j;exit_price=price;reason="opposite_delta_fade"
            break
        if (side>0 and price<=stop) or (side<0 and price>=stop):
            exit_i=j;exit_price=price;reason="stop_gap"
            break
        if (side>0 and price>=target) or (side<0 and price<=target):
            exit_i=j;exit_price=target;reason="tp_gap"
            break
        if (side>0 and float(d["low"][j])<=stop) or (side<0 and float(d["high"][j])>=stop):
            exit_i=j;exit_price=stop;reason="stop_first"
            break
        if (side>0 and float(d["high"][j])>=target) or (side<0 and float(d["low"][j])<=target):
            exit_i=j;exit_price=target;reason="tp"
            break
        if trail_activate>0 and trail_distance>0:
            close=float(d["close"][j])
            peak_close=max(peak_close,close) if side>0 else min(peak_close,close)
            if side*(peak_close-entry)>=trail_activate*atr:
                trailing=True
            if trailing:
                proposed=peak_close-side*trail_distance*atr
                stop=max(stop,proposed) if side>0 else min(stop,proposed)
    ret=side*(exit_price/entry-1)-COST
    return dict(signal_idx=signal_i,entry_i=j0,exit_i=exit_i,
        side=side,entry_ms=int(d["t"][j0]),exit_ms=int(d["t"][exit_i]),
        ret=float(ret),hold_h=4*(exit_i-j0),reason=reason,
        realized=reason!="boundary_mark_unrealized",
        entry_regime=study.score_regime(d,signal_i))


def sequential(d,symbol,cap,mode,start,end):
    st=max(study.MIN_START,int(np.searchsorted(d["t"],start)))
    en=int(np.searchsorted(d["t"],end))
    en=min(en,d["n"])
    if en-st<4:
        return dict(trades=0,account_pct=0.,time_exits=0,unfinished=0,
            mean_hours=None,win_rate=None,by_reason={},entries=[])
    selected=study.strict_events(d)
    next_free=st
    cash=ACCOUNT
    peak=cash
    dd=0.
    outcomes=[]
    time_exits=0
    closed=0
    unfinished=0
    wins=0
    durations=[]
    why=collections.Counter()
    for i,side in selected:
        if i+1<st or i+1>=en or i+1<next_free:
            continue
        p=run_trade(d,i,side,en,cap,mode,COIN_SPECS[symbol])
        if p is None:
            continue
        cash+=POSITION*p["ret"]
        peak=max(peak,cash)
        dd=max(dd,1-cash/peak)
        closed+=int(p["realized"])
        unfinished+=int(not p["realized"])
        wins+=int(p["realized"] and p["ret"]>0)
        time_exits+=int(p["reason"]=="time_cap")
        durations.append(p["hold_h"])
        why[p["reason"]]+=1
        outcomes.append(p)
        next_free=p["exit_i"]+1
        if not p["realized"]:
            break
    return dict(trades=closed,account_pct=round(100*(cash/ACCOUNT-1),3),
       time_exits=time_exits,unfinished=unfinished,
       mean_hours=round(float(np.mean(durations)),2) if durations else None,
       win_rate=round(wins/closed,3) if closed else None,
       realized_and_boundary_dd_pct=round(100*dd,3),
       by_reason=dict(why),entries=outcomes)


def matched_signals(d,symbol,mode,start,end):
    st=max(study.MIN_START,int(np.searchsorted(d["t"],start)))
    en=min(d["n"],int(np.searchsorted(d["t"],end)))
    cohorts=collections.defaultdict(list)
    comparisons={}
    for i,side in study.strict_events(d):
        if i+1<st or i+1>=en:
            continue
        no=run_trade(d,i,side,en,None,mode,COIN_SPECS[symbol])
        short=run_trade(d,i,side,en,48,mode,COIN_SPECS[symbol])
        if no is None or short is None or not(no["realized"] and short["realized"]):
            continue
        entry_region=no["entry_regime"]
        cohort=(entry_region,"LONG" if side>0 else "SHORT")
        cohorts[cohort].append(short["ret"]-no["ret"])
        cohorts[(entry_region,"BOTH")].append(short["ret"]-no["ret"])
        cohorts[("ALL","BOTH")].append(short["ret"]-no["ret"])
    for key,diff in cohorts.items():
        sample=np.array(diff,dtype=float)
        comparisons[key[0]+":"+key[1]]=dict(n=len(diff),
            mean_48_vs_uncapped_nominal_pp=round(100*float(np.mean(sample)),4),
            improved_pct=round(100*float(np.mean(sample>0)),1),
            worsened_pct=round(100*float(np.mean(sample<0)),1),
            unchanged_pct=round(100*float(np.mean(sample==0)),1))
    return comparisons


def main():
    data,sources=study.read_data()
    performance={}
    matches={}
    for sym in COIN_SPECS:
        d,_=data[sym]
        performance[sym]={}
        matches[sym]={}
        for mode in MODES:
            performance[sym][mode]={}
            matches[sym][mode]={}
            for period,(start,end) in SPLITS.items():
                if period=="inspected_aug_oct" and sym=="TONUSDT":
                    continue
                outcomes={}
                for cap in CAPS:
                    result=sequential(d,sym,cap,mode,start,end)
                    # Keep compact runs; drop ledgers except 48h and uncapped.
                    events=result.pop("entries")
                    if cap in (48,None):
                        result["ledger"]=[dict(entry_ms=x["entry_ms"],exit_ms=x["exit_ms"],
                                  side=x["side"],reason=x["reason"],hold_h=x["hold_h"],
                                  net_pct=round(100*x["ret"],5)) for x in events]
                    outcomes[cap_name(cap)]=result
                performance[sym][mode][period]=outcomes
                matches[sym][mode][period]=matched_signals(d,sym,mode,start,end)
    # Never select on previously inspected Aug-Oct. First period is TRAIN
    # for cap selection; two periods are strictly out-of-time descriptive.
    best_cal={}
    for sym in COIN_SPECS:
        best_cal[sym]={}
        for mode in MODES:
            runs=performance[sym][mode]["calibration"]
            ranked=sorted(((v["account_pct"],k) for k,v in runs.items()
                if v["trades"]>=7),reverse=True)
            best_cal[sym][mode]=dict(selected_on_calibration=ranked[0][1] if ranked else None,
                                    top3=[dict(cap=k,result_pct=p) for p,k in ranked[:3]])
    o=dict(title="DeltaRSI 48h time exits using historical per-coin ATR parameters",
       source_run=os.environ.get("GITHUB_RUN_ID","local"),
       source_sha=os.environ.get("GITHUB_SHA","local"),
       distinct_immutable_source=sources,
       per_coin_known_rules={
           sym:dict(stop_atr=x[0],take_atr=x[1],trail_trigger_atr=x[2],
                    trail_distance_atr=x[3]) for sym,x in COIN_SPECS.items()},
       unknown_coin_parameters="XRP and LINK final historic prop SL/TP settings not stated, deliberately excluded from per-coin replay",
       from_user_strategy="ATR from last CLOSED bar before signal, execute strict fade next 4H OPEN",
       limitations=[
          "TON actual trailing updated every 1H, this 4H-only study is NOT an exact recreation",
          "Earlier prop forced closing began ~100 minutes before 48h; here tested exact 4H OPEN 48h only",
          "No three-slot common cash/equity account or 5% daily/10% overall/Turbo6% monitoring, funding or 5x leverage",
          "Calibrated ATR14 EWM initial seed may differ from exchange/Pine",
          "Time cap selection on historical calibration is not independent proof, especially where calibration is loss-making",
          "Aug-Oct already inspected and never used for cap selection",
          "Sign and price extrema are hindsight descriptors, not predictors available at entry",
          "No lookahead in trade decisions; SL/TP on 4H OHLC stop-first, trail updates on 4H close for TON",
       ],
       historical_span=study.SPLITS,
       caps_tested=CAPS,
       chosen_on_calibration_only=best_cal,
       by_coin_per_exit_mode_period=performance,
       paired_same_signal_by_market_regime=matches)
    (ROOT/"DELTARSI_48H_PER_COIN_RULES.json").write_text(json.dumps(o,ensure_ascii=False,indent=2))
    summary={}
    for sym in COIN_SPECS:
        summary[sym]={}
        for mode in MODES:
            summary[sym][mode]={}
            for p,v in performance[sym][mode].items():
                summary[sym][mode][p]={h:v[h]["account_pct"]
                   for h in ("24h","36h","48h","60h","72h","uncapped")}
    print("PER_COIN_48H_SUMMARY",json.dumps(dict(summary=summary,
         calibration_choice=best_cal,paired=matches),ensure_ascii=False),flush=True)
    md=["# 48 часов на исторических per-coin ATR-параметрах DeltaRSI","",
      "Строгий medium→weak, вход на следующем 4H OPEN, ATR(14) предыдущей свечи перед сигнальной.",
      "Это исследовательская **4H** имитация, НЕ точная проверка старого 1H TON trail и общих prop-слотов.",
      "Проп-правила XRP/LINK для этого теста не заданы, исключены без выдуманных SL/TP.",
      "В отчёте оба режима: с противоположным выходом / без него. Исторические данные скачаны не были.",
      "",
      "| Актив | SL / TP ATR | Режим | Калибровочный выбор | 48h calib | 48h val1 | 48h val2 | 48h без cap, val2 |",
      "|---|---|---|---|---:|---:|---:|---:|"]
    for sym in COIN_SPECS:
        x=COIN_SPECS[sym]
        for mode in MODES:
            rec=performance[sym][mode]
            c=best_cal[sym][mode]["selected_on_calibration"]
            md.append(f"| {sym[:-4]} | {x[0]}/{x[1]} | {mode} | {c} | "
              f"{rec['calibration']['48h']['account_pct']:+.2f}% | "
              f"{rec['validation1']['48h']['account_pct']:+.2f}% | "
              f"{rec['validation2']['48h']['account_pct']:+.2f}% | "
              f"{rec['validation2']['uncapped']['account_pct']:+.2f}% |")
    md+=["","## Сравнение одной и той же исходной сделки по рынку","",
        "В JSON — отдельные группы bull/bear/range/pullback и LONG/SHORT; средняя разница 48h−uncapped и доля улучшений.",
        "Это независимый от числа повторных входов **парный** анализ, но сделки намеренно перекрываются и не являются портфелем.",
        "",
        "## Ограничения и вывод","",
        "48ч не равно длительности DeltaRSI полного цикла. Проверяется граница удержания с конкретным SL/TP в конкретных типах рынка.",
        "Двойная проверка обратного выхода показывает, что прежние предпочтения сильно зависят от механики выхода.",
        "Не включать результат в реальную проп-стратегию без полного 1H/portfolio risk replay.",
        "Август–октябрь просмотрен прежде и не служит для подбора лучших часов."]
    (ROOT/"DELTARSI_48H_PER_COIN_RULES.md").write_text("\n".join(md)+"\n")


if __name__=="__main__":
    main()
