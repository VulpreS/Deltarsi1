# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-02T08:00:00+00:00; **8925** closed candles.

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

### All first fades — 1248 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1247 | 50.4% | +0.051% | +1.055% | -1.050% |
| 12h | 1246 | 50.7% | +0.033% | +1.518% | -1.525% |
| 24h | 1244 | 51.8% | +0.035% | +2.201% | -2.221% |
| 48h | 1240 | 50.5% | -0.055% | +3.175% | -3.289% |
| 72h | 1237 | 53.3% | +0.090% | +3.930% | -4.043% |
| 120h | 1229 | 52.2% | -0.089% | +5.168% | -5.224% |
| 168h | 1221 | 50.7% | -0.075% | +6.096% | -6.063% |

### First fades near liquidity — 1029 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1029 | 50.5% | +0.032% | +1.001% | -1.007% |
| 12h | 1028 | 51.2% | +0.025% | +1.458% | -1.481% |
| 24h | 1026 | 53.4% | +0.116% | +2.147% | -2.089% |
| 48h | 1022 | 51.3% | +0.036% | +3.132% | -3.126% |
| 72h | 1021 | 53.0% | +0.038% | +3.857% | -3.915% |
| 120h | 1013 | 52.2% | -0.115% | +5.126% | -5.151% |
| 168h | 1007 | 51.8% | +0.058% | +6.097% | -5.931% |

### First fades with liquidity sweep — 272 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 272 | 50.4% | +0.060% | +1.163% | -1.112% |
| 12h | 272 | 53.3% | -0.011% | +1.590% | -1.596% |
| 24h | 272 | 52.9% | +0.053% | +2.409% | -2.336% |
| 48h | 271 | 50.2% | -0.103% | +3.341% | -3.502% |
| 72h | 270 | 51.1% | -0.259% | +3.968% | -4.302% |
| 120h | 269 | 52.0% | -0.575% | +5.075% | -5.496% |
| 168h | 268 | 50.4% | -0.314% | +6.036% | -6.301% |

### Near or swept — 1043 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1043 | 50.6% | +0.035% | +1.007% | -1.007% |
| 12h | 1042 | 51.0% | +0.015% | +1.460% | -1.486% |
| 24h | 1040 | 53.3% | +0.097% | +2.143% | -2.105% |
| 48h | 1036 | 50.9% | -0.001% | +3.118% | -3.152% |
| 72h | 1035 | 52.7% | +0.009% | +3.845% | -3.953% |
| 120h | 1027 | 52.1% | -0.121% | +5.116% | -5.186% |
| 168h | 1021 | 51.6% | +0.067% | +6.106% | -5.963% |

### Away from liquidity — 205 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 204 | 49.5% | +0.130% | +1.305% | -1.267% |
| 12h | 204 | 49.5% | +0.127% | +1.819% | -1.727% |
| 24h | 204 | 44.6% | -0.286% | +2.496% | -2.808% |
| 48h | 204 | 48.5% | -0.329% | +3.462% | -3.987% |
| 72h | 202 | 56.4% | +0.504% | +4.368% | -4.505% |
| 120h | 202 | 53.0% | +0.074% | +5.431% | -5.416% |
| 168h | 200 | 46.0% | -0.801% | +6.048% | -6.575% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +10.13% |
| high | 2703.78 | 22.2 | 17 | +17.67% |
| high | 2518.93 | 22.2 | 12 | +9.63% |
| low | 2407.44 | 21.9 | 9 | +4.78% |
| low | 2484.94 | 15.3 | 11 | +8.15% |
| low | 2432.00 | 15.0 | 11 | +5.85% |
| high | 2721.59 | 13.9 | 7 | +18.45% |
| low | 2680.62 | 13.5 | 8 | +16.67% |
| low | 2355.61 | 11.2 | 5 | +2.52% |
| high | 2736.32 | 10.6 | 4 | +19.09% |
| low | 2294.98 | 10.5 | 4 | -0.12% |
| low | 2319.21 | 9.9 | 5 | +0.94% |
| low | 2473.84 | 9.8 | 7 | +7.67% |
| low | 2693.08 | 9.7 | 7 | +17.21% |
| high | 2549.53 | 9.5 | 4 | +10.96% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
