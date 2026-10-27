import csv
import unittest
from pathlib import Path
from analyze_mtf_5y import indicator
from deltapulse_daily_strategy_v1 import lifecycle_candidates, stop_level
from daily_delta_percentile_window_sensitivity import load

class DailyDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=load("BTCUSDT")
        cls.ind=indicator(cls.rows)
        cls.ind["timestamps"]=[r[0] for r in cls.rows]

    def test_prefix_no_future_delta(self):
        i=650
        earlier=indicator(self.rows[:i+1])
        self.assertEqual(earlier["delta"][i],self.ind["delta"][i])
        self.assertEqual(earlier["color"][i],self.ind["color"][i])

    def test_prefix_no_future_signal(self):
        n=1250
        short={k:v[:n] for k,v in self.ind.items()}
        full,_=lifecycle_candidates(self.ind,"pulse_crest")
        prefix,_=lifecycle_candidates(short,"pulse_crest")
        a=[(e["i"],e["side"]) for e in full if e["i"]<n-2]
        b=[(e["i"],e["side"]) for e in prefix]
        self.assertEqual(a,b)

    def test_pivot_confirmed_as_of_signal(self):
        i=1100
        entry=self.rows[i+1][1]
        self.assertEqual(stop_level(self.rows,i,entry,1,"confirmed_pivot"),
                         stop_level(self.rows[:i+1],i,entry,1,"confirmed_pivot"))

    def test_daily_data_has_no_gaps(self):
        for sym in ("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"):
            p=Path("data")/(sym+"_1d_binance_um.csv")
            with p.open() as f:times=[int(x["open_ms"]) for x in csv.DictReader(f)]
            self.assertGreater(len(times),700)
            self.assertTrue(all(b-a==86400000 for a,b in zip(times,times[1:])),sym)

    def test_no_duplicate_signals_in_same_episode(self):
        events,_=lifecycle_candidates(self.ind,"pulse_crest")
        last=0;episode=0;counts={}
        episode_ids=[]
        for d in self.ind["delta"]:
            sign=1 if d>0 else -1 if d<0 else 0
            if sign!=last:episode+=1;last=sign
            episode_ids.append(episode)
        for e in events:
            ep=episode_ids[e["i"]]
            counts[ep]=counts.get(ep,0)+1
            self.assertEqual(counts[ep],1)

if __name__=="__main__":
    unittest.main()
