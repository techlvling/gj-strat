"""Add the month-end USD bid (flow atlas: buy USD 11:00-12:00 UTC = 16:30-17:30 IST on the 3rd-last
weekday of the month, SL 0.25 x ATR20, time exit) as a 4th leg to the prop baskets.

Legs: vol-box, vol-gotobi, fade (as before); M-3 USDJPY (one trade a month); M-3 on the other five USD
pairs that settle T+2 (EURUSD, GBPUSD, USDCHF, AUDUSD, NZDUSD), which with USDJPY makes the six-pair basket.
Fixed before running:
  A. Alpha Swing (P1 +10%, P2 +5%, 10% static, 5% daily, >= 3 days, no consistency rule):
     base vol-box 0.25% + vol-gotobi 3% + fade 0.5%; + M-3 USDJPY 1 / 2 / 3%; + six-pair basket at
     0.25% / 0.5% per pair (1.5% / 3% in all).
     An add-on is accepted if months per funded account is lower and pass eventually % is not lower than
     the base, both for challenges started 2011-2025 and for those started 2018-2025 (after the period
     the flow was found in).
  B. Blueberry Instant Elite $2.5k (rules in run_blueberry_elite.py, 10% cushion): base vol-box 0.25% +
     vol-gotobi 1.5%; + M-3 USDJPY 0.5 / 1 / 1.5%; + six-pair basket at 0.25% per pair.
     Accepted if avg paid in 24 months is higher and accounts lost within 24 months is not higher, for
     accounts started 2011-2024 and 2018-2024.
Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_m3_addon.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market, load_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, month_end_usd_bid, simulate
from gjstrat.prop import instant_table, prop_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import per_stats

OUT = "results/m3_addon"
ALPHA = dict(targets=(0.10, 0.05), max_dd=0.10, daily=0.05, min_days=3)
BLUE = dict(size=2_500, split=0.8, min_pay=100, every=14, dd=0.10, qday=0.005, ndays=5, horizon=730)
OTHERS = {"EURUSD": "SELL", "GBPUSD": "SELL", "USDCHF": "BUY", "AUDUSD": "SELL", "NZDUSD": "SELL"}
# risk % per leg: vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 other five pairs
A_MIXES = {"base: vol-box 0.25% + vol-gotobi 3% + fade 0.5%": (0.25, 3, 0.5, 0, 0),
           "+ M-3 USDJPY 1%": (0.25, 3, 0.5, 1, 0), "+ M-3 USDJPY 2%": (0.25, 3, 0.5, 2, 0),
           "+ M-3 USDJPY 3%": (0.25, 3, 0.5, 3, 0),
           "+ M-3 six pairs 0.25% each (1.5%)": (0.25, 3, 0.5, 0.25, 0.25),
           "+ M-3 six pairs 0.5% each (3%)": (0.25, 3, 0.5, 0.5, 0.5)}
B_MIXES = {"base: vol-box 0.25% + vol-gotobi 1.5%": (0.25, 1.5, 0, 0, 0),
           "+ M-3 USDJPY 0.5%": (0.25, 1.5, 0, 0.5, 0), "+ M-3 USDJPY 1%": (0.25, 1.5, 0, 1, 0),
           "+ M-3 USDJPY 1.5%": (0.25, 1.5, 0, 1.5, 0),
           "+ M-3 six pairs 0.25% each (1.5%)": (0.25, 1.5, 0, 0.25, 0.25)}


def net(m, sym, tr, sw):
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    return tr, account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)["R"].to_numpy()


def since(legs, day):
    out = []
    for tr, r in legs:
        keep = np.array([t.day >= pd.Timestamp(day) for t in tr], dtype=bool)
        out.append(([t for t, k in zip(tr, keep) if k], r[keep]))
    return out


def build_legs():
    """USDJPY market and the five legs: vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 other five pairs."""
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    d = daily_table(m)
    d11 = d[d.index >= pd.Timestamp("2011-01-01")]
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d11)) if t is not None]
    m3 = [t for t in (simulate(m, s) for s in month_end_usd_bid(m, d11, "BUY")) if t is not None]
    legs = [net(m, "USDJPY", [t for t in box if hot(t)], sw), net(m, "USDJPY", [t for t in got if hot(t)], sw),
            net(m, "USDJPY", fade, sw), net(m, "USDJPY", m3, sw)]
    other_tr, other_r = [], []
    for sym, side in OTHERS.items():
        mp = load_market(f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        assert mp.t0 == m.t0                                   # same minute grid as USDJPY
        dp = daily_table(mp)
        tr, r = net(mp, sym, [t for t in (simulate(mp, s) for s in month_end_usd_bid(mp, dp[dp.index >= pd.Timestamp("2011-01-01")], side))
                              if t is not None], sw)
        other_tr += tr; other_r.append(r)
        print("M-3", sym, len(tr), round(r.mean(), 3), flush=True)
        del mp
    order = sorted(range(len(other_tr)), key=lambda k: (other_tr[k].exit_i, other_tr[k].entry_i))
    other_r = np.concatenate(other_r)[order]
    legs.append(([other_tr[k] for k in order], other_r))
    return m, legs


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m, legs = build_legs()
    # the new legs on their own
    rows = []
    for name, (tr, r) in (("M-3 USDJPY", legs[3]), ("M-3 other five pairs", legs[4])):
        rows.append({"leg": name, "trades": len(r), "win %": (r > 0).mean() * 100, "avg R": r.mean(),
                     **per_stats(r, pd.DatetimeIndex([t.day for t in tr]))})
    solo = pd.DataFrame(rows).set_index("leg")

    # A. Alpha Swing
    atabs = []
    for label, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
        tab = prop_table(m, lg, A_MIXES, **ALPHA)
        tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
        tab.insert(0, "window", label)
        atabs.append(tab)
        print("alpha", label, flush=True)
    A = pd.concat(atabs)
    ok_a = {}
    for mix in list(A_MIXES)[1:]:
        ok_a[mix] = all(A[A.window == w].loc[mix, "months per funded account"] < A[A.window == w].iloc[0]["months per funded account"]
                        and A[A.window == w].loc[mix, "pass eventually %"] >= A[A.window == w].iloc[0]["pass eventually %"]
                        for w in A.window.unique())
    A["accepted"] = [None if mix == list(A_MIXES)[0] else ok_a[mix] for mix in A.index]
    A.to_csv(f"{OUT}/alpha.csv")

    # B. Blueberry Instant Elite
    btabs = []
    for label, lg in (("starts 2011-2024", legs), ("starts 2018-2024", since(legs, "2018-01-01"))):
        tab = instant_table(m, lg, B_MIXES, (0.10,), last_start="2024-10-07", **BLUE).droplevel(0)
        tab.insert(0, "window", label)
        btabs.append(tab)
        print("blueberry", label, flush=True)
    B = pd.concat(btabs)
    ok_b = {}
    for mix in list(B_MIXES)[1:]:
        ok_b[mix] = all(B[B.window == w].loc[mix, "avg paid in 24 months $"] > B[B.window == w].iloc[0]["avg paid in 24 months $"]
                        and B[B.window == w].loc[mix, "account lost within 24 months %"] <= B[B.window == w].iloc[0]["account lost within 24 months %"]
                        for w in B.window.unique())
    B["accepted"] = [None if mix == list(B_MIXES)[0] else ok_b[mix] for mix in B.index]
    B.to_csv(f"{OUT}/blueberry.csv")

    acols = ["window", "pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
             "median months to pass", "months per funded account", "max DD %", "accepted"]
    bcols = ["window", "got ≥1 payout %", "avg paid in 12 months $", "avg paid in 24 months $", "avg per month $",
             "account lost within 24 months %", "accepted"]
    A.index.name = B.index.name = "mix"
    open(f"{OUT}/REPORT.md", "w").write(
        "# Month-end USD bid (M-3) as a 4th prop leg\n\nRules and acceptance in run_m3_addon.py (fixed before running).\n\n"
        "## The new legs alone (avg R after costs)\n\n" + fmt_table(solo, ".3f") +
        "\n\n## A. Alpha Swing $10k\n\n" + fmt_table(A[acols], ".1f") +
        "\n\n## B. Blueberry Instant Elite $2.5k (10% cushion)\n\n" + fmt_table(B[bcols], ".0f") + "\n")
    pd.set_option("display.width", 250)
    print(solo.round(3).to_string()); print(A[acols].round(1).to_string()); print(B[bcols].round(0).to_string())
