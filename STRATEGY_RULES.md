# DeltaRSI 4H Exhaustion — Research Candidate v0.1

Status: **PAPER TRADING ONLY**. This is not a validated profitable live system.

## Instruments and timeframe
- Trade ETHUSDT, BTCUSDT, ICPUSDT on 4-hour bars. HYPEUSDT is excluded: held-out results were negative for the selected logic and only ~5003 hours were available.
- Evaluate signals only on a fully closed 4-hour bar (UTC-aligned exchange candle).
- Only one position per instrument. LONG and SHORT are allowed. No averaging, martingale, or pyramiding.

## Exact indicator
1. SMA21 of close.
2. RSI12 via Wilder RMA of changes in SMA21.
3. EMA7 of RSI12.
4. Mirror RSI around 50: `rsi_mirror=min(rsi,100-rsi)`; same for EMA.
5. `delta=sign(rsi-ema)*abs(100*ln(rsi_mirror/ema_mirror))`.
6. Delta color classification as in `Delta` Pine file, threshold 60. Red = negative, blue = positive.
7. Signal LONG: **previous 4H bar mediumR, current closed 4H bar weakR**. Signal SHORT: **mediumB -> weakB**. No separate RSI threshold or divergence filter.

## Execution
- Entry: **next 4H bar open**, not on the signal bar.
- ATR14 Wilder, calculated on closed signal bar; risk distances based on signal ATR.
- Initial stop: 2.5 ATR from entry, adverse direction.
- Take profit: 3.0 ATR from entry, favorable direction.
- Time exit: at the close of the 12th 4H bar after entry (48 hours).
- First of stop, target, or time exit. If both stop and target touched within same bar, assume **stop first**.
- Assumed round-trip cost: 0.15% of notional (0.11% taker fees + 0.04% slippage). Funding and exchange-specific constraints NOT modeled.
- Signal cannot be filled retroactively: stale alerts must be skipped.
- Risk for paper trading: **0.25% of account equity per stop**. `quantity=(equity*0.0025)/(2.5*ATR)`, then cap notional exposure to 1x equity per instrument and comply with exchange quantity/precision/minimums. Never size positions using leveraged buying power alone.
- Portfolio cap: max 0.75% of equity risk across simultaneous stops; daily realized loss cap 1% and equity drawdown circuit breaker 5% from peak, both are **untested operational safeguards**, not backtested improvements.

## Backtest evidence (2026-10-26)
One-year ETH/BTC/ICP 1H data resampled to 4H. First 70% train, last 30% untouched. No overlap on same instrument. Holdout on ETH/BTC/ICP combined: 125 trades, 51.2% profitable, +0.422% mean return/trade, PF 1.374. By asset: ETH 44 trades PF 1.50; BTC 44 PF 1.19; ICP 37 PF 1.41. Full four-asset holdout including HYPE: 148 trades, PF 1.187, +0.246% mean; HYPE alone 23 trades, PF 0.695, -0.713% mean.
Training on three assets (earlier run): 276 trades, 54.7% wins, +0.452% mean, PF 1.271.
Daily alternatives: too few trades, unstable. Strict wave divergence detection: no qualifying signals under current implementation, NOT validated.
Caveats: 0.15% friction estimate, no funding, no partial fills, no mark-price liquidations, no exchange outage handling; selected instruments after observing holdout introduces selection bias. Need a fresh forward paper period and broader out-of-sample years before deploying capital. The reported mean returns are not account returns. Max drawdowns are material and the naive full-notional backtest is not safe for leveraged deployment.

## Operational deployment gates
1. Verify indicator outputs bar-for-bar against TradingView on at least 30 sampled bars per symbol.
2. Paper trade 50+ consecutive fresh signals over multiple regimes, record fills/funding/slippage.
3. Re-run on an untouched forward period without changing parameters.
4. Only after independent validation consider exchange execution with explicit user authorization, keys held in secure secret storage, idempotent orders, mark-price stops, kill switch, persistent state, retries, and reconciliations. No live orders are implemented.

## Reproducibility
- Cached CSV: `data/ETHUSDT_1h.csv`, `data/BTCUSDT_1h.csv`, `data/ICPUSDT_1h.csv`, `data/HYPEUSDT_1h.csv`.
- Backtest script: `research_multiasset.py`.
- Machine-readable report: `reports/multiasset_4h_1d_results.json`.
- Signal-only script: `paper_signal_4h.py`. It does not send orders or fetch live candles.
