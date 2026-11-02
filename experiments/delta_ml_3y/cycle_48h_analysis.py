"""DeltaRSI 4H cycle-duration and 48-hour forced-exit investigation.

Research questions, measured SEPARATELY:
 (1) how long does one same-sign histogram INTENSITY spell last?
     and time from a strict medium->weak signal to the next such signal;
 (2) how long does a signed DeltaRSI half-wave and full sign cycle last?
 (3) how long are opposite-signal-to-opposite-signal price swings and the
     LOCAL LOW/HIGH-to-HIGH/LOW timing between those signals?
     Extremum selection uses a symmetric +/- 3 CLOSED 4h bar window:
     hindsight analysis ONLY, NEVER an entry signal.
 (4) does forcing closure at 48h improve a realistic trade replay versus
     12..96h, no cap, with or without a fixed 2.5 ATR TP?

History from immutable GitHub Releases; no historical re-download. Original
Delta Pine numeric code remains unchanged. Retired Binance TONUSDT truncated
before June 23 2026; GRAMUSDT is a different contract with a short record.
Backtest uses closed 4h signals, next open entry, fee+spread 0.18% RT,
OHLC stop-first, no imposed portfolio liquidation policy, no funding.
Aug-Oct 2026 has ALREADY been inspected; never select live parameters there.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from train import ROOT, features
import research_rules as rr

ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT","ICPUSDT","ZECUSDT","TONUSDT","GRAMUSDT")
PRELIST=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT","ICPUSDT","ZECUSDT","TONUSDT")
CUTOFF_TON=int(dt.datetime(2026,6,23,8,tzinfo=dt.timezone.utc).timestamp()*1000)
STEP=4*3600000
COST_RT=.0018
STRESS_RT=.0036
NOTIONAL=840.
CAPITAL=5000.
MIN_START=220
TIME_CAPS=(12,24,36,40,44,48,52,56,60,72,84,96,None)
CONTROL_TYPES=("sl_tp_opposite","sl_opposite_without_tp","sl_tp_without_opposite")
SPLITS={
 "calibration":(int(dt.datetime(2023,11,1,tzinfo=dt.timezone.utc).timestamp()*1000),rr.DATE_A),
 "validation1":(rr.DATE_A,rr.DATE_B),
 "validation2":(rr.DATE_B,rr.CUT),
 "inspected_aug_oct":(rr.CUT,2**62),
}
BINS=((0,12),(12,24),(24,36),(36,48),(48,60),(60,72),(72,96),(96,144),(144,240),(240,float("inf")))


def iso(ms):
    return dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc).isoformat()


def time_summary(values):
    v=np.asarray(values,dtype=float)
    if not len(v):
        return dict(n=0,median_h=None,mean_h=None,p25_h=None,p75_h=None,p90_h=None,
                    under_48_pct=None,in_36_60_pct=None,distribution={})
    buckets={}
    for low,high in BINS:
        name=f"{low}-{high}" if math.isfinite(high) else f"{low}+"
        buckets[name]=int(np.sum((v>=low)&(v<high)))
    return dict(n=len(v),median_h=round(float(np.median(v)),1),
      mean_h=round(float(np.mean(v)),1),
      p25_h=round(float(np.percentile(v,25)),1),
      p75_h=round(float(np.percentile(v,75)),1),
      p90_h=round(float(np.percentile(v,90)),1),
      under_48_pct=round(100*float(np.mean(v<=48)),1),
      in_36_60_pct=round(100*float(np.mean((v>=36)&(v<=60))),1),
      distribution=buckets)


def read_data():
    dataset={}
    signatures={}
    for sym in ASSETS:
        f=ROOT/"data"/(sym+".json")
        if not f.is_file():
            if sym=="GRAMUSDT":
                print("GRAM_MISSING_SKIPPED",str(f),flush=True)
                continue
            raise FileNotFoundError("Existing frozen cache missing: "+str(f))
        raw=f.read_bytes()
        rows=json.loads(raw)
        discarded=0
        if sym=="TONUSDT":
            discarded=sum(x[0]>=CUTOFF_TON for x in rows)
            if discarded<700:
                raise RuntimeError("Unexpected TON delisting placeholders, refuse to use unverified prices")
            rows=[r for r in rows if r[0]<CUTOFF_TON]
        if len(rows)<250:
            raise RuntimeError(f"{sym}: insufficient 4h records")
        if any(b[0]-a[0]!=STEP for a,b in zip(rows,rows[1:])):
            raise RuntimeError(f"{sym}: 4h discontinuity; no interpolation")
        df=features(rows,sym)
        d=rr.make_arrays(df)
        dataset[sym]=(d,df)
        signatures[sym]=dict(first=iso(rows[0][0]),last=iso(rows[-1][0]),
           rows=len(rows),discarded_retired_contract_rows=discarded,
           sha256=hashlib.sha256(raw).hexdigest())
    return dataset,signatures


def score_regime(d,i):
    """Causal 7/30-day movement normalized by CURRENT ATR/close."""
    if i<180:
        return "UNCLASSIFIED"
    px=d["close"]
    a=float(d["atr"][i])
    if not np.isfinite(a) or a<=0 or px[i]<=0:
        return "UNCLASSIFIED"
    k=a/px[i]
    r7=(px[i]/px[i-42]-1)/k
    r30=(px[i]/px[i-180]-1)/k
    if r7>2 and r30>3:return "BULL_TREND"
    if r7< -2 and r30< -3:return "BEAR_TREND"
    if r7< -2 and r30>3:return "BULL_PULLBACK"
    if r7>2 and r30< -3:return "BEAR_RALLY"
    return "RANGE_CONFLICT"


def sign_switches(d):
    dr=d["dr"]
    seen=[]
    last=0
    for i in range(MIN_START,len(dr)):
        if not np.isfinite(dr[i]) or dr[i]==0:
            continue
        new=int(np.sign(dr[i]))
        if last and new!=last:
            seen.append((i,new))
        last=new
    return seen


def strict_events(d):
    sh=d["shade"]
    out=[]
    for i in range(MIN_START,len(sh)):
        p,n=int(sh[i-1]),int(sh[i])
        if p==6 and n==8:out.append((i,1))
        if p==2 and n==4:out.append((i,-1))
    return out


def expanded_events(d):
    sh=d["shade"]
    out=[]
    for i in range(MIN_START,len(sh)):
        p,n=int(sh[i-1]),int(sh[i])
        if p in (6,7) and n==8:out.append((i,1))
        if p in (2,3) and n==4:out.append((i,-1))
    return out


def curve_cycles(d):
    dr=d["dr"]
    sh=d["shade"]
    n=len(dr)
    spells=[]
    category_switches=[]
    starts=None
    previous_code=None
    last_nonzero=None
    for i in range(MIN_START,n):
        code=int(sh[i])
        if code not in range(1,9):
            if starts is not None:
                spells.append(dict(start=starts,end=i-1,
                    hours=4*(i-starts),code=previous_code))
            starts=None
            previous_code=None
            continue
        if starts is None:
            starts=i
            previous_code=code
        elif code!=previous_code:
            spells.append(dict(start=starts,end=i-1,
                 hours=4*(i-starts),code=previous_code))
            if (code<=4)==(previous_code<=4):
                category_switches.append(dict(at=i,from_color=previous_code,to_color=code,
                     direction="positive" if code<=4 else "negative",
                     elapsed_since_prior_change_h=0))
            starts=i
            previous_code=code
    if starts is not None:
        # Incomplete right-censored spell is excluded.
        pass
    # Event-to-event runs of ANY SHADE change (including sign crossings).
    switches=[i for i in range(MIN_START+1,n)
              if int(sh[i]) in range(1,9) and int(sh[i-1]) in range(1,9)
              and int(sh[i])!=int(sh[i-1])]
    same_sign_switch=[i for i in switches
              if (sh[i]<=4)==(sh[i-1]<=4)]
    all_switch_intervals=[4*(b-a) for a,b in zip(switches,switches[1:])]
    local_intensity_intervals=[4*(b-a) for a,b in zip(same_sign_switch,same_sign_switch[1:])]
    sig=strict_events(d)
    sig_idx=[s[0] for s in sig]
    switches_sign=sign_switches(d)
    sign_idx=[s[0] for s in switches_sign]
    halfwaves=[4*(b-a) for a,b in zip(sign_idx,sign_idx[1:])]
    fullwave=[4*(c-a) for a,c in zip(sign_idx,sign_idx[2:])]
    # Strict successive fade events can be in the same direction or opposite.
    fade_intervals=[4*(b-a) for a,b in zip(sig_idx,sig_idx[1:])]
    same_side_fade=[4*(sig[q+1][0]-sig[q][0]) for q in range(len(sig)-1)
                    if sig[q][1]==sig[q+1][1]]
    opposite_fade=[4*(sig[q+1][0]-sig[q][0]) for q in range(len(sig)-1)
                   if sig[q][1]!=sig[q+1][1]]
    # From a signal to next change in Delta sign (prospective temporal question;
    # this statistic is hindsight-only, not available when placing the trade).
    next_zero=[]
    zptr=0
    for sig_i,_ in sig:
        while zptr<len(sign_idx) and sign_idx[zptr]<=sig_i:zptr+=1
        if zptr<len(sign_idx):
            next_zero.append(4*(sign_idx[zptr]-sig_i))
    # Price extremes at separate reversal-signal windows +/-3 bars, with
    # bounds clamped by neighboring signals to prevent overlapping windows.
    extrema=[]
    for q,(i,side) in enumerate(sig):
        lo=max(MIN_START,i-3,(sig[q-1][0]+1) if q else MIN_START)
        hi=min(n-1,i+3,(sig[q+1][0]-1) if q+1<len(sig) else n-1)
        if lo>hi:continue
        px=d["low"][lo:hi+1] if side>0 else d["high"][lo:hi+1]
        ext_i=lo+int(np.argmin(px) if side>0 else np.argmax(px))
        extrema.append(dict(signal_i=i,extreme_i=ext_i,side=side,
                    extreme_price=float(d["low"][ext_i] if side>0 else d["high"][ext_i]),
                    before_after_signal_hours=4*(ext_i-i)))
    ex_durations=[]
    sig_durations=[]
    sig_to_pivot=[]
    for a,b in zip(extrema,extrema[1:]):
        if a["side"]==b["side"] or a["extreme_i"]>=b["extreme_i"]:
            continue
        ex_durations.append(4*(b["extreme_i"]-a["extreme_i"]))
        sig_durations.append(4*(b["signal_i"]-a["signal_i"]))
        sig_to_pivot.append(b["before_after_signal_hours"])
    # Full sign wave price peak-to-trough based on sign-cross partition.
    sign_wave_extreme=[]
    for u,v in zip(sign_idx,sign_idx[1:]):
        direction=np.sign(dr[u])
        if direction==0:continue
        # Diagnostic absolute price swing between highest high and lowest low
        # INSIDE the sign-defined wave. Do not infer direction from this.
        high_i=u+int(np.argmax(d["high"][u:v+1]))
        low_i=u+int(np.argmin(d["low"][u:v+1]))
        sign_wave_extreme.append(4*abs(high_i-low_i))
    out=dict(
       intensity_spell=time_summary([x["hours"] for x in spells]),
       intensity_repaint_transition=time_summary(all_switch_intervals),
       intensity_same_sign_transition=time_summary(local_intensity_intervals),
       strict_signal_to_next_strict=time_summary(fade_intervals),
       strict_signal_to_same_side=time_summary(same_side_fade),
       strict_signal_to_opposite_side=time_summary(opposite_fade),
       strict_signal_to_next_delta_zero=time_summary(next_zero),
       sign_halfwave=time_summary(halfwaves),
       sign_fullcycle=time_summary(fullwave),
       local_extreme_to_opposite_local_extreme=time_summary(ex_durations),
       signal_to_opposite_signal_in_extrema_pairs=time_summary(sig_durations),
       price_signal_to_nearby_extreme_offset=time_summary(sig_to_pivot),
       intra_sign_wave_price_high_low_separation=time_summary(sign_wave_extreme),
       strict_fade_events=len(sig),expanded_fade_events=len(expanded_events(d)),
       sign_cross_events=len(sign_idx),shading_events=len(switches),
       single_spells=len(spells))
    out["method_notes"]={
      "intensity_spell":"Uninterrupted run of one of eight Pine shade codes; zeros break a run; completed runs only",
      "intensity_same_sign_transition":"time between successive shade-code changes where sign stays same",
      "strict_signal_to_next_strict":"medium(red/blue) -> weak(red/blue), time until next strict event of any side",
      "sign_halfwave":"consecutive Delta sign crossings: one same-sign phase",
      "sign_fullcycle":"two successive half-waves, a full positive/negative cycle",
      "local_extreme_to_opposite_local_extreme":"high/low within +/-3 bars of strict opposite LONG/SHORT fade signal, clamped by neighboring signals; descriptive hindsight ONLY",
      "signal_to_opposite_signal_in_extrema_pairs":"same paired consecutive opposite LONG and SHORT strict signals before pivot selection",
      "price_signal_to_nearby_extreme_offset":"pivot-bar timestamp minus corresponding signal-bar timestamp; can be negative (pivot precedes signal)",
      "intra_sign_wave_price_high_low_separation":"absolute time difference between highest high and lowest low inside same-sign Delta phase; not tradeable entry or exit",
    }
    return out


def execute_trade(d, signal_i,side,stop_idx,cap_h,profile):
    """No exit can execute before entry next OPEN. Bar OHLC is checked only
    if the position survived the bar OPEN.
    """
    j0=signal_i+1
    if j0>=stop_idx:
        return None
    entry=float(d["op"][j0])
    atr=float(d["atr"][signal_i])
    if entry<=0 or not np.isfinite(atr) or atr<=0:
        return None
    stop=entry-side*2.5*atr
    has_tp=profile!="sl_opposite_without_tp"
    has_opposite=profile!="sl_tp_without_opposite"
    target=entry+side*2.5*atr if has_tp else None
    if stop<=0 or (target is not None and target<=0):
        return None
    k_final=stop_idx-1
    when="unrealized_boundary"
    exit_price=float(d["close"][k_final])
    reached=cap_h is not None and j0+(cap_h//4)<stop_idx
    horizon_index=j0+(cap_h//4) if reached else None
    exit_i=k_final
    for j in range(j0,stop_idx):
        op=float(d["op"][j])
        if horizon_index is not None and j>=horizon_index:
            exit_price=op
            when="time_cap"
            exit_i=j
            break
        if j>j0 and has_opposite and rr.should_exit(d,j,side,"reverse_fade"):
            exit_price=op
            when="opposite_fade"
            exit_i=j
            break
        if ((side==1 and op<=stop) or (side==-1 and op>=stop)):
            exit_price=op
            when="stop_gap"
            exit_i=j
            break
        if target is not None and ((side==1 and op>=target) or (side==-1 and op<=target)):
            exit_price=target
            when="take_gap"
            exit_i=j
            break
        lo=float(d["low"][j])
        hi=float(d["high"][j])
        if ((side==1 and lo<=stop) or (side==-1 and hi>=stop)):
            exit_price=stop
            when="stop_first"
            exit_i=j
            break
        if target is not None and ((side==1 and hi>=target) or (side==-1 and lo<=target)):
            exit_price=target
            when="take"
            exit_i=j
            break
    net=side*(exit_price/entry-1)-COST_RT
    return dict(entry_i=j0,exit_i=exit_i,entry_ms=int(d["t"][j0]),
       exit_ms=int(d["t"][exit_i]),side=side,entry=entry,exit=exit_price,
       ret=float(net),hold_h=4*(exit_i-j0),realized=when!="unrealized_boundary",
       reason=when,signal_idx=signal_i,entry_regime=score_regime(d,signal_i))


def backtest(d,cap_h,profile,start,end,return_ledger=False,stress=False):
    i_first=max(MIN_START,int(np.searchsorted(d["t"],start)))
    i_stop=min(d["n"],int(np.searchsorted(d["t"],end)))
    if i_stop<=i_first+1:
        return dict(trades=0,profit_pct=0.,closed=0,unfinished=0,win_rate=None,
                    profit_factor=None,average_hold_h=None,reasons={},
                    ledger=[] if return_ledger else None)
    i_free=i_first
    cash=CAPITAL
    peak=CAPITAL
    dd=0.
    n=0
    wins=0
    marked=0
    durations=[]
    netvals=[]
    reasons=collections.Counter()
    ledger=[]
    for i,side in strict_events(d):
        e=i+1
        if e<i_first or e>=i_stop or e<i_free:
            continue
        tr=execute_trade(d,i,side,i_stop,cap_h,profile)
        if tr is None:
            continue
        net=tr["ret"] - ((STRESS_RT-COST_RT) if stress else 0.)
        cash+=NOTIONAL*net
        peak=max(peak,cash)
        dd=max(dd,1-cash/peak)
        durations.append(tr["hold_h"])
        netvals.append(net)
        reasons[tr["reason"]]+=1
        i_free=tr["exit_i"]+1
        if tr["realized"]:
            n+=1
            wins+=int(net>0)
        else:
            marked+=1
        if return_ledger:
            ledger.append({k:v for k,v in tr.items() if k not in ("signal_idx","entry_i","exit_i") } |
              dict(net_stressed=round(net,7),pnl_dollars=round(NOTIONAL*net,2)))
        if not tr["realized"]:
            break
    gain=sum(max(0.,x) for x in netvals)
    loss=-sum(min(0.,x) for x in netvals)
    result=dict(trades=n,account_return_pct=round(100*(cash/CAPITAL-1),3),
       closed=n,unfinished=marked,
       win_rate=round(wins/n,3) if n else None,
       profit_factor=round(gain/loss,3) if loss else None,
       average_hold_h=round(float(np.mean(durations)),2) if durations else None,
       median_hold_h=round(float(np.median(durations)),2) if durations else None,
       max_closed_trade_dd_pct=round(100*dd,3),
       time_exit_count=int(reasons["time_cap"]),
       reasons=dict(reasons))
    if return_ledger:
        result["ledger"]=ledger
    return result


def compare_grid(data,predefined="sl_tp_opposite"):
    # Select best cap using ONLY calibration period; report other two folds
    # and inspect last already-viewed Aug-Oct as a NON-OOS diagnostic.
    scenarios={}
    for profile in CONTROL_TYPES:
        profile_results={}
        for label,(a,b) in SPLITS.items():
            profile_results[label]={}
            for sym,(d,df) in data.items():
                if sym=="GRAMUSDT" and label!="inspected_aug_oct":
                    continue
                if sym=="TONUSDT" and label=="inspected_aug_oct":
                    continue
                curve={}
                for cap in TIME_CAPS:
                    key=f"{cap}h" if cap is not None else "uncapped"
                    curve[key]=backtest(d,cap,profile,a,b)
                profile_results[label][sym]=curve
        scenarios[profile]=profile_results
    return scenarios


def add_cycle_group_summary(data):
    summaries={}
    for sym,(d,df) in data.items():
        summaries[sym]=curve_cycles(d)
    # Per-regime *completed* half-waves, no double count across data.
    regime_lifetime=collections.defaultdict(list)
    regime_fade_to_next=collections.defaultdict(list)
    for sym,(d,df) in data.items():
        zi=sign_switches(d)
        for (start,_),(end,_) in zip(zi,zi[1:]):
            r=score_regime(d,start)
            if r!="UNCLASSIFIED":
                regime_lifetime[r].append(4*(end-start))
        ev=strict_events(d)
        for (start,side),(end,nextside) in zip(ev,ev[1:]):
            r=score_regime(d,start)
            if r!="UNCLASSIFIED":
                regime_fade_to_next[r].append(4*(end-start))
    return summaries,dict(sign_halfwave_by_regime={
        k:time_summary(v) for k,v in regime_lifetime.items()},
        strict_signal_to_next_by_regime={
            k:time_summary(v) for k,v in regime_fade_to_next.items()})


def pick_from_calibration(scenarios):
    # Simple stability penalization across seven continuous markets;
    # TON only up to delisting is still included in calibration.
    out={}
    for p,split in scenarios.items():
        cal=split["calibration"]
        ranking=[]
        for cap in TIME_CAPS:
            key=f"{cap}h" if cap is not None else "uncapped"
            stats=[cal[sym][key] for sym in PRELIST if sym in cal]
            scores=[z["account_return_pct"] for z in stats]
            traded=[z["closed"] for z in stats]
            score=(.5*np.mean(scores)+.32*np.median(scores)+.2*min(scores)
                   -.08*np.std(scores))
            if sum(traded)<50:
                score-=1000
            ranking.append(dict(key=key,score=round(float(score),3),
                mean_calibration_pct=round(float(np.mean(scores)),3),
                median_calibration_pct=round(float(np.median(scores)),3),
                worst_coin_calibration_pct=round(float(min(scores)),3),
                total_trades=sum(traded)))
        ranking.sort(key=lambda z:z["score"],reverse=True)
        out[p]=dict(calibration_selected=ranking[0]["key"],rank_calibration=ranking,
                     by_split={})
        for splitname,coins in split.items():
            summary=[]
            for cap in ("24h","36h","48h","60h","72h","uncapped",ranking[0]["key"]):
                stats={sym:coins[sym][cap] for sym in PRELIST if sym in coins}
                values=[q["account_return_pct"] for q in stats.values()]
                if not values:
                    continue
                summary.append(dict(cap=cap,mean_asset_pct=round(float(np.mean(values)),3),
                  median_asset_pct=round(float(np.median(values)),3),
                  worst_asset_pct=round(float(min(values)),3),
                  profitable_assets=sum(v>0 for v in values),
                  total_closed_trades=sum(z["closed"] for z in stats.values()),
                  total_time_exits=sum(z["time_exit_count"] for z in stats.values()),
                  by_coin=stats))
            out[p]["by_split"][splitname]=summary
    return out


def paired_fixed_entries(data):
    """Same signal set irrespective of re-entry timing: isolates pure
    forced-closure value from changed trading frequency.
    A fixed entry can overlap another; this statistic is NOT portfolio PnL.
    """
    selected=("24h","36h","48h","60h","72h","uncapped")
    points={}
    for sym,(d,df) in data.items():
        if sym=="GRAMUSDT":
            continue
        period={}
        ev=strict_events(d)
        for label,(start,end) in SPLITS.items():
            if label=="inspected_aug_oct" and sym=="TONUSDT":
                continue
            stop=min(d["n"],int(np.searchsorted(d["t"],end)))
            s=max(MIN_START,int(np.searchsorted(d["t"],start)))
            table=collections.defaultdict(list)
            n=0
            for i,side in ev:
                if not(s<=i+1<stop):
                    continue
                outcomes={}
                for key in selected:
                    cap=None if key=="uncapped" else int(key[:-1])
                    tr=execute_trade(d,i,side,stop,cap,"sl_tp_opposite")
                    if tr is None or not tr["realized"]:
                        break  # no fixed paired comparison with open end
                    outcomes[key]=tr["ret"]
                if len(outcomes)!=len(selected):
                    continue
                n+=1
                for key,ret in outcomes.items():
                    table[key].append(ret)
            if n:
                base=np.asarray(table["uncapped"])
                cap48=np.asarray(table["48h"])
                period[label]=dict(signals=n,
                  mean_nominal_trade_by_cap_pct={
                    k:round(float(np.mean(table[k]))*100,4) for k in selected},
                  paired_48_minus_uncapped_pct=round(float(np.mean(cap48-base))*100,4),
                  percent_48_better=round(float(np.mean(cap48>base))*100,2),
                  percent_48_worse=round(float(np.mean(cap48<base))*100,2),
                  percent_tied=round(float(np.mean(cap48==base))*100,2))
        points[sym]=period
    return points


def main():
    data,sources=read_data()
    cycle,regime_cycles=add_cycle_group_summary(data)
    scenarios=compare_grid(data)
    capped_selection=pick_from_calibration(scenarios)
    same_entry=paired_fixed_entries(data)
    # Don't load huge all-case ledgers: useful reproducible 48h and no-cap rows
    trades={}
    for sym,(d,df) in data.items():
        if sym=="GRAMUSDT":
            # short separate contract is purely descriptive
            continue
        trades[sym]={}
        for label,(start,end) in SPLITS.items():
            if label=="inspected_aug_oct" and sym=="TONUSDT":
                continue
            trades[sym][label]={}
            for cap in (48,None):
                key="48h" if cap else "uncapped"
                trades[sym][label][key]=backtest(d,cap,"sl_tp_opposite",
                                                  start,end,return_ledger=True)
    out=dict(title="DeltaRSI cycle duration versus 48-hour forced exit across old Binance USDT-M contracts",
        run_id=os.environ.get("GITHUB_RUN_ID","local"),
        sha=os.environ.get("GITHUB_SHA","local"),
        source=sources,
        indicator="Executable root Pine Delta, SMA21/RSI12 RMA/EMA7 signed symmetric log histogram; strict medium->weak",
        original_user_experiment="48h best was reported previously for other per-coin and prop trading configurations; this experiment tests whether it generalizes",
        definitions="Three distinct clocks: shade intensity persistence; Delta zero-cross half/full cycle; price swing between opposite fades.",
        decision_causality="Cycle extremes are hindsight DESCRIPTION ONLY; trade decisions use only closed bar and next open",
        periods={k:(iso(a),iso(b) if b<2**62 else "archive_end") for k,(a,b) in SPLITS.items()},
        methodological_settings=dict(candle_hours=4,fee_roundtrip=COST_RT,
          initial_cash_per_coin=CAPITAL,fixed_notional_per_trade=NOTIONAL,
          initial_sl_atr=2.5,initial_tp_atr_when_enabled=2.5,
          frozen_entry="medium->weak same red / blue; 4h next open",
          time_exit="first bar open at exactly N hours after true entry, IF not already SL/TP/opposite",
          available_horizons=TIME_CAPS,notional_leverage=1.,
          no_portfolio_slot_conflicts=True,sl_first_if_sl_tp_touched=True,
          no_funding=True,censored_boundary_not_exec_time_exit=True),
        cycle_durations=cycle,regime_cycle_durations=regime_cycles,
        timecap_by_asset_period=scenarios,
        cap_rank_chosen_calibration_only=capped_selection,
        paired_signal_trade_analysis=same_entry,
        baseline_trade_ledgers=trades,
        warnings=[
          "Historical BTC/ETH/BNB/XRP/LINK/ICP/ZEC/TON selected from previous analyses, so even pre-Aug fold known, not virgin OOS",
          "Aug-Oct inspected previously, DO NOT choose exit horizon from it",
          "TONUSDT 759 zero-volume false candles from delisting removed. GRAMUSDT analyzed separately and not stitched",
          "Local extrema selected with +-3 bars of future prices; purely descriptive and CANNOT be used to trade",
          "Time cap backtest is only same-symbol sequential one-position trading: does not include 3-slot portfolio, prop threshold days, daily 5%/overall 10%, Turbo 6%",
          "No 48h result can be called optimal without actual no-cap and other time checks on new data after parameter freeze",
          "Profit includes marks of still-open trades at fold boundary and each is identified unfinished; no artificial liquidation",
          "Trading profit is fixed $840 nominal and costs 0.18% round-trip, NO 5x leverage or margin funding",
          "Uniform SL/TP2.5 ATR is not user's per-coin earlier prop policy (BTC2.5/5, ETH1.5/5 etc): historical superiority of 48h not automatically replicated",
        ])
    (ROOT/"DELTARSI_CYCLE_48H.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
    digest=dict(cycles={s:{k:v for k,v in e.items()
             if k in ("intensity_spell","strict_signal_to_next_strict",
                        "sign_halfwave","sign_fullcycle",
                        "local_extreme_to_opposite_local_extreme")}
         for s,e in cycle.items()},
       calibration_winners={p:z["calibration_selected"]
                             for p,z in capped_selection.items()},
       comparisons={p:{split:[dict(cap=v["cap"],mean=v["mean_asset_pct"],
                        n=v["total_closed_trades"]) for v in rows]
                for split,rows in z["by_split"].items()}
          for p,z in capped_selection.items()})
    print("DELTA_CYCLES_SUMMARY",json.dumps(digest,ensure_ascii=False),flush=True)
    md=["# DeltaRSI: циклы интенсивности, знака, экстремумов и 48 часов","",
      "Отдельное исследование, прежние стратегии и отчёты не изменены. Данные из старых GitHub Release.",
      "Все длительности в часах; 4H — минимальное разрешение. GRAM отдельно от снятого TON.",
      "Смена интенсивности — строго по Pine shade, смена знака — Delta пересекает ноль.",
      "Extrema — HIGH/LOW в окне ±3 бара у противоположных сигналов, hindsight-only.",
      "",
      "## Длительности","",
      "| Актив | Стабильный цвет (медиана) | Следующая смена medium→weak | Полуволна знака | Полный цикл знака | Экстремум↔экстремум |",
      "|---|---:|---:|---:|---:|---:|"]
    for sym,z in cycle.items():
        fmt=lambda key:str(z[key]["median_h"]) if z[key]["median_h"] is not None else "нет"
        md.append(f"| {sym.replace('USDT','')} | {fmt('intensity_spell')} | "
          f"{fmt('strict_signal_to_next_strict')} | {fmt('sign_halfwave')} | "
          f"{fmt('sign_fullcycle')} | {fmt('local_extreme_to_opposite_local_extreme')} |")
    md+=["","## Что на самом деле даёт time-exit 48h?","",
      "Все результаты ниже: отдельные стратегии 840$ номинал на 5000$; не результаты общей проп-модели.",
      "SL=2.5 ATR, TP=2.5 ATR при наличии; противоположный сигнал при наличии.",
      "Для честного сравнения периодов 48h нельзя переобучать на августе–октябре.",
      ""]
    for p,rs in capped_selection.items():
        md+=["### "+p,"",
             "Калибровочный выбор среди капов: **"+rs["calibration_selected"]+"**; выбор на известной истории не является независимым подтверждением.","",
             "| Период | Cap | Средний результат по монетам | Положительных | Сделок |",
             "|---|---|---:|---:|---:|"]
        for split,rows in rs["by_split"].items():
            for z in rows:
                if z["cap"] not in ("24h","36h","48h","60h","72h","uncapped",rs["calibration_selected"]):
                    continue
                md.append(f"| {split} | {z['cap']} | {z['mean_asset_pct']:+.3f}% | "
                          f"{z['profitable_assets']} | {z['total_closed_trades']} |")
        md.append("")
    md+=["## Контроль частоты входов: одинаковые исходные сигналы","",
         "| Монета | Период | Сигналов | Средний эффект 48h − без лимита на сделку, п.п. | 48h лучше, % |",
         "|---|---|---:|---:|---:|"]
    for sym,z in same_entry.items():
        for split,res in z.items():
            md.append(f"| {sym} | {split} | {res['signals']} | "
              f"{res['paired_48_minus_uncapped_pct']:+.3f} | {res['percent_48_better']:.1f}% |")
    md+=["","## Важные ограничения","",
         "Длительность цикла НЕ доказывает прибыльность ограничения 48 часов. Разные входы/выходы меняют частоту и структуру сделок.",
         "Не воспроизводится точный старый проп-бот: в нём были другие пер-coin SL/TP, ограничения слотов, цели дней и размер маржи.",
         "Делистинг TON: свечи после 23 июня 2026 были нулевыми, они исключены. GRAM — отдельный контракт.",
         "Здесь нет реальной принудительной ликвидации на границах периодов, только отдельная mark-to-market оценка открытых позиций.",
         "Исследование описательное/ретроспективное; нужен новый OOS и точный Upscale портфель перед выводом о лучшем тайм-лимите."]
    (ROOT/"DELTARSI_CYCLE_48H.md").write_text("\n".join(md)+"\n")


if __name__=="__main__":
    main()
