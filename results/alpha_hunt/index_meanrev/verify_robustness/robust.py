"""Adversarial ROBUSTNESS verifier for the two claimed Nasdaq 100 survivors of `index_meanrev`
(MR4 and MR6). Re-uses the original pipeline pieces (imported, never edited): calendar/VIX helpers,
rsi_wilder, gjstrat.patterns.simulate (minute-by-minute stop on real bid/ask), run_all_matrix.net_r costs,
run_index_anomalies.live_at entry, same segmenting rule (GAP), same periods.

Checks (all fixed before running):
  1. Parameter neighbours (+-25 % / adjacent values), full grids:
       MR4: threshold {0.75, 1.0, 1.25} sigma x hold {4, 5, 6} closes x SL {1.5, 2.0, 2.5} ATR20
            x sigma window {45, 60, 75}                                   (81 combos, 80 neighbours)
       MR6: RSI2 threshold {3.75, 5, 6.25} x trend SMA {150, 200, 250} x exit SMA {4, 5, 6}
            x cap {8, 10, 12} x SL {1.5, 2.0, 2.5}                      (243 combos, 242 neighbours)
     each grid run at signal/entry/exit clock shifted by -30, -15, 0 minutes (signal minute 15:24 / 15:39 /
     15:54 NY) = main neighbour set (every combo except the exact base at shift 0), plus +10 (16:04 signal)
     reported separately: the CFD stops quoting at 16:15 NY (16:00 in 2012 and 2015-17), so +30 after the
     close does not exist on this instrument. Wider one-at-a-time sweeps reported separately.
  2. Time shifts of the base rules: combined clock shift {-60,-45,-30,-15,+10}; exit only {-30,-15,+15}
     (MR6: +15 only - its exit decision needs the 15:54 close); entry delayed +4 (15:59) / +10 (16:05),
     with and without the same exit delay; entry at 10:00 NY the next trading day.
  3. Year split (positive years), leave-one-year-out, removal of the top 3/5/10 trades, best-year share.
  4. Multiple testing: Bonferroni/Holm over the family's 44 tests; drift-aware null = random-entry clones
     with the same mechanics and per-period trade counts -> probability to pass the charter bar by luck.
  5. Drift-adjusted (excess) R for every neighbour: R - period mean log return per calendar day x calendar
     days held x entry / stop (same definition as the family's post-hoc diagnostic).

    python results/alpha_hunt/index_meanrev/verify_robustness/robust.py
"""
from __future__ import annotations

import itertools
import os
import pickle
import sys
import time

ROOT = "/home/user/gj-strat"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gjstrat.data import load_market  # noqa: E402
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate  # noqa: E402
from run_all_matrix import net_r  # noqa: E402
from run_alpha_index_meanrev import GAP, L3, calendar, rsi_wilder  # noqa: E402
from run_edge_hunt import PER  # noqa: E402
from run_index_anomalies import live_at  # noqa: E402
from run_usdjpy_sl import tstat  # noqa: E402

OUT = "results/alpha_hunt/index_meanrev/verify_robustness"
SYM = "USATECHIDXUSD"
PATH = "data/usatechidxusd_2011-01-02_2026-10-07.npz"


def per_of(day):
    for p, (a, b) in PER.items():
        if pd.Timestamp(a) <= day <= pd.Timestamp(b):
            return p
    return None


