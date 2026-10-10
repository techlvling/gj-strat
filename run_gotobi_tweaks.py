"""Gotobi short tweaks on USDJPY 2010-2026 (pre-declared, ~41 variants).

Base grid: exit 03:00 / 04:00 / 06:00 / 07:00 UTC (12 / 13 / 15 / 16 JST) x SL 0.15 / 0.25 / 0.4
ATR20 x TP none / 1R / 2R (36). Filters on the current rule (exit 06:00, SL 0.25, no TP):
run-up, month-end only, skip Mondays (3). Bonus leg: long 00:00 -> 00:55 UTC on gotobi (1,
already tested before as "P1 fix-long 00:00UTC gotobi"). Current rule = exit 06:00, SL 0.25, no TP.

Selection, fixed before running: highest design (2010-2017) t among the short variants.
It must have design avg R > 0, every base-grid neighbour (one step on exit, SL or TP) positive
in design, and beat the current rule's avg R in BOTH check (2018-2023) and holdout (2024-2026).
Otherwise the current rule stays. Costs: $7/lot, swap (+1% markup), 0.2 pip slippage.

    python run_gotobi_tweaks.py
"""
from __future__ import annotations

import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import daily_table, gotobi_short, tokyo_fix
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

OUT = "results/gotobi_tweaks"
EXITS = [(3, 0), (4, 0), (6, 0), (7, 0)]
SLS = [0.15, 0.25, 0.4]
TPS = [None, 1.0, 2.0]
CURRENT = "exit 06:00 SL0.25 TP-"
rp.BUILDERS.update({"gotobi": gotobi_short, "fix": tokyo_fix})


def name(ex, sl, tp, filt="none"):
    n = f"exit {ex[0]:02d}:00 SL{sl:g} TP{'-' if tp is None else f'{tp:g}R'}"
    return n if filt == "none" else f"{n} +{filt}"


def grid():
    g = [(name(ex, sl, tp), "gotobi", dict(exit_at=ex, sl_atr=sl, tp_r=tp))
         for ex in EXITS for sl in SLS for tp in TPS]
    g += [(name((6, 0), 0.25, None, f), "gotobi", dict(filt=f)) for f in ("runup", "monthend", "nomonday")]
    g += [("bonus: long 00:00->fix", "fix", dict(mode="pre", at=(0, 0), days_filter="gotobi"))]
    return g


def neighbours(n):
    for i, ex in enumerate(EXITS):
        for j, sl in enumerate(SLS):
            for k, tp in enumerate(TPS):
                if name(ex, sl, tp) == n:
                    out = []
                    for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                        a, b, c = i + di, j + dj, k + dk
                        if 0 <= a < len(EXITS) and 0 <= b < len(SLS) and 0 <= c < len(TPS):
                            out.append(name(EXITS[a], SLS[b], TPS[c]))
                    return out
    return []                                            # filters: neighbours = the current rule


def main():
    os.makedirs(OUT, exist_ok=True)
    rp.SYM = "USDJPY"
    rp.M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                        "data/usdjpy_2010-01-01_2026-10-07.npz")
    d = daily_table(rp.M)
    rp.D = d[d.index >= pd.Timestamp("2010-01-01")]
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    g = grid()
    with Pool(os.cpu_count()) as pool:
        out = pool.map(rp.evaluate, g)
    res = pd.DataFrame([r for r, _ in out]).set_index("setup")
    res.to_csv(f"{OUT}/grid_full.csv")

    shorts = res.drop(index="bonus: long 00:00->fix")
    best = shorts["design t"].idxmax()
    nb = neighbours(best) or [CURRENT]
    cur = res.loc[CURRENT]
    checks = {
        "design avg R > 0": res.loc[best, "design avg R"] > 0,
        "all neighbours positive in design": bool((res.loc[nb, "design avg R"] > 0).all()),
        "beats current in check": res.loc[best, "check avg R"] > cur["check avg R"],
        "beats current in holdout": res.loc[best, "holdout avg R"] > cur["holdout avg R"],
    }
    winner = best if all(checks.values()) else CURRENT

    cols = ["design trades", "design win %", "design avg R", "design t", "check avg R", "check t"]
    show = res[cols].sort_values("design t", ascending=False)
    hcols = [c for c in res.columns if c.startswith(("design", "check", "holdout"))]
    head = res.loc[list(dict.fromkeys([best, CURRENT])), hcols].T
    rep = ["# Gotobi short tweaks — USDJPY 2010–2026\n",
           f"{len(res)} pre-declared variants (see run_gotobi_tweaks.py). Holdout shown only for the "
           f"design-best variant and the current rule.\n",
           f"**Design-best: {best}.** Checks: " + ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in checks.items()),
           f"\n**Rule to use: {winner}**\n", "## Design-best vs current, all periods\n", fmt_table(head, ".3f"),
           "\n## All variants (design + check)\n", fmt_table(show, ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(show.round(3).head(15).to_string())
    print("neighbours:", nb)
    print(head.round(3).to_string())
    print(checks, "->", winner)


if __name__ == "__main__":
    main()
