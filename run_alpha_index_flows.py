"""Alpha hunt family `index_flows`: index calendar flows on fixed dates, long AND short swing trades.
(1) option expiry (dealer hedging / pinning) and (2) month-end pension / balanced-fund rebalancing
conditional on the month-to-date stock-bond gap. Everything below was fixed before running.

Theory. (1) As monthly index options near expiry, dealer delta hedges unwind (charm / vanna, pinning):
expiry week is calm and upward-biased, the following week is weaker (Stivers & Sun 2013 JBF; Ni,
Pearson & Poteshman 2005 JFE; Golez & Jackwerth 2012 JFE; practitioner opex seasonality). 0DTE growth
since 2022 may have diluted it, so 2011-2021 vs 2022+ is reported. (2) When stocks beat bonds month to
date, mandated rebalancing sells equities into month-end, and the reverse when stocks lag; the pressure
partly reverts after month-end (Harvey, Mazzoleni & Melone 2025 NBER; Etula, Rinne, Suominen &
Vaittinen 2020 RFS). The direction is conditional on an observable stock-bond gap G, unlike the
unconditional turn-of-month (E1b) tested before.

MARKETS: USATECHIDXUSD (Nasdaq 100 CFD, minute bid/ask, primary, data from 2011-09-18) and USA500IDXUSD
(S&P 500 CFD, hourly bid candles 2012-2026, replication). Loaded one at a time, single process.

TIMING
  * NYSE trading days = weekdays minus holidays.NYSE (python-holidays 0.57; it includes Sandy 2012 and
    2018-12-05 but not the 2025-01-09 closure - kept as the spec says).
  * Nasdaq "close" of day D = market at the first live minute (vol > 0) in [15:55, 16:00) New York
    (run_index_anomalies.live_at). Entries are market orders at that minute (buys on ask, sells on bid,
    gjstrat.patterns.simulate). Time exits at the open of the 15:55 NY minute of the exit day. Stops are
    checked minute by minute on bid/ask. ATR20 = gjstrat.patterns.daily_table(m).atr20 of the entry day
    (shifted, known before the day).
  * S&P "close" of day D = close of the 15:00-16:00 NY hourly bar (live bars only, v > 0). Buys fill at
    C + 0.5 pt, sells at C - 0.5 pt, time exits at C -/+ 0.5 pt (1.0 pt per round trip, as
    run_index_replication). Stops are checked on later hourly bars (bid low for longs, bid high for
    shorts) from the 16:00 bar of the entry day through the 15:00 bar of the exit day; a stop fills at the
    stop level, or at the bar open when price gapped through, with 0.25 pt slippage. Financing 3%/yr x
    calendar nights / 365 x entry price. ATR20 = mean(H - L) of the 20 previous days, days = live hourly
    bars grouped into 17:00-17:00 NY days (weekday labels).

A. OPTION EXPIRY. X = 3rd Friday of the month; if it is an NYSE holiday, the preceding trading day.
  O1 opex-week long: BUY at the close of the last trading day before the Monday of X's week; time exit at
     the close on X; SL 2.0 x ATR20.
  O2 post-opex short: SELL at the close on X; time exit at the close of the last trading day of the
     following week (Mon-Fri); SL 2.0 x ATR20.
  O3 = O1 in Mar / Jun / Sep / Dec only.     O4 = O2 in Mar / Jun / Sep / Dec only.

B. PENSION REBALANCING. Day s = 4th-last NYSE trading day of the month; pme = last trading day of the
   previous month; ME = last trading day of the month; TD3 = 3rd trading day of the next month.
   G = MTD equity return - MTD bond return.
     MTD equity return = S&P close(s) / close(pme) - 1 (hourly 16:00 closes); the Nasdaq closes when an
       S&P close is missing (all of 2011 and Jan 2012, plus S&P data gaps).
     MTD bond return = -8.5 x (DGS10_last - DGS10_pme) / 100; DGS10_last = latest FRED DGS10 value dated
       strictly before s (no look-ahead), DGS10_pme = latest value dated <= pme (data/extra/DGS10.csv,
       https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10).
  P1 (theta = 0): G > 0 -> SELL, G < 0 -> BUY at the close of s; time exit at the close of ME; SL 1.5 x ATR20.
  P2: P1 only when |G| > 0.02.
  P3: P1 in quarter-end months only (Mar, Jun, Sep, Dec).
  P4 conditional turn of month: BUY at the close of ME, time exit at the close of TD3, only when that
     month's G (from day s) > 0 (rebalancing selling ends, price rebounds); SL 1.0 x ATR20.

CONTROLS (reported, not candidates):
  C1 the same long hold as O1 in every non-expiry week: BUY at the close of the last trading day before
     the Monday, exit at the close of the last trading day of that Mon-Fri week, for every week that does
     not contain an X; SL 2.0 x ATR20.
  C2 unconditional long from the close of s to the close of ME; SL 1.5 x ATR20.
  C3 the P4 window (ME -> TD3, BUY) when G < 0; SL 1.0 x ATR20.
  C4 unconditional E1b turn of month recomputed: BUY ME close -> TD3 close every month; SL 1.0 x ATR20.

OBVIOUS-IMPOSSIBILITY FIXES (decided before running):
  * Look-ahead in G for the Nasdaq: the S&P 16:00 close of day s is not known at the Nasdaq entry
    (15:55-16:00). For Nasdaq trades the day-s equity level is the S&P price at 15:00 NY (open of the
    15:00-16:00 hourly bar); the pme level stays the 16:00 close. In fallback months the Nasdaq entry price
    itself (bid at the entry minute) is used. S&P trades use the 16:00 close exactly as specified (signal
    and fill at the same close, the run_index_replication convention). The report counts the months where
    the sign of G, or |G| > 2%, differs between the two definitions.
  * Nasdaq: a trade is skipped when its exit day has no tick between 09:30 and the 15:55 exit minute
    (data gap: there is no exit price). Half days keep the last traded price.
  * S&P hourly files contain flat zero-volume bars; only bars with v > 0 are used.
  * A trade needs ATR20 and both closes; otherwise the plan is skipped.

COSTS: Nasdaq via run_all_matrix.net_r (0.25 pt slippage, doubled on stop fills, 3%/yr financing per
rollover night), trades sorted by (exit_i, entry_i). S&P as above. R = net P&L / stop distance.

PERIODS / SURVIVAL (charter): run_edge_hunt.PER: design 2010-17 (indices from data start), check 2018-23,
holdout 2024-26, by entry day. A candidate survives if, on the Nasdaq, design t >= 2 AND avg R > 0 in
check AND in holdout. The S&P replicates if its avg R > 0 over the whole period. 8 candidate tests
(O1-O4, P1-P4 on the Nasdaq) -> ~0.05 survivors expected by luck (8 x 0.006).

REPORT (results/alpha_hunt/index_flows/REPORT.md + csv): per variant x market: trades, trades/month
(months with data), win %, avg win / avg loss, avg R and t per period, last 3 years (2023-10-08..2026-10-07).
O-variants split 2011-2021 vs 2022+ (0DTE). P-variants: avg R by G tercile (full-sample terciles of G,
descriptive only) and the hit rate of the predicted direction (sign of the close-to-close move of the
planned window = trade side, ignoring the stop). Worst single day in % at 0.5% risk per trade (marked to
market at each close, by NY trading day; and realised only).

IF A CANDIDATE SURVIVES: prop sim as run_index_prop.py: run_m3_addon.build_legs() basket (vol-box 0.25%
+ vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3%) + the new leg at 1% and 2% risk, run_m3_addon.ALPHA rules,
normal risk and boost x1.5, challenges started 2011-2025 and 2018-2025; accepted if months per funded
account is lower and pass eventually % not lower in both windows. Nasdaq trades join the USDJPY grid at
(UTC time - m_usdjpy.t0) minutes.

POST-HOC (added AFTER the first run had been seen; never candidates, never counted as survivors):
  H1  mirror of O2, because O2 was strongly negative: BUY at the close on X, time exit at the close of the
      last trading day of the following week, SL 2.0 x ATR20. Data-snooped by construction.
  H2  half-day G fill: in ~10 months G was missing because pme or s is a half day (day after Thanksgiving,
      Dec 31 in the CFD data) with no 16:00 / 15:55 price. Re-run P1-P4 and C3 (suffix "h") with the
      day's last live price at or before 16:00 NY used when the close is missing (S&P: last live hourly
      bar starting 09:00-15:00; Nasdaq: last live minute 09:30-15:59, bid close). Sensitivity only.

    python run_alpha_index_flows.py          # everything (prop sim only if a candidate survives)
    python run_alpha_index_flows.py prop     # prop sim from the saved trades
    python run_alpha_index_flows.py posthoc  # H1 / H2 (appends to REPORT.md)
"""
from __future__ import annotations

