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
from gjstrat.prop import instant_table
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
    for tr in (box, got):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        legs.append((tr, account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()))
    tab = instant_table(m, legs, MIXES, CUSHIONS, size=SIZE, split=SPLIT, min_pay=MIN_PAY, every=EVERY, dd=DD, qday=QDAY,
                        ndays=NDAYS, last_start="2024-10-07", horizon=730)
    tab.to_csv(f"{OUT}/summary.csv")
    show = tab.copy(); show.index = [f"{a} · {b}" for a, b in show.index]; show.index.name = "Cushion · plan"
    open(f"{OUT}/REPORT.md", "w").write("# Blueberry Instant Elite $2,500 — confirmed rules, money withdrawn\n\n"
                                        "Rules and assumptions in run_blueberry_elite.py.\n\n" + fmt_table(show, ".0f") + "\n")
    pd.set_option("display.width", 250)
    print(tab.round(0).to_string())
