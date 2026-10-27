"""Deterministic causal partial-4H / cost / boundary regression tests. No network."""
import datetime as dt,math,random,unittest
from analyze_mtf_5y import indicator
from completed_candles import aggregate_completed
from causal_4h_parity_audit import CausalDelta,qualifying,load,trade,events,H,FOUR,iso
def ms(s):return int(dt.datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()*1000)
class TestCausal4hParity(unittest.TestCase):
 def test_streaming_indicator_full_and_partial_exact(self):
  rng=random.Random(101)
  rows=[];price=100.
  for i in range(260):
   price=max(5,price*(1+rng.uniform(-.035,.035)))
   rows.append((i*FOUR,price,price*1.01,price*.99,price))
  st=CausalDelta()
  for i,row in enumerate(rows):
   if i>=32:
    partial=row[4]*(1+.003)
    a=st.step(partial,commit=False)
    exp=indicator(rows[:i]+[(row[0],partial,partial,partial,partial)])
    if math.isfinite(exp["delta"][-1]):
     self.assertAlmostEqual(a[0],exp["delta"][-1],places=8)
     self.assertEqual(a[1],exp["color"][-1])
   got=st.step(row[4],commit=True)
   ref=indicator(rows[:i+1])
   if math.isfinite(ref["delta"][-1]):
    self.assertAlmostEqual(got[0],ref["delta"][-1],places=8)
    self.assertEqual(got[1],ref["color"][-1])
 def test_no_partial_commit_and_future_mutation(self):
  st=CausalDelta()
  for i in range(220):st.step(100+5*math.sin(i/7),commit=True)
  prior=(len(st.closes),st.delta,st.ema,st.rolling)
  first=st.step(90.,commit=False)
  st.step(150.,commit=False)
  self.assertEqual(prior,(len(st.closes),st.delta,st.ema,st.rolling))
  self.assertEqual(first,st.step(90.,commit=False))
 def test_peak_and_sign_and_ratio(self):
  self.assertTrue(qualifying(-40,-35,-25))
  self.assertFalse(qualifying(-40,-35,-35))
  self.assertFalse(qualifying(-30,-40,-18))
  self.assertFalse(qualifying(-40,-35,10))
  self.assertFalse(qualifying(-10,-5,-2))
 def test_l3_0800_has_no_current_hour_and_0900_first_partial(self):
  raw,_=load("BTCUSDT")
  at8=ms("2026-09-18T08:00:00Z");at9=at8+H
  before=aggregate_completed([r for r in raw if r[0]+H<=at8],4,asof_ms=at8)
  after=aggregate_completed([r for r in raw if r[0]+H<=at9],4,asof_ms=at9)
  self.assertEqual(before[-1][0],at8-FOUR)
  self.assertEqual(after[-1][0],at8-FOUR)
  partial=[r for r in raw if at8<=r[0] and r[0]+H<=at9]
  self.assertEqual(len(partial),1)
  expected=indicator(before+[(at8,partial[0][1],partial[0][2],partial[0][3],partial[0][4])])
  st=CausalDelta()
  for r in before:st.step(r[4],commit=True)
  self.assertAlmostEqual(st.step(partial[0][4])[0],expected["delta"][-1],places=8)
 def test_no_entry_before_decision(self):
  raw,_=load("BTCUSDT")
  ev,_=events(raw)
  by={r[0]:i for i,r in enumerate(raw)}
  for mode in ("forming","closed","frozen_turn"):
   for e in ev[mode]:
    self.assertEqual(raw[e["entry_i"]][0],e["decision_ms"])
    self.assertGreaterEqual(e["decision_ms"],e["bucket_ms"]+H)
    if mode=="forming":self.assertLess(e["decision_ms"],e["bucket_ms"]+FOUR)
    if mode=="closed":self.assertEqual(e["decision_ms"],e["bucket_ms"]+FOUR)
    if mode!="frozen_turn":self.assertEqual(e["atr_asof_utc"],iso(e["bucket_ms"]))
 def test_symmetric_long_short_and_funding(self):
  raw=[(i*H,100,103,97,100) for i in range(80)]
  e=dict(entry_i=1,bucket_ms=0,side=1,atr_4h=1.)
  a=trade(raw,e,.0015,.0003,eq=1.)
  b=trade(raw,{**e,"side":-1},.0015,.0003,eq=1.)
  self.assertEqual(a["reason"],"stop")
  self.assertEqual(b["reason"],"stop")
  self.assertLess(a["net"],0);self.assertLess(b["net"],0)
  self.assertEqual(a["entry_i"],1)
  self.assertEqual(a["exit_i"],1)
  self.assertGreater(a["fees"],0)
  self.assertEqual(a["funding"],0)
 def test_entry_at_exact_funding_boundary_does_not_charge_immediately(self):
  raw=[(i*H,100,100.1,99.9,100) for i in range(70)]
  e=dict(entry_i=8,bucket_ms=0,side=1,atr_4h=2.)
  t=trade(raw,e,.0015,.0003)
  self.assertEqual(t["reason"],"time")
  self.assertGreater(t["funding"],0)
  self.assertAlmostEqual(t["funding"]/((t["risk_cash"]/(2.5*2))*100*.0003),6)
if __name__=="__main__":unittest.main()
