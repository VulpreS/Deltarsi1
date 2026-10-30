# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-30T07:00:00+00:00; **8852** closed candles.

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

### All first fades — 1237 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1236 | 50.6% | +0.052% | +1.060% | -1.055% |
| 12h | 1235 | 51.0% | +0.037% | +1.528% | -1.528% |
| 24h | 1234 | 52.1% | +0.043% | +2.214% | -2.222% |
| 48h | 1229 | 50.6% | -0.051% | +3.178% | -3.287% |
| 72h | 1224 | 53.2% | +0.072% | +3.919% | -4.049% |
| 120h | 1218 | 52.1% | -0.096% | +5.165% | -5.236% |
| 168h | 1216 | 50.7% | -0.077% | +6.102% | -6.069% |

### First fades near liquidity — 1021 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1020 | 50.7% | +0.033% | +1.005% | -1.011% |
| 12h | 1019 | 51.4% | +0.029% | +1.467% | -1.483% |
| 24h | 1018 | 53.6% | +0.126% | +2.158% | -2.088% |
| 48h | 1013 | 51.3% | +0.039% | +3.130% | -3.120% |
| 72h | 1009 | 52.9% | +0.019% | +3.845% | -3.920% |
| 120h | 1005 | 52.2% | -0.114% | +5.126% | -5.158% |
| 168h | 1003 | 51.9% | +0.058% | +6.104% | -5.934% |

### First fades with liquidity sweep — 270 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 270 | 50.4% | +0.061% | +1.167% | -1.115% |
| 12h | 270 | 53.3% | -0.011% | +1.597% | -1.601% |
| 24h | 270 | 53.0% | +0.055% | +2.422% | -2.345% |
| 48h | 269 | 50.2% | -0.099% | +3.348% | -3.503% |
| 72h | 269 | 51.3% | -0.253% | +3.971% | -4.296% |
| 120h | 268 | 52.2% | -0.566% | +5.083% | -5.493% |
| 168h | 268 | 50.4% | -0.314% | +6.036% | -6.301% |

### Near or swept — 1035 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1034 | 50.8% | +0.036% | +1.010% | -1.011% |
| 12h | 1033 | 51.2% | +0.019% | +1.468% | -1.487% |
| 24h | 1032 | 53.5% | +0.106% | +2.154% | -2.105% |
| 48h | 1027 | 50.9% | +0.001% | +3.117% | -3.146% |
| 72h | 1023 | 52.6% | -0.010% | +3.832% | -3.958% |
| 120h | 1019 | 52.1% | -0.121% | +5.116% | -5.193% |
| 168h | 1017 | 51.7% | +0.068% | +6.113% | -5.966% |

### Away from liquidity — 202 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 202 | 49.5% | +0.133% | +1.314% | -1.276% |
| 12h | 202 | 50.0% | +0.131% | +1.833% | -1.739% |
| 24h | 202 | 45.0% | -0.281% | +2.518% | -2.824% |
| 48h | 202 | 49.0% | -0.317% | +3.493% | -4.003% |
| 72h | 201 | 56.2% | +0.490% | +4.359% | -4.512% |
| 120h | 199 | 52.3% | +0.030% | +5.415% | -5.454% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +13.11% |
| high | 2703.78 | 22.2 | 17 | +20.86% |
| high | 2518.93 | 22.2 | 12 | +12.60% |
| low | 2407.44 | 21.9 | 9 | +7.62% |
| low | 2669.15 | 19.9 | 12 | +19.31% |
| low | 2484.94 | 15.3 | 11 | +11.08% |
| low | 2432.00 | 15.0 | 11 | +8.71% |
| high | 2721.59 | 13.9 | 7 | +21.66% |
| low | 2680.62 | 13.5 | 8 | +19.83% |
| high | 2748.49 | 12.6 | 5 | +22.86% |
| low | 2355.61 | 11.2 | 5 | +5.30% |
| high | 2736.32 | 10.6 | 4 | +22.32% |
| low | 2294.98 | 10.5 | 4 | +2.59% |
| low | 2319.21 | 9.9 | 5 | +3.67% |
| low | 2473.84 | 9.8 | 7 | +10.58% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
