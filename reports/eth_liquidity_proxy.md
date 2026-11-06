# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-06T08:00:00+00:00; **9021** closed candles.

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

### All first fades — 1263 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1262 | 50.4% | +0.044% | +1.051% | -1.054% |
| 12h | 1261 | 50.9% | +0.031% | +1.517% | -1.525% |
| 24h | 1260 | 51.8% | +0.041% | +2.212% | -2.222% |
| 48h | 1256 | 50.5% | -0.040% | +3.177% | -3.286% |
| 72h | 1254 | 52.9% | +0.076% | +3.925% | -4.033% |
| 120h | 1244 | 52.1% | -0.108% | +5.142% | -5.232% |
| 168h | 1237 | 50.9% | -0.056% | +6.100% | -6.036% |

### First fades near liquidity — 1044 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1043 | 50.4% | +0.024% | +0.998% | -1.013% |
| 12h | 1042 | 51.3% | +0.021% | +1.457% | -1.482% |
| 24h | 1041 | 53.3% | +0.121% | +2.161% | -2.094% |
| 48h | 1037 | 51.3% | +0.053% | +3.136% | -3.126% |
| 72h | 1035 | 52.7% | +0.029% | +3.860% | -3.904% |
| 120h | 1026 | 52.1% | -0.122% | +5.104% | -5.153% |
| 168h | 1021 | 52.0% | +0.075% | +6.102% | -5.906% |

### First fades with liquidity sweep — 278 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 278 | 50.0% | +0.042% | +1.146% | -1.119% |
| 12h | 278 | 53.2% | -0.015% | +1.573% | -1.599% |
| 24h | 277 | 53.4% | +0.132% | +2.470% | -2.312% |
| 48h | 274 | 50.4% | -0.056% | +3.368% | -3.484% |
| 72h | 274 | 51.1% | -0.251% | +3.988% | -4.266% |
| 120h | 272 | 51.8% | -0.583% | +5.058% | -5.494% |
| 168h | 270 | 50.4% | -0.304% | +6.024% | -6.300% |

### Near or swept — 1058 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1057 | 50.5% | +0.027% | +1.003% | -1.013% |
| 12h | 1056 | 51.1% | +0.011% | +1.458% | -1.486% |
| 24h | 1055 | 53.2% | +0.102% | +2.157% | -2.110% |
| 48h | 1051 | 50.9% | +0.016% | +3.122% | -3.152% |
| 72h | 1049 | 52.3% | +0.000% | +3.847% | -3.941% |
| 120h | 1040 | 52.0% | -0.129% | +5.094% | -5.188% |
| 168h | 1035 | 51.8% | +0.084% | +6.110% | -5.938% |

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
| high | 2530.45 | 33.5 | 20 | +13.64% |
| low | 2407.38 | 23.5 | 11 | +8.11% |
| high | 2518.93 | 22.2 | 12 | +13.12% |
| low | 2484.94 | 15.3 | 11 | +11.59% |
| low | 2432.00 | 15.0 | 11 | +9.22% |
| low | 2355.61 | 11.2 | 5 | +5.79% |
| low | 2294.98 | 10.5 | 4 | +3.06% |
| low | 2235.80 | 10.2 | 6 | +0.41% |
| low | 2319.21 | 9.9 | 5 | +4.15% |
| low | 2473.84 | 9.8 | 7 | +11.10% |
| high | 2549.53 | 9.5 | 4 | +14.49% |
| high | 2445.95 | 8.4 | 5 | +9.84% |
| low | 2280.48 | 8.0 | 2 | +2.41% |
| high | 2415.80 | 7.3 | 5 | +8.49% |
| high | 2276.12 | 7.0 | 3 | +2.22% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
