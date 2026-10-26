"""Causal hourly execution comparison: closed 4H fade vs forming 4H fade.
Research only. Historic samples previously examined, NOT untouched holdout.
"""
import csv,datetime as dt,json,math,statistics
from pathlib import Path
from analyze_mtf_5y import indicator
from research_multiasset import atr
from execution_core import resolve_bar
H=3600000;COST=.0015
SYMS=("BTCUSDT","ETHUSDT","ICPUSDT","HYPEUSDT")
def load(sym):
 with open("data/"+sym+"_1h.csv") as f:
  return [(int(dt.datetime.fromisoformat(r["timestamp_utc"]).timestamp()*1000),*[float(r[k]) for k in ("open","high","low","close")]) for r in csv.DictReader(f)]
def events(raw):
 # Work with 4H UTC buckets; each decision at the close of an available 1H candle.
 bars=[];events=[];groups={}
 for i,r in enumerate(raw):groups.setdefault(r[0]//(4*H),[]).append((i,r))
 for key,g in sorted(groups.items()):
  if len(g)!=4 or [x[1][0] for x in g]!=[key*4*H+j*H for j in range(4)]:continue
  b=(key*4*H,g[0][1][1],max(x[1][2] for x in g),min(x[1][3] for x in g),g[-1][1][4])
  if len(bars)<210:bars.append(b);continue
  prev=indicator(bars);old=prev["delta"][-1]
  if not math.isfinite(old):bars.append(b);continue
  for h in range(1,5):
   j=g[h-1][0];subset=[x[1] for x in g[:h]]
   partial=(key*4*H,subset[0][1],max(x[2] for x in subset),min(x[3] for x in subset),subset[-1][4])
   ind=indicator(bars+[partial]);d=ind["delta"][-1];color=ind["color"][-1]
   side=1 if old<0 else -1
   if not math.isfinite(d) or side*d>=0:continue
   fade=abs(d)<abs(old)
   if not fade:continue
   # First hourly decision when fading is detected within 4H.
   # Feature thresholds are prespecified, NOT tuned to test.
   if h==1 or not any(x["bucket"]==key for x in events):
    events.append(dict(hour=j,bucket=key,side=side,ratio=abs(d)/abs(old),h=h,old=old,delta=d,
       color=color,kind="forming" if h<4 else "closed"))
  bars.append(b)
 return events
def simulate(raw,es,kind,stopmode,exitmode,ratio_max=1.0):
 # Event selection by first observed fade, one position at a time; never same-hour fills.
 # closed4h baseline: filter h=4 signals separately from full event set in caller.
 ar=atr(raw);tr=[];until=-1
 for e in es:
  i=e["hour"]+1
  if i<=until or i>=len(raw)-50 or e["ratio"]>ratio_max:continue
  side=e["side"];entry=raw[i][1]
  if stopmode=="atr":stop=entry-side*2*ar[e["hour"]]
  else:
   recent=raw[max(0,i-48):i]
   stop=(min(r[3] for r in recent) if side==1 else max(r[2] for r in recent))-side*.05*ar[e["hour"]]
  risk=side*(entry-stop)/entry
  if not .001<=risk<=.12:continue
  end=min(i+(12 if exitmode=="12h" else 48)-1,len(raw)-1)
  target=entry+side*3*(entry-stop)*side # 3R
  out=raw[end][4];ex=end;reason="time"
  for k in range(i,end+1):
   fill,why=resolve_bar(raw[k],side,stop,target)
   if why:out=fill;ex=k;reason=why;break
  ret=side*(out/entry-1)-COST
  tr.append(dict(entry=i,exit=ex,side=side,net_pct=ret*100,R=ret/risk,reason=reason))
  until=ex
 return tr
def stat(t):
 if not t:return {"n":0}
 v=[x["net_pct"] for x in t];r=[x["R"] for x in t];p=sum(max(0,x) for x in v);l=-sum(min(0,x) for x in v)
 return {"n":len(t),"win_pct":round(100*sum(x>0 for x in v)/len(v),1),"mean_net_pct":round(statistics.mean(v),3),"mean_R":round(statistics.mean(r),3),"pf":round(p/l,3) if l else None}
def main():
 out={"method":"1H closed snapshots of forming 4H; signal after 1H close, entry next 1H open; 0.15% costs; conservative stop-first; 3R TP; no funding. Data previously used for research: exploratory, not fresh holdout.","assets":{}}
 for sym in SYMS:
  raw=load(sym);all_events=events(raw)
  # closed 4H uses only fade known at h=4, recompute event subset with last snapshot
  closed=[]
  groups={}
  for i,r in enumerate(raw):groups.setdefault(r[0]//(4*H),[]).append((i,r))
  bars=[]
  for key,g in sorted(groups.items()):
   if len(g)!=4:continue
   b=(key*4*H,g[0][1][1],max(x[1][2] for x in g),min(x[1][3] for x in g),g[-1][1][4])
   if len(bars)>=210:
    ind=indicator(bars+[b]);old=ind["delta"][-2];d=ind["delta"][-1]
    if math.isfinite(old) and math.isfinite(d) and d*old>0 and abs(d)<abs(old):
     closed.append(dict(hour=g[-1][0],side=1 if d<0 else -1,ratio=abs(d)/abs(old)))
   bars.append(b)
  cases=[]
  for mode,es in (("forming_first",all_events),("closed_4h",closed)):
   for stop in ("atr","48h_swing"):
    for exitmode in ("12h","48h"):
     for filt in (1.0,.7):
      t=simulate(raw,es,mode,stop,exitmode,filt)
      n=len(raw);cuts=(0,n//2,n*3//4,n)
      segments=[stat([x for x in t if cuts[j]<=x["entry"]<cuts[j+1]]) for j in range(3)]
      cases.append(dict(mode=mode,stop=stop,exit=exitmode,fade_ratio_max=filt,all=stat(t),periods=segments))
  out["assets"][sym]={"hourly_bars":len(raw),"forming_events":len(all_events),"closed_events":len(closed),"cases":cases}
  print(sym,"events",len(all_events),len(closed),flush=True)
 Path("reports/causal_entry_exit_benchmark.json").write_text(json.dumps(out,indent=2))
 for sym,x in out["assets"].items():
  print(sym,[(z["mode"],z["stop"],z["exit"],z["fade_ratio_max"],z["all"]["n"],z["all"].get("mean_R")) for z in x["cases"]],flush=True)
if __name__=="__main__":main()
