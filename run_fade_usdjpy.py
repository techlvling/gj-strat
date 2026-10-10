"""Version C (fade) on USDJPY with the box-sized stop, 2010-2026.

The first box breakout after 06:00 IST is VIRTUAL (no trade). If that virtual trade hits its
SL (1 x box + spread from its entry), a real trade opens there in the SL direction, SL 1 x box,
TP = RR x SL, optional break-even at 3R (+1/6 SL), the engine's Version C rules otherwise
(virtual TP / BE hit -> no trade; max 2 real trades a day). Pre-declared grid (12):
RR 2 / 3 / 5 / 9  x  BE off / 3R (only RR > 3)  x  entry window: virtual SL before 11:00 IST / any time.
Reference: the green box (Version B) and its re-entry trades only.

Selection, fixed before running: best design (2010-2017) t; it counts only if design t >= 2 and
avg R > 0 in check (2018-2023) AND holdout (2024-2026). Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_fade_usdjpy.py
"""
from __future__ import annotations

import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

OUT = "results/fade_usdjpy"
M = DAYS = SWAP = None


def grid():
    g = []
    for rr in (2, 3, 5, 9):
        for be in ((None, 3) if rr > 3 else (None,)):
            for exp in (True, False):
                g.append((f"C RR{rr} BE{'-' if be is None else '3R'} {'by 11:00' if exp else 'any time'}",
                          dict(rr=rr, be_trigger=be, version="C", fade_expiry_11=exp)))
    g.append(("ref: green box B (all trades)", dict(rr=9, be_trigger=3, version="B")))
    return g


def evaluate(item):
    name, kw = item
    p = Params(sl_pips=30, be_plus=5, sl_box_mult=1.0, **kw)
    tr, _ = run(M, p, DAYS)
    out = [(name, tr)]
    if name.startswith("ref"):
        out.append(("ref: green box B re-entries only", [t for t in tr if t.num == 2]))
    rows = []
    for nm, ts in out:
        ts = sorted(ts, key=lambda t: (t.exit_i, t.entry_i))
        lg = account(ts, M, 10_000, risk_pct=0.5, commission=7, swap=SWAP, sym="USDJPY", slippage_pips=0.2)
        r, day = lg["R"].to_numpy(), pd.to_datetime(lg["day"])
        row = {"setup": nm}
        for per, (a, b) in PERIODS.items():
            x = r[np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))]
            row.update({f"{per} trades": len(x), f"{per} win %": (x > 0).mean() * 100, f"{per} avg R": x.mean(),
                        f"{per} t": tstat(x)})
        rows.append(row)
    return rows


def main():
    global M, DAYS, SWAP
    os.makedirs(OUT, exist_ok=True)
    M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(M, start="2010-01-01")
    _, pr = run(M, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    DAYS = [x for x in days if x.date() not in sk]
    SWAP = SwapModel.from_fred("rates", 1.0)
    with Pool(os.cpu_count()) as pool:
        out = pool.map(evaluate, grid())
    res = pd.DataFrame([r for rows in out for r in rows]).set_index("setup")
    res.to_csv(f"{OUT}/grid.csv")
    fades = res[res.index.str.startswith("C ")]
    best = fades["design t"].idxmax()
    ok = {"design t >= 2": fades.loc[best, "design t"] >= 2,
          "check avg R > 0": fades.loc[best, "check avg R"] > 0,
          "holdout avg R > 0": fades.loc[best, "holdout avg R"] > 0}
    verdict = "PASS" if all(ok.values()) else "FAIL"
    cols = [c for c in res.columns if c.endswith(("trades", "win %", "avg R", " t"))]
    rep = ["# Version C (fade) on USDJPY, box-sized stop, 2010–2026\n",
           "Grid, costs and selection rule in run_fade_usdjpy.py (fixed before running).\n",
           f"**Design-best: {best}** — " + ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in ok.items()) +
           f" → **{verdict}**\n", fmt_table(res[cols].sort_values("design t", ascending=False), ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(res[["design trades", "design win %", "design avg R", "design t", "check avg R", "check t",
               "holdout avg R", "holdout t"]].sort_values("design t", ascending=False).round(3).to_string())
    print(best, ok, verdict)


if __name__ == "__main__":
    main()
