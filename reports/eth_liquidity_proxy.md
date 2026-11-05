# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-05T08:00:00+00:00; **8997** closed candles.

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

### All first fades — 1260 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1260 | 50.5% | +0.048% | +1.053% | -1.051% |
| 12h | 1258 | 51.0% | +0.034% | +1.519% | -1.522% |
| 24h | 1256 | 51.8% | +0.027% | +2.199% | -2.221% |
| 48h | 1254 | 50.4% | -0.043% | +3.178% | -3.279% |
| 72h | 1248 | 53.0% | +0.083% | +3.912% | -4.035% |
| 120h | 1240 | 52.2% | -0.098% | +5.154% | -5.220% |
| 168h | 1235 | 51.0% | -0.054% | +6.096% | -6.041% |

### First fades near liquidity — 1041 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1041 | 50.5% | +0.028% | +1.000% | -1.009% |
| 12h | 1039 | 51.4% | +0.024% | +1.459% | -1.479% |
| 24h | 1037 | 53.2% | +0.104% | +2.146% | -2.093% |
| 48h | 1035 | 51.2% | +0.050% | +3.136% | -3.119% |
| 72h | 1029 | 52.8% | +0.037% | +3.844% | -3.905% |
| 120h | 1022 | 52.3% | -0.109% | +5.118% | -5.139% |
| 168h | 1019 | 52.1% | +0.077% | +6.097% | -5.912% |

### First fades with liquidity sweep — 277 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 277 | 50.2% | +0.056% | +1.150% | -1.107% |
| 12h | 275 | 53.5% | -0.004% | +1.584% | -1.588% |
| 24h | 274 | 52.9% | +0.057% | +2.409% | -2.325% |
| 48h | 274 | 50.4% | -0.056% | +3.368% | -3.484% |
| 72h | 272 | 51.1% | -0.251% | +3.954% | -4.285% |
| 120h | 271 | 52.0% | -0.557% | +5.073% | -5.481% |
| 168h | 270 | 50.4% | -0.304% | +6.024% | -6.300% |

### Near or swept — 1055 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1055 | 50.6% | +0.032% | +1.005% | -1.009% |
| 12h | 1053 | 51.2% | +0.015% | +1.460% | -1.483% |
| 24h | 1051 | 53.1% | +0.086% | +2.142% | -2.109% |
| 48h | 1049 | 50.8% | +0.013% | +3.123% | -3.144% |
| 72h | 1043 | 52.4% | +0.008% | +3.832% | -3.943% |
| 120h | 1036 | 52.1% | -0.116% | +5.109% | -5.174% |
| 168h | 1033 | 51.9% | +0.086% | +6.105% | -5.943% |

### Away from liquidity — 205 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 205 | 49.8% | +0.131% | +1.301% | -1.264% |
| 12h | 205 | 49.8% | +0.133% | +1.820% | -1.721% |
| 24h | 205 | 44.9% | -0.275% | +2.495% | -2.797% |
| 48h | 205 | 48.3% | -0.327% | +3.459% | -3.971% |
| 72h | 205 | 55.6% | +0.465% | +4.322% | -4.505% |
| 120h | 204 | 52.5% | -0.004% | +5.386% | -5.452% |
| 168h | 202 | 46.5% | -0.768% | +6.050% | -6.541% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +4.55% |
| low | 2407.38 | 23.5 | 11 | -0.53% |
| high | 2703.78 | 22.2 | 17 | +11.71% |
| high | 2518.93 | 22.2 | 12 | +4.08% |
| low | 2484.94 | 15.3 | 11 | +2.67% |
| low | 2432.00 | 15.0 | 11 | +0.48% |
| high | 2721.59 | 13.9 | 7 | +12.45% |
| low | 2680.62 | 13.5 | 8 | +10.76% |
| low | 2355.61 | 11.2 | 5 | -2.67% |
| low | 2294.98 | 10.5 | 4 | -5.18% |
| low | 2319.21 | 9.9 | 5 | -4.18% |
| low | 2473.84 | 9.8 | 7 | +2.21% |
| low | 2693.08 | 9.7 | 7 | +11.27% |
| high | 2549.53 | 9.5 | 4 | +5.34% |
| high | 2445.95 | 8.4 | 5 | +1.06% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
