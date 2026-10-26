# DeltaRSI researcher handoff — cycle 4, 2026-10-26 (P0 #7 completed 4H bars)

**Decision: P0 #7 CODE + SYNTHETIC TESTS DONE; historical comparison DONE; NO PROMOTION / RESEARCH ONLY.** Workflow [40382846181](https://github.com/VulpreS/Deltarsi1/actions/runs/40382846181) SUCCESS, producer commit `6323a539b9d50c1b2ac9f4cdcf331bb4419da8c4`; deterministic seed 20261026; cached CSV only, no downloads, no live orders. All chronological slices are **previously inspected historical data, NOT independent OOS**.

## Cycle 4 addendum — missing-interior HTF look-ahead guard (2026-10-26)

During review of strict aggregation, found **a second latent data-timing defect** in `analyze_mtf_5y.main.lookup`: it indexed HTF bars arithmetically, assuming no skipped intermediate 4H/1D bucket. After strict aggregation drops an incomplete interior bucket, this could select a **future** HTF bar at an earlier 1H signal timestamp. Fixed `last_closed_htf_index` using actual UTC close timestamps and `bisect_right`; new regression covers a missing 04:00–08:00 bucket, ensuring the 08:00 bar is not visible at the 07:00 1H signal. **This is a real potential look-ahead defect in gappy datasets; cached BTC/ETH/ICP/HYPE 1H data have zero missing hours, so no demonstrated historical effect.** New CI [40383121465](https://github.com/VulpreS/Deltarsi1/actions/runs/40383121465) verifies updated fixtures and reruns cached audit; original cycle-4 metrics unchanged. No orders or downloads. For newly arriving datasets with missing HTF buckets, future work should also make time-based hold/ATR semantics explicit across gaps.

## Hypothesis and manager priorities
Read manager directives (latest 18:51 UTC), issues #7 (P0 strict aggregation), #6 (funding/net paired CI), #5 (venue/portfolio/forward), and prior handoff. Hypothesis: legacy permissive 4H bucketing admits incomplete first 4H bar and drops a fully closed final bar, affecting signals or trades. Prioritize #7 before any parameter search.

## Changes and reproducibility
- Added `completed_candles.py` with one UTC-aligned, as-of-gated strict engine: all 4 constituent 1H open times must be present, in order, and fully closed by as-of; rejects duplicate, non-monotonic, invalid OHLC. Research `analyze_mtf_5y.aggregate` and `paper_signal_4h.aggregate_completed_4h` now use this shared engine. Historical default as-of is inferred from the final cached 1H bar close; paper requires actual wall-clock as-of.
- `feature_walkforward.data(sym,aggregation='legacy'|'strict')` preserves the legacy engine **audit-only** for exact before/after comparisons; same feature formulas and execution. Added `test_completed_candles.py` with partial first (1/2/3/4 source hours), interior gap, duplicate/out-of-order, complete/incomplete final, as-of at/just before close, UTC boundaries, invalid OHLC, research/paper parity. Updated older `test_candidate_b_semantics.py` expectation to retain a fully closed final bar.
- Added `aggregation_impact_audit.py` and workflow `.github/workflows/p0-strict-aggregation.yml`. GitHub Actions SUCCESS (all new and prior execution regression tests, frozen cache audit). The earlier P0 execution workflow 40382669548 failed only because a *new synthetic parity fixture* used monotonic prices with undefined RSI/Delta NaN; fixture replaced by oscillating prices; successful 40382846181 supersedes that fixture failure.
- Machine-readable `reports/aggregation_impact.json`: source hashes, exact producer SHA, CI run ID, five UTC non-overlapping window boundaries, UTC-mapped signal/entry/side keys, before/after metrics at 15/25/40 bp assumed round-trip fees+slippage, baseline and retrospectively selected filters. No actual funding available in this **aggregation-only** audit.

## Cached-data results (fixed 2.5 ATR stop / 3 ATR target / 12×4H)
| Asset | Legacy → strict 4H bars | Legacy → strict trades | Legacy → strict 15bp PF | Key changes |
|---|---|---|---|---|
| BTC | 2190 → 2189 | 130 → 130 | 1.3377 → 1.3377 | none; partial first 12:00 removed |
| ETH | 2189 → 2190 | 129 → 129 | 1.3178 → 1.3230 | none; completed 08:00 tail included, time-exit price changes |
| ICP | 2190 → 2189 | **133 → 132** | **1.1158 → 1.1465** | **one LONG entry removed:** signal 2025-11-30 12:00 UTC, entry 16:00 UTC |
| HYPE | 1251 → 1250 | 69 → 69 | 0.7889 → 0.7889 | none; invalid first 00:00 bucket removed |

ICP removed entry is near 210-bar feature warm-up after the discarded partial first bucket. It is **not evidence of better strategy**; it changes reported trade count and PF mechanically. ETH 15bp mean net changed +0.4055% → +0.4106% on identical 129 entry keys; old 4H tail was discarded. BTC and HYPE trade returns unchanged. Selected BTC OB (55), ETH OB (43), ICP EMA200 (59), HYPE (65) entry counts/keys unchanged; selected ETH matched fixed/raw-reverse same **43** entries in both aggregations. Under common UTC-window cuts, ETH selected raw-reverse PF 2.0988 at 15bp before/after (different window boundaries from prior 2.0564 report, so **do not interpret as improvement**). HYPE still rejected. The JSON includes 15/25/40bp win/mean/PF/pseudo-DD and entry diffs for all assets.

**CSV SHA256:** BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`; HYPE `7b1e66fbf6aee1f1407e877c7e1e4aaaeb8489009925438eadc53cf1b6c35bae`.

## Limitations / risk
- Historical cache last-hour close inference is **not proof of original data receipt/venue**; paper explicit as-of is safe, but actual live candle-close provenance remains UNKNOWN. Direct same-venue 4H OHLCV, 1H volume for BTC/ICP/HYPE, observed funding, spreads/mark price unavailable. This is a data-integrity correction, **not a new edge**.
- PF and pseudo-equity/DD use sequential per-symbol full-notional simulation, not an executable cross-asset risk-sized portfolio. Five UTC windows are non-overlapping, but historically contaminated by prior selection. The changed ETH time-exit result may also reflect changed last-window availability.
- Other cached reports from earlier commits must be tagged legacy; do not silently compare mismatched aggregation versions. New 4H historical tail is treated complete only when source last 1H row is assumed closed.

## Conclusion and concrete next manager decisions
1. **#7 DONE for synthetic/cached scope:** Review the one ICP dropped entry and ETH tail effect; confirm paper/research strict aggregation should become canonical. Keep issue open only if external venue parity is considered mandatory under #7.
2. **#6 P0 NEXT:** implement bounded UTC 00/08/16 funding-event counts (intrabar stop/TP uncertain), time-exit final-close duration, 0/1/3bp adverse synthetic stress and **net** paired 30-day-block CI on same ETH 43 entry IDs; embed producer SHA and tests. Do not claim the gross CI is net.
3. **#5 PARTIAL/BLOCKED:** risk-sized executable cross-asset portfolio, source/market manifest and same-venue 4H OHLC parity; no fabricated provenance. Pre-register prospective forward stream with immutable receipts, >=90 days and >=50 trades/candidate before assessment.
4. **No promotion, no orders.** User notification is warranted for corrected **ICP historical count (133→132)** and confirmed partial-candle bug, not for an unvalidated new strategy.

---

# DeltaRSI researcher handoff — cycle 3, 2026-10-26 (matched exit cohort)

**Decision: NO PROMOTION / PAPER ONLY.** Completed P1-C matched-entry component; no independent OOS. GitHub Actions [matched exit audit run 40372778396](https://github.com/VulpreS/Deltarsi1/actions/runs/40372778396) passed, after fixing an initially incorrect synthetic fixture. No candle downloads, no real orders.

## Hypothesis / priority
Read issues #4 and #5, previous handoff and `reports/manager_directives.md` first. Predeclared **ETH selected OHLC order-block proxy** (2.5 ATR stop, 6 ATR target, 12×4h maximum): exiting on **raw opposite DeltaRSI** may improve net expectancy versus fixed exit *on identical entries*. Secondary frozen baseline (2.5 ATR stop / 3 ATR target / 12×4h) for BTC, ETH, ICP, HYPE; structure and trail3 are diagnostic, not selection candidates.

## Changes / reproducibility
- Added `matched_exit_audit.py`, `test_matched_exit_audit.py`, `.github/workflows/matched-exit-audit.yml`. Code revision tested: `b6edc1eeafc3c1389f1f440724eec7e761dfd82a`; workflow produced `reports/matched_exit_audit.json` with 5 non-overlapping chronological slices and across-slice aggregate.
- Frozen fixed-exit engine determines entry IDs and scheduling **once**; each exit mode is then evaluated on exactly those same entries, even if it exits early. Exit checks use `execution_core.resolve_bar` (adverse stop gap, stop-first), signal close -> following open, and trailing updates only after close. Assertion verifies baseline fixed trade gross return parity with `p0_gap_audit.simulate`.
- Synthetic regression tests: opposite raw signal at next open, stop priority, adverse gap on *post-entry* bar, fee/funding math, insufficient time-block bootstrap guard. Tests passed on GitHub Actions. One initial test incorrectly placed an adverse gap on the entry candle (where stop was calculated from that new open), so it was fixed; not a simulator defect.
- Time-block paired bootstrap: fixed seed 20261026, 2,500 draws, resample **30-calendar-day blocks**, report percentile 95% interval for challenger minus fixed gross percentage-point return. Fee assumptions cancel in matched differences when fixed costs are equal.
- Committed `data/*_1h.csv` only; BTC SHA256 `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`; HYPE `7b1e66fbf6aee1f1407e877c7e1e4aaaeb8489009925438eadc53cf1b6c35bae`.

## Results: exact matched entries, 0.15% round-trip assumed costs
| Cohort | N | Fixed mean net % / PF / win% | Raw reverse mean net % / PF / win% | Mean paired gross delta (pp), 95% 30d-block CI |
|---|---:|---|---|---|
| BTC frozen | 130 | +0.3340 / 1.338 / 56.92 | +0.3084 / 1.315 / 57.69 | -0.0256 [-0.0689,+0.0057] |
| ETH frozen | 129 | +0.3908 / 1.305 / 52.71 | +0.4509 / 1.382 / 55.81 | +0.0601 [-0.0603,+0.1641] |
| **ETH selected OB** | **43** | **+0.8341 / 1.785 / 58.14** | **+1.0128 / 2.056 / 60.47** | **+0.1787 [-0.0202,+0.4321]** |
| ICP frozen | 133 | +0.2332 / 1.116 / 51.13 | +0.2392 / 1.127 / 51.88 | +0.0060 [-0.1747,+0.2111] |
| HYPE frozen | 69 | -0.4688 / 0.789 / 47.83 | -0.4101 / 0.812 / 49.28 | +0.0587 [-0.1292,+0.2657] |

**All reverse-exit paired CIs include zero.** ETH selected OB reverse is positive in 4/5 slice mean comparisons but one slice has N=4 and another N=7, and the selected OB entry filter was already selected on these data. No robust inference of improvement. ETH OB raw reverse PF @ 0.15/0.25/0.40% cost = 2.056/1.914/1.716; assumed adverse funding 1/3 bp per 8h (plus 15bp fees) PF = 1.994/1.873. These are *stress assumptions*, not observed venue funding.

Structural exit on selected ETH cohort mean +1.0432% and PF 2.312, but win% 48.84 and paired 95% CI for improvement [-0.3365,+0.6480] pp. This is not evidence to select structure. Trail3 adds almost nothing. BTC/ICP structure hurts average returns, HYPE still loses. Complete per-window PF, 15/25/40bp cost stresses, assumed funding and pseudo-equity DD are in the JSON.

## Limitations / blockers
- **Historical data are contaminated** by prior research; five windows are sequential/non-overlapping diagnostics, NOT untouched holdouts. Bootstrap cannot repair model-selection bias. 12 calendar blocks on BTC/ETH/ICP and 7 on HYPE; CIs are fragile.
- Paired cohort forces identical entry IDs; *early-exit re-entry and opportunity costs are intentionally excluded*. `pseudo_compound_pct` and `pseudo_max_dd_pct` are not executable portfolio equity metrics. No concurrent exposure, mark-price stops, venue funding, cross-asset covariance or real slippage.
- Source venue and market type remain unknown; no direct 4H same-venue OHLC parity for all assets. BTC/ICP/HYPE lack 1H volume. No newly arrived immutable forward data.
- **Do not interpret positive historical PF as validated deployable edge. No real orders.**

## Conclusion and concrete manager questions / next iteration
1. **P1-C PARTIAL:** Paired exit attribution implemented and verified, no statistically resolved advantage; next build separately executable non-overlap, cross-asset stop-risk-sized portfolio (0.25% equity risk/trade, max 2 concurrent, cap aggregate stop risk at 0.50% equity), record mark-to-market DD and worst month. Include cost 15/25/40bp and explicit unavailable actual funding.
2. **P1-D NOT DONE:** Freeze one candidate (suggest ETH raw reverse selected OB, but acknowledge retrospective selection) and baseline *before* collecting strictly post-cutoff forward shadow records; minimum forward sample/duration, version/venue hashes and pass/fail criteria required. Never call historical cached rows forward.
3. **P0-B PARTIAL/BLOCKED:** Request venue/spot-perp provenance and same-venue direct 4H OHLC, actual funding series; no new historical candles were fetched this cycle.
4. **P0-A DONE for covered engines:** Regression suite still passed; continue watching other research scripts for divergence.

---

# DeltaRSI researcher handoff — cycle 2, 2026-10-26

**Decision: NO PROMOTION / PAPER ONLY.** This cycle resolved a critical *potential* fill bias and a real reverse-exit semantics error; no independently validated new edge. No orders, no candle downloads. Read manager issues [#4](https://github.com/VulpreS/Deltarsi1/issues/4) and [#5](https://github.com/VulpreS/Deltarsi1/issues/5) plus manager directives before work.

## 1. Hypotheses and priority
- **P0-A (execution):** stop gaps were optimistically filled at the stop in three simulators, and filtered opposite signals mislabeled as raw DeltaRSI. Align execution and test whether cached-history PnL changes.
- **P0-B (data):** 1H OHLCV and separately cached 4H volume might be discontinuous or sourced from incompatible venues; test cache-only continuity and, where possible, sum-of-1H vs direct 4H volume parity.
- **Secondary (exit):** rerun already-selected structural exits with actual *raw* opposite DeltaRSI; do not tune parameters.

## 2. Code changes and verification
- Added `execution_core.py:resolve_bar` (shared LONG/SHORT stop-first fills; adverse gap at worse of opening price/stop; favorable target gap conservatively at target; invalid OHLC rejected). Routed `feature_walkforward.sim`, `research_multiasset.simulate`, `dynamic_exit_research.simulate` and `structural_exit_research.sim` through it. Other grid experiments reuse the feature engine.
- `structural_exit_research.sim` now accepts `raw_features`; opposite DeltaRSI exits use the **unfiltered** signal while entry remains filtered. Previous `reports/structural_exits.json` was regenerated with corrected semantics.
- Added `test_p0_execution.py` and `test_cache_integrity.py`: deterministic LONG/SHORT stop gaps across all four engines, stop+target same candle, gap-through-target, split entry, last-bar time exit, next-close trailing update, raw reverse bypassing entry filters, invalid OHLC, and lagged volume SMA excluding current bar.
- Added `p0_gap_audit.py` and `cache_integrity_audit.py`; workflow `p0-execution-audit.yml` passed (runs [40364223802](https://github.com/VulpreS/Deltarsi1/actions/runs/40364223802), [40364350718](https://github.com/VulpreS/Deltarsi1/actions/runs/40364350718)); structural rerun [40364310889](https://github.com/VulpreS/Deltarsi1/actions/runs/40364310889) passed. No external dependencies or exchange fetch in these audits.

## 3. Data and reproducibility
Source: committed `data/*_1h.csv` and `data/*_4h_volume.csv` only. Each report includes source SHA256 and UTC coverage; full paths `reports/p0_gap_audit.json`, `reports/p0_cache_integrity.json`, `reports/structural_exits.json`.
- BTC 8,761, ETH 8,760, ICP 8,761, HYPE 5,003 hourly candles: **zero duplicate hours, zero missing hours, zero invalid OHLC**. Direct 4H volume timestamp grids also have zero gaps.
- ETH 1H volume aggregated into 4H agrees with cached direct 4H volume for **2,190/2,190** complete overlapping buckets (random seed 20261026; all 30 sampled match; zero measured relative difference).
- BTC, ICP, HYPE 1H CSVs contain **no volume field**; 1H→4H volume parity **BLOCKED**. No direct 4H OHLC cache exists for any asset. No source/venue manifest identifying the actual fallback venue per CSV; **venue parity remains unverified**, even for ETH despite quantitative volume agreement.
- SHA256 1H: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`; HYPE `7b1e66fbf6aee1f1407e877c7e1e4aaaeb8489009925438eadc53cf1b6c35bae`.

## 4. Results vs frozen baseline
Five chronological non-overlapping slices per asset; entry next 4H open, max hold 12×4H, stop-first, no concurrent same-symbol positions. Slices **already inspected by previous research; NOT independent OOS**. Full-notional max DD, not stop-risk-sized portfolio DD.

| Asset | Baseline N | Legacy vs corrected adverse gaps | PF @ 0.15% total cost | PF @ 0.25% | PF @ 0.40% | Max DD @ 0.15% |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 130 | 0; identical | 1.338 | 1.227 | 1.076 | 23.53% |
| ETH | 129 | 0; identical | 1.305 | 1.219 | 1.101 | 28.16% |
| ICP | 133 | 0; identical | 1.116 | 1.065 | 0.992 | 35.51% |
| HYPE | 69 | 0; identical | 0.789 | 0.750 | 0.695 | 38.01% |

**Interpretation:** the stop-gap fill defect was real in code and demonstrably changes synthetic gap cases, but **zero adverse stop gaps were observed** in these particular cached baseline and selected-entry simulations. Thus the historical performance figures were unchanged by this correction; never claim that it increased or reduced historical returns.

Previously selected *exploratory* filters at 0.15% total cost: BTC OHLC OB proxy N=55 PF=1.822 max DD=16.17%; ETH OB proxy N=43 PF=1.785 DD=17.22%; ICP EMA200 N=59 PF=1.626 DD=25.83%; HYPE alternative N=65 PF=0.744 DD=41.46%. These were chosen after examining all periods and **cannot validate an edge**. At 0.40% total cost baseline ICP PF drops below 1. Assumed *adverse* funding stress of 0.01% and 0.03% per 8h is reported separately; actual venue funding, mark-price triggers, impact and correlated portfolio DD are unavailable.

Corrected raw-reverse ETH exit (same historical sequential windows) mean trade return: **+1.307%, +1.076%, +0.783%** versus fixed **+1.180%, +0.755%, +0.659%**. BTC/ICP do not improve consistently; HYPE remains unprofitable. Reverse-exit test is still **not matched-cohort causal attribution** (early exits can permit extra entries) and **not independent**.

## 5. Limitations and release decision
- No untouched forward sample, no independently verified direct 4H OHLC venue parity, no actual funding/mark-price execution data. The last 4H bucket is still unconditionally dropped in the historical `aggregate`; paper alert uses a separate completed-bucket guard.
- Old reports generated before this patch must not be interpreted as execution-parity evidence; `reports/structural_exits.json` was regenerated, other grid reports should be tagged with producing commit and re-run only if needed.
- Tests prove defined synthetic cases, not all venue microstructure scenarios. Historical full-notional DD is unsuitable for live portfolio risk.
- **Do not trade live. No strategy promotion.**

## 6. Concrete questions / next manager iteration
1. **P0-B:** Can a provenance manifest be supplied for each 1H OHLC and direct 4H volume CSV (exchange, market type, endpoint, fetched UTC, symbol mapping)? Direct 4H OHLC from *the same venue* is required for ≥30-bucket parity; do not label cross-venue matches as verified.
2. **P1-C:** Pre-register exactly one challenger (candidate: ETH raw reverse vs frozen fixed), then implement matched-entry paired returns + time-block bootstrap 95% CI, plus a separate non-overlap executable portfolio. Include 0.25% equity risk/stop, correlated caps, fee/slippage 15/25/40bp and actual funding if provenance is available.
3. **P1-D:** Freeze strategy/source hashes and UTC cutoff; append *newly arriving* paper candles with receipt timestamps and no backfill-as-forward. Set minimum sample/duration and pass criteria before observing forward results. No order placement.
4. Decide whether to replace `aggregate()` with an explicit fully-closed 4H bucket predicate across all historical research modules, after verifying parity against cached raw hourly candles.

**Status:** P0-A DONE for four covered engines and fixtures; P0-B PARTIAL (ETH volume parity, cache continuity), blocked on provenance/direct 4H OHLC for full parity; P1-C/P1-D NOT DONE.

---

# Research handoff — cycle 1 (2026-10-26)

## Work performed
Reviewed `feature_walkforward.py` and `analyze_mtf_5y.py`. Added `test_candidate_b_semantics.py` and GitHub Actions `candidate-b-audit.yml`. Audit workflow run 40354266118 passed. Synthetic fixtures confirm: signal-bar extremes are not used as fills; entry uses next 4H open; stop takes precedence when stop and target touch in same bar; no split-boundary entry; aggregation discards last 4H bucket.

## Methodological concerns / next directives requested
1. **Important:** `aggregate()` unconditionally discards the last 4H bucket, even if all 4 source 1H candles are complete. This is conservative but loses one valid candle; confirm intended behavior.
2. Verify real Binance/HYPE 4H volume timestamps match aggregated 1H UTC bars. Synthetic execution tests do not prove live data alignment.
3. Add fixture showing volume SMA excludes current bar and guards missing volume.
4. The current candidate uses all chronological splits for selection; genuinely new data needed before any unbiased performance claim.
5. Funding and actual execution costs are not yet included; add independently sourced funding time series before production readiness.

## Manager decision needed
Prioritize timestamp-volume audit, portfolio concurrent-position simulator, or forward-only data collector. Recommend timestamp-volume audit first, then forward collector. No real trading.
