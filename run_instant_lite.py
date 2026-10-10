"""Blueberry Funded 'Instant Lite' $2,500 account with the vol-filtered USDJPY box + gotobi.

Rules as reported (verify with Blueberry): 2% daily loss (of the day's starting balance, closed
trades), 4% max drawdown trailing the balance high and locking at the starting balance, max 1%
risk per trade once the account is 4% up. No profit target. An account is started on every
trading day 2011-01..2025-10 and followed for 12 months: breached or not, and profit if alive.
Min lot 0.01 (~$0.068/pip on USDJPY): risk below about $2-3 per trade can't be placed, so box
risk starts at 0.1%. All costs ($7/lot, swap +1%, 0.2 pip slippage). No withdrawals modelled.

    python run_instant_lite.py
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

SIZE, OUT = 2_500, "results/instant_lite"
DAILY, MAXDD, CAP_AT, CAP = 0.02, 0.04, 1.04, 1.0
MIXES = {f"gotobi {g:g}%": (0, g) for g in (0.25, 0.5, 0.75, 1.0)}
MIXES.update({"vol-box 0.25% alone": (0.25, 0), "vol-box 0.1% + gotobi 0.5%": (0.1, 0.5),
              "vol-box 0.25% + gotobi 0.5%": (0.25, 0.5), "vol-box 0.1% + gotobi 0.75%": (0.1, 0.75)})

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
    for name, (rb, rg) in MIXES.items():
        risk = np.where(S == 0, rb, rg)
        live = [k for k in range(len(T)) if risk[k] > 0]
        starts = [k for i, k in enumerate(live) if (i == 0 or T[k].day != T[live[i - 1]].day) and T[k].day <= pd.Timestamp("2025-10-07")]
        out = []
        for s0 in starts:
            t_end = m.ts(T[s0].entry_i) + pd.Timedelta(days=365)
            bal, peak, floor, open_, cur, day0, res, when = 1.0, 1.0, 1 - MAXDD, {}, None, 1.0, "alive", 365
            for p in range(first_pos[s0], len(ev)):
                k = trade[p]
                if k < s0 or risk[k] == 0:
                    continue
                if m.ts(bar[p]) > t_end:
                    break
                if kind[p]:
                    pct = min(risk[k], CAP) if bal >= CAP_AT else risk[k]
                    open_[k] = pct / 100 * bal
                    continue
                if k not in open_:
                    continue
                if ny[k] != cur:
                    cur, day0 = ny[k], bal
                bal += open_.pop(k) * R[k]
                peak = max(peak, bal)
                floor = min(max(floor, peak - MAXDD), 1.0)          # trails the high, locks at the start balance
                if bal - day0 < -DAILY * day0 or bal <= floor:
                    res = "daily" if bal - day0 < -DAILY * day0 else "max dd"
                    when = (m.ts(bar[p]) - m.ts(T[s0].entry_i)).days
                    break
            out.append((res, when, bal - 1 if res == "alive" else np.nan))
        o = pd.DataFrame(out, columns=["res", "days", "profit"])
        alive = o.res == "alive"
        rows.append({"plan": name, "breached ≤3 months %": ((~alive) & (o.days <= 92)).mean() * 100,
                     "breached ≤6 months %": ((~alive) & (o.days <= 183)).mean() * 100,
                     "breached ≤12 months %": (~alive).mean() * 100,
                     "of which daily 2% %": (o.res == "daily").mean() * 100,
                     "survivors: median 12-month profit %": o.profit[alive].median() * 100,
                     "survivors: avg 12-month profit $": o.profit[alive].mean() * SIZE,
                     "expected 12-month payout $ (80%)": (o.profit.fillna(0).clip(lower=0) * SIZE * 0.8).mean()})
    tab = pd.DataFrame(rows).set_index("plan").sort_values("expected 12-month payout $ (80%)", ascending=False)
    tab.to_csv(f"{OUT}/summary.csv")
    open(f"{OUT}/REPORT.md", "w").write("# Blueberry Funded Instant Lite $2,500 — vol-box + gotobi (USDJPY)\n\n"
                                        "Rules as reported (verify): 2% daily, 4% trailing-lock max drawdown, 1% max risk after +4%. "
                                        "Details and assumptions in run_instant_lite.py.\n\n" + fmt_table(tab, ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(tab.round(1).to_string())
