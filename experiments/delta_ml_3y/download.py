"""Download 3 years of 4h OHLCV from Bybit public API; archive per symbol."""
import json,time,datetime as dt,urllib.request, pathlib,sys
SYMS=("BTCUSDT","ETHUSDT","TONUSDT","BNBUSDT","XRPUSDT","LINKUSDT")
START=int(dt.datetime(2023,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
END=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
CUT=int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()*1000)
OUT=pathlib.Path("experiments/delta_ml_3y/data");OUT.mkdir(parents=True,exist_ok=True)
def fetch(sym,end):
 url="https://api.bybit.com/v5/market/kline?category=linear&symbol=%s&interval=240&limit=1000&end=%d"%(sym,end)
 for attempt in range(7):
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"delta-ml-research/1.0"})
   with urllib.request.urlopen(req,timeout=35) as f:payload=json.load(f)
   if payload.get("retCode")!=0:raise RuntimeError(str(payload)[:300])
   return payload["result"]["list"]
  except Exception as exc:
   if attempt==6:raise
   time.sleep(2**attempt)
for sym in SYMS:
 records={};cursor=END-1
 while cursor>=START:
  page=fetch(sym,cursor)
  if not page:break
  oldest=cursor
  for row in page:
   t=int(row[0]);oldest=min(oldest,t)
   if START<=t<END:records[t]=[t,*[float(v) for v in row[1:6]]]
  print(sym,"page",len(page),"total",len(records),flush=True)
  if oldest>=cursor:break
  cursor=oldest-1
  time.sleep(.12)
 rows=[records[t] for t in sorted(records)]
 train=sum(x[0]<CUT for x in rows);test=len(rows)-train
 (OUT/(sym+".json")).write_text(json.dumps(rows,separators=(",",":")))
 print("DATA_SUMMARY",json.dumps({"symbol":sym,"rows":len(rows),"train":train,"test":test,"first":rows[0][0] if rows else None,"last":rows[-1][0] if rows else None}),flush=True)
 if len(rows)<1500:raise RuntimeError("Insufficient data for "+sym)
