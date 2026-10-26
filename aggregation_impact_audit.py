"""P0 #7 strict-vs-legacy cached OHLC aggregation audit. No network/orders.

Fixed previously selected configs and fixed chronological UTC boundaries.
Historical windows already inspected: NOT independent OOS.
"""
import bisect
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from feature_walkforward import data
from p0_gap_audit import CONFIGS,simulate,metrics
from pattern_confluence import flags
from matched_exit_audit import exit_one, selected_entries, metric

ASSETS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
COSTS=(.0015,.0025,.004)
SEED=20261026

def ts(ms):
    return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).isoformat()

def filtered(rows,features,name):
    if name is None:return features
    return [({**f,"turn":f["turn"] and flags(rows,features,i).get(name,False)}
             if f else None) for i,f in enumerate(features)]

def key(rows,t):
    return (ts(rows[t["signal_index"]][0]),ts(rows[t["entry_index"]][0]),t["side"])

def audit_config(old,new,config,utc_edges):
    filt,sl,tp,hold=CONFIGS[config]
    out={}
    for label,(rows,raw) in (("legacy",old),("strict",new)):
        f=filtered(rows,raw,filt)
        stamps=[r[0] for r in rows]
        cuts=[bisect.bisect_left(stamps,edge) for edge in utc_edges]
        cuts[0]=0;cuts[-1]=len(rows)
        per=[simulate(rows,f,cuts[k],cuts[k+1],sl,tp,hold,"corrected")
             for k in range(5)]
        trades=[t for p in per for t in p]
        out[label]={"trades":trades,"keys":[key(rows,t) for t in trades],
                    "by_cost":{f"{int(c*10000)}bp":metrics(trades,c,0.) for c in COSTS},
                    "five_slices":[{f"{int(c*10000)}bp":metrics(p,c,0.) for c in COSTS}
                                   for p in per]}
    a=set(map(tuple,out["legacy"]["keys"]))
    b=set(map(tuple,out["strict"]["keys"]))
    for d in out.values():
        del d["trades"]
    return {"legacy":out["legacy"],"strict":out["strict"],
            "identical_entry_keys":a==b,
            "legacy_only_count":len(a-b),"strict_only_count":len(b-a),
            "legacy_only_examples":sorted(a-b)[:10],"strict_only_examples":sorted(b-a)[:10]}

def eth_matched(rows,raw,edges):
    f=filtered(rows,raw,"ob_proxy")
    stamps=[r[0] for r in rows]
    cuts=[bisect.bisect_left(stamps,e) for e in edges]
    cuts[0]=0;cuts[-1]=len(rows)
    cohort=[]
    for k in range(5):
        lo,hi=cuts[k],cuts[k+1]
        for t in selected_entries(rows,f,lo,hi,2.5,6.0):
            fixed=exit_one(rows,raw,t,2.5,6.0,"fixed",hi)
            reverse=exit_one(rows,raw,t,2.5,6.0,"reverse",hi)
            cohort.append((fixed,reverse))
    return {"n":len(cohort),"entry_keys":[key(rows,p[0]) for p in cohort],
            "modes":{mode:{f"{int(c*10000)}bp":metric([p[ix]["gross"]-c for p in cohort])
                          for c in COSTS} for mode,ix in (("fixed",0),("raw_reverse",1))}}

def main():
    result={"title":"P0 #7 UTC completed-bar impact audit",
        "historical_warning":"ALL windows reused after prior selection, NOT independent OOS; no tuning.",
        "producer_git_sha":os.getenv("GITHUB_SHA","unknown-local"),
        "ci_run_id":os.getenv("GITHUB_RUN_ID","unknown-local"),
        "seed":SEED,"costs_round_trip":[.0015,.0025,.004],
        "funding":"actual unavailable, not applied in this aggregation-only comparison",
        "execution":"next 4H open, canonical stop-first gap-safe, 12 bars maximum; five UTC chronological non-overlapping slices",
        "source_venue":"UNKNOWN for all assets; no new candles downloaded",
        "configs":"Frozen baseline 2.5/3/12 all; selected BTC OB 2.5/4/12, ETH OB 2.5/6/12, ICP EMA200 2.5/4/12, HYPE unfiltered 2.5/6/12; no search",
        "assets":{}}
    for sym in ASSETS:
        old=data(sym,"legacy")
        new=data(sym,"strict")
        newrows=new[0]
        edges=[newrows[0][0]]+[newrows[len(newrows)*i//5][0] for i in range(1,5)]+[newrows[-1][0]+4*3600000]
        configs={}
        for name in ("baseline","selected_"+sym.replace("USDT","")):
            configs[name]=audit_config(old,new,name,edges)
        result["assets"][sym]={"sha256":hashlib.sha256((Path("data")/(sym+"_1h.csv")).read_bytes()).hexdigest(),
             "legacy_bars":len(old[0]),"strict_bars":len(newrows),
             "legacy_first_utc":ts(old[0][0][0]),"legacy_last_utc":ts(old[0][-1][0]),
             "strict_first_utc":ts(newrows[0][0]),"strict_last_utc":ts(newrows[-1][0]),
             "five_utc_edges":[ts(x) for x in edges],"configs":configs}
        if sym=="ETHUSDT":
            l=eth_matched(*old,edges);s=eth_matched(*new,edges)
            lk=set(map(tuple,l["entry_keys"]));sk=set(map(tuple,s["entry_keys"]))
            result["assets"][sym]["selected_eth_matched"]={"legacy":l,"strict":s,
                "identical_entry_keys":lk==sk,
                "legacy_only_count":len(lk-sk),"strict_only_count":len(sk-lk)}
    p=Path("reports/aggregation_impact.json")
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps({s:{"bars":[v["legacy_bars"],v["strict_bars"]],
         "baseline_N":[v["configs"]["baseline"][x]["by_cost"]["15bp"]["n"] for x in ("legacy","strict")],
         "baseline_key_diffs":[v["configs"]["baseline"]["legacy_only_count"],v["configs"]["baseline"]["strict_only_count")]}
         for s,v in result["assets"].items()}))
if __name__=="__main__":
    main()
