"""Two adaptive rules on the USDJPY basket (2010-2026), pre-declared.

Base basket: vol-box 0.25% + vol-gotobi 1.5% + fade 0.5% (fade on all days).
  1. Regime switch: the fade only on LOW-vol days (ATR20 < its rolling 250-day median), so in high vol
     the box + gotobi trade and in low vol only the fade does. (Also shows fade R in high vs low vol.)
  2. Strategy momentum: each leg trades only if its own R over the previous 6 months (all its
     signals, closed before the entry) is > 0.
Score per period (2010-17 / 2018-23 / 2024-26): total return % (simple sum of risk x R), max drawdown
of that running sum, and return / max DD. A rule is accepted only if return / max DD beats the base
in all three periods. Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_adaptive.py
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
from run_edge_hunt import PER, per_stats

OUT = "results/adaptive"
RISK = {"vol-box": 0.25, "vol-gotobi": 1.5, "fade": 0.5}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    atr_ok = lambda t: not np.isnan(med.get(t.day, np.nan))
    hot = lambda t: atr_ok(t) and d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2010-01-01")])) if t is not None]

    def frame(name, tr):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        r = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
        return pd.DataFrame({"leg": name, "day": [t.day for t in tr], "entry": [m.ts(t.entry_i) for t in tr],
                             "exit": [m.ts(t.exit_i) for t in tr], "R": r, "hot": [hot(t) for t in tr],
                             "warm": [atr_ok(t) for t in tr]})

    F = pd.concat([frame("vol-box", [t for t in box if hot(t)]), frame("vol-gotobi", [t for t in got if hot(t)]),
                   frame("fade", fade)], ignore_index=True)

    # fade in high vs low vol
    fd = F[F.leg == "fade"]
    split = pd.DataFrame([{"fade on": k, **per_stats(g.R.to_numpy(), pd.DatetimeIndex(g.day))}
                          for k, g in (("high-vol days", fd[fd.hot]), ("low-vol days", fd[~fd.hot & fd.warm]))]).set_index("fade on")

    # momentum flag: leg's R over the 6 months before entry (closed trades only) > 0
    F = F.sort_values("exit").reset_index(drop=True)
    mom = np.zeros(len(F), bool)
    for leg, g in F.groupby("leg"):
        ex, cum = g["exit"].to_numpy(), np.cumsum(g["R"].to_numpy())
        for i, row in g.iterrows():
            a = np.searchsorted(ex, np.datetime64(row.entry - pd.Timedelta(days=182)))
            b = np.searchsorted(ex, np.datetime64(row.entry))
            prior = (cum[b - 1] if b else 0) - (cum[a - 1] if a else 0)
            mom[i] = b > a and prior > 0
    F["mom"] = mom

    def score(mask, label):
        G = F[mask].sort_values("exit")
        x = G.R.to_numpy() * G.leg.map(RISK).to_numpy()
        row = {"basket": label}
        for p, (a, b) in PER.items():
            sel = (pd.DatetimeIndex(G.day) >= pd.Timestamp(a)) & (pd.DatetimeIndex(G.day) <= pd.Timestamp(b))
            eq = np.cumsum(x[np.asarray(sel)])
            dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(eq) else np.nan
            row.update({f"{p} return %": eq[-1] if len(eq) else 0, f"{p} max DD %": dd, f"{p} return/DD": (eq[-1] / dd) if dd else np.nan})
        return row

    allm = np.ones(len(F), bool)
    rows = [score(allm, "base: vol-box + vol-gotobi + fade (all days)"),
            score(~((F.leg == "fade") & (F.hot | ~F.warm)), "1. regime switch: fade only on low-vol days"),
            score(F.mom.to_numpy(), "2. strategy momentum (6-month R > 0)")]
    res = pd.DataFrame(rows).set_index("basket")
    base_row = res.iloc[0]
    res["accepted"] = [None] + [bool(all(res.loc[i, f"{p} return/DD"] > base_row[f"{p} return/DD"] for p in PER)) for i in res.index[1:]]
    res.to_csv(f"{OUT}/summary.csv"); split.to_csv(f"{OUT}/fade_by_vol.csv")
    open(f"{OUT}/REPORT.md", "w").write("# Adaptive rules on the USDJPY basket, 2010–2026\n\nRules in run_adaptive.py (fixed before running).\n\n"
                                        "## Fade in high vs low volatility\n\n" + fmt_table(split, ".3f") +
                                        "\n\n## Baskets (simple-sum % at vol-box 0.25%, vol-gotobi 1.5%, fade 0.5%)\n\n" + fmt_table(res, ".2f") + "\n")
    pd.set_option("display.width", 250)
    print(split.round(3).to_string()); print(res.round(2).T.to_string())
