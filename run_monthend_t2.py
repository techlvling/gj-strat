"""Follow-up on the flow atlas: the USD bid on the 3rd-last weekday of the month (11:00-12:00 UTC).

Hypothesis (fixed before running): spot FX settles two business days after the trade (T+2), so dollars
needed ON the last business day of the month are bought on the 3rd-last. USDCAD settles T+1, so its
dollars for month-end are bought one day later, on the 2nd-last.
Tests, every one at the window the atlas found (11:00-12:00 UTC = 16:30-17:30 IST), SL 0.25 x ATR20,
real bid/ask + $7/lot + 0.2 pip slippage + swap:
  1. Buy USD in each of the 7 USD pairs on the k-th last weekday, k = 0 (last) .. 4.
     Prediction P1: the six T+2 pairs (basket, equal weight) do best at k = 2.
     Prediction P2: USDCAD does best at k = 1.
  2. The six-pair basket at k = 2 per period (2010-17 / 2018-23 / 2024-26): prediction P3, > 0 in all three.
  3. Quarter-end months vs other months (descriptive).
  4. USD strength (from the atlas) per UTC half-hour on 3rd-last weekdays vs other weekdays (descriptive).

    python run_monthend_t2.py
"""
import os
import warnings
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import MAJORS, load_market
from gjstrat.patterns import Signal, daily_table, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER, per_stats
from run_flow_atlas import FILES, G, T0, ny_label
from run_usdjpy_sl import tstat

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT = "results/monthend_t2"
KS = range(5)
T2_PAIRS = [p for p in MAJORS if p != "USDCAD"]


def kth_last(days):
    D = days.values.astype("datetime64[D]")
    m1 = (D.astype("datetime64[M]") + np.timedelta64(1, "M")).astype("datetime64[D]")
    return np.busday_count(D + np.timedelta64(1, "D"), m1)


