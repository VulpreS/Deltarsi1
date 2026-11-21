# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-21T08:00:00+00:00; **9381** closed candles.

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

### All first fades — 1307 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1306 | 50.7% | +0.046% | +1.065% | -1.060% |
| 12h | 1305 | 50.8% | +0.028% | +1.528% | -1.541% |
| 24h | 1305 | 51.6% | +0.024% | +2.222% | -2.249% |
| 48h | 1302 | 50.5% | -0.038% | +3.203% | -3.314% |
| 72h | 1299 | 53.0% | +0.082% | +3.945% | -4.074% |
| 120h | 1289 | 52.1% | -0.072% | +5.193% | -5.268% |
| 168h | 1282 | 51.1% | -0.032% | +6.170% | -6.123% |

### First fades near liquidity — 1062 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1062 | 50.4% | +0.021% | +0.996% | -1.014% |
| 12h | 1062 | 51.3% | +0.004% | +1.451% | -1.497% |
| 24h | 1062 | 53.2% | +0.089% | +2.145% | -2.124% |
| 48h | 1061 | 51.1% | +0.038% | +3.146% | -3.155% |
| 72h | 1059 | 52.6% | +0.010% | +3.857% | -3.954% |
| 120h | 1055 | 52.0% | -0.118% | +5.132% | -5.195% |
| 168h | 1053 | 52.1% | +0.077% | +6.147% | -5.989% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 284 | 50.7% | -0.011% | +3.428% | -3.490% |
| 72h | 283 | 51.6% | -0.213% | +4.030% | -4.277% |
| 120h | 280 | 51.8% | -0.476% | +5.189% | -5.467% |
| 168h | 280 | 50.4% | -0.212% | +6.178% | -6.296% |

### Near or swept — 1079 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1079 | 50.6% | +0.028% | +1.006% | -1.012% |
| 12h | 1079 | 51.1% | -0.007% | +1.456% | -1.504% |
| 24h | 1079 | 53.1% | +0.073% | +2.146% | -2.140% |
| 48h | 1078 | 50.7% | +0.005% | +3.139% | -3.181% |
| 72h | 1076 | 52.3% | -0.019% | +3.849% | -3.995% |
| 120h | 1071 | 51.9% | -0.122% | +5.128% | -5.233% |
| 168h | 1069 | 51.9% | +0.092% | +6.165% | -6.021% |

### Away from liquidity — 228 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 227 | 51.1% | +0.131% | +1.343% | -1.287% |
| 12h | 226 | 49.6% | +0.198% | +1.871% | -1.717% |
| 24h | 226 | 44.7% | -0.213% | +2.585% | -2.771% |
| 48h | 224 | 49.6% | -0.243% | +3.514% | -3.954% |
| 72h | 223 | 56.5% | +0.569% | +4.408% | -4.455% |
| 120h | 218 | 52.8% | +0.171% | +5.515% | -5.440% |
| 168h | 213 | 46.9% | -0.653% | +6.191% | -6.637% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| low | 2407.38 | 23.5 | 11 | +47.84% |
| low | 2235.38 | 12.1 | 8 | +37.28% |
| low | 2355.61 | 11.2 | 5 | +44.67% |
| low | 2294.98 | 10.5 | 4 | +40.94% |
| low | 2319.21 | 9.9 | 5 | +42.43% |
| high | 2445.95 | 8.4 | 5 | +50.21% |
| low | 2280.48 | 8.0 | 2 | +40.05% |
| high | 2415.80 | 7.3 | 5 | +48.36% |
| high | 2276.12 | 7.0 | 3 | +39.78% |
| low | 2307.41 | 6.9 | 3 | +41.70% |
| low | 2251.24 | 6.9 | 4 | +38.26% |
| low | 2226.61 | 6.9 | 5 | +36.74% |
| low | 2209.38 | 6.9 | 4 | +35.68% |
| high | 2306.04 | 6.7 | 4 | +41.62% |
| low | 1751.09 | 6.6 | 2 | +7.54% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
