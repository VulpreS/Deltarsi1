"""Exact saved Pine Delta shade transitions vs Codex closed-4H fade, cached 1H only.\n\natr_basis=prior reproduces prior historical results (one-bar-lagged ATR).\natr_basis=signal_close uses ATR from the fully closed 4h SIGNAL candle,\navailable before entering next 4h bar; recommended for future controlled research.\nNever silently mix baselines with different ATR reference.\n"""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,events,H,CausalDelta
from completed_candles import aggregate_completed
from research_multiasset import atr
import experiments.upscale_year_portfolio.run as engine
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT")
DAY=24*H
MODE=(("atr",2.5),("atr",3.),False)
def pine_shade(d,prev):
 if not math.isfinite(d) or not math.isfinite(prev):return None
 a=abs(d)
 if d>0:
  if a>60 and d>prev:return "bright_blue"
  if a>60 and d<prev:return "medium_blue"
  if a<=60 and a>abs(prev):return "midweak_blue"
  if a<=60 and a<abs(prev):return "weak_blue"
 if d<0:
  if a>60 and d<prev:return "bright_red"
  if a>60 and d>prev:return "medium_red"
  if a<=60 and a>abs(prev):return "midweak_red"
  if a<=60 and a<abs(prev):return "weak_red"
 return None
def pine_events(raw,expanded=False,atr_basis='prior'):
 if atr_basis not in ('prior','signal_close'):raise ValueError('atr_basis must be prior or signal_close')
 bars=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
 av=atr(bars);state=CausalDelta();previous_shade=None;out={}
 for i,b in enumerate(bars):
  prior=state.delta
  d,_,_=state.step(b[4],commit=True)
  shade=pine_shade(d,prior)
  atr_index=i if atr_basis=='signal_close' else i-1
  if i>=210 and shade and previous_shade and math.isfinite(av[atr_index]) and av[atr_index]>0:
   source=("medium_red","midweak_red") if expanded else ("medium_red",)
   source_b=("medium_blue","midweak_blue") if expanded else ("medium_blue",)
   side=1 if previous_shade in source and shade=="weak_red" else (-1 if previous_shade in source_b and shade=="weak_blue" else 0)
   entry=b[0]+4*H
   if side and entry<=raw[-1][0]:out[entry]=dict(side=side,atr_4h=av[atr_index],entry_ms=entry)
  previous_shade=shade
 return out
def main():
 raw={};sigs={};sha={}
 for s in SYMS:
  rows,sha[s]=load(s);raw[s]={x[0]:x for x in rows}
  ev,_=events(rows)
  sigs[s]={"codex":{e["entry_ms"]:e for e in ev["closed"]},
           "pine_exact":pine_events(rows),
           "pine_including_midweak":pine_events(rows,True)}
 out=dict(title="Exact Pine shade transition versus Codex signal, common symmetric RSI12 SMA21 EMA7",
  source_sha=sha,sl="2.5 ATR",tp="3 ATR",be=False,initial_usd=5000,
  fee_per_side=.0008,spread_roundtrip=.0002,
  caveats=["Pine uses default symmetric mode, threshold 60, color 45 to color 80; second diagnostic includes 55/60 to 80.",
  "Original Pine indicator only paints colors; trading direction assigned from red fade=long and blue fade=short.",
  "Codex closed-4H peak>=15 and ratio<=0.7; same indicator mathematical core.",
  "1H cached history only; BNB and ZEC missing 1H cache; GRAM absent. TON included as separate research asset.",
  "Portfolio 20% initial notional, max 3, hourly stop-first, 48h hold; no OOS or live orders.",
  "Prop phase bookkeeping prototype is not contract-verified; focus on PnL and breach."],results=[])
 groups=[(s,) for s in SYMS]+[SYMS[:3],SYMS]
 for group in groups:
  common=set.intersection(*(set(raw[s]) for s in group))
  end=max(common);start=max(min(common),end-365*DAY+H)
  times=list(range(start,end+H,H))
  if any(t not in common for t in times):raise ValueError("Missing common hourly bars "+str(group))
  engine.SYMS=group
  for name in ("codex","pine_exact","pine_including_midweak"):
   sig={s:sigs[s][name] for s in group}
   r=engine.simulate({s:raw[s] for s in group},sig,times,{s:MODE for s in group},reset_phases=False)
   record=dict(group="+".join(s.replace("USDT","") for s in group),signal=name,days=r["days"],
    signals=sum(sum(t in sig[s] for t in times) for s in group),
    return_pct=r["return_since_last_phase_reset_pct"],equity=r["balance_or_equity_usd"],
    trades=r["closed_trades"],win_pct=r["win_rate_pct"],pf=r["profit_factor"],
    max_dd_pct=r["max_intrahour_dd_pct"],breach=r["breach"],worst_day_usd=r["worst_day_equity_drop_usd"],
    by_symbol=r["by_symbol"])
   out["results"].append(record);print("COMPARE",json.dumps(record,ensure_ascii=False),flush=True)
 p=Path("experiments/pine_vs_codex/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
