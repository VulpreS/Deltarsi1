"""Deterministic as-of price-range gates, no external data."""
import unittest
from price_range_gate_audit import (FOUR, H, FEE, GATES, range_features,
                                    train_medians, split_events, summarize_opportunities)

class PriceRangeGateTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for i in range(40):
            start = i * FOUR
            close = 100 + i * .2
            self.rows.append((start, close, close + 2, close - 2, close))

    def test_4h_asof_excludes_forming_bar(self):
        t = 30 * FOUR
        a = range_features(self.rows, t)
        self.assertEqual(a["asof_last_4h_close_utc"],
                         __import__("causal_4h_parity_audit").iso(t))
        changed = list(self.rows)
        changed[30] = (30*FOUR, 1000, 2000, 1, 1000)
        self.assertEqual(a, range_features(changed, t))

    def test_boundary_4h_close_included(self):
        t = 30 * FOUR
        a = range_features(self.rows, t)
        changed = list(self.rows)
        changed[29] = (29*FOUR, 100, 200, 1, 100)
        b = range_features(changed, t)
        self.assertNotEqual(a["range6_pct"], b["range6_pct"])

    def test_no_insufficient_history(self):
        self.assertIsNone(range_features(self.rows, 23*FOUR))
        self.assertIsNotNone(range_features(self.rows, 24*FOUR))

    def test_train_only_threshold_not_affected_by_future(self):
        cut = 100 * H
        es = [{"entry_ms": 1, "price_range": {g: .1 for g in GATES}},
              {"entry_ms": 2, "price_range": {g: .3 for g in GATES}},
              {"entry_ms": cut, "price_range": {g: 100 for g in GATES}}]
        a = train_medians(es, cut)
        self.assertTrue(all(abs(a[g] - .2) < 1e-12 for g in GATES))
        es[-1]["price_range"] = {g: 10000 for g in GATES}
        self.assertEqual(a, train_medians(es, cut))

    def test_split_end_exclusive(self):
        es = [{"entry_i": i} for i in [4, 5, 6]]
        self.assertEqual([e["entry_i"] for e in split_events([], es, 5, 6)], [5])

    def test_fee_frozen(self):
        self.assertEqual(FEE, .0015)

if __name__ == "__main__":
    unittest.main()
