# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-03T08:00:00+00:00; **8949** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1283**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1281 | 50.4% | +0.040% | +1.049% | -1.056% |
| 12h | 1280 | 50.4% | +0.009% | +1.508% | -1.540% |
| 24h | 1277 | 51.1% | -0.019% | +2.181% | -2.260% |
| 48h | 1273 | 50.1% | -0.101% | +3.162% | -3.371% |
| 72h | 1269 | 53.0% | +0.083% | +3.966% | -4.141% |
| 120h | 1264 | 51.7% | -0.115% | +5.233% | -5.320% |
| 168h | 1253 | 50.3% | -0.145% | +6.140% | -6.222% |

## All fading bars
Events: **4970**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4966 | 49.4% | -0.005% | +1.061% | -1.104% |
| 12h | 4962 | 48.6% | -0.071% | +1.499% | -1.638% |
| 24h | 4955 | 50.1% | -0.092% | +2.169% | -2.414% |
| 48h | 4938 | 50.0% | -0.102% | +3.150% | -3.505% |
| 72h | 4930 | 52.6% | +0.035% | +3.970% | -4.206% |
| 120h | 4900 | 50.5% | -0.185% | +5.172% | -5.413% |
| 168h | 4877 | 51.4% | -0.279% | +6.063% | -6.368% |

## Actual Pine color transitions to less intense shades
Events: **1448**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1446 | 49.6% | +0.015% | +1.044% | -1.071% |
| 12h | 1444 | 50.1% | -0.020% | +1.494% | -1.562% |
| 24h | 1441 | 50.5% | -0.058% | +2.164% | -2.308% |
| 48h | 1437 | 49.3% | -0.169% | +3.139% | -3.437% |
| 72h | 1433 | 52.1% | +0.030% | +3.938% | -4.206% |
| 120h | 1426 | 51.1% | -0.170% | +5.198% | -5.368% |
| 168h | 1415 | 50.2% | -0.216% | +6.083% | -6.267% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
