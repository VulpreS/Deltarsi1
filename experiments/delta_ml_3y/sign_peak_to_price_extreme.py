"""Histogram sign → strongest Delta peak → nearby PRICE high/low → opposite peak.

Primary, per user:
 * positive (blue) run: strongest positive histogram bar; price HIGH +/-3 4h bars;
 * negative (red) run: strongest negative histogram bar; price LOW +/-3 4h bars;
 * pair successive alternating signs; time is between the selected PRICE extrema.

Also report sign-switch frequency, raw sign-run lengths, histogram peak-to-peak
distances, and perturbation of window radius +/-1,2,3,4 bars.

Two separate numerical definitions for comparability:
 - executable root Pine Delta: SMA(close,21) -> Wilder RSI12 -> EMA7 ->
   signed symmetric log delta (reuses train.pine_indicator).
 - user-confirmed RSI(27)/EMA(7) from closing price (no preliminary SMA21).
Never conflate the resulting cycle durations. TON stops before delisting;
GRAM is independent and never stitched.
These are HINDSIGHT measurements; the hist peak is only known after the
next sign change, cannot be used as a real-time entry or exit.
"""
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from train import ROOT, pine_indicator

COINS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT",
       "ICPUSDT","ZECUSDT","TONUSDT","GRAMUSDT")
WARMUP=220
FOUR_HOURS=4*3600000
TON_LAST_EXCLUSIVE=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
WINDOWS=(1,2,3,4)
BINS=((0,12),(12,24),(24,36),(36,48),(48,60),(60,72),
      (72,96),(96,120),(120,144),(144,192),(192,240),(240,336),
      (336,None))
VERSIONS=("rsi27_ema7","root_pine_executable")


def rsi27_delta(close):
    """Seed Wilder RSI27 using first 27 close-to-close differences;
    then EMA7 of valid RSI, alpha 2/(7+1) = 0.25.
    """
    n=len(close)
    out=np.full(n,np.nan)
    changes=np.diff(close)
    count=27
    if n<=count:
        return out
    gains=np.maximum(changes[:count],0.)
    losses=np.maximum(-changes[:count],0.)
    avgg=float(np.mean(gains))
    avgl=float(np.mean(losses))
    ema=None
    for i in range(count,n):
        if i>count:
            c=float(changes[i-1])
            avgg=(avgg*(count-1)+max(0.,c))/count
            avgl=(avgl*(count-1)+max(0.,-c))/count
        value=(100. if avgl==0 and avgg>0
               else (50. if avgl==0 and avgg==0 else 100.-100./(1.+avgg/avgl)))
        ema=value if ema is None else .25*value+.75*ema
        out[i]=value-ema
    return out


def iso(ts):
    return dt.datetime.fromtimestamp(int(ts)/1000,dt.timezone.utc).isoformat()


def load_all():
    obj={}
    for sym in COINS:
        p=ROOT/"data"/(sym+".json")
        if not p.exists():
            raise FileNotFoundError(f"Missing immutable 4h candle snapshot: {p}")
        raw=p.read_bytes()
        rows=json.loads(raw)
        removed=0
        if sym=="TONUSDT":
            removed=sum(int(row[0])>=TON_LAST_EXCLUSIVE for row in rows)
            if removed<700:
                raise RuntimeError("Unexpected TONUSDT delisted tail; audit required")
            rows=[r for r in rows if r[0]<TON_LAST_EXCLUSIVE]
        t=np.asarray([r[0] for r in rows],dtype=np.int64)
        if len(t)<500 or not np.all(np.diff(t)==FOUR_HOURS):
            raise RuntimeError(f"{sym}: invalid continuous 4h series {len(t)}")
        close=np.asarray([r[4] for r in rows],dtype=float)
        high=np.asarray([r[2] for r in rows],dtype=float)
        low=np.asarray([r[3] for r in rows],dtype=float)
        if np.any(low<=0) or np.any(high<low):
            raise RuntimeError(f"{sym}: invalid OHLC")
        obj[sym]=dict(t=t,close=close,high=high,low=low,
            first=iso(t[0]),last=iso(t[-1]),bars=len(t),
            discarded_delisted_rows=removed,
            source_sha256=hashlib.sha256(raw).hexdigest())
    return obj


