"""DeltaRSI cross-asset synchrony and weekday/hour seasonality in 4h waves.

Frozen source: existing Binance Vision 4h candles in three immutable GitHub
Releases, no market downloads. 7 continuous assets for primary statistics.
TON perpetual expired June 2026; GRAM is separate, secondary only.

Events:
  (a) change of sign at the CLOSE of a 4h bar (new blue/red run),
  (b) high/low of price within +/- 3 bars of the highest |Delta| bar in
      each COMPLETED blue/red sign wave; hindsight price pivots only.
Both RSI27-EMA7 and actual root Pine numeric implementation are examined.

Tests:
  (i) BTC-anchored same-direction cross-coin matches +/-4h, +/-8h,
      +/-12h, +/-24h; random circular independent cross-asset shifts
      preserve each series' event clustering and frequency;
  (ii) frequency of events on weekdays and UTC 4h candle closes,
      weekly synchronized shifts preserving actual shared market shocks.
  (iii) year-by-year day peaks to test repeatability.
No inference of future timing or tradeable calendar edge.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import math
import os

import numpy as np

import sign_peak_to_price_extreme as peaks
from train import ROOT

ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT","ICPUSDT","ZECUSDT")
OPTIONAL=("TONUSDT","GRAMUSDT")
VERSIONS=("rsi27_ema7","root_pine_executable")
EVENTS=("sign_flip","price_extreme")
STEP=4*3600000
RNG=np.random.default_rng(20261105)
PERM_N=800
WEEKDAY=("Mon","Tue","Wed","Thu","Fri","Sat","Sun")
WINDOW_BARS=(1,2,3,6)
CUTOFFS=[
    ("2023-11—2024-10","2023-11-01","2024-11-01"),
    ("2024-11—2025-10","2024-11-01","2025-11-01"),
    ("2025-11—2026-10","2025-11-01","2026-10-28"),
]


def timestamp(text):
    return int(dt.datetime.fromisoformat(text).replace(tzinfo=dt.timezone.utc).timestamp()*1000)


def event_arrays(data,version):
    h=peaks.histogram(data["close"],version)
    finite=np.isfinite(h)
    sign=np.zeros(len(h),dtype=np.int8)
    sign[finite&(h>0)]=1
    sign[finite&(h<0)]=-1
    idx=np.flatnonzero((sign[1:]!=sign[:-1])&(sign[1:]!=0)&(sign[:-1]!=0))+1
    idx=idx[idx>=peaks.WARMUP]
    flip=np.column_stack((data["t"][idx]+STEP,sign[idx].astype(np.int64))).astype(np.int64)
    pivots=peaks.locate_peaks(data,version,3)
    extreme=np.asarray([(int(data["t"][p["price_extreme_i"]]),int(p["side"]))
                        for p in pivots],dtype=np.int64)
    # Separate pivot at HIGH/LOW from its peak histogram bar (for checks).
    histpeak=np.asarray([(int(data["t"][p["histogram_peak_i"]])+STEP,int(p["side"]))
                          for p in pivots],dtype=np.int64)
    return dict(sign_flip=flip.reshape(-1,2),
                price_extreme=extreme.reshape(-1,2),
                histogram_peak=histpeak.reshape(-1,2))


def common_period(market_data):
    start=max(int(market_data[s]["t"][peaks.WARMUP]) for s in ASSETS)
    end=min(int(market_data[s]["t"][-1]+STEP) for s in ASSETS)
    return start,end


def in_period(a,start,end):
    return a[(a[:,0]>=start)&(a[:,0]<end)]


def nearest_distance(anchors,target):
    """Smallest ABS time difference in 4h bars. Inputs sorted int bar slots."""
    if not len(anchors):
        return np.asarray([],dtype=np.int64)
    if len(target)==0:
        return np.full(len(anchors),10**9,dtype=np.int64)
    pos=np.searchsorted(target,anchors,side="left")
    left=target[np.clip(pos-1,0,len(target)-1)]
    right=target[np.clip(pos,0,len(target)-1)]
    return np.minimum(np.abs(anchors-left),np.abs(anchors-right))


def matching(anchor,alt,tolerance):
    hit=np.zeros(len(anchor),dtype=bool)
    for side in (-1,1):
        ix=np.flatnonzero(anchor[:,1]==side)
        if not len(ix):continue
        a=(anchor[ix,0]//STEP).astype(np.int64)
        o=(alt[alt[:,1]==side,0]//STEP).astype(np.int64)
        hit[ix]=nearest_distance(a,o)<=tolerance
    return hit


def score_anchor(anchor,others,window):
    pair={}
    matches=np.ones(len(anchor),dtype=np.int16)
    for symbol,events in others.items():
        m=matching(anchor,events,window)
        pair[symbol]=round(float(np.mean(m))*100,2) if len(m) else None
        matches+=m.astype(np.int16)
    return dict(anchors=len(anchor),mean_extra_coins=round(float(np.mean(matches-1)),3),
                at_least_4_of_7_pct=round(float(np.mean(matches>=4))*100,3),
                at_least_5_of_7_pct=round(float(np.mean(matches>=5))*100,3),
                at_least_6_of_7_pct=round(float(np.mean(matches>=6))*100,3),
                all_7_pct=round(float(np.mean(matches>=7))*100,3),
                each_asset_pct=pair),matches


def rotate_independently(a,start,end,offset):
    """Circular phase shift of one entire asset on the shared 4h grid."""
    n=(end-start)//STEP
    idx=(a[:,0]-start)//STEP
    shifted=(idx+offset)%n
    res=np.column_stack((start+shifted*STEP,a[:,1])).astype(np.int64)
    return res[np.argsort(res[:,0])]


def shared_shock_null(anchor,others,start,end,window):
    observed,_=score_anchor(anchor,others,window)
    n=(end-start)//STEP
    samples=np.empty((PERM_N,4),dtype=float)
    # Cache per-event arrays with all time positions aligned to common grid.
    for j in range(PERM_N):
        rolled={}
        for sym,ev in others.items():
            # At least 14 days away from original phase, not a trivial near-shift.
            offset=int(RNG.integers(84,n-84))
            rolled[sym]=rotate_independently(ev,start,end,offset)
        metric,_=score_anchor(anchor,rolled,window)
        samples[j]=[metric["mean_extra_coins"],metric["at_least_4_of_7_pct"],
                    metric["at_least_5_of_7_pct"],metric["all_7_pct"]]
    names=("mean_extra_coins","at_least_4_of_7_pct","at_least_5_of_7_pct","all_7_pct")
    stats={}
    for i,name in enumerate(names):
        distribution=samples[:,i]
        actual=observed[name]
        stats[name]=dict(observed=actual,
            random_mean=round(float(np.mean(distribution)),3),
            random_p95=round(float(np.percentile(distribution,95)),3),
            empirical_one_sided_p=round(float((1+np.sum(distribution>=actual))/(PERM_N+1)),4))
    return dict(metrics=observed,permutation=stats,permutations=PERM_N,
                null="Independent circular shifts of each non-BTC asset, >=14d offset")


def utc_parts(events):
    ms=events[:,0].astype(np.int64)
    day=ms//86400000
    dow=(day+3)%7
    hh=((ms//3600000)%24).astype(np.int64)
    week=(day+3)//7
    year=np.asarray([dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).year for x in ms])
    return dow.astype(np.int64),(hh//4).astype(np.int64),week.astype(np.int64),year


def time_rate(dataset):
    dow,slot,week,yr=utc_parts(dataset)
    counts=np.bincount(dow,minlength=7)
    slots=np.bincount(slot,minlength=6)
    weekdays={WEEKDAY[i]:int(counts[i]) for i in range(7)}
    peaksdays=np.argsort(-counts)[:3]
    observed_max=float(max(counts)/max(1,len(dow)))
    observed_spread=float((max(counts)-min(counts))/max(1,len(dow)))
    observed_utc=float(max(slots)/max(1,len(dow)))
    ids=np.unique(week)
    weekidx=np.searchsorted(ids,week)
    perm_max_day=np.empty(PERM_N)
    perm_spread=np.empty(PERM_N)
    perm_max_time=np.empty(PERM_N)
    # Simultaneous shift for ALL coins and BOTH directions in the same
    # calendar week: preserves real cross-coin synchronized clusters.
    for k in range(PERM_N):
        shiftday=RNG.integers(0,7,size=len(ids))
        dow2=(dow+shiftday[weekidx])%7
        c=np.bincount(dow2,minlength=7)
        perm_max_day[k]=np.max(c)/len(dow)
        perm_spread[k]=(np.max(c)-np.min(c))/len(dow)
        shifthour=RNG.integers(0,6,size=len(ids))
        slot2=(slot+shifthour[weekidx])%6
        perm_max_time[k]=np.max(np.bincount(slot2,minlength=6))/len(dow)
    yrparts={}
    for name,start,end in CUTOFFS:
        t0=timestamp(start);t1=timestamp(end)
        m=(dataset[:,0]>=t0)&(dataset[:,0]<t1)
        c=np.bincount(dow[m],minlength=7)
        yrparts[name]=dict(events=int(m.sum()),days={WEEKDAY[i]:int(c[i]) for i in range(7)},
                 most_common=WEEKDAY[int(np.argmax(c))] if len(c) else None)
    return dict(n=len(dataset),weekday_counts=weekdays,
        peak_days=[WEEKDAY[int(i)] for i in peaksdays],
        weekday_percent={WEEKDAY[i]:round(float(counts[i]/len(dow))*100,2) for i in range(7)},
        time_bins_utc={f"{4*i:02d}:00":int(slots[i]) for i in range(6)},
        most_common_utc_close=f"{int(np.argmax(slots))*4:02d}:00",
        max_day_share_pct=round(observed_max*100,2),
        random_max_day_share_mean_pct=round(float(np.mean(perm_max_day))*100,2),
        adjusted_p_any_weekday=round(float((1+np.sum(perm_max_day>=observed_max))/(PERM_N+1)),4),
        adjusted_p_weekday_spread=round(float((1+np.sum(perm_spread>=observed_spread))/(PERM_N+1)),4),
        max_hour_share_pct=round(observed_utc*100,2),
        adjusted_p_any_4h_utc_slot=round(float((1+np.sum(perm_max_time>=observed_utc))/(PERM_N+1)),4),
        year_look=yrparts,
        null="One independent random day/hour phase for all coins per calendar week, preserves shared market shocks and week activity",
        permutations=PERM_N)


def direction_weekdays(events):
    return {("blue_positive" if side==1 else "red_negative"):
         {WEEKDAY[i]:int(np.sum(utc_parts(events[events[:,1]==side])[0]==i))
                      for i in range(7)}
             for side in (1,-1)}


def optional_pairs(base,others,market_data,version,event,start,end):
    result={}
    anchor=base["BTCUSDT"][event]
    for sym in OPTIONAL:
        if sym not in others:
            continue
        t=others[sym][event]
        sm=max(start,int(market_data[sym]["t"][peaks.WARMUP]))
        em=min(end,int(market_data[sym]["t"][-1]+STEP))
        a=in_period(anchor,sm,em)
        b=in_period(t,sm,em)
        if len(a)<4:
            continue
        result[sym]=dict(n_btc=len(a),n_other=len(b),
            same_direction_within_8h=round(float(np.mean(matching(a,b,2)))*100,2),
            same_direction_within_12h=round(float(np.mean(matching(a,b,3)))*100,2),
            comparable_range=[dt.datetime.fromtimestamp(sm/1000,dt.timezone.utc).date().isoformat(),
                              dt.datetime.fromtimestamp(em/1000,dt.timezone.utc).date().isoformat()])
    return result


def main():
    data=peaks.load_all()
    start,end=common_period(data)
    results={}
    for version in VERSIONS:
        event_map={sym:event_arrays(d,version) for sym,d in data.items()}
        core={sym:{name:in_period(e[name],start,end) for name in EVENTS}
              for sym,e in event_map.items() if sym in ASSETS}
        result={}
        for name in EVENTS:
            anchor=core["BTCUSDT"][name]
            others={s:core[s][name] for s in ASSETS if s!="BTCUSDT"}
            matches={}
            for span in WINDOW_BARS:
                z,_=score_anchor(anchor,others,span)
                matches[f"+/-{span*4}h"]=z
            important_null=shared_shock_null(anchor,others,start,end,2)
            all_events=np.vstack([core[s][name] for s in ASSETS])
            calendar=time_rate(all_events)
            per_asset_week={sym:dict(day_counts={WEEKDAY[i]:int(np.sum(utc_parts(core[sym][name])[0]==i))
                           for i in range(7)},
                            strongest_day=WEEKDAY[int(np.argmax(np.bincount(utc_parts(core[sym][name])[0],minlength=7)))],
                            n=len(core[sym][name])) for sym in ASSETS}
            result[name]=dict(anchors_BTC_count=len(anchor),synchronized_by_window=matches,
                permutation_null_8h=important_null,
                weekday_UTC=calendar,
                weekday_by_asset=per_asset_week,
                weekday_by_direction=direction_weekdays(all_events),
                secondary_delisted_TON_and_new_GRAM=optional_pairs(core,event_map,data,version,name,start,end))
            print("SYNCHRONY_CASE",json.dumps(dict(version=version,event=name,
                windows={k:dict(n=v["anchors"],matched_5_of_7=v["at_least_5_of_7_pct"],
                                matched_4_of_7=v["at_least_4_of_7_pct"],
                                per_alt=v["each_asset_pct"]) for k,v in matches.items()},
                null=result[name]["permutation_null_8h"]["permutation"],
                weekday={k:calendar[k] for k in ("weekday_counts","peak_days",
                      "adjusted_p_any_weekday","adjusted_p_weekday_spread",
                      "most_common_utc_close","adjusted_p_any_4h_utc_slot","year_look")},
                ton_gram=result[name]["secondary_delisted_TON_and_new_GRAM"]),
                ensure_ascii=False),flush=True)
        results[version]=result
    report=dict(title="Seven-asset DeltaRSI sign-flip and histogram high/low peak synchronization plus weekday effect",
        run_id=os.environ.get("GITHUB_RUN_ID","local"),
        sha=os.environ.get("GITHUB_SHA","local"),
        source="Frozen 4h futures candles from previous GitHub Releases, no exchange download",
        price_extreme="max High or min Low within +/-3 4h bars around largest signed histogram column, hindsight-only",
        first_utc=dt.datetime.fromtimestamp(start/1000,dt.timezone.utc).isoformat(),
        last_utc=dt.datetime.fromtimestamp(end/1000,dt.timezone.utc).isoformat(),
        market_core=ASSETS,
        side_assets=OPTIONAL,
        null_permutations=PERM_N,
        event_bar_time="Delta sign flip timestamp is close of just-completed 4h candle; price extreme is its candle OPEN as exact intra-bar hour unknown",
        overlap_windows_hours=[w*4 for w in WINDOW_BARS],
        indicator_versions=VERSIONS,
        results=results,
        caveats=[
         "Common cross-asset synchrony can arise from shared BTC and global crypto factors; it does not imply forecastable predictive lead or causality",
         "A synchronized 4h price peak is known only retrospectively; +/-3-bar window uses future candles and is NOT an actionable real-time signal",
         "Same weekday recurrence is assessed with whole-week event cluster-preserving null, not naive independent-event chi-square",
         "With 7 assets cross-coin dependence is real; same-week rotations preserve it for calendar testing",
         "4h bar resolution cannot distinguish exact intra-bar High or Low times: UTC bar-open is a timestamp convention",
         "Separate actual Pine SMA21/RSI12 Delta and RSI27-EMA7; their frequent flip rates imply different chance-match baselines",
         "TONUSDT delisted in June 2026; GRAMUSDT is a separate contract since July 2026; they are NOT part of the seven-asset 3y core",
         "Aug-Oct has been repeatedly inspected, so this exploratory finding is not an independent future market timing edge",
         "UTC days, not Amsterdam local days: conversions may move events across midnight or weekend at DST change",
         "Random-shift null preserves within-coin event autocorrelation but assumes cross-market alignment absent under null",
         "No trading execution, funding, prop-compliance or 48h result tested in this file",
        ])
    (ROOT/"WEEKDAY_CROSS_COIN_SYNCHRONY.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    lines=["# DeltaRSI: синхронность смен направления по монетам и дни недели","",
       f"Период: {report['first_utc']} — {report['last_utc']}.",
       "7 сопоставимых контрактов BTC ETH BNB XRP LINK ICP ZEC; TON/GRAM только отдельно.",
       "Все времена UTC. Смена знака ставится в момент ЗАКРЫТИЯ 4h, ценовой High/Low — на дату свечи.",
       "Синхронность не означает предсказуемость. Статистическая вероятность учитывает случайные сдвиги.",
       "",
       "## Совпадения минимум пяти из семи монет относительно BTC","",
       "| Индикатор | Тип | ±4 ч | ±8 ч | ±12 ч | ±24 ч | Случайно ±8 ч | p-значение |",
       "|---|---|---:|---:|---:|---:|---:|---:|"]
    for version,vr in results.items():
        for kind,r in vr.items():
            spans=r["synchronized_by_window"]
            null=r["permutation_null_8h"]["permutation"]["at_least_5_of_7_pct"]
            lines.append(f"| {version} | {kind} | {spans['+/-4h']['at_least_5_of_7_pct']:.1f}% | "
                f"{spans['+/-8h']['at_least_5_of_7_pct']:.1f}% | "
                f"{spans['+/-12h']['at_least_5_of_7_pct']:.1f}% | "
                f"{spans['+/-24h']['at_least_5_of_7_pct']:.1f}% | "
                f"{null['random_mean']:.1f}% | {null['empirical_one_sided_p']:.4f} |")
    lines+=["","## Сравнение дней недели с сохранением совместных рыночных событий","",
       "| Индикатор | Тип | Чаще всего | День недели: p с коррекцией | Час UTC | Час UTC: p с коррекцией |",
       "|---|---|---|---:|---:|---:|"]
    for version,vr in results.items():
        for kind,r in vr.items():
            d=r["weekday_UTC"]
            lines.append(f"| {version} | {kind} | {', '.join(d['peak_days'][:2])} | "
                  f"{d['adjusted_p_any_weekday']:.4f} | "
                  f"{d['most_common_utc_close']} | {d['adjusted_p_any_4h_utc_slot']:.4f} |")
    lines+=["","**Методология:** 800 независимых круглых сдвигов по монетам для синхронизации; 800 случайных совместных сдвигов рынка отдельно по каждой календарной неделе для часов/дней. Это устраняет наивное предположение, будто совпадения BTC и альткоинов независимы.",
      "",
      "Полные недельные частоты, сравнение по трём годам, календарные таблицы каждого актива, статистика раздельно Blue/Red и TON/GRAM — в JSON.",
      "Контракт TONUSDT после делистинга не используется. Нет нового скачивания свечей или торговли.",
      "Важное ограничение: пики High/Low получены задним числом; 4h High/Low не содержит точного часа экстремума внутри свечи."]
    (ROOT/"WEEKDAY_CROSS_COIN_SYNCHRONY.md").write_text("\n".join(lines)+"\n")
    print("SYNC_CALENDAR_SUMMARY",json.dumps(
        {v:{k:dict(five_of_seven_8h=z["synchronized_by_window"]["+/-8h"]["at_least_5_of_7_pct"],
                     expected_five_of_seven_8h=z["permutation_null_8h"]["permutation"]["at_least_5_of_7_pct"]["random_mean"],
                     sync_p=z["permutation_null_8h"]["permutation"]["at_least_5_of_7_pct"]["empirical_one_sided_p"],
                     weekday_top=z["weekday_UTC"]["peak_days"][:2],
                     weekday_p=z["weekday_UTC"]["adjusted_p_any_weekday"],
                     hour_top=z["weekday_UTC"]["most_common_utc_close"],
                     hour_p=z["weekday_UTC"]["adjusted_p_any_4h_utc_slot"])
             for k,z in r.items()} for v,r in results.items()},
        ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
