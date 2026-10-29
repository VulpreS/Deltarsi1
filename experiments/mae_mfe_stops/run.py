"""MAE/MFE and SL/hold sensitivity research; historical data only."""
import json,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.new_assets_2026.run import download
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import run,H,iso
from causal_4h_parity_audit import load
ASSETS=("APTUSDT","TIAUSDT","ARBUSDT","SUIUSDT","ICPUSDT")
STOPS=(1.5,2.5,3.5,5.,7.)
HOLDS=(48,72,96)
TARGETS=(2.5,5.)
def paths(rows,events):
 bars={r[0]:r for r in rows};times=sorted(bars);index={t:i for i,t in enumerate(times)}
 paths=[]
 for t,e in sorted(events.items()):
  if t not in index:continue
  i=index[t];side=e["side"];atr=e["atr_4h"];entry=bars[t][1]
  if not math.isfinite(atr) or atr<=0:continue
  highs=[];lows=[]
  for r in rows[i:i+96]:
   highs.append(r[2]);lows.append(r[3])
  if len(highs)<96:continue
  paths.append(dict(entry=iso(t),side=side,atr=round(atr,9),mae_atr=round(max((entry-x)/atr for x in lows) if side==1 else max((x-entry)/atr for x in highs),3),mfe_atr=round(max((x-entry)/atr for x in highs) if side==1 else max((entry-x)/atr for x in lows),3),adverse_then_recovery=any((min(lows[:k+1])<entry-2.5*atr and highs[k]>entry+2.5*atr) if side==1 else (max(highs[:k+1])>entry+2.5*atr and lows[k]<entry-2.5*atr) for k in range(96))))
 return paths
def main():
 result={"notes":["Selection uses first 70% only; OOS is held out.","Research simulator checks intrabar stop before target; ambiguous same-bar outcomes conservative.","MAE/MFE uses 96h future path regardless of exit; not executable trade outcome.","ICP data from existing repository; other assets from public monthly futures archives."],"assets":{}}
 for s in ASSETS:
  try:
   rows=load(s)[0] if s=="ICPUSDT" else download(s)
   events=pine_events(rows);raw={s:{r[0]:r for r in rows}};sig={s:events};times=sorted(raw[s]);split=len(times)*7//10
   training=times[:split];test=times[split:]
   grid=[]
   for hold in HOLDS:
    for sl in STOPS:
     for tp in TARGETS:
      p=(sl,tp,None,None)
      tr=run(raw,sig,{s:p},training,max_hours=hold)
      te=run(raw,sig,{s:p},test,max_hours=hold)
      grid.append(dict(hold=hold,sl=sl,tp=tp,train={k:tr[k] for k in ("closed_net_pnl","trades","max_intrahour_dd","breach","profit_factor")},oos={k:te[k] for k in ("closed_net_pnl","trades","max_intrahour_dd","breach","profit_factor","win_rate","stops","time_exits")}))
   viable=[g for g in grid if g["train"]["breach"] is None]
   selected=max(viable or grid,key=lambda g:g["train"]["closed_net_pnl"])
   frozen=next(g for g in grid if g["hold"]==48 and g["sl"]==5. and g["tp"]==5.)
   pp=paths(rows,events)
   out=dict(candles=len(rows),signals=len(events),selected=selected,reference_48h_5atr=frozen,paths_count=len(pp),paths=pp,grid=grid)
   result["assets"][s]=out
   print("SENSITIVITY",s,json.dumps({k:out[k] for k in ("candles","signals","selected","reference_48h_5atr","paths_count")}),flush=True)
  except Exception as e:
   result["assets"][s]={"error":str(e)}
   print("SENSITIVITY_ERROR",s,str(e),flush=True)
 p=Path("experiments/mae_mfe_stops/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2))
if __name__=="__main__":main()
