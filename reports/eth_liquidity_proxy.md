# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-08T08:00:00+00:00; **9069** closed candles.

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

### All first fades — 1269 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1268 | 50.6% | +0.044% | +1.049% | -1.050% |
| 12h | 1268 | 51.0% | +0.032% | +1.512% | -1.519% |
| 24h | 1266 | 51.8% | +0.038% | +2.204% | -2.219% |
| 48h | 1263 | 50.6% | -0.024% | +3.185% | -3.281% |
| 72h | 1260 | 53.1% | +0.100% | +3.936% | -4.033% |
| 120h | 1254 | 52.1% | -0.105% | +5.147% | -5.230% |
| 168h | 1244 | 51.0% | -0.054% | +6.083% | -6.046% |

### First fades near liquidity — 1049 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1048 | 50.6% | +0.024% | +0.995% | -1.010% |
| 12h | 1048 | 51.5% | +0.022% | +1.452% | -1.477% |
| 24h | 1047 | 53.3% | +0.117% | +2.152% | -2.091% |
| 48h | 1044 | 51.4% | +0.073% | +3.145% | -3.122% |
| 72h | 1041 | 52.9% | +0.057% | +3.873% | -3.904% |
| 120h | 1035 | 52.1% | -0.120% | +5.111% | -5.150% |
| 168h | 1026 | 52.1% | +0.076% | +6.089% | -5.913% |

### First fades with liquidity sweep — 278 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 278 | 50.0% | +0.042% | +1.146% | -1.119% |
| 12h | 278 | 53.2% | -0.015% | +1.573% | -1.599% |
| 24h | 278 | 53.2% | +0.114% | +2.461% | -2.325% |
| 48h | 278 | 50.7% | +0.009% | +3.413% | -3.467% |
| 72h | 277 | 51.6% | -0.167% | +4.039% | -4.232% |
| 120h | 274 | 51.5% | -0.584% | +5.085% | -5.469% |
| 168h | 272 | 50.4% | -0.303% | +6.022% | -6.292% |

### Near or swept — 1063 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1062 | 50.7% | +0.027% | +1.000% | -1.010% |
| 12h | 1062 | 51.3% | +0.013% | +1.453% | -1.481% |
| 24h | 1061 | 53.2% | +0.098% | +2.148% | -2.107% |
| 48h | 1058 | 51.0% | +0.035% | +3.132% | -3.148% |
| 72h | 1055 | 52.6% | +0.029% | +3.861% | -3.941% |
| 120h | 1049 | 52.0% | -0.127% | +5.102% | -5.185% |
| 168h | 1040 | 51.9% | +0.085% | +6.097% | -5.944% |

### Away from liquidity — 206 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 206 | 50.0% | +0.131% | +1.298% | -1.258% |
| 12h | 206 | 49.5% | +0.132% | +1.814% | -1.713% |
| 24h | 205 | 44.9% | -0.275% | +2.495% | -2.797% |
| 48h | 205 | 48.3% | -0.327% | +3.459% | -3.971% |
| 72h | 205 | 55.6% | +0.465% | +4.322% | -4.505% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 204 | 46.6% | -0.760% | +6.008% | -6.566% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +13.00% |
| low | 2407.38 | 23.5 | 11 | +7.51% |
| high | 2518.93 | 22.2 | 12 | +12.49% |
| low | 2484.94 | 15.3 | 11 | +10.97% |
| low | 2432.00 | 15.0 | 11 | +8.61% |
| low | 2355.61 | 11.2 | 5 | +5.19% |
| low | 2294.98 | 10.5 | 4 | +2.49% |
| low | 2235.80 | 10.2 | 6 | -0.16% |
| low | 2319.21 | 9.9 | 5 | +3.57% |
| low | 2473.84 | 9.8 | 7 | +10.47% |
| high | 2549.53 | 9.5 | 4 | +13.85% |
| high | 2445.95 | 8.4 | 5 | +9.23% |
| low | 2280.48 | 8.0 | 2 | +1.84% |
| high | 2415.80 | 7.3 | 5 | +7.88% |
| high | 2276.12 | 7.0 | 3 | +1.64% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
