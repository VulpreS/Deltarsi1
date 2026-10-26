# Candidate B — DeltaRSI + Relative Volume, 4H (research only)

**Frozen on 2026-10-26. No real trading authorization.**

## Signals
- Instruments: BTCUSDT, ETHUSDT, ICPUSDT. HYPEUSDT only for external cross-asset monitoring.
- Source data: locally cached 1H OHLC resampled to UTC 4H and venue-specific 4H base volume.
- DeltaRSI as in `analyze_mtf_5y.indicator()` and `feature_walkforward.data()`.
- At close of bar k, the signed DeltaRSI histogram retains the same sign as k-1; its magnitude falls below k-1; the k-1 magnitude is at least k-2 and >=15.
- Volume of completed signal bar k **strictly greater** than arithmetic mean volume of preceding 20 completed 4H bars, excluding k.
- Negative DeltaRSI: LONG. Positive: SHORT.
- Enter at the next 4H open. No overlapping positions in the same instrument.
- Initial stop = 2.5 ATR(14) calculated at signal close; take profit = 6 ATR(14); time exit at end of 12 bars (48h), whichever comes first. Intrabar stop is assumed first when stop and target both touched.
- Research fee assumption: 0.15% round-trip of notional; additional 0.4% round-trip stress still leaves positive historical average, but funding and real liquidity are **not** included.
- Risk management candidate: 0.25% of equity at initial stop, no leverage required, max portfolio initial risk 0.75%, no averaging, no automatic order submission.

## Evidence and limitations
- 223 pooled historical BTC/ETH/ICP trades across chronological 50%/25%/25% segments; average +0.942% per trade with baseline 0.15% assumed costs; all three instruments positive in all three segments, but last segment ETH only +0.064% average on 19 trades.
- 14 of 45 neighboring parameter settings met exploratory positive-result criteria. 5/7/10-day holds generally worse.
- **Selection bias:** candidate was selected after inspecting all three segments. None of these is now an independent final holdout. Do not present these figures as out-of-sample evidence.
- **Critical next work:** obtain genuinely new chronological candles incrementally (do not redownload history), perform a sealed forward test without any parameter changes, compare signal bars with TradingView, use exchange funding history and realistic fee/slippage estimates, inspect maximum adverse excursion and portfolio drawdown under concurrent BTC/ETH/ICP signals, test regime robustness. Account for differences between Binance and Hyperliquid volume markets. Add walk-forward purging/embargo for 48h overlapping labels.
- A sustained forward advantage is not guaranteed. No live exchange execution implemented.

## Files
- `long_hold_research.py`
- `robustness_4h_volume.py`
- `reports/long_hold_research.json`
- `reports/robustness_4h_volume.json`