class Series_:
    """Close series at a given signal minute with lazily computed features; memoised trade execution."""

    def __init__(self, m, d, cal, hh, mm):
        self.m = m
        rows = []
        for day in cal:
            i = local_idx(m, day, hh, mm, NY)
            if i < 0 or i >= m.n - 1 or not m.vol[i] > 0:
                continue
            rows.append((day, i, m.bc[i]))
        cs = pd.DataFrame(rows, columns=["day", "i", "C"]).set_index("day")
        cs["atr20"] = d["atr20"].reindex(cs.index).to_numpy()
        pos = cal.get_indexer(cs.index)
        gap = np.diff(pos, prepend=pos[0] - 1) - 1
        cs["seg"] = np.cumsum(gap > GAP)
        self.cs = cs
        self.C = cs.C.to_numpy()
        self.I = cs.i.to_numpy()
        self.seg = cs.seg.to_numpy()
        self.atr = cs.atr20.to_numpy(dtype=float)
        self.days = cs.index
        self.n = len(cs)
        self._f = {}
        self._memo = {}

    def feat(self, kind, w):
        key = (kind, w)
        if key in self._f:
            return self._f[key]
        out = np.full(self.n, np.nan)
        for s in np.unique(self.seg):
            ix = np.flatnonzero(self.seg == s)
            c = pd.Series(self.C[ix])
            if kind == "sig":
                r = np.log(c / c.shift(1))
                v = r.shift(1).rolling(w).std().to_numpy()
            elif kind == "r":
                v = np.log(c / c.shift(1)).to_numpy()
            elif kind == "sma":
                v = c.rolling(w).mean().to_numpy()
            elif kind == "rsi":
                v = rsi_wilder(c.to_numpy(), w)
            out[ix] = v
        self._f[key] = out
        return out

    def kth(self, j, k):
        jj = j + k
        return jj if jj < self.n and self.seg[jj] == self.seg[j] else None

    def first_above(self, j, sma, cap):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= self.n or self.seg[jj] != self.seg[j]:
                return None
            if self.C[jj] > sma[jj]:
                return jj
        return j + cap

    def execute(self, j, jx, slm, ent_delay=0, exit_off=0):
        key = (j, jx, slm, ent_delay, exit_off)
        if key in self._memo:
            return self._memo[key]
        m = self.m
        if ent_delay == "next10":           # decide at the close, buy at 10:00 NY on the next trading day
            if j + 1 >= jx:
                self._memo[key] = None
                return None
            s = live_at(m, local_idx(m, self.days[j + 1], 10, 0, NY))
        else:
            s = live_at(m, int(self.I[j]) + 1 + ent_delay)
        x = int(self.I[jx]) + 1 + exit_off
        sl = slm * self.atr[j]
        res = None
        if not (s < 0 or x <= s + 1 or x >= m.n or not sl > 0):
            t = simulate(m, Signal(self.days[j], "BUY", s, "market", None, s + 1, sl, None, x, "v"))
            if t is not None:
                R = float(net_r(m, SYM, [t], None)[0])
                hold_days = (m.ts(t.exit_i) - m.ts(t.entry_i)).total_seconds() / 86400
                res = dict(day=self.days[j], j=j, jx=jx, entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i), entry=t.entry,
                           exit=t.exit, reason=t.reason, risk=t.risk, R_gross=t.r, R=R, cal_days=hold_days, hold=jx - j)
        self._memo[key] = res
        return res

    def walk(self, ent, exit_fn, slm, ent_delay=0, exit_off=0, overlap=False):
        busy, rows = -1, []
        for j in np.flatnonzero(ent):
            if (not overlap and j <= busy) or not self.atr[j] > 0:
                continue
            jx = exit_fn(j)
            if jx is None:
                continue
            t = self.execute(j, jx, slm, ent_delay, exit_off)
            if t is None:
                continue
            rows.append(t)
            busy = jx
        return pd.DataFrame(rows)


# --------------------------------------------------------------------------- rules
def mr4(S, thr=1.0, hold=5, sl=2.0, sw=60, **kw):
    r, s = S.feat("r", 1), S.feat("sig", sw)
    with np.errstate(invalid="ignore"):
        ent = r < -thr * s
    return S.walk(ent, lambda j: S.kth(j, hold), sl, **kw)


def mr6(S, rt=5.0, trend=200, ex=5, cap=10, sl=2.0, rn=2, use_trend=True, **kw):
    rsi, smaT, smaE = S.feat("rsi", rn), S.feat("sma", trend), S.feat("sma", ex)
    with np.errstate(invalid="ignore"):
        ent = (rsi < rt) & ((S.C > smaT) if use_trend else np.isfinite(rsi))
    return S.walk(ent, lambda j: S.first_above(j, smaE, cap), sl, **kw)


# --------------------------------------------------------------------------- stats
DRIFT = {}


def set_drift(S):
    """Period drift (mean log return per calendar day) from the base close series."""
    for p, (a, b) in PER.items():
        x = S.cs[(S.cs.index >= a) & (S.cs.index <= b)]
        DRIFT[p] = np.log(x.C.iloc[-1] / x.C.iloc[0]) / (x.index[-1] - x.index[0]).days


