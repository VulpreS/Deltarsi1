"""Configurable-duration challenge comparison with fixed margin 10/15%, leverage <=3."""
from dataclasses import asdict
from pathlib import Path
import argparse,json,os
import pandas as pd
from upscale.backtest import Config,features,load_data,simulate
from upscale.fortnight import full_window_starts,aggregate


def run(out, days=30):
    if days <= 0: raise ValueError('days must be positive')
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    windows=[]; summaries=[]; configs={}; manifest=[]; ledgers=[]; paired=[]; baseline_windows=[]
    for tf in ('4h','1h'):
        frames,source=load_data(tf); manifest+=source
        starts=full_window_starts(next(iter(frames.values())).index,days=days)
        for n in (20,40):
            for long_only in (False,True):
                prepared={s:features(d,Config(lookback=n,long_only=long_only)) for s,d in frames.items()}
                for margin in (.10,.15):
                    for leverage in (1.,2.,3.):
                        cfg=Config(family='trend',lookback=n,long_only=long_only,sizing_mode='margin',margin_fraction=margin,position_leverage=leverage,leverage_cap=3.,max_stop_pct=.05,portfolio_risk=.04,daily_stop=.025)
                        key=f'{tf}_trend{n}_{"long" if long_only else "both"}_margin{margin*100:g}_lev{leverage:g}'
                        configs[key]=asdict(cfg); rows=[]; baseline_rows=[]; sample_saved=False
                        for start in starts:
                            r=simulate(frames,cfg,start=start,challenge=True,days=days,prepared_features=prepared)
                            row=dict(candidate=key,timeframe=tf,**r['summary']); windows.append(row); rows.append(row)
                            if days>14:
                                b=simulate(frames,cfg,start=start,challenge=True,days=14,prepared_features=prepared)
                                baseline_row=dict(candidate=key,timeframe=tf,**b['summary'])
                                baseline_rows.append(baseline_row); baseline_windows.append(baseline_row)
                            for trade in r['trades']:
                                ledgers.append(dict(candidate=key,window_start=str(start),**trade))
                            if row['outcome']=='passed' and not sample_saved:
                                pd.DataFrame(r['daily']).to_csv(out/f'{key}_first_pass_daily.csv',index=False); sample_saved=True
                        a=dict(candidate=key,timeframe=tf,margin_pct=margin*100,leverage=leverage,**aggregate(rows),rejected_stop_cap=sum(r['rejected_stop_cap'] for r in rows),rejected_budget=sum(r['rejected_budget'] for r in rows))
                        summaries.append(a); print(json.dumps(a),flush=True)
                        if baseline_rows:
                            b=aggregate(baseline_rows)
                            paired.append(dict(candidate=key,timeframe=tf,matched_starts=len(rows),passed_14d=b['passed'],passed_current=a['passed'],days=days,phase1_14d=b['phase1_completed'],phase1_current=a['phase1_completed'],failed_14d=b['failed'],failed_current=a['failed']))
    report=dict(schema=4,days=days,git_sha=os.getenv('GITHUB_SHA','local'),goal=f'Both stages within {days} calendar days total; 10/15% current-equity margin and leverage 1/2/3',paired_comparison=paired,configs=configs,manifest=manifest,summaries=summaries,windows=windows,selection='No winner selected on previously inspected retrospective data',limitations=[
        'Same entry, exit, sizing and research safeguards as the 14-day margin experiment; only the allowed completion horizon changes.',
        'Margin = 10% or 15% of current pre-entry equity. Notional = margin times selected leverage (1, 2 or 3). No inverse-stop risk resizing.',
        'ATR stop wider than 5% of entry is rejected, never clipped. Fees/slippage/funding add to price-stop losses.',
        'Extra research safeguards: aggregate reserved stop risk <=4% initial NAV; new entry skipped if planned all-stop NAV is below 96% of UTC day-start equity or 92% initial NAV. Skipped entries are counted; requested position is never silently downsized.',
        'Internal daily guard 2.5%, no new entry below initial NAV -6%; margin fraction is not halved at -4%. These are research safeguards, not user-supplied trading rules.',
        f'Weekly {days}-day windows overlap; trades repeat across windows/profiles. Counts are not independent observations or future probabilities.',
        'Previously inspected exchange OHLC, not prospective Upscale oracle/execution data. Timeframe histories have different coverage.',
        'Conservative simultaneous adverse extrema and liquidation at extrema may overstate intrabar losses or modeled breaches relative to real-time guards.',
        'Entry-bar profitable exits zeroed due unknown 60-second timing. Stops before targets; adverse gap fills and costs retained.',
        'Both stages use 5%/8% targets, 3/5 profit days >=0.5%, strict best-day <30%, daily 5% and static total 10%; stage 2 independently resets NAV=1; eligibility checked at UTC day end.',
        f'10% total loss model excludes new $200k Basic 8% phase-2/funded exception. Timeout means missing the {days}-day research goal, not a rule breach.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame(summaries).to_csv(out/'comparison.csv',index=False)
    if paired:
        pd.DataFrame(paired).to_csv(out/'paired_14d_comparison.csv',index=False)
        pd.DataFrame([{k:v for k,v in r.items() if k!='completed_phases'} for r in baseline_windows]).to_csv(out/'matched_14d_starts.csv',index=False)
    pd.DataFrame([{k:v for k,v in r.items() if k!='completed_phases'} for r in windows]).to_csv(out/'challenge_starts.csv',index=False)
    pd.DataFrame(ledgers).to_csv(out/'all_trades.csv.gz',index=False,compression='gzip')
    lines=[f'# Upscale: {days} days, fixed margin 10/15%, leverage up to 3','',
        'Same trend entry/exit and margin rules; only completion horizon changed. All 48 predefined profiles reported; no validated winner selected.','',
        '| Candidate | Starts | Phase 1 done | Both passed | Passed % | Modeled breaches | Timeout |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summaries: lines.append(f'| {r["candidate"]} | {r["starts"]} | {r["phase1_completed"]} | {r["passed"]} | {r["passed_pct"]:.1f} | {r["failed"]} | {r["timed_out"]} |')
    if paired:
        lines+=['','## 14-day comparison on identical start dates','',
            'The 14-day baseline is rerun on exactly the same start dates eligible for the longer horizon; all other settings are unchanged. Weekly windows overlap and are not independent observations.','',
            f'| Timeframe | Profile/windows | Passed in 14d | Passed in {days}d | Phase 1 in 14d | Phase 1 in {days}d | Modeled breaches 14d | Modeled breaches {days}d |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
        for tf in ('4h','1h'):
            ps=[p for p in paired if p['timeframe']==tf]
            vals=[sum(p[k] for p in ps) for k in ('matched_starts','passed_14d','passed_current','phase1_14d','phase1_current','failed_14d','failed_current')]
            lines.append('| '+tf+' | '+' | '.join(map(str,vals))+' |')
        lines+=['','All per-profile paired outcomes are in paired_14d_comparison.csv and the matched baseline windows in matched_14d_starts.csv.']
    lines+=['','## Position accounting','',
        'Example on NAV=10,000: margin=1,000–1,500, leverage=3, notional=3,000–4,500. A 5% price stop loses 150–225 before costs (1.5–2.25% account). Actual ATR stops can be tighter.',
        'All window trade ledgers, including non-passing ones, are in all_trades.csv.gz. Each trade records pre-entry equity, margin, notional, price-stop percent and planned loss percent.','',
        '## Limits of evidence','']+['- '+x for x in report['limitations']]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/upscale_margin_30d');p.add_argument('--days',type=int,default=30);a=p.parse_args();run(a.out,days=a.days)
