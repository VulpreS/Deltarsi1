# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-23T09:00:00+00:00; **9430** closed candles.

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

### All first fades — 1311 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1310 | 50.7% | +0.044% | +1.065% | -1.062% |
| 12h | 1310 | 50.8% | +0.029% | +1.530% | -1.544% |
| 24h | 1309 | 51.6% | +0.024% | +2.226% | -2.254% |
| 48h | 1307 | 50.7% | -0.023% | +3.224% | -3.316% |
| 72h | 1305 | 53.0% | +0.082% | +3.962% | -4.087% |
| 120h | 1299 | 52.1% | -0.056% | +5.230% | -5.278% |
| 168h | 1289 | 51.0% | -0.045% | +6.179% | -6.146% |

### First fades near liquidity — 1065 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1064 | 50.3% | +0.017% | +0.995% | -1.017% |
| 12h | 1064 | 51.2% | -0.000% | +1.450% | -1.499% |
| 24h | 1063 | 53.2% | +0.085% | +2.143% | -2.127% |
| 48h | 1062 | 51.0% | +0.033% | +3.144% | -3.163% |
| 72h | 1062 | 52.4% | -0.003% | +3.852% | -3.980% |
| 120h | 1059 | 51.9% | -0.125% | +5.134% | -5.218% |
| 168h | 1055 | 52.0% | +0.058% | +6.138% | -6.010% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 283 | 51.9% | -0.426% | +5.247% | -5.469% |
| 168h | 280 | 50.4% | -0.212% | +6.178% | -6.296% |

### Near or swept — 1082 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1081 | 50.5% | +0.024% | +1.006% | -1.015% |
| 12h | 1081 | 51.0% | -0.011% | +1.455% | -1.506% |
| 24h | 1080 | 53.1% | +0.069% | +2.145% | -2.143% |
| 48h | 1079 | 50.7% | +0.000% | +3.137% | -3.190% |
| 72h | 1079 | 52.2% | -0.031% | +3.843% | -4.020% |
| 120h | 1076 | 51.9% | -0.122% | +5.139% | -5.252% |
| 168h | 1071 | 51.8% | +0.073% | +6.157% | -6.042% |

### Away from liquidity — 229 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 229 | 51.5% | +0.137% | +1.346% | -1.283% |
| 12h | 229 | 50.2% | +0.217% | +1.883% | -1.724% |
| 24h | 229 | 45.0% | -0.191% | +2.609% | -2.773% |
| 48h | 228 | 50.4% | -0.133% | +3.635% | -3.916% |
| 72h | 226 | 57.1% | +0.621% | +4.532% | -4.409% |
| 120h | 223 | 53.4% | +0.260% | +5.671% | -5.404% |
| 168h | 218 | 47.2% | -0.624% | +6.292% | -6.659% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +39.69% |
| low | 2235.38 | 12.1 | 8 | +29.71% |
| low | 2355.61 | 11.2 | 5 | +36.68% |
| low | 2294.98 | 10.5 | 4 | +33.17% |
| low | 2319.21 | 9.9 | 5 | +34.57% |
| high | 2445.95 | 8.4 | 5 | +41.92% |
| low | 2280.48 | 8.0 | 2 | +32.32% |
| high | 2276.12 | 7.0 | 3 | +32.07% |
| low | 2307.41 | 6.9 | 3 | +33.89% |
| low | 2251.24 | 6.9 | 4 | +30.63% |
| low | 2226.61 | 6.9 | 5 | +29.20% |
| low | 2209.38 | 6.9 | 4 | +28.20% |
| high | 2306.04 | 6.7 | 4 | +33.81% |
| low | 1751.09 | 6.6 | 2 | +1.61% |
| high | 2389.93 | 6.4 | 3 | +38.67% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
