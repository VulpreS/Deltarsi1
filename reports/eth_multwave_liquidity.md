# ETHUSDT 1H — multi-wave DeltaRSI divergence × liquidity proxy

Dataset: 8828 closed candles, 2025-10-26T12:00:00+00:00 to 2026-10-29T07:00:00+00:00.

## Causal wave rule

- Momentum wave peak is confirmed at the **first fading histogram bar**; entry at that candle close.
- A subsequent same-sign wave must be within 72 hours and separated by a trough at least 15% below the smaller peak.
- Bearish divergence: a higher candle high at momentum peak but a DeltaRSI peak at least 8% lower. Bullish is symmetric using candle lows.
- Waves 2, 3 and 4 are counted from the last qualified same-sign wave. A wave-2 divergence is allowed even if a wave-3/4 divergence does not follow.
- Liquidity proximity: a confirmed historical high/low zone within 0.5% of entry close; sweep: wick crosses zone and closes back inside.
- Zone pivots require three right-hand confirmation candles. Current signals cannot use newly confirmed zones until the following candle.

## Results by group (directional close-to-close, before fees)

### All 2–4 wave divergences: 21 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 21 | 52.4% | +0.564% | +1.393% | -1.027% |
| 12h | 21 | 76.2% | +1.160% | +2.350% | -1.193% |
| 24h | 21 | 76.2% | +0.858% | +3.220% | -1.515% |
| 48h | 21 | 57.1% | +1.172% | +3.979% | -2.711% |
| 72h | 21 | 38.1% | +0.754% | +5.240% | -3.573% |
| 120h | 21 | 61.9% | +1.365% | +6.056% | -4.183% |
| 168h | 21 | 57.1% | +0.965% | +7.305% | -4.365% |

### Wave 2 divergences: 5 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 5 | 40.0% | +0.591% | +1.512% | -0.488% |
| 12h | 5 | 80.0% | +2.330% | +3.831% | -0.886% |
| 24h | 5 | 80.0% | +0.001% | +3.981% | -1.539% |
| 48h | 5 | 40.0% | +2.121% | +5.311% | -2.863% |
| 72h | 5 | 60.0% | +3.546% | +8.374% | -2.997% |
| 120h | 5 | 60.0% | +3.209% | +10.138% | -4.007% |
| 168h | 5 | 80.0% | +2.596% | +10.653% | -4.007% |

### Wave 3 divergences: 7 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 7 | 71.4% | +0.562% | +1.567% | -0.881% |
| 12h | 7 | 71.4% | +0.829% | +1.943% | -0.985% |
| 24h | 7 | 71.4% | +0.899% | +2.816% | -1.043% |
| 48h | 7 | 57.1% | -0.014% | +3.176% | -2.680% |
| 72h | 7 | 14.3% | -1.178% | +3.841% | -4.498% |
| 120h | 7 | 71.4% | +0.615% | +4.802% | -5.063% |
| 168h | 7 | 28.6% | -2.091% | +4.911% | -5.063% |

### Wave 4 divergences: 9 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 9 | 44.4% | +0.549% | +1.191% | -1.441% |
| 12h | 9 | 77.8% | +0.768% | +1.843% | -1.525% |
| 24h | 9 | 77.8% | +1.302% | +3.111% | -1.869% |
| 48h | 9 | 66.7% | +1.569% | +3.863% | -2.652% |
| 72h | 9 | 44.4% | +0.705% | +4.585% | -3.173% |
| 120h | 9 | 55.6% | +0.924% | +4.765% | -3.596% |
| 168h | 9 | 66.7% | +2.436% | +7.307% | -4.022% |

### Divergences near liquidity: 17 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 17 | 52.9% | +0.646% | +1.473% | -1.017% |
| 12h | 17 | 76.5% | +1.294% | +2.413% | -1.222% |
| 24h | 17 | 76.5% | +0.958% | +3.417% | -1.514% |
| 48h | 17 | 52.9% | +1.387% | +4.160% | -2.855% |
| 72h | 17 | 35.3% | +0.980% | +5.645% | -3.742% |
| 120h | 17 | 70.6% | +1.939% | +6.581% | -4.124% |
| 168h | 17 | 58.8% | +1.122% | +7.562% | -4.349% |

### Divergences with sweep: 4 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 4 | 50.0% | +0.224% | +1.178% | -0.689% |
| 12h | 4 | 75.0% | +0.378% | +1.357% | -0.851% |
| 24h | 4 | 100.0% | +1.076% | +2.801% | -0.851% |
| 48h | 4 | 75.0% | +1.305% | +3.115% | -1.627% |
| 72h | 4 | 0.0% | -2.323% | +3.115% | -3.693% |
| 120h | 4 | 75.0% | +0.518% | +3.879% | -4.336% |
| 168h | 4 | 25.0% | -0.739% | +4.499% | -4.336% |

