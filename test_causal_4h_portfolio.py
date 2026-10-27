"""Deterministic fixtures for shared-capital causal 1H portfolio execution."""
import unittest
from causal_4h_portfolio_audit import simulate,metrics,H,SYMS
def candle(t,o=100,h=101,l=99,c=100):return (t,o,h,l,c)
def event(t,side=1,a=4):
 return {"entry_ms":t,"decision_ms":t,"side":side,"atr_4h":a}
def fixture():
 data={}
 for s in SYMS:
  data[s]={"rows":{i*H:candle(i*H) for i in range(4)},
   "events":{m:{} for m in ("forming","closed","frozen_turn")}}
 return data
class PortfolioCausalTest(unittest.TestCase):
 def test_max_two_and_gap_release_before_admission(self):
  d=fixture()
  for s in SYMS:d[s]["events"]["forming"][0]=event(0)
  d["BTCUSDT"]["rows"][H]=candle(H,89,90,88,89)
  d["ICPUSDT"]["events"]["forming"][H]=event(H)
  res=simulate(d,[0,H,2*H,3*H],"forming",cost=0,rate=0)
  self.assertEqual(res["skips"].get("max_positions"),1)
  self.assertEqual(res["attempts"]["ICPUSDT"],2)
  self.assertTrue(any(x["symbol"]=="ICPUSDT" and x["entry_ms"]==H for x in res["trades"]))
  b=[x for x in res["trades"] if x["symbol"]=="BTCUSDT"][0]
  self.assertEqual(b["reason"],"stop")
  self.assertAlmostEqual(b["net"],b["risk"]*(-11/10),places=9)
 def test_intrabar_ambiguous_stop_first(self):
  d=fixture()
  d["ETHUSDT"]["events"]["closed"][0]=event(0)
  d["ETHUSDT"]["rows"][0]=candle(0,100,115,89,105)
  r=simulate(d,[0,H,2*H,3*H],"closed",0,0)
  self.assertEqual(len(r["trades"]),1)
  self.assertEqual(r["trades"][0]["reason"],"stop")
  self.assertAlmostEqual(r["trades"][0]["R"],-1)
 def test_future_signal_rejected(self):
  d=fixture()
  d["ETHUSDT"]["events"]["forming"][0]=event(H)
  with self.assertRaises(AssertionError):simulate(d,[0,H],"forming",0,0)
 def test_costs_and_funding_do_not_improve_pnl(self):
  d=fixture()
  d["BTCUSDT"]["events"]["closed"][0]=event(0)
  x=simulate(d,[0,H,2*H,3*H],"closed",0,0)
  y=simulate(d,[0,H,2*H,3*H],"closed",.004,.0003)
  self.assertLess(y["final_cash"],x["final_cash"])
 def test_window_reset_no_pre_window_entries(self):
  d=fixture()
  d["BTCUSDT"]["events"]["forming"][0]=event(0)
  x=simulate(d,[H,2*H,3*H],"forming",0,0)
  self.assertEqual(metrics(x)["n"],0)
if __name__=="__main__":unittest.main()
