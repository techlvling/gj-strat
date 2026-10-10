"""Prop challenge: USDJPY box vs fade (Version C) vs both, each with USDJPY gotobi.

Strategies (frozen rules, USDJPY): green box (Version B, RR 9, BE 3R, SL 1 x box); fade
(Version C, RR 5, no BE, virtual SL by 11:00 IST, SL 1 x box); gotobi short.
Mixes fixed before running (risk % per trade). Same challenge as run_prop_portfolio.py
(P1 +8%, P2 +6%, static 10%, daily 4%, >= 3 days, a start on every trading day 2010-01..2025-10),
all costs ($7/lot, swap +1% markup, 0.2 pip slippage).

    python run_prop_fade.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_prop_sim import challenge

OUT = "results/prop_fade"
NAMES = ["box", "fade", "gotobi"]
#        box, fade, gotobi
MIXES = {"box 0.25% + gotobi 2% (current best)": (0.25, 0.0, 2.0),
         "fade 0.25% + gotobi 2%": (0.0, 0.25, 2.0),
         "fade 0.5% + gotobi 2%": (0.0, 0.5, 2.0),
         "box 0.25% + fade 0.25% + gotobi 2%": (0.25, 0.25, 2.0),
         "box 0.25% + fade 0.25% + gotobi 1.5%": (0.25, 0.25, 1.5),
         "fade 0.5% alone": (0.0, 0.5, 0.0)}


def net_R(m, trades, swap):
    trades = sorted(trades, key=lambda t: (t.exit_i, t.entry_i))
    lg = account(trades, m, 10_000, commission=7, swap=swap, sym="USDJPY", slippage_pips=0.2)
    assert (lg["entry_i"].to_numpy() == [t.entry_i for t in trades]).all()
    return trades, lg["R"].to_numpy()


def main():
    os.makedirs(OUT, exist_ok=True)
    swap = SwapModel.from_fred("rates", 1.0)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    d = daily_table(m)
    d = d[d.index >= pd.Timestamp("2010-01-01")]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d)) if t is not None]

    trades = []
    for s, tr in enumerate((box, fade, got)):
        tr, r = net_R(m, tr, swap)
        trades += [(t, x, s) for t, x in zip(tr, r)]
    trades.sort(key=lambda x: (x[0].entry_i, x[0].exit_i, x[2]))
    T = [x[0] for x in trades]
    R = np.array([x[1] for x in trades])
    strat = np.array([x[2] for x in trades])
    daily = pd.DataFrame({"day": [t.day for t in T], "s": strat, "R": R}).pivot_table(
        index="day", columns="s", values="R", aggfunc="sum").fillna(0)
    corr = daily[0].corr(daily[1])

    exit_utc = pd.DatetimeIndex([m.ts(t.exit_i) for t in T])
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
    last_start = pd.Timestamp("2025-10-07")

    rows = []
    for name, mix in MIXES.items():
        risk = np.array(mix, dtype=float)[strat]
        # a challenge starts at the first trade THIS mix takes on each day
        live = np.flatnonzero(risk > 0)
        starts = [k for i, k in enumerate(live) if (i == 0 or cal_day[k] != cal_day[live[i - 1]])
                  and cal_day[k] <= last_start]
        res = []
        for s in starts:
            r, phase, pos = challenge(ev, R, ny_day, cal_day, s, risk)
            res.append((r, (m.ts(bar_of_pos[pos]) - m.ts(T[s].entry_i)).days))
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
                eq_t.append(m.ts(T[k].exit_i))
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
        "# Prop challenge — USDJPY box vs fade vs both, with gotobi\n\n"
        f"Trades: box {len(box)}, fade {len(fade)}, gotobi {len(got)}. Correlation of daily box and fade "
        f"results: {corr:.2f}. Mixes fixed before running; rules and costs in run_prop_fade.py.\n\n"
        + fmt_table(tab, ".1f") + "\n")
    print(f"box/fade daily correlation {corr:.2f}; trades box {len(box)} fade {len(fade)} gotobi {len(got)}")
    pd.set_option("display.width", 250)
    print(tab.round(1).to_string())


if __name__ == "__main__":
    main()