def stats(g, name=""):
    row = {"test": name}
    if g is None or not len(g):
        row.update(n=0)
        return row
    r = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    per = np.array([per_of(x) for x in day])
    drift = np.array([DRIFT.get(p, 0.0) for p in per])
    exc = r - drift * g.cal_days.to_numpy() * g.entry.to_numpy() / g.risk.to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    row.update({"n": len(r), "avg R": r.mean(), "t": tstat(r), "win %": (r > 0).mean() * 100,
                "avg win/loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
                "excess R": exc.mean(), "excess t": tstat(exc)})
    for p in PER:
        v, e = r[per == p], exc[per == p]
        row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v),
                    f"{p} excess R": e.mean() if len(e) else np.nan})
    v = r[np.asarray((day >= L3[0]) & (day <= L3[1]))]
    row["last3y avg R"] = v.mean() if len(v) else np.nan
    yr = pd.Series(r, index=day.year).groupby(level=0).mean()
    row["years"] = len(yr)
    row["pos years"] = int((yr > 0).sum())
    row["charter pass"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0) \
        if row["design n"] > 1 else False
    return row


def summarize(G, label):
    G = G.copy()
    nb = G[~G.is_base]
    def frac(mask):
        return f"{int(mask.sum())}/{len(mask)} ({mask.mean() * 100:.0f}%)"
    out = {"grid": label, "neighbours": len(nb),
           "avg R > 0": frac(nb["avg R"] > 0),
           "design>0 & check>0 & holdout>0": frac((nb["design avg R"] > 0) & (nb["check avg R"] > 0) & (nb["holdout avg R"] > 0)),
           "charter pass": frac(nb["charter pass"]),
           "design t >= 2": frac(nb["design t"] >= 2),
           "excess R > 0": frac(nb["excess R"] > 0),
           "excess all 3 periods > 0": frac((nb["design excess R"] > 0) & (nb["check excess R"] > 0) & (nb["holdout excess R"] > 0)),
           "median avg R": round(nb["avg R"].median(), 3), "median excess R": round(nb["excess R"].median(), 3),
           "median design t": round(nb["design t"].median(), 2), "min avg R": round(nb["avg R"].min(), 3)}
    return out


def year_table(g):
    day = pd.DatetimeIndex(g.day)
    y = g.groupby(day.year).R.agg(["count", "mean", "sum"])
    y.index.name = "year"
    return y


