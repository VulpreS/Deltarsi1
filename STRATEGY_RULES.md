# DeltaRSI 4H Exhaustion — Research Candidate v0.1

Status: **PAPER TRADING ONLY**. This is not a validated profitable live system.

## Instruments and timeframe
- Paper trade ETHUSDT, BTCUSDT, ICPUSDT on 4-hour bars. Monitor HYPEUSDT in research-only mode: only ~5003 hours were available and holdout result is slightly negative.
- Evaluate signals only on a fully closed 4-hour bar (UTC-aligned exchange candle).
- Only one position per instrument. LONG and SHORT are allowed. No averaging, martingale, or pyramiding.

## Exact indicator
1. SMA21 of close.
2. RSI12 via Wilder RMA of changes in SMA21.
3. EMA7 of RSI12.
4. Mirror RSI around 50: `rsi_mirror=min(rsi,100-rsi)`; same for EMA.
5. `delta=sign(rsi-ema)*abs(100*ln(rsi_mirror/ema_mirror))`.
6. The **chosen revised signal** does not depend on color threshold 60. It uses histogram magnitude: `abs(delta[k]) < abs(delta[k-1])`, `abs(delta[k-1]) >= abs(delta[k-2])`, and `abs(delta[k-1]) >= 15`.
7. Delta at k and k-1 must have the same sign. LONG when delta[k] is negative; SHORT when positive. This catches the first weakening after a local impulse peak. No separate RSI threshold, divergence, or trend filter. The previous medium->weak color transition is retained as a comparator, not the primary rule.

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

## Backtest evidence (2026-10-26, corrected split isolation and 12-bar exit)
One-year ETH/BTC/ICP 1H cached data resampled to 4H. HYPE covers ~5,003 hours, April–October 2026. First 70% train per instrument, last 30% evaluated independently; training has a hold-length embargo before the boundary. One position at a time per instrument; 0.15% round-trip fees and slippage.

**Chosen 4H local-peak weakening rule (turn):** train 339 trades, win 53.1%, mean +0.249%/trade, PF 1.139; held-out 154 trades, win 51.3%, mean +0.337%, PF 1.266. Held-out by asset: ETH 43 trades PF 1.625; BTC 43 PF 1.655; ICP 44 PF 1.110; HYPE 24 PF 0.946. Held-out full-notional drawdowns: ETH 15.53%, BTC 10.54%, ICP 22.07%, HYPE 15.52%.
**Color medium→weak comparator:** train 326 trades PF 1.116; held-out 158 trades PF 1.087.
**Optimized trend-filter variants:** failed on held-out data (best training config previously had 4H holdout PF 0.892). Feature walkforward tested 3,240 combinations and the best train/validation variants mostly failed the final quarter.
**Five sequential non-overlapping 4H slices:** baseline PF ETH 2.61/1.64/0.75/0.82/1.74; BTC 1.28/1.37/1.33/1.01/1.73; ICP 0.89/1.11/1.11/2.08/0.90; HYPE 0.17/0.67/1.91/0.58/0.87. At 0.40% round-trip costs, full-sample PF falls to ETH 1.19, BTC 1.08, ICP 1.01, HYPE 0.70. These are **reused historical data, not new independent confirmation**.
**1D:** inconsistent/sparse; not approved. **Divergence:** strict wave detector found zero qualifying signals; not validated.

Limitations: funding, mark-price stops, exchange outages, variable slippage and liquidation risk not modeled; model selection has already used the historical holdout, so an untouched future period is still required. Mean returns are not equity returns. Full-notional drawdowns were large. Never infer safe leverage from these results. See `reports/audit_2026-10-26.md` for cached-volume ablations, cost stress and corrected code defects.

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
