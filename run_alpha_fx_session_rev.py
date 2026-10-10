"""Alpha hunt, family `fx_session_rev`: conditional cross-session currency-strength reversal.
Asia/overnight extremes faded into London/NY. Spec fixed BEFORE running; nothing below was chosen from the data.

Theory: home-hours order flow pushes a currency away from fair value overnight; foreign dealers absorb it in
London/NY and revert the move (Breedon & Ranaldo 2013 JMCB; Ranaldo 2009). Grossman & Miller 1988: the price
concession grows with the size of the imbalance, so we condition on unusually large overnight dispersion and trade
only the extreme pair. Krohn, Mueller & Whelan 2024 JF: USD bid into fixes, reversing after. The flow atlas found
this only unconditionally (1-3 bp, below costs). Competing pre-declared hypothesis: intraday momentum
(Elaut, Frommel & Lampaert 2018) -> the momentum variants, judged with the same bar.

DAYS
  t = every weekday (London date) 2010-01-04 .. 2026-10-07.
  Stamp A = close of the 16:54 America/New_York minute of the previous weekday (Friday for a Monday), before the
            17:00 NY rollover.  Stamp B = close of the 06:59 Europe/London minute of day t.
  Both DST-aware, exactly as gjstrat.patterns.local_idx (computed vectorised, then asserted equal to local_idx for
  every day). Entry minute E = 07:00 London of t (= B + 1).
  Exit X1 = open of the 16:05 London minute of t (after the WM/R 16:00 fix).
  Exit X2 = open of the 16:55 New York minute of t (before the rollover).

PASS 1 (28 pairs, each loaded once, Pool(2), del after use)
  For every day: mid = (bid close + ask close) / 2 at stamp A and at stamp B; live flag = vol > 0 in at least one
  of the 5 minutes ending at the stamp (minutes i-4..i); daily_table(m).atr20 of day t (NY-close label t =
  session 17:00 NY t-1 .. 17:00 NY t, which contains the 07:00 London entry; shifted, known before the day).
  A day is VALID only if all 28 pairs are live at both stamps.

STRENGTH (valid days only)
  s_c = (1/8) * sum over the 7 currencies j != c of ln(P_cj(B) / P_cj(A)), P_cj = price of c in units of j
  (pair XY: P_XY = mid, P_YX = 1/mid). The 8 s_c sum to 0 (checked).
  S = argmax s_c (strongest), W = argmin s_c (weakest), D = s_S - s_W.
  Filter F: D >= 1.5 * median(D over the previous 60 VALID days) (prior days only; undefined for the first 60
  valid days -> F variants skip those days).

TRADE (one per day)
  The W/S pair in its quoted form (28 pairs = all 8-currency combinations). Market order at the open of the 07:00
  London minute (buys fill on ask, sells on bid; gjstrat.patterns.simulate).
  REVERSAL (primary): buy W, sell S (pair WS -> BUY, pair SW -> SELL). MOMENTUM (control): the opposite.
  SL = 1.0 x ATR20 of the traded pair (daily_table atr20 of day t), no TP, time exit at X1 or X2.
  A day whose traded pair has no atr20 (daily_table warm-up, early 2010) is skipped and counted.

VARIANTS (8 tests)
  V1 reversal, no filter, X1      V5 momentum, no filter, X1
  V2 reversal, F,         X1      V6 momentum, F,         X1
  V3 reversal, no filter, X2      V7 momentum, no filter, X2
  V4 reversal, F,         X2      V8 momentum, F,         X2
  V1-V4 are the reversal candidates; V5-V8 are the competing hypothesis, reported and judged with the same bar.

COSTS (pass 2: each traded pair loaded once, Pool(2))
  All variants' trades on that pair are simulated; per (variant, pair):
  R = gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m, 10_000, commission=7,
      swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'], then reassembled by date.
  (Both exits are before the 17:00 NY rollover, so swap is always 0.)

STATISTICS / REPORT
  Pooled per variant (each day = one trade): trades, trades/month (over 2010-01..2026-10), win %, avg win / avg
  loss (losses = R <= 0), avg R and t over trades, month-clustered t (sum of R per calendar month of the trade
  day, 0 for months without trades, months from the variant's first trade), per period design 2010-17 / check
  2018-23 / holdout 2024-26 and last 3 years (2023-10-08 .. 2026-10-07).
  Per-pair trade counts and avg R; number of pairs with avg R > 0 among pairs with >= 20 trades.
  Home-hours subset: days with W or S in {JPY, AUD, NZD}.
  Avg R by D tercile: (a) D_rel = D / median(prev 60 valid D), cutoffs = terciles of D_rel over DESIGN days, applied
  to every period; (b) raw D, full-sample terciles (descriptive). Reversal should grow with D.
  Costs: entry spread / R, exit-bar spread / R, commission + slippage in R, gross (pre-commission) vs net avg R.
  Overlap with the current prop basket (run_m3_addon.build_legs(): vol-box, vol-gotobi, fade, M-3 USDJPY,
  M-3 other five pairs): share of trade days on which a basket trade is open on the same UTC date as our entry,
  and share of our trades whose holding interval overlaps a basket trade.
  Cross-check: correlation of s_c (x1e4) with the summed 30-min currency strengths of data/flow_series_v2.npz over
  17:00 NY (A) .. 07:00 London (B), Tue-Fri valid days (Monday's weekend gap is not in the flow series).

SURVIVAL (charter bar, per test, on the pooled trade series)
  design t (over trades) >= 2 AND avg R > 0 in check AND avg R > 0 in holdout. The month-clustered design t is
  shown next to it; if it is < 2 for a survivor that is flagged.
  8 tests -> about 8 x 0.006 = 0.05 survivors expected by luck.
  If any test survives: prop sim (Alpha Swing rules run_m3_addon.ALPHA, gjstrat.prop.prop_table) of the basket
  (vol-box 0.25%, vol-gotobi 3%, fade 0.5%, M-3 USDJPY 3%, M-3 others 0) alone, + survivor at 0.5% and 1% risk per
  trade, and the survivor alone at 1%; challenges started 2011-2025 and 2018-2025. All pairs share t0 2009-12-31
  with USDJPY, so trades join the USDJPY grid without shifting.

    python run_alpha_fx_session_rev.py            # pass 1, pass 2, report (+ basket overlap, prop sim if survivor)
    python run_alpha_fx_session_rev.py --report   # report from the caches
"""
import os
import sys
import time
from collections import namedtuple
from multiprocessing import Pool
from types import SimpleNamespace

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import MAJORS, MINORS, load_market
from gjstrat.patterns import LDN, NY, Signal, daily_table, local_idx, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/fx_session_rev"
DATA = "data/{}_2010-01-01_2026-10-07.npz"
PAIRS = MAJORS + MINORS
CCYS = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
HOME = {"JPY", "AUD", "NZD"}
T0 = pd.Timestamp("2009-12-31")
DAY0, DAY1 = "2010-01-04", "2026-10-07"
SPAN = (pd.Timestamp("2010-01-01"), pd.Timestamp("2026-10-07"))
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
F_MULT, F_LOOK, SL_ATR = 1.5, 60, 1.0
VARIANTS = {"V1": ("rev", False, "X1"), "V2": ("rev", True, "X1"), "V3": ("rev", False, "X2"),
            "V4": ("rev", True, "X2"), "V5": ("mom", False, "X1"), "V6": ("mom", True, "X1"),
            "V7": ("mom", False, "X2"), "V8": ("mom", True, "X2")}
