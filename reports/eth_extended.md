# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-07T07:00:00+00:00; **9044** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1295**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1293 | 50.3% | +0.032% | +1.045% | -1.060% |
| 12h | 1292 | 50.4% | +0.004% | +1.504% | -1.543% |
| 24h | 1292 | 51.2% | -0.015% | +2.189% | -2.264% |
| 48h | 1289 | 50.3% | -0.063% | +3.188% | -3.365% |
| 72h | 1285 | 52.7% | +0.072% | +3.965% | -4.138% |
| 120h | 1277 | 51.8% | -0.128% | +5.208% | -5.333% |
| 168h | 1269 | 50.5% | -0.123% | +6.143% | -6.198% |

## All fading bars
Events: **5028**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5025 | 49.5% | -0.003% | +1.063% | -1.104% |
| 12h | 5024 | 48.8% | -0.061% | +1.507% | -1.635% |
| 24h | 5012 | 50.3% | -0.079% | +2.183% | -2.413% |
| 48h | 4994 | 50.1% | -0.072% | +3.169% | -3.498% |
| 72h | 4982 | 52.3% | +0.014% | +3.968% | -4.214% |
| 120h | 4955 | 50.6% | -0.183% | +5.151% | -5.419% |
| 168h | 4929 | 51.5% | -0.262% | +6.069% | -6.344% |

## Actual Pine color transitions to less intense shades
Events: **1462**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1460 | 49.5% | +0.009% | +1.040% | -1.076% |
| 12h | 1459 | 50.1% | -0.020% | +1.494% | -1.563% |
| 24h | 1459 | 50.5% | -0.048% | +2.176% | -2.308% |
| 48h | 1455 | 49.6% | -0.125% | +3.169% | -3.427% |
| 72h | 1450 | 51.9% | +0.021% | +3.942% | -4.202% |
| 120h | 1441 | 51.1% | -0.186% | +5.171% | -5.380% |
| 168h | 1433 | 50.4% | -0.197% | +6.085% | -6.243% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
