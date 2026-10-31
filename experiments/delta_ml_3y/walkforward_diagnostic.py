"""Monthly forward-chaining-style stability diagnostics for PRESELECTED ETH/LINK rules.

Historical only (2023-11-01 through 2026-07-31). Does not select a policy
or tune any thresholds. Trades run CONTINUOUSLY across month boundaries;
cash PnL is assigned to month of trade close. Moving-block bootstrap
estimates sampling variability, not data-snooping-adjusted confidence.
"""
import collections
import datetime as dt
import json
import math
import os
import pathlib

import numpy as np

import research_rules as rr
from train import ROOT, features

ASSETS=("ETHUSDT","LINKUSDT")
START_MS=int(dt.datetime(2023,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
CUTOFF=int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()*1000)
RULES={
 "primary": ("strict_trend",2.5,2.5,(0.,0.),"reverse_fade"),
 "alternative": ("strict_trend",2.5,0.,(3.,1.5),"zero_cross"),
}
FIXED_POSITION_USD=840.
START_EQUITY_USD=5000.
FEE_SCENARIOS=(0.0018,0.0036)
MONTHLY_BLOCK=3
BOOT_REPS=4000


def months():
    y,m=2023,11
    while (y,m)<(2026,8):
        yield f"{y:04d}-{m:02d}"
        y,m=(y+1,1) if m==12 else (y,m+1)


def iso(ms):
    return dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc).isoformat()


def monthly_bootstrap(values):
    arr=np.asarray(values,dtype=float)
    n=len(arr)
    rng=np.random.default_rng(20261031)
    draws=[]
    for _ in range(BOOT_REPS):
        output=[]
        while len(output)<n:
            start=int(rng.integers(0,n))
            output.extend(arr[(start+j)%n] for j in range(MONTHLY_BLOCK))
        draws.append(sum(output[:n]))
    return dict(p05_total_pct=round(float(np.percentile(draws,5)),3),
      p50_total_pct=round(float(np.percentile(draws,50)),3),
      p95_total_pct=round(float(np.percentile(draws,95)),3),
      resampled_positive_fraction=round(float(np.mean(np.asarray(draws)>0)),4),
      n_months=n,block_months=MONTHLY_BLOCK,repetitions=BOOT_REPS)


def run_trades(d,rule):
    signals=rr.candidates(d,rule[0])
    limit=int(np.searchsorted(d["t"],CUTOFF))
    next_free=START_MS
    trades=[]
    boundary_open=[]
    for i,side in signals:
        entry=int(d["t"][i+1])
        if entry<START_MS or entry>=CUTOFF or entry<next_free:
            continue
        trade=rr.trade(d,i,side,limit,rule)
        if trade is None:
            continue
        if trade["reason"]=="evaluation_boundary":
            boundary_open.append(trade)
            break
        trades.append(trade)
        next_free=int(trade["exit_ms"])+rr.STEP if hasattr(rr,"STEP") else int(trade["exit_ms"])+4*3600000
    return trades,boundary_open