import glob
import lzma
import os
import sys
import time
from collections import namedtuple

import holidays
import numpy as np
import pandas as pd

from gjstrat.data import CANDLE_DTYPE, load_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from run_all_matrix import net_r
from run_backtest import fmt_table
from run_edge_hunt import PER, per_stats
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/index_flows"
NQ, SP = "USATECHIDXUSD", "USA500IDXUSD"
NQ_PATH = "data/usatechidxusd_2011-01-02_2026-10-07.npz"
NAMES = {NQ: "Nasdaq 100", SP: "S&P 500"}
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
DUR = 8.5
QUARTER = (3, 6, 9, 12)
VARIANTS = {  # name: (SL x ATR20, description, candidate?)
    "O1": (2.0, "opex-week long: Fri before -> X", True),
    "O2": (2.0, "post-opex short: X -> end of next week", True),
    "O3": (2.0, "O1 quarterly months", True),
    "O4": (2.0, "O2 quarterly months", True),
    "P1": (1.5, "rebalance: s -> ME, against sign(G)", True),
    "P2": (1.5, "P1 with abs(G) > 2%", True),
    "P3": (1.5, "P1 quarter-end months", True),
    "P4": (1.0, "TOM long ME -> TD3 when G > 0", True),
    "C1": (2.0, "control: long non-expiry weeks", False),
    "C2": (1.5, "control: long s -> ME unconditional", False),
    "C3": (1.0, "control: TOM long when G < 0", False),
    "C4": (1.0, "control: E1b TOM long unconditional", False),
}
CANDS = [v for v, x in VARIANTS.items() if x[2]]
POSTHOC = {"H1": (2.0, "post-hoc: long X -> end of next week (O2 mirror)", False),
           **{f"{v}h": (VARIANTS[v][0], VARIANTS[v][1] + " [half-day G fill]", False) for v in ("P1", "P2", "P3", "P4", "C3")}}
SLM = {v: x[0] for v, x in {**VARIANTS, **POSTHOC}.items()}


# --------------------------------------------------------------------------- calendar
def nyse(a: str, b: str) -> pd.DatetimeIndex:
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    hol = set(holidays.NYSE(years=range(a.year, b.year + 1)))
    return pd.DatetimeIndex([d for d in pd.bdate_range(a, b) if d.date() not in hol])


CAL = nyse("2011-01-01", "2026-12-31")
CAL_P = CAL.to_period("M")
MONTHS = pd.period_range("2011-09", "2026-10", freq="M")


