"""Building blocks: volume profile + value area, 15m bars, ATR, swing points, 15m bias, drive-in.

Time is "tod": minutes after midnight ET of the trading day (the prior day's 18:00 is -360).
A 1m bar at tod m covers [m, m+1) and is usable once it closes at m+1. A 15m bar starting at s
covers [s, s+15) and is usable at s+15. Prices are mid (average of the bid and ask candles).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ON_START = -360      # 18:00 ET the prior day
GAP_CHECK = 420      # 07:00
RTH_OPEN = 570       # 09:30
ENTRY_END = 660      # 11:00 (bias and entries)
EOD = 960            # 16:00


# --------------------------------------------------------------------------- volume profile
@dataclass
class Levels:
    poc: float           # centre of the highest-volume bin
    vah: float           # top edge of the value area's highest bin
    val: float           # bottom edge of the value area's lowest bin
    coverage: float      # share of total volume inside the value area (>= 0.70)
    total: float


def volume_profile(low: np.ndarray, high: np.ndarray, vol: np.ndarray,
                   bin_size: float = 1.0) -> tuple[int, np.ndarray]:
    """Bin k covers [k*bin, (k+1)*bin). Each bar's volume is split equally over every bin from the
    bin holding its low to the bin holding its high. Returns (index of the first bin, volumes)."""
    lo_b = np.floor(low / bin_size).astype(np.int64)
    hi_b = np.floor(high / bin_size).astype(np.int64)
    k0 = int(lo_b.min())
    n = hi_b - lo_b + 1
    rep = np.repeat(np.arange(len(lo_b)), n)
    offs = np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n)
    prof = np.bincount(lo_b[rep] + offs - k0, weights=(vol / n)[rep],
                       minlength=int(hi_b.max()) - k0 + 1)
    return k0, prof


def value_area(k0: int, prof: np.ndarray, bin_size: float = 1.0, pct: float = 0.70) -> Levels:
    """Start at the POC; each step compares the next two bins above with the next two below and
    adds ONE bin on the heavier side, until `pct` of the volume is covered. On an exact tie both
    sides get one bin (keeps the rule mirror-symmetric). POC ties go to the lowest bin."""
    total = float(prof.sum())
    p = int(np.argmax(prof))
    lo = hi = p
    cov = float(prof[p])
    n = len(prof)
    while cov < pct * total:
        can_up, can_dn = hi + 1 < n, lo > 0
        if not (can_up or can_dn):
            break
        up2 = prof[hi + 1:hi + 3].sum() if can_up else -1.0
        dn2 = prof[max(lo - 2, 0):lo].sum() if can_dn else -1.0
        if up2 > dn2:
            hi += 1
            cov += prof[hi]
        elif dn2 > up2:
            lo -= 1
            cov += prof[lo]
        else:
            hi, lo = hi + 1, lo - 1
            cov += prof[hi] + prof[lo]
    return Levels(poc=(k0 + p + 0.5) * bin_size, vah=(k0 + hi + 1) * bin_size,
                  val=(k0 + lo) * bin_size, coverage=cov / total if total else np.nan, total=total)


# --------------------------------------------------------------------------- bars / ATR
def bars15(tod: np.ndarray, o, h, l, c):
    """15m bars on the ET clock (:00 :15 :30 :45) built from the 1m bars. Returns start tods + OHLC."""
    key = np.floor_divide(tod, 15) * 15
    starts, first = np.unique(key, return_index=True)
    last = np.r_[first[1:], len(key)] - 1
    return (starts, o[first], np.maximum.reduceat(h, first), np.minimum.reduceat(l, first), c[last])


def true_range(h, l, c) -> np.ndarray:
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return tr


def sma(x: np.ndarray, n: int) -> np.ndarray:
    """out[i] = mean(x[i-n+1 .. i]); NaN until n values exist."""
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.cumsum(np.r_[0.0, x])
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def atr15_at_close(tod1: np.ndarray, starts15: np.ndarray, atr15: np.ndarray) -> np.ndarray:
    """ATR of the 15m bars that have closed when each 1m bar closes (close = tod + 1)."""
    k = np.searchsorted(starts15, tod1 + 1 - 15, side="right") - 1
    out = np.full(len(tod1), np.nan)
    ok = k >= 0
    out[ok] = atr15[k[ok]]
    return out


# --------------------------------------------------------------------------- swings
def swing_lows(low: np.ndarray, n: int = 5) -> np.ndarray:
    """True at j if low[j] is strictly below the n bars before and the n bars after.
    Confirmed only when bar j+n closes."""
    out = np.zeros(len(low), bool)
    if len(low) >= 2 * n + 1:
        w = sliding_window_view(low, 2 * n + 1)
        ctr = w[:, n]
        out[n:len(low) - n] = (ctr < w[:, :n].min(1)) & (ctr < w[:, n + 1:].min(1))
    return out


def swing_highs(high: np.ndarray, n: int = 5) -> np.ndarray:
    return swing_lows(-high, n)


def obvious_level(price: np.ndarray, is_swing: np.ndarray, t: int, side: int,
                  n: int = 5, lookback: int = 60) -> tuple[float, int]:
    """The level bar t is tested against, known before bar t opens.
    side=+1 (long setups): lowest confirmed swing low among the last `lookback` closed bars
    (t-lookback .. t-1), confirmed means j+n <= t-1, and still intact (no bar j+1..t-1 traded
    below it). side=-1: highest intact swing high (pass highs). Returns (level, bar) or (nan, -1)."""
    x = price * side                      # work in "low" space: long lows, negated short highs
    best, best_j = np.inf, -1
    run_min = np.inf                      # min of x over j+1 .. t-1
    for j in range(t - 1, max(t - lookback, 0) - 1, -1):
        if j <= t - 1 - n and is_swing[j] and x[j] <= run_min and x[j] < best:
            best, best_j = x[j], j
        run_min = min(run_min, x[j])
    return (best * side, best_j) if best_j >= 0 else (np.nan, -1)


# --------------------------------------------------------------------------- drive in / out
def drive_in(o, h, l, c, atr, s: int, side: int, win: int = 10, k: float = 1.5) -> tuple[bool, float]:
    """Bars max(s-win+1, 0) .. s (the up-to-10 closed bars ending at the sweep extreme bar s).
    Long: needs a bearish gap (bars b1, b1+1, b1+2 with high[b1+2] < low[b1]; the one closest to s)
    and a bearish bar with body >= k * ATR. Returns (ok, gap level = low[b1]).
    Short mirror: bullish gap low[b1+2] > high[b1], gap level = high[b1], bullish big bar."""
    a = max(s - win + 1, 0)
    gap = np.nan
    for b1 in range(s - 2, a - 1, -1):
        if (side > 0 and h[b1 + 2] < l[b1]) or (side < 0 and l[b1 + 2] > h[b1]):
            gap = l[b1] if side > 0 else h[b1]
            break
    body_in = (o[a:s + 1] - c[a:s + 1]) * side          # > 0: bar moved INTO the sweep
    big = bool(np.any(body_in >= k * atr[a:s + 1]))
    return (not np.isnan(gap)) and big, gap


def drive_out(o, c, atr, t: int, side: int, gap: float, k: float = 1.5) -> bool:
    """Long: bullish bar with body >= k*ATR closing above the gap's top. Short: mirror."""
    body = (c[t] - o[t]) * side
    return bool(body >= k * atr[t] and (c[t] - gap) * side > 0)


