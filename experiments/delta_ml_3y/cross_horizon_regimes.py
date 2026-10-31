"""Cross-horizon regime study: same date, eight very different crypto markets.

BTC/ETH/BNB/XRP/LINK/ICP/ZEC are continuously traded Binance USD-M
futures; TONUSDT only until 2026-06-23 delisting; GRAMUSDT separately
since 2026-07-02. Strictly never join their price histories across the gap.

This is a descriptive CAUSAL-feature diagnostic, not learned production rules.
Return horizons are 7, 30, 90 days, computed only from CLOSED 4h bars.
Exit outcomes are future realized counterfactuals, used only for RESEARCH.
"""
import collections
import datetime as dt
import hashlib
import json
import os

import numpy as np
import pandas as pd

import research_rules as rr
from train import ROOT, features

ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT",
        "TONUSDT","ICPUSDT","ZECUSDT","GRAMUSDT")
REGIME_LABELS=("BULL_TREND","BEAR_TREND","BULL_PULLBACK",
               "BEAR_RALLY","RANGE_CONFLICT")
EXIT_VARIANTS={
    "symmetric_2p5":("strict",2.5,2.5,(0.,0.),"reverse_fade"),
    "wide_4_5":("strict",4.,5.,(0.,0.),"reverse_fade"),
    "zero_trailing":("strict",2.5,0.,(3.,1.5),"zero_cross"),
    "tight_1p5":("strict",1.5,2.5,(0.,0.),"reverse_fade"),
}
START_TEST=rr.CUT
STEP=4*3600000
DEL_TON=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
BASE_COST=.0018


def iso(ms):
    return dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc).isoformat()


def read(sym):
    p=ROOT/"data"/(sym+".json")
    if not p.is_file():
        raise FileNotFoundError(f"Immutable archive restore failed: {p}")
    content=p.read_bytes()
    rows=json.loads(content)
    source=len(rows)
    invalid_tail=0
    if sym=="TONUSDT":
        invalid_tail=sum(row[0]>=DEL_TON for row in rows)
        if invalid_tail<700 or not all(row[5]==0 for row in rows if row[0]>=DEL_TON+STEP):
            raise RuntimeError("Unexpected TON delisting tail; manual audit required")
        rows=[row for row in rows if row[0]<DEL_TON]
    if any(b[0]-a[0]!=STEP for a,b in zip(rows,rows[1:])):
        raise RuntimeError(f"{sym}: discontinuity; no synthetic price series")
    if sym=="GRAMUSDT" and rows[0][0]!=int(dt.datetime(2026,7,2,8,tzinfo=dt.timezone.utc).timestamp()*1000):
        raise RuntimeError("GRAM futures July 2 listing start mismatch")
    return rows,dict(original_rows=source,usable_rows=len(rows),
      sha256=hashlib.sha256(content).hexdigest(),invalid_delisted_ton_tail=invalid_tail,
      first=iso(rows[0][0]),last=iso(rows[-1][0]))


def enrich(sym,rows):
    df=features(rows,sym)
    close=df.close
    a=df.atr_pct
    r7=close.pct_change(42)
    r30=close.pct_change(180)
    r90=close.pct_change(540)
    # All thresholds adapt to each asset's current 4h ATR and use only
    # its past, so a fixed 4% BTC move is not conflated with a 4% ZEC move.
    th_fast=2.0*a
    th_slow=3.0*a
    fup=r7>th_fast
    fdown=r7<-th_fast
    sup=r30>th_slow
    sdown=r30<-th_slow
    group=np.full(len(df),"RANGE_CONFLICT",dtype=object)
    group[(fup&sup).to_numpy()]="BULL_TREND"
    group[(fdown&sdown).to_numpy()]="BEAR_TREND"
    group[(fdown&sup).to_numpy()]="BULL_PULLBACK"
    group[(fup&sdown).to_numpy()]="BEAR_RALLY"
    vol_ref=a.shift(1).rolling(120,min_periods=100).median()
    volratio=a/vol_ref.replace(0,np.nan)
    df["horizon_state"]=group
    df["return7"]=r7
    df["return30"]=r30
    df["return90"]=r90
    df["volratio"]=volratio
    df["expansion"]=(volratio>1.55).fillna(False)
    return df


def events(df):
    arr=rr.make_arrays(df)
    signals=rr.candidates(arr,"expanded")
    out=[]
    for i,side in signals:
        if i<220 or i>=len(df)-1:
            continue
        row=df.iloc[i]
        strict=int(arr["shade"][i-1]) in (2,6)
        record=dict(t=int(arr["t"][i]),entry=int(arr["t"][i+1]),
          side=side,strict=bool(strict),regime=str(row.horizon_state),
          expansion=bool(row.expansion),volratio=float(row.volratio)
             if pd.notna(row.volratio) else None,
          macro90=float(row.return90) if pd.notna(row.return90) else None,
          results={})
        for profile,p in EXIT_VARIANTS.items():
            trade=rr.trade(arr,i,side,arr["n"],p)
            if trade is not None and trade["reason"]!="evaluation_boundary":
                record["results"][profile]=dict(net=trade["ret"],exit=int(trade["exit_ms"]),
                    hold=trade["hold_hours"],why=trade["reason"])
        out.append(record)
    return out


