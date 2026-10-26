"""One-shot cache of 4H exchange volume. Never overwrite OHLC research cache."""
import csv,datetime as dt,json,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path("data");H=3600000
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"DeltaRSIResearch/1.0"})
 with urllib.request.urlopen(req,timeout=35) as f:return json.load(f)
def main():
 for sym in ("ETHUSDT","BTCUSDT","ICPUSDT","HYPEUSDT"):
  p=ROOT/(sym+"_4h_volume.csv")
  if p.exists():print("CACHED",sym);continue
  raw=ROOT/(sym+"_1h.csv")
  with raw.open() as f: rr=list(csv.DictReader(f))
  lo=int(dt.datetime.fromisoformat(rr[0]["timestamp_utc"]).timestamp()*1000)
  hi=int(dt.datetime.fromisoformat(rr[-1]["timestamp_utc"]).timestamp()*1000)
  out={};errors=[]
  if sym!="HYPEUSDT":
   for host in ("https://data-api.binance.vision","https://api.binance.us"):
    try:
     cursor=lo
     while cursor<=hi:
      q=urllib.parse.urlencode({"symbol":sym,"interval":"4h","startTime":cursor,"endTime":hi,"limit":1000})
      b=get(host+"/api/v3/klines?"+q)
      if not b:break
      for x in b:out[int(x[0])]=float(x[5])
      cursor=int(b[-1][0])+4*H;time.sleep(.07)
     if len(out)<500:raise ValueError("Too few")
     break
    except Exception as e:errors.append(str(e));out={}
  else:
   try:
    for cursor in range(lo,hi+1,1500*4*H):
     end=min(hi,cursor+1500*4*H-4*H)
     payload=json.dumps({"type":"candleSnapshot","req":{"coin":"HYPE","interval":"4h","startTime":cursor,"endTime":end}}).encode()
     req=urllib.request.Request("https://api.hyperliquid.xyz/info",data=payload,headers={"Content-Type":"application/json"})
     with urllib.request.urlopen(req,timeout=35) as f:b=json.load(f)
     for x in b:out[int(x["t"])]=float(x["v"])
     time.sleep(.07)
   except Exception as e:errors.append(str(e))
  if len(out)<400:
   print("VOLUME_UNAVAILABLE",sym,errors,flush=True);continue
  with p.open("w",newline="") as f:
   w=csv.writer(f);w.writerow(("timestamp_ms","base_volume"))
   for t in sorted(out):w.writerow((t,out[t]))
  print("VOLUME_SAVED",sym,len(out),flush=True)
if __name__=="__main__":main()
