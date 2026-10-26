# DeltaRSI ETHUSDT 1H — preliminary fading study

Period: 2026-09-26 12:00 UTC to 2026-10-26 11:00 UTC (720 candles).
Source: data/ETHUSDT_1h.csv, repository VulpreS/Deltarsi1.

## Method
SMA21(close), Wilder RSI12, EMA7(RSI), mirrored signed logarithmic delta from Delta.
On each fully observed hourly bar, test abs(delta[t]) < abs(delta[t-1]); first-fading subset additionally requires abs(delta[t-1]) > abs(delta[t-2]).
For positive delta, hypothetical short; for negative delta, hypothetical long.
Measure close-to-close directional returns at +1,+3,+6,+12,+24 hours.
All signals are treated as events, not executable positions; overlapping events are allowed.
No fees, spread, slippage or funding. RSI seeding may differ slightly from TradingView.
In this implementation every strict fall in magnitude also transitions to a lower-intensity color tier in the Pine color scheme (the >60 boundary may be crossed). This is not a comparison of perceived screen brightness.

## First fading bar after growth (99 events)
| Horizon | Available events | Directional win rate | Mean directional return |
|---|---:|---:|---:|
| 1h | 99 | 51.5% | -0.055% |
| 3h | 99 | 44.4% | -0.032% |
| 6h | 99 | 46.5% | -0.065% |
| 12h | 98 | 49.0% | +0.059% |
| 24h | 97 | 51.5% | +0.180% |

## All falling bars (381 events)
| Horizon | Available events | Directional win rate | Mean directional return |
|---|---:|---:|---:|
| 1h | 381 | 47.8% | -0.003% |
| 3h | 379 | 49.3% | +0.016% |
| 6h | 376 | 50.0% | +0.043% |
| 12h | 374 | 49.5% | +0.047% |
| 24h | 364 | 48.1% | -0.007% |

## Caveats
- These are event-level statistics, not a strategy backtest.
- Only 30 days of data; sample is too small to establish an edge.
- Repeated signals in one wave create dependence and overcounting.
- The mirrored log delta has degeneracies when RSI and EMA straddle 50.
- A separate test should classify multi-wave divergence only using peaks already confirmed at the time of entry, and measure MFE/MAE, transaction costs, and walk-forward performance.
- The original wave report uses a different definition (completed positive waves), so its count of 3 divergences must not be compared directly with other definitions.
