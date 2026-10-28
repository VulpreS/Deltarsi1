import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import pandas as pd
from upscale.backtest import Config,simulate
from upscale.fortnight import full_window_starts
from upscale.margin_study import run

class HorizonTests(unittest.TestCase):
    def synthetic(self):
        idx=pd.date_range('2025-01-01',periods=40*6,freq='4h',tz='UTC')
        d=pd.DataFrame(dict(open=100.,high=100.1,low=99.9,close=100.),index=idx)
        d.loc[idx.hour==20,['high','close']]=[102.1,102.]
        f=pd.DataFrame(dict(signal=(idx.hour==0).astype(int),kind='range',atr=.5,mid=100.45,exit_low=90.,exit_high=110.),index=idx)
        return d,f
    def test_later_pass_uses_thirty_day_allowance(self):
        d,f=self.synthetic()
        cfg=Config(risk=.01,portfolio_risk=.02,fee=0,slippage=0,funding=0,daily_stop=.025)
        with patch('upscale.backtest.features',return_value=f):
            short=simulate({'BTCUSDT':d},cfg,challenge=True,days=14)
            long=simulate({'BTCUSDT':d},cfg,challenge=True,days=30)
        self.assertEqual(short['summary']['outcome'],'timeout')
        self.assertEqual(short['summary']['elapsed_days'],14)
        self.assertEqual(long['summary']['outcome'],'passed')
        self.assertEqual(long['summary']['elapsed_days'],23)
        self.assertEqual(short['summary']['phase1_date'],long['summary']['phase1_date'])
    def test_thirty_day_timeout_is_exact(self):
        d,f=self.synthetic()
        cfg=Config(risk=.00001,portfolio_risk=.00002,fee=0,slippage=0,funding=0)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},cfg,challenge=True,days=30)
        self.assertEqual(r['summary']['outcome'],'timeout')
        self.assertEqual(r['summary']['elapsed_days'],30)
        self.assertEqual(len(r['daily']),30)
    def test_matched_start_dates_exclude_short_tail(self):
        idx=pd.date_range('2025-01-01 13:00',periods=3000,freq='1h',tz='UTC')
        short=full_window_starts(idx,days=14);long=full_window_starts(idx,days=30)
        self.assertTrue(long.equals(short[:len(long)]))
        self.assertLess(len(long),len(short))
        self.assertLessEqual(long[-1]+pd.Timedelta(days=30),idx[-1]+pd.Timedelta(hours=1))
    def test_invalid_horizon_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'invalid'
            with self.assertRaises(ValueError):run(p,days=0)
            self.assertFalse(p.exists())

if __name__=='__main__':unittest.main()
