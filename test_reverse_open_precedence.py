"""P0 #14: resting-order vs pending reverse at next 4H open. No orders."""
import unittest
from unittest.mock import patch
from portfolio_risk_audit import simulate, SYMS
from test_portfolio_risk_audit import sample

class TestReverseOpenPrecedence(unittest.TestCase):
    def scenario(self,side,opening):
        eth=SYMS[1]
        # entry at bar 1; raw opposite signal at bar 2 close;
        # competing resting order and reverse at bar 3 open.
        sig={(eth,0):side,(eth,2):-side}
        high=max(100.,opening)+1.
        low=min(100.,opening)-1.
        bars={(eth,3):(opening,high,low,opening)}
        data,times=sample(n=5,signals=sig,overrides=bars)
        with patch("portfolio_risk_audit.flags",return_value={"ob_proxy":True}):
            a=simulate(data,times,variant="challenger",cost=.0015,rate=.0003)
            b=simulate(data,times,variant="challenger",cost=.0015,rate=.0003,open_precedence="market_first")
        ta=next(t for t in a["trades"] if t["entry_utc"]=="1970-01-01T04:00:00+00:00")
        tb=next(t for t in b["trades"] if t["entry_utc"]=="1970-01-01T04:00:00+00:00")
        return a,b,ta,tb

    def test_long_target_gap_precedence(self):
        a,b,ta,tb=self.scenario(1,114.)
        self.assertEqual((ta["exit_reason"],ta["exit"]),("target",112.))
        self.assertEqual((tb["exit_reason"],tb["exit"]),("raw_reverse_next_open",114.))
        self.assertEqual(len(a["pending_gap_competitions"]),1)
        self.assertLess(ta["net_pnl"],tb["net_pnl"])
        self.assertAlmostEqual(a["final_cash"],1+sum(t["net_pnl"] for t in a["trades"]))
        self.assertEqual(ta["funding_events_max"],tb["funding_events_max"])
        self.assertEqual(ta["exit_utc_earliest"],"1970-01-01T12:00:00+00:00")

    def test_short_target_gap_precedence(self):
        a,b,ta,tb=self.scenario(-1,86.)
        self.assertEqual((ta["exit_reason"],ta["exit"]),("target",88.))
        self.assertEqual((tb["exit_reason"],tb["exit"]),("raw_reverse_next_open",86.))
        self.assertLess(ta["net_pnl"],tb["net_pnl"])

    def test_long_stop_gap_precedence(self):
        a,b,ta,tb=self.scenario(1,93.)
        self.assertEqual((ta["exit_reason"],ta["exit"]),("stop",93.))
        self.assertEqual((tb["exit_reason"],tb["exit"]),("raw_reverse_next_open",93.))
        self.assertAlmostEqual(ta["net_pnl"],tb["net_pnl"])

    def test_short_stop_gap_precedence(self):
        a,b,ta,tb=self.scenario(-1,107.)
        self.assertEqual((ta["exit_reason"],ta["exit"]),("stop",107.))
        self.assertEqual((tb["exit_reason"],tb["exit"]),("raw_reverse_next_open",107.))
        self.assertAlmostEqual(ta["net_pnl"],tb["net_pnl"])

    def test_inside_band_reverse(self):
        for side in (1,-1):
            a,b,ta,tb=self.scenario(side,100.)
            self.assertEqual(ta["exit_reason"],"raw_reverse_next_open")
            self.assertEqual(ta["exit"],tb["exit"])
            self.assertEqual(a["pending_gap_competitions"],[])

    def test_two_old_positions_third_symbol_admission(self):
        eth,btc,icp=SYMS[1],SYMS[0],SYMS[2]
        sig={(eth,0):1,(btc,0):1,(eth,2):-1,(icp,2):1}
        bars={(eth,3):(114.,115.,113.,114.),(btc,3):(94.,95.,93.,94.)}
        data,times=sample(n=5,signals=sig,overrides=bars)
        with patch("portfolio_risk_audit.flags",return_value={"ob_proxy":True}):
            out=simulate(data,times,variant="challenger",cost=.0015,rate=.0003)
        exits=[t for t in out["trades"] if t["entry_utc"]=="1970-01-01T04:00:00+00:00"]
        self.assertEqual(len(exits),2)
        self.assertEqual({t["symbol"]:t["exit_reason"] for t in exits},{eth:"target",btc:"stop"})
        self.assertTrue(any(t["symbol"]==icp and t["entry_utc"]=="1970-01-01T12:00:00+00:00" for t in out["trades"]))
        self.assertAlmostEqual(out["final_cash"],1+sum(t["net_pnl"] for t in out["trades"]),places=10)

    def test_baseline_negative_control(self):
        data,times=sample(n=5,signals={(SYMS[0],0):1},
                          overrides={(SYMS[0],2):(110.,111.,109.,110.)})
        a=simulate(data,times,variant="baseline")
        b=simulate(data,times,variant="baseline",open_precedence="market_first")
        self.assertEqual(a["trades"],b["trades"])
        self.assertEqual(a["pending_gap_competitions"],[])
        self.assertEqual(b["pending_gap_competitions"],[])

    def test_invalid_precedence_fails_closed(self):
        data,times=sample(n=3)
        with self.assertRaises(ValueError):
            simulate(data,times,open_precedence="guess")

if __name__=="__main__":
    unittest.main()
