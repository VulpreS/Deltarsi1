# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-06T08:00:00+00:00; **9021** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1292**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1291 | 50.2% | +0.032% | +1.046% | -1.061% |
| 12h | 1290 | 50.4% | +0.004% | +1.505% | -1.544% |
| 24h | 1289 | 51.2% | -0.011% | +2.194% | -2.262% |
| 48h | 1285 | 50.2% | -0.083% | +3.174% | -3.368% |
| 72h | 1283 | 52.6% | +0.069% | +3.966% | -4.134% |
| 120h | 1273 | 51.7% | -0.131% | +5.211% | -5.329% |
| 168h | 1266 | 50.6% | -0.124% | +6.148% | -6.197% |

## All fading bars
Events: **5013**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5008 | 49.4% | -0.004% | +1.064% | -1.105% |
| 12h | 5005 | 48.7% | -0.062% | +1.509% | -1.638% |
| 24h | 4995 | 50.3% | -0.082% | +2.183% | -2.416% |
| 48h | 4982 | 50.0% | -0.088% | +3.157% | -3.503% |
| 72h | 4970 | 52.3% | +0.013% | +3.966% | -4.210% |
| 120h | 4938 | 50.5% | -0.187% | +5.157% | -5.412% |
| 168h | 4913 | 51.6% | -0.263% | +6.068% | -6.349% |

## Actual Pine color transitions to less intense shades
Events: **1459**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1458 | 49.4% | +0.008% | +1.041% | -1.076% |
| 12h | 1457 | 50.1% | -0.020% | +1.496% | -1.564% |
| 24h | 1455 | 50.6% | -0.045% | +2.181% | -2.307% |
| 48h | 1450 | 49.4% | -0.148% | +3.153% | -3.432% |
| 72h | 1448 | 51.8% | +0.018% | +3.942% | -4.198% |
| 120h | 1437 | 51.0% | -0.188% | +5.174% | -5.376% |
| 168h | 1429 | 50.5% | -0.197% | +6.092% | -6.241% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
