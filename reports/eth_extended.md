# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-26T11:00:00+00:00; **8760** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1250**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1250 | 50.3% | +0.038% | +1.055% | -1.065% |
| 12h | 1249 | 50.6% | +0.012% | +1.518% | -1.551% |
| 24h | 1248 | 51.4% | -0.015% | +2.198% | -2.268% |
| 48h | 1246 | 50.2% | -0.105% | +3.181% | -3.385% |
| 72h | 1245 | 52.9% | +0.059% | +3.965% | -4.166% |
| 120h | 1241 | 51.8% | -0.120% | +5.246% | -5.347% |
| 168h | 1232 | 50.2% | -0.158% | +6.162% | -6.255% |

## All fading bars
Events: **4867**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4862 | 49.4% | -0.005% | +1.066% | -1.111% |
| 12h | 4860 | 48.9% | -0.062% | +1.508% | -1.642% |
| 24h | 4851 | 50.3% | -0.087% | +2.187% | -2.425% |
| 48h | 4838 | 49.9% | -0.104% | +3.170% | -3.525% |
| 72h | 4830 | 52.5% | +0.017% | +3.982% | -4.240% |
| 120h | 4798 | 50.5% | -0.196% | +5.190% | -5.451% |
| 168h | 4779 | 51.4% | -0.291% | +6.089% | -6.408% |

## Actual Pine color transitions to less intense shades
Events: **1412**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1412 | 49.6% | +0.014% | +1.050% | -1.080% |
| 12h | 1411 | 50.3% | -0.017% | +1.505% | -1.572% |
| 24h | 1409 | 50.7% | -0.054% | +2.182% | -2.318% |
| 48h | 1407 | 49.4% | -0.174% | +3.159% | -3.454% |
| 72h | 1406 | 52.0% | +0.006% | +3.942% | -4.233% |
| 120h | 1400 | 51.1% | -0.176% | +5.214% | -5.396% |
| 168h | 1391 | 50.3% | -0.226% | +6.108% | -6.300% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
