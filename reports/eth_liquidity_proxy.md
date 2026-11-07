# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-07T07:00:00+00:00; **9044** closed candles.

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

### All first fades — 1266 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1264 | 50.5% | +0.044% | +1.051% | -1.053% |
| 12h | 1263 | 50.9% | +0.031% | +1.515% | -1.524% |
| 24h | 1263 | 51.8% | +0.037% | +2.207% | -2.223% |
| 48h | 1260 | 50.6% | -0.020% | +3.192% | -3.282% |
| 72h | 1256 | 52.9% | +0.080% | +3.924% | -4.038% |
| 120h | 1248 | 52.2% | -0.106% | +5.139% | -5.236% |
| 168h | 1240 | 50.9% | -0.056% | +6.096% | -6.037% |

### First fades near liquidity — 1047 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1045 | 50.5% | +0.024% | +0.997% | -1.012% |
| 12h | 1044 | 51.3% | +0.021% | +1.455% | -1.481% |
| 24h | 1044 | 53.3% | +0.116% | +2.156% | -2.096% |
| 48h | 1041 | 51.5% | +0.077% | +3.153% | -3.123% |
| 72h | 1037 | 52.7% | +0.033% | +3.859% | -3.910% |
| 120h | 1029 | 52.2% | -0.121% | +5.101% | -5.157% |
| 168h | 1022 | 52.0% | +0.074% | +6.105% | -5.902% |

### First fades with liquidity sweep — 278 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 278 | 50.0% | +0.042% | +1.146% | -1.119% |
| 12h | 278 | 53.2% | -0.015% | +1.573% | -1.599% |
| 24h | 278 | 53.2% | +0.114% | +2.461% | -2.325% |
| 48h | 277 | 50.9% | +0.024% | +3.426% | -3.458% |
| 72h | 274 | 51.1% | -0.251% | +3.988% | -4.266% |
| 120h | 272 | 51.8% | -0.583% | +5.058% | -5.494% |
| 168h | 271 | 50.2% | -0.304% | +6.037% | -6.282% |

### Near or swept — 1061 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1059 | 50.6% | +0.027% | +1.002% | -1.012% |
| 12h | 1058 | 51.1% | +0.011% | +1.456% | -1.486% |
| 24h | 1058 | 53.1% | +0.097% | +2.152% | -2.112% |
| 48h | 1055 | 51.1% | +0.040% | +3.140% | -3.149% |
| 72h | 1051 | 52.4% | +0.005% | +3.846% | -3.947% |
| 120h | 1043 | 52.1% | -0.127% | +5.092% | -5.192% |
| 168h | 1036 | 51.7% | +0.083% | +6.113% | -5.933% |

### Away from liquidity — 205 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 205 | 49.8% | +0.131% | +1.301% | -1.264% |
| 12h | 205 | 49.8% | +0.133% | +1.820% | -1.721% |
| 24h | 205 | 44.9% | -0.275% | +2.495% | -2.797% |
| 48h | 205 | 48.3% | -0.327% | +3.459% | -3.971% |
| 72h | 205 | 55.6% | +0.465% | +4.322% | -4.505% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 204 | 46.6% | -0.760% | +6.008% | -6.566% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +12.67% |
| low | 2407.38 | 23.5 | 11 | +7.19% |
| high | 2518.93 | 22.2 | 12 | +12.15% |
| low | 2484.94 | 15.3 | 11 | +10.64% |
| low | 2432.00 | 15.0 | 11 | +8.28% |
| low | 2355.61 | 11.2 | 5 | +4.88% |
| low | 2294.98 | 10.5 | 4 | +2.18% |
| low | 2235.80 | 10.2 | 6 | -0.45% |
| low | 2319.21 | 9.9 | 5 | +3.26% |
| low | 2473.84 | 9.8 | 7 | +10.14% |
| high | 2549.53 | 9.5 | 4 | +13.51% |
| high | 2445.95 | 8.4 | 5 | +8.90% |
| low | 2280.48 | 8.0 | 2 | +1.54% |
| high | 2415.80 | 7.3 | 5 | +7.56% |
| high | 2276.12 | 7.0 | 3 | +1.34% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
