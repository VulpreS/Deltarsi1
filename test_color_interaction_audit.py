"""Cycle 18 deterministic causal regression tests. No external calls."""
import math
import unittest
from color_interaction_audit import (
    FOUR, H, FEE, admissible, color_events, less_intense,
    one_to_one_matches, price_context, train_thresholds)
from completed_candles import aggregate_completed


class ColorInteractionTests(unittest.TestCase):
    def test_transition_exact_color_and_sign(self):
        self.assertTrue(less_intense("mediumR", "weakR", -35, -20))
        self.assertTrue(less_intense("strongB", "mediumB", 90, 70))
        self.assertFalse(less_intense("weakR", "weakR", -30, -20))
        self.assertFalse(less_intense("mediumR", "weakB", -30, 10))
        self.assertFalse(less_intense("strongB", "mediumB", 90, 95))
        self.assertFalse(less_intense("", "weakB", math.nan, 10))

    def test_sweep_reclaim_direction(self):
        bars = [(i*FOUR, 100., 103., 97., 100.) for i in range(12)]
        # SHORT current high sweeps six previous highs but closes below 103.
        bars[-1] = (11*FOUR, 100., 105., 99., 102.)
        self.assertTrue(price_context(bars, 11, -1)["sweep_reclaim"])
        self.assertFalse(price_context(bars, 11, 1)["sweep_reclaim"])
        # LONG current low sweeps previous six lows, close back above 97.
        bars[-1] = (11*FOUR, 100., 101., 95., 98.)
        self.assertTrue(price_context(bars, 11, 1)["sweep_reclaim"])
        self.assertFalse(price_context(bars, 11, -1)["sweep_reclaim"])

    def test_h1_compression_expansion_and_threshold(self):
        bars = []
        for i in range(12):
            high, low = (101., 99.) if i < 6 else (106., 94.)
            bars.append((i*FOUR, 100., high, low, 100.))
        f = price_context(bars, 11, 1)
        self.assertAlmostEqual(f["prior6_range_pct"], 2.)
        self.assertAlmostEqual(f["current6_range_pct"], 12.)
        e = {"side": 1, "price": f}
        th = {"prior6_range_pct_median": 3., "expansion_ratio_median": 1.2}
        self.assertTrue(admissible(e, "H1_LONG_expansion", th))
        self.assertFalse(admissible(e, "H2_SHORT_upper_sweep", th))
        self.assertFalse(admissible(e, "H1_LONG_expansion",
                                    dict(th, prior6_range_pct_median=1.)))

    def test_train_only_no_future_calibration(self):
        base = {"side": 1, "price": {"prior6_range_pct": 2.,
                 "expansion_ratio": 1.1}, "entry_ms": 1}
        other = {"side": 1, "price": {"prior6_range_pct": 4.,
                 "expansion_ratio": 1.4}, "entry_ms": 2}
        future = {"side": 1, "price": {"prior6_range_pct": 100.,
                 "expansion_ratio": 100.}, "entry_ms": 100}
        t = train_thresholds([base, other, future], 100)
        self.assertAlmostEqual(t["prior6_range_pct_median"], 3.)
        self.assertAlmostEqual(t["expansion_ratio_median"], 1.25)
        future["price"] = {"prior6_range_pct": 9999., "expansion_ratio": 9999.}
        self.assertEqual(t, train_thresholds([base, other, future], 100))

    def test_many_to_one_manual_matches_are_not_double_counted(self):
        e = [{"event_id": "A", "side": 1, "entry_ms": 10*H},
             {"event_id": "B", "side": 1, "entry_ms": 12*H},
             {"event_id": "C", "side": -1, "entry_ms": 10*H}]
        labels = [{"row_id": "T001", "side": 1, "entry_ms": 10*H},
                  {"row_id": "T002", "side": 1, "entry_ms": 11*H},
                  {"row_id": "T003", "side": -1, "entry_ms": 10*H}]
        matched, s = one_to_one_matches(e, labels)
        self.assertEqual(s["labels_matched"], 3)
        self.assertEqual(len(set(x["label_id"] for x in matched.values())), 3)
        self.assertEqual(matched["A"]["label_id"], "T001")
        self.assertEqual(matched["C"]["label_id"], "T003")
        self.assertGreater(s["duplicate_edges_discarded"], 0)

    @staticmethod
    def synthetic():
        raw = []
        for i in range(1200):
            price = 100+9*math.sin(i/27)+3*math.sin(i/8)+.01*i
            raw.append((i*H, price, price+1.5, price-1.5, price))
        return raw

    def test_closed_4h_asof_and_future_mutation(self):
        raw = self.synthetic()
        bars = aggregate_completed(raw, 4, asof_ms=raw[-1][0]+H)
        es, _ = color_events(raw, bars)
        self.assertGreater(len(es), 0, "Synthetic oscillation should produce color fades")
        e = es[0]
        t = e["decision_ms"]
        self.assertEqual(e["entry_ms"], t)
        self.assertEqual(e["last_known_1h_close_utc"], e["decision_utc"])
        self.assertEqual(e["price"]["feature_source_last_4h_close_utc"], e["decision_utc"])
        changed = list(raw)
        for i, b in enumerate(changed):
            if b[0] > t:
                changed[i] = (b[0], b[1]*10, b[2]*10, b[3]*10, b[4]*10)
        es2, _ = color_events(changed)
        old = next(x for x in es if x["event_id"] == e["event_id"])
        new = next(x for x in es2 if x["event_id"] == e["event_id"])
        self.assertEqual(old, new)

    def test_4h_close_boundary_requires_all_four_hours(self):
        raw = self.synthetic()
        t = 260*FOUR
        before = aggregate_completed(raw, 4, asof_ms=t-1)
        after = aggregate_completed(raw, 4, asof_ms=t)
        self.assertEqual(before[-1][0], 258*FOUR)
        self.assertEqual(after[-1][0], 259*FOUR)

    def test_fee_frozen_and_no_orders(self):
        self.assertEqual(FEE, .0015)


if __name__ == "__main__":
    unittest.main()
