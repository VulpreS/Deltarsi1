# Multi-agent operating agreement — DeltaRSI

## Roles and communication
- **Research agent (daily ~08:00 Moscow):** execute reproducible experiments, record assumptions and code, update research reports, answer open research issues.
- **Research lead (daily ~19:00 Moscow):** review results critically, prioritize issues, audit data leakage and risk, define acceptance criteria, decide what to test next.
- **Human owner:** approves capital allocation, exchange account connections, and any real-money deployment. Neither agent may autonomously authorize live orders.

These are separate scheduled ChatGPT tasks, **not** continuously communicating AI processes. Shared state lives in GitHub commits, issues, and reports. No direct agent-to-agent messaging or perpetual runtime is assumed.

## Research decision loop
1. Lead opens or prioritizes one falsifiable hypothesis with baseline, metric, costs, and frozen evaluation design.
2. Researcher implements and runs experiment using existing OHLC and volume cache; append only missing data.
3. Researcher commits machine-readable results, error logs, and method notes; no cherry-picked charts.
4. Lead checks leakage, sample size, cross-asset and regime consistency, parameter neighborhoods, funding/slippage sensitivity and worst drawdown; reject if invalid.
5. Promote only to **paper candidate** after a new, previously unseen chronological evaluation. Compare against frozen Candidate B and buy-and-hold/cash benchmarks.
6. Paper trading needs reproducible signal parity, actual exchange fees/funding and order execution simulation.
7. Production requires explicit human approval, API credential management, idempotent orders, stop orders, kill switches, reconciliation, monitoring and rollback. Research bots must never send live orders.

## Immediate priority queue
P0: Reconcile indicator calculation with TradingView, UTC 4H candle alignment, volume source consistency, and signal timing. Verify no look-ahead.
P0: Backtest funding/fees/slippage and portfolio drawdowns with correlated BTC/ETH/ICP positions; test stop-gap assumptions.
P1: Create incremental forward data cache, sealed prospective evaluation, and paper trade ledger.
P1: Compare exit logic 48h vs 72h vs 5/7/10 days under the *same entry cohort*, not just non-overlapping backtests.
P2: Research alternative regimes (trend/momentum/volatility/volume), only after P0 passes.

## Promotion gates
- Sufficient new independent trades and calendar time across market regimes, not only 30-50 clustered trades.
- Positive net expectancy after conservative costs, with uncertainty intervals, portfolio max drawdown and exposure limits.
- No significant collapse when perturbing stop/target/hold/volume threshold.
- Forward paper results broadly consistent with research, execution parity verified.
- Human sign-off required for any real-money production step.