def histogram(close,version):
    if version=="rsi27_ema7":
        return rsi27_delta(close)
    if version=="root_pine_executable":
        return pine_indicator(close)[1]
    raise ValueError(version)


def sign_runs(hist):
    """Completed uninterrupted nonzero sign runs. Exclude 1st & final
    runs to avoid left/right censoring. Zero, NaN splits a run.
    """
    n=len(hist)
    signs=np.zeros(n,dtype=np.int8)
    finite=np.isfinite(hist)
    signs[finite&(hist>0)]=1
    signs[finite&(hist<0)]=-1
    all_runs=[]
    start=None
    prior=0
    for i in range(WARMUP,n):
        direction=int(signs[i])
        if direction==0:
            if start is not None:
                all_runs.append(dict(start=start,end=i,side=prior))
            start=None
            prior=0
        elif start is None:
            start=i
            prior=direction
        elif direction!=prior:
            all_runs.append(dict(start=start,end=i,side=prior))
            start=i
            prior=direction
    # The final right-censored run is not scored. The first run after
    # WARMUP may be left-censored (started before WARMUP), discard it.
    if len(all_runs)<=1:return []
    return all_runs[1:]


def locate_peaks(data,version,radius):
    hist=histogram(data["close"],version)
    runs=sign_runs(hist)
    peaks=[]
    for run in runs:
        start,end,side=run["start"],run["end"],run["side"]
        # A sign run's biggest *absolute* histogram column.
        hidx=start+int(np.argmax(np.abs(hist[start:end])))
        lo=max(0,hidx-radius)
        hi=min(len(hist),hidx+radius+1)
        price_data=data["high"][lo:hi] if side>0 else data["low"][lo:hi]
        pidx=lo+int(np.argmax(price_data) if side>0 else np.argmin(price_data))
        peaks.append(dict(
            run_start_i=start,run_end_i=end,side=side,
            histogram_peak_i=hidx,price_extreme_i=pidx,
            run_duration_h=(end-start)*4,
            histogram_peak_value=float(hist[hidx]),
            price=float(data["high"][pidx] if side>0 else data["low"][pidx]),
            peak_to_price_extreme_h=(pidx-hidx)*4,
            hist_peak_time=iso(data["t"][hidx]),
            price_extreme_time=iso(data["t"][pidx])))
    return peaks


def summarize(xs):
    v=np.asarray(xs,dtype=float)
    if not len(v):return dict(n=0)
    hist={}
    for lo,hi in BINS:
        label=f"{lo}-{hi if hi is not None else 'plus'}"
        hist[label]=int(np.sum((v>=lo)&((v<hi) if hi is not None else True)))
    return dict(n=len(v),median_h=round(float(np.median(v)),2),
        mean_h=round(float(np.mean(v)),2),
        p10_h=round(float(np.percentile(v,10)),2),
        p25_h=round(float(np.percentile(v,25)),2),
        p75_h=round(float(np.percentile(v,75)),2),
        p90_h=round(float(np.percentile(v,90)),2),
        pct_under_36=round(100*float(np.mean(v<36)),2),
        pct_36_to_72=round(100*float(np.mean((v>=36)&(v<=72))),2),
        pct_73_to_143=round(100*float(np.mean((v>72)&(v<144))),2),
        pct_144_plus=round(100*float(np.mean(v>=144)),2),
        pct_under_equal_48=round(100*float(np.mean(v<=48)),2),
        histogram_counts=hist)


