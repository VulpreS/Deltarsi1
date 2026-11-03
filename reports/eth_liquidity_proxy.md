# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-03T08:00:00+00:00; **8949** closed candles.

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

### All first fades — 1254 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1252 | 50.6% | +0.052% | +1.054% | -1.048% |
| 12h | 1251 | 50.9% | +0.036% | +1.519% | -1.521% |
| 24h | 1248 | 51.8% | +0.034% | +2.199% | -2.219% |
| 48h | 1244 | 50.4% | -0.058% | +3.166% | -3.288% |
| 72h | 1240 | 53.2% | +0.091% | +3.924% | -4.039% |
| 120h | 1235 | 52.1% | -0.091% | +5.164% | -5.221% |
| 168h | 1224 | 50.7% | -0.077% | +6.092% | -6.061% |

### First fades near liquidity — 1035 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1033 | 50.6% | +0.034% | +1.000% | -1.005% |
| 12h | 1032 | 51.4% | +0.027% | +1.459% | -1.477% |
| 24h | 1029 | 53.3% | +0.113% | +2.144% | -2.089% |
| 48h | 1026 | 51.2% | +0.032% | +3.121% | -3.125% |
| 72h | 1022 | 53.0% | +0.040% | +3.857% | -3.912% |
| 120h | 1019 | 52.1% | -0.117% | +5.121% | -5.148% |
| 168h | 1009 | 51.7% | +0.052% | +6.092% | -5.932% |

### First fades with liquidity sweep — 274 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 273 | 50.5% | +0.060% | +1.160% | -1.109% |
| 12h | 273 | 53.5% | -0.010% | +1.586% | -1.592% |
| 24h | 272 | 52.9% | +0.053% | +2.409% | -2.336% |
| 48h | 272 | 50.0% | -0.109% | +3.329% | -3.500% |
| 72h | 271 | 51.3% | -0.249% | +3.966% | -4.289% |
| 120h | 270 | 51.9% | -0.582% | +5.067% | -5.498% |
| 168h | 269 | 50.2% | -0.324% | +6.024% | -6.302% |

### Near or swept — 1049 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1047 | 50.7% | +0.037% | +1.006% | -1.006% |
| 12h | 1046 | 51.1% | +0.017% | +1.460% | -1.482% |
| 24h | 1043 | 53.1% | +0.094% | +2.140% | -2.105% |
| 48h | 1040 | 50.8% | -0.005% | +3.108% | -3.151% |
| 72h | 1036 | 52.7% | +0.011% | +3.844% | -3.950% |
| 120h | 1033 | 52.0% | -0.124% | +5.112% | -5.183% |
| 168h | 1023 | 51.5% | +0.062% | +6.100% | -5.963% |

### Away from liquidity — 205 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 205 | 49.8% | +0.131% | +1.301% | -1.264% |
| 12h | 205 | 49.8% | +0.133% | +1.820% | -1.721% |
| 24h | 205 | 44.9% | -0.275% | +2.495% | -2.797% |
| 48h | 204 | 48.5% | -0.329% | +3.462% | -3.987% |
| 72h | 204 | 55.9% | +0.495% | +4.329% | -4.493% |
| 120h | 202 | 53.0% | +0.074% | +5.431% | -5.416% |
| 168h | 201 | 46.3% | -0.783% | +6.050% | -6.557% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +12.09% |
| high | 2703.78 | 22.2 | 17 | +19.76% |
| high | 2518.93 | 22.2 | 12 | +11.58% |
| low | 2407.44 | 21.9 | 9 | +6.64% |
| low | 2484.94 | 15.3 | 11 | +10.07% |
| low | 2432.00 | 15.0 | 11 | +7.73% |
| high | 2721.59 | 13.9 | 7 | +20.55% |
| low | 2680.62 | 13.5 | 8 | +18.74% |
| low | 2355.61 | 11.2 | 5 | +4.34% |
| high | 2736.32 | 10.6 | 4 | +21.21% |
| low | 2294.98 | 10.5 | 4 | +1.66% |
| low | 2319.21 | 9.9 | 5 | +2.73% |
| low | 2473.84 | 9.8 | 7 | +9.58% |
| low | 2693.08 | 9.7 | 7 | +19.29% |
| high | 2549.53 | 9.5 | 4 | +12.93% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
