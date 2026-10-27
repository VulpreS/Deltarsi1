# Upscale Crypto Backtester

## Current objective: both stages in 14 days

The current Actions experiment is `python -m upscale.fortnight`. It evaluates
both stages within **14 calendar days total**, including the 3/5 profitable-day
requirements and strict API 30% consistency. Weekly UTC starts use only full
windows; 4h and 1h histories are evaluated separately. Fixed variants: trend
lookbacks 20/40, both directions or long-only, per-trade risk 0.25% / 0.5% / 1%.
Portfolio risk budget is twice per-trade risk; internal daily guard is 2.5%,
other loss and exposure controls remain. This is a risk/direction sensitivity
experiment, not an invitation to increase risk on an unprofitable strategy.

No winner is selected from this already-inspected history. Report every start,
pass, phase-1 completion, modeled breach and timeout. A timeout is a missed
research deadline, not a prop rule violation. Overlapping windows are dependent.
Conservative adverse-extreme guard execution can overstate losses/violations
relative to continuous monitoring; exact path and fill data are unavailable.

```bash
python -m unittest discover -s tests_upscale -v
python -m upscale.fortnight --out reports/upscale_14d
```

The older 180-day experiment below remains reproducible as a historical
baseline, but is not the user's target or the current Actions default.


Offline research using existing BTC/ETH CSV cache only. Does not fetch candles,
read credentials, connect exchange accounts or send orders. Shared account NAV
starts at 1; account dollar size is not required for percentage-based research.

Run:

```bash
pip install numpy==2.2.6 pandas==2.2.3
python -m unittest discover -s tests_upscale -v
python -m upscale.backtest --out reports/upscale
```

GitHub Actions runs the same commands, writes a job summary, and uploads all
results as artifacts without committing generated files or modifying old strategies.

## Historical baseline: frozen first experiment

Six candidates: trend, range, mixed, each with lookback 20 or 40. BTC and ETH,
4-hour candles. Signals at closed candle, execution next open. Both directions.
Trend: close breaks prior N-bar extreme, ATR(14) RMA stop 2 ATR,
exit on previous close crossing opposite 10-bar channel or after 120 hours.
Range: prior close outside 2 standard deviation band, current close back inside;
directional efficiency <0.3; stop 1.5 ATR, target prior known middle, 24-hour cap.
Mixed: choose trend when efficiency >=0.3, otherwise range. One position per symbol.
No pyramiding, averaging down, or volume assumptions. Thresholds are hypotheses.

Development 2020–2023, validation 2024, historical holdout 2025 onward.
Select only on 2024 return/max(1%, drawdown), requiring positive development and
validation, >=20 validation trades, and no validation breach. No fallback winner
if all fail. These data have been studied before: not a sealed or forward test.

Risk per trade 0.25% of initial NAV including reserved fees and fill slippage;
aggregate reserved stop risk <=0.75%; aggregate notional <=5x equity.
Internal daily guard 1.5%; halve new risk below initial NAV -4%; no new entries
below -6%. No promise of live drawdown protection.

Costs: 0.008% per fill; adverse 0.02% slippage per fill; crypto funding 0.015%
of current notional at UTC 00/08/16. Default entry spacing per symbol >=4h,
consistent with BTC/ETH zero-spread >=1h rule; slippage remains charged.
2x-slippage and long-only holdout diagnostics on selected candidate. Hourly cache
is a separate diagnostic, not spliced into four-hour execution data.

## Challenge simulation

Monthly starts in 2025+ with a full 180-day history window. Both stages sequential:
5% / 8% realised gain, 3 / 5 profitable UTC days (>=0.5% initial NAV), best day
strictly <30% of total gain, daily equity loss 5%, static total loss 10%.
Phase 2 conservatively resets to NAV=1. The documentation says stages use the
same account: verify reset/profit carryover details with account before deployment.
Windows overlap; pass share is descriptive, not a future success probability.
API 60-second adjustment: entry-bar positive stop/target closes conservatively
zeroed; negative PnL and all costs retained. Exact intrabar time cannot be known.
Stops precede targets; portfolio adverse extremes conservatively simultaneous.
Day baseline is UTC opening equity, including floating PnL; funding charged after
baseline and before exits/new entries. Uncertain settlement ordering must be
reconciled against actual platform statements in paper trading.

CSV validation rejects gaps, duplicates, invalid OHLC and misaligned timestamps.
Always discards final source candle. Results include hashes and source boundaries.
Exchange candles are proxies for Upscale oracle quotes, not exact fill evidence.
No 15m data exist in this cache; no 15m claims are made. New $200k Basic stage
2/funded 8% total drawdown is NOT modeled by this 10% configuration.

Sources checked 2026-10-27:
- https://docs.upscale.trade/how-to-join-upscale/participation_requirements
- https://docs.upscale.trade/trading-mechanics/fees
- https://docs.upscale.trade/trading-mechanics/funding

Until paper verification and prospective validation, every candidate is research only.
