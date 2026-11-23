# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-23T09:00:00+00:00; **9430** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1340**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1339 | 50.5% | +0.032% | +1.060% | -1.069% |
| 12h | 1339 | 50.3% | +0.002% | +1.519% | -1.562% |
| 24h | 1338 | 51.0% | -0.026% | +2.208% | -2.292% |
| 48h | 1336 | 50.4% | -0.064% | +3.219% | -3.395% |
| 72h | 1334 | 52.8% | +0.075% | +4.001% | -4.182% |
| 120h | 1328 | 51.7% | -0.079% | +5.294% | -5.371% |
| 168h | 1318 | 50.7% | -0.110% | +6.223% | -6.298% |

## All fading bars
Events: **5250**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5245 | 49.7% | -0.007% | +1.072% | -1.119% |
| 12h | 5245 | 49.0% | -0.065% | +1.518% | -1.655% |
| 24h | 5241 | 50.0% | -0.098% | +2.191% | -2.439% |
| 48h | 5222 | 50.0% | -0.093% | +3.190% | -3.543% |
| 72h | 5207 | 52.0% | +0.001% | +3.998% | -4.275% |
| 120h | 5184 | 50.3% | -0.179% | +5.233% | -5.495% |
| 168h | 5166 | 51.4% | -0.292% | +6.149% | -6.488% |

## Actual Pine color transitions to less intense shades
Events: **1517**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1516 | 49.7% | +0.013% | +1.056% | -1.085% |
| 12h | 1516 | 50.1% | -0.015% | +1.514% | -1.582% |
| 24h | 1515 | 50.4% | -0.057% | +2.197% | -2.337% |
| 48h | 1512 | 49.7% | -0.120% | +3.207% | -3.458% |
| 72h | 1509 | 52.0% | +0.035% | +3.987% | -4.240% |
| 120h | 1502 | 51.1% | -0.127% | +5.272% | -5.417% |
| 168h | 1492 | 50.5% | -0.179% | +6.182% | -6.339% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
