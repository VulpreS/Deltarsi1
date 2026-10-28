"""Journal-derived DeltaRSI color signals, closed 4H -> next hourly open.

Indicator source: root Delta (SMA21, Wilder RSI12, EMA7). Mechanical entry/exit
interpretation, not a claim to recover discretionary selection or partial exits.
"""
import math
import numpy as np
import pandas as pd
from analyze_delta import sma,rsi_rma,ema


def pine_colors(delta):
    """Four Pine opacities per sign. Equal magnitude is gray, not weak."""
    colors=['gray']*len(delta)
    for k in range(1,len(delta)):
        d,prev=delta[k],delta[k-1]
        if not (math.isfinite(d) and math.isfinite(prev)): continue
        a,b=abs(d),abs(prev)
        suffix='B' if d>0 else 'R'
        if d==0:continue
        if a>60 and ((d>0 and d>prev) or (d<0 and d<prev)): c='strong'
        elif a>60 and ((d>0 and d<prev) or (d<0 and d>prev)): c='medium'
        elif a<=60 and a>b:c='faint'
        elif a<=60 and a<b:c='weak'
        else:continue
        colors[k]=c+suffix
    return colors


def indicator(d):
    rsi=rsi_rma(sma(d.close.tolist(),21),12);signal=ema(rsi,7)
    delta=[]
    for r,e in zip(rsi,signal):
        if r is None or e is None:
            delta.append(math.nan);continue
        rm,em=min(r,100-r),min(e,100-e)
        if rm<=0 or em<=0:delta.append(math.nan);continue
        magnitude=abs(100*math.log(rm/em))
        delta.append(magnitude if r>e else -magnitude)
    return pd.DataFrame(dict(rsi=rsi,ema=signal,delta=delta,color=pine_colors(delta)),index=d.index)


def journal_signal(prev,now):
    # Journal says medium-red -> weak-red long, weak-blue short. Enter short
    # only at first appearance, not on every consecutive weak blue candle.
    if now=='weakR' and prev in ('mediumR','faintR'):return 1
    if now=='weakB' and prev in ('strongB','mediumB','faintB'):return -1
    return 0


def prepare(hourly,stop_mode='peak_bar',long_only=False):
    if stop_mode not in ('peak_bar','whole_wave'):raise ValueError(stop_mode)
    counts=hourly.resample('4h').size()
    bars=hourly.resample('4h').agg(dict(open='first',high='max',low='min',close='last')).loc[counts==4]
    ind=indicator(bars)
    tr=pd.concat([bars.high-bars.low,(bars.high-bars.close.shift()).abs(),(bars.low-bars.close.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    records=[];wave=[];old_sign=0
    for k,t in enumerate(bars.index):
        d=float(ind.delta.iloc[k]);sign=1 if d>0 else -1 if d<0 else 0
        if not math.isfinite(d) or not sign:
            wave=[];old_sign=0
        else:
            wave=wave+[k] if sign==old_sign else [k];old_sign=sign
        signal=journal_signal(ind.color.iloc[k-1],ind.color.iloc[k]) if k>0 else 0
        if k<60:signal=0
        stop=math.nan;source=None
        if signal and wave:
            peak=max(wave,key=lambda j:abs(float(ind.delta.iloc[j])))
            chosen=peak if stop_mode=='peak_bar' else (min(wave,key=lambda j:bars.low.iloc[j]) if signal==1 else max(wave,key=lambda j:bars.high.iloc[j]))
            stop=float(bars.low.iloc[chosen] if signal==1 else bars.high.iloc[chosen])
            source=str(bars.index[chosen]+pd.Timedelta(hours=4))
        records.append(dict(signal=signal if not long_only or signal>0 else 0,reverse_signal=signal,kind='delta',atr=float(atr.iloc[k]),mid=math.nan,exit_low=math.nan,exit_high=math.nan,stop_price=stop,delta=d,rsi=float(ind.rsi.iloc[k]) if pd.notna(ind.rsi.iloc[k]) else math.nan,stop_source_time=source))
    # Decision becomes visible only once the entire 4H bucket has closed.
    decision=pd.DataFrame(records,index=bars.index+pd.Timedelta(hours=4))
    prepared=decision.reindex(hourly.index)
    for key in ('signal','reverse_signal'):prepared[key]=prepared[key].fillna(0)
    prepared['kind']='delta';prepared['atr']=decision.atr.reindex(hourly.index,method='ffill')
    return prepared,ind,bars
