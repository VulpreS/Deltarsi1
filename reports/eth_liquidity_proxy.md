# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-26T11:00:00+00:00; **8760** closed candles.

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

### All first fades — 1221 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1221 | 50.5% | +0.051% | +1.060% | -1.057% |
| 12h | 1220 | 51.1% | +0.041% | +1.530% | -1.531% |
| 24h | 1219 | 52.1% | +0.039% | +2.217% | -2.226% |
| 48h | 1217 | 50.5% | -0.061% | +3.185% | -3.301% |
| 72h | 1216 | 53.1% | +0.066% | +3.923% | -4.063% |
| 120h | 1212 | 52.2% | -0.096% | +5.176% | -5.247% |
| 168h | 1203 | 50.6% | -0.089% | +6.114% | -6.091% |

### First fades near liquidity — 1007 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1007 | 50.6% | +0.030% | +1.003% | -1.013% |
| 12h | 1006 | 51.6% | +0.031% | +1.467% | -1.485% |
| 24h | 1006 | 53.6% | +0.120% | +2.159% | -2.091% |
| 48h | 1004 | 51.2% | +0.028% | +3.131% | -3.132% |
| 72h | 1003 | 52.8% | +0.017% | +3.850% | -3.933% |
| 120h | 999 | 52.4% | -0.114% | +5.139% | -5.171% |
| 168h | 992 | 51.9% | +0.052% | +6.117% | -5.958% |

### First fades with liquidity sweep — 268 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 268 | 50.4% | +0.060% | +1.171% | -1.119% |
| 12h | 268 | 53.4% | -0.019% | +1.597% | -1.608% |
| 24h | 268 | 53.0% | +0.064% | +2.423% | -2.336% |
| 48h | 268 | 50.0% | -0.102% | +3.350% | -3.511% |
| 72h | 268 | 51.1% | -0.257% | +3.976% | -4.307% |
| 120h | 266 | 52.3% | -0.583% | +5.087% | -5.514% |
| 168h | 264 | 50.0% | -0.354% | +6.042% | -6.351% |

### Near or swept — 1021 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1021 | 50.7% | +0.034% | +1.009% | -1.013% |
| 12h | 1020 | 51.4% | +0.021% | +1.468% | -1.489% |
| 24h | 1020 | 53.4% | +0.101% | +2.154% | -2.108% |
| 48h | 1018 | 50.8% | -0.010% | +3.118% | -3.159% |
| 72h | 1017 | 52.5% | -0.013% | +3.837% | -3.972% |
| 120h | 1013 | 52.2% | -0.121% | +5.129% | -5.206% |
| 168h | 1006 | 51.7% | +0.062% | +6.125% | -5.990% |

### Away from liquidity — 200 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 200 | 49.5% | +0.139% | +1.322% | -1.279% |
| 12h | 200 | 50.0% | +0.139% | +1.846% | -1.742% |
| 24h | 199 | 45.2% | -0.275% | +2.540% | -2.835% |
| 48h | 199 | 48.7% | -0.324% | +3.526% | -4.026% |
| 72h | 199 | 56.3% | +0.467% | +4.362% | -4.531% |
| 120h | 199 | 52.3% | +0.030% | +5.415% | -5.454% |
| 168h | 197 | 45.2% | -0.860% | +6.057% | -6.608% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +8.41% |
| high | 2703.78 | 22.2 | 17 | +15.84% |
| high | 2518.93 | 22.2 | 12 | +7.92% |
| low | 2407.44 | 21.9 | 9 | +3.14% |
| low | 2669.15 | 19.9 | 12 | +14.36% |
| low | 2484.94 | 15.3 | 11 | +6.46% |
| low | 2432.00 | 15.0 | 11 | +4.20% |
| high | 2721.59 | 13.9 | 7 | +16.60% |
| low | 2680.62 | 13.5 | 8 | +14.85% |
| high | 2748.49 | 12.6 | 5 | +17.76% |
| low | 2355.84 | 10.7 | 4 | +0.93% |
| high | 2736.32 | 10.6 | 4 | +17.23% |
| low | 2473.84 | 9.8 | 7 | +5.99% |
| low | 2693.08 | 9.7 | 7 | +15.38% |
| high | 2549.53 | 9.5 | 4 | +9.23% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
