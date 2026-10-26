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
