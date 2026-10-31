"""Causal port of REGIME block from user's Market Regime & Signal Scoring Model.

Source: VulpreS/Market-Regime-Signal-Scoring-Model,
file 'Market Regime & Signal Scoring Model.pine',
GitHub blob SHA d29bb61a02e82b9e3f4de0fed9d5a826a0a70165.

IMPORTANT: Pine score_short/score_long mean SHORT-TERM/HIGHER TIMEFRAME,
not bear/bull trading direction! The actual direction uses bias_short and
bias_long. Only REGIME mode is modeled, NOT default SCALP mode or its separate
RSI signal/cooldown system. Existing DeltaRSI entries remain unchanged.

Safety: all 4H features use bar-close data; daily context is the PREVIOUS
completed UTC DAILY bar for every intraday bar, a conservative fixed HTF
alignment. This is not an exact timestamp parity claim against TradingView's
request.security on the last intraday bar. All trade decisions next 4H open.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PINE_REF="VulpreS/Market-Regime-Signal-Scoring-Model:Market Regime & Signal Scoring Model.pine"
PINE_BLOB_SHA="d29bb61a02e82b9e3f4de0fed9d5a826a0a70165"
REGIME_LABELS=("MATURE TREND","FRESH MOVE","AGING TREND",
               "CONFLICT","SLEEPING","NEUTRAL")
STEP=4*3600000


def rma(series,n):
    """Wilder-style average; ewm initialization is an approximation to Pine ta.rma's SMA seed."""
    return pd.Series(series).ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def weighted_nw_sma18(close):
    """Past-only Gaussian NW kernel: w = exp(-0.5*(i/2)^2), 18 bars."""
    src=pd.Series(close).rolling(18,min_periods=18).mean()
    weight=np.exp(-.5*(np.arange(18)/2.0)**2)
    sumw=float(weight.sum())
    total=sum(weight[i]*src.shift(i) for i in range(18))
    return total/sumw


