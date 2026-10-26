"""P0 chronology and fee-notional regression fixtures; cached-only, no orders."""
import unittest
from portfolio_risk_audit import simulate, resolve_open_gap, SYMS, HOUR_MS
from test_portfolio_risk_audit import sample


class TestPortfolioOpenOrdering(unittest.TestCase):
    def test_two_correlated_long_gap_stops_free_slots_for_third(self):
        signals={(SYMS[0],0):1,(SYMS[1],0):1,(SYMS[2],1):1}
        bars={(SYMS[0],2):(94.,95.,93.,94.),(SYMS[1],2):(94.,95.,93.,94.)}
        data,times=sample(n=5,signals=signals,overrides=bars)
        out=simulate(data,times,cost=.0015,rate=.0003)
        gaps=[x for x in out["trades"] if x["symbol"] in SYMS[:2]]
        self.assertEqual(len(gaps),2)
        self.assertTrue(all(x["exit_reason"]=="stop" and x["exit"]==94. for x in gaps))
        self.assertTrue(all(x["exit_utc_earliest"]=="1970-01-01T08:00:00+00:00" for x in gaps))
        entrant=next(x for x in out["trades"] if x["symbol"]==SYMS[2])
        self.assertEqual(entrant["entry_utc"],"1970-01-01T08:00:00+00:00")
        self.assertLess(entrant["equity_before"],1.)
        self.assertAlmostEqual(entrant["stop_risk"],.0025*entrant["equity_before"],places=10)
        self.assertNotIn("max_two_positions",out["skips"])

    def test_same_symbol_reentry_after_gap_stop(self):
        data,times=sample(n=5,signals={(SYMS[0],0):1,(SYMS[0],1):1},
          overrides={(SYMS[0],2):(90.,92.,89.,91.)})
        out=simulate(data,times,cost=0.,rate=0.)
        trades=[x for x in out["trades"] if x["symbol"]==SYMS[0]]
        self.assertEqual(len(trades),2)
        self.assertEqual(trades[0]["exit_utc_earliest"],trades[1]["entry_utc"])
        self.assertEqual(trades[0]["exit"],90.)
        self.assertEqual(trades[1]["entry"],90.)
        self.assertNotIn("same_symbol_open",out["skips"])

    def test_long_short_gap_stops_and_competing_third(self):
        sig={(SYMS[0],0):1,(SYMS[1],0):-1,(SYMS[2],1):1}
        bad={(SYMS[0],2):(94.,95.,93.,94.),(SYMS[1],2):(106.,107.,105.,106.)}
        data,times=sample(n=5,signals=sig,overrides=bad)
        out=simulate(data,times,cost=0.,rate=0.)
        self.assertEqual([(x["symbol"],x["exit"]) for x in out["trades"][:2]],
                         [(SYMS[0],94.),(SYMS[1],106.)])
        self.assertEqual(next(x for x in out["trades"] if x["symbol"]==SYMS[2])["entry_utc"],
                         "1970-01-01T08:00:00+00:00")

    def test_target_gap_fills_at_target_and_exit_notional_fee(self):
        sig={(SYMS[0],0):1,(SYMS[2],1):1}
        data,times=sample(n=5,signals=sig,
            overrides={(SYMS[0],2):(110.,111.,108.,110.)})
        cost=.0015
        out=simulate(data,times,cost=cost,rate=0.)
        t=next(x for x in out["trades"] if x["symbol"]==SYMS[0])
        self.assertEqual((t["exit_reason"],t["exit"]),("target",106.))
        self.assertEqual(t["exit_utc_earliest"],"1970-01-01T08:00:00+00:00")
        self.assertAlmostEqual(t["fees"],(100.+106.)*t["quantity"]*cost/2,places=12)
        self.assertAlmostEqual(t["exit_notional"],106.*t["quantity"],places=12)
        self.assertAlmostEqual(t["net_pnl"],t["gross_pnl"]-t["fees"],places=12)
        self.assertEqual(next(x for x in out["trades"] if x["symbol"]==SYMS[2])["entry_utc"],
                         "1970-01-01T08:00:00+00:00")
        self.assertAlmostEqual(out["final_cash"],out["start_cash"]+
                               sum(x["net_pnl"] for x in out["trades"]),places=10)

    def test_intrabar_low_not_available_to_open_admission(self):
        sig={(SYMS[0],0):1,(SYMS[1],0):1,(SYMS[2],1):1}
        bars={(SYMS[0],2):(100.,101.,94.,99.),
              (SYMS[1],2):(100.,101.,94.,99.)}
        data,times=sample(n=5,signals=sig,overrides=bars)
        out=simulate(data,times,cost=0.,rate=0.)
        self.assertNotIn(SYMS[2],[x["symbol"] for x in out["trades"]])
        self.assertEqual(out["skips"].get("max_two_positions"),1)
        self.assertTrue(all(x["exit_reason"]=="stop" for x in out["trades"]))

    def test_open_gap_classifier_does_not_read_intrabar(self):
        self.assertEqual(resolve_open_gap(94.,1,95.,106.),(94.,"stop"))
        self.assertEqual(resolve_open_gap(106.,-1,105.,94.),(106.,"stop"))
        self.assertEqual(resolve_open_gap(110.,1,95.,106.),(106.,"target"))
        self.assertEqual(resolve_open_gap(90.,-1,105.,94.),(94.,"target"))
        self.assertEqual(resolve_open_gap(100.,1,95.,106.),(None,None))
        self.assertEqual(resolve_open_gap(100.,-1,105.,94.),(None,None))


if __name__=="__main__":
    unittest.main()
