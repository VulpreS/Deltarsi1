# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-10-31T07:00:00+00:00; **8876** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1269**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1268 | 50.4% | +0.039% | +1.054% | -1.062% |
| 12h | 1267 | 50.4% | +0.008% | +1.514% | -1.549% |
| 24h | 1266 | 51.4% | -0.015% | +2.193% | -2.268% |
| 48h | 1263 | 50.3% | -0.095% | +3.181% | -3.375% |
| 72h | 1258 | 53.1% | +0.082% | +3.973% | -4.144% |
| 120h | 1250 | 51.7% | -0.122% | +5.232% | -5.336% |
| 168h | 1246 | 50.4% | -0.140% | +6.153% | -6.227% |

## All fading bars
Events: **4929**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4925 | 49.5% | -0.005% | +1.064% | -1.108% |
| 12h | 4921 | 48.7% | -0.070% | +1.504% | -1.644% |
| 24h | 4912 | 50.2% | -0.091% | +2.181% | -2.423% |
| 48h | 4899 | 50.0% | -0.097% | +3.165% | -3.511% |
| 72h | 4887 | 52.7% | +0.034% | +3.979% | -4.213% |
| 120h | 4864 | 50.4% | -0.188% | +5.172% | -5.422% |
| 168h | 4838 | 51.5% | -0.275% | +6.080% | -6.376% |

## Actual Pine color transitions to less intense shades
Events: **1433**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1432 | 49.7% | +0.015% | +1.048% | -1.077% |
| 12h | 1430 | 50.1% | -0.021% | +1.501% | -1.571% |
| 24h | 1429 | 50.7% | -0.054% | +2.176% | -2.316% |
| 48h | 1425 | 49.5% | -0.164% | +3.158% | -3.442% |
| 72h | 1420 | 52.3% | +0.028% | +3.948% | -4.212% |
| 120h | 1412 | 51.0% | -0.177% | +5.197% | -5.382% |
| 168h | 1407 | 50.3% | -0.214% | +6.093% | -6.274% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
