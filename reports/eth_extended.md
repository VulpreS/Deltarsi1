# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-22T08:00:00+00:00; **9405** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1338**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1337 | 50.6% | +0.035% | +1.060% | -1.067% |
| 12h | 1337 | 50.4% | +0.005% | +1.520% | -1.561% |
| 24h | 1336 | 51.1% | -0.022% | +2.209% | -2.290% |
| 48h | 1334 | 50.3% | -0.073% | +3.214% | -3.395% |
| 72h | 1331 | 52.7% | +0.070% | +3.989% | -4.182% |
| 120h | 1324 | 51.8% | -0.072% | +5.297% | -5.353% |
| 168h | 1315 | 50.6% | -0.123% | +6.203% | -6.306% |

## All fading bars
Events: **5241**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5235 | 49.8% | -0.004% | +1.073% | -1.116% |
| 12h | 5231 | 49.1% | -0.060% | +1.520% | -1.652% |
| 24h | 5221 | 50.1% | -0.093% | +2.192% | -2.437% |
| 48h | 5206 | 49.9% | -0.101% | +3.185% | -3.534% |
| 72h | 5195 | 52.0% | -0.003% | +3.988% | -4.272% |
| 120h | 5172 | 50.4% | -0.175% | +5.232% | -5.484% |
| 168h | 5145 | 51.2% | -0.306% | +6.121% | -6.493% |

## Actual Pine color transitions to less intense shades
Events: **1515**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1514 | 49.8% | +0.016% | +1.056% | -1.083% |
| 12h | 1514 | 50.2% | -0.013% | +1.515% | -1.581% |
| 24h | 1512 | 50.5% | -0.052% | +2.198% | -2.335% |
| 48h | 1509 | 49.6% | -0.131% | +3.200% | -3.457% |
| 72h | 1505 | 52.0% | +0.027% | +3.969% | -4.242% |
| 120h | 1498 | 51.1% | -0.121% | +5.274% | -5.401% |
| 168h | 1487 | 50.4% | -0.198% | +6.151% | -6.351% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
