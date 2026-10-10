"""Verifier: parameter-neighbour robustness and random-entry (drift) test for Nasdaq MR4 / MR6, on the
independent re-implementation (reimpl_nasdaq.py). Not a new test: diagnostics of the claimed survivors.

    python results/alpha_hunt/index_meanrev/verify_code/grid_nasdaq.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from reimpl_nasdaq import PER, main, stats, t_of  # noqa: E402


def run_rules(X, trade):
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

    def walk(ent, ex, ksl, overlap=False):
        busy, rows = -1, []
        for j in np.flatnonzero(ent):
            if (not overlap and j <= busy) or not A[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = trade(j, jx, ksl)
            if t is None:
                continue
            t["j"] = j
            rows.append(t)
            busy = jx
        return pd.DataFrame(rows)

    out = {}
    with np.errstate(invalid="ignore"):
        for thr in (0.75, 1.0, 1.25, 1.5):
            for hold in (3, 4, 5, 6, 7):
                for ksl in (1.5, 2.0, 3.0):
                    out[f"MR4 thr{thr} hold{hold} sl{ksl}"] = walk(r < -thr * s60, lambda j, h=hold: kth(j, h), ksl)
        for thr in (3, 5, 7, 10):
            for cap in (5, 10):
                for ksl in (1.5, 2.0, 3.0):
                    out[f"MR6 rsi<{thr} cap{cap} sl{ksl}"] = walk((C > s200) & (rsi < thr), lambda j, c=cap: first_exit(j, c), ksl)
        # every eligible day, overlapping, same mechanics (random-entry pool)
        out["POOL4"] = walk(np.isfinite(s60), lambda j: kth(j, 5), 2.0, overlap=True)
        out["POOL6"] = walk(C > s200, lambda j: first_exit(j, 10), 2.0, overlap=True)
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 300)
    out = main(rules_fn=run_rules)
    rows = [stats(g, k) for k, g in out.items() if not k.startswith("POOL")]
    G = pd.DataFrame(rows)
    G["survives"] = (G["design t"] >= 2) & (G["check avgR"] > 0) & (G["holdout avgR"] > 0)
    G.to_csv("results/alpha_hunt/index_meanrev/verify_code/grid_nasdaq.csv", index=False)
    print(G.round(3).to_string())
    for fam in ("MR4", "MR6"):
        g = G[G.test.str.startswith(fam)]
        print(fam, "neighbours:", len(g), "survive:", int(g.survives.sum()), "design t>=2:", int((g["design t"] >= 2).sum()),
              "check>0:", int((g["check avgR"] > 0).sum()), "holdout>0:", int((g["holdout avgR"] > 0).sum()))
    # random-entry test: same number of trades per period drawn from all eligible days (no signal), mean R
    rng = np.random.default_rng(7)
    for name, pool, claim in (("MR4", out["POOL4"], out["MR4 thr1.0 hold5 sl2.0"]), ("MR6", out["POOL6"], out["MR6 rsi<5 cap10 sl2.0"])):
        print(f"\n{name}: random-entry pool (every eligible day, overlapping) vs the signal")
        for p, (a, b) in PER.items():
            P = pool[(pool.day >= a) & (pool.day <= b)].R.to_numpy()
            S = claim[(claim.day >= a) & (claim.day <= b)].R.to_numpy()
            if not len(S):
                continue
            sims = np.array([rng.choice(P, len(S), replace=False).mean() for _ in range(20000)])
            frac_t2 = np.mean([t_of(rng.choice(P, len(S), replace=False)) >= 2 for _ in range(4000)])
            print(f"  {p}: signal n={len(S)} avg {S.mean():+.3f} | pool n={len(P)} avg {P.mean():+.3f} | "
                  f"P(random mean >= signal) = {np.mean(sims >= S.mean()):.3f} | P(random t >= 2) = {frac_t2:.3f}")
