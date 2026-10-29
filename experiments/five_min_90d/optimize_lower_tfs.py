"""Train-only per-coin SL/TP/BE/hold selection for 5m and 15m Delta signals.

Signal formula remains the project's CausalDelta/pine_shade implementation.
Execution held fixed at 5m for all signal timeframes (including 4h control).
No OOS or 4h parameters used in selection of 5m/15m variants.
Fee stress .08% each side, spread .04% roundtrip, 5% max price stop (clamp).
"""
import json,math,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.compare_three_timeframes import (
    SELECTED,TF_MS,GROUPS,WINDOWS,ohlc_from_5m,make_lower_tf_signals,make_4h_signals)
from research_multiasset import atr

# Selected in advance, never from out-of-sample performance:
SL_GRID=(.25,.5,1.,2.)
TP_GRID=(.25,.5,1.,2.)
EXIT_GRID=((None,4),(None,12),(None,24),(.005,8),(.01,24),(.015,48))
TRAIN=e.START, e.START+60*e.DAY
OOS=e.START+60*e.DAY,e.END
def score(r):
    """Utility of single-coin 60-day TRAIN with downside and turnover penalties."""
    if r["breach"] is not None:return -1e8
    if r["trades"]<8:return -1e7+(r["trades"]*100)
    # Cumulative phase profit survives challenge-phase equity reset.
    return r["cumulative_phase_profit_usd"]-30*r["max_dd_pct"]-0.15*r["trades"]

