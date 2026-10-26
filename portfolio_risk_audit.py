"""P1 chronological, risk-sized, OHLC-only portfolio audit. NEVER submits orders.
Frozen baseline BTC/ETH/ICP versus same baseline with retrospectively selected
ETH OB-proxy + raw reverse exit. ALL cached history already inspected, not OOS.
"""
import datetime as dt, hashlib, json, math, os, statistics
from pathlib import Path
from feature_walkforward import data
from pattern_confluence import flags
from execution_core import resolve_bar
from funding_timing import exposure_bounds, HOUR_MS

SYMS=("BTCUSDT","ETHUSDT","ICPUSDT")
COSTS=(.0015,.0025,.004)
FUNDING=(0.,.0001,.0003)
MAX_POS=2
RISK=.0025
PORT_RISK=.005
MAX_GROSS_LEVERAGE=2.
MAX_SYMBOL_NOTIONAL=1.
HOLD=12
SEED=20261026
FREEZE_UTC="2026-10-26T16:00:00Z"
CONFIG={"symbols":SYMS,"signal":"completed 4H turn","baseline":{"sl_atr":2.5,"tp_atr":3.,"hold_bars":12},
        "challenger_ETH":{"filter":"OHLC OB proxy","sl_atr":2.5,"tp_atr":6.,"hold_bars":12,"exit":"raw opposite turn at next open"},
        "risk_fraction":RISK,"portfolio_stop_risk_fraction":PORT_RISK,"max_positions":MAX_POS,
        "max_gross_leverage":MAX_GROSS_LEVERAGE,"max_symbol_notional":MAX_SYMBOL_NOTIONAL,
        "tie_priority":SYMS,"costs":COSTS,"funding":FUNDING,"seed":SEED}
CONFIG_HASH=hashlib.sha256(json.dumps(CONFIG,sort_keys=True).encode()).hexdigest()

def iso(t):
    return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()

def prepare():
    series={}; hashes={}
    for s in SYMS:
        p=Path("data")/(s+"_1h.csv")
        if not p.is_file():raise FileNotFoundError("Cached 1H required: "+str(p))
        hashes[s]=hashlib.sha256(p.read_bytes()).hexdigest()
        rows,feat=data(s,aggregation="strict")
        if any(rows[i][0]-rows[i-1][0]!=4*HOUR_MS for i in range(1,len(rows))):
            raise ValueError("Missing 4H bar in "+s+"; fail closed")
        series[s]={"rows":rows,"feat":feat}
    common=sorted(set.intersection(*(set(x["rows"][i][0] for i in range(len(x["rows"]))) for x in series.values())))
    if not common:raise ValueError("No aligned UTC bars")
    # Restrict to one contiguous common interval; fail closed on any interior gap.
    if any(b-a!=4*HOUR_MS for a,b in zip(common,common[1:])):
        raise ValueError("Non-contiguous shared 4H grid")
    for s,x in series.items():
        idx={r[0]:i for i,r in enumerate(x["rows"])}
        x["map"]={t:idx[t] for t in common}
    return series,common,hashes

def exposure(p,mark,now,rate,exact=False):
    if not rate:return 0.
    # Max event count includes funding boundary at mark; actual venue is UNKNOWN.
    n=exposure_bounds(p["entry_ms"],now,now)["funding_events_max"]
    return p["notional"]*rate*n

def mark_equity(cash,active,series,t,rate):
    v=cash
    for s,p in active.items():
        row=series[s]["rows"][series[s]["map"][t]]
        v+=p["side"]*p["qty"]*(row[4]-p["entry"])-exposure(p,row[4],t+4*HOUR_MS,rate)
    return v

def cash_at_open(cash,active,series,t,rate):
    v=cash
    for s,p in active.items():
        row=series[s]["rows"][series[s]["map"][t]]
        v+=p["side"]*p["qty"]*(row[1]-p["entry"])-exposure(p,row[1],t,rate)
    return v