def bins(events_by_asset):
    periods={
      "calibration":(0,rr.DATE_A),
      "validation1":(rr.DATE_A,rr.DATE_B),
      "validation2":(rr.DATE_B,rr.CUT),
      "inspected":(rr.CUT,2**62)}
    groups={}
    signal_by_asset={}
    for period,(start,end) in periods.items():
        co=collections.defaultdict(list)
        count=collections.defaultdict(lambda:collections.Counter())
        for sym,evs in events_by_asset.items():
            for e in evs:
                if not e["strict"] or not start<=e["entry"]<end:
                    continue
                count[sym][e["regime"]]+=1
                for profile,v in e["results"].items():
                    if v["exit"]>=end:
                        continue  # no future exit may leak into earlier period
                    co[(e["regime"],"LONG" if e["side"]==1 else "SHORT",profile)].append(
                       (sym,v["net"],v["hold"],e["expansion"]))
        rec={}
        for (regime,side,profile),xs in co.items():
            net=np.asarray([x[1] for x in xs],dtype=float)
            bycoin=collections.Counter(x[0] for x in xs)
            gain=float(sum(max(0.,x) for x in net))
            loss=float(-sum(min(0.,x) for x in net))
            rec[f"{regime}:{side}:{profile}"]=dict(
              samples=len(xs),assets=len(bycoin),mean_nominal_pct=round(100*float(np.mean(net)),3),
              median_nominal_pct=round(100*float(np.median(net)),3),
              p20_pct=round(100*float(np.quantile(net,.2)),3),
              win_rate=round(float(np.mean(net>0)),3),
              profit_factor=round(gain/loss,3) if loss else None,
              mean_hold_hours=round(float(np.mean([x[2] for x in xs])),1),
              high_vol_samples=sum(x[3] for x in xs),
              source_coins=dict(bycoin))
        groups[period]=rec
        signal_by_asset[period]={sym:dict(c) for sym,c in count.items()}
    return groups,signal_by_asset


def monthly_phase_stats(df):
    dates=pd.to_datetime(df.t,unit="ms",utc=True)
    parts={}
    for p,(start,end) in dict(calibration=(0,rr.DATE_A),
           validation1=(rr.DATE_A,rr.DATE_B),
           validation2=(rr.DATE_B,rr.CUT),
           inspected=(rr.CUT,2**62)).items():
        series=df[(df.t>=start)&(df.t<end)]
        parts[p]=dict(candles=len(series),
            states=dict(collections.Counter(series.horizon_state)))
    return parts


