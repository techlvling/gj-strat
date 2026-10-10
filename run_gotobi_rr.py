"""Gotobi short exited by RR instead of time (USDJPY 2010-2026).

Same entry (sell at the 09:55 JST fix on gotobi days, SL 0.25 x ATR20) but no 15:00 JST exit:
the trade runs until TP (1 / 1.5 / 2 / 3 R) or SL, with a 10-day safety cap. Overnight holds pay
swap (+1% markup). Compared with the current time exit. Pre-declared rule: an RR exit replaces
the time exit only if design (2010-2017) t >= 2 and it beats the current rule's avg R in both
check (2018-2023) and holdout (2024-2026).

    python run_gotobi_rr.py
"""
from dataclasses import replace
from datetime import date
from multiprocessing import Pool
import os

import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import daily_table, gotobi_short
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

CAP = 10 * 1440


def gotobi_rr(m, d, tp_r):
    return [replace(s, tp_dist=tp_r * s.sl_dist, exit_by_i=s.start_i + CAP) for s in gotobi_short(m, d)]


rp.BUILDERS.update({"rr": gotobi_rr, "time": gotobi_short})
GRID = [("current: time exit 15:00 JST", "time", {})] + \
       [(f"RR exit TP {k:g}R (no time exit)", "rr", dict(tp_r=k)) for k in (1, 1.5, 2, 3)]

if __name__ == "__main__":
    rp.SYM = "USDJPY"
    rp.M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    d = daily_table(rp.M)
    rp.D = d[d.index >= pd.Timestamp("2010-01-01")]
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    with Pool(os.cpu_count()) as pool:
        out = pool.map(rp.evaluate, GRID)
    res = pd.DataFrame([r for r, _ in out]).set_index("setup")
    cur = res.iloc[0]
    res["replaces current"] = [False] + [bool(r["design t"] >= 2 and r["check avg R"] > cur["check avg R"]
                                              and r["holdout avg R"] > cur["holdout avg R"]) for _, r in res.iloc[1:].iterrows()]
    cols = [f"{p} {c}" for p in ("design", "check", "holdout") for c in ("trades", "win %", "avg R", "t")] + \
           ["holdout max DD % (0.5%)", "replaces current"]
    os.makedirs("results/gotobi_rr", exist_ok=True)
    res.to_csv("results/gotobi_rr/grid.csv")
    open("results/gotobi_rr/REPORT.md", "w").write("# Gotobi short: RR exit vs time exit (USDJPY 2010–2026)\n\n"
                                                    "Rules and pass test in run_gotobi_rr.py.\n\n" + fmt_table(res[cols], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(3).T.to_string())