def main():
    allraw={};sigs={tf:{} for tf in ("5m","15m","4h")};sources={}
    for sym in e.SYMS:
        rows=e.download(sym)
        allraw[sym]={r[0]:r for r in rows}
        hour=ohlc_from_5m(rows,e.H)
        four=ohlc_from_5m(rows,4*e.H)
        a4=atr(four);am={r[0]:a for r,a in zip(four,a4)}
        sigs["4h"][sym]=make_4h_signals(hour)
        for tf in ("5m","15m"):
            sampled=ohlc_from_5m(rows,TF_MS[tf])
            sigs[tf][sym],_=make_lower_tf_signals(sampled,tf,am)
        sources[sym]={tf:sum(e.START<=t<e.END for t in sigs[tf][sym])
                      for tf in sigs}
        print("DATA",sym,len(rows),json.dumps(sources[sym]),flush=True)
    rawn=len(range(e.START,e.END,e.M))
    common=set.intersection(*(set(v) for v in allraw.values()))
    got=sum(t in common for t in range(e.START,e.END,e.M))
    if got!=rawn:raise RuntimeError(f"incomplete common 5m data: {got}/{rawn}")
    baseline={sym:tuple(SELECTED[sym]) for sym in e.SYMS}
    frozen_par={s:(x[0],x[1],None,None) for s,x in baseline.items()}
    frozen_exits={s:{"be":x[2],"hold":x[3]} for s,x in baseline.items()}
    results={"run_sha":os.getenv("GITHUB_SHA"),"run_id":os.getenv("GITHUB_RUN_ID"),
        "data":"Binance UM 5m input; closed 5m 15m 4h signal candles",
        "source_signal":"CausalDelta/pine_shade; 4h existing pine_events",
        "periods":{name:[str(start),str(end)] for name,(start,end) in WINDOWS.items()},
        "symbols":list(e.SYMS),"source_signal_counts":sources,
        "grid":{"sl_atr4h":SL_GRID,"tp_atr4h":TP_GRID,
                "be_price_move_and_hold_hours":EXIT_GRID,
                "fee_per_side":.0008,"spread_roundtrip":.0004,
                "funding_per_8h":e.FUNDING,"price_stop_max_pct":5,
                "stop_cap_method":"clamp","position_usd_notional":1000},
        "selected":{},"portfolio":{},"selection_method":"TRAIN only; score=cumulative phase profit - 30*DDpct - 0.15*trades, disallow breach and <8 trades",
        "limitations":[
          "Selection is in-sample, first 60 days only. OOS final 30 days never in selection objective.",
          "Original 4h parameters unchanged. No 5m/15m OOS retuning.",
          "Per-asset isolation does not guarantee same outcome on shared 8-asset account.",
          "This is DeltaRSI scaled 5m/15m; NOT user's separate 5m RSI+RVGI strategy.",
          "ATR(4h) used for risk-price distances on all TF, while multipliers are optimized per coin AND per signal TF.",
          "Price stop capped to 5% from entry; partial fills, hidden quote source, venue rules unverified.",
          "OHLC stop-first; same-entry-candle profitable target deferred, not exact 60-second constraint.",
          "Upscale phase engine is approximate: 30% consistency, risk mark, funding and phase reset unverified.",
          "OOS calendar has been examined in earlier experiments; not a genuinely untouched unseen market."
        ]}
    old_fee,old_spread=e.FEE,e.SPREAD
    e.FEE,e.SPREAD=.0008,.0004
    try:
      for tf in ("5m","15m"):
        selected={}
        results["selected"][tf]={}
        for sym in e.SYMS:
          ranked=[]
          for sl in SL_GRID:
            for tp in TP_GRID:
              for be,hold in EXIT_GRID:
                params={sym:(sl,tp,None,None)}
                ex={sym:{"be":be,"hold":hold}}
                r=e.simulate(allraw,sigs[tf],(sym,),params=params,
                      start=TRAIN[0],end=TRAIN[1],
                      exit_by_symbol=ex,cap_price_stop=True,stop_cap_mode="clamp",
                      entry_profit_policy="defer")
                ranked.append((score(r),sl,tp,be,hold,r))
          ranked.sort(key=lambda x:(x[0],x[5]["cumulative_phase_profit_usd"],-x[5]["max_dd_pct"]),reverse=True)
          top=ranked[0]
          selected[sym]=(top[1],top[2],top[3],top[4])
          short=lambda x:{"score":round(x[0],3),"sl_atr4h":x[1],"tp_atr4h":x[2],
               "be_trigger_price_pct":None if x[3] is None else 100*x[3],
               "hold_hours":x[4],
               "train":{k:x[5][k] for k in ("cumulative_phase_profit_usd","breach","trades",
                 "win_rate_pct","profit_factor","max_dd_pct","fees","funding","phases")}}
          results["selected"][tf][sym]={"choice":short(top),"top5":[short(x) for x in ranked[:5]],
                          "candidates_evaluated":len(ranked)}
          print("SELECTED",tf,sym,json.dumps(short(top),ensure_ascii=False),flush=True)
        par={s:(x[0],x[1],None,None) for s,x in selected.items()}
        exs={s:{"be":x[2],"hold":x[3]} for s,x in selected.items()}
        modes={tf:{"signal_tf":tf,"params":par,"exits":exs},
               "4h_fixed": {"signal_tf":"4h","params":frozen_par,"exits":frozen_exits}}
        results["portfolio"][tf]={}
        for mode,config in modes.items():
          results["portfolio"][tf][mode]={}
          for window,(start,end) in WINDOWS.items():
            results["portfolio"][tf][mode][window]={}
            for grp,g in GROUPS.items():
              r=e.simulate(allraw,sigs[config["signal_tf"]],g,
                  params=config["params"],start=start,end=end,
                  exit_by_symbol=config["exits"],cap_price_stop=True,
                  stop_cap_mode="clamp",entry_profit_policy="defer")
              results["portfolio"][tf][mode][window][grp]=r
              slim={k:r[k] for k in ("phases","cumulative_phase_profit_usd",
                   "breach","max_dd_pct","trades","win_rate_pct","profit_factor",
                   "fees","funding","skipped")}
              print("PORTFOLIO",tf,mode,window,grp,json.dumps(slim,ensure_ascii=False),flush=True)
    finally:
      e.FEE,e.SPREAD=old_fee,old_spread
    p=Path("experiments/five_min_90d/optimized_lower_tf_results.json")
    p.write_text(json.dumps(results,indent=2,ensure_ascii=False))
    print("DONE",str(p),"bytes",p.stat().st_size,flush=True)
if __name__=="__main__":main()
