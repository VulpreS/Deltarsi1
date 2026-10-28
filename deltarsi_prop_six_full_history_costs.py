"""Full available common 1h history, one $5000 account, four vs six symbols.
Research only. Compare baseline and pre-specified DeltaRSI decay priority.
No account reset; record breaches without hiding subsequent PnL.
"""
import json,datetime as dt
from pathlib import Path
import deltarsi_prop_four_assets_one_account as b
from causal_4h_parity_audit import load,events,H
FOUR=("BTCUSDT","ETHUSDT","ICPUSDT","TONUSDT")
SIX=FOUR+("BNBUSDT","ZECUSDT")
b.PARAM.update({"BNBUSDT":(None,None),"ZECUSDT":(None,None)})
raw_cache={};signals={};hashes={}
for sym in SIX:
 raw,sha=load(sym)
 raw_cache[sym]=raw;hashes[sym]=sha
 ev,_=events(raw)
 signals[sym]={e["entry_ms"]:e for e in ev["closed"]}
def simulate(syms,fee,funding,priority):
 # Existing full-account simulator with one change: rank simultaneous signals.
 # We inject cached load/events and symbol selection, then restore afterwards.
 old_syms=b.SYMS;old_load=b.load;old_events=b.events
 def cached_load(sym):return raw_cache[sym],hashes[sym]
 def cached_events(raw):
  sym=next(k for k,v in raw_cache.items() if v is raw)
  return {"closed":list(signals[sym].values())},None
 b.SYMS=syms;b.load=cached_load;b.events=cached_events
 try:
  return b.simulate(fee,funding)
 finally:
  b.SYMS=old_syms;b.load=old_load;b.events=old_events
# To avoid altering the existing simulator, baseline uses it unchanged.
# Priority modes use a dedicated source-derived variant with sorting of eligible signals.
import inspect
src=inspect.getsource(b.simulate)
src=src.replace("def simulate(fee=.00008,funding=.00015,max_positions=3):","def ranked_simulate(fee=.00008,funding=.00015,max_positions=3,priority='baseline'):")
src=src.replace("  for sym in SYMS:\n   if sym in p or t not in signals[sym]:continue","  candidates=[sym for sym in SYMS if sym not in p and t in signals[sym]]\n  if priority!='baseline':\n   def score(sym):\n    e=signals[sym][t];peak=abs(e['prior_4h_delta']);decay=max(0.,1.-e['ratio'])\n    return peak if priority=='peak' else decay if priority=='decay' else __import__('math').log1p(peak)*decay\n   candidates.sort(key=lambda sym:(-score(sym),sym))\n  for sym in candidates:")
scope=dict(b.__dict__);exec(src,scope)
ranked=scope["ranked_simulate"]
def run(syms,fee,funding,priority):
 scope["SYMS"]=syms
 scope["load"]=lambda sym:(raw_cache[sym],hashes[sym])
 def getevents(raw):
  sym=next(k for k,v in raw_cache.items() if v is raw)
  return {"closed":list(signals[sym].values())},None
 scope["events"]=getevents
 return ranked(fee,funding,priority=priority)
out={"description":"Continuous account, no funding; spread represented as half of quoted full spread on each side. Fee 0.08% per side or 0.08% round trip scenarios; OHLC fills without additional slippage. In-sample research.","models":{}}
for model,commission_side,spread_full in (("fee_008_each_spread_0015",.0008,.00015),("fee_008_each_spread_003",.0008,.0003),("fee_008_each_spread_004",.0008,.0004),("fee_008_roundtrip_spread_003",.0004,.0003)):
 fee=commission_side+spread_full/2
 out["models"][model]={}
 for name,syms,priority in (("four_baseline",FOUR,"baseline"),("six_baseline",SIX,"baseline"),("six_decay",SIX,"decay"),("six_combined",SIX,"combined")):
  z=run(syms,fee,0.,priority)
  out["models"][model][name]=z
  print(model,name,{k:z[k] for k in ("return_pct","max_dd_pct","daily_breach_days","total_breach","closed_trades")},flush=True)
Path("reports").mkdir(exist_ok=True)
Path("reports/deltarsi_prop_six_full_history_costs.json").write_text(json.dumps(out,indent=2))