def main():
    rr.COST_RT=BASE_COST
    datasets={}
    rows_by_asset={}
    source={}
    all_events={}
    for sym in ASSETS:
        rows,meta=read(sym)
        source[sym]=meta
        rows_by_asset[sym]=rows
        df=enrich(sym,rows)
        datasets[sym]=df
        all_events[sym]=events(df)
    group_stats,count=bins(all_events)
    snapshots={}
    for sym,df in datasets.items():
        end=df.iloc[-1]
        snapshots[sym]=dict(timestamp=iso(int(end.t)),
             regime=str(end.horizon_state),last_close=round(float(end.close),8),
             ret_7d_pct=round(float(end.return7)*100,2)
                 if pd.notna(end.return7) else None,
             ret_30d_pct=round(float(end.return30)*100,2)
                 if pd.notna(end.return30) else None,
             ret_90d_pct=round(float(end.return90)*100,2)
                 if pd.notna(end.return90) else None,
             atr_pct=round(float(end.atr_pct)*100,3)
                 if pd.notna(end.atr_pct) else None,
             relative_volatility=round(float(end.volratio),2)
                 if pd.notna(end.volratio) else None,
             vol_expansion=bool(end.expansion),
             strict_signals=len([e for e in all_events[sym] if e["strict"]]))
    source_note=dict(
       ton_delisted="Binance TONUSDT Perpetual delisted 2026-06-23 09:00 UTC; zero-volume placeholder candles removed",
       gram_listed="Binance GRAMUSDT Perpetual began trading 2026-07-02 08:00 UTC",
       no_stitching=True,
       no_granular_user_trade_data=True)
    result=dict(title="DeltaRSI 4h cross-horizon regime diagnostic BTC ETH BNB XRP LINK ICP ZEC old TON new GRAM",
       created_by_github_action=os.environ.get("GITHUB_RUN_ID","local"),
       code_sha=os.environ.get("GITHUB_SHA","local"),
       source=source,source_notes=source_note,
       indicator="Executable root Pine Delta RSI12 of SMA21 with EMA7 and symmetric signed log, threshold 60",
       market_state_formula=dict(
         fast="7-day return / 4h ATR14 >2 (bull) or <-2 (bear)",
         medium="30-day return / 4h ATR14 >3 (bull) or <-3 (bear)",
         both_positive="BULL_TREND",both_negative="BEAR_TREND",
         medium_positive_fast_negative="BULL_PULLBACK",
         medium_negative_fast_positive="BEAR_RALLY",
         remaining="RANGE_CONFLICT",
         macro="90-day return diagnostic only; never used as classifier before 540 bars",
         volatility="current ATR14/close divided by past 120-bar median ATRpct; expansion >1.55",
         causal=True),
       latest=snapshots,
       states_by_coin_period={sym:monthly_phase_stats(df) for sym,df in datasets.items()},
       closed_event_research_by_period=group_stats,
       exact_entry_signal_counts=count,
       tested_exits={name:dict(stop_atr=p[1],take_atr=p[2],
             trailing_atr=p[3],exit=p[4]) for name,p in EXIT_VARIANTS.items()},
       caveats=[
          "No optimization in this descriptive study; do not select best profile based on previously inspected Aug-Oct",
          "Outcome samples are overlapping counterfactual events, not a directly executable portfolio",
          "No forced 48h exit; 7/30/90d windows describe PAST market context, NOT trade holding cap",
          "New GRAMUSDT is a different futures contract; post-June TONUSDT zero-volume candles are discarded",
          "GRAM only 706 candles (Jul-Oct), insufficient for three years of training; keep it separate",
          "Future outcomes used solely to describe historical realized returns, never to label current regime",
          "August-October observed previously, not virgin out-of-sample",
          "Per-market notional $840 and 0.18% round-trip historical execution assumption; no funding or full Upscale prop risk replay",
          "User's manual trades excluded completely",
       ])
    (ROOT/"CROSS_HORIZON_REGIME_REPORT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    snap={k:dict(regime=v["regime"],ret7=v["ret_7d_pct"],
            ret30=v["ret_30d_pct"],ret90=v["ret_90d_pct"],
            explosion=v["vol_expansion"]) for k,v in snapshots.items()}
    print("CROSS_HORIZON_REGIMES",json.dumps(
        dict(latest=snap,counts={k:len(v) for k,v in all_events.items()},
             grouped_profiles=len(group_stats["validation2"]),
             key_cutoffs=[iso(rr.DATE_A),iso(rr.DATE_B),iso(rr.CUT)]),
             ensure_ascii=False),flush=True)
    lines=["# DeltaRSI: один период — девять отдельных инструментов, восемь экономических активов","",
      "TONUSDT до делистинга и GRAMUSDT после нового листинга — РАЗНЫЕ контракты. Искусственных свечей в промежутке нет.",
      "Гипотеза: 7-дневный и 30-дневный тренды могут противоречить друг другу; 90 дней — отдельный контекст. Волатильность нормируется для каждого актива.",
      "Состояние рассчитано только по закрытым 4h свечам. Это исторические данные до 27 октября, **не котировки на сейчас**.","",
      "| Контракт | Дата последней 4H | 7д | 30д | 90д | Состояние | Всплеск ATR? |",
      "|---|---|---:|---:|---:|---|---|"]
    for sym,v in snapshots.items():
        def fmt(k):
            return (f"{v[k]:+.2f}%" if v[k] is not None else "н/д")
        lines.append(f"| {sym} | {v['timestamp'][:10]} | {fmt('ret_7d_pct')} | {fmt('ret_30d_pct')} | {fmt('ret_90d_pct')} | {v['regime']} | {'да' if v['vol_expansion'] else 'нет'} |")
    lines+=["","## Входы и выходы","",
      "Отдельные табличные группы по 7/30д состоянию, стороне сделки и типу выхода находятся в CROSS_HORIZON_REGIME_REPORT.json.",
      "Для каждой группы показаны число закрытых будущих сделок, средний результат, 20-й процентиль и доля прибыльных.",
      "Это **описательная статистика перекрывающихся событий**, а не подтверждённая исполнимая стратегия и не обучение на будущем.",
      "Сигналы medium→weak берутся из исходного исполняемого Pine. Все трейды — после закрытия свечи.",
      "Не меняем прошлые результаты BTC/ETH/BNB/XRP/LINK/ICP/ZEC/TON, сохраняем их с пометкой о делистинге TON и нетронутом форварде с 1 ноября.",
      "Выводы по новому GRAM могут измениться, поскольку 3 года истории недоступны и 90д контекст возникает лишь к концу архива.",
      "",
      "## Что НЕ проверено","",
      "Не было модели общего 3-слотового проп-счёта, 1h/tick исполнения, funding, подтверждения всех лимитов Upscale.",
      "Август–октябрь — ранее просмотренный период. Новые правила нельзя выбирать по нему и затем считать их независимыми.",
      "Реальных торговых ордеров нет."]
    (ROOT/"CROSS_HORIZON_REGIME_REPORT.md").write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