def core_regime(close,high,low,lookback=60):
    close=pd.Series(close,dtype=float).reset_index(drop=True)
    high=pd.Series(high,dtype=float).reset_index(drop=True)
    low=pd.Series(low,dtype=float).reset_index(drop=True)
    nw=weighted_nw_sma18(close)
    slope=nw.diff()
    slope_sign=np.sign(slope)
    consistent=((((slope>0)&(slope.shift(1)>0)&(slope.shift(2)>0)&(slope.shift(3)>0)) |
                ((slope<0)&(slope.shift(1)<0)&(slope.shift(2)<0)&(slope.shift(3)<0))).astype(float)
    higher_lows=((low>low.shift(1))&(low.shift(1)>low.shift(2))&
                 (low.shift(2)>low.shift(3))&(low.shift(3)>low.shift(4)))
    lower_highs=((high<high.shift(1))&(high.shift(1)<high.shift(2))&
                 (high.shift(2)<high.shift(3))&(high.shift(3)<high.shift(4)))
    structure=(higher_lows|lower_highs).astype(float)
    e50=close.ewm(span=50,adjust=False).mean()
    e100=close.ewm(span=100,adjust=False).mean()
    e200=close.ewm(span=200,adjust=False).mean()
    ema_pos=(((close>e50)&(e50>e100)&(e100>e200)) |
             ((close<e50)&(e50<e100)&(e100<e200))).astype(float)
    ema_dist_score=(5*(close-e50).abs()/close.replace(0,np.nan)).clip(0,1).fillna(0)
    slope_mean=slope.rolling(6,min_periods=6).mean()
    trend_up=((slope_mean>0)&(e50>e100)&(higher_lows|~lower_highs))
    trend_down=((slope_mean<0)&(e50<e100)&(lower_highs|~higher_lows))
    bias=np.where(trend_up,"UP",np.where(trend_down,"DOWN","NEUTRAL"))
    mid=close.rolling(20,min_periods=20).mean()
    stdev=close.rolling(20,min_periods=20).std(ddof=0)
    width=4*stdev/mid.replace(0,np.nan)    # BB(20,2): (upper-lower)/mid
    rolling_max=width.rolling(lookback,min_periods=lookback).max()
    squeeze=(1-width/rolling_max.replace(0,np.nan)).clip(0,1).fillna(0)
    prev=close.shift(1)
    tr=pd.concat((high-low,(high-prev).abs(),(low-prev).abs()),axis=1).max(axis=1)
    atr=rma(tr,14)
    atr_expand=((atr>atr.shift(1))&(atr.shift(1)>atr.shift(2))).astype(float)
    short_score=(1.1*consistent+.9*ema_pos+.6*ema_dist_score+
                 .7*atr_expand+.8*structure+.9*squeeze)
    daily_score=.6*consistent+.8*ema_pos+.6*atr_expand
    return pd.DataFrame(dict(short_score=short_score,long_score_same_tf=daily_score,
        bias=bias,nw_slope=slope,nw_slope_mean=slope_mean,
        nw_consistency=consistent,ema_pos=ema_pos,ema_dist_score=ema_dist_score,
        price_structure=structure,atr_expand=atr_expand,bb_squeeze=squeeze,
        atr=atr))


def causal_daily_from_4h(rows):
    """Build complete UTC daily bars only; map to next UTC date (never same-day)."""
    x=pd.DataFrame(rows,columns=["t","open","high","low","close","volume"])
    if (x.t.diff().dropna()!=STEP).any():
        raise RuntimeError("Noncontiguous 4h data; no daily HTF interpolation")
    x["utc_date"]=pd.to_datetime(x.t,unit="ms",utc=True).dt.floor("D")
    days=x.groupby("utc_date",sort=True)
    daily=days.agg(open=("open","first"),high=("high","max"),
            low=("low","min"),close=("close","last"),volume=("volume","sum"),
            bars=("t","count"))
    daily=daily[daily.bars==6]
    if daily.empty:
        raise RuntimeError("No complete UTC daily bars for MTF regime")
    z=core_regime(daily.close.to_numpy(),daily.high.to_numpy(),daily.low.to_numpy())
    z.index=daily.index
    z["daily_date"]=daily.index
    return z


def scoring_features(rows,normalize_higher_tf=False):
    d=pd.DataFrame(rows,columns=["t","open","high","low","close","volume"])
    local=core_regime(d.close,d.high,d.low)
    day=causal_daily_from_4h(rows)
    df=pd.concat([d.reset_index(drop=True),local.reset_index(drop=True)],axis=1)
    df["utc_date"]=pd.to_datetime(df.t,unit="ms",utc=True).dt.floor("D")
    yesterday=(df["utc_date"]-pd.Timedelta(days=1))
    # Daily data unavailable for current day until after UTC close.
    htf=day.reindex(yesterday).reset_index(drop=True)
    short=df["short_score"]
    long_raw=htf["long_score_same_tf"].fillna(0)
    # EXPLICIT counterfactual: rescale 0..2 to 0..5 to make\n    # originally unreachable MATURE/AGING states reachable. Original is default.\n    long=long_raw*2.5 if normalize_higher_tf else long_raw\n    local_bias=pd.Series(df["bias"],index=df.index)
    daily_bias=pd.Series(htf["bias"].fillna("NEUTRAL"),index=df.index)
    align=(local_bias!="NEUTRAL")&(local_bias==daily_bias)
    conflict=(local_bias!="NEUTRAL")&(daily_bias!="NEUTRAL")&(local_bias!=daily_bias)
    composite=(.6*short+.4*long+.3*align.astype(int)-.5*conflict.astype(int)).clip(0,5)
    high_s=short>=2.8
    high_l=long>=2.6
    choices=[
        high_s&high_l&align,
        high_s&~high_l,
        high_l&~high_s,
        conflict,
        (short<2)&(long<2)]
    regime=np.select(choices,list(REGIME_LABELS[:5]),default="NEUTRAL")
    output=pd.DataFrame(dict(
        score_short_term=short.to_numpy(),
        score_higher_tf=long.to_numpy(),
        score_higher_tf_raw=long_raw.to_numpy(),
        composite=composite.to_numpy(),
        bias_short_term=local_bias.to_numpy(),
        bias_higher_tf=daily_bias.to_numpy(),
        aligned=align.to_numpy(),conflict=conflict.to_numpy(),
        regime=regime,
        nw_slope_consistency=df.nw_consistency.to_numpy(),
        price_structure=df.price_structure.to_numpy(),
        ema_pos=df.ema_pos.to_numpy(),
        ema_dist_score=df.ema_dist_score.to_numpy(),
        atr_expand=df.atr_expand.to_numpy(),
        bb_squeeze=df.bb_squeeze.to_numpy(),
        htf_previous_complete_day_only=np.ones(len(df),dtype=bool),
    ))
    return output


def audit_no_future(ohlcv,spots=(1100,2400,3800)):
    """Prefix parity: no historical feature changes when later OHLCV is hidden."""
    full=scoring_features(ohlcv)
    keys=("regime","composite","score_short_term","score_higher_tf",
          "bias_short_term","bias_higher_tf")
    for i in spots:
        if i>=len(ohlcv)-5:
            continue
        prefix=scoring_features(ohlcv[:i+1])
        for col in keys:
            a=prefix[col].iloc[-1]
            b=full[col].iloc[i]
            if isinstance(a,str):
                if a!=b:raise AssertionError(f"Future leak {col} at {i}: {a} != {b}")
            elif not np.isclose(float(a),float(b),rtol=1e-8,atol=1e-10):
                raise AssertionError(f"Future leak {col} at {i}: {a} != {b}")
    return True
