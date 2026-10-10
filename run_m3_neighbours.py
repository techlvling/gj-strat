"""Robustness of the M-3 add-on (run_m3_addon.py): the same comparison at neighbouring risk settings.
Overlapping accounts share trades, so one loss can breach a whole cohort; neighbours show how much of
a difference is the add-on and how much is path luck. Fixed before running:
  Alpha Swing (starts 2011-2025): vol-box 0.2 / 0.3% (gotobi 3%) and vol-gotobi 2.5 / 3.5% (box 0.25%),
  fade 0.5%, each without and with M-3 USDJPY 3%.
  Blueberry Elite (starts 2011-2024, 10% cushion): vol-gotobi 1.4 / 1.6% (box 0.25%) and vol-box
  0.2 / 0.3% (gotobi 1.5%), each without and with M-3 USDJPY 0.5%.

    python run_m3_neighbours.py
"""
from multiprocessing import Pool

import pandas as pd

from gjstrat.prop import instant_table, prop_table
from run_backtest import fmt_table
from run_m3_addon import ALPHA, BLUE, OUT, build_legs

M, LEGS = None, None


def alpha_one(item):
    tab = prop_table(M, LEGS, dict([item]), **ALPHA)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    return tab


def blue_one(item):
    return instant_table(M, LEGS, dict([item]), (0.10,), last_start="2024-10-07", **BLUE).droplevel(0)


if __name__ == "__main__":
    M, LEGS = build_legs()
    am, bm = [], []
    for b, g in ((0.2, 3), (0.3, 3), (0.25, 2.5), (0.25, 3.5)):
        am += [(f"box {b:g}% · gotobi {g:g}% · fade 0.5%", (b, g, 0.5, 0, 0)), (f"box {b:g}% · gotobi {g:g}% · fade 0.5% + M-3 3%", (b, g, 0.5, 3, 0))]
    for b, g in ((0.25, 1.4), (0.25, 1.6), (0.2, 1.5), (0.3, 1.5)):
        bm += [(f"box {b:g}% · gotobi {g:g}%", (b, g, 0, 0, 0)), (f"box {b:g}% · gotobi {g:g}% + M-3 0.5%", (b, g, 0, 0.5, 0))]
    with Pool(4) as pool:
        A = pd.concat(pool.map(alpha_one, am, chunksize=1))
        B = pd.concat(pool.map(blue_one, bm, chunksize=1))
    A.to_csv(f"{OUT}/alpha_neighbours.csv"); B.to_csv(f"{OUT}/blueberry_neighbours.csv")
    acols = ["pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %", "months per funded account"]
    bcols = ["got ≥1 payout %", "avg paid in 24 months $", "account lost within 24 months %"]
    A.index.name = B.index.name = "mix"
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Robustness: neighbouring risk settings (run_m3_neighbours.py)\n\n### Alpha Swing, starts 2011–2025\n\n"
                + fmt_table(A[acols], ".1f") + "\n\n### Blueberry Elite, starts 2011–2024\n\n" + fmt_table(B[bcols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(A[acols].round(1).to_string()); print(B[bcols].round(1).to_string())
