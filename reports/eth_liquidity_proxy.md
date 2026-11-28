# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-28T09:00:00+00:00; **9550** closed candles.

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

### All first fades — 1325 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1324 | 50.6% | +0.047% | +1.071% | -1.063% |
| 12h | 1324 | 50.9% | +0.035% | +1.537% | -1.547% |
| 24h | 1323 | 51.6% | +0.027% | +2.232% | -2.261% |
| 48h | 1319 | 50.9% | -0.007% | +3.231% | -3.332% |
| 72h | 1315 | 53.1% | +0.095% | +3.979% | -4.098% |
| 120h | 1311 | 52.0% | -0.053% | +5.260% | -5.299% |
| 168h | 1307 | 51.2% | -0.027% | +6.235% | -6.156% |

### First fades near liquidity — 1078 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1077 | 50.1% | +0.019% | +1.002% | -1.018% |
| 12h | 1077 | 51.3% | +0.006% | +1.457% | -1.504% |
| 24h | 1076 | 53.1% | +0.086% | +2.150% | -2.139% |
| 48h | 1072 | 51.4% | +0.054% | +3.150% | -3.181% |
| 72h | 1068 | 52.4% | +0.002% | +3.853% | -3.993% |
| 120h | 1065 | 51.7% | -0.137% | +5.132% | -5.249% |
| 168h | 1062 | 51.8% | +0.036% | +6.133% | -6.049% |

### First fades with liquidity sweep — 286 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 286 | 50.7% | +0.076% | +1.181% | -1.103% |
| 12h | 286 | 53.1% | +0.000% | +1.608% | -1.601% |
| 24h | 285 | 53.7% | +0.138% | +2.491% | -2.316% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 284 | 51.8% | -0.434% | +5.246% | -5.494% |
| 168h | 284 | 50.4% | -0.211% | +6.227% | -6.311% |

### Near or swept — 1095 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1094 | 50.4% | +0.027% | +1.012% | -1.017% |
| 12h | 1094 | 51.0% | -0.005% | +1.462% | -1.511% |
| 24h | 1093 | 53.0% | +0.070% | +2.151% | -2.155% |
| 48h | 1089 | 51.1% | +0.021% | +3.143% | -3.207% |
| 72h | 1085 | 52.2% | -0.026% | +3.844% | -4.033% |
| 120h | 1082 | 51.7% | -0.134% | +5.138% | -5.282% |
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
| 168h | 228 | 49.1% | -0.418% | +6.589% | -6.536% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +45.62% |
| low | 2235.38 | 12.1 | 8 | +35.21% |
| low | 2319.21 | 9.9 | 5 | +40.28% |
| high | 2445.95 | 8.4 | 5 | +47.95% |
| high | 1844.37 | 8.0 | 5 | +11.56% |
| low | 2280.48 | 8.0 | 2 | +37.94% |
| high | 2276.12 | 7.0 | 3 | +37.68% |
| low | 2307.41 | 6.9 | 3 | +39.57% |
| low | 2251.24 | 6.9 | 4 | +36.17% |
| low | 2226.61 | 6.9 | 5 | +34.68% |
| low | 2209.38 | 6.9 | 4 | +33.64% |
| low | 1633.66 | 6.7 | 2 | -1.19% |
| high | 2306.04 | 6.7 | 4 | +39.49% |
| low | 1751.09 | 6.6 | 2 | +5.92% |
| high | 2259.45 | 6.3 | 7 | +36.67% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