### Divergences near or swept: 18 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 18 | 55.6% | +0.639% | +1.469% | -0.994% |
| 12h | 18 | 77.8% | +1.257% | +2.367% | -1.187% |
| 24h | 18 | 77.8% | +0.931% | +3.357% | -1.463% |
| 48h | 18 | 55.6% | +1.367% | +4.059% | -2.730% |
| 72h | 18 | 33.3% | +0.801% | +5.462% | -3.735% |
| 120h | 18 | 66.7% | +1.784% | +6.403% | -4.166% |
| 168h | 18 | 55.6% | +0.857% | +7.330% | -4.379% |

### Divergences away from liquidity: 3 signals

| Horizon | N | Win rate | Mean return | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|
| 6h | 3 | 33.3% | +0.113% | +0.935% | -1.228% |
| 12h | 3 | 66.7% | +0.581% | +2.246% | -1.228% |
| 24h | 3 | 66.7% | +0.422% | +2.394% | -1.830% |
| 48h | 3 | 66.7% | +0.008% | +3.496% | -2.600% |
| 72h | 3 | 66.7% | +0.467% | +3.905% | -2.600% |
| 120h | 3 | 33.3% | -1.152% | +3.980% | -4.283% |
| 168h | 3 | 66.7% | +1.613% | +7.152% | -4.283% |

## Most recent qualifying events

| UTC | Direction | Wave | Entry USDT | Delta peak | Near zone | Sweep |
|---|---|---:|---:|---:|---|---|
| 2025-11-07T13:00:00+00:00 | long | 4 | 3240.99 | 25.365 | yes | no |
| 2025-11-08T05:00:00+00:00 | short | 4 | 3431.18 | 35.998 | yes | no |
| 2025-12-06T01:00:00+00:00 | long | 2 | 3026.82 | 56.356 | yes | no |
| 2025-12-07T15:00:00+00:00 | long | 3 | 3027.01 | 32.07 | yes | no |
| 2026-02-03T06:00:00+00:00 | short | 2 | 2320.48 | 31.769 | yes | no |
| 2026-03-02T17:00:00+00:00 | short | 3 | 2041.01 | 26.192 | yes | no |
| 2026-03-19T15:00:00+00:00 | long | 3 | 2118.81 | 24.809 | yes | yes |
| 2026-03-19T17:00:00+00:00 | long | 3 | 2126.96 | 24.272 | no | yes |
| 2026-03-19T19:00:00+00:00 | long | 3 | 2141.19 | 24.73 | yes | no |
| 2026-03-20T01:00:00+00:00 | long | 3 | 2150.88 | 23.677 | yes | no |
| 2026-03-20T07:00:00+00:00 | long | 3 | 2150.54 | 18.172 | yes | yes |
| 2026-03-21T07:00:00+00:00 | short | 4 | 2155.67 | 23.513 | yes | yes |
| 2026-03-21T10:00:00+00:00 | short | 4 | 2154.34 | 26.724 | yes | no |
| 2026-05-13T20:00:00+00:00 | long | 4 | 2263.75 | 17.823 | yes | no |
| 2026-06-09T15:00:00+00:00 | long | 4 | 1636.4 | 48.011 | no | no |
| 2026-07-06T13:00:00+00:00 | long | 2 | 1744.89 | 38.412 | yes | no |
| 2026-07-26T07:00:00+00:00 | short | 2 | 1881.56 | 44.889 | yes | no |
| 2026-08-23T03:00:00+00:00 | long | 4 | 2413.98 | 30.908 | yes | no |
| 2026-09-23T11:00:00+00:00 | long | 4 | 2727.96 | 31.58 | yes | no |
| 2026-09-23T14:00:00+00:00 | long | 4 | 2676.36 | 33.461 | no | no |

## Limitations

- This is a defined, exploratory 2–4-wave interpretation, not a claim that the user's visual wave counting is identical.
- These are stop-liquidity proxies based on historical OHLCV, **not** actual CoinGlass liquidation clusters.
- No commissions, slippage, funding, stop/TP, or intrabar execution-order modeling.
- Overlapping event horizons violate independent-trial assumptions; small groups are unstable.
- Parameters were chosen heuristically and have not been validated out of sample.
- This uses first absolute-magnitude fading, not an exact comparison of Pine rendered RGB shades.
