"""Blueberry Funded Instant Elite $2,500 with the confirmed rules (screenshot, Oct 2026):
10% max drawdown, trailing lock (trails the balance high, locks at the start balance), no daily
limit, no target, no consistency, max risk 1.5% per trade (2% with add-on), payouts every 14 days
after 5 trading days with >= 0.5% profit on equity, 80% split; $100 minimum payout (trader share).

Assumptions: a payout needs 5 qualifying days (day P/L >= +0.5% of the day's start balance) since
the previous payout; a payout takes the profit above max(start, floor + cushion), leaving `cushion`
between the balance and the drawdown floor (the floor does not move down after a payout); no open
trades at the payout moment. Cushions fixed before running: 10% / 7% / 5%.
Accounts start on every trading day 2011-01..2024-10 and run 24 months or until breached.
Vol-filtered USDJPY box + gotobi, all costs.

    python run_blueberry_elite.py
"""
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

SIZE, SPLIT, MIN_PAY, EVERY, DD, QDAY, NDAYS, OUT = 2_500, 0.8, 100, 14, 0.10, 0.005, 5, "results/blueberry_elite"
MIXES = {"vol-box 0.25% + gotobi 1%": (0.25, 1.0), "vol-box 0.25% + gotobi 1.5%": (0.25, 1.5),
         "vol-box 0.5% + gotobi 1.5%": (0.5, 1.5), "gotobi 1.5% alone": (0, 1.5),
         "vol-box 0.25% + gotobi 2% (add-on)": (0.25, 2.0)}
CUSHIONS = (0.10, 0.07, 0.05)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    box, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                 [x for x in days if x.date() not in sk])
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    box = [t for t in box if d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2011-01-01")])) if t is not None]
    legs = []
    for s, tr in enumerate((box, got)):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        R = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
        legs += [(t, r, s) for t, r in zip(tr, R)]
    legs.sort(key=lambda x: (x[0].entry_i, x[0].exit_i))
    T = [x[0] for x in legs]; R = np.array([x[1] for x in legs]); S = np.array([x[2] for x in legs])
    ev = sorted([(t.entry_i, 1, k) for k, t in enumerate(T)] + [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(T)])
    kind = np.array([o == 1 for _, o, _ in ev]); trade = np.array([k for _, _, k in ev]); bar = np.array([b for b, _, _ in ev])
    ny = np.array((pd.DatetimeIndex([m.ts(t.exit_i) for t in T]).tz_localize("UTC").tz_convert("America/New_York")
                   + pd.Timedelta(hours=7)).tz_localize(None).normalize())
    first_pos = {}
    for p in np.flatnonzero(kind):
        first_pos.setdefault(trade[p], p)
    rows = []
    for cush in CUSHIONS:
        for name, (rb, rg) in MIXES.items():
            risk = np.where(S == 0, rb, rg)
            live = [k for k in range(len(T)) if risk[k] > 0]
            starts = [k for i, k in enumerate(live) if (i == 0 or T[k].day != T[live[i - 1]].day)
                      and T[k].day <= pd.Timestamp("2024-10-07")]
            out = []
            for s0 in starts:
                t0 = m.ts(T[s0].entry_i)
                bal, peak, floor, open_ = 1.0, 1.0, 1 - DD, {}
                cur, day0, day_pnl, qdays = None, 1.0, 0.0, 0
                paid, pay12, n_pay, next_pay, breached, first_pay = 0.0, 0.0, 0, t0 + pd.Timedelta(days=EVERY), False, None
                for p in range(first_pos[s0], len(ev)):
                    k = trade[p]
                    if k < s0 or risk[k] == 0:
                        continue
                    now = m.ts(bar[p])
                    if now > t0 + pd.Timedelta(days=730):
                        break
                    while now >= next_pay:
                        base = max(1.0, floor + cush)
                        amt = (bal - base) * SIZE
                        if amt * SPLIT >= MIN_PAY and qdays >= NDAYS and not open_:
                            paid += amt * SPLIT; n_pay += 1; qdays = 0
                            pay12 += amt * SPLIT if next_pay <= t0 + pd.Timedelta(days=365) else 0
                            first_pay = first_pay or (next_pay - t0).days
                            bal = base
                        next_pay += pd.Timedelta(days=EVERY)
                    if kind[p]:
                        open_[k] = risk[k] / 100 * bal
                        continue
                    if k not in open_:
                        continue
                    if ny[k] != cur:
                        if cur is not None and day_pnl >= QDAY * day0:
                            qdays += 1
                        cur, day0, day_pnl = ny[k], bal, 0.0
                    pnl = open_.pop(k) * R[k]
                    bal += pnl; day_pnl += pnl
                    peak = max(peak, bal)
                    floor = min(max(floor, peak - DD), 1.0)
                    if bal <= floor:
                        breached = True
                        break
                out.append((paid, pay12, n_pay, breached, first_pay))
            o = pd.DataFrame(out, columns=["paid", "paid12", "n", "breached", "first"])
            rows.append({"cushion kept": f"{cush:.0%}", "plan": name, "got ≥1 payout %": (o.n > 0).mean() * 100,
                         "days to first payout (median)": o["first"].median(),
                         "avg paid in 12 months $": o.paid12.mean(), "median paid in 12 months $": o.paid12.median(),
                         "avg paid in 24 months $": o.paid.mean(), "avg per month $": o.paid.mean() / 24,
                         "account lost within 24 months %": o.breached.mean() * 100})
    tab = pd.DataFrame(rows).set_index(["cushion kept", "plan"])
    tab.to_csv(f"{OUT}/summary.csv")
    show = tab.copy(); show.index = [f"{a} · {b}" for a, b in show.index]; show.index.name = "Cushion · plan"
    open(f"{OUT}/REPORT.md", "w").write("# Blueberry Instant Elite $2,500 — confirmed rules, money withdrawn\n\n"
                                        "Rules and assumptions in run_blueberry_elite.py.\n\n" + fmt_table(show, ".0f") + "\n")
    pd.set_option("display.width", 250)
    print(tab.round(0).to_string())
