"""One-year 4h-Delta partial TP search, 5m OHLC execution, 8 symbols.

Training: 2025-07-01..2026-01-01 (184d)
Model selection validation: 2026-01-01..2026-04-01 (90d)
Post-selection test: 2026-04-01..2026-07-01 (91d, previously inspected
Apr-Jun in earlier experiments, NOT completely fresh unseen OOS).
Annual data: Binance USD-M monthly 5m archives, download where not cached.

Frozen signal = original experiments.pine_vs_codex.run.pine_events;
frozen ATR SL/TP, BE, hold from SELECTED. Fixed prices in percent of entry.
Only exit allocation and its threshold levels are variable. All trading
expenses include proportional exit-leg fees and residual funding.

Never choose configurations based on post-selection test data.
"""
import os,sys,io,csv,zipfile,urllib.request,json,math,time,hashlib,datetime as dt
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d import run as e
from experiments.five_min_90d.compare_three_timeframes import SELECTED,ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events

DAY=e.DAY
TZ=dt.timezone.utc
def ms(y,m,d=1):return int(dt.datetime(y,m,d,tzinfo=TZ).timestamp()*1000)
START=ms(2025,7)
TRAIN_END=ms(2026,1)
VALID_END=ms(2026,4)
END=ms(2026,7)
WARM=ms(2025,5)
MONTHS=[(2025,m) for m in range(5,13)]+[(2026,m) for m in range(1,7)]
YEARMONTHS=[f"{y}-{m:02d}" for y,m in MONTHS]
OUT=Path("experiments/five_min_90d/partial_annual")
CACHE=Path(os.getenv("BINANCE_MONTH_CACHE","/tmp/delta_binance_5m_cache"))
WINDOWS={"train":(START,TRAIN_END),"validation":(TRAIN_END,VALID_END),
         "final_test":(VALID_END,END),"full_year":(START,END)}
SYMS=tuple(e.SYMS)
COST_PER_SIDE=.0008
SPREAD_ROUNDTRIP=.0004
# Only experiment user-requested exit allocation: thresholds are PRICE changes,
# and fractions are of INITIAL $1k qty, not remaining qty.
def generate_ladders():
 ladders=[()]
 for level in (.005,.01,.015,.02):
  for fraction in (.10,.15,.20,.25,.35,.50):
   ladders.append(((level,fraction),))
 two_pairs=((.005,.015),(.005,.02),(.005,.03),
            (.0075,.015),(.01,.02),(.01,.03),
            (.015,.03),(.02,.04))
 shares=((.10,.20),(.15,.20),(.15,.30),(.20,.20),
         (.20,.30),(.25,.25),(.25,.35),(.35,.25))
 for p in two_pairs:
  for share in shares:ladders.append(tuple(zip(p,share)))
 triples=((.005,.015,.03),(.005,.015,.04),
          (.0075,.02,.04),(.01,.02,.04))
 share3=((.10,.20,.20),(.15,.20,.20),(.15,.20,.30),
         (.15,.25,.30),(.20,.20,.20),(.20,.25,.25),
         (.25,.25,.25))
 for p in triples:
  for sh in share3:ladders.append(tuple(zip(p,sh)))
 # Baseline + 24 single + 64 double + 28 triple = 117.
 assert len(ladders)==117 and len(set(ladders))==len(ladders)
 return ladders
def label(ladder):
 if not ladder:return "NO_PARTIAL"
 return ",".join(f"+{threshold*100:g}%:{fraction*100:g}%" for threshold,fraction in ladder)
def score_train(r):
 if r["breach"]:return -1e8
 # Absolute profitability + modest risk penalty and phase acceleration.
 # This objective is fully defined before observing validation/test.
 days=r["phases"][0]["days"] if r["phases"] else 999.
 all_days=sum(x["days"] for x in r["phases"][:2]) if len(r["phases"])>=2 else 999.
 return round(
   r["cumulative_phase_profit_usd"]
   - 30*r["max_dd_pct"]
   + (120 if r["phases"] else 0)
   + (250 if len(r["phases"])>=2 else 0)
   - min(days,200)*.4
   - min(all_days,400)*.3,3)
def summarize(r):
 return {k:r.get(k) for k in
  ("cumulative_phase_profit_usd","breach","max_dd_pct","trades","wins",
   "win_rate_pct","profit_factor","fees","funding","skipped","phases","equity")}
