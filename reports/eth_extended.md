# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-15T08:00:00+00:00; **9237** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1315**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1315 | 50.2% | +0.031% | +1.052% | -1.068% |
| 12h | 1313 | 50.3% | -0.001% | +1.507% | -1.556% |
| 24h | 1311 | 51.1% | -0.028% | +2.193% | -2.275% |
| 48h | 1308 | 50.3% | -0.066% | +3.198% | -3.375% |
| 72h | 1306 | 52.8% | +0.094% | +3.986% | -4.144% |
| 120h | 1303 | 51.9% | -0.080% | +5.261% | -5.332% |
| 168h | 1298 | 50.8% | -0.074% | +6.193% | -6.230% |

## All fading bars
Events: **5145**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5139 | 49.6% | -0.003% | +1.065% | -1.106% |
| 12h | 5136 | 49.0% | -0.061% | +1.509% | -1.638% |
| 24h | 5133 | 50.3% | -0.089% | +2.185% | -2.413% |
| 48h | 5117 | 50.0% | -0.078% | +3.177% | -3.501% |
| 72h | 5106 | 52.2% | +0.042% | +4.001% | -4.215% |
| 120h | 5071 | 50.5% | -0.177% | +5.188% | -5.443% |
| 168h | 5040 | 51.7% | -0.226% | +6.109% | -6.381% |

## Actual Pine color transitions to less intense shades
Events: **1487**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1487 | 49.4% | +0.010% | +1.048% | -1.082% |
| 12h | 1485 | 50.0% | -0.025% | +1.499% | -1.576% |
| 24h | 1483 | 50.4% | -0.062% | +2.181% | -2.321% |
| 48h | 1479 | 49.6% | -0.128% | +3.178% | -3.437% |
| 72h | 1476 | 52.0% | +0.055% | +3.969% | -4.200% |
| 120h | 1472 | 51.2% | -0.139% | +5.231% | -5.379% |
| 168h | 1465 | 50.6% | -0.151% | +6.136% | -6.273% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
