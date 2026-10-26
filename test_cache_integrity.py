"""P0 regression: lagged 4H volume mean excludes the current signal bar."""
import unittest
from cache_integrity_audit import volume_above_lagged_mean

class LaggedVolumeTests(unittest.TestCase):
    def test_excludes_signal_and_uses_full_prior_window(self):
        v=[100.]+[1.]*19+[2.]
        # Correct prior 20 average=5.95; buggy current-included window
        # would drop the 100 and give 1.05, producing a false signal.
        self.assertFalse(volume_above_lagged_mean(v,20,20))
        v[0]=1.
        self.assertTrue(volume_above_lagged_mean(v,20,20))

    def test_rejects_missing_or_short_history(self):
        self.assertFalse(volume_above_lagged_mean([1.]*20,19,20))
        v=[1.]*21;v[7]=None
        self.assertFalse(volume_above_lagged_mean(v,20,20))
        v[7]=1.;v[20]=None
        self.assertFalse(volume_above_lagged_mean(v,20,20))

if __name__=="__main__":
    unittest.main()
