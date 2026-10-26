"""Volume-filter ablation, using cached volume from matching venues and baseline risk rules."""
import csv,json,statistics
from pathlib import Path
from feature_walkforward import data,sim,stats,SYMS
CONFIG=("turn","none","none",2.5,3.,12,"both")
def main():
 out={}
 for sym in SYMS:
  rows,feat=data(sym);p=Path("data")/(sym+"_4h_volume.csv")
  if not p.exists():out[sym]={"error":"volume unavailable"};continue
  with p.open() as f:vmap={int(x["timestamp_ms"]):float(x["base_volume"]) for x in csv.DictReader(f)}
  vols=[vmap.get(x[0],None) for x in rows]
  # All tests are performed on the final 25% segment. This is diagnostic, not a fresh blind test.
  start=int(len(rows)*.75);records={}
  for name in ("base","vol_above_ma20","vol_below_ma20","vol_above_1_5x","vol_rising","vol_declining"):
   ff=[]
   for i,f in enumerate(feat):
    if f is None:ff.append(None);continue
    vf=dict(f)
    if name!="base":
     window=vols[i-20:i] if i>=20 else []
     if len(window)!=20 or any(x is None for x in window) or vols[i] is None:
      vf["turn"]=False
     else:
      ratio=vols[i]/(sum(window)/20) if sum(window)>0 else 0
      prior=vols[i-1]
      allowed={"vol_above_ma20":ratio>=1,"vol_below_ma20":ratio<1,"vol_above_1_5x":ratio>=1.5,"vol_rising":vols[i]>prior,"vol_declining":vols[i]<prior}[name]
      vf["turn"]=vf["turn"] and allowed
    ff.append(vf)
   t,dd=sim(rows,ff,CONFIG,start,len(rows))
   records[name]={"stats":stats(t),"max_drawdown_full_notional_pct":round(100*dd,2)}
  out[sym]={"volume_bars":len(vmap),"last_quarter":records}
 Path("reports/volume_ablation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
