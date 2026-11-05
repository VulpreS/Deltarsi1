"""Robustness tests for cross-coin DeltaRSI timing alignment.

Preserve earlier first-run analysis, add stricter null that circularly
randomizes event timestamp WITHIN each calendar month, preserving monthly
volatility regimes and each coin's local frequency of switches. Also
separately report positive->negative and negative->positive, thirds of
the 3-year history, and altcoin lead/lag relative to BTC.

Only existing GitHub Release Binance 4h data, no exchange downloads.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import os
import numpy as np

import weekday_cross_coin_synchrony as sync
from train import ROOT

N=900
RNG=np.random.default_rng(2026110502)
SPLITS=sync.CUTOFFS
ASSETS=sync.ASSETS
VERSIONS=sync.VERSIONS
KINDS=sync.EVENTS
STEP=sync.STEP


def month_start(ms):
    z=dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc)
    return int(dt.datetime(z.year,z.month,1,tzinfo=dt.timezone.utc).timestamp()*1000)


def next_month(ms):
    z=dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc)
    y,m=(z.year+1,1) if z.month==12 else (z.year,z.month+1)
    return int(dt.datetime(y,m,1,tzinfo=dt.timezone.utc).timestamp()*1000)


def monthly_rotate(evt):
    """Preserve event count in each month and clustering within month."""
    out=evt.copy()
    # Vectorize month grouping instead of recomputing datetime.fromtimestamp
    # for each event for each of 900 permutations.
    months=evt[:,0].astype("datetime64[ms]").astype("datetime64[M]")
    unique,idx=np.unique(months,return_inverse=True)
    for j,month in enumerate(unique):
        mask=(idx==j)
        start=int(month.astype("datetime64[ms]").astype(np.int64))
        next_start=int((month+np.timedelta64(1,"M")).astype("datetime64[ms]").astype(np.int64))
        length=(next_start-start)//STEP
        offset=int(RNG.integers(8,length-8))
        out[mask,0]=start+(((evt[mask,0]-start)//STEP+offset)%length)*STEP
    return out[np.argsort(out[:,0])]


def test_month_preserving(anchor,others):
    actual,_=sync.score_anchor(anchor,others,2)
    samples=np.empty((N,3),dtype=float)
    for i in range(N):
        fake={s:monthly_rotate(ev) for s,ev in others.items()}
        z,_=sync.score_anchor(anchor,fake,2)
        samples[i]=[z["at_least_4_of_7_pct"],z["at_least_5_of_7_pct"],z["all_7_pct"]]
    out={}
    for i,name in enumerate(("at_least_4_of_7_pct","at_least_5_of_7_pct","all_7_pct")):
        obs=actual[name];dist=samples[:,i]
        out[name]=dict(observed=obs,monthly_null_mean=round(float(np.mean(dist)),3),
            monthly_null_p95=round(float(np.percentile(dist,95)),3),
            empirical_p=round(float((1+sum(dist>=obs))/(N+1)),5))
    return out


def lead_lag(a,b):
    """Signed lag of the nearest ALT event matching BTC's new sign."""
    all_lags=[]
    for side in (-1,1):
        aa=a[a[:,1]==side]
        bb=b[b[:,1]==side]
        if not len(bb):
            continue
        ta=(aa[:,0]//STEP).astype(np.int64)
        tb=(bb[:,0]//STEP).astype(np.int64)
        i=np.searchsorted(tb,ta)
        left=tb[np.clip(i-1,0,len(tb)-1)]
        right=tb[np.clip(i,0,len(tb)-1)]
        best=np.where(np.abs(right-ta)<np.abs(left-ta),right,left)
        lag=(best-ta)*4
        all_lags.extend(lag[np.abs(lag)<=12].tolist())
    if not all_lags:
        return dict(n=0)
    x=np.asarray(all_lags)
    return dict(n=len(x),same_4h_bar_pct=round(float(np.mean(x==0))*100,2),
         alt_after_BTC_pct=round(float(np.mean(x>0))*100,2),
         alt_before_BTC_pct=round(float(np.mean(x<0))*100,2),
         median_lag_h=float(np.median(x)),
         avg_lag_h=round(float(np.mean(x)),2),
         counts_by_lag={str(v):int(np.sum(x==v)) for v in range(-12,13,4)})


def by_year(a,others):
    year={}
    for label,begin,end in SPLITS:
        s=sync.timestamp(begin);e=sync.timestamp(end)
        anchor=sync.in_period(a,s,e)
        o={sym:sync.in_period(z,s,e) for sym,z in others.items()}
        if len(anchor)==0:
            continue
        score,counts=sync.score_anchor(anchor,o,2)
        year[label]=dict(BTC_anchors=len(anchor),
            matched_4plus_pct=score["at_least_4_of_7_pct"],
            matched_5plus_pct=score["at_least_5_of_7_pct"],
            matched_all7_pct=score["all_7_pct"])
    return year


def direction(a,others):
    ans={}
    for side,label in ((1,"new_blue_positive"),(-1,"new_red_negative")):
        aa=a[a[:,1]==side]
        bb={s:o[o[:,1]==side] for s,o in others.items()}
        r,_=sync.score_anchor(aa,bb,2)
        ans[label]=dict(events=r["anchors"],matched_5_of_7_pct=r["at_least_5_of_7_pct"],
            matched_all7_pct=r["all_7_pct"])
    return ans


def anchor_examples(a,others,n=8):
    examples=[]
    metric,counts=sync.score_anchor(a,others,2)
    candidates=np.flatnonzero(counts>=5)
    for ix in candidates[-n:]:
        anchor=a[ix:ix+1]
        matched=[s for s,o in others.items() if sync.matching(anchor,o,2)[0]]
        examples.append(dict(time_utc=dt.datetime.fromtimestamp(
               int(a[ix,0])/1000,dt.timezone.utc).isoformat(),
               direction="blue_positive" if a[ix,1]==1 else "red_negative",
               coins=["BTC"]+[s[:-4] for s in matched],
               count=len(matched)+1))
    return examples


def symmetric_check(events):
    score={}
    for target in ASSETS:
        others={k:v for k,v in events.items() if k!=target}
        z,_=sync.score_anchor(events[target],others,2)
        score[target]=dict(events=z["anchors"],aligned_5plus_pct=z["at_least_5_of_7_pct"],
            aligned_4plus_pct=z["at_least_4_of_7_pct"])
    return score


def main():
    data=sync.peaks.load_all()
    start,end=sync.common_period(data)
    results={}
    for version in VERSIONS:
        events={s:sync.event_arrays(data[s],version) for s in ASSETS}
        result={}
        for name in KINDS:
            e={s:sync.in_period(events[s][name],start,end) for s in ASSETS}
            a=e["BTCUSDT"]
            others={s:e[s] for s in ASSETS if s!="BTCUSDT"}
            out=dict(monthly_shuffle=test_month_preserving(a,others),
                     by_year=by_year(a,others),
                     direction=direction(a,others),
                     pair_lead_lag={s:lead_lag(a,v) for s,v in others.items()},
                     symmetrical_anchor_check=symmetric_check(e),
                     recent_examples_5plus=anchor_examples(a,others),
                     note="Calendar shuffle preserves each coin monthly sign-change frequency and most within-month clustering; cross-coin correlation destroyed. Year analysis split into 3 nonoverlapping blocks.")
            result[name]=out
            print("SYNCHRONY_ROBUSTNESS",json.dumps(dict(version=version,event=name,
                monthnull=out["monthly_shuffle"]["at_least_5_of_7_pct"],
                by_year=out["by_year"],
                by_direction=out["direction"],
                lead_lag={s:{k:v[k] for k in ("same_4h_bar_pct","alt_after_BTC_pct","median_lag_h")}
                           for s,v in out["pair_lead_lag"].items()},
                symmetry={s:v["aligned_5plus_pct"] for s,v in out["symmetrical_anchor_check"].items()},
                examples=out["recent_examples_5plus"][-4:]),
                ensure_ascii=False),flush=True)
        results[version]=result
    report=dict(title="Robustness of common DeltaRSI cross-coin time and calendar synchronization",
       base_run_source="41991118432",run_id=os.environ.get("GITHUB_RUN_ID","local"),
       sample_size=N,
       source="Previously cached 4h Binance futures; no market downloads",
       same_coin_event_clustering_preserved=True,
       monthly_activity_regime_preserved=True,
       in_sample_observational=True,
       results=results,
       limitations=[
           "Month shuffle preserves counts and within-month spacing except at boundaries; null is approximate, not a perfect stationary stochastic process",
           "Many crypto coins are correlated, so same-time moves are expected; this validates co-movement, not causality or predictable triggers",
           "4h time resolution masks intrabar ordering, especially when nearest lags equal 0",
           "BTC anchor matching can re-use an alt event across adjacent anchors; reported frequencies are event alignments, not disjoint cycles",
           "Price peaks are selected with future +/-3 4h bars, are retrospectively dated, and are NOT available as entry signals",
           "All timestamps UTC; local weekday patterns can shift with time zones and daylight saving",
           "Wave signs use both user RSI27-EMA7 and original root Pine SMA21-RSI12, which have different event rates",
           "Excludes expired TONUSDT and recently listed GRAMUSDT from 7-coin full-period core",
           "Not a validated time-of-week trading edge or indication of a certain next reversal date",
       ])
    (ROOT/"SYNCHRONY_ROBUSTNESS.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    lines=["# Повторная проверка: действительно ли пики и смены знака совпадают?","",
        "Строгий контроль: перемешивание времени отдельно внутри каждого месяца, с сохранением частоты событий каждой монеты.",
        "Измеряется процент BTC-событий, для которых одновременно минимум 5 из 7 монет показывают событие того же знака с точностью +/-8 часов.",
        "",
        "| Индикатор | Событие | Реально | Случайно при месячном сохранении режима | p |",
        "|---|---|---:|---:|---:|"]
    for version,result in results.items():
        for kind,z in result.items():
            d=z["monthly_shuffle"]["at_least_5_of_7_pct"]
            lines.append(f"| {version} | {kind} | {d['observed']:.2f}% | "
                         f"{d['monthly_null_mean']:.2f}% | {d['empirical_p']:.5f} |")
    lines+=["","## Повторяемость по трём годам","",
            "| Версия | Событие | Период | BTC-событий | 5+/7 в +/-8ч |",
            "|---|---|---|---:|---:|"]
    for v,r in results.items():
        for kind,z in r.items():
            for per,d in z["by_year"].items():
                lines.append(f"| {v} | {kind} | {per} | {d['BTC_anchors']} | {d['matched_5plus_pct']:.2f}% |")
    lines+=["","Пары направления вверх/вниз, таблица лидирования BTC/альткоинов и конкретные примеры UTC находятся в JSON.",
        "Совпадения не являются заранее известными торговыми сигналами. Пики цены требуют окна +/-3 свечи и видны ретроспективно.",
        "Дни недели исследованы отдельно: общий недельный ритм и синхронизация между монетами НЕ одно и то же."]
    (ROOT/"SYNCHRONY_ROBUSTNESS.md").write_text("\n".join(lines)+"\n")
    print("MONTHLY_NULL_SYNC_COMPLETE",json.dumps(
        {v:{kind:z["monthly_shuffle"]["at_least_5_of_7_pct"]
            for kind,z in r.items()} for v,r in results.items()},ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
