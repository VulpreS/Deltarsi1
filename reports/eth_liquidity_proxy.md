# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-18T09:00:00+00:00; **9310** closed candles.

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

### All first fades — 1299 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1297 | 50.6% | +0.042% | +1.059% | -1.062% |
| 12h | 1297 | 50.7% | +0.029% | +1.523% | -1.538% |
| 24h | 1295 | 51.7% | +0.025% | +2.215% | -2.242% |
| 48h | 1289 | 50.5% | -0.030% | +3.201% | -3.311% |
| 72h | 1286 | 52.8% | +0.080% | +3.938% | -4.075% |
| 120h | 1279 | 52.2% | -0.078% | +5.192% | -5.265% |
| 168h | 1275 | 51.2% | -0.003% | +6.173% | -6.094% |

### First fades near liquidity — 1059 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1058 | 50.4% | +0.019% | +0.995% | -1.015% |
| 12h | 1058 | 51.4% | +0.011% | +1.451% | -1.489% |
| 24h | 1057 | 53.4% | +0.101% | +2.147% | -2.110% |
| 48h | 1055 | 51.3% | +0.061% | +3.149% | -3.139% |
| 72h | 1055 | 52.6% | +0.028% | +3.861% | -3.939% |
| 120h | 1053 | 52.1% | -0.110% | +5.139% | -5.191% |
| 168h | 1051 | 52.1% | +0.077% | +6.143% | -5.982% |

### First fades with liquidity sweep — 283 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 282 | 50.7% | +0.062% | +1.166% | -1.112% |
| 12h | 282 | 53.2% | -0.012% | +1.598% | -1.605% |
| 24h | 282 | 53.5% | +0.126% | +2.485% | -2.321% |
| 48h | 280 | 50.7% | +0.012% | +3.427% | -3.480% |
| 72h | 280 | 51.4% | -0.192% | +4.033% | -4.262% |
| 120h | 280 | 51.8% | -0.476% | +5.189% | -5.467% |
| 168h | 279 | 50.5% | -0.169% | +6.199% | -6.264% |

### Near or swept — 1076 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1075 | 50.6% | +0.026% | +1.005% | -1.014% |
| 12h | 1075 | 51.2% | +0.000% | +1.457% | -1.497% |
| 24h | 1074 | 53.3% | +0.085% | +2.148% | -2.127% |
| 48h | 1071 | 50.9% | +0.025% | +3.140% | -3.167% |
| 72h | 1071 | 52.3% | -0.002% | +3.851% | -3.983% |
| 120h | 1069 | 52.0% | -0.114% | +5.135% | -5.229% |
| 168h | 1066 | 52.0% | +0.103% | +6.166% | -6.006% |

### Away from liquidity — 223 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 222 | 50.5% | +0.117% | +1.319% | -1.291% |
| 12h | 222 | 48.6% | +0.169% | +1.843% | -1.741% |
| 24h | 221 | 44.3% | -0.266% | +2.539% | -2.801% |
| 48h | 218 | 48.6% | -0.301% | +3.501% | -4.013% |
| 72h | 215 | 55.3% | +0.493% | +4.369% | -4.537% |
| 120h | 210 | 52.9% | +0.105% | +5.483% | -5.446% |
| 168h | 209 | 47.4% | -0.541% | +6.207% | -6.541% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +39.52% |
| low | 2407.38 | 23.5 | 11 | +32.73% |
| low | 2484.94 | 15.3 | 11 | +37.01% |
| low | 2432.00 | 15.0 | 11 | +34.09% |
| low | 2235.38 | 12.1 | 8 | +23.25% |
| low | 2355.61 | 11.2 | 5 | +29.88% |
| low | 2294.98 | 10.5 | 4 | +26.53% |
| low | 2319.21 | 9.9 | 5 | +27.87% |
| high | 2445.95 | 8.4 | 5 | +34.86% |
| low | 2280.48 | 8.0 | 2 | +25.73% |
| high | 2415.80 | 7.3 | 5 | +33.20% |
| high | 2276.12 | 7.0 | 3 | +25.49% |
| low | 2307.41 | 6.9 | 3 | +27.22% |
| low | 2251.24 | 6.9 | 4 | +24.12% |
| low | 2226.61 | 6.9 | 5 | +22.76% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
