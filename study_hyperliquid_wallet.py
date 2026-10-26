"""Read-only Hyperliquid wallet study. Public fills + 1h/4h/1d candles."""
import csv,json,time,urllib.request,datetime as dt
from collections import defaultdict
from pathlib import Path
API="https://api.hyperliquid.xyz/info"
WALLET="0x62b6CF6f399911ABDd132e57C5C5e11604974A81".lower()
ROOT=Path("wallet_study")
ROOT.mkdir(exist_ok=True)
def query(payload):
    req=urllib.request.Request(API,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","User-Agent":"DeltaRSIResearch/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
def save_csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
def main():
    # The API exposes up to 10,000 latest fills, 2,000 per request.
    recent=query({"type":"userFills","user":WALLET,"aggregateByTime":False})
    if not recent:
        raise RuntimeError("No fills found. Verify wallet is the trading account, not agent wallet.")
    first=min(int(x["time"]) for x in recent)
    fills={}
    # Start before the earliest of the recent 2000 fills, walking back as far as API permits.
    # userFillsByTime only supports forward pagination; start 2023 to include available 10k.
    start=int(dt.datetime(2023,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
    while True:
        page=query({"type":"userFillsByTime","user":WALLET,"startTime":start,"aggregateByTime":False})
        if not page:break
        for x in page:fills[str(x.get("tid",x.get("hash","")))+":"+str(x["time"])]=x
        last=max(int(x["time"]) for x in page)
        if last<start:break
        start=last+1
        if len(page)<1900 or len(fills)>=10000:break
        time.sleep(.2)
    if not fills:
        fills={str(i):x for i,x in enumerate(recent)}
    fills=sorted(fills.values(),key=lambda x:int(x["time"]))
    (ROOT/"fills_raw.json").write_text(json.dumps(fills,ensure_ascii=False,indent=2))
    flat=[]
    bycoin=defaultdict(list)
    for x in fills:
        coin=x["coin"]
        bycoin[coin].append(x)
        flat.append({k:x.get(k,"") for k in ("coin","time","side","dir","px","sz","startPosition","closedPnl","fee","feeToken","crossed","oid","tid","hash")})
    save_csv(ROOT/"fills.csv",flat)
    summary=["# Hyperliquid wallet: factual trade history","","Wallet: "+WALLET,
             f"Retrieved fills: {len(fills)}; coins: {len(bycoin)}.",
             "Fills are executions, not independent trades. Closed PnL is realized PnL per execution.",
             "Recent history is limited by Hyperliquid API to 10,000 fills.","",
             "| Coin | Fills | First UTC | Last UTC | Sum closed PnL (USDC) | Fees |",
             "|---|---:|---|---|---:|---:|"]
    for coin,items in sorted(bycoin.items(),key=lambda t:len(t[1]),reverse=True):
        start_t=min(int(x["time"]) for x in items)
        end_t=max(int(x["time"]) for x in items)
        def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        pnl=sum(float(x.get("closedPnl") or 0) for x in items)
        fee=sum(float(x.get("fee") or 0) for x in items)
        summary.append(f"| {coin} | {len(items)} | {iso(start_t)} | {iso(end_t)} | {pnl:.2f} | {fee:.2f} |")
        if coin.startswith("@"):
            summary.append(f"Note: {coin} is a spot identifier; no perp candle download.")
            continue
        for interval,ms in (("1h",3600000),("4h",14400000),("1d",86400000)):
            # 100 bars before first execution, 30 after last. Max 4500 per request.
            cursor=start_t-100*ms
            end=min(int(time.time()*1000),end_t+30*ms)
            candles={}
            while cursor<end:
                to=min(end,cursor+4000*ms)
                data=query({"type":"candleSnapshot","req":{"coin":coin,"interval":interval,"startTime":cursor,"endTime":to}})
                for bar in data:candles[int(bar["t"])]=bar
                cursor=to+ms
                time.sleep(.12)
            rows=[{"time_utc":iso(t),"timestamp_ms":t,"open":bar["o"],"high":bar["h"],"low":bar["l"],"close":bar["c"],"volume":bar["v"],"trades":bar.get("n","")} for t,bar in sorted(candles.items())]
            save_csv(ROOT/(coin.replace(":","_")+"_"+interval+".csv"),rows)
            summary.append(f"  - {coin} {interval}: {len(rows)} candles.")
    summary+=["","## Analysis caveats","",
       "Real liquidation heatmaps and historical stop/TP orders are NOT included in public fills.",
       "Execution sequence, partial closes, scaling and realized PnL can be studied; motivations and intended liquidity targets require charts or user's annotations.",
       "Funding is not included in realized fill PnL above.",
       "Historical candles are bounded by Hyperliquid's available candle window (latest 5000 per interval)."]
    (ROOT/"summary.md").write_text("\n".join(summary)+"\n",encoding="utf8")
    print("\n".join(summary[:15]))
if __name__=="__main__":main()
