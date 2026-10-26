"""Synthetic matched-exit audit invariants; no external data."""
import unittest
from matched_exit_audit import exit_one,bootstrap_delta,metric,net

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
        rows[4]=(rows[4][0],94,96,93,95)
        rev=exit_one(rows,self.raw(),trade,2.5,6.0,"reverse",20)
        self.assertEqual(rev["exit_price"],94)

    def test_30d_bootstrap_requires_enough_time_blocks(self):
        rows=self.rows()
        a=[{"signal_index":3,"gross":.01}]
        b=[{"signal_index":3,"gross":.02}]
        result=bootstrap_delta(a,b,rows)
        self.assertIsNone(result["ci95_mean_delta_pct"])

    def test_fee_and_funding_adverse(self):
        trade={"gross":.03,"hours":12}
        self.assertAlmostEqual(net(trade,.0025,.0001),.0273)
        self.assertEqual(metric([.01,-.01])["n"],2)

if __name__=="__main__":unittest.main()
