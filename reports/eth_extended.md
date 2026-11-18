# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-18T09:00:00+00:00; **9310** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1328**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1326 | 50.4% | +0.030% | +1.054% | -1.069% |
| 12h | 1326 | 50.2% | +0.002% | +1.512% | -1.557% |
| 24h | 1324 | 51.1% | -0.025% | +2.197% | -2.281% |
| 48h | 1318 | 50.2% | -0.072% | +3.197% | -3.391% |
| 72h | 1315 | 52.5% | +0.073% | +3.978% | -4.172% |
| 120h | 1308 | 51.8% | -0.101% | +5.258% | -5.359% |
| 168h | 1304 | 50.8% | -0.070% | +6.217% | -6.249% |

## All fading bars
Events: **5184**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5180 | 49.7% | -0.003% | +1.067% | -1.108% |
| 12h | 5178 | 49.0% | -0.057% | +1.512% | -1.639% |
| 24h | 5173 | 50.2% | -0.089% | +2.185% | -2.414% |
| 48h | 5166 | 50.0% | -0.086% | +3.177% | -3.515% |
| 72h | 5146 | 51.9% | +0.009% | +3.989% | -4.253% |
| 120h | 5118 | 50.4% | -0.194% | +5.210% | -5.484% |
| 168h | 5088 | 51.4% | -0.282% | +6.113% | -6.450% |

## Actual Pine color transitions to less intense shades
Events: **1502**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1500 | 49.6% | +0.009% | +1.049% | -1.082% |
| 12h | 1500 | 49.9% | -0.021% | +1.503% | -1.576% |
| 24h | 1498 | 50.4% | -0.060% | +2.184% | -2.326% |
| 48h | 1492 | 49.5% | -0.135% | +3.178% | -3.455% |
| 72h | 1487 | 51.7% | +0.025% | +3.959% | -4.236% |
| 120h | 1480 | 51.0% | -0.161% | +5.232% | -5.411% |
| 168h | 1473 | 50.6% | -0.148% | +6.163% | -6.294% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
