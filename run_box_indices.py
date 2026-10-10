"""Box breakout on JPN225 and Nasdaq 100 (2011-2026, never used to design any rule).

Pre-declared setups per index (Version B engine: OCO stops at the box, re-entry at the box level,
SL = 1 x box + spread, max 2 trades/day, trades may run overnight):
  1. green box unchanged: 05:00-06:00 IST box, orders to 11:00 IST, RR 9, BE 3R
  2. open-hour box: first hour of the cash session, RR 9, BE 3R
       JPN225: 09:00-10:00 JST (05:30 IST), orders to 15:00 JST
       Nasdaq: 09:30-10:30 New York (DST-aware), orders to 12:00 New York
  3. open-hour box, RR 2, no break-even
Costs: slippage per stop fill (JPN225 2 pt, Nasdaq 0.25 pt), no commission, overnight
financing 3% a year of the price per rollover day (17:00 NY, Wednesday x3), both sides.
Pass rule, fixed before running: avg R > 0 with t >= 2 over 2011-2026, and positive in more
than half of the years.

    python run_box_indices.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/box_indices"
SLIP = {"JPNIDXJPY": 2.0, "USATECHIDXUSD": 0.25}
FIN = 0.03 / 365
NY = "America/New_York"


def setups(sym):
    green = dict(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0)
    if sym == "JPNIDXJPY":
        op = dict(box_start_min=330, box_len=60, order_hours=5.0)
    else:                                                 # filled per day (DST) in run_setup
        op = dict(box_len=60, order_hours=1.5)
    return {"1 green box (05:00 IST)": (green, None),
            "2 open-hour box RR9 BE3R": ({**green, **op}, sym),
            "3 open-hour box RR2 no BE": ({**green, **op, "rr": 2, "be_trigger": None}, sym)}


def run_setup(m, kw, open_sym, days):
    """Version B trades; Nasdaq's open-hour box moves with US daylight saving."""
    groups = [(kw, days)]
    if open_sym == "USATECHIDXUSD":
        dst = [d for d in days if pd.Timestamp(d).tz_localize(NY).dst() != pd.Timedelta(0)]
        dset = set(dst)
        std = [d for d in days if d not in dset]
        groups = [({**kw, "box_start_min": 1140}, dst), ({**kw, "box_start_min": 1200}, std)]   # 19:00 / 20:00 IST
    out = []
    for p_kw, ds in groups:
        _, probe = run(m, Params(**{**p_kw, "rr": 2, "be_trigger": None}), ds)
        sk = {x for x, _ in probe.skipped_dates}
        tr, _ = run(m, Params(**p_kw), [x for x in ds if x.date() not in sk])
        out += tr
    return sorted(out, key=lambda t: (t.entry_i, t.exit_i))


def net_r(m, sym, trades):
    r = []
    for t in trades:
        nights = SwapModel.rollovers(m.ts(t.entry_i), m.ts(t.exit_i))["days"].sum()
        cost = SLIP[sym] * (1 + (t.reason in ("SL", "BE"))) + FIN * nights * t.entry
        r.append(t.r - cost / t.risk)
    return np.array(r)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for sym in SLIP:
        m = build_market(sym, date(2011, 1, 2), date(2026, 10, 7), "data/raw",
                         f"data/{sym.lower()}_2011-01-02_2026-10-07.npz")
        days = trading_days(m, start="2011-01-03")
        for name, (kw, open_sym) in setups(sym).items():
            tr = run_setup(m, kw, open_sym, days)
            r = net_r(m, sym, tr)
            yrs = pd.Series(r, index=[t.day.year for t in tr]).groupby(level=0).sum()
            ok = r.mean() > 0 and tstat(r) >= 2 and (yrs > 0).mean() > 0.5
            rows.append({"index": sym, "setup": name, "trades": len(r), "win %": (r > 0).mean() * 100,
                         "avg R": r.mean(), "t": tstat(r), "years +": f"{(yrs > 0).sum()}/{len(yrs)}",
                         "pass": ok})
            print(rows[-1], flush=True)
    res = pd.DataFrame(rows).set_index(["index", "setup"])
    res.to_csv(f"{OUT}/summary.csv")
    show = res.copy()
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Index · setup"
    open(f"{OUT}/REPORT.md", "w").write(
        "# Box breakout on JPN225 and Nasdaq 100, 2011–2026\n\nSetups, costs and pass rule in "
        "run_box_indices.py (all fixed before running).\n\n" + fmt_table(show, ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
