import csv,math,statistics,datetime as dt
from pathlib import Path
from analyze_mtf_5y import indicator,aggregate
P=Path('reports');P.mkdir(exist_ok=True)
with open('data/ETHUSDT_1h.csv') as f: raw=list(csv.DictReader(f))[-8760:]
r=[(int(dt.datetime.fromisoformat(x['timestamp_utc']).timestamp()*1000),*[float(x[k]) for k in ('open','high','low','close')]) for x in raw]
a=indicator(r);r4=aggregate(r,4);rd=aggregate(r,24);i4=indicator(r4);id=indicator(rd)
# Price extrema confirmed 3 candles later, never known before confirmation.
p=[]
for i in range(3,len(r)-3):
    h=all(r[i][2]>r[j][2] for j in range(i-3,i+4) if j!=i)
    l=all(r[i][3]<r[j][3] for j in range(i-3,i+4) if j!=i)
    if h!=l:p.append((i,'H' if h else 'L',r[i][2] if h else r[i][3],i+3))
peaks=[]
for x,y in zip(p,p[1:]):
    if x[1]==y[1]:continue
    v=[a['delta'][j] for j in range(x[0]+1,y[0]+1) if math.isfinite(a['delta'][j])]
    v=[z for z in v if z>0] if y[1]=='H' else [-z for z in v if z<0]
    if v:peaks.append({'type':y[1],'price':y[2],'peak':max(v),'confirm':y[3]})
state=[{'H':0,'L':0} for _ in r];age=[{'H':999,'L':999} for _ in r]
hist={'H':[],'L':[]};cur=0
for k in range(len(r)):
    while cur<len(peaks) and peaks[cur]['confirm']<=k:
        v=peaks[cur];hist[v['type']].append(v);cur+=1
    for typ in ('H','L'):
        h=hist[typ]
        if len(h)<2:continue
        more=lambda x,y:y['price']>x['price'] if typ=='H' else y['price']<x['price']
        two=more(h[-2],h[-1]) and h[-1]['peak']<h[-2]['peak']
        three=len(h)>=3 and more(h[-3],h[-1]) and more(h[-2],h[-1]) and h[-1]['peak']<h[-3]['peak']
        state[k][typ]=3 if three else (2 if two else 0)
        age[k][typ]=k-h[-1]['confirm']
def htf(k,h,series,ind):
    bucket=(r[k][0]+3600000)//(h*3600000)-1
    j=bucket-series[0][0]//(h*3600000)
    return ind['rsi'][j] if 0<=j<len(series) else math.nan
names=['early_all','late_all','early_two','late_two','early_three','late_three','early_two_htf','late_two_htf']
signals={x:{} for x in names}
for k in range(200,len(r)-122):
    prev,now=a['color'][k-1],a['color'][k]
    transitions={('strongR','mediumR'):('early',1),('mediumR','weakR'):('late',1),('strongB','mediumB'):('early',-1),('mediumB','weakB'):('late',-1)}
    if (prev,now) not in transitions:continue
    kind,side=transitions[prev,now];typ='L' if side==1 else 'H'
    w=state[k][typ] if age[k][typ]<=18 else 0
    x,y=htf(k,4,r4,i4),htf(k,24,rd,id)
    near=(x<=40 or y<=40) if side==1 else (x>=60 or y>=60)
    for n,ok in [(kind+'_all',True),(kind+'_two',w>=2),(kind+'_three',w>=3),(kind+'_two_htf',w>=2 and near)]:
        if ok:signals[n][k]=side
def simulate(sig,hold,opposite):
    result=[];k=200
    while k<len(r)-hold-2:
        if k not in sig:k+=1;continue
        side=sig[k];start=k+1;end=start+hold
        if opposite:
            for j in range(start,end):
                if sig.get(j)==-side:end=j+1;break
        entry=r[start][1];out=r[end][1]
        held=r[start:end]
        hi=max(v[2] for v in held);lo=min(v[3] for v in held)
        result.append((side*(out/entry-1)*100-0.11,((hi/entry-1)*100 if side==1 else (1-lo/entry)*100),((1-lo/entry)*100 if side==1 else (hi/entry-1)*100),end-start))
        k=end+1
    return result
def fmt(v):
    if not v:return '0 | — | — | — | — | — | —'
    wins=sum(x[0]>0 for x in v)/len(v)*100
    profit=sum(max(0,x[0]) for x in v);loss=-sum(min(0,x[0]) for x in v)
    pf=profit/loss if loss else float('inf')
    return f"{len(v)} | {wins:.1f} | {statistics.mean(x[0]):+.3f} | {pf:.2f} | {statistics.mean(x[1] for x in v):.2f} | {statistics.mean(x[2] for x in v):.2f} | {statistics.median(x[3] for x in v):.0f}"
lines=['# ETH DeltaRSI wave logic comparison','',f'Hourly candles: {len(r)}. Early = strong to medium; late = medium to weak. Two-wave: price extends and histogram weakens. Three-wave: third price extreme beyond first two; third histogram peak below first (second may be smaller). Price pivots confirmed after 3 candles; signal within 18h. 4H/1D filter RSI <=40 for LONG or >=60 for SHORT on either HTF.','', '**One open position at a time.** Entry and exit at next hourly open. Round-trip fee 0.11% (two 0.055% taker fills), no slippage/funding/stops. All figures in-sample; wave segmentation approximates visual analysis. MFE and MAE use held-bar extremes.','']
for label,hold,op in [('24h',24,False),('48h',48,False),('Opposite signal or 120h',120,True)]:
    lines+=['## '+label,'','| Variant | Trades | Win % | Mean net % | Profit factor | Mean MFE % | Mean MAE % | Median hours |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for n in names:lines.append('| '+n+' | '+fmt(simulate(signals[n],hold,op))+' |')
    lines.append('')
(P/'eth_wave_logic_comparison.md').write_text('\n'.join(lines))
print('\n'.join(lines))
