# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-05T08:00:00+00:00; **8997** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1289**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1289 | 50.3% | +0.036% | +1.048% | -1.058% |
| 12h | 1287 | 50.4% | +0.006% | +1.508% | -1.541% |
| 24h | 1285 | 51.1% | -0.025% | +2.181% | -2.262% |
| 48h | 1283 | 50.1% | -0.085% | +3.174% | -3.362% |
| 72h | 1277 | 52.7% | +0.076% | +3.954% | -4.135% |
| 120h | 1269 | 51.8% | -0.121% | +5.223% | -5.319% |
| 168h | 1264 | 50.6% | -0.122% | +6.144% | -6.202% |

## All fading bars
Events: **4995**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4989 | 49.4% | -0.007% | +1.061% | -1.105% |
| 12h | 4985 | 48.7% | -0.074% | +1.499% | -1.639% |
| 24h | 4982 | 50.2% | -0.098% | +2.170% | -2.419% |
| 48h | 4970 | 49.9% | -0.095% | +3.154% | -3.497% |
| 72h | 4955 | 52.4% | +0.019% | +3.960% | -4.210% |
| 120h | 4930 | 50.5% | -0.184% | +5.163% | -5.407% |
| 168h | 4900 | 51.6% | -0.266% | +6.065% | -6.355% |

## Actual Pine color transitions to less intense shades
Events: **1455**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1454 | 49.5% | +0.012% | +1.043% | -1.073% |
| 12h | 1452 | 50.1% | -0.022% | +1.494% | -1.562% |
| 24h | 1450 | 50.5% | -0.062% | +2.165% | -2.308% |
| 48h | 1448 | 49.4% | -0.150% | +3.153% | -3.427% |
| 72h | 1441 | 51.9% | +0.024% | +3.928% | -4.201% |
| 120h | 1433 | 51.1% | -0.179% | +5.185% | -5.367% |
| 168h | 1426 | 50.6% | -0.195% | +6.086% | -6.248% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
