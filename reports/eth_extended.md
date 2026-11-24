# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-24T11:00:00+00:00; **9456** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1342**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1342 | 50.5% | +0.033% | +1.061% | -1.068% |
| 12h | 1341 | 50.3% | +0.003% | +1.521% | -1.565% |
| 24h | 1340 | 51.0% | -0.026% | +2.208% | -2.295% |
| 48h | 1339 | 50.3% | -0.068% | +3.216% | -3.408% |
| 72h | 1336 | 52.8% | +0.082% | +4.015% | -4.181% |
| 120h | 1331 | 51.6% | -0.085% | +5.298% | -5.382% |
| 168h | 1324 | 50.8% | -0.091% | +6.257% | -6.285% |

## All fading bars
Events: **5266**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5263 | 49.7% | -0.009% | +1.073% | -1.124% |
| 12h | 5260 | 49.1% | -0.062% | +1.520% | -1.662% |
| 24h | 5252 | 50.0% | -0.098% | +2.192% | -2.446% |
| 48h | 5243 | 49.8% | -0.099% | +3.185% | -3.564% |
| 72h | 5224 | 52.1% | +0.011% | +4.017% | -4.279% |
| 120h | 5195 | 50.2% | -0.188% | +5.230% | -5.512% |
| 168h | 5174 | 51.4% | -0.284% | +6.161% | -6.483% |

## Actual Pine color transitions to less intense shades
Events: **1520**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1520 | 49.7% | +0.013% | +1.056% | -1.084% |
| 12h | 1518 | 50.1% | -0.014% | +1.516% | -1.585% |
| 24h | 1517 | 50.4% | -0.056% | +2.197% | -2.340% |
| 48h | 1516 | 49.7% | -0.126% | +3.204% | -3.474% |
| 72h | 1512 | 52.1% | +0.045% | +4.006% | -4.240% |
| 120h | 1505 | 51.0% | -0.133% | +5.276% | -5.427% |
| 168h | 1498 | 50.7% | -0.162% | +6.212% | -6.327% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
