"""Run the established annual 4h DeltaRSI 117-ladder research at exactly 15%.

Scenario only: $750 notional on initial $5000, max 3 concurrent trades.
The previously agreed 17.5%/$875 scenario and its historical results remain
unchanged. No change to signals, fees, exits, or optimization windows.
"""
import os
os.environ["DELTA_POSITION_NOTIONAL"]="750"
os.environ["DELTA_OUTPUT_DIR"]="experiments/five_min_90d/partial_annual_15pct"
from experiments.five_min_90d.optimize_partial_take_4h import main
if __name__=="__main__":
 main()
