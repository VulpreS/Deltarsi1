"""4H-only entry confluence validation. No live orders. Strictly causal features."""
import json
from pathlib import Path
from feature_walkforward import data,sim,stats
from pattern_confluence import flags

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
ENTRY=("baseline","ema200","ema20_50","ob_proxy","sweep5","engulf","ob_ema")
EXITS=((2.5,4.,12),(2.5,6.,12),(1.5,6.,12))
def run():
    out={"description":"4H native strategy, data from strict completed 4H aggregation. Each signal is confirmed on completed bar; next 4H open entry. All configurations and periods exploratory because prior cycles inspected entire history. No untouched OOS. No funding. 0.15% roundtrip friction.","assets":{}}
    for sym in SYMS:
        rows,feats=data(sym,aggregation="strict")
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        candidates=[]
        for filt in ENTRY:
            ff=[({**f,"turn":f["turn"] and flags(rows,feats,i).get(filt,False)} if f else None) for i,f in enumerate(feats)]
            for sl,tp,hold in EXITS:
                cfg=("turn","none","none",sl,tp,hold,"both")
                seg=[stats(sim(rows,ff,cfg,cuts[i],cuts[i+1])[0]) for i in range(3)]
                candidates.append({"entry":filt,"stop_atr":sl,"target_atr":tp,"max_hours":hold*4,"segments":seg})
        out["assets"][sym]=candidates
    Path("reports/4h_entry_validation.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({k:len(v) for k,v in out["assets"].items()}))
if __name__=="__main__":run()
