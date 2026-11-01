# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-01T08:00:00+00:00; **8901** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1273**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1273 | 50.2% | +0.038% | +1.050% | -1.060% |
| 12h | 1272 | 50.2% | +0.006% | +1.509% | -1.546% |
| 24h | 1269 | 51.4% | -0.016% | +2.189% | -2.265% |
| 48h | 1266 | 50.2% | -0.097% | +3.177% | -3.376% |
| 72h | 1264 | 53.0% | +0.080% | +3.975% | -4.147% |
| 120h | 1253 | 51.6% | -0.124% | +5.230% | -5.335% |
| 168h | 1247 | 50.4% | -0.143% | +6.149% | -6.227% |

## All fading bars
Events: **4938**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4938 | 49.4% | -0.005% | +1.062% | -1.107% |
| 12h | 4937 | 48.6% | -0.071% | +1.500% | -1.641% |
| 24h | 4930 | 50.2% | -0.091% | +2.176% | -2.418% |
| 48h | 4913 | 50.0% | -0.101% | +3.162% | -3.513% |
| 72h | 4900 | 52.6% | +0.034% | +3.980% | -4.214% |
| 120h | 4877 | 50.4% | -0.190% | +5.170% | -5.421% |
| 168h | 4850 | 51.4% | -0.284% | +6.069% | -6.379% |

## Actual Pine color transitions to less intense shades
Events: **1437**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1437 | 49.5% | +0.014% | +1.045% | -1.075% |
| 12h | 1436 | 49.9% | -0.023% | +1.496% | -1.567% |
| 24h | 1433 | 50.7% | -0.055% | +2.172% | -2.313% |
| 48h | 1429 | 49.5% | -0.165% | +3.153% | -3.443% |
| 72h | 1426 | 52.2% | +0.027% | +3.950% | -4.214% |
| 120h | 1415 | 51.0% | -0.179% | +5.195% | -5.382% |
| 168h | 1408 | 50.3% | -0.217% | +6.090% | -6.274% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
