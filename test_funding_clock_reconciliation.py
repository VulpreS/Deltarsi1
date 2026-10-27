"""Synthetic deterministic checks for P0 #12 funding-clock reconciliation."""
import copy
import unittest

from funding_clock_reconciliation import RATE, event_count_1h, reconcile
from funding_timing import exposure_bounds, HOUR_MS


def fixture():
    entry = "1970-01-01T00:00:00+00:00"
    old_trade = {
        "symbol":"BTCUSDT","entry_utc":entry,"side":"LONG",
        "exit_reason":"time","entry":100.,"exit":101.,
        "exit_utc_earliest":"1970-01-01T16:00:00+00:00",
        "exit_utc_latest":"1970-01-01T16:00:00+00:00",
        "quantity":.1,"notional":10.,"gross_pnl":.1,"fees":.015,
        "funding_events_max":2,"funding_max":.006,"net_pnl":.079
    }
    new_trade = {
        "symbol":"BTCUSDT","entry_ms":0,"exit_ms":16*HOUR_MS,
        "side":1,"reason":"time","entry_price":100.,"exit_price":101.,
        "quantity":.1,"gross":.1,"fees":.015,"funding":.003,"net":.082
    }
    oldgrid={};newgrid={}
    for cost in (15,25,40):
        for f in (0,1,3):
            oldgrid[f"{cost}bp_fee_{f}bp_funding"]={
                "n":1,"net_return_pct":7.9,"net_pf":2.,
                "max_close_to_close_mtm_dd_pct":1.}
            newgrid[f"{cost}bp_cost_{f}bp_funding"]={
                "n":1,"net_return_pct":8.2,"pf":2.1,
                "max_hourly_close_mtm_dd_pct":.9}
    old={"source_hashes":{"BTCUSDT":"abc"},"strategy_hash":"old",
         "full_common_history":{"baseline":{"trades":[old_trade],
         "metrics":{"net_return_pct":7.9},"stress_grid":oldgrid}}}
    new={"source_sha256":{"BTCUSDT":"abc"},"config_sha256":"new",
         "full":{"frozen_turn":{"primary_trade_ledger":[new_trade],
         "primary":{"net_return_pct":8.2},"stress":newgrid}}}
    return old,new


class FundingClockTest(unittest.TestCase):
    def test_exact_accounting_and_event_decomposition(self):
        old,new=fixture()
        r=reconcile(old,new)
        self.assertEqual(r["matched_trade_ids"],1)
        self.assertEqual(r["event_counts"]["4h_more"],1)
        self.assertEqual(r["event_counts"]["1h_more"],0)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["timing_funding_delta"],.003)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["sizing_funding_delta"],0.)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["net_delta"],-.003)
        self.assertEqual(len(r["cost_funding_grid"]),9)

    def test_compounded_size_decomposition(self):
        old,new=fixture()
        x=new["full"]["frozen_turn"]["primary_trade_ledger"][0]
        x["quantity"]=.08
        x["gross"]=.08
        x["fees"]=.012
        x["funding"]=.0024
        x["net"]=.0656
        new["full"]["frozen_turn"]["primary"]["net_return_pct"]=6.56
        r=reconcile(old,new)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["timing_funding_delta"],.003)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["sizing_funding_delta"],.0006)
        self.assertAlmostEqual(r["sum_4h_minus_1h"]["funding_delta"],.0036)

    def test_fail_closed_on_different_fill(self):
        old,new=fixture()
        new["full"]["frozen_turn"]["primary_trade_ledger"][0]["exit_price"]=102.
        with self.assertRaises(AssertionError):reconcile(old,new)

    def test_fail_closed_on_source_or_trade_id_mismatch(self):
        old,new=fixture()
        new["source_sha256"]["BTCUSDT"]="different"
        with self.assertRaises(AssertionError):reconcile(old,new)
        old,new=fixture()
        new["full"]["frozen_turn"]["primary_trade_ledger"][0]["entry_ms"]=HOUR_MS
        with self.assertRaises(AssertionError):reconcile(old,new)

    def test_fail_closed_on_fractional_event_count(self):
        _,new=fixture()
        x=new["full"]["frozen_turn"]["primary_trade_ledger"][0]
        x["funding"]*=1.5
        with self.assertRaises(AssertionError):event_count_1h(x)

    def test_utc_8h_boundary_upper_vs_lower(self):
        self.assertEqual(exposure_bounds(0,7*HOUR_MS,8*HOUR_MS)["funding_events_max"],1)
        self.assertEqual(exposure_bounds(0,7*HOUR_MS,7*HOUR_MS)["funding_events_max"],0)
        self.assertEqual(exposure_bounds(0,8*HOUR_MS,8*HOUR_MS)["funding_events_min"],0)


if __name__=="__main__":
    unittest.main()
