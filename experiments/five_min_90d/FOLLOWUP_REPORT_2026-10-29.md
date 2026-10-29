# Eight-asset DeltaRSI: 5m vs 15m execution follow-up (2026-10-29)

## Reproducibility
- Successful GitHub Actions run: https://github.com/VulpreS/Deltarsi1/actions/runs/40883171664
- Code SHA: `e05d02ef6d2d66cdde87366b0393cf0c3aff0a57`
- Artifact: `eight-asset-5m-15m-oos` / `followup_execution_results.json` (full structured results, 84 comparison cases + 48 stress cases)
- Script: `experiments/five_min_90d/followup_execution.py`
- Execution engine: `experiments/five_min_90d/run.py`
- Signal ID: `experiments.pine_vs_codex.run.pine_events` (unchanged; 4h closed signals)
- Universe: BTC ETH ICP TON BNB ZEC XRP LINK (8), one $5,000 account (max 3 positions), separate two-account/BTC-ETH comparisons.
- Binance USD-M 5m OHLC (five monthly ZIP archives per asset), 15m aggregated from same 5m source.
- Dates UTC: 2026-04-02—2026-07-01 (90d); train first 60 days, OOS 2026-06-01—2026-07-01 (30d).
- Position sizing: fixed $1,000 notional, not 10–15% margin allocation.

## Main results: one account, eight coins, 5m
| Scenario | Full 90d phase 1 | Full 90d phase 2 | 30d OOS phase 1 | Full DD | Trades (full) | Full WR | Full PF |
|---|---|---|---|---:|---:|---:|---:|
| Legacy baseline ATR SL/TP, 48h, no BE | day 71 | not passed | day 21 | 4.858% | 55 | 70.91% | 2.440 |
| Selected ATR SL/TP, common BE+1%, 48h | day 60 | not passed | not passed | 3.146% | 70 | 25.71% | 6.910 |
| Selected per-coin SL/TP, BE, hold | day 21 | day 67 (46 days after phase 1) | day 22; phase 2 not passed | 3.650% | 64 | 54.69% | 6.879 |
| Selected per-coin, stop CLAMP to <=5% of entry price | day 21 | day 67 | day 22; phase 2 not passed | 3.569% | 64 | 54.69% | 7.051 |
| Selected per-coin, REJECT trades needing >5% price stop | day 21 | not passed | not passed | 2.384% | 38 | 73.68% | 5.227 |
| Selected per-coin, fee 0.08%/side, spread 0.04% RT, CLAMP stop to 5% | day 21 | day 67 | day 22; phase 2 not passed | 3.689% | 64 | 53.12% | 5.290 |

- The per-coin 5m plan passes phase 1 on 2026-04-23 and phase 2 on 2026-06-08 in the modeled full 90d. This exceeds the owner's target of ~14 days.
- 15m execution (using 4h signals) gives the same phase dates, number of trades and essentially identical realized outcomes. Cost/funding and intrabar DD can differ slightly. **This is not a comparison to 15m signal generation.**
- The difference between legacy same-entry-bar profit-zeroing and deferred same-bar take was zero on the historical baseline, although the included synthetic sanity test detected the behavior.
- One $5,000 account on all 8 assets performed better for speed than BTC/ETH only or the two separately funded group accounts in this test. The first separate account A passed both phases only after 78 days, account B only the first, BTC/ETH only the first (81 days).
- At cost stress .0008 fee per side + .0004 spread RT, stop clamp 5%, modeled cumulative phase ledger profit is $947.31 (not the same as end NAV due to phase resets), no simulated breach.
- At low fee .00008 per side + .0002 spread RT, stop clamp 5%, modeled cumulative phase ledger profit is $1053.65; no simulated breach.
- **OOS qualification:** final independent 30d, per-asset stop clamp scenario achieved phase 1 on day 22 and did not achieve phase 2. Neither 5m nor 15m demonstrated both stages within the independent 30d period.

## Frozen per-asset parameters (SL/TP in 4h ATR multiples)
| Coin | SL | TP | BE trigger (price move) | Max hold |
|---|---:|---:|---:|---:|
| BTC | 2.5 | 2.5 | off | 48h |
| ETH | 1.5 | 2.5 | off | 48h |
| ICP | 2.5 | 2.5 | +1.5% | 72h |
| TON | 1.0 | 1.5 | off | 48h |
| BNB | 3.5 | 5.0 | off | 48h |
| ZEC | 1.5 | 2.5 | +1.5% | 72h |
| XRP | 1.5 | 2.5 | off | 48h |
| LINK | 2.5 | 2.5 | +1.0% | 48h |

## Important limitations and interpretation
1. These are model outcomes, not verified real Upscale challenge completions. The exact 60-second rule, account mark-price risk, 30% consistency, UTC phase accounting, execution, order fees and official Upscale tariff are NOT independently confirmed.
2. The mechanical Delta implementation `pine_events/CausalDelta` has NOT been fully audited against the original Pine mathematical body. Do not call this a different version of the user's indicator; do not change it silently.
3. Wick confirmation, waves, divergences, discretionary partial exits are not included.
4. Same 4h closed signal on all comparisons; 15m is an execution resolution only. Stop-first high/low on OHLC and synthetic aggregated 15m create execution ambiguity. Adverse 8-asset wick extremes treated as concurrent is conservative; 15m may under-detect drawdowns.
5. Funding is modeled as a positive charge every 8h; spreads as simple costs, no explicit additional slippage, fills in the original engine are only approximations.
6. Selected parameters were chosen on the first 60 days **in an earlier optimization study**. Full 90d is NOT independent. This follow-up did not retune OOS.
7. Prior engine incorrectly discarded same-entry-5m-candle profit. New implementation defers profitable exit to the next candle; this is a **proxy**, not 60-second-rule certification.
8. The phase ledger now handles end-of-window completion without double counting. Structured result shows stage-completion NAV and cumulative per-phase profit; avoid equating `net_pnl` with end equity after resets.
9. Price stop cap `reject` excludes entire signals whose stop would exceed 5%; `clamp` keeps signals but shortens stop to 5%. These are separate risk policies, not equivalent.
10. NO LIVE ORDERS PLACED. Before forward or live trade, require Pine parity audit, official Upscale compliance, slippage/fee calibration, account-risk unit tests, multi-period walk-forward and fresh data.

## Next hypotheses
- 4h signal unchanged: walk-forward per-coin configurations over additional time periods and genuine new regimes.
- Compare structural stop vs ATR and alternative exit logic, without fitting on OOS.
- Implement event-by-event phase accounting, 60-second event timing or 1m data, gap/slippage/funding sign and actual platform rules.
- Investigate whether +5%/8% with 3/5 qualifying profit days can be achieved inside 14–30 calendar days without breaches (current best full-period 67 days).
