# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-11T08:00:00+00:00; **9141** closed candles.

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

### All first fades — 1275 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1275 | 50.5% | +0.051% | +1.057% | -1.048% |
| 12h | 1275 | 51.0% | +0.039% | +1.521% | -1.521% |
| 24h | 1274 | 51.8% | +0.036% | +2.209% | -2.221% |
| 48h | 1273 | 50.7% | -0.010% | +3.202% | -3.281% |
| 72h | 1269 | 53.0% | +0.100% | +3.937% | -4.037% |
| 120h | 1263 | 52.2% | -0.084% | +5.166% | -5.238% |
| 168h | 1256 | 51.1% | -0.042% | +6.105% | -6.065% |

### First fades near liquidity — 1051 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1051 | 50.4% | +0.024% | +0.993% | -1.009% |
| 12h | 1051 | 51.4% | +0.017% | +1.449% | -1.482% |
| 24h | 1050 | 53.2% | +0.105% | +2.147% | -2.101% |
| 48h | 1050 | 51.4% | +0.071% | +3.152% | -3.128% |
| 72h | 1049 | 52.8% | +0.050% | +3.869% | -3.913% |
| 120h | 1044 | 52.2% | -0.094% | +5.134% | -5.161% |
| 168h | 1037 | 52.2% | +0.082% | +6.112% | -5.937% |

### First fades with liquidity sweep — 279 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 279 | 50.2% | +0.058% | +1.169% | -1.117% |
| 12h | 279 | 53.4% | -0.000% | +1.595% | -1.594% |
| 24h | 279 | 53.4% | +0.129% | +2.480% | -2.318% |
| 48h | 279 | 50.9% | +0.043% | +3.437% | -3.455% |
| 72h | 278 | 51.4% | -0.182% | +4.024% | -4.238% |
| 120h | 278 | 51.8% | -0.487% | +5.170% | -5.451% |
| 168h | 274 | 50.0% | -0.343% | +6.041% | -6.309% |

### Near or swept — 1066 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1066 | 50.6% | +0.031% | +1.005% | -1.008% |
| 12h | 1066 | 51.2% | +0.011% | +1.456% | -1.485% |
| 24h | 1065 | 53.1% | +0.090% | +2.148% | -2.115% |
| 48h | 1065 | 51.1% | +0.043% | +3.145% | -3.151% |
| 72h | 1063 | 52.5% | +0.021% | +3.857% | -3.950% |
| 120h | 1058 | 52.1% | -0.101% | +5.124% | -5.195% |
| 168h | 1051 | 52.0% | +0.091% | +6.120% | -5.967% |

### Away from liquidity — 209 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 209 | 50.2% | +0.150% | +1.326% | -1.254% |
| 12h | 209 | 49.8% | +0.178% | +1.852% | -1.703% |
| 24h | 209 | 45.0% | -0.242% | +2.516% | -2.760% |
| 48h | 208 | 48.6% | -0.283% | +3.497% | -3.948% |
| 72h | 206 | 55.8% | +0.509% | +4.351% | -4.485% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +22.91% |
| low | 2407.38 | 23.5 | 11 | +16.93% |
| high | 2518.93 | 22.2 | 12 | +22.35% |
| low | 2484.94 | 15.3 | 11 | +20.69% |
| low | 2432.00 | 15.0 | 11 | +18.12% |
| low | 2235.38 | 12.1 | 8 | +8.57% |
| low | 2355.61 | 11.2 | 5 | +14.41% |
| low | 2294.98 | 10.5 | 4 | +11.47% |
| low | 2319.21 | 9.9 | 5 | +12.65% |
| high | 2445.95 | 8.4 | 5 | +18.80% |
| low | 2280.48 | 8.0 | 2 | +10.76% |
| high | 2415.80 | 7.3 | 5 | +17.34% |
| high | 2276.12 | 7.0 | 3 | +10.55% |
| low | 2307.41 | 6.9 | 3 | +12.07% |
| low | 2251.24 | 6.9 | 4 | +9.34% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
