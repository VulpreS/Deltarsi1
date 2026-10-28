import unittest
import numpy as np
import pandas as pd
from upscale.rsi_histogram import indicator,pine_colors,journal_signal,prepare
from upscale.backtest import Config,simulate

class HistogramTests(unittest.TestCase):
    def hourly(self,n=1400):
        idx=pd.date_range('2025-01-01',periods=n,freq='1h',tz='UTC')
        x=np.arange(n);c=100+8*np.sin(x/31)+2*np.sin(x/7)
        return pd.DataFrame(dict(open=c,high=c+.5,low=c-.5,close=c),index=idx)
    def test_original_indicator_parity(self):
        from analyze_mtf_5y import indicator as reference
        d=self.hourly().iloc[:800]
        bars=[(int(t.timestamp()*1000),*map(float,row)) for t,row in zip(d.index,d.to_numpy())]
        a=indicator(d);b=reference(bars)
        np.testing.assert_allclose(a.rsi.to_numpy(),b['rsi'],atol=1e-8,rtol=1e-8,equal_nan=True)
        np.testing.assert_allclose(a.delta.to_numpy(),b['delta'],atol=1e-6,rtol=1e-8,equal_nan=True)
    def test_four_actual_pine_intensities_and_equal_gray(self):
        colors=pine_colors([50,70,65,55,40,40,45,-70,-65,-40])
        self.assertEqual(colors[1:7],['strongB','mediumB','weakB','weakB','gray','faintB'])
        self.assertEqual(colors[7:],['strongR','mediumR','weakR'])
    def test_journal_entry_rules_no_repeated_weak(self):
        self.assertEqual(journal_signal('mediumR','weakR'),1)
        self.assertEqual(journal_signal('faintR','weakR'),1)
        self.assertEqual(journal_signal('strongB','weakB'),-1)
        self.assertEqual(journal_signal('weakB','weakB'),0)
        self.assertEqual(journal_signal('weakR','weakR'),0)
    def test_future_mutation_including_forming_bucket_is_invisible(self):
        d=self.hourly();b=d.copy();cut=d.index[1000];b.loc[cut:]*=2
        a,_,_=prepare(d);z,_,_=prepare(b)
        pd.testing.assert_frame_equal(a.loc[:cut],z.loc[:cut])
    def test_only_closed_four_hour_decisions_and_known_stops(self):
        d=self.hourly();f,_,bars=prepare(d)
        active=f[f.signal!=0]
        self.assertGreater(len(active),0)
        self.assertTrue(all(t.hour%4==0 for t in active.index))
        self.assertTrue(all(pd.Timestamp(row.stop_source_time)<=t for t,row in active.iterrows()))
        partial=d.iloc[1:]
        _,_,b=prepare(partial)
        self.assertNotIn(d.index[0],b.index)
    def test_long_only_preserves_unfiltered_exit(self):
        d=self.hourly();a,_,_=prepare(d);b,_,_=prepare(d,long_only=True)
        self.assertTrue((b.signal>=0).all())
        pd.testing.assert_series_equal(a.reverse_signal,b.reverse_signal)
        self.assertTrue((b.reverse_signal<0).any())
    def test_structural_stop_and_reverse_exit_have_no_24h_timeout(self):
        d=self.hourly(50);d.loc[:,:]=[100,100.01,99.99,100]
        f=pd.DataFrame(dict(signal=0,reverse_signal=0,kind='delta',atr=10.,mid=np.nan,exit_low=np.nan,exit_high=np.nan,stop_price=np.nan),index=d.index)
        f.loc[d.index[0],['signal','stop_price']]=[1,99.]
        f.loc[d.index[30],'reverse_signal']=-1
        cfg=Config(sizing_mode='margin',margin_fraction=.1,position_leverage=3,leverage_cap=3,portfolio_risk=.04,fee=0,slippage=0,funding=0)
        r=simulate({'BTCUSDT':d},cfg,prepared_features={'BTCUSDT':f})
        self.assertEqual(len(r['trades']),1)
        t=r['trades'][0]
        self.assertEqual(t['stop'],99.)
        self.assertEqual(t['exit_time'],str(d.index[30]))
        self.assertAlmostEqual(t['planned_loss_pct'],.3)

if __name__=='__main__':unittest.main()
