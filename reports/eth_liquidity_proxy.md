# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-28T07:00:00+00:00; **8804** closed candles.

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

### All first fades — 1229 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1228 | 50.4% | +0.048% | +1.057% | -1.056% |
| 12h | 1227 | 51.0% | +0.038% | +1.525% | -1.529% |
| 24h | 1224 | 52.1% | +0.041% | +2.214% | -2.222% |
| 48h | 1221 | 50.5% | -0.061% | +3.179% | -3.295% |
| 72h | 1218 | 53.2% | +0.069% | +3.922% | -4.058% |
| 120h | 1216 | 52.1% | -0.099% | +5.168% | -5.243% |
| 168h | 1211 | 50.8% | -0.076% | +6.112% | -6.079% |

### First fades near liquidity — 1013 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1012 | 50.5% | +0.029% | +1.001% | -1.013% |
| 12h | 1011 | 51.4% | +0.029% | +1.463% | -1.483% |
| 24h | 1009 | 53.6% | +0.122% | +2.157% | -2.088% |
| 48h | 1007 | 51.1% | +0.027% | +3.127% | -3.128% |
| 72h | 1005 | 52.9% | +0.020% | +3.849% | -3.928% |
| 120h | 1003 | 52.2% | -0.117% | +5.129% | -5.166% |
| 168h | 998 | 52.0% | +0.060% | +6.118% | -5.945% |

### First fades with liquidity sweep — 269 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 269 | 50.2% | +0.060% | +1.167% | -1.118% |
| 12h | 269 | 53.2% | -0.021% | +1.593% | -1.606% |
| 24h | 269 | 53.2% | +0.067% | +2.420% | -2.332% |
| 48h | 268 | 50.0% | -0.102% | +3.350% | -3.511% |
| 72h | 268 | 51.1% | -0.257% | +3.976% | -4.307% |
| 120h | 268 | 52.2% | -0.566% | +5.083% | -5.493% |
| 168h | 265 | 50.2% | -0.339% | +6.043% | -6.341% |

### Near or swept — 1027 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1026 | 50.6% | +0.032% | +1.006% | -1.013% |
| 12h | 1025 | 51.2% | +0.019% | +1.464% | -1.487% |
| 24h | 1023 | 53.5% | +0.102% | +2.152% | -2.104% |
| 48h | 1021 | 50.7% | -0.010% | +3.113% | -3.154% |
| 72h | 1019 | 52.6% | -0.009% | +3.836% | -3.966% |
| 120h | 1017 | 52.1% | -0.124% | +5.119% | -5.201% |
| 168h | 1012 | 51.8% | +0.070% | +6.126% | -5.977% |

### Away from liquidity — 202 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 202 | 49.5% | +0.133% | +1.314% | -1.276% |
| 12h | 202 | 50.0% | +0.131% | +1.833% | -1.739% |
| 24h | 201 | 45.3% | -0.272% | +2.529% | -2.823% |
| 48h | 200 | 49.0% | -0.320% | +3.517% | -4.013% |
| 72h | 199 | 56.3% | +0.467% | +4.362% | -4.531% |
| 120h | 199 | 52.3% | +0.030% | +5.415% | -5.454% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +7.16% |
| high | 2703.78 | 22.2 | 17 | +14.50% |
| high | 2518.93 | 22.2 | 12 | +6.67% |
| low | 2407.44 | 21.9 | 9 | +1.95% |
| low | 2669.15 | 19.9 | 12 | +13.03% |
| low | 2484.94 | 15.3 | 11 | +5.23% |
| low | 2432.00 | 15.0 | 11 | +2.99% |
| high | 2721.59 | 13.9 | 7 | +15.26% |
| low | 2680.62 | 13.5 | 8 | +13.52% |
| high | 2748.49 | 12.6 | 5 | +16.39% |
| low | 2355.84 | 10.7 | 4 | -0.23% |
| high | 2736.32 | 10.6 | 4 | +15.88% |
| low | 2473.84 | 9.8 | 7 | +4.76% |
| low | 2693.08 | 9.7 | 7 | +14.05% |
| high | 2549.53 | 9.5 | 4 | +7.97% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
