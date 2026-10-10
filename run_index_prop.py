"""Alpha Swing with the Nasdaq calendar trades added (only those that replicated on the S&P 500 and the
Nikkei, see run_index_replication.py): E1b turn of month (buy the close of the last trading day, sell the
close of the 3rd trading day; SL 1 x ATR20) and E3 pre-holiday (hold the trading day before an NYSE
holiday; SL 0.5 x ATR20). Nasdaq 100 CFD trades moved onto the USDJPY minute grid.
Fixed before running: each added at 1% and 2% risk, on the current basket (vol-box 0.25% + vol-gotobi 3% +
fade 0.5% + M-3 3%), with and without the boost x1.5 rule (run_prop_risk_rules.py).
Accepted if months per funded account is lower and pass eventually % is not lower than the same basket
without them, for starts 2011-2025 and 2018-2025.

    python run_index_prop.py E1b E3        # the effects that replicated
"""
import os
import sys
from collections import namedtuple

import pandas as pd

from gjstrat.prop import prop_table
from run_backtest import fmt_table
from run_index_anomalies import evaluate
from run_m3_addon import ALPHA, build_legs, since
from run_prop_risk_rules import make_rule

OUT = "results/index_prop"
NAMES = {"E1b": "E1b turn of month (from last day)", "E3": "E3 pre-holiday"}
Tr = namedtuple("Tr", "day entry_i exit_i")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    use = [k for k in sys.argv[1:] if k in NAMES]
    m, legs = build_legs()
    _, trades, nq = evaluate("USATECHIDXUSD")
    off = int((nq.t0 - m.t0) // pd.Timedelta(minutes=1))
    for k in use:
        tr, r = trades[NAMES[k]]
        legs.append(([Tr(t.day, t.entry_i + off, t.exit_i + off) for t in tr], r))
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(use)}
    for risk in (1, 2):
        for j, k in enumerate(use):
            mixes[f"basket + {k} {risk}%"] = base + tuple(risk if i == j else 0 for i in range(len(use)))
        if len(use) > 1:
            mixes[f"basket + {' + '.join(use)} {risk}% each"] = base + (risk,) * len(use)
    tabs = []
    for rule, scale in (("normal risk", None), ("boost x1.5", make_rule(boost=1.5))):
        for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
            t = prop_table(m, lg, mixes, **ALPHA, **({"scale": scale} if scale else {}))
            t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
            t.insert(0, "window", w)
            t.insert(0, "risk rule", rule)
            tabs.append(t)
            print(rule, w, flush=True)
    P = pd.concat(tabs)
    acc = {}
    for rule in P["risk rule"].unique():
        for mix in list(mixes)[1:]:
            acc[(rule, mix)] = all(
                P[(P["risk rule"] == rule) & (P.window == w)].loc[mix, "months per funded account"]
                < P[(P["risk rule"] == rule) & (P.window == w)].loc["basket", "months per funded account"]
                and P[(P["risk rule"] == rule) & (P.window == w)].loc[mix, "pass eventually %"]
                >= P[(P["risk rule"] == rule) & (P.window == w)].loc["basket", "pass eventually %"]
                for w in P.window.unique())
    P["accepted"] = [None if mix == "basket" else acc[(rule, mix)] for rule, mix in zip(P["risk rule"], P.index)]
    P.index.name = "mix"
    P.to_csv(f"{OUT}/summary.csv")
    cols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
            "pass eventually %", "median months to pass", "months per funded account", "accepted"]
    open(f"{OUT}/REPORT.md", "w").write("# Alpha Swing with the Nasdaq calendar trades\n\nRules in run_index_prop.py "
                                        f"(fixed before running). Added: {', '.join(NAMES[k] for k in use) or 'none'}.\n\n"
                                        + fmt_table(P[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(P[cols].round(1).to_string())
