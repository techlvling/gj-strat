"""Last 3 years (2023-10-07 to 2026-10-07) analytics of the vol-filtered USDJPY box + gotobi plan.
Per-strategy trade stats and one compounding $10,000 account for two risk mixes. All costs.

    python run_last3y_plan.py
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

START, END = pd.Timestamp("2023-10-07"), pd.Timestamp("2026-10-07")
MIXES = {"real money (vol-box 0.25% + gotobi 1%)": (0.25, 1.0), "funded (vol-box 0.25% + gotobi 2%)": (0.25, 2.0)}

m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
sw = SwapModel.from_fred("rates", 1.0)
days = trading_days(m, start="2010-01-01")
_, pr = run(m, Params(sl_box_mult=1.0), days)
sk = {x for x, _ in pr.skipped_dates}
box, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
             [x for x in days if x.date() not in sk])
d = daily_table(m)
med = d["atr20"].rolling(250, min_periods=250).median()
box = [t for t in box if d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan) and t.day >= START]
got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= START])) if t is not None]

legs, per = [], []
for s, (nm, tr) in enumerate((("vol-box", box), ("gotobi", got))):
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    lg = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)
    R = lg["R"].to_numpy()
    legs += [(t.entry_i, t.exit_i, r, s) for t, r in zip(tr, R)]
    streak = mx = 0
    for x in R:
        streak = streak + 1 if x <= 0 else 0
        mx = max(mx, streak)
    per.append({"strategy": nm, "trades": len(R), "trades / month": len(R) / 36, "win %": (R > 0).mean() * 100,
                "avg R": R.mean(), "total R": R.sum(), "best trade R": R.max(), "longest losing streak": mx,
                "avg SL pips": lg["risk_pips"].mean(), "exits": ", ".join(f"{k} {v:.0f}%" for k, v in
                                                                         lg["exit_reason"].value_counts(normalize=True).mul(100).items())})
ev = sorted([(e, 1, k) for k, (e, x, r, s) in enumerate(legs)] + [(x, 0 if x > e else 2, k) for k, (e, x, r, s) in enumerate(legs)])
acct, months = [], {}
for name, risks in MIXES.items():
    bal, peak, dd, open_, ts, bals = 10_000.0, 10_000.0, 0.0, {}, [], []
    for _, kind, k in ev:
        e, x, r, s = legs[k]
        if kind == 1:
            open_[k] = risks[s] / 100 * bal
        else:
            bal += open_.pop(k) * r
            peak, dd = max(peak, bal), max(dd, 1 - bal / peak)
            ts.append(m.ts(x)); bals.append(bal)
    eq = pd.Series(bals, index=ts)
    me = eq.groupby(eq.index.to_period("M")).last()
    mr = me.pct_change() * 100
    mr.iloc[0] = (me.iloc[0] / 10_000 - 1) * 100
    months[name] = mr.round(1)
    ye = eq.groupby(eq.index.year).last()
    acct.append({"plan": name, "$10k became": round(bal), "total %": (bal / 10_000 - 1) * 100,
                 "per year %": ((bal / 10_000) ** (1 / 3) - 1) * 100, "max drawdown %": dd * 100,
                 "winning months": f"{(mr > 0).sum()}/{len(mr)}", "best month %": mr.max(), "worst month %": mr.min(),
                 "avg month %": mr.mean()})
P, A = pd.DataFrame(per).set_index("strategy"), pd.DataFrame(acct).set_index("plan")
M = pd.DataFrame(months); M.index = M.index.astype(str); M.index.name = "Month"
txt = ("# Last 3 years (Oct 2023 – Oct 2026): vol-filtered USDJPY box + gotobi\n\nAll costs ($7/lot, swap +1%, "
       "0.2 pip slippage); one compounding account from $10,000.\n\n## Strategies\n\n" + fmt_table(P, ".2f") +
       "\n\n## Account\n\n" + fmt_table(A, ".1f") + "\n\n## Month by month (%)\n\n" + fmt_table(M, ".1f") + "\n")
open("results/box_dd_filters/LAST3Y.md", "w").write(txt)
pd.set_option("display.width", 250)
print(P.round(2).to_string()); print(A.round(1).to_string()); print(M.to_string())
