"""Canonical deterministic OHLC stop/target fills for research (no orders).

A stop that is already breached at the bar open fills at the *worse*
opening price, not the stop trigger. When stop and target both touch,
assume stop first. Trailing levels must be updated AFTER this call and
take effect no earlier than the next candle.
"""
import math

def resolve_bar(bar, side, stop, target):
    """Return (fill_price, reason) or (None, None).

    bar: (utc_open_ms, open, high, low, close), side: +1 LONG / -1 SHORT.
    Stop/target were known before this bar opened.
    """
    if side not in (1, -1):
        raise ValueError("side must be +1 or -1")
    _, op, hi, lo, cl = bar
    if not all(math.isfinite(v) and v > 0 for v in (op, hi, lo, cl, stop, target)):
        raise ValueError("Non-finite/nonpositive OHLC or stop/target")
    if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
        raise ValueError("Invalid OHLC envelope")
    if (side == 1 and not stop < target) or (side == -1 and not stop > target):
        raise ValueError("Stop and target not ordered for side")
    hit_stop = lo <= stop if side == 1 else hi >= stop
    hit_target = hi >= target if side == 1 else lo <= target
    if hit_stop:
        # gap through stop: conservative adverse execution at the open
        return (min(op, stop) if side == 1 else max(op, stop)), "stop"
    if hit_target:
        # favorable opening gap: conservatively fill at the target
        return target, "target"
    return None, None
