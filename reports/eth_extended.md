# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-28T07:00:00+00:00; **8804** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1258**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1257 | 50.2% | +0.036% | +1.051% | -1.064% |
| 12h | 1256 | 50.5% | +0.009% | +1.513% | -1.548% |
| 24h | 1253 | 51.5% | -0.013% | +2.196% | -2.264% |
| 48h | 1250 | 50.2% | -0.104% | +3.176% | -3.380% |
| 72h | 1247 | 52.9% | +0.061% | +3.964% | -4.161% |
| 120h | 1245 | 51.7% | -0.122% | +5.237% | -5.343% |
| 168h | 1240 | 50.4% | -0.145% | +6.160% | -6.242% |

## All fading bars
Events: **4887**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4883 | 49.3% | -0.006% | +1.064% | -1.110% |
| 12h | 4880 | 48.8% | -0.064% | +1.505% | -1.640% |
| 24h | 4877 | 50.3% | -0.086% | +2.183% | -2.418% |
| 48h | 4864 | 49.9% | -0.106% | +3.161% | -3.515% |
| 72h | 4850 | 52.6% | +0.022% | +3.976% | -4.229% |
| 120h | 4828 | 50.4% | -0.188% | +5.180% | -5.437% |
| 168h | 4795 | 51.5% | -0.287% | +6.088% | -6.402% |

## Actual Pine color transitions to less intense shades
Events: **1420**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1419 | 49.5% | +0.013% | +1.047% | -1.079% |
| 12h | 1418 | 50.2% | -0.019% | +1.500% | -1.570% |
| 24h | 1415 | 50.8% | -0.052% | +2.180% | -2.313% |
| 48h | 1412 | 49.4% | -0.173% | +3.153% | -3.447% |
| 72h | 1408 | 52.1% | +0.009% | +3.941% | -4.229% |
| 120h | 1406 | 51.0% | -0.181% | +5.200% | -5.391% |
| 168h | 1399 | 50.4% | -0.214% | +6.107% | -6.288% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
