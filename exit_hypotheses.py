"""Compare exits for fixed DeltaRSI entry on cached historical data."""
import json
from pathlib import Path
from feature_walkforward import data,sim,stats
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
def main():
    report={}
    for symbol in SYMS:
        rows,features=data(symbol)
        cuts=(0,len(rows)//2,len(rows)*3//4,len(rows))
        variants=[]
        for stop in (1.5,2.5,3.5):
            for target in (2.,4.,6.,8.):
                for bars in (6,12,18,30,42,60):
                    cfg=("turn","none","none",stop,target,bars,"both")
                    periods=[stats(sim(rows,features,cfg,cuts[i],cuts[i+1])[0]) for i in range(3)]
                    variants.append(dict(stop=stop,target=target,hours=bars*4,periods=periods))
        report[symbol]=variants
    Path("reports/exit_hypotheses.json").write_text(json.dumps(report,indent=2))
    print("evaluated",sum(map(len,report.values())),"asset-variants")
if __name__=="__main__":main()
