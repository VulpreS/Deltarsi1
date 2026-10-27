"""Independent funding-clock boundary fixtures; no candle network."""
import unittest
from independent_funding_clock_audit import (
    PERIOD_MS as P, HOUR_MS as H, events, bounds, hourly_bounds, check_ledger
)


class IndependentFundingClockTests(unittest.TestCase):
    def test_entry_boundary_excluded_and_exit_uncertain(self):
        self.assertEqual(events(0, 0, True), [])
        self.assertEqual(events(0, P, False), [])
        self.assertEqual(events(0, P, True), [P])
        self.assertEqual(events(P, 2*P, True), [2*P])
        self.assertEqual(bounds(0, P, P), (0, 1))

    def test_multiple_utc_events(self):
        self.assertEqual(events(4*H, 24*H, True), [8*H, 16*H, 24*H])
        self.assertEqual(bounds(4*H, 24*H, 24*H), (2, 3))

    def test_long_short_intrabar_and_exact_time(self):
        for side in (1, -1):
            for reason in ("stop", "target"):
                trade = dict(entry_ms=4*H, exit_ms=8*H, reason=reason, side=side)
                self.assertEqual(hourly_bounds(trade), (0, 1))
            trade = dict(entry_ms=4*H, exit_ms=8*H, reason="time", side=side)
            self.assertEqual(hourly_bounds(trade), (0, 1))
            trade["reason"] = "terminal"
            self.assertEqual(hourly_bounds(trade), (0, 1))

    def test_open_gap_broad_lower_bound(self):
        trade = dict(entry_ms=0, exit_ms=8*H, reason="stop")
        self.assertEqual(hourly_bounds(trade), (0, 1))
        # Gap at 08:00 could have occurred precisely at funding settlement;
        # without a gap flag the lower bound is intentionally conservative.

    def test_actual_exit_notional_fees(self):
        x = dict(quantity=2., entry_price=100., exit_price=110.,
                 gross=20., fees=.315, funding=.06, net=19.625)
        # 2*(100+110)*0.0015/2=.315; funding=200*3bp*1=.06
        check_ledger(x, 0, 1, True)
        x["fees"] = .3
        with self.assertRaises(AssertionError):
            check_ledger(x, 0, 1, True)

    def test_funding_cannot_be_derived_from_debit(self):
        x = dict(quantity=2., entry_price=100., exit_price=110.,
                 gross=20., fees=.315, funding=.06, net=19.625)
        check_ledger(x, 0, 1, True)
        x["funding"] = .12
        with self.assertRaises(AssertionError):
            check_ledger(x, 0, 1, True)

    def test_invalid_clock(self):
        with self.assertRaises(ValueError): events(10, 9, True)
        with self.assertRaises(ValueError): bounds(10, 9, 10)
        with self.assertRaises(TypeError): events(0.0, P, True)


if __name__ == "__main__":
    unittest.main()
