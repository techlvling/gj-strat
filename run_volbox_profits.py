"""Profits of the vol-filtered box + gotobi plan (USDJPY 2010-2026), one compounding account
from $10,000 per mix; year-by-year returns. Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_volbox_profits.py
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

MIXES = {"vol-box 0.5% alone": (0.5, 0), "gotobi 1% alone": (0, 1), "real money: vol-box 0.25% + gotobi 1%": (0.25, 1),
         "funded: vol-box 0.25% + gotobi 2%": (0.25, 2), "challenge: vol-box 0.25% + gotobi 3%": (0.25, 3)}

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
d2 = d[d.index >= pd.Timestamp("2010-01-01")]
got = [t for t in (simulate(m, s) for s in gotobi_short(m, d2)) if t is not None]
legs = []
for s, tr in enumerate((box, got)):
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    R = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    legs += [(t.entry_i, t.exit_i, r, s) for t, r in zip(tr, R)]
ev = sorted([(e, 1, k) for k, (e, x, r, s) in enumerate(legs)] + [(x, 0 if x > e else 2, k) for k, (e, x, r, s) in enumerate(legs)])
summary, yearly = [], {}
for name, (rb, rg) in MIXES.items():
    bal, peak, dd, open_, ts, bals = 10_000.0, 10_000.0, 0.0, {}, [], []
    for _, kind, k in ev:
        e, x, r, s = legs[k]
        risk = rb if s == 0 else rg
        if risk == 0:
            continue
        if kind == 1:
            open_[k] = risk / 100 * bal
        else:
            bal += open_.pop(k) * r
            peak, dd = max(peak, bal), max(dd, 1 - bal / peak)
            ts.append(m.ts(x)); bals.append(bal)
    eq = pd.Series(bals, index=ts)
    ye = eq.groupby(eq.index.year).last()
    yr = ye.pct_change() * 100
    yr.iloc[0] = (ye.iloc[0] / 10_000 - 1) * 100
    yearly[name] = yr.round(1)
    years = (ts[-1] - ts[0]).days / 365.25
    summary.append({"plan": name, "$10k became": round(bal), "per year %": ((bal / 10_000) ** (1 / years) - 1) * 100,
                    "max drawdown %": dd * 100, "worst year %": yr.min(), "best year %": yr.max(),
                    "losing years": f"{(yr < 0).sum()}/{len(yr)}", "last 3 years %": (ye.iloc[-1] / ye.loc[2023] - 1) * 100})
s = pd.DataFrame(summary).set_index("plan")
y = pd.DataFrame(yearly)
y.index.name = "Year"
txt = ("# Profits — vol-filtered USDJPY box + gotobi (2010–2026, all costs, from $10,000)\n\n" + fmt_table(s, ".1f") +
       "\n\n## Year by year (%)\n\n" + fmt_table(y, ".1f") + "\n\n2026 = Jan to early Oct. 'Last 3 years' = end-2023 to Oct 2026.\n")
open("results/box_dd_filters/PROFITS.md", "w").write(txt)
pd.set_option("display.width", 250)
print(s.round(1).to_string()); print(y.to_string())
