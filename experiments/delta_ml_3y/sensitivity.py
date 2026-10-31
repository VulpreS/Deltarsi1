"""Out-of-sample-preserving robustness audit of the preselected ETH/LINK candidate.

Do not refit rules to inspected Aug-Oct data. Data source = prior GitHub
Actions artifact. Margin 16.8% of initial equity per position, 1x notional.
Strictly research, not prop-rule compliance or live-order instructions.
"""
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import research_rules as rr
from train import ASSETS, ROOT, features

FULL = ("BTCUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT")
FOCUS = ("ETHUSDT", "LINKUSDT")
START = int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
PERIODS = {"calibration":(START,rr.DATE_A),"validation1":(rr.DATE_A,rr.DATE_B),
           "validation2":(rr.DATE_B,rr.CUT),"inspected_aug_oct":(rr.CUT,2**62)}
RULES = {
    "selected_equal_rr": ("strict_trend",2.5,2.5,(0.,0.),"reverse_fade"),
    "stability_no_tp": ("strict_trend",2.5,0.,(3.,1.5),"zero_cross"),
    "no_ema200_control": ("strict",2.5,2.5,(0.,0.),"reverse_fade"),
    "no_tp_no_trail": ("strict_trend",2.5,0.,(0.,0.),"zero_cross")
}
COSTS = (0.0018,0.0036,0.005)
INITIAL = 5000.
POSITION = 0.168 * INITIAL

def portfolio(ledger, arrays, start, end):
    """Stress estimate of worst simultaneous OHLC adverse mark on a 4h grid.

    Each asset has at most one position; orders are assumed filled as by the
    base backtest. No intrabar cross-asset execution ordering is inferred.
    """
    ledger = sorted(ledger,key=lambda z:(z["exit_ms"],z["entry_ms"]))
    ticks=sorted(set(int(t) for sym in FOCUS for t in arrays[sym]["t"]
                     if start<=t<end))
    lookup={sym:{int(t):i for i,t in enumerate(d["t"])}
            for sym,d in arrays.items() if sym in FOCUS}
    peak=INITIAL
    max_peak_dd=0.
    min_initial_equity=INITIAL
    day_equity=None
    prev_day=None
    daily_breach_dates=set()
    fixed_10pct_breach=False
    trailing_10pct_breach=False
    max_slots=0
    history=[]
    for t in ticks:
        # Whole prior trades are realized; same-candle stops are treated as still
        # open for adverse marking on the exit candle (conservative).
        done=[p for p in ledger if p["exit_ms"]<t]
        active=[p for p in ledger if p["entry_ms"]<=t<=p["exit_ms"]]
        base=INITIAL+sum(POSITION*p["ret"] for p in done)
        open_pnl=0.
        worst_pnl=0.
        for p in active:
            sym=p["symbol"]
            i=lookup[sym].get(t)
            if i is None:
                continue
            d=arrays[sym]
            side=p["side"]
            v0=float(d["op"][i])
            adverse=float(d["low"][i] if side==1 else d["high"][i])
            open_pnl += POSITION*(side*(v0/p["entry"]-1)-rr.COST_RT)
            worst_pnl += POSITION*(side*(adverse/p["entry"]-1)-rr.COST_RT)
        open_eq=base+open_pnl
        adverse_eq=base+worst_pnl
        day=t//(24*3600000)
        if day!=prev_day:
            prev_day=day
            day_equity=open_eq
        peak=max(peak,open_eq)
        max_peak_dd=max(max_peak_dd,1-adverse_eq/peak)
        min_initial_equity=min(min_initial_equity,adverse_eq)
        if adverse_eq<day_equity*.95:
            daily_breach_dates.add(day)
        fixed_10pct_breach |= adverse_eq<INITIAL*.90
        trailing_10pct_breach |= adverse_eq<peak*.90
        max_slots=max(max_slots,len(active))
        if t%(7*24*3600000)==0:
            history.append([t,round(open_eq,2),round(adverse_eq,2)])
    final=INITIAL+sum(POSITION*p["ret"] for p in ledger)
    return dict(trades=len(ledger),starting_balance_usd=INITIAL,
        fixed_position_usd=POSITION,final_balance_usd=round(final,2),
        net_pct=round(100*(final/INITIAL-1),3),
        adverse_4h_peak_dd_pct=round(100*max_peak_dd,3),
        worst_intrabar_mark_to_initial_pct=round(100*(min_initial_equity/INITIAL-1),3),
        daily_5pct_breach_dates=len(daily_breach_dates),
        fixed_initial_10pct_breach=bool(fixed_10pct_breach),
        trailing_10pct_from_peak_breach=bool(trailing_10pct_breach),
        max_simultaneous_positions=max_slots,
        equity_sample=history)