NAMES = {v: f"{v} {'reversal' if a == 'rev' else 'momentum'}, {'F' if f else 'no filter'}, "
            f"{'X1 16:05 LDN' if x == 'X1' else 'X2 16:55 NY'}" for v, (a, f, x) in VARIANTS.items()}
CANDIDATES = ["V1", "V2", "V3", "V4"]
LEG_NAMES = ["vol-box", "vol-gotobi", "fade", "M-3 USDJPY", "M-3 other five"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def path_of(sym):
    return DATA.format(sym.lower())


# --------------------------------------------------------------------------- stamps
def stamps() -> pd.DataFrame:
    T = pd.bdate_range(DAY0, DAY1)
    prev = T - pd.offsets.BDay(1)

    def idx(days, hh, mm, tz):
        u = (days + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(tz).tz_convert("UTC").tz_localize(None)
        return np.asarray((u - T0) // pd.Timedelta(minutes=1), dtype=np.int64)

    st = pd.DataFrame({"prev": prev, "iA": idx(prev, 16, 54, NY), "iB": idx(T, 6, 59, LDN),
                       "iE": idx(T, 7, 0, LDN), "iX1": idx(T, 16, 5, LDN), "iX2": idx(T, 16, 55, NY)}, index=T)
    # literal cross-check against gjstrat.patterns.local_idx for every day
    shim = SimpleNamespace(idx=lambda ts: int((ts - T0) // pd.Timedelta(minutes=1)))
    for day, r in st.iterrows():
        assert local_idx(shim, r.prev, 16, 54, NY) == r.iA
        assert local_idx(shim, day, 6, 59, LDN) == r.iB
        assert local_idx(shim, day, 7, 0, LDN) == r.iE
        assert local_idx(shim, day, 16, 5, LDN) == r.iX1
        assert local_idx(shim, day, 16, 55, NY) == r.iX2
    assert (st.iE == st.iB + 1).all()
    return st


# --------------------------------------------------------------------------- pass 1
def pass1_pair(args):
    sym, days, iA, iB = args
    t = time.time()
    m = load_market(path_of(sym))
    assert m.t0 == T0, (sym, m.t0)
    out = {}
    for k, i in (("A", iA), ("B", iB)):
        ok = (i >= 4) & (i < m.n)
        ic = np.clip(i, 4, m.n - 1)
        mid = (m.bc[ic] + m.ac[ic]) / 2
        live = np.zeros(len(i), dtype=bool)
        for j in range(5):
            live |= m.vol[ic - j] > 0
        live &= ok
        mid[~ok] = np.nan
        out[f"mid{k}"], out[f"live{k}"] = mid, live
    d = daily_table(m)
    out["atr"] = d["atr20"].reindex(pd.DatetimeIndex(days)).to_numpy()
    n = m.n
    del m, d
    return sym, out, n, time.time() - t


def run_pass1(st):
    cache = f"{OUT}/pass1.pkl"
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    days = st.index.to_numpy()
    jobs = [(s, days, st.iA.to_numpy(), st.iB.to_numpy()) for s in PAIRS]
    res = {}
    with Pool(2) as pool:
        for sym, out, n, sec in pool.imap_unordered(pass1_pair, jobs):
            res[sym] = out
            log(f"pass1 {sym}: n={n} liveA={out['liveA'].mean():.3f} liveB={out['liveB'].mean():.3f} "
                f"atr={np.isfinite(out['atr']).mean():.3f} {sec:.1f}s")
    cols = {}
    for s in PAIRS:
        for k in ("midA", "midB", "liveA", "liveB", "atr"):
            cols[(k, s)] = res[s][k]
    P = pd.DataFrame(cols, index=st.index)
    P.to_pickle(cache)
    return P


def build_days(st, P) -> pd.DataFrame:
    """Per-day table: validity, strengths, S, W, D, filter, traded pair and side."""
    liveA, liveB = P["liveA"].astype(bool), P["liveB"].astype(bool)
    valid = (liveA.all(axis=1) & liveB.all(axis=1)).to_numpy()
    lr = np.log(P["midB"] / P["midA"])
    s = pd.DataFrame(0.0, index=P.index, columns=CCYS)
    for c in CCYS:
        for p in PAIRS:
            if p[:3] == c:
                s[c] += lr[p]
            elif p[3:] == c:
                s[c] -= lr[p]
    s /= 8
    days = pd.DataFrame(index=P.index)
    days["valid"] = valid
    for c in CCYS:
        days[f"s_{c}"] = s[c].where(valid)
    days["ssum"] = s.sum(axis=1).where(valid)
    sv = s[valid]
    days["S"] = pd.Series(sv.idxmax(axis=1), index=sv.index).reindex(P.index)
    days["W"] = pd.Series(sv.idxmin(axis=1), index=sv.index).reindex(P.index)
    days["D"] = (sv.max(axis=1) - sv.min(axis=1)).reindex(P.index)
    Dv = days.loc[valid, "D"]
    med = Dv.rolling(F_LOOK, min_periods=F_LOOK).median().shift(1)
    days["med60"] = med.reindex(P.index)
    days["D_rel"] = days.D / days.med60
    days["F"] = np.where(days.med60.notna(), (days.D >= F_MULT * days.med60).astype(float), np.nan)
    sym, side = [], []
    for w, s_ in zip(days.W, days.S):
        if not isinstance(w, str):
            sym.append(None); side.append(None)
        elif w + s_ in PAIRS:
            sym.append(w + s_); side.append("BUY")
        else:
            assert s_ + w in PAIRS
            sym.append(s_ + w); side.append("SELL")
    days["sym"], days["rev_side"] = sym, side
    days["atr"] = [P[("atr", p)].iat[k] if p else np.nan for k, p in enumerate(sym)]
    for c in ("iA", "iB", "iE", "iX1", "iX2"):
        days[c] = st[c]
    days["home"] = [isinstance(w, str) and (w in HOME or s_ in HOME) for w, s_ in zip(days.W, days.S)]
    return days


# --------------------------------------------------------------------------- pass 2
def pass2_pair(args):
    sym, plan = args
    t = time.time()
    m = load_market(path_of(sym))
    assert m.t0 == T0
    sw = SwapModel.from_fred("rates", 1.0)
    sims = {}
    for day, rev_side, iE, iX1, iX2, atr in plan:
        for a in ("rev", "mom"):
            side = rev_side if a == "rev" else ("SELL" if rev_side == "BUY" else "BUY")
            for x, ix in (("X1", iX1), ("X2", iX2)):
                tr = simulate(m, Signal(pd.Timestamp(day), side, int(iE), "market", None, int(iE) + 1,
                                        SL_ATR * atr, None, int(ix), f"{a}-{x}"))
                sims[(pd.Timestamp(day), a, x)] = tr
    fmap = {pd.Timestamp(r[0]): r for r in plan}
    rows = []
    for v, (a, filt, x) in VARIANTS.items():
        tr = [sims[(day, a, x)] for day in fmap if sims[(day, a, x)] is not None]
        if filt:
            tr = [t_ for t_ in tr if FLAGS[sym][t_.day] == 1.0]
        if not tr:
            continue
        tr = sorted(tr, key=lambda t_: (t_.exit_i, t_.entry_i))
        acc = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
        Rmap = dict(zip(acc.entry_i.to_numpy(), acc.R.to_numpy()))
        for t_ in tr:
            rows.append({"variant": v, "day": t_.day, "sym": sym, "side": t_.side, "entry_i": t_.entry_i,
                         "exit_i": t_.exit_i, "entry": t_.entry, "exit": t_.exit, "reason": t_.reason,
                         "risk": t_.risk, "r_gross": t_.r, "R": Rmap[t_.entry_i],
                         "spread_in_R": t_.spread / t_.risk,
                         "spread_out_R": max(m.ao[t_.exit_i] - m.bo[t_.exit_i], 0.0) / t_.risk})
    nmiss = sum(1 for k, v_ in sims.items() if v_ is None)
    del m
    return sym, pd.DataFrame(rows), nmiss, time.time() - t


FLAGS = {}


def _init(flags):
    global FLAGS
    FLAGS = flags


def run_pass2(days):
    cache = f"{OUT}/trades.csv"
    if os.path.exists(cache):
        T = pd.read_csv(cache, parse_dates=["day"])
        return T
    tradable = days[days.valid & days.sym.notna() & days.atr.notna()]
    jobs, flags = [], {}
    for sym, g in tradable.groupby("sym"):
        plan = [(day, r.rev_side, r.iE, r.iX1, r.iX2, r.atr) for day, r in g.iterrows()]
        flags[sym] = {pd.Timestamp(day): r.F for day, r in g.iterrows()}
        jobs.append((sym, plan))
    jobs.sort(key=lambda j: -len(j[1]))
    out = []
    with Pool(2, initializer=_init, initargs=(flags,)) as pool:
        for sym, df, nmiss, sec in pool.imap_unordered(pass2_pair, jobs):
            out.append(df)
            log(f"pass2 {sym}: days={len(flags[sym])} trades={len(df)} unsimulated={nmiss} {sec:.1f}s")
    T = pd.concat(out, ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T = T.sort_values(["variant", "day"]).reset_index(drop=True)
    T.to_csv(cache, index=False)
    return T


# --------------------------------------------------------------------------- statistics
def months_between(a, b):
    return len(pd.period_range(a, b, freq="M"))


def month_t(g, a, b):
    if not len(g):
        return np.nan
    months = pd.period_range(a, b, freq="M")
    s = g.groupby(pd.DatetimeIndex(g.day).to_period("M")).R.sum().reindex(months, fill_value=0.0)
    return tstat(s.to_numpy())


def periods():
    p = {k: (pd.Timestamp(a), pd.Timestamp(b)) for k, (a, b) in PER.items()}
    p["last3y"] = L3
    return p


def test_row(g: pd.DataFrame) -> dict:
    r = g.R.to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    first = g.day.min() if len(g) else SPAN[0]
    row = {"trades": len(r), "trades/month": len(r) / months_between(SPAN[0], SPAN[1]),
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r),
           "month t": month_t(g, max(first, SPAN[0]), SPAN[1]),
           "SL %": (g.reason == "SL").mean() * 100 if len(g) else np.nan}
    for p, (a, b) in periods().items():
        x = g[(g.day >= a) & (g.day <= b)]
        row.update({f"{p} n": len(x), f"{p} avg R": x.R.mean() if len(x) else np.nan,
                    f"{p} t": tstat(x.R.to_numpy()),
                    f"{p} month t": month_t(x, max(a, first), min(b, SPAN[1])) if len(x) else np.nan})
    row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    return row


def flow_crosscheck(days):
    z = np.load("data/flow_series_v2.npz")
    v = days[days.valid & (days.index.dayofweek >= 1)]
    k0 = ((v.iA.to_numpy() + 6) // 30).astype(int)           # 17:00 NY half-hour
    assert ((v.iA.to_numpy() + 6) % 30 == 0).all()
    k1 = (v.iE.to_numpy() // 30).astype(int)                  # 07:00 London half-hour (exclusive)
    assert (v.iE.to_numpy() % 30 == 0).all()
    rows = []
    for c in CCYS:
        f = z[c]
        cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(f))])
        fs = cs[k1] - cs[k0]
        mine = v[f"s_{c}"].to_numpy() * 1e4
        rows.append({"ccy": c, "days": len(v), "corr": np.corrcoef(mine, fs)[0, 1],
                     "mean |s| (bp)": np.abs(mine).mean(), "mean |flow| (bp)": np.abs(fs).mean()})
    return pd.DataFrame(rows).set_index("ccy")


# --------------------------------------------------------------------------- basket overlap / prop
Tr = namedtuple("Tr", "day entry_i exit_i")


def basket_overlap(T, days):
    from run_m3_addon import build_legs
    m, legs = build_legs()
    assert m.t0 == T0
    out = []
    for v in VARIANTS:
        g = T[T.variant == v]
        ei, xi = g.entry_i.to_numpy(), g.exit_i.to_numpy()
        d0 = ((pd.DatetimeIndex(g.day) - T0) // pd.Timedelta(minutes=1)).to_numpy()   # 00:00 UTC of day t
        row = {"variant": v, "trades": len(g)}
        any_day, any_ov = np.zeros(len(g), bool), np.zeros(len(g), bool)
        for name, (tr, _) in zip(LEG_NAMES, legs):
            be = np.array([t.entry_i for t in tr]); bx = np.array([t.exit_i for t in tr])
            sd, ov = np.zeros(len(g), bool), np.zeros(len(g), bool)
            for k0 in range(0, len(g), 500):
                sl = slice(k0, k0 + 500)
                sd[sl] = ((be[None, :] < d0[sl, None] + 1440) & (bx[None, :] >= d0[sl, None])).any(1)
                ov[sl] = ((be[None, :] < xi[sl, None]) & (bx[None, :] > ei[sl, None])).any(1)
            row[f"{name} same UTC day %"] = sd.mean() * 100
            row[f"{name} overlap %"] = ov.mean() * 100
            any_day |= sd; any_ov |= ov
        row["any leg same UTC day %"] = any_day.mean() * 100
        row["any leg overlap %"] = any_ov.mean() * 100
        out.append(row)
    return m, legs, pd.DataFrame(out).set_index("variant")


def prop(m, legs, T, survivors):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, since
    names = []
    for v in survivors:
        g = T[(T.variant == v) & (T.exit_i < m.n)].sort_values(["exit_i", "entry_i"])
        legs = legs + [([Tr(pd.Timestamp(d), int(a), int(b)) for d, a, b in zip(g.day, g.entry_i, g.exit_i)],
                        g.R.to_numpy())]
        names.append(v)
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(names)}
    for j, nm in enumerate(names):
        one = lambda x: tuple(x if i == j else 0 for i in range(len(names)))
        mixes[f"basket + {nm} 0.5%"] = base + one(0.5)
        mixes[f"basket + {nm} 1%"] = base + one(1.0)
        mixes[f"{nm} alone 1%"] = (0,) * len(base) + one(1.0)
    tabs = []
    for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
        t = prop_table(m, lg, mixes, **ALPHA)
        t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
        t.insert(0, "window", w)
        tabs.append(t)
        log("prop", w)
    P = pd.concat(tabs)
    P.index.name = "mix"
    P.to_csv(f"{OUT}/prop.csv")
    return P


# --------------------------------------------------------------------------- report
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    st = stamps()
    log("stamps", len(st))
    P = run_pass1(st)
    days = build_days(st, P)
    days.drop(columns=["iA", "iB", "iE", "iX1", "iX2"]).to_csv(f"{OUT}/days.csv")
    nv = int(days.valid.sum())
    log(f"valid days {nv}/{len(days)}; F days {int((days.F == 1).sum())}; max |sum s| {days.ssum.abs().max():.2e}")
    T = run_pass2(days)
    log("trades", len(T))
    D = days[["D", "D_rel", "W", "S", "home", "F"]]
    T = T.join(D, on="day")

    # ---- per variant tests
    rows = {v: test_row(T[T.variant == v]) for v in VARIANTS}
    tests = pd.DataFrame(rows).T
    tests.index.name = "variant"
    tests.insert(0, "name", [NAMES[v] for v in tests.index])
    tests.to_csv(f"{OUT}/tests.csv")
    survivors = [v for v in VARIANTS if tests.loc[v, "survives"]]

    # ---- home-hours subset
    home = pd.DataFrame({v: test_row(T[(T.variant == v) & T.home]) for v in VARIANTS}).T
    home.index.name = "variant"
    home.to_csv(f"{OUT}/home_subset.csv")

    # ---- per pair
    pp = T.groupby(["variant", "sym"]).R.agg(["size", "mean"]).rename(columns={"size": "n", "mean": "avg R"})
    pp.to_csv(f"{OUT}/per_pair.csv")
    ppos = {}
    for v in VARIANTS:
        x = pp.loc[v]
        x = x[x.n >= 20]
        ppos[v] = f"{int((x['avg R'] > 0).sum())}/{len(x)}"
    pair_n = pp["n"].unstack(0)
    pair_r = pp["avg R"].unstack(0)
    pair_tab = pd.concat({"n": pair_n[["V1", "V2"]], "avg R": pair_r}, axis=1)
    pair_tab.columns = [f"{a} {b}" for a, b in pair_tab.columns]
    pair_tab = pair_tab.sort_values("n V1", ascending=False)
    pair_tab.index.name = "pair"

    # ---- D terciles
    dv = days[days.valid & days.D_rel.notna()]
    cut_rel = dv.loc[(dv.index >= pd.Timestamp(PER["design"][0])) & (dv.index <= pd.Timestamp(PER["design"][1])),
                     "D_rel"].quantile([1 / 3, 2 / 3]).to_numpy()
    cut_raw = days.loc[days.valid, "D"].quantile([1 / 3, 2 / 3]).to_numpy()
    T["terc_rel"] = np.where(T.D_rel.isna(), np.nan, 1 + (T.D_rel > cut_rel[0]) + (T.D_rel > cut_rel[1]))
    T["terc_raw"] = 1 + (T.D > cut_raw[0]).astype(int) + (T.D > cut_raw[1]).astype(int)
    trows = []
    for v in ("V1", "V3", "V5", "V7"):
        for kind in ("terc_rel", "terc_raw"):
            for q in (1, 2, 3):
                g = T[(T.variant == v) & (T[kind] == q)]
                row = {"variant": v, "tercile by": "D_rel (design cutoffs)" if kind == "terc_rel" else "raw D (full sample)",
                       "tercile": q, "n": len(g), "avg R": g.R.mean(), "t": tstat(g.R.to_numpy())}
                for p, (a, b) in periods().items():
                    x = g[(g.day >= a) & (g.day <= b)]
                    row[f"{p} avg R"] = x.R.mean() if len(x) else np.nan
                    row[f"{p} t"] = tstat(x.R.to_numpy())
                trows.append(row)
    terc = pd.DataFrame(trows)
    terc.to_csv(f"{OUT}/terciles.csv", index=False)
    f_share = float((days.loc[days.valid, "F"] == 1).sum() / days.loc[days.valid, "F"].notna().sum())

    # ---- costs
    crows = []
    for v in VARIANTS:
        g = T[T.variant == v]
        rt = (g.spread_in_R + g.spread_out_R) / 2                 # round-trip spread paid = half in + half out
        mid = g.r_gross + rt
        crows.append({"variant": v, "entry spread / R": g.spread_in_R.mean(),
                      "exit-bar spread / R": g.spread_out_R.mean(), "round-trip spread (R)": rt.mean(),
                      "commission + slippage (R)": (g.r_gross - g.R).mean(),
                      "total cost (R)": (rt + g.r_gross - g.R).mean(),
                      "mid-to-mid avg R (approx)": mid.mean(), "mid-to-mid t": tstat(mid.to_numpy()),
                      "gross avg R (bid/ask, before comm.)": g.r_gross.mean(), "net avg R": g.R.mean(),
                      "avg hold h": ((g.exit_i - g.entry_i) / 60).mean()})
    costs = pd.DataFrame(crows).set_index("variant")
    costs.to_csv(f"{OUT}/costs.csv")

    # ---- by year
    T["year"] = T.day.dt.year
    by_year = T.groupby(["year", "variant"]).R.mean().unstack()
    by_year.to_csv(f"{OUT}/by_year.csv")

    # ---- validity / pair frequency
    vd = days[days.valid]
    ccy_freq = pd.DataFrame({"weakest W %": vd.W.value_counts(normalize=True) * 100,
                             "strongest S %": vd.S.value_counts(normalize=True) * 100}).reindex(CCYS)
    ccy_freq.index.name = "ccy"
    invalid_by_dow = (~days.valid).groupby(days.index.dayofweek).mean() * 100
    xc = flow_crosscheck(days)
    xc.to_csv(f"{OUT}/flow_crosscheck.csv")

    # ---- basket overlap + prop
    mb, legs, ov = None, None, None
    if "--no-basket" not in sys.argv:
        mb, legs, ov = basket_overlap(T, days)
        ov.to_csv(f"{OUT}/basket_overlap.csv")
        log("basket overlap done")
    Pp = prop(mb, legs, T, survivors) if survivors and legs is not None else None

    # ---- report
    def ptab(df):
        cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t",
                "design n", "design avg R", "design t", "design month t", "check n", "check avg R", "check t",
                "holdout n", "holdout avg R", "holdout t", "last3y n", "last3y avg R", "last3y t", "survives"]
        x = df[cols].copy()
        for c in cols:
            if c != "survives":
                x[c] = x[c].astype(float)
        return fmt_table(x, ".3f")

    n_tests = len(VARIANTS)
    surv_txt = ", ".join(f"{v} (month t design {tests.loc[v, 'design month t']:.2f})" for v in survivors) or "none"
    txt = [
        "# Alpha hunt: fx_session_rev (conditional cross-session currency-strength reversal)\n",
        "Spec, rules and the survival bar are in the docstring of `run_alpha_fx_session_rev.py` (fixed before running).",
        "Every weekday t: currency strength s_c from the 16:54 NY close of the previous weekday (A) to the 06:59 London",
        "close of t (B), all 28 pairs; trade the weakest/strongest pair at the 07:00 London open, SL 1 x ATR20, no TP,",
        "exit 16:05 London (X1) or 16:55 NY (X2). Reversal = buy the weakest, sell the strongest; momentum = opposite.",
        "Filter F = D >= 1.5 x median D of the previous 60 valid days. Costs: real bid/ask, $7/lot, 0.2 pip slippage",
        "per stop fill, swap (always 0: both exits are before the rollover).\n",
        f"Valid days (all 28 pairs live at both stamps): {nv} of {len(days)} weekdays. Invalid share by weekday "
        f"(Mon..Fri, %): {', '.join(f'{x:.1f}' for x in invalid_by_dow.to_numpy())}. F days: {int((days.F == 1).sum())} "
        f"({f_share * 100:.1f}% of valid days with a defined filter). Max |sum of s_c| = {days.ssum.abs().max():.1e} "
        "(rounding).\n",
        f"**Tests judged: {n_tests} (4 reversal candidates V1-V4, 4 momentum controls V5-V8, same bar). "
        f"Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): {surv_txt}. "
        f"Expected by luck: {n_tests} x 0.006 = {n_tests * 0.006:.2f}.**\n",
        "## All tests (pooled over pairs, one trade per day, net R)\n",
        "t = over trades; month t = month-clustered (sum of R per calendar month, zero-trade months count as 0). "
        "last3y = 2023-10-08..2026-10-07.\n",
        ptab(tests), "",
        "## Home-hours subset (W or S in JPY, AUD, NZD)\n",
        ptab(home), "",
        "## Avg R by D tercile (unfiltered variants)\n",
        f"D_rel = D / median(previous 60 valid D); tercile cutoffs from design days: {cut_rel[0]:.3f}, {cut_rel[1]:.3f} "
        f"(F needs D_rel >= 1.5). Raw D cutoffs (full sample): {cut_raw[0] * 1e4:.1f} bp, {cut_raw[1] * 1e4:.1f} bp.\n",
        fmt_table(terc.set_index("variant"), ".3f"), "",
        "## Costs (share of R)\n",
        "R unit = 1 x ATR20 of the traded pair. Round-trip spread = (spread at the entry bar + spread at the exit bar) / 2 "
        "(half of each is paid crossing from mid). Gross = on real bid/ask before commission/slippage; mid-to-mid = gross + "
        "round-trip spread (approximate: frictionless result). Total cost = round-trip spread + commission + slippage.\n",
        fmt_table(costs, ".3f"), "",
        "## Per pair (n = trades, avg R net)\n",
        "Pairs positive among pairs with >= 20 trades: " + ", ".join(f"{v} {ppos[v]}" for v in VARIANTS) + "\n",
        fmt_table(pair_tab, ".3f"), "",
        "## Avg R by year\n",
        fmt_table(by_year, ".3f"), "",
        "## Which currencies are the extremes (valid days)\n",
        fmt_table(ccy_freq, ".1f"), "",
        "## Cross-check of the strength computation vs data/flow_series_v2.npz (Tue-Fri)\n",
        fmt_table(xc, ".3f"), "",
    ]
    if ov is not None:
        txt += ["## Overlap with the current prop basket (run_m3_addon.build_legs)\n",
                "same UTC day = a basket trade is open at some time on the UTC date of our trade day; "
                "overlap = a basket trade is open during our holding period.\n",
                fmt_table(ov, ".1f"), ""]
    if Pp is not None:
        cols = ["window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
                "pass eventually %", "median months to pass", "months per funded account", "max DD %"]
        txt += ["## Prop sim (Alpha Swing, run_m3_addon.ALPHA)\n",
                "Basket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3%.\n", fmt_table(Pp[cols], ".1f"), ""]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt) + "\n")
    pd.set_option("display.width", 250)
    print(tests[["trades", "avg R", "t", "month t", "design avg R", "design t", "check avg R", "check t",
                 "holdout avg R", "holdout t", "last3y avg R", "survives"]].to_string())
    log(f"survivors: {survivors}; total {time.time() - t_start:.0f}s")
    log("DONE")


if __name__ == "__main__":
    main()
