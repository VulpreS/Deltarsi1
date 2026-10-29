"""90-day 5-minute execution experiment, 4h closed-candle signals, 8 symbols."""
import sys,io,csv,zipfile,urllib.request,datetime as dt,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from completed_candles import aggregate_completed
from experiments.pine_vs_codex.run import pine_events
from experiments.two_accounts_opposite_exit.run import OLD,NEW
from experiments.max_strategy_grid.prop_portfolio import iso
SYMS=OLD+NEW;M=300000;H=3600000;DAY=24*H;INITIAL=5000.;FEE=.00008;SPREAD=.0002;FUNDING=.00015
END=int(dt.datetime(2026,7,1,tzinfo=dt.timezone.utc).timestamp()*1000)
START=END-90*DAY;WARMUP=START-60*DAY
PARAMS=json.loads(Path("experiments/max_strategy_grid/pine_baseline_2026-10-29.json").read_text())["parameters"]
PARAMS.update({"XRPUSDT":[5.,2.5,None,None],"LINKUSDT":[5.,5.,None,None]})
def download(s):
 out=[]
 for y,m in [(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]:
  url=f"https://data.binance.vision/data/futures/um/monthly/klines/{s}/5m/{s}-5m-{y}-{m:02d}.zip"
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=120) as f:payload=f.read()
  with zipfile.ZipFile(io.BytesIO(payload)) as z:
   with z.open(z.namelist()[0]) as f:
    for line in io.TextIOWrapper(f,encoding="utf-8"):
     b=line.strip().split(",")
     try:t=int(b[0])
     except (ValueError,IndexError):continue
     if WARMUP<=t<END:out.append((t,*map(float,b[1:5])))
  print("ARCHIVE",s,y,m,len(out),flush=True)
 out.sort()
 if not out or any(b[0]-a[0]!=M for a,b in zip(out,out[1:])):raise ValueError("Missing 5m candles "+s)
 return out
