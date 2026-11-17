# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-17T09:00:00+00:00; **9286** closed candles.

## What the proxy means

This is **NOT CoinGlass liquidation heatmap**. It uses confirmed local swing highs/lows as potential stop-liquidity clusters, weights them by relative candle volume, merges levels within 0.35%, and expires zones after 30 days without a new confirmed pivot. There is no open-interest, leverage, or actual liquidation-position data.
Swing pivots are confirmed only **3 hours later**; all signals use zones known before the signal candle. A level's strength is a heuristic, not an estimated dollar amount of liquidations.

## Signal definitions

- DeltaRSI: SMA21 → RSI12 Wilder → EMA7 → mirrored signed log delta.
- Entry event: first reduction in absolute histogram magnitude after an increase, with same delta sign on both latest bars. This corresponds to fading, not a separately audited exact RGB/color transition.
- Positive delta implies hypothetical short, negative delta hypothetical long.
- Near: relevant prior high (for short) / low (for long) is within 0.5% of signal candle close.
- Sweep: signal candle wicks beyond a pre-existing relevant level, but closes back inside; preceding close must have been on the inside.
- Entry price: signal candle close. MFE/MAE from subsequent candle high/low; intrabar ordering not modeled.

## Groups

### All first fades — 1295 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1294 | 50.5% | +0.043% | +1.058% | -1.060% |
| 12h | 1292 | 50.7% | +0.026% | +1.519% | -1.539% |
| 24h | 1289 | 51.6% | +0.020% | +2.208% | -2.247% |
| 48h | 1286 | 50.5% | -0.032% | +3.202% | -3.311% |
| 72h | 1282 | 52.9% | +0.084% | +3.942% | -4.070% |
| 120h | 1277 | 52.2% | -0.065% | +5.198% | -5.252% |
| 168h | 1274 | 51.3% | +0.007% | +6.176% | -6.085% |

### First fades near liquidity — 1057 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1057 | 50.3% | +0.019% | +0.994% | -1.016% |
| 12h | 1056 | 51.3% | +0.008% | +1.448% | -1.491% |
| 24h | 1055 | 53.3% | +0.099% | +2.144% | -2.112% |
| 48h | 1055 | 51.3% | +0.061% | +3.149% | -3.139% |
| 72h | 1053 | 52.7% | +0.033% | +3.865% | -3.934% |
| 120h | 1053 | 52.1% | -0.110% | +5.139% | -5.191% |
| 168h | 1050 | 52.2% | +0.089% | +6.147% | -5.972% |

### First fades with liquidity sweep — 282 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 282 | 50.7% | +0.062% | +1.166% | -1.112% |
| 12h | 281 | 53.0% | -0.022% | +1.588% | -1.608% |
| 24h | 280 | 53.2% | +0.115% | +2.473% | -2.331% |
| 48h | 280 | 50.7% | +0.012% | +3.427% | -3.480% |
| 72h | 280 | 51.4% | -0.192% | +4.033% | -4.262% |
| 120h | 279 | 52.0% | -0.437% | +5.205% | -5.432% |
| 168h | 279 | 50.5% | -0.169% | +6.199% | -6.264% |

### Near or swept — 1074 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1074 | 50.6% | +0.026% | +1.004% | -1.015% |
| 12h | 1073 | 51.1% | -0.003% | +1.453% | -1.499% |
| 24h | 1071 | 53.1% | +0.081% | +2.144% | -2.130% |
| 48h | 1071 | 50.9% | +0.025% | +3.140% | -3.167% |
| 72h | 1069 | 52.4% | +0.002% | +3.856% | -3.977% |
| 120h | 1068 | 52.1% | -0.104% | +5.139% | -5.220% |
| 168h | 1065 | 52.0% | +0.115% | +6.170% | -5.996% |

### Away from liquidity — 221 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 220 | 50.5% | +0.125% | +1.321% | -1.282% |
| 12h | 219 | 48.9% | +0.167% | +1.839% | -1.738% |
| 24h | 218 | 44.0% | -0.279% | +2.521% | -2.825% |
| 48h | 215 | 48.4% | -0.314% | +3.511% | -4.029% |
| 72h | 213 | 55.4% | +0.494% | +4.376% | -4.533% |
| 120h | 209 | 53.1% | +0.135% | +5.496% | -5.416% |
| 168h | 209 | 47.4% | -0.541% | +6.207% | -6.541% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +39.64% |
| low | 2407.38 | 23.5 | 11 | +32.85% |
| low | 2484.94 | 15.3 | 11 | +37.13% |
| low | 2432.00 | 15.0 | 11 | +34.20% |
| low | 2235.38 | 12.1 | 8 | +23.35% |
| low | 2355.61 | 11.2 | 5 | +29.99% |
| low | 2294.98 | 10.5 | 4 | +26.64% |
| low | 2319.21 | 9.9 | 5 | +27.98% |
| high | 2445.95 | 8.4 | 5 | +34.97% |
| low | 2280.48 | 8.0 | 2 | +25.84% |
| high | 2415.80 | 7.3 | 5 | +33.31% |
| high | 2276.12 | 7.0 | 3 | +25.60% |
| low | 2307.41 | 6.9 | 3 | +27.33% |
| low | 2251.24 | 6.9 | 4 | +24.23% |
| low | 2226.61 | 6.9 | 5 | +22.87% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
