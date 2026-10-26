"""Generate deterministic 4H DeltaRSI exhaustion alerts from locally cached hourly candles.
No live prices, orders, credentials, or execution. Only report the latest completed 4H bar.
"""
import csv,datetime as dt,json,math,sys
from pathlib import Path
from analyze_mtf_5y import indicator
from completed_candles import aggregate_completed_4h as _strict_completed_4h
from research_multiasset import atr
SYMS=("ETHUSDT","BTCUSDT","ICPUSDT","HYPEUSDT")
HOUR_MS=3_600_000

def aggregate_completed_4h(raw, now_ms=None):
    """Paper alerts only use fully closed UTC 4H bars as of wall-clock time."""
    if now_ms is None:
        now_ms=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)
    return _strict_completed_4h(raw, asof_ms=now_ms)

def main():
    alerts=[]
    for sym in SYMS:
        path=Path("data")/(sym+"_1h.csv")
        if not path.exists():continue
        with path.open() as f:xs=list(csv.DictReader(f))
        raw=[(int(dt.datetime.fromisoformat(x["timestamp_utc"]).timestamp()*1000),*[float(x[k]) for k in ("open","high","low","close")]) for x in xs]
        rows=aggregate_completed_4h(raw);i=len(rows)-1
        if i<70:continue
        d=indicator(rows)["delta"];v=atr(rows)[i]
        side=1 if d[i]<0 else -1
        signal=math.isfinite(d[i-2]) and d[i]*d[i-1]>0 and abs(d[i])<abs(d[i-1]) and abs(d[i-1])>=abs(d[i-2]) and abs(d[i-1])>=15
        signal_time=dt.datetime.fromtimestamp(rows[i][0]/1000,dt.timezone.utc)
        alert={"symbol":sym,"timeframe":"4h","last_closed_bar_start_utc":signal_time.isoformat(),"last_closed_bar_end_utc":(signal_time+dt.timedelta(hours=4)).isoformat(),"signal":"LONG" if signal and side==1 else ("SHORT" if signal else "NONE"),"delta":round(d[i],3),"atr14":round(v,5),"status":"RESEARCH_ONLY" if sym=="HYPEUSDT" else "PAPER_ONLY","entry":"NEXT_4H_OPEN_NOT_YET_KNOWN","stop_distance":round(2.5*v,5),"target_distance":round(3*v,5),"time_exit_bars":12}
        alerts.append(alert)
    print(json.dumps({"warning":"Historical cached data only. Do not execute stale signals.","alerts":alerts},indent=2))
if __name__=="__main__":main()