def concentration(g, name):
    r = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    srt = np.sort(r)[::-1]
    y = g.groupby(day.year).R.sum()
    row = {"test": name, "n": len(r), "avg R": r.mean(), "t": tstat(r), "total R": r.sum(),
           "best year": int(y.idxmax()), "best year sum R": y.max(), "best-year share of total %": y.max() / r.sum() * 100}
    for k in (1, 3, 5, 10):
        rest = srt[k:]
        row[f"avg R w/o top {k}"] = rest.mean()
        row[f"t w/o top {k}"] = tstat(rest)
    loyo = []
    for yy in sorted(set(day.year)):
        rest = r[day.year != yy]
        loyo.append(rest.mean())
    row["leave-one-year-out min avg R"] = min(loyo)
    row["leave-one-year-out max avg R"] = max(loyo)
    # dropping the best year: does design still clear t>=2?
    bx = g[day.year != row["best year"]]
    st = stats(bx, "")
    row["w/o best year: design t"] = st.get("design t")
    row["w/o best year: check avg R"] = st.get("check avg R")
    row["w/o best year: holdout avg R"] = st.get("holdout avg R")
    return row


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    m = load_market(PATH)
    d = daily_table(m)
    cal = calendar("nyse", m.t0 + pd.Timedelta(days=1), m.ts(m.n - 1))
    # the CFD stops quoting at 16:15 NY (16:00 in 2012 and 2015-2017), so +30 min after the close does not
    # exist; the positive side is +10 (16:04 signal, live only 2013-14 and 2018+) and delayed entries/exits
    shifts = {-60: (14, 54), -45: (15, 9), -30: (15, 24), -15: (15, 39), 0: (15, 54), 10: (16, 4)}
    SS = {k: Series_(m, d, cal, *hm) for k, hm in shifts.items()}
    set_drift(SS[0])
    print("series built", {k: S.n for k, S in SS.items()}, f"{time.time() - t0:.0f}s", flush=True)

    base4, base6 = mr4(SS[0]), mr6(SS[0])
    rows = [stats(base4, "MR4 base"), stats(base6, "MR6 base")]
    print(pd.DataFrame(rows)[["test", "n", "avg R", "design avg R", "design t", "check avg R", "holdout avg R",
                              "last3y avg R"]].round(3).to_string(), flush=True)
    # cross-check vs the saved trades
    T = pd.read_pickle("results/alpha_hunt/index_meanrev/trades.pkl")
    for v, b in (("MR4", base4), ("MR6", base6)):
        o = T[(T.market == SYM) & (T.variant == v)]
        mg = pd.merge(o[["day", "R"]], b[["day", "R"]], on="day", how="outer", suffixes=("_orig", "_ver"))
        print(v, "orig", len(o), "verifier", len(b), "max |dR|", np.nanmax(np.abs(mg.R_orig - mg.R_ver)),
              "unmatched", int(mg.isna().any(axis=1).sum()), flush=True)
    base4.to_csv(f"{OUT}/base_MR4_trades.csv", index=False)
    base6.to_csv(f"{OUT}/base_MR6_trades.csv", index=False)

    # ---------------------------------------------------------------- 1. neighbour grids
    G4, G6 = [], []
    for sh in (-30, -15, 0, 10):
        S = SS[sh]
        for thr, hold, sl, sw in itertools.product((0.75, 1.0, 1.25), (4, 5, 6), (1.5, 2.0, 2.5), (45, 60, 75)):
            g = mr4(S, thr, hold, sl, sw)
            row = stats(g, f"MR4 thr{thr} hold{hold} sl{sl} sig{sw} shift{sh:+d}")
            row.update(shift=sh, thr=thr, hold=hold, sl=sl, sw=sw,
                       is_base=(sh == 0 and thr == 1.0 and hold == 5 and sl == 2.0 and sw == 60))
            G4.append(row)
        print("MR4 grid shift", sh, f"{time.time() - t0:.0f}s", flush=True)
        for rt, trend, ex, cap, sl in itertools.product((3.75, 5.0, 6.25), (150, 200, 250), (4, 5, 6), (8, 10, 12), (1.5, 2.0, 2.5)):
            g = mr6(S, rt, trend, ex, cap, sl)
            row = stats(g, f"MR6 rsi<{rt} sma{trend} exit{ex} cap{cap} sl{sl} shift{sh:+d}")
            row.update(shift=sh, rt=rt, trend=trend, ex=ex, cap=cap, sl=sl,
                       is_base=(sh == 0 and rt == 5.0 and trend == 200 and ex == 5 and cap == 10 and sl == 2.0))
            G6.append(row)
        print("MR6 grid shift", sh, f"{time.time() - t0:.0f}s", flush=True)
    G4, G6 = pd.DataFrame(G4), pd.DataFrame(G6)
    G4.to_csv(f"{OUT}/grid_MR4.csv", index=False)
    G6.to_csv(f"{OUT}/grid_MR6.csv", index=False)
    summ = []
    for G, fam in ((G4, "MR4"), (G6, "MR6")):
        summ.append(summarize(G[G["shift"].isin([-30, -15, 0])], f"{fam} main set (shifts -30/-15/0)"))
        for sh in (-30, -15, 0, 10):
            summ.append(summarize(G[G["shift"] == sh], f"{fam} shift {sh:+d}" + (" (data gaps 2012/15-17)" if sh == 10 else "")))
    # one-parameter-at-a-time neighbours (others at base, shift 0)
    for G, fam, base in ((G4, "MR4", dict(thr=1.0, hold=5, sl=2.0, sw=60)),
                         (G6, "MR6", dict(rt=5.0, trend=200, ex=5, cap=10, sl=2.0))):
        mask = np.zeros(len(G), bool)
        for p in base:
            others = np.ones(len(G), bool)
            for q, v in base.items():
                if q != p:
                    others &= G[q] == v
            mask |= others & (G["shift"] == 0)
        summ.append(summarize(G[mask], f"{fam} one-at-a-time (shift 0)"))
    SUM = pd.DataFrame(summ)
    SUM.to_csv(f"{OUT}/grid_summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
    print(SUM.to_string(), flush=True)

    # marginal views: avg over grid by each parameter value (shift 0)
    marg = []
    for G, fam, params in ((G4, "MR4", ("thr", "hold", "sl", "sw", "shift")), (G6, "MR6", ("rt", "trend", "ex", "cap", "sl", "shift"))):
        for p in params:
            for v, g in G.groupby(p):
                marg.append({"family": fam, "param": p, "value": v, "combos": len(g), "mean avg R": g["avg R"].mean(),
                             "share avg R>0 %": (g["avg R"] > 0).mean() * 100, "share charter pass %": g["charter pass"].mean() * 100,
                             "mean design t": g["design t"].mean(), "mean excess R": g["excess R"].mean()})
    MG = pd.DataFrame(marg)
    MG.to_csv(f"{OUT}/grid_marginals.csv", index=False)
    print(MG.round(3).to_string(), flush=True)

    # ---------------------------------------------------------------- wider one-at-a-time sweeps
    wide = []
    S0 = SS[0]
    for thr in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        wide.append(stats(mr4(S0, thr=thr), f"MR4 thr {thr}"))
    for hold in (1, 2, 3, 4, 5, 6, 7, 8, 10):
        wide.append(stats(mr4(S0, hold=hold), f"MR4 hold {hold}"))
    for sl in (1.0, 1.5, 2.0, 2.5, 3.0, 5.0):
        wide.append(stats(mr4(S0, sl=sl), f"MR4 SL {sl}"))
    for sw in (20, 40, 60, 100, 120):
        wide.append(stats(mr4(S0, sw=sw), f"MR4 sigma window {sw}"))
    for rt in (2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 7.5, 10.0, 15.0):
        wide.append(stats(mr6(S0, rt=rt), f"MR6 RSI2 < {rt}"))
    for rn, rt in ((3, 5.0), (3, 10.0), (3, 15.0), (4, 15.0), (4, 20.0)):
        wide.append(stats(mr6(S0, rt=rt, rn=rn), f"MR6 RSI{rn} < {rt}"))
    for trend in (100, 150, 200, 250, 300):
        wide.append(stats(mr6(S0, trend=trend), f"MR6 trend SMA {trend}"))
    wide.append(stats(mr6(S0, use_trend=False), "MR6 no trend filter"))
    for ex in (3, 4, 5, 6, 7, 10):
        wide.append(stats(mr6(S0, ex=ex), f"MR6 exit SMA {ex}"))
    for cap in (3, 5, 7, 8, 10, 12, 15, 20):
        wide.append(stats(mr6(S0, cap=cap), f"MR6 cap {cap}"))
    for sl in (1.0, 1.5, 2.0, 2.5, 3.0, 5.0):
        wide.append(stats(mr6(S0, sl=sl), f"MR6 SL {sl}"))
    W = pd.DataFrame(wide)
    W.to_csv(f"{OUT}/wide_sweeps.csv", index=False)
    wc = ["test", "n", "avg R", "t", "design n", "design avg R", "design t", "check avg R", "holdout avg R", "last3y avg R",
          "excess R", "pos years", "years", "charter pass"]
    print(W[wc].round(3).to_string(), flush=True)

    # ---------------------------------------------------------------- 2. time shifts of the base
    ts_rows = []
    for sh in (-60, -45, -30, -15, 0, 10):
        ts_rows.append(stats(mr4(SS[sh]), f"MR4 clock {sh:+d} min (signal+entry+exit)"))
        ts_rows.append(stats(mr6(SS[sh]), f"MR6 clock {sh:+d} min (signal+entry+exit)"))
    for off in (-30, -15, 15):
        ts_rows.append(stats(mr4(S0, exit_off=off), f"MR4 exit only {off:+d} min"))
    ts_rows.append(stats(mr6(S0, exit_off=15), "MR6 exit only +15 min"))
    ts_rows.append(stats(mr4(S0, ent_delay="next10"), "MR4 entry next day 10:00 NY"))
    ts_rows.append(stats(mr6(S0, ent_delay="next10"), "MR6 entry next day 10:00 NY"))
    for dl in (4, 10):
        ts_rows.append(stats(mr4(S0, ent_delay=dl), f"MR4 entry delayed +{dl} min"))
        ts_rows.append(stats(mr6(S0, ent_delay=dl), f"MR6 entry delayed +{dl} min"))
        ts_rows.append(stats(mr4(S0, ent_delay=dl, exit_off=dl), f"MR4 entry+exit delayed +{dl} min (signal 15:54)"))
        ts_rows.append(stats(mr6(S0, ent_delay=dl, exit_off=dl), f"MR6 entry+exit delayed +{dl} min (signal 15:54)"))
    TS = pd.DataFrame(ts_rows)
    TS.to_csv(f"{OUT}/time_shifts.csv", index=False)
    print(TS[wc].round(3).to_string(), flush=True)

    # ---------------------------------------------------------------- 3. year split / concentration
    for nm, g in (("MR4", base4), ("MR6", base6)):
        y = year_table(g)
        y.to_csv(f"{OUT}/years_{nm}.csv")
        print(nm, "by year\n", y.round(3).to_string(), flush=True)
    CO = pd.DataFrame([concentration(base4, "MR4"), concentration(base6, "MR6")])
    CO.to_csv(f"{OUT}/concentration.csv", index=False)
    print(CO.round(3).T.to_string(), flush=True)

    # ---------------------------------------------------------------- 4. drift-aware null (random-entry clones)
    # pools: every eligible signal day, overlapping, same mechanics
    sig60 = S0.feat("sig", 60)
    pool4 = S0.walk(np.isfinite(sig60), lambda j: S0.kth(j, 5), 2.0, overlap=True)
    smaT, smaE, rsi = S0.feat("sma", 200), S0.feat("sma", 5), S0.feat("rsi", 2)
    with np.errstate(invalid="ignore"):
        elig6 = S0.C > smaT
    pools6 = {h: S0.walk(elig6, lambda j, h=h: S0.kth(j, h), 2.0, overlap=True) for h in range(1, 11)}
    # same mechanics as MR6 (exit first close > SMA5) but entering on random below-SMA5 days with C > SMA200
    with np.errstate(invalid="ignore"):
        elig6b = (S0.C > smaT) & (S0.C < smaE)
    pool6b = S0.walk(elig6b, lambda j: S0.first_above(j, smaE, 10), 2.0, overlap=True)
    with open(f"{OUT}/pools.pkl", "wb") as f:
        pickle.dump(dict(pool4=pool4, pools6=pools6, pool6b=pool6b), f)
    print("pools", len(pool4), {h: len(p) for h, p in pools6.items()}, len(pool6b), f"{time.time() - t0:.0f}s", flush=True)

    rng = np.random.default_rng(20261010)
    K = 20000
    nul = []

    def run_null(name, sig_g, draw):
        cnt = sig_g.day.map(per_of).value_counts().to_dict()
        passes, means, dts = 0, [], []
        for _ in range(K):
            ok, allr = True, []
            res = {}
            for p in ("design", "check", "holdout"):
                x = draw(p, cnt.get(p, 0))
                res[p] = x
                allr.append(x)
            dt = tstat(res["design"])
            ok = dt >= 2 and res["check"].mean() > 0 and res["holdout"].mean() > 0
            passes += ok
            means.append(np.concatenate(allr).mean())
            dts.append(dt)
        means, dts = np.array(means), np.array(dts)
        st = stats(sig_g, "")
        nul.append({"null": name, "counts": cnt, "P(pass charter bar)": passes / K,
                    "P(random design t >= signal design t)": float(np.mean(dts >= st["design t"])),
                    "P(random full avg R >= signal avg R)": float(np.mean(means >= st["avg R"])),
                    "random mean avg R": means.mean(), "signal avg R": st["avg R"], "signal design t": st["design t"]})

    P4 = {p: pool4[pool4.day.map(per_of) == p].R.to_numpy() for p in PER}
    run_null("MR4: random days, hold 5, SL 2", base4, lambda p, n: rng.choice(P4[p], n, replace=False))
    P6 = {(h, p): pools6[h][pools6[h].day.map(per_of) == p].R.to_numpy() for h in pools6 for p in PER}
    holds6 = base6.hold.to_numpy()

    def draw6(p, n):
        hh = rng.choice(holds6, n)
        return np.array([rng.choice(P6[(h, p)]) for h in hh])
    run_null("MR6: random C>SMA200 days, hold-matched to MR6, SL 2", base6, draw6)
    P6b = {p: pool6b[pool6b.day.map(per_of) == p].R.to_numpy() for p in PER}
    run_null("MR6: random C>SMA200 & C<SMA5 days, MR6 exit rule, SL 2", base6, lambda p, n: rng.choice(P6b[p], n, replace=True))
    NU = pd.DataFrame(nul)
    NU.to_csv(f"{OUT}/null_passrate.csv", index=False)
    print(NU.to_string(), flush=True)
    print("DONE", f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
