"""Can the 1:9 box win more often? Walk-forward trade filter (meta-labelling) on the USDJPY green box.

Trades: Version B, RR 9, BE 3R, SL 1 x box, 05:00 IST box, all days 2010-2026, all costs.
Label: net R > 0. Features, all known at entry (NY-close daily table, shifted):
  box size / ATR20; ATR20 / its 250-day median; trade side x [prior-day return / ATR, (prior close -
  SMA50) / ATR, overnight move 17:00 NY -> 05:00 IST / ATR, entry beyond prior-day high/low / ATR];
  re-entry flag; minutes from 06:00 to the fill; entry spread (pips); weekday dummies; gotobi day;
  last two weekdays of the month.
Model: L2 logistic regression (lambda 1 on standardised features), fixed before running.
Walk-forward: for each year Y = 2014..2026 train on trades before Y, then score Y's trades; keep a trade
if its score >= the median training score (the model's top half).
Accepted if the kept trades' avg R beats both all trades and the current vol-box filter (ATR20 >= 250-day
median) in 2014-17, 2018-23 and 2024-26.

    python run_box_meta.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, is_gotobi, kth_last_weekday, local_idx
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/box_meta"
IST = "Asia/Kolkata"
PER = {"2014-17": ("2014-01-01", "2017-12-31"), "2018-23": ("2018-01-01", "2023-12-31"), "2024-26": ("2024-01-01", "2026-12-31")}


def fit_logit(X, y, lam=1.0, iters=50):
    """L2-penalised logistic regression by Newton's method (intercept not penalised)."""
    Xb = np.c_[np.ones(len(X)), X]
    w = np.zeros(Xb.shape[1])
    P = np.eye(Xb.shape[1]) * lam
    P[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) + P @ w
        H = (Xb * (p * (1 - p))[:, None]).T @ Xb + P
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w


def features(m, d, tr):
    med = d["atr20"].rolling(250, min_periods=250).median()
    c2 = d["close"].shift(2)
    rows = []
    for t in tr:
        r = d.loc[t.day] if t.day in d.index else None
        if r is None or not r.atr20 > 0:
            rows.append(None)
            continue
        sgn = 1 if t.side == "BUY" else -1
        a = r.atr20
        b5 = m.bo[local_idx(m, t.day, 5, 0, IST)]
        o6 = local_idx(m, t.day, 6, 0, IST)
        beyond = (t.entry - r.prev_high) / a if t.side == "BUY" else (r.prev_low - t.entry) / a
        f = {"box / ATR": t.range_pips * m.pip / a, "ATR / median": a / med.get(t.day, np.nan),
             "with prior day": sgn * (r.prev_close - c2.get(t.day, np.nan)) / a, "with SMA50": sgn * (r.prev_close - r.sma50) / a,
             "with overnight": sgn * (b5 - r.prev_close) / a, "beyond prior high/low": beyond, "re-entry": float(t.num == 2),
             "fill minutes": (t.entry_i - o6) / 300, "spread pips": t.spread / m.pip, "gotobi": float(is_gotobi(t.day)),
             "month end": float(kth_last_weekday(pd.DatetimeIndex([t.day]))[0] <= 1)}
        for k, nm in enumerate(["Mon", "Tue", "Wed", "Thu"]):
            f[nm] = float(t.day.dayofweek == k)
        rows.append(f)
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    box, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
                 [x for x in days if x.date() not in sk])
    box = sorted(box, key=lambda t: (t.exit_i, t.entry_i))
    R = account(box, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    d = daily_table(m)
    F = features(m, d, box)
    keep = np.array([f is not None and all(np.isfinite(list(f.values()))) for f in F])
    X = pd.DataFrame([f for f, k in zip(F, keep) if k])
    R, tr = R[keep], [t for t, k in zip(box, keep) if k]
    day = pd.DatetimeIndex([t.day for t in tr])
    y = (R > 0).astype(float)
    score = np.full(len(R), np.nan)
    take = np.zeros(len(R), bool)
    coefs = []
    for Y in range(2014, 2027):
        trn, tst = day < pd.Timestamp(f"{Y}-01-01"), (day >= pd.Timestamp(f"{Y}-01-01")) & (day < pd.Timestamp(f"{Y + 1}-01-01"))
        mu, sd = X[trn].mean(), X[trn].std().replace(0, 1)
        Z = ((X - mu) / sd).to_numpy()
        w = fit_logit(Z[trn], y[trn])
        s_tr = 1 / (1 + np.exp(-np.c_[np.ones(trn.sum()), Z[trn]] @ w))
        s_ts = 1 / (1 + np.exp(-np.c_[np.ones(tst.sum()), Z[tst]] @ w))
        score[tst] = s_ts
        take[tst] = s_ts >= np.median(s_tr)
        coefs.append(pd.Series(w[1:], index=X.columns, name=Y))
    vol = X["ATR / median"].to_numpy() >= 1.0
    oos = day >= pd.Timestamp("2014-01-01")
    rows = []
    for name, mask in (("all box trades", oos), ("vol-box (current filter)", oos & vol), ("model: kept (top half)", oos & take),
                       ("model: skipped", oos & ~take), ("model kept + vol filter", oos & take & vol)):
        r = R[mask]
        wins, losses = r[r > 0], r[r <= 0]
        row = {"set": name, "trades": len(r), "win %": (r > 0).mean() * 100, "avg win / avg loss": wins.mean() / -losses.mean(),
               "avg R": r.mean(), "t": tstat(r)}
        for p, (a, b) in PER.items():
            v = r[np.asarray((day[mask] >= pd.Timestamp(a)) & (day[mask] <= pd.Timestamp(b)))]
            row.update({f"{p} avg R": v.mean(), f"{p} win %": (v > 0).mean() * 100})
        rows.append(row)
    T = pd.DataFrame(rows).set_index("set")
    acc = all(T.loc["model: kept (top half)", f"{p} avg R"] > max(T.loc["all box trades", f"{p} avg R"], T.loc["vol-box (current filter)", f"{p} avg R"])
              for p in PER)
    C = pd.DataFrame(coefs); C.index = [str(i) for i in C.index]
    T.to_csv(f"{OUT}/summary.csv"); C.to_csv(f"{OUT}/coefficients_by_year.csv")
    open(f"{OUT}/REPORT.md", "w").write(
        "# Box meta-labelling: walk-forward logistic filter on the USDJPY 1:9 box\n\nRules in run_box_meta.py (fixed before "
        f"running). Out-of-sample 2014–2026 only.\n\n**Accepted: {acc}**\n\n" + fmt_table(T, ".3f") +
        "\n\n## Model weights (standardised features), by training cut-off year\n\n" + fmt_table(C.T, ".2f") + "\n")
    pd.set_option("display.width", 250)
    print(T.round(3).to_string()); print("accepted:", acc); print(C.T.round(2).to_string())
