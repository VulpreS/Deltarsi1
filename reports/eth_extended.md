# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-11T08:00:00+00:00; **9141** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1304**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1304 | 50.3% | +0.039% | +1.052% | -1.056% |
| 12h | 1304 | 50.5% | +0.011% | +1.510% | -1.540% |
| 24h | 1303 | 51.2% | -0.016% | +2.191% | -2.261% |
| 48h | 1302 | 50.4% | -0.053% | +3.198% | -3.363% |
| 72h | 1298 | 52.8% | +0.093% | +3.977% | -4.136% |
| 120h | 1292 | 51.8% | -0.107% | +5.233% | -5.335% |
| 168h | 1285 | 50.7% | -0.109% | +6.152% | -6.223% |

## All fading bars
Events: **5087**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5081 | 49.8% | +0.003% | +1.066% | -1.098% |
| 12h | 5075 | 49.0% | -0.055% | +1.510% | -1.629% |
| 24h | 5071 | 50.4% | -0.082% | +2.178% | -2.408% |
| 48h | 5052 | 50.1% | -0.061% | +3.170% | -3.483% |
| 72h | 5040 | 52.3% | +0.031% | +3.977% | -4.209% |
| 120h | 5013 | 50.6% | -0.162% | +5.176% | -5.420% |
| 168h | 4982 | 51.7% | -0.245% | +6.077% | -6.365% |

## Actual Pine color transitions to less intense shades
Events: **1473**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1473 | 49.6% | +0.016% | +1.048% | -1.071% |
| 12h | 1473 | 50.2% | -0.011% | +1.502% | -1.559% |
| 24h | 1472 | 50.5% | -0.051% | +2.178% | -2.306% |
| 48h | 1469 | 49.6% | -0.116% | +3.177% | -3.424% |
| 72h | 1465 | 51.9% | +0.044% | +3.954% | -4.195% |
| 120h | 1459 | 51.1% | -0.164% | +5.200% | -5.379% |
| 168h | 1450 | 50.6% | -0.187% | +6.095% | -6.267% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
