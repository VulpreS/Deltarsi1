# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-10T08:00:00+00:00; **9117** closed candles.

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

### All first fades — 1274 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1273 | 50.5% | +0.050% | +1.057% | -1.049% |
| 12h | 1273 | 51.0% | +0.035% | +1.518% | -1.522% |
| 24h | 1273 | 51.8% | +0.034% | +2.206% | -2.222% |
| 48h | 1269 | 50.7% | -0.016% | +3.196% | -3.280% |
| 72h | 1266 | 53.0% | +0.094% | +3.932% | -4.038% |
| 120h | 1260 | 52.3% | -0.062% | +5.177% | -5.223% |
| 168h | 1254 | 51.0% | -0.059% | +6.095% | -6.064% |

### First fades near liquidity — 1050 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1050 | 50.5% | +0.024% | +0.994% | -1.009% |
| 12h | 1050 | 51.4% | +0.017% | +1.450% | -1.482% |
| 24h | 1050 | 53.2% | +0.105% | +2.147% | -2.101% |
| 48h | 1049 | 51.5% | +0.077% | +3.154% | -3.124% |
| 72h | 1047 | 52.8% | +0.051% | +3.869% | -3.910% |
| 120h | 1041 | 52.4% | -0.068% | +5.147% | -5.143% |
| 168h | 1035 | 52.1% | +0.061% | +6.101% | -5.935% |

### First fades with liquidity sweep — 279 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 279 | 50.2% | +0.058% | +1.169% | -1.117% |
| 12h | 279 | 53.4% | -0.000% | +1.595% | -1.594% |
| 24h | 279 | 53.4% | +0.129% | +2.480% | -2.318% |
| 48h | 278 | 50.7% | +0.009% | +3.413% | -3.467% |
| 72h | 278 | 51.4% | -0.182% | +4.024% | -4.238% |
| 120h | 277 | 52.0% | -0.449% | +5.189% | -5.422% |
| 168h | 274 | 50.0% | -0.343% | +6.041% | -6.309% |

### Near or swept — 1065 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1065 | 50.6% | +0.031% | +1.005% | -1.008% |
| 12h | 1065 | 51.3% | +0.011% | +1.457% | -1.486% |
| 24h | 1065 | 53.1% | +0.090% | +2.148% | -2.115% |
| 48h | 1063 | 51.1% | +0.040% | +3.141% | -3.149% |
| 72h | 1061 | 52.5% | +0.022% | +3.856% | -3.948% |
| 120h | 1055 | 52.2% | -0.076% | +5.138% | -5.178% |
| 168h | 1049 | 51.9% | +0.070% | +6.109% | -5.965% |

### Away from liquidity — 209 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 208 | 50.0% | +0.144% | +1.323% | -1.260% |
| 12h | 208 | 49.5% | +0.157% | +1.834% | -1.711% |
| 24h | 208 | 44.7% | -0.255% | +2.501% | -2.773% |
| 48h | 206 | 48.5% | -0.306% | +3.481% | -3.954% |
| 72h | 205 | 55.6% | +0.465% | +4.322% | -4.505% |
| 120h | 205 | 52.7% | +0.006% | +5.378% | -5.459% |
| 168h | 205 | 46.8% | -0.721% | +6.028% | -6.568% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +19.44% |
| low | 2407.38 | 23.5 | 11 | +13.64% |
| high | 2518.93 | 22.2 | 12 | +18.90% |
| low | 2484.94 | 15.3 | 11 | +17.30% |
| low | 2432.00 | 15.0 | 11 | +14.80% |
| low | 2235.38 | 12.1 | 8 | +5.52% |
| low | 2355.61 | 11.2 | 5 | +11.19% |
| low | 2294.98 | 10.5 | 4 | +8.33% |
| low | 2319.21 | 9.9 | 5 | +9.47% |
| high | 2549.53 | 9.5 | 4 | +20.34% |
| high | 2445.95 | 8.4 | 5 | +15.46% |
| low | 2280.48 | 8.0 | 2 | +7.64% |
| high | 2415.80 | 7.3 | 5 | +14.03% |
| high | 2276.12 | 7.0 | 3 | +7.44% |
| low | 2307.41 | 6.9 | 3 | +8.92% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
