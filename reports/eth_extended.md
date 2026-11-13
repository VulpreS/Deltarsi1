# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-13T08:00:00+00:00; **9189** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1308**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1307 | 50.3% | +0.036% | +1.051% | -1.058% |
| 12h | 1307 | 50.4% | +0.006% | +1.508% | -1.545% |
| 24h | 1306 | 51.2% | -0.018% | +2.190% | -2.264% |
| 48h | 1304 | 50.4% | -0.052% | +3.199% | -3.360% |
| 72h | 1303 | 52.8% | +0.101% | +3.986% | -4.133% |
| 120h | 1298 | 51.8% | -0.094% | +5.243% | -5.331% |
| 168h | 1292 | 50.8% | -0.097% | +6.169% | -6.228% |

## All fading bars
Events: **5117**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5115 | 49.7% | -0.000% | +1.064% | -1.101% |
| 12h | 5110 | 49.2% | -0.053% | +1.510% | -1.627% |
| 24h | 5106 | 50.5% | -0.074% | +2.185% | -2.398% |
| 48h | 5087 | 50.0% | -0.070% | +3.168% | -3.486% |
| 72h | 5071 | 52.2% | +0.025% | +3.974% | -4.211% |
| 120h | 5040 | 50.6% | -0.160% | +5.179% | -5.422% |
| 168h | 5013 | 51.7% | -0.232% | +6.094% | -6.368% |

## Actual Pine color transitions to less intense shades
Events: **1479**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1478 | 49.5% | +0.015% | +1.046% | -1.073% |
| 12h | 1478 | 50.1% | -0.018% | +1.499% | -1.566% |
| 24h | 1476 | 50.6% | -0.050% | +2.179% | -2.308% |
| 48h | 1473 | 49.6% | -0.114% | +3.178% | -3.421% |
| 72h | 1472 | 52.0% | +0.053% | +3.964% | -4.192% |
| 120h | 1465 | 51.1% | -0.153% | +5.209% | -5.375% |
| 168h | 1459 | 50.6% | -0.172% | +6.114% | -6.271% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