def prev_td(day):
    """Last trading day strictly before `day`."""
    k = CAL.searchsorted(day, side="left") - 1
    return CAL[k] if k >= 0 else None


def last_td_le(day):
    k = CAL.searchsorted(day, side="right") - 1
    return CAL[k] if k >= 0 else None


def opex(per: pd.Period) -> pd.Timestamp:
    first = pd.Timestamp(year=per.year, month=per.month, day=1)
    x = first + pd.Timedelta(days=(4 - first.dayofweek) % 7 + 14)
    return x if x in CAL else last_td_le(x - pd.Timedelta(days=1))


def month_days(per):
    return CAL[CAL_P == per]


def month_frame() -> pd.DataFrame:
    rows = []
    for per in MONTHS:
        d, dp, dn = month_days(per), month_days(per - 1), month_days(per + 1)
        rows.append({"month": per, "s": d[-4], "ME": d[-1], "pme": dp[-1], "TD3": dn[2]})
    return pd.DataFrame(rows).set_index("month")


def plan(M: pd.DataFrame, G: pd.Series) -> list[tuple]:
    """(variant, entry day, exit day, side, G) for one market; G indexed by month (NaN = unknown)."""
    out = []
    xweeks = set()
    for per in MONTHS:
        X = opex(per)
        mon = X - pd.Timedelta(days=X.dayofweek)
        xweeks.add(mon)
        ent = prev_td(mon)
        nmon = mon + pd.Timedelta(days=7)
        ex2 = last_td_le(nmon + pd.Timedelta(days=4))
        q = per.month in QUARTER
        out.append(("O1", ent, X, "BUY", np.nan))
        if q:
            out.append(("O3", ent, X, "BUY", np.nan))
        if ex2 is not None and ex2 >= nmon:
            out.append(("O2", X, ex2, "SELL", np.nan))
            if q:
                out.append(("O4", X, ex2, "SELL", np.nan))
    for mon in pd.date_range("2011-09-19", "2026-10-05", freq="W-MON"):
        if mon in xweeks:
            continue
        wk = CAL[(CAL >= mon) & (CAL <= mon + pd.Timedelta(days=4))]
        if len(wk):
            out.append(("C1", prev_td(mon), wk[-1], "BUY", np.nan))
    for per, r in M.iterrows():
        g = G.get(per, np.nan)
        out.append(("C2", r.s, r.ME, "BUY", g))
        out.append(("C4", r.ME, r.TD3, "BUY", g))
        if not np.isfinite(g) or g == 0:
            continue
        side = "SELL" if g > 0 else "BUY"
        out.append(("P1", r.s, r.ME, side, g))
        if abs(g) > 0.02:
            out.append(("P2", r.s, r.ME, side, g))
        if per.month in QUARTER:
            out.append(("P3", r.s, r.ME, side, g))
        out.append(("P4" if g > 0 else "C3", r.ME, r.TD3, "BUY", g))
    return out


# --------------------------------------------------------------------------- data
def load_dgs10() -> pd.Series:
    df = pd.read_csv("data/extra/DGS10.csv", parse_dates=["observation_date"])
    return pd.Series(pd.to_numeric(df["DGS10"], errors="coerce").to_numpy(), index=df["observation_date"]).dropna()


def asof(s: pd.Series, day, strict: bool) -> float:
    k = s.index.searchsorted(day, side="left" if strict else "right") - 1
    return float(s.iloc[k]) if k >= 0 else np.nan


def spx_bars() -> pd.DataFrame:
    parts = []
    for f in sorted(glob.glob("data/hourly/USA500IDXUSD/*.bi5")):
        y, mth = map(int, os.path.basename(f)[:-4].split("_"))
        raw = open(f, "rb").read()
        if not raw:
            continue
        rec = np.frombuffer(lzma.decompress(raw), dtype=CANDLE_DTYPE)
        t0 = pd.Timestamp(year=y, month=mth, day=1)
        idx = t0 + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
        parts.append(pd.DataFrame({k: rec[k] / 1000.0 for k in "ohlc"} | {"v": rec["v"].astype(float)}, index=idx))
    b = pd.concat(parts).sort_index()
    b = b[~b.index.duplicated()]
    return b[b.v > 0]