def jsonwrite(name,d):
 OUT.mkdir(parents=True,exist_ok=True)
 path=OUT/name
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
 return path
def get_month(sym,y,m):
 CACHE.mkdir(parents=True,exist_ok=True)
 file=CACHE/f"{sym}-5m-{y}-{m:02d}.zip"
 if file.exists() and file.stat().st_size>10000:
  try:
   with zipfile.ZipFile(file) as z:
    if z.testzip() is None:return file
  except Exception:pass
  file.unlink()
 url=(f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/5m/"
      f"{sym}-5m-{y}-{m:02d}.zip")
 for retry in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={
     "User-Agent":"Mozilla/5.0 delta-strategy-research"}),timeout=120) as resp:
    content=resp.read()
   if len(content)<10000:raise ValueError("Short download")
   tmp=file.with_suffix(".part")
   tmp.write_bytes(content)
   with zipfile.ZipFile(tmp) as z:
    if z.testzip() is not None:raise ValueError("Corrupted ZIP")
   tmp.replace(file)
   return file
  except Exception as exc:
   if retry==3:raise RuntimeError(f"Unable to download {url}: {exc}") from exc
   time.sleep(2*(retry+1))
def read_symbol(sym,files):
 res=[]
 for file in sorted(files):
  with zipfile.ZipFile(file) as z:
   with z.open(z.namelist()[0]) as stream:
    for line in io.TextIOWrapper(stream,encoding="utf-8"):
     chunks=line.strip().split(",")
     try:t=int(chunks[0])
     except (ValueError,IndexError):continue
     if WARM<=t<END:res.append((t,*map(float,chunks[1:5])))
 res.sort(key=lambda x:x[0])
 if not res or res[0][0]>WARM or res[-1][0]<END-e.M:
  raise RuntimeError(f"{sym}: incomplete boundary data {res[0][0] if res else 'none'}..{res[-1][0] if res else 'none'}")
 if any(b[0]-a[0]!=e.M for a,b in zip(res,res[1:])):
  bad=next((a[0],b[0]) for a,b in zip(res,res[1:]) if b[0]-a[0]!=e.M)
  raise RuntimeError(f"{sym}: non-contiguous 5m candles {bad}")
 return res
def source_load():
 jobs=[(sym,y,m) for sym in SYMS for y,m in MONTHS]
 files={s:[] for s in SYMS}
 with ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(get_month,*p):p for p in jobs}
  done=0
  for future in as_completed(futures):
   sym,y,m=futures[future]
   f=future.result()
   files[sym].append(f)
   done+=1
   if done%14==0 or done==len(jobs):
    print("DOWNLOAD_MONTHS",done,len(jobs),flush=True)
 data={};signals={};manifest={}
 for sym in SYMS:
  rows=read_symbol(sym,files[sym])
  data[sym]={v[0]:v for v in rows}
  hourly=ohlc_from_5m(rows,e.H)
  signals[sym]=pine_events(hourly)
  manifest[sym]={
   "bars_5m":len(rows),"first_ms":rows[0][0],"last_ms":rows[-1][0],
   "signals_in_year":sum(START<=t<END for t in signals[sym]),
   "monthly_files":YEARMONTHS,
   "candle_sha256":hashlib.sha256("".join(str(x) for x in rows).encode()).hexdigest(),
  }
  print("SOURCE_VALID",sym,json.dumps(manifest[sym]),flush=True)
 assert len(range(START,END,e.M))==(END-START)//e.M==365*288
 return data,signals,manifest