def diagnostics():
    arrays={}
    for symbol in ASSETS:
        p=ROOT/"data"/(symbol+".json")
        if not p.is_file():
            raise FileNotFoundError("historical cache missing "+str(p))
        rows=json.loads(p.read_text())
        arrays[symbol]=rr.make_arrays(features(rows,symbol))
    all_months=list(months())
    results={}
    for rule_label,rule in RULES.items():
        results[rule_label]={}
        for fee in FEE_SCENARIOS:
            rr.COST_RT=fee
            ledger=[]
            pending=0
            for sym,d in arrays.items():
                trades,open_at_cut=run_trades(d,rule)
                pending+=len(open_at_cut)
                ledger.extend({**t,"symbol":sym} for t in trades)
            by_month={m:dict(ETHUSDT=0.,LINKUSDT=0.,trades=0,win=0)
                      for m in all_months}
            ledger.sort(key=lambda x:(x["exit_ms"],x["symbol"]))
            for t in ledger:
                month=iso(t["exit_ms"])[:7]
                if month not in by_month:
                    continue
                by_month[month][t["symbol"]]+=FIXED_POSITION_USD*t["ret"]
                by_month[month]["trades"]+=1
                by_month[month]["win"]+=int(t["ret"]>0)
            month_rows=[]
            for m,cell in by_month.items():
                pnl=float(cell["ETHUSDT"]+cell["LINKUSDT"])
                month_rows.append(dict(month=m,closed_trades=cell["trades"],
                  eth_cash_pnl=round(cell["ETHUSDT"],2),
                  link_cash_pnl=round(cell["LINKUSDT"],2),
                  portfolio_return_pct=round(100*pnl/START_EQUITY_USD,4)))
            values=[x["portfolio_return_pct"] for x in month_rows]
            cum=np.cumsum(values)
            equity=np.r_[0,cum]
            high=np.maximum.accumulate(equity)
            dd=np.max(high-equity)
            raw_by_asset={sym:sum(FIXED_POSITION_USD*t["ret"] for t in ledger if t["symbol"]==sym) for sym in ASSETS}
            rolling3=[sum(values[i:i+3]) for i in range(len(values)-2)]
            rolling6=[sum(values[i:i+6]) for i in range(len(values)-5)]
            years={}
            for row in month_rows:
                y=row["month"][:4]
                years[y]=round(years.get(y,0)+row["portfolio_return_pct"],4)
            report=dict(
                rule=rule_label,fee_roundtrip=fee,source="cached 3yr Binance Vision 4h archive",
                cutoff=iso(CUTOFF),
                no_fit_no_tuning=True,manual_trades_used=False,
                month_rows=month_rows,annual_pnl_pct=years,
                metrics=dict(months=len(month_rows),closed_trades=len(ledger),
                    open_positions_at_training_boundary=pending,
                    account_return_pct=round(float(sum(values)),3),
                    eth_return_pct=round(100*raw_by_asset["ETHUSDT"]/START_EQUITY_USD,3),
                    link_return_pct=round(100*raw_by_asset["LINKUSDT"]/START_EQUITY_USD,3),
                    profitable_months=sum(v>0 for v in values),
                    loss_months=sum(v<0 for v in values),
                    no_close_months=sum(x["closed_trades"]==0 for x in month_rows),
                    max_drawdown_on_month_end_realized_pct=round(float(dd),3),
                    worst_3m_closed_pct=round(float(min(rolling3)),3),
                    worst_6m_closed_pct=round(float(min(rolling6)),3),
                    best_month_pct=round(float(max(values)),3),
                    worst_month_pct=round(float(min(values)),3),
                    bootstrap_3mo=monthly_bootstrap(values)))
            results[rule_label][str(fee)]=report
    doc=dict(title="Prospective research prerequisite: frozen-rule monthly diagnostic",
      run_id=os.environ.get("GITHUB_RUN_ID","local"),
      code_sha=os.environ.get("GITHUB_SHA","local"),
      current_policy_selection_date="2026-10-31",
      is_independent_test=False,preselected_symbols=ASSETS,
      cross_month_trades="not forcibly closed at month boundary",
      no_48h_cap=True,
      results=results,
      caveats=[
       "Rules and ETH/LINK pair were selected with knowledge of history; this historical month split is NOT an independent walk-forward discovery test",
       "No refitting occurs month to month. Only a frozen-rule rolling diagnostics, NOT a nested reoptimized OOS study",
       "Closed PnL attributed to EXIT month; mark-to-market and intrabar drawdowns omitted from monthly diagnostic",
       "Cash PnL fixed $840 each trade / $5000 account (16.8% initial, no leverage); not compounded",
       "Last open position at Aug1 excluded from closed PnL; no artificial 48h exit",
       "3-month moving block bootstrap captures time dependence crudely; selection bias not corrected",
       "August-October 2026 already inspected; NEVER use it to optimize; prospective starts Nov1",
       "Funding, Upscale equity stop and real execution not validated"
      ])
    (ROOT/"WALKFORWARD_DIAGNOSTIC.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2))
    items=[]
    for name in RULES:
        for fee in FEE_SCENARIOS:
            obj=results[name][str(fee)]
            items.append(dict(rule=name,cost=fee,metrics=obj["metrics"]))
    print("WALKFORWARD_DIAGNOSTIC",json.dumps(items,ensure_ascii=False),flush=True)
    lines=["# Диагностика неизменных правил DeltaRSI по месяцам","",
       "В этой проверке нет оптимизации. История до 01.08.2026 была известна при выборе ETH/LINK, поэтому это не независимый OOS.",
       "Переходящие между месяцами позиции НЕ закрываются искусственно. PnL относится к месяцу закрытия сделки.",
       "Реальные будущие данные оцениваются отдельно, начиная с 01.11.2026.","",
       "| Правило | Полные расходы | Сделок | Результат счёта | Убыточных месяцев | Худшие 3 месяца | Bootstrap 5% |",
       "|---|---:|---:|---:|---:|---:|---:|"]
    for item in items:
        m=item["metrics"]
        lines.append(f"| {item['rule']} | {100*item['cost']:.2f}% | {m['closed_trades']} | "
          f"{m['account_return_pct']:.2f}% | {m['loss_months']} | "
          f"{m['worst_3m_closed_pct']:.2f}% | {m['bootstrap_3mo']['p05_total_pct']:.2f}% |")
    lines+=["","## Предостережение","",
        "Bootstrap — условная неопределённость уже выбранных правил; он не устраняет data snooping.",
        "Для настоящего подтверждения необходимо продолжить неизменный бумажный форвард после 1 ноября 2026.",
        "Полная таблица 33 месячных периодов и bootstrap находится в WALKFORWARD_DIAGNOSTIC.json."]
    (ROOT/"WALKFORWARD_DIAGNOSTIC.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    diagnostics()
