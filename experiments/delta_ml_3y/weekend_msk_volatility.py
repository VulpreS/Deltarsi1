"""Is BTC/crypto ALWAYS quiet from Friday night to Sunday afternoon/evening MSK?

Descriptive research on immutable Binance USD-M 4h OHLCV cache.
Main window MSK: Friday 03:00 <= t < Sunday 19:00, i.e. 64h (16x4h).
Sensitivity: Fri 03-Sun 15 / Sun 19 / Sun 23 and Sat 03-Mon 03.
Time zone is permanently Europe/Moscow UTC+03:00 (no DST).

Metrics per fully observed ISO week: per-bar root mean square log-return,
mean absolute log-return, mean high-low range, trading volume, whole-window
range/return, risk of BTC 4h 2% and 3% candles and >5% whole-window range.
Paired bootstrap resamples entire weeks; avoids treating synchronized coins
as independent observations. All BTC market regime labels are based on
30-day PAST BTC return before Friday's window, NEVER future outcomes.
No feature leakage, parameter tuning, trading orders or re-download.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT",
        "ICPUSDT","ZECUSDT")
SECONDARY=("TONUSDT","GRAMUSDT")
STEP=4*3600000
TON_DEL=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
MSK_SHIFT=pd.Timedelta(hours=3)
WEEK_BARS=42
BOOT=5000
RNG=np.random.default_rng(20261108)


def clean(sym):
    path=ROOT/"data"/(sym+".json")
    if not path.exists():
        raise FileNotFoundError(f"Archive release must be restored: {path}")
    b=path.read_bytes()
    rows=json.loads(b)
    if sym=="TONUSDT":
        dropped=sum(int(z[0])>=TON_DEL for z in rows)
        if dropped<700:
            raise RuntimeError("Retired TONUSDT audit: expected >700 invalid delisted candles")
        rows=[z for z in rows if z[0]<TON_DEL]
    if len(rows)<200 or any(y[0]-x[0]!=STEP for x,y in zip(rows,rows[1:])):
        raise RuntimeError(f"{sym} data contain gap or insufficient rows")
    d=pd.DataFrame(rows,columns=("ts","open","high","low","close","volume"))
    msk=pd.to_datetime(d.ts,unit="ms",utc=True)+MSK_SHIFT
    d["dow"]=msk.dt.dayofweek.astype(int)
    d["hour"]=msk.dt.hour.astype(int)
    iso=msk.dt.isocalendar()
    d["week"]=iso.year.astype(str)+"-W"+iso.week.astype(str).str.zfill(2)
    d["msk_date"]=msk.dt.strftime("%Y-%m-%d")
    d["r"]=np.log(d.close/d.close.shift(1))
    d["abs_pct"]=100*np.abs(d.r)
    d["range_pct"]=100*(d.high-d.low)/d.open
    d["year"]=msk.dt.year
    d["mom30"]=100*(d.close/d.close.shift(180)-1)
    d["window"]=(d.dow>=4)&((d.dow<=5)|((d.dow==6)&(d.hour<19)))
    d["fri_first"]=(d.dow==4)&(d.hour<15)
    d["fri_second"]=(d.dow==4)&(d.hour>=15)
    d["sat_sun"]=(d.dow==5)|((d.dow==6)&(d.hour<19))
    d["sun_late"]=(d.dow==6)&(d.hour>=19)
    d["weekend_48"]=(d.dow==5)|(d.dow==6)
    return d,dict(first=pd.to_datetime(d.ts.iloc[0],unit="ms",utc=True).isoformat(),
       last=pd.to_datetime(d.ts.iloc[-1],unit="ms",utc=True).isoformat(),
       source_sha256=hashlib.sha256(b).hexdigest(),rows=len(rows))


def stats(a):
    return dict(
        bars=len(a),
        mean_abs_pct=float(a.abs_pct.mean()),
        mean_range_pct=float(a.range_pct.mean()),
        rms_ret_pct=float(100*np.sqrt(np.mean(a.r.to_numpy()**2))),
        mean_volume=float(a.volume.mean()),
        total_volume=float(a.volume.sum()),
        large_1pct_bars=int((a.abs_pct>=1).sum()),
        large_2pct_bars=int((a.abs_pct>=2).sum()),
        large_3pct_bars=int((a.abs_pct>=3).sum()),
        total_highlow_pct=float(100*(a.high.max()/a.low.min()-1)),
        net_abs_pct=float(100*abs(a.close.iloc[-1]/a.open.iloc[0]-1))
    )


def weekwise(d):
    records=[]
    for week,g in d.groupby("week",sort=True):
        if len(g)!=WEEK_BARS or g.r.isna().any():
            continue
        if sorted(g.dow.value_counts().tolist())!=[6]*7:
            continue
        s=g[g.window]
        other=g[~g.window]
        if len(s)!=16 or len(other)!=26:
            raise RuntimeError(f"Weekend MSK candle alignment error {week}, {len(s)}")
        sstat=stats(s)
        o=stats(other)
        sat_sun=stats(g[g.sat_sun])
        friday_first=stats(g[g.fri_first])
        friday_second=stats(g[g.fri_second])
        sunday_late=stats(g[g.sun_late])
        early_sunday=g[(g.dow==6)&(g.hour<15)]
        late_sunday=g[(g.dow==6)&(g.hour>=19)]
        friday_to_sun15=pd.concat([g[(g.dow==4)|(g.dow==5)],early_sunday])
        sun23=pd.concat([s,g[(g.dow==6)&(g.hour==19)]])
        sat_to_mon=stats(g[g.weekend_48])
        mon_wed=stats(g.iloc[0:16])
        early=stats(friday_to_sun15)
        later=stats(sun23)
        # 30d price change at very first Friday MSK candle; no future.
        fri=g[(g.dow==4)&(g.hour==3)]
        mom=float(fri.mom30.iloc[0]) if len(fri) else np.nan
        regime="UP_8PCT" if mom>=8 else ("DOWN_8PCT" if mom<=-8 else "FLAT_8PCT")
        records.append(dict(
            week=week,year=int(g.year.mode().iloc[0]),mom30_before_friday_pct=mom,
            regime=regime,
            weekend_rms=sstat["rms_ret_pct"],outside_rms=o["rms_ret_pct"],
            weekend_abs=sstat["mean_abs_pct"],outside_abs=o["mean_abs_pct"],
            weekend_range_mean=sstat["mean_range_pct"],outside_range_mean=o["mean_range_pct"],
            weekend_vol=sstat["mean_volume"],outside_vol=o["mean_volume"],
            weekend_64h_range=sstat["total_highlow_pct"],
            weekend_64h_net_abs=sstat["net_abs_pct"],
            weekday_mon_wed_64h_range=mon_wed["total_highlow_pct"],
            large_1=sstat["large_1pct_bars"],
            large_2=sstat["large_2pct_bars"],
            large_3=sstat["large_3pct_bars"],
            friday_first_rms=friday_first["rms_ret_pct"],
            friday_second_rms=friday_second["rms_ret_pct"],
            satsun_rms=sat_sun["rms_ret_pct"],
            sunday_late_rms=sunday_late["rms_ret_pct"],
            friday_to_sun15_rms=early["rms_ret_pct"],
            friday_to_sun23_rms=later["rms_ret_pct"],
            sat_to_mon_rms=sat_to_mon["rms_ret_pct"]
        ))
    return pd.DataFrame(records)


def summary(w):
    if not len(w):
        return dict(weeks=0)
    weekr=w.weekend_rms.to_numpy()
    outs=w.outside_rms.to_numpy()
    ab=w.weekend_abs.to_numpy()
    ao=w.outside_abs.to_numpy()
    vol=w.weekend_vol.to_numpy()
    volout=w.outside_vol.to_numpy()
    idx=RNG.integers(0,len(w),size=(BOOT,len(w)))
    # Weekly-block bootstrap preserving paired within-week comparisons.
    # Average squared 4h return in weekend and outside; convert to RMS.
    ratio=np.sqrt(np.mean(weekr[idx]**2,axis=1)/np.mean(outs[idx]**2,axis=1))
    ratio_abs=np.mean(ab[idx],axis=1)/np.mean(ao[idx],axis=1)
    ratio_vol=np.mean(vol[idx],axis=1)/np.mean(volout[idx],axis=1)
    weekend_ratio=np.sqrt(float(np.mean(weekr**2)/np.mean(outs**2)))
    exc=(w.weekend_64h_range>=5)
    biggest=w.nlargest(8,"weekend_64h_range")
    return dict(weeks=len(w),
        weekend_4h_rms_pct=round(float(np.sqrt(np.mean(weekr**2))),4),
        other_4h_rms_pct=round(float(np.sqrt(np.mean(outs**2))),4),
        volatility_ratio=round(weekend_ratio,4),
        volatility_ratio_ci95=[round(float(x),4) for x in np.percentile(ratio,[2.5,97.5])],
        mean_abs_ratio=round(float(np.mean(ab)/np.mean(ao)),4),
        abs_ratio_ci95=[round(float(x),4) for x in np.percentile(ratio_abs,[2.5,97.5])],
        mean_volume_ratio=round(float(np.mean(vol)/np.mean(volout)),4),
        volume_ratio_ci95=[round(float(x),4) for x in np.percentile(ratio_vol,[2.5,97.5])],
        fraction_weekend_rms_lower_than_rest_pct=round(float(100*np.mean(weekr<outs)),1),
        fraction_weekend_rms_higher_than_rest_pct=round(float(100*np.mean(weekr>outs)),1),
        fraction_weekend_rms_more_than_1p5x_pct=round(float(100*np.mean(weekr>1.5*outs)),1),
        fraction_weekend_rms_below_0p75x_pct=round(float(100*np.mean(weekr<.75*outs)),1),
        fraction_satsun_rms_lower_than_rest_pct=round(float(100*np.mean(w.satsun_rms<outs)),1),
        big_4h_1pct_week_pct=round(float(100*np.mean(w.large_1>0)),1),
        big_4h_2pct_week_pct=round(float(100*np.mean(w.large_2>0)),1),
        big_4h_3pct_week_pct=round(float(100*np.mean(w.large_3>0)),1),
        weekend_64h_range_median_pct=round(float(w.weekend_64h_range.median()),3),
        weekend_64h_range_p75_pct=round(float(w.weekend_64h_range.quantile(.75)),3),
        weekend_64h_range_p90_pct=round(float(w.weekend_64h_range.quantile(.90)),3),
        weekend_64h_range_gte_3_pct=round(float(100*np.mean(w.weekend_64h_range>=3)),1),
        weekend_64h_range_gte_5_pct=round(float(100*exc.mean()),1),
        weekend_64h_range_gte_8_pct=round(float(100*np.mean(w.weekend_64h_range>=8)),1),
        weekend_64h_range_gte_10_pct=round(float(100*np.mean(w.weekend_64h_range>=10)),1),
        weekend_64h_range_higher_than_monday_wednesday_pct=round(float(100*np.mean(w.weekend_64h_range>w.weekday_mon_wed_64h_range)),1),
        subperiods_rms_relative_to_nonwindow={
          name:round(float(np.sqrt(np.mean(w[name]**2)/np.mean(outs**2))),3)
          for name in ("friday_first_rms","friday_second_rms","satsun_rms","sunday_late_rms",
                       "friday_to_sun15_rms","friday_to_sun23_rms","sat_to_mon_rms")},
        exceptional_top8=[dict(week=z.week,range_pct=round(float(z.weekend_64h_range),2),
                         abs_net_pct=round(float(z.weekend_64h_net_abs),2),
                         rms_ratio=round(float(z.weekend_rms/z.outside_rms),2),
                         had_2pct_bar=bool(z.large_2>0)) for z in biggest.itertuples()])


def weekday_stats(d):
    # Per-week volume normalization so a year with more trading volume
    # cannot dominate the day-of-week volume comparison.
    d=d.copy()
    d["vol_week_mean"]=d.groupby("week").volume.transform("mean")
    d["vol_relative"]=d.volume/d.vol_week_mean.replace(0,np.nan)
    r={}
    for day in range(7):
        p=d[d.dow==day]
        r[("Mon","Tue","Wed","Thu","Fri","Sat","Sun")[day]]=dict(
          candles=len(p),
          mean_abs_pct=round(float(p.abs_pct.mean()),4),
          rms_return_pct=round(float(100*np.sqrt(np.nanmean(p.r**2))),4),
          mean_candle_range_pct=round(float(p.range_pct.mean()),4),
          volume_vs_same_week_avg=round(float(p.vol_relative.mean()),3))
    return r


def by_subperiod(w):
    out={}
    # Compare three broad calendar eras, then explicit market regime.
    groups={"2024":w[(w.year==2024)],
            "2025":w[(w.year==2025)],
            "2026":w[(w.year==2026)]}
    for phase in ("UP_8PCT","DOWN_8PCT","FLAT_8PCT"):
        groups["BTC_30d_"+phase]=w[w.regime==phase]
    for k,z in groups.items():
        if len(z)>=8:
            s=summary(z)
            out[k]={name:s.get(name) for name in (
                "weeks","volatility_ratio","volatility_ratio_ci95",
                "fraction_weekend_rms_lower_than_rest_pct",
                "fraction_weekend_rms_more_than_1p5x_pct",
                "weekend_64h_range_gte_5_pct")}
    return out


def main():
    report=dict(title="Weekend crypto volatility: Friday night to Sunday evening Moscow time",
        run_id=os.environ.get("GITHUB_RUN_ID","local"),
        sha=os.environ.get("GITHUB_SHA","local"),
        baseline_source="Immutable 4h Binance USD-M Binance Vision GitHub Releases. NO new candle downloads.",
        timezone="MSK UTC+03:00 fixed, no DST",
        main_window="Friday 03:00 MSK (4h Binance bar opening) through Sunday 19:00 MSK (exclusive), 16 bars=64h",
        alternate_windows=["Friday 03:00 to Sunday 15:00 MSK 60h",
                           "Friday 03:00 to Sunday 23:00 MSK 68h",
                           "Saturday 03:00 to Monday 03:00 MSK 48h",
                           "Friday 03:00-15:00 vs Fri15:00-Sat03:00 vs Sat03:00-Sun19:00 vs Sunday19:00-Monday03:00"],
        quote="volatility ratio = sqrt(mean of weekend 4h log-return squared / mean of remaining weekly 4h log-return squared)",
        typical_question="Is the Friday night to Sunday evening MSK period ALWAYS less volatile?",
        market_regime_def="BTC price change in last 180 closed 4h candles before first Friday bar; >+8% bullish, <-8% bearish, else neutral; descriptive only",
        statistical_model="paired complete ISO weeks, 5000 bootstrapped week resamples with replacement",
        results={},sources={},
        caveats=[
           "Low volatility on average is not an absolute calendar rule: events, liquidations or weekend news can trigger large moves",
           "4h source candle boundaries are at 03,07,11,15,19,23 MSK, so Friday00 / Sunday evening are approximated with full candles; 1h/tick needed for more exact boundaries",
           "RMS of returns measures price movement, while high-low range and exchange volume are separate facets",
           "UTC 4h Binance kline volume does not distinguish aggressive buyers/sellers or open interest",
           "BTC plus altcoin evidence is correlated: count weeks rather than coins as independent samples",
           "2026 data end Oct 27 and may not represent subsequent market regime",
           "TON was delisted and truncated, GRAM newly listed, both secondary not pooled with seven continuous assets",
           "No funding, intrabar sequence, leverage or actual prop trading equity; descriptive only",
           "Weekday and sub-session comparisons were inspired by user observation: exploratory, not independent OOS",
        ])
    all_data={}
    for symbol in ASSETS+SECONDARY:
        d,meta=clean(symbol)
        all_data[symbol]=d
        report["sources"][symbol]=meta
    btc=all_data["BTCUSDT"]
    btc_week=weekwise(btc)
    btc_regime=btc_week.set_index("week").regime
    for symbol,d in all_data.items():
        w=weekwise(d)
        if symbol!="BTCUSDT":
            w["regime"]=w.week.map(btc_regime).fillna("UNCLASSIFIED")
        report["results"][symbol]=dict(
          market_is_secondary=symbol in SECONDARY,
          all_weeks=summary(w),
          by_2024_2025_2026_and_BTC_regime=by_subperiod(w),
          seven_weekdays=weekday_stats(d),
          weekly_metrics=[dict(week=z.week,year=int(z.year),
                regime=z.regime,
                weekend_4h_rms=round(float(z.weekend_rms),4),
                other_4h_rms=round(float(z.outside_rms),4),
                ratio=round(float(z.weekend_rms/z.outside_rms),4),
                high_low_range_pct=round(float(z.weekend_64h_range),3),
                max_4h_2pct_bar=bool(z.large_2>0),
                window_64h_net_abs_pct=round(float(z.weekend_64h_net_abs),3))
                  for z in w.itertuples()])
        one=report["results"][symbol]["all_weeks"]
        print("WEEKEND_VOLATILITY_ASSET",json.dumps(dict(symbol=symbol,
          weeks=one["weeks"],ratio=one["volatility_ratio"],
          ci=one["volatility_ratio_ci95"],
          lower_week_pct=one["fraction_weekend_rms_lower_than_rest_pct"],
          range5pct_week_pct=one["weekend_64h_range_gte_5_pct"],
          high_satsun_pct=one["subperiods_rms_relative_to_nonwindow"]["satsun_rms"],
          subperiods=one["subperiods_rms_relative_to_nonwindow"],
          yearly={key:{k:v for k,v in z.items() if k in (
            "weeks","volatility_ratio","fraction_weekend_rms_lower_than_rest_pct")}
            for key,z in report["results"][symbol]["by_2024_2025_2026_and_BTC_regime"].items()}),
          ensure_ascii=False),flush=True)
    (ROOT/"WEEKEND_MSK_VOLATILITY.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    lines=["# Рынок криптовалют с ночи пятницы до вечера воскресенья по МСК",
      "",
      "Исследовано на сохранённых исторических 4H-свечах. Никаких новых данных с биржи не скачивалось.",
      "**Главное окно:** пятница 03:00 → воскресенье 19:00 MSK (64 часа, 16 полностью попадающих 4H свечей).",
      "Базовый эталон — остальные 26 четырёхчасовых свечей **той же недели**. RMS log returns, отдельно диапазон High/Low и объём.",
      "Доверительные интервалы получены по неделям, а не путём ошибочного предположения независимости свечей или монет.",
      "",
      "| Монета | Полных недель | Выходные / остальная неделя, волатильность | 95% интервал | В скольких неделях выходные спокойнее | 64ч High/Low ≥5% |",
      "|---|---:|---:|---|---:|---:|"]
    for symbol in ASSETS:
        z=report["results"][symbol]["all_weeks"]
        lo,hi=z["volatility_ratio_ci95"]
        lines.append(f"| {symbol[:-4]} | {z['weeks']} | {z['volatility_ratio']:.3f}× | "
           f"[{lo:.3f}; {hi:.3f}] | {z['fraction_weekend_rms_lower_than_rest_pct']:.1f}% | "
           f"{z['weekend_64h_range_gte_5_pct']:.1f}% |")
    lines+=["","## BTC: дни недели и крупные исключения","",
      "| День МСК | RMS 4h движения, % | Свечной диапазон, % | Относительный объём |",
      "|---|---:|---:|---:|"]
    for day,z in report["results"]["BTCUSDT"]["seven_weekdays"].items():
        lines.append(f"| {day} | {z['rms_return_pct']:.3f}% | {z['mean_candle_range_pct']:.3f}% | {z['volume_vs_same_week_avg']:.3f}× |")
    lines+=["","**Важное:** частота 5% High/Low за весь период измеряет максимальную внутриокновую амплитуду, а не чистую доходность позиции.",
      "Период 64ч не обязан быть менее волатильным, чем неделя, даже если статистически средние значения ниже.",
      "",
      "### 8 самых волатильных пятниц–воскресений BTC",""]
    for z in report["results"]["BTCUSDT"]["all_weeks"]["exceptional_top8"]:
        lines.append(f"- {z['week']}: High/Low {z['range_pct']:.2f}%, чистое абсолютное движение {z['abs_net_pct']:.2f}%, RMS weekend/other {z['rms_ratio']:.2f}×.")
    lines+=["","## Устойчивость по годам и BTC-рынку","",
       "В JSON сохранено разделение по 2024/2025/2026, а также по состоянию BTC за 30 дней ДО начала каждой пятницы.",
       "Дополнительные окна: Fri03–Sun15, Fri03–Sun23, Sat03–Mon03; отдельные ранняя пятница, вечер пятницы, суббота+воскресенье до 19, позднее воскресенье.",
       "Все времена — MSK, фиксированное UTC+3. Торговые стратегии, история свечей, прошлые результаты и форвард не изменены."]
    (ROOT/"WEEKEND_MSK_VOLATILITY.md").write_text("\n".join(lines)+"\n")
    print("WEEKEND_BTC_SUMMARY",json.dumps(report["results"]["BTCUSDT"]["all_weeks"],ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
