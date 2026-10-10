"""Verifier: independent re-implementation of the S&P 500 (hourly bid candles) MR4 / MR6 replication, plus a
hold-matched random-long benchmark, compared with the saved trades.pkl.

    python results/alpha_hunt/index_meanrev/verify_code/reimpl_spx.py
"""
from __future__ import annotations

import glob
import lzma
import os

import holidays
import numpy as np
import pandas as pd

NY = "America/New_York"
DT = np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
PER = {"design": ("2010-01-01", "2017-12-31"), "check": ("2018-01-01", "2023-12-31"), "holdout": ("2024-01-01", "2026-12-31")}


def t_of(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 1 else np.nan


def bars():
    out = []
    for f in sorted(glob.glob("data/hourly/USA500IDXUSD/*.bi5")):
        raw = open(f, "rb").read()
        if not raw:
            continue
        y, mo = map(int, os.path.basename(f)[:-4].split("_"))
        a = np.frombuffer(lzma.decompress(raw), dtype=DT)
        ts = pd.Timestamp(y, mo, 1) + pd.to_timedelta(a["t"].astype(np.int64), unit="s")
        out.append(pd.DataFrame({"o": a["o"] / 1e3, "h": a["h"] / 1e3, "l": a["l"] / 1e3, "c": a["c"] / 1e3, "v": a["v"]}, index=ts))
    b = pd.concat(out).sort_index()
    b = b[~b.index.duplicated()]
    return b[b.v > 0]


def run():
    b = bars()
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    lab = (loc + pd.Timedelta(hours=7)).normalize()
    day = pd.DataFrame({"h": b.h.values, "l": b.l.values}, index=lab).groupby(level=0).agg(h=("h", "max"), l=("l", "min"))
    day = day[day.index.dayofweek < 5]
    atr = (day.h - day.l).rolling(20).mean().shift(1)
    hol = set(holidays.NYSE(years=range(2011, 2027)))
    cal = pd.DatetimeIndex([d for d in pd.bdate_range("2012-01-01", "2026-10-07") if d.date() not in hol])
    m15 = np.asarray(loc.hour == 15)
    cs = pd.DataFrame({"C": b.c.values[m15], "k": np.flatnonzero(m15)}, index=loc[m15].normalize())
    cs = cs[cs.index.isin(cal)]
    pos = cal.get_indexer(cs.index)
    cs["seg"] = np.cumsum((np.diff(pos, prepend=pos[0] - 1) - 1) > 5)
    parts = []
    for _, g in cs.groupby("seg"):
        g = g.copy()
        c = g.C
        g["r"] = np.log(c).diff()
        g["s60"] = g.r.shift(1).rolling(60).std()
        d = c.diff()
        ag = d.clip(lower=0).iloc[1:].ewm(alpha=0.5, adjust=False).mean()
        al = (-d).clip(lower=0).iloc[1:].ewm(alpha=0.5, adjust=False).mean()
        rsi = 100 - 100 / (1 + ag / al)
        rsi[(al == 0) & (ag > 0)] = 100.0
        rsi[(al == 0) & (ag == 0)] = 50.0
        rsi.iloc[0] = np.nan
        g["rsi"] = rsi.reindex(g.index)
        g["s200"], g["s5"] = c.rolling(200).mean(), c.rolling(5).mean()
        parts.append(g)
    cs = pd.concat(parts)
    cs["A"] = atr.reindex(cs.index).values
    C, seg, K = cs.C.values, cs.seg.values, cs.k.values
    r, s60, rsi, s200, s5, A = (cs[x].values for x in ("r", "s60", "rsi", "s200", "s5", "A"))
    N = len(cs)
    O, L = b.o.values, b.l.values

    def trade(j, jx):
        sl = 2.0 * A[j]
        if not sl > 0:
            return None
        e = C[j] + 0.5
        stop = e - sl
        seg_l = L[K[j] + 1: K[jx] + 1]           # bars after the entry bar up to and incl. the exit-day 15:00 bar
        hit = np.flatnonzero(seg_l <= stop)
        if len(hit):
            q = K[j] + 1 + hit[0]
            px, why = min(stop, O[q]) - 0.25, "SL"
            xd = (b.index[q] + pd.Timedelta(minutes=30)).tz_localize("UTC").tz_convert(NY).tz_localize(None).normalize()
        else:
            px, why, xd = C[jx] - 0.5, "TIME", cs.index[jx]
        nights = max((xd - cs.index[j]).days, 0)
        return dict(day=cs.index[j], h=jx - j, R=(px - e - 0.03 * nights / 365 * e) / sl, reason=why)

    def kth(j, k):
        jj = j + k
        return jj if jj < N and seg[jj] == seg[j] else None

    def fx(j, cap=10):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= N or seg[jj] != seg[j]:
                return None
            if C[jj] > s5[jj]:
                return jj
        return j + cap

    def walk(ent, ex):
        busy, rows = -1, []
        for j in np.flatnonzero(ent):
            if j <= busy or not A[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = trade(j, jx)
            if t is None:
                continue
            rows.append(t)
            busy = jx
        return pd.DataFrame(rows)

    with np.errstate(invalid="ignore"):
        res = {"MR4": walk(r < -s60, lambda j: kth(j, 5)), "MR6": walk((C > s200) & (rsi < 5), fx)}
        pools = {}
        for name, elig, df in (("MR4", np.isfinite(s60), res["MR4"]), ("MR6", C > s200, res["MR6"])):
            for h in sorted(set(df.h)):
                rows = []
                for j in np.flatnonzero(elig):
                    jx = kth(j, h)
                    if jx is None or not A[j] > 0:
                        continue
                    t = trade(j, jx)
                    if t:
                        rows.append(t)
                pools[(name, h)] = pd.DataFrame(rows)
    return res, pools


def per_of(d):
    for p, (a, b) in PER.items():
        if pd.Timestamp(a) <= d <= pd.Timestamp(b):
            return p


if __name__ == "__main__":
    res, pools = run()
    T = pd.read_pickle("results/alpha_hunt/index_meanrev/trades.pkl")
    for v, g in res.items():
        o = T[(T.market == "USA500IDXUSD") & (T.variant == v)]
        mg = o.merge(g, on="day", how="outer", indicator=True, suffixes=("_o", "_m"))
        both = mg[mg._merge == "both"]
        print(f"{v}: orig {len(o)} avg {o.R.mean():+.4f} | mine {len(g)} avg {g.R.mean():+.4f} | match {mg._merge.value_counts().to_dict()} "
              f"| max |dR| {np.abs(both.R_o - both.R_m).max():.2e}")
        g = g.assign(per=g.day.map(per_of))
        bench = {}
        for (nm, h), P in pools.items():
            if nm == v:
                for p, x in P.assign(per=P.day.map(per_of)).groupby("per"):
                    bench[(h, p)] = x.R.mean()
        g["ex"] = g.R - [bench[(h, p)] for h, p in zip(g.h, g.per)]
        for p in PER:
            x = g[g.per == p]
            print(f"   {p}: n={len(x)} avg R {x.R.mean():+.3f} (t {t_of(x.R):.2f}) | hold-matched excess {x.ex.mean():+.3f} (t {t_of(x.ex):.2f})")