# --------------------------------------------------------------------------- bias
@dataclass
class Bias:
    side: int            # +1 long, -1 short, 0 none
    kind: str            # "B1", "B2", "none", "conflict"
    active: int          # tod at which it becomes active (close of the confirming 15m bar)


def find_bias(starts, h15, l15, c15, vah: float, val: float, eligible_start: int,
              acceptance: bool, cutoff: int = ENTRY_END, lookback: int = 4) -> Bias:
    """First confirmed bias, using only 15m bars that start at/after `eligible_start` and close by
    `cutoff`. B1 long: a bar's low < VAL and that bar or one of the next 4 closes > VAL (target POC
    or 2R). B1 short mirrors at VAH. B2 (if on): two consecutive closes > VAH = long, < VAL = short.
    Same bar: B1 long + B1 short = conflict (no trade); B1 beats B2 (they can only agree on side)."""
    idx = np.flatnonzero((starts >= eligible_start) & (starts + 15 <= cutoff))
    for p, i in enumerate(idx):
        win = idx[max(0, p - lookback):p + 1]
        b1l = c15[i] > val and bool((l15[win] < val).any())
        b1s = c15[i] < vah and bool((h15[win] > vah).any())
        prev = idx[p - 1] if p >= 1 else None
        b2l = acceptance and prev is not None and c15[prev] > vah and c15[i] > vah
        b2s = acceptance and prev is not None and c15[prev] < val and c15[i] < val
        act = int(starts[i]) + 15
        if b1l and b1s:
            return Bias(0, "conflict", act)
        if b1l or b1s:
            return Bias(1 if b1l else -1, "B1", act)
        if b2l or b2s:
            return Bias(1 if b2l else -1, "B2", act)
    return Bias(0, "none", -1)
