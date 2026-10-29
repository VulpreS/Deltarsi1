"""Research sweep on new Bybit USDT linear assets. Downloads 1h candles in CI, no live orders."""
import sys,json,time,datetime as dt,urllib.request,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.pine_vs_codex.run import pine_events
from experiments.max_strategy_grid.prop_portfolio import run,H,DAY,iso
ASSETS=("PEPEUSDT","ALTUSDT","TIAUSDT","APTUSDT","SUIUSDT","POLUSDT","ARBUSDT")
API="https://api.bybit.com/v5/market/kline"
START=int(dt.datetime(2025,10,29,tzinfo=dt.timezone.utc).timestamp()*1000)
END=int(dt.datetime(2026,10,27,tzinfo=dt.timezone.utc).timestamp()*1000)
PARAMS=[(1.5,1.5,None,None),(1.5,2.5,None,None),(1.5,5.,None,None),(2.5,2.5,None,None),(2.5,5.,None,None),(5.,2.5,None,None),(5.,5.,None,None)]
def download(s):
 out=[];t=START
 while t<END:
  url=API+"?"+urllib.parse.urlencode(dict(category="linear",symbol=s,interval="60",start=t,end=min(END-1,t+999*H),limit=1000))
  for attempt in range(5):
   try:
    req=urllib.request.Request(url,headers={"User-Agent":"Deltarsi1-research/1.0"})
    with urllib.request.urlopen(req,timeout=35) as f:batch=json.load(f)
    if batch.get("retCode")!=0:raise ValueError(str(batch)[:300])
    batch=batch["result"]["list"]
    batch.sort(key=lambda b:int(b[0]))
    break
   except Exception:
    if attempt==4:raise
    time.sleep(2**attempt)
  if not batch:break
  out.extend((int(b[0]),float(b[1]),float(b[2]),float(b[3]),float(b[4])) for b in batch)
  t=int(batch[-1][0])+H
  if int(batch[-1][0])>=END-H:break
 if len(out)<500:raise ValueError("Insufficient candles for "+s)
 if any(b[0]-a[0]!=H for a,b in zip(out,out[1:])):raise ValueError("Missing/duplicate hourly candles "+s)
 return out
def main():
 raw={};signals={};meta={}
 for s in ASSETS:
  try:
   rows=download(s);raw[s]={r[0]:r for r in rows};signals[s]=pine_events(rows)
   meta[s]=dict(count=len(rows),start=iso(rows[0][0]),end=iso(rows[-1][0]),signals=len(signals[s]))
   print("DATA",s,json.dumps(meta[s]),flush=True)
  except Exception as e:
   meta[s]=dict(error=str(e));print("DATA_ERROR",s,str(e),flush=True)
 if not raw:raise RuntimeError("No assets downloaded")
 results=dict(meta=meta,parameters=PARAMS,per_asset={},portfolio={},notes=[
  "Exact tested pine_events proxy, not final RSI27 variant.",
  "Data from Bybit linear USDT futures public hourly klines, fetched at CI runtime.",
  "Individual ATR grids are in-sample explorations; not validated out of sample.",
  "Fixed 48h max hold, 20% initial balance position, max three positions, fees 0.08% each side, spread 0.02% roundtrip.",
  "Prop risk checks approximate and must be audited before trading."])
 for s in raw:
  times=sorted(raw[s])
  if len(times)<400:continue
  # First 70% for choosing per-symbol SL/TP; remaining 30% for out-of-sample check.
  split=(len(times)*7)//10
  training=times[:split];testing=times[split:]
  sweeps=[]
  for p in PARAMS:
   tr=run({s:raw[s]},{s:signals[s]},{s:p},training,reset=False,max_hours=48)
   te=run({s:raw[s]},{s:signals[s]},{s:p},testing,reset=False,max_hours=48)
   sweeps.append(dict(params=p,train=tr,test=te))
  chosen=max(sweeps,key=lambda v:v["train"]["closed_net_pnl"])
  results["per_asset"][s]=dict(sweeps=sweeps,selected=chosen)
  print("ASSET_BEST",s,json.dumps(dict(params=chosen["params"],train=chosen["train"],test=chosen["test"])),flush=True)
 # Portfolio OOS: common continuous 1h data, independent flat start and identical time window.
 common=set.intersection(*(set(x) for x in raw.values()))
 if common:
  times=sorted(common)
  if len(times)>500:
   split=(len(times)*7)//10
   for label,window in (("full",times),("oos",times[split:])):
    params={s:tuple(results["per_asset"][s]["selected"]["params"]) for s in raw}
    for mode in (False,True):
     r=run(raw,signals,params,window,reset=mode,max_hours=48)
     key=label+("_challenge" if mode else "_continuous")
     results["portfolio"][key]=r
     print("NEW_ASSET_PORTFOLIO",key,json.dumps(r),flush=True)
 else:print("WARN no common hourly data",flush=True)
 path=Path("experiments/new_assets_2026/results.json");path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(results,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
