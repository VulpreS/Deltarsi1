import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from upscale.backtest import Config,simulate
from upscale.fortnight import full_window_starts,aggregate

class FortnightTests(unittest.TestCase):
    def synthetic(self,days=20):
        idx=pd.date_range('2025-01-01',periods=days*6,freq='4h',tz='UTC')
        d=pd.DataFrame(dict(open=100.,high=100.1,low=99.9,close=100.),index=idx)
        # One daily entry; known target reached only at end of UTC day.
        d.loc[idx.hour==20,['high','close']]=[102.1,102.]
        f=pd.DataFrame(dict(signal=(idx.hour==0).astype(int),kind='range',atr=.5,mid=102.,exit_low=90.,exit_high=110.),index=idx)
        return d,f
    def test_both_stages_can_pass_and_reset(self):
        d,f=self.synthetic()
        cfg=Config(risk=.01,portfolio_risk=.02,fee=0,slippage=0,funding=0,daily_stop=.025)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},cfg,challenge=True,days=14)
        s=r['summary']
        import json
        json.dumps(r,allow_nan=False)
        self.assertEqual(s['outcome'],'passed')
        self.assertEqual(s['elapsed_days'],9)
        self.assertEqual([p['phase'] for p in s['completed_phases']],[1,2])
        self.assertEqual([p['profit_days'] for p in s['completed_phases']],[4,5])
        self.assertEqual(len(r['daily']),9)
        self.assertTrue(all(p['best_day_share']<.3 for p in s['completed_phases']))
    def test_exactly_fourteen_days_total(self):
        d,f=self.synthetic()
        cfg=Config(risk=.00001,portfolio_risk=.00002,fee=0,slippage=0,funding=0)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},cfg,challenge=True)
        self.assertEqual(r['summary']['outcome'],'timeout')
        self.assertEqual(r['summary']['elapsed_days'],14)
        self.assertEqual(len(r['daily']),14)
    def test_floating_daily_loss_breaches_before_recovery(self):
        d,f=self.synthetic(2)
        # High risk test deliberately disables internal daily guard; hard prop rule remains.
        d.iloc[0]=[100,100.1,100,100]
        d.iloc[1]=[100,100.1,94,100]
        f.loc[:,'signal']=0; f.iloc[0,f.columns.get_loc('signal')]=1
        f.loc[:,'atr']=10.; f.loc[:,'mid']=120.
        cfg=Config(risk=.1,portfolio_risk=.1,fee=0,slippage=0,funding=0,daily_stop=.9)
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},cfg,challenge=True)
        # Notional=.1/15; a 6-point drop is only 4%, so use deeper intrabar low.
        d.iloc[1,d.columns.get_loc('low')]=91.
        with patch('upscale.backtest.features',return_value=f):
            r=simulate({'BTCUSDT':d},cfg,challenge=True)
        self.assertEqual(r['summary']['outcome'],'failed')
        self.assertEqual(r['summary']['breach'],'daily')
    def test_no_incomplete_windows_and_utc_start(self):
        idx=pd.date_range('2025-01-01 13:00',periods=1000,freq='1h',tz='UTC')
        starts=full_window_starts(idx)
        self.assertTrue(len(starts)>0)
        self.assertTrue(all(t.hour==0 for t in starts))
        self.assertGreaterEqual(starts[0],idx[60])
        self.assertLessEqual(starts[-1]+pd.Timedelta(days=14),idx[-1]+pd.Timedelta(hours=1))
    def test_failures_not_counted_as_timeouts(self):
        rows=[dict(outcome=k,phase1_date=None,elapsed_days=14,return_pct=0,worst_day_pct=-1,max_drawdown_pct=1) for k in ['passed','failed','timeout']]
        s=aggregate(rows)
        self.assertEqual((s['passed'],s['failed'],s['timed_out']),(1,1,1))

if __name__=='__main__': unittest.main()
