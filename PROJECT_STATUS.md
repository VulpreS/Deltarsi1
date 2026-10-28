# PROJECT_STATUS.md — Upscale integration handoff
Updated: 2026-10-28

## Where we stopped
1. Selected Upscale prop firm, initially challenge stage, crypto instruments; bots/API and position carry allowed per user.
2. Planned account: demo $10,000 with API; eventual challenge $5,000. A previous read-only attempt at endpoint `/accounts/with-risk-status` returned HTTP 403. Cause and actual access remain unverified. No confirmed successful account connection, and no orders have been executed.
3. User wants an algorithmic strategy based primarily on DeltaRSI on 4h, with backtests using existing repository candles and GitHub Actions. A simplified three-wave peak/area event study was created, but is not sufficient to launch.
4. Last research result: 93 total events mixed 1h/4h, no demonstrated advantage; exact indicator parity and 4h segmentation remain open.
5. User subsequently discussed academic parallels of nonlinear RSI transformations; this is conceptual research, not deployment progress.

## Immediate next steps for Codex
- Inspect repo structure, Pine indicator, existing backtest files, data quality and current Actions.
- Confirm which DeltaRSI source/parameters are authoritative (versions conflict), then port Pine calculation bit-for-bit and unit-test against reference candles.
- Verify current Upscale API docs and challenge rules with user-provided official sources; diagnose 403 without exposing credentials; establish READ-ONLY account/balance/permissions checks first.
- Implement paper/dry-run execution with closed-candle signals and strict 5% daily/10% overall account-level kill switches, including equity and unrealized PnL as required by official rules.
- Backtest 4h-only BTC/ETH over user-preferred 30-day challenge horizon plus longer out-of-sample periods. Compare multiple strategies/filters and report drawdown, pass/fail of challenge, win rate, trade count, MFE/MAE and fees. Do not optimize solely to a two-week success anecdote.
- Only after explicit approval, move to demo trading. Never place live trades without separate authorization.

## Open decisions
- Official Upscale API documentation/auth/permissions and whether account is challenge/demo/funded.
- Exact current prop account size and margin allocation.
- Latest exact DeltaRSI formula and histogram intensity thresholds.
- Risk limits calculation, UTC reset, challenge day definitions, leverage/position caps.
- Paper execution first vs authorized demo trading.

See AGENTS.md for detailed strategy context.
