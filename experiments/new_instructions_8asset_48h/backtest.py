"""Reproduce the CANONICAL 'новые инструкции' 4h Delta configuration.

The primary instruction README is parsed; frozen six original parameters are
validated against the old six-asset grid JSON, and added XRP/LINK settings against
the historical pre-optimization 5m PARAMS. No parameter optimization, no BE.
$5000 account, $840 (16.8%) per position, max 3, 48 hours for ALL symbols,
TON trailing +3 ATR activation / 0.5 ATR distance (1h fills). Original
portfolio engine, 1h OHLC fills, .08% fee per side, .02% spread roundtrip,
funding excluded, ATR previous completed 4h signal as old original workflow.

Backtest 2025-07-01..2026-06-30 and 2026-04-01..2026-06-30,
including 6-coin comparison on identical time windows. Not live-accurate
Upscale simulation: historic phase engine omits 30% consistency and has
approximate drawdown / price execution.
"""
import os,sys,json,re,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.five_min_90d.optimize_partial_take_4h import source_load,START,VALID_END,END
from experiments.five_min_90d.compare_three_timeframes import ohlc_from_5m
from experiments.pine_vs_codex.run import pine_events
from experiments.five_min_90d import run as historical_eight
import experiments.max_strategy_grid.prop_portfolio as prop

OUT=Path("experiments/new_instructions_8asset_48h")
README=Path("новые инструкции/README.md")
SIX_JSON=Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json")
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT","BNBUSDT","ZECUSDT","XRPUSDT","LINKUSDT")
ADDED={"XRPUSDT":(5.,2.5,None,None),"LINKUSDT":(5.,5.,None,None)}
SIX=tuple(s for s in SYMS if s not in ADDED)
H=prop.H

def check_document():
 txt=README.read_text(encoding="utf-8")
 assert "16,8%" in txt and "$840" in txt and "50,4%" in txt,"Position 16.8 percent missing"
 assert "**Единое время удержания 48 часов" in txt,"48 hours not documented"
 assert "исполнение, SL/TP и трейлинг отслеживать по 1-часовым свечам" in txt
 assert "funding ранее исключался" in txt
 params={}
 for line in txt.splitlines():
  v=[x.strip() for x in line.split("|")]
  if len(v)!=6 or v[1] not in SYMS:continue
  s=v[1]
  assert s not in params,("Duplicate symbol",s)
  sl,tp=float(v[2]),float(v[3])
  if v[4]=="Нет":act=dist=None
  else:
   m=re.fullmatch(r"([0-9.]+)\s*/\s*([0-9.]+)",v[4])
   assert m,("Unrecognized trailing",s,v[4])
   act,dist=float(m.group(1)),float(m.group(2))
  params[s]=(sl,tp,act,dist)
 assert set(params)==set(SYMS),("Missing symbols in canonical instructions",set(SYMS)-set(params))
 old=json.loads(SIX_JSON.read_text(encoding="utf-8"))["parameters"]
 assert set(old)==set(SIX)
 for s in SIX:assert params[s]==tuple(old[s]),("Original frozen parameters changed",s,params[s],old[s])
 for s,x in ADDED.items():
  assert params[s]==x,("Unexpected added settings",s,params[s])
  assert tuple(historical_eight.PARAMS[s])==x,("Not sourced from historical XRP/LINK params",s)
 print("PRIMARY_DOCUMENT_VALIDATED",json.dumps(params,ensure_ascii=False),flush=True)
 return params

def unit_test():
 # Verify restored TON trailing updates only after close of 1h candle.
 bars={
  0:(0,100.,100.1,99.9,100.),
  H:(H,100.,104.,100.,103.),
  2*H:(2*H,104.,104.2,103.,104.),
  3*H:(3*H,104.,104.1,103.6,103.8),
  4*H:(4*H,103.8,104.,103.7,103.9)}
 got=prop.run({"TONUSDT":bars},
  {"TONUSDT":{0:{"side":1,"atr_4h":1.}}},
  {"TONUSDT":(2.5,5.,3.,.5)},
  sorted(bars),reset=False,max_hours=48)
 assert got["trades"]==1 and got["stops"]==1 and got["takes"]==0,got
 # 3.5% profit at original $100 price -> stop triggered at $103.50 next bar.
 expected=prop.NOTIONAL*(.035-(prop.FEE+prop.SPREAD/2)*(1+1.035))
 assert abs(got["closed_net_pnl"]-round(expected,2))<.015,(got,expected)
 print("TON_TRAILING_UNIT_PASSED",json.dumps({"notional_usd":prop.NOTIONAL,
  "stop_price":103.5,"net_pnl_usd":got["closed_net_pnl"]}),flush=True)

