"""Causal 4h DeltaRSI market-regime study across eight Binance futures assets.

Core question: can a shared causal entry filter generalize, while EXIT rules
vary by trend/strength regime? No real orders, no 48h force close.
- Existing six assets: immutable release restored by workflow.
- ICP/ZEC: additional immutable release from separate source-only download.
- Every feature is as of signal-bar CLOSE.
- Exit-choice training uses ONLY trades exiting before the training cutoff.
- Calibration -> validation1 and expanding calibration+validation1 -> validation2.
- Aug-Oct 2026 previously inspected; diagnostic only, NEVER used for choice.
- Leave-one-coin-out on validation2 tests transfer to an unseen coin.
"""
import collections
import datetime as dt
import hashlib
import itertools
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

import research_rules as rr
from train import ROOT, features

ASSETS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","LINKUSDT",
        "TONUSDT","ICPUSDT","ZECUSDT")
CUTOFF_A=rr.DATE_A    # 2025-07-01
CUTOFF_B=rr.DATE_B    # 2026-02-01
CUTOFF_C=rr.CUT       # 2026-08-01
ALL_END=2**62
COST_RT=.0018
DOUBLE_COST_RT=.0036
ACCOUNT_USD=5000.
POSITION_USD=840.
REGIMES=("UP_STRONG","UP_WEAK","DOWN_STRONG","DOWN_WEAK","RANGE")
BASELINE="symmetric"
EXIT_PROFILES={
 "symmetric":("strict",2.5,2.5,(0.,0.),"reverse_fade"),
 "tight":("strict",1.5,2.5,(0.,0.),"reverse_fade"),
 "wide":("strict",4.0,5.0,(0.,0.),"reverse_fade"),
 "zero_trail":("strict",2.5,0.,(3.,1.5),"zero_cross"),
 "wide_zero":("strict",4.,5.,(3.,1.5),"zero_cross"),
 "momentum":("strict",2.5,5.,(3.,1.5),"momentum_rollover"),
 "risk_trail":("strict",2.5,2.5,(3.,1.5),"risk_only"),
}
ENTRY_POLICIES=("strict_all","strict_align","strict_no_counter",
                "strict_strong_only","expanded_align","expanded_all")


def iso(t):
    return dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).isoformat()


