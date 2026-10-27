"""Synthetic tests for redacted BTC execution discrepancy ledger; no network/orders."""
import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from manual_trade_discrepancy_ledger import (
    parse_msk, location, distance_pct, candidates, first_stop_touch,
    make_report, H,
)

class LedgerTests(unittest.TestCase):
    def test_msk_and_missing_date_only(self):
        self.assertEqual(parse_msk("2026-09-18 11:00").isoformat(),
                         "2026-09-18T08:00:00+00:00")
        self.assertIsNone(parse_msk("2026-09-18"))
    def test_outside_range_and_equal_boundary(self):
        b = dict(open=100., high=110., low=90., close=105.)
        self.assertEqual(location(b, 110), "inside")
        self.assertEqual(location(b, 111), "above_high")
        self.assertEqual(location(b, 89), "below_low")
        self.assertAlmostEqual(distance_pct(b, 111), 100/110)
    def test_nearby_candidate_is_not_a_fill(self):
        t = parse_msk("2026-09-18 11:00")
        b = {t + H: dict(open=100., high=105., low=95., close=100.)}
        c = candidates(b, t, 103)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["offset_hours"], 1)
    def test_static_stop_skips_entry_and_exit_hours(self):
        t = parse_msk("2026-09-18 11:00")
        b = {t: dict(low=80, high=120), t+H: dict(low=89, high=100),
             t+2*H: dict(low=90, high=110)}
        self.assertEqual(first_stop_touch(b, t, t+2*H, 90, "LONG"), t+H)
        self.assertIsNone(first_stop_touch(b, t, t+H, 90, "LONG"))
        self.assertEqual(first_stop_touch(b, t, t+2*H, 95, "SHORT"), t+H)
    def test_redaction_and_pre_cache_quality(self):
        with tempfile.TemporaryDirectory() as td:
            l, c = Path(td)/"labels.csv", Path(td)/"bars.csv"
            with l.open("w", newline="") as f:
                w=csv.writer(f)
                w.writerow(["entry_msk","entry","sl","exit1_msk","exit1",
                            "exit1_pct","exit2_msk","exit2","exit2_pct",
                            "entry_reason","exit_reason","quality"])
                w.writerow(["2026-09-18 11:00",100,90,"2026-09-18 13:00",111,100,
                            "","","","red","blue","ok"])
                w.writerow(["2025-01-01 11:00",100,110,"2025-01-02 11:00",90,50,
                            "2025-01-03",80,50,"blue","red","exit2_time_missing"])
            with c.open("w", newline="") as f:
                w=csv.writer(f);w.writerow(["timestamp_utc","open","high","low","close"])
                w.writerow(["2026-09-18T08:00:00+00:00",100,105,95,101])
                w.writerow(["2026-09-18T09:00:00+00:00",101,102,99,100])
                w.writerow(["2026-09-18T10:00:00+00:00",100,104,96,102])
            r=make_report(l,c)
            self.assertEqual(r["summary"]["n_source_trades"],2)
            self.assertEqual(r["summary"]["n_source_quality_flags"],1)
            self.assertEqual(r["summary"]["n_distinct_flagged_ledger_rows"],2)
            self.assertEqual(r["discrepancies"][1]["quality_category"],
                             "second_exit_time_incomplete")
            import json
            serialized=json.dumps(r)
            self.assertNotIn('"entry": 100',serialized)
            self.assertNotIn('"sl": 90',serialized)
            self.assertNotIn("exit2_time_missing",serialized)
if __name__ == "__main__":
    unittest.main()
