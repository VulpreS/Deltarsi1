"""P0 #12: reconcile frozen standalone 4H execution with portfolio engine.

No optimization, no network, no orders. Reuses committed 1H caches.
Two standalone portfolio modes: actual per-symbol risk caps and isolated
diagnostic with relaxed leverage caps (NOT a deployable strategy).
Compares exact UTC signal/entry keys, matched exit prices and reasons, plus
five chronological non-overlapping already-inspected windows.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import portfolio_risk_audit as portfolio
from p0_gap_audit import simulate as standalone

SYMS = ("BTCUSDT", "ETHUSDT", "ICPUSDT")
H4 = 4 * 3_600_000
SOURCE = "reports/standalone_parity_audit.json"

def millis(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)

def key(s, side):
    return (s, "LONG" if side == 1 else "SHORT")

def standalone_ledger(rows, feat, lo, hi):
    result = standalone(rows, feat, lo, hi, 2.5, 3.0, 12, "corrected")
    return {key(portfolio.iso(rows[t["signal_index"]][0]), t["side"]):
            {"signal_index": t["signal_index"],
             "entry_index": t["entry_index"],
             "exit_index": t["exit_index"],
             "entry_utc": portfolio.iso(rows[t["entry_index"]][0]),
             "exit_utc": portfolio.iso(rows[t["exit_index"]][0]),
             "exit_reason": t["reason"],
             "gross_return": t["gross"],
             "side": t["side"]}
            for t in result}

def portfolio_ledger(trades):
    return {(t["signal_utc"], t["side"]): t for t in trades}

def classify_portfolio_only(entry, standalone_trades):
    # Standalone skips signals while holding and the exit bar itself:
    # k becomes exit_index+1, while portfolio may enter on exit+1 open.
    k = entry["signal_index"]
    for t in standalone_trades.values():
        if t["entry_index"] <= k <= t["exit_index"]:
            return "standalone_position_or_exit_bar_cooldown"
    return "unexplained_portfolio_only"

def classify_standalone_only(trade, portfolio_trades):
    t = millis(trade["entry_utc"])
    for p in portfolio_trades.values():
        # Existing position must have entered earlier; open-time exits at t
        # are already settled and must NOT count as occupied.
        if millis(p["entry_utc"]) < t and (t < millis(p["exit_utc_earliest"]) or
            (t == millis(p["exit_utc_earliest"]) and
             millis(p["exit_utc_latest"]) > t)):
            return "portfolio_existing_position"
    return "portfolio_other_or_cap"

def reconcile(rows, st, pt):
    common=set(st)&set(pt);only_s=set(st)-set(pt);only_p=set(pt)-set(st)
    economic_diffs=[];reason_diffs=[]
    for k in sorted(common):
        a,b=st[k],pt[k]
        # Same entry key should have exactly same execution prices and reason
        # unless one of the engines violates its frozen execution semantics.
        actual_gross=(1 if b["side"]=="LONG" else -1)*(b["exit"]/b["entry"]-1)
        if (abs(actual_gross-a["gross_return"])>1e-10 or
            b["entry_utc"]!=a["entry_utc"]):
            economic_diffs.append({"key":k,"standalone":a,"portfolio":{
                "entry_utc":b["entry_utc"],"exit_reason":b["exit_reason"],
                "exit":b["exit"],"gross_return":actual_gross}})
        if b["exit_reason"]!=a["exit_reason"]:
            reason_diffs.append({"key":k,"standalone":a["exit_reason"],
                "portfolio":b["exit_reason"],"same_economic_fill":abs(actual_gross-a["gross_return"])<=1e-10})
    # Expose compact deterministic examples and full category counts.
    from collections import Counter
    p_classes=Counter(classify_portfolio_only(
        {"signal_index":next(i for i,r in enumerate(rows) if portfolio.iso(r[0])==k[0])},st) for k in only_p)
    s_classes=Counter(classify_standalone_only(st[k],pt) for k in only_s)
    return {"standalone_n":len(st),"portfolio_n":len(pt),"matched_n":len(common),
            "standalone_only_n":len(only_s),"portfolio_only_n":len(only_p),
            "standalone_only_reasons":dict(s_classes),
            "portfolio_only_reasons":dict(p_classes),
            "matched_economic_discrepancy_n":len(economic_diffs),
            "matched_economic_discrepancy_examples":economic_diffs[:8],
            "exit_reason_label_discrepancy_n":len(reason_diffs),
            "exit_reason_label_discrepancy_examples":reason_diffs[:8],
            "standalone_only_examples":[list(k) for k in sorted(only_s)[:8]],
            "portfolio_only_examples":[list(k) for k in sorted(only_p)[:8]]}

def run():
    series,common,hashes=portfolio.prepare()
    cuts=[0]+[len(common)*i//5 for i in range(1,5)]+[len(common)]
    out={"title":"P0 #12 standalone vs portfolio UTC trade-ID parity",
         "producer_commit_sha":os.getenv("GITHUB_SHA","local"),
         "ci_run_id":os.getenv("GITHUB_RUN_ID","local"),
         "source_sha256":hashes,
         "hypothesis":"Trade-count discrepancies are due to independent scheduling, risk caps and cross-asset competition, not mismatched fill semantics.",
         "freeze":"Frozen 2.5x4H ATR stop / 3x4H ATR target / 12x4H bars; turn signal, next open.",
         "caution":"Previously inspected history; not independent OOS. Diagnostic relaxed-cap standalone is NOT a tradeable strategy. Costs 15bp assumed; funding zero for exact execution parity. Actual venue funding absent.",
         "windows":[]}
    saved=(portfolio.SYMS,portfolio.MAX_POS,portfolio.MAX_SYMBOL_NOTIONAL,portfolio.MAX_GROSS_LEVERAGE)
    try:
        for w,(a,b) in enumerate([(0,len(common))]+list(zip(cuts[:-1],cuts[1:]))):
            times=common[a:b]
            row={"window":"full" if w==0 else w,"start_utc":portfolio.iso(times[0]),
                 "end_close_utc":portfolio.iso(times[-1]+H4),"assets":{}}
            for sym in SYMS:
                x=series[sym];lo=x["map"][times[0]];hi=x["map"][times[-1]]+1
                st=standalone_ledger(x["rows"],x["feat"],lo,hi)
                variants={}
                for mode in ("capped","relaxed_cap"):
                    portfolio.SYMS=(sym,)
                    portfolio.MAX_POS=1
                    portfolio.MAX_SYMBOL_NOTIONAL=1. if mode=="capped" else 1e9
                    portfolio.MAX_GROSS_LEVERAGE=2. if mode=="capped" else 1e9
                    p=portfolio.simulate(series,times,"baseline",.0015,0.)
                    pt=portfolio_ledger(p["trades"])
                    v=reconcile(x["rows"],st,pt)
                    v["portfolio_metrics"]=portfolio.metrics(p)
                    variants[mode]=v
                row["assets"][sym]=variants
            out["windows"].append(row)
    finally:
        portfolio.SYMS,portfolio.MAX_POS,portfolio.MAX_SYMBOL_NOTIONAL,portfolio.MAX_GROSS_LEVERAGE=saved
    # Also retain actual multi-symbol portfolio metrics for comparison, with
    # original 2 slots and 0.5% aggregate stop-risk.
    p=portfolio.simulate(series,common,"baseline",.0015,0.)
    out["full_multisymbol_15bp_0funding"]=portfolio.metrics(p)
    # Signal+side keys are only unique WITHIN a symbol. Never key a
    # multi-symbol ledger this way: correlated entries share UTC timestamps.
    cross={}
    full=out["windows"][0]["assets"]
    for sym in SYMS:
        # Recompute isolated portfolio on the same calendar for exact trade IDs.
        portfolio.SYMS=(sym,)
        isolated=portfolio_ledger(portfolio.simulate(series,common,"baseline",.0015,0.)["trades"])
        actual=portfolio_ledger([t for t in p["trades"] if t["symbol"]==sym])
        cross[sym]={"isolated_n":len(isolated),"multi_n":len(actual),
                    "matched_n":len(set(isolated)&set(actual)),
                    "isolated_only_n":len(set(isolated)-set(actual)),
                    "multi_only_n":len(set(actual)-set(isolated)),
                    "isolated_only_examples":[list(k) for k in sorted(set(isolated)-set(actual))[:8]],
                    "multi_only_examples":[list(k) for k in sorted(set(actual)-set(isolated))[:8]]}
    portfolio.SYMS=SYMS
    out["cross_asset_competition"]=cross
    Path(SOURCE).write_text(json.dumps(out,ensure_ascii=False,indent=2))
    for w in out["windows"]:
        print("WINDOW",w["window"])
        for sym,modes in w["assets"].items():
            for mode,z in modes.items():
                print(sym,mode,"standalone",z["standalone_n"],"portfolio",z["portfolio_n"],
                      "matched",z["matched_n"],"economic_diffs",z["matched_economic_discrepancy_n"],
                      "standalone_only",z["standalone_only_reasons"],
                      "portfolio_only",z["portfolio_only_reasons"])
    return out

if __name__=="__main__":
    run()
