"""Add XRP SOL DOGE TRX LINK NEAR LTC UNI to frozen Pine portfolio; research only."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load
from experiments.pine_vs_codex.run import pine_events
from experiments.new_assets_2026.run import download,PARAMS
from experiments.max_strategy_grid.prop_portfolio import run,H,DAY,iso
OLD=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT")
NEW=("XRPUSDT","SOLUSDT","DOGEUSDT","TRXUSDT","LINKUSDT","NEARUSDT","LTCUSDT","UNIUSDT")
def main():
 raw={};sig={};meta={}
 baseline=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
 params={s:tuple(v) for s,v in baseline.items()}
 for s in OLD+NEW:
  try:
   rows,_=load(s) if s in OLD else (download(s),None)
   raw[s]={r[0]:r for r in rows};sig[s]=pine_events(rows)
   meta[s]=dict(rows=len(rows),start=iso(rows[0][0]),end=iso(rows[-1][0]),signals=len(sig[s]))
   print("ASSET",s,json.dumps(meta[s]),flush=True)
  except Exception as e:
   meta[s]=dict(error=str(e));print("ASSET_ERROR",s,str(e),flush=True)
 for s in NEW:
  if s not in raw:continue
  ts=sorted(raw[s]);cut=int(len(ts)*.7);train=ts[:cut];test=ts[cut:]
  trials=[]
  for p in PARAMS:
   a=run({s:raw[s]},{s:sig[s]},{s:p},train,max_hours=48)
   b=run({s:raw[s]},{s:sig[s]},{s:p},test,max_hours=48)
   trials.append(dict(params=p,train=a,test=b))
  chosen=max(trials,key=lambda x:x["train"]["closed_net_pnl"])
  params[s]=tuple(chosen["params"])
  meta[s]["chosen"]=chosen
  print("NEW_PARAM",s,json.dumps(dict(params=chosen["params"],train_pnl=chosen["train"]["closed_net_pnl"],test_pnl=chosen["test"]["closed_net_pnl"],test_trades=chosen["test"]["trades"])),flush=True)
 out=dict(meta=meta,comparison={},notes=["Historical tested pine_events RSI12/SMA21 transform, not final RSI27.","New symbol exits selected on first 70% and evaluated on last 30%; exploratory in-sample selection.","Each group uses identical common 1h timestamps and fixed $1000 position, max 3, 48h, 0.08% per-side fee, 0.02% roundtrip spread.","Cached old assets and downloaded Binance futures new assets; exchange differences may affect comparability."])
 for name,group in (("old_six",OLD),("old_plus_new",OLD+NEW),("old_five",tuple(s for s in OLD if s!="TONUSDT")),("five_plus_new",tuple(s for s in OLD if s!="TONUSDT")+NEW)):
  if any(s not in raw for s in group):
   print("SKIP_GROUP",name,"missing assets",flush=True);continue
  common=set.intersection(*(set(raw[s]) for s in group))
  if not common:print("SKIP_GROUP",name,"no common candles",flush=True);continue
  ts=sorted(common)
  if any(b-a!=H for a,b in zip(ts,ts[1:])):print("SKIP_GROUP",name,"gapped common candles",flush=True);continue
  for window,subset in (("common",ts),("last_30d",ts[-720:]),("last_90d",ts[-2160:])):
   if len(subset)<min(720,len(ts)):continue
   r=run({s:raw[s] for s in group},{s:sig[s] for s in group},{s:params[s] for s in group},subset,max_hours=48)
   out["comparison"][name+"_"+window]=r
   print("EXPANDED_PORTFOLIO",name,window,json.dumps(r),flush=True)
 p=Path("experiments/expanded_14_assets/results.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
