import csv,datetime as dt,json,time,urllib.parse,urllib.request
from pathlib import Path
H=3600000
end=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)//H*H
start=end-365*24*H
rows={}
cursor=start
while cursor<end:
 q=urllib.parse.urlencode(dict(category="linear",symbol="TONUSDT",interval="60",start=cursor,end=end-1,limit=1000))
 url="https://api.bybit.com/v5/market/kline?"+q
 req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSI-Research/1.0"})
 with urllib.request.urlopen(req,timeout=40) as response:data=json.load(response)
 if data.get("retCode")!=0:raise RuntimeError(str(data)[:500])
 batch=data["result"]["list"]
 if not batch:break
 for r in batch:
  t=int(r[0])
  if start<=t<end:rows[t]=[t,*[float(r[i]) for i in (1,2,3,4)]]
 newest=max(int(r[0]) for r in batch)
 if newest<cursor:raise RuntimeError("Pagination stalled")
 cursor=newest+H
 print("Downloaded",len(rows),"through",dt.datetime.fromtimestamp(newest/1000,dt.timezone.utc),flush=True)
 time.sleep(.15)
times=sorted(rows)
if len(times)<24*180:raise RuntimeError("TON history shorter than 180 days")
if any(b-a!=H for a,b in zip(times,times[1:])):raise RuntimeError("TON OHLC gaps detected")
path=Path("data/TONUSDT_1h.csv")
path.parent.mkdir(exist_ok=True)
with path.open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["timestamp_utc","open","high","low","close"])
 for t in times:w.writerow([dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat(),*rows[t][1:]])
print("SAVED",path,len(times),flush=True)
