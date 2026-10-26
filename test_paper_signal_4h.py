"""Regression tests for the cached, order-free 4H signal aggregator."""
import unittest
from paper_signal_4h import aggregate_completed_4h, HOUR_MS

class CompletedCandleTests(unittest.TestCase):
    def setUp(self):
        self.raw=[(i*HOUR_MS,100.+i,101.+i,99.+i,100.5+i) for i in range(80)]

    def test_complete_tail_is_retained(self):
        bars=aggregate_completed_4h(self.raw,now_ms=80*HOUR_MS)
        self.assertEqual(len(bars),20)
        self.assertEqual(bars[-1][0],76*HOUR_MS)
        self.assertEqual(bars[-1][4],79.5+100)

    def test_incomplete_tail_is_rejected(self):
        bars=aggregate_completed_4h(self.raw[:-1],now_ms=80*HOUR_MS)
        self.assertEqual(len(bars),19)

    def test_still_open_hour_is_not_closed(self):
        bars=aggregate_completed_4h(self.raw,now_ms=79*HOUR_MS+HOUR_MS//2)
        self.assertEqual(len(bars),19)

    def test_new_partial_bucket_does_not_hide_previous_complete(self):
        raw=self.raw+[(80*HOUR_MS,180.,181.,179.,180.5)]
        bars=aggregate_completed_4h(raw,now_ms=81*HOUR_MS)
        self.assertEqual(len(bars),20)
        self.assertEqual(bars[-1][0],76*HOUR_MS)

if __name__=="__main__":
    unittest.main()
