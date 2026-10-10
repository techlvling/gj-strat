"""Intraday pattern search (flat by the New York close), 2010-2026.

Pre-declared grid, 20 setups per market:
  I1 London-open breakout of the 00:00-06:59 UTC range: SL 0.5 / 1 x range, TP 1R / 2R    (4)
  I2 previous-day high/low breakout 07:00-16:00 UTC: SL 0.25 / 0.5 x ATR20, TP 1R / 2R   (4)
  I3 NR7 / inside-day breakout of yesterday's range: SL = that range, TP 1R / 2R         (4)
  I4 New York opening-range breakout (09:30 + 30 / 60 min): SL = range, TP 1R / 2R       (4)
  I5 quiet-hours scalp 22:00-06:00 UTC, fade 15m closes outside Bollinger 2 / 2.5 sd,
     TP band middle, SL 0.15 / 0.3 x ATR20, exit 07:00 UTC                               (4)
Costs, periods and survival rule as run_patterns.py (design 2010-2017 avg R > 0 with t >= 2
AND check 2018-2023 avg R > 0). A setup counts as robust only if it survives on >= 2 markets.
Holdout 2024-2026 shown only for survivors.

    python run_patterns_intraday.py [--pairs USDJPY XAUUSD ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import (contraction_breakout, daily_table, london_breakout, night_reversion,
                              ny_orb, prevday_breakout)
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

PAIRS = ["USDJPY", "EURJPY", "GBPJPY", "EURUSD", "GBPUSD"]
OUT = "results/patterns_intraday"
rp.BUILDERS.update({"ldnbo": london_breakout, "pdbo": prevday_breakout, "contr": contraction_breakout,
                    "orb": ny_orb, "night": night_reversion})


def grid():
    g = []
    for sl in (0.5, 1.0):
        for rr in (1, 2):
            g.append((f"I1 ldn-breakout SL{sl:g}range TP{rr}R", "ldnbo", dict(sl_range=sl, rr=rr)))
    for sl in (0.25, 0.5):
        for rr in (1, 2):
            g.append((f"I2 prevday-breakout SL{sl:g}ATR TP{rr}R", "pdbo", dict(sl_atr=sl, rr=rr)))
    for kind in ("nr7", "inside"):
        for rr in (1, 2):
            g.append((f"I3 {kind}-breakout TP{rr}R", "contr", dict(kind=kind, rr=rr)))
    for mins in (30, 60):
        for rr in (1, 2):
            g.append((f"I4 ny-orb {mins}m TP{rr}R", "orb", dict(minutes=mins, rr=rr)))
    for bs in (2.0, 2.5):
        for sl in (0.15, 0.3):
            g.append((f"I5 night-scalp BB{bs:g} SL{sl:g}ATR", "night", dict(band_std=bs, sl_atr=sl)))
    return g


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="*", default=PAIRS)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    pairs, OUT = a.pairs, a.out
    os.makedirs(OUT, exist_ok=True)
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    frames = []
    for sym in pairs:
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
    n_surv = res.survives.groupby(level="setup").sum()
    res["markets surviving"] = res.index.get_level_values("setup").map(n_surv)
    res["robust"] = res.survives & (res["markets surviving"] >= 2)
    for c in [c for c in res.columns if c.startswith("holdout")]:
        res.loc[~res.survives, c] = np.nan
    res.to_csv(f"{OUT}/grid.csv")

    cols = ["design trades", "design win %", "design avg R", "design t", "check trades", "check win %",
            "check avg R", "check t", "survives", "robust"]
    show = res[cols].sort_values("design t", ascending=False)
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Setup · pair"
    surv = res[res.survives]
    rep = [f"# Intraday pattern search — {', '.join(pairs)}, 2010–2026\n",
           f"20 pre-declared setups per market, {len(res)} tests (see run_patterns_intraday.py). Costs: $7/lot, swap "
           "(+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 "
           "with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.\n",
           f"**Survivors: {len(surv)} of {len(res)}, robust (≥ 2 markets): {int(res.robust.sum())}.** "
           f"About {len(res) / 50:.0f} would pass by luck.\n",
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
