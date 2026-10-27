"""Deterministic regression fixtures for exploratory pattern grid."""
import unittest
from pattern_edge_search import FEE,allowed,stop_for,one,stats,asof_features,block_ci_mean_R
H=3600000
class PatternSearchTests(unittest.TestCase):
    def ev(self,side=1,atr=2):
        return dict(entry_i=2,entry_utc="1970-01-01T02:00:00+00:00",
          symbol="SYN",mode="turn",side=side,atr_4h=atr,asof_utc="1970-01-01T02:00:00+00:00",
          peak_low=98.,peak_high=102.,wave_low=96.,wave_high=104.,
          trend50=True,trend200=False,wick_reject=False,sweep20=False)
    def test_fixed_fee_and_next_open(self):
        raw=[(i*H,100,101,99,100) for i in range(4)]
        t=one(raw,self.ev(), "atr2.5",3,1,4)
        self.assertEqual(t["entry_i"],2)
        self.assertEqual(t["exit_i"],2)
        self.assertEqual(t["exit_reason"],"time")
        self.assertAlmostEqual(t["net_pct"],-FEE*100)
    def test_stop_first_both_touched(self):
        raw=[(i*H,100,101,99,100) for i in range(4)]
        raw[2]=(2*H,100,120,90,110)
        t=one(raw,self.ev(), "atr2.5",3,2,4)
        self.assertEqual(t["exit_reason"],"stop")
        self.assertLess(t["net_R"],-1)
    def test_gap_through_stop(self):
        raw=[(i*H,100,101,99,100) for i in range(5)]
        raw[3]=(3*H,90,92,88,91)
        t=one(raw,self.ev(), "atr2.5",3,3,5)
        self.assertEqual(t["exit_i"],3)
        self.assertLess(t["net_R"],-1.9)
    def test_short_symmetric_stop(self):
        e=self.ev(-1)
        self.assertAlmostEqual(stop_for(e,100,-1,"atr2.5"),105)
        self.assertAlmostEqual(stop_for(e,100,-1,"prior_peak4h"),102.1)
        self.assertAlmostEqual(stop_for(e,100,-1,"prior_wave6x4h"),104.1)
    def test_filters_are_conjunctive(self):
        e=self.ev()
        self.assertTrue(allowed(e,"follow_ema50"))
        self.assertFalse(allowed(e,"counter_ema50"))
        self.assertFalse(allowed(e,"sweep20"))
        self.assertFalse(allowed(e,"wick_reject"))
    def test_invalid_structural_geometry(self):
        e=self.ev();e["peak_low"]=105.
        raw=[(i*H,100,101,99,100) for i in range(4)]
        self.assertIsNone(one(raw,e,"prior_peak4h",3,12,4))
    def test_calendar_block_ci(self):
        cohort=[dict(entry_utc=f"2026-0{i}-01T00:00:00+00:00",net_R=0.25) for i in (1,2,3)]
        x=block_ci_mean_R(cohort)
        self.assertEqual(x["blocks"],3)
        self.assertEqual(x["ci95_R"],[0.25,0.25])
    def test_zero_trades(self):
        self.assertEqual(stats([])["n"],0)
if __name__=="__main__":unittest.main()
