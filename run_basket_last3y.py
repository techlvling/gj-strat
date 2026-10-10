"""Last 3 years (2023-10-07 to 2026-10-07): the USDJPY basket with the month-end USD bid (M-3) added.
Legs: vol-box, vol-gotobi, fade, M-3 (rules in run_m3_addon.py). Per-strategy trade stats, and one
compounding account per plan, with and without M-3. All costs ($7/lot, swap +1%, 0.2 pip slippage).

    python run_basket_last3y.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, month_end_usd_bid, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table

OUT = "results/basket_last3y"
START, END = pd.Timestamp("2023-10-07"), pd.Timestamp("2026-10-07")
LEGS = ["vol-box", "vol-gotobi", "fade", "M-3"]
PLANS = {  # name: (start balance, risk % per leg in LEGS order)
    "Alpha $10k": (10_000, (0.25, 3, 0.5, 0)), "Alpha $10k + M-3 3%": (10_000, (0.25, 3, 0.5, 3)),
    "Blueberry $2.5k": (2_500, (0.25, 1.5, 0, 0)), "Blueberry $2.5k + M-3 1%": (2_500, (0.25, 1.5, 0, 1)),
    "Real money $10k": (10_000, (0.25, 1, 0, 0)), "Real money $10k + M-3 1%": (10_000, (0.25, 1, 0, 1))}


def mix_text(risks):
    return " + ".join(f"{n} {r:g}%" for n, r in zip(LEGS, risks) if r > 0)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    d = daily_table(m)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk and x >= START]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    dl = d[d.index >= START]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, dl)) if t is not None]
    m3 = [t for t in (simulate(m, s) for s in month_end_usd_bid(m, dl, "BUY")) if t is not None]

    legs, per = [], []
    for s, tr in enumerate(([t for t in box if hot(t)], [t for t in got if hot(t)], fade, m3)):
        tr = sorted([t for t in tr if t.day >= START], key=lambda t: (t.exit_i, t.entry_i))
        lg = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)
        R = lg["R"].to_numpy()
        legs += [(t.entry_i, t.exit_i, r, s) for t, r in zip(tr, R)]
        streak = mx = 0
        for x in R:
            streak = streak + 1 if x <= 0 else 0
            mx = max(mx, streak)
        per.append({"strategy": LEGS[s], "trades": len(R), "trades / month": len(R) / 36, "win %": (R > 0).mean() * 100,
                    "avg R": R.mean(), "total R": R.sum(), "best trade R": R.max(), "longest losing streak": mx,
                    "avg SL pips": lg["risk_pips"].mean()})
    ev = sorted([(e, 1, k) for k, (e, x, r, s) in enumerate(legs)] + [(x, 0 if x > e else 2, k) for k, (e, x, r, s) in enumerate(legs)])
    acct, months, years = [], {}, {}
    for name, (start, risks) in PLANS.items():
        bal, peak, dd, open_, ts, bals = float(start), float(start), 0.0, {}, [], []
        for _, kind, k in ev:
            e, x, r, s = legs[k]
            if risks[s] == 0:
                continue
            if kind == 1:
                open_[k] = risks[s] / 100 * bal
            else:
                bal += open_.pop(k) * r
                peak, dd = max(peak, bal), max(dd, 1 - bal / peak)
                ts.append(m.ts(x)); bals.append(bal)
        eq = pd.Series(bals, index=ts)
        me = eq.groupby(eq.index.to_period("M")).last()
        me = me.reindex(pd.period_range(me.index.min(), me.index.max(), freq="M")).ffill()
        mr = me.pct_change() * 100
        mr.iloc[0] = (me.iloc[0] / start - 1) * 100
        months[name] = mr
        ye = eq.groupby(eq.index.year).last()
        years[name] = (ye / ye.shift(1).fillna(start) - 1) * 100
        acct.append({"plan": name, "mix": mix_text(risks), "start $": start, "end $": round(bal), "profit $": round(bal - start),
                     "total %": (bal / start - 1) * 100, "per year %": ((bal / start) ** (1 / 3) - 1) * 100,
                     "max drawdown %": dd * 100, "winning months": f"{(mr > 0).sum()}/{len(mr)}",
                     "best month %": mr.max(), "worst month %": mr.min(), "avg month $": (bal - start) / len(mr)})
    P, A = pd.DataFrame(per).set_index("strategy"), pd.DataFrame(acct).set_index("plan")
    with_m3 = [n for n in PLANS if "M-3" in n]
    M = pd.DataFrame({n: months[n] for n in with_m3}); M.index = M.index.astype(str); M.index.name = "Month"
    Y = pd.DataFrame({n: years[n] for n in with_m3}); Y.index.name = "Year"
    P.to_csv(f"{OUT}/strategies.csv"); A.to_csv(f"{OUT}/accounts.csv"); M.to_csv(f"{OUT}/months.csv")
    open(f"{OUT}/REPORT.md", "w").write(
        "# Last 3 years (Oct 2023 – Oct 2026): USDJPY basket + month-end USD bid (M-3)\n\nAll costs ($7/lot, swap +1%, "
        "0.2 pip slippage); one compounding account per plan. Rules in run_basket_last3y.py.\n\n## Strategies\n\n"
        + fmt_table(P, ".2f") + "\n\n## Accounts (with and without M-3)\n\n" + fmt_table(A, ".1f") +
        "\n\n## Year by year (%, plans with M-3; 2023 = Oct–Dec, 2026 = to 7 Oct)\n\n" + fmt_table(Y, ".1f") +
        "\n\n## Month by month (%, plans with M-3)\n\n" + fmt_table(M, ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(P.round(2).to_string()); print(A.round(1).to_string()); print(Y.round(1).to_string()); print(M.round(1).to_string())
