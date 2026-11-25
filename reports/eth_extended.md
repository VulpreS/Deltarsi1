# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-25T10:00:00+00:00; **9479** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1345**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1343 | 50.5% | +0.033% | +1.060% | -1.069% |
| 12h | 1343 | 50.3% | +0.001% | +1.519% | -1.566% |
| 24h | 1342 | 51.0% | -0.024% | +2.209% | -2.294% |
| 48h | 1340 | 50.4% | -0.065% | +3.217% | -3.411% |
| 72h | 1339 | 52.8% | +0.085% | +4.012% | -4.192% |
| 120h | 1334 | 51.6% | -0.080% | +5.312% | -5.384% |
| 168h | 1328 | 50.8% | -0.101% | +6.253% | -6.302% |

## All fading bars
Events: **5280**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5277 | 49.7% | -0.010% | +1.072% | -1.125% |
| 12h | 5275 | 48.9% | -0.066% | +1.517% | -1.663% |
| 24h | 5266 | 50.0% | -0.096% | +2.192% | -2.445% |
| 48h | 5251 | 49.9% | -0.094% | +3.187% | -3.570% |
| 72h | 5242 | 52.2% | +0.013% | +4.011% | -4.298% |
| 120h | 5208 | 50.2% | -0.187% | +5.242% | -5.517% |
| 168h | 5184 | 51.4% | -0.292% | +6.157% | -6.495% |

## Actual Pine color transitions to less intense shades
Events: **1523**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1521 | 49.7% | +0.013% | +1.056% | -1.085% |
| 12h | 1521 | 50.0% | -0.018% | +1.514% | -1.586% |
| 24h | 1520 | 50.3% | -0.057% | +2.197% | -2.339% |
| 48h | 1517 | 49.7% | -0.123% | +3.205% | -3.476% |
| 72h | 1516 | 52.1% | +0.047% | +4.002% | -4.253% |
| 120h | 1509 | 51.0% | -0.124% | +5.294% | -5.426% |
| 168h | 1502 | 50.6% | -0.170% | +6.209% | -6.342% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
