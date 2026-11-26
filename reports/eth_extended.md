# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-26T09:00:00+00:00; **9502** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1348**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1347 | 50.4% | +0.033% | +1.060% | -1.072% |
| 12h | 1346 | 50.4% | +0.006% | +1.523% | -1.568% |
| 24h | 1344 | 51.0% | -0.025% | +2.209% | -2.297% |
| 48h | 1342 | 50.4% | -0.062% | +3.220% | -3.410% |
| 72h | 1340 | 52.8% | +0.086% | +4.014% | -4.194% |
| 120h | 1336 | 51.7% | -0.075% | +5.323% | -5.381% |
| 168h | 1331 | 50.7% | -0.102% | +6.255% | -6.311% |

## All fading bars
Events: **5294**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5292 | 49.7% | -0.008% | +1.073% | -1.126% |
| 12h | 5287 | 49.0% | -0.063% | +1.520% | -1.664% |
| 24h | 5279 | 50.1% | -0.096% | +2.190% | -2.449% |
| 48h | 5266 | 50.0% | -0.089% | +3.191% | -3.569% |
| 72h | 5250 | 52.2% | +0.017% | +4.013% | -4.303% |
| 120h | 5222 | 50.3% | -0.183% | +5.257% | -5.518% |
| 168h | 5195 | 51.3% | -0.300% | +6.153% | -6.509% |

## Actual Pine color transitions to less intense shades
Events: **1527**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1526 | 49.7% | +0.013% | +1.056% | -1.087% |
| 12h | 1524 | 50.1% | -0.013% | +1.517% | -1.588% |
| 24h | 1522 | 50.3% | -0.057% | +2.197% | -2.342% |
| 48h | 1520 | 49.8% | -0.120% | +3.206% | -3.476% |
| 72h | 1517 | 52.1% | +0.048% | +4.004% | -4.255% |
| 120h | 1512 | 51.1% | -0.117% | +5.310% | -5.424% |
| 168h | 1505 | 50.6% | -0.171% | +6.211% | -6.350% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
