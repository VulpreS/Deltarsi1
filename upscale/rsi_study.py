"""Upscale 30-day test of the owner's Delta indicator and journal color rules.

These rules are an explicitly limited mechanical reconstruction. Price-context
selection, discretionary entries and partial manual exits are not inferred.
"""
from dataclasses import asdict
from pathlib import Path
import argparse,hashlib,json,os
import pandas as pd
from upscale.backtest import Config,load_data,simulate
from upscale.fortnight import full_window_starts,aggregate
from upscale.rsi_histogram import prepare


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    frames,manifest=load_data('1h')
    idx=next(iter(frames.values())).index
    # At least 60 complete 4H bars before first eligible challenge entry.
    starts=full_window_starts(idx,days=30)
    starts=starts[starts>=idx[240].ceil('D')]
    summaries=[];windows=[];ledgers=[];configs={};full=[];signals=[]
    for stop in ('peak_bar','whole_wave'):
        for long_only in (False,True):
            prepared={}
            for symbol,d in frames.items():
                f,ind,bars=prepare(d,stop_mode=stop,long_only=long_only);prepared[symbol]=f
                if stop=='peak_bar' and not long_only:
                    pd.concat([bars,ind],axis=1).to_csv(out/f'{symbol}_4h_indicator.csv',index_label='bar_open_utc')
                events=f[f.signal!=0].copy();events['symbol']=symbol;events['stop_mode']=stop;events['long_only']=long_only
                events.index.name='entry_decision_utc';signals.append(events.reset_index())
            for margin in (.10,.15):
                for leverage in (1.,2.,3.):
                    cfg=Config(family='delta_journal',sizing_mode='margin',margin_fraction=margin,position_leverage=leverage,leverage_cap=3.,max_stop_pct=.05,portfolio_risk=.04,daily_stop=.025,long_only=long_only)
                    key=f'delta4h_{stop}_{"long" if long_only else "both"}_m{margin*100:g}_x{leverage:g}'
                    configs[key]=asdict(cfg);rows=[]
                    history=simulate(frames,cfg,start=idx[240],prepared_features=prepared)
                    full.append(dict(candidate=key,**history['summary']))
                    pd.DataFrame(history['trades']).to_csv(out/f'{key}_history_trades.csv',index=False)
                    pd.DataFrame(history['equity']).to_csv(out/f'{key}_history_equity.csv',index=False)
                    for start in starts:
                        r=simulate(frames,cfg,start=start,challenge=True,days=30,prepared_features=prepared)
                        row=dict(candidate=key,**r['summary']);rows.append(row);windows.append(row)
                        for trade in r['trades']:ledgers.append(dict(candidate=key,window_start=str(start),**trade))
                    a=dict(candidate=key,**aggregate(rows),full_history=history['summary']);summaries.append(a)
                    print(json.dumps(a),flush=True)
    limits=[
        'Indicator is the current repository Delta: SMA21 -> Wilder RSI12 -> EMA7 -> mirrored signed logarithmic delta. Display multiplier 1.5 does not change color threshold 60.',
        'Journal-derived mechanical LONG: medium/faint red -> weak red. SHORT: first weak blue after strong/medium/faint blue. No repeated entry on consecutive weak bars. Original four Pine intensity branches retained; equal magnitude is gray.',
        'Entry at next hourly open after a fully closed UTC 4H signal. 4H candles are constructed solely from four complete cached hourly candles, not spliced with a different 4H source.',
        'Exit on the opposite unfiltered journal color signal at next hourly open, or protective stop or account guard. No fixed TP, ATR exit, arbitrary 24/48h cap or forced RSI cross filter. Window end closes remaining positions.',
        'Structural stop is an assumption, not a uniquely recovered user rule: low/high of maximum-abs-delta candle in current same-sign wave, versus low/high of the entire known same-sign wave. Both are known before entry, zero extra buffer. Invalid/wider-than-5% stops reject entry.',
        'This is not the full manual strategy. Manual price-context selection, bright-to-medium-plus-buybacks exception, intrabar/forming-4H entries and discretionary partial exits are not specified sufficiently to reproduce.',
        'The 42 manual annotations are not replayed as verified fills or used for parameter fitting. They only establish textual color-entry/exit reasons. No claim of the owner\'s manual win rate.',
        'Margin 10/15% current pre-entry equity; leverage 1/2/3; same costs and research safeguards as previous Upscale experiments. Extra safeguards: daily guard 2.5%, planned all-stop NAV >=96% day-start and >=92% initial NAV, reserved stop risk <=4% initial NAV, stop new entries at initial NAV -6%.',
        'Source history is previously inspected. Weekly challenge windows overlap; counts are not independent future success probabilities. No ranking or tuning on these results.',
        'Hourly OHLC cannot reproduce exact intrahour prices, Upscale oracle execution or 60-second profit adjustment. Stop-first/adverse-extreme assumptions can overstate losses. Fees/slippage/funding retained.',
        'Stage model remains 5%/8% targets, 3/5 profit days >=0.5%, strict best-day <30%, 5% daily and 10% total loss, independent NAV reset for phase 2 and UTC day-end qualification. Platform stage carryover remains an assumption; new $200k 8% exception not modeled.']
    root=Path(__file__).resolve().parents[1]
    report=dict(schema=1,git_sha=os.getenv('GITHUB_SHA','local'),indicator_source='Delta',indicator_sha256=hashlib.sha256((root/'Delta').read_bytes()).hexdigest(),manual_journal_sha256=hashlib.sha256((root/'data/manual_btc_trades_2025_2026.csv').read_bytes()).hexdigest(),manifest=manifest,days=30,configs=configs,summaries=summaries,windows=windows,full_history=full,limitations=limits)
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame([{k:v for k,v in a.items() if k!='full_history'} for a in summaries]).to_csv(out/'comparison.csv',index=False)
    pd.DataFrame([{k:v for k,v in a.items() if k!='completed_phases'} for a in full]).to_csv(out/'full_history.csv',index=False)
    pd.DataFrame([{k:v for k,v in a.items() if k!='completed_phases'} for a in windows]).to_csv(out/'challenge_starts.csv',index=False)
    pd.DataFrame(ledgers).to_csv(out/'all_window_trades.csv.gz',index=False,compression='gzip')
    pd.concat(signals,ignore_index=True).to_csv(out/'signal_catalog.csv',index=False)
    lines=['# DeltaRSI journal rules: Upscale, both stages within 30 days','',
        'Mechanical reconstruction of the current indicator and journal color rules. No claim to reproduce all discretionary selection. BTC/ETH shared equity, 4H signals, 1H execution.','',
        '| Candidate | Starts | Phase 1 | Both passed | Modeled breaches | Timeout | History return % | History PF | History trades |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for a in summaries:
        h=a['full_history'];pf=f'{h["profit_factor"]:.2f}' if h['profit_factor'] is not None else '—'
        lines.append(f'| {a["candidate"]} | {a["starts"]} | {a["phase1_completed"]} | {a["passed"]} | {a["failed"]} | {a["timed_out"]} | {h["return_pct"]:.2f} | {pf} | {h["trades"]} |')
    lines+=['','## Exact scope and limits','']+['- '+x for x in limits]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='reports/upscale_rsi');a=p.parse_args();run(a.out)
