"""Gotobi + the USDJPY box traded ONLY on gotobi days, with every RR (2010-2026).

Part 1 - box (Version B, SL 1 x box, 05:00 IST box) on gotobi days only, pre-declared grid:
RR 2..10 x break-even off / 3R (+1/6 SL, only where RR > 3) = 16 variants. Selection: best design
(2010-2017) t; it counts only if design t >= 2 and avg R > 0 in check (2018-2023) and holdout
(2024-2026). Costs: $7/lot, swap +1%, 0.2 pip slippage.
Part 2 - prop challenge (gjstrat.prop): gotobi 2% + gotobi-day box (design-best variant) at
0.25 / 0.5 / 1%, vs the current plan (box on all days 0.25% + gotobi 2%) and gotobi 2% alone.

    python run_gotobi_box_rr.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, is_gotobi, simulate
from gjstrat.prop import prop_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

OUT = "results/gotobi_box_rr"
M = DAYS = GDAYS = SWAP = None


def grid():
    return [(rr, be) for rr in range(2, 11) for be in ((None, 3) if rr > 3 else (None,))]


def name(rr, be):
    return f"box RR{rr} BE{'-' if be is None else '3R'}"


def box(rr, be, days):
    tr, _ = run(M, Params(rr=rr, sl_pips=30, be_trigger=be, be_plus=5, version="B", sl_box_mult=1.0), days)
    return sorted(tr, key=lambda t: (t.exit_i, t.entry_i))


def net(tr):
    lg = account(tr, M, 10_000, risk_pct=0.5, commission=7, swap=SWAP, sym="USDJPY", slippage_pips=0.2)
    assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
    return lg["R"].to_numpy()


def evaluate(item):
    rr, be = item
    tr = box(rr, be, GDAYS)
    r, day = net(tr), pd.DatetimeIndex([t.day for t in tr])
    row = {"setup": name(rr, be)}
    for per, (a, b) in PERIODS.items():
        x = r[np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))]
        row.update({f"{per} trades": len(x), f"{per} win %": (x > 0).mean() * 100, f"{per} avg R": x.mean(),
                    f"{per} t": tstat(x)})
    row.update({"all avg R": r.mean(), "all t": tstat(r)})
    return row


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(M, start="2010-01-01")
    _, pr = run(M, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    DAYS = [x for x in days if x.date() not in sk]
    GDAYS = [x for x in DAYS if is_gotobi(x)]
    SWAP = SwapModel.from_fred("rates", 1.0)
    with Pool(4) as pool:
        res = pd.DataFrame(pool.map(evaluate, grid())).set_index("setup")
    best = res["design t"].idxmax()
    ok = {"design t >= 2": res.loc[best, "design t"] >= 2, "check avg R > 0": res.loc[best, "check avg R"] > 0,
          "holdout avg R > 0": res.loc[best, "holdout avg R"] > 0}
    verdict = "PASS" if all(ok.values()) else "FAIL"
    res.to_csv(f"{OUT}/grid.csv")
    print(res.round(3).to_string())
    print(best, ok, verdict)

    rr_b, be_b = next(g for g in grid() if name(*g) == best)
    d = daily_table(M)
    d = d[d.index >= pd.Timestamp("2010-01-01")]
    got = sorted([t for t in (simulate(M, s) for s in gotobi_short(M, d)) if t is not None],
                 key=lambda t: (t.exit_i, t.entry_i))
    gbox = box(rr_b, be_b, GDAYS)
    green = box(9, 3, DAYS)
    legs = [(got, net(got)), (gbox, net(gbox)), (green, net(green))]
    mixes = {"current: box all days 0.25% + gotobi 2%": (2.0, 0.0, 0.25),
             "gotobi 2% alone": (2.0, 0.0, 0.0),
             f"gotobi 2% + gotobi-day {best} 0.25%": (2.0, 0.25, 0.0),
             f"gotobi 2% + gotobi-day {best} 0.5%": (2.0, 0.5, 0.0),
             f"gotobi 2% + gotobi-day {best} 1%": (2.0, 1.0, 0.0)}
    tab = prop_table(M, legs, mixes)
    tab.to_csv(f"{OUT}/prop.csv")
    cols = [f"{p} {c}" for p in PERIODS for c in ("trades", "win %", "avg R", "t")] + ["all avg R", "all t"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Gotobi + box on gotobi days only, every RR (USDJPY 2010–2026)\n\nGrid, costs and rules in "
        f"run_gotobi_box_rr.py.\n\n**Design-best box: {best}** — " +
        ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in ok.items()) + f" → **{verdict}**\n\n" +
        fmt_table(res[cols].sort_values("design t", ascending=False), ".3f") +
        "\n\n## Prop challenge\n\n" + fmt_table(tab, ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(tab.round(1).to_string())
