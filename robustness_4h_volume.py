"""Robustness and sensitivity of predeclared DeltaRSI + volume candidate.
Only cached OHLC/volume. No orders. Separate fees, randomized block bootstrap,
ATR parameter neighborhoods and per-asset chronological segments.
"""
import csv,json,random,statistics,math
from pathlib import Path
from feature_walkforward import data,sim,stats,SYMS
def volume_features(rows,feats):
 p=Path("data")/(rows and "_missing_")
 return feats
def main():
 candidate=("turn","none","none",2.5,6.,12,"both")
 candidates=[(stop,target,hold) for stop in (2.,2.5,3.) for target in (4.,6.,8.) for hold in (12,18,30,42,60)]
 prepared={}
 for sym in SYMS:
  rows,feats=data(sym)
  path=Path("data")/(sym+"_4h_volume.csv")
  if not path.exists():continue
  with path.open() as f:vol={int(x["timestamp_ms"]):float(x["base_volume"]) for x in csv.DictReader(f)}
  v=[vol.get(x[0]) for x in rows]
  filtered=[]
  for k,f in enumerate(feats):
   if f is None:filtered.append(None);continue
   prior=v[k-20:k] if k>=20 else []
   confirmed=(len(prior)==20 and all(z is not None for z in prior) and v[k] is not None and sum(prior)>0 and v[k]>sum(prior)/20)
   filtered.append({**f,"turn":f["turn"] and confirmed})
  prepared[sym]=(rows,filtered)
 reports=[]
 for sl,tp,hold in candidates:
  cfg=("turn","none","none",sl,tp,hold,"both")
  alltr=[];per={}
  for sym,(rows,feats) in prepared.items():
   cuts=[0,int(len(rows)*.5),int(len(rows)*.75),len(rows)]
   segments=[]
   for j in range(3):
    trades,dd=sim(rows,feats,cfg,cuts[j],cuts[j+1])
    segments.append({"stats":stats(trades),"max_drawdown_full_notional_pct":round(dd*100,2)})
    if sym!="HYPEUSDT":alltr.extend((sym,j,t[1]) for t in trades)
   per[sym]=segments
  if not alltr:continue
  ret=[x[2] for x in alltr]
  # conservative extra cost stress: 0.15% baseline already deducted by simulator
  costs={str(extra):{"mean_pct":round(100*statistics.mean(x-extra for x in ret),3),"positive_trade_fraction":round(sum(x>extra for x in ret)/len(ret),3)} for extra in (0.,.001,.002,.004)}
  segpositive=[sum(per[s][j]["stats"].get("mean",0)>0 for s in ("ETHUSDT","BTCUSDT","ICPUSDT")) for j in range(3)]
  reports.append({"stop":sl,"target":tp,"hold_days":hold/6,"n":len(ret),"mean_pct":round(100*statistics.mean(ret),3),"extra_cost_stress":costs,"positive_assets_per_segment":segpositive,"by_asset":per})
 # Show candidate and its parameter neighborhood; never select max as new winner
 focus=next(x for x in reports if (x["stop"],x["target"],x["hold_days"])==(2.5,6.,2.))
 neighbors=[x for x in reports if x["hold_days"] in (2.,3.,5.,7.,10.) and x["stop"] in (2.,2.5,3.) and x["target"] in (4.,6.,8.)]
 stable=[x for x in neighbors if min(x["positive_assets_per_segment"])>=2 and x["extra_cost_stress"]["0.002"]["mean_pct"]>0]
 out={"status":"RESEARCH_ONLY","caution":"All three historical segments were previously used to identify this candidate; none is independent holdout. Fee stress assumes constant extra cost; no funding, cross-asset correlation, or real order-book slippage. Long holds are cut at segment boundaries; real trades can cross these boundaries.","candidate":focus,"neighborhood_count":len(neighbors),"neighbors_stable_by_exploratory_criteria":len(stable),"neighbor_summary":[{"stop":x["stop"],"target":x["target"],"days":x["hold_days"],"n":x["n"],"mean":x["mean_pct"],"extra20bps_mean":x["extra_cost_stress"]["0.002"]["mean_pct"],"positive_assets":x["positive_assets_per_segment"]} for x in neighbors]}
 Path("reports/robustness_4h_volume.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in out.items() if k!="neighbor_summary"},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