def simulate(raw,signals,params,assets,start,end,reset):
 times=list(range(start,end,H))
 assert len(times)==(end-start)//H
 for s in assets:
  count=sum(t in raw[s] for t in times)
  assert count==len(times),("Incomplete hourly source",s,count,len(times))
 output=prop.run({s:raw[s] for s in assets},{s:signals[s] for s in assets},
  {s:params[s] for s in assets},times,reset=reset,max_hours=48)
 assert set(output["by_symbol"])==set(assets)
 assert sum(v["trades"] for v in output["by_symbol"].values())==output["trades"]
 return output

def main():
 assert prop.INITIAL==5000. and prop.FEE==.0008 and prop.SPREAD==.0002
 assert prop.NOTIONAL==1000.,"Historic engine changed unexpectedly"
 prop.NOTIONAL=840.
 params=check_document()
 unit_test()
 raw5,_,manifest=source_load()
 assert set(raw5)==set(SYMS)
 hourly={};signals={};coverage={}
 for s in SYMS:
  rows=sorted(raw5[s].values())
  bucket=ohlc_from_5m(rows,H)
  assert bucket and bucket[0][0]<START and bucket[-1][0]==END-H,(s,len(bucket))
  hourly[s]={b[0]:b for b in bucket}
  signals[s]=pine_events(bucket,expanded=False,atr_basis="prior")
  coverage[s]={
   "hourly_bars":len(bucket),
   "year_signal_count":sum(START<=t<END for t in signals[s]),
   "q2_signal_count":sum(VALID_END<=t<END for t in signals[s]),
   "5m_bars":manifest[s]["bars_5m"],
   "source_first":bucket[0][0],"source_last":bucket[-1][0]}
  print("ASSET_CHECK",s,json.dumps(coverage[s]),flush=True)
 studies={
  "eight_annual_challenge_reset":(SYMS,START,END,True),
  "eight_annual_continuous":(SYMS,START,END,False),
  "eight_apr_jun_challenge_reset":(SYMS,VALID_END,END,True),
  "six_annual_challenge_reset":(SIX,START,END,True),
  "six_apr_jun_challenge_reset":(SIX,VALID_END,END,True)}
 results={}
 for name,(assets,start,end,reset) in studies.items():
  v=simulate(hourly,signals,params,assets,start,end,reset)
  results[name]=v
  print("PORTFOLIO_RESULT",name,json.dumps(v,ensure_ascii=False),flush=True)
 outputs={
  "source":"новые инструкции/README.md",
  "source_original_6":"experiments/max_strategy_grid/pine_baseline_2026-10-29.json",
  "source_added_2":"experiments/five_min_90d/run.py PARAMS.update",
  "parameters":params,
  "config":{"assets":list(SYMS),"starting_deposit_usd":prop.INITIAL,
   "position_notional_usd":prop.NOTIONAL,"position_allocation_pct":16.8,
   "max_positions":3,"max_notional_usd":prop.NOTIONAL*3,
   "fee_per_side":prop.FEE,"spread_roundtrip":prop.SPREAD,
   "funding":0,"uniform_hold_hours":48,
   "signal_timeframe":"4h","execution_timeframe":"1h",
   "atr_reference":"prior closed 4h bar (frozen original signal implementation)",
   "ton_trailing_activation_atr":3,"ton_trailing_distance_atr":.5,
   "stop_price_cap":None,"breakeven":None,
   "max_daily_drawdown_pct":5,"max_total_drawdown_pct":10,
   "phase_consistency_30pct":"not implemented in legacy prop engine"},
  "data_provenance":manifest,"asset_coverage":coverage,
  "results":results,
  "limitations":[
   "Uses exact original hourly prop_portfolio.run mechanics, unlike recent eight-coin five-minute execution studies.",
   "5m source aggregated to 1h for equal venue/window 8 asset comparison; source is Binance USD-M, not Upscale quotes.",
   "6-coin reference uses identical calendar windows as the eight-coin test, not the older 244/362-day mismatched-universe results.",
   "Only 16.8% notional changed from original document; original six per-coin SL/TP/trailing unchanged; added XRP and LINK come from historical eight-symbol parameters.",
   "No separate price cap on ATR initial stop, no BE and no funding, per original instructions.",
   "All positions max 48h, regardless of per-coin parameters in other experiments.",
   "Stop-first for ambiguous hourly candle, and closing 4h signal only.",
   "Original simulator does not implement 30% consistency; 5/10% risk and phase rules approximate.",
   "Historic signal source uses lagged prior 4h ATR and CausalDelta based on executed SMA21/RMA-RSI12/EMA7/log transformation, not header-only RSI27.",
   "No OOS refit or strategy optimization; settings selected in earlier training studies, and trading periods overlap their training."
   ]}
 OUT.mkdir(parents=True,exist_ok=True)
 file=OUT/"results.json"
 file.write_text(json.dumps(outputs,ensure_ascii=False,indent=2,allow_nan=False))
 print("CANONICAL_CONFIG_BACKTEST_FINISHED",str(file),file.stat().st_size,flush=True)

if __name__=="__main__":main()
