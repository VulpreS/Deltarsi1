"""Synthetic matched-exit audit invariants; no external data."""
import unittest
from matched_exit_audit import exit_one,bootstrap_delta,metric,net
from funding_timing import funding_event_count, exposure_bounds, HOUR_MS

class MatchedExitTests(unittest.TestCase):
    def rows(self):
        # timestamp, open, high, low, close; synthetic 4h candles
        step=4*3600000
        return [(i*step,100,101,99,100) for i in range(20)]

    def raw(self):
        f=[None]*20
        f[3]={"turn":True,"side":1,"atr":2.0}
        f[5]={"turn":True,"side":-1,"atr":2.0}
        return f

    def test_reverse_uses_raw_opposite_signal_next_open(self):
        rows=self.rows()
        rows[5]=(rows[5][0],100,101,99,100)
        rows[6]=(rows[6][0],99,100,98,99)
        trade={"signal_index":3,"entry_index":4,"side":1}
        fixed=exit_one(rows,self.raw(),trade,2.5,6.0,"fixed",20)
        rev=exit_one(rows,self.raw(),trade,2.5,6.0,"reverse",20)
        self.assertEqual(rev["exit_index"],6)
        self.assertEqual(rev["exit_price"],99)
        self.assertEqual(rev["reason"],"reverse")
        self.assertGreater(fixed["exit_index"],rev["exit_index"])

    def test_stop_precedes_reverse_and_gap_worse_than_stop(self):
        rows=self.rows()
        rows[4]=(rows[4][0],100,101,94,97)
        trade={"signal_index":3,"entry_index":4,"side":1}
        rev=exit_one(rows,self.raw(),trade,2.5,6.0,"reverse",20)
        self.assertEqual(rev["exit_price"],95)
        self.assertEqual(rev["reason"],"stop")
        rows[4]=(rows[4][0],100,101,99,100)
        rows[5]=(rows[5][0],94,96,93,95)
        rev=exit_one(rows,self.raw(),trade,2.5,6.0,"reverse",20)
        self.assertEqual(rev["exit_price"],94)

    def test_30d_bootstrap_requires_enough_time_blocks(self):
        rows=self.rows()
        a=[{"signal_index":3,"gross":.01,"funding_events_min":0,"funding_events_max":0}]
        b=[{"signal_index":3,"gross":.02,"funding_events_min":0,"funding_events_max":0}]
        result=bootstrap_delta(a,b,rows)
        self.assertIsNone(result["ci95_mean_delta_pct"])

    def test_fee_and_funding_adverse(self):
        trade={"gross":.03,"funding_events_min":1,"funding_events_max":2}
        self.assertAlmostEqual(net(trade,.0025,.0001),.0273)
        self.assertAlmostEqual(net(trade,.0025,.0001,"min"),.0274)
        self.assertEqual(metric([.01,-.01])["n"],2)

    def test_time_exit_duration_1_2_3_12_bars(self):
        rows=self.rows()
        trade={"signal_index":3,"entry_index":4,"side":1}
        for bars in (1,2,3,12):
            with self.subTest(bars=bars):
                t=exit_one(rows,self.raw(),trade,2.5,6.0,"fixed",4+bars)
                self.assertEqual(t["reason"],"time")
                self.assertEqual(t["hours_min"],4*bars)
                self.assertEqual(t["hours_max"],4*bars)
                self.assertEqual(t["exit_earliest_ms"],rows[4+bars-1][0]+4*HOUR_MS)
                self.assertEqual(t["funding_events_max"],bars//2)
        # Old bug returned 0h for 1-bar and 44h for 12-bar time exits.

    def test_funding_utc_boundaries_00_08_16(self):
        h=HOUR_MS
        for start in (0,8*h,16*h,24*h):
            with self.subTest(start=start):
                self.assertEqual(funding_event_count(start,start+8*h,True),1)
                self.assertEqual(funding_event_count(start,start+8*h,False),0)
                self.assertEqual(funding_event_count(start,start+8*h-1,True),0)
                self.assertEqual(funding_event_count(start,start+8*h+1,False),1)
                self.assertEqual(funding_event_count(start,start,True),0)
        self.assertEqual(exposure_bounds(0,7*h,9*h)["funding_events_min"],0)
        self.assertEqual(exposure_bounds(0,7*h,9*h)["funding_events_max"],1)
        with self.assertRaises(ValueError):
            exposure_bounds(9*h,8*h,10*h)

    def test_intrabar_funding_stop_bounds_both_sides(self):
        rows=self.rows()
        # Entry 16:00 UTC; touched stop on bar 20:00-24:00;
        # 24:00 is a funding boundary, unknown intrabar fill ordering.
        for side in (1,-1):
            with self.subTest(side=side):
                rr=list(rows)
                rr[5]=(rr[5][0],100,106 if side==-1 else 101,
                       94 if side==1 else 99,100)
                trade={"signal_index":3,"entry_index":4,"side":side}
                result=exit_one(rr,self.raw(),trade,2.5,6.0,"fixed",20)
                self.assertEqual(result["reason"],"stop")
                self.assertEqual(result["hours_min"],4)
                self.assertEqual(result["hours_max"],8)
                self.assertEqual(result["funding_events_min"],0)
                self.assertEqual(result["funding_events_max"],1)

    def test_paired_net_bootstrap_includes_funding_duration(self):
        block=30*24*HOUR_MS
        rows=[(i*block,100,101,99,100) for i in range(4)]
        fixed=[{"signal_index":i,"gross":.01,
                "funding_events_min":0,"funding_events_max":0} for i in range(4)]
        reverse=[{"signal_index":i,"gross":.02,
                  "funding_events_min":1,"funding_events_max":1} for i in range(4)]
        result=bootstrap_delta(fixed,reverse,rows,seed=42,cost=.0015,funding=.0003)
        self.assertEqual(result["calendar_blocks"],4)
        self.assertEqual(result["comparison"],"paired NET return")
        self.assertAlmostEqual(result["mean_delta_pct"],.97)
        self.assertEqual(result["ci95_mean_delta_pct"],[.97,.97])

if __name__=="__main__":unittest.main()
