# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-22T08:00:00+00:00; **9405** closed candles.

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

### All first fades — 1309 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1308 | 50.8% | +0.047% | +1.066% | -1.060% |
| 12h | 1308 | 50.9% | +0.032% | +1.531% | -1.542% |
| 24h | 1307 | 51.7% | +0.028% | +2.227% | -2.251% |
| 48h | 1305 | 50.6% | -0.032% | +3.218% | -3.316% |
| 72h | 1302 | 53.0% | +0.077% | +3.949% | -4.087% |
| 120h | 1295 | 52.2% | -0.048% | +5.232% | -5.259% |
| 168h | 1286 | 50.9% | -0.057% | +6.158% | -6.154% |

### First fades near liquidity — 1063 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1062 | 50.4% | +0.021% | +0.996% | -1.014% |
| 12h | 1062 | 51.3% | +0.004% | +1.451% | -1.497% |
| 24h | 1062 | 53.2% | +0.089% | +2.145% | -2.124% |
| 48h | 1062 | 51.0% | +0.033% | +3.144% | -3.163% |
| 72h | 1061 | 52.5% | -0.002% | +3.854% | -3.972% |
| 120h | 1057 | 52.0% | -0.117% | +5.141% | -5.200% |
| 168h | 1055 | 52.0% | +0.058% | +6.138% | -6.010% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 284 | 51.4% | -0.227% | +4.028% | -4.306% |
| 120h | 282 | 52.1% | -0.412% | +5.264% | -5.435% |
| 168h | 280 | 50.4% | -0.212% | +6.178% | -6.296% |

### Near or swept — 1080 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1079 | 50.6% | +0.028% | +1.006% | -1.012% |
| 12h | 1079 | 51.1% | -0.007% | +1.456% | -1.504% |
| 24h | 1079 | 53.1% | +0.073% | +2.146% | -2.140% |
| 48h | 1079 | 50.7% | +0.000% | +3.137% | -3.190% |
| 72h | 1078 | 52.2% | -0.029% | +3.846% | -4.012% |
| 120h | 1074 | 52.0% | -0.114% | +5.146% | -5.234% |
| 168h | 1071 | 51.8% | +0.073% | +6.157% | -6.042% |

### Away from liquidity — 229 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 229 | 51.5% | +0.137% | +1.346% | -1.283% |
| 12h | 229 | 50.2% | +0.217% | +1.883% | -1.724% |
| 24h | 228 | 45.2% | -0.186% | +2.609% | -2.775% |
| 48h | 226 | 50.0% | -0.185% | +3.606% | -3.922% |
| 72h | 224 | 56.7% | +0.588% | +4.448% | -4.446% |
| 120h | 221 | 53.4% | +0.269% | +5.651% | -5.380% |
| 168h | 215 | 46.5% | -0.706% | +6.167% | -6.711% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +42.67% |
| low | 2235.38 | 12.1 | 8 | +32.48% |
| low | 2355.61 | 11.2 | 5 | +39.61% |
| low | 2294.98 | 10.5 | 4 | +36.01% |
| low | 2319.21 | 9.9 | 5 | +37.45% |
| high | 2445.95 | 8.4 | 5 | +44.96% |
| low | 2280.48 | 8.0 | 2 | +35.15% |
| high | 2415.80 | 7.3 | 5 | +43.17% |
| high | 2276.12 | 7.0 | 3 | +34.89% |
| low | 2307.41 | 6.9 | 3 | +36.75% |
| low | 2251.24 | 6.9 | 4 | +33.42% |
| low | 2226.61 | 6.9 | 5 | +31.96% |
| low | 2209.38 | 6.9 | 4 | +30.94% |
| high | 2306.04 | 6.7 | 4 | +36.67% |
| low | 1751.09 | 6.6 | 2 | +3.78% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
