# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-12T08:00:00+00:00; **9165** closed candles.

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

### All first fades — 1277 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1276 | 50.5% | +0.050% | +1.057% | -1.049% |
| 12h | 1276 | 51.0% | +0.039% | +1.521% | -1.521% |
| 24h | 1275 | 51.8% | +0.037% | +2.209% | -2.219% |
| 48h | 1274 | 50.7% | -0.007% | +3.204% | -3.278% |
| 72h | 1273 | 53.0% | +0.101% | +3.941% | -4.038% |
| 120h | 1266 | 52.2% | -0.076% | +5.171% | -5.234% |
| 168h | 1260 | 51.3% | +0.001% | +6.137% | -6.053% |

### First fades near liquidity — 1053 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1052 | 50.4% | +0.023% | +0.993% | -1.010% |
| 12h | 1052 | 51.4% | +0.017% | +1.448% | -1.482% |
| 24h | 1051 | 53.3% | +0.106% | +2.147% | -2.099% |
| 48h | 1050 | 51.4% | +0.071% | +3.152% | -3.128% |
| 72h | 1050 | 52.8% | +0.042% | +3.866% | -3.919% |
| 120h | 1047 | 52.2% | -0.085% | +5.140% | -5.157% |
| 168h | 1041 | 52.4% | +0.134% | +6.151% | -5.923% |

### First fades with liquidity sweep — 279 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 279 | 50.2% | +0.058% | +1.169% | -1.117% |
| 12h | 279 | 53.4% | -0.000% | +1.595% | -1.594% |
| 24h | 279 | 53.4% | +0.129% | +2.480% | -2.318% |
| 48h | 279 | 50.9% | +0.043% | +3.437% | -3.455% |
| 72h | 279 | 51.6% | -0.157% | +4.046% | -4.223% |
| 120h | 278 | 51.8% | -0.487% | +5.170% | -5.451% |
| 168h | 277 | 50.5% | -0.185% | +6.159% | -6.252% |

### Near or swept — 1068 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1067 | 50.5% | +0.030% | +1.004% | -1.009% |
| 12h | 1067 | 51.3% | +0.012% | +1.456% | -1.486% |
| 24h | 1066 | 53.2% | +0.091% | +2.148% | -2.113% |
| 48h | 1065 | 51.1% | +0.043% | +3.145% | -3.151% |
| 72h | 1065 | 52.5% | +0.020% | +3.859% | -3.953% |
| 120h | 1061 | 52.1% | -0.092% | +5.131% | -5.191% |
| 168h | 1055 | 52.1% | +0.142% | +6.158% | -5.953% |

### Away from liquidity — 209 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 209 | 50.2% | +0.150% | +1.326% | -1.254% |
| 12h | 209 | 49.8% | +0.178% | +1.852% | -1.703% |
| 24h | 209 | 45.0% | -0.242% | +2.516% | -2.760% |
| 48h | 209 | 48.8% | -0.264% | +3.507% | -3.929% |
| 72h | 208 | 55.8% | +0.518% | +4.359% | -4.473% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +23.42% |
| low | 2407.38 | 23.5 | 11 | +17.42% |
| high | 2518.93 | 22.2 | 12 | +22.86% |
| low | 2484.94 | 15.3 | 11 | +21.20% |
| low | 2432.00 | 15.0 | 11 | +18.62% |
| low | 2235.38 | 12.1 | 8 | +9.03% |
| low | 2355.61 | 11.2 | 5 | +14.90% |
| low | 2294.98 | 10.5 | 4 | +11.94% |
| low | 2319.21 | 9.9 | 5 | +13.12% |
| high | 2445.95 | 8.4 | 5 | +19.30% |
| low | 2280.48 | 8.0 | 2 | +11.23% |
| high | 2415.80 | 7.3 | 5 | +17.83% |
| high | 2276.12 | 7.0 | 3 | +11.02% |
| low | 2307.41 | 6.9 | 3 | +12.54% |
| low | 2251.24 | 6.9 | 4 | +9.80% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
