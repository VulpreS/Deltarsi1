"""Long-hold DeltaRSI experiment: cached 4H OHLC and 4H volume, no orders.
Compare 2/3/5/7/10 day holds across all three chronological segments.
"""
import json,csv,statistics,math
from pathlib import Path
from feature_walkforward import data,sim,stats,SYMS
def run():
 out={}
 for sym in SYMS:
  rows,feats=data(sym)
  p=Path("data")/(sym+"_4h_volume.csv")
  vm={}
  if p.exists():
   with p.open() as f:vm={int(x["timestamp_ms"]):float(x["base_volume"]) for x in csv.DictReader(f)}
  vv=[vm.get(x[0]) for x in rows]
  featv=[]
  for k,f in enumerate(feats):
   if f is None:featv.append(None);continue
   g=dict(f)
   w=vv[k-20:k] if k>=20 else []
   g["volconfirmed"]=len(w)==20 and all(v is not None for v in w) and vv[k] is not None and sum(w)>0 and vv[k]>sum(w)/20
   featv.append(g)
  a=int(len(rows)*.5);b=int(len(rows)*.75)
  configs=[]
  for signal in ("turn","late"):
   for vol in ("none","above_ma20"):
    for stop in (1.5,2.5,4.0):
     for target in (3.,6.,10.):
      for days in (2,3,5,7,10):
       for direction in ("both","long","short"):
        cfg=(signal,"none","none",stop,target,days*6,direction)
        ff=feats if vol=="none" else [{**f,signal:f[signal] and featv[k]["volconfirmed"]} if f is not None else None for k,f in enumerate(feats)]
        pieces=[stats(sim(rows,ff,cfg,lo,hi)[0]) for lo,hi in ((0,a),(a,b),(b,len(rows)))]
        configs.append({"rule":{"signal":signal,"volume":vol,"stop_atr":stop,"target_atr":target,"hold_days":days,"direction":direction},"segments":pieces})
  out[sym]=configs
 # Evaluate shared rules across BTC, ETH, ICP; HYPE is independent secondary check.
 keys=[json.dumps(x["rule"],sort_keys=True) for x in out["BTCUSDT"]]
 ranked=[]
 for i,key in enumerate(keys):
  seg=[]
  for j in range(3):
   sample=[out[s][i]["segments"][j] for s in ("ETHUSDT","BTCUSDT","ICPUSDT")]
   n=sum(x["n"] for x in sample)
   # weighted average return; PF across aggregate approximated via weighted gains/losses from PF and win rate not possible; use weighted mean.
   mean=sum(x.get("mean",0)*x["n"] for x in sample)/n if n else None
   seg.append({"n":n,"weighted_mean_pct":round(mean,3) if mean is not None else None,"positive_assets":sum(x.get("mean",0)>0 and x["n"]>=5 for x in sample)})
  if all(x["n"]>=30 and x["weighted_mean_pct"]>0 and x["positive_assets"]>=2 for x in seg):
   ranked.append({"rule":json.loads(key),"segments":seg,"hype_segments":out["HYPEUSDT"][i]["segments"]})
 ranked.sort(key=lambda x:min(v["weighted_mean_pct"] for v in x["segments"]),reverse=True)
 summary={"method":"Cached 4H OHLC+volume; chronological 50/25/25 per asset, 0.15% round-trip cost; time exits 2,3,5,7,10 days; one position per asset; stop prioritized; no funding. This is exploratory selection on all three windows, NOT untouched OOS.","configurations_per_asset":len(keys),"survivors":len(ranked),"top_20":ranked[:20],"baseline_long_holds":[{"days":days,"assets":{s:next(x for x in out[s] if x["rule"]=={"signal":"turn","volume":"none","stop_atr":2.5,"target_atr":3.,"hold_days":days,"direction":"both"})["segments"] for s in SYMS}} for days in (2,3,5,7,10)]}
 Path("reports/long_hold_research.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":run()
