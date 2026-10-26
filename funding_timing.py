"""UTC funding-event exposure bounds for OHLC-only research.

Synthetic funding stress only: no venue rates, settlement receipts, mark price,
or venue provenance. Entry at 4H bar open is treated as AFTER an event at that
same instant. Exits exactly on a funding boundary have unknown ordering, so
the lower bound excludes that event and the upper bound includes it.
"""
import math

HOUR_MS = 3600000
PERIOD_MS = 8 * HOUR_MS

def funding_event_count(entry_ms, exit_ms, include_exit=True):
    """Number of 00/08/16 UTC events in (entry, exit] or (entry, exit)."""
    if exit_ms < entry_ms:
        raise ValueError("exit before entry")
    if not all(isinstance(t, int) for t in (entry_ms, exit_ms)):
        raise TypeError("timestamps must be integer milliseconds")
    if include_exit:
        return max(0, exit_ms // PERIOD_MS - entry_ms // PERIOD_MS)
    return max(0, (exit_ms - 1) // PERIOD_MS - entry_ms // PERIOD_MS)

def exposure_bounds(entry_ms, earliest_exit_ms, latest_exit_ms):
    """Conservative bounds when OHLC hides exact stop/TP time."""
    if not (entry_ms <= earliest_exit_ms <= latest_exit_ms):
        raise ValueError("invalid UTC exposure interval")
    return {
        "entry_ms": entry_ms,
        "exit_earliest_ms": earliest_exit_ms,
        "exit_latest_ms": latest_exit_ms,
        "hours_min": (earliest_exit_ms - entry_ms) / HOUR_MS,
        "hours_max": (latest_exit_ms - entry_ms) / HOUR_MS,
        "funding_events_min": funding_event_count(entry_ms, earliest_exit_ms, False),
        "funding_events_max": funding_event_count(entry_ms, latest_exit_ms, True),
    }

def net_return(trade, roundtrip_cost, adverse_funding_per_event, bound="max"):
    """Net return with explicit upper/lower UTC event exposure bounds."""
    if bound not in ("min", "max"):
        raise ValueError("bound must be min or max")
    if roundtrip_cost < 0 or adverse_funding_per_event < 0:
        raise ValueError("stress assumptions must be nonnegative")
    key = "funding_events_" + bound
    if key not in trade:
        raise KeyError("trade lacks UTC funding exposure bounds")
    return trade["gross"] - roundtrip_cost - trade[key] * adverse_funding_per_event
