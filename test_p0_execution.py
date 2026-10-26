"""P0 regression fixtures: all tests run on synthetic candles, never submit orders."""
import unittest
from execution_core import resolve_bar
from feature_walkforward import sim as feature_sim
from research_multiasset import simulate as multi_sim
from dynamic_exit_research import simulate as dynamic_sim
from structural_exit_research import sim as structure_sim

H=14_400_000
CFG=("turn","none","none",2.5,3.,12,"both")
MCFG=("turn",0,"none",2.5,3.,12,"both")

def fixture(side=1, gap=True, ambiguous=False):
    rows=[(i*H,100.,101.,99.,100.) for i in range(230)]
    feat=[None]*230
    feat[211]={"turn":True,"side":side,"atr":2.}
    if gap:
        rows[213]=(213*H,90.,92.,88.,90.) if side==1 else (213*H,110.,112.,108.,110.)
    if ambiguous:
        rows[212]=(212*H,100.,120.,90.,100.)
    sig=[(211,side,False,False,True,0,False,False,40.,2.)]
    return rows,feat,sig

class ExecutionParityTests(unittest.TestCase):
    def test_long_short_adverse_stop_gaps_across_engines(self):
        for side in (1,-1):
            with self.subTest(side=side):
                rows,feat,sig=fixture(side)
                expected=90. if side==1 else 110.
                ret=side*(expected/100.-1)-.0015
                f,_=feature_sim(rows,feat,CFG,210,230)
                m,_=multi_sim((rows,sig),MCFG,0,start=211)
                d=dynamic_sim(rows,feat,210,230,2.5,3.,"fixed",12)
                s=structure_sim(rows,feat,210,230,2.5,3.,"fixed")
                for name,got in (("feature",f),("multi",m),("dynamic",d),("structure",s)):
                    self.assertEqual(len(got),1,(name,got))
                    self.assertAlmostEqual(got[0][1],ret,places=10,msg=name)

    def test_same_bar_stop_target_stop_first(self):
        rows,feat,sig=fixture(gap=False,ambiguous=True)
        expected=-.05-.0015
        for got in (feature_sim(rows,feat,CFG,210,230)[0],
                    multi_sim((rows,sig),MCFG,0,start=211)[0],
                    dynamic_sim(rows,feat,210,230,2.5,3.,"fixed",12),
                    structure_sim(rows,feat,210,230,2.5,3.,"fixed")):
            self.assertEqual(len(got),1)
            self.assertAlmostEqual(got[0][1],expected,places=10)

    def test_target_gap_is_not_favorable_slippage(self):
        row=(0,110.,111.,109.,110.)
        self.assertEqual(resolve_bar(row,1,95.,106.),(106.,"target"))
        self.assertEqual(resolve_bar((0,90.,91.,89.,90.),-1,105.,94.),(94.,"target"))

    def test_ambiguous_gap_is_conservatively_stop_first(self):
        self.assertEqual(resolve_bar((0,110.,112.,90.,105.),1,95.,106.),(95.,"stop"))

    def test_invalid_ohlc_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_bar((0,100.,99.,98.,101.),1,95.,106.)
        with self.assertRaises(ValueError):
            resolve_bar((0,100.,101.,99.,float("nan")),1,95.,106.)

    def test_next_bar_entry_and_split_embargo(self):
        rows,feat,_=fixture(gap=False)
        self.assertEqual(feature_sim(rows,feat,CFG,210,212)[0],[])
        self.assertEqual(dynamic_sim(rows,feat,210,212,2.5,3.,"fixed",12),[])
        self.assertEqual(structure_sim(rows,feat,210,212,2.5,3.,"fixed"),[])
        # Signal-bar low must not stop an entry that starts at next open.
        rows[211]=(211*H,100.,101.,1.,100.)
        self.assertEqual(len(feature_sim(rows,feat,CFG,210,230)[0]),1)

    def test_time_exit_last_eligible_close(self):
        rows,feat,_=fixture(gap=False)
        rows[223]=(223*H,100.,105.,99.,104.)
        got=dynamic_sim(rows,feat,210,230,2.5,6.,"fixed",12)
        self.assertAlmostEqual(got[0][1],.04-.0015,places=10)

    def test_trailing_updates_only_after_close(self):
        rows,feat,_=fixture(gap=False)
        rows[212]=(212*H,100.,104.,99.,103.)
        rows[213]=(213*H,98.,100.,97.,99.)
        got=dynamic_sim(rows,feat,210,230,2.5,6.,"trail2",12)
        self.assertAlmostEqual(got[0][1],-.02-.0015,places=10)

    def test_raw_reverse_not_entry_filtered_reverse(self):
        rows,feat,_=fixture(gap=False)
        rows[213]=(213*H,100.,101.,98.,99.)
        rows[214]=(214*H,98.,101.,97.,100.)
        raw=feat.copy()
        raw[213]={"turn":True,"side":-1,"atr":2.}
        reverse=structure_sim(rows,feat,210,230,2.5,6.,"reverse",raw_features=raw)
        fixed=structure_sim(rows,feat,210,230,2.5,6.,"fixed",raw_features=raw)
        self.assertAlmostEqual(reverse[0][1],-.02-.0015,places=10)
        self.assertAlmostEqual(fixed[0][1],-.0015,places=10)

if __name__=="__main__":
    unittest.main()
