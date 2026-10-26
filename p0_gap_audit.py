"""P0 execution audit on immutable repository 1H CSV caches. No network, no orders.

Pre-registered configurations from manager directives and existing reports.
Old-vs-new uses IDENTICAL signal/entry cohorts, identical non-overlap rules.
Historical five slices are already inspected; NOT independent OOS.
"""
import csv,datetime as dt,hashlib,json,math,statistics
from pathlib import Path
from feature_walkforward import data
from pattern_confluence import flags
from execution_core import resolve_bar

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
CONFIGS={
 "baseline":(None,2.5,3.0,12),
 "selected_BTC":("ob_proxy",2.5,4.,12),
 "selected_ETH":("ob_proxy",2.5,6.,12),
 "selected_ICP":("ema200",2.5,4.,12),
 "selected_HYPE":(None,2.5,6.,12)
}
COSTS=(.0015,.0025,.004)
FUNDING_STRESS=(0.,.0001,.0003) # assumed adverse per 8h, NOT observed funding

def simulate(rows,features,lo,hi,sl,tp,hold,engine):
    trades=[];k=max(210,lo)
    while k<min(hi-1,len(rows)-1):
        f=features[k]
        if not f or not f["turn"]:
            k+=1;continue
        entry_i=k+1
        if entry_i>=hi:break
        entry=rows[entry_i][1];side=f["side"];atr=f["atr"]
        stop=entry-side*sl*atr;target=entry+side*tp*atr
        end=min(entry_i+hold-1,hi-1,len(rows)-1)
        out=rows[end][4];reason="time";gap=False
        for j in range(entry_i,end+1):
            bar=rows[j];op=bar[1]
            hit_stop=bar[3]<=stop if side==1 else bar[2]>=stop
            hit_target=bar[2]>=target if side==1 else bar[3]<=target
            if hit_stop:
                gap=(op<stop if side==1 else op>stop)
                out=stop if engine=="legacy" else resolve_bar(bar,side,stop,target)[0]
                end=j;reason="stop";break
            if hit_target:
                out=target;end=j;reason="target";break
        trades.append(dict(signal_index=k,entry_index=entry_i,exit_index=end,
                           side=side,gross=side*(out/entry-1),
                           bars=end-entry_i+1,reason=reason,adverse_gap=gap))
        k=end+1
    return trades

def metrics(trades,cost,funding_per_8h):
    r=[t["gross"]-cost-math.ceil(t["bars"]/2)*funding_per_8h for t in trades]
    if not r:return dict(n=0,win_pct=None,mean_pct=None,pf=None,max_dd_pct=None)
    profits=sum(max(0,x) for x in r);losses=-sum(min(0,x) for x in r)
    eq=1.;peak=1.;maxdd=0.
    for v in r:
        eq*=max(.001,1+v);peak=max(peak,eq);maxdd=max(maxdd,1-eq/peak)
    return dict(n=len(r),win_pct=round(100*sum(x>0 for x in r)/len(r),2),
                mean_pct=round(100*statistics.mean(r),4),
                pf=round(profits/losses,4) if losses else None,
                max_dd_pct=round(100*maxdd,3),
                net_compounded_pct=round(100*(eq-1),3))

def main():
    result={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "hypothesis":"Stop gaps filled at trigger overstate net performance; compare identical entry cohorts.",
        "caution":"All historical slices previously inspected; no independent OOS, no new candles downloaded, no real orders.",
        "execution":"Next-open entry; stop-first ambiguous 4H; adverse stop gap at worse(open,stop); 4H time exit at close; no cross-asset risk netting.",
        "funding":"Actual venue funding unavailable. Funding stress 0/0.01/0.03 percent per 8h is a synthetic adverse cost, not historical realized funding.",
        "costs":"Assumed total round-trip fee plus slippage 0.15/0.25/0.40 percent, independent of simulated funding.",
        "assets":{}}
    for sym in SYMS:
        path=Path("data")/(sym+"_1h.csv")
        source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        rows,features=data(sym)
        cuts=[0]+[len(rows)*i//5 for i in range(1,5)]+[len(rows)]
        chosen=("baseline","selected_"+sym.split("USDT")[0])
        asset={"source_csv":str(path),"sha256":source_hash,"four_hour_bars":len(rows),
               "five_slice_edges":cuts,"configs":{}}
        for config_name in chosen:
            filt,sl,tp,hold=CONFIGS[config_name]
            filtered=features if filt is None else [
                ({**f,"turn":f["turn"] and flags(rows,features,i).get(filt,False)} if f else None)
                for i,f in enumerate(features)]
            paired=[]
            for idx in range(5):
                old=simulate(rows,filtered,cuts[idx],cuts[idx+1],sl,tp,hold,"legacy")
                new=simulate(rows,filtered,cuts[idx],cuts[idx+1],sl,tp,hold,"corrected")
                assert [x["signal_index"] for x in old]==[x["signal_index"] for x in new]
                paired.append((old,new))
            cfg={"filter":filt or "none","stop_atr":sl,"target_atr":tp,"max_hold_4h_bars":hold,
                 "slices":[]}
            for old,new in paired:
                cfg["slices"].append({
                    "gap_count":sum(x["adverse_gap"] for x in new),
                    "legacy_15bp":metrics(old,.0015,0.),
                    "corrected_15bp":metrics(new,.0015,0.)})
            all_old=sum((p[0] for p in paired),[])
            all_new=sum((p[1] for p in paired),[])
            cfg["totals"]={
                "adverse_stop_gaps":sum(x["adverse_gap"] for x in all_new),
                "legacy_15bp":metrics(all_old,.0015,0.),
                "corrected_by_cost":{str(int(c*10000))+"bp":metrics(all_new,c,0.) for c in COSTS},
                "funding_stress_at_15bp":{str(round(f*10000))+"bp_per_8h":metrics(all_new,.0015,f) for f in FUNDING_STRESS}
            }
            asset["configs"][config_name]=cfg
        result["assets"][sym]=asset
    out=Path("reports/p0_gap_audit.json");out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({sym:{key:{"n":v["totals"]["corrected_by_cost"]["15bp"]["n"],
        "gaps":v["totals"]["adverse_stop_gaps"],"pf":v["totals"]["corrected_by_cost"]["15bp"]["pf"]}
        for key,v in d["configs"].items()} for sym,d in result["assets"].items()}))
if __name__=="__main__":main()