def spx_closes(b: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    lab = (loc + pd.Timedelta(hours=7)).normalize()
    dd = pd.DataFrame({"high": b.h.to_numpy(), "low": b.l.to_numpy()}, index=lab).groupby(level=0).agg(
        high=("high", "max"), low=("low", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.high - dd.low).rolling(20).mean().shift(1)
    hr, ldate = loc.hour, loc.normalize()
    sel = hr == 15
    cs = pd.DataFrame({"C": b.c.to_numpy()[sel], "O15": b.o.to_numpy()[sel], "start": b.index[sel]}, index=ldate[sel])
    cs = cs[cs.index.isin(CAL)]
    cs = cs[~cs.index.duplicated()]
    cs["ts"] = cs.start + pd.Timedelta(hours=1)
    cs["atr20"] = atr.reindex(cs.index).to_numpy()
    return cs, atr


def nq_closes(m) -> pd.DataFrame:
    last = m.ts(m.n - 1)
    rows = []
    for day in CAL[(CAL >= m.t0.normalize()) & (CAL <= last)]:
        i = live_at(m, local_idx(m, day, 15, 55, NY))
        if i >= 0:
            rows.append((day, i, m.bo[i], m.ts(i)))
    return pd.DataFrame(rows, columns=["day", "i", "C", "ts"]).set_index("day")


def compute_g(M: pd.DataFrame, sp: pd.DataFrame, nq: pd.DataFrame, dgs: pd.Series) -> pd.DataFrame:
    G = M.copy()
    rows = []
    for per, r in M.iterrows():
        s, p = r.s, r.pme
        sp_ok = s in sp.index and p in sp.index
        nq_ok = s in nq.index and p in nq.index
        eq16 = sp.C[s] / sp.C[p] - 1 if sp_ok else np.nan
        eq15 = sp.O15[s] / sp.C[p] - 1 if sp_ok else np.nan
        eqn = nq.C[s] / nq.C[p] - 1 if nq_ok else np.nan
        yl, yp = asof(dgs, s, strict=True), asof(dgs, p, strict=False)
        bond = -DUR * (yl - yp) / 100
        rows.append({"eq_sp16": eq16, "eq_sp15": eq15, "eq_nq": eqn, "y_last": yl, "y_pme": yp, "bond": bond,
                     "src": "S&P" if sp_ok else ("Nasdaq" if nq_ok else "none"),
                     "G_sp": (eq16 if sp_ok else eqn) - bond, "G_nq": (eq15 if sp_ok else eqn) - bond})
    return pd.concat([G, pd.DataFrame(rows, index=M.index)], axis=1)


# --------------------------------------------------------------------------- execution
def run_nasdaq(plans, m, d, nqc) -> pd.DataFrame:
    atr = d["atr20"]
    by_v = {}
    meta = {}
    for v, a, b, side, g in plans:
        if a is None or b is None or b <= a:
            continue
        s = live_at(m, local_idx(m, a, 15, 55, NY))
        x = local_idx(m, b, 15, 55, NY)
        sl = SLM[v] * atr.get(a, np.nan)
        if s < 0 or x <= s + 1 or x >= m.n or not sl > 0:
            continue
        o = max(local_idx(m, b, 9, 30, NY), 0)
        if not (m.vol[o:x + 1] > 0).any():
            continue
        t = simulate(m, Signal(a, side, s, "market", None, s + 1, sl, None, x, v))
        if t is None:
            continue
        by_v.setdefault(v, []).append(t)
        meta[(v, a)] = (b, g)
    recs = []
    for v, tr in by_v.items():
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        R = net_r(m, NQ, tr, None)
        for t, r in zip(tr, R):
            b, g = meta[(v, t.day)]
            recs.append(dict(market=NQ, variant=v, day=t.day, exit_day=b, side=t.side, G=g, entry_ts=m.ts(t.entry_i),
                             exit_ts=m.ts(t.exit_i), entry=t.entry, exit=t.exit, reason=t.reason, risk=t.risk,
                             R_gross=t.r, R=r, c_in=nqc.C.get(t.day, np.nan), c_out=nqc.C.get(b, np.nan)))
    return pd.DataFrame(recs)


def run_spx(plans, b: pd.DataFrame, cs: pd.DataFrame) -> pd.DataFrame:
    starts = b.index.values
    O, Hh, Ll = b.o.to_numpy(), b.h.to_numpy(), b.l.to_numpy()
    recs = []
    for v, a, xd, side, g in plans:
        if a is None or xd is None or xd <= a or a not in cs.index or xd not in cs.index:
            continue
        sl = SLM[v] * cs.atr20[a]
        if not sl > 0:
            continue
        Ca, Cx = cs.C[a], cs.C[xd]
        i0 = np.searchsorted(starts, cs.start[a].to_datetime64(), side="right")
        i1 = np.searchsorted(starts, cs.start[xd].to_datetime64(), side="right")
        if side == "BUY":
            entry = Ca + 0.5
            stop = entry - sl
            hit = np.flatnonzero(Ll[i0:i1] <= stop)
        else:
            entry = Ca - 0.5
            stop = entry + sl
            hit = np.flatnonzero(Hh[i0:i1] >= stop)
        if len(hit):
            k = i0 + hit[0]
            px = (min(stop, O[k]) - 0.25) if side == "BUY" else (max(stop, O[k]) + 0.25)
            reason, xts = "SL", pd.Timestamp(starts[k]) + pd.Timedelta(minutes=30)
            xday = xts.tz_localize("UTC").tz_convert(NY).tz_localize(None).normalize()
        else:
            px = Cx - 0.5 if side == "BUY" else Cx + 0.5
            reason, xts, xday = "TIME", cs.ts[xd], xd
        gross = (px - entry) if side == "BUY" else (entry - px)
        fin = 0.03 * max((xday - a).days, 0) / 365 * entry
        recs.append(dict(market=SP, variant=v, day=a, exit_day=xd, side=side, G=g, entry_ts=cs.ts[a], exit_ts=xts,
                         entry=entry, exit=px, reason=reason, risk=sl, R_gross=gross / sl, R=(gross - fin) / sl,
                         c_in=Ca, c_out=Cx))
    return pd.DataFrame(recs)


# --------------------------------------------------------------------------- statistics
def ft(df: pd.DataFrame, fmt: str = ".3f") -> str:
    """fmt_table with a flattened MultiIndex and integer counts kept as integers (report formatting only)."""
    df = df.copy()
    if isinstance(df.index, pd.MultiIndex):
        name = " · ".join(str(x) for x in df.index.names)
        df.index = [" · ".join(str(x) for x in k) for k in df.index]
        df.index.name = name
    return fmt_table(df.astype(object), fmt)


def label(ts) -> pd.DatetimeIndex:
    ts = pd.DatetimeIndex(ts)
    return (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def basic(r: np.ndarray) -> dict:
    wins, losses = r[r > 0], r[r <= 0]
    return {"trades": len(r), "win %": (r > 0).mean() * 100 if len(r) else np.nan,
            "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
            "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}


def test_row(g: pd.DataFrame, months: int) -> dict:
    r = g.R.to_numpy() if len(g) else np.array([])
    day = pd.DatetimeIndex(g.day) if len(g) else pd.DatetimeIndex([])
    row = basic(r)
    row["trades/month"] = len(r) / months if months else np.nan
    row.update(per_stats(r, day))
    v = r[np.asarray((day >= L3[0]) & (day <= L3[1]))] if len(r) else r
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    row["SL %"] = (g.reason == "SL").mean() * 100 if len(g) else np.nan
    row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    return row


def mtm_days(tr: pd.DataFrame, closes: pd.DataFrame) -> dict:
    """R of every trade marked at each close strictly inside the trade, booked by NY trading-day label
    (17:00 roll); costs on the exit day."""
    cts, cpx = closes.ts.values, closes.C.to_numpy()
    out = {}
    for t in tr.itertuples():
        a = np.searchsorted(cts, pd.Timestamp(t.entry_ts).to_datetime64(), side="right")
        z = np.searchsorted(cts, pd.Timestamp(t.exit_ts).to_datetime64(), side="left")
        ts = [t.entry_ts] + list(pd.DatetimeIndex(cts[a:z])) + [t.exit_ts]
        px = np.r_[t.entry, cpx[a:z], t.exit]
        sgn = 1.0 if t.side == "BUY" else -1.0
        inc = sgn * np.diff(px) / t.risk
        inc[-1] += t.R - t.R_gross
        for lb, x in zip(label(ts[1:]), inc):
            out[lb] = out.get(lb, 0.0) + x
    return out


def realised_days(tr: pd.DataFrame) -> dict:
    if not len(tr):
        return {}
    return pd.Series(tr.R.to_numpy(), index=label(tr.exit_ts)).groupby(level=0).sum().to_dict()


# --------------------------------------------------------------------------- prop sim
def prop(survivors: list[str]):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    T = pd.read_pickle(f"{OUT}/trades.pkl")
    Tr = namedtuple("Tr", "day entry_i exit_i")
    m, legs = build_legs()
    for v in survivors:
        g = T[(T.market == NQ) & (T.variant == v)].copy()
        g["ei"] = ((pd.DatetimeIndex(g.entry_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g["xi"] = ((pd.DatetimeIndex(g.exit_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g = g[g.xi < m.n].sort_values(["xi", "ei"])
        legs.append(([Tr(pd.Timestamp(d), int(a), int(b)) for d, a, b in zip(g.day, g.ei, g.xi)], g.R.to_numpy()))
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(survivors)}
    for risk in (1, 2):
        for j, v in enumerate(survivors):
            mixes[f"basket + Nasdaq {v} {risk}%"] = base + tuple(risk if i == j else 0 for i in range(len(survivors)))
        if len(survivors) > 1:
            mixes[f"basket + {' + '.join(survivors)} {risk}% each"] = base + (risk,) * len(survivors)
    tabs = []
    for rule, scale in (("normal risk", None), ("boost x1.5", make_rule(boost=1.5))):
        for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
            t = prop_table(m, lg, mixes, **ALPHA, **({"scale": scale} if scale else {}))
            t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
            t.insert(0, "window", w)
            t.insert(0, "risk rule", rule)
            tabs.append(t)
            print("prop", rule, w, flush=True)
    P = pd.concat(tabs)
    acc = {}
    for rule in P["risk rule"].unique():
        for mix in list(mixes)[1:]:
            q = lambda w: P[(P["risk rule"] == rule) & (P.window == w)]
            acc[(rule, mix)] = all(q(w).loc[mix, "months per funded account"] < q(w).loc["basket", "months per funded account"]
                                   and q(w).loc[mix, "pass eventually %"] >= q(w).loc["basket", "pass eventually %"]
                                   for w in P.window.unique())
    P["accepted"] = [None if mix == "basket" else acc[(rule, mix)] for rule, mix in zip(P["risk rule"], P.index)]
    P.index.name = "mix"
    P.to_csv(f"{OUT}/prop.csv")
    cols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
            "pass eventually %", "median months to pass", "months per funded account", "max DD %", "accepted"]
    cols = [c for c in cols if c in P.columns]
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)\n\nBasket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + "
                "M-3 USDJPY 3% (run_m3_addon.build_legs); surviving Nasdaq leg(s) added at 1% and 2% risk (as run_index_prop.py).\n\n"
                + fmt_table(P[cols], ".1f") + "\n")
    print(P[cols].round(1).to_string())
    return P


# --------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    dgs = load_dgs10()
    M = month_frame()

    # S&P hourly closes first (small), then the Nasdaq minute market
    b = spx_bars()
    spc, _ = spx_closes(b)
    print(f"S&P: {len(b)} live hourly bars, {len(spc)} closes {spc.index.min().date()}..{spc.index.max().date()}", flush=True)

    m = load_market(NQ_PATH)
    d = daily_table(m)
    nqc = nq_closes(m)
    print(f"Nasdaq: {len(nqc)} closes {nqc.index.min().date()}..{nqc.index.max().date()} ({time.time() - t_start:.0f}s)", flush=True)
    G = compute_g(M, spc, nqc, dgs)
    G.to_csv(f"{OUT}/g_months.csv")
    TN = run_nasdaq(plan(M, G.G_nq), m, d, nqc)
    nq_months = nqc.index.to_period("M").nunique()
    del m, d
    print(f"Nasdaq trades: {len(TN)} ({time.time() - t_start:.0f}s)", flush=True)
    TS = run_spx(plan(M, G.G_sp), b, spc)
    sp_months = spc.index.to_period("M").nunique()
    del b
    print(f"S&P trades: {len(TS)} ({time.time() - t_start:.0f}s)", flush=True)
    T = pd.concat([TN, TS], ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T["exit_day"] = pd.to_datetime(T.exit_day)
    T["dir_hit"] = np.sign(T.c_out - T.c_in) == np.where(T.side == "BUY", 1, -1)
    T.to_pickle(f"{OUT}/trades.pkl")
    T.to_csv(f"{OUT}/trades.csv", index=False)
    months = {NQ: nq_months, SP: sp_months}
    closes = {NQ: nqc, SP: spc}

    # charter table
    rows = []
    for sym in (NQ, SP):
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            rows.append({"market": sym, "variant": v, **test_row(g, months[sym]),
                         "dir hit %": g.dir_hit.mean() * 100 if len(g) else np.nan})
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT}/tests.csv", index=False)
    nq = R[R.market == NQ].set_index("variant")
    sp = R[R.market == SP].set_index("variant")
    judge = nq.loc[CANDS, ["trades", "design avg R", "design t", "check avg R", "holdout avg R", "last3y avg R"]].copy()
    judge["Nasdaq charter bar"] = nq.loc[CANDS, "survives"]
    judge["S&P avg R"] = sp.loc[CANDS, "avg R"]
    judge["S&P t"] = sp.loc[CANDS, "t"]
    judge["S&P replicates"] = judge["S&P avg R"] > 0
    judge.index.name = "candidate"
    surv = [v for v in CANDS if bool(nq.loc[v, "survives"])]

    # option-expiry split 2011-2021 vs 2022+
    osplit = []
    for sym in (NQ, SP):
        for v in ("O1", "O2", "O3", "O4", "C1"):
            g = T[(T.market == sym) & (T.variant == v)]
            row = {"market": NAMES[sym], "variant": v}
            for nm, msk in (("2011-2021", g.day < pd.Timestamp("2022-01-01")), ("2022+", g.day >= pd.Timestamp("2022-01-01"))):
                x = g[msk].R.to_numpy()
                row.update({f"{nm} n": len(x), f"{nm} avg R": x.mean() if len(x) else np.nan, f"{nm} t": tstat(x),
                            f"{nm} win %": (x > 0).mean() * 100 if len(x) else np.nan})
            osplit.append(row)
    OS = pd.DataFrame(osplit).set_index(["market", "variant"])
    OS.to_csv(f"{OUT}/opex_split.csv")

    # G analysis: terciles (full-sample cutoffs, descriptive), direction hit rates
    gstats, gterc = [], []
    for sym, gcol in ((NQ, "G_nq"), (SP, "G_sp")):
        gs = G[gcol].dropna()
        cut = gs.quantile([1 / 3, 2 / 3]).to_numpy()
        terc = lambda x: np.where(x <= cut[0], "T1 low", np.where(x <= cut[1], "T2 mid", "T3 high"))
        sub = T[(T.market == sym) & T.variant.isin(["P1", "P2", "P3", "P4", "C2", "C3", "C4"]) & T.G.notna()].copy()
        sub["tercile"] = terc(sub.G.to_numpy())
        for (v, tc), g in sub.groupby(["variant", "tercile"]):
            r = g.R.to_numpy()
            gterc.append({"market": NAMES[sym], "variant": v, "tercile": tc, "G range": f"{g.G.min() * 100:+.1f}%..{g.G.max() * 100:+.1f}%",
                          "n": len(r), "avg R": r.mean(), "t": tstat(r), "win %": (r > 0).mean() * 100,
                          "dir hit %": g.dir_hit.mean() * 100})
        gstats.append({"market": NAMES[sym], "months with G": len(gs), "G>0 months": int((gs > 0).sum()),
                       "abs(G)>2% months": int((gs.abs() > 0.02).sum()), "G tercile cut 1": cut[0], "G tercile cut 2": cut[1],
                       "G mean": gs.mean(), "G sd": gs.std()})
    GT = pd.DataFrame(gterc).set_index(["market", "variant", "tercile"])
    GT.to_csv(f"{OUT}/g_terciles.csv")
    GS = pd.DataFrame(gstats).set_index("market")
    both = G[["G_nq", "G_sp"]].dropna()
    sign_diff = int((np.sign(both.G_nq) != np.sign(both.G_sp)).sum())
    thr_diff = int(((both.G_nq.abs() > 0.02) != (both.G_sp.abs() > 0.02)).sum())
    src_counts = G.src.value_counts().to_dict()

    # worst day at 0.5% risk
    wd = []
    mtm = {(s, v): mtm_days(T[(T.market == s) & (T.variant == v)], closes[s]) for s in (NQ, SP) for v in VARIANTS}
    rea = {(s, v): realised_days(T[(T.market == s) & (T.variant == v)]) for s in (NQ, SP) for v in VARIANTS}
    for s in (NQ, SP):
        for v in VARIANTS:
            pm, pr = pd.Series(mtm[(s, v)]) * 0.5, pd.Series(rea[(s, v)]) * 0.5
            if not len(pm):
                continue
            wd.append({"market": NAMES[s], "set": v, "worst day % (MTM)": pm.min(), "date": pm.idxmin().date(),
                       "worst day % (realised)": pr.min(), "date ": pr.idxmin().date(), "days < -0.5% (MTM)": int((pm < -0.5).sum()),
                       "worst trade R": T[(T.market == s) & (T.variant == v)].R.min()})
    for nm, vs in (("all 8 candidates at 0.5% each", CANDS), ("O1 + O2 + P1 + P4 at 0.5% each", ["O1", "O2", "P1", "P4"])):
        pm = pd.concat([pd.Series(mtm[(NQ, v)]) for v in vs], axis=1, sort=True).fillna(0).sum(axis=1) * 0.5
        pr = pd.concat([pd.Series(rea[(NQ, v)]) for v in vs], axis=1, sort=True).fillna(0).sum(axis=1) * 0.5
        wd.append({"market": "Nasdaq 100", "set": nm, "worst day % (MTM)": pm.min(), "date": pm.idxmin().date(),
                   "worst day % (realised)": pr.min(), "date ": pr.idxmin().date(), "days < -0.5% (MTM)": int((pm < -0.5).sum()),
                   "worst trade R": T[(T.market == NQ) & T.variant.isin(vs)].R.min()})
    WD = pd.DataFrame(wd).set_index(["market", "set"])
    WD.to_csv(f"{OUT}/worst_day.csv")

    # by year (Nasdaq and S&P avg R)
    YR = T.groupby(["market", "variant", pd.DatetimeIndex(T.day).year]).R.mean().unstack()
    YR.columns = [str(c) for c in YR.columns]
    YR.to_csv(f"{OUT}/by_year.csv")

    # ------------------------------------------------------------------ report
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R", "design t",
            "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n", "last3y avg R",
            "last3y t", "SL %", "dir hit %", "survives"]

    def tab(sym):
        x = R[R.market == sym].set_index("variant")[cols].copy()
        x.index = [f"{v} {VARIANTS[v][1]}" for v in x.index]
        x.index.name = "variant"
        return ft(x, ".3f")

    n_tests = len(CANDS)
    s_list = ", ".join(f"Nasdaq {v}" for v in surv) or "none"
    def yr_tab(sym):
        y = YR.loc[sym].reindex(list(VARIANTS))
        y.index.name = "variant"
        return ft(y, ".2f")
    txt = ["# Alpha hunt: index calendar flows - option expiry and month-end pension rebalancing (`index_flows`)\n",
           "Rules, variants and the survival bar are in the docstring of `run_alpha_index_flows.py` (fixed before running). "
           "Swing trades of 3-7 trading days on the close, long and short, stops 1-2 x ATR20 (Nasdaq checked minute by minute "
           "on bid/ask; S&P on hourly bars), all costs included. Periods: design 2011-17 (data start), check 2018-23, "
           "holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.\n",
           f"**Candidate tests: {n_tests} (O1-O4, P1-P4 on the Nasdaq; S&P = replication, C1-C4 = controls). "
           f"Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): {len(surv)} ({s_list}). "
           f"Expected by luck: {n_tests * 0.006:.2f}.**\n",
           "## Judging (candidates)\n", "Nasdaq gets the charter bar; the S&P replicates if its avg R > 0 over the whole period.\n",
           ft(judge, ".3f"), "\n",
           f"## Nasdaq 100 ({NQ})\n", f"Months with data: {months[NQ]}. trades/month = trades / months with data. "
           "dir hit % = share of trades whose planned close-to-close window moved in the trade's direction (ignores the stop).\n",
           tab(NQ), "\n",
           f"## S&P 500 ({SP}, hourly) - replication\n", f"Months with data: {months[SP]}.\n", tab(SP), "\n",
           "## Option expiry: 2011-2021 vs 2022+ (0DTE era)\n", ft(OS, ".3f"), "\n",
           "## Pension rebalancing: the stock-bond gap G\n",
           f"G source by month: {src_counts} (S&P hourly closes; Nasdaq fallback). Nasdaq trades use the look-ahead-free G "
           f"(S&P 15:00 price on day s); S&P trades use the 16:00 close. Months where the sign of G differs between the two: "
           f"{sign_diff} of {len(both)}; where abs(G) > 2% differs: {thr_diff}.\n",
           ft(GS, ".4f"), "\n",
           "### Avg R by G tercile (full-sample tercile cut-offs of each market's G; descriptive only)\n",
           "P1-P3 trade against sign(G) (low tercile = BUY, high = SELL); P4 / C3 / C4 / C2 are longs. dir hit % = the planned "
           "window moved the predicted way.\n", ft(GT, ".3f"), "\n",
           "## Worst single day at 0.5% risk per trade\n",
           "MTM = open trades marked at each close, booked by NY trading day (17:00 roll); realised = net R on the exit day.\n",
           ft(WD, ".2f"), "\n",
           "## Avg R per trade by year\n", "### Nasdaq 100\n", yr_tab(NQ), "\n", "### S&P 500\n", yr_tab(SP), "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(R[["market", "variant", "trades", "trades/month", "win %", "avg R", "t", "design avg R", "design t", "check avg R",
             "holdout avg R", "last3y avg R", "dir hit %", "survives"]].round(3).to_string())
    print(judge.round(3).to_string())
    print(OS.round(3).to_string())
    print(GS.round(4).to_string())
    print(GT.round(3).to_string())
    print(WD.round(2).to_string())
    print("G source", src_counts, "sign diff", sign_diff, "thr diff", thr_diff)
    print("survivors:", s_list, f"({time.time() - t_start:.0f}s)", flush=True)
    if surv:
        prop(surv)
    print("DONE", flush=True)


# --------------------------------------------------------------------------- post-hoc (after the first run)
def day_close_fallback_nq(m, day):
    a, b = local_idx(m, day, 9, 30, NY), local_idx(m, day, 16, 0, NY)
    if a < 0 or b >= m.n:
        return np.nan
    w = np.flatnonzero(m.vol[a:b] > 0)
    return float(m.bc[a + w[-1]]) if len(w) else np.nan


def posthoc():
    os.makedirs(OUT, exist_ok=True)
    dgs = load_dgs10()
    M = month_frame()
    G0 = pd.read_csv(f"{OUT}/g_months.csv")
    G0.index = pd.PeriodIndex(G0.month, freq="M")
    b = spx_bars()
    spc, _ = spx_closes(b)
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    live = pd.Series(b.c.to_numpy()[(loc.hour >= 9) & (loc.hour <= 15)], index=loc.normalize()[(loc.hour >= 9) & (loc.hour <= 15)])
    sp_last = live.groupby(level=0).last()                     # last live bar close of each NY date
    m = load_market(NQ_PATH)
    d = daily_table(m)
    nqc = nq_closes(m)
    need = sorted(set(M.s) | set(M.pme))
    sp16 = {x: spc.C[x] if x in spc.index else sp_last.get(x, np.nan) for x in need}
    sp15 = {x: spc.O15[x] if x in spc.index else sp_last.get(x, np.nan) for x in need}
    nqx = {x: nqc.C[x] if x in nqc.index else day_close_fallback_nq(m, x) for x in need}
    rows = []
    for per, r in M.iterrows():
        s_, p_ = r.s, r.pme
        sp_ok = np.isfinite(sp16[s_]) and np.isfinite(sp16[p_])
        nq_ok = np.isfinite(nqx[s_]) and np.isfinite(nqx[p_])
        bond = -DUR * (asof(dgs, s_, True) - asof(dgs, p_, False)) / 100
        eqs16 = sp16[s_] / sp16[p_] - 1 if sp_ok else np.nan
        eqs15 = sp15[s_] / sp16[p_] - 1 if sp_ok else np.nan
        eqn = nqx[s_] / nqx[p_] - 1 if nq_ok else np.nan
        rows.append({"month": per, "G_sp_alt": (eqs16 if sp_ok else eqn) - bond, "G_nq_alt": (eqs15 if sp_ok else eqn) - bond,
                     "src_alt": "S&P" if sp_ok else ("Nasdaq" if nq_ok else "none")})
    GA = pd.DataFrame(rows).set_index("month")
    GA = GA.join(G0[["G_sp", "G_nq", "src"]])
    # keep primary G wherever it existed; fill only the missing months
    GA["G_sp_h"] = GA.G_sp.where(GA.G_sp.notna(), GA.G_sp_alt)
    GA["G_nq_h"] = GA.G_nq.where(GA.G_nq.notna(), GA.G_nq_alt)
    filled = GA[GA.G_nq.isna() & GA.G_nq_h.notna()]
    GA.to_csv(f"{OUT}/posthoc_g_fill.csv")

    def ph_plans(G):
        out = [(f"{v}h", a, x, side, g) for v, a, x, side, g in plan(M, G) if v in ("P1", "P2", "P3", "P4", "C3")]
        out += [("H1", a, x, "BUY", g) for v, a, x, side, g in plan(M, G) if v == "O2"]
        return out
    TN = run_nasdaq(ph_plans(GA.G_nq_h), m, d, nqc)
    nq_months = nqc.index.to_period("M").nunique()
    del m, d
    TS = run_spx(ph_plans(GA.G_sp_h), b, spc)
    sp_months = spc.index.to_period("M").nunique()
    del b
    T = pd.concat([TN, TS], ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T["dir_hit"] = np.sign(T.c_out - T.c_in) == np.where(T.side == "BUY", 1, -1)
    T.to_csv(f"{OUT}/posthoc_trades.csv", index=False)
    T0 = pd.read_pickle(f"{OUT}/trades.pkl")
    rows = []
    for sym, mo in ((NQ, nq_months), (SP, sp_months)):
        for v in ["H1", "O2", "C1", "P1", "P1h", "P2", "P2h", "P3", "P3h", "P4", "P4h", "C3", "C3h"]:
            src = T if v in POSTHOC else T0
            g = src[(src.market == sym) & (src.variant == v)]
            row = {"market": NAMES[sym], "variant": v, **test_row(g, mo), "dir hit %": g.dir_hit.mean() * 100 if len(g) else np.nan}
            for nm, msk in (("2011-21", g.day < pd.Timestamp("2022-01-01")), ("2022+", g.day >= pd.Timestamp("2022-01-01"))):
                x = g[msk].R.to_numpy()
                row.update({f"{nm} avg R": x.mean() if len(x) else np.nan, f"{nm} t": tstat(x)})
            rows.append(row)
    PH = pd.DataFrame(rows)
    PH.to_csv(f"{OUT}/posthoc_tests.csv", index=False)
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R", "design t",
            "check avg R", "check t", "holdout avg R", "holdout t", "last3y avg R", "last3y t", "2011-21 avg R", "2022+ avg R",
            "dir hit %", "survives"]
    tabs = []
    for sym in (NQ, SP):
        x = PH[PH.market == NAMES[sym]].set_index("variant")[cols]
        x.index = [f"{v} {({**VARIANTS, **POSTHOC})[v][1]}" for v in x.index]
        x.index.name = "variant"
        tabs += [f"### {NAMES[sym]}\n", ft(x, ".3f"), ""]
    txt = ["\n## Post-hoc checks (added after seeing the first run; NOT candidates, not counted)\n",
           "H1 = long the week after expiry (mirror of O2, chosen because O2 lost) - data-snooped, so its 'survives' flag means "
           "nothing statistically. Rows with suffix h = P-variants re-run with G filled on half days (last live price that day); "
           f"months filled for the Nasdaq: {len(filled)} ({', '.join(str(p) for p in filled.index)}). Primary rows shown next to them.\n",
           *tabs]
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n".join(txt) + "\n")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(PH[["market", "variant", "trades", "avg R", "t", "design avg R", "design t", "check avg R", "holdout avg R",
              "last3y avg R", "2011-21 avg R", "2022+ avg R", "survives"]].round(3).to_string())
    print("filled months:", list(map(str, filled.index)))
    print("DONE", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "posthoc":
        posthoc()
    elif len(sys.argv) > 1 and sys.argv[1] == "prop":
        R = pd.read_csv(f"{OUT}/tests.csv")
        s = R[(R.market == NQ) & R.survives & R.variant.isin(CANDS)]
        prop(list(s.variant))
        print("DONE", flush=True)
    else:
        main()
