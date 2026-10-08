"""Approved USDJPY strategy (green/), last 3 years of data: analytics with all costs.

    python run_usdjpy_last3y.py      # needs data/usdjpy_2010-01-01_2026-10-07.npz
"""
from __future__ import annotations

from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gjstrat.accounting import account, breakdown, equity_curve, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import C, INK2, clean_log, fmt_table, stat_table

START, END, OUT = "2023-10-09", "2026-10-07", "results/usdjpy_last3y"
P = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0)

m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                 "data/usdjpy_2010-01-01_2026-10-07.npz")
days = trading_days(m, start=START, end=END)
trades, cnt = run(m, P, days)
swap = SwapModel.from_fred("rates", 1.0)
logs = {f"{r}% risk": account(trades, m, 10_000, risk_pct=r, commission=7, swap=swap, sym="USDJPY",
                              slippage_pips=0.2) for r in (0.5, 1.0)}
lg = logs["0.5% risk"]
clean_log(lg).to_csv(f"{OUT}/trades.csv", index=False)
yrs = (pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25
s = {k: stats(v, 10_000, yrs) for k, v in logs.items()}

d = pd.to_datetime(lg["day"])
lg["year"], lg["month"] = d.dt.year, d.dt.strftime("%Y-%m")
by_year = lg.groupby("year").agg(trades=("R", "size"), win_rate=("R", lambda x: (x > 0).mean() * 100),
                                 avg_R=("R", "mean"), total_R=("R", "sum"),
                                 return_pct=("pnl_usd", lambda x: np.nan))
eq = equity_curve(lg)
for y in by_year.index:
    e = eq[eq.index.year == y]
    prev = eq[eq.index.year < y]
    start_bal = prev.iloc[-1] if len(prev) else 10_000
    by_year.loc[y, "return_pct"] = (e.iloc[-1] / start_bal - 1) * 100
monthly = lg.groupby("month")["R"].sum()
parts = {"Side": lg["side"], "Trade number": lg["trade_num"], "Exit reason": lg["exit_reason"],
         "Day of week": pd.Categorical(d.dt.day_name(), ["Monday", "Tuesday", "Wednesday", "Thursday",
                                                        "Friday"], ordered=True)}

fig, axes = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axes[0]
for k, (name, l) in enumerate(logs.items()):
    e = equity_curve(l)
    ax.plot(e.index, e.to_numpy(), color=C[k], lw=1.8, drawstyle="steps-post",
            label=f"{name} ({e.iloc[-1] / 100 - 100:+.0f}%)")
ax.axhline(10_000, color=INK2, lw=0.8)
ax.set_title("USDJPY Version B, last 3 years: balance from $10,000 (all costs)", loc="left")
ax.set_ylabel("Closed balance (USD)")
ax.legend(loc="upper left")
ax = axes[1]
ax.bar(range(len(monthly)), monthly.to_numpy(), color=np.where(monthly > 0, "#2a78d6", "#e34948"), width=0.75)
ax.axhline(0, color=INK2, lw=0.8)
ticks = list(range(0, len(monthly), 3))
ax.set_xticks(ticks, [monthly.index[i] for i in ticks], rotation=60, fontsize=8)
ax.set_title("Total R per month", loc="left")
ax.grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(f"{OUT}/last3y.png", dpi=125)
plt.close(fig)

by_year.index.name = "Year"
rep = [f"# USDJPY approved strategy — last 3 years ({START} → {END})\n",
       "Version B, SL = 1 × box, RR 9, BE 3R, 05:00 IST box. $7/lot, swap (+1% markup), 0.2 pip "
       "slippage per stop fill.\n", stat_table(s), "\n![Last 3 years](last3y.png)\n",
       "## By year (0.5% risk)\n", fmt_table(by_year, ".2f"),
       f"\nPositive months: {(monthly > 0).sum()} of {len(monthly)}. Best {monthly.max():+.1f}R "
       f"({monthly.idxmax()}), worst {monthly.min():+.1f}R ({monthly.idxmin()}).\n"]
for name, key in parts.items():
    b = breakdown(lg, pd.Series(key, index=lg.index))
    b.index.name = name
    rep += [f"**By {name.lower()}**\n", fmt_table(b, ".3f"), ""]
open(f"{OUT}/REPORT.md", "w").write("\n".join(rep))
print(pd.DataFrame(s).round(2).to_string())
print(by_year.round(2).to_string())
print("months +:", (monthly > 0).sum(), "/", len(monthly), "best", monthly.max().round(1), monthly.idxmax(),
      "worst", monthly.min().round(1), monthly.idxmin())
for name, key in parts.items():
    print(breakdown(lg, pd.Series(key, index=lg.index)).round(3).to_string())
