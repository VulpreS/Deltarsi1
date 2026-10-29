"""Canonical RSI27 RMA - EMA7 4H intensity study; hourly portfolio execution.
Only symbols with existing 1H cache; shorter overlap explicitly reported.
Research-only signal proxy: weakening delta magnitude; no wick/wave confirmations.
"""
import sys,json,math,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import experiments.upscale_year_portfolio.run as engine
from causal_4h_parity_audit import load,H
from completed_candles import aggregate_completed
from research_multiasset import atr
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT","TONUSDT")
DAY=24*H
def canonical(raw,ratio):
 bars=aggregate_completed(raw,4,asof_ms=raw[-1][0]+H)
 av=atr(bars);avg_gain=avg_loss=None;ema=None;previous=None;previous2=None;out={}
 gains=[];losses=[]
 for i,b in enumerate(bars):
  if i==0:continue
  change=b[4]-bars[i-1][4]
  gains.append(max(0,change));losses.append(max(0,-change))
  if i<27:continue
  if i==27:
   avg_gain=sum(gains[:27])/27;avg_loss=sum(losses[:27])/27
  else:
   avg_gain=(avg_gain*26+gains[-1])/27
   avg_loss=(avg_loss*26+losses[-1])/27
  rsi=100 if avg_loss==0 else 100-100/(1+avg_gain/avg_loss)
  ema=rsi if ema is None else ema*.75+rsi*.25
  delta=rsi-ema
  # proxy for medium->weak: a two-step reduction in same-colored impulse
  if previous is not None and previous2 is not None and i>=210:
   if delta*previous>0 and previous*previous2>0 and abs(previous2)>=abs(previous) and abs(delta)<=abs(previous)*ratio:
    entry=b[0]+4*H
    if entry<=raw[-1][0] and math.isfinite(av[i-1]) and av[i-1]>0:
     out[entry]=dict(side=1 if delta<0 else -1,atr_4h=av[i-1],entry_ms=entry)
  previous2=previous;previous=delta
 return out
def run():
 raw={};sig={};sha={};meta={}
 for s in SYMS:
  rows,sha[s]=load(s);raw[s]={x[0]:x for x in rows};meta[s]=dict(start=engine.iso(rows[0][0]),end=engine.iso(rows[-1][0]+H),hours=len(rows))
  sig[s]={r:canonical(rows,r) for r in (.65,.8,.95)}
 result=dict(title="Canonical DeltaRSI RSI27 RMA minus EMA7, hourly 5-symbol portfolio",sources=meta,sha=sha,
  assumptions=["Intensity medium->weak is PROXY: two-step declining absolute delta with same sign and ratio threshold.",
   "No candle-wick confirmation, 2nd/3rd wave requirement, divergence, or higher timeframe filter.",
   "All five have cached 1H; BNB SOL XRP have only 4H and cannot enter equal-resolution hourly portfolio.",
   "20% initial account notional per position, max 3 open, one per symbol.",
   "Same conservative stop-first, day-start equity and original balance risk assumptions as preceding study.",
   "No independent OOS, no live orders."],tests={})
 for symbols in (("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT"),SYMS):
  common=set.intersection(*(set(raw[s]) for s in symbols))
  end=max(common);start=max(min(common),end-365*DAY+H)
  times=list(range(start,end+H,H))
  if any(t not in common for t in times):
   print("SKIP_NONCONTIGUOUS",symbols,flush=True);continue
  engine.SYMS=symbols
  data={s:raw[s] for s in symbols}
  for ratio in (.65,.8,.95):
   signals={s:sig[s][ratio] for s in symbols}
   for sl,tp,be,label in [(("atr",2.5),("atr",3.),False,"atr"),(("fixed",1.5),("atr",3.),False,"fixed15_atr"),(("fixed",2.),("fixed",2.),False,"fixed2"),(("atr",2.5),("atr",3.),True,"atr_be1")]:
    mode={s:(sl,tp,be) for s in symbols}
    name=f"{len(symbols)}symbols_ratio{ratio:g}_{label}"
    x=engine.simulate(data,signals,times,mode,reset_phases=False)
    result["tests"][name]={k:v for k,v in x.items() if k not in ("trades","daily")}
    print(name,json.dumps(result["tests"][name]),flush=True)
 p=Path("experiments/canonical_delta_portfolio/results.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(result,indent=2))
if __name__=="__main__":run()
