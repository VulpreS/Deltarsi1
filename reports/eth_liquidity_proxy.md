# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-27T09:00:00+00:00; **9526** closed candles.

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

### All first fades — 1323 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1322 | 50.6% | +0.045% | +1.068% | -1.063% |
| 12h | 1321 | 50.9% | +0.032% | +1.534% | -1.549% |
| 24h | 1319 | 51.7% | +0.028% | +2.229% | -2.260% |
| 48h | 1315 | 50.8% | -0.017% | +3.226% | -3.333% |
| 72h | 1313 | 53.2% | +0.097% | +3.978% | -4.098% |
| 120h | 1309 | 52.0% | -0.055% | +5.258% | -5.296% |
| 168h | 1305 | 51.1% | -0.030% | +6.224% | -6.161% |

### First fades near liquidity — 1076 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1075 | 50.1% | +0.017% | +0.998% | -1.019% |
| 12h | 1074 | 51.2% | +0.002% | +1.453% | -1.507% |
| 24h | 1072 | 53.2% | +0.087% | +2.146% | -2.138% |
| 48h | 1068 | 51.2% | +0.041% | +3.143% | -3.181% |
| 72h | 1066 | 52.5% | +0.004% | +3.851% | -3.993% |
| 120h | 1063 | 51.7% | -0.141% | +5.130% | -5.245% |
| 168h | 1062 | 51.8% | +0.036% | +6.133% | -6.049% |

### First fades with liquidity sweep — 285 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 284 | 51.8% | -0.434% | +5.246% | -5.494% |
| 168h | 284 | 50.4% | -0.211% | +6.227% | -6.311% |

### Near or swept — 1093 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1092 | 50.4% | +0.025% | +1.009% | -1.018% |
| 12h | 1091 | 51.0% | -0.009% | +1.458% | -1.513% |
| 24h | 1089 | 53.1% | +0.071% | +2.148% | -2.154% |
| 48h | 1085 | 50.9% | +0.009% | +3.136% | -3.207% |
| 72h | 1083 | 52.3% | -0.024% | +3.843% | -4.033% |
| 120h | 1080 | 51.7% | -0.137% | +5.135% | -5.279% |
| 168h | 1079 | 51.6% | +0.055% | +6.160% | -6.076% |

### Away from liquidity — 230 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 230 | 51.7% | +0.145% | +1.350% | -1.279% |
| 12h | 230 | 50.4% | +0.225% | +1.893% | -1.719% |
| 24h | 230 | 45.2% | -0.176% | +2.617% | -2.763% |
| 48h | 230 | 50.4% | -0.139% | +3.648% | -3.923% |
| 72h | 230 | 57.4% | +0.665% | +4.613% | -4.402% |
| 120h | 229 | 53.7% | +0.330% | +5.840% | -5.377% |
| 168h | 226 | 48.7% | -0.438% | +6.531% | -6.563% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +39.30% |
| low | 2235.38 | 12.1 | 8 | +29.34% |
| low | 2355.61 | 11.2 | 5 | +36.30% |
| low | 2294.98 | 10.5 | 4 | +32.79% |
| low | 2319.21 | 9.9 | 5 | +34.19% |
| high | 2445.95 | 8.4 | 5 | +41.53% |
| high | 1844.37 | 8.0 | 5 | +6.72% |
| low | 2280.48 | 8.0 | 2 | +31.95% |
| high | 2276.12 | 7.0 | 3 | +31.70% |
| low | 2307.41 | 6.9 | 3 | +33.51% |
| low | 2251.24 | 6.9 | 4 | +30.26% |
| low | 2226.61 | 6.9 | 5 | +28.84% |
| low | 2209.38 | 6.9 | 4 | +27.84% |
| high | 2306.04 | 6.7 | 4 | +33.43% |
| low | 1751.09 | 6.6 | 2 | +1.32% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
