# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-31T07:00:00+00:00; **8876** closed candles.

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

### All first fades — 1240 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1239 | 50.6% | +0.052% | +1.059% | -1.054% |
| 12h | 1238 | 51.0% | +0.036% | +1.526% | -1.530% |
| 24h | 1237 | 52.1% | +0.039% | +2.211% | -2.227% |
| 48h | 1234 | 50.6% | -0.052% | +3.185% | -3.291% |
| 72h | 1229 | 53.4% | +0.089% | +3.931% | -4.042% |
| 120h | 1221 | 52.1% | -0.099% | +5.163% | -5.236% |
| 168h | 1217 | 50.8% | -0.071% | +6.104% | -6.064% |

### First fades near liquidity — 1022 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1022 | 50.7% | +0.033% | +1.005% | -1.011% |
| 12h | 1022 | 51.4% | +0.027% | +1.465% | -1.485% |
| 24h | 1021 | 53.6% | +0.120% | +2.156% | -2.094% |
| 48h | 1018 | 51.3% | +0.038% | +3.138% | -3.125% |
| 72h | 1013 | 53.1% | +0.037% | +3.858% | -3.913% |
| 120h | 1007 | 52.1% | -0.122% | +5.121% | -5.161% |
| 168h | 1004 | 52.0% | +0.066% | +6.108% | -5.929% |

### First fades with liquidity sweep — 271 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 271 | 50.6% | +0.061% | +1.167% | -1.114% |
| 12h | 271 | 53.5% | -0.009% | +1.595% | -1.598% |
| 24h | 270 | 53.0% | +0.055% | +2.422% | -2.345% |
| 48h | 270 | 50.0% | -0.109% | +3.346% | -3.512% |
| 72h | 269 | 51.3% | -0.253% | +3.971% | -4.296% |
| 120h | 268 | 52.2% | -0.566% | +5.083% | -5.493% |
| 168h | 268 | 50.4% | -0.314% | +6.036% | -6.301% |

### Near or swept — 1036 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1036 | 50.8% | +0.036% | +1.010% | -1.011% |
| 12h | 1036 | 51.2% | +0.017% | +1.466% | -1.489% |
| 24h | 1035 | 53.4% | +0.101% | +2.151% | -2.110% |
| 48h | 1032 | 50.9% | -0.000% | +3.125% | -3.151% |
| 72h | 1027 | 52.8% | +0.008% | +3.845% | -3.951% |
| 120h | 1021 | 52.0% | -0.128% | +5.112% | -5.196% |
| 168h | 1018 | 51.8% | +0.075% | +6.116% | -5.960% |

### Away from liquidity — 204 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 203 | 49.8% | +0.133% | +1.310% | -1.271% |
| 12h | 202 | 50.0% | +0.131% | +1.833% | -1.739% |
| 24h | 202 | 45.0% | -0.281% | +2.518% | -2.824% |
| 48h | 202 | 49.0% | -0.317% | +3.493% | -4.003% |
| 72h | 202 | 56.4% | +0.504% | +4.368% | -4.505% |
| 120h | 200 | 52.5% | +0.053% | +5.423% | -5.439% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +12.76% |
| high | 2703.78 | 22.2 | 17 | +20.49% |
| high | 2518.93 | 22.2 | 12 | +12.25% |
| low | 2407.44 | 21.9 | 9 | +7.28% |
| low | 2669.15 | 19.9 | 12 | +18.94% |
| low | 2484.94 | 15.3 | 11 | +10.73% |
| low | 2432.00 | 15.0 | 11 | +8.38% |
| high | 2721.59 | 13.9 | 7 | +21.28% |
| low | 2680.62 | 13.5 | 8 | +19.46% |
| high | 2748.49 | 12.6 | 5 | +22.48% |
| low | 2355.61 | 11.2 | 5 | +4.97% |
| high | 2736.32 | 10.6 | 4 | +21.94% |
| low | 2294.98 | 10.5 | 4 | +2.27% |
| low | 2319.21 | 9.9 | 5 | +3.35% |
| low | 2473.84 | 9.8 | 7 | +10.24% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
