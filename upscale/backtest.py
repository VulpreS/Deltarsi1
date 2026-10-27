"""Offline, causal OHLC research. No exchange client or live-order capability."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Config:
    family: str = 'trend'
    lookback: int = 20
    risk: float = .0025
    fee: float = .00008
    slippage: float = .0002  # adverse each fill, research assumption
    funding: float = .00015
    daily_stop: float = .015
    portfolio_risk: float = .0075
    leverage_cap: float = 5.
    long_only: bool = False


def load_data(tf='4h'):
    frames, manifest = {}, []
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        path = ROOT / 'data' / (f'{symbol}_4h_binance_um.csv' if tf == '4h' else f'{symbol}_1h.csv')
        d = pd.read_csv(path)
        t = pd.to_datetime(d.open_ms, unit='ms', utc=True) if 'open_ms' in d else pd.to_datetime(d.timestamp_utc, utc=True)
        d.index = pd.DatetimeIndex(t)
        d = d[['open','high','low','close']].astype(float)
        if not d.index.is_monotonic_increasing or d.index.has_duplicates:
            raise ValueError(f'{path}: unordered or duplicate timestamps')
        step = pd.Timedelta(tf)
        if (d.index.to_series().diff().dropna() != step).any():
            raise ValueError(f'{path}: missing or irregular candles; refusing silent fill')
        if not np.isfinite(d.to_numpy()).all() or (d <= 0).any().any():
            raise ValueError(f'{path}: invalid prices')
        if ((d.high < d[['open','close','low']].max(axis=1)) | (d.low > d[['open','close','high']].min(axis=1))).any():
            raise ValueError(f'{path}: invalid OHLC')
        if any((x.value // step.value) * step.value != x.value for x in d.index):
            raise ValueError(f'{path}: candles not aligned to UTC')
        # Source's final row may be a still-open candle: always discard it.
        d = d.iloc[:-1]
        frames[symbol] = d
        manifest.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), rows=len(d), first=str(d.index[0]), last=str(d.index[-1])))
    common = frames['BTCUSDT'].index.intersection(frames['ETHUSDT'].index)
    return {s:d.loc[common] for s,d in frames.items()}, manifest


def features(d, cfg):
    """Every decision field at row t uses only candles strictly before t."""
    c=d.close; n=cfg.lookback
    tr=pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    mid=c.rolling(n).mean(); sd=c.rolling(n).std(ddof=0)
    hi=d.high.rolling(n).max().shift(1); lo=d.low.rolling(n).min().shift(1)
    efficiency=(c-c.shift(n)).abs()/c.diff().abs().rolling(n).sum().replace(0,np.nan)
    trend=np.where(c>hi,1,np.where(c<lo,-1,0))
    # Re-entry after excursion, requiring low directional efficiency.
    fade=np.where((c.shift()< (mid-2*sd).shift()) & (c>=mid-2*sd),1,
         np.where((c.shift()>(mid+2*sd).shift()) & (c<=mid+2*sd),-1,0))
    fade=np.where(efficiency<.3,fade,0)
    if cfg.family=='trend': signal=trend; kind=np.full(len(d),'trend')
    elif cfg.family=='range': signal=fade; kind=np.full(len(d),'range')
    elif cfg.family=='mixed':
        signal=np.where(efficiency>=.3,trend,fade); kind=np.where(efficiency>=.3,'trend','range')
    else: raise ValueError(cfg.family)
    if cfg.long_only: signal=np.maximum(signal,0)
    f=pd.DataFrame(dict(signal=signal,kind=kind,atr=atr,mid=mid,exit_low=d.low.rolling(10).min().shift(1),exit_high=d.high.rolling(10).max().shift(1)),index=d.index).shift(1)
    f.loc[d.index[:max(60,n+15)],'signal']=0
    return f


def adjusted_gross(gross, age_seconds):
    return 0. if gross>0 and age_seconds<60 else gross


def consistency(best_day, total):
    return total>0 and best_day/total < .30-1e-12


def simulate(frames, cfg, start=None, end=None, challenge=False, days=14, prepared_features=None):
    """One shared BTC/ETH account. NAV units: initial capital = 1.

    Conservative OHLC: stop precedes TP, adverse gap fills; simultaneous adverse
    extremes bound portfolio equity. Entry-bar profitable exits are zeroed since
    OHLC cannot establish the 60-second window. No intrabar order is suppressed.
    """
    feat=prepared_features if prepared_features is not None else {s:features(d,cfg) for s,d in frames.items()}
    idx=next(iter(frames.values())).index
    if start is not None: idx=idx[idx>=pd.Timestamp(start)]
    if end is not None: idx=idx[idx<pd.Timestamp(end)]
    if challenge and len(idx): idx=idx[idx<idx[0]+pd.Timedelta(days=days)]
    # NumPy arrays keep repeated challenge starts inexpensive.
    rows={s:d.loc[idx].to_numpy() for s,d in frames.items()}
    fs={s:f.loc[idx].to_numpy() for s,f in feat.items()}
    cash=1.; pos={}; trades=[]; curve=[]; daily=[]; day=None; day_base=1.; halted=False
    peak=1.; maxdd=0.; min_equity=1.; worst_day=0.; breach=None
    phase=1; phase_initial=1.; phase_base=1.; phase_daily=[]; phase1_date=None; outcome='timeout' if challenge else 'complete'
    previous_close=1.; stop_all=False; completed_phases=[]
    step=next(iter(frames.values())).index[1]-next(iter(frames.values())).index[0]
    def equity(prices):
        return cash+sum(p['qty']*p['side']*(prices[s]-p['entry']) for s,p in pos.items())
    def close(s, price, t, reason, ambiguous=False):
        nonlocal cash
        p=pos.pop(s); fill=price*(1-p['side']*cfg.slippage)
        raw=p['qty']*p['side']*(fill-p['entry'])
        gross=adjusted_gross(raw,0 if ambiguous else (t-p['time']).total_seconds())
        fee=p['qty']*fill*cfg.fee
        cash+=gross-fee
        trades.append(dict(symbol=s,side=p['side'],kind=p['kind'],entry_time=str(p['time']),exit_time=str(t),entry=p['entry'],exit=fill,raw_gross=raw,gross=gross,net=gross-fee-p['entry_fee']-p['funding'],funding=p['funding'],reason=reason,api_60s_ambiguous=bool(ambiguous and raw>0)))
    def finish_day(eq):
        gain=eq-day_base
        daily.append(dict(day=str(day),equity=eq,pnl=gain,return_on_day_start=gain/day_base,phase=phase))
        phase_daily.append(gain)
    for i,t in enumerate(idx):
        bars={s:r[i] for s,r in rows.items()}
        opens={s:r[0] for s,r in bars.items()}
        closes={s:r[3] for s,r in bars.items()}
        opening_eq=equity(opens)
        if day!=t.date():
            if day is not None: finish_day(previous_close)
            day=t.date(); day_base=opening_eq; halted=False
        # UTC settlement charged before exits and new entries. Gap exposure is real.
        for s,p in pos.items():
            if t.hour in (0,8,16):
                funding=p['qty']*opens[s]*cfg.funding; cash-=funding; p['funding']+=funding
        opening_eq=equity(opens)
        if opening_eq<=day_base*.95: breach='daily'; stop_all=True
        if opening_eq<=phase_initial*.90: breach='total'; stop_all=True
        if opening_eq<=day_base*(1-cfg.daily_stop): halted=True
        # Prior closed-candle exits execute at this open, after adverse stop gaps.
        for s,p in list(pos.items()):
            row=fs[s][i]; op=opens[s]
            if (p['side']==1 and op<=p['stop']) or (p['side']==-1 and op>=p['stop']):
                close(s,op,t,'gap_stop'); continue
            if stop_all or halted:
                close(s,op,t,'account_guard'); continue
            sig,kind,atr,mid,exitlo,exithi=row
            exit_signal=(p['kind']=='trend' and ((p['side']==1 and frames[s].close.loc[:t].iloc[-2]<exitlo) or (p['side']==-1 and frames[s].close.loc[:t].iloc[-2]>exithi)))
            if exit_signal or (t-p['time']).total_seconds()>=p['max_hours']*3600:
                close(s,op,t,'channel_or_time')
        if not stop_all and not halted:
            for s in sorted(frames):
                if s in pos: continue
                sig,kind,atr,mid,_,_=fs[s][i]
                if not np.isfinite(float(sig)) or not sig or not np.isfinite(float(atr)): continue
                side=int(sig); entry=opens[s]*(1+side*cfg.slippage)
                distance=float(atr)*(2. if kind=='trend' else 1.5)
                if distance<=0: continue
                eq=equity(opens)
                drawdown=max(0,1-eq/phase_initial)
                if drawdown>=.06: halted=True; break
                risk=cfg.risk*(.5 if drawdown>=.04 else 1.)*phase_initial
                # Reserve total stop loss plus entry/exit fees and slippage.
                budget_per_unit=distance+entry*(2*cfg.fee+cfg.slippage)
                used=sum(p['reserved'] for p in pos.values())
                available=max(0,cfg.portfolio_risk*phase_initial-used)
                notional=sum(p['qty']*opens[k] for k,p in pos.items())
                qty=min(risk/budget_per_unit,available/budget_per_unit,max(0,cfg.leverage_cap*eq-notional)/entry)
                if qty<=0: continue
                entry_fee=qty*entry*cfg.fee; cash-=entry_fee
                target=float(mid) if kind=='range' else None
                if target is not None and side*(target-entry)<=0:
                    cash+=entry_fee; continue
                pos[s]=dict(side=side,entry=entry,qty=qty,stop=entry-side*distance,target=target,time=t,kind=kind,max_hours=120 if kind=='trend' else 24,entry_fee=entry_fee,funding=0.,reserved=qty*budget_per_unit)
        # Bound intrabar equity at jointly adverse extrema (not claimed synchronous).
        adverse={s:(bars[s][2] if p['side']==1 else bars[s][1]) for s,p in pos.items()}
        # Stop execution limits excursion unless the open gapped across the stop.
        adverse={s:(max(v,pos[s]['stop']) if pos[s]['side']==1 else min(v,pos[s]['stop'])) for s,v in adverse.items()}
        worst=equity(adverse) if pos else cash
        worst-=sum(p['qty']*adverse[s]*(cfg.fee+cfg.slippage) for s,p in pos.items())
        min_equity=min(min_equity,worst); maxdd=max(maxdd,1-worst/peak)
        worst_day=min(worst_day,worst/day_base-1)
        if worst<=day_base*.95: breach='daily'; stop_all=True
        if worst<=phase_initial*.90: breach='total'; stop_all=True
        if worst<=day_base*(1-cfg.daily_stop):
            halted=True
            # OHLC cannot locate guard crossing: liquidate all at conservative extrema.
            for s in list(pos): close(s,adverse[s],t,'intrabar_account_guard',ambiguous=pos[s]['time']==t)
        for s,p in list(pos.items()):
            op,hi,lo,cl=bars[s]
            stop_hit=lo<=p['stop'] if p['side']==1 else hi>=p['stop']
            target_hit=p['target'] is not None and (hi>=p['target'] if p['side']==1 else lo<=p['target'])
            if stop_hit: close(s,p['stop'],t,'stop',ambiguous=p['time']==t)
            elif target_hit: close(s,p['target'],t,'target',ambiguous=p['time']==t)
        eq=equity(closes); peak=max(peak,eq); maxdd=max(maxdd,1-eq/peak)
        previous_close=eq
        curve.append(dict(time=str(t+step),equity=eq,phase=phase))
        if stop_all:
            for s in list(pos): close(s,closes[s],t+step,'breach')
            outcome='failed'; break
        # Evaluate only at UTC day end, with positions flattened and costs charged.
        if challenge and (t+step).hour==0:
            target=.05 if phase==1 else .08
            current=phase_daily+[eq-day_base]
            total=eq-phase_base
            if total>=target*phase_initial and sum(x>=.005*phase_initial-1e-12 for x in current)>=(3 if phase==1 else 5) and consistency(max(current),total):
                for s in list(pos): close(s,closes[s],t+step,'phase_flatten')
                # Recheck realised balance, net of final costs.
                total=cash-phase_base; current[-1]=cash-day_base
                if total>=target*phase_initial and sum(x>=.005*phase_initial-1e-12 for x in current)>=(3 if phase==1 else 5) and consistency(max(current),total):
                    finish_day(cash); day=None
                    completed_phases.append(dict(phase=phase,completed_at=str(t+step),net_gain_pct=total*100,profit_days=sum(x>=.005*phase_initial-1e-12 for x in current),best_day_share=max(current)/total))
                    if phase==2: outcome='passed'; break
                    phase1_date=str(t+step); phase=2
                    # Conservative independent new stage starting at NAV=1.
                    cash=1.; phase_initial=1.; phase_base=1.; phase_daily=[]; previous_close=1.; peak=1.; day_base=1.
    # Mark-to-market headline plus separately stated forced-close net result.
    for s in list(pos): close(s,closes[s],t+step,'end_of_sample')
    if curve:
        curve[-1]['equity']=cash
        maxdd=max(maxdd,1-cash/peak)
        min_equity=min(min_equity,cash)
        worst_day=min(worst_day,cash/day_base-1)
        if cash<=phase_initial*.90: breach='total'; outcome='failed'
        elif cash<=day_base*.95: breach='daily'; outcome='failed'
    if len(idx) and day is not None: finish_day(cash)
    profits=[x['net'] for x in trades]; win=sum(x for x in profits if x>0); loss=-sum(x for x in profits if x<0)
    return dict(summary=dict(outcome=outcome,return_pct=(cash-1)*100,max_drawdown_pct=maxdd*100,min_equity=min_equity,worst_day_pct=worst_day*100,trades=len(trades),win_rate=sum(x>0 for x in profits)/len(profits) if profits else None,profit_factor=win/loss if loss else None,breach=breach,phase=phase,phase1_date=phase1_date,completed_phases=completed_phases,elapsed_days=float((t+step-idx[0])/pd.Timedelta(days=1)) if len(idx) else 0,profit_days_current_phase=sum(x>=.005*phase_initial-1e-12 for x in phase_daily),start=str(idx[0]) if len(idx) else None,end=str(t+step) if len(idx) else None,ambiguous_profit_exits=sum(x['api_60s_ambiguous'] for x in trades)),trades=trades,equity=curve,daily=daily)


def run(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    frames,manifest=load_data('4h')
    configs=[Config(family=f,lookback=n) for f in ('trend','range','mixed') for n in (20,40)]
    def name(c): return f'{c.family}_{c.lookback}'
    results={}; metrics=[]
    periods={'development':('2020-01-01','2024-01-01'),'validation':('2024-01-01','2025-01-01'),'historical_holdout':('2025-01-01',None)}
    for cfg in configs:
        results[name(cfg)]={}
        for label,(a,b) in periods.items():
            result=simulate(frames,cfg,start=pd.Timestamp(a,tz='UTC'),end=pd.Timestamp(b,tz='UTC') if b else None)
            results[name(cfg)][label]=result['summary']
            if label=='historical_holdout':
                pd.DataFrame(result['trades']).to_csv(out/f'{name(cfg)}_trades.csv',index=False)
                pd.DataFrame(result['equity']).to_csv(out/f'{name(cfg)}_equity.csv',index=False)
                pd.DataFrame(result['daily']).to_csv(out/f'{name(cfg)}_daily.csv',index=False)
            metrics.append(dict(candidate=name(cfg),period=label,**result['summary']))
    # Frozen selection on 2024 alone. No selection on 2025+ or stress results.
    eligible=[c for c in configs if results[name(c)]['development']['return_pct']>0 and results[name(c)]['validation']['return_pct']>0 and not results[name(c)]['validation']['breach'] and results[name(c)]['validation']['trades']>=20]
    chosen=max(eligible,key=lambda c:results[name(c)]['validation']['return_pct']/max(1,results[name(c)]['validation']['max_drawdown_pct'])) if eligible else None
    # Always run all candidates' monthly starts; do not report only a lucky winner.
    starts=pd.date_range(pd.Timestamp('2025-01-01',tz='UTC'),next(iter(frames.values())).index[-1]-pd.Timedelta(days=180),freq='MS',tz='UTC')
    challenges=[]
    for cfg in configs:
        for start in starts:
            r=simulate(frames,cfg,start=start,challenge=True,days=180)
            challenges.append(dict(candidate=name(cfg),**r['summary']))
    details={}
    if chosen:
        for label,cfg in [('base',chosen),('double_slippage',Config(**{**asdict(chosen),'slippage':chosen.slippage*2})),('long_only',Config(**{**asdict(chosen),'long_only':True}))]:
            r=simulate(frames,cfg,start=pd.Timestamp('2025-01-01',tz='UTC')); details[label]=r['summary']
            pd.DataFrame(r['trades']).to_csv(out/f'{label}_trades.csv',index=False)
            pd.DataFrame(r['equity']).to_csv(out/f'{label}_equity.csv',index=False)
            pd.DataFrame(r['daily']).to_csv(out/f'{label}_daily.csv',index=False)
        hourly,hour_manifest=load_data('1h'); manifest+=hour_manifest
        details['hourly_diagnostic']=simulate(hourly,chosen)['summary']
    report=dict(schema=1,git_sha=os.getenv('GITHUB_SHA','local'),manifest=manifest,configs=[asdict(c) for c in configs],results=results,selected=name(chosen) if chosen else None,selection='2024 return / max(1%, drawdown); positive development and validation; >=20 validation trades; no validation breach',diagnostics=details,challenges=challenges,limitations=['Previously researched historical data; chronological holdout is not genuinely unseen forward evidence.','Exchange OHLC are proxies, not Upscale oracle/execution history.','No volume inputs. Final source row discarded.','4h OHLC cannot verify subminute execution or true intrabar equity path; entry-bar profitable exits zeroed conservatively.','Stops before targets; simultaneous adverse extrema conservatively bound portfolio equity; guards cannot guarantee live limits.','Funding uses current price notional at UTC 00/08/16, existing positions charged before exits; new entries after settlement. Exact platform boundary ordering requires paper verification.','Challenge windows overlap and are not independent probabilities. 180-day horizon is a research choice, not a prop deadline.','Phase 2 starts at independent NAV=1; stage transition profitability treatment requires account-specific confirmation.','Total drawdown modeled at 10%; new $200k Basic stage 2/funded 8% requires a different configuration.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame(metrics).to_csv(out/'comparison.csv',index=False)
    pd.DataFrame(challenges).to_csv(out/'challenge_starts.csv',index=False)
    lines=['# Upscale crypto: initial research','',f'Selected using 2024 only: **{report["selected"] or "NONE — no candidate passed selection"}**.','', '| Candidate | Period | Return % | Max DD % | Trades | PF |','|---|---|---:|---:|---:|---:|']
    for m in metrics: lines.append(f'| {m["candidate"]} | {m["period"]} | {m["return_pct"]:.2f} | {m["max_drawdown_pct"]:.2f} | {m["trades"]} | {m["profit_factor"] or 0:.2f} |')
    lines+=['','## Both-stage challenge starts','', '| Candidate | Passed | Failed | Timeout | Total |','|---|---:|---:|---:|---:|']
    for cfg in configs:
        rs=[r for r in challenges if r['candidate']==name(cfg)]
        lines.append(f'| {name(cfg)} | '+ ' | '.join(str(sum(r['outcome']==k for r in rs)) for k in ('passed','failed','timeout'))+f' | {len(rs)} |')
    lines+=['','## Selected candidate diagnostics','', '```json',json.dumps(details,indent=2),'```','','## Limits of evidence','']+['- '+x for x in report['limitations']]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',default='reports/upscale'); args=p.parse_args(); run(args.out)
