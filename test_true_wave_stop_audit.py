"""Deterministic fixtures for true causal peak/wave stops (#16)."""
import unittest
from true_wave_stop_audit import (H, FEE, wave_snapshot, stop_price,
                                  trade_one, stats)


def bar(i, low, high):
    return (i * 4 * H, 100., high, low, 100.)


class TrueWaveTests(unittest.TestCase):
    def test_long_wave_longer_than_six_and_peak_in_middle(self):
        bars = [bar(i, 95 - i, 105 + i) for i in range(10)]
        deltas = [5., -10., -20., -70., -30., -15., -9., -8., -7., 20.]
        x = wave_snapshot(bars, deltas, 9, 1, 4)
        self.assertEqual((x["start_i"], x["end_i"], x["peak_i"]), (1, 8, 3))
        self.assertEqual(x["wave_length"], 8)
        self.assertEqual(x["peak_low"], bars[3][3])
        self.assertEqual(x["wave_low"], min(b[3] for b in bars[1:9]))
        self.assertLess(stop_price(100, 1, 2, "true_whole_wave", x),
                        stop_price(100, 1, 2, "true_peak_bar", x))

    def test_short_wave_shorter_than_six_and_sign_flip(self):
        bars = [bar(i, 98 - i, 102 + i) for i in range(6)]
        deltas = [-3., 7., 20., 11., -5., -8.]
        x = wave_snapshot(bars, deltas, 4, -1, 4)
        self.assertEqual((x["start_i"], x["end_i"], x["peak_i"]), (1, 3, 2))
        self.assertEqual(x["wave_length"], 3)
        self.assertEqual(stop_price(100, -1, 2, "true_peak_bar", x), bars[2][2] + .1)
        self.assertEqual(stop_price(100, -1, 2, "true_whole_wave", x), bars[3][2] + .1)

    def test_partial_4h_never_reads_unclosed_current_bar(self):
        bars = [bar(i, 95, 105) for i in range(6)]
        deltas = [2., -12., -60., -30., 999., 5000.]
        x = wave_snapshot(bars, deltas, 4, 1, 1)
        self.assertEqual((x["start_i"], x["end_i"], x["peak_i"]), (1, 3, 2))
        changed = [*deltas]
        changed[4:] = [-9999., 0.]
        mutated = [*bars]
        mutated[4:] = [bar(4, 1, 999), bar(5, 1, 999)]
        self.assertEqual(x, wave_snapshot(mutated, changed, 4, 1, 1))

    def test_closed_4h_can_use_current_completed_bucket(self):
        bars = [bar(i, 95, 105) for i in range(5)]
        x = wave_snapshot(bars, [1., -10., -30., -90., -80.], 4, 1, 4)
        self.assertEqual(x["end_i"], 4)
        self.assertEqual(x["peak_i"], 3)

    def test_msk_l3_decision_utc_and_asof_boundary(self):
        import datetime as dt
        msk = dt.datetime(2026, 9, 18, 11, tzinfo=dt.timezone(dt.timedelta(hours=3)))
        self.assertEqual(msk.astimezone(dt.timezone.utc).hour, 8)
        # 08:00 UTC is a 4H open; no candle beginning 08:00 may be known.
        bars = [bar(i, 95, 105) for i in range(4)]
        x = wave_snapshot(bars, [1., -30., -20., -100.], 3, 1, 1)
        self.assertEqual(x["end_i"], 2)

    def test_invalid_stop_and_fee(self):
        raw = [(i*H,100.,101.,99.,100.) for i in range(5)]
        t, why = trade_one(raw, 2, 1, 101., 4)
        self.assertIsNone(t)
        self.assertEqual(why, "invalid_stop_geometry")
        t, why = trade_one(raw, 2, 1, 95., 2)
        self.assertIsNone(why)
        self.assertAlmostEqual(t["net_pct"], -FEE*100)
        self.assertAlmostEqual(t["net_R"], -FEE*100/5)

    def test_stop_first_and_adverse_gap(self):
        raw = [(i*H,100.,101.,99.,100.) for i in range(6)]
        raw[2] = (2*H,100.,120.,80.,100.)
        t, why = trade_one(raw, 2, 1, 95., 5)
        self.assertEqual(t["exit_reason"], "stop")
        self.assertEqual(t["exit"], 95.)
        raw[2] = (2*H,100.,101.,99.,100.)
        raw[3] = (3*H,90.,91.,89.,90.)
        t, why = trade_one(raw, 2, 1, 95., 5)
        self.assertEqual(t["exit_reason"], "stop")
        self.assertEqual(t["exit"], 90.)
        self.assertLess(t["net_R"], -1.9)

    def test_mutating_future_after_exit_cannot_change_trade(self):
        raw = [(i*H,100.,101.,99.,100.) for i in range(6)]
        raw[2] = (2*H,100.,120.,80.,100.)
        first, _ = trade_one(raw, 2, 1, 95., 5)
        changed = [*raw]
        changed[4] = (4*H,100.,500.,1.,100.)
        self.assertEqual(first, trade_one(changed, 2, 1, 95., 5)[0])

    def test_empty_stats(self):
        self.assertEqual(stats([])["n"], 0)


if __name__ == "__main__":
    unittest.main()