def run():
    arrays={}
    entrysets={}
    for sym in FULL:
        f=ROOT/"data"/(sym+".json")
        if not f.exists():
            raise FileNotFoundError(f)
        arrays[sym]=rr.make_arrays(features(json.loads(f.read_text()),sym))
    for sym,d in arrays.items():
        for mode in ("strict","strict_trend"):
            entrysets[(sym,mode)]=rr.candidates(d,mode)
    report=dict(source="PREVIOUS 41231907011 ARTIFACT; no network market data",
         code_sha=os.environ.get("GITHUB_SHA","local"),
         github_run=os.environ.get("GITHUB_RUN_ID","local"),
         asset_selection="ETH/LINK selected ONLY because both pass all three pre-August chronological checks on both previous policies",
         periods={k:[rr.iso(a),rr.iso(b) if b<2**62 else "latest cached 2026-10-27"] for k,(a,b) in PERIODS.items()},
         cost_stress={},controls={},portfolio={},checks={})
    for label,p in RULES.items():
        report["controls"][label]={}
        for name,period in PERIODS.items():
            rr.COST_RT=0.0018
            out=rr.evaluate(arrays,entrysets,p,*period)
            report["controls"][label][name]=out["summary"]
    for label in ("selected_equal_rr","stability_no_tp"):
        p=RULES[label]
        report["cost_stress"][label]={}
        for cost in COSTS:
            rr.COST_RT=cost
            per={}
            for name,period in PERIODS.items():
                selected={k:v for k,v in arrays.items() if k in FOCUS}
                result=rr.evaluate(selected,entrysets,p,*period,include_ledger=True)
                per[name]=dict(summary=result["summary"],
                               by_symbol=result["by_asset"])
                if cost==0.0018:
                    port=portfolio(result["ledger"],arrays,*period)
                    # Don't include large detailed curve in compact report
                    port.pop("equity_sample",None)
                    report["portfolio"].setdefault(label,{})[name]=port
            report["cost_stress"][label][str(cost)]=per
    report["checks"]["all_three_positive_at_base_cost"]={
        label: all(all(report["cost_stress"][label]["0.0018"][per]["by_symbol"][sym]["return_pct"]>0 for sym in FOCUS)
            for per in ("calibration","validation1","validation2"))
        for label in ("selected_equal_rr","stability_no_tp")}
    report["checks"]["all_three_positive_at_double_cost"]={
        label: all(all(report["cost_stress"][label]["0.0036"][per]["by_symbol"][sym]["return_pct"]>0 for sym in FOCUS)
            for per in ("calibration","validation1","validation2"))
        for label in ("selected_equal_rr","stability_no_tp")}
    report["caveats"]=[
        "Aug-Oct test was previously inspected; cannot count as virgin untouched validation",
        "Asset selection ETH/LINK is post-selection over six candidates; requires future forward test",
        "Worst OHLC mark on each 4h is conservative across assets but not an exact 1h/tick risk replay",
        "Fee and spread approximations, no funding, no slippage shocks, no actual Upscale platform margin accounting",
        "No forced 48h exit; a trade may remain open until SL, TP, trailing, opposite fade, Delta zero-crossing or evaluation boundary",
        "Portfolio: two independent simultaneous positions of 16.8% INITIAL balance each, maximum 2 active",
        "Performance is not verified compliance with any prop-firm challenge; no real orders"
    ]
    out=ROOT/"sensitivity_report.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    summary=dict(checks=report["checks"],
        base_cost_selected={period:report["cost_stress"]["selected_equal_rr"]["0.0018"][period]["summary"] for period in PERIODS},
        double_cost_selected={period:report["cost_stress"]["selected_equal_rr"]["0.0036"][period]["summary"] for period in PERIODS},
        portfolio_selected=report["portfolio"]["selected_equal_rr"])
    print("SENSITIVITY_REPORT",json.dumps(summary,ensure_ascii=False),flush=True)
    lines=["# DeltaRSI – ETH + LINK: комиссия и портфельный риск","",
        "На этих данных все правила были выбраны по периодам ДО 01.08.2026. Последние месяцы просмотрены ранее.",
        "Данные: только артефакт Actions, без нового скачивания.","",
        "Правило A: medium→weak по точному Pine + EMA200 по направлению сделки; SL/TP 2.5 ATR; выход на обратном сигнале.",
        "Правило B: такой же вход, SL 2.5 ATR, без тейка, trailing после +3 ATR на 1.5 ATR, выход при пересечении нуля Delta.",
        "Маржа 16.8% стартовых $5000 на монету, плечо для исследования 1x, максимум 2 позиции.","",
        "| Период | 1× ETH+LINK; 0.18% roundtrip | Капитал с $5000 | Худшая 4h DD (оценка) | Дней с возможным нарушением 5% |",
        "|---|---:|---:|---:|---:|"]
    for period in PERIODS:
        p0=report["portfolio"]["selected_equal_rr"][period]
        s0=report["cost_stress"]["selected_equal_rr"]["0.0018"][period]["summary"]
        lines.append(f"| {period} | {s0['mean_asset_return_pct']:.2f}% средн. по активам | ${p0['final_balance_usd']:.2f} | {p0['adverse_4h_peak_dd_pct']:.2f}% | {p0['daily_5pct_breach_dates']} |")
    lines+=["","Результаты индивидуальных активов и удвоенной комиссии — в sensitivity_report.json.",
        "Все результаты условные: нет подтверждённой проп-комплаенс модели или реального исполнения."]
    (ROOT/"SENSITIVITY_REPORT.md").write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    run()
