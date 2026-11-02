"""Verify DeltaRSI time-scale robustness to TWO materially distinct definitions.

A = executable root Pine: SMA(close,21), RSI12, EMA7 and signed
    symmetric log Delta, threshold60, precise 8 shade color codes.
B = user's most recently stated mathematical specification:
    RSI27(close, Wilder RMA) - EMA7(RSI27), NO SMA21 or symmetric log.

Because the *color/intensity thresholds* for B have NOT been provided
in a verified Pine source, DO NOT pretend its medium->weak entries are
the same as variant A. Compare sign-zero crossings, half/full cycles,
time from completed-wave's absolute Delta peak to zero crossing, and
first magnitude decrease after the eventual peak. The peak is hindsight
ONLY, not an executable signal; never use it for trading.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import math
import os

import numpy as np

import cycle_48h_analysis as prior
from train import ROOT


def rsi27_ema7(close):
    close=np.asarray(close,dtype=float)
    n=len(close)
    rsi=np.full(n,np.nan,dtype=float)
    ema=np.full(n,np.nan,dtype=float)
    delta=np.full(n,np.nan,dtype=float)
    length=27
    if n<=length:
        return rsi,ema,delta
    diff=np.diff(close)
    gain=np.maximum(diff[:length],0.)
    loss=np.maximum(-diff[:length],0.)
    g=float(np.mean(gain))
    l=float(np.mean(loss))
    for i in range(length,n):
        if i>length:
            ch=close[i]-close[i-1]
            g=(g*(length-1)+max(ch,0.))/length
            l=(l*(length-1)+max(-ch,0.))/length
        val=(100. if l==0 else (0. if g==0 else 100.-100./(1.+g/l)))
        rsi[i]=val
        ema[i]=val if i==length else ema[i-1]*.75+val*.25
        delta[i]=val-ema[i]
    return rsi,ema,delta


def sign_wave_stats(delta,start=220):
    times=[]
    peaks=[]
    fading=[]
    high_before_cross=[]
    events=[]
    seq=[]
    state=0
    began=None
    for i in range(start,len(delta)):
        val=delta[i]
        if not np.isfinite(val) or val==0:
            continue
        sign=int(np.sign(val))
        if began is None:
            began=i
            state=sign
            continue
        if sign!=state:
            if i-began>=2:
                segment=np.asarray(delta[began:i])
                peak_idx=began+int(np.argmax(np.abs(segment)))
                first_fade=peak_idx+1
                wave_h=4*(i-began)
                peak_h=4*(i-peak_idx)
                fade_h=4*(i-first_fade) if first_fade<i else 0
                times.append(wave_h)
                peaks.append(peak_h)
                fading.append(fade_h)
                events.append((began,i,state,peak_idx))
                high_before_cross.append(peak_idx)
            began=i
            state=sign
    full=[4*(events[k+1][1]-events[k-1][1])
          for k in range(1,len(events)-1)]
    return dict(
      halfwave=prior.time_summary(times),
      fullcycle=prior.time_summary(full),
      peak_abs_delta_to_zero=prior.time_summary(peaks),
      first_decay_bar_after_peak_to_zero=prior.time_summary(fading),
      completed_halfwaves=len(events),
      peak_selection_uses_future=True)


def compare():
    data,source=prior.read_data()
    result={}
    for sym,(d,df) in data.items():
        plain_rsi,ema,plain_delta=rsi27_ema7(d["close"])
        a=sign_wave_stats(d["dr"])
        b=sign_wave_stats(plain_delta)
        # STRICT no-lookahead prefix validation for alternate formula.
        for at in (333,1250,2300,4500):
            if at>=len(plain_delta):
                continue
            check=rsi27_ema7(d["close"][:at+1])[2]
            if not np.isclose(check[-1],plain_delta[at],rtol=1e-12,atol=1e-12):
                raise AssertionError(f"{sym} RSI27 prefix future leak at {at}")
        result[sym]=dict(
          old_root_pine_sma21_rsi12_symmetric=a,
          stated_rsi27_minus_ema7=b,
          same_delta_formula=False,
          numeric_difference_not_standardized=True)
        print("RSI27_TIMES",json.dumps(dict(symbol=sym,
          root_half=a["halfwave"],plain27_half=b["halfwave"],
          root_fade=a["peak_abs_delta_to_zero"],
          plain27_fade=b["peak_abs_delta_to_zero"]),
          ensure_ascii=False),flush=True)
    payload=dict(experiment="DeltaRSI exact-math version sensitivity / signs and fading cycles",
       github_run=os.environ.get("GITHUB_RUN_ID","local"),
       github_sha=os.environ.get("GITHUB_SHA","local"),
       sources=source,results=result,
       original_indicator="executable root Delta Pine: SMA(close,21) -> RSI12 RMA -> EMA7 -> symmetric signed log",
       alternative_indicator="Wilder RSI(27) applied directly to CLOSE -> EMA7 of RSI -> Delta RSI minus EMA",
       candle_resolution_hours=4,
       warnings=[
         "RSI27 alternate does not invent medium/weak shade thresholds, so not compared for exact signal-to-signal trading",
         "Peak and fading bar picked with hindsight inside completed sign wave: DESCRIPTIVE only, not real-time entry",
         "Original Pine itself contains an inconsistent comment RSI27 while executable code length=12 and SMA21",
         "The entire 48h trading PnL experiment reported separately tested only executable root Delta math and its exact colors",
         "Historic retired TONUSDT false zero-volume bars removed, GRAMUSDT listed July2026 is not connected",
         "Full sign cycle statistics use consecutive completed sign-wave sequences, incomplete final wave ignored",
       ])
    (ROOT/"RSI27_VS_PINE12_CYCLES.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    lines=["# Две формулы DeltaRSI: сравнение знаковых циклов и затухания","",
        "Исполняемый Pine = SMA21→RSI12→EMA7→symmetric log, **не** RSI27−EMA7.",
        "Отдельно сравниваем математическую версию RSI27 от CLOSE с EMA7. Цветовые пороги для plain RSI27 не заданы, поэтому строгие medium→weak сигналы только для Pine-варианта.",
        "Пик Delta и момент начала его затухания известны лишь ПОСЛЕ завершения полуволны, использовать как онлайн-сигнал нельзя.","",
        "| Актив | Pine полуволна | RSI27 полуволна | Pine от пика до нуля | RSI27 от пика до нуля | RSI27 доля затуханий <=48h |",
        "|---|---:|---:|---:|---:|---:|"]
    for sym,z in result.items():
        a=z["old_root_pine_sma21_rsi12_symmetric"]
        b=z["stated_rsi27_minus_ema7"]
        lines.append(f"| {sym[:-4]} | {a['halfwave']['median_h']} ч | "
           f"{b['halfwave']['median_h']} ч | "
           f"{a['peak_abs_delta_to_zero']['median_h']} ч | "
           f"{b['peak_abs_delta_to_zero']['median_h']} ч | "
           f"{b['first_decay_bar_after_peak_to_zero']['under_48_pct']}% |")
    lines+=["","Данные из уже сохранённых immutable исторических архивов, никаких новых скачиваний.",
       "48-часовой доходный бэктест из соседних отчётов не переносится на новую формулу RSI27 автоматически.",
       "Для полной проверки RSI27 потребуются точные правила интенсивности/оттенков этой версии."]
    (ROOT/"RSI27_VS_PINE12_CYCLES.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    compare()
