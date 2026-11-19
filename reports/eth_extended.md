# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-19T09:00:00+00:00; **9334** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1331**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1331 | 50.5% | +0.034% | +1.057% | -1.066% |
| 12h | 1329 | 50.3% | +0.003% | +1.514% | -1.557% |
| 24h | 1328 | 51.1% | -0.029% | +2.196% | -2.283% |
| 48h | 1324 | 50.4% | -0.063% | +3.204% | -3.381% |
| 72h | 1318 | 52.7% | +0.077% | +3.978% | -4.169% |
| 120h | 1311 | 51.7% | -0.108% | +5.255% | -5.365% |
| 168h | 1306 | 50.8% | -0.069% | +6.221% | -6.253% |

## All fading bars
Events: **5195**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5190 | 49.7% | -0.001% | +1.068% | -1.107% |
| 12h | 5185 | 49.0% | -0.057% | +1.512% | -1.639% |
| 24h | 5184 | 50.2% | -0.092% | +2.183% | -2.416% |
| 48h | 5173 | 50.0% | -0.084% | +3.179% | -3.512% |
| 72h | 5166 | 52.1% | +0.015% | +3.990% | -4.248% |
| 120h | 5133 | 50.3% | -0.207% | +5.204% | -5.495% |
| 168h | 5106 | 51.5% | -0.246% | +6.143% | -6.440% |

## Actual Pine color transitions to less intense shades
Events: **1505**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1505 | 49.7% | +0.013% | +1.052% | -1.080% |
| 12h | 1503 | 50.0% | -0.020% | +1.505% | -1.576% |
| 24h | 1502 | 50.3% | -0.063% | +2.183% | -2.328% |
| 48h | 1498 | 49.7% | -0.127% | +3.184% | -3.446% |
| 72h | 1492 | 51.9% | +0.033% | +3.959% | -4.232% |
| 120h | 1483 | 51.0% | -0.167% | +5.229% | -5.416% |
| 168h | 1476 | 50.7% | -0.136% | +6.174% | -6.295% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
