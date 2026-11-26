# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-26T09:00:00+00:00; **9502** closed candles.

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

### All first fades — 1319 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1318 | 50.6% | +0.044% | +1.066% | -1.065% |
| 12h | 1317 | 50.9% | +0.032% | +1.534% | -1.550% |
| 24h | 1315 | 51.6% | +0.025% | +2.227% | -2.259% |
| 48h | 1313 | 50.7% | -0.021% | +3.224% | -3.332% |
| 72h | 1311 | 53.1% | +0.094% | +3.976% | -4.100% |
| 120h | 1307 | 52.1% | -0.052% | +5.260% | -5.289% |
| 168h | 1302 | 51.1% | -0.037% | +6.213% | -6.161% |

### First fades near liquidity — 1072 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1071 | 50.1% | +0.016% | +0.995% | -1.021% |
| 12h | 1070 | 51.2% | +0.002% | +1.453% | -1.508% |
| 24h | 1068 | 53.1% | +0.083% | +2.142% | -2.136% |
| 48h | 1066 | 51.1% | +0.036% | +3.142% | -3.180% |
| 72h | 1065 | 52.5% | +0.002% | +3.852% | -3.992% |
| 120h | 1062 | 51.8% | -0.137% | +5.132% | -5.240% |
| 168h | 1061 | 51.8% | +0.037% | +6.133% | -6.044% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 284 | 51.8% | -0.434% | +5.246% | -5.494% |
| 168h | 284 | 50.4% | -0.211% | +6.227% | -6.311% |

### Near or swept — 1089 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1088 | 50.4% | +0.023% | +1.006% | -1.019% |
| 12h | 1087 | 51.0% | -0.009% | +1.458% | -1.515% |
| 24h | 1085 | 53.0% | +0.067% | +2.144% | -2.152% |
| 48h | 1083 | 50.8% | +0.004% | +3.134% | -3.206% |
| 72h | 1082 | 52.2% | -0.025% | +3.844% | -4.032% |
| 120h | 1079 | 51.7% | -0.134% | +5.137% | -5.274% |
| 168h | 1078 | 51.7% | +0.056% | +6.160% | -6.071% |

### Away from liquidity — 230 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 230 | 51.7% | +0.145% | +1.350% | -1.279% |
| 12h | 230 | 50.4% | +0.225% | +1.893% | -1.719% |
| 24h | 230 | 45.2% | -0.176% | +2.617% | -2.763% |
| 48h | 230 | 50.4% | -0.139% | +3.648% | -3.923% |
| 72h | 229 | 57.2% | +0.656% | +4.599% | -4.419% |
| 120h | 228 | 53.9% | +0.333% | +5.844% | -5.361% |
| 168h | 224 | 48.2% | -0.484% | +6.464% | -6.593% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +41.29% |
| low | 2235.38 | 12.1 | 8 | +31.19% |
| low | 2355.61 | 11.2 | 5 | +38.25% |
| low | 2294.98 | 10.5 | 4 | +34.69% |
| low | 2319.21 | 9.9 | 5 | +36.11% |
| high | 2445.95 | 8.4 | 5 | +43.55% |
| high | 1844.37 | 8.0 | 5 | +8.24% |
| low | 2280.48 | 8.0 | 2 | +33.84% |
| high | 2276.12 | 7.0 | 3 | +33.58% |
| low | 2307.41 | 6.9 | 3 | +35.42% |
| low | 2251.24 | 6.9 | 4 | +32.12% |
| low | 2226.61 | 6.9 | 5 | +30.68% |
| low | 2209.38 | 6.9 | 4 | +29.67% |
| high | 2306.04 | 6.7 | 4 | +35.34% |
| low | 1751.09 | 6.6 | 2 | +2.77% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
