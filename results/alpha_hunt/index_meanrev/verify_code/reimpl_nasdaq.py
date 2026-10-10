"""Independent re-implementation (verifier) of Nasdaq 100 MR4 and MR6 from run_alpha_index_meanrev.py.
Uses only numpy/pandas/holidays on the raw npz (no gjstrat / run_* helpers), then compares trade by trade
with the saved trades.pkl, and runs sensitivity checks.

    python results/alpha_hunt/index_meanrev/verify_code/reimpl_nasdaq.py
"""
from __future__ import annotations

import sys
from datetime import date

import holidays
import numpy as np
import pandas as pd

NY = "America/New_York"
PATH = "data/usatechidxusd_2011-01-02_2026-10-07.npz"
OUTD = "results/alpha_hunt/index_meanrev/verify_code"
PER = {"design": ("2010-01-01", "2017-12-31"), "check": ("2018-01-01", "2023-12-31"), "holdout": ("2024-01-01", "2026-12-31")}
SLIP, FIN = 0.25, 0.03 / 365


def t_of(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 1 else np.nan


def load():
    z = np.load(PATH)
    t0 = pd.Timestamp(str(z["t0"]))
    d = {k: z[k] for k in ("bo", "bh", "bl", "bc", "ao", "vol")}
    return t0, d


def main(segment=True, sig_mm=54, cost_mult=1.0, rules_fn=None):
    t0, z = load()
    bo, bh, bl, bc, ao, vol = z["bo"], z["bh"], z["bl"], z["bc"], z["ao"], z["vol"]
    n = len(bo)
    utc = t0 + pd.to_timedelta(np.arange(n, dtype=np.int64), unit="min")
    loc = pd.DatetimeIndex(utc).tz_localize("UTC").tz_convert(NY).tz_localize(None)
    mod = loc.hour * 60 + loc.minute
    # ---- daily ATR20: NY 17:00-17:00 days from live minutes, Mon-Fri labels, mean of 20 previous H-L
    live = vol > 0
    lab = (loc[live] + pd.Timedelta(hours=7)).normalize()
    dd = pd.DataFrame({"h": bh[live], "l": bl[live]}, index=lab).groupby(level=0).agg(h=("h", "max"), l=("l", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.h - dd.l).rolling(20).mean().shift(1)
    # ---- signal closes: 15:(sig_mm) NY minute with ticks, NYSE trading day
    yrs = range(2011, 2027)
    hol = set(holidays.NYSE(years=yrs))
    sel = np.flatnonzero((mod == 15 * 60 + sig_mm) & live)
    days = loc[sel].normalize()
    keep = np.array([(d.dayofweek < 5) and (d.date() not in hol) for d in days])
    sel, days = sel[keep], days[keep]
    cs = pd.DataFrame({"i": sel, "C": bc[sel]}, index=days)
    cs = cs[cs.index >= pd.Timestamp("2011-09-19")]
    # trading-day gap -> segments
    cal = pd.bdate_range("2011-09-01", "2026-10-31")
    cal = pd.DatetimeIndex([d for d in cal if d.date() not in hol])
    pos = cal.get_indexer(cs.index)
    gap = np.diff(pos, prepend=pos[0] - 1) - 1
    cs["seg"] = np.cumsum(gap > 5) if segment else 0
    feats = []
    for _, g in cs.groupby("seg"):
        g = g.copy()
        c = g.C
        g["r"] = np.log(c).diff()
        g["sig60"] = g.r.shift(1).rolling(60).std(ddof=1)
        dlt = c.diff()
        up, dn = dlt.clip(lower=0), (-dlt).clip(lower=0)
        ag = up.iloc[1:].ewm(alpha=0.5, adjust=False).mean()     # Wilder n=2, seeded by mean of first 2
        al = dn.iloc[1:].ewm(alpha=0.5, adjust=False).mean()
        rsi = 100 - 100 / (1 + ag / al)
        rsi[(al == 0) & (ag > 0)] = 100.0
        rsi[(al == 0) & (ag == 0)] = 50.0
        rsi.iloc[0] = np.nan                                      # needs 2 changes
        g["rsi2"] = rsi.reindex(g.index)
        g["sma200"] = c.rolling(200).mean()
        g["sma5"] = c.rolling(5).mean()
        feats.append(g)
    cs = pd.concat(feats)
    cs["atr20"] = atr.reindex(cs.index).to_numpy()
    C, seg, I = cs.C.to_numpy(), cs.seg.to_numpy(), cs.i.to_numpy()
    r, s60, rsi, s200, s5, A = (cs[k].to_numpy(float) for k in ("r", "sig60", "rsi2", "sma200", "sma5", "atr20"))
    N = len(cs)

    def rollover_days(a_ts, b_ts):
        # weekday 17:00 NY rollovers in (a, b], Wednesday counts 3
        dlist = pd.date_range(a_ts.normalize() - pd.Timedelta(days=2), b_ts.normalize() + pd.Timedelta(days=2))
        tot = 0
        for d in dlist:
            if d.dayofweek >= 5:
                continue
            ro = (d + pd.Timedelta(hours=17)).tz_localize(NY).tz_convert("UTC").tz_localize(None)
            if a_ts < ro <= b_ts:
                tot += 3 if d.dayofweek == 2 else 1
        return tot

    def trade(j, jx, k_sl):
        s = -1
        for q in range(I[j] + 1, I[j] + 6):
            if vol[q] > 0:
                s = q
                break
        x = I[jx] + 1
        sl = k_sl * A[j]
        if s < 0 or x <= s + 1 or not sl > 0:
            return None
        e = ao[s]
        stop = e - sl
        hit = np.flatnonzero(bl[s:x] <= stop + 1e-7)
        if len(hit):
            k = s + hit[0]
            px = stop if k == s else (bo[k] if bo[k] < stop - 1e-7 else stop)
            why, xi = "SL", k
        else:
            px, why, xi = bo[x], "TIME", x
        a_ts, b_ts = t0 + pd.Timedelta(minutes=int(s)), t0 + pd.Timedelta(minutes=int(xi))
        cost = cost_mult * (SLIP * (2 if why == "SL" else 1) + FIN * rollover_days(a_ts, b_ts) * e)
        return dict(day=cs.index[j], entry_ts=a_ts, exit_ts=b_ts, entry=e, exit=px, reason=why, risk=sl,
                    R_gross=(px - e) / sl, R=(px - e - cost) / sl)

    def first_exit(j, cap):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= N or seg[jj] != seg[j]:
                return None
            if C[jj] > s5[jj]:
                return jj
        return j + cap

    def kth(j, k):
        jj = j + k
        return jj if jj < N and seg[jj] == seg[j] else None

    if rules_fn is not None:
        return rules_fn(dict(C=C, seg=seg, r=r, s60=s60, rsi=rsi, s200=s200, s5=s5, A=A, N=N, cs=cs), trade)
    with np.errstate(invalid="ignore"):
        rules = {"MR4": (r < -s60, lambda j: kth(j, 5), 2.0),
                 "MR6": ((C > s200) & (rsi < 5), lambda j: first_exit(j, 10), 2.0),
                 "B4": (np.isfinite(s60), lambda j: kth(j, 5), 2.0),
                 "B5": (C > s200, lambda j: first_exit(j, 10), 2.0)}
    out = {}
    for v, (ent, ex, k) in rules.items():
        busy, rows = -1, []
        for j in np.flatnonzero(ent):
            if j <= busy or not A[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = trade(j, jx, k)
            if t is None:
                continue
            rows.append(t)
            busy = jx
        out[v] = pd.DataFrame(rows)
    return out, cs


def stats(g, name):
    rr = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    row = {"test": name, "n": len(rr), "avgR": rr.mean(), "t": t_of(rr), "win%": (rr > 0).mean() * 100}
    for p, (a, b) in PER.items():
        v = rr[(day >= a) & (day <= b)]
        row[f"{p} n"], row[f"{p} avgR"], row[f"{p} t"] = len(v), v.mean() if len(v) else np.nan, t_of(v)
    v = rr[(day >= "2023-10-08") & (day <= "2026-10-07")]
    row["last3y avgR"] = v.mean()
    return row


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    mode = sys.argv[1] if len(sys.argv) > 1 else "base"
    kw = dict(base={}, noseg=dict(segment=False), c2=dict(cost_mult=2.0), m50=dict(sig_mm=50))[mode]
    out, cs = main(**kw)
    rows = [stats(g, f"{mode} {v}") for v, g in out.items()]
    print(pd.DataFrame(rows).round(3).to_string())
    for v, g in out.items():
        g.to_csv(f"{OUTD}/reimpl_{mode}_{v}.csv", index=False)
    if mode == "base":
        T = pd.read_pickle("results/alpha_hunt/index_meanrev/trades.pkl")
        for v in ("MR4", "MR6"):
            o = T[(T.market == "USATECHIDXUSD") & (T.variant == v)].copy()
            o["day"] = pd.to_datetime(o.day)
            mine = out[v]
            mg = o.merge(mine, on="day", how="outer", suffixes=("_orig", "_mine"), indicator=True)
            print(v, "orig", len(o), "mine", len(mine), mg["_merge"].value_counts().to_dict())
            both = mg[mg["_merge"] == "both"]
            print("  max |entry diff|", np.abs(both.entry_orig - both.entry_mine).max(),
                  " max |exit diff|", np.abs(both.exit_orig - both.exit_mine).max(),
                  " max |R diff|", np.abs(both.R_orig - both.R_mine).max(),
                  " reason mismatches", (both.reason_orig != both.reason_mine).sum())
            print(mg[mg["_merge"] != "both"][["day", "_merge", "R_orig", "R_mine"]].to_string())
