# DeltaRSI journal rules: Upscale, both stages within 30 days

Mechanical reconstruction of the current indicator and journal color rules. No claim to reproduce all discretionary selection. BTC/ETH shared equity, 4H signals, 1H execution.

| Candidate | Starts | Phase 1 | Both passed | Modeled breaches | Timeout | History return % | History PF | History trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| delta4h_peak_bar_both_m10_x1 | 47 | 0 | 0 | 0 | 47 | 2.42 | 1.09 | 314 |
| delta4h_peak_bar_both_m10_x2 | 47 | 1 | 0 | 0 | 47 | 4.53 | 1.09 | 314 |
| delta4h_peak_bar_both_m10_x3 | 47 | 1 | 0 | 0 | 47 | -6.79 | 0.00 | 12 |
| delta4h_peak_bar_both_m15_x1 | 47 | 1 | 0 | 0 | 47 | 3.51 | 1.09 | 314 |
| delta4h_peak_bar_both_m15_x2 | 47 | 1 | 0 | 0 | 47 | -6.79 | 0.00 | 12 |
| delta4h_peak_bar_both_m15_x3 | 47 | 1 | 0 | 0 | 47 | -6.38 | 0.00 | 7 |
| delta4h_peak_bar_long_m10_x1 | 47 | 0 | 0 | 0 | 47 | 0.55 | 1.05 | 155 |
| delta4h_peak_bar_long_m10_x2 | 47 | 0 | 0 | 0 | 47 | 0.96 | 1.04 | 155 |
| delta4h_peak_bar_long_m10_x3 | 47 | 0 | 0 | 0 | 47 | 1.23 | 1.03 | 155 |
| delta4h_peak_bar_long_m15_x1 | 47 | 0 | 0 | 0 | 47 | 0.77 | 1.04 | 155 |
| delta4h_peak_bar_long_m15_x2 | 47 | 0 | 0 | 0 | 47 | 1.23 | 1.03 | 155 |
| delta4h_peak_bar_long_m15_x3 | 47 | 0 | 0 | 0 | 47 | 0.41 | 1.01 | 155 |
| delta4h_whole_wave_both_m10_x1 | 47 | 1 | 0 | 0 | 47 | 7.10 | 1.20 | 353 |
| delta4h_whole_wave_both_m10_x2 | 47 | 3 | 0 | 0 | 47 | 14.76 | 1.21 | 352 |
| delta4h_whole_wave_both_m10_x3 | 47 | 3 | 0 | 0 | 47 | 21.63 | 1.19 | 353 |
| delta4h_whole_wave_both_m15_x1 | 47 | 3 | 0 | 0 | 47 | 11.09 | 1.21 | 352 |
| delta4h_whole_wave_both_m15_x2 | 47 | 3 | 0 | 0 | 47 | 21.63 | 1.19 | 353 |
| delta4h_whole_wave_both_m15_x3 | 47 | 2 | 0 | 0 | 47 | -6.18 | 0.06 | 10 |
| delta4h_whole_wave_long_m10_x1 | 47 | 0 | 0 | 0 | 47 | 0.01 | 1.00 | 170 |
| delta4h_whole_wave_long_m10_x2 | 47 | 0 | 0 | 0 | 47 | -0.18 | 0.99 | 170 |
| delta4h_whole_wave_long_m10_x3 | 47 | 0 | 0 | 0 | 47 | -6.07 | 0.00 | 10 |
| delta4h_whole_wave_long_m15_x1 | 47 | 0 | 0 | 0 | 47 | -0.06 | 1.00 | 170 |
| delta4h_whole_wave_long_m15_x2 | 47 | 0 | 0 | 0 | 47 | -6.07 | 0.00 | 10 |
| delta4h_whole_wave_long_m15_x3 | 47 | 0 | 0 | 0 | 47 | -6.61 | 0.00 | 8 |

## Exact scope and limits

- Indicator is the current repository Delta: SMA21 -> Wilder RSI12 -> EMA7 -> mirrored signed logarithmic delta. Display multiplier 1.5 does not change color threshold 60.
- Journal-derived mechanical LONG: medium/faint red -> weak red. SHORT: first weak blue after strong/medium/faint blue. No repeated entry on consecutive weak bars. Original four Pine intensity branches retained; equal magnitude is gray.
- Entry at next hourly open after a fully closed UTC 4H signal. 4H candles are constructed solely from four complete cached hourly candles, not spliced with a different 4H source.
- Exit on the opposite unfiltered journal color signal at next hourly open, or protective stop or account guard. No fixed TP, ATR exit, arbitrary 24/48h cap or forced RSI cross filter. Window end closes remaining positions.
- Structural stop is an assumption, not a uniquely recovered user rule: low/high of maximum-abs-delta candle in current same-sign wave, versus low/high of the entire known same-sign wave. Both are known before entry, zero extra buffer. Invalid/wider-than-5% stops reject entry.
- This is not the full manual strategy. Manual price-context selection, bright-to-medium-plus-buybacks exception, intrabar/forming-4H entries and discretionary partial exits are not specified sufficiently to reproduce.
- The 42 manual annotations are not replayed as verified fills or used for parameter fitting. They only establish textual color-entry/exit reasons. No claim of the owner's manual win rate.
- Margin 10/15% current pre-entry equity; leverage 1/2/3; same costs and research safeguards as previous Upscale experiments. Extra safeguards: daily guard 2.5%, planned all-stop NAV >=96% day-start and >=92% initial NAV, reserved stop risk <=4% initial NAV, stop new entries at initial NAV -6%.
- Source history is previously inspected. Weekly challenge windows overlap; counts are not independent future success probabilities. No ranking or tuning on these results.
- Hourly OHLC cannot reproduce exact intrahour prices, Upscale oracle execution or 60-second profit adjustment. Stop-first/adverse-extreme assumptions can overstate losses. Fees/slippage/funding retained.
- Stage model remains 5%/8% targets, 3/5 profit days >=0.5%, strict best-day <30%, 5% daily and 10% total loss, independent NAV reset for phase 2 and UTC day-end qualification. Platform stage carryover remains an assumption; new $200k 8% exception not modeled.
