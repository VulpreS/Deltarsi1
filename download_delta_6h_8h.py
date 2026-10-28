import csv,datetime as dt,json,time,urllib.parse,urllib.request,sys
from pathlib import Path
TF=int(sys.argv[1]); SYMBOL=sys.argv[2].upper()
if TF not in (6,8):raise ValueError('TF must be 6 or 8')
if SYMBOL not in ('BTCUSDT','ETHUSDT','ICPUSDT','TONUSDT','BNBUSDT','ZECUSDT'):raise ValueError('Unsupported symbol')
H=TF*3600000
INTERVAL=str(TF*60)
end=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)//H*H
start=end-365*24*3600000
def request(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; research downloader)"})
 with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
def bybit():
 rows={};cursor=start
 while cursor<end:
  q=urllib.parse.urlencode(dict(category="linear",symbol=SYMBOL,interval=INTERVAL,start=cursor,end=end-1,limit=1000))
  data=request("https://api.bybit.com/v5/market/kline?"+q)
  if data.get("retCode")!=0:raise RuntimeError(str(data)[:500])
  batch=data["result"]["list"]
  if not batch:break
  for r in batch:
   t=int(r[0])
   if start<=t<end:rows[t]=[t,*[float(r[i]) for i in (1,2,3,4)]]
  newest=max(int(r[0]) for r in batch)
  if newest<cursor:raise RuntimeError("Bybit pagination stalled")
  cursor=newest+H
  print("Bybit",len(rows),"through",dt.datetime.fromtimestamp(newest/1000,dt.timezone.utc),flush=True)
  time.sleep(.12)
 return rows
def binance():
 rows={};cursor=start
 hosts=["https://fapi.binance.com","https://fapi1.binance.com","https://data-api.binance.vision","https://api.binance.com"]
 endpoint=["/fapi/v1/klines","/fapi/v1/klines","/api/v3/klines","/api/v3/klines"]
 while cursor<end:
  q=urllib.parse.urlencode(dict(symbol=SYMBOL,interval=f"{TF}h",startTime=cursor,endTime=end-1,limit=1000))
  errors=[];batch=None
  for host,path in zip(hosts,endpoint):
   try:
    batch=request(host+path+"?"+q)
    if not isinstance(batch,list):raise ValueError(str(batch)[:200])
    break
   except Exception as ex:errors.append(f"{host}: {ex}")
  if batch is None:raise RuntimeError("All Binance endpoints failed: "+"; ".join(errors))
  if not batch:break
  for r in batch:
   t=int(r[0])
   if start<=t<end:rows[t]=[t,*[float(r[i]) for i in (1,2,3,4)]]
  newest=max(int(r[0]) for r in batch)
  if newest<cursor:raise RuntimeError("Binance pagination stalled")
  cursor=newest+H
  print("Binance",len(rows),"through",dt.datetime.fromtimestamp(newest/1000,dt.timezone.utc),flush=True)
  time.sleep(.12)
 return rows
try:
 rows=bybit();source="bybit_linear"
except Exception as ex:
 print("Bybit unavailable:",repr(ex),"trying Binance fallback",flush=True)
 rows=binance();source="binance_futures_or_spot"
times=sorted(rows)
if len(times)<int(180*24/TF):raise RuntimeError(f"{SYMBOL} history shorter than 180 days")
gaps=[(a,b,(b-a)//H-1) for a,b in zip(times,times[1:]) if b-a!=H]
if gaps:
 print("GAPS",SYMBOL,"count",len(gaps),"first",gaps[:12],flush=True)
 raise RuntimeError(f"{SYMBOL} 4H OHLC gaps detected: {len(gaps)}; first={gaps[:3]}")
path=Path(f"data/{SYMBOL}_{TF}h.csv");path.parent.mkdir(exist_ok=True)
with path.open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["timestamp_utc","open","high","low","close"])
 for t in times:w.writerow([dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),*rows[t][1:]])
Path(f"data/{SYMBOL}_{TF}h_source.json").write_text(json.dumps(dict(source=source,start_ms=times[0],end_ms=times[-1],candles=len(times)),indent=2))
print("SAVED",path,len(times),"source",source,flush=True)
