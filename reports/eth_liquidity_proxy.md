# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-13T08:00:00+00:00; **9189** closed candles.

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

### All first fades — 1279 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1278 | 50.5% | +0.048% | +1.056% | -1.051% |
| 12h | 1278 | 50.9% | +0.033% | +1.519% | -1.526% |
| 24h | 1277 | 51.8% | +0.034% | +2.208% | -2.224% |
| 48h | 1275 | 50.7% | -0.009% | +3.204% | -3.279% |
| 72h | 1274 | 53.1% | +0.109% | +3.946% | -4.035% |
| 120h | 1269 | 52.2% | -0.071% | +5.176% | -5.235% |
| 168h | 1263 | 51.1% | -0.029% | +6.123% | -6.072% |

### First fades near liquidity — 1053 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1053 | 50.3% | +0.021% | +0.992% | -1.012% |
| 12h | 1053 | 51.4% | +0.016% | +1.447% | -1.484% |
| 24h | 1053 | 53.3% | +0.102% | +2.146% | -2.105% |
| 48h | 1051 | 51.4% | +0.069% | +3.151% | -3.129% |
| 72h | 1050 | 52.8% | +0.042% | +3.866% | -3.919% |
| 120h | 1049 | 52.2% | -0.089% | +5.141% | -5.162% |
| 168h | 1044 | 52.2% | +0.096% | +6.134% | -5.945% |

### First fades with liquidity sweep — 280 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 280 | 50.4% | +0.058% | +1.167% | -1.114% |
| 12h | 280 | 53.2% | -0.019% | +1.591% | -1.610% |
| 24h | 279 | 53.4% | +0.129% | +2.480% | -2.318% |
| 48h | 279 | 50.9% | +0.043% | +3.437% | -3.455% |
| 72h | 279 | 51.6% | -0.157% | +4.046% | -4.223% |
| 120h | 278 | 51.8% | -0.487% | +5.170% | -5.451% |
| 168h | 278 | 50.4% | -0.236% | +6.137% | -6.285% |

### Near or swept — 1069 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1069 | 50.5% | +0.028% | +1.003% | -1.011% |
| 12h | 1069 | 51.2% | +0.005% | +1.453% | -1.492% |
| 24h | 1068 | 53.2% | +0.088% | +2.148% | -2.119% |
| 48h | 1066 | 51.0% | +0.041% | +3.144% | -3.151% |
| 72h | 1065 | 52.5% | +0.020% | +3.859% | -3.953% |
| 120h | 1063 | 52.1% | -0.096% | +5.131% | -5.196% |
| 168h | 1058 | 52.0% | +0.105% | +6.142% | -5.976% |

### Away from liquidity — 210 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 209 | 50.2% | +0.150% | +1.326% | -1.254% |
| 12h | 209 | 49.8% | +0.178% | +1.852% | -1.703% |
| 24h | 209 | 45.0% | -0.242% | +2.516% | -2.760% |
| 48h | 209 | 48.8% | -0.264% | +3.507% | -3.929% |
| 72h | 209 | 56.0% | +0.563% | +4.390% | -4.452% |
| 120h | 206 | 52.9% | +0.055% | +5.407% | -5.434% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +30.95% |
| low | 2407.38 | 23.5 | 11 | +24.58% |
| high | 2518.93 | 22.2 | 12 | +30.36% |
| low | 2484.94 | 15.3 | 11 | +28.60% |
| low | 2432.00 | 15.0 | 11 | +25.86% |
| low | 2235.38 | 12.1 | 8 | +15.68% |
| low | 2355.61 | 11.2 | 5 | +21.90% |
| low | 2294.98 | 10.5 | 4 | +18.77% |
| low | 2319.21 | 9.9 | 5 | +20.02% |
| high | 2445.95 | 8.4 | 5 | +26.58% |
| low | 2280.48 | 8.0 | 2 | +18.02% |
| high | 2415.80 | 7.3 | 5 | +25.02% |
| high | 2276.12 | 7.0 | 3 | +17.79% |
| low | 2307.41 | 6.9 | 3 | +19.41% |
| low | 2251.24 | 6.9 | 4 | +16.50% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
