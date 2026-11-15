# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-15T08:00:00+00:00; **9237** closed candles.

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

### All first fades — 1286 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1286 | 50.4% | +0.042% | +1.058% | -1.061% |
| 12h | 1284 | 50.9% | +0.026% | +1.518% | -1.537% |
| 24h | 1282 | 51.7% | +0.023% | +2.211% | -2.235% |
| 48h | 1279 | 50.6% | -0.024% | +3.202% | -3.294% |
| 72h | 1277 | 53.0% | +0.102% | +3.946% | -4.046% |
| 120h | 1274 | 52.3% | -0.057% | +5.195% | -5.236% |
| 168h | 1269 | 51.2% | -0.006% | +6.148% | -6.075% |

### First fades near liquidity — 1055 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1055 | 50.2% | +0.017% | +0.991% | -1.017% |
| 12h | 1054 | 51.3% | +0.008% | +1.446% | -1.491% |
| 24h | 1053 | 53.3% | +0.102% | +2.146% | -2.105% |
| 48h | 1053 | 51.4% | +0.066% | +3.152% | -3.133% |
| 72h | 1053 | 52.7% | +0.033% | +3.865% | -3.934% |
| 120h | 1050 | 52.2% | -0.101% | +5.136% | -5.172% |
| 168h | 1049 | 52.2% | +0.107% | +6.152% | -5.955% |

### First fades with liquidity sweep — 280 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 280 | 50.4% | +0.058% | +1.167% | -1.114% |
| 12h | 280 | 53.2% | -0.019% | +1.591% | -1.610% |
| 24h | 280 | 53.2% | +0.115% | +2.473% | -2.331% |
| 48h | 280 | 50.7% | +0.012% | +3.427% | -3.480% |
| 72h | 279 | 51.6% | -0.157% | +4.046% | -4.223% |
| 120h | 279 | 52.0% | -0.437% | +5.205% | -5.432% |
| 168h | 278 | 50.4% | -0.236% | +6.137% | -6.285% |

### Near or swept — 1071 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1071 | 50.4% | +0.024% | +1.002% | -1.015% |
| 12h | 1070 | 51.1% | -0.003% | +1.452% | -1.499% |
| 24h | 1069 | 53.1% | +0.084% | +2.146% | -2.122% |
| 48h | 1069 | 51.0% | +0.030% | +3.143% | -3.162% |
| 72h | 1068 | 52.4% | +0.011% | +3.859% | -3.967% |
| 120h | 1065 | 52.1% | -0.094% | +5.136% | -5.201% |
| 168h | 1063 | 52.0% | +0.115% | +6.160% | -5.985% |

### Away from liquidity — 215 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 215 | 50.2% | +0.132% | +1.335% | -1.286% |
| 12h | 214 | 49.5% | +0.167% | +1.846% | -1.729% |
| 24h | 213 | 44.6% | -0.284% | +2.537% | -2.803% |
| 48h | 210 | 48.6% | -0.300% | +3.504% | -3.965% |
| 72h | 209 | 56.0% | +0.563% | +4.390% | -4.452% |
| 120h | 209 | 53.1% | +0.135% | +5.496% | -5.416% |
| 168h | 206 | 47.1% | -0.632% | +6.088% | -6.538% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +39.69% |
| low | 2407.38 | 23.5 | 11 | +32.90% |
| low | 2484.94 | 15.3 | 11 | +37.18% |
| low | 2432.00 | 15.0 | 11 | +34.26% |
| low | 2235.38 | 12.1 | 8 | +23.40% |
| low | 2355.61 | 11.2 | 5 | +30.04% |
| low | 2294.98 | 10.5 | 4 | +26.70% |
| low | 2319.21 | 9.9 | 5 | +28.03% |
| high | 2445.95 | 8.4 | 5 | +35.03% |
| low | 2280.48 | 8.0 | 2 | +25.89% |
| high | 2415.80 | 7.3 | 5 | +33.37% |
| high | 2276.12 | 7.0 | 3 | +25.65% |
| low | 2307.41 | 6.9 | 3 | +27.38% |
| low | 2251.24 | 6.9 | 4 | +24.28% |
| low | 2226.61 | 6.9 | 5 | +22.92% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
