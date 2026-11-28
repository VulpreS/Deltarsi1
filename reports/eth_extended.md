# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-28T09:00:00+00:00; **9550** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1354**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1353 | 50.4% | +0.036% | +1.065% | -1.070% |
| 12h | 1353 | 50.4% | +0.009% | +1.526% | -1.564% |
| 24h | 1352 | 51.0% | -0.022% | +2.215% | -2.299% |
| 48h | 1348 | 50.7% | -0.048% | +3.226% | -3.410% |
| 72h | 1344 | 52.8% | +0.088% | +4.017% | -4.192% |
| 120h | 1340 | 51.6% | -0.076% | +5.323% | -5.390% |
| 168h | 1336 | 50.8% | -0.092% | +6.277% | -6.306% |

## All fading bars
Events: **5319**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5315 | 49.6% | -0.007% | +1.075% | -1.124% |
| 12h | 5315 | 48.9% | -0.063% | +1.521% | -1.663% |
| 24h | 5307 | 50.1% | -0.091% | +2.196% | -2.449% |
| 48h | 5294 | 50.3% | -0.078% | +3.196% | -3.568% |
| 72h | 5279 | 52.3% | +0.020% | +4.019% | -4.300% |
| 120h | 5250 | 50.2% | -0.184% | +5.258% | -5.534% |
| 168h | 5222 | 51.3% | -0.292% | +6.175% | -6.510% |

## Actual Pine color transitions to less intense shades
Events: **1534**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1533 | 49.6% | +0.015% | +1.060% | -1.085% |
| 12h | 1533 | 50.1% | -0.011% | +1.519% | -1.584% |
| 24h | 1531 | 50.4% | -0.055% | +2.202% | -2.342% |
| 48h | 1527 | 50.0% | -0.106% | +3.212% | -3.475% |
| 72h | 1522 | 52.2% | +0.051% | +4.005% | -4.253% |
| 120h | 1517 | 51.0% | -0.118% | +5.309% | -5.435% |
| 168h | 1512 | 50.7% | -0.157% | +6.240% | -6.342% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
