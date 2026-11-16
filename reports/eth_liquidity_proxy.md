# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-16T08:00:00+00:00; **9261** closed candles.

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

### All first fades — 1289 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1288 | 50.4% | +0.042% | +1.057% | -1.061% |
| 12h | 1288 | 50.8% | +0.027% | +1.518% | -1.539% |
| 24h | 1286 | 51.7% | +0.023% | +2.209% | -2.246% |
| 48h | 1282 | 50.5% | -0.029% | +3.204% | -3.304% |
| 72h | 1279 | 52.9% | +0.089% | +3.942% | -4.061% |
| 120h | 1275 | 52.2% | -0.066% | +5.192% | -5.246% |
| 168h | 1273 | 51.2% | -0.004% | +6.166% | -6.090% |

### First fades near liquidity — 1055 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1055 | 50.2% | +0.017% | +0.991% | -1.017% |
| 12h | 1055 | 51.3% | +0.007% | +1.446% | -1.492% |
| 24h | 1055 | 53.3% | +0.099% | +2.144% | -2.112% |
| 48h | 1053 | 51.4% | +0.066% | +3.152% | -3.133% |
| 72h | 1053 | 52.7% | +0.033% | +3.865% | -3.934% |
| 120h | 1051 | 52.1% | -0.111% | +5.133% | -5.183% |
| 168h | 1050 | 52.2% | +0.089% | +6.147% | -5.972% |

### First fades with liquidity sweep — 280 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 280 | 50.4% | +0.058% | +1.167% | -1.114% |
| 12h | 280 | 53.2% | -0.019% | +1.591% | -1.610% |
| 24h | 280 | 53.2% | +0.115% | +2.473% | -2.331% |
| 48h | 280 | 50.7% | +0.012% | +3.427% | -3.480% |
| 72h | 280 | 51.4% | -0.192% | +4.033% | -4.262% |
| 120h | 279 | 52.0% | -0.437% | +5.205% | -5.432% |
| 168h | 279 | 50.5% | -0.169% | +6.199% | -6.264% |

### Near or swept — 1071 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1071 | 50.4% | +0.024% | +1.002% | -1.015% |
| 12h | 1071 | 51.1% | -0.003% | +1.452% | -1.499% |
| 24h | 1071 | 53.1% | +0.081% | +2.144% | -2.130% |
| 48h | 1069 | 51.0% | +0.030% | +3.143% | -3.162% |
| 72h | 1069 | 52.4% | +0.002% | +3.856% | -3.977% |
| 120h | 1066 | 52.1% | -0.105% | +5.133% | -5.212% |
| 168h | 1065 | 52.0% | +0.115% | +6.170% | -5.996% |

### Away from liquidity — 218 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 217 | 50.2% | +0.126% | +1.326% | -1.288% |
| 12h | 217 | 49.3% | +0.173% | +1.845% | -1.736% |
| 24h | 215 | 44.7% | -0.267% | +2.536% | -2.824% |
| 48h | 213 | 48.4% | -0.327% | +3.510% | -4.019% |
| 72h | 210 | 55.7% | +0.533% | +4.382% | -4.486% |
| 120h | 209 | 53.1% | +0.135% | +5.496% | -5.416% |
| 168h | 208 | 47.1% | -0.610% | +6.143% | -6.573% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +40.11% |
| low | 2407.38 | 23.5 | 11 | +33.29% |
| low | 2484.94 | 15.3 | 11 | +37.59% |
| low | 2432.00 | 15.0 | 11 | +34.66% |
| low | 2235.38 | 12.1 | 8 | +23.77% |
| low | 2355.61 | 11.2 | 5 | +30.43% |
| low | 2294.98 | 10.5 | 4 | +27.07% |
| low | 2319.21 | 9.9 | 5 | +28.41% |
| high | 2445.95 | 8.4 | 5 | +35.43% |
| low | 2280.48 | 8.0 | 2 | +26.27% |
| high | 2415.80 | 7.3 | 5 | +33.76% |
| high | 2276.12 | 7.0 | 3 | +26.03% |
| low | 2307.41 | 6.9 | 3 | +27.76% |
| low | 2251.24 | 6.9 | 4 | +24.65% |
| low | 2226.61 | 6.9 | 5 | +23.29% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
