# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-09T08:00:00+00:00; **9093** closed candles.

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

### All first fades — 1273 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1273 | 50.5% | +0.050% | +1.057% | -1.049% |
| 12h | 1272 | 51.0% | +0.036% | +1.519% | -1.521% |
| 24h | 1269 | 51.8% | +0.032% | +2.200% | -2.220% |
| 48h | 1266 | 50.6% | -0.019% | +3.191% | -3.280% |
| 72h | 1263 | 53.0% | +0.089% | +3.927% | -4.041% |
| 120h | 1256 | 52.1% | -0.098% | +5.149% | -5.233% |
| 168h | 1248 | 51.1% | -0.051% | +6.082% | -6.053% |

### First fades near liquidity — 1050 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1050 | 50.5% | +0.024% | +0.994% | -1.009% |
| 12h | 1050 | 51.4% | +0.017% | +1.450% | -1.482% |
| 24h | 1049 | 53.3% | +0.110% | +2.149% | -2.095% |
| 48h | 1047 | 51.5% | +0.078% | +3.153% | -3.122% |
| 72h | 1044 | 52.8% | +0.045% | +3.864% | -3.913% |
| 120h | 1037 | 52.2% | -0.111% | +5.114% | -5.154% |
| 168h | 1029 | 52.2% | +0.072% | +6.084% | -5.921% |

### First fades with liquidity sweep — 279 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 279 | 50.2% | +0.058% | +1.169% | -1.117% |
| 12h | 279 | 53.4% | -0.000% | +1.595% | -1.594% |
| 24h | 278 | 53.2% | +0.114% | +2.461% | -2.325% |
| 48h | 278 | 50.7% | +0.009% | +3.413% | -3.467% |
| 72h | 278 | 51.4% | -0.182% | +4.024% | -4.238% |
| 120h | 274 | 51.5% | -0.584% | +5.085% | -5.469% |
| 168h | 272 | 50.4% | -0.303% | +6.022% | -6.292% |

### Near or swept — 1065 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1065 | 50.6% | +0.031% | +1.005% | -1.008% |
| 12h | 1065 | 51.3% | +0.011% | +1.457% | -1.486% |
| 24h | 1063 | 53.2% | +0.092% | +2.145% | -2.111% |
| 48h | 1061 | 51.1% | +0.041% | +3.139% | -3.147% |
| 72h | 1058 | 52.5% | +0.016% | +3.851% | -3.951% |
| 120h | 1051 | 52.0% | -0.118% | +5.105% | -5.189% |
| 168h | 1043 | 52.0% | +0.081% | +6.092% | -5.952% |

### Away from liquidity — 208 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 208 | 50.0% | +0.144% | +1.323% | -1.260% |
| 12h | 207 | 49.8% | +0.161% | +1.843% | -1.705% |
| 24h | 206 | 44.7% | -0.275% | +2.486% | -2.786% |
| 48h | 205 | 48.3% | -0.327% | +3.459% | -3.971% |
| 72h | 205 | 55.6% | +0.465% | +4.322% | -4.505% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +19.18% |
| low | 2407.38 | 23.5 | 11 | +13.38% |
| high | 2518.93 | 22.2 | 12 | +18.64% |
| low | 2484.94 | 15.3 | 11 | +17.04% |
| low | 2432.00 | 15.0 | 11 | +14.54% |
| low | 2235.38 | 12.1 | 8 | +5.28% |
| low | 2355.61 | 11.2 | 5 | +10.95% |
| low | 2294.98 | 10.5 | 4 | +8.09% |
| low | 2319.21 | 9.9 | 5 | +9.23% |
| high | 2549.53 | 9.5 | 4 | +20.08% |
| high | 2445.95 | 8.4 | 5 | +15.20% |
| low | 2280.48 | 8.0 | 2 | +7.41% |
| high | 2415.80 | 7.3 | 5 | +13.78% |
| high | 2276.12 | 7.0 | 3 | +7.20% |
| low | 2307.41 | 6.9 | 3 | +8.68% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
