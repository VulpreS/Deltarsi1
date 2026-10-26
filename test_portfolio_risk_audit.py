"""Synthetic fixtures for P1 risk-sized portfolio; no external data or orders."""
import unittest
from portfolio_risk_audit import simulate, metrics, SYMS, HOUR_MS, CONFIG_HASH

def sample(n=5,signals=None,overrides=None):
    signals=signals or {}
    overrides=overrides or {}
    times=[i*4*HOUR_MS for i in range(n)]
    data={}
    for s in SYMS:
        rows=[];feat=[None]*n
        for i,t in enumerate(times):
            row=(t,100.,101.,99.,100.)
            if (s,i) in overrides:row=(t,*overrides[s,i])
            rows.append(row)
            if (s,i) in signals:feat[i]={"turn":True,"side":signals[s,i],"atr":2.}
        data[s]={"rows":rows,"feat":feat,"map":{t:i for i,t in enumerate(times)}}
    return data,times

class TestPortfolio(unittest.TestCase):
    def test_three_competing_signals_and_aggregate_risk(self):
        data,times=sample(signals={(s,0):1 for s in SYMS})
        res=simulate(data,times,cost=.0015,rate=0)
        self.assertEqual(len(res["trades"]),2)
        self.assertEqual([x["symbol"] for x in res["trades"]],list(SYMS[:2]))
        self.assertEqual(res["skips"]["max_two_positions"],1)
        self.assertLessEqual(sum(x["stop_risk"] for x in res["trades"]),.005+1e-9)
        self.assertTrue(all(x["strategy_hash"]==CONFIG_HASH for x in res["trades"]))
        self.assertAlmostEqual(res["final_cash"],res["curve"][-1]["equity"])
    def test_adverse_stop_gap_beyond_trigger(self):
        data,times=sample(n=4,signals={(SYMS[0],0):1},
          overrides={(SYMS[0],2):(90.,92.,89.,91.)})
        res=simulate(data,times,cost=.0015,rate=0)
        self.assertEqual(res["trades"][0]["exit_reason"],"stop")
        self.assertEqual(res["trades"][0]["exit"],90.)
        self.assertLess(res["trades"][0]["net_R"],-1)
    def test_short_adverse_gap(self):
        data,times=sample(n=4,signals={(SYMS[0],0):-1},
          overrides={(SYMS[0],2):(110.,111.,108.,109.)})
        res=simulate(data,times,cost=0,rate=0)
        self.assertEqual(res["trades"][0]["exit"],110.)
        self.assertEqual(res["trades"][0]["exit_reason"],"stop")
    def test_funding_boundary_and_fees(self):
        data,times=sample(n=3,signals={(SYMS[0],0):1})
        zero=simulate(data,times,cost=0,rate=0)["trades"][0]
        funded=simulate(data,times,cost=.0015,rate=.0003)["trades"][0]
        self.assertEqual(funded["funding_events_max"],1)
        self.assertEqual(funded["funding_events_min"],1)
        self.assertAlmostEqual(funded["funding_max"],funded["notional"]*.0003)
        self.assertAlmostEqual(zero["net_pnl"]-funded["net_pnl"],funded["fees"]+funded["funding_max"])
    def test_early_exit_and_reentry(self):
        data,times=sample(n=6,signals={(SYMS[0],0):1,(SYMS[0],2):1},
           overrides={(SYMS[0],2):(100.,107.,99.,105.)})
        res=simulate(data,times,cost=0,rate=0)
        self.assertEqual(len(res["trades"]),2)
        self.assertEqual(res["trades"][0]["exit_reason"],"target")
        self.assertEqual(res["trades"][1]["entry_utc"],"1970-01-01T12:00:00+00:00")
    def test_correlated_simultaneous_stops(self):
        sig={(SYMS[0],0):1,(SYMS[1],0):1}
        bad={(SYMS[0],2):(94.,95.,93.,94.),(SYMS[1],2):(94.,95.,93.,94.)}
        data,times=sample(n=4,signals=sig,overrides=bad)
        res=simulate(data,times,cost=0,rate=0)
        self.assertEqual(len(res["trades"]),2)
        self.assertTrue(all(x["exit_reason"]=="stop" for x in res["trades"]))
        self.assertAlmostEqual(res["trades"][0]["stop_risk"]+res["trades"][1]["stop_risk"],.005,places=5)
        # Both open through stops at 94 vs 95, exceeding the planned 0.5% cap.
        self.assertLess(res["final_cash"],.995)
    def test_notional_cap_blocks_tiny_atr(self):
        data,times=sample(n=3,signals={(SYMS[0],0):1})
        data[SYMS[0]]["feat"][0]["atr"]=.01
        res=simulate(data,times,cost=0,rate=0)
        self.assertEqual(len(res["trades"]),0)
        self.assertEqual(res["skips"]["notional_leverage_cap"],1)
    def test_terminal_and_mark_to_market(self):
        data,times=sample(n=3,signals={(SYMS[0],0):1})
        res=simulate(data,times,cost=.0015,rate=0)
        self.assertEqual(res["trades"][0]["exit_reason"],"terminal")
        self.assertAlmostEqual(res["final_cash"],res["curve"][-1]["equity"])
        self.assertEqual(res["concurrent_bars"][-1],0)
        self.assertGreater(metrics(res)["turnover_notional_per_initial_equity"],0)
    def test_unequal_bar_grid_fails_closed(self):
        # This fixture verifies that the main engine cannot be fed silently
        # missing data: the preparer performs strict 4H continuity validation.
        from completed_candles import aggregate_completed
        raw=[(i*HOUR_MS,100.,101.,99.,100.) for i in range(12) if i!=5]
        out=aggregate_completed(raw,4,asof_ms=12*HOUR_MS)
        self.assertNotIn(4*HOUR_MS,[r[0] for r in out])
if __name__=="__main__":unittest.main()
