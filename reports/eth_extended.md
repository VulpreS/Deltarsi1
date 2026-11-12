# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-12T08:00:00+00:00; **9165** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1306**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1305 | 50.3% | +0.038% | +1.052% | -1.057% |
| 12h | 1305 | 50.5% | +0.012% | +1.509% | -1.540% |
| 24h | 1304 | 51.2% | -0.015% | +2.191% | -2.260% |
| 48h | 1303 | 50.4% | -0.050% | +3.200% | -3.360% |
| 72h | 1302 | 52.8% | +0.093% | +3.981% | -4.137% |
| 120h | 1295 | 51.8% | -0.099% | +5.238% | -5.331% |
| 168h | 1289 | 50.9% | -0.067% | +6.183% | -6.211% |

## All fading bars
Events: **5106**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5104 | 49.8% | +0.005% | +1.066% | -1.096% |
| 12h | 5098 | 49.1% | -0.052% | +1.510% | -1.626% |
| 24h | 5087 | 50.4% | -0.081% | +2.180% | -2.403% |
| 48h | 5071 | 50.1% | -0.061% | +3.170% | -3.483% |
| 72h | 5052 | 52.2% | +0.024% | +3.973% | -4.213% |
| 120h | 5029 | 50.5% | -0.173% | +5.170% | -5.427% |
| 168h | 4995 | 51.8% | -0.206% | +6.104% | -6.352% |

## Actual Pine color transitions to less intense shades
Events: **1476**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1475 | 49.6% | +0.016% | +1.047% | -1.072% |
| 12h | 1475 | 50.2% | -0.010% | +1.502% | -1.559% |
| 24h | 1473 | 50.6% | -0.050% | +2.178% | -2.305% |
| 48h | 1472 | 49.7% | -0.113% | +3.178% | -3.421% |
| 72h | 1469 | 51.9% | +0.044% | +3.957% | -4.196% |
| 120h | 1462 | 51.1% | -0.157% | +5.204% | -5.375% |
| 168h | 1455 | 50.7% | -0.138% | +6.130% | -6.252% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
