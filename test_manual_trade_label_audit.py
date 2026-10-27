"""No external data, orders, or network. Deterministic label normalization fixtures."""
import unittest
from manual_trade_label_audit import parse_msk, asof_hour, normalize, stats, stop_touched_before_first, in_cache, H

def row(**kw):
    x=dict(entry_msk="2026-09-18 11:00",entry="100",sl="90",
           exit1_msk="2026-09-19 11:00",exit1="110",exit1_pct="100",
           exit2_msk="",exit2="",exit2_pct="",entry_reason="red_medium_to_weak",
           exit_reason="weak_blue",quality="ok")
    x.update(kw)
    return x

class ManualLabelTests(unittest.TestCase):
    def test_msk_utc_and_asof(self):
        ms=parse_msk("2026-09-18 11:00")
        self.assertEqual(ms,1789718400000) # 08:00 UTC
        self.assertEqual(asof_hour([ms-H,ms,ms+H],ms),0)
        self.assertEqual(asof_hour([ms,ms+H],ms),-1)

    def test_cache_boundaries_are_integer_timestamps(self):
        times=[1000,2000,3000]
        self.assertTrue(in_cache(times,1000))
        self.assertTrue(in_cache(times,3000))
        self.assertFalse(in_cache(times,999))
        self.assertFalse(in_cache(times,3001))
        self.assertFalse(in_cache(times,None))
        self.assertFalse(in_cache([],1000))

    def test_fee_and_R_long(self):
        t=normalize(row())
        self.assertEqual(t["side"],1)
        self.assertAlmostEqual(t["net_pct"],9.8425)
        self.assertAlmostEqual(t["net_R"],.98425)
        self.assertFalse(t["issues"])

    def test_short(self):
        t=normalize(row(entry="100",sl="110",exit1="90"))
        self.assertEqual(t["side"],-1)
        self.assertGreater(t["net_pct"],0)

    def test_two_stage_50_50(self):
        t=normalize(row(exit1="110",exit1_pct="50",
                        exit2="120",exit2_pct="50",
                        exit2_msk="2026-09-20 11:00"))
        self.assertAlmostEqual(t["net_pct"],14.83875)
        self.assertEqual(t["holding_hours"],36)

    def test_no_double_count_remaining(self):
        with self.assertRaises(ValueError):
            normalize(row(exit1_pct="50",exit2="120",exit2_pct="100",
                          exit2_msk="2026-09-20 11:00"))

    def test_suspect_date_not_repaired(self):
        t=normalize(row(exit1_msk="2026-02-05 23:00"))
        self.assertIn("exit_before_entry",t["issues"])

    def test_date_only_exit_flag(self):
        t=normalize(row(exit1_pct="50",exit2="120",exit2_pct="50",
                        exit2_msk="2026-09-20"))
        self.assertIn("missing_second_exit_time",t["issues"])

    def test_static_stop_chronology_excludes_ambiguous_entry_and_exit_hours(self):
        ms=parse_msk("2026-09-18 11:00")
        raw=[(ms,100,101,88,99),(ms+H,99,100,95,98),
             (ms+2*H,98,99,89,97),(ms+3*H,97,99,95,98)]
        self.assertFalse(stop_touched_before_first(raw,ms,ms+2*H,1,90))
        self.assertTrue(stop_touched_before_first(raw,ms,ms+3*H,1,90))
        self.assertFalse(stop_touched_before_first(raw,ms,ms+3*H,-1,110))

    def test_stats_one_win_one_loss(self):
        a=normalize(row())
        b=normalize(row(exit1="90"))
        s=stats([a,b])
        self.assertEqual(s["n"],2)
        self.assertEqual(s["win_pct"],50.)
        self.assertGreater(s["hypothetical_closed_trade_dd_pct"],0)

if __name__=="__main__":
    unittest.main()
