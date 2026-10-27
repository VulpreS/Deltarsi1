"""14-day challenge comparison with fixed margin 10/15%, leverage <=3."""
from dataclasses import asdict
from pathlib import Path
import argparse,json,os
import pandas as pd
from upscale.backtest import Config,features,load_data,simulate
from upscale.fortnight import full_window_starts,aggregate


def run(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    windows=[]; summaries=[]; configs={}; manifest=[]; ledgers=[]
    for tf in ('4h','1h'):
        frames,source=load_data(tf); manifest+=source
        starts=full_window_starts(next(iter(frames.values())).index)
        for n in (20,40):
            for long_only in (False,True):
                prepared={s:features(d,Config(lookback=n,long_only=long_only)) for s,d in frames.items()}
                for margin in (.10,.15):
                    for leverage in (1.,2.,3.):
                        cfg=Config(family='trend',lookback=n,long_only=long_only,sizing_mode='margin',margin_fraction=margin,position_leverage=leverage,leverage_cap=3.,max_stop_pct=.05,portfolio_risk=.04,daily_stop=.025)
                        key=f'{tf}_trend{n}_{"long" if long_only else "both"}_margin{margin*100:g}_lev{leverage:g}'
                        configs[key]=asdict(cfg); rows=[]; sample_saved=False
                        for start in starts:
                            r=simulate(frames,cfg,start=start,challenge=True,days=14,prepared_features=prepared)
                            row=dict(candidate=key,timeframe=tf,**r['summary']); windows.append(row); rows.append(row)
                            for trade in r['trades']:
                                ledgers.append(dict(candidate=key,window_start=str(start),**trade))
                            if row['outcome']=='passed' and not sample_saved:
                                pd.DataFrame(r['daily']).to_csv(out/f'{key}_first_pass_daily.csv',index=False); sample_saved=True
                        a=dict(candidate=key,timeframe=tf,margin_pct=margin*100,leverage=leverage,**aggregate(rows),rejected_stop_cap=sum(r['rejected_stop_cap'] for r in rows),rejected_budget=sum(r['rejected_budget'] for r in rows))
                        summaries.append(a); print(json.dumps(a),flush=True)
    report=dict(schema=3,git_sha=os.getenv('GITHUB_SHA','local'),goal='Both stages within 14 calendar days total; 10/15% current-equity margin and leverage 1/2/3',configs=configs,manifest=manifest,summaries=summaries,windows=windows,selection='No winner selected on previously inspected retrospective data',limitations=[
        'Only sizing changed; entry/exit signals are the same trend20/40 baselines, not a new strategy.',
        'Margin = 10% or 15% of current pre-entry equity. Notional = margin times selected leverage (1, 2 or 3). No inverse-stop risk resizing.',
        'ATR stop wider than 5% of entry is rejected, never clipped. Fees/slippage/funding add to price-stop losses.',
        'Extra research safeguards: aggregate reserved stop risk <=4% initial NAV; new entry skipped if planned all-stop NAV is below 96% of UTC day-start equity or 92% initial NAV. Skipped entries are counted; requested position is never silently downsized.',
        'Internal daily guard 2.5%, no new entry below initial NAV -6%; margin fraction is not halved at -4%. These are research safeguards, not user-supplied trading rules.',
        'Weekly 14-day windows overlap; trades repeat across windows/profiles. Counts are not independent observations or future probabilities.',
        'Previously inspected exchange OHLC, not prospective Upscale oracle/execution data. Timeframe histories have different coverage.',
        'Conservative simultaneous adverse extrema and liquidation at extrema may overstate intrabar losses or modeled breaches relative to real-time guards.',
        'Entry-bar profitable exits zeroed due unknown 60-second timing. Stops before targets; adverse gap fills and costs retained.',
        'Both stages use 5%/8% targets, 3/5 profit days >=0.5%, strict best-day <30%, daily 5% and static total 10%; stage 2 independently resets NAV=1; eligibility checked at UTC day end.',
        '10% total loss model excludes new $200k Basic 8% phase-2/funded exception. Timeout means missing the 14-day research goal, not a rule breach.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame(summaries).to_csv(out/'comparison.csv',index=False)
    pd.DataFrame([{k:v for k,v in r.items() if k!='completed_phases'} for r in windows]).to_csv(out/'challenge_starts.csv',index=False)
    pd.DataFrame(ledgers).to_csv(out/'all_trades.csv.gz',index=False,compression='gzip')
    lines=['# Upscale: 14 days, fixed margin 10/15%, leverage up to 3','',
        'Same trend entry/exit rules. Only position sizing changed. All 48 predefined profiles reported; no validated winner selected.','',
        '| Candidate | Starts | Phase 1 done | Both passed | Passed % | Modeled breaches | Timeout |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summaries: lines.append(f'| {r["candidate"]} | {r["starts"]} | {r["phase1_completed"]} | {r["passed"]} | {r["passed_pct"]:.1f} | {r["failed"]} | {r["timed_out"]} |')
    lines+=['','## Position accounting','',
        'Example on NAV=10,000: margin=1,000–1,500, leverage=3, notional=3,000–4,500. A 5% price stop loses 150–225 before costs (1.5–2.25% account). Actual ATR stops can be tighter.',
        'All window trade ledgers, including non-passing ones, are in all_trades.csv.gz. Each trade records pre-entry equity, margin, notional, price-stop percent and planned loss percent.','',
        '## Limits of evidence','']+['- '+x for x in report['limitations']]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/upscale_margin');a=p.parse_args();run(a.out)
