"""Costs and gotobi refinements (USDJPY 2010-2026).

A. Cost sensitivity of vol-box, gotobi, fade: commission $0 / 3.5 / 7 (base) / 10 per lot round turn x
   slippage 0 / 0.2 (base) / 0.5 / 1.0 pip per stop fill (gotobi: entry is a market order -> slippage
   charged on its SL exits only, as in the base runs).
B. Gotobi with a sell LIMIT instead of market: limit at the 09:55 JST bid + 1 / + 2 pips, valid 5 / 15 min;
   unfilled -> no trade. (Pre-declared; accepted if avg R beats market entry in all three periods.)
C. Gotobi vol filter: only when ATR20 >= its rolling 250-day median, and the reverse (below median).
   Accepted if avg R beats unfiltered gotobi in all three periods.
Periods: 2010-17 / 2018-23 / 2024-26. Swap +1% everywhere.

    python run_costs_gotobi_vol.py
"""
import os
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import per_stats

OUT = "results/costs_gotobi"

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    vbox = [t for t in box if hot(t)]
    gsig = gotobi_short(m, d[d.index >= pd.Timestamp("2010-01-01")])
    got = [t for t in (simulate(m, s) for s in gsig) if t is not None]

    def R(tr, comm=7, slip=0.2):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        return account(tr, m, 10_000, commission=comm, swap=sw, sym="USDJPY", slippage_pips=slip)["R"].to_numpy(), \
            pd.DatetimeIndex([t.day for t in sorted(tr, key=lambda t: (t.exit_i, t.entry_i))])

    # A. cost grid
    rows = []
    for nm, tr in (("vol-box", vbox), ("gotobi", got), ("fade", fade)):
        for comm in (0, 3.5, 7, 10):
            for slip in (0, 0.2, 0.5, 1.0):
                r, dd = R(tr, comm, slip)
                last3 = r[np.asarray(dd >= pd.Timestamp("2023-10-07"))]
                rows.append({"strategy": nm, "commission $/lot": comm, "slippage pips": slip, "avg R 2010-26": r.mean(),
                             "avg R last 3 years": last3.mean()})
    cost = pd.DataFrame(rows)
    cost.to_csv(f"{OUT}/cost_grid.csv", index=False)

    # B. limit entry for gotobi, C. vol filter
    def stats(name, tr):
        r, dd = R(tr)
        return {"variant": name, "trades": len(r), "win %": (r > 0).mean() * 100, **per_stats(r, dd)}
    ref = stats("gotobi market entry (current)", got)
    rows2 = [ref]
    for up in (1, 2):
        for wait in (5, 15):
            lim = []
            for s in gsig:
                if s.start_i <= 0 or s.start_i >= m.n:
                    continue
                lvl = m.bo[s.start_i] + up * m.pip
                lim.append(replace(s, kind="limit", level=lvl, expiry_i=s.start_i + wait))
            rows2.append(stats(f"limit +{up} pip, valid {wait} min", [t for t in (simulate(m, s) for s in lim) if t is not None]))
    rows2.append(stats("vol filter: ATR20 >= 250-day median", [t for t in got if hot(t)]))
    rows2.append(stats("vol filter: ATR20 < 250-day median", [t for t in got if not hot(t) and not np.isnan(med.get(t.day, np.nan))]))
    g = pd.DataFrame(rows2).set_index("variant")
    g["beats current in every period"] = [None] + [bool(all(g.loc[i, f"{p} avg R"] > ref[f"{p} avg R"] for p in ("design", "check", "holdout")))
                                                   for i in g.index[1:]]
    g.to_csv(f"{OUT}/gotobi_variants.csv")
    pv = cost.pivot_table(index=["strategy", "commission $/lot"], columns="slippage pips", values="avg R 2010-26").round(3)
    pv.columns = [f"slip {c:g}" for c in pv.columns]
    gcols = ["trades", "win %", "design avg R", "check avg R", "holdout avg R", "beats current in every period"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Costs and gotobi refinements (USDJPY 2010–2026)\n\nRules in run_costs_gotobi_vol.py.\n\n"
        "## A. Avg R per trade 2010–2026 by commission (rows) and slippage per stop fill (columns)\n\n"
        + fmt_table(pv.reset_index().set_index(["strategy", "commission $/lot"]), ".3f") +
        "\n\n## B–C. Gotobi limit entry and vol filter\n\n" + fmt_table(g[gcols], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(pv.to_string()); print(g[gcols].round(3).to_string())
