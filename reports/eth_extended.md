# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-29T07:00:00+00:00; **8828** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1263**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1262 | 50.3% | +0.039% | +1.055% | -1.061% |
| 12h | 1261 | 50.4% | +0.008% | +1.513% | -1.548% |
| 24h | 1258 | 51.4% | -0.014% | +2.191% | -2.264% |
| 48h | 1253 | 50.3% | -0.101% | +3.174% | -3.375% |
| 72h | 1250 | 52.9% | +0.062% | +3.960% | -4.155% |
| 120h | 1246 | 51.8% | -0.120% | +5.237% | -5.338% |
| 168h | 1243 | 50.4% | -0.142% | +6.158% | -6.234% |

## All fading bars
Events: **4899**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4897 | 49.3% | -0.005% | +1.065% | -1.109% |
| 12h | 4895 | 48.7% | -0.066% | +1.504% | -1.640% |
| 24h | 4887 | 50.3% | -0.085% | +2.182% | -2.417% |
| 48h | 4877 | 49.9% | -0.103% | +3.159% | -3.511% |
| 72h | 4864 | 52.5% | +0.022% | +3.972% | -4.222% |
| 120h | 4838 | 50.5% | -0.184% | +5.179% | -5.426% |
| 168h | 4811 | 51.6% | -0.271% | +6.091% | -6.385% |

## Actual Pine color transitions to less intense shades
Events: **1425**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1424 | 49.6% | +0.016% | +1.050% | -1.077% |
| 12h | 1423 | 50.2% | -0.021% | +1.501% | -1.570% |
| 24h | 1420 | 50.8% | -0.053% | +2.176% | -2.313% |
| 48h | 1415 | 49.5% | -0.170% | +3.152% | -3.443% |
| 72h | 1412 | 52.1% | +0.010% | +3.937% | -4.222% |
| 120h | 1407 | 51.0% | -0.179% | +5.200% | -5.387% |
| 168h | 1402 | 50.4% | -0.210% | +6.105% | -6.281% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
