# Upscale Crypto Backtester

## Current experiment: owner DeltaRSI journal color rules

Actions runs `python -m upscale.rsi_study --out reports/upscale_rsi`.
Uses the current root `Delta`: SMA21 -> Wilder RSI12 -> EMA7 -> mirrored signed
log delta. The Pine display multiplier 1.5 does not modify raw color threshold 60.
The four intensity branches are preserved; equality is gray rather than weak.

Mechanical reconstruction from the owner's journal: LONG medium/faint red ->
weak red; SHORT first weak blue after strong/medium/faint blue. Entry after a
fully closed 4H candle at next 1H open, exit on the unfiltered opposite journal
signal at next open. No fixed TP or arbitrary 24/48-hour cap; protective stops,
account guards and challenge/sample-end closures remain. Long-only entries still
retain short signals for exiting longs. Historical indicators are reconstructed
from the SAME complete cached 1H bars used for execution, without source splicing.

Stop is not uniquely specified by the journal. Two disclosed assumptions are
compared: extreme of actual peak-|delta| candle in known same-sign wave, and
extreme of the whole known same-sign wave. No added buffer. Invalid or >5%
price-stop geometry rejects entry. Margin 10/15%, leverage 1/2/3, 30-day both-stage
goal, costs and extra safeguards remain as documented below.

This is NOT a claim that every fade is the owner's full entry rule. Manual
price-context selection, exceptional bright-to-medium + buybacks entry,
forming-candle timing and partial exits are not fully formalized. The 42 manual
annotations provide textual rule context, not replayed verified fills or training
labels. Indicator, source/journal hashes, all eligible signals, every trade and
all attempted profiles are exported. No winner is selected on inspected history.

Prior study commands remain available separately:
- `python -m upscale.margin_study --days 30 --out reports/upscale_margin_30d`
- `python -m upscale.margin_study --days 14 --out reports/upscale_margin`
- `python -m upscale.fortnight --out reports/upscale_14d`

## Previous experiments


## Current position model: fixed margin, leverage at most 3

The previous margin-only workflow ran `python -m upscale.margin_study --days 30 --out reports/upscale_margin_30d`.
The margin comparison allows **30 calendar days total for both stages**. The comparison
reruns the 14-day baseline on exactly the same eligible weekly start dates, with
all sizing, entry/exit rules, costs and research safeguards unchanged. Prior
14-day reports remain in their original folder. Reproduce the old horizon with
`--days 14 --out reports/upscale_margin`.
User constraints: margin 10–15% of account equity; leverage no greater than 3;
stop no farther than 5% price movement; both challenge stages in 30 days.
Fixed experiment uses margin 10% / 15% and leverage 1 / 2 / 3 on the same
trend20/40 baselines and 1h/4h cached BTC/ETH candles, both directions / long only.
This changes sizing, not the already rejected entry/exit hypothesis.

Notional = current pre-entry equity × margin fraction × leverage. ATR stop
above 5% rejects the entry; tighter stops do not increase notional. No hidden
inverse-stop sizing or margin reduction at 4% drawdown. Costs remain separate.

Extra research safeguards (not supplied by user): <=4% initial NAV aggregate
reserved stop risk, planned all-stop equity >=96% UTC-day-start and >=92%
initial NAV, daily guard 2.5%, stop new entries below initial NAV -6%. An entry
that does not fit is skipped and counted rather than resized. These limits
can affect passage speed; they are disclosed in the report.

Every window and trade is exported, including failed and timed-out windows.
Trade fields expose margin, notional, pre-entry equity, stop percent and planned
loss percent. Monthly or weekly overlapping windows are dependent observations.

## Previous experiment: fixed risk, both stages in 14 days

The previous fixed-risk experiment is `python -m upscale.fortnight`. It evaluates
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
