"""P0 cached-data integrity audit. Reads CSV only, never downloads.

Direct 4H OHLC comparison is NOT possible: repo caches only direct 4H volume.
Unknown venue provenance is reported as UNKNOWN, not inferred as verified.
"""
import csv,datetime as dt,hashlib,json,math,random,statistics
from collections import Counter
from pathlib import Path

H=3_600_000
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
def volume_above_lagged_mean(volumes,k,n=20):
    """Uses only previous n completed bars, not signal bar volume in the SMA."""
    if k<n or k>=len(volumes) or volumes[k] is None:return False
    prev=volumes[k-n:k]
    if len(prev)!=n or any(v is None or not math.isfinite(v) for v in prev):return False
    return volumes[k]>sum(prev)/n

def ms(s):
    d=dt.datetime.fromisoformat(s)
    if d.tzinfo is None or d.utcoffset()!=dt.timedelta(0):
        raise ValueError("Timestamp not UTC: "+s)
    return int(d.timestamp()*1000)

def audit(sym):
    p=Path("data")/(sym+"_1h.csv")
    with p.open() as f:raw=list(csv.DictReader(f))
    with p.open() as f:headers=next(csv.reader(f))
    t=[ms(r["timestamp_utc"]) for r in raw]
    duplicates=len(t)-len(set(t))
    missing=sum(max(0,(b-a)//H-1) for a,b in zip(t,t[1:]))
    irregular=sum(b-a!=H for a,b in zip(t,t[1:]))
    bad_ohlc=0
    for r in raw:
        o,h,l,c=[float(r[k]) for k in ("open","high","low","close")]
        if not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or h<max(o,c) or l>min(o,c):
            bad_ohlc+=1
    vpath=Path("data")/(sym+"_4h_volume.csv")
    with vpath.open() as f:vraw=list(csv.DictReader(f))
    vt=[int(x["timestamp_ms"]) for x in vraw]
    v4={int(x["timestamp_ms"]):float(x["base_volume"]) for x in vraw}
    aligned=sum(x%(4*H)==0 for x in vt)
    direct4_gaps=sum(max(0,(b-a)//(4*H)-1) for a,b in zip(vt,vt[1:]))
    result={
      "one_hour_path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
      "one_hour_fields":headers,"one_hour_count":len(raw),
      "first_utc":dt.datetime.fromtimestamp(t[0]/1000,dt.timezone.utc).isoformat(),
      "last_utc":dt.datetime.fromtimestamp(t[-1]/1000,dt.timezone.utc).isoformat(),
      "duplicate_hours":duplicates,"missing_hours":missing,
      "non_hourly_steps":irregular,"invalid_ohlc_bars":bad_ohlc,
      "four_hour_volume_path":str(vpath),
      "four_hour_volume_sha256":hashlib.sha256(vpath.read_bytes()).hexdigest(),
      "four_hour_volume_count":len(vraw),
      "four_hour_volume_utc_aligned":aligned==len(vt),
      "four_hour_volume_missing_buckets":direct4_gaps,
      "one_hour_venue":"UNKNOWN: no per-file source manifest",
      "four_hour_volume_venue":"UNKNOWN: source script has fallbacks, file does not record chosen host",
      "direct_four_hour_ohlc_parity":"NOT_TESTABLE: no direct 4H OHLC CSV in cache"}
    if "volume" in headers:
        byhour={ms(r["timestamp_utc"]):float(r["volume"]) for r in raw}
        pairs=[]
        for start,direct in v4.items():
            hours=[byhour.get(start+i*H) for i in range(4)]
            if any(x is None for x in hours):continue
            summed=sum(hours)
            if direct<=0:continue
            pairs.append((start,abs(summed-direct)/direct,summed,direct))
        sample=random.Random(20261026).sample(pairs,min(30,len(pairs)))
        rel=[x[1] for x in pairs]
        result["volume_parity"]={
          "status":"QUANTITATIVE_ONLY: does not prove matching venue without source manifest",
          "complete_4h_overlap_count":len(pairs),
          "precommitted_random_seed":20261026,
          "sample_size":len(sample),
          "sample_max_relative_error_pct":round(100*max((x[1] for x in sample),default=0),5),
          "all_median_relative_error_pct":round(100*statistics.median(rel),5) if rel else None,
          "all_max_relative_error_pct":round(100*max(rel),5) if rel else None,
          "sample_within_0_1_pct":sum(x[1]<=.001 for x in sample),
          "sample_within_1_pct":sum(x[1]<=.01 for x in sample),
          "first_3_samples":[{"utc":dt.datetime.fromtimestamp(x[0]/1000,dt.timezone.utc).isoformat(),
                               "sum_1h":round(x[2],6),"direct_4h":round(x[3],6),
                               "relative_error_pct":round(100*x[1],5)} for x in sample[:3]]}
    else:
        result["volume_parity"]={"status":"BLOCKED: 1H source has no volume field; cannot compare direct 4H volume with sum of 1H volume"}
    return result

def main():
    report={"status":"P0 CACHED OHLCV PROVENANCE AUDIT",
            "caution":"No downloads, no direct 4H OHLC cache, no signed venue manifest. Quantitative volume agreement is not proof of identical venue.",
            "symbols":{s:audit(s) for s in SYMS}}
    Path("reports/p0_cache_integrity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({s:{"missing":r["missing_hours"],"dup":r["duplicate_hours"],"bad":r["invalid_ohlc_bars"],"volume_parity":r["volume_parity"]} for s,r in report["symbols"].items()}))
if __name__=="__main__":main()
