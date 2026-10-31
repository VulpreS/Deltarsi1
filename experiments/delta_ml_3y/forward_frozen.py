"""Frozen, prospective ETH/LINK 4h DeltaRSI paper-only test.

History is restored from an immutable GitHub Actions archive. Fetch ONLY new
daily 4h Binance Vision ZIPs after 2026-10-27, with a SAME-EXCHANGE monthly
archive fallback for a missing daily ZIP. No 3-year redownload, no fit/tuning.
Prospective eligibility starts 2026-11-01T00:00:00Z, after rule selection.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import pathlib
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np

import research_rules as rr
from train import ROOT, features

ASSETS = ("ETHUSDT", "LINKUSDT")
START_FORWARD = dt.datetime(2026,11,1,tzinfo=dt.timezone.utc)
FORWARD_MS = int(START_FORWARD.timestamp()*1000)
STEP = 4*3600*1000
BASES = ("https://data.binance.vision/",
         "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/")
FROZEN = {
    "primary": ("strict_trend",2.5,2.5,(0.0,0.0),"reverse_fade"),
    "alternative": ("strict_trend",2.5,0.0,(3.0,1.5),"zero_cross"),
}
FROZEN_AT = "2026-10-31"
FEE_RT = 0.0018
STARTING_EQUITY = 5000.
POSITION_USD = 840.


def iso(ms):
    return dt.datetime.fromtimestamp(int(ms)/1000,dt.timezone.utc).isoformat()


def fetch_zip(path):
    errors=[]
    missing=0
    for base in BASES:
        url=base+path
        for attempt in range(2):
            try:
                request=urllib.request.Request(url,headers={"User-Agent":"DeltaRSI-frozen-forward/1.0"})
                with urllib.request.urlopen(request,timeout=30) as response:
                    payload=response.read()
                if not payload.startswith(b"PK"):
                    raise ValueError(f"Not a ZIP from {url}: {payload[:100]!r}")
                return payload
            except urllib.error.HTTPError as e:
                if e.code==404:
                    missing+=1
                    break
                errors.append(f"{url} HTTP {e.code}")
                if e.code in (403,451):
                    break
            except (urllib.error.URLError,TimeoutError,ValueError) as e:
                errors.append(f"{url}: {e}")
            if attempt==0:
                time.sleep(1)
    if missing==len(BASES):
        return None
    raise RuntimeError("Archive error: "+ "; ".join(errors[-4:]))


def parse_zip(data,path):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        csv_files=[s for s in archive.namelist() if s.endswith(".csv")]
        if len(csv_files)!=1:
            raise ValueError(f"CSV archive mismatch {path}: {csv_files}")
        rows={}
        with archive.open(csv_files[0]) as src:
            for v in csv.reader(io.TextIOWrapper(src,encoding="utf-8-sig")):
                if not v or not v[0].isdigit():
                    continue
                t=int(v[0])
                if t>10**14:
                    t//=1000
                if t%STEP:
                    raise ValueError(f"Misaligned candle in {path}: {t}")
                rows[t]=[t,*[float(v[i]) for i in (1,2,3,4,5)]]
    return rows


def archive_path(sym,period,when):
    tag=when.isoformat() if isinstance(when,dt.date) else str(when)
    return f"data/futures/um/{period}/klines/{sym}/4h/{sym}-4h-{tag}.zip"


def extend_baseline(symbol,baseline,last_day):
    old_last=int(baseline[-1][0])
    old_day=dt.datetime.fromtimestamp(old_last/1000,dt.timezone.utc).date()
    next_day=old_day+dt.timedelta(days=1)
    known={int(x[0]):x for x in baseline}
    appended=[]
    missing=[]
    fetched=[]
    monthly_cache={}
    while next_day<=last_day:
        path=archive_path(symbol,"daily",next_day)
        body=fetch_zip(path)
        rows=parse_zip(body,path) if body is not None else None
        via="daily"
        if rows is None:
            key=next_day.strftime("%Y-%m")
            if key not in monthly_cache:
                mp=archive_path(symbol,"monthly",key)
                z=fetch_zip(mp)
                monthly_cache[key]=parse_zip(z,mp) if z is not None else None
            if monthly_cache[key] is not None:
                start=int(dt.datetime.combine(next_day,dt.time(0),dt.timezone.utc).timestamp()*1000)
                rows={t:r for t,r in monthly_cache[key].items() if start<=t<start+24*3600000}
                via="monthly_fallback"
        if not rows or len(rows)!=6:
            missing.append(next_day.isoformat())
            break  # NEVER skip a missing day to process later candles
        begin=int(dt.datetime.combine(next_day,dt.time(0),dt.timezone.utc).timestamp()*1000)
        expected=[begin+i*STEP for i in range(6)]
        if sorted(rows)!=expected:
            missing.append(f"{next_day}:non_contiguous_archive")
            break
        for t in expected:
            if t not in known:
                appended.append(rows[t])
                known[t]=rows[t]
        fetched.append(dict(date=next_day.isoformat(),source=via))
        next_day+=dt.timedelta(days=1)
    out=[known[t] for t in sorted(known)]
    gap=next((a[0] for a,b in zip(out,out[1:]) if b[0]-a[0]!=STEP),None)
    if gap is not None:
        raise RuntimeError(f"{symbol}: noncontiguous timeline after {iso(gap)}")
    return out,dict(symbol=symbol,base_last=iso(old_last),
                    first_new=iso(appended[0][0]) if appended else None,
                    latest=iso(out[-1][0]),new_bars=len(appended),
                    missing_days=missing,archive_sources=fetched)


def observed_trades(d,params):
    arrays=rr.make_arrays(features(d,"X"))  # true asset passed through feature() above? overridden below
    return arrays


def replay(rows,symbol,params):
    df=features(rows,symbol)
    d=rr.make_arrays(df)
    events=rr.candidates(d,params[0])
    latest=int(d["t"][-1])
    next_free=FORWARD_MS
    closed=[]
    open_position=None
    pending_signal=[]
    for i,side in events:
        entry_ms=int(d["t"][i+1])
        if entry_ms<FORWARD_MS or entry_ms<next_free:
            continue
        trade=rr.trade(d,i,side,len(d),params)
        if trade is None:
            pending_signal.append(dict(signal_utc=iso(d["t"][i]),side=side,
                 reason="next_open_or_complete_bar_unavailable"))
            continue
        trade["symbol"]=symbol
        if trade["reason"]=="evaluation_boundary":
            open_position=dict(symbol=symbol,side=side,
                signal_utc=iso(d["t"][i]),entry_utc=iso(trade["entry_ms"]),
                entry_price=trade["entry"],last_closed_bar=iso(latest),
                latest_close=float(d["close"][-1]),
                mark_to_market_net_pct=round(100*trade["ret"],4),
                status="OPEN_AT_DATA_BOUNDARY_NOT_A_CLOSED_TRADE")
            break
        closed.append(trade)
        next_free=int(trade["exit_ms"])+STEP
    # The last bar might contain a new entry signal whose next open is not downloaded.
    if events:
        for i,side in events[-2:]:
            if int(d["t"][i])>=FORWARD_MS-STEP and i+1==len(d):
                pending_signal.append(dict(signal_utc=iso(d["t"][i]),side=side,
                     reason="awaiting_next_4h_open"))
    return closed,open_position,pending_signal


def stats(trades):
    profit=sum(POSITION*t["ret"] for t in trades)
    losses=[t for t in trades if t["ret"]<0]
    gains=[t for t in trades if t["ret"]>0]
    return dict(closed_trades=len(trades),realized_profit_usd=round(profit,2),
       realized_pct_initial_equity=round(100*profit/STARTING_EQUITY,4),
       win_rate=(len(gains)/len(trades)) if trades else None,
       nominal_profit_factor=(sum(t["ret"] for t in gains)/-sum(t["ret"] for t in losses)) if losses else None,
       median_hold_hours=round(float(np.median([t["hold_hours"] for t in trades])),2) if trades else None)


def main():
    rr.COST_RT=FEE_RT
    now=dt.datetime.now(dt.timezone.utc)
    last_complete_day=now.date()-dt.timedelta(days=1)
    snapshots={}
    source={}
    for symbol in ASSETS:
        p=ROOT/"data"/(symbol+".json")
        if not p.is_file():
            raise FileNotFoundError(f"{p} absent; restore old 3-year GitHub artifact, do NOT redownload")
        baseline=json.loads(p.read_text())
        if baseline[-1][0]>=FORWARD_MS:
            raise ValueError(f"{symbol} base includes prospective data; immutable baseline expected")
        source[symbol]=dict(baseline_rows=len(baseline),
            baseline_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        full,diag=extend_baseline(symbol,baseline,last_complete_day)
        snapshots[symbol]=full
        source[symbol].update(diag)
    common_end=min(int(snapshots[s][-1][0]) for s in ASSETS)
    valid_to=common_end+STEP
    # Identical time cutoff for ETH and LINK; never compare different horizons.
    for s in ASSETS:
        snapshots[s]=[r for r in snapshots[s] if r[0]<=common_end]
    result=dict(experiment="frozen_delta_eth_link_paper_forward",
       research_only=True,as_of=now.isoformat(),policy_frozen=FROZEN_AT,
       true_forward_from=START_FORWARD.isoformat(),
       rule_source="original Pine executable mathematical core, strict medium->weak and EMA200",
       base_artifact_run_id=41231907011,
       costs_round_trip=FEE_RT,
       fixed_position_usd=POSITION_USD,starting_equity_usd=STARTING_EQUITY,
       fee_description="0.08% each side plus 0.02% round-trip spread proxy",
       no_48h_cap=True,source=source,run=os.environ.get("GITHUB_RUN_ID","local"),
       candidate_models={},data_through=iso(common_end),scored_through=iso(valid_to),
       status="complete_closed_days" if valid_to>FORWARD_MS else "awaiting_forward_candles",
       warnings=[
           "No historical date before Nov 1 2026 is scored as genuine forward; policy was selected Oct 31",
           "Immutable rules: no model fitting, policy selection, threshold adjustment or use of future data",
           "Contiguous 4h timeline required; if daily ZIP missing, same-exchange monthly ZIP fallback only",
           "Open positions have unrealized paper PnL; do NOT count as closed trade",
           "New candle archives only; existing 3-year candles restored from previous GitHub artifact/release",
           "All tests are paper research; no brokerage, execution, funding, slippage or prop validation",
       ])
    for label,params in FROZEN.items():
        trades=[]
        unresolved=[]
        pending=[]
        for sym in ASSETS:
            c,o,p=replay(snapshots[sym],sym,params)
            trades+=c
            if o:
                unresolved.append(o)
            pending+=p
        result["candidate_models"][label]=dict(parameters={
           "entry":params[0],"stop_atr":params[1],"take_atr":params[2],
           "trail_activation_atr":params[3][0],"trail_distance_atr":params[3][1],
           "indicator_exit":params[4]},
           realized=stats(trades),closed_trades=trades,
           open_positions=unresolved,pending_signals=pending)
    if any(v["missing_days"] for v in source.values()):
        result["status"]="incomplete_archive_gap"
    elif valid_to<=FORWARD_MS:
        result["status"]="awaiting_forward_candles"
    (ROOT/"FROZEN_FORWARD_REPORT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    digest={k:dict(candles=v["new_bars"],last=v["latest"],missing=v["missing_days"][:3])
            for k,v in source.items()}
    print("FROZEN_FORWARD",json.dumps(dict(status=result["status"],
         as_of=result["as_of"],data_through=result["data_through"],
         baseline=digest,summary={k:v["realized"] for k,v in result["candidate_models"].items()},
         open={k:len(v["open_positions"]) for k,v in result["candidate_models"].items()}),
         ensure_ascii=False),flush=True)
    lines=["# DeltaRSI ETH/LINK — замороженный форвард","",
           "Настоящий prospective старт: 2026-11-01 00:00 UTC. Ручных сделок нет, дообучения нет.",
           "Данные за 28—31 октября могут догружаться только для восстановления непрерывного контекста.",
           f"Запуск GitHub: {result['run']}; состояние: {result['status']}",
           f"Последняя закрытая 4H свеча: {result['data_through']}","",
           "| Вариант | Закрытых сделок | Реализованный результат на $5000 | Открытых |",
           "|---|---:|---:|---:|"]
    for key,ans in result["candidate_models"].items():
        lines.append(f"| {key} | {ans['realized']['closed_trades']} | "
          f"{ans['realized']['realized_pct_initial_equity']:.3f}% | {len(ans['open_positions'])} |")
    lines+=["","Это исследовательский бумажный мониторинг; результаты до старта форварда не считаются.",
       "Непрерывность свечей строго проверяется. Параметры нельзя менять по результатам этого периода.",
       "Подробная бухгалтерия закрытых сделок и оценка открытых — в FROZEN_FORWARD_REPORT.json."]
    (ROOT/"FROZEN_FORWARD_REPORT.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
