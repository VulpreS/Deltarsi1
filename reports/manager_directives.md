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

---

# Manager review — cycle 2, 2026-10-26 17:52 UTC

## Sources reviewed and evidence boundary
- Latest researcher handoff: `reports/research_handoff.md` cycle 2 (commit `47441d0f8b39`).
- CI: P0 execution parity `40364350718` SUCCESS; structural exit rerun `40364310889` SUCCESS.
- Reports: `reports/p0_gap_audit.json`, `reports/p0_cache_integrity.json`, regenerated `reports/structural_exits.json`.
- Newest research code: `matched_exit_audit.py` commit `8f71534e1f965ee91a67828b219d4b84cbe5a417`, **not yet run/committed as a report** at this review.
- These are previously inspected historical data; **NO independent OOS**. This manager review did not reproduce the tests in a separate environment; it inspected code, committed reports and GitHub Actions conclusions.

## Decision register — confirmed / rejected / pending
| Item | Decision | Basis |
|---|---|---|
| P0-A shared adverse-gap execution and raw reverse semantics | **DONE for four covered engines / fixture scope; still no venue fill verification** | `execution_core.resolve_bar` wired into feature, multiasset, dynamic and structural simulations; synthetic tests passed; 0 adverse stop gaps observed in frozen cached baseline/selected cohorts, so historical returns unchanged. Do not claim PnL improved. |
| P0-B cached OHLCV continuity | **PARTIAL** | BTC 8,761 / ETH 8,760 / ICP 8,761 / HYPE 5,003 hourly rows, no duplicate/missing hour or invalid OHLC. ETH 2,190/2,190 1H-volume sums match cached 4H volume. But no per-file exchange/market provenance, no direct 4H OHLC, and no 1H volume for BTC/ICP/HYPE. ETH match is quantitative, not independent venue proof. |
| 5-slice frozen baseline | **DESCRIPTIVE, NOT VALIDATED** | At 15bp total assumed round-trip costs: BTC N130 PF1.338 DD23.53%; ETH N129 PF1.305 DD28.16%; ICP N133 PF1.116 DD35.51%; HYPE N69 PF0.789 DD38.01%. DD is full-notional per-symbol pseudo-equity, NOT risk-sized portfolio DD. At 40bp ICP PF0.992. Funding stress is synthetic, not actual. |
| BTC/ETH OHLC OB proxy and ICP EMA200 | **EXPLORATORY ONLY** | Retrospective winner selection; no order-book depth and no independent forward sample. |
| Raw opposite DeltaRSI ETH exit | **CANDIDATE TO TEST, NOT PROMOTED** | Corrected sequential 3-slice ETH mean returns +1.307/+1.076/+0.783% vs fixed +1.180/+0.755/+0.659%; different scheduling and repeated historical inspection invalidate causal/forward claims. |
| HYPE existing strategy | **REJECT for deployment** | Frozen baseline PF <1 and unknown venue provenance. |
| Forward-only shadow | **NOT STARTED / BLOCKED** | No verified venue/market source, immutable receipt-time data log or frozen version manifest. |

## Newly identified blocker in latest matched-cohort code
`matched_exit_audit.py` (commit `8f71534e1f96`) implements matched-entry comparisons and 30-day block bootstrap, but no CI/report was available at review. `exit_one()` calculates holding hours from entry bar **open** to exit bar **open** even for time exits filled at the last bar **close**; this may undercount elapsed funding intervals. Stops/targets fill intrabar at unknown timestamps, so exact 8h funding charges cannot be inferred from OHLC alone. `bootstrap_delta()` uses **gross** differences, not funding-adjusted net deltas. Its entry cohort is selected by frozen fixed-exit scheduling, so paired results are descriptive and potentially conditioned on baseline exit outcomes; separate executable scheduling is mandatory. Do not claim these are proven performance improvements.

## Concrete next tasks and acceptance, priority order
### P0-C — matched audit execution and funding-timing correction — [issue #6](https://github.com/VulpreS/Deltarsi1/issues/6)
**Hypothesis:** after time-accurate adverse funding stress and a fixed matched cohort, the ETH raw-reverse exit retains positive net paired advantage over fixed exit.
**Acceptance:** deterministic 1/2/3/12-bar duration and 00/08/16 UTC funding boundary tests; bounded intrabar timing; aligned funding conventions across `p0_gap_audit` and `matched_exit_audit`; CI + committed JSON with hashes/seed/commit; 30-day block bootstrap **net** paired 95% CI, N, effective blocks, 15/25/40bp costs and 0/1/3bp funding stress; baseline cohort vs separate non-overlap executable portfolio with 0.25% equity stop-risk, correlated exposure caps, worst month, max DD, return/DD. Historical confidence interval is NOT independent OOS. **No parameter search on independent sample.**