def pair_trades(sym):
    m = load_market(FILES[sym])
    d = daily_table(m)
    sw = SwapModel.from_fred("rates", 1.0)
    days = pd.bdate_range("2010-01-04", "2026-10-06")
    k = kth_last(days)
    rows = []
    for kk in KS:
        sigs = []
        for day in days[k == kk]:
            i, j = m.idx(day + pd.Timedelta(hours=11)), m.idx(day + pd.Timedelta(hours=12))
            if j >= m.n - 1:
                continue
            live = np.flatnonzero(m.vol[i: i + 5] > 0)
            atr = d["atr20"].get(ny_label(day + pd.Timedelta(hours=11)), np.nan)
            if not len(live) or np.isnan(atr):
                continue
            side = "BUY" if sym.startswith("USD") else "SELL"
            sigs.append(Signal(day, side, i + live[0], "market", None, i + live[0] + 1, 0.25 * atr, None, j, "t2"))
        tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
        r = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)["R"].to_numpy()
        rows += [{"symbol": sym, "k": kk, "day": t.day, "R": x} for t, x in zip(tr, r)]
    print("done", sym, flush=True)
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with Pool(4) as pool:
        X = pd.DataFrame([x for xs in pool.map(pair_trades, MAJORS, chunksize=1) for x in xs])
    X.to_csv(f"{OUT}/trades.csv", index=False)
    lab = {0: "last", 1: "2nd-last", 2: "3rd-last", 3: "4th-last", 4: "5th-last"}

    # 1. every pair x k, all years
    t1 = X.groupby(["symbol", "k"])["R"].agg(["count", "mean", tstat]).rename(columns={"count": "trades", "mean": "avg R", "tstat": "t"})
    piv = t1["avg R"].unstack("k").rename(columns=lambda c: f"{lab[c]} avg R")
    pivt = t1["t"].unstack("k").rename(columns=lambda c: f"{lab[c]} t")
    tab1 = piv.join(pivt)[[f"{lab[k]} {s}" for k in KS for s in ("avg R", "t")]]

    # basket = mean R of the six T+2 pairs per day (days where all six traded)
    B = X[X.symbol.isin(T2_PAIRS)].pivot_table(index=["k", "day"], columns="symbol", values="R").dropna().mean(1).rename("R").reset_index()
    rows = []
    for kk in KS:
        b = B[B.k == kk]
        rows.append({"day": f"{lab[kk]} weekday", "basket days": len(b), "avg R 2010-26": b.R.mean(), "t 2010-26": tstat(b.R),
                     **per_stats(b.R.to_numpy(), pd.DatetimeIndex(b.day))})
    tab2 = pd.DataFrame(rows).set_index("day")
    best_basket = int(tab2["avg R 2010-26"].to_numpy().argmax())
    best_cad = int(piv.loc["USDCAD"].to_numpy().argmax())
    b2 = B[B.k == 2]
    p3 = all(per_stats(b2.R.to_numpy(), pd.DatetimeIndex(b2.day))[f"{p} avg R"] > 0 for p in PER)

    # 3. quarter-end months
    qe = pd.DatetimeIndex(b2.day).month.isin([3, 6, 9, 12])
    tab3 = pd.DataFrame([{"months": nm, "basket days": int(msk.sum()), "avg R": b2.R[msk].mean(), "t": tstat(b2.R[msk])}
                         for nm, msk in (("quarter-end", qe), ("other", ~qe))]).set_index("months")

    # 4. USD strength profile by UTC half-hour, 3rd-last weekday vs other weekdays
    usd = np.load("data/flow_series_v2.npz")["USD"]
    ts = T0 + pd.to_timedelta(np.arange(G) * 30, unit="min")
    day = pd.DatetimeIndex(ts).normalize()
    wk = day.dayofweek < 5
    kk = np.full(G, -1)
    kk[wk] = kth_last(day[wk])
    slot = pd.DatetimeIndex(ts).hour * 2 + pd.DatetimeIndex(ts).minute // 30
    prof = []
    for s in range(48):
        a = usd[(kk == 2) & (slot == s)]
        o = usd[wk & (kk != 2) & (slot == s)]
        a, o = a[~np.isnan(a)], o[~np.isnan(o)]
        prof.append({"UTC": f"{s // 2:02d}:{(s % 2) * 30:02d}", "IST": (pd.Timestamp("2000-01-01") + pd.Timedelta(minutes=30 * s + 330)).strftime("%H:%M"),
                     "3rd-last bp": a.mean(), "3rd-last t": tstat(a), "other days bp": o.mean()})
    tab4 = pd.DataFrame(prof).set_index("UTC")

    verdict = (f"P1 (six-pair basket best at the 3rd-last weekday): {'YES' if best_basket == 2 else 'NO'} (best: {lab[best_basket]}). "
               f"P2 (USDCAD best at the 2nd-last weekday): {'YES' if best_cad == 1 else 'NO'} (best: {lab[best_cad]}). "
               f"P3 (basket > 0 in all three periods): {'YES' if p3 else 'NO'}.")
    open(f"{OUT}/REPORT.md", "w").write(
        "# Month-end T+2 USD bid (11:00–12:00 UTC = 16:30–17:30 IST)\n\nRules and predictions in run_monthend_t2.py (fixed before running).\n\n"
        f"**{verdict}**\n\n## 1. Buy USD 11:00–12:00 UTC on the k-th last weekday, per pair, 2010–2026 (R after costs)\n\n"
        + fmt_table(tab1, ".3f") + "\n\n## 2. Six T+2 pairs as one basket (equal weight)\n\n" + fmt_table(tab2, ".3f")
        + "\n\n## 3. Basket on the 3rd-last weekday: quarter-end months vs others\n\n" + fmt_table(tab3, ".3f")
        + "\n\n## 4. USD strength per half-hour (bp), 3rd-last weekday vs other weekdays, 2010–2026\n\n" + fmt_table(tab4, ".2f") + "\n")
    pd.set_option("display.width", 250)
    print(verdict); print(tab1.round(3).to_string()); print(tab2.round(3).to_string()); print(tab3.round(3).to_string())
    print(tab4.round(2).to_string())
