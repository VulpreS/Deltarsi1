# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-04T08:00:00+00:00; **8973** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1285**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1285 | 50.4% | +0.041% | +1.050% | -1.054% |
| 12h | 1284 | 50.5% | +0.012% | +1.509% | -1.537% |
| 24h | 1283 | 51.2% | -0.015% | +2.181% | -2.255% |
| 48h | 1277 | 50.0% | -0.101% | +3.158% | -3.366% |
| 72h | 1273 | 52.8% | +0.079% | +3.955% | -4.137% |
| 120h | 1266 | 51.8% | -0.114% | +5.229% | -5.316% |
| 168h | 1258 | 50.5% | -0.135% | +6.143% | -6.207% |

## All fading bars
Events: **4982**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4981 | 49.5% | -0.004% | +1.062% | -1.103% |
| 12h | 4977 | 48.8% | -0.068% | +1.500% | -1.634% |
| 24h | 4970 | 50.2% | -0.089% | +2.170% | -2.410% |
| 48h | 4955 | 49.8% | -0.104% | +3.145% | -3.500% |
| 72h | 4938 | 52.5% | +0.032% | +3.964% | -4.204% |
| 120h | 4913 | 50.5% | -0.185% | +5.165% | -5.409% |
| 168h | 4887 | 51.5% | -0.274% | +6.065% | -6.359% |

## Actual Pine color transitions to less intense shades
Events: **1450**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1450 | 49.7% | +0.016% | +1.045% | -1.070% |
| 12h | 1449 | 50.2% | -0.017% | +1.495% | -1.558% |
| 24h | 1448 | 50.6% | -0.054% | +2.165% | -2.302% |
| 48h | 1441 | 49.3% | -0.170% | +3.135% | -3.432% |
| 72h | 1437 | 52.0% | +0.026% | +3.929% | -4.202% |
| 120h | 1429 | 51.2% | -0.168% | +5.193% | -5.362% |
| 168h | 1420 | 50.4% | -0.207% | +6.086% | -6.253% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
