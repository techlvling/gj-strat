"""Prop challenge (P1 8%, P2 6%, static 10%, daily 4%, >= 3 days) for USDJPY portfolios:
the box breakout (Version B, RR 9, BE 3R, SL 1 box) and the gotobi Tokyo-fix short
(sell at 09:55 JST on gotobi days, exit 15:00 JST, SL 0.25 x ATR20), alone and combined.

Risk mixes fixed before running. A challenge starts on every trading day 2010-2025 (each has >= 12
months of data); share passed within 2 / 3 / 12 months. Full-period max drawdown and yearly
return come from one continuous account. All costs: $7/lot, swap +1% markup, 0.2 pip slippage.

    python run_prop_portfolio.py
"""
from __future__ import annotations

import os
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, simulate, tokyo_fix
from gjstrat.swap import SwapModel
from run_backtest import C, INK2, fmt_table
from run_prop_sim import challenge

OUT = "results/prop_portfolio"
MIXES = {"box 0.5%": (0.5, 0.0), "gotobi 1%": (0.0, 1.0), "gotobi 2%": (0.0, 2.0),
         "box 0.5% + gotobi 1%": (0.5, 1.0), "box 0.5% + gotobi 2%": (0.5, 2.0),
         "box 0.25% + gotobi 2%": (0.25, 2.0)}


def net_R(m, trades, swap):
    lg = account(trades, m, 10_000, commission=7, swap=swap, sym="USDJPY", slippage_pips=0.2)
    return lg.set_index(["entry_i", "exit_i"])["R"]


def main():
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                     "data/usdjpy_2010-01-01_2026-10-07.npz")
    swap = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {d for d, _ in pr.skipped_dates}
    box, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                 [d for d in days if d.date() not in sk])
    d = daily_table(m)
    d = d[d.index >= pd.Timestamp("2010-01-01")]
    got = [t for t in (simulate(m, s) for s in tokyo_fix(m, d, mode="post", at=(6, 0), days_filter="gotobi"))
           if t is not None]
    rb, rg = net_R(m, box, swap), net_R(m, got, swap)
    trades = [(t, rb[(t.entry_i, t.exit_i)], 0) for t in box] + [(t, rg[(t.entry_i, t.exit_i)], 1) for t in got]
    trades.sort(key=lambda x: (x[0].entry_i, x[0].exit_i))
    T = [x[0] for x in trades]
    R = np.array([x[1] for x in trades])
    strat = np.array([x[2] for x in trades])
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
    bar_of_pos = np.array([b for b, _, _ in raw])
    starts = [k for k in range(len(T)) if (k == 0 or cal_day[k] != cal_day[k - 1])
              and cal_day[k] <= pd.Timestamp("2025-10-07")]

    rows, curves = [], {}
    for name, (rbox, rgot) in MIXES.items():
        risk = np.where(strat == 0, rbox, rgot).astype(float)
        if (risk == 0).all():
            continue
        res = []
        for s in starts:
            if risk[s] == 0:
                continue
            r, phase, pos = challenge(ev, R, ny_day, cal_day, s, risk)
            res.append((r, (m.ts(bar_of_pos[pos]) - m.ts(T[s].entry_i)).days))
        res = pd.DataFrame(res, columns=["result", "days"])
        passed = res.result == "PASS"
        # one continuous account for drawdown and yearly return
        bal, peak, dd, open_ = 1.0, 1.0, 0.0, {}
        eq_t, eq_v = [], []
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
                eq_t.append(m.ts(T[k].exit_i)); eq_v.append(bal)
        years = (eq_t[-1] - eq_t[0]).days / 365.25
        curves[name] = pd.Series(eq_v, index=eq_t)
        rows.append({"mix": name, "trades": int((risk > 0).sum()),
                     "pass ≤2 months %": (passed & (res.days <= 61)).mean() * 100,
                     "pass ≤3 months %": (passed & (res.days <= 92)).mean() * 100,
                     "pass ≤12 months %": (passed & (res.days <= 365)).mean() * 100,
                     "fail ≤12 months %": (res.result.str.startswith("fail") & (res.days <= 365)).mean() * 100,
                     "fails by daily 4% %": (res.result == "fail: daily 4%").mean() * 100,
                     "max DD % 2010–26": dd * 100, "per year %": (bal ** (1 / years) - 1) * 100})
        print(rows[-1], flush=True)
    tab = pd.DataFrame(rows).set_index("mix")
    tab.to_csv(f"{OUT}/summary.csv")

    fig, ax = plt.subplots(figsize=(12, 5))
    for k, (name, c) in enumerate(curves.items()):
        ax.plot(c.index, c.to_numpy() * 10_000, color=C[k % len(C)], lw=1.5, drawstyle="steps-post",
                label=f"{name} (max DD {tab.loc[name, 'max DD % 2010–26']:.0f}%)")
    ax.set_yscale("log")
    ax.axhline(10_000, color=INK2, lw=0.8)
    ax.set_title("USDJPY portfolios: one continuous account from $10,000 (all costs)", loc="left")
    ax.legend(fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/portfolios.png", dpi=125)
    plt.close(fig)
    tab.index.name = "Mix"
    open(f"{OUT}/REPORT.md", "w").write(
        "# Prop challenge — USDJPY box breakout + gotobi Tokyo-fix short\n\n"
        "Challenges started on every trading day 2010-01 to 2025-10 (P1 +8%, P2 +6%, static 10%, daily 4%, "
        "≥3 days). All costs. Risk mixes fixed before running.\n\n" + fmt_table(tab, ".1f") +
        "\n\n![Portfolios](portfolios.png)\n")
    print(tab.round(1).to_string())


if __name__ == "__main__":
    main()
