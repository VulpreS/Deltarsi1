# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-24T11:00:00+00:00; **9456** closed candles.

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

### All first fades — 1313 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1313 | 50.7% | +0.045% | +1.066% | -1.061% |
| 12h | 1312 | 50.8% | +0.030% | +1.532% | -1.547% |
| 24h | 1311 | 51.6% | +0.024% | +2.226% | -2.257% |
| 48h | 1310 | 50.6% | -0.027% | +3.221% | -3.330% |
| 72h | 1307 | 53.1% | +0.090% | +3.977% | -4.086% |
| 120h | 1302 | 52.0% | -0.062% | +5.235% | -5.290% |
| 168h | 1295 | 51.2% | -0.025% | +6.214% | -6.134% |

### First fades near liquidity — 1066 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1066 | 50.3% | +0.016% | +0.995% | -1.016% |
| 12h | 1065 | 51.2% | -0.001% | +1.450% | -1.504% |
| 24h | 1065 | 53.1% | +0.086% | +2.143% | -2.132% |
| 48h | 1064 | 51.0% | +0.032% | +3.141% | -3.175% |
| 72h | 1062 | 52.4% | -0.003% | +3.852% | -3.980% |
| 120h | 1061 | 51.8% | -0.132% | +5.131% | -5.233% |
| 168h | 1057 | 52.0% | +0.061% | +6.145% | -6.013% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 284 | 51.8% | -0.434% | +5.246% | -5.494% |
| 168h | 282 | 50.7% | -0.168% | +6.247% | -6.258% |

### Near or swept — 1083 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1083 | 50.5% | +0.024% | +1.006% | -1.015% |
| 12h | 1082 | 50.9% | -0.012% | +1.455% | -1.511% |
| 24h | 1082 | 53.0% | +0.070% | +2.145% | -2.148% |
| 48h | 1081 | 50.7% | -0.000% | +3.134% | -3.201% |
| 72h | 1079 | 52.2% | -0.031% | +3.843% | -4.020% |
| 120h | 1078 | 51.8% | -0.129% | +5.137% | -5.267% |
| 168h | 1074 | 51.9% | +0.079% | +6.172% | -6.041% |

### Away from liquidity — 230 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 230 | 51.7% | +0.145% | +1.350% | -1.279% |
| 12h | 230 | 50.4% | +0.225% | +1.893% | -1.719% |
| 24h | 229 | 45.0% | -0.191% | +2.609% | -2.773% |
| 48h | 229 | 50.2% | -0.155% | +3.631% | -3.938% |
| 72h | 228 | 57.5% | +0.660% | +4.608% | -4.399% |
| 120h | 224 | 53.1% | +0.258% | +5.706% | -5.397% |
| 168h | 221 | 48.0% | -0.533% | +6.417% | -6.586% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +41.39% |
| low | 2235.38 | 12.1 | 8 | +31.29% |
| low | 2355.61 | 11.2 | 5 | +38.35% |
| low | 2294.98 | 10.5 | 4 | +34.79% |
| low | 2319.21 | 9.9 | 5 | +36.21% |
| high | 2445.95 | 8.4 | 5 | +43.66% |
| high | 1844.37 | 8.0 | 5 | +8.32% |
| low | 2280.48 | 8.0 | 2 | +33.94% |
| high | 2276.12 | 7.0 | 3 | +33.68% |
| low | 2307.41 | 6.9 | 3 | +35.52% |
| low | 2251.24 | 6.9 | 4 | +32.22% |
| low | 2226.61 | 6.9 | 5 | +30.77% |
| low | 2209.38 | 6.9 | 4 | +29.76% |
| high | 2306.04 | 6.7 | 4 | +35.44% |
| low | 1751.09 | 6.6 | 2 | +2.85% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
