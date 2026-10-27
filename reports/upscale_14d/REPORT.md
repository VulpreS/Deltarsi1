# Both Upscale stages within 14 calendar days

Existing candles only. Fixed trend20/40, both directions / long only, risk 0.25% / 0.5% / 1%.
All predefined variants shown; no independently validated winner selected.

| Candidate | Starts | Phase 1 done | Both passed | Passed % | Failed | Timeout | Median days if passed |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4h_trend20_both_risk0.25 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend20_both_risk0.5 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend20_both_risk1 | 93 | 1 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend20_long_risk0.25 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend20_long_risk0.5 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend20_long_risk1 | 93 | 1 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_both_risk0.25 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_both_risk0.5 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_both_risk1 | 93 | 1 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_long_risk0.25 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_long_risk0.5 | 93 | 0 | 0 | 0.0 | 0 | 93 | — |
| 4h_trend40_long_risk1 | 93 | 1 | 0 | 0.0 | 0 | 93 | — |
| 1h_trend20_both_risk0.25 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend20_both_risk0.5 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend20_both_risk1 | 50 | 0 | 0 | 0.0 | 4 | 46 | — |
| 1h_trend20_long_risk0.25 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend20_long_risk0.5 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend20_long_risk1 | 50 | 0 | 0 | 0.0 | 3 | 47 | — |
| 1h_trend40_both_risk0.25 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend40_both_risk0.5 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend40_both_risk1 | 50 | 0 | 0 | 0.0 | 1 | 49 | — |
| 1h_trend40_long_risk0.25 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend40_long_risk0.5 | 50 | 0 | 0 | 0.0 | 0 | 50 | — |
| 1h_trend40_long_risk1 | 50 | 0 | 0 | 0.0 | 1 | 49 | — |

## Interpretation

A pass must satisfy both profit targets, minimum profitable days and strict best-day consistency, after costs. Merely reaching +13% at some point is not enough.
Timeout means not completed within the requested 14 days. See each window and completion timestamps in results.json. Final-stage NAV is not cumulative two-stage return.

## Limits of evidence

- Already inspected history: this is a retrospective diagnostic, not fresh out-of-sample evidence.
- Weekly 14-day windows overlap; descriptive pass percentages are not independent future probabilities.
- 1h and 4h have different data coverage. Compare risk/direction within each timeframe, not raw pass rates across timeframes.
- BTC/ETH exchange OHLC proxy rather than Upscale oracle execution; 60-second positive entry-bar closes conservatively zeroed.
- Simultaneous adverse extremes and stop-first ordering are conservative OHLC assumptions. Guard exits at adverse extrema may overstate losses and modeled breaches relative to continuous real-time monitoring.
- Phase 2 starts at independent NAV=1; actual platform stage carryover details require confirmation.
- 5%/8% targets, 3/5 profitable days >=0.5%, best day strictly below 30%, 5% daily and 10% static total loss assumed.
- Day-end phase checks only: this conservative scheduling may defer intraday qualification to midnight.
- Internal daily guard 2.5%; half risk at initial-equity loss 4%; stop new entries at 6%; portfolio stop budget twice per-trade risk; max 5x notional.
- 14 days is the research target requested by user, not an Upscale deadline; timeout is not disqualification.
- 10% total loss configuration excludes new $200k Basic 8% phase-2/funded exception.
- First-pass ledgers are illustrative, not representative; all outcomes are included in windows JSON/CSV.