def simulate(raw,signals,group,params=None,start=START,end=END,be_trigger=None,max_hold=48,exit_by_symbol=None,step=M,entry_profit_policy='defer',cap_price_stop=False,stop_cap_mode='reject',collect_trades=False):
 if entry_profit_policy not in ('defer','zero'):raise ValueError('entry_profit_policy')
 if stop_cap_mode not in ('reject','clamp'):raise ValueError('stop_cap_mode')
 if step not in (M,3*M,48*M):raise ValueError('step must be 5m, 15m or 4h')
 if exit_by_symbol is None:exit_by_symbol={}
 if params is None:params=PARAMS
 trade_details=[];cash=INITIAL;pos={};phase=1;phase_start=start;phases=[];daybase=INITIAL;day=None;qual=0;profitdays=[];peak=INITIAL;breach=None;trades=[];fees=0.;funding=0.;skipped=0;maxdd=0.;pending=False
 def equity(prices):
  return cash+sum(z["side"]*z["qty"]*(prices[s]-z["entry"])-z["qty"]*prices[s]*(FEE+SPREAD/2) for s,z in pos.items())
 for t in range(start,end,step):
  bars={s:raw[s][t] for s in group};opens={s:b[1] for s,b in bars.items()};closes={s:b[4] for s,b in bars.items()}
  if pending and not pos:
   phase+=1;phase_start=t;cash=INITIAL;peak=INITIAL;qual=0;profitdays=[];pending=False;daybase=INITIAL
  if day!=t//DAY:day=t//DAY;daybase=equity(opens)
  for s in sorted(group):
   if t not in signals[s]:continue
   if pending or s in pos or len(pos)>=3:skipped+=1;continue
   e=signals[s][t];side=e["side"];atr=e["atr_4h"];sl,tp,_,_=params[s];o=opens[s]
   stop=o-side*sl*atr;target=o+side*tp*atr
   if stop<=0 or target<=0:continue
   if cap_price_stop and abs(o-stop)/o>.05:
    if stop_cap_mode=='reject':continue
    stop=o*(1-side*.05)
   qty=1000/o;fee=1000*(FEE+SPREAD/2);cash-=fee;fees+=fee
   pos[s]=dict(side=side,qty=qty,entry=o,stop=stop,target=target,entry_t=t,phase=phase,
                  initial_stop=stop,signal_atr=atr,entry_fee=fee,raw_stop=o-side*sl*atr,
                  max_fav_move=0.,max_adverse_move=0.,stop_updates=0)
  if t%(8*H)==0:
   for s,z in pos.items():
    charge=z["qty"]*opens[s]*FUNDING;cash-=charge;funding+=charge
  # Conservative worst mark before any intrabar stop; all assets' adverse extremes simultaneous.
  adverse={s:(min(b[1],b[3]) if s in pos and pos[s]["side"]==1 else max(b[1],b[2]) if s in pos else b[4]) for s,b in bars.items()}
  worst=equity(adverse);maxdd=max(maxdd,(peak-worst)/max(peak,1)*100)
  if worst<=daybase*.95 or worst<=INITIAL*.90:
   breach=dict(time=iso(t),kind="daily" if worst<=daybase*.95 else "total",equity=round(worst,2));break
  for s in list(pos):
   z=pos[s];o,h,l,c=bars[s][1:];side=z["side"];stop=z["stop"];target=z["target"]
   if collect_trades:
    z['max_fav_move']=max(z['max_fav_move'],side*((h if side==1 else l)/z['entry']-1))
    z['max_adverse_move']=max(z['max_adverse_move'],-side*((l if side==1 else h)/z['entry']-1))
   if side*(o-stop)<=0:price=o;reason="stop_gap"
   elif side*(o-target)>=0 and (t>z['entry_t'] or entry_profit_policy=='zero'):price=o;reason="take_gap"
   elif (l<=stop if side==1 else h>=stop):price=stop;reason="stop"
   elif (h>=target if side==1 else l<=target) and (t>z['entry_t'] or entry_profit_policy=='zero'):price=target;reason="take"
   elif t-z["entry_t"]>=exit_by_symbol.get(s,{}).get('hold',max_hold)*H-step:price=c;reason="time"
   else:
    be=exit_by_symbol.get(s,{}).get('be',be_trigger)
    if be is not None and t>z["entry_t"]:
     if side*(h-z["entry"]) >=be*z["entry"] if side==1 else side*(l-z["entry"])>=be*z["entry"]:
      new_stop=max(stop,z["entry"]) if side==1 else min(stop,z["entry"])
      if new_stop!=z['stop']:z['stop_updates']+=1
      z['stop']=new_stop
    continue
   gross=side*z["qty"]*(price-z["entry"])
   if entry_profit_policy=='zero' and t==z["entry_t"] and gross>0:gross=0.;reason="60sec_legacy_zero"
   fee=z["qty"]*price*(FEE+SPREAD/2);cash+=gross-fee;fees+=fee
   trades.append(dict(symbol=s,phase=phase,pnl=round(gross-fee-1000*(FEE+SPREAD/2),5),reason=reason,entry=iso(z["entry_t"]),exit=iso(t+step)))
   if collect_trades:
    trade_details.append(dict(symbol=s,side=side,phase=phase,
      entry_ms=z['entry_t'],exit_bar_open_ms=t,exit_known_ms=t+step,
      entry_utc=iso(z['entry_t']),exit_utc=iso(t+step),
      entry_price=z['entry'],exit_price=price,initial_stop=z['initial_stop'],
      original_atr_stop=z['raw_stop'],active_stop=stop,target=z['target'],
      initial_risk_price_pct=100*abs(z['entry']-z['initial_stop'])/z['entry'],
      stop_updates=z['stop_updates'],is_breakeven_stop=reason.startswith('stop') and z['stop_updates']>0,
      reason=reason,hold_hours=(t+step-z['entry_t'])/H,
      gross_pnl_usd=gross,fees_usd=z['entry_fee']+fee,
      pnl_usd=round(gross-fee-z['entry_fee'],5),
      mfe_pct=100*z['max_fav_move'],mae_pct=100*z['max_adverse_move']))
   del pos[s]
  last=equity(closes);peak=max(peak,last)
  if last<=daybase*.95 or last<=INITIAL*.90:
   breach=dict(time=iso(t+step),kind="daily" if last<=daybase*.95 else "total",equity=round(last,2));break
  if (t+step)%DAY==0:
   pnl=last-daybase
   if pnl>0:profitdays.append(pnl)
   if phase<=2 and pnl>=INITIAL*.005:qual+=1
   if phase<=2 and not pending and not pos and last>=INITIAL*(1.05 if phase==1 else 1.08) and qual>=(3 if phase==1 else 5) and max(profitdays,default=0)<.30*(last-INITIAL):
    phases.append(dict(phase=phase,completed=iso(t+step),days=round((t+step-phase_start)/DAY,2),qualifying_days=qual,phase_equity_usd=round(last,2),phase_profit_usd=round(last-INITIAL,2)))
    pending=True
 return dict(group=group,trade_details=trade_details if collect_trades else None,phases=phases,cumulative_phase_profit_usd=round(sum(p['phase_profit_usd'] for p in phases)+(0 if pending else last-INITIAL),2),phase_now=phase,equity=round(last,2),breach=breach,max_dd_pct=round(maxdd,3),trades=len(trades),wins=sum(x['pnl']>0 for x in trades),losses=sum(x['pnl']<=0 for x in trades),win_rate_pct=round(100*sum(x['pnl']>0 for x in trades)/len(trades),2) if trades else None,profit_factor=round(sum(max(x['pnl'],0) for x in trades)/-sum(min(x['pnl'],0) for x in trades),3) if sum(x['pnl']<0 for x in trades) else None,trade_pnl_by_symbol={s:round(sum(x['pnl'] for x in trades if x['symbol']==s),2) for s in group},skipped=skipped,fees=round(fees,2),funding=round(funding,2),phase_pnl=round(last-INITIAL,2),net_pnl=round(sum(x['pnl'] for x in trades)-funding,2),funded_trades=sum(x['phase']==3 for x in trades))
