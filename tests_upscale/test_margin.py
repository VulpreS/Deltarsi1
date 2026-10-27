import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from upscale.backtest import Config,simulate

class MarginTests(unittest.TestCase):
    def data(self,atr=1.):
        idx=pd.date_range('2025-01-01',periods=4,freq='4h',tz='UTC')
        d=pd.DataFrame(dict(open=100.,high=100.1,low=99.9,close=100.),index=idx)
        f=pd.DataFrame(dict(signal=[1,0,0,0],kind='trend',atr=atr,mid=100.,exit_low=90.,exit_high=110.),index=idx)
        return d,f
    def result(self,margin=.1,leverage=3.,atr=1.,symbols=('BTCUSDT',),**kwargs):
        d,f=self.data(atr)
        cfg=Config(sizing_mode='margin',margin_fraction=margin,position_leverage=leverage,leverage_cap=3.,fee=0.,slippage=0.,funding=0.,portfolio_risk=.04,daily_stop=.025,**kwargs)
        with patch('upscale.backtest.features',return_value=f):
            return simulate({s:d for s in symbols},cfg)
    def test_margin_and_notional_exact(self):
        for margin in (.1,.15):
            for leverage in (1.,2.,3.):
                r=self.result(margin,leverage);t=r['trades'][0]
                self.assertAlmostEqual(t['entry_margin']/t['entry_equity'],margin)
                self.assertAlmostEqual(t['entry_notional']/t['entry_margin'],leverage)
    def test_tighter_stop_does_not_inflate_position(self):
        a=self.result(atr=.5)['trades'][0];b=self.result(atr=2.)['trades'][0]
        self.assertEqual(a['entry_notional'],b['entry_notional'])
        self.assertLess(a['planned_loss_pct'],b['planned_loss_pct'])
    def test_stops_over_five_percent_rejected(self):
        r=self.result(atr=3.)
        self.assertEqual(r['trades'],[])
        self.assertEqual(r['summary']['rejected_stop_cap'],1)
    def test_stop_exactly_five_percent_accepted(self):
        t=self.result(margin=.15,atr=2.5)['trades'][0]
        self.assertAlmostEqual(t['planned_stop_pct'],.05)
        self.assertAlmostEqual(t['planned_loss_pct'],2.25)
    def test_portfolio_budget_skips_second_not_resizes(self):
        r=self.result(margin=.15,atr=2.5,symbols=('BTCUSDT','ETHUSDT'))
        self.assertEqual(len(r['trades']),1)
        self.assertAlmostEqual(r['trades'][0]['entry_margin'],.15)
        self.assertEqual(r['summary']['rejected_budget'],1)
    def test_leverage_cannot_exceed_cap(self):
        with self.assertRaises(ValueError): Config(sizing_mode='margin',position_leverage=4,leverage_cap=3)

if __name__=='__main__':unittest.main()
