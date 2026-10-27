"""Regression checks: 4H DeltaPulse data integrity and causality.

No live exchange calls, no orders. Runs entirely on cached repo 4H OHLC.
"""
import csv
import math
import unittest
from pathlib import Path

from analyze_mtf_5y import indicator
from deltapulse_4h_archive import STARTS,H4,read_cache
from deltapulse_4h_strategy_v1 import candidates,initial_stop,replay,WARMUP

class FourHourDeltaPulseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=read_cache("BTCUSDT")
        assert len(cls.rows)>10000
        cls.ind=indicator(cls.rows)

    def test_archives_no_gaps(self):
        for asset in STARTS:
            r=read_cache(asset)
            self.assertGreater(len(r),1000)
            self.assertTrue(all(x[0]%H4==0 for x in r),asset)
            self.assertTrue(all(y[0]-x[0]==H4 for x,y in zip(r,r[1:])),asset)
            self.assertTrue(all(row[1]>0 and row[3]<=min(row[1],row[4]) and
                                row[2]>=max(row[1],row[4]) for row in r),asset)

    def test_indicator_uses_closed_prefix_only(self):
        k=610
        short=indicator(self.rows[:k+1])
        for key in ("delta","rsi","color"):
            self.assertEqual(short[key][-1],self.ind[key][k])

    def test_crest_selection_no_future_leakage(self):
        cut=3500
        before={k:v[:cut] for k,v in self.ind.items()}
        all_events,_=candidates(self.ind,"crest",60,.8)
        prefix,_=candidates(before,"crest",60,.8)
        ref=[(x["i"],x["side"],x["peak_i"]) for x in all_events if x["i"]<cut-2]
        got=[(x["i"],x["side"],x["peak_i"]) for x in prefix]
        self.assertEqual(ref,got)

    def test_one_crest_per_signed_episode(self):
        events,_=candidates(self.ind,"crest",60,.8)
        seen=set();episode=0;previous=0;ids=[]
        for value in self.ind["delta"]:
            signed=1 if value>0 else -1 if value<0 else 0
            if signed!=previous:
                episode+=1;previous=signed
            ids.append(episode)
        for e in events:
            self.assertNotIn(ids[e["i"]],seen)
            seen.add(ids[e["i"]])

    def test_stop_never_depends_on_future_bars(self):
        k=1000;price=self.rows[k+1][1]
        for side in (1,-1):
            for mode in ("confirmed_pivot","recent_6bar_extreme"):
                a=initial_stop(self.rows,k,price,side,mode)
                b=initial_stop(self.rows[:k+1],k,price,side,mode)
                self.assertEqual(a,b)

    def test_trade_log_has_causal_entry_times_and_accounting(self):
        p=Path("reports/deltapulse_4h_v1_primary_trades.csv")
        with p.open() as f:trades=list(csv.DictReader(f))
        self.assertGreater(len(trades),150)
        for t in trades:
            self.assertLessEqual(t["signal_time"],t["entry_time"])
            self.assertLessEqual(t["entry_time"],t["exit_time"])
            side=1 if t["direction"]=="LONG" else -1
            op=float(t["entry_price"]);exitprice=float(t["exit_price"])
            result=100*(side*(exitprice/op-1)-.0015)
            self.assertAlmostEqual(float(t["net_pct"]),result,delta=.003)
            self.assertGreater(float(t["initial_risk_pct"]),0)
            self.assertLessEqual(float(t["initial_risk_pct"]),15)

if __name__=="__main__":
    unittest.main()
