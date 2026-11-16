# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-16T08:00:00+00:00; **9261** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1318**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1317 | 50.2% | +0.030% | +1.052% | -1.069% |
| 12h | 1317 | 50.3% | -0.000% | +1.507% | -1.558% |
| 24h | 1315 | 51.1% | -0.028% | +2.192% | -2.285% |
| 48h | 1311 | 50.3% | -0.071% | +3.200% | -3.385% |
| 72h | 1308 | 52.7% | +0.082% | +3.982% | -4.158% |
| 120h | 1304 | 51.8% | -0.089% | +5.259% | -5.341% |
| 168h | 1302 | 50.8% | -0.071% | +6.210% | -6.245% |

## All fading bars
Events: **5166**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5161 | 49.6% | -0.003% | +1.066% | -1.107% |
| 12h | 5155 | 49.0% | -0.058% | +1.510% | -1.638% |
| 24h | 5145 | 50.3% | -0.088% | +2.185% | -2.416% |
| 48h | 5133 | 49.9% | -0.089% | +3.177% | -3.519% |
| 72h | 5117 | 52.0% | +0.022% | +3.994% | -4.237% |
| 120h | 5087 | 50.4% | -0.198% | +5.188% | -5.469% |
| 168h | 5052 | 51.6% | -0.249% | +6.106% | -6.407% |

## Actual Pine color transitions to less intense shades
Events: **1492**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1491 | 49.4% | +0.009% | +1.047% | -1.082% |
| 12h | 1490 | 49.9% | -0.024% | +1.499% | -1.578% |
| 24h | 1487 | 50.4% | -0.062% | +2.179% | -2.330% |
| 48h | 1483 | 49.5% | -0.137% | +3.179% | -3.451% |
| 72h | 1479 | 51.9% | +0.038% | +3.964% | -4.219% |
| 120h | 1473 | 51.1% | -0.147% | +5.229% | -5.387% |
| 168h | 1469 | 50.6% | -0.148% | +6.151% | -6.286% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
