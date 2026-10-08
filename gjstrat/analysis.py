"""Breakout quality measures that do not depend on the RR / BE settings."""
from __future__ import annotations

from .data import Market
from .engine import EPS, Trade, _first


def levels_before_stop(m: Market, t: Trade, levels=(1, 2, 3)) -> int:
    """How many of `levels` (in R) price reached before the original stop, using the trade's own
    entry and 1R, ignoring its TP/BE. Same conventions as the engine: longs on bid, shorts on
    ask, the stop wins a bar that touches both, the entry bar can only stop out."""
    if t.side == "BUY":
        lo, hi = m.bl, m.bh
        sl = t.entry - t.risk
        adverse = lambda s: lo[s] <= sl + EPS
        favour = lambda s, lvl: hi[s] >= lvl - EPS
        target = lambda L: t.entry + L * t.risk
    else:
        lo, hi = m.al, m.ah
        sl = t.entry + t.risk
        adverse = lambda s: hi[s] >= sl - EPS
        favour = lambda s, lvl: lo[s] <= lvl + EPS
        target = lambda L: t.entry - L * t.risk
    if adverse(slice(t.entry_i, t.entry_i + 1))[0]:
        return 0
    pos, reached = t.entry_i + 1, 0
    for L in levels:
        lvl = target(L)
        j = _first(lambda s: adverse(s) | favour(s, lvl), pos, m.n)
        if j < 0 or adverse(slice(j, j + 1))[0]:
            return reached
        reached, pos = reached + 1, j
    return reached
