"""Frozen 14-calendar-day BOTH-stage challenge experiment; offline cached data."""
from dataclasses import asdict, replace
from pathlib import Path
import argparse, json, os
import numpy as np
import pandas as pd
from upscale.backtest import Config, features, load_data, simulate


def full_window_starts(index, days=14, cadence='7D'):
    # Warm up at least 60 source candles; UTC-midnight starts; no short final windows.
    first=max(index[60].ceil('D'),pd.Timestamp('2025-01-01',tz='UTC'))
    last=index[-1]+(index[1]-index[0])-pd.Timedelta(days=days)
    return pd.date_range(first,last,freq=cadence)


def aggregate(rows):
    n=len(rows); passed=[r for r in rows if r['outcome']=='passed']
    return dict(starts=n,passed=len(passed),passed_pct=100*len(passed)/n if n else 0,
        phase1_completed=sum(r['phase1_date'] is not None for r in rows),
        failed=sum(r['outcome']=='failed' for r in rows),
        timed_out=sum(r['outcome']=='timeout' for r in rows),
        median_pass_days=float(np.median([r['elapsed_days'] for r in passed])) if passed else None,
        median_final_stage_return_pct=float(np.median([r['return_pct'] for r in rows])) if n else None,
        worst_day_pct=min((r['worst_day_pct'] for r in rows),default=None),
        worst_max_drawdown_pct=max((r['max_drawdown_pct'] for r in rows),default=None))


def run(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    manifest=[]; configs={}; windows=[]; summaries=[]
    # Fixed before run, no tuning against these window outcomes. Previous range/mixed
    # candidates already negative: focus on trend20/40, direction and risk sensitivity.
    for tf in ('4h','1h'):
        frames,source=load_data(tf); manifest+=source
        starts=full_window_starts(next(iter(frames.values())).index)
        for n in (20,40):
            for long_only in (False,True):
                base=Config(family='trend',lookback=n,long_only=long_only,daily_stop=.025)
                prepared={s:features(d,base) for s,d in frames.items()}
                for risk in (.0025,.005,.01):
                    cfg=replace(base,risk=risk,portfolio_risk=2*risk)
                    key=f'{tf}_trend{n}_{"long" if long_only else "both"}_risk{risk*100:g}'
                    configs[key]=asdict(cfg); rows=[]
                    for start in starts:
                        result=simulate(frames,cfg,start=start,challenge=True,days=14,prepared_features=prepared)
                        row=dict(candidate=key,timeframe=tf,**result['summary']); rows.append(row); windows.append(row)
                        # First passing ledger is an illustration, not evidence of consistency.
                        if row['outcome']=='passed' and sum(x['outcome']=='passed' for x in rows)==1:
                            pd.DataFrame(result['trades']).to_csv(out/f'{key}_first_pass_trades.csv',index=False)
                            pd.DataFrame(result['daily']).to_csv(out/f'{key}_first_pass_daily.csv',index=False)
                    summary=dict(candidate=key,timeframe=tf,**aggregate(rows)); summaries.append(summary)
                    print(json.dumps(summary),flush=True)
    report=dict(schema=2,git_sha=os.getenv('GITHUB_SHA','local'),goal='Both stages completed within 14 calendar days total',days=14,cadence='weekly UTC-midnight starts',configs=configs,manifest=manifest,summaries=summaries,windows=windows,selection='None: all predefined variants reported; ranking is descriptive, not independently validated.',limitations=[
        'Already inspected history: this is a retrospective diagnostic, not fresh out-of-sample evidence.',
        'Weekly 14-day windows overlap; descriptive pass percentages are not independent future probabilities.',
        '1h and 4h have different data coverage. Compare risk/direction within each timeframe, not raw pass rates across timeframes.',
        'BTC/ETH exchange OHLC proxy rather than Upscale oracle execution; 60-second positive entry-bar closes conservatively zeroed.',
        'Simultaneous adverse extremes and stop-first ordering are conservative OHLC assumptions. Guard exits at adverse extrema may overstate losses and modeled breaches relative to continuous real-time monitoring.',
        'Phase 2 starts at independent NAV=1; actual platform stage carryover details require confirmation.',
        '5%/8% targets, 3/5 profitable days >=0.5%, best day strictly below 30%, 5% daily and 10% static total loss assumed.',
        'Day-end phase checks only: this conservative scheduling may defer intraday qualification to midnight.',
        'Internal daily guard 2.5%; half risk at initial-equity loss 4%; stop new entries at 6%; portfolio stop budget twice per-trade risk; max 5x notional.',
        '14 days is the research target requested by user, not an Upscale deadline; timeout is not disqualification.',
        '10% total loss configuration excludes new $200k Basic 8% phase-2/funded exception.',
        'First-pass ledgers are illustrative, not representative; all outcomes are included in windows JSON/CSV.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame([{k:v for k,v in r.items() if k!='completed_phases'} for r in windows]).to_csv(out/'challenge_starts.csv',index=False)
    pd.DataFrame(summaries).to_csv(out/'comparison.csv',index=False)
    lines=['# Both Upscale stages within 14 calendar days','',
        'Existing candles only. Fixed trend20/40, both directions / long only, risk 0.25% / 0.5% / 1%.',
        'All predefined variants shown; no independently validated winner selected.','',
        '| Candidate | Starts | Phase 1 done | Both passed | Passed % | Failed | Timeout | Median days if passed |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        median=f'{r["median_pass_days"]:.1f}' if r['median_pass_days'] is not None else '—'
        lines.append(f'| {r["candidate"]} | {r["starts"]} | {r["phase1_completed"]} | {r["passed"]} | {r["passed_pct"]:.1f} | {r["failed"]} | {r["timed_out"]} | {median} |')
    lines+=['','## Interpretation','',
        'A pass must satisfy both profit targets, minimum profitable days and strict best-day consistency, after costs. Merely reaching +13% at some point is not enough.',
        'Timeout means not completed within the requested 14 days. See each window and completion timestamps in results.json. Final-stage NAV is not cumulative two-stage return.',
        '', '## Limits of evidence','']+['- '+x for x in report['limitations']]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',default='reports/upscale_14d'); a=p.parse_args(); run(a.out)
