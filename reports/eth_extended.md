# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-21T08:00:00+00:00; **9381** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1336**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1335 | 50.5% | +0.034% | +1.059% | -1.067% |
| 12h | 1334 | 50.3% | +0.002% | +1.517% | -1.559% |
| 24h | 1334 | 51.0% | -0.026% | +2.204% | -2.288% |
| 48h | 1331 | 50.3% | -0.079% | +3.199% | -3.393% |
| 72h | 1328 | 52.8% | +0.075% | +3.984% | -4.170% |
| 120h | 1318 | 51.7% | -0.095% | +5.259% | -5.362% |
| 168h | 1311 | 50.7% | -0.098% | +6.214% | -6.277% |

## All fading bars
Events: **5221**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5218 | 49.7% | -0.008% | +1.070% | -1.118% |
| 12h | 5212 | 49.0% | -0.068% | +1.513% | -1.651% |
| 24h | 5206 | 50.1% | -0.093% | +2.188% | -2.424% |
| 48h | 5195 | 49.9% | -0.106% | +3.173% | -3.531% |
| 72h | 5183 | 52.1% | +0.007% | +3.989% | -4.254% |
| 120h | 5166 | 50.3% | -0.181% | +5.222% | -5.486% |
| 168h | 5133 | 51.4% | -0.289% | +6.128% | -6.473% |

## Actual Pine color transitions to less intense shades
Events: **1512**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1511 | 49.8% | +0.015% | +1.056% | -1.084% |
| 12h | 1509 | 50.0% | -0.020% | +1.510% | -1.578% |
| 24h | 1509 | 50.4% | -0.058% | +2.192% | -2.331% |
| 48h | 1505 | 49.6% | -0.141% | +3.180% | -3.457% |
| 72h | 1502 | 52.0% | +0.032% | +3.965% | -4.232% |
| 120h | 1492 | 51.0% | -0.142% | +5.241% | -5.409% |
| 168h | 1483 | 50.5% | -0.176% | +6.161% | -6.325% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
