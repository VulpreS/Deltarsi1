"""Forensic delta-only entry fingerprint: manual BTC vs color transition 1h/4h.
No outcomes used to choose rules. Closed-candle, no lookahead, cached 1h only.
"""
import sys,csv,datetime as dt,json,math,statistics,bisect,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from causal_4h_parity_audit import load,H,FOUR
from analyze_mtf_5y import indicator,aggregate
from manual_trade_label_audit import normalize
OUT=Path("experiments/manual_entry_delta_fingerprint")
def iso(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).isoformat()
def median(a):return round(statistics.median(a),4) if a else None
def mode_color(x):
 if not x:return "missing"
 if x.startswith("strong"):return "bright"
 if x.startswith("medium"):return "medium"
 if x.startswith("weak"):return "weak"
 return x
def features(rows,ind,j,side):
 if j<8 or j>=len(rows):return None
 d=ind["delta"];c=ind["color"];z=d[j];p=d[j-1]
 if not all(math.isfinite(d[k]) for k in range(j-8,j+1)):return None
 expected="R" if side==1 else "B"
 sign=lambda x:1 if x>0 else -1 if x<0 else 0
 # Most recent contiguous same-color wave, including entry bar
 st=j
 while st>0 and sign(d[st-1])==sign(z):st-=1
 wave=d[st:j+1];peak=max(abs(x) for x in wave)
 # local recent fading (intensity lower than prior), turns and color transitions
 last=[abs(d[k]) for k in range(j-5,j+1)]
 prev_c=c[j-1];cur_c=c[j]
 localpeaks=sum(1 for k in range(max(st+1,j-7),j) if abs(d[k])>=abs(d[k-1]) and abs(d[k])>abs(d[k+1]))
 return dict(delta=round(z,4),prev_delta=round(p,4),color=cur_c,prev_color=prev_c,
  same_expected_sign=cur_c.endswith(expected),weak=cur_c=="weak"+expected,
  medium_to_weak=(prev_c=="medium"+expected and cur_c=="weak"+expected),
  bright_to_medium=(prev_c=="strong"+expected and cur_c=="medium"+expected),
  bright_to_weak=(prev_c=="strong"+expected and cur_c=="weak"+expected),
  just_faded=abs(z)<abs(p),fade2=abs(z)<abs(p)<abs(d[j-2]),
  weak_after_any=(cur_c=="weak"+expected and prev_c!="weak"+expected),
  after_bright_wave=any(c[k]=="strong"+expected for k in range(st,j)),
  after_bright_recent4=any(c[k]=="strong"+expected for k in range(max(st,j-4),j)),
  peak_ratio=round(abs(z)/peak,4) if peak else None,
  fade_ratio=round(abs(z)/abs(p),4) if abs(p)>0 else None,
  wave_age=j-st+1,local_peaks_8=localpeaks,
  prev3=[round(d[k],2) for k in range(j-3,j+1)],
  prev3colors=c[j-3:j+1],
  change_pct=round((abs(z)/abs(p)-1)*100,2) if abs(p)>0 else None)
