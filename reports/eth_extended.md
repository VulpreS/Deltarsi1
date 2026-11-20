# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-20T09:00:00+00:00; **9358** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1334**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1333 | 50.6% | +0.037% | +1.060% | -1.065% |
| 12h | 1333 | 50.3% | +0.007% | +1.518% | -1.554% |
| 24h | 1331 | 51.0% | -0.031% | +2.197% | -2.284% |
| 48h | 1328 | 50.3% | -0.065% | +3.201% | -3.382% |
| 72h | 1324 | 52.9% | +0.090% | +3.982% | -4.157% |
| 120h | 1315 | 51.6% | -0.117% | +5.247% | -5.368% |
| 168h | 1308 | 50.8% | -0.086% | +6.214% | -6.264% |

## All fading bars
Events: **5207**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5203 | 49.8% | +0.001% | +1.070% | -1.106% |
| 12h | 5202 | 49.1% | -0.055% | +1.515% | -1.638% |
| 24h | 5195 | 50.1% | -0.096% | +2.182% | -2.419% |
| 48h | 5184 | 50.0% | -0.087% | +3.176% | -3.513% |
| 72h | 5173 | 52.1% | +0.019% | +3.991% | -4.244% |
| 120h | 5146 | 50.2% | -0.214% | +5.199% | -5.495% |
| 168h | 5118 | 51.4% | -0.273% | +6.130% | -6.458% |

## Actual Pine color transitions to less intense shades
Events: **1509**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1508 | 49.8% | +0.017% | +1.056% | -1.079% |
| 12h | 1508 | 50.1% | -0.015% | +1.510% | -1.573% |
| 24h | 1505 | 50.3% | -0.065% | +2.184% | -2.329% |
| 48h | 1502 | 49.6% | -0.129% | +3.181% | -3.447% |
| 72h | 1498 | 52.1% | +0.045% | +3.963% | -4.221% |
| 120h | 1487 | 50.8% | -0.175% | +5.222% | -5.418% |
| 168h | 1480 | 50.5% | -0.166% | +6.161% | -6.314% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
