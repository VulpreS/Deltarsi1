# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-30T07:00:00+00:00; **8852** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1266**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1265 | 50.4% | +0.040% | +1.054% | -1.063% |
| 12h | 1264 | 50.5% | +0.009% | +1.516% | -1.548% |
| 24h | 1263 | 51.5% | -0.010% | +2.195% | -2.264% |
| 48h | 1258 | 50.3% | -0.095% | +3.175% | -3.371% |
| 72h | 1253 | 52.9% | +0.065% | +3.961% | -4.151% |
| 120h | 1247 | 51.7% | -0.120% | +5.235% | -5.336% |
| 168h | 1245 | 50.4% | -0.146% | +6.150% | -6.231% |

## All fading bars
Events: **4912**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4907 | 49.4% | -0.005% | +1.066% | -1.109% |
| 12h | 4906 | 48.7% | -0.070% | +1.506% | -1.645% |
| 24h | 4899 | 50.3% | -0.085% | +2.183% | -2.418% |
| 48h | 4887 | 50.0% | -0.097% | +3.162% | -3.508% |
| 72h | 4877 | 52.6% | +0.025% | +3.972% | -4.217% |
| 120h | 4850 | 50.4% | -0.194% | +5.170% | -5.427% |
| 168h | 4828 | 51.4% | -0.290% | +6.073% | -6.389% |

## Actual Pine color transitions to less intense shades
Events: **1429**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1427 | 49.6% | +0.016% | +1.050% | -1.078% |
| 12h | 1426 | 50.2% | -0.020% | +1.503% | -1.569% |
| 24h | 1425 | 50.8% | -0.050% | +2.179% | -2.313% |
| 48h | 1420 | 49.5% | -0.164% | +3.153% | -3.439% |
| 72h | 1415 | 52.1% | +0.013% | +3.937% | -4.219% |
| 120h | 1408 | 51.0% | -0.179% | +5.198% | -5.385% |
| 168h | 1406 | 50.3% | -0.220% | +6.090% | -6.278% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
