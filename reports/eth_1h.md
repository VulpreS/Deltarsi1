# ETHUSDT 1H — DeltaRSI exploratory report

Closed candles: **720**; from 2026-09-26T12:00:00+00:00 to 2026-10-26T11:00:00+00:00.

## Method
SMA(21) → Wilder RSI(12) → EMA(7), then mirrored logarithmic delta exactly as in Delta.
A bearish divergence is counted when a completed positive-delta wave has a higher price high but a lower delta peak than the preceding positive wave.
This is a retrospective structural study, not an executable entry strategy. Wave completion is known only after crossing zero.

## Results
Completed positive waves: **21**.
Bearish wave divergences: **3**.

| Wave confirmed UTC | Price high previous → current | Delta peak previous → current | Return next 6h | Return next 12h |
|---|---:|---:|---:|---:|
| 2026-10-11T11:00:00+00:00 | 2511.11 → 2519.51 | 137.40 → 37.05 | +1.27% | +1.21% |
| 2026-10-14T08:00:00+00:00 | 2522.63 → 2530.44 | 54.58 → 0.88 | -2.85% | -3.56% |
| 2026-10-22T03:00:00+00:00 | 2446.27 → 2526.62 | 64.18 → 45.63 | -1.50% | -1.87% |

## Limitations
- No commissions, spread, funding or slippage included.
- The sample is short; results cannot establish predictive edge.
- The symmetric transform may create artificial zero readings around RSI 50.
- Signals at first histogram fading require a separate non-lookahead backtest.
