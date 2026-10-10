"""Alpha Capital 'Alpha Swing' 2-step challenge with the vol-filtered USDJPY box + gotobi.

Rules as reported for Alpha Swing (verify in the Alpha dashboard): Phase 1 +10%, Phase 2 +5%,
10% static max loss, 5% daily loss, >= 3 trading days per phase; run with and without a 40%
consistency rule (no single day > 40% of the phase's profit; otherwise keep trading).
Risk mixes fixed before running. Challenges start on every trading day 2011-01..2025-10;
a failed attempt restarts at once (fee $100 assumed). All costs ($7/lot, swap +1%, 0.2 pip).

    python run_prop_alpha_swing.py
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

OUT = "results/prop_alpha_swing"
RULES = dict(targets=(0.10, 0.05), max_dd=0.10, daily=0.05, min_days=3)
MIXES = {f"vol-box {b:g}% + gotobi {g:g}%": (b, g) for b, g in
         ((0.25, 2), (0.25, 3), (0.25, 4), (0.5, 2), (0.5, 3), (0.5, 4))}

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
    med = d["atr20"].rolling(250, min_periods=250).median()
    box = [t for t in box if d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2011-01-01")])) if t is not None]
    legs = []
    for tr in (box, got):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        legs.append((tr, account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()))
    out = []
    for label, extra in (("no consistency rule", {}), ("40% consistency rule", {"consistency": 0.4})):
        tab = prop_table(m, legs, MIXES, **RULES, **extra)
        tab.insert(0, "rules", label)
        tab["fees per funded account $"] = 100 / (tab["pass eventually %"] / 100)
        tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
        out.append(tab)
    res = pd.concat(out)
    res.to_csv(f"{OUT}/summary.csv")
    cols = ["rules", "pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
            "fails by daily limit %", "median months to pass", "months per funded account", "fees per funded account $"]
    open(f"{OUT}/REPORT.md", "w").write("# Alpha Capital — Alpha Swing challenge with vol-box + gotobi (USDJPY)\n\n"
                                        "Rules (as reported; verify): P1 +10%, P2 +5%, 10% static max loss, 5% daily, "
                                        "≥3 days per phase. Details in run_prop_alpha_swing.py.\n\n" + fmt_table(res[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(1).to_string())