### P0-B continuation — provenance and 4H completion — [issue #5](https://github.com/VulpreS/Deltarsi1/issues/5)
**Hypothesis:** mixed venue or incomplete 4H buckets can invalidate volume and pattern filters.
**Acceptance:** per-CSV venue/market/symbol/endpoint/fetch-UTC manifest and checksums, direct 4H OHLCV from same venue for ≥30 fully closed random buckets per asset; 1H→4H OHLCV parity within predeclared tolerance; explicit intermediate complete-bucket predicate, first/last bucket tests, SMA20 lag test; missing volume reported as UNKNOWN rather than filled with other-venue data. **Do not download redundant candles; append only missing validation data.**

### P1-D — preregistered forward-only shadow — [issue #5](https://github.com/VulpreS/Deltarsi1/issues/5)
**Hypothesis:** a frozen strategy maintains positive net expectancy on strictly new, timestamped candles.
**Acceptance:** pre-register frozen baseline and at most one ETH challenger, code/data/parameter hashes, venue, UTC cutoff, minimum duration/sample size and pass/fail risk metrics before observing forward outcomes; append-only receipts with wall-clock arrival times, sealed evaluation log and no backfill counted as forward; simulated fills only; no exchange orders or trading permissions. **No tuning on sealed forward data.**

## Next manager checkpoint
1. Verify issue #6 implementation/CI/report and specifically correct duration/funding bootstrap semantics.
2. Check #5 venue manifest and fully closed 4H parity; mark blocked if missing.
3. Review matched-net paired 95% CI and *separate* executable portfolio; compare with frozen 2.5ATR/3ATR/48h baseline.
4. Verify forward-only collector has immutable timestamps and preregistration before treating any sample as prospective.
5. Continue **NO PROMOTION / RESEARCH ONLY** until independent forward evidence and separate human authorization for production.

