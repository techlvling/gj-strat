"""4H supply/demand zones (built on BID candles).

Base     : a run of 1-3 consecutive candles, each with body < 50% of its own range, with a
           non-base candle (or the data edge) on each side. Runs of 4+ are not bases.
Impulse  : within the next 3 candles, price moves away from the base by >= K x ATR(14):
           demand: highest high since the base - base high  >= K x ATR
           supply: base low - lowest low since the base     >= K x ATR
           (ATR = Wilder ATR(14) at the last base candle). The first candle where either
           side qualifies is the impulse candle; if both qualify on the same candle the base
           is ambiguous and skipped.
Zone     : full = base low..high; body = lowest..highest candle body in the base.
Active   : from the close of the impulse candle (its start + 4h), never earlier.
Expiry   : after 50 4H bars (bars impulse+1 .. impulse+50), or at the first touch (engine).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BAR = pd.Timedelta(hours=4)
DEMAND, SUPPLY = 1, -1


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    tr = np.empty(len(h))
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    atr = np.full(len(h), np.nan)
    if len(h) >= n:
        atr[n - 1] = tr[:n].mean()
        for i in range(n, len(h)):
            atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    return atr


def small_body(o, h, l, c) -> np.ndarray:
    rng = h - l
    return (rng > 0) & (np.abs(c - o) < 0.5 * rng)


def find_zones(b4: pd.DataFrame, k: float, mode: str = "full", max_age: int = 50,
               atr: np.ndarray | None = None) -> tuple[pd.DataFrame, dict]:
    o, h, l, c = (b4[x].to_numpy(float) for x in ("bo", "bh", "bl", "bc"))
    t = b4.index
    n = len(o)
    if atr is None:
        atr = atr_wilder(h, l, c)
    small = small_body(o, h, l, c)
    rows, stats = [], {"bases": 0, "long_runs_ignored": 0, "ambiguous": 0, "no_impulse": 0}
    i = 0
    while i < n:
        if not small[i]:
            i += 1
            continue
        s = i
        while i < n and small[i]:
            i += 1
        e = i - 1                                  # run s..e, e+1 is not small (or end)
        if e - s + 1 > 3:
            stats["long_runs_ignored"] += 1
            continue
        if np.isnan(atr[e]) or e + 1 >= n:
            continue
        stats["bases"] += 1
        base_hi, base_lo = h[s:e + 1].max(), l[s:e + 1].min()
        thr = k * atr[e]
        hi, lo, j, up, dn = -np.inf, np.inf, -1, False, False
        for jj in range(e + 1, min(e + 4, n)):
            hi, lo = max(hi, h[jj]), min(lo, l[jj])
            up, dn = hi - base_hi >= thr, base_lo - lo >= thr
            if up or dn:
                j = jj
                break
        if up and dn:
            stats["ambiguous"] += 1
            continue
        if j < 0:
            stats["no_impulse"] += 1
            continue
        if mode == "full":
            top, bot = base_hi, base_lo
        elif mode == "body":
            top = np.maximum(o[s:e + 1], c[s:e + 1]).max()
            bot = np.minimum(o[s:e + 1], c[s:e + 1]).min()
        else:
            raise ValueError(mode)
        expires = t[j + max_age] + BAR if j + max_age < n else pd.Timestamp.max
        rows.append((DEMAND if up else SUPPLY, t[s], t[e], e - s + 1, t[j], t[j] + BAR,
                     expires, top, bot, atr[j]))
    z = pd.DataFrame(rows, columns=["kind", "base_start", "base_end", "base_len", "impulse",
                                    "active_from", "expires", "top", "bottom", "atr"])
    z["kind"] = z["kind"].astype(int)
    return z, stats
