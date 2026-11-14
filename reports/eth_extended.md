# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-14T08:00:00+00:00; **9213** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1311**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1311 | 50.3% | +0.037% | +1.052% | -1.058% |
| 12h | 1309 | 50.4% | +0.006% | +1.508% | -1.546% |
| 24h | 1308 | 51.1% | -0.022% | +2.189% | -2.267% |
| 48h | 1306 | 50.4% | -0.054% | +3.201% | -3.363% |
| 72h | 1304 | 52.8% | +0.097% | +3.985% | -4.136% |
| 120h | 1302 | 51.8% | -0.092% | +5.250% | -5.336% |
| 168h | 1295 | 50.8% | -0.084% | +6.181% | -6.226% |

## All fading bars
Events: **5133**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5130 | 49.6% | -0.002% | +1.065% | -1.103% |
| 12h | 5127 | 49.0% | -0.059% | +1.508% | -1.634% |
| 24h | 5117 | 50.4% | -0.081% | +2.182% | -2.405% |
| 48h | 5106 | 50.1% | -0.055% | +3.182% | -3.481% |
| 72h | 5087 | 52.1% | +0.011% | +3.973% | -4.220% |
| 120h | 5052 | 50.5% | -0.177% | +5.175% | -5.434% |
| 168h | 5029 | 51.6% | -0.250% | +6.090% | -6.385% |

## Actual Pine color transitions to less intense shades
Events: **1483**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1483 | 49.5% | +0.015% | +1.048% | -1.073% |
| 12h | 1481 | 50.1% | -0.018% | +1.500% | -1.567% |
| 24h | 1479 | 50.5% | -0.056% | +2.177% | -2.313% |
| 48h | 1476 | 49.7% | -0.111% | +3.182% | -3.422% |
| 72h | 1473 | 51.9% | +0.049% | +3.963% | -4.195% |
| 120h | 1469 | 51.1% | -0.151% | +5.215% | -5.379% |
| 168h | 1462 | 50.6% | -0.160% | +6.125% | -6.269% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
