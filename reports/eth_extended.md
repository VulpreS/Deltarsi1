# ETHUSDT 1H — extended DeltaRSI study

Period: 2025-10-26T12:00:00+00:00 to 2026-11-02T08:00:00+00:00; **8925** closed candles.

Original SMA21 → Wilder RSI12 → EMA7 → mirrored signed log delta.
For positive delta, fade implies hypothetical short; negative delta implies hypothetical long.
Entry is the close of the fading candle; returns are directional close-to-close.
MFE and MAE use subsequent hourly highs/lows, with no assumed intrabar execution order.

## First fading bar after a growing bar
Events: **1277**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1276 | 50.2% | +0.039% | +1.050% | -1.058% |
| 12h | 1275 | 50.2% | +0.005% | +1.507% | -1.544% |
| 24h | 1273 | 51.2% | -0.018% | +2.183% | -2.262% |
| 48h | 1269 | 50.2% | -0.098% | +3.171% | -3.373% |
| 72h | 1266 | 53.0% | +0.082% | +3.972% | -4.144% |
| 120h | 1258 | 51.8% | -0.113% | +5.237% | -5.323% |
| 168h | 1250 | 50.3% | -0.143% | +6.144% | -6.225% |

## All fading bars
Events: **4955**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4952 | 49.4% | -0.006% | +1.061% | -1.105% |
| 12h | 4949 | 48.5% | -0.073% | +1.498% | -1.640% |
| 24h | 4938 | 50.1% | -0.092% | +2.172% | -2.416% |
| 48h | 4930 | 50.0% | -0.101% | +3.154% | -3.506% |
| 72h | 4913 | 52.6% | +0.033% | +3.976% | -4.214% |
| 120h | 4887 | 50.5% | -0.184% | +5.174% | -5.414% |
| 168h | 4865 | 51.4% | -0.279% | +6.067% | -6.371% |

## Actual Pine color transitions to less intense shades
Events: **1441**.

| Horizon | N | Win rate | Mean close return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1440 | 49.5% | +0.015% | +1.045% | -1.074% |
| 12h | 1439 | 49.9% | -0.024% | +1.494% | -1.566% |
| 24h | 1437 | 50.5% | -0.057% | +2.166% | -2.310% |
| 48h | 1433 | 49.4% | -0.167% | +3.146% | -3.439% |
| 72h | 1429 | 52.2% | +0.029% | +3.946% | -4.210% |
| 120h | 1420 | 51.1% | -0.169% | +5.201% | -5.371% |
| 168h | 1412 | 50.3% | -0.215% | +6.086% | -6.269% |

## Important limitations
- Event study, not trade-by-trade PnL: events can overlap and cluster.
- No commissions, spread, funding, slippage or liquidation.
- Mean MFE and mean MAE are separate extrema; their ordering is unknown.
- No wave-number stratification yet; color transitions and fading are evaluated separately.
- The mirrored-log delta has discontinuities and can produce misleadingly low values near RSI 50.
- A 365-day sample still requires out-of-sample testing before drawing trading conclusions.
