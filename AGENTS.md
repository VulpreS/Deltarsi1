# AGENTS.md — Context for Codex (2026-10-28)

Language: Russian. Project: DeltaRSI research, 4h strategy, and prospective Upscale prop-firm bot. This is a context handoff, NOT permission to trade.

## User's core indicator and discretionary logic
- Confirm exact Pine source/parameters before any backtest. Latest user-described DeltaRSI is RSI(27) RMA minus EMA(RSI,7), but prior versions used RSI SMA15, EMA88 and a nonlinear/log transform. Repo contains legacy implementations with DIFFERENT parameters. Do not silently treat them as equivalent. Identify authoritative Pine code and reconcile with user.
- Histogram positive/blue and negative/red, with bright/medium/weak intensity. Evaluate on CLOSED candles only.
- Main TF 4h, higher 1d, 1h for synchronization.
- Long entry: current negative/red histogram switches medium -> weak after exhaustion, ideally second/third wave and wick/rejection near local price extreme. Short symmetric. Bright phase not mandatory. Price may set a new low while DeltaRSI fails to set a new negative peak (divergence).
- User hypothesis: 2–4 same-side impulse waves, separated by corrections; decreasing peak magnitude across three waves suggests exhaustion; if third is stronger than second, fourth may follow. Distinguish peak amplitude, histogram area, average intensity and duration.
- Stop behind price extreme associated with strongest histogram phase; move stop to breakeven once underlying price moves +1% in favor; possible partial TP at liquidity levels; exits on opposite histogram medium -> weak, alternative exit on return of current color to medium; exceptional wick/spike exits.
- Test realistic fees (0.08% per side), spread 0.015–0.04%; funding generally omitted by user for initial tests.

## Upscale prop account context
- User chose Upscale over 21founded; crypto, bots/API allowed, overnight positions and news trading permitted per user understanding (verify actual current contract).
- Challenge restrictions: daily drawdown 5%, total drawdown 10%. Exact basis/reset time must be verified with prop rules, not assumed.
- User described a $10,000 demo account with API; earlier API call to /accounts/with-risk-status returned HTTP 403 (permissions/IP/read-only uncertainty). This is NOT a confirmed working trading connection.
- Plans included a $5,000 live challenge, 60% maximum capital deployed, BTC/ETH 30% each, maximum 3 simultaneous trades; other sizing ideas: $2,000 per position on $10k demo. Clarify latest allocation and how leverage, margin and prop drawdown interact before implementing.
- User described per-trade allocated margin 10–15% and stop at <=5% underlying move, NOT 10–15% equity loss; do not confuse these.
- Challenge targets reported by user: stage 1 +5% and 3 days >=0.5%, stage 2 +8% and 5 days >=0.5%; reset at 00:00 UTC; funded payout conditions to verify.
- Never place live or demo orders, store credentials, or turn on auto-trading without explicit user authorization. Start read-only API diagnostic and paper simulation. Never commit API keys, tokens, secrets, account identifiers or raw authenticated responses.

## Existing GitHub research
- Repo has historical candle CSVs in data/; do not redownload unnecessarily.
- Experimental script deltarsi_wave_peak_area_study.py and workflow .github/workflows/deltarsi-wave-peak-area.yml. Auto-runs on push; latest previously successful run 40696905046.
- Initial study: 93 wave events pooled BTC/ETH/ICP/TON and 1h/4h; 50 fading peaks, 43 third-rebound. Tiny subsamples and no validated predictive advantage. Crucially it uses legacy indicator and simplistic sign-segment wave labeling; NOT an exact test of the user's indicator/rules. Do not present these findings as a definitive falsification or validation.
- Next research: verify indicator parity, 4h-only tests, 10–40 candles, event-based MFE/MAE, realistic risk and challenge-level drawdown, out-of-sample/walk-forward, compare nonlinear DeltaRSI to plain RSI-EMA histogram.

## Working practices
- Read current repository files and workflows first; avoid duplicating existing code.
- Closed-candle and lookahead-free backtesting; account for overlapping trades, commissions, spread, timezone, funding assumptions, liquidation and prop limits.
- Provide reproducible GitHub Actions outputs, summaries, failures and links; don't invent backtest results.
- Communicate in Russian. Ask for missing API documentation and permissions rather than guessing endpoint behavior.
