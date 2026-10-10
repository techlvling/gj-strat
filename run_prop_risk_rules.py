"""Faster Alpha Swing passes with risk rules on the current basket (vol-box 0.25% + vol-gotobi 3% +
fade 0.5% + M-3 3%). Same trades; each new trade's risk is scaled by the phase's progress
p = balance / phase start - 1 (target T = +10% in P1, +5% in P2; floor -10%, daily limit 5%).
Rules, fixed before running (first matching condition wins; P2 factor applied on top):
  base               x1
  boost 1.5 / 2      x1.5 / x2 while p < 0.4 T
  protect            x0.5 while p <= -5%
  finish             x0.5 once p >= 0.8 T
  P2 half            x0.5 in phase 2
  boost 2 + protect;  boost 2 + protect + finish;  boost 2 + protect + P2 half
Every trade's risk is capped at 4%, so one full loss stays inside the 5% daily limit.
Accepted if pass <= 3 months % is higher AND months per funded account is lower than the base, for
challenges started 2011-2025 and 2018-2025. All costs.

    python run_prop_risk_rules.py
"""
from multiprocessing import Pool

import pandas as pd

from gjstrat.prop import prop_table
from run_backtest import fmt_table
from run_m3_addon import ALPHA, build_legs, since

OUT = "results/prop_risk_rules"
MIX = {"basket": (0.25, 3, 0.5, 3, 0)}          # vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 others
RULES = {"base": {}, "boost 1.5": dict(boost=1.5), "boost 2": dict(boost=2.0), "protect": dict(protect=True),
         "finish": dict(finish=True), "P2 half": dict(p2=0.5), "boost 2 + protect": dict(boost=2.0, protect=True),
         "boost 2 + protect + finish": dict(boost=2.0, protect=True, finish=True),
         "boost 2 + protect + P2 half": dict(boost=2.0, protect=True, p2=0.5)}
CAP = 4.0
M, LEGS = None, None


def make_rule(boost=1.0, protect=False, finish=False, p2=1.0):
    def f(pct, bal, phase, target):
        p = bal - 1
        if protect and p <= -0.05:
            s = 0.5
        elif finish and p >= 0.8 * target:
            s = 0.5
        elif p < 0.4 * target:
            s = boost
        else:
            s = 1.0
        if phase == 1:
            s *= p2
        return min(pct * s, CAP)
    return f


def one(job):
    window, name = job
    legs = LEGS if window == "starts 2011-2025" else since(LEGS, "2018-01-01")
    tab = prop_table(M, legs, MIX, **ALPHA, scale=make_rule(**RULES[name]))
    tab.index = [name]
    tab.insert(0, "window", window)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    return tab


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    M, LEGS = build_legs()
    jobs = [(w, n) for w in ("starts 2011-2025", "starts 2018-2025") for n in RULES]
    with Pool(2) as pool:
        T = pd.concat(pool.map(one, jobs, chunksize=1))
    T.index.name = "rule"
    acc = {}
    for n in list(RULES)[1:]:
        acc[n] = all(T[(T.window == w)].loc[n, "pass ≤3 months %"] > T[(T.window == w)].loc["base", "pass ≤3 months %"] and
                     T[(T.window == w)].loc[n, "months per funded account"] < T[(T.window == w)].loc["base", "months per funded account"]
                     for w in T.window.unique())
    T["accepted"] = [None if n == "base" else acc[n] for n in T.index]
    T.to_csv(f"{OUT}/summary.csv")
    cols = ["window", "pass ≤1 month %", "pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
            "fails by daily limit %", "pass eventually %", "median months to pass", "months per funded account", "accepted"]
    open(f"{OUT}/REPORT.md", "w").write("# Alpha Swing: risk rules on the current basket\n\nRules in run_prop_risk_rules.py "
                                        "(fixed before running).\n\n" + fmt_table(T[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(T[cols].round(1).to_string())
