"""Flow / session pattern search on USDJPY, EURJPY, GBPJPY, EURUSD, GBPUSD 2010-2026.

Pre-declared grid (12 setups per pair, 60 tests), London / New York wall-clock times:
  F1 month-end fix: last trading day, 14:00 London, fade / follow the month-to-date move,
     exit 16:05 / 17:00 London, SL 0.5 x ATR20                                     (4)
  F2 4pm London fix fade: 15:00-16:00 move >= 0.2 x ATR20 -> fade at 16:00,
     exit 17:00 / 18:00 London, SL 0.25 / 0.5 x ATR20                             (4)
  F3 NY-open momentum: direction of 09:30-10:00 NY, entry 10:00 NY,
     exit 15:00 / 16:00 NY, SL 0.25 / 0.5 x ATR20                                 (4)
Costs, periods and survival rule as run_patterns.py (design 2010-2017 avg R > 0 with t >= 2
AND check 2018-2023 avg R > 0; holdout 2024-2026 shown only for survivors).

    python run_patterns_flow.py
"""
from __future__ import annotations

import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import daily_table, london_fix_fade, month_end_fix, ny_open_momentum
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

PAIRS = ["USDJPY", "EURJPY", "GBPJPY", "EURUSD", "GBPUSD"]
OUT = "results/patterns_flow"
rp.BUILDERS.update({"monthend": month_end_fix, "ldnfix": london_fix_fade, "nyopen": ny_open_momentum})


def grid():
    g = []
    for direction in ("fade", "follow"):
        for ex in ((16, 5), (17, 0)):
            g.append((f"F1 month-end {direction} exit {ex[0]}:{ex[1]:02d}LDN", "monthend",
                      dict(direction=direction, exit_at=ex)))
    for ex in ((17, 0), (18, 0)):
        for sl in (0.25, 0.5):
            g.append((f"F2 ldn-fix fade exit {ex[0]}:00LDN SL{sl:g}ATR", "ldnfix", dict(exit_at=ex, sl_atr=sl)))
    for ex in ((15, 0), (16, 0)):
        for sl in (0.25, 0.5):
            g.append((f"F3 ny-open mom exit {ex[0]}:00NY SL{sl:g}ATR", "nyopen", dict(exit_at=ex, sl_atr=sl)))
    return g


def main():
    os.makedirs(OUT, exist_ok=True)
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    frames = []
    for sym in PAIRS:
        rp.SYM = sym
        rp.M = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                            f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(rp.M)
        rp.D = d[d.index >= pd.Timestamp("2010-01-01")]
        with Pool(os.cpu_count()) as pool:                 # forked after the globals are set
            out = pool.map(rp.evaluate, grid())
        res = pd.DataFrame([r for r, _ in out])
        res.insert(0, "pair", sym)
        frames.append(res)
        print(sym, "done", flush=True)
    res = pd.concat(frames).set_index(["setup", "pair"])
    res["survives"] = (res["design avg R"] > 0) & (res["design t"] >= 2) & (res["check avg R"] > 0)
    for c in [c for c in res.columns if c.startswith("holdout")]:
        res.loc[~res.survives, c] = np.nan
    res.to_csv(f"{OUT}/grid.csv")

    cols = ["design trades", "design win %", "design avg R", "design t", "check trades", "check avg R",
            "check t", "survives"]
    show = res[cols].sort_values("design t", ascending=False)
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Setup · pair"
    surv = res[res.survives]
    rep = ["# Flow / session pattern search — 5 pairs, 2010–2026\n",
           "12 pre-declared setups per pair, 60 tests (see run_patterns_flow.py). Costs: $7/lot, swap "
           "(+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 "
           "with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.\n",
           f"**Survivors: {len(surv)} of {len(res)}.** With 60 tries, 1–2 would pass by luck.\n",
           fmt_table(show, ".3f")]
    if len(surv):
        hcols = [c for c in res.columns if c.startswith(("design", "check", "holdout"))]
        t = surv[hcols].T
        t.columns = [f"{a} · {b}" for a, b in t.columns]
        rep += ["\n## Survivors incl. holdout\n", fmt_table(t, ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(show.round(3).to_string())
    if len(surv):
        print(surv[[c for c in res.columns if c.startswith("holdout")]].round(3).to_string())


if __name__ == "__main__":
    main()
