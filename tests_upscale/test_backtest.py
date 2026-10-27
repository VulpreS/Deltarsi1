import unittest
import pandas as pd
import numpy as np
from upscale.backtest import Config, features, simulate, adjusted_gross, consistency

class EngineTests(unittest.TestCase):
    def frame(self,n=100):
        idx=pd.date_range('2024-01-01',periods=n,freq='4h',tz='UTC')
        c=100+np.sin(np.arange(n)/3)
        return pd.DataFrame({'open':c,'high':c+1,'low':c-1,'close':c},index=idx)
    def test_features_cannot_see_current_or_future(self):
        d=self.frame(); altered=d.copy(); altered.iloc[80:]*=2
        for family in ('trend','range','mixed'):
            cfg=Config(family=family)
            pd.testing.assert_frame_equal(features(d,cfg).iloc[:81],features(altered,cfg).iloc[:81])
    def test_api_adjustment(self):
        self.assertEqual(adjusted_gross(10,59),0)
        self.assertEqual(adjusted_gross(-10,1),-10)
        self.assertEqual(adjusted_gross(10,60),10)
    def test_strict_consistency(self):
        self.assertFalse(consistency(.03,.10))
        self.assertTrue(consistency(.029,.10))
    def test_stop_before_target_and_costs(self):
        from unittest.mock import patch
        d=self.frame(4); d.loc[:,:]=[100,110,90,100]
        f=pd.DataFrame(dict(signal=[1,0,0,0],kind=['range']*4,atr=[2]*4,mid=[105]*4,exit_low=[90]*4,exit_high=[110]*4),index=d.index)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},Config())
        self.assertEqual(r['trades'][0]['reason'],'stop')
        self.assertLess(r['trades'][0]['net'],0)
        self.assertLessEqual(-r['trades'][0]['net'],.00251)
    def test_funding_only_existing_positions_at_boundary(self):
        from unittest.mock import patch
        d=self.frame(4); d.loc[:,:]=[100,100.1,99.9,100]
        f=pd.DataFrame(dict(signal=[1,0,0,0],kind=['trend']*4,atr=[2]*4,mid=[100]*4,exit_low=[90]*4,exit_high=[110]*4),index=d.index)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},Config())
        tr=r['trades'][0]
        self.assertAlmostEqual(tr['funding'], .0025/(4+100.02*(.00016+.0002))*100*.00015)
    def test_shared_leverage_cap(self):
        from unittest.mock import patch
        d=self.frame(4); d.loc[:,:]=[100,100.01,99.99,100]
        f=pd.DataFrame(dict(signal=[1]*4,kind=['trend']*4,atr=[.1]*4,mid=[100]*4,exit_low=[90]*4,exit_high=[110]*4),index=d.index)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d,'ETHUSDT':d},Config(leverage_cap=.1))
        self.assertLess(sum(-t['net'] for t in r['trades']),.001)

if __name__=='__main__': unittest.main()
