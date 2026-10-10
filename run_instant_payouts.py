"""Blueberry Instant Elite $2,500: money actually withdrawn, with 14-day payouts and a $100 minimum.

Account rules as reported (verify): no daily limit, 10% max drawdown, 80% profit split, payout
every 14 days, minimum payout $100 (taken as the trader's 80% share -> needs >= $125 of profit).
Two drawdown models:
  static   floor fixed at start - 10%; each payout takes all profit above the $2,500 start
  trailing floor trails the balance high by 10% and locks at the start; a payout only takes profit
           above floor + 10% (so the full 10% cushion is kept after every payout)
An account starts on every trading day 2011-01..2024-10 and runs 24 months or until breached.
Vol-filtered USDJPY box + gotobi, all costs ($7/lot, swap +1%, 0.2 pip slippage).

    python run_instant_payouts.py
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

SIZE, SPLIT, MIN_PAY, EVERY, DD, OUT = 2_500, 0.8, 100, 14, 0.10, "results/instant_payouts"
MIXES = {"vol-box 0.25% + gotobi 1%": (0.25, 1), "vol-box 0.25% + gotobi 2%": (0.25, 2),
         "vol-box 0.25% + gotobi 3%": (0.25, 3), "gotobi 2% alone": (0, 2)}

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
    first_pos = {}
    for p in np.flatnonzero(kind):
        first_pos.setdefault(trade[p], p)
    rows = []
    for model in ("static", "trailing"):
        for name, (rb, rg) in MIXES.items():
            risk = np.where(S == 0, rb, rg)
            live = [k for k in range(len(T)) if risk[k] > 0]
            starts = [k for i, k in enumerate(live) if (i == 0 or T[k].day != T[live[i - 1]].day)
                      and T[k].day <= pd.Timestamp("2024-10-07")]
            out = []
            for s0 in starts:
                t0 = m.ts(T[s0].entry_i)
                bal, peak, floor, open_ = 1.0, 1.0, 1 - DD, {}
                paid, pay12, n_pay, next_pay, breached, first_pay = 0.0, 0.0, 0, t0 + pd.Timedelta(days=EVERY), False, None
                for p in range(first_pos[s0], len(ev)):
                    k = trade[p]
                    if k < s0 or risk[k] == 0:
                        continue
                    now = m.ts(bar[p])
                    if now > t0 + pd.Timedelta(days=730):
                        break
                    while now >= next_pay:                          # payout dates passed: withdraw if allowed
                        base = 1.0 if model == "static" else max(1.0, floor + DD)
                        amt = (bal - base) * SIZE
                        if amt * SPLIT >= MIN_PAY and not open_:
                            paid += amt * SPLIT; n_pay += 1
                            pay12 += amt * SPLIT if next_pay <= t0 + pd.Timedelta(days=365) else 0
                            first_pay = first_pay or (next_pay - t0).days
                            bal, peak = base, max(base, peak if model == "static" else base)
                        next_pay += pd.Timedelta(days=EVERY)
                    if kind[p]:
                        open_[k] = risk[k] / 100 * bal
                        continue
                    if k not in open_:
                        continue
                    bal += open_.pop(k) * R[k]
                    peak = max(peak, bal)
                    if model == "trailing":
                        floor = min(max(floor, peak - DD), 1.0)
                    if bal <= floor:
                        breached = True
                        break
                out.append((paid, pay12, n_pay, breached, first_pay))
            o = pd.DataFrame(out, columns=["paid", "paid12", "n", "breached", "first"])
            rows.append({"drawdown": model, "plan": name, "got ≥1 payout %": (o.n > 0).mean() * 100,
                         "days to first payout (median)": o["first"].median(),
                         "avg paid in first 12 months $": o.paid12.mean(), "median paid in 12 months $": o.paid12.median(),
                         "avg paid over 24 months $": o.paid.mean(), "avg per month $": o.paid.mean() / 24,
                         "account lost within 24 months %": o.breached.mean() * 100})
    tab = pd.DataFrame(rows).set_index(["drawdown", "plan"])
    tab.to_csv(f"{OUT}/summary.csv")
    show = tab.copy(); show.index = [f"{a} · {b}" for a, b in show.index]; show.index.name = "Drawdown · plan"
    open(f"{OUT}/REPORT.md", "w").write("# Blueberry Instant Elite $2,500 — money actually withdrawn\n\n"
                                        "14-day payouts, $100 minimum, 80% split; rules and models in run_instant_payouts.py.\n\n"
                                        + fmt_table(show, ".0f") + "\n")
    pd.set_option("display.width", 250)
    print(tab.round(0).to_string())
