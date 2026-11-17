# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-17T09:00:00+00:00; **9286** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1324**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1323 | 50.3% | +0.031% | +1.053% | -1.068% |
| 12h | 1321 | 50.2% | -0.001% | +1.508% | -1.558% |
| 24h | 1318 | 51.0% | -0.030% | +2.190% | -2.287% |
| 48h | 1315 | 50.2% | -0.073% | +3.198% | -3.392% |
| 72h | 1311 | 52.6% | +0.076% | +3.982% | -4.167% |
| 120h | 1306 | 51.8% | -0.088% | +5.263% | -5.347% |
| 168h | 1303 | 50.9% | -0.060% | +6.221% | -6.240% |

## All fading bars
Events: **5173**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5171 | 49.7% | -0.002% | +1.066% | -1.107% |
| 12h | 5169 | 49.0% | -0.058% | +1.510% | -1.638% |
| 24h | 5166 | 50.2% | -0.090% | +2.182% | -2.416% |
| 48h | 5146 | 49.9% | -0.088% | +3.176% | -3.519% |
| 72h | 5133 | 52.0% | +0.009% | +3.991% | -4.253% |
| 120h | 5106 | 50.5% | -0.172% | +5.220% | -5.464% |
| 168h | 5072 | 51.6% | -0.255% | +6.119% | -6.424% |

## Actual Pine color transitions to less intense shades
Events: **1498**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1497 | 49.6% | +0.010% | +1.049% | -1.081% |
| 12h | 1495 | 49.9% | -0.024% | +1.500% | -1.577% |
| 24h | 1492 | 50.3% | -0.064% | +2.177% | -2.331% |
| 48h | 1487 | 49.4% | -0.138% | +3.178% | -3.457% |
| 72h | 1483 | 51.8% | +0.028% | +3.963% | -4.232% |
| 120h | 1476 | 51.2% | -0.138% | +5.242% | -5.389% |
| 168h | 1472 | 50.7% | -0.139% | +6.165% | -6.287% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
