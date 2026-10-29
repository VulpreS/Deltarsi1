# Isolated experiment: five partial take-profits

Research only. NOT production logic. Do not import this experiment into the trading bot or official challenge reports.

## Hypothesis
For trades where the baseline strategy's intended take-profit exceeds 2.5% of underlying price movement, compare baseline execution against a single position split into five equal partial exits.

## Exit schedule
- At +0.5% favorable price movement: close 20% of initial position.
- At +1.0%: close another 20%.
- At +1.5%: close another 20%.
- At +2.0%: close another 20%.
- At +2.5%: close remaining 20%.
- Keep the baseline stop-loss and its existing adjustment rules, including breakeven move at +1% if applicable. On stop hit, close only remaining quantity. Previously realized partial profits remain realized.
- For short positions, favorable moves are downward; percentages are underlying price changes, not account PnL or levered ROI.
- For trades whose baseline target is <=2.5%, retain baseline exit logic without modification.
- On candles touching both stop and target(s), use lower-timeframe sequence if available; otherwise apply conservative stop-first handling and report ambiguity. No lookahead.
- Commission on each exit leg and entry, spread/slippage, rounding, min order size, and funding assumptions must be accounted for.
- Equal 20% allocations are a provisional assumption, pending user confirmation.

## Reporting
Compare to original baseline on identical signals: net PnL, win rate, max drawdown, realized reward/risk, MFE/MAE, number of filled partial targets, stop frequency, time in trade, and prop challenge pass/fail metrics. Separate by symbol and timeframe, especially 4h. Do not blend into official results.

## Safety
This directory is a specification only. No trading orders, API keys, workflow triggers, or automated production integration. Keep this experiment explicitly opt-in.
