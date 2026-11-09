# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-09T08:00:00+00:00; **9093** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1302**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1302 | 50.3% | +0.037% | +1.052% | -1.057% |
| 12h | 1301 | 50.5% | +0.009% | +1.508% | -1.540% |
| 24h | 1298 | 51.2% | -0.019% | +2.183% | -2.261% |
| 48h | 1295 | 50.3% | -0.062% | +3.187% | -3.363% |
| 72h | 1292 | 52.7% | +0.081% | +3.968% | -4.140% |
| 120h | 1285 | 51.8% | -0.120% | +5.218% | -5.330% |
| 168h | 1277 | 50.7% | -0.119% | +6.129% | -6.212% |

## All fading bars
Events: **5052**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5046 | 49.5% | -0.002% | +1.063% | -1.101% |
| 12h | 5045 | 48.9% | -0.061% | +1.506% | -1.634% |
| 24h | 5040 | 50.4% | -0.079% | +2.175% | -2.406% |
| 48h | 5029 | 50.1% | -0.063% | +3.164% | -3.483% |
| 72h | 5013 | 52.3% | +0.027% | +3.972% | -4.208% |
| 120h | 4982 | 50.6% | -0.176% | +5.160% | -5.417% |
| 168h | 4955 | 51.7% | -0.254% | +6.057% | -6.355% |

## Actual Pine color transitions to less intense shades
Events: **1469**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1469 | 49.5% | +0.014% | +1.046% | -1.073% |
| 12h | 1468 | 50.2% | -0.016% | +1.498% | -1.561% |
| 24h | 1465 | 50.5% | -0.052% | +2.170% | -2.305% |
| 48h | 1462 | 49.6% | -0.124% | +3.167% | -3.424% |
| 72h | 1459 | 51.9% | +0.034% | +3.946% | -4.199% |
| 120h | 1450 | 51.0% | -0.179% | +5.183% | -5.374% |
| 168h | 1441 | 50.6% | -0.192% | +6.073% | -6.256% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
