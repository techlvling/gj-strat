"""Robustness of the box volatility filter + prop test with gotobi (USDJPY 2010-2026).

Part 1 - neighbours of the accepted filter (ATR20 >= rolling 250-day median): window 125 / 250 / 500
days x threshold 0.9 / 1.0 / 1.1 x median. A real effect should hold across the whole block.
Part 2 - prop challenge (gjstrat.prop): vol-filtered box (250, 1.0) at 0.25 / 0.5 / 1% with
gotobi 2% and 3%, against the current plans. Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_box_vol_check.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.prop import prop_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_box_dd_filters import stats

OUT = "results/box_dd_filters"

if __name__ == "__main__":
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    tr, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                [x for x in days if x.date() not in sk])
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    R = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    day = pd.DatetimeIndex([t.day for t in tr])
    d = daily_table(m)
    atr = d["atr20"].reindex(day).to_numpy()

    def keep(win, k):
        return atr >= k * d["atr20"].rolling(win, min_periods=win).median().reindex(day).to_numpy()

    rows = []
    for win in (125, 250, 500):
        for k in (0.9, 1.0, 1.1):
            mask = keep(win, k)
            rows.append({"window": win, "threshold x median": k, "kept %": mask.mean() * 100, **stats(R[mask], day[mask])})
    rob = pd.DataFrame(rows).set_index(["window", "threshold x median"])
    rob.to_csv(f"{OUT}/vol_neighbours.csv")

    d2 = d[d.index >= pd.Timestamp("2010-01-01")]
    got = sorted([t for t in (simulate(m, s) for s in gotobi_short(m, d2)) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
    Rg = account(got, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    mask = keep(250, 1.0)
    legs = [(got, Rg), ([t for t, k in zip(tr, mask) if k], R[mask]), (tr, R)]
    mixes = {"current: box 0.25% + gotobi 2%": (2, 0, 0.25), "challenge: box 0.25% + gotobi 3%": (3, 0, 0.25),
             "gotobi 2% alone": (2, 0, 0)}
    for g in (2, 3):
        for b in (0.25, 0.5, 1.0):
            mixes[f"vol-box {b:g}% + gotobi {g}%"] = (g, b, 0)
    tab = prop_table(m, legs, mixes)
    tab["fees per funded account $"] = 100 / (tab["pass eventually %"] / 100)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    tab.to_csv(f"{OUT}/prop_vol.csv")
    pcols = ["pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
             "months per funded account", "fees per funded account $", "max DD %", "per year %"]
    rcols = ["kept %"] + [f"{p} {c}" for p in ("design", "check", "holdout") for c in ("avg R", "max DD % (0.5%)")]
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Robustness: neighbouring vol-filter settings\n\n" + fmt_table(rob[rcols], ".2f") +
                "\n\n## Prop challenge with the vol-filtered box\n\n" + fmt_table(tab[pcols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(rob[rcols].round(3).to_string())
    print(tab[pcols].round(1).to_string())