def main():
 raw,_=load("BTCUSDT");h4=aggregate(raw,4);i1=indicator(raw);i4=indicator(h4)
 ht=[b[0]+FOUR for b in h4];t1=[b[0]+H for b in raw]
 with open("data/manual_btc_trades_2025_2026.csv") as f:source=list(csv.DictReader(f))
 result=[]
 for n,r in enumerate(source,1):
  z=normalize(r);ent=z["entry_ms"];rec=dict(id=n,entry_msk=r["entry_msk"],side="LONG" if z["side"]==1 else "SHORT",quality=r["quality"],reason=r["entry_reason"],issues=z["issues"])
  if ent is None or ent<t1[0] or ent>t1[-1]:
   rec["status"]="outside";result.append(rec);continue
  j1=bisect.bisect_right(t1,ent)-1;j4=bisect.bisect_right(ht,ent)-1
  rec.update(status="flagged" if z["issues"] else "in_cache",one_h=features(raw,i1,j1,z["side"]),four_h=features(h4,i4,j4,z["side"]),
    one_h_closed=iso(t1[j1]),four_h_closed=iso(ht[j4]),
    hour_since_4h_close=round((ent-ht[j4])/H,2))
  result.append(rec)
 # For any entry we compare with opportunity set at ALL 4h close times, not all hours.
 clean=[x for x in result if x["status"]=="in_cache" and x["four_h"] and x["one_h"]]
 allopp=[]
 for j in range(60,len(h4)-1):
  t=ht[j]
  if not(t1[0]<=t<=t1[-1]):continue
  for side in (1,-1):
   f=features(h4,i4,j,side)
   if f:allopp.append(dict(time=t,side=side,feat=f))
 def summarize(rr,tf):
  feats=[x[tf] for x in rr if x[tf]]
  return dict(n=len(feats),expected_sign=sum(x["same_expected_sign"] for x in feats),
    weak=sum(x["weak"] for x in feats),
    medium_to_weak=sum(x["medium_to_weak"] for x in feats),
    weak_after_any=sum(x["weak_after_any"] for x in feats),
    fading=sum(x["just_faded"] for x in feats),
    fade2=sum(x["fade2"] for x in feats),
    after_bright_wave=sum(x["after_bright_wave"] for x in feats),
    after_bright_recent4=sum(x["after_bright_recent4"] for x in feats),
    median_fade_ratio=median([x["fade_ratio"] for x in feats if x["fade_ratio"] is not None]),
    median_peak_ratio=median([x["peak_ratio"] for x in feats if x["peak_ratio"] is not None]),
    median_wave_age=median([x["wave_age"] for x in feats]),
    colors=dict(collections.Counter(x["color"] for x in feats)),
    prev_colors=dict(collections.Counter(x["prev_color"] for x in feats)))
 # Same 4h window manual selection vs all opportunities; match exact bar end
 clean4={ (int(dt.datetime.fromisoformat(x["four_h_closed"]).timestamp()*1000),1 if x["side"]=="LONG" else -1) for x in clean}
 unique_manual_at4=[x for x in allopp if (x["time"],x["side"]) in clean4]
 candidates=[x for x in allopp if x["feat"]["same_expected_sign"]]
 def stats_opp(opp):
  feats=[x["feat"] for x in opp]
  return dict(n=len(feats),weak=sum(x["weak"] for x in feats),medium_to_weak=sum(x["medium_to_weak"] for x in feats),
    fading=sum(x["just_faded"] for x in feats),fade2=sum(x["fade2"] for x in feats),
    after_bright_wave=sum(x["after_bright_wave"] for x in feats))
 # Print per-trade compact row for manual inspection.
 compact=[dict(id=x["id"],entry=x["entry_msk"],side=x["side"],h4_close=x.get("four_h_closed"),
   h4=x.get("four_h"),h1=x.get("one_h")) for x in clean]
 summary=dict(total=len(result),clean=len(clean),in_cache=sum(x["status"]=="in_cache" for x in result),
  closed1h=summarize(clean,"one_h"),closed4h=summarize(clean,"four_h"),
  four_h_opportunities=len(allopp),four_h_expected_sign_candidates=stats_opp(candidates),
  four_h_manual_same_bar=stats_opp(unique_manual_at4),
  manual_offset_hours=dict(collections.Counter(x["hour_since_4h_close"] for x in clean)),
  examples=compact)
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"result.json").write_text(json.dumps(dict(summary=summary,entries=result),ensure_ascii=False,indent=2))
 print("DELTA_FINGERPRINT_SUMMARY",json.dumps({k:v for k,v in summary.items() if k!="examples"},ensure_ascii=False))
 print("DELTA_FINGERPRINT_TRADES",json.dumps(compact,ensure_ascii=False))
if __name__=="__main__":main()
