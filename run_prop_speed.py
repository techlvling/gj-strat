"""Fastest / cheapest way to a funded account with the two real edges (USDJPY box + gotobi).

Risk mixes (fixed before running): box 0 / 0.25 / 0.5 / 1% x gotobi 1 / 2 / 3%. Challenge as
gjstrat.prop (P1 +8%, P2 +6%, static 10%, daily 4%, >= 3 days). A failed attempt is restarted
straight away with a new fee. Fee assumed $100 per attempt.
  fees per funded account  = fee / P(an attempt passes)
  months per funded account = average attempt length / P(pass)
All costs ($7/lot, swap +1%, 0.2 pip slippage).

    python run_prop_speed.py
"""
import os
from datetime import date

import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.prop import prop_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

FEE = 100
OUT = "results/prop_speed"

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    box, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                 [x for x in days if x.date() not in sk])
    d = daily_table(m)
    d = d[d.index >= pd.Timestamp("2010-01-01")]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d)) if t is not None]
    legs = []
    for tr in (box, got):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        legs.append((tr, account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()))
    mixes = {f"box {b:g}% + gotobi {g:g}%": (b, g) for b in (0, 0.25, 0.5, 1.0) for g in (1, 2, 3)}
    tab = prop_table(m, legs, mixes)
    tab["fees per funded account $"] = FEE / (tab["pass eventually %"] / 100)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    tab = tab.sort_values("months per funded account")
    tab.to_csv(f"{OUT}/summary.csv")
    cols = ["pass ≤1 month %", "pass ≤2 months %", "pass ≤3 months %", "pass eventually %", "fails by daily limit %",
            "avg days per attempt", "fees per funded account $", "months per funded account", "max DD %"]
    open(f"{OUT}/REPORT.md", "w").write("# Fastest / cheapest route to a funded account (USDJPY box + gotobi)\n\n"
                                        f"Fee ${FEE} per attempt; failed attempts restart at once. Rules in run_prop_speed.py.\n\n"
                                        + fmt_table(tab[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(tab[cols].round(1).to_string())
