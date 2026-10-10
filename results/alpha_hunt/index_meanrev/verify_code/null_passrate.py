"""Verifier: how often does a RANDOM-entry long clone (same mechanics, same trade counts per period) pass the
charter bar on the Nasdaq? (drift-aware null vs the report's 0.6% zero-mean null)"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from reimpl_nasdaq import PER, main, t_of
from holdmatch_nasdaq import rules, per_of

mr6, mr4, pools = main(rules_fn=rules)
rng = np.random.default_rng(11)
for name, g in (("MR4", mr4), ("MR6", mr6)):
    cnt = g.day.map(per_of).value_counts().to_dict()
    # MR6 clone: random eligible days, hold drawn from MR6's own hold distribution
    P = {h: P.assign(per=P.day.map(per_of)) for (nm, h), P in pools.items() if nm == name}
    hs = g.h.to_numpy()
    passes = 0; K = 5000
    for _ in range(K):
        ok = True
        for p in ("design", "check", "holdout"):
            n = cnt.get(p, 0)
            hh = rng.choice(hs, n)
            x = np.array([rng.choice(P[h][P[h].per == p].R.to_numpy()) for h in hh])
            if p == "design":
                ok &= t_of(x) >= 2
            else:
                ok &= x.mean() > 0
            if not ok:
                break
        passes += ok
    print(f"{name}: random-entry clone passes the full charter bar in {passes / K * 100:.1f}% of draws (counts {cnt})")
