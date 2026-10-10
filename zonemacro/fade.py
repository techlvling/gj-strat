"""Fade the impulse: trade AGAINST the 4H impulses found by zones.find_zones.

Event   : the same base + impulse as the zone study (base of 1-3 small-body candles, then a
          move of K x ATR(14) within 3 candles; full-range base).
Side    : opposite to the impulse (up impulse -> sell, down impulse -> buy).
Entry   : "close"   - at market at the close of the impulse candle.
          "confirm" - at market at the close of the first 4H candle within the next 6 that closes
                      against the impulse (bearish after an up impulse); no such candle -> no trade.
          Sells fill at bid, buys at ask (close of the last 15m bar of that 4H candle).
Stop    : beyond the impulse extreme (highest high since the base for an up impulse, up to and
          including the entry candle) + buffer, buffer = max(spread, 0.1 x ATR(14) 4H).
Target  : "1R", "2R", or "base" = the base's near edge (top of the base after an up impulse);
          a base target under 1R away is skipped and counted.
Exits, gaps, same-candle SL/TP, skips (stop < 2 x spread) and swap: as engine.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import engine as E

MAX_WAIT = 6
H4 = pd.Timedelta(hours=4)


def fade_candidates(m: E.M15, b4: pd.DataFrame, z: pd.DataFrame, atr4: np.ndarray, entry: str,
                    target: str) -> tuple[pd.DataFrame, dict]:
    o, h, l, c = (b4[x].to_numpy(float) for x in ("bo", "bh", "bl", "bc"))
    n4 = len(o)
    close_ns = (b4.index + H4).to_numpy().astype("datetime64[ns]").astype(np.int64)
    pos = pd.Series(np.arange(n4), index=b4.index)
    rows, st = [], {"impulses": len(z), "no_confirmation": 0}
    for zi, r in enumerate(z.itertuples(index=False)):
        kind = int(r.kind)                       # +1 up impulse (demand), -1 down impulse (supply)
        side = -kind
        e, j = int(pos[r.base_end]), int(pos[r.impulse])
        if entry == "close":
            ce = j
        else:
            ce = -1
            for k in range(j + 1, min(j + 1 + MAX_WAIT, n4)):
                if (c[k] < o[k]) if kind > 0 else (c[k] > o[k]):
                    ce = k
                    break
            if ce < 0:
                st["no_confirmation"] += 1
                continue
        ext = h[e + 1:ce + 1].max() if kind > 0 else l[e + 1:ce + 1].min()
        i = int(np.searchsorted(m.t, close_ns[ce], side="left")) - 1   # last 15m bar of candle ce
        if i < 0 or i >= m.n - 1:
            continue
        sp = m.spread[i]
        buf = max(sp, 0.1 * atr4[ce])
        if side < 0:
            px, stop = m.bc[i], ext + buf
        else:
            px, stop = m.ac[i], ext - buf
        R = side * (px - stop)
        skip, tp = E.SKIP_NONE, np.nan
        if not R >= 2 * sp:
            skip = E.SKIP_STOP
        elif target in ("1R", "2R"):
            tp = px + side * (1 if target == "1R" else 2) * R
        else:
            tp = r.top if kind > 0 else r.bottom   # base near edge (full range)
            if side * (tp - px) < R:
                skip = E.SKIP_TP
        if skip == E.SKIP_NONE:
            xi, xp, reason = E.simulate_exit(m, side, stop, tp, i, False)
            res = side * (xp - px) / R
        else:
            xi, xp, reason, res = -1, np.nan, "", np.nan
        rows.append((zi, side, i, i, px, stop, tp, R, xi, xp, reason, res, abs(ext - (r.top if kind > 0 else r.bottom)),
                     sp, skip, False))
    cand = pd.DataFrame(rows, columns=E.CAND_COLS)
    cand = cand.sort_values(["entry_idx", "zone"], kind="stable").reset_index(drop=True)
    return cand, st