def settle(s,p,price,why,earliest,latest,cash,ledger,cost,rate,series):
    b=exposure_bounds(p["entry_ms"],earliest,latest)
    fee_exit=p["qty"]*price*cost/2
    funding=p["notional"]*rate*b["funding_events_max"]
    gross=p["side"]*p["qty"]*(price-p["entry"])
    cash+=gross-fee_exit-funding
    net=gross-p["fee_entry"]-fee_exit-funding
    ledger.append({"symbol":s,"side":"LONG" if p["side"]==1 else "SHORT",
      "signal_utc":iso(p["signal_ms"]),"entry_utc":iso(p["entry_ms"]),
      "exit_utc_earliest":iso(earliest),"exit_utc_latest":iso(latest),
      "exit_reason":why,"entry":p["entry"],"exit":price,"stop":p["stop"],"target":p["target"],
      "quantity":p["qty"],"notional":p["notional"],"exit_notional":p["qty"]*price,"stop_risk":p["risk"],
      "gross_pnl":gross,"fees":p["fee_entry"]+fee_exit,"funding_max":funding,
      "funding_events_min":b["funding_events_min"],"funding_events_max":b["funding_events_max"],
      "net_pnl":net,"net_pct_initial_equity":100*net/p["equity_before"],
      "net_R":net/p["risk"],"equity_before":p["equity_before"],"cash_after":cash,
      "strategy_hash":CONFIG_HASH})
    return cash

def resolve_open_gap(open_price, side, stop, target):
    """Only information available at this open: no current-bar high/low/close.

    Adverse stop gaps fill at open. Favorable target gaps fill at the target,
    deliberately forfeiting price improvement. Returns (fill, reason).
    """
    if side not in (1, -1) or not all(math.isfinite(v) and v > 0 for v in (open_price, stop, target)):
        raise ValueError("Invalid open/side/stop/target")
    if side * (target - stop) <= 0:
        raise ValueError("Invalid stop/target ordering")
    if side * (open_price - stop) <= 0:
        return open_price, "stop"
    if side * (open_price - target) >= 0:
        return target, "target"
    return None, None


def simulate(series,times,variant="baseline",cost=.0015,rate=0.,start_cash=1.):
    """Sequential bar-close equity marks, new entries at next open; no shared future data."""
    cash=start_cash;active={};ledger=[];curve=[];skips={};counts=[0,0,0];turnover=0.
    def skip(why):skips[why]=skips.get(why,0)+1
    for step,t in enumerate(times):
        closed_before=len(ledger)
        # Prior close's reverse exit is executed at THIS open, before new entries.
        for s in tuple(active):
            p=active[s]
            if p.get("reverse_pending"):
                op=series[s]["rows"][series[s]["map"][t]][1]
                cash=settle(s,p,op,"raw_reverse_next_open",t,t,cash,ledger,cost,rate,series)
                turnover+=p["qty"]*op;del active[s]
        # P0 chronology: settle OLD positions already through stop/target
        # at this open BEFORE admitting any new signals. Do not inspect the
        # new bar's high/low/close here. The gap loss and exit fee must affect
        # available slots, same-symbol lock, cash and risk sizing immediately.
        for s in tuple(active):
            p=active[s]
            op=series[s]["rows"][series[s]["map"][t]][1]
            fill,why=resolve_open_gap(op,p["side"],p["stop"],p["target"])
            if why:
                cash=settle(s,p,fill,why,t,t,cash,ledger,cost,rate,series)
                turnover+=p["qty"]*fill
                del active[s]
        # Entries use only signal bar whose close is <= this open.
        if step>0:
            for s in SYMS:  # deterministic priority for competing signals
                x=series[s];i=x["map"][t];f=x["feat"][i-1]
                if not f or not f["turn"]:continue
                challenger=(variant=="challenger" and s=="ETHUSDT")
                if challenger and not flags(x["rows"],x["feat"],i-1).get("ob_proxy",False):
                    skip("ETH_OB_filter");continue
                if s in active:skip("same_symbol_open");continue
                if len(active)>=MAX_POS:skip("max_two_positions");continue
                atr=f["atr"];side=f["side"]
                entry=x["rows"][i][1]
                sl,tp=(2.5,6.) if challenger else (2.5,3.)
                if not math.isfinite(atr) or atr<=0 or entry<=0:
                    skip("invalid_atr_or_price");continue
                stop=entry-side*sl*atr;target=entry+side*tp*atr
                if stop<=0 or target<=0 or side*(entry-stop)<=0:
                    skip("invalid_stop");continue
                eq=cash_at_open(cash,active,series,t,rate)
                if eq<=0:skip("insolvent");continue
                existing_risk=sum(p["risk"] for p in active.values())
                budget=min(RISK*eq,PORT_RISK*eq-existing_risk)
                if budget<=0:skip("aggregate_stop_risk");continue
                qty=budget/abs(entry-stop)
                notional=qty*entry
                gross=sum(p["notional"] for p in active.values())
                # Reject rather than silently reduce intended 0.25%-risk sizing.
                if notional>MAX_SYMBOL_NOTIONAL*eq or gross+notional>MAX_GROSS_LEVERAGE*eq:
                    skip("notional_leverage_cap");continue
                entry_fee=notional*cost/2
                if entry_fee>=eq or cash-entry_fee<=0:
                    skip("fee_affordability");continue
                cash-=entry_fee;turnover+=notional
                active[s]={"entry_ms":t,"signal_ms":x["rows"][i-1][0],
                           "entry_index":i,"entry":entry,"side":side,"qty":qty,
                           "notional":notional,"risk":budget,"fee_entry":entry_fee,
                           "stop":stop,"target":target,"equity_before":eq,
                           "reverse_pending":False}
        # Resolve current 4H OHLC pessimistically. Stops outrank targets.
        for s in tuple(active):
            p=active[s];x=series[s];i=x["map"][t];bar=x["rows"][i]
            fill,why=resolve_bar(bar,p["side"],p["stop"],p["target"])
            if why:
                cash=settle(s,p,fill,why,t,t+4*HOUR_MS,cash,ledger,cost,rate,series)
                turnover+=p["qty"]*fill;del active[s];continue
            if i-p["entry_index"]>=HOLD-1 or step==len(times)-1:
                reason="time" if i-p["entry_index"]>=HOLD-1 else "terminal"
                cash=settle(s,p,bar[4],reason,t+4*HOUR_MS,t+4*HOUR_MS,cash,ledger,cost,rate,series)
                turnover+=p["qty"]*bar[4];del active[s];continue
            if variant=="challenger" and s=="ETHUSDT":
                f=x["feat"][i]
                if f and f["turn"] and f["side"]==-p["side"]:
                    p["reverse_pending"]=True
        eq=mark_equity(cash,active,series,t,rate)
        if eq<=0:raise AssertionError("Non-positive equity")
        counts[len(active)]+=1
        for closed in ledger[closed_before:]:
            closed["equity_after_bar_close_mtm"]=eq
        curve.append({"utc":iso(t+4*HOUR_MS),"equity":eq,"active":len(active)})
    assert not active
    return {"trades":ledger,"curve":curve,"skips":skips,"concurrent_bars":counts,"turnover_notional":turnover,
            "start_cash":start_cash,"final_cash":cash}

