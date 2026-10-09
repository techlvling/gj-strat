"""Home-hours drift test on USDJPY, EURJPY, GBPJPY, EURUSD, GBPUSD 2010-2026.

Idea (Ranaldo 2009, Breedon & Ranaldo 2013; popular on r/algotrading / FX seasonality write-ups):
a currency tends to weaken during its own business hours and firm during foreign hours.
Sources disagree on the sign for some pairs, so both directions are pre-declared.

Pre-declared grid (40 tests), local wall-clock times, weekdays, market in / time out:
  H1 Tokyo   09:00-15:00 JST  : USDJPY, EURJPY, GBPJPY   (JPY home)       home-weak = BUY
  H2 Europe  08:00-13:00 LDN  : EURUSD, GBPUSD, EURJPY, GBPJPY (EUR/GBP home) home-weak = SELL
  H3 US      12:00-16:30 NY   : EURUSD, GBPUSD, USDJPY   (USD home, after London) home-weak =
                                BUY EURUSD/GBPUSD, SELL USDJPY
  x direction home-weak / home-strong x SL 0.5 / 1.0 x ATR20 (wide: mostly time exits)
Costs, periods and survival rule as run_patterns.py (design 2010-2017 avg R > 0 with t >= 2
AND check 2018-2023 avg R > 0; holdout 2024-2026 shown only for survivors).
Also reported: raw cost-free drift of each window in pips (design and check only).

    python run_patterns_hours.py
"""
from __future__ import annotations

import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

import run_patterns as rp
from gjstrat.data import build_market
from gjstrat.patterns import LDN, NY, daily_table, home_hours, local_idx
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

PAIRS = ["USDJPY", "EURJPY", "GBPJPY", "EURUSD", "GBPUSD"]
OUT = "results/patterns_hours"
TKY = "Asia/Tokyo"
rp.BUILDERS.update({"home": home_hours})

# window: (label, start, end, tz, {pair: home-weak side})
WINDOWS = [
    ("H1 tokyo", (9, 0), (15, 0), TKY, {"USDJPY": "BUY", "EURJPY": "BUY", "GBPJPY": "BUY"}),
    ("H2 europe", (8, 0), (13, 0), LDN, {"EURUSD": "SELL", "GBPUSD": "SELL", "EURJPY": "SELL",
                                         "GBPJPY": "SELL"}),
    ("H3 us", (12, 0), (16, 30), NY, {"EURUSD": "BUY", "GBPUSD": "BUY", "USDJPY": "SELL"}),
]
FLIP = {"BUY": "SELL", "SELL": "BUY"}


def grid(sym):
    g = []
    for label, a, b, tz, sides in WINDOWS:
        if sym not in sides:
            continue
        for how in ("home-weak", "home-strong"):
            side = sides[sym] if how == "home-weak" else FLIP[sides[sym]]
            for sl in (0.5, 1.0):
                g.append((f"{label} {how} {side} SL{sl:g}ATR", "home",
                          dict(start=a, end=b, tz=tz, side=side, sl_atr=sl)))
    return g


def raw_drift(m, d, sym):
    """Cost-free bid move over each window, in pips, signed so + = home currency weakened."""
    rows = []
    for label, a, b, tz, sides in WINDOWS:
        if sym not in sides:
            continue
        sgn = 1 if sides[sym] == "BUY" else -1
        mv = {}
        for day in d.index[d.index.dayofweek < 5]:
            i, j = local_idx(m, day, *a, tz), local_idx(m, day, *b, tz)
            if 0 <= i and j < m.n:
                mv[day] = sgn * (m.bo[j] - m.bo[i]) / m.pip
        s = pd.Series(mv)
        row = {"window · pair": f"{label} · {sym}"}
        for p in ("design", "check"):
            lo, hi = rp.PERIODS[p]
            x = s[(s.index >= lo) & (s.index <= hi)].to_numpy()
            row.update({f"{p} days": len(x), f"{p} mean pips": x.mean(), f"{p} t": tstat(x)})
        rows.append(row)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    rp.SWAP = SwapModel.from_fred("rates", 1.0)
    frames, drift = [], []
    for sym in PAIRS:
        rp.SYM = sym
        rp.M = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                            f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(rp.M)
        rp.D = d[d.index >= pd.Timestamp("2010-01-01")]
        drift += raw_drift(rp.M, rp.D, sym)
        g = grid(sym)
        with Pool(os.cpu_count()) as pool:                 # forked after the globals are set
            out = pool.map(rp.evaluate, g)
        res = pd.DataFrame([r for r, _ in out])
        res.insert(0, "pair", sym)
        frames.append(res)
        print(sym, "done", flush=True)
    res = pd.concat(frames).set_index(["setup", "pair"])
    res["survives"] = (res["design avg R"] > 0) & (res["design t"] >= 2) & (res["check avg R"] > 0)
    for c in [c for c in res.columns if c.startswith("holdout")]:
        res.loc[~res.survives, c] = np.nan
    res.to_csv(f"{OUT}/grid.csv")
    drift = pd.DataFrame(drift).set_index("window · pair")
    drift.to_csv(f"{OUT}/raw_drift.csv")

    cols = ["design trades", "design win %", "design avg R", "design t", "check trades", "check avg R",
            "check t", "survives"]
    show = res[cols].sort_values("design t", ascending=False)
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Setup · pair"
    surv = res[res.survives]
    rep = ["# Home-hours drift test — 5 pairs, 2010–2026\n",
           f"{len(res)} pre-declared tests (see run_patterns_hours.py). Costs: $7/lot, swap (+1% markup), "
           "0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 "
           "AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.\n",
           f"**Survivors: {len(surv)} of {len(res)}.** Opposite directions of one window are near mirror "
           "images, so about 1 would pass by luck.\n",
           "## Raw drift before costs (+ = home currency weakened), pips per day\n",
           fmt_table(drift, ".2f"),
           "\n## Tradeable version (after costs)\n",
           fmt_table(show, ".3f")]
    if len(surv):
        hcols = [c for c in res.columns if c.startswith(("design", "check", "holdout"))]
        t = surv[hcols].T
        t.columns = [f"{a} · {b}" for a, b in t.columns]
        rep += ["\n## Survivors incl. holdout\n", fmt_table(t, ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(drift.round(2).to_string())
    print(show.round(3).to_string())
    if len(surv):
        print(surv[[c for c in res.columns if c.startswith("holdout")]].round(3).to_string())


if __name__ == "__main__":
    main()
