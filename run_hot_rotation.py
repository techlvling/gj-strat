"""Short-term alpha, tested walk-forward: do recent winners keep winning next month?

Universe (trade streams, all costs as in run_all_matrix.py): every family in run_all_matrix (BOX-A, BOX-B,
GOTOBI, P2-P4, F1-F3, I1-I5) plus BOX-C fade, vol-filtered BOX-B and GOTOBI (ATR20 >= its 250-day
median) and the month-end USD bid (M-3, USD pairs), on 28 FX pairs, gold, JPN225 and Nasdaq.
Each month M, using only trades closed before M: rank streams by the t-stat of their R over the last
L months (needs >= 5 trades, t > 0), keep the top K, and trade all their signals in month M.
Variants, fixed before running: L = 1 / 3 / 6 months x K = 3 / 5 / 10 (9). Months 2011-07..2026-10.
Accepted if the selected trades' avg R is > 0 AND above the all-streams avg R in each period
(2011-07..2017 / 2018-23 / 2024-26). The accepted variant with the best 2011-17 avg R then goes into
the Alpha Swing prop simulation: alone at 0.5% / 1% per trade, and added to the current basket at 0.5%.

    python run_hot_rotation.py
"""
import os
import pickle
from collections import namedtuple
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.data import MAJORS, build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, month_end_usd_bid, simulate
from gjstrat.prop import prop_table
from gjstrat.swap import SwapModel
from run_all_matrix import MARKETS, PATTERNS, net_r
from run_backtest import fmt_table
from run_m3_addon import ALPHA, build_legs, since
from run_usdjpy_sl import tstat

OUT, CACHE = "results/hot_rotation", "data/hot_streams.pkl"
T0 = pd.Timestamp("2009-12-31")                  # USDJPY grid (prop simulation)
PER = {"2011-07..2017": ("2011-07-01", "2017-12-31"), "2018-23": ("2018-01-01", "2023-12-31"),
       "2024-26": ("2024-01-01", "2026-12-31")}
VARIANTS = [(L, K) for L in (1, 3, 6) for K in (3, 5, 10)]
Tr = namedtuple("Tr", "day entry_i exit_i")