def tiny_unit_tests():
 # Independently exercise new partial ledger using synthetic 5m candles.
 # No 4h signal warmup needed, entry is explicit.
 t=0;m=e.M
 rows={0:(0,100,100,100,100),m:(m,100,102,100,101),
       2*m:(2*m,101,102,94,100),3*m:(3*m,100,100,100,100)}
 data={"BTCUSDT":rows};signals={"BTCUSDT":{0:{"side":1,"atr_4h":4.}}}
 kwargs=dict(params={"BTCUSDT":(5.,5.,None,None)},start=0,end=4*m,
  cap_price_stop=True,stop_cap_mode="clamp",collect_trades=True)
 prev_fee,prev_spread=e.FEE,e.SPREAD
 e.FEE=COST_PER_SIDE;e.SPREAD=SPREAD_ROUNDTRIP
 try:
  a=e.simulate(data,signals,("BTCUSDT",),partials=(),**kwargs)
  b=e.simulate(data,signals,("BTCUSDT",),partials=((.005,.15),(.015,.20)),**kwargs)
  assert a["trades"]==b["trades"]==1,(a,b)
  tr=b["trade_details"][0]
  assert len(tr["partial_events"])==2, tr
  assert abs(tr["partial_qty_closed_pct"]-35)<1e-6,tr
  assert tr["remaining_qty_pct"]>64.99,tr
  assert b["net_pnl"]>a["net_pnl"],(a["net_pnl"],b["net_pnl"])
  # No positive exit allowed on entry 5m candle.
  cdata={"BTCUSDT":{0:(0,100.,102.,100.,101.),m:(m,101,101,94,100)}}
  c=e.simulate(cdata,signals,("BTCUSDT",),partials=((.005,.15),),**{
   **kwargs,"end":2*m})
  assert c["trade_details"][0]["partial_events"]==[],c
  print("PARTIAL_UNIT_TESTS_PASSED",json.dumps({
    "baseline_pnl":a["net_pnl"],"partial_pnl":b["net_pnl"],
    "partials":tr["partial_events"]}),flush=True)
 finally:e.FEE,e.SPREAD=prev_fee,prev_spread

def test(data,signals,params,exits,period,ladder,group=SYMS,ledger=False):
 start,end=WINDOWS[period]
 r=e.simulate(data,signals,group,params=params,start=start,end=end,
    exit_by_symbol=exits,step=e.M,entry_profit_policy="defer",
    cap_price_stop=True,stop_cap_mode="clamp",
    collect_trades=ledger,partials=ladder)
 return r