def metrics(res):
    ledger=res["trades"];curve=res["curve"];n=len(ledger)
    vals=[x["net_pnl"] for x in ledger]
    p=sum(max(0,v) for v in vals);l=-sum(min(0,v) for v in vals)
    peak=res["start_cash"];dd=0.;worst=None
    monthly={}
    for c in curve:
        peak=max(peak,c["equity"]);dd=max(dd,1-c["equity"]/peak)
        monthly[c["utc"][:7]]=c["equity"]
    prev=res["start_cash"]
    for month,value in sorted(monthly.items()):
        r=value/prev-1
        if worst is None or r<worst[1]:worst=(month,r)
        prev=value
    streak=longest=0
    for v in vals:
        streak=streak+1 if v<0 else 0;longest=max(longest,streak)
    nb=len(curve)
    by={}
    for s in SYMS:
        a=[x for x in ledger if x["symbol"]==s]
        pp=sum(max(0,x["net_pnl"]) for x in a)
        ll=-sum(min(0,x["net_pnl"]) for x in a)
        by[s]={"n":len(a),"net_pnl":round(sum(x["net_pnl"] for x in a),7),
               "pf":round(pp/ll,4) if ll else None,
               "mean_net_R":round(statistics.mean(x["net_R"] for x in a),4) if a else None}
    ret=res["final_cash"]/res["start_cash"]-1
    return {"n":n,"win_pct":round(100*sum(v>0 for v in vals)/n,2) if n else None,
      "net_pf":round(p/l,4) if l else None,"mean_net_R":round(statistics.mean(x["net_R"] for x in ledger),4) if n else None,
      "net_return_pct":round(100*ret,4),"gross_trade_pnl":round(sum(x["gross_pnl"] for x in ledger),7),
      "fees":round(sum(x["fees"] for x in ledger),7),"funding":round(sum(x["funding_max"] for x in ledger),7),
      "max_close_to_close_mtm_dd_pct":round(100*dd,4),
      "return_over_max_dd":round(ret/dd,4) if dd else None,
      "worst_calendar_month":worst[0] if worst else None,
      "worst_month_pct":round(100*worst[1],4) if worst else None,
      "exposure_pct":round(100*(1-res["concurrent_bars"][0]/len(curve)),2) if curve else None,
      "concurrent_bar_counts":res["concurrent_bars"],"skipped_signals":res["skips"],
      "longest_loss_streak":longest,"turnover_notional_per_initial_equity":round(res["turnover_notional"]/res["start_cash"],4),
      "per_asset":by}