def streams(sym):
    swap = SwapModel.from_fred("rates", 1.0)
    start = date(2011, 1, 2) if "IDX" in sym else date(2010, 1, 1)
    m = build_market(sym, start, date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_{start}_2026-10-07.npz")
    full = daily_table(m)
    med = full["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: full["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    d = full[full.index >= pd.Timestamp(start)]
    days = trading_days(m, start=str(start + pd.Timedelta(days=1)))
    _, probe = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in probe.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    out = {f"BOX-{v}": run(m, Params(rr=9, be_trigger=3, version=v, **base), days)[0] for v in ("A", "B")}
    out["BOX-C fade"] = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)[0]
    out["BOX-B vol"] = [t for t in out["BOX-B"] if hot(t)]
    if sym.endswith("JPY"):
        out["GOTOBI"] = [t for t in (simulate(m, s) for s in gotobi_short(m, d)) if t is not None]
        out["GOTOBI vol"] = [t for t in out["GOTOBI"] if hot(t)]
    if sym in MAJORS:
        out["M-3"] = [t for t in (simulate(m, s) for s in month_end_usd_bid(m, d, "BUY" if sym.startswith("USD") else "SELL"))
                      if t is not None]
    for name, (fn, kw) in PATTERNS.items():
        out[name] = [t for t in (simulate(m, s) for s in fn(m, d, **kw)) if t is not None]
    res = {}
    for name, tr in out.items():
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        r = net_r(m, sym, tr, swap)
        res[name] = (pd.DatetimeIndex([t.day for t in tr]), pd.DatetimeIndex([m.ts(t.entry_i) for t in tr]),
                     pd.DatetimeIndex([m.ts(t.exit_i) for t in tr]), np.asarray(r, dtype=float))
    print(sym, "done", flush=True)
    return sym, res


def load_streams():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    with Pool(3) as pool:
        S = dict(pool.map(streams, MARKETS, chunksize=1))
    pickle.dump(S, open(CACHE, "wb"))
    return S


def selections(df, n_streams, months):
    """sel[(L, K)] = bool array streams x months: picked for that month."""
    mi = {p: i for i, p in enumerate(months)}
    ex = df["exit"].dt.to_period("M").map(mi).to_numpy()
    ok = ~pd.isna(ex)
    ex = ex[ok].astype(int)
    sid, r = df["sid"].to_numpy()[ok], df["R"].to_numpy()[ok]
    shape = (n_streams, len(months) + 1)
    N, S1, S2 = np.zeros(shape), np.zeros(shape), np.zeros(shape)
    np.add.at(N, (sid, ex + 1), 1); np.add.at(S1, (sid, ex + 1), r); np.add.at(S2, (sid, ex + 1), r * r)
    cN, c1, c2 = N.cumsum(1), S1.cumsum(1), S2.cumsum(1)          # column j = months < j
    sel = {}
    for L, K in VARIANTS:
        pick = np.zeros((n_streams, len(months)), bool)
        for j in range(L, len(months)):
            n = cN[:, j] - cN[:, j - L]
            s1, s2 = c1[:, j] - c1[:, j - L], c2[:, j] - c2[:, j - L]
            with np.errstate(divide="ignore", invalid="ignore"):
                mu = s1 / n
                var = (s2 - n * mu ** 2) / (n - 1)
                t = mu / np.sqrt(var / n)
            t[~((n >= 5) & (var > 0) & (t > 0))] = -np.inf
            top = np.argsort(-t)[:K]
            pick[top[np.isfinite(t[top])], j] = True
        sel[(L, K)] = pick
    return sel


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    S = load_streams()
    keys = [(sym, name) for sym in S for name in S[sym] if len(S[sym][name][3])]
    parts = []
    for i, (sym, name) in enumerate(keys):
        day, ent, ex, r = S[sym][name]
        parts.append(pd.DataFrame({"sid": i, "day": day, "entry": ent, "exit": ex, "R": r}))
    df = pd.concat(parts, ignore_index=True)
    months = pd.period_range("2010-01", "2026-10", freq="M")
    sel = selections(df, len(keys), months)
    mi = {p: i for i, p in enumerate(months)}
    dmo = df["day"].dt.to_period("M").map(mi).fillna(0).to_numpy().astype(int)
    live = df["day"] >= pd.Timestamp("2011-07-01")
    rows = []
    for (L, K), pick in [(("all", "all"), None)] + list(sel.items()):
        mask = live.to_numpy() & (True if pick is None else pick[df["sid"].to_numpy(), dmo])
        x = df[mask]
        row = {"lookback months": L, "top K": K, "trades": len(x), "trades / month": len(x) / ((2026 - 2011) * 12 + 4)}
        for p, (a, b) in PER.items():
            v = x["R"][(x["day"] >= pd.Timestamp(a)) & (x["day"] <= pd.Timestamp(b))].to_numpy()
            row.update({f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v)})
        rows.append(row)
    res = pd.DataFrame(rows)
    basel = res.iloc[0]
    res["accepted"] = [None] + [bool(all(res.loc[i, f"{p} avg R"] > 0 and res.loc[i, f"{p} avg R"] > basel[f"{p} avg R"] for p in PER))
                                for i in range(1, len(res))]
    res = res.set_index(["lookback months", "top K"])
    res.to_csv(f"{OUT}/variants.csv")
    pd.set_option("display.width", 250)
    print(res.round(3).to_string(), flush=True)

    # what gets picked most (all variants pooled)
    picks = sum(p.astype(int) for p in sel.values()).sum(1)
    top_picked = pd.Series(picks, index=[f"{a} · {b}" for a, b in keys]).sort_values(ascending=False).head(15)

    prop_txt = "No variant accepted: no prop simulation.\n"
    acc = res[res["accepted"] == True]
    if len(acc):
        L, K = acc["2011-07..2017 avg R"].idxmax()
        pick = sel[(L, K)]
        x = df[live.to_numpy() & pick[df["sid"].to_numpy(), dmo]].sort_values(["exit", "entry"])
        tr = [Tr(dy, int((e - T0) // pd.Timedelta(minutes=1)), int((xx - T0) // pd.Timedelta(minutes=1)))
              for dy, e, xx in zip(x["day"], x["entry"], x["exit"])]
        m, legs = build_legs()
        legs = legs[:4] + [(tr, x["R"].to_numpy())]
        mixes = {"current basket": (0.25, 3, 0.5, 3, 0), f"rotation L{L} K{K} 0.5%": (0, 0, 0, 0, 0.5),
                 f"rotation L{L} K{K} 1%": (0, 0, 0, 0, 1.0), f"basket + rotation 0.5%": (0.25, 3, 0.5, 3, 0.5)}
        tabs = []
        for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
            t = prop_table(m, lg, mixes, **ALPHA)
            t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
            t.insert(0, "window", w)
            tabs.append(t)
        P = pd.concat(tabs)
        P.to_csv(f"{OUT}/prop.csv")
        cols = ["window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
                "months per funded account"]
        prop_txt = fmt_table(P[cols], ".1f") + "\n"
        print(P[cols].round(1).to_string())
    open(f"{OUT}/REPORT.md", "w").write(
        "# Short-term alpha: recent winners next month (walk-forward)\n\nRules in run_hot_rotation.py (fixed before running). "
        f"{len(keys)} trade streams.\n\n## Variants (first row = trade every stream)\n\n" + fmt_table(res, ".3f") +
        "\n\n## Most-picked streams (months picked, all variants)\n\n" + fmt_table(top_picked.to_frame("months"), ".0f") +
        "\n\n## Alpha Swing prop simulation\n\n" + prop_txt)
    print(top_picked.to_string())
