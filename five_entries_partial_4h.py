"""Causal 1H-resolution reconstruction of forming 4H DeltaRSI at five user chart entries.
At 11:00 chart UTC+3 => 08:00 UTC, no new 1H close yet.
Rebuild partial 4H OHLC after each 1H close, replacing ONLY latest incomplete 4H bar.
No final 4H indicator used for earlier observation. No orders.
"""
import csv,datetime as dt,json,math
from pathlib import Path
from analyze_mtf_5y import indicator
from completed_candles import aggregate_completed
H=3600000;FOUR=4*H
CASES=[("L1","2026-09-25 23:00",1,83982),("L2","2026-10-01 15:00",1,83897.79),("L3","2026-09-18 11:00",1,78793.30),("S1","2026-09-22 07:00",-1,85668.69),("S2","2026-10-05 15:00",-1,86192.72)]
def ts(s):return int(dt.datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
def load():
    with open("data/BTCUSDT_1h.csv") as f:
        return [(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
def observe(raw,cutoff):
    eligible=[r for r in raw if r[0]+H<=cutoff]
    completed=aggregate_completed(eligible,4,asof_ms=cutoff)
    if not completed:return None
    last=completed[-1][0]+FOUR
    partial=[r for r in eligible if last<=r[0]<last+FOUR]
    bars=list(completed)
    if partial:bars.append((last,partial[0][1],max(r[2] for r in partial),min(r[3] for r in partial),partial[-1][4]))
    ind=indicator(bars)
    out=[]
    for i in range(max(0,len(bars)-5),len(bars)):
        d=ind["delta"][i]
        out.append({"utc_4h_open":iso(bars[i][0]),"delta":round(d,2) if math.isfinite(d) else None,"color":ind["color"][i],
                    "close":round(bars[i][4],2),"completed":bars[i][0]+FOUR<=cutoff})
    return {"asof_utc":iso(cutoff),"last_complete_4h_utc":iso(completed[-1][0]),"partial_hours":len(partial),"tail":out}
def main():
    raw=load();output={"assumption":"Screenshot timezone UTC+3, exact timestamps user-marked, not proven. Hourly bars are usable only AFTER their 1h close; no intrahour observation possible.","cases":[]}
    for name,chart,side,entry in CASES:
        moment=ts(chart)-3*H
        # entry exact; surrounding hourly closes -8h to +12h
        obs=[observe(raw,moment+k*H) for k in range(-8,13)]
        obs=[o for o in obs if o]
        relevant=[r for r in raw if moment-4*H<=r[0]<=moment+8*H]
        output["cases"].append({"id":name,"side":"LONG" if side==1 else "SHORT","chart_local":chart,"entry_utc":iso(moment),
          "entry_price":entry,"observations":obs,
          "hourly_around_entry":[{"utc":iso(r[0]),"ohlc":[round(v,2) for v in r[1:]]} for r in relevant]})
    Path("reports/five_entries_partial_4h.json").write_text(json.dumps(output,indent=2,ensure_ascii=False))
    for c in output["cases"]:
        print(c["id"],c["entry_utc"])
        for o in c["observations"]:
            if o["asof_utc"] in (c["entry_utc"],iso(ts(c["chart_local"])-3*H+H),iso(ts(c["chart_local"])-3*H+2*H),iso(ts(c["chart_local"])-3*H+4*H)):
                print(" ",o["asof_utc"],o["partial_hours"],o["tail"][-1])
if __name__=="__main__":main()
