"""Verifier: hold-matched random-entry benchmark for Nasdaq MR6 (and MR4). For every claimed trade with hold h
closes, the benchmark is the mean R of entering on every eligible day of the same period with the same
mechanics (exit at the h-th later close, SL 2 x ATR20, same costs). Excess = R - benchmark; t per period.
Eligible = C > SMA200 for MR6 (its own trend filter), sigma60 defined for MR4.

    python results/alpha_hunt/index_meanrev/verify_code/holdmatch_nasdaq.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from reimpl_nasdaq import PER, main, t_of  # noqa: E402


def per_of(day):
    for p, (a, b) in PER.items():
        if pd.Timestamp(a) <= day <= pd.Timestamp(b):
            return p


def rules(X, trade):
    C, seg, r, s60, rsi, s200, s5, A, N = (X[k] for k in ("C", "seg", "r", "s60", "rsi", "s200", "s5", "A", "N"))

    def kth(j, k):
        jj = j + k
        return jj if jj < N and seg[jj] == seg[j] else None

    def first_exit(j, cap):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= N or seg[jj] != seg[j]:
                return None
            if C[jj] > s5[jj]:
                return jj
        return j + cap

    def walk(ent, ex):
        busy, rows = -1, []
        for j in np.flatnonzero(ent):
            if j <= busy or not A[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = trade(j, jx, 2.0)
            if t is None:
                continue
            t["h"] = jx - j
            rows.append(t)
            busy = jx
        return pd.DataFrame(rows)

    with np.errstate(invalid="ignore"):
        mr6 = walk((C > s200) & (rsi < 5), lambda j: first_exit(j, 10))
        mr4 = walk(r < -s60, lambda j: kth(j, 5))
        pools = {}
        for name, elig in (("MR6", C > s200), ("MR4", np.isfinite(s60))):
            for h in sorted(set((mr6 if name == "MR6" else mr4).h)):
                rows = []
                for j in np.flatnonzero(elig):
                    if not A[j] > 0:
                        continue
                    jx = kth(j, h)
                    if jx is None:
                        continue
                    t = trade(j, jx, 2.0)
                    if t is not None:
                        rows.append((t["day"], t["R"]))
                pools[(name, h)] = pd.DataFrame(rows, columns=["day", "R"])
    return mr6, mr4, pools


if __name__ == "__main__":
    mr6, mr4, pools = main(rules_fn=rules)
    for name, g in (("MR6", mr6), ("MR4", mr4)):
        g = g.copy()
        g["per"] = g.day.map(per_of)
        bench = {}
        for (nm, h), P in pools.items():
            if nm != name:
                continue
            P = P.assign(per=P.day.map(per_of))
            for p, x in P.groupby("per"):
                bench[(h, p)] = x.R.mean()
        g["bench"] = [bench[(h, p)] for h, p in zip(g.h, g.per)]
        g["excess"] = g.R - g.bench
        print(f"\n{name}: hold distribution {g.h.value_counts().sort_index().to_dict()}")
        for p in PER:
            x = g[g.per == p]
            print(f"  {p}: n={len(x)} avg R {x.R.mean():+.3f} (t {t_of(x.R):.2f}) | hold-matched bench {x.bench.mean():+.3f} | "
                  f"excess {x.excess.mean():+.3f} (t {t_of(x.excess):.2f})")
        print(f"  all: excess {g.excess.mean():+.3f} (t {t_of(g.excess):.2f})")
        print("  by year avg R:", g.groupby(pd.DatetimeIndex(g.day).year).R.agg(["count", "mean"]).round(2).T.to_dict())
