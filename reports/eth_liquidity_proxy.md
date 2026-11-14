# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-14T08:00:00+00:00; **9213** closed candles.

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

### All first fades — 1282 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1282 | 50.5% | +0.049% | +1.057% | -1.051% |
| 12h | 1280 | 50.9% | +0.033% | +1.519% | -1.527% |
| 24h | 1279 | 51.8% | +0.029% | +2.207% | -2.227% |
| 48h | 1277 | 50.7% | -0.011% | +3.205% | -3.282% |
| 72h | 1275 | 53.0% | +0.105% | +3.945% | -4.038% |
| 120h | 1273 | 52.2% | -0.069% | +5.184% | -5.240% |
| 168h | 1266 | 51.2% | -0.016% | +6.135% | -6.070% |

### First fades near liquidity — 1053 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1053 | 50.3% | +0.021% | +0.992% | -1.012% |
| 12h | 1053 | 51.4% | +0.016% | +1.447% | -1.484% |
| 24h | 1053 | 53.3% | +0.102% | +2.146% | -2.105% |
| 48h | 1053 | 51.4% | +0.066% | +3.152% | -3.133% |
| 72h | 1051 | 52.7% | +0.037% | +3.864% | -3.923% |
| 120h | 1050 | 52.2% | -0.101% | +5.136% | -5.172% |
| 168h | 1047 | 52.2% | +0.112% | +6.148% | -5.944% |

### First fades with liquidity sweep — 280 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 280 | 50.4% | +0.058% | +1.167% | -1.114% |
| 12h | 280 | 53.2% | -0.019% | +1.591% | -1.610% |
| 24h | 280 | 53.2% | +0.115% | +2.473% | -2.331% |
| 48h | 279 | 50.9% | +0.043% | +3.437% | -3.455% |
| 72h | 279 | 51.6% | -0.157% | +4.046% | -4.223% |
| 120h | 279 | 52.0% | -0.437% | +5.205% | -5.432% |
| 168h | 278 | 50.4% | -0.236% | +6.137% | -6.285% |

### Near or swept — 1069 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1069 | 50.5% | +0.028% | +1.003% | -1.011% |
| 12h | 1069 | 51.2% | +0.005% | +1.453% | -1.492% |
| 24h | 1069 | 53.1% | +0.084% | +2.146% | -2.122% |
| 48h | 1068 | 51.0% | +0.038% | +3.146% | -3.155% |
| 72h | 1066 | 52.4% | +0.015% | +3.858% | -3.957% |
| 120h | 1065 | 52.1% | -0.094% | +5.136% | -5.201% |
| 168h | 1061 | 52.0% | +0.120% | +6.156% | -5.974% |

### Away from liquidity — 213 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 213 | 50.2% | +0.152% | +1.329% | -1.251% |
| 12h | 211 | 49.8% | +0.173% | +1.853% | -1.707% |
| 24h | 210 | 44.8% | -0.249% | +2.517% | -2.761% |
| 48h | 209 | 48.8% | -0.264% | +3.507% | -3.929% |
| 72h | 209 | 56.0% | +0.563% | +4.390% | -4.452% |
| 120h | 208 | 52.9% | +0.062% | +5.429% | -5.442% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +33.53% |
| low | 2407.38 | 23.5 | 11 | +27.04% |
| low | 2484.94 | 15.3 | 11 | +31.13% |
| low | 2432.00 | 15.0 | 11 | +28.34% |
| low | 2235.38 | 12.1 | 8 | +17.96% |
| low | 2355.61 | 11.2 | 5 | +24.31% |
| low | 2294.98 | 10.5 | 4 | +21.11% |
| low | 2319.21 | 9.9 | 5 | +22.39% |
| high | 2445.95 | 8.4 | 5 | +29.07% |
| low | 2280.48 | 8.0 | 2 | +20.34% |
| high | 2415.80 | 7.3 | 5 | +27.48% |
| high | 2276.12 | 7.0 | 3 | +20.11% |
| low | 2307.41 | 6.9 | 3 | +21.76% |
| low | 2251.24 | 6.9 | 4 | +18.80% |
| low | 2226.61 | 6.9 | 5 | +17.50% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
