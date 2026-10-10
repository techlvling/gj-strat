"""Prop challenge: does adding EURJPY gotobi help the USDJPY box + gotobi plan?

Strategies (frozen rules): USDJPY green box, USDJPY gotobi short, EURJPY gotobi short (same rule).
Mixes fixed before running (risk % per trade): see MIXES. Same challenge as run_prop_portfolio.py
(P1 +8%, P2 +6%, static 10%, daily 4%, >= 3 days, start on every trading day 2010-01..2025-10),
all costs ($7/lot, swap +1% markup, 0.2 pip slippage).

    python run_prop_ej.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, simulate, tokyo_fix
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_prop_sim import challenge

OUT = "results/prop_ej"
#         box UJ, gotobi UJ, gotobi EJ
MIXES = {"box 0.25% + UJ gotobi 2% (current best)": (0.25, 2.0, 0.0),
         "box 0.25% + UJ 1% + EJ 1% (same total)": (0.25, 1.0, 1.0),
         "box 0.25% + UJ 1.5% + EJ 1%": (0.25, 1.5, 1.0),
         "box 0.25% + UJ 2% + EJ 1% (added on top)": (0.25, 2.0, 1.0),
         "box 0.25% + UJ 2% + EJ 2%": (0.25, 2.0, 2.0)}


def net_R(m, sym, trades, swap):
    lg = account(trades, m, 10_000, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
    return lg.set_index(["entry_i", "exit_i"])["R"]


def gotobi(m):
    d = daily_table(m)
    d = d[d.index >= pd.Timestamp("2010-01-01")]
    return [t for t in (simulate(m, s) for s in tokyo_fix(m, d, mode="post", at=(6, 0), days_filter="gotobi"))
            if t is not None]


def main():
    os.makedirs(OUT, exist_ok=True)
    swap = SwapModel.from_fred("rates", 1.0)
    uj = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    ej = build_market("EURJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/eurjpy_2010-01-01_2026-10-07.npz")
    assert uj.t0 == ej.t0                                   # same minute grid -> comparable bar indices
    days = trading_days(uj, start="2010-01-01")
    _, pr = run(uj, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    box, _ = run(uj, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                 [x for x in days if x.date() not in sk])
    g_uj, g_ej = gotobi(uj), gotobi(ej)
    parts = [(box, net_R(uj, "USDJPY", box, swap), 0), (g_uj, net_R(uj, "USDJPY", g_uj, swap), 1),
             (g_ej, net_R(ej, "EURJPY", g_ej, swap), 2)]
    trades = [(t, R[(t.entry_i, t.exit_i)], s) for tr, R, s in parts for t in tr]
    trades.sort(key=lambda x: (x[0].entry_i, x[0].exit_i, x[2]))
    T = [x[0] for x in trades]
    R = np.array([x[1] for x in trades])
    strat = np.array([x[2] for x in trades])

    # correlation of the two gotobi legs on shared days
    a = pd.Series({t.day: r for t, r, s in trades if s == 1})
    b = pd.Series({t.day: r for t, r, s in trades if s == 2})
    corr = a.to_frame("uj").join(b.to_frame("ej"), how="inner").corr().iloc[0, 1]

    exit_utc = pd.DatetimeIndex([uj.ts(t.exit_i) for t in T])
    ny_day = np.array((exit_utc.tz_localize("UTC").tz_convert("America/New_York") + pd.Timedelta(hours=7))
                      .tz_localize(None).normalize())
    cal_day = np.array([t.day for t in T])
    raw = sorted([(t.entry_i, 1, k) for k, t in enumerate(T)] +
                 [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(T)])
    kind = np.array([1 if o == 1 else 0 for _, o, _ in raw])
    trade = np.array([k for _, _, k in raw])
    first_pos = np.empty(len(T), dtype=int)
    for pos in np.flatnonzero(kind == 1):
        first_pos[trade[pos]] = pos
    ev = {"kind": kind, "trade": trade, "first_pos": first_pos}
    bar_of_pos = np.array([x for x, _, _ in raw])
    starts = [k for k in range(len(T)) if (k == 0 or cal_day[k] != cal_day[k - 1])
              and cal_day[k] <= pd.Timestamp("2025-10-07")]

    rows = []
    for name, mix in MIXES.items():
        risk = np.array(mix, dtype=float)[strat]
        res = []
        for s in starts:
            if risk[s] == 0:
                continue
            r, phase, pos = challenge(ev, R, ny_day, cal_day, s, risk)
            res.append((r, (uj.ts(bar_of_pos[pos]) - uj.ts(T[s].entry_i)).days))
        res = pd.DataFrame(res, columns=["result", "days"])
        passed = res.result == "PASS"
        bal, peak, dd, open_, eq_t = 1.0, 1.0, 0.0, {}, []
        for pos in range(len(kind)):
            k = trade[pos]
            if risk[k] == 0:
                continue
            if kind[pos] == 1:
                open_[k] = risk[k] / 100 * bal
            else:
                bal += open_.pop(k) * R[k]
                peak = max(peak, bal)
                dd = max(dd, 1 - bal / peak)
                eq_t.append(uj.ts(T[k].exit_i))
        years = (eq_t[-1] - eq_t[0]).days / 365.25
        rows.append({"mix": name,
                     "pass ≤2 months %": (passed & (res.days <= 61)).mean() * 100,
                     "pass ≤3 months %": (passed & (res.days <= 92)).mean() * 100,
                     "pass ≤6 months %": (passed & (res.days <= 183)).mean() * 100,
                     "fail ≤6 months %": (res.result.str.startswith("fail") & (res.days <= 183)).mean() * 100,
                     "median months to pass": res.days[passed].median() / 30.4,
                     "fails by daily 4% %": (res.result == "fail: daily 4%").mean() * 100,
                     "max DD % 2010–26": dd * 100, "per year %": (bal ** (1 / years) - 1) * 100})
        print(rows[-1], flush=True)
    tab = pd.DataFrame(rows).set_index("mix")
    tab.to_csv(f"{OUT}/summary.csv")
    open(f"{OUT}/REPORT.md", "w").write(
        "# Prop challenge — adding EURJPY gotobi to USDJPY box + gotobi\n\n"
        f"Correlation of USDJPY and EURJPY gotobi results on the same days: {corr:.2f}. "
        "Mixes fixed before running; rules and costs in run_prop_ej.py.\n\n" + fmt_table(tab, ".1f") + "\n")
    print(f"gotobi UJ/EJ correlation: {corr:.2f}")
    pd.set_option("display.width", 250)
    print(tab.round(1).to_string())


if __name__ == "__main__":
    main()
