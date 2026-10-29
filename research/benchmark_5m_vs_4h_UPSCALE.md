# Benchmark: 5m vs 4h vs combined — Upscale

Status: specification; NOT a completed backtest.

## Common simulation
- Initial equity: 5000 USDT, no leverage assumed unless explicitly configured.
- Instruments: BTCUSDT and ETHUSDT; use identical UTC start/end for all modes.
- Evaluation window: most recent 30 complete calendar days for which 5m and 4h OHLCV both exist; record exact dates.
- Historical warmup before evaluation required for all indicators; do not count warmup trades.
- Modes: 5m-only, 4h-only, combined (shared portfolio and capital).
- Capital in positions <= 60% of starting equity (configurable); no double counting shared capital.
- Fee: 0.08% of notional on entry and 0.08% on exit; spread: test 0.015% and 0.04% round-trip convention explicitly documented.
- Closed-candle signals only; earliest fill at next candle open with spread and fees. No lookahead.
- Stop/TP executed intrabar using high/low. If both hit on same bar, use adverse-first conservative convention; report ambiguous bars.
- Mark-to-market equity for drawdown, daily loss limits and total drawdown; include open positions.
- Upscale daily loss 5%, overall loss 10%; verify official reference equity and daily reset rules before claiming compliance.
- Challenge stage 1: +5% and >=3 distinct days with >=0.5% qualifying profit; stage 2: +8% and >=5 such days. Model phase transitions and reset assumptions explicitly.
- Separate optimization window from evaluation window. Do not select SL/TP on the same 30-day evaluation period.
- Strategy 4h: RSI(27) Wilder RMA; signal EMA(7) of RSI; DeltaRSI=RSI-EMA(RSI,7). Implement documented intensity shift entry/exit only after formal thresholds are verified. Do not silently invent thresholds.
- Strategy 5m: use existing RSI-based implementation and its exact parameters; preserve strategy identity. Verify executable code before benchmarking.
- Combined mode: same signals, deterministic order and position allocation; record collisions and capital contention.

## Required output per mode
- Dates and OHLCV source, sample coverage, missing bars, warmup.
- Trades, win rate, net PnL, fees, profit factor, average net trade, max drawdown, worst daily loss.
- Days to phase 1 and phase 2 (or 'not passed'), days >=0.5%, number of limit violations.
- Equity curve and daily equity CSV; individual trade CSV with signal/fill timestamps.
- Results for both spread scenarios; sensitivity to stop/target settings and out-of-sample stability.
- Explicit distinction between trade signal count and executed fills.
- No results may be labeled verified unless code executed on actual candles and reports generated.
