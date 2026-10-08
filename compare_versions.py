"""Base settings, side by side: Version A, B, C (fade the first break) and C without the
11:00 expiry on the reversal stop. Same days and the same in-sample / out-of-sample split as
run_backtest.py.

    python compare_versions.py            # needs data/gbpjpy_1m.npz from run_backtest.py
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from gjstrat.accounting import account, equity_curve, stats
from gjstrat.data import load_market
from gjstrat.engine import Params, run, trading_days
from run_backtest import (BASE, START, START_BAL, breakdowns, clean_log, plot_equity, split_days,
                          stat_table, years_of)

VERSIONS = {
    "A (breakout, 6-bar re-entry)": Params(**BASE, version="A"),
    "B (breakout, range re-entry)": Params(**BASE, version="B"),
    "C (fade, stop expires 11:00)": Params(**BASE, version="C"),
    "C (fade, no 11:00 expiry)": Params(**BASE, version="C", fade_expiry_11=False),
}
COUNTS = [("initial_expired", "Neither side broke by 11:00"),
          ("fade_cancel_tp", "C: virtual breakout hit TP → reversal cancelled"),
          ("fade_cancel_be", "C: virtual breakout hit BE stop → reversal cancelled"),
          ("fade_expired", "C: virtual SL hit at/after 11:00 → reversal stop expired"),
          ("fade_cancel_open", "C: virtual breakout still open at data end"),
          ("fade_filled", "C: reversal trades opened"),
          ("fade_same_bar", "C: reversal filled on the bar that broke the range"),
          ("reentry_skipped_time", "Re-entry skipped: wait reaches 11:00"),
          ("reentry_skipped_invalid", "Re-entry skipped: invalid stop"),
          ("reentry_expired", "Re-entry orders expired"),
          ("reentry_filled", "Re-entry orders filled")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/version_comparison")
    ap.add_argument("--commission", type=float, default=0.0)
    args = ap.parse_args()
    out = args.out
    os.makedirs(f"{out}/trade_logs", exist_ok=True)

    m = load_market("data/gbpjpy_1m.npz")
    days = trading_days(m, start=START)
    _, probe = run(m, Params(**BASE), days)
    skipped = {d for d, _ in probe.skipped_dates}
    days = [d for d in days if d.date() not in skipped]
    is_days, oos_days = split_days(days)
    is_set = set(is_days)

    res = {}
    for name, p in VERSIONS.items():
        trades, cnt = run(m, p, days)
        acct = lambda ts: account(ts, m, START_BAL, commission=args.commission)
        log = acct(trades)
        res[name] = dict(
            p=p, log=log, cnt=cnt, all=stats(log, START_BAL, years_of(days)),
            is_=stats(acct([t for t in trades if t.day in is_set]), START_BAL, years_of(is_days)),
            oos=stats(acct([t for t in trades if t.day not in is_set]), START_BAL, years_of(oos_days)))
        clean_log(log).to_csv(f"{out}/trade_logs/base_{p.label}.csv", index=False)

    plot_equity({n: equity_curve(r["log"]) for n, r in res.items()}, f"{out}/equity_versions.png",
                "Base settings (RR 4, SL 30+spread, BE 3R+5): A vs B vs C, closed balance",
                split=oos_days[0])

    rep = ["# Version comparison — breakout (A, B) vs fade (C)\n",
           f"Base settings RR 4, SL 30 pips + spread, BE 3R → +5 pips. {len(days)} days "
           f"{days[0].date()} → {days[-1].date()}; in-sample to {is_days[-1].date()}, "
           f"out-of-sample from {oos_days[0].date()}.\n",
           "**Version C:** the first break of the 05:00–05:59 IST box is *not* traded. It is "
           "followed virtually with the normal SL/TP/BE. A stop order in the opposite direction "
           "sits at the virtual trade's SL price. It fills only if the virtual trade is stopped "
           "out, and is cancelled if the virtual trade hits TP or BE first. The real trade then "
           "follows the usual rules: SL pips + spread from its own entry, RR × that for TP, BE, "
           "and the Version A 6-minute re-entry if it is stopped before 11:00, max 2 real trades.\n",
           "## Full period\n", stat_table({n: r["all"] for n, r in res.items()}),
           "\n## In-sample\n", stat_table({n: r["is_"] for n, r in res.items()}),
           "\n## Out-of-sample\n", stat_table({n: r["oos"] for n, r in res.items()}),
           "\n![Equity](equity_versions.png)\n", "## Order counts\n",
           "| | " + " | ".join(res) + " |", "|---|" + "---|" * len(res)]
    for k, label in COUNTS:
        rep.append(f"| {label} | " + " | ".join(str(r["cnt"].as_dict()[k]) for r in res.values()) + " |")
    for name in list(res)[2:]:
        lg = res[name]["log"]
        rep.append(f"\n## Breakdowns — {name}\n")
        rep.append(breakdowns(lg))
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep) + "\n")
    for name, r in res.items():
        s = r["all"]
        print(f"{name:32s} trades={s['trades']:4d} win={s['win_rate']:5.1f}% avgR={s['avg_R']:+.3f} "
              f"PF={s['profit_factor']:.2f} t={s['sqn']:+.2f} DD={s['max_dd_pct']:.1f}% "
              f"ret={s['net_return_pct']:+.1f}% | IS avgR={r['is_']['avg_R']:+.3f} "
              f"OOS avgR={r['oos']['avg_R']:+.3f}")
    print({n: {k: r["cnt"].as_dict()[k] for k, _ in COUNTS} for n, r in res.items()})


if __name__ == "__main__":
    main()
