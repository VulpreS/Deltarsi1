"""Sensitivity analysis: cross-coin price extrema chosen strictly INSIDE own sign-wave.

Prevents +/-3 bar windows around fast RSI27 peaks from assigning neighboring
positive and negative waves the same 4h price bar, an artifact previously
observed in ~19% of RSI27 price high/low pairs.

Same 7 coins, same +/-8h BTC-anchor matching; monthly regime-preserving
random time shifts; weekday and example dates. Does not replace the
unrestricted +/-3-bar user definition, reports it as independent check.
"""
import collections
import datetime as dt
import json
import os
import numpy as np

import weekday_cross_coin_synchrony as base
import synchrony_robustness as strictnull
from train import ROOT

ASSETS=base.ASSETS
VERSIONS=base.VERSIONS
STEP=base.STEP


def clipped_events(market,version,radius=3):
    h=base.peaks.histogram(market["close"],version)
    runs=base.peaks.sign_runs(h)
    results=[]
    for r in runs:
        start,end,side=r["start"],r["end"],r["side"]
        p=start+int(np.argmax(np.abs(h[start:end])))
        left=max(start,p-radius)
        right=min(end-1,p+radius)
        if left>right:
            continue
        prices=market["high"][left:right+1] if side>0 else market["low"][left:right+1]
        k=left+int(np.argmax(prices) if side>0 else np.argmin(prices))
        results.append((int(market["t"][k]),int(side)))
    return np.asarray(results,dtype=np.int64).reshape(-1,2)


def calculate():
    data=base.peaks.load_all()
    start,end=base.common_period(data)
    results={}
    for version in VERSIONS:
        all_events={s:base.in_period(clipped_events(data[s],version),start,end)
                    for s in ASSETS}
        anchor=all_events["BTCUSDT"]
        others={s:e for s,e in all_events.items() if s!="BTCUSDT"}
        metrics,_=base.score_anchor(anchor,others,2)
        nulldist=strictnull.test_month_preserving(anchor,others)
        grouped=np.vstack([all_events[s] for s in ASSETS])
        day=base.time_rate(grouped)
        result=dict(
            BTC_events=len(anchor),
            same_side_5of7_within_8h_pct=metrics["at_least_5_of_7_pct"],
            per_asset_match_pct=metrics["each_asset_pct"],
            no_monthly_null=nulldist["at_least_5_of_7_pct"],
            strict_within_own_sign_run=True,
            weekdays=day["weekday_counts"],
            top_weekdays=day["peak_days"],
            weekday_anyday_adjusted_p=day["adjusted_p_any_weekday"],
            sample_recent= strictnull.anchor_examples(anchor,others,6),
            distinct_price_extreme_timestamps={sym:dict(events=len(a),
                unique_4h_bars=len(np.unique(a[:,0])),
                duplicate_event_bars=int(len(a)-len(np.unique(a[:,0]))))
                for sym,a in all_events.items()},
        )
        results[version]=result
        print("CLIPPED_PIVOT_SIGN_SYNCHRONY",json.dumps(dict(
            version=version,match_5of7=result["same_side_5of7_within_8h_pct"],
            monthly_null=result["no_monthly_null"],top_days=result["top_weekdays"],
            day_p=result["weekday_anyday_adjusted_p"],
            unique_bars=result["distinct_price_extreme_timestamps"]["BTCUSDT"]),
            ensure_ascii=False),flush=True)
    output=dict(title="Window-overlap-robust DeltaRSI price pivot synchronization",
        code_sha=os.environ.get("GITHUB_SHA","local"),
        run_id=os.environ.get("GITHUB_RUN_ID","local"),
        original_unrestricted_study_run="41991118432",
        monthly_null_study_run="41991726709",
        definition="peak of signed histogram, choose High (blue) or Low (red) within +/-3 4h bars CLAMPED to its OWN sign run boundaries",
        same_day_label="UTC price candle OPEN, not exact intra-candle price extremum moment",
        results=results,
        caveats=["Changes original +/-3 price window to forbid crossing a histogram sign boundary; this is a robustness test, not a silent revision.",
                 "4h OHLC does not reveal exact intra-bar time of high or low.",
                 "Retired TON and new GRAM excluded from continuous 7-asset pool.",
                 "Peaks are retrospective and cannot be used to predict a turn before histogram sign wave completes.",
                 "Synchrony is cross-correlated response to shared market factors, not proof of profitable predictive calendar timing."])
    (ROOT/"CLIPPED_SIGN_EXTREME_ROBUSTNESS.json").write_text(json.dumps(output,ensure_ascii=False,indent=2))
    lines=["# Контроль перекрывающихся окон ценовых экстремумов","",
          "Обновление исследования по пользователю: High/Low выбираем возле наибольшего столбца синего/красного знака, но строго в пределах того же знака.",
          "Это контроль устойчивости, исходная формулировка +/-3 свечи сохраняется отдельно.",
          "",
          "| Индикатор | 5 из 7 экстремумов в +/-8 ч | Случайно внутри месяца | p | Сильнейшие дни |",
          "|---|---:|---:|---:|---|"]
    for k,z in results.items():
        d=z["no_monthly_null"]
        lines.append(f"| {k} | {z['same_side_5of7_within_8h_pct']:.2f}% | "
             f"{d['monthly_null_mean']:.2f}% | {d['empirical_p']:.4f} | "
             f"{', '.join(z['top_weekdays'][:2])} |")
    lines.extend(["","Недельные результаты — по UTC и с коррекцией за выбор максимального дня. Пик ретроспективный. Никаких ордеров нет."])
    (ROOT/"CLIPPED_SIGN_EXTREME_ROBUSTNESS.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    calculate()
