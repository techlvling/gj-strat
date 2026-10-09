"""Random-entry benchmark.

Entries are market orders at the close of random 15m bars where the 1H trend filter points the
same way (buy at ask, sell at bid). Stop distance = the real strategy's median stop distance,
target = its median planned target multiple, same BE rule, same exit rules (manage_bar).
Each random trade is simulated independently; a seed's trades are compounded in time order.
"""
from __future__ import annotations

import numpy as np

from .engine import Bars


def resolve(b: Bars, entries: np.ndarray, side: int, d: float, m: float,
            be_at_r: float = 1.0) -> np.ndarray:
    """R result (price terms) of a market entry at the close of each bar in `entries`.
    Vectorized copy of engine.manage_bar, starting on the bar after entry."""
    n = b.n
    e = entries.astype(np.int64)
    entry = b.ac[e] if side == 1 else b.bc[e]
    stop = entry - side * d
    tp = entry + side * m * d
    be_on = m >= be_at_r
    trig = entry + side * be_at_r * d
    be_done = np.zeros(len(e), bool)
    R = np.full(len(e), np.nan)
    u = np.arange(len(e))
    step = 1
    while len(u):
        k = e[u] + step
        over = k >= n
        if over.any():                    # data ended: mark to market at the last close
            last = b.bc[n - 1] if side == 1 else b.ac[n - 1]
            R[u[over]] = side * (last - entry[u[over]]) / d
            u, k = u[~over], k[~over]
            if not len(u):
                break
        s = stop[u]
        if side == 1:
            o, lo, hi = b.bo[k], b.bl[k], b.bh[k]
            gap_sl, hit_sl = o <= s, lo <= s
            gap_tp, hit_tp = o >= tp[u], hi >= tp[u]
            hit_be = hi >= trig[u]
        else:
            o, lo, hi = b.ao[k], b.al[k], b.ah[k]
            gap_sl, hit_sl = o >= s, hi >= s
            gap_tp, hit_tp = o <= tp[u], lo <= tp[u]
            hit_be = lo <= trig[u]
        px = np.where(gap_sl, o, np.where(hit_sl, s, np.where(gap_tp, o, tp[u])))
        done = hit_sl | hit_tp
        R[u[done]] = side * (px[done] - entry[u[done]]) / d
        mv = ~done & be_on & ~be_done[u] & hit_be
        be_done[u[mv]] = True
        stop[u[mv]] = entry[u[mv]]
        u = u[~done]
        step += 1
    return R


def random_benchmark(b: Bars, eligible: dict[int, np.ndarray], n_side: dict[int, int],
                     d: float, m: float, seeds: int = 1000, risk: float = 0.01,
                     comm_R: float = 0.0, seed0: int = 0) -> dict[str, np.ndarray]:
    """Distribution over `seeds` of avg R, net return, win rate and profit factor for
    n_side[+1] random buys and n_side[-1] random sells drawn from `eligible` bars."""
    pools = {}
    for s in (1, -1):
        if n_side.get(s, 0) > 0:
            idx = eligible[s]
            pools[s] = (idx, resolve(b, idx, s, d, m) - comm_R)
    rng = np.random.default_rng(seed0)
    out = {k: np.empty(seeds) for k in ("avg_R", "net_return", "win_rate", "pf")}
    for j in range(seeds):
        ts, rs = [], []
        for s, (idx, R) in pools.items():
            k = n_side[s]
            pick = rng.choice(len(idx), size=k, replace=len(idx) < k)
            ts.append(idx[pick])
            rs.append(R[pick])
        t = np.concatenate(ts)
        r = np.concatenate(rs)[np.argsort(t, kind="stable")]
        out["avg_R"][j] = r.mean()
        out["net_return"][j] = np.prod(1 + risk * r) - 1
        out["win_rate"][j] = (r > 0).mean()
        loss = -r[r < 0].sum()
        out["pf"][j] = r[r > 0].sum() / loss if loss > 0 else np.inf
    return out


def percentile_of(value: float, dist: np.ndarray) -> float:
    """% of the distribution strictly below `value` (ties count half)."""
    return float(100 * ((dist < value).mean() + 0.5 * (dist == value).mean()))
