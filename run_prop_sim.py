"""Prop-firm challenge pass rate for USDJPY Version B (SL = 1 x box, RR 9, BE 3R).

A two-phase challenge is started on every trading day since 2010 and played forward on the
backtested trades (net of $7/lot, swap with 1% markup and slippage per stop fill):
  * Phase 1: +8%, Phase 2: +6% (fresh balance), both need trades on >= 3 distinct days
  * fail: closed balance <= 90% of the phase's starting balance (static 10% max drawdown)
  * fail: closed P/L in one day < -4% of that day's starting balance (day ends 17:00 New York)
  * no time limit; challenges the data runs out on are reported as unfinished
Risk is a % of the current closed balance at entry. Floating P/L is not checked (closed trades
only), so real daily/max drawdown breaches can come slightly earlier than shown here.

    python run_prop_sim.py      # needs data/usdjpy_2010-01-01_2026-10-07.npz
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

SYM = "USDJPY"
RISKS = [0.25, 0.5, 0.75, 1.0]


def challenge(ev, R, ny_day, ist_day, start_trade, risk, targets=(0.08, 0.06), max_dd=0.10,
              daily=0.04, min_days=3):
    """Play the challenge from trade `start_trade` (in entry order). Returns
    (result, phase reached, event position at the end)."""
    phase, bal, open_, days = 0, 1.0, {}, set()
    cur_day, day_start = None, 1.0
    for pos in range(ev["first_pos"][start_trade], len(ev["kind"])):
        k, kind = ev["trade"][pos], ev["kind"][pos]
        if k < start_trade:
            continue
        if kind == 1:                                   # entry
            open_[k] = risk / 100 * bal
            days.add(ist_day[k])
            continue
        if k not in open_:
            continue                                    # opened in a previous phase
        if ny_day[k] != cur_day:
            cur_day, day_start = ny_day[k], bal
        bal += open_.pop(k) * R[k]
        if bal - day_start < -daily * day_start:
            return "fail: daily 4%", phase + 1, pos
        if bal <= 1 - max_dd:
            return "fail: max 10%", phase + 1, pos
        if bal >= 1 + targets[phase] and len(days) >= min_days:
            if phase == len(targets) - 1:
                return "PASS", phase + 1, pos
            phase, bal, open_, days, cur_day = phase + 1, 1.0, {}, set(), None
    return "unfinished", phase + 1, len(ev["kind"]) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slippage", type=float, default=0.2)
    ap.add_argument("--out", default="results/prop_sim")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    m = build_market(SYM, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                     "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(m, start="2010-01-01")
    _, probe = run(m, Params(sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    days = [d for d in days if d.date() not in skipped]
    p = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0)
    trades, _ = run(m, p, days)
    trades.sort(key=lambda t: (t.entry_i, t.exit_i))
    lg = account(trades, m, 10_000, commission=7, swap=SwapModel.from_fred("rates", 1.0), sym=SYM,
                 slippage_pips=args.slippage).set_index(["entry_i", "exit_i"])
    R = lg.loc[[(t.entry_i, t.exit_i) for t in trades], "R"].to_numpy()
    exit_utc = pd.DatetimeIndex([m.ts(t.exit_i) for t in trades])
    ny = exit_utc.tz_localize("UTC").tz_convert("America/New_York")
    ny_day = np.array((ny + pd.Timedelta(hours=7)).tz_localize(None).normalize())
    ist_day = np.array([t.day for t in trades])

    # one event list for everything: (bar, order, trade) with exits before entries on a bar
    raw = sorted([(t.entry_i, 1, k) for k, t in enumerate(trades)] +
                 [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(trades)])
    kind = np.array([1 if o == 1 else 0 for _, o, _ in raw])
    trade = np.array([k for _, _, k in raw])
    first_pos = np.empty(len(trades), dtype=int)
    for pos in np.flatnonzero(kind == 1):
        first_pos[trade[pos]] = pos
    ev = {"kind": kind, "trade": trade, "first_pos": first_pos}
    bar_of_pos = np.array([b for b, _, _ in raw])

    # a challenge starts at the first trade of each trading day
    starts = [k for k in range(len(trades)) if k == 0 or ist_day[k] != ist_day[k - 1]]
    rows, detail = [], []
    for risk in RISKS:
        for s in starts:
            res, phase, pos = challenge(ev, R, ny_day, ist_day, s, risk)
            days_taken = (m.ts(bar_of_pos[pos]) - m.ts(trades[s].entry_i)).days
            detail.append({"risk %": risk, "start": ist_day[s], "result": res, "phase": phase,
                           "calendar days": days_taken})
        print(f"risk {risk}% done", flush=True)
    det = pd.DataFrame(detail)
    det.to_csv(f"{args.out}/challenges.csv", index=False)

    done = det[det.result != "unfinished"].copy()
    done["era"] = np.where(pd.to_datetime(done.start) < pd.Timestamp("2018-01-01"), "2010–2017", "2018–2026")
    for (risk, era), g in list(done.groupby(["risk %", "era"])) + [((r, "all"), done[done["risk %"] == r]) for r in RISKS]:
        passed = g[g.result == "PASS"]
        p1_fail = g[(g.result != "PASS") & (g.phase == 1)]
        rows.append({"risk %": risk, "starts": era, "challenges": len(g),
                     "PASS both %": len(passed) / len(g) * 100,
                     "fail in P1 %": len(p1_fail) / len(g) * 100,
                     "fail in P2 %": (len(g) - len(passed) - len(p1_fail)) / len(g) * 100,
                     "fails by daily 4% %": (g.result == "fail: daily 4%").mean() * 100,
                     "median days to pass": passed["calendar days"].median(),
                     "median days to fail": g[g.result != "PASS"]["calendar days"].median()})
    res = pd.DataFrame(rows).sort_values(["starts", "risk %"]).set_index(["starts", "risk %"])
    res.index = [f"{a} · {b:g}%" for a, b in res.index]
    res.index.name = "Challenge start · risk"
    unfinished = (det.result == "unfinished").groupby(det["risk %"]).sum().to_dict()

    rep = ["# Prop challenge pass rate — USDJPY Version B (SL 1 × box, RR 9, BE 3R)\n",
           "Rules: Phase 1 +8%, Phase 2 +6%, static 10% max drawdown, 4% daily drawdown (day ends "
           "17:00 New York), at least 3 trading days per phase, no time limit, weekend holding allowed. "
           f"Trades net of $7/lot, swap (+1% markup) and {args.slippage:g} pip slippage per stop fill. "
           "One challenge started on every trading day since 2010; closed-trade balance only.\n",
           fmt_table(res, ".1f"),
           f"\nChallenges still running when the data ends (excluded): {unfinished}.\n"]
    with open(f"{args.out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    pd.set_option("display.width", 250)
    print(res.round(1).to_string())
    print("unfinished:", unfinished)


if __name__ == "__main__":
    main()
