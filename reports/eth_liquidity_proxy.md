# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-27T06:00:00+00:00; **8779** closed candles.

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

### All first fades — 1224 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1223 | 50.5% | +0.051% | +1.060% | -1.056% |
| 12h | 1222 | 51.1% | +0.040% | +1.528% | -1.530% |
| 24h | 1221 | 52.1% | +0.040% | +2.216% | -2.225% |
| 48h | 1218 | 50.4% | -0.062% | +3.183% | -3.299% |
| 72h | 1217 | 53.2% | +0.068% | +3.924% | -4.060% |
| 120h | 1213 | 52.3% | -0.090% | +5.179% | -5.243% |
| 168h | 1206 | 50.7% | -0.087% | +6.111% | -6.089% |

### First fades near liquidity — 1009 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1009 | 50.6% | +0.031% | +1.003% | -1.012% |
| 12h | 1008 | 51.5% | +0.031% | +1.465% | -1.484% |
| 24h | 1007 | 53.5% | +0.119% | +2.157% | -2.090% |
| 48h | 1005 | 51.1% | +0.027% | +3.130% | -3.131% |
| 72h | 1004 | 52.9% | +0.020% | +3.851% | -3.930% |
| 120h | 1000 | 52.4% | -0.107% | +5.143% | -5.166% |
| 168h | 993 | 51.9% | +0.048% | +6.115% | -5.958% |

### First fades with liquidity sweep — 269 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 269 | 50.2% | +0.060% | +1.167% | -1.118% |
| 12h | 269 | 53.2% | -0.021% | +1.593% | -1.606% |
| 24h | 268 | 53.0% | +0.064% | +2.423% | -2.336% |
| 48h | 268 | 50.0% | -0.102% | +3.350% | -3.511% |
| 72h | 268 | 51.1% | -0.257% | +3.976% | -4.307% |
| 120h | 267 | 52.4% | -0.554% | +5.101% | -5.494% |
| 168h | 264 | 50.0% | -0.354% | +6.042% | -6.351% |

### Near or swept — 1023 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1023 | 50.7% | +0.034% | +1.008% | -1.012% |
| 12h | 1022 | 51.3% | +0.021% | +1.466% | -1.489% |
| 24h | 1021 | 53.4% | +0.100% | +2.153% | -2.107% |
| 48h | 1019 | 50.7% | -0.011% | +3.116% | -3.158% |
| 72h | 1018 | 52.6% | -0.010% | +3.838% | -3.968% |
| 120h | 1014 | 52.3% | -0.114% | +5.133% | -5.201% |
| 168h | 1007 | 51.6% | +0.058% | +6.124% | -5.989% |

### Away from liquidity — 201 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 200 | 49.5% | +0.139% | +1.322% | -1.279% |
| 12h | 200 | 50.0% | +0.139% | +1.846% | -1.742% |
| 24h | 200 | 45.5% | -0.267% | +2.536% | -2.828% |
| 48h | 199 | 48.7% | -0.324% | +3.526% | -4.026% |
| 72h | 199 | 56.3% | +0.467% | +4.362% | -4.531% |
| 120h | 199 | 52.3% | +0.030% | +5.415% | -5.454% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +9.76% |
| high | 2703.78 | 22.2 | 17 | +17.28% |
| high | 2518.93 | 22.2 | 12 | +9.26% |
| low | 2407.44 | 21.9 | 9 | +4.42% |
| low | 2669.15 | 19.9 | 12 | +15.78% |
| low | 2484.94 | 15.3 | 11 | +7.79% |
| low | 2432.00 | 15.0 | 11 | +5.49% |
| high | 2721.59 | 13.9 | 7 | +18.05% |
| low | 2680.62 | 13.5 | 8 | +16.27% |
| high | 2748.49 | 12.6 | 5 | +19.22% |
| low | 2355.84 | 10.7 | 4 | +2.19% |
| high | 2736.32 | 10.6 | 4 | +18.69% |
| low | 2473.84 | 9.8 | 7 | +7.30% |
| low | 2693.08 | 9.7 | 7 | +16.81% |
| high | 2549.53 | 9.5 | 4 | +10.59% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
