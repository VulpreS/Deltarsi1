"""P0 standalone/portfolio parity fixtures: classification and exact fill checks."""
import unittest
from standalone_parity_audit import (
    key, portfolio_ledger, classify_portfolio_only, classify_standalone_only, reconcile
)
import datetime as dt

def ts(h):
    return int(dt.datetime(2026,1,1,h,tzinfo=dt.timezone.utc).timestamp()*1000)

class ParityFixtures(unittest.TestCase):
    def test_cross_asset_key_collision_fails_closed(self):
        rows=[{"symbol":"BTCUSDT","signal_utc":"x","side":"LONG"},
              {"symbol":"ETHUSDT","signal_utc":"x","side":"LONG"}]
        with self.assertRaisesRegex(ValueError,"partition by symbol"):
            portfolio_ledger(rows)
    def test_key(self):
        self.assertEqual(key("2026-01-01T00:00:00+00:00",1),
                         ("2026-01-01T00:00:00+00:00","LONG"))
    def test_standalone_exit_bar_cooldown(self):
        st={("x","LONG"):{"entry_index":2,"exit_index":5}}
        self.assertEqual(classify_portfolio_only({"signal_index":5},st),
                         "standalone_position_or_exit_bar_cooldown")
        self.assertEqual(classify_portfolio_only({"signal_index":6},st),
                         "unexplained_portfolio_only")
    def test_open_exit_releases_slot(self):
        st={"entry_utc":"2026-01-01T04:00:00+00:00"}
        pt={"x":{"entry_utc":"2026-01-01T00:00:00+00:00",
                 "exit_utc_earliest":"2026-01-01T04:00:00+00:00",
                 "exit_utc_latest":"2026-01-01T04:00:00+00:00"}}
        self.assertEqual(classify_standalone_only(st,pt),"portfolio_other_or_cap")
    def test_intrabar_exit_cannot_free_slot_at_open(self):
        st={"entry_utc":"2026-01-01T04:00:00+00:00"}
        pt={"x":{"entry_utc":"2026-01-01T00:00:00+00:00",
                 "exit_utc_earliest":"2026-01-01T04:00:00+00:00",
                 "exit_utc_latest":"2026-01-01T08:00:00+00:00"}}
        self.assertEqual(classify_standalone_only(st,pt),"portfolio_existing_position")
    def test_existing_position_blocks(self):
        st={"entry_utc":"2026-01-01T04:00:00+00:00"}
        pt={"x":{"entry_utc":"2026-01-01T00:00:00+00:00",
                 "exit_utc_earliest":"2026-01-01T08:00:00+00:00"}}
        self.assertEqual(classify_standalone_only(st,pt),"portfolio_existing_position")
    def test_matched_fill_parity(self):
        a="2026-01-01T00:00:00+00:00";b="2026-01-01T04:00:00+00:00"
        rows=[(ts(0),100,101,99,100),(ts(4),100,101,99,100)]
        st={(a,"LONG"):{"signal_index":0,"entry_index":1,"exit_index":1,
              "entry_utc":b,"exit_utc":b,"exit_reason":"stop",
              "gross_return":-.01,"side":1}}
        pt={(a,"LONG"):{"signal_utc":a,"entry_utc":b,"exit_utc_earliest":b,
              "side":"LONG","entry":100,"exit":99,"exit_reason":"stop"}}
        self.assertEqual(reconcile(rows,st,pt)["matched_economic_discrepancy_n"],0)
        pt[(a,"LONG")]["exit"]=98
        self.assertEqual(reconcile(rows,st,pt)["matched_economic_discrepancy_n"],1)

if __name__=="__main__":unittest.main()