def add_regime(d):
    """Closed-bar only regime: EMA200 slope and EMA50 structure + ADX14.

    Flags exploding ATR/close relative to 120 *past* closed bars.
    This is not an objective ground truth, only an explicit testable definition.
    """
    high=pd.Series(d["high"])
    low=pd.Series(d["low"])
    close=pd.Series(d["close"])
    tr=pd.concat((high-low,(high-close.shift(1)).abs(),
                  (low-close.shift(1)).abs()),axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rise=high.diff();fall=-low.diff()
    plus=pd.Series(np.where((rise>fall)&(rise>0),rise,0.))
    minus=pd.Series(np.where((fall>rise)&(fall>0),fall,0.))
    plusdi=100*plus.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr.replace(0,np.nan)
    minusdi=100*minus.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr.replace(0,np.nan)
    dx=100*(plusdi-minusdi).abs()/(plusdi+minusdi).replace(0,np.nan)
    adx=dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    ema50=close.ewm(span=50,adjust=False).mean()
    ema200=close.ewm(span=200,adjust=False).mean()
    # 18×4h slope normalized by current ATR is dimensionless.
    slope=(ema200-ema200.shift(18))/atr.replace(0,np.nan)
    pct_atr=atr/close.replace(0,np.nan)
    volref=pct_atr.shift(1).rolling(120,min_periods=100).median()
    expansion=(pct_atr/volref.replace(0,np.nan)>1.55).fillna(False)
    up=(close>ema200)&(ema50>ema200)&(slope>.15)
    down=(close<ema200)&(ema50<ema200)&(slope<-.15)
    strong=(adx>=24.)
    regime=np.full(len(d["close"]),"RANGE",dtype=object)
    upa=up.to_numpy();dna=down.to_numpy();sta=strong.to_numpy()
    regime[upa&sta]="UP_STRONG"
    regime[upa&~sta]="UP_WEAK"
    regime[dna&sta]="DOWN_STRONG"
    regime[dna&~sta]="DOWN_WEAK"
    d.update(regime=regime,adx=np.nan_to_num(adx.to_numpy(),nan=0.),
        slope_atr=np.nan_to_num(slope.to_numpy(),nan=0.),
        atr_pct=np.nan_to_num(pct_atr.to_numpy(),nan=0.),
        vol_expand=expansion.to_numpy().astype(bool))
    return d


def classify_coins():
    assets={}
    source={}
    for sym in ASSETS:
        path=ROOT/"data"/(sym+".json")
        if not path.is_file():
            raise FileNotFoundError(f"{sym} missing frozen cache {path}")
        payload=path.read_bytes()
        rows=json.loads(payload)
        if len(rows)<3000:
            raise RuntimeError(f"Insufficient {sym} history: {len(rows)}")
        if any(b[0]-a[0]!=4*3600000 for a,b in zip(rows,rows[1:])):
            raise RuntimeError(f"{sym}: 4h missing candle; no interpolation")
        d=add_regime(rr.make_arrays(features(rows,sym)))
        assets[sym]=d
        source[sym]=dict(rows=len(rows),first=iso(rows[0][0]),
           last=iso(rows[-1][0]),sha256=hashlib.sha256(payload).hexdigest(),
           last_regime=str(d["regime"][-1]),last_adx=round(float(d["adx"][-1]),2),
           last_ema_slope_atr=round(float(d["slope_atr"][-1]),3),
           last_atr_pct=round(float(d["atr_pct"][-1])*100,3),
           latest_vol_expansion=bool(d["vol_expand"][-1]))
    return assets,source


def is_entry_eligible(ev,policy):
    strict=ev["strict"]
    aligned=((ev["regime"].startswith("UP") and ev["side"]==1) or
             (ev["regime"].startswith("DOWN") and ev["side"]==-1))
    counter=((ev["regime"].startswith("UP") and ev["side"]==-1) or
             (ev["regime"].startswith("DOWN") and ev["side"]==1))
    strong=ev["regime"].endswith("STRONG")
    if policy=="strict_all":
        return strict
    if policy=="strict_align":
        return strict and aligned
    if policy=="strict_no_counter":
        return strict and not counter
    if policy=="strict_strong_only":
        return strict and aligned and strong
    if policy=="expanded_align":
        return aligned
    if policy=="expanded_all":
        return True
    raise ValueError(policy)


def prepare_events(assets):
    """Cache all historical counterfactual outcomes, but mask by exit timestamp
    in training. Nothing from the OOS windows is used for fitting choices.
    """
    events={}
    by_symbol=collections.Counter()
    for sym,d in assets.items():
        raw=rr.candidates(d,"expanded")
        evs=[]
        for i,side in raw:
            if i+1>=d["n"]-1:
                continue
            old=int(d["shade"][i-1])
            strict=(old==6 or old==2)
            reg=str(d["regime"][i])
            record=dict(symbol=sym,i=i,side=side,strict=strict,
                  regime=reg,volatile=bool(d["vol_expand"][i]),
                  adx=round(float(d["adx"][i]),2),
                  entry_ms=int(d["t"][i+1]),outcomes={})
            for style,p in EXIT_PROFILES.items():
                outcome=rr.trade(d,i,side,d["n"],p)
                if outcome is None or outcome["reason"]=="evaluation_boundary":
                    continue  # censored, never silently treat as profitable
                record["outcomes"][style]=outcome
            evs.append(record)
            by_symbol[sym]+=1
        events[sym]=evs
    return events,dict(by_symbol)


def fit_exit_map(events,train_end,excluded=None):
    """One pooled EXIT profile per regime × side, trained across assets.

    Requires >=12 completed independent signal examples and >=3 source coins.
    Sparse regimes fall back to fixed symmetric, never to future labels.
    """
    excluded=set(excluded or ())
    candidates=collections.defaultdict(list)
    for sym,evs in events.items():
        if sym in excluded:
            continue
        for ev in evs:
            if not ev["strict"] or ev["entry_ms"]>=train_end:
                continue
            candidates[(ev["regime"],ev["side"])].append(ev)
    mapping={}
    diagnostics={}
    for regime in REGIMES:
        for side in (1,-1):
            k=(regime,side)
            cohort=candidates[k]
            result=[]
            for style in EXIT_PROFILES:
                completed=[(ev,o) for ev in cohort
                         if (o:=ev["outcomes"].get(style)) is not None and
                            o["exit_ms"]<train_end]
                counts=collections.Counter(ev["symbol"] for ev,_ in completed)
                n=len(completed)
                if n<12 or len(counts)<3:
                    continue
                net=np.array([o["ret"] for _,o in completed],dtype=float)
                bycoin=[float(np.mean([o["ret"] for ev,o in completed
                         if ev["symbol"]==coin])) for coin in counts]
                # Do not reward profiles that never exit and conceal trades.
                coverage=n/max(1,len(cohort))
                # Mean plus lower-tail and transfer sensitivity.
                sc=(100*(.55*np.mean(net)+.30*np.quantile(net,.2)
                         +.15*np.median(bycoin))
                    -3.5*(1-coverage)
                    -.03*float(np.median([o["hold_hours"] for _,o in completed]))/24)
                # Regularize towards simplest baseline, avoid sparse overfit.
                if style==BASELINE:
                    sc+=.08
                result.append(dict(style=style,score=round(float(sc),5),
                    n=n,assets=len(counts),coverage=round(coverage,3),
                    mean_pct=round(100*float(np.mean(net)),3),
                    p20_pct=round(100*float(np.quantile(net,.2)),3)))
            result.sort(key=lambda x:x["score"],reverse=True)
            pick=result[0]["style"] if result else BASELINE
            mapping[k]=pick
            diagnostics[f"{regime}:{'LONG' if side==1 else 'SHORT'}"]=dict(
                total_signals=len(cohort),selected=pick,
                all_profiles=result,reason="insufficient independent cross-coin observations"
                  if not result else "selected on pre-cutoff realized outcomes")
    return mapping,diagnostics


def run_period(events, policy, regime_map, start, end, cost=COST_RT,
               selected_assets=None,with_trades=False):
    chosen=set(selected_assets or events)
    byasset={}
    ledger=[]
    by_reg=collections.defaultdict(lambda:dict(n=0,cash_pct=0.,positive=0))
    for sym in sorted(chosen):
        candidates=events.get(sym,[])
        equity=ACCOUNT_USD
        peak=ACCOUNT_USD
        next_allowed=start
        count=0
        wins=0
        for ev in candidates:
            if ev["entry_ms"]<start or ev["entry_ms"]>=end:
                continue
            if ev["entry_ms"]<next_allowed or not is_entry_eligible(ev,policy):
                continue
            style=regime_map.get((ev["regime"],ev["side"]),BASELINE)
            trade=ev["outcomes"].get(style)
            if not trade:
                continue
            if trade["exit_ms"]>=end:
                continue  # never book a future exit in a past fold
            net=trade["ret"]-(cost-COST_RT)
            equity+=POSITION_USD*net
            peak=max(peak,equity)
            count+=1
            wins+=int(net>0)
            next_allowed=trade["exit_ms"]+1  # skip signal in same exit 4h candle
            bucket=f"{ev['regime']}:{'LONG' if ev['side']==1 else 'SHORT'}"
            by_reg[bucket]["n"]+=1
            by_reg[bucket]["cash_pct"]+=100*POSITION_USD*net/ACCOUNT_USD
            by_reg[bucket]["positive"]+=int(net>0)
            if with_trades:
                ledger.append(dict(symbol=sym,regime=ev["regime"],side=ev["side"],
                    entry=iso(trade["entry_ms"]),exit=iso(trade["exit_ms"]),
                    exit_style=style,entry_type="strict" if ev["strict"] else "expanded",
                    entry_adx=ev["adx"],high_volatility=ev["volatile"],
                    net_pct_nominal=round(100*net,4),
                    account_cash_pnl=round(POSITION_USD*net,2),
                    exit_reason=trade["reason"],hold_hours=trade["hold_hours"]))
        byasset[sym]=dict(trades=count,return_pct=round(100*(equity/ACCOUNT_USD-1),3),
                         profit_usd=round(equity-ACCOUNT_USD,2),
                         win_pct=round(100*wins/count,1) if count else None)
    returns=[v["return_pct"] for v in byasset.values()]
    summed=sum(v["trades"] for v in byasset.values())
    summary=dict(symbols=len(byasset),trades=summed,mean_coin_return_pct=round(float(np.mean(returns)),3),
        median_coin_return_pct=round(float(np.median(returns)),3),
        worst_coin_return_pct=round(float(min(returns)),3),
        profitable_coins=sum(x>0 for x in returns),
        total_cash_pnl_usd=round(sum(v["profit_usd"] for v in byasset.values()),2))
    by_reg_out={k:dict(n=v["n"],cash_pct=round(v["cash_pct"],3),
                win_pct=round(100*v["positive"]/v["n"],1)) for k,v in by_reg.items()}
    return dict(summary=summary,by_asset=byasset,by_regime=by_reg_out,
                trade_ledger=ledger if with_trades else None)


def pick_entry(events,mapping,start,end,excluded=None):
    """Choose one SHARED entry policy using only earlier fold."""
    included=[s for s in events if s not in set(excluded or ())]
    candidates=[]
    for policy in ENTRY_POLICIES:
        stats=run_period(events,policy,mapping,start,end,selected_assets=included)["summary"]
        n=stats["trades"]
        if n<40:
            score=-1000+n
        else:
            score=(.68*stats["mean_coin_return_pct"] +
                   .25*stats["median_coin_return_pct"] +
                   .20*stats["worst_coin_return_pct"] +
                   .15*stats["profitable_coins"])
            if policy=="strict_all":
                score+=.30  # prespecified preference for simpler true user signal
            if policy.startswith("expanded"):
                score-=.20
        candidates.append(dict(entry=policy,score=round(score,4),stats=stats))
    candidates.sort(key=lambda x:x["score"],reverse=True)
    return candidates[0]["entry"],candidates


def occupancy(assets):
    result={}
    for sym,d in assets.items():
        segments={}
        for label,(start,end) in {
            "calibration":(0,CUTOFF_A),"validation1":(CUTOFF_A,CUTOFF_B),
            "validation2":(CUTOFF_B,CUTOFF_C),"inspected_aug_oct":(CUTOFF_C,ALL_END)
        }.items():
            r=d["regime"][(d["t"]>=start)&(d["t"]<end)]
            counts=collections.Counter(r.tolist())
            n=len(r)
            segments[label]=dict(bars=n,counts=dict(counts),
                 proportions={k:round(counts.get(k,0)/n,3) for k in REGIMES} if n else {})
        result[sym]=segments
    return result


def diagnose_events(events):
    out={}
    for sym,evs in events.items():
        data=collections.defaultdict(lambda:dict(signals=0,strict=0,long=0,short=0,expanded=0))
        for ev in evs:
            cohort= "calibration" if ev["entry_ms"]<CUTOFF_A else (
                "validation1" if ev["entry_ms"]<CUTOFF_B else (
                "validation2" if ev["entry_ms"]<CUTOFF_C else "inspected_aug_oct"))
            stats=data[(cohort,ev["regime"])]
            stats["signals"]+=1
            stats["strict"]+=int(ev["strict"])
            stats["expanded"]+=int(not ev["strict"])
            stats["long" if ev["side"]==1 else "short"]+=1
        out[sym]={f"{k[0]}:{k[1]}":v for k,v in data.items()}
    return out


def main():
    rr.COST_RT=COST_RT
    assets,sources=classify_coins()
    events,counts=prepare_events(assets)
    baseline={(r,s):BASELINE for r in REGIMES for s in (-1,1)}

    # Phase A: calibration only; July 2025—Jan 2026 was never a training label.
    map_a,map_diag_a=fit_exit_map(events,CUTOFF_A)
    chosen_a,rank_a=pick_entry(events,map_a,0,CUTOFF_A)
    val_a=run_period(events,chosen_a,map_a,CUTOFF_A,CUTOFF_B,with_trades=True)
    base_val_a=run_period(events,"strict_all",baseline,CUTOFF_A,CUTOFF_B)

    # Phase B: expanding train through Jan 2026. Feb-Jul 2026 is next check.
    map_b,map_diag_b=fit_exit_map(events,CUTOFF_B)
    chosen_b,rank_b=pick_entry(events,map_b,0,CUTOFF_B)
    val_b=run_period(events,chosen_b,map_b,CUTOFF_B,CUTOFF_C,with_trades=True)
    base_val_b=run_period(events,"strict_all",baseline,CUTOFF_B,CUTOFF_C)
    stress_val_b=run_period(events,chosen_b,map_b,CUTOFF_B,CUTOFF_C,
                            cost=DOUBLE_COST_RT)

    # Transfer: on each coin, fit on OTHER seven, and test this coin in val2.
    transfer={}
    for sym in ASSETS:
        excluded={sym}
        loo_map,_=fit_exit_map(events,CUTOFF_B,excluded=excluded)
        loo_entry,rank_=pick_entry(events,loo_map,0,CUTOFF_B,excluded=excluded)
        tr=run_period(events,loo_entry,loo_map,CUTOFF_B,CUTOFF_C,
                      selected_assets=[sym],with_trades=True)
        transfer[sym]=dict(trained_on=[x for x in ASSETS if x!=sym],
                           entry=loo_entry,holdout=tr["summary"],
                           by_asset=tr["by_asset"],regime=tr["by_regime"])

    # Only a diagnostic: the 2026 Aug-Oct market has ALREADY been inspected.
    inspected=run_period(events,chosen_b,map_b,CUTOFF_C,ALL_END,with_trades=True)
    base_inspected=run_period(events,"strict_all",baseline,CUTOFF_C,ALL_END)

    output=dict(title="DeltaRSI 8-asset shared regime-conditioned entry and exit experiment",
       research_only=True,code_sha=os.environ.get("GITHUB_SHA","local"),
       run_id=os.environ.get("GITHUB_RUN_ID","local"),
       assets=ASSETS,sources=sources,
       signal_math="Root Pine Delta executable SMA21(close)->Wilder RSI12->EMA7(RSI)->symmetric signed log Delta threshold60",
       regime_definition=dict(
          trend="close and EMA50 above/below EMA200 and EMA200 18-bar slope more than 0.15 ATR",
          strength="Wilder ADX14 >= 24 marks STRONG; otherwise WEAK",
          range="everything not classified as aligned UP or DOWN",
          volatility_expansion="ATR14/close > 1.55 times previous-120-bar rolling median",
          causal="every input uses candles closed at or before the signal timestamp",
          labels=REGIMES),
       fee_roundtrip=COST_RT,stress_fee_roundtrip=DOUBLE_COST_RT,
       notional_each_trade_usd=POSITION_USD,starting_account_usd=ACCOUNT_USD,
       per_asset_independent=True,
       exit_profiles={k:dict(sl_atr=v[1],tp_atr=v[2],
                 trailing_activation_atr=v[3][0],trailing_distance_atr=v[3][1],
                 histogram_exit=v[4]) for k,v in EXIT_PROFILES.items()},
       entry_policies=ENTRY_POLICIES,
       periods=dict(calibration_end=iso(CUTOFF_A),validation1_end=iso(CUTOFF_B),
                  validation2_end=iso(CUTOFF_C),inspected_only_from=iso(CUTOFF_C)),
       market_occupancy=occupancy(assets),signals_by_regime=diagnose_events(events),
       events_per_symbol=counts,
       phase_A=dict(train_before=iso(CUTOFF_A),selected_entry=chosen_a,
          ranked_entry=rank_a,learned_exits=map_diag_a,
          next_validation=val_a,fixed_baseline=base_val_a),
       phase_B=dict(train_before=iso(CUTOFF_B),selected_entry=chosen_b,
          ranked_entry=rank_b,learned_exits=map_diag_b,
          next_validation=val_b,fixed_baseline=base_val_b,double_fee_validation=stress_val_b),
       leave_one_coin_out_validation2=transfer,
       previously_inspected_aug_oct=dict(regime_policy=inspected,
                                         fixed_baseline=base_inspected),
       flags=dict(independent_unseen_coin_check=True,
          chrono_pre_august_heldout=True,
          august_october_not_untouched=True,
          multiple_comparison_bias=True,
          not_prop_compliant=True,live_orders=False),
       caveats=[
         "All historical folds known in prior research; historical walk-forward does not replace new prospective OOS",
         "Regime definition is hypothesis, not a true latent market state, ADX and EMA are lagging",
         "Market regime computed as of signal close, not future candle",
         "Profiles chosen on hypothetical standalone event cohorts, not an executable nested portfolio; actual execution assessed sequentially in later fold",
         "One at a time per coin, independent $840 fixed notional per coin; NOT a common 3-slot $5000 prop account",
         "Labels learned only from COMPLETED trades exiting prior to cutoff; cohorts with insufficient coin breadth fallback to symmetric",
         "No funding, slippage shocks, 1h/tick execution, full Upscale / Turbo risk compliance",
         "Aug-Oct inspected before this work and cannot be used to select rules",
         "ICP/ZEC historical coverage may differ from TON; metrics show exact dates",
         "No manual trades used and no forced 48-hour exit",
       ])
    path=ROOT/"REGIME_EIGHT_ASSETS_REPORT.json"
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
    headline=dict(
       phase_A=dict(entry=chosen_a,regime=val_a["summary"],
                    constant=base_val_a["summary"]),
       phase_B=dict(entry=chosen_b,regime=val_b["summary"],
                    constant=base_val_b["summary"],
                    double_cost=stress_val_b["summary"]),
       transfer={sym:z["holdout"] for sym,z in transfer.items()},
       diagnostic_inspected=dict(regime=inspected["summary"],
                                baseline=base_inspected["summary"]),
       latest_regimes={sym:data["last_regime"] for sym,data in sources.items()},
       regime_exits={k:v["selected"] for k,v in map_diag_b.items()})
    print("REGIME_EIGHT_ASSETS",json.dumps(headline,ensure_ascii=False),flush=True)

    lines=["# DeltaRSI: восемь разных рынков — общие входы и зависящие от режима выходы","",
       "Это **эксперимент**, а не готовая стратегия. ETH/LINK и четыре индивидуальных правила не переписаны.",
       "8 Binance USD-M 4H: BTC, ETH, BNB, XRP, LINK, TON, ICP, ZEC.",
       "Источник: неизменяемые архивы GitHub Release; повторно загружались только ранее отсутствовавшие ICP/ZEC.",
       "Не использовать август–октябрь для подбора: период ранее просмотрен.",
       "Все признаки на закрытой 4h; никакого принудительного закрытия через 48ч.","",
       "## Гипотеза о режиме рынка","",
       "UP/DOWN определяется EMA200 slope + EMA50, strong/weak — ADX14, RANGE когда согласованного тренда нет.",
       "Флаг всплеска волатильности — ATR% относительно прошлых 120 свечей; в текущем опыте он аналитический, не фильтр входа.",
       "Выход выбирается по режиму НА МОМЕНТ ВХОДА, а не подглядывает в следующие свечи.",
       "",
       "## Исторические последовательные тесты","",
       "| Период | Вход | Адаптивный: сделки / средняя доходность | Постоянный: сделки / средняя доходность |",
       "|---|---|---|---|"]
    for name,step in [("A: июль 2025—январь 2026",output["phase_A"]),
                       ("B: февраль—июль 2026",output["phase_B"])]:
        m=step["next_validation"]["summary"];n=step["fixed_baseline"]["summary"]
        lines.append(f"| {name} | {step['selected_entry']} | {m['trades']} / {m['mean_coin_return_pct']:+.3f}% | {n['trades']} / {n['mean_coin_return_pct']:+.3f}% |")
    lines+=["","## Режимно-зависимые выходы, обученные только до февраля 2026","",
            "| Режим / направление | Профиль выхода | Сделок обучения / причина |",
            "|---|---|---|"]
    for cohort,d in map_diag_b.items():
        lines.append(f"| {cohort} | {d['selected']} | {d['total_signals']}; {d['reason']} |")
    lines+=["","## Проверка переноса на другие монеты (каждая исключалась из обучения)","",
         "| Монета | Вход по другим семи | Сделок | Результат / $5000 |",
         "|---|---|---:|---:|"]
    for sym,z in transfer.items():
        lines.append(f"| {sym} | {z['entry']} | {z['holdout']['trades']} | {z['holdout']['mean_coin_return_pct']:+.3f}% |")
    lines+=["","## Последнее наблюдаемое состояние, **не сигнал входа**","",
         "| Монета | Режим на последней непрерывной 4H свече | ADX14 | Наклон EMA200 / ATR |",
         "|---|---|---:|---:|"]
    for sym,z in sources.items():
        lines.append(f"| {sym} | {z['last_regime']} | {z['last_adx']:.1f} | {z['last_ema_slope_atr']:.2f} |")
    lines+=["","## Ограничения","",
            "Валидация истории ранее исследовалась, это не virgin OOS. Выбор профиля по самостоятельным событиям — приблизительный; затем отдельная последовательная симуляция.",
            "Выводы подвержены data-snooping: несколько режимов и вариантов выхода. Необходим форвард после 01.11.2026 и проверка 1h/tick рисков.",
            "Общая модель проп-счёта 5%/10% и Turbo 6% пока не выполнена.",
            "Все сигналы и сделки в JSON отчёте; никаких реальных торговых ордеров."]
    (ROOT/"REGIME_EIGHT_ASSETS_REPORT.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
