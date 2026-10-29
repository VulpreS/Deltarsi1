# Isolated experiment: one full-position TP per run

Research only. NOT production logic. Do not import into trading bot, official challenge reports, or other strategy optimizations.

## Exact user clarification (2026-10-29)
ONE position, ONE take-profit per run. FIVE INDEPENDENT runs, NOT five partial exits.

For trades whose baseline strategy target is GREATER than 2.5% favorable movement of the underlying asset, replace that target with one of:
- Run A: full exit at +0.5%
- Run B: full exit at +1.0%
- Run C: full exit at +1.5%
- Run D: full exit at +2.0%
- Run E: full exit at +2.5%

Trades with baseline target <=2.5% retain their original baseline exit logic. Use the same entry signal, position sizing, initial stop, stop management (including any existing breakeven rule), and non-target exit rules in all five runs. The whole position closes on the first triggered exit, no partial TP, no pyramiding. For shorts, targets are favorable downward underlying-price moves, NOT levered ROI.

Do not filter trades based on whether their *realized future* baseline PnL was >2.5%; qualifying trades must be identified using the predeclared target known at entry, without lookahead.

## Test methodology
- Pin a named baseline implementation and exact dataset; compare the five runs against an unmodified baseline.
- Evaluate on closed-candle entry signals; execute with intrabar stop/target detection using available OHLC. For a bar containing both SL and TP, assume SL first unless reliable finer-grained sequence exists. Preserve gap/slippage assumptions.
- Apply the same fees, spread, funding policy, and prop-account risk rules in all variants.
- Report per-run: count of eligible trades, all trades, net PnL, win rate, profit factor, max drawdown, stop/BE frequency, average holding time, and challenge pass/fail; split by asset and period.
- Changing TP may change trade duration and hence future eligible entry sequence. Distinguish matched-entry trade comparison from full sequential portfolio replay; do not incorrectly claim both have identical executed trades.
- This is an opt-in research specification, not an implemented or completed backtest. No live/demo orders or workflow trigger.

## Isolation
Only files inside experiments/fixed_tp_grid/ may implement this test; do not modify production strategy or its outputs. This repository is not private merely because the experiment is in a separate directory.
