# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-27T09:00:00+00:00; **9526** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1352**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1351 | 50.4% | +0.034% | +1.063% | -1.071% |
| 12h | 1350 | 50.4% | +0.005% | +1.523% | -1.567% |
| 24h | 1348 | 51.1% | -0.022% | +2.212% | -2.298% |
| 48h | 1344 | 50.5% | -0.058% | +3.221% | -3.411% |
| 72h | 1342 | 52.9% | +0.090% | +4.016% | -4.192% |
| 120h | 1338 | 51.6% | -0.078% | +5.321% | -5.388% |
| 168h | 1334 | 50.7% | -0.095% | +6.266% | -6.310% |

## All fading bars
Events: **5307**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5306 | 49.6% | -0.008% | +1.074% | -1.125% |
| 12h | 5304 | 48.9% | -0.065% | +1.519% | -1.665% |
| 24h | 5294 | 50.1% | -0.094% | +2.193% | -2.448% |
| 48h | 5279 | 50.1% | -0.084% | +3.192% | -3.570% |
| 72h | 5266 | 52.4% | +0.022% | +4.018% | -4.300% |
| 120h | 5241 | 50.1% | -0.187% | +5.256% | -5.531% |
| 168h | 5207 | 51.3% | -0.295% | +6.162% | -6.510% |

## Actual Pine color transitions to less intense shades
Events: **1531**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1530 | 49.7% | +0.014% | +1.058% | -1.086% |
| 12h | 1529 | 50.1% | -0.014% | +1.517% | -1.586% |
| 24h | 1527 | 50.4% | -0.054% | +2.200% | -2.341% |
| 48h | 1522 | 49.9% | -0.116% | +3.207% | -3.477% |
| 72h | 1520 | 52.2% | +0.052% | +4.004% | -4.254% |
| 120h | 1515 | 51.0% | -0.120% | +5.307% | -5.433% |
| 168h | 1509 | 50.6% | -0.161% | +6.226% | -6.347% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