def main():
 tiny_unit_tests()
 data,signals,manifest=source_load()
 # Check exact 90d historic baseline as a diagnostic. Longer warm-up changes
 # near-threshold history if the old 60d warmup diverges.
 params={s:(sl,tp,None,None) for s,(sl,tp,be,hold) in SELECTED.items()}
 exits={s:{"be":be,"hold":hold} for s,(sl,tp,be,hold) in SELECTED.items()}
 save={"head_sha":os.getenv("GITHUB_SHA"),"run_id":os.getenv("GITHUB_RUN_ID"),
   "periods_utc":{"train":"2025-07-01..2025-12-31",
     "validation":"2026-01-01..2026-03-31",
     "final_test":"2026-04-01..2026-06-30",
     "full_year":"2025-07-01..2026-06-30"},
   "data":manifest,
   "assets":list(SYMS),"same_signal":"original pine_events/CausalDelta 4h",
   "test_source":"Binance monthly USD-M 5m archives May 2025..Jun 2026",
   "costs":{"fee_per_side":COST_PER_SIDE,"spread_roundtrip":SPREAD_ROUNDTRIP,
    "funding_8h":e.FUNDING,"initial_account":e.INITIAL,
    "notional_per_position":1000,"max_positions":3},
   "rule":"Partial fills: price % above/below entry, fractions of original qty; 5m stop and full TP checked before partial fills. No partial fill during entry candle, all legs charged costs; leftover follows frozen per-asset BE, SL, ATR TP, max hold.",
   "stop_cap":"5% of entry price, clamp",
   "train_objective":"cumulative phase profit minus 30*DD plus phase pass reward and time penalty; no breached candidates",
   "ladders":{},"train_rankings":[],"validation_rankings":[],
   "selection":{},"portfolio_comparisons":{},
   "limitations":[
    "All assets and 5m execution same baseline; partial exits only independent variable.",
    "Train Jul-Dec 2025, validation Jan-Mar 2026, test Apr-Jun 2026. Apr-Jun had been inspected in earlier experiments, thus not a truly new untouched OOS.",
    "Underlying Python CausalDelta not fully parity-verified with user's Pine body.",
    "If both stop and partial target touch same OHLC bar, stop-first assumed; true order unobservable.",
    "No exit in the same entry 5m bar; this does NOT prove 60-second rule compliance.",
    "Real Upscale equity, consistency, phase reset and funding sign unverified.",
    "No actual orderbook slippage; monthly Binance archive quotes differ from Upscale.",
    "A phase-reset USD aggregate is not directly a buy-and-hold or percentage return.",
    "More candidate ladders increases multiple-testing and overfitting risk.",
    "No real orders placed."]}
 old_fee,old_spread=e.FEE,e.SPREAD
 e.FEE=COST_PER_SIDE;e.SPREAD=SPREAD_ROUNDTRIP
 try:
  # Always show exact no-partial train, validation, final and full-year.
  baseline={}
  for period in WINDOWS:
   run=test(data,signals,params,exits,period,(),ledger=period=="final_test")
   baseline[period]=summarize(run)
   if period=="final_test":
    save["baseline_final_test_trade_ledger"]=run["trade_details"]
   print("BASELINE",period,json.dumps(baseline[period],ensure_ascii=False),flush=True)
  save["portfolio_comparisons"]["baseline"]=baseline
  jsonwrite("annual_checkpoint_baseline.json",save)

  ladders=generate_ladders()
  train=[]
  for idx,ladder in enumerate(ladders):
   r=test(data,signals,params,exits,"train",ladder)
   row={"id":idx,"ladder":ladder,"label":label(ladder),
        "score":score_train(r),"metrics":summarize(r)}
   train.append(row)
   if idx%10==0:print("TRAIN_CANDIDATE",idx,len(ladders),row["score"],row["label"],flush=True)
  train.sort(key=lambda row:(row["score"],row["metrics"]["cumulative_phase_profit_usd"]),reverse=True)
  save["train_rankings"]=train
  # Always take 15 train-best, user-proposed 0.5/1.5 15%/20% ladder and
  # baseline into the validation stage, without examining final-test.
  proposed=((.005,.15),(.015,.20))
  shortlist={row["id"] for row in train[:15]}
  shortlist.add(ladders.index(proposed));shortlist.add(0)
  valid=[]
  for idx in sorted(shortlist):
   ladder=ladders[idx]
   r=test(data,signals,params,exits,"validation",ladder)
   row={"id":idx,"ladder":ladder,"label":label(ladder),
        "metrics":summarize(r),"score":score_train(r)}
   valid.append(row)
   print("VALIDATE",idx,row["score"],row["label"],json.dumps(
      {k:row["metrics"][k] for k in ("cumulative_phase_profit_usd","max_dd_pct","breach","phases")},ensure_ascii=False),flush=True)
  valid.sort(key=lambda row:(row["score"],row["metrics"]["cumulative_phase_profit_usd"]),reverse=True)
  save["validation_rankings"]=valid
  winner=valid[0]
  # Keep the baseline as a competitor; never replace it with a bad chosen
  # validation strategy just because optimizer produced a ranking.
  final_ids={winner["id"],ladders.index(proposed),0}
  # Predeclared other structures for interpretability, with no final-test ranking.
  simple=((.005,.15),)
  final_ids.add(ladders.index(simple))
  final_ids.add(ladders.index(((.005,.15),(.015,.20),(.03,.20))))
  save["selection"]={"winner_id":winner["id"],"winner":winner,
    "user_proposed_id":ladders.index(proposed),
    "train_size":len(train),"validation_size":len(valid),
    "selection_freeze_before_final_test":True}
  for idx in sorted(final_ids):
   ladder=ladders[idx];key=f"candidate_{idx}_{label(ladder)}"
   save["ladders"][key]=ladder
   save["portfolio_comparisons"][key]={}
   for period in WINDOWS:
    res=test(data,signals,params,exits,period,ladder,ledger=period=="final_test")
    save["portfolio_comparisons"][key][period]=summarize(res)
    if period=="final_test":
     save["portfolio_comparisons"][key]["final_test_trade_ledger"]=res["trade_details"]
    if period in ("final_test","full_year"):
     print("FINAL_REPORT",key,period,json.dumps(summarize(res),ensure_ascii=False),flush=True)
   jsonwrite("annual_checkpoint_comparisons.json",save)
  # Portfolio-by-asset secondary check, freeze nothing per-coin yet.
  # More granular per-asset optimization on 117 ladders is left as next study
  # because it compounds overfitting; global ladders have 117 degrees tested.
 finally:e.FEE,e.SPREAD=old_fee,old_spread
 p=jsonwrite("annual_partial_take_results.json",save)
 print("YEAR_COMPLETED",p,p.stat().st_size,flush=True)
if __name__=="__main__":main()
