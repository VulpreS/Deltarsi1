# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-19T09:00:00+00:00; **9334** closed candles.

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

### All first fades — 1302 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1302 | 50.7% | +0.046% | +1.063% | -1.059% |
| 12h | 1300 | 50.8% | +0.030% | +1.525% | -1.539% |
| 24h | 1299 | 51.7% | +0.022% | +2.214% | -2.244% |
| 48h | 1295 | 50.7% | -0.021% | +3.208% | -3.301% |
| 72h | 1289 | 52.9% | +0.084% | +3.938% | -4.073% |
| 120h | 1282 | 52.1% | -0.085% | +5.189% | -5.271% |
| 168h | 1277 | 51.2% | -0.002% | +6.177% | -6.099% |

### First fades near liquidity — 1061 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1061 | 50.4% | +0.021% | +0.996% | -1.013% |
| 12h | 1059 | 51.4% | +0.009% | +1.450% | -1.492% |
| 24h | 1059 | 53.3% | +0.098% | +2.145% | -2.114% |
| 48h | 1057 | 51.3% | +0.062% | +3.151% | -3.136% |
| 72h | 1055 | 52.6% | +0.028% | +3.861% | -3.939% |
| 120h | 1053 | 52.1% | -0.110% | +5.139% | -5.191% |
| 168h | 1053 | 52.1% | +0.077% | +6.147% | -5.989% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 283 | 53.0% | -0.021% | +1.594% | -1.614% |
| 24h | 283 | 53.4% | +0.123% | +2.478% | -2.328% |
| 48h | 282 | 51.1% | +0.030% | +3.439% | -3.461% |
| 72h | 280 | 51.4% | -0.192% | +4.033% | -4.262% |
| 120h | 280 | 51.8% | -0.476% | +5.189% | -5.467% |
| 168h | 279 | 50.5% | -0.169% | +6.199% | -6.264% |

### Near or swept — 1078 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1078 | 50.6% | +0.029% | +1.006% | -1.012% |
| 12h | 1076 | 51.1% | -0.002% | +1.456% | -1.499% |
| 24h | 1076 | 53.2% | +0.082% | +2.147% | -2.130% |
| 48h | 1074 | 50.9% | +0.029% | +3.144% | -3.163% |
| 72h | 1071 | 52.3% | -0.002% | +3.851% | -3.983% |
| 120h | 1069 | 52.0% | -0.114% | +5.135% | -5.229% |
| 168h | 1068 | 52.0% | +0.104% | +6.171% | -6.013% |

### Away from liquidity — 224 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 224 | 50.9% | +0.130% | +1.332% | -1.284% |
| 12h | 224 | 49.1% | +0.183% | +1.857% | -1.730% |
| 24h | 223 | 44.4% | -0.268% | +2.539% | -2.795% |
| 48h | 221 | 49.3% | -0.265% | +3.520% | -3.973% |
| 72h | 218 | 56.0% | +0.510% | +4.365% | -4.515% |
| 120h | 213 | 52.6% | +0.060% | +5.461% | -5.479% |
| 168h | 209 | 47.4% | -0.541% | +6.207% | -6.541% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +40.07% |
| low | 2407.38 | 23.5 | 11 | +33.25% |
| low | 2484.94 | 15.3 | 11 | +37.55% |
| low | 2432.00 | 15.0 | 11 | +34.62% |
| low | 2235.38 | 12.1 | 8 | +23.73% |
| low | 2355.61 | 11.2 | 5 | +30.39% |
| low | 2294.98 | 10.5 | 4 | +27.03% |
| low | 2319.21 | 9.9 | 5 | +28.37% |
| high | 2445.95 | 8.4 | 5 | +35.39% |
| low | 2280.48 | 8.0 | 2 | +26.23% |
| high | 2415.80 | 7.3 | 5 | +33.72% |
| high | 2276.12 | 7.0 | 3 | +25.99% |
| low | 2307.41 | 6.9 | 3 | +27.72% |
| low | 2251.24 | 6.9 | 4 | +24.61% |
| low | 2226.61 | 6.9 | 5 | +23.25% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