### Cycle 2 late-arriving CI addendum (2026-10-26 17:53 UTC; supersedes "not yet run" above)
While the manager review was being committed, the researcher **ran** the new matched audit: workflow [40372778396](https://github.com/VulpreS/Deltarsi1/actions/runs/40372778396) SUCCESS after an earlier failed run; committed `reports/matched_exit_audit.json` in `f4386df7ab`. This changes P1-C from NOT RUN to **PARTIAL / CI PASS**. The code still has the funding-duration and gross-only-bootstrap limitations identified above; CI tests do not include time-exit holding-hour/funding-boundary fixtures.

**ETH preselected OB, same baseline-scheduled 43 entry IDs, 15bp assumed total round-trip cost:** fixed mean net +0.8341%/trade, PF 1.7849, win 58.14%; raw reverse mean net +1.0128%, PF 2.0564, win 60.47%. **Paired gross mean delta +0.1787 percentage points, 30-day-block bootstrap 95% CI [−0.0202, +0.4321] pp (12 blocks)**: interval **includes zero**. Therefore there is NO demonstrated statistically robust improvement, even before prospective testing; do not promote. At 40bp, fixed PF1.4969 vs reverse PF1.7157, still reused history and gross-only CI. Structure exit yields higher matched mean but worse winrate and CI also crosses zero; do not cherry-pick it.

**P0-C issue #6 stays OPEN:** require accurate time/funding accounting, net paired CI, explicit strategy hash, separate risk-sized executable portfolio and independent prospective evaluation. **Do not claim that the passed workflow validates trading edge.**


---

## Manager cycle 3 — 2026-10-26 18:51 UTC (latest decision; overrides older status where inconsistent)

### Inputs and reproducibility check
Read `reports/research_handoff.md` cycle 3, `reports/matched_exit_audit.json`, `reports/p0_cache_integrity.json`, latest GitHub issues #4/#5/#6, and inspected `matched_exit_audit.py`, `test_matched_exit_audit.py`, `execution_core.py`, `p0_gap_audit.py`, `feature_walkforward.py`, `analyze_mtf_5y.py`, `paper_signal_4h.py`. Latest handoff commit `b6585cb2` (17:53 UTC). Matched audit workflow 40372778396 SUCCESS; an earlier fixture failure 40372717682 was fixed. Report stores source CSV SHA256, freeze UTC, bootstrap seed in source and 2,500 draws, but **does not embed exact producer code commit SHA or CI run ID**. This manager reviewed code and published reports, not an independently rerun environment.

### Findings — confirmed / rejected / pending
- **Confirmed within synthetic scope:** gap-safe stop fills and stop-first ordering via shared `execution_core.resolve_bar`; no observed adverse stop gaps in historical baseline/selected cache; next-open reverse signal in matched audit; five-slice same-entry comparisons and reported 15/25/40bp hypothetical round-trip fee+slippage.
- **Not confirmed:** improvement of ETH selected-OB raw-reverse over fixed. Same 43 retrospectively selected entries: fixed +0.8341% mean net/PF1.7849/win58.14%; reverse +1.0128%/PF2.0564/win60.47% at 15bp. **Paired bootstrap uses gross delta** +0.1787 percentage points, 95% 30-calendar-day block CI **[-0.0202,+0.4321]pp**, 12 effective blocks; includes zero. This is reused historical data, not independent OOS. Other asset frozen baseline paired reverse CIs also include zero.
- **Rejected for promotion:** HYPE (frozen PF0.7893 at 15bp); structural exit and trailing as strategy upgrades; pseudo-compound equity as an executable risk-sized portfolio; claim of proven historical edge.
- **P0 NEW #7:** `analyze_mtf_5y.aggregate` accepts **incomplete first 4H bucket** when CSV starts at non-4H UTC hour. BTC/ICP begin at 13:00 UTC -> first 12:00 4H bucket contains only 3 hourly rows; HYPE begins at 03:00 UTC -> first 00:00 4H bucket contains 1. Last bucket always dropped even when complete. First partial bucket is a data integrity bug; it is not in itself proof of look-ahead or altered PnL. Must test impact. Paper and research aggregate functions differ.
- **P0 OPEN #6:** `matched_exit_audit.exit_one` reports hours from entry-open to exit-bar-open even when time exit occurs at last-bar-close, potentially undercharging synthetic funding. Intrabar stops/targets have unknown timestamps; funding must be bracketed. `bootstrap_delta` is **gross-only**, despite the hypothesis about *net* improvement. `p0_gap_audit.metrics` uses `ceil(bars/2)`, a different approximation. Need bounded UTC funding-event accounting, net paired CI, and code SHA embedded in JSON.
- **P0/P1 OPEN #5:** Venue/market source still UNKNOWN, direct same-venue 4H OHLC parity unavailable, BTC/ICP/HYPE 1H volume absent. ETH cached 1H→4H volume matches 2,190/2,190 but that is not signed venue provenance. No actual funding, mark-price, spreads/impact, or new immutable forward records.
- **P1 OPEN #6/#5:** Fixed-cohort pseudo-DD is not executable portfolio DD; early-exit reentry and correlated exposure are excluded. Need separate chronological portfolio with stop-risk 0.25% equity per trade, max two simultaneous positions, aggregate initial stop risk <=0.50% equity, mark-to-market drawdown and worst month. Stress costs 15/25/40bp and funding bounds.

### Mandatory tasks for next researcher cycle (priority, hypothesis, acceptance)
1. **P0 — #7 strict 4H aggregation.** Hypothesis: first/last incomplete 4H buckets change indicator states and perhaps entries. Acceptance: shared completed-bar/as-of aggregation; fixtures for partial first/interior/last buckets, UTC boundaries, duplicates, non-monotonic timestamps and paper parity; before/after frozen historical comparisons with UTC-mapped entry IDs, source+code hashes, 15/25/40bp costs, CI run; report any zero differences. **Do not retune.**
2. **P0 — #6 funding/net inference.** Hypothesis: corrected funding accounting may reduce or reverse ETH exit advantage. Acceptance: 1/2/3/12-bar close and 00/08/16 UTC boundary tests; intrabar lower/upper funding bounds; 0/1/3bp per-8h adverse stresses explicitly synthetic; same 43 entry IDs; **net** paired 30d-block CI, effective blocks, PF/win/mean at 15/25/40bp; full producer commit SHA and test workflow URL. Keep CI including zero visible.
3. **P1 — #5 executable portfolio and source provenance.** Hypothesis: correlated risk and actual market economics reduce historical PF. Acceptance: frozen baseline vs one retrospectively selected ETH challenger, separate chronological no-overlap trade scheduling, cross-asset max two positions/0.50% stop-risk cap, 0.25% stop risk/trade, equity mark-to-market DD/worst month/return-DD; provenance manifest or explicit BLOCKED for missing venue, direct same-venue 4H and actual funding.
4. **P1 — #5 forward-only shadow preregistration.** Hypothesis: historical edge survives *strictly new* observed bars. Acceptance **before any forward outcomes are inspected**: immutable strategy/code/data/venue hashes, UTC cutoff, fixed baseline and at most one challenger, precommitted minimum >=90 calendar days and >=50 independent executed trades *per candidate* before statistical evaluation (if infeasible, report insufficient evidence rather than relax thresholds), cost assumptions and risk gates; append-only receipt timestamps, no historical backfill counted forward; no tuning on sealed evaluation data. No live orders.

### Next manager review gates
Verify #7 synthetic fixtures + historical diff, #6 net paired bootstrap/funding timing, #5 venue provenance and executable portfolio, then prospective shadow setup. Until these pass: **RESEARCH ONLY, no paper performance claim, no production without separate user authorization.**


---

## Manager cycle 4 — 2026-10-26 19:53 UTC (LATEST; overrides prior status)

### Inputs actually inspected
- Researcher handoff cycle 4 + missing-interior-HTF addendum (`reports/research_handoff.md`), issue #7 comments and closure, issue #6/#5/#4 progress, code `completed_candles.py`, `analyze_mtf_5y.py`, `matched_exit_audit.py`, `funding_timing.py`, and synthetic `test_matched_exit_audit.py`.
- `reports/aggregation_impact.json` (producer `a58fc86b46214862b5b88e66c822c2a482eb5239`, CI 40383121465 SUCCESS), `reports/matched_exit_audit.json` (producer `c21ec909ab004edcf5fda265ee72a2a1635adb0e`, CI 40390587719 SUCCESS), `reports/p0_cache_integrity.json`, frozen prior baseline. Latest matched report was generated 2026-10-26 19:52:25 UTC and committed in `0f7e8c347`.
- Workflow failures 40390463895 (SyntaxError unmatched brace) and 40390526709 (test fixture lacked funding bounds) were diagnosed from job logs and superseded by successful 40390587719. These are corrected implementation/test defects, NOT evidence of a profitable edge.
- All datasets and five chronological windows were previously inspected. **NO independent OOS.** This is a GitHub code/report/CI review, not an independent exchange-data reproduction.

### Decision register: confirmed, rejected, pending
1. **#7 DONE / CLOSED for synthetic and cached scope.** Strict UTC completed 4H aggregation is shared across research/paper and rejects partial buckets. Missing-interior HTF lookup now uses actual close times, preventing a *potential* future-HTF look-ahead on gappy datasets. Cached 1H has zero interior gaps, so no demonstrated historical look-ahead profit effect. Frozen baseline at 15bp: BTC 130→130 PF1.3377 unchanged; ETH 129→129 PF1.3178→1.3230 due completed tail; ICP 133→132 PF1.1158→1.1465 due one entry removed near warmup; HYPE 69→69 PF0.7889 unchanged. **Mechanical data correction, not improvement.** External same-venue parity remains #5.
2. **#6 PARTIAL / synthetic accounting implemented.** UTC 00/08/16 funding exposure min/max, time-exit final-close duration, deterministic 1/2/3/12-bar fixtures, paired NET bootstrap, and fee+synthetic funding stresses are now in code and CI. On **same 43 retrospective ETH OB entry IDs**, fixed 15bp mean net +0.8666% / PF1.8212 / win58.14%; raw opposite DeltaRSI mean net +1.0453% / PF2.0988 / win60.47%. Paired net difference +0.1787 percentage points, 95% 30-day-block CI **[-0.0202,+0.4321] pp** (12 blocks) **includes zero**. At 3bp adverse funding/event, upper event bound, paired +0.1955pp CI **[-0.0078,+0.4572]** also includes zero. Same fee per completed matched trade cancels in paired delta, though individual PF/win/net change. Changed absolute metrics vs older matched report reflect strict 4H/UTC slicing, not a new edge. Actual funding remains unknown; `p0_gap_audit` accounting still requires reconciliation. **NO PROMOTION.**
3. **#4 DONE for four canonical covered engines/fixtures, OPEN for uncovered code paths and venue fills.** Stop-first adverse gap and next-open raw reverse were regression tested. No independent venue fill validation.
4. **#5 BLOCKED for provenance and prospective validation.** Source venue/spot-vs-perp UNKNOWN, no direct same-venue 4H OHLCV parity, no BTC/ICP/HYPE 1H volume, actual funding/spreads/mark price absent, no immutable new forward receipts. ETH 2190/2190 cached volume match does not establish venue.
5. **Rejected for deployment:** HYPE historical baseline (PF<1), previously tuned structure/trailing as upgrades, full-notional pseudo-DD as executable portfolio DD, claim of statistically resolved ETH reverse superiority. BTC/ETH OB and ICP EMA200 remain retrospective hypotheses.

### Mandatory next tasks (ordered; hypothesis, acceptance and restrictions)
- **P0 / issue #6 — reconcile economics and versioned matched results.** Hypothesis: inconsistent legacy synthetic funding conventions or time-exit accounting could change conclusions. **Acceptance:** compare `p0_gap_audit.metrics` with UTC funding events for identical frozen trade IDs, LONG/SHORT, intrabar min/max, exact boundary; publish erratum for older legacy reports; verify report source SHA256, producer SHA, CI URL, seed and identical entry IDs; report 15/25/40bp fee+slippage and 0/1/3bp **hypothetical** funding net paired CI with 30d blocks; flag actual funding UNKNOWN; CI must not silently suppress zero-crossing. No parameter tuning on final quarter or independent/forward sample.
- **P0/P1 / issue #5 — source provenance and preregistered shadow.** Hypothesis: cross-venue data, missing volume or actual funding will reduce apparent edge. **Acceptance:** per-symbol exchange/market/endpoint/fetch/receipt UTC manifest, 1H→direct same-venue 4H OHLCV parity on >=30 preselected fully closed buckets per symbol with fixed tolerances; record unknown as blocked. BEFORE viewing any forward outcomes freeze baseline and at most one ETH challenger, exact code/config/data/venue hashes and UTC cutoff; >=90 calendar days and >=50 independent executed shadow trades/candidate, net PF/expectancy/DD gates, append-only observed receipt timestamps; no backfill counted forward. No independent evaluation stream retuning.
- **P1 / NEW issue #8 — risk-sized executable portfolio.** Hypothesis: historical fixed-cohort mean/PF overstate portfolio risk-adjusted edge. **Acceptance:** chronological independently scheduled fills, no same-symbol overlap, 0.25% equity stop risk/trade, max two positions and 0.50% aggregate stop risk, quantity/notional/margin limits, simultaneous signal policy, skipped opportunity counts, mark-to-market DD, worst month, return/DD, exposure and turnover; 15/25/40bp fees and 0/1/3bp synthetic funding, adverse gaps, deterministic fixtures and reproducible CI with SHA. Compare frozen 2.5ATR/3ATR/48h BTC/ETH/ICP benchmark with at most one previously selected ETH OB 2.5/6/48h raw-reverse challenger. **No optimization on independent holdout.**
- **P1 / issue #3 — trade ledger/pattern research deferred** until #5/#6/#8 integrity gates; never publish private user trade ledger into a public repository. No new threshold search on sealed forward data.

### Next manager cycle gates
1. Read latest researcher handoff, issue #6/#5/#8 updates and CI; verify reconciliation of old/new funding conventions and producer SHA.
2. Check venue source manifest and forward preregistration; if absent, retain BLOCKED.
3. Review portfolio code and compare risk-sized baseline vs challenger, ensure actual trade opportunity and cross-asset risk constraints.
4. Demand clear DONE/PARTIAL/BLOCKED handoff and separate statistical vs production authorization. **No live orders. Paper only after readiness, production only with explicit user approval.**


### Late-arriving researcher cycle 5 verification — 2026-10-26 19:55 UTC
After this manager review, researcher published a newer handoff cycle 5 (commit `886a2f8c9`) and reran the matched audit under the expanded CI suite: **workflow 40390672109 SUCCESS**, report producer SHA **`8bc3b8e67e68935f52f8eb9ebdb225f96a2acf00`**; this **supersedes the c21/40390587719 provenance** cited above. Current `reports/matched_exit_audit.json` has this newer producer/run and unchanged primary ETH N43, 15bp fixed +0.8666% PF1.8212, reverse +1.0453% PF2.0988, paired net +0.1787pp 95% CI [-0.0202,+0.4321]pp; 3bp funding stress max-bound CI [-0.0078,+0.4572]pp. Both intervals include zero. New workflow runs execution and completed-candle regression suites in addition to funding tests. #6 remains PARTIAL because old funding convention reconciliation, observed venue costs and independently scheduled risk portfolio are incomplete; #8 and #5 remain mandatory. Do not select on sealed OOS. No orders.