def analyze(data,version,radius=3):
    peaks=locate_peaks(data,version,radius)
    # Time between opposite sign switches: completed sign-spell duration.
    sign_lengths=[p["run_duration_h"] for p in peaks]
    # Adjacent hist-peak and nearby extreme intervals. Ensure each pair has
    # opposite direction; a 0 sign gap can split two same-side runs, skip it.
    pairs=[]
    hist_hours=[]
    price_hours=[]
    pos_to_neg=[]
    neg_to_pos=[]
    negative_time_pairs=0
    for a,b in zip(peaks,peaks[1:]):
        if a["side"]==b["side"]:
            continue
        hd=(b["histogram_peak_i"]-a["histogram_peak_i"])*4
        pdur=(b["price_extreme_i"]-a["price_extreme_i"])*4
        if hd<=0:
            continue
        hist_hours.append(hd)
        if pdur<=0:
            negative_time_pairs+=1
            continue
        price_hours.append(pdur)
        change=b["price"]/a["price"]-1.
        if a["side"]==1:
            pos_to_neg.append(pdur)
        else:
            neg_to_pos.append(pdur)
        pairs.append(dict(
            blue_to_red=bool(a["side"]>0),
            from_hist_peak_utc=a["hist_peak_time"],
            to_hist_peak_utc=b["hist_peak_time"],
            from_price_extreme_utc=a["price_extreme_time"],
            to_price_extreme_utc=b["price_extreme_time"],
            hist_peak_to_hist_peak_h=hd,
            price_extreme_to_price_extreme_h=pdur,
            move_pct=round(change*100,4),
            first_peak=b["histogram_peak_value"],
            first_extreme_price=a["price"],second_extreme_price=b["price"]))
    # Sign change per calendar month: use 30.44d average, not dependent
    # on the signs' full history before WARMUP.
    active_days=(len(data["t"])-WARMUP)*4/24
    switches=len([1 for a,b in zip(peaks,peaks[1:]) if a["side"]!=b["side"]])
    med_peak_delta=np.median([p["peak_to_price_extreme_h"] for p in peaks]) if peaks else None
    return dict(
        sign_switches=switches,
        sign_changes_per_30d=round(switches*30/active_days,2),
        completed_signed_histogram_waves=len(peaks),
        sign_wave_duration=summarize(sign_lengths),
        hist_peak_to_next_opposite_hist_peak=summarize(hist_hours),
        price_extreme_to_next_opposite_price_extreme=summarize(price_hours),
        blue_high_to_red_low=summarize(pos_to_neg),
        red_low_to_blue_high=summarize(neg_to_pos),
        median_price_extreme_relative_to_hist_peak_h=float(med_peak_delta) if med_peak_delta is not None else None,
        invalid_nonchronological_price_peak_pairs=negative_time_pairs,
        example_pairs_last_10=pairs[-10:])


