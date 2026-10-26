"""P0 #14 cached-only, reproducible resting-vs-market-first reverse-gap census.
Frozen baseline/challenger, no optimization, no orders or network.
"""
import datetime as dt,hashlib,json,os
from pathlib import Path
from portfolio_risk_audit import (prepare,simulate,metrics,COSTS,FUNDING,CONFIG_HASH,iso,
                                   HOUR_MS)
def key(t):return (t["symbol"],t["side"],t["signal_utc"],t["entry_utc"])
def reconcile(a,b):
    aa={key(t):t for t in a["trades"]};bb={key(t):t for t in b["trades"]}
    if len(aa)!=len(a["trades"]) or len(bb)!=len(b["trades"]):
        raise AssertionError("Duplicate trade ID")
    shared=set(aa)&set(bb)
    changed=[]
    for k in sorted(shared):
        x,y=aa[k],bb[k]
        if abs(x["net_pnl"]-y["net_pnl"])>1e-11 or x["exit"]!=y["exit"] or x["exit_utc_latest"]!=y["exit_utc_latest"]:
            changed.append({"id":k,"resting":{"exit":x["exit"],"reason":x["exit_reason"],"net_pnl":x["net_pnl"],"fees":x["fees"],"funding":x["funding_max"]},
              "market":{"exit":y["exit"],"reason":y["exit_reason"],"net_pnl":y["net_pnl"],"fees":y["fees"],"funding":y["funding_max"]}})
    return {"shared":len(shared),"changed_shared":len(changed),
            "resting_only":len(set(aa)-set(bb)),"market_only":len(set(bb)-set(aa)),
            "changed_examples":changed[:30]}
def main():
    series,times,hashes=prepare()
    report={"title":"P0 #14 pending-reverse vs resting-gap precedence, frozen portfolio",
            "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "code_sha":os.environ.get("GITHUB_SHA","local"),
            "ci_run":os.environ.get("GITHUB_RUN_ID","local"),
            "source_hashes":hashes,"config_hash":CONFIG_HASH,
            "assumptions":"resting_first canonical: old stop gap fills adverse open, target gap fills target, then pending reverse market at open; market_first alternative sensitivity. Only open OHLC used before admission. 15/25/40bp total friction, 0/1/3bp adverse synthetic UTC 8h funding. Venue priority unverified; no actual funding, no orders.",
            "warning":"Previously inspected cache; chronological windows are not untouched OOS. No strategy promotion.",
            "full":{},"windows":[]}
    for variant in ("baseline","challenger"):
        cells={}
        for cost in COSTS:
            for funding in FUNDING:
                a=simulate(series,times,variant,cost,funding,open_precedence="resting_first")
                b=simulate(series,times,variant,cost,funding,open_precedence="market_first")
                k=f"{round(cost*10000)}bp_fee_{round(funding*10000)}bp_funding"
                cells[k]={"resting_first":metrics(a),"market_first":metrics(b),
                          "trade_reconciliation":reconcile(a,b),
                          "competing_gap_count":len(a["pending_gap_competitions"])}
                if cost==.0015 and funding==.0003:
                    cells[k]["competing_gap_ledger"]=a["pending_gap_competitions"]
        report["full"][variant]=cells
    cuts=[0]+[len(times)*i//5 for i in range(1,5)]+[len(times)]
    for i in range(5):
        chunk=times[cuts[i]:cuts[i+1]]
        w={"window":i+1,"start_utc":iso(chunk[0]),"end_close_utc":iso(chunk[-1]+4*HOUR_MS),"variants":{}}
        for variant in ("baseline","challenger"):
            a=simulate(series,chunk,variant,.0015,.0003,open_precedence="resting_first")
            b=simulate(series,chunk,variant,.0015,.0003,open_precedence="market_first")
            w["variants"][variant]={"resting_first":metrics(a),"market_first":metrics(b),
                                    "competing_gap_count":len(a["pending_gap_competitions"]),
                                    "trade_reconciliation":reconcile(a,b)}
        report["windows"].append(w)
    path=Path("reports/reverse_gap_priority_audit.json")
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({"full":{v:{k:{"count":x["competing_gap_count"],"resting":x["resting_first"]["net_return_pct"],
                   "market":x["market_first"]["net_return_pct"],"diff":x["trade_reconciliation"]["changed_shared"]} for k,x in cells.items()} for v,cells in report["full"].items()},
                   "windows":[{"window":w["window"],"challenger":w["variants"]["challenger"]["competing_gap_count"]} for w in report["windows"]]}))
if __name__=="__main__":main()
