# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-10-29T07:00:00+00:00; **8828** closed candles.

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

### All first fades — 1234 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1233 | 50.5% | +0.052% | +1.060% | -1.053% |
| 12h | 1232 | 51.0% | +0.036% | +1.525% | -1.529% |
| 24h | 1229 | 52.1% | +0.039% | +2.209% | -2.222% |
| 48h | 1224 | 50.6% | -0.058% | +3.178% | -3.291% |
| 72h | 1221 | 53.2% | +0.069% | +3.918% | -4.053% |
| 120h | 1217 | 52.2% | -0.096% | +5.168% | -5.239% |
| 168h | 1214 | 50.8% | -0.073% | +6.110% | -6.071% |

### First fades near liquidity — 1018 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1017 | 50.6% | +0.033% | +1.005% | -1.010% |
| 12h | 1016 | 51.4% | +0.027% | +1.463% | -1.483% |
| 24h | 1013 | 53.6% | +0.121% | +2.153% | -2.087% |
| 48h | 1009 | 51.2% | +0.031% | +3.127% | -3.124% |
| 72h | 1007 | 52.9% | +0.021% | +3.846% | -3.923% |
| 120h | 1004 | 52.3% | -0.114% | +5.129% | -5.161% |
| 168h | 1001 | 52.0% | +0.064% | +6.115% | -5.937% |

### First fades with liquidity sweep — 270 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 269 | 50.2% | +0.060% | +1.167% | -1.118% |
| 12h | 269 | 53.2% | -0.021% | +1.593% | -1.606% |
| 24h | 269 | 53.2% | +0.067% | +2.420% | -2.332% |
| 48h | 269 | 50.2% | -0.099% | +3.348% | -3.503% |
| 72h | 268 | 51.1% | -0.257% | +3.976% | -4.307% |
| 120h | 268 | 52.2% | -0.566% | +5.083% | -5.493% |
| 168h | 267 | 50.6% | -0.302% | +6.057% | -6.305% |

### Near or swept — 1032 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1031 | 50.7% | +0.036% | +1.010% | -1.010% |
| 12h | 1030 | 51.2% | +0.017% | +1.464% | -1.488% |
| 24h | 1027 | 53.5% | +0.102% | +2.149% | -2.104% |
| 48h | 1023 | 50.8% | -0.007% | +3.113% | -3.150% |
| 72h | 1021 | 52.6% | -0.008% | +3.833% | -3.962% |
| 120h | 1018 | 52.2% | -0.121% | +5.119% | -5.197% |
| 168h | 1015 | 51.8% | +0.074% | +6.123% | -5.968% |

### Away from liquidity — 202 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 202 | 49.5% | +0.133% | +1.314% | -1.276% |
| 12h | 202 | 50.0% | +0.131% | +1.833% | -1.739% |
| 24h | 202 | 45.0% | -0.281% | +2.518% | -2.824% |
| 48h | 201 | 49.3% | -0.316% | +3.505% | -4.007% |
| 72h | 200 | 56.0% | +0.465% | +4.349% | -4.520% |
| 120h | 199 | 52.3% | +0.030% | +5.415% | -5.454% |
| 168h | 199 | 45.7% | -0.819% | +6.044% | -6.596% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +9.53% |
| high | 2703.78 | 22.2 | 17 | +17.03% |
| high | 2518.93 | 22.2 | 12 | +9.03% |
| low | 2407.44 | 21.9 | 9 | +4.20% |
| low | 2669.15 | 19.9 | 12 | +15.53% |
| low | 2484.94 | 15.3 | 11 | +7.56% |
| low | 2432.00 | 15.0 | 11 | +5.27% |
| high | 2721.59 | 13.9 | 7 | +17.80% |
| low | 2680.62 | 13.5 | 8 | +16.03% |
| high | 2748.49 | 12.6 | 5 | +18.96% |
| low | 2355.61 | 11.2 | 5 | +1.96% |
| high | 2736.32 | 10.6 | 4 | +18.44% |
| low | 2294.98 | 10.5 | 4 | -0.67% |
| low | 2473.84 | 9.8 | 7 | +7.08% |
| low | 2693.08 | 9.7 | 7 | +16.57% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
