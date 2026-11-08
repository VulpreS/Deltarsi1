# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-08T08:00:00+00:00; **9069** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1298**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1297 | 50.3% | +0.032% | +1.044% | -1.058% |
| 12h | 1297 | 50.5% | +0.005% | +1.501% | -1.538% |
| 24h | 1295 | 51.2% | -0.014% | +2.186% | -2.259% |
| 48h | 1292 | 50.3% | -0.066% | +3.181% | -3.364% |
| 72h | 1289 | 52.8% | +0.092% | +3.976% | -4.133% |
| 120h | 1283 | 51.7% | -0.128% | +5.215% | -5.327% |
| 168h | 1273 | 50.7% | -0.121% | +6.130% | -6.206% |

## All fading bars
Events: **5040**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5038 | 49.5% | -0.003% | +1.061% | -1.102% |
| 12h | 5038 | 48.9% | -0.060% | +1.505% | -1.631% |
| 24h | 5029 | 50.4% | -0.078% | +2.179% | -2.407% |
| 48h | 5013 | 50.1% | -0.067% | +3.166% | -3.490% |
| 72h | 4995 | 52.4% | +0.032% | +3.979% | -4.207% |
| 120h | 4970 | 50.6% | -0.182% | +5.155% | -5.415% |
| 168h | 4938 | 51.6% | -0.261% | +6.061% | -6.349% |

## Actual Pine color transitions to less intense shades
Events: **1465**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1464 | 49.5% | +0.009% | +1.038% | -1.073% |
| 12h | 1464 | 50.2% | -0.019% | +1.492% | -1.559% |
| 24h | 1462 | 50.5% | -0.048% | +2.173% | -2.304% |
| 48h | 1459 | 49.6% | -0.128% | +3.162% | -3.425% |
| 72h | 1455 | 52.0% | +0.043% | +3.955% | -4.194% |
| 120h | 1448 | 51.0% | -0.185% | +5.181% | -5.371% |
| 168h | 1437 | 50.5% | -0.195% | +6.074% | -6.250% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
