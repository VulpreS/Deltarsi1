# DeltaRSI researcher handoff — cycle 15, 2026-10-27 ~09:00 MSK — TRUE PEAK/WAVE STOPS (#16, #15)

**Decision: REJECT unconditional replacement of 2.5ATR stop by true peak-bar stop; true whole-wave stop INCONCLUSIVE/UNPROMOTED. Causal code, cached-data matched tests and 1,122-event ledger committed. No orders.**

## Hypothesis and manager priorities read
Read current issues #10, #15 (P0 aligned calendar/regime collapse), #16 (P1 genuine peak vs same-sign wave), #11 and saved cycle-14 handoff plus manager directives. Predeclared **one small stop-family ablation**: on the *same causal DeltaRSI entry opportunities*, the extremum of the actual strongest already-known opposite-sign 4H DeltaRSI bar, or the entire contiguous already-known opposite-sign wave, could improve net R / WR over 2.5ATR. Fixed TP **1.2R**, timeout **48h**, 0.05 ATR structural buffer, round-trip **FEE=0.0015**. Funding excluded per owner instructions for pattern discovery. No parameter search and no model selection on diagnostic third.

## Changes, data, reproducibility
- New `true_wave_stop_audit.py`, `test_true_wave_stop_audit.py`, `.github/workflows/true-wave-stop-audit.yml`; 1,122-event full ledger at `reports/true_wave_stop_audit.json` (all eligible and rejected stops, exact wave start/end/peak UTC, delta peak, OHLC extremes, stop, reason, R and source hashes). Script: `python -m unittest -v test_true_wave_stop_audit test_pattern_edge_search test_causal_4h_parity test_completed_candles && python -u true_wave_stop_audit.py`.
- Only cached `data/{BTC,ETH,ICP,HYPE}USDT_1h.csv`. Existing 4H indicator and frozen causal 1H entry stream; next-hour-open execution; 1H OHLC stop-first and adverse gaps; fees on actual entry/exit notional; same 0.25% equity stop-risk *normalization* (R). No exchange calls.
- Causal wave: use current 4H only when fully closed; for forming h1–h3 use previous completed 4H. Trace consecutive *opposite-sign* completed DeltaRSI back to last sign flip; peak is max absolute DeltaRSI within that wave; whole-wave extreme covers every bar in wave, **not a fixed six-bar proxy**. Explicit reject if stop is on wrong side or <0.1%/>12% of entry.
- UTC calendar aligned across BTC/ETH/ICP: train **2025-10-26 13:00 → 2026-04-27 00:00**, validation **2026-04-27 00:00 → 2026-07-27 06:00**, inspected diagnostic **2026-07-27 06:00 → 2026-10-26 12:00** (end exclusive). HYPE shorter history, reported separately as a negative control. Windows **all previously inspected**, NOT independent OOS. Pairwise stop comparisons require ATR and the *specific* challenger both geometrically valid; no artificial triple-stop eligibility gate.
- Synthetic fixtures: >6/<6 wave length, interior peak, LONG/SHORT sign flips, early forming vs completed 4H, L3 2026-09-18 11:00 MSK = 08:00 UTC no current-bar knowledge, invalid geometry, stop+TP same hour, adverse gap, mutation of future prices/indicator and seeded 30-day block CI. Latest fully passing source run: [40458168781](https://github.com/VulpreS/Deltarsi1/actions/runs/40458168781). A prior run [40458116590](https://github.com/VulpreS/Deltarsi1/actions/runs/40458116590) had tests and research **PASS**, but report persistence failed because two runners concurrently rebased the same JSON; workflow now uses fresh-ref/reset/copy/retry instead of conflicted rebase (commit `a52575cb`); **same-SHA [CI 40458203283](https://github.com/VulpreS/Deltarsi1/actions/runs/40458203283) SUCCESS** with tests, cached backtest and report persistence all passing.
- Code commits: `68a86d4` original producer, `89be0b1` correct pairwise cohort, `c080246` block bootstrap, `6cd6cc5` deterministic CI fixture, `b048733` chronological pseudo-DD order, `a52575c` safe report persistence. No tuning of the strategy parameters.

## Results: same BTC/ETH/ICP calendar, frozen 4H turn, fixed 15bp friction
| Window | Stop | All eligible N | WR | Mean net R | PF |
|---|---|---:|---:|---:|---:|
| Train | ATR2.5 | 341 | 55.72% | +0.09664 | 1.3177 |
| Train | TRUE peak bar | 270 | 49.26% | -0.04749 | 0.9081 |
| Train | TRUE whole wave | 338 | 50.00% | +0.00034 | 1.0007 |
| Validation | ATR2.5 | 191 | 56.02% | +0.04238 | 1.1324 |
| Validation | TRUE peak bar | 146 | 52.74% | -0.01251 | 0.9754 |
| Validation | TRUE whole wave | 197 | 52.28% | +0.01898 | 1.0415 |
| Previously inspected diagnostic | ATR2.5 | 216 | 44.91% | -0.00088 | 0.9975 |
| Previously inspected diagnostic | TRUE peak bar | 152 | 40.79% | -0.24789 | 0.6069 |
| Previously inspected diagnostic | TRUE whole wave | 214 | 42.99% | -0.14455 | 0.7218 |

**Matched opportunity attribution (core only, challenger minus ATR, paired 30-day UTC block bootstrap exploratory 95% CI):**
- TRUE peak: train **N267, -0.20093R** CI [-0.33403, -0.07143], validation **N142, -0.12080R** CI [-0.33194, +0.04457], inspected diagnostic **N152, -0.21363R** CI [-0.29588, -0.12692].
- TRUE whole wave: train **N334, -0.09849R** CI [-0.24306, +0.00610], validation **N190, -0.03157R** CI [-0.14025, +0.08885], inspected diagnostic **N214, -0.14450R** CI [-0.19173, -0.05696].
- **Geometry mechanism:** train frozen-turn median stop distance ATR **4.61%**, true peak **1.71%**, true wave **2.50%**; median round-trip fee per initial R **0.0327R / 0.0883R / 0.0596R** respectively. Tighter structural stops pay materially higher cost per R and are often hit/rejected.
- **Six-bar proxy not equivalent:** across 762 core frozen-turn candidate entries, 547 (**71.8%**) have true same-sign waves **longer than six 4H bars**; median wave length **11**. The prior `prior_wave6x4h` stop cannot be described as a true wave stop.
- Forming true whole-wave vs ATR matched: train **N47 -0.4322R**, validation **N22 +0.0042R**, inspected diagnostic **N32 -0.1879R**. No stable benefit from the early-entry subfamily.
- Results are not a same-calendar *executable portfolio*: overlapping frozen signal opportunities can share capital; the displayed pseudo DD is not hourly MTM portfolio DD. Block CIs use only 4–6 calendar blocks and are not selection-adjusted.

## Interpretation, limits, decisions
**REJECT** universal peak-bar stop as an ATR replacement in this fixed entry/exit family. **INCONCLUSIVE / do not promote** true whole-wave stop: small pockets of better R exist by asset/side, but combined matched train/validation are not positive and the already-inspected diagnostic fails. **RETAIN** ATR2.5 as the frozen descriptive control, **not** an independently validated trading edge. Do not search for winners in the diagnostic period. 1H OHLC cannot establish exact intrabar fills; no verified venue provenance or prospective immutable sample. This experiment deliberately holds exit TP/time fixed, so it does not answer joint optimal exit or discretionary selectivity. No CSV of expanded user trade labels available. No orders.

## Questions and concrete next iteration for research lead
1. Approve the **true wave/peak causal geometry DONE** for issue #16 but keep issue open for the CSV importer and **three causal matched exit policies** (fixed, raw opposite closed DeltaRSI next-open, price rejection / momentum fade next-open) with identical initial entry IDs? Recommend yes.
2. Run a preregistered *small* regime/price-rejection filter test using only train to calibrate and validation to rank; do not reuse inspected diagnostic for selection. Explicitly examine why peak/wave stops are so tight (fee-to-R, wrong-side rejection, trend transitions) and price-action selectivity; never treat every histogram fade as entry.
3. Build an executable shared-capital BTC/ETH/ICP comparison (0.25% stop-risk/trade, max 2 positions, 0.50% total, hourly MTM DD, missed admissions). Distinguish matched-entry R from independently scheduled portfolio results.
4. Implement validated `symbol,side,timestamp_MSK,entry,exit,stop,notes,confidence` importer and five annotated case ledger, preserving chart-time vs fill uncertainty. No filter fitting to five examples.
5. Preregister a new prospective paper-only stream before claiming stable positive net expectancy. No live orders without separate explicit authorization.

---

# DeltaRSI researcher handoff — cycle 14, 2026-10-27 ~08:00 MSK — priority shift to ENTRY/EXIT EDGE (#10/#11)

**Decision: FIRST FULL PATTERN GRID COMPLETED; NO ROBUST NEW EDGE; NO LIVE ORDERS.** Manager issues #10/#11 (27 Oct priority change) supersede the previous funding-focused queue: prioritize finding selective high-win-rate net-positive entries/exits; keep **FEE=0.0015 fixed round-trip**, and **exclude funding** from this research. Read issues and prior handoff/directives before the experiment.

## Hypothesis and preregistered search
Hypothesis: **not every DeltaRSI fading histogram is a trade**. A combination of prior-wave exhaustion, 4H EMA trend context, 1H price rejection/sweep and causal structural stops might improve both net expectancy and win rate across train/validation, and retain performance in a third chronological diagnostic period.

Exploratory grid of **486 rules**: three signal families (forming h1..3 fade; completed h4 fade; frozen completed 4H turn), six filters (none, follow/counter EMA50, follow EMA200, 1H wick rejection, 20h swing sweep), three stops (2.5 prior-known ATR, preceding 4H peak-bar extreme, extreme of six preceding completed 4H candles), three TP levels (1.2R/1.5R/3R), and three timeouts (12/24/48h). Same fixed cost across all cells. Trend filters use **previous fully closed 4H** for every family; wick/sweep use **last completed 1H** at decision. Entry is next 1H open. No future candle used to decide; stop known at entry; stop-first when both touched; adverse gap fills via shared execution core. Stops and TP evaluated together as a pair.

## Changes, code, reproducibility and evidence
- New `pattern_edge_search.py`, `test_pattern_edge_search.py`, `.github/workflows/pattern-edge-search.yml`; machine-readable `reports/pattern_edge_search.json` contains **all 486 cells including failures**, per-symbol/side diagnostics for top 10, rejection counts, seed, exact fee and SHA256 for each cached source.
- Reproduce: `python -m unittest -v test_pattern_edge_search test_causal_4h_parity test_completed_candles && python -u pattern_edge_search.py`. No exchange calls or orders.
- **GitHub Actions run [40452609549](https://github.com/VulpreS/Deltarsi1/actions/runs/40452491428) SUCCESS, 25 tests OK**, grid run and report committed. Producer SHA `f992f8f70433a7f51b4e786eae8588f7e4db2820`; new test SHA `c096640446e2881121b3997facc65e098a2fbde4` included in run. Earlier failed runs 40452432776/40452440167 were a temporary syntax error in the newly added bootstrap note, fixed before this successful run.
- Inputs only committed `data/BTCUSDT_1h.csv`, `ETHUSDT_1h.csv`, `ICPUSDT_1h.csv`, `HYPEUSDT_1h.csv`; source hashes are in JSON and unchanged from prior cycles. Event counts BTC 32/35/255, ETH 35/32/233, ICP 40/32/274, HYPE 15/14/125 (forming/closed/turn). No candle downloads.
- Each asset split 50/25/25 chronologically. Candidate rank uses **only first two periods**; last period is a **diagnostic already examined in prior research**, NOT untouched OOS. Gate: train >=30, validation >=12, positive mean net R and PF>1 in both. **100/486** pass. Top 10 selected without using the third period. Fixed fee = **15bp round-trip** including entry/exit execution notionals; no cost parameter optimization.

## Results: pattern discovery, NOT independent validation
| Rule | Train N / WR / mean R / PF | Validation N / WR / mean R / PF | Previously seen last period N / WR / mean R / PF |
|---|---|---|---|
| #1 turn + follow EMA50 + prior six-4H wave stop + TP3R/48h | 57 / 63.16% / +0.589 / 2.625 | 39 / 61.54% / +0.434 / 2.076 | **37 / 21.62% / −0.566 / 0.305** |
| #2 same, TP1.5R/48h | 58 / 63.79% / +0.395 / 2.141 | 40 / 70.00% / +0.452 / 2.464 | **37 / 35.14% / −0.259 / 0.607** |
| #3 same as #1, 24h | 62 / 58.06% / +0.410 / 2.366 | 43 / 53.49% / +0.387 / 2.470 | **41 / 21.95% / −0.483 / 0.313** |
| #4 turn + follow EMA50 + prior six-4H wave stop + TP1.2R/48h | 58 / 67.24% / +0.339 / 2.100 | 40 / 72.50% / +0.422 / 2.491 | **39 / 38.46% / −0.280 / 0.550** |
| #5 forming fade, no extra filter, ATR2.5, TP3R/48h | 46 / 63.04% / +0.321 / 2.103 | 23 / 60.87% / +0.302 / 2.434 | **32 / 34.38% / −0.152 / 0.656** |
| Closest frozen reference 4H turn, ATR2.5 stop, **3ATR target = TP1.2R**, 48h | 209 / 51.20% / +0.014 / 1.042 | 125 / 58.40% / +0.082 / 1.285 | **137 / 50.36% / +0.091 / 1.299** |

**All 10/10 top-ranked rules have negative mean R and PF<1 in the previously inspected third period.** Of 100 train/validation-qualified configurations, 21 have positive last-period expectancy and PF>1, but selecting those 21 after inspecting last-period outcomes would be post-hoc overfitting. The unfiltered 2.5ATR-stop/3ATR-target reference remains marginally positive across three reused periods, but HYPE's 1.2R reference is negative in its last period (19 trades, −0.077R, PF0.775), and this reference is not a shared-capital portfolio or an independently validated edge.

For #1, last-period LONG 24 trades/20.83% WR/−0.572R, SHORT 13/23.08% WR/−0.554R. Last-period per-asset mean R: BTC −0.190 (N10), ETH −0.690 (N15), ICP −0.485 (N6), HYPE −0.961 (N6). Its exploratory 30-calendar-day block bootstrap last-period mean R 95% interval is [−0.951, −0.342] with **only four effective blocks**; NOT selection-adjusted, NOT independent. Top-10 full block CIs and per-asset/side diagnostics are in JSON.

## Limitations / risks / failed hypotheses
1. **Cross-regime failure:** the apparently strongest EMA50 + wave-stop combination collapses in the latest reused segment on both sides and all four assets. Strong historical train/validation WR alone is not a reliable edge.
2. **Data snooping:** all three historical periods were already examined by earlier studies. Even the nominal last 25% is contaminated. The bootstrap interval is conditional on the selected rule and only 4 last-period blocks; do not claim out-of-sample significance.
3. **Execution model:** per-symbol sequential non-overlap, 0.25%-risk-normalized R-based pseudo DD, not shared-capital hourly mark-to-market DD; no cross-symbol competition or venue fills. Historical `mean_net_pct` is per-notional price return, NOT portfolio return. Price stop `prior_wave6x4h` is a fixed **six-bar proxy**, not the entire actual DeltaRSI wave. Structural stops can be rejected for geometry.
4. No user-expanded labeled trade CSV yet; five annotated chart cases are not independent wins or exact fill timestamps. No real orders.

## Conclusion and concrete manager questions / next cycle
1. **Reject promotion of all 10 top rules**: none survives even the reused diagnostic segment. Do not re-rank using that segment; retain the unfiltered 4H turn as a descriptive control and mark all selected rules exploratory.
2. Next prioritize **regime shift analysis** (why trend-following wave stops collapse: pre-entry trend strength, long/short asymmetry, trend transitions, stop distance and 1H price structure), using a *predeclared* small feature ablation. Investigate **net-positive high-WR regimes**, not funding/accounting.
3. Prepare CSV importer `symbol,side,timestamp_MSK,entry,exit,stop,notes,confidence` for incoming user-marked trades. Compare causal features at each annotated decision and all losing/rejected controls, with explicit uncertainty in timestamps; do NOT tune solely to five marked wins.
4. Next experiment: predeclare a **regime filter** on train only, validate without inspecting the third segment for selection; show N/WR/avg R/PF and opportunity loss, LONG/SHORT separately, then hold fixed for prospective paper-only data. Re-run 3 candidate families on common-capital portfolio before any strategy recommendation.
5. Need fresh forward immutable receipts and >=90 days / >=50 independent virtual fills for credible confirmation. No orders; no production authorization.

---

# DeltaRSI researcher handoff — cycle 13, 2026-10-27 ~07:00 MSK (P0 #12 independent UTC funding enumeration)

**Status: INDEPENDENT EVENT CLOCK AUDIT + 309-ROW RECONCILIATION COMMITTED; 66/66 SAME-SHA REGRESSION TESTS PASS. #12 REMAINS OPEN. NO NEW ALPHA CLAIM, NO ORDERS.**

## Hypothesis and priority read before changes
Read current manager cycle-12 directives, open issue #12, saved researcher cycle-12 handoff and frozen reports. Hypothesis: 4H/1H funding-event differences arise solely from conservative OHLC exit-time bounds, and event counts can be reproduced by **independently enumerating 00/08/16 UTC timestamps**, not by dividing already booked funding debits. A second hypothesis is that funding-settlement ordering at exact exit boundaries creates a material bounded uncertainty even when the 4H/1H upper bounds agree. No parameter tuning.

## Code and reproducibility
- Added `independent_funding_clock_audit.py` and `test_independent_funding_clock_audit.py`; extended `.github/workflows/p0-funding-clock-reconciliation.yml` to run the seven new fixtures plus the existing 59 integrated tests, both audits, and commit the report. The first workflow edit had an invalid literal newline and produced a no-job failure; corrected in commit `6ab53aa5`, then [CI 40447024839](https://github.com/VulpreS/Deltarsi1/actions/runs/40447024839) **SUCCESS**, **66 tests** on that exact code SHA. This failure was YAML syntax only; the corrected run executed both audits successfully.
- Reproduce without exchange calls: `python -m unittest -v test_funding_clock_reconciliation test_independent_funding_clock_audit test_causal_4h_portfolio test_causal_4h_parity test_completed_candles test_portfolio_open_order test_reverse_open_precedence test_standalone_parity_audit test_portfolio_risk_audit && python independent_funding_clock_audit.py`.
- Inputs: committed cached `reports/portfolio_risk_audit.json` and `reports/causal_4h_portfolio_audit.json` from BTC/ETH/ICP 1H candles. The full report `reports/independent_funding_clock_audit.json` includes 309 matched rows, source/config SHA256, UTC entry/exit bounds, independently enumerated min/max events, both quantities, gross, fees, funding and net plus differences. Script fails closed on changed candle hashes, missing/duplicate IDs, side/fill mismatch, incorrect booked funding, fee notional or net arithmetic. No candle download and no order placement.
- Funding convention audited (not venue-confirmed): event at **entry** instant excluded; event at exact **exit** instant excluded for lower bound and included for upper bound. Stop/TP fill within hourly OHLC remains uncertain. Without a gap flag in 1H trade ledger, its lower bound can be deliberately wider than the actual possible gap exit interval.

## Results (frozen 15bp total friction + adverse synthetic 3bp per UTC 8h funding event)
1. **309/309** frozen 4H and 1H fills/reasons matched. Independent UTC event enumeration reproduced **52** extra conservative 4H upper-bound events (23 stop, 29 target), **zero** cases with 1H more. This confirms cycle-12 funding timing explanation **without deriving event counts from booked debits**. No change to frozen trades or baseline return.
2. New **within-1H lower/upper exposure census**, where an event exactly at the exit is uncertain: frozen turn **1301–1428 events** across 309 trades (**127 uncertain events**: 88 time exits, 19 stops, 20 targets); forming **354–366** across 89 trades (12 uncertain); completed fade **308–339** across 83 trades (31 uncertain, including 13 time exits).
3. At fixed booked entry notionals, the sum of upper-minus-lower **synthetic funding debits** is **0.247246 percentage points of initial capital** for frozen turn, **0.028911pp** forming, **0.062881pp** completed fade. **These are sensitivity envelopes, not recomputed portfolio returns**: changing funding changes subsequent equity-dependent quantities. The 0.247pp boundary envelope is larger than the previously identified **0.11945pp** 4H-vs-1H upper-bound return discrepancy; the latter is NOT alpha.
4. All matched ledger fees use actual entry/exit execution notionals; booked funding equals independently enumerated *upper* count × notional × 3bp; per-trade gross − fee − funding = net. 66 deterministic/integrated tests passed in the linked same-SHA CI. No new independent-window backtest was claimed; all history was previously inspected.

## Limitations, interpretation and decision
- No observed venue funding, mark-trigger order chronology, actual fill timestamps or same-venue source provenance. The funding-clock audit tests *synthetic* settlement conventions and does not prove that either lower or upper bound equals real Bybit funding.
- The `time` exits at exact UTC funding boundaries are especially sensitive to exchange event ordering. 88 of 127 frozen-turn uncertain events arise there. The present upper-bound stress is deliberately adverse, not a realistic estimate of settlement.
- 4H vs 1H mark-to-market DD still differs by sampling frequency. No admission/skip trace parity with legacy standalone, no ETH-challenger nine-cell economic parity and no truly independent OOS or immutable forward receipts. Do **not** close #12 or promote a strategy. HYPE remains excluded.

## Concrete manager questions / next cycle
1. Accept **independent event-clock enumeration DONE** for the frozen 309-trade cohort, but leave #12 P0 OPEN for all-candidate admission/reentry reason parity and full 15/25/40bp × 0/1/3bp **baseline + ETH challenger** reconciliation? Recommend yes.
2. Prioritize one identical-clock portfolio replay that explicitly chooses exit-boundary convention (upper/lower as two **predeclared sensitivities**), re-sizes every subsequent position and reports PF/return/hourly MTM DD/worst month. Do not change entry thresholds or select a winning historical variant.
3. Require direct same-venue OHLCV, actual 00/08/16 UTC funding and fee/spread/mark execution provenance under #5 before any shadow/paper readiness decision. Preregister a truly prospective, append-only shadow sample; never relabel reused history as OOS.
4. Continue to treat #13 completed-vs-forming as exploratory and do not deploy or send real orders.

---

# DeltaRSI researcher handoff — cycle 12, 2026-10-27 ~05:55 MSK (P0 #12 funding-clock reconciliation)

**Status: AUDIT CODE + DETERMINISTIC TESTS + REPRODUCIBLE REPORT COMMITTED; HISTORICAL FUNDING DISCREPANCY EXPLAINED. NO INDEPENDENT OOS, NO STRATEGY PROMOTION, NO ORDERS.**

## Hypothesis / manager tasks read first
Read open issues #12 (P0 chronological economic parity), #13 (P1 shared-capital forming/closed 4H), #5 (venue/funding provenance), cycle-11 handoff and `reports/manager_directives.md`. Hypothesis: the +0.1194 percentage-point 1H-vs-4H frozen-turn portfolio return discrepancy is caused by the wider 4H OHLC funding-exposure upper bound plus compounding of equity-dependent sizing, **not** a signal edge or mismatched fills.

## Changes and reproducibility
- Added `funding_clock_reconciliation.py`, `test_funding_clock_reconciliation.py`, `.github/workflows/p0-funding-clock-reconciliation.yml`; latest source commit `b9d0a994c82249b5ce7a3c778001b256c54080b8` (adds per-engine cash-conservation assertions), original code commit `248e8e519aac3181239bf6aa5e6f8c6c77581235`.
- Reproduce with **existing cached reports** (no candle fetch): `python -m unittest -v test_funding_clock_reconciliation test_causal_4h_portfolio test_causal_4h_parity test_completed_candles test_portfolio_open_order test_reverse_open_precedence test_standalone_parity_audit test_portfolio_risk_audit && python funding_clock_reconciliation.py`. The workflow executes the same tests and saves `reports/funding_clock_reconciliation.json`.
- Matched all 309 BTC/ETH/ICP frozen-turn entries by symbol + UTC entry; strict fail-closed on source hashes, duplicate/missing IDs, side, entry/exit fills and reason, fractional inferred funding events, per-trade funding and net accounting. No rule, parameter, signal or trade was changed.
- Per-trade algebra decomposes funding difference `F4-F1 = rate*N4*(events4-events1) + rate*(N4-N1)*events1`, separating **time-bound** vs **equity-compounding size** effects. Nine 15/25/40bp friction × 0/1/3bp adverse synthetic funding scenarios are reported. Original source candle SHA256 BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`, ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`, ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`.

## Results: frozen-turn 309-trade matched accounting
- **309/309 matched fills; 52 trades** have one more synthetic UTC funding event in the 4H conservative upper bound than the 1H bound; 257 equal, **zero** cases with 1H more. BTC 21/123, ETH 18/97, ICP 13/89. Of 52: 29 target and 23 stop; no time/terminal exits differ.
- At 3bp adverse synthetic funding/event and 15bp friction, 4H − 1H funding debit = **+0.0011555782 initial equity** (0.11556 percentage points). Timing convention contributes +0.0011707256, position-size compounding −0.0000151474. Gross PnL delta −0.0000560242; fee delta −0.0000171437; **net 4H − 1H = −0.0011944586** (~−0.11945pp). This exactly reconciles previously reported **4H +1.7528% vs 1H +1.8722%** within report rounding.
- **Funding 0bp negative control:** identical 4H/1H net returns at all 15/25/40bp costs: +4.7203%, +2.5694%, −0.5748%, respectively. At 25bp/3bp, 4H −0.3375% vs 1H −0.2205%; at 40bp/3bp, −3.3929% vs −3.2795%. The strategy remains cost-sensitive and not robust.
- Per-asset and per-exit-reason breakdowns, 309-event census, exact examples, nine-scenario PF/return/DD table, SHA256 of both input reports and source config hashes are in `reports/funding_clock_reconciliation.json`. Latest producer SHA `b9d0a994c82249b5ce7a3c778001b256c54080b8`; the machine-readable report regenerated after the added per-engine cash-conservation checks. Workflow run URL/status was not available from the connector at handoff time, so do not claim independently verified CI SUCCESS solely from the report.

## Limitations and conclusion
- This is **reconciliation of reused historical ledgers**, not fresh bktest evidence or untouched OOS. Hourly OHLC narrows the conservative possible stop/target time interval; it does **not** reveal actual fill timestamp, funding settlement ordering or exchange receipts. Both models use assumed adverse 3bp/8h funding, not observed venue rates.
- 4H marks and 1H hourly-close MTM drawdowns have different sampling frequency. Do not directly compare their DD without standardizing marks. No order book, mark-trigger, slippage observation, or venue/market provenance. The 1H-vs-4H discrepancy is **not alpha**.
- **Decision:** keep frozen strategy unchanged. Prefer the 1H tighter conservative funding-clock convention for future **research comparisons only**, clearly labeled synthetic, pending venue-verified actual funding. No production promotion and no real orders.

## Concrete manager questions / next iteration
1. Accept #12 **funding discrepancy classified and 309-trade economic bridge DONE**, but keep **venue-funding parity and independently verified CI run status OPEN**? Recommend yes. Do not mark whole #12 complete until integrated test-run status and admission/skip parity are confirmed.
2. Require **single-SHA integrated CI confirmation** and, if needed, separate exact per-UTC candidate admission/skip trace for frozen 4H vs hourly; report any unexplained IDs. Do not change frozen thresholds.
3. Under #5 obtain exchange, spot/perp, observed UTC funding receipts and direct same-venue 4H OHLC parity. Freeze a prospective post-cutoff shadow stream before any strategy ranking.
4. Do not use the 0.1194pp reconciliation as evidence for forming/closed fades or reselect strategies on the already-inspected final third.

---

# DeltaRSI researcher handoff — cycle 11, 2026-10-27 ~05:00 MSK (P1 #13 shared-capital causal 4H portfolio)

**Decision: EXPLORATORY ONLY / NO STRATEGY PROMOTION / NO LIVE ORDERS.** Integrated cached-only [CI 40435628911](https://github.com/VulpreS/Deltarsi1/actions/runs/40435628911) **SUCCESS**. Full [report](https://github.com/VulpreS/Deltarsi1/blob/main/reports/causal_4h_portfolio_audit.json), [code](https://github.com/VulpreS/Deltarsi1/blob/main/causal_4h_portfolio_audit.py), [tests](https://github.com/VulpreS/Deltarsi1/blob/main/test_causal_4h_portfolio.py). Last producer code commit `8d9c1bf8`, workflow `043b1314`; config SHA256 `fba5c1c87fe87faa3b069f45ff8503b89583a17b040714e0243a97eecbddb493`.

## Hypothesis / priority and manager instructions reviewed first
Read current open issues #13 (updated manager acceptance: shared capital/true MTM DD/UTC admission ledger/4H parity), #12, #14 and cycle-10 researcher handoff plus manager directives. **Hypothesis:** earlier 1H-observed fading DeltaRSI might lose its apparent advantage versus completed-4H fading when both compete for BTC/ETH/ICP capital. Do not retune the frozen `ratio <= 0.7`, `prior peak >= 15`, 2.5 ATR stop, 3 ATR target, 48h hold. Frozen completed-4H `turn` is a separate signal baseline. HYPE is excluded from shared portfolio and retained as a negative control in the previous causal report.

## Changes / reproducibility
- New `causal_4h_portfolio_audit.py`, `test_causal_4h_portfolio.py`, `.github/workflows/p1-causal-4h-portfolio.yml`; regression workflow also runs previous causal, candle-completion, gap-priority, standalone parity and portfolio tests. No exchange network calls or order placement.
- Reuse EXACT cycle-10 causal `events()` streams (first qualifying h=1..3, completed h=4, plus completed-turn reference). Next 1H open, previous fully completed 4H ATR for fade; 4H completed signal ATR for turn. Shared portfolio: max 2 positions, risk 0.25% equity per initial stop, aggregate stop risk <=0.5%, per-symbol notional <=1x equity, aggregate gross <=2x, deterministic BTC→ETH→ICP admission. At each hour OPEN settle old resting stop/target gaps before new entries; only after admissions inspect OHLC with stop-first ambiguity. Time exit after 48 completed 1H bars; close remaining positions at terminal window end.
- Costs 15/25/40 bp total friction, half on actual entry notional and half on actual exit notional; 0/1/3 bp adverse **synthetic** funding per UTC 8h exposure upper bound. Mark equity every hourly close including unrealized PnL and synthetic funding. Report 3 nonoverlapping equity-reset chronological windows, asset/side decomposition, worst month, exposure, 3x3 stress, exact UTC signal accept/reject trace, full trade ledger, cash and price-only equal-weight buy/hold.
- Source SHA256: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`. **No re-download.**

## Results (15bp friction + 3bp adverse synthetic funding per 8h; all cached history reused)
| Shared-capital mode | Trades | Net return | PF | Hourly-close MTM DD | Exposure |
|---|---:|---:|---:|---:|---:|
| Forming h=1..3 | 89 | +3.4464% | 1.4737 | 1.7352% | 28.02% |
| Completed h=4 | 83 | +3.7426% | 1.5875 | 1.2256% | 26.74% |
| Frozen 4H turn reference, executed hourly | 309 | +1.8722% | 1.0746 | 3.3238% | 78.13% |

- **Three nonoverlapping reused windows**, forming/closed/turn returns: window 1 +2.1161/+1.5839/−0.9740%; window 2 +2.6516/+2.7221/+0.5687%; window 3 **−1.3141/−0.5812/+2.1375%**. Both fade rules fail the last inspected window; no robust cross-regime advantage. Forming is inferior to completed fade overall in both return and DD; this is descriptive, not independent proof.
- Forming BTC/ETH/ICP accepted 28/30/31 trades; net PnL +0.014827/+0.024530/−0.004893 on initial equity 1. Completed 30/27/26; +0.015332/+0.017175/+0.004918. Forming 48 LONG/41 SHORT; completed 40 LONG/43 SHORT. Admission trace: forming 107 attempts, 15 same-symbol skips, 3 max-position skips; completed 99 attempts, 12 and 4. No leverage-cap breaches in this cohort.
- Fee stress: forming 40bp/3bp +1.8596%, PF 1.2329; completed 40bp/3bp +2.2538%, PF 1.3205. Frozen turn 25bp/3bp −0.2205%, 40bp/3bp −3.2795%. These are assumptions, NOT observed venue costs.
- Price-only equal-weight buy/hold BTC/ETH/ICP at 15bp = −30.4966%, but has radically different directional exposure and is **not a risk-matched alpha benchmark**. Cash = 0%.
- **P0 #12 reconciliation:** all 309 frozen-turn hourly entries exactly match the 309 entries in the previous 4H portfolio; 0 unmatched and 0 exit-price/reason differences. But 1H funding upper-bound timing and equity-dependent sizing differ: 287 quantities, 293 funding debits and 294 fees differ. Historical 4H baseline +1.7528% vs hourly reference +1.8722%; old/new aggregate gross 0.0771501/0.0772061, fees 0.0310004/0.0310175, funding 0.0286222/0.0274666. **Do not mistake the +0.1194 percentage-point difference for alpha** or imply exact economics parity. Fills match; modeled funding/position sizes differ.

## Limitations / blockers / conclusion
- **No independent out-of-sample data:** all 3 historical windows have been previously inspected. Positive full-history PF is exploratory; comparison is not evidence of reproducible strategy. No optimization or cherry-picking this cycle.
- Hourly close MTM DD is more granular than prior 4H DD but does not measure intrahour/tick drawdown, queue fills, spread, mark-trigger stops or liquidation. OHLC stop-first is conservative, not an exchange replay.
- Funding is synthetic adverse upper-bound; true exchange, market type and observed funding remain unavailable. 1H-vs-4H funding convention differences materially affect cumulative PnL.
- Upstream `causal_4h_parity_audit.PARAMS["peak_requires_previous_nonrising"]=True` is **misleading documentation**: actual frozen `qualifying()` requires `abs(prev)>=abs(prevprev)` (prior magnitude nondecreasing). No rule changed. Correct label in a separate compatibility-preserving documentation patch if manager approves.
- **NO strategy promotion; NO real orders.**

## Concrete questions / next manager iteration
1. Accept #13 as **portfolio capital competition + hourly MTM risk DONE within cached model**, but **independent OOS and actual funding OPEN**? Recommend yes. The forming signal does not improve full-history portfolio risk/return and both fades lose in last reused third.
2. Standardize and explicitly preregister a single **funding boundary convention** for both 1H and 4H engines (or use observed venue funding), then verify 309-trade cash/quantity parity. Keep source/venue unknown status explicit.
3. Decide whether to correct misleading `peak_requires_previous_nonrising` metadata without changing the frozen predicate/hash, and whether the closed fade warrants **prospective shadow-only** observation as a challenger. No retroactive selection on inspected windows.
4. Obtain venue/spot-vs-perp provenance, direct same-venue 4H OHLC, actual funding, and append-only post-cutoff hourly receipt records. Freeze hashes and minimum sample before interpreting forward results; do not backfill as forward.
5. No production deployment or orders without explicit user authorization.

---

# DeltaRSI researcher handoff — cycle 10, 2026-10-27 ~04:00 MSK (P1 #13 causal forming-4H parity)

**Status: REPRODUCIBLE EXPLORATORY AUDIT / CI PASS; NO ROBUST EARLY-ENTRY EDGE, NO INDEPENDENT OOS, NO LIVE ORDERS.** [CI 40429556695](https://github.com/VulpreS/Deltarsi1/actions/runs/40429556695) SUCCESS. [Machine-readable report](https://github.com/VulpreS/Deltarsi1/blob/main/reports/causal_4h_parity_audit.json). Research code `causal_4h_parity_audit.py`; fixtures `test_causal_4h_parity.py`. Parameter SHA256 `9bcd09692a163f18c29b6f5e19236a079857488c6f4ba1b4370acb68d3a1a974`.

## Hypothesis / manager priorities read first
Read current open issues **#14 P0**, **#12 P0**, **#13 P1**, latest cycle-9 handoff and `reports/manager_directives.md`. #14 is fixed for synthetic resting-first semantics with **zero** historical competing gap-open reversals; #12 has matched standalone fill parity but still requires broader admission trace. **This cycle tests #13**: does earlier *causally observed* 4H DeltaRSI fading improve execution when **both** early and closed decisions use the *same previously completed 4H ATR*, 2.5 ATR stop, 3 ATR target, 48h hold, conservative 1H fills, 0.25% equity initial stop-risk, identical fee/funding grid? One predeclared exploratory fade hypothesis: previous opposite DeltaRSI >=15 and at/above its prior magnitude, current same-sign magnitude <=70% of previous; first qualifying 1H close at h=1..3 versus qualifying 4H close at h=4. No parameter search.

## Changes and causal reproducibility
- Added `causal_4h_parity_audit.py` (commit `b07eb40e`) and tests `test_causal_4h_parity.py` (commit `e22d4f13`), plus workflow `.github/workflows/p1-causal-4h-parity.yml` (commit `7f8e46e5`). CI ran regression suite and generated report; all steps SUCCESS.
- **Streaming `CausalDelta`** reproduces the canonical full-history SMA(21)→RSI RMA(12)→EMA(7)→DeltaRSI on every completed 4H bar and on hypothetical partial bars, with tests comparing against the canonical full-prefix calculation. Partial h=1..3 snapshots **never commit** indicator state. Decision at 1H close, fill no earlier than next 1H open. At 2026-09-18 08:00 UTC (11:00 MSK, corrected L3), the 08:00–09:00 hourly bar is **not yet closed**; its first partial update is available only at 09:00 UTC. No use of future 4H close.
- Strict completed UTC 4H aggregation from cached 1H only, fail closed on gaps; no downloads, APIs or orders. Full cached CSV SHA256 BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`, ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`, ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`, HYPE `7b1e66fbf6aee1f1407e877c7e1e4aaaeb8489009925438eadc53cf1b6c35bae`.
- Both fade strategies use ATR computed **only through previous completed 4H candle**, the same stop/target multiples, 48 × 1H bars, gap-safe stop-first, 15/25/40bp round-trip fee+slippage charged on actual entry/exit notional and synthetic **0/1/3bp adverse funding per UTC 8h event**, upper-bound event timing for intrabar fills. Risk-sized 0.25% of equity at stop, max 1× equity per-symbol notional; one position per symbol; no same-exit-hour re-entry. **Separately** evaluated canonical completed-4H `turn` signal with ATR known at signal close, as a **distinct frozen-signal reference** (not identical engine/portfolio to #12).
- Full chronological per-symbol runs and **three nonoverlapping window-reset regimes**, separate LONG/SHORT schedules, **matched same-bucket/side opportunities** (overlapping event-study, not executable), 30-day calendar-block bootstrap (1200 deterministic draws), reversed-side negative control, 0%-cash and price-only buy-and-hold contextual benchmarks.

## Results — 15bp friction + synthetic 3bp adverse funding / 8h
| Asset | Early forming N / return / PF | Closed fade N / return / PF | Frozen turn N / return / PF | Same-bucket pairs / mean early−closed (pp) / bootstrap 95% CI (pp) |
|---|---|---|---|---|
| BTC | 29 / **+1.1872% / 1.5598** | 31 / **+1.2401% / 1.5836** | 137 / +2.6577% / 1.2262 | 26 / +0.03965 / [+0.00708,+0.06763] |
| ETH | 30 / **+2.4179% / 2.1739** | 28 / **+1.9899% / 2.0874** | 136 / +1.1451% / 1.1004 | 28 / −0.01794 / [−0.06063,+0.01234] |
| ICP | 33 / **−0.8344% / 0.7674** | 28 / **+0.4113% / 1.1545** | 138 / −0.6831% / 0.9380 | 30 / +0.01525 / [−0.00671,+0.03907] |
| HYPE | 13 / **−0.8090% / 0.4605** | 12 / **−0.5575% / 0.5307** | 69 / −0.9622% / 0.8387 | 11 / +0.06604 / [+0.00295,+0.10649] |

**Interpretation:** BTC's positive matched-pair CI (26 pairs / 11 calendar blocks) is **exploratory only**, with positive-only hypothesis-selection exposure and overlapping outcomes; BTC *separately executable* early schedule actually underperformed closed fade. ETH's higher early executable return **reverses sign** on identical matched opportunities. ICP/HYPE early executable rules lose money; HYPE reversed-side negative control **gains +0.6081%** (13 trades), indicating fragile directional signal. There is **no cross-asset, cross-window robust incremental early-entry edge**.

Three chronological windows (early vs closed, 15bp/3bp, per-symbol equity reset): BTC +0.8794/+0.7242, +0.7398/+0.9331, −0.4315/−0.4170%; ETH +0.8220/+0.7576, +1.7491/+1.8033, −0.1633/−0.5700%; ICP +0.1454/+0.0987, −0.1309/−0.0281, −0.8486/+0.3405%; HYPE −0.5350/−0.2667, +0.4916/+0.0933, −0.7633/−0.3844%. **Last-window early returns negative for all four symbols.** All windows were previously examined in other research, so chronological non-overlap is NOT independent OOS.

## Limitations / decision
- This closes **a substantial but not all** of #13: no single **multi-asset** portfolio comparison with shared capital, max two positions and true mark-to-market drawdown yet; current DD is **closed-trade DD only** and understates intrabar risk. Independent per-symbol results cannot be added as portfolio returns. Frozen-turn reference uses 1H intrabar fills and a separate signal definition; not numerical parity with #12 risk-sized 4H portfolio.
- Same-bucket matched pairs are overlapping hypothetical trades with independent fixed-equity risk sizing, **not** an executable matched-entry cohort. Early vs closed can differ in whether a signal exists at all; full schedules have different trade counts and opportunity costs. Paired bootstrap CI is not an independent proof, ignores model-selection uncertainty, and has only 5–11 calendar blocks.
- All history is reused/contaminated by prior exploration. Funding and 15/25/40bp friction are assumptions, not observed venue economics; OHLC does not reveal queue, spread, mark-price triggers or exact intrahour fills. HYPE venue provenance remains unknown.
- **Decision: do NOT promote early entry or closed fade.** Preserve frozen turn as reference, paper research only, no real orders.

## Specific questions / proposed next iteration for manager
1. Should #13 be marked **PARTIAL / causal event timing, ATR parity and cost grid VERIFIED**, with **portfolio competition and MTM drawdown OPEN**? Recommend yes. Reconcile same-UTC frozen turn trade IDs with #12 before any numerical ranking.
2. Next researcher: feed **both frozen early and closed event streams** into the P0-corrected `portfolio_risk_audit` event-driven engine with max 2 concurrent positions, 0.25%/trade and 0.5% total risk, 15/25/40bp × 0/1/3bp stress, true MTM DD, explicit skip/admission trace and identical UTC calendar; include HYPE only as negative control. **No retuning.**
3. Investigate the *causal* last-window breakdown (all four early negative), especially regime/side and 1H gap sensitivity, **diagnostics only**; no regime filter selection on these inspected windows.
4. Require source-verified venue/market, observed funding and append-only timestamped **future** 1H receipts before declaring any alpha. No independent holdout exists in the cache.

---

# DeltaRSI researcher handoff — cycle 9, 2026-10-27 03:00 MSK (P0 #14 reverse-gap order priority)

**Status: P0 #14 CODE FIX + HISTORICAL CENSUS VERIFIED IN CI; NO ECONOMIC CHANGE ON CACHED HISTORY. No independent OOS, no production approval, no orders.** [GitHub Actions 40422961335](https://github.com/VulpreS/Deltarsi1/actions/runs/40422961335) SUCCESS. [Full report](https://github.com/VulpreS/Deltarsi1/blob/main/reports/reverse_gap_priority_audit.json).

## Hypothesis and manager priorities read first
Read open manager issues #14 (new highest P0), #12, #13, #8, #9 and #11; reviewed prior cycle-8 handoff and manager directives. **Hypothesis:** the ETH raw-opposite-DeltaRSI exit, scheduled at the next 4H open, may incorrectly override a resting stop or target already crossed at that open; the old market-first ordering can credit favorable price improvement beyond the target. This is a genuine synthetic execution-policy defect, but historical frequency was unknown.

## Changes / reproducibility
- `portfolio_risk_audit.py`: canonical `open_precedence="resting_first"`. At each UTC 4H open, check existing resting stop/target using **only OPEN**; adverse stop gap fills at OPEN, favorable target gap fills conservatively at TARGET. If neither triggered, execute pending reverse at OPEN. Then release positions and admit new signals; only afterward inspect intrabar high/low with stop-first. Alternative `market_first` explicitly retained as sensitivity, never silently the canonical result. Funding and exit fee are debited once by `settle`; no strategy thresholds changed.
- Added `pending_gap_competitions` event census with exact signal/entry/open UTC, direction, alternative fill prices, quantity and hypothetical gross/exit-fee differences.
- New `test_reverse_open_precedence.py`: long/short target-gap, long/short stop-gap, both directions inside band, two old positions plus third-symbol signal, unchanged baseline negative control, invalid policy rejection. The old market-first code fails favorable target fixtures. Existing portfolio and aggregation regressions included.
- New `reverse_gap_priority_audit.py`, `.github/workflows/p0-reverse-gap-priority.yml`. Reproduce: `python -m unittest -v test_reverse_open_precedence test_portfolio_open_order test_portfolio_risk_audit test_completed_candles && python reverse_gap_priority_audit.py`. Uses **only cached 1H**, strict 4H derived bars; no network/fetch/orders. Producer code commits: `0109d7ef` (engine), `611e4abe` (tests), `e04f597c` (audit), `1db1c5f6` (workflow).
- Frozen CONFIG_HASH from engine; unchanged source SHA256: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`.

## Historical results / economics
**Competing pending-reversal vs resting stop/target OPEN gaps: exactly ZERO** for both frozen baseline and ETH challenger across the full common historical cache, **all nine** 15/25/40bp total-friction × 0/1/3bp synthetic adverse funding scenarios, and each of five chronological nonoverlapping windows. Matched trade IDs and economic fills unchanged in both precedence conventions; zero changed matched trades, no only-in-one-policy trades.

| Frozen portfolio, 15bp friction + 3bp adverse synthetic funding/8h | Resting-first | Old market-first |
|---|---:|---:|
| Baseline BTC+ETH+ICP trades | 309 | 309 |
| Baseline net return / PF / MTM DD | +1.7528% / 1.0697 / 3.3683% | identical |
| ETH challenger portfolio trades | 281 | 281 |
| Challenger net return / PF / MTM DD | +1.0711% / 1.0461 / 3.4507% | identical |

Fee/funding sensitivity unchanged: baseline 25bp/3bp **−0.3375%**, 40bp/3bp **−3.3929%**; challenger 25bp/3bp **−0.7564%**, 40bp/3bp **−3.4361%**. Five-window baseline returns −0.1478/−0.6350/−0.5189/−0.0285/+2.6087%; challenger −0.5485/−0.6683/+0.7957/−0.3573/+1.4031% (15bp/3bp). All five windows were previously inspected, **NOT independent OOS**. No retuning, no alpha claim.

## Limitations / conclusion
Synthetic fixtures prove a real *potential* fill bias, but the cached cohort contains **zero** affected historical instances, so do **not** claim it caused past PnL inflation. Actual exchange resting order activation, mark-vs-last triggers, venue fill priority, funding rates and true spread/impact are unknown. Portfolio model remains OHLC-based and conservative, not exchange replay. ETH challenger still inferior to baseline on full risk-sized portfolio under 15bp/3bp and has no forward validation.

## Concrete questions / proposed next iteration for manager
1. Accept #14 as **FIXED for deterministic resting-first policy and historical zero-incidence census**, but retain venue-order semantics as an external unresolved assumption. Decide whether #12 can close its open-time-priority component; its broader admission-reason reconciliation may remain open.
2. Next prioritize #13 **matched forming-4H vs closed-4H**, with the same 4H ATR, risk, stop/TP/hold, fee/funding grid and explicit UTC event stream. Freeze one hypothesis; no selection on reused final quarter. Include negative control and by-asset/by-side windows.
3. For forward evaluation, obtain verifiable venue/market source and receipt-time immutable data. Keep all inspected historical windows labeled exploratory; do not promote strategy until sealed prospective evidence.

---

# DeltaRSI researcher handoff — cycle 8, 2026-10-26 22:55 UTC (P0 #12 standalone trade-ID parity)

**Status: P0 #12 PARTIAL — exact shared-trade execution parity VERIFIED; remaining stress grid and historical competing-gap census OPEN. No independently confirmed edge, no production approval, no orders.** Latest CI [40416043908](https://github.com/VulpreS/Deltarsi1/actions/runs/40416043908) SUCCESS, 32 regression tests; producer commit `ba3aada52ab4f1b97cf784cb1bab14db57960bb1`. Full report [reports/standalone_parity_audit.json](https://github.com/VulpreS/Deltarsi1/blob/main/reports/standalone_parity_audit.json).

## Hypothesis / leader priorities read before execution
Reviewed open manager issues [#12](https://github.com/VulpreS/Deltarsi1/issues/12), [#13](https://github.com/VulpreS/Deltarsi1/issues/13), [#9](https://github.com/VulpreS/Deltarsi1/issues/9), [#8](https://github.com/VulpreS/Deltarsi1/issues/8), [#11](https://github.com/VulpreS/Deltarsi1/issues/11) and prior `reports/research_handoff.md`, `reports/manager_directives.md`, `reports/portfolio_risk_audit.json`, `reports/matched_exit_audit.json`. **P0 hypothesis:** standalone frozen 4H baseline and chronological risk-sized portfolio should agree on entry and gross exit for identical signal UTC+direction; aggregate N differences arise from different re-entry scheduling and cross-symbol risk competition, not silently inconsistent fill rules.

## Changes / reproducibility
- Added `standalone_parity_audit.py`: frozen 2.5×4H ATR stop, 3×4H ATR target, max 12 completed 4H bars; exact UTC signal/entry key comparison between `p0_gap_audit.simulate` and `portfolio_risk_audit.simulate` for each symbol alone. Five chronological **nonoverlapping** windows plus one full continuous run, with separate per-window resets. No retuning, no network access or candle fetch. Runs at 15bp assumed round-trip friction and **zero synthetic funding for fill-parity isolation**.
- Isolated portfolio checked both with production notional/leverage caps and with caps relaxed *for diagnostic only*; results were identical in all full-history standalone runs. All same-signal exit prices and gross percentage returns compared to numerical tolerance 1e-10. One per-symbol last-trade exit reason differs only in label `time` vs `terminal` at the common-data boundary; **same economic fill**.
- Added cross-asset exact-key comparison between isolated-symbol portfolio and 3-symbol portfolio with 2-position / 0.5% aggregate initial stop-risk cap. Fixed an **audit-only** bug where dictionary keys omitted symbol and silently collapsed simultaneous cross-asset signal IDs; added fail-closed duplicate-key regression. This was NOT a defect in the portfolio trading engine.
- Added `test_standalone_parity_audit.py` fixtures for same-signal price/side parity, exit-bar cooldown, open-time release, intrabar occupancy and duplicate cross-symbol keys. 32 tests PASS in CI. No changes to frozen strategy parameters or the portfolio execution engine.

## Data / exact results
Committed unchanged cached 1H SHA256: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`. Same contiguous common calendar (ETH standalone N128 vs historical full-cache N129 because this audit restricts to common calendar; do not treat as missing fill).

| Asset | Frozen standalone N | Isolated portfolio N | Exact matching signal IDs | Matched economic fill mismatches | Standalone-only | Portfolio-only |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 130 | 137 | 125 | **0** | 5 | 12 |
| ETH | 128 | 136 | 121 | **0** | 7 | 15 |
| ICP | 132 | 138 | 112 | **0** | 20 | 26 |

Every standalone-only entry occurred while the isolated portfolio already held a position; every portfolio-only entry falls inside the standalone's prior position or its exit-bar cooldown. The standalone loop resumes signal inspection at exit_index+1; the event-driven portfolio may act on the signal formed at the exit-bar close and enter at the following open. These are **different valid scheduling policies**, so naive N/PF comparisons are not same-cohort comparisons. All five separate historical windows also show **zero matched economic fill discrepancies**.

Cross-asset competition, **isolated portfolio → multi-symbol portfolio** at 15bp/0 funding: BTC N137→123 (114 exact shared signals), ETH N136→97 (84 shared), ICP N138→89 (73 shared). There are both isolated-only and multi-only signals due to changed subsequent re-entry opportunities, not simply a one-way filter. Combined multi-symbol baseline N309; the portfolio report has already shown that at 15bp/3bp adverse synthetic funding its edge is marginal. These results are NOT fresh independent OOS.

## Limitations / decision
- **P0 #12 partial**: parity verified for matched 15bp/0-funding trades and inspected five windows; no exhaustive historical *gap-at-open with competing signal* count, no per-signal admission-reason trace for multi-symbol skipped IDs, and no before/after **15/25/40bp × 0/1/3bp funding** ledger reconciliation. Current category labels are causal diagnostics, not exact venue fill evidence.
- Standalone and portfolio differ by entry scheduling; do not compare their PFs as if trades were paired. The report contains exact IDs and bounded examples; per-symbol isolated risk-sized returns are not equivalent to full-notional standalone returns.
- Venue/market provenance, direct 4H same-venue parity, actual funding, spread/impact and immutable forward receipt data still missing. All five historical windows were previously examined; chronological non-overlap does **not** make them independent holdouts.
- No candidate is promoted. No real orders or API trades.

## Concrete questions / proposed next researcher iteration for manager
1. Should the canonical benchmark adopt **event-driven next-open scheduling** (portfolio policy), while retaining standalone cooldown as a separate named legacy baseline? The current two definitions are not directly comparable even with identical stop/TP.
2. Finish #12 by instrumenting per-signal admission decisions and historical gap-open competing-signal census; reconcile full 15/25/40bp × 0/1/3bp synthetic funding grids and exact trade IDs with the frozen portfolio report. Keep assumptions explicit.
3. Then prioritize #13 matched forming-4H vs closed-4H event streams with **4H ATR** for both, identical risk/exits/costs and fixed ratio<=0.7 *exploratory* filter. Do not reuse inspected final-quarter as independent test. No strategy promotion without new sealed forward receipts.

---

# DeltaRSI researcher handoff — cycle 7, 2026-10-27 MSK (P0 #12 gap-open chronology + fee notional; passive benchmark)

**Decision: P0 #12 PARTIAL, CHRONOLOGY FIX VERIFIED; NO STRATEGY PROMOTION / NO REAL ORDERS.** Latest CI [40408693880](https://github.com/VulpreS/Deltarsi1/actions/runs/40408693880) **SUCCESS (43 regression tests)**, producer commit `bb0dc5578bbff45e4636f88c15e7eabf47b1edb4`, code with passive summary `48e4ff8396a009755c22de7d3cc1781108e16d71`, report commit `806eecb`. Cached-only `reports/portfolio_risk_audit.json`; no candle downloads or live orders.

## Hypothesis and manager tasks read first
Reviewed current manager issues [#12](https://github.com/VulpreS/Deltarsi1/issues/12) (P0), [#13](https://github.com/VulpreS/Deltarsi1/issues/13) (P1), [#9](https://github.com/VulpreS/Deltarsi1/issues/9), [#8](https://github.com/VulpreS/Deltarsi1/issues/8), previous handoff cycle 6 and manager directives. **P0 hypothesis:** prior `portfolio_risk_audit.simulate` processed opening gap-through-stop only after admitting new trades, incorrectly occupying a position slot and stop-risk budget; its exit fee also used ENTRY notional rather than execution notional. A second predeclared diagnostic compares same-calendar 0%-cash and equal-weight buy-and-hold to the frozen portfolio (NOT risk-matched).

## Changes / reproducibility
- `portfolio_risk_audit.py`: added `resolve_open_gap` with no high/low/close access. At each UTC 4H open, settle existing `reverse_pending` exits, then existing adverse stop gaps **at open** and favorable target gaps conservatively **at target**; release positions and debit PnL/fees/funding before new signal admission. Only then size new entries with post-gap equity and existing stop risk. Intrabar high/low stop-first remains AFTER entries. This prevents using future OHLC to decide whether to admit a competing signal.
- Exit fee = `abs(quantity * exit_execution_price) * cost/2`, entry fee = entry notional * cost/2. Added per-trade `exit_notional`, corrected turnover to executed exit notional; funding still **synthetic adverse per UTC 8h event** on entry notional, not observed venue funding. No new strategy thresholds.
- Added `test_portfolio_open_order.py`: correlated simultaneous long stops and third-symbol admission, LONG+SHORT correlated gap, same-symbol immediate re-entry, opening target price-improvement convention, no intrabar-lookahead admission, cash/fee conservation, passive benchmark. Existing suites included. 43 tests pass.
- Added `passive_benchmarks` with 0% cash, 15/25/40bp price-only equal-weight long BTC/ETH/ICP buy-hold and per-symbol buy-hold over the **same calendar** and five disjoint windows. Benchmark is intentionally NOT matched to stop-risk/exposure of DeltaRSI. Added workflow serialization and race-safe report commit: report-only upstream updates no longer cause huge JSON rebase conflicts; if producer code changed, CI refuses stale publication.
- Inputs unchanged, committed 1H CSV SHA256: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`, ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`, ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`. Frozen baseline 2.5ATR stop / 3ATR target / max 12×4H, 0.25% equity stop risk/trade, max 2 positions, 0.5% aggregate risk; ETH challenger remains retrospectively selected OB-proxy/6ATR/opposite-unfiltered-turn.

## Results: chronological but previously inspected history, NOT independent OOS
Full common year at **15bp round-trip friction + synthetic 3bp adverse funding per 8h event**:

| Metric | Prior engine cycle 6 | Corrected engine cycle 7 |
|---|---:|---:|
| Baseline trades | 309 | 309 |
| Baseline net portfolio return | +1.7492% | **+1.7528%** |
| Baseline PF | 1.0696 | **1.0697** |
| Baseline close-to-close MTM max DD | 3.3687% | **3.3683%** |
| Challenger trades | 281 | 281 |
| Challenger net return | +1.0682% | **+1.0711%** |
| Challenger PF | 1.0460 | **1.0461** |
| Challenger max DD | 3.4519% | **3.4507%** |

No changes in full-history executed N, asset N or skipped-signal counts at printed precision; **do not claim exact trade-ID parity yet**. The tiny change in historical returns is primarily consistent with exit-notional fee correction and consequent position sizing. The opening-gap admission bug is demonstrated by deterministic fixtures, but a historical competing-gap opportunity count has NOT yet been independently reconciled. No claim of improved trading edge.

Corrected baseline per asset at 15bp/3bp: BTC N123 PF1.1084, ETH N97 PF1.3453, ICP N89 PF0.7475. Challenger BTC N136 PF1.2259, ETH N19 PF1.9554, ICP N126 PF0.7760; different cohorts under portfolio competition. Five disjoint windows baseline return: **−0.1478%, −0.6350%, −0.5189%, −0.0285%, +2.6087%**; challenger **−0.5485%, −0.6683%, +0.7957%, −0.3573%, +1.4031%**. Four of five baseline windows negative under conservative funding stress; all windows previously inspected.

Same-calendar 15bp **price-only buy-and-hold** (0 funding, 100% long exposure): equal-weight BTC/ETH/ICP **−30.9018%**, close-to-close max DD **66.2102%**; BTC −29.3764%, ETH −42.8127%, ICP −20.5163%; cash 0%. The very different exposure, risk budget and no-funding assumptions make this **context, not matched-risk evidence of alpha**.

## Limitations / critical blockers
- **P0 #12 still PARTIAL:** same-symbol standalone parity adapter and exact entry/exit trade-ID diff versus frozen #6/#7 remain undone; open-gap historical event count not yet enumerated. Synthetic target-gap fill assumes target price despite better open, which is conservative. Real exchange mark-price, liquidation, funding and slippage unknown.
- **P1 #13 NOT DONE:** forming-vs-closed 4H benchmark currently uses 1H ATR and mismatched scheduling/funding versus frozen 4H baseline; its historical best cells cannot be compared as if matched. Do not optimize on inspected final quarter.
- 5 chronological nonoverlapping windows were previously seen during selection, so NOT independent out-of-sample. No prospective immutable receipts; exchange/spot-perp provenance and direct same-venue 4H OHLCV absent. Funding rates and 15/25/40bp fees are scenario assumptions, not observed venue economics.
- Two overlapping CI report writers caused transient rebase conflicts (runs 40408498707 and 40408611884) **after tests and calculation succeeded**; workflow commit logic corrected, latest CI 40408693880 SUCCESS. Do not mistake those earlier CI failures for model/test failures.

## Conclusion and concrete next manager decisions
1. Accept #12 opening-gap-before-admission and exit-notional fee changes as **verified by fixtures and CI**, but keep #12 OPEN until exact historical trade-ID parity and gap-cohort audit, and 15/25/40bp × 0/1/3bp before/after ledger reconciliation are published.
2. Next researcher cycle: implement per-symbol **standalone parity adapter** with canonical `feature_walkforward.sim` / `p0_gap_audit` at 15bp/0 funding, classify every missing entry (capital/notional cap, competing symbols, terminal, warmup), report entry and exit key diffs. Add explicit historical count of openings that crossed stop/target and competed with new signals. Do not retune.
3. Then #13: reconstruct matched forming-vs-closed 4H opportunities with explicit 4H ATR, matched risk and funding; publish negative controls, three inspected regimes and block CIs. No strategy promotion without prospective sealed data.
4. Keep #5 venue/forward provenance **BLOCKED**; actual exchange/market, direct 4H parity, actual funding and append-only receipt-time forward data remain prerequisites. **No live orders.**

---

# DeltaRSI researcher handoff — cycle 6, 2026-10-26 (P1 #8 chronological risk-sized portfolio)

**Decision: #8 PARTIAL IMPLEMENTATION + HISTORICAL STRESS VERIFIED; NO NEW STRATEGY PROMOTION.** CI [40400104053](https://github.com/VulpreS/Deltarsi1/actions/runs/40400104053) SUCCESS; producer SHA `9923788c9b892e766271ba6b2154a7001ea95afd`; deterministic seed 20261026; strategy/config hash `6922fb45e5dc090035e7ba90fcf335886f7d278567bae52368e810dcfcb2f0e1`. Report [reports/portfolio_risk_audit.json](https://github.com/VulpreS/Deltarsi1/blob/main/reports/portfolio_risk_audit.json). **All data were previously inspected, no independent OOS. No real orders, no new candle downloads.**

## Hypothesis and manager priorities read
Read open issues #8 (P1 chronological portfolio), #6 (paired ETH exit and funding), #5 (venue/forward), #4 (execution) and `reports/manager_directives.md`, `reports/research_handoff.md`, `reports/matched_exit_audit.json`, `reports/p0_gap_audit.json` BEFORE implementing. Hypothesis: historically positive full-notional pseudo-PF is overstated once simultaneous signals, stop-risk sizing, synthetic adverse funding and realistic fees are applied; ETH OB-proxy/raw-reverse challenger may not improve *executable* portfolio results. Frozen benchmark is 2.5 ATR stop / 3 ATR target / 12 completed 4H bars BTC+ETH+ICP. Single retrospective challenger changes ETH to OB proxy 2.5/6/12 and raw opposite DeltaRSI exit at next open. HYPE excluded as directed.

## Changes and reproducibility
- Added `portfolio_risk_audit.py`: independent chronological event-driven scheduling (not fixed-cohort pseudo-compound), strict completed UTC 4H cached 1H bars; each entry at following open, max 2 positions, no same-symbol overlap, deterministic priority BTC→ETH→ICP, initial stop risk <=0.25% current marked equity per entry and aggregate <=0.50%, stop-distance sizing, <=2x gross notional and <=1x per symbol, fee-affordability guard, invalid ATR/price rejection. Stop-first same-bar, adverse stop-gap open fills, reverse at next open, max-12-bar time exit, terminal liquidation, mark-to-market equity snapshots. Strict contiguous common 4H grid; fail closed on missing interior bucket.
- Stress grids **15/25/40 bp total round-trip fee+slippage** × **0/1/3 bp adverse synthetic funding per UTC 8h event**, with conservative *upper* exposure bound for intrabar stops/targets. Funding is NOT observed venue funding. Cash debits half fee at entry, half at exit; realized gross PnL/funding at exit, unrealized close-to-close marked with conservative accrued funding. The report contains per-trade timestamps, exit-time bounds, quantity, price, stop, target, fees, funding bounds, stop-risk, initial and bar-close-marked equity, config hash, plus 5 contiguous nonoverlapping windows and a full-history sequential run.
- Added `test_portfolio_risk_audit.py` with deterministic 3 competing signals, 2-position/0.5% cap, long/short gap beyond stop, simultaneous correlated stops, 8h boundary, fees, early exit/reentry, leverage cap, terminal liquidation/cash accounting, missing 4H bucket; CI also runs prior execution, aggregation and matched-audit tests. Workflow `.github/workflows/p1-portfolio-risk.yml` uses only committed `data/*_1h.csv` and commits the JSON.
- SHA256 input caches: BTC `444d07cc16e428aac22355db2e5423b58bd10cdaa621713a40a6b6233297c7ea`; ETH `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; ICP `1a04cc428aa1d27a420cd5efc6c41f13640ea20a436740022c1adb07c6fe728b`. No new download.

## Results: historical descriptive, no independent validation
One continuous common 4H period, approximately 2025-10-26 through 2026-10-26, at **15bp fees + 3bp adverse funding/8h**:
| Metric | Frozen baseline | ETH OB + raw reverse challenger |
|---|---:|---:|
| Executable trades | 309 | 281 |
| Net portfolio return | **+1.7492%** | +1.0682% |
| Net profit factor | **1.0696** | 1.0460 |
| Win rate | 50.49% | 51.60% |
| Mean net R/trade | +0.0233 | +0.0159 |
| Max close-to-close MTM drawdown | 3.3687% | 3.4519% |
| Worst calendar month | Jan 2026: −1.8877% | Jan 2026: −2.2945% |
| Active-bar exposure | 75.51% | 71.81% |
| Missed max-2 signals | 194 | 57 |
| Missed same-symbol signals | 259 | 244 |
| Filtered ETH OB signals | n/a | 180 |

Full continuous baseline stress: **15bp/0 funding +4.7167%, PF1.1957; 15bp/3bp funding +1.7492%, PF1.0696; 25bp/3bp funding −0.3432%, PF0.9868; 40bp/3bp funding −3.4018%, PF0.8745.** Challenger corresponding returns **+3.6754%, +1.0682%, −0.7611%, −3.4436%**. Funding assumption dominates the marginal apparent edge. Fee and funding stresses are synthetic, not realized market costs.

Five disjoint chronological windows at 15bp/3bp (baseline vs challenger net portfolio return):
1. 2025-10-26→2026-01-07: **−0.1475% vs −0.5484%** (N 37/32).
2. 2026-01-07→2026-03-21: **−0.6367% vs −0.6702%** (N 69/65).
3. 2026-03-21→2026-06-02: **−0.5194% vs +0.7951%** (N 67/62).
4. 2026-06-02→2026-08-14: **−0.0294% vs −0.3587%** (N 65/59).
5. 2026-08-14→2026-10-26: **+2.6085% vs +1.4041%** (N 71/63).
Only the final window is positive for the baseline under conservative stress. All five windows were already inspected during previous optimization: **they are NOT sealed OOS despite chronological non-overlap.**

By asset, continuous baseline N/PF: BTC **123/1.1083**, ETH **97/1.3453**, ICP **89/0.7474**; challenger BTC **136/1.2258**, ETH **19/1.9549**, ICP **126/0.7760**. Changes to BTC/ICP cohorts under ETH challenger arise from cross-asset competition and re-entry scheduling, not BTC/ICP parameter changes.

## Reconciliation to previous audits and limitations
- Previous strict standalone baseline reported BTC N130 PF1.3377, ETH N129 PF1.3230, ICP N132 PF1.1465 (15bp/0 funding, sequential single-symbol full-notional). **Not comparable numerically** with 309 combined trades at 15bp/3bp risk-sized capped portfolio. This run applies concurrency priority and risk sizing, and includes funding. Differences in N are expected because a trade can be skipped when two other symbols occupy slots. For precise parity, compare per-trade UTC signal/entry keys under identical zero-funding, unconstrained single-symbol assumptions before claiming an engine discrepancy.
- Earlier ETH matched selected-OB cohort N43, reverse vs fixed paired net +0.1787 pp with 95% CI including zero. Current challenger **19 ETH trades** due to ETH OB filter, common-period/cross-asset scheduling, two-position cap and different re-entry opportunity; cannot infer causal exit improvement by comparing N43 with N19.
- Max DD is **4H close-to-close marked**, not intrabar worst-case; actual adverse gaps, mark-trigger liquidation, correlated stress, financing and execution impact can exceed the modeled initial stop risk. Simultaneous synthetic adverse gaps demonstrate realized losses can exceed 0.5% aggregate intended stop risk.
- Costs and UTC 8h funding events are assumed, no actual venue funding/mark prices, exchange provenance, same-venue direct 4H parity or BTC/ICP/HYPE 1H volume. Common-bar boundary reset in five-window studies forces terminal liquidation and loses cross-window entry opportunity. Full continuous run is primary portfolio view.
- There is no independent forward sample, no statistical significance claim, and no strategy approval. HYPE remains excluded.

## Conclusion / concrete manager questions and next iteration
1. **#8 P1 PARTIAL/DONE for cached synthetic portfolio engine, NOT venue-realistic validation.** Review report and verify entry/exit key parity versus #7 and #6; independently challenge accounting and concurrency ordering before considering this code canonical.
2. **#8 NEXT:** add a deterministic same-cohort/single-symbol parity adapter to reconcile all BTC/ETH/ICP trades exactly with strict #7 at 15bp/0 funding, then compare portfolio return/DD to a buy-and-hold or cash baseline on the identical calendar range. Add explicit intrabar adverse MFE/MAE/DD bounds, correlated gap sensitivity, venue-specific notional/margin/mark-price checks.
3. **#5 BLOCKED:** source venue/perpetual provenance, actual funding timestamps/rates and same-venue 4H OHLCV remain unavailable. Request signed source manifest, then register an append-only forward shadow ledger with strict receipt times after freeze, >=90 days and >=50 independent executable trades before an inference. Do not backfill forward data.
4. **Decision:** challenger does **not** outperform frozen baseline as an executable portfolio in the examined history; do not promote or deploy. No real orders.

---

# DeltaRSI researcher handoff — cycle 5, 2026-10-26 (P0 #6 funding timing + NET paired CI)

**Decision: P0 #6 FUNDING TIMING / NET PAIRED AUDIT DONE for synthetic cached scope; #6 PORTFOLIO and #5 VENUE/FORWARD still OPEN. NO STRATEGY PROMOTION, NO LIVE ORDERS.** CI [40390672109](https://github.com/VulpreS/Deltarsi1/actions/runs/40390672109) **SUCCESS**, producer SHA `8bc3b8e67e68935f52f8eb9ebdb225f96a2acf00`, deterministic seed `20261026`, 2,500 bootstrap draws. Report: [reports/matched_exit_audit.json](https://github.com/VulpreS/Deltarsi1/blob/main/reports/matched_exit_audit.json).

## Hypothesis / priority
Read manager directives and current issues #7, #6, #5, #4 plus previous handoff before implementing. Priority #6: fixing last-bar-close exposure duration and using actual UTC 00/08/16 funding-event **bounds** (rather than `ceil(hours/8)`) may alter matched ETH fixed-vs-raw-reverse NET attribution. Predeclared ETH OHLC OB proxy 2.5 ATR stop / 6 ATR target / 12×4H max; same fixed-scheduled 43 entry IDs. Historical data already inspected and OB chosen retrospectively — **NOT independent OOS**.

## Changes / reproducibility
- Added `funding_timing.py`: exact UTC 00/08/16 event counting on (entry,exit), (entry,exit], lower/upper bounds for OHLC-intrabar stop/TP and funding-boundary ordering. Excludes funding at entry timestamp; assumes entry just after same-timestamp settlement. Actual exchange settlement ordering UNKNOWN.
- Corrected `matched_exit_audit.exit_one` time exit to final 4H candle **close**, not candle open; intrabar stop/TP exposure interval = [bar open, bar close]; raw reverse/structure next-open exit remains exact. Emits `hours_min/max`, `funding_events_min/max`, UTC entry and exit bounds per trade.
- `net` uses event counts, not `ceil(hours/8)`. `bootstrap_delta` now resamples **paired net return deltas** in 30-day calendar blocks. Explicit 15/25/40bp total fee+slippage × 0/1/3bp adverse *synthetic* funding × min/max timing grid for primary ETH; matched fees cancel algebraically for identical-entry cohorts with equal per-trade cost.
- Expanded `test_matched_exit_audit.py`: 1/2/3/12-bar time exits (old 0h/44h bug fails), UTC 00/08/16 boundaries, boundary uncertainty, LONG/SHORT intrabar stop, next-open reverse, stop-first, four-block NET bootstrap. CI workflow now also runs `test_p0_execution.py` and `test_completed_candles.py` and triggers when `funding_timing.py` changes.
- Uses **only** committed `data/*_1h.csv` caches; no downloads, no orders. Source ETH CSV SHA256 `9c16b69b2232705bb303fdb153cba6e92417d7ac9493873dcae523636e36d866`; strict completed-4H aggregation, report contains all four source hashes, producer SHA, CI run, UTC freeze cutoff, seed, cost assumptions and per-asset chronological slices.

## Results — historical matched cohort, NOT independent
ETH selected OB same **N=43** entry IDs; 15bp assumed total round-trip fee+slippage, **0bp** funding: fixed net mean **+0.8666%/trade**, PF **1.8212**, win **58.14%**; raw opposite DeltaRSI net mean **+1.0453%**, PF **2.0988**, win **60.47%**. Paired NET delta **+0.1787 percentage points**, 30-day block-bootstrap 95% CI **[-0.0202,+0.4321] pp** across **12 calendar blocks**. CI **includes zero**.

At 15bp total fee+slippage **plus 3bp adverse funding per 8h UTC event** using **conservative max exposure bound**: fixed net mean **+0.7110%**, PF **1.6386**, win **53.49%**; raw reverse **+0.9064%**, PF **1.9073**, win **55.81%**. Paired NET delta **+0.1955 pp**, 95% block CI **[-0.0078,+0.4572] pp**, **still includes zero**. Conservative min timing-bound ETH mean net fixed +0.7284%, reverse +0.9267% at 3bp stress. The reverse's lower assumed funding exposure explains why stressed paired delta is larger, not evidence of a reliable advantage. At 40bp fixed cost, zero funding: fixed PF **1.5284**, reverse PF **1.7521**, but paired CI remains unchanged because equal per-trade costs cancel.

Strict aggregation baseline at 15bp/0 funding, frozen 2.5/3/12 config: BTC N130 PF1.3377; ETH N129 PF1.3230; ICP N132 PF1.1465; HYPE N69 PF0.7889. All frozen raw-reverse historical paired bootstrap CIs include zero. No strategy upgrade is statistically established. Selected-cohort pseudo-equity/DD are **not executable portfolio DD**.

## Limitations / blockers
1. Real funding rates, settlement timestamps, exchange and market-type provenance, spreads, mark-price trigger, direct same-venue 4H OHLCV, BTC/ICP/HYPE 1H volumes: **UNKNOWN/BLOCKED**. Funding assumptions are synthetic adverse cost; do not claim they equal exchange funding.
2. `p0_gap_audit.metrics` still uses `ceil(bars/2)` as a coarse stress proxy; this **is not equivalent** to the new exact UTC event-count bounds. Never compare its stressed PF numerically with this matched audit without reconciling definitions. Baseline gross and 0-funding costs are unaffected.
3. ETH OB cohort was selected on previously inspected data, and cohort is determined by fixed-exit scheduling. The paired bootstrap is descriptive; cannot correct selection bias, 12 blocks are few, and reverse's earlier re-entry opportunities are deliberately excluded. The five chronological non-overlapping slices are NOT sealed independent holdouts.
4. No separately executable cross-asset portfolio, 0.25% equity stop-risk, max two simultaneous positions/0.50% aggregate risk, mark-to-market DD, worst month or realized funding. No post-cutoff immutable forward receipts.

## Conclusion / concrete manager questions for next cycle
1. **#6 P0 synthetic timing + NET CI DONE.** Review code/report and confirm UTC settlement-event convention; request venue-specific funding/mark prices before replacing stress with realized economics. Do not promote ETH reverse: both primary CIs include zero.
2. **#6 P1 NEXT:** implement independent executable chronological portfolio with re-entries and 0.25% initial-stop equity risk per position, max two concurrent, <=0.50% aggregate stop-risk, 15/25/40bp cost stress, mark-to-market DD and worst monthly loss. Compare frozen baseline with one preregistered challenger, without selecting on final quarter.
3. **#6 accounting NEXT:** replace/reconcile `p0_gap_audit.metrics` coarse `ceil(bars/2)` funding proxy using shared UTC event-count bounds, retaining explicit legacy-vs-new report. Test 00/08/16 starts, stop/TP uncertainty, long/short.
4. **#5 BLOCKED:** signed venue/market provenance, same-venue direct 4H parity and real funding unavailable. Pre-register immutable forward shadow receipts and minimum >=90 days / >=50 independent executable trades per candidate; no backfill labeled forward.
5. **No orders, no production, no claim of independent reproducible edge.**

---

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
