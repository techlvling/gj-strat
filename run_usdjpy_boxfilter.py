"""USDJPY Version B (SL = 1 x box, RR 9, BE 3R): skip days whose box is unusually small?

Pre-declared protocol (written before any result was seen):
  * filter: skip the day if its 05:00-05:59 IST box < k x median box of the previous 20 valid days
  * candidates: k = none, 0.3, 0.5, 0.7
  * costs: $7 per lot round turn + swap (1% markup) + 0.2 pip slippage per stop fill
  * pick ONE k on 2010-2017 by avg R; check it on 2018-2026

    python run_usdjpy_boxfilter.py     # needs data/usdjpy_2010-01-01_2026-10-07.npz
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import START_BAL, fmt_table, years_of
from run_usdjpy_sl import DESIGN_END, SYM, tstat

KS = [None, 0.3, 0.5, 0.7]
SLIP = 0.2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--out", default="results/usdjpy_boxfilter")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    m = build_market(SYM, date.fromisoformat(args.start), date.fromisoformat(args.end), "data/raw",
                     f"data/usdjpy_{args.start}_{args.end}.npz")
    days = trading_days(m, start=args.start)
    _, probe = run(m, Params(sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    days = [d for d in days if d.date() not in skipped]
    periods = {"design 2010–2017": lambda d: d < DESIGN_END, "check 2018–2026": lambda d: d >= DESIGN_END}
    swap = SwapModel.from_fred("rates", 1.0)

    rows = []
    for k in KS:
        p = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0,
                   min_box_rel=k)
        trades, cnt = run(m, p, days)
        for pname, inside in periods.items():
            pdays = [d for d in days if inside(d)]
            ts = [t for t in trades if inside(t.day)]
            lg = account(ts, m, START_BAL, commission=7, swap=swap, sym=SYM, slippage_pips=SLIP)
            half = account(ts, m, START_BAL, risk_pct=0.5, commission=7, swap=swap, sym=SYM,
                           slippage_pips=SLIP)
            s, s05 = stats(lg, START_BAL, years_of(pdays)), stats(half, START_BAL, years_of(pdays))
            traded_days = len({t.day for t in ts if t.num == 1})
            rows.append({"filter": "none" if k is None else f"box < {k:g} × median",
                         "period": pname, "days traded": traded_days, "trades": s["trades"],
                         "win rate %": s["win_rate"], "avg R": s["avg_R"], "t": s["sqn"],
                         "losing streak": s["longest_losing_streak"],
                         "max DD % (1%)": s["max_dd_pct"], "max DD % (0.5%)": s05["max_dd_pct"],
                         "return % (0.5%)": s05["net_return_pct"], "per year % (0.5%)": s05["cagr_pct"]})
        print(f"k={k}: {cnt.skipped_small_box} days skipped as small", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(f"{args.out}/summary.csv", index=False)
    des = res[res.period.str.startswith("design")].set_index("filter")
    pick = des["avg R"].idxmax()
    chk = res[res.period.str.startswith("check")].set_index("filter").loc[pick]

    show = res.set_index(["period", "filter"])
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Period · filter"
    rep = ["# USDJPY Version B, RR 9, BE 3R, SL = 1 × box: relative small-box filter\n",
           "Protocol fixed before any result: skip the day if its box < k × median box of the previous "
           "20 tradable days; k = none, 0.3, 0.5, 0.7. All numbers after $7/lot, swap (+1% markup) and "
           f"{SLIP:g} pip slippage per stop fill. Pick on 2010–2017 by avg R; check on 2018–2026.\n",
           f"**Pick: {pick}.** Check 2018–2026: avg R {chk['avg R']:+.3f} (t {chk['t']:+.2f}), "
           f"{chk['return % (0.5%)']:+.0f}% at 0.5% risk, max DD {chk['max DD % (0.5%)']:.0f}%.\n",
           fmt_table(show, ".3f")]
    with open(f"{args.out}/REPORT.md", "w") as f:
        f.write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(res.round(3).to_string(index=False))
    print("PICK:", pick)


if __name__ == "__main__":
    main()
