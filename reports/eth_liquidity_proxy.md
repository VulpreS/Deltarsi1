# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-01T08:00:00+00:00; **8901** closed candles.

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

### All first fades — 1244 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1244 | 50.4% | +0.050% | +1.056% | -1.052% |
| 12h | 1243 | 50.8% | +0.034% | +1.521% | -1.527% |
| 24h | 1240 | 52.0% | +0.037% | +2.207% | -2.224% |
| 48h | 1237 | 50.5% | -0.054% | +3.181% | -3.293% |
| 72h | 1235 | 53.3% | +0.088% | +3.933% | -4.045% |
| 120h | 1224 | 52.0% | -0.101% | +5.160% | -5.236% |
| 168h | 1218 | 50.7% | -0.074% | +6.101% | -6.065% |

### First fades near liquidity — 1026 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1026 | 50.5% | +0.032% | +1.002% | -1.009% |
| 12h | 1025 | 51.2% | +0.026% | +1.461% | -1.483% |
| 24h | 1022 | 53.6% | +0.120% | +2.154% | -2.093% |
| 48h | 1021 | 51.2% | +0.035% | +3.133% | -3.128% |
| 72h | 1019 | 53.0% | +0.036% | +3.861% | -3.917% |
| 120h | 1009 | 52.0% | -0.127% | +5.118% | -5.163% |
| 168h | 1005 | 51.9% | +0.062% | +6.104% | -5.930% |

### First fades with liquidity sweep — 272 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 272 | 50.4% | +0.060% | +1.163% | -1.112% |
| 12h | 272 | 53.3% | -0.011% | +1.590% | -1.596% |
| 24h | 271 | 53.1% | +0.056% | +2.417% | -2.340% |
| 48h | 270 | 50.0% | -0.109% | +3.346% | -3.512% |
| 72h | 270 | 51.1% | -0.259% | +3.968% | -4.302% |
| 120h | 269 | 52.0% | -0.575% | +5.075% | -5.496% |
| 168h | 268 | 50.4% | -0.314% | +6.036% | -6.301% |

### Near or swept — 1040 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1040 | 50.6% | +0.035% | +1.007% | -1.010% |
| 12h | 1039 | 51.0% | +0.016% | +1.462% | -1.488% |
| 24h | 1036 | 53.5% | +0.101% | +2.150% | -2.109% |
| 48h | 1035 | 50.8% | -0.003% | +3.120% | -3.154% |
| 72h | 1033 | 52.7% | +0.006% | +3.848% | -3.955% |
| 120h | 1023 | 51.9% | -0.133% | +5.108% | -5.198% |
| 168h | 1019 | 51.7% | +0.072% | +6.113% | -5.961% |

### Away from liquidity — 204 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 204 | 49.5% | +0.130% | +1.305% | -1.267% |
| 12h | 204 | 49.5% | +0.127% | +1.819% | -1.727% |
| 24h | 204 | 44.6% | -0.286% | +2.496% | -2.808% |
| 48h | 202 | 49.0% | -0.317% | +3.493% | -4.003% |
| 72h | 202 | 56.4% | +0.504% | +4.368% | -4.505% |
| 120h | 201 | 52.7% | +0.064% | +5.428% | -5.426% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +11.16% |
| high | 2703.78 | 22.2 | 17 | +18.77% |
| high | 2518.93 | 22.2 | 12 | +10.65% |
| low | 2407.44 | 21.9 | 9 | +5.75% |
| low | 2669.15 | 19.9 | 12 | +17.25% |
| low | 2484.94 | 15.3 | 11 | +9.16% |
| low | 2432.00 | 15.0 | 11 | +6.83% |
| high | 2721.59 | 13.9 | 7 | +19.55% |
| low | 2680.62 | 13.5 | 8 | +17.75% |
| low | 2355.61 | 11.2 | 5 | +3.48% |
| high | 2736.32 | 10.6 | 4 | +20.20% |
| low | 2294.98 | 10.5 | 4 | +0.81% |
| low | 2319.21 | 9.9 | 5 | +1.88% |
| low | 2473.84 | 9.8 | 7 | +8.67% |
| low | 2693.08 | 9.7 | 7 | +18.30% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
