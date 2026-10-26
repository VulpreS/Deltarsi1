"""Prevent future-period leakage in cached DeltaRSI backtests."""
import unittest
from feature_walkforward import sim as feature_sim
from research_multiasset import simulate as multiasset_simulate

CFG_FEATURE=("turn","none","none",2.5,3.0,12,"both")
CFG_MULTI=("turn",0,"none",2.5,3.0,12,"both")

class ChronologicalBoundaryTests(unittest.TestCase):
    def test_no_entry_outside_feature_split(self):
        rows=[(i*14_400_000,100.,100.1,99.9,100.) for i in range(230)]
        feats=[None]*230
        feats[218]={"turn":True,"side":1,"atr":1.}
        trades,_=feature_sim(rows,feats,CFG_FEATURE,210,219)
        self.assertEqual(trades,[], "Signal on last split bar enters next split")

    def test_training_embargo_and_independent_holdout(self):
        rows=[(i*14_400_000,100.,100.1,99.9,100.) for i in range(130)]
        def signal(k):
            return (k,1,False,False,True,0,False,False,40.,1.)
        data=(rows,[signal(98),signal(101)])
        train,_=multiasset_simulate(data,CFG_MULTI,100)
        test,_=multiasset_simulate(data,CFG_MULTI,0,start=100)
        self.assertEqual(train,[], "Training PnL must not consume post-cut candles")
        self.assertEqual(len(test),1)
        self.assertEqual(test[0][0],101)

if __name__=="__main__":
    unittest.main()
