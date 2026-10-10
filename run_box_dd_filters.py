"""Drawdown filters for the USDJPY green box (2010-2026).

Filters (fixed before running), applied to the green box trades (Version B, RR 9, BE 3R, SL 1 x box):
  vol    trade only when ATR20 (known before the day) >= its rolling 250-day median
  equity trade only when the box's own running R total (trades closed before this entry, taken or
         not) is >= its 50-trade moving average; always trade during the first 50 trades
  both   vol AND equity
Accepted only if max drawdown (0.5% risk, compounding inside each period) is lower than the
unfiltered box in ALL of 2010-17 / 2018-23 / 2024-26 and avg R is not lower in 2018-23 and 2024-26.
Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_box_dd_filters.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

OUT = "results/box_dd_filters"


def max_dd(r, risk=0.5):
    if not len(r):
        return np.nan
    eq = np.cumprod(1 + risk / 100 * r)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]                          # start balance counts as a peak
    return (1 - eq / peak).max() * 100


def stats(r, day):
    row = {}
    for per, (a, b) in PERIODS.items():
        mask = np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))
        x = r[mask]
        row.update({f"{per} trades": len(x), f"{per} avg R": x.mean(), f"{per} t": tstat(x),
                    f"{per} max DD % (0.5%)": max_dd(x)})
    row.update({"all trades": len(r), "all avg R": r.mean(), "all max DD % (0.5%)": max_dd(r)})
    return row


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    tr, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                [x for x in days if x.date() not in sk])
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))                       # exit order (account order)
    R = account(tr, m, 10_000, risk_pct=0.5, commission=7, swap=SwapModel.from_fred("rates", 1.0),
                sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    day = pd.DatetimeIndex([t.day for t in tr])

    # vol filter: ATR20 of the NY session that contains 05:00 IST of the trading day (label = same date)
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    atr = d["atr20"].reindex(day).to_numpy()
    vol_ok = atr >= med.reindex(day).to_numpy()                                # NaN -> False (warm-up)

    # equity filter: running R of trades closed strictly before each entry vs its 50-trade average
    exits = np.array([t.exit_i for t in tr])
    cum = np.cumsum(R)
    ma = pd.Series(cum).rolling(50).mean().to_numpy()
    n_before = np.searchsorted(exits, [t.entry_i for t in tr], side="left")
    eq_ok = np.array([True if n < 50 else cum[n - 1] >= ma[n - 1] for n in n_before])

    sets = {"box (no filter)": np.ones(len(tr), bool), "vol filter": vol_ok, "equity filter": eq_ok,
            "vol + equity": vol_ok & eq_ok}
    rows = []
    for name, keep in sets.items():
        rows.append({"setup": name, "share of trades kept %": keep.mean() * 100, **stats(R[keep], day[keep])})
    res = pd.DataFrame(rows).set_index("setup")
    base = res.loc["box (no filter)"]
    res["accepted"] = [None] + [bool(all(res.loc[s, f"{p} max DD % (0.5%)"] < base[f"{p} max DD % (0.5%)"] for p in PERIODS)
                                     and res.loc[s, "check avg R"] >= base["check avg R"]
                                     and res.loc[s, "holdout avg R"] >= base["holdout avg R"]) for s in res.index[1:]]
    res.to_csv(f"{OUT}/summary.csv")
    open(f"{OUT}/REPORT.md", "w").write("# Drawdown filters for the USDJPY green box (2010–2026)\n\n"
                                        "Filters and acceptance rule in run_box_dd_filters.py (fixed before running).\n\n"
                                        + fmt_table(res, ".2f") + "\n")
    pd.set_option("display.width", 250)
    print(res.round(3).T.to_string())
