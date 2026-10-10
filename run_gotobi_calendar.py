"""Gotobi short: Japanese business calendar and entry time (USDJPY 2010-2026).

Variants (fixed before running): current rule (weekends-only calendar, entry 09:55 JST);
Japanese calendar (no trade on a JP public holiday; a gotobi date on a holiday/weekend moves to
the previous JP business day) with entry 09:50 / 09:55 / 10:00 JST. Exit 15:00 JST, SL 0.25 ATR.
Replace the current rule only if design t >= 2 and it beats the current avg R in both check and
holdout. Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_gotobi_calendar.py
"""
import os
from datetime import date
from multiprocessing import Pool

import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import daily_table, gotobi_short
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

rp.BUILDERS.update({"g": gotobi_short})
GRID = [("current (weekend calendar, 09:55)", "g", {}),
        ("JP calendar, entry 09:50", "g", dict(calendar="jp", entry_at=(0, 50))),
        ("JP calendar, entry 09:55", "g", dict(calendar="jp")),
        ("JP calendar, entry 10:00", "g", dict(calendar="jp", entry_at=(1, 0)))]

if __name__ == "__main__":
    rp.SYM = "USDJPY"
    rp.M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    d = daily_table(rp.M)
    rp.D = d[d.index >= pd.Timestamp("2010-01-01")]
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    with Pool(4) as pool:
        out = pool.map(rp.evaluate, GRID)
    res = pd.DataFrame([r for r, _ in out]).set_index("setup")
    cur = res.iloc[0]
    res["replaces current"] = [False] + [bool(r["design t"] >= 2 and r["check avg R"] > cur["check avg R"]
                                              and r["holdout avg R"] > cur["holdout avg R"]) for _, r in res.iloc[1:].iterrows()]
    cols = [f"{p} {c}" for p in ("design", "check", "holdout") for c in ("trades", "win %", "avg R", "t")] + ["replaces current"]
    os.makedirs("results/gotobi_calendar", exist_ok=True)
    res.to_csv("results/gotobi_calendar/grid.csv")
    open("results/gotobi_calendar/REPORT.md", "w").write("# Gotobi short: Japanese calendar and entry time (USDJPY 2010–2026)\n\n"
                                                          "Rules and pass test in run_gotobi_calendar.py.\n\n" + fmt_table(res[cols], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(3).T.to_string())
