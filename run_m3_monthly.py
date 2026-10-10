"""Month by month: the month-end USD bid (M-3, buy USDJPY 16:30-17:30 IST on the 3rd-last weekday) and
the two full plans with it, 2011-2026. All costs ($7/lot, swap +1%, 0.2 pip slippage).

  * M-3 alone: one trade a month, in pips (after costs), R, and $ at fixed risk: Alpha $10k x 3% = $300,
    Blueberry $2.5k x 1% = $25.
  * Full plans, % of the starting balance per month (simple sum of risk x R by exit month):
    Alpha = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%; Blueberry = vol-box 0.25% + vol-gotobi 1.5% + M-3 1%.

    python run_m3_monthly.py
"""
import os

import numpy as np
import pandas as pd

from run_backtest import fmt_table
from run_m3_addon import build_legs

OUT = "results/m3_monthly"
ALPHA_RISK = (0.25, 3, 0.5, 3, 0)
BLUE_RISK = (0.25, 1.5, 0, 1, 0)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m, legs = build_legs()
    tr, r = legs[3]
    month = lambda t: m.ts(t.exit_i).to_period("M")
    M3 = pd.DataFrame({"month": [month(t) for t in tr], "trade day": [t.day.strftime("%a %d %b %Y") for t in tr],
                       "exit": ["stop loss" if t.reason == "SL" else "17:30 IST" for t in tr],
                       "pips": [x * t.risk / m.pip for t, x in zip(tr, r)], "R": r,
                       "Alpha $": r * 300, "Blueberry $": r * 25}).set_index("month")
    M3.to_csv(f"{OUT}/m3_trades.csv")
    yr = M3.groupby(M3.index.year).agg(trades=("R", "size"), wins=("R", lambda x: int((x > 0).sum())), pips=("pips", "sum"),
                                       R=("R", "sum"), **{"Alpha $": ("Alpha $", "sum"), "Blueberry $": ("Blueberry $", "sum")})
    yr.index.name = "year"

    def plan(risk):
        rows = [(month(t), risk[s] * x) for s, (tl, rl) in enumerate(legs) for t, x in zip(tl, rl) if risk[s] > 0]
        p = pd.DataFrame(rows, columns=["month", "pct"]).groupby("month")["pct"].sum()
        return p.reindex(pd.period_range("2011-01", "2026-10", freq="M"), fill_value=0.0)
    A, B = plan(ALPHA_RISK), plan(BLUE_RISK)
    P = pd.DataFrame({"Alpha %": A, "Blueberry %": B})
    P.to_csv(f"{OUT}/plans_monthly.csv")
    py = P.groupby(P.index.year).agg(["mean", "min", "max", lambda x: (x > 0).mean() * 100])
    py.columns = [f"{a} {b}" for a, b in zip(py.columns.get_level_values(0),
                                             ["avg/month", "worst month", "best month", "months up %"] * 2)]
    py.index.name = "year"
    last = P.loc["2025-10":"2026-10"].copy()
    last["Alpha $"], last["Blueberry $"] = last["Alpha %"] * 100, last["Blueberry %"] * 25
    last.index = [str(x) + (" (to 7 Oct)" if str(x) == "2026-10" else "") for x in last.index]; last.index.name = "month"
    m3last = M3.loc["2023-10":].copy(); m3last.index = m3last.index.astype(str)
    summ = pd.DataFrame({"M-3 alone (Alpha $)": [M3["Alpha $"].sum() / len(P), M3["Alpha $"].groupby(M3.index.year).sum().median()],
                         "Alpha plan %": [A.mean(), A.groupby(A.index.year).sum().median()],
                         "Blueberry plan %": [B.mean(), B.groupby(B.index.year).sum().median()]},
                        index=["average per month", "median year total"])
    open(f"{OUT}/REPORT.md", "w").write(
        "# Month by month: M-3 and the full plans, 2011–2026\n\nRules in run_m3_monthly.py. Fixed risk (no compounding).\n\n"
        "## M-3 trades, last 3 years\n\n" + fmt_table(m3last, ".1f") + "\n\n## M-3 per year\n\n" + fmt_table(yr, ".1f") +
        "\n\n## Full plans per year (% of starting balance per month)\n\n" + fmt_table(py, ".1f") +
        "\n\n## Full plans, last 12 months\n\n" + fmt_table(last, ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(m3last.round(1).to_string()); print(yr.round(1).to_string()); print(py.round(2).to_string())
    print(last.round(2).to_string()); print(summ.round(2).to_string())
