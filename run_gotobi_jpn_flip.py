"""Gotobi rule flipped on JPN225: BUY at 00:55 UTC (09:55 JST) on gotobi days, exit 06:00 UTC,
SL 0.25 x ATR20, no TP. Costs: 2 pt slippage per stop fill (exit at SL), no commission, no
overnight. Also re-shows the original SELL. Pass, fixed before running: avg R > 0 with t >= 2.

    python run_gotobi_jpn_flip.py
"""
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.patterns import daily_table, gotobi_short, simulate
from run_usdjpy_sl import tstat

m = build_market("JPNIDXJPY", date(2011, 1, 2), date(2026, 10, 7), "data/raw",
                 "data/jpnidxjpy_2011-01-02_2026-10-07.npz")
d = daily_table(m)
d = d[d.index >= pd.Timestamp("2011-01-02")]
lines = []
for side in ("BUY", "SELL"):
    sigs = [replace(s, side=side) for s in gotobi_short(m, d)]
    tr = [t for t in (simulate(m, s) for s in sigs) if t is not None]
    r = np.array([t.r - 2.0 * (1 + (t.reason == "SL")) / t.risk for t in tr])
    yrs = pd.Series(r, index=[t.day.year for t in tr]).groupby(level=0).sum()
    gross = np.array([t.r for t in tr])
    lines.append(f"| {side} | {len(r)} | {(r > 0).mean() * 100:.1f} | {gross.mean():+.3f} | {r.mean():+.3f} | "
                 f"{tstat(r):.2f} | {(yrs > 0).sum()}/{len(yrs)} | {'PASS' if r.mean() > 0 and tstat(r) >= 2 else 'FAIL'} |")
rep = ("# Gotobi on JPN225, flipped (buy) vs original (sell), 2011–2026\n\n"
       "| Side | Trades | Win % | Avg R before slippage | Avg R net | t | Years + | Verdict |\n"
       "|---|---|---|---|---|---|---|---|\n" + "\n".join(lines) + "\n")
open("results/gotobi_jpn_flip/REPORT.md", "w").write(rep)
print(rep)
