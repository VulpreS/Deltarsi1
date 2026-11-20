# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-20T09:00:00+00:00; **9358** closed candles.

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

### All first fades — 1305 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1304 | 50.8% | +0.049% | +1.065% | -1.058% |
| 12h | 1304 | 50.8% | +0.034% | +1.529% | -1.536% |
| 24h | 1302 | 51.6% | +0.019% | +2.215% | -2.245% |
| 48h | 1299 | 50.6% | -0.024% | +3.205% | -3.302% |
| 72h | 1295 | 53.1% | +0.097% | +3.943% | -4.061% |
| 120h | 1286 | 51.9% | -0.095% | +5.181% | -5.274% |
| 168h | 1279 | 51.1% | -0.019% | +6.170% | -6.110% |

### First fades near liquidity — 1062 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1061 | 50.4% | +0.021% | +0.996% | -1.013% |
| 12h | 1061 | 51.4% | +0.011% | +1.452% | -1.491% |
| 24h | 1061 | 53.3% | +0.095% | +2.146% | -2.115% |
| 48h | 1059 | 51.2% | +0.057% | +3.148% | -3.139% |
| 72h | 1057 | 52.7% | +0.033% | +3.862% | -3.936% |
| 120h | 1055 | 52.0% | -0.118% | +5.132% | -5.195% |
| 168h | 1053 | 52.1% | +0.077% | +6.147% | -5.989% |

### First fades with liquidity sweep — 284 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 284 | 50.7% | +0.068% | +1.169% | -1.107% |
| 12h | 284 | 53.2% | -0.011% | +1.599% | -1.609% |
| 24h | 284 | 53.5% | +0.123% | +2.481% | -2.324% |
| 48h | 283 | 50.9% | +0.016% | +3.428% | -3.467% |
| 72h | 282 | 51.8% | -0.165% | +4.043% | -4.239% |
| 120h | 280 | 51.8% | -0.476% | +5.189% | -5.467% |
| 168h | 280 | 50.4% | -0.212% | +6.178% | -6.296% |

### Near or swept — 1079 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1078 | 50.6% | +0.029% | +1.006% | -1.012% |
| 12h | 1078 | 51.1% | -0.000% | +1.457% | -1.498% |
| 24h | 1078 | 53.2% | +0.079% | +2.147% | -2.131% |
| 48h | 1076 | 50.8% | +0.024% | +3.140% | -3.166% |
| 72h | 1074 | 52.4% | +0.005% | +3.854% | -3.977% |
| 120h | 1071 | 51.9% | -0.122% | +5.128% | -5.233% |
| 168h | 1069 | 51.9% | +0.092% | +6.165% | -6.021% |

### Away from liquidity — 226 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 226 | 51.3% | +0.144% | +1.346% | -1.275% |
| 12h | 226 | 49.6% | +0.198% | +1.871% | -1.717% |
| 24h | 224 | 44.2% | -0.273% | +2.539% | -2.793% |
| 48h | 223 | 49.3% | -0.252% | +3.515% | -3.962% |
| 72h | 221 | 56.6% | +0.549% | +4.376% | -4.468% |
| 120h | 215 | 52.1% | +0.040% | +5.444% | -5.475% |
| 168h | 210 | 47.1% | -0.583% | +6.191% | -6.565% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +44.93% |
| low | 2407.38 | 23.5 | 11 | +37.88% |
| low | 2484.94 | 15.3 | 11 | +42.32% |
| low | 2432.00 | 15.0 | 11 | +39.29% |
| low | 2235.38 | 12.1 | 8 | +28.03% |
| low | 2355.61 | 11.2 | 5 | +34.92% |
| low | 2294.98 | 10.5 | 4 | +31.44% |
| low | 2319.21 | 9.9 | 5 | +32.83% |
| high | 2445.95 | 8.4 | 5 | +40.09% |
| low | 2280.48 | 8.0 | 2 | +30.61% |
| high | 2415.80 | 7.3 | 5 | +38.36% |
| high | 2276.12 | 7.0 | 3 | +30.36% |
| low | 2307.41 | 6.9 | 3 | +32.16% |
| low | 2251.24 | 6.9 | 4 | +28.94% |
| low | 2226.61 | 6.9 | 5 | +27.53% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
