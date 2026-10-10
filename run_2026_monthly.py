"""2026 month by month: vol-box, gotobi (all days and vol-filtered) and fade on USDJPY, in R and as
account % for the Alpha mix (vol-box 0.25% + gotobi 3% + fade 0.5%, simple sum of risk x R per month).
All costs ($7/lot, swap +1%, 0.2 pip slippage). Months by trade exit.

    python run_2026_monthly.py
"""
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
sw = SwapModel.from_fred("rates", 1.0)
days = trading_days(m, start="2025-01-01")
_, pr = run(m, Params(sl_box_mult=1.0), days)
sk = {x for x, _ in pr.skipped_dates}
days = [x for x in days if x.date() not in sk]
base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
d = daily_table(m)
med = d["atr20"].rolling(250, min_periods=250).median()
hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2025-06-01")])) if t is not None]
legs = {"vol-box": [t for t in box if hot(t)], "gotobi": got, "vol-gotobi": [t for t in got if hot(t)], "fade": fade}
monthly, trades = {}, {}
for name, tr in legs.items():
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    lg = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)
    mon = pd.to_datetime(lg["exit_time_ist"]).dt.to_period("M")
    s = pd.Series(lg["R"].to_numpy(), index=mon)
    s = s[s.index.year == 2026]
    monthly[name] = s.groupby(level=0).sum()
    trades[name] = s.groupby(level=0).size()
R = pd.DataFrame(monthly).fillna(0.0)
N = pd.DataFrame(trades).fillna(0).astype(int)
R["Alpha mix %"] = 0.25 * R["vol-box"] + 3 * R["gotobi"] + 0.5 * R["fade"]
R["Blueberry mix % (vol-box 0.25 + vol-gotobi 1.5)"] = 0.25 * R["vol-box"] + 1.5 * R["vol-gotobi"]
R.index = R.index.astype(str); N.index = N.index.astype(str)
R.loc["2026 total"] = R.sum()
N.loc["2026 total"] = N.sum()
tab = R.round(2).astype(str)
for c in ("vol-box", "gotobi", "vol-gotobi", "fade"):
    tab[c] = R[c].map(lambda x: f"{x:+.2f}R") + " (" + N[c].astype(str) + ")"
tab.index.name = "Month"
txt = ("# 2026 month by month — USDJPY vol-box, gotobi, fade\n\nR per month (trades in brackets), by exit month; "
       "mix columns = % of account (simple sum). All costs. Jan–early Oct 2026.\n\n" + fmt_table(tab, "") + "\n")
open("results/box_dd_filters/MONTHLY_2026.md", "w").write(txt)
print(tab.to_string())
