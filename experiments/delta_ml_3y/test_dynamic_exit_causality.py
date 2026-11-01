"""Deterministic no-lookahead checks for DeltaRSI dynamic-exit backtester.

No exchange API, no GitHub data download; only synthetic OHLC and scores.
Run: python -u experiments/delta_ml_3y/test_dynamic_exit_causality.py
"""
import numpy as np
import pandas as pd

import dynamic_exit_regimes as de

STEP=4*3600000


def fixture():
    n=14
    ts=np.arange(n,dtype=np.int64)*STEP+1780000000000-(1780000000000%STEP)
    opens=np.full(n,100.,dtype=float)
    closes=np.full(n,100.,dtype=float)
    highs=np.full(n,101.,dtype=float)
    lows=np.full(n,99.,dtype=float)
    opens[3]=100.
    closes[3]=102.
    highs[3]=103.
    lows[3]=99.
    opens[4]=102.5
    closes[4]=102.
    highs[4]=200.
    lows[4]=50.
    arr=dict(t=ts,op=opens,close=closes,high=highs,low=lows,
             atr=np.full(n,2.),dr=np.full(n,0.5),
             shade=np.zeros(n,dtype=int),n=n)
    scores=np.full(n,2.0)
    scores[2]=3.5
    scores[3]=1.0
    scores[4]=4.9  # unseen at bar 4 OPEN: must not affect exit
    sc=pd.DataFrame(dict(
         composite=scores,
         regime=["FRESH MOVE"]*n,
         bias_short_term=["UP"]*n,
         bias_higher_tf=["UP"]*n))
    return arr,sc


def test_prior_closed_score_exit():
    d,s=fixture()
    z=de.one_trade(d,s,signal_idx=2,side=1,last_exclusive=d["n"],
                   policy=de.POLICIES["score_profit"])
    assert z["reason"]=="market_score_peak_decay",z
    assert z["exit_idx"]==4,z
    assert z["exit"]==102.5,z
    # The signal at bar 4 open must use last CLOSED score from bar 3, not bar 4.
    assert z["exit_score"]==1.0,z


def test_unseen_bar_cannot_change_open_exit():
    d,s=fixture()
    control=de.one_trade(d,s,2,1,d["n"],de.POLICIES["score_profit"])
    d["high"][4]=10000.
    d["low"][4]=.1
    d["close"][4]=.1
    s.loc[4,"composite"]=999.
    after=de.one_trade(d,s,2,1,d["n"],de.POLICIES["score_profit"])
    assert control["exit"]==after["exit"]
    assert control["exit_idx"]==after["exit_idx"]
    assert control["net"]==after["net"]
    assert control["mfe_atr"]==after["mfe_atr"]


def test_stop_first_if_both_intrabar():
    d,s=fixture()
    d["low"][3]=94.
    d["high"][3]=106.
    z=de.one_trade(d,s,2,1,d["n"],de.POLICIES["fixed_2p5"])
    assert z["exit_idx"]==3 and z["exit"]==95.
    assert z["reason"]=="stop_or_conservative_stop_first"


def test_boundary_is_mark_not_executed_exit():
    d,s=fixture()
    z=de.one_trade(d,s,2,1,4,de.POLICIES["fixed_2p5"])
    assert not z["realized"]
    assert z["reason"]=="unrealized_mark_at_fold_boundary"


def main():
    test_prior_closed_score_exit()
    test_unseen_bar_cannot_change_open_exit()
    test_stop_first_if_both_intrabar()
    test_boundary_is_mark_not_executed_exit()
    print("DYNAMIC_EXIT_CAUSALITY_TESTS: PASS (4 synthetic tests)")


if __name__=="__main__":
    main()
