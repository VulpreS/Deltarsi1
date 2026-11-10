# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-10T08:00:00+00:00; **9117** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1303**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1302 | 50.3% | +0.037% | +1.052% | -1.057% |
| 12h | 1302 | 50.5% | +0.008% | +1.507% | -1.542% |
| 24h | 1302 | 51.2% | -0.018% | +2.188% | -2.263% |
| 48h | 1298 | 50.4% | -0.059% | +3.192% | -3.362% |
| 72h | 1295 | 52.7% | +0.086% | +3.972% | -4.137% |
| 120h | 1289 | 51.9% | -0.086% | +5.244% | -5.320% |
| 168h | 1283 | 50.7% | -0.126% | +6.142% | -6.221% |

## All fading bars
Events: **5071**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5067 | 49.6% | -0.001% | +1.063% | -1.100% |
| 12h | 5063 | 48.9% | -0.060% | +1.504% | -1.632% |
| 24h | 5052 | 50.4% | -0.081% | +2.175% | -2.408% |
| 48h | 5040 | 50.2% | -0.057% | +3.172% | -3.479% |
| 72h | 5029 | 52.2% | +0.020% | +3.968% | -4.214% |
| 120h | 4995 | 50.7% | -0.145% | +5.184% | -5.407% |
| 168h | 4970 | 51.6% | -0.255% | +6.066% | -6.360% |

## Actual Pine color transitions to less intense shades
Events: **1472**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1470 | 49.5% | +0.014% | +1.045% | -1.072% |
| 12h | 1470 | 50.1% | -0.017% | +1.497% | -1.561% |
| 24h | 1469 | 50.5% | -0.051% | +2.175% | -2.307% |
| 48h | 1465 | 49.6% | -0.121% | +3.172% | -3.423% |
| 72h | 1462 | 51.9% | +0.038% | +3.949% | -4.196% |
| 120h | 1455 | 51.2% | -0.140% | +5.213% | -5.362% |
| 168h | 1448 | 50.5% | -0.202% | +6.086% | -6.266% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
