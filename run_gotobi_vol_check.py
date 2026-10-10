"""Gotobi vol filter: robustness (window 125 / 250 / 500 x threshold 0.9 / 1.0 / 1.1) and the Alpha
Swing challenge with vol-filtered box + vol-filtered gotobi (+ fade). Same rules/costs as before.

    python run_gotobi_vol_check.py
"""
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
from run_edge_hunt import per_stats

OUT = "results/costs_gotobi"
RULES = dict(targets=(0.10, 0.05), max_dd=0.10, daily=0.05, min_days=3)

if __name__ == "__main__":
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    d = daily_table(m)
    got = sorted([t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2011-01-01")])) if t is not None],
                 key=lambda t: (t.exit_i, t.entry_i))
    Rg = account(got, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    gd = pd.DatetimeIndex([t.day for t in got])
    atr = d["atr20"].reindex(gd).to_numpy()
    rows = []
    for win in (125, 250, 500):
        for k in (0.9, 1.0, 1.1):
            keep = atr >= k * d["atr20"].rolling(win, min_periods=win).median().reindex(gd).to_numpy()
            rows.append({"window": win, "threshold x median": k, "kept %": keep.mean() * 100, **per_stats(Rg[keep], gd[keep])})
    rob = pd.DataFrame(rows).set_index(["window", "threshold x median"])
    rob.to_csv(f"{OUT}/gotobi_vol_neighbours.csv")
    print(rob[["kept %", "design avg R", "check avg R", "holdout avg R"]].round(3).to_string())

    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    def net(tr):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        return tr, account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    legs = [net([t for t in box if hot(t)]), net(got), net([t for t in got if hot(t)]), net(fade)]
    mixes = {"current: vol-box 0.25% + gotobi 3% + fade 0.5%": (0.25, 3, 0, 0.5),
             "vol-box 0.25% + vol-gotobi 3% + fade 0.5%": (0.25, 0, 3, 0.5),
             "vol-box 0.25% + vol-gotobi 4% + fade 0.5%": (0.25, 0, 4, 0.5),
             "vol-box 0.25% + gotobi 2% + vol-gotobi +2% (4% on hot days) + fade 0.5%": (0.25, 2, 2, 0.5),
             "vol-box 0.25% + vol-gotobi 3%": (0.25, 0, 3, 0)}
    tab = prop_table(m, legs, mixes, **RULES)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    tab.to_csv(f"{OUT}/swing_vol_gotobi.csv")
    cols = ["pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
            "median months to pass", "months per funded account", "max DD %"]
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Gotobi vol filter: neighbouring settings\n\n" + fmt_table(rob[["kept %", "design avg R", "check avg R", "holdout avg R"]], ".3f")
                + "\n\n## Alpha Swing challenge with vol-filtered gotobi\n\n" + fmt_table(tab[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(tab[cols].round(1).to_string())
