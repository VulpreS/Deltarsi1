# DeltaRSI manager directives — 2026-10-26, cycle 1

**Authority:** research coordination only. No real orders, API trading permissions, leverage deployment, or production promotion. All currently inspected historical segments are **contaminated by prior model selection**; do not call them independent OOS.

## Review inputs
- `reports/research_handoff.md` (researcher cycle 1): synthetic Candidate B execution checks passed, timestamp/volume and funding still open.
- `reports/audit_2026-10-26.md`: historical 5-slice baseline, gap-filling claimed in an independent JS audit; corrected split boundary and stale paper-alert bar; no independently verified edge.
- `reports/feature_walkforward.json`: 3,240 candidate search, strongest train/validation models often fail on final quarter; winner's curse.
- `reports/pattern_confluence.json`, `reports/dynamic_exits.json`, `reports/structural_exits.json`: explorations after examining all segments, not confirmatory results.
- Code: `feature_walkforward.py`, `research_multiasset.py`, `dynamic_exit_research.py`, `structural_exit_research.py`, `analyze_mtf_5y.py`, `paper_signal_4h.py`, `test_candidate_b_semantics.py`.

## Decision register
| Finding | Decision | Why |
|---|---|---|
| Candidate B synthetic next-open, same-bar stop-first and split boundary checks | **Verified only for covered fixtures** | CI passed, but fixtures omit gap-through-stop, venue timestamp/volume parity and funding. |
| Fixed 2.5ATR stop / 3ATR target / 12×4h baseline | **Keep as frozen reference, not validated production strategy** | BTC five historical PF slices 1.28/1.37/1.33/1.01/1.73, but selection exposure and execution costs remain. |
| BTC/ETH OHLC order-block proxies, ICP EMA200 gate | **Exploratory only** | Retrospectively selected after inspecting all three segments; OB is not actual order-book liquidity. |
| Break-even, ATR trailing, structural exit, reverse DeltaRSI | **No promotion** | Changes trade scheduling; inconsistent improvement, some windows worse. Reverse signal in structural experiment uses already filtered entry signal, NOT raw opposite DeltaRSI. |
| HYPE deployment | **Rejected pending fresh evidence** | Baseline PF 0.79 on reused full sample; venue provenance and short history uncertain. |
| 157 annual trades across BTC/ETH/ICP | **Historical descriptive count only** | Selected 55+43+59 trades from ~one-year BTC/ETH/ICP cached history; no guarantee of future count, simultaneous signals can overlap. |

## Blocking defects and audit discrepancies
1. **P0 gap-through-stop:** `feature_walkforward.sim()`, `research_multiasset.simulate()`, and `structural_exit_research.sim()` fill a touched stop at `stop`, even when next bar opens beyond stop (optimistic fill). `dynamic_exit_research.simulate()` uses adverse open-vs-stop logic. This makes exit comparisons apples-to-oranges and conflicts with the audit document's statement that adverse gaps use worse fills. Correct a shared execution engine or explicitly normalize all experiments.
2. **P0 inconsistent comparison cohort:** `structural_exit_research` and dynamic exits allow earlier exit -> earlier re-entry. Thus differing N and mean returns do not identify causal improvement from exit alone. Use same entry IDs / one entry cohort and a separate realistic non-overlap portfolio analysis.
3. **P0 reverse-signal semantics:** `structural_exit_research.sim` receives `filtered` features, so its `rev` only triggers if the opposite DeltaRSI also passes the ENTRY order-block/EMA filter. Rename or add true unfiltered opposite-DeltaRSI exit.
4. **P0 candle/volume parity:** `analyze_mtf_5y.aggregate()` always drops final bucket, and does not check four source 1H bars for every intermediate 4H bucket. Paper-alert fix is local to `paper_signal_4h.py`. Verify UTC alignment, missing hours, completed bars, exchange/venue and OHLCV provenance, and volume SMA20 lag.
5. **P0 realistic execution economics:** historical fee `FEE=.0015` assumes 0.15% round trip (fees + slippage), but is not venue-specific; funding/impact/mark-trigger liquidation and correlated exposure are absent.
6. **P1 reproducibility:** source CSV data provenance, hashes, exact UTC cutoff, executable workflow commit SHA, and frozen parameters must accompany each result.

## Mandatory researcher tasks (do in priority order)
### P0-A: Execution parity and regression tests
**Hypothesis:** correcting adverse gap fills and matching stop/TP/time semantics will materially change reported exit rankings.
**Acceptance:** single deterministic engine or parity adapter for baseline and exit variants; fixtures for LONG and SHORT gap-through-stop, stop+target same bar, stop+target gap, last-bar time exit, first eligible next-bar entry, split boundary, stale/missing OHLC, trailing update only after bar close, and actual unfiltered reverse signal. CI fails on original gap bug and passes after correction. Rerun frozen 2.5/3/12 baseline and each selected variant on exactly the same cached data; publish old vs corrected N, win%, mean net%, PF, max DD and source hashes. NO parameter search against previously labeled 'holdout'.
### P0-B: OHLCV timestamp and venue audit
**Hypothesis:** data-source/aggregation differences can account for some apparent edges.
**Acceptance:** for each asset, record exchange, market type (spot/perpetual), symbol, source URL/endpoint, first/last UTC hour, gaps, duplicates, checksums; 1H->4H OHLCV parity against direct 4H venue candles on at least 30 randomly chosen fully closed buckets per symbol, tolerance defined in advance; test complete/incomplete/missing intermediate buckets; SMA20 volume lag fixture excludes current bar; report unmatched venues separately rather than mixing.
### P1-C: Honest exit comparison and portfolio accounting
**Hypothesis:** reverse DeltaRSI improves risk-adjusted expectancy compared with 48h fixed exit on matched entries.
**Acceptance:** freeze entry signal timestamps and side; run fixed, raw-reverse, structural and trailing exits on identical initial entry IDs, report matched-pair return delta and 95% time-block bootstrap CI, including missed follow-up signals as a distinct executable-portfolio analysis. Same stop-gap/fee logic. Simulate cross-asset concurrent exposure with equity-risk sizing, caps, funding and 0.15/0.25/0.40% total cost scenarios; show annualized turnover, profit factor, max DD, return/DD, worst monthly loss, exposure and trade count. No strategy approval based on historical best cell.
### P1-D: Forward-only shadow collector
**Hypothesis:** frozen baseline plus at most one predeclared challenger can sustain positive net expectancy in newly arriving candles.
**Acceptance:** append-only forward OHLCV with receipt timestamps strictly AFTER 2026-10-26 16:00 UTC (freeze time), immutable signal/entry/exit audit log, versioned strategy hash and venue; never backfill as 'forward'; shadow fills only, no orders; include funding when data available, otherwise conservative stress with explicit missing-data flag. Pre-register pass/fail criteria and minimum duration/sample size before observing forward outcomes; no tweaking using the forward evaluation stream. Compare to frozen baseline on identical calendar periods. PAPER ONLY.

## Next-cycle checks
1. Read latest researcher handoff, issue comments, workflow status and commits. Verify P0-A gap regression and raw reverse semantics first.
2. Reconcile `reports/audit_2026-10-26.md` gap claim with current Python simulators; demand erratum if different engines.
3. Check P0-B venue/timestamp evidence, then P1-C matched cohort, then P1-D immutable forward stream.
4. Classify each task DONE / PARTIAL / BLOCKED with commit SHA, tests and numbers. Do not promote a strategy without a clean forward sample and separate explicit user approval for production.