def main():
 raw={};signals={}
 for s in SYMS:
  rows=download(s);raw[s]={r[0]:r for r in rows}
  hourly=[]
  for i in range(0,len(rows),12):
   chunk=rows[i:i+12]
   if len(chunk)==12 and chunk[0][0]%H==0 and chunk[-1][0]-chunk[0][0]==11*M:
    hourly.append((chunk[0][0],chunk[0][1],max(b[2] for b in chunk),min(b[3] for b in chunk),chunk[-1][4]))
  signals[s]=pine_events(hourly)
  print("DATA",s,len(rows),"4h_signals",sum(START<=t<END for t in signals[s]),flush=True)
 common=set.intersection(*(set(v) for v in raw.values()))
 if START not in common or END-M not in common or len([t for t in common if START<=t<END])!=90*288:raise ValueError("5m coverage gap")
 groups={"one_account_all":SYMS,"account_A":("BTCUSDT","ETHUSDT","TONUSDT","ZECUSDT","XRPUSDT"),"account_B":("ICPUSDT","BNBUSDT","LINKUSDT")}
 result={k:simulate(raw,signals,g) for k,g in groups.items()}
 result["notes"]=["5m OHLC execution, closed 4h signals, 90 days 2026-04-02 to 2026-06-30.","Historical Pine proxy RSI12 SMA21 EMA7, NOT user final RSI27 EMA7.","60-second rule conservatively rejects same-5m-candle positive exit; 5m OHLC cannot resolve exact seconds.","5m adverse extremes across assets simultaneous; conservative risk check.","Upscale 30% consistency, 5% daily, 10% total, funding every 8h, phase resets.","Fixed 0.02% roundtrip spread; no slippage or actual bid/ask. Not exchange-exact.","No look-ahead: signals on completed 4h candles, 5m execution."] 
 print("RESULT_5M",json.dumps(result,ensure_ascii=False),flush=True)
 Path("experiments/five_min_90d/results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