def main():
    series,times,hashes=prepare()
    # Common UTC nonoverlapping chronological windows, independent equity resets;
    # all periods have been seen during prior research, NOT untouched OOS.
    cuts=[0]+[len(times)*i//5 for i in range(1,5)]+[len(times)]
    report={"title":"P1 executable chronological 4H portfolio; previously inspected history",
      "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "producer_commit_sha":os.environ.get("GITHUB_SHA","local"),
      "ci_run_id":os.environ.get("GITHUB_RUN_ID","local"),
      "source_hashes":hashes,"config":CONFIG,"strategy_hash":CONFIG_HASH,
      "freeze_utc":FREEZE_UTC,"data_warning":"Historical cache previously inspected; no independent OOS. No real orders.",
      "accounting":"Starting equity=1 per window. Cash plus close-mark unrealized less conservative accrued synthetic funding. Risk size=0.25% equity / stop distance, max 2 simultaneous, 0.5% aggregate initial stop risk, max 2x gross notional. Fixed priority BTC/ETH/ICP; same-symbol lockout. Half round-trip fee at entry and half on EXIT execution notional. Pre-existing open-time gaps settle before signal admission; adverse stop gaps at open, favorable target gaps conservatively at target. Intrabar stop-first after admission. Synthetic adverse funding max UTC 8h bound; no venue rates. Exit fills intrabar have unknown timing. Monthly mark-to-market at last bar close. No market impact or mark-price liquidation.",
      "boundary_warning":"Independent portfolio schedules within each nonoverlapping window; equity reset and terminal close at window end. No selection based on any window. Different cohort and scheduling from prior pseudo-equity reports.",
      "windows":[],"full_common_history":{}}
    for j in range(5):
        chunk=times[cuts[j]:cuts[j+1]]
        w={"window":j+1,"start_utc":iso(chunk[0]),"end_close_utc":iso(chunk[-1]+4*HOUR_MS),"bars":len(chunk),"variants":{}}
        for variant in ("baseline","challenger"):
            grid={}
            for c in COSTS:
                for f in FUNDING:
                    res=simulate(series,chunk,variant,c,f)
                    key=f"{round(c*10000)}bp_fee_{round(f*10000)}bp_funding"
                    grid[key]=metrics(res)
                    if c==.0015 and f==.0003:
                        w["variants"][variant]={"primary_metrics":metrics(res),"trades":res["trades"],"equity_curve":res["curve"]}
            w["variants"][variant]["stress_grid"]=grid
        report["windows"].append(w)
    for variant in ("baseline","challenger"):
        res=simulate(series,times,variant,.0015,.0003)
        full_stress={}
        for c in COSTS:
            for f in FUNDING:
                key=f"{round(c*10000)}bp_fee_{round(f*10000)}bp_funding"
                full_stress[key]=metrics(simulate(series,times,variant,c,f))
        report["full_common_history"][variant]={"metrics":metrics(res),"stress_grid":full_stress,
            "trades":res["trades"],"equity_curve":res["curve"]}
    path=Path("reports/portfolio_risk_audit.json");path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({"source_hashes":hashes,"windows":[{"window":w["window"],
      "baseline":w["variants"]["baseline"]["primary_metrics"]["net_return_pct"],
      "challenger":w["variants"]["challenger"]["primary_metrics"]["net_return_pct"],
      "baseline_dd":w["variants"]["baseline"]["primary_metrics"]["max_close_to_close_mtm_dd_pct"],
      "challenger_dd":w["variants"]["challenger"]["primary_metrics"]["max_close_to_close_mtm_dd_pct"]} for w in report["windows"]],
      "full":{k:v["metrics"] for k,v in report["full_common_history"].items()}},ensure_ascii=False))
if __name__=="__main__":main()