def main():
    dataset=load_all()
    result=dict(
        title="Corrected DeltaRSI peak sign-flip price-high/low extrema cycle lengths",
        date_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        github_run=os.environ.get("GITHUB_RUN_ID","local"),
        code_sha=os.environ.get("GITHUB_SHA","local"),
        data={k:{c:v for c,v in x.items() if c not in ("t","high","low","close")}
              for k,x in dataset.items()},
        precise_definition="Blue/positive run -> its largest positive Delta bar, choose max price HIGH within +/-3 4h bars. Next red/negative run -> most negative Delta bar, choose min price LOW within +/-3 4h bars. Measure actual time between those two price extremes, and vice versa.",
        incomplete_sign_runs_excluded=True,
        artificial_48_hour_timeout=False,
        in_sample_hindsight_only=True,
        formal_signal_medium_to_weak_NOT_used=True,
        sign_switches_closed_bar_only=True,
        versions=dict(
            rsi27_ema7="User-defined Wilder RSI(27) of CLOSE minus EMA(7) of RSI27, without SMA input smoothing",
            root_pine_executable="Actual root 'Delta' Pine SMA(close,21) -> Wilder RSI12 -> EMA7 -> symmetric signed-log Delta",
        ),
        sensitivity_windows_bars=WINDOWS,
        results={},
        caveats=[
            "The histogram peak is known only after the run ends; these peaks are hindsight descriptive extrema, NOT real-time tradable signals",
            "Price extremum window +/-3 completed or future candles about histogram peak is hindsight and should not appear in causal strategy features",
            "Short 36-72h and long 144+h are post-hoc hypotheses; distribution reports 0-36 and 73-143 too to expose potential continuum",
            "An interval between price high and price low is a different object from sign-wave duration and between hist peaks",
            "No artificial TON/GRAM stitching; retired TON futures end June 23 2026 and GRAM starts July 2",
            "Only continuous Binance futures 4H archives through Oct 27 2026; do not infer 48h optimal trade holding time from histogram cycles",
        ])
    for version in VERSIONS:
        result["results"][version]={}
        for sym,data in dataset.items():
            result["results"][version][sym]={
                "primary_window3":analyze(data,version,3),
                "window_sensitivity":{
                    str(r):{k:v for k,v in analyze(data,version,r).items()
                             if k in ("sign_switches","sign_changes_per_30d","price_extreme_to_next_opposite_price_extreme",
                                      "blue_high_to_red_low","red_low_to_blue_high","invalid_nonchronological_price_peak_pairs")}
                    for r in WINDOWS}}
        print("SIGN_PEAK_VERSION",version,json.dumps({
            sym:dict(switches=v["primary_window3"]["sign_switches"],
                per30d=v["primary_window3"]["sign_changes_per_30d"],
                halfwave=v["primary_window3"]["sign_wave_duration"]["median_h"],
                hist_peak_to_peak=v["primary_window3"]["hist_peak_to_next_opposite_hist_peak"]["median_h"],
                price_peak_to_peak=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["median_h"],
                price_short=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["pct_36_to_72"],
                price_long=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["pct_144_plus"],
                under36=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["pct_under_36"],
                mid=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["pct_73_to_143"],
                samples=v["primary_window3"]["price_extreme_to_next_opposite_price_extreme"]["n"])
            for sym,v in result["results"][version].items()
        },ensure_ascii=False),flush=True)
    (ROOT/"SIGN_PEAK_TO_PRICE_EXTREME_REPORT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    lines=["# DeltaRSI: ПИК синей гистограммы -> HIGH, смена знака -> ПИК красной -> LOW","",
       "Это переопределение экстремумов пользователя: нет зависимости от сигнала medium→weak.",
       "Для каждого непрерывного знака гистограммы берём единственный наибольший по модулю столбец.",
       "В пределах +/-3 свечей 4H от него выбираем ценовой HIGH (синий, +) или LOW (красный, -).",
       "Между двумя последовательными противоположными знаками получаем интервал High→Low или Low→High.",
       "Параллельно считаем длину самих знаковых фаз и расстояние между пиками гистограммы.",
       "Это статистика прошлых циклов с использованием будущего; для реального входа неизвестна до последующей смены знака.",
       "",
       "| Версия | Монета | Смен знака / 30 д | Медиана фазы знака | Пик гист. -> пик гист. | High↔Low | Доля 36–72 ч | Доля 144+ ч |",
       "|---|---|---:|---:|---:|---:|---:|---:|"]
    for version in VERSIONS:
        for sym,v in result["results"][version].items():
            s=v["primary_window3"]
            h=s["price_extreme_to_next_opposite_price_extreme"]
            lines.append(f"| {version} | {sym.replace('USDT','')} | {s['sign_changes_per_30d']:.2f} | "
              f"{s['sign_wave_duration']['median_h']:.0f} ч | "
              f"{s['hist_peak_to_next_opposite_hist_peak']['median_h']:.0f} ч | "
              f"{h['median_h']:.0f} ч | {h['pct_36_to_72']:.1f}% | {h['pct_144_plus']:.1f}% |")
    lines+=["","## Проверки устойчивости к выбору +/- окна","",
       "В JSON сохранены +/-1, +/-2, +/-3, +/-4 свечи. При разных окнах меняется точный экстремум и время между парами, но не частота смен знака.",
       "Также сохранены отдельные High→Low и Low→High, чтобы не смешивать подъём и падение.",
       "",
       "## Границы интерпретации","",
       "Нужно отличать 1) сколько длится знак, 2) время от одного максимального столбца до противоположного, 3) расстояние по времени между настоящими High/Low.",
       "48 часов не обязаны быть медианой любого из трёх часов и не означают автоматически лучшую фиксацию прибыли.",
       "Версия RSI27−EMA7 и исполняемая версия исходного Pine — ДВА РАЗНЫХ индикатора, результаты нельзя смешивать.",
       "Завершённые фазы знака начинаются и заканчиваются при переходах знака; неполные начальная и последняя фазы исключены.",
       "Ордера и старые стратегии не изменялись. Сводная разметка с последними 10 парами есть в JSON."]
    (ROOT/"SIGN_PEAK_TO_PRICE_EXTREME_REPORT.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
