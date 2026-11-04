# ETHUSDT 1H — causal liquidity heatmap proxy + DeltaRSI

Period: 2025-10-26T12:00:00+00:00 to 2026-11-04T08:00:00+00:00; **8973** closed candles.

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

### All first fades — 1256 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1256 | 50.6% | +0.053% | +1.055% | -1.047% |
| 12h | 1255 | 51.1% | +0.040% | +1.521% | -1.518% |
| 24h | 1254 | 51.8% | +0.037% | +2.199% | -2.213% |
| 48h | 1248 | 50.3% | -0.059% | +3.162% | -3.283% |
| 72h | 1244 | 53.1% | +0.086% | +3.913% | -4.036% |
| 120h | 1237 | 52.2% | -0.090% | +5.160% | -5.217% |
| 168h | 1229 | 50.9% | -0.067% | +6.095% | -6.046% |

### First fades near liquidity — 1037 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1037 | 50.7% | +0.035% | +1.002% | -1.004% |
| 12h | 1036 | 51.5% | +0.032% | +1.461% | -1.473% |
| 24h | 1035 | 53.3% | +0.117% | +2.145% | -2.083% |
| 48h | 1029 | 51.1% | +0.031% | +3.116% | -3.122% |
| 72h | 1026 | 52.8% | +0.035% | +3.844% | -3.908% |
| 120h | 1021 | 52.2% | -0.116% | +5.117% | -5.143% |
| 168h | 1013 | 51.9% | +0.061% | +6.096% | -5.917% |

### First fades with liquidity sweep — 274 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 274 | 50.7% | +0.063% | +1.159% | -1.107% |
| 12h | 274 | 53.6% | -0.002% | +1.589% | -1.588% |
| 24h | 274 | 52.9% | +0.057% | +2.409% | -2.325% |
| 48h | 272 | 50.0% | -0.109% | +3.329% | -3.500% |
| 72h | 272 | 51.1% | -0.251% | +3.954% | -4.285% |
| 120h | 270 | 51.9% | -0.582% | +5.067% | -5.498% |
| 168h | 269 | 50.2% | -0.324% | +6.024% | -6.302% |

### Near or swept — 1051 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 1051 | 50.8% | +0.038% | +1.008% | -1.004% |
| 12h | 1050 | 51.3% | +0.022% | +1.462% | -1.478% |
| 24h | 1049 | 53.2% | +0.098% | +2.141% | -2.099% |
| 48h | 1043 | 50.7% | -0.006% | +3.103% | -3.148% |
| 72h | 1040 | 52.5% | +0.006% | +3.832% | -3.946% |
| 120h | 1035 | 52.1% | -0.122% | +5.107% | -5.179% |
| 168h | 1027 | 51.7% | +0.071% | +6.104% | -5.948% |

### Away from liquidity — 205 events

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 205 | 49.8% | +0.131% | +1.301% | -1.264% |
| 12h | 205 | 49.8% | +0.133% | +1.820% | -1.721% |
| 24h | 205 | 44.9% | -0.275% | +2.495% | -2.797% |
| 48h | 205 | 48.3% | -0.327% | +3.459% | -3.971% |
| 72h | 204 | 55.9% | +0.495% | +4.329% | -4.493% |
| 120h | 202 | 53.0% | +0.074% | +5.431% | -5.416% |
| 168h | 202 | 46.5% | -0.768% | +6.050% | -6.541% |

## Current strongest heuristic zones

| Side | Price (USDT) | Relative strength | Pivot confirmations | Distance from latest close |
|---|---:|---:|---:|---:|
| high | 2530.45 | 33.5 | 20 | +8.92% |
| high | 2703.78 | 22.2 | 17 | +16.39% |
| high | 2518.93 | 22.2 | 12 | +8.43% |
| low | 2407.44 | 21.9 | 9 | +3.63% |
| low | 2484.94 | 15.3 | 11 | +6.96% |
| low | 2432.00 | 15.0 | 11 | +4.69% |
| high | 2721.59 | 13.9 | 7 | +17.15% |
| low | 2680.62 | 13.5 | 8 | +15.39% |
| low | 2355.61 | 11.2 | 5 | +1.40% |
| high | 2736.32 | 10.6 | 4 | +17.79% |
| low | 2294.98 | 10.5 | 4 | -1.21% |
| low | 2319.21 | 9.9 | 5 | -0.17% |
| low | 2473.84 | 9.8 | 7 | +6.49% |
| low | 2693.08 | 9.7 | 7 | +15.92% |
| high | 2549.53 | 9.5 | 4 | +9.75% |

## Caveats

- Event outcomes overlap; no transaction fees, spread, funding, slippage, position sizing or stop/TP simulation.
- A historical pivot level is only a liquidity *proxy*, not proof of pending stops or forced liquidations.
- MFE/MAE are separate maxima and minima; the ordering is unknown.
- Zone merge width, age, and proximity are exploratory parameters and should be tested out of sample.
- The mirrored-log RSI delta can have discontinuities around RSI 50.
- The initial 7 days are used for warmup. No 2–4 wave-divergence filter is applied in this version.
- Historical zones are reconstructed causally, but the latest-zone snapshot is not a historical heatmap.
