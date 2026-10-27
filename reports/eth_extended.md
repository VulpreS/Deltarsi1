# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-27T06:00:00+00:00; **8779** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1253**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1252 | 50.3% | +0.038% | +1.054% | -1.064% |
| 12h | 1251 | 50.5% | +0.012% | +1.517% | -1.550% |
| 24h | 1250 | 51.4% | -0.014% | +2.197% | -2.267% |
| 48h | 1247 | 50.1% | -0.105% | +3.179% | -3.384% |
| 72h | 1246 | 52.9% | +0.061% | +3.966% | -4.163% |
| 120h | 1242 | 51.9% | -0.114% | +5.249% | -5.343% |
| 168h | 1235 | 50.3% | -0.156% | +6.159% | -6.253% |

## All fading bars
Events: **4877**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4872 | 49.4% | -0.005% | +1.065% | -1.110% |
| 12h | 4869 | 48.8% | -0.063% | +1.507% | -1.641% |
| 24h | 4863 | 50.3% | -0.085% | +2.186% | -2.421% |
| 48h | 4850 | 49.8% | -0.107% | +3.164% | -3.523% |
| 72h | 4838 | 52.6% | +0.023% | +3.984% | -4.233% |
| 120h | 4810 | 50.6% | -0.180% | +5.196% | -5.439% |
| 168h | 4786 | 51.5% | -0.289% | +6.088% | -6.407% |

## Actual Pine color transitions to less intense shades
Events: **1415**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1414 | 49.6% | +0.015% | +1.050% | -1.080% |
| 12h | 1413 | 50.2% | -0.018% | +1.504% | -1.571% |
| 24h | 1412 | 50.8% | -0.053% | +2.181% | -2.316% |
| 48h | 1408 | 49.4% | -0.174% | +3.157% | -3.453% |
| 72h | 1407 | 52.0% | +0.009% | +3.943% | -4.231% |
| 120h | 1401 | 51.2% | -0.171% | +5.216% | -5.392% |
| 168h | 1394 | 50.3% | -0.224% | +6.105% | -6.298% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
