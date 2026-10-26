"""P0 #7 synthetic regression fixtures: complete as-of aggregation, no network."""
import unittest
import math
from completed_candles import HOUR_MS, aggregate_completed_4h, aggregate_completed
from analyze_mtf_5y import aggregate, indicator
from paper_signal_4h import aggregate_completed_4h as paper_aggregate
from research_multiasset import atr

H=HOUR_MS
def raw(start=0,n=16):
    return [(t*H,100.+t,101.+t,99.+t,100.+t) for t in range(start,start+n)]

class StrictCandleTests(unittest.TestCase):
    def test_first_partial_1_2_3_and_complete_4(self):
        for first in (1,2,3):
            with self.subTest(first=first):
                self.assertEqual(aggregate_completed_4h(raw(4-first,first),4*H),[])
        self.assertEqual(len(aggregate_completed_4h(raw(0,4),4*H)),1)

    def test_partial_first_does_not_poison_later_complete(self):
        a=raw(1,7) # 01/02/03 partial, 04/05/06/07 full
        got=aggregate_completed_4h(a,8*H)
        self.assertEqual([x[0] for x in got],[4*H])

    def test_missing_interior_hour_discards_only_its_bucket(self):
        a=[x for x in raw(0,12) if x[0]!=5*H]
        self.assertEqual([x[0] for x in aggregate_completed_4h(a,12*H)],[0,8*H])

    def test_duplicate_and_nonmonotonic_rejected(self):
        for a in (raw(0,2)+raw(1,2), list(reversed(raw(0,4)))):
            with self.assertRaises(ValueError):
                aggregate_completed_4h(a,8*H)

    def test_last_complete_vs_incomplete_and_asof(self):
        self.assertEqual([x[0] for x in aggregate_completed_4h(raw(0,8),8*H)],[0,4*H])
        self.assertEqual([x[0] for x in aggregate_completed_4h(raw(0,7),8*H)],[0])
        self.assertEqual([x[0] for x in aggregate_completed_4h(raw(0,8),8*H-1)],[0])
        self.assertEqual([x[0] for x in aggregate_completed_4h(raw(0,8),8*H+1)],[0,4*H])

    def test_last_source_hour_must_close(self):
        self.assertEqual(aggregate_completed_4h(raw(0,4),4*H-1),[])
        self.assertEqual(len(aggregate_completed_4h(raw(0,4),4*H)),1)

    def test_utc_boundaries_and_day_boundary(self):
        a=raw(0,28)
        self.assertEqual([x[0]//H for x in aggregate_completed_4h(a,28*H)],[0,4,8,12,16,20,24])
        self.assertEqual([x[0]//H for x in aggregate_completed(a,24,24*H)],[0])

    def test_paper_historical_parity_at_same_asof(self):
        a=[]
        for i in range(4*230):
            close=100+8*math.sin(i/9)
            a.append((i*H,close,close+1,close-1,close))
        asof=4*230*H
        research=aggregate(a,4,asof_ms=asof)
        paper=paper_aggregate(a,now_ms=asof)
        self.assertEqual(research,paper)
        self.assertEqual(indicator(research)["color"],indicator(paper)["color"])
        self.assertAlmostEqual(indicator(research)["delta"][-1],indicator(paper)["delta"][-1])
        self.assertAlmostEqual(atr(research)[-1],atr(paper)[-1])

    def test_invalid_bar_rejected(self):
        a=raw(0,4);a[1]=(H,100.,90.,110.,100.)
        with self.assertRaises(ValueError):aggregate_completed_4h(a,4*H)

if __name__=="__main__":
    unittest.main()
