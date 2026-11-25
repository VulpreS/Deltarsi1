# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-25T10:00:00+00:00; **9479** closed candles.

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

### All first fades — 1316 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1314 | 50.7% | +0.044% | +1.065% | -1.062% |
| 12h | 1314 | 50.8% | +0.027% | +1.530% | -1.548% |
| 24h | 1313 | 51.6% | +0.025% | +2.226% | -2.256% |
| 48h | 1311 | 50.6% | -0.024% | +3.222% | -3.332% |
| 72h | 1310 | 53.1% | +0.092% | +3.973% | -4.098% |
| 120h | 1305 | 52.0% | -0.058% | +5.248% | -5.291% |
| 168h | 1299 | 51.1% | -0.035% | +6.211% | -6.151% |

### First fades near liquidity — 1069 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1067 | 50.2% | +0.015% | +0.994% | -1.017% |
| 12h | 1067 | 51.1% | -0.004% | +1.448% | -1.505% |
| 24h | 1066 | 53.1% | +0.084% | +2.142% | -2.132% |
| 48h | 1065 | 51.1% | +0.036% | +3.143% | -3.178% |
| 72h | 1064 | 52.4% | +0.000% | +3.849% | -3.990% |
| 120h | 1062 | 51.8% | -0.137% | +5.132% | -5.240% |
| 168h | 1059 | 51.9% | +0.046% | +6.138% | -6.030% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 284 | 51.8% | -0.434% | +5.246% | -5.494% |
| 168h | 283 | 50.5% | -0.198% | +6.231% | -6.289% |

### Near or swept — 1086 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1084 | 50.5% | +0.023% | +1.005% | -1.015% |
| 12h | 1084 | 50.8% | -0.015% | +1.453% | -1.512% |
| 24h | 1083 | 53.0% | +0.068% | +2.143% | -2.148% |
| 48h | 1082 | 50.7% | +0.004% | +3.135% | -3.204% |
| 72h | 1081 | 52.2% | -0.028% | +3.841% | -4.030% |
| 120h | 1079 | 51.7% | -0.134% | +5.137% | -5.274% |
| 168h | 1076 | 51.8% | +0.065% | +6.165% | -6.057% |

### Away from liquidity — 230 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 230 | 51.7% | +0.145% | +1.350% | -1.279% |
| 12h | 230 | 50.4% | +0.225% | +1.893% | -1.719% |
| 24h | 230 | 45.2% | -0.176% | +2.617% | -2.763% |
| 48h | 229 | 50.2% | -0.155% | +3.631% | -3.938% |
| 72h | 229 | 57.2% | +0.656% | +4.599% | -4.419% |
| 120h | 226 | 53.5% | +0.305% | +5.779% | -5.377% |
| 168h | 223 | 48.0% | -0.519% | +6.433% | -6.605% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +46.01% |
| low | 2235.38 | 12.1 | 8 | +35.58% |
| low | 2355.61 | 11.2 | 5 | +42.87% |
| low | 2294.98 | 10.5 | 4 | +39.20% |
| low | 2319.21 | 9.9 | 5 | +40.67% |
| high | 2445.95 | 8.4 | 5 | +48.35% |
| high | 1844.37 | 8.0 | 5 | +11.87% |
| low | 2280.48 | 8.0 | 2 | +38.32% |
| high | 2276.12 | 7.0 | 3 | +38.05% |
| low | 2307.41 | 6.9 | 3 | +39.95% |
| low | 2251.24 | 6.9 | 4 | +36.54% |
| low | 2226.61 | 6.9 | 5 | +35.05% |
| low | 2209.38 | 6.9 | 4 | +34.00% |
| high | 2306.04 | 6.7 | 4 | +39.87% |
| low | 1751.09 | 6.6 | 2 | +6.21% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
