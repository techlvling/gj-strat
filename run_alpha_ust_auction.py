"""Alpha hunt, family `ust_auction`: the US Treasury auction concession cycle traded through USDJPY and gold.
Spec fixed BEFORE running; nothing below was chosen from the data.

Theory: primary dealers must absorb pre-announced Treasury coupon supply with limited risk capacity, so
Treasuries cheapen (yields rise) in the days before an auction and recover (yields fall) after it
(Lou, Yan & Zhang 2013 RFS; Fleming & Rosenberg 2008; Beetsma et al. 2016 for euro-area auctions). USDJPY moves
with US yields through the rate differential; gold moves against real/nominal yields (Erb & Harvey 2013).
Expected size is small (a few bp of yield, ~10-25 USDJPY pips), transmission indirect: prior low-medium.
The month-end 2y/5y/7y cluster is also a candidate explanation for the M-3 USD bid in the existing basket.

EVENTS: data/extra/ust_auctions.csv (fiscaldata auctions_query 2009-06..2026-10; URL in data/extra/SOURCES.csv).
  Keep security_type in {Note, Bond} with inflation_index_security == 'No' and floating_rate == 'No'
  (drops TIPS and FRNs).
  MID group: security_term 3-Year, 10-Year (incl. reopenings '9-Year xx-Month'), 30-Year (incl. '29-Year xx-Month').
  END group: 2-Year, 5-Year, 7-Year.  (20-year bonds and everything else belong to neither group.)
  A cluster = the auctions of one group within the same Mon-Fri calendar week; record its first and last
  auction day. Results are released at 13:00 ET.
  SPEC FIX (obvious impossibility): rows with offering_amt < $1bn are dropped. There are two, both $25 million
  (2019-06-21 '9-Year 11-Month', 2021-12-02 '19-Year 11-Month'); a $25m line is not a supply event that dealers
  must absorb, and the 2019 row would otherwise form a lone one-auction MID "cluster" on a Friday.
  Clusters split by the debt ceiling are kept as the rule gives them (Oct/Nov 2015: 5y+7y one week, the delayed
  2y the next week, so that 2y-only cluster's PRE window overlaps the previous cluster's windows).

WINDOWS (America/New_York, DST-aware via gjstrat.patterns.local_idx; NYSE trading days from holidays.NYSE,
  plus 2025-01-09, the national day of mourning that holidays 0.57 misses -- same fix as run_alpha_fomc_cycle):
  PRE : from the 15:55 NY minute five trading days before the cluster's first auction day, to the 12:55 NY minute
        on its last auction day.
  POST: from the 13:05 NY minute on the last auction day, to the 15:55 NY minute two trading days later.

TRADES (direction fixed by theory: yields rise into the auction and fall after; USDJPY rises with US yields;
  gold falls with yields):
  USDJPY BUY in PRE, SELL in POST.  XAUUSD SELL in PRE, BUY in POST.
  Market entry at the first live minute (vol > 0) at the window start: run_index_anomalies.live_at, i.e. the first
  traded minute within 5 minutes of the stated time; no live minute -> the trade is skipped (counted).
  Time exit at the window end (open of the 15:55 / 12:55 NY minute; gjstrat.patterns.simulate, bid/ask).
  SL 1.0 x ATR20 = daily_table atr20 (shifted, known before the day) of the NY-close session containing the
  entry minute (= the entry day). No TP. Windows whose start is before the data/ATR history (Jan 2010) or whose
  end is after the data end (2026-10-07) are skipped.

VARIANTS (8 tests): {USDJPY, XAUUSD} x {MID, END} x {PRE, POST}.
  USDJPY-MID-PRE (BUY), USDJPY-MID-POST (SELL), USDJPY-END-PRE (BUY), USDJPY-END-POST (SELL),
  XAUUSD-MID-PRE (SELL), XAUUSD-MID-POST (BUY), XAUUSD-END-PRE (SELL), XAUUSD-END-POST (BUY).
  Report-only (not tests): both markets pooled per group x window.

COSTS (mandatory):
  USDJPY: gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m, 10_000, commission=7,
          swap=SwapModel.from_fred('rates', 1.0), sym='USDJPY', slippage_pips=0.2)['R'].
  XAUUSD: run_all_matrix.net_r (commission, slippage per fill + per stop fill, 3%/yr financing per rollover).

PROTOCOL / SURVIVAL (charter): periods by the trade's entry day: design 2010-17, check 2018-23, holdout 2024-26.
  Survives = design t >= 2 AND avg R > 0 in check AND in holdout.
  Report per test: trades, trades/month, win %, avg win / avg loss, avg R and t per period, last 3 years
  (entries after 2023-10-07), and avg R per calendar year. 8 tests -> 8 x 0.006 = 0.048 survivors by luck.

DIAGNOSTICS (not selected on):
  1. Yield concession itself: DGS10 (FRED, end-of-day H.15; missing bond-holiday values forward-filled on NYSE
     days) per cluster in three non-overlapping legs, in bp: PRE = close of the PRE start day -> close of the day
     before the last auction day; AUCTION DAY = close-to-close change on the last auction day (contains both the
     hours before and after the 13:00 result -- daily data cannot split it); POST = close of the last auction
     day -> close two trading days later. Mean, t and n by group and period. Theory: PRE > 0, POST < 0.
     DGS2 (data/extra/DGS2.csv) is shown alongside as context. If the concession is absent in 2010-2026, the FX /
     gold results cannot be attributed to it.
  2. Overlap with the M-3 USDJPY leg (gjstrat.patterns.month_end_usd_bid(m, d >= 2011-01-01, 'BUY'), as in
     run_m3_addon.build_legs): share of M-3 trades whose entry minute lies inside an END-PRE window (and inside
     an END-POST window), and their avg R inside vs outside.
  3. Gotobi: per trade, the number of gotobi Tokyo fixes (gjstrat.patterns.is_gotobi weekdays, 09:55 JST =
     00:55 UTC) inside the SCHEDULED window (entry minute -> scheduled time exit); correlation of trade R with that
     count, avg R with vs without. CHANGE AFTER THE FIRST RUN (diagnostic only, no test affected): the first run
     counted fixes inside the realized holding period, which is mechanically confounded (a stop-out shortens the
     hold, so 'no gotobi fix' picked out the early stop-outs at about -1R); the scheduled window removes that.
     The realized-hold count is kept in trades.csv (n_gotobi_held) for transparency.
  Also: mean signed fill-to-fill move per window before costs (USDJPY in pips, gold in USD and bp), stale exits.

PROP: if any variant survives, Alpha Swing prop sim joined to run_m3_addon.build_legs() (base vol-box 0.25% +
  vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3%), the survivor added at 1% and 2%, normal risk and boost x1.5
  (run_prop_risk_rules.make_rule), starts 2011-2025 and 2018-2025; accepted if months per funded account is
  lower and pass eventually % is not lower in both windows (as run_index_prop / run_alpha_fomc_cycle).
  Gold trades join the USDJPY grid by entry/exit UTC timestamps.

COMPUTE: USDJPY then XAUUSD, each loaded alone and deleted; no multiprocessing.

    python run_alpha_ust_auction.py      # writes results/alpha_hunt/ust_auction/
"""
import gc
import os
import re
import time
from collections import namedtuple
from datetime import date

import holidays
import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import load_market
from gjstrat.patterns import NY, Signal, daily_table, is_gotobi, local_idx, month_end_usd_bid, simulate, utc_idx
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_backtest import fmt_table as _fmt_table
from run_edge_hunt import PER
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/ust_auction"
AUCT = "data/extra/ust_auctions.csv"
FILES = {"USDJPY": "data/usdjpy_2010-01-01_2026-10-07.npz", "XAUUSD": "data/xauusd_2010-01-01_2026-10-07.npz"}
SIDE = {("USDJPY", "PRE"): "BUY", ("USDJPY", "POST"): "SELL", ("XAUUSD", "PRE"): "SELL", ("XAUUSD", "POST"): "BUY"}
VARIANTS = [f"{s}-{g}-{w}" for s in ("USDJPY", "XAUUSD") for g in ("MID", "END") for w in ("PRE", "POST")]
DATA_END = pd.Timestamp("2026-10-07")
LAST3 = pd.Timestamp("2023-10-08")
Tr = namedtuple("Tr", "day entry_i exit_i")


def fmt_table(df, f=".2f"):
    """run_backtest.fmt_table on an object copy, so iterrows keeps integer counts as integers."""
    return _fmt_table(df.astype(object), f)


# ----------------------------------------------------------------------------------------- calendar / events
def nyse_days():
    hol = set(holidays.NYSE(years=range(2009, 2028))) | {date(2025, 1, 9)}
    return pd.DatetimeIndex([x for x in pd.bdate_range("2009-05-01", "2027-03-31") if x.date() not in hol])


def group_of(term):
    if term in ("3-Year", "10-Year", "30-Year") or re.fullmatch(r"(9|29)-Year \d+-Month", term):
        return "MID"
    if term in ("2-Year", "5-Year", "7-Year"):
        return "END"
    return None


def load_clusters(days):
    a = pd.read_csv(AUCT, parse_dates=["auction_date"])
    a = a[a.security_type.isin(["Note", "Bond"]) & (a.inflation_index_security == "No") & (a.floating_rate == "No")].copy()
    amt = a.offering_amt.astype(float)
    tiny = a[amt < 1e9]
    a = a[amt >= 1e9].copy()
    a["group"] = a.security_term.map(group_of)
    a = a.dropna(subset=["group"])
    a["week"] = a.auction_date - pd.to_timedelta(a.auction_date.dt.dayofweek, unit="D")
    pos = {d: k for k, d in enumerate(days)}
    rows = []
    for (g, wk), x in a.sort_values("auction_date").groupby(["group", "week"]):
        first, last = x.auction_date.min(), x.auction_date.max()
        assert first in pos and last in pos, f"auction day not an NYSE trading day: {first.date()} {last.date()}"
        pf, pl = pos[first], pos[last]
        rows.append({"group": g, "week": wk, "first": first, "last": last, "n_auctions": len(x),
                     "auction_days": x.auction_date.nunique(), "terms": "/".join(x.security_term),
                     "pre_start": days[pf - 5], "day_before_last": days[pl - 1], "post_end": days[pl + 2]})
    C = pd.DataFrame(rows).sort_values(["first", "group"]).reset_index(drop=True)
    C["cid"] = np.arange(len(C))
    return C, tiny


# ----------------------------------------------------------------------------------------- market tests
def session_label(ts_utc):
    return (pd.Timestamp(ts_utc).tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def window_idx(m, c, w):
    if w == "PRE":
        return local_idx(m, c.pre_start, 15, 55, NY), local_idx(m, c.last, 12, 55, NY)
    return local_idx(m, c.last, 13, 5, NY), local_idx(m, c.post_end, 15, 55, NY)


def gotobi_fixes(m):
    gd = [x for x in pd.bdate_range("2009-12-01", "2026-12-31") if is_gotobi(x)]
    return np.array(sorted(utc_idx(m, x, 0, 55) for x in gd))


def run_market(sym, C, sw):
    t0 = time.time()
    m = load_market(FILES[sym])
    d = daily_table(m)
    gfix = gotobi_fixes(m)
    parts, skips = [], []
    for g in ("MID", "END"):
        for w in ("PRE", "POST"):
            v, side = f"{sym}-{g}-{w}", SIDE[(sym, w)]
            pairs, sk = [], {"variant": v, "clusters": 0, "outside data / no ATR": 0, "no live entry minute": 0,
                             "no fill / exit before entry": 0}
            for c in C[C.group == g].itertuples():
                sk["clusters"] += 1
                i, j = window_idx(m, c, w)
                if i < 0 or j >= m.n - 1:
                    sk["outside data / no ATR"] += 1
                    continue
                s = live_at(m, i)
                if s < 0:
                    sk["no live entry minute"] += 1
                    continue
                atr = d["atr20"].get(session_label(m.ts(s)), np.nan)
                if not atr > 0:
                    sk["outside data / no ATR"] += 1
                    continue
                if j <= s + 1:
                    sk["no fill / exit before entry"] += 1
                    continue
                t = simulate(m, Signal(session_label(m.ts(s)), side, s, "market", None, s + 1, 1.0 * atr, None, j, v))
                if t is None:
                    sk["no fill / exit before entry"] += 1
                    continue
                pairs.append((t, c, j))
            skips.append(sk)
            pairs.sort(key=lambda p: (p[0].exit_i, p[0].entry_i))
            tr = [p[0] for p in pairs]
            if not tr:
                continue
            if sym == "USDJPY":
                lg = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
                assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
                r = lg["R"].to_numpy()
            else:
                r = net_r(m, sym, tr, None)
            sgn = np.array([1.0 if t.side == "BUY" else -1.0 for t in tr])
            move = sgn * np.array([t.exit - t.entry for t in tr])
            ent = np.array([t.entry_i for t in tr])
            ext = np.array([t.exit_i for t in tr])
            jj = np.array([p[2] for p in pairs])
            ngot_held = np.searchsorted(gfix, ext, "left") - np.searchsorted(gfix, ent, "left")
            ngot = np.searchsorted(gfix, jj, "left") - np.searchsorted(gfix, ent, "left")
            parts.append(pd.DataFrame({
                "variant": v, "sym": sym, "group": g, "window": w, "side": side,
                "cid": [p[1].cid for p in pairs], "last_auction": [p[1].last for p in pairs],
                "day": [t.day for t in tr], "R": r, "R_gross": [t.r for t in tr],
                "entry_utc": [m.ts(t.entry_i) for t in tr], "exit_utc": [m.ts(t.exit_i) for t in tr],
                "entry": [t.entry for t in tr], "exit": [t.exit for t in tr], "sl": [t.risk for t in tr],
                "reason": [t.reason for t in tr], "move": move, "move_pips": move / m.pip,
                "move_bp": move / np.array([t.entry for t in tr]) * 1e4,
                "hours": (ext - ent) / 60.0, "n_gotobi": ngot, "n_gotobi_held": ngot_held,
                "stale_exit": [t.reason == "TIME" and m.vol[max(t.exit_i - 4, 0): t.exit_i + 1].sum() == 0 for t in tr]}))
            print(v, len(tr), round(float(np.mean(r)), 3), flush=True)
    m3 = None
    if sym == "USDJPY":
        m3 = m3_overlap(m, d, C, sw)
    T = pd.concat(parts, ignore_index=True)
    print(sym, "done", f"{time.time() - t0:.0f}s", flush=True)
    del m, d
    gc.collect()
    return T, pd.DataFrame(skips), m3


def m3_overlap(m, d, C, sw):
    d11 = d[d.index >= pd.Timestamp("2011-01-01")]
    tr = sorted([t for t in (simulate(m, s) for s in month_end_usd_bid(m, d11, "BUY")) if t is not None],
                key=lambda t: (t.exit_i, t.entry_i))
    r = account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()
    E = C[C.group == "END"]
    win = {w: np.array([window_idx(m, c, w) for c in E.itertuples()]) for w in ("PRE", "POST")}
    ins = {}
    for w, a in win.items():
        ins[w] = np.array([bool(((a[:, 0] <= t.entry_i) & (t.entry_i < a[:, 1])).any()) for t in tr])
    return pd.DataFrame({"day": [t.day for t in tr], "R": r, "entry_utc": [m.ts(t.entry_i) for t in tr],
                         "in_END_PRE": ins["PRE"], "in_END_POST": ins["POST"]})


# ----------------------------------------------------------------------------------------- stats
def per_mask(day, p):
    a, b = PER[p]
    day = pd.DatetimeIndex(day)
    return np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))


def summary(name, r, day):
    r, day = np.asarray(r, float), pd.DatetimeIndex(day)
    wins, losses = r[r > 0], r[r <= 0]
    months = max(((day.max() - day.min()).days + 1) / 30.44, 1.0) if len(r) else np.nan
    row = {"test": name, "trades": len(r), "trades/month": len(r) / months if len(r) else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}
    for p in PER:
        v = r[per_mask(day, p)]
        row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v)})
    v = r[np.asarray(day >= LAST3)]
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    return row


def yields(C, days):
    out = []
    for ser in ("DGS10", "DGS2"):
        y = pd.read_csv(f"data/extra/{ser}.csv", na_values=["."], parse_dates=["observation_date"])
        y = y.set_index("observation_date")[ser].dropna()
        y = y.reindex(y.index.union(days)).ffill().reindex(days)
        for c in C.itertuples():
            if c.pre_start < pd.Timestamp("2010-01-01") or c.post_end > DATA_END:
                continue
            a, b, l, e = (y.get(x, np.nan) for x in (c.pre_start, c.day_before_last, c.last, c.post_end))
            out.append({"series": ser, "group": c.group, "cid": c.cid, "day": c.pre_start,
                        "PRE": (b - a) * 100, "AUCTION DAY": (l - b) * 100, "POST": (e - l) * 100})
    Y = pd.DataFrame(out)
    rows = []
    for (ser, g), x in Y.groupby(["series", "group"], sort=False):
        for p in ["all"] + list(PER):
            sel = np.ones(len(x), bool) if p == "all" else per_mask(x.day, p)
            z = x[sel]
            row = {"series": ser, "group": g, "period": p, "clusters": len(z)}
            for leg in ("PRE", "AUCTION DAY", "POST"):
                row[f"{leg} bp"] = z[leg].mean()
                row[f"{leg} t"] = tstat(z[leg].dropna())
            rows.append(row)
    return Y, pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------- prop
def prop(survivors, trades):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    m, legs = build_legs()
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(survivors)}
    for v in survivors:
        T = trades[trades.variant == v].sort_values(["exit_utc", "entry_utc"])
        ei = ((pd.DatetimeIndex(T.entry_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        xi = ((pd.DatetimeIndex(T.exit_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        legs.append(([Tr(pd.Timestamp(d), a, b) for d, a, b in zip(T.day, ei, xi)], T.R.to_numpy()))
    for risk in (1, 2):
        for j, v in enumerate(survivors):
            mixes[f"basket + {v} {risk}%"] = base + tuple(risk if i == j else 0 for i in range(len(survivors)))
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
    acc = []
    for rule, mix in zip(P["risk rule"], P.index):
        if mix == "basket":
            acc.append(None)
            continue
        ok = True
        for w in P.window.unique():
            q = P[(P["risk rule"] == rule) & (P.window == w)]
            ok &= bool(q.loc[mix, "months per funded account"] < q.loc["basket", "months per funded account"]
                       and q.loc[mix, "pass eventually %"] >= q.loc["basket", "pass eventually %"])
        acc.append(ok)
    P["accepted"] = acc
    P.index.name = "mix"
    del m
    return P


# ----------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    days = nyse_days()
    C, tiny = load_clusters(days)
    C.to_csv(f"{OUT}/clusters.csv", index=False)
    print("clusters", C.groupby("group").size().to_dict(), "dropped tiny", len(tiny), flush=True)
    sw = SwapModel.from_fred("rates", 1.0)

    T1, S1, M3 = run_market("USDJPY", C, sw)
    T2, S2, _ = run_market("XAUUSD", C, sw)
    trades = pd.concat([T1, T2], ignore_index=True)
    trades["day"] = pd.to_datetime(trades.day)
    trades.to_csv(f"{OUT}/trades.csv", index=False)
    SK = pd.concat([S1, S2]).set_index("variant")
    M3.to_csv(f"{OUT}/m3_overlap.csv", index=False)

    # charter table
    S = pd.DataFrame([summary(v, trades[trades.variant == v].R, trades[trades.variant == v].day) for v in VARIANTS]).set_index("test")
    S["survives"] = [bool(x["design t"] >= 2 and x["check avg R"] > 0 and x["holdout avg R"] > 0) for _, x in S.iterrows()]
    S.to_csv(f"{OUT}/summary.csv")
    survivors = [v for v in VARIANTS if S.loc[v, "survives"]]

    # pooled report-only
    pool = []
    for g in ("MID", "END"):
        for w in ("PRE", "POST"):
            x = trades[(trades.group == g) & (trades.window == w)]
            pool.append(summary(f"pooled {g}-{w} (USDJPY {SIDE[('USDJPY', w)]} + gold {SIDE[('XAUUSD', w)]})", x.R, x.day))
    POOL = pd.DataFrame(pool).set_index("test")

    # per year
    trades["year"] = trades.day.dt.year
    YR = trades.pivot_table(index="variant", columns="year", values="R", aggfunc="mean").reindex(VARIANTS)
    YRN = trades.pivot_table(index="variant", columns="year", values="R", aggfunc="size").reindex(VARIANTS)
    YR.to_csv(f"{OUT}/per_year.csv")
    YR.columns = [str(c) for c in YR.columns]
    yrs_pos = (YR > 0).sum(axis=1).rename("years > 0").to_frame()
    yrs_pos["years"] = YR.notna().sum(axis=1)

    # gross move before costs
    mv = []
    for v in VARIANTS:
        x = trades[trades.variant == v]
        unit = "pips" if x.sym.iloc[0] == "USDJPY" else "USD"
        col = "move_pips" if unit == "pips" else "move"
        row = {"test": v, "unit": unit, "mean move (signed, fill to fill)": x[col].mean(), "t": tstat(x[col]),
               "mean move bp": x.move_bp.mean(), "mean R before costs": x.R_gross.mean(), "mean R net": x.R.mean(),
               "mean SL (unit)": (x.sl / (0.01 if unit == "pips" else 1)).mean(), "mean hours held": x.hours.mean(),
               "SL exits %": (x.reason == "SL").mean() * 100, "stale exits": int(x.stale_exit.sum())}
        for p in PER:
            row[f"{p} move"] = x[per_mask(x.day, p)][col].mean()
        mv.append(row)
    MV = pd.DataFrame(mv).set_index("test")

    # yields
    Y, YS = yields(C, days)
    Y.to_csv(f"{OUT}/yield_windows.csv", index=False)
    YS = YS.set_index("series")

    # M-3 overlap
    m3rows = []
    for lab, sel in (("all M-3 trades", np.ones(len(M3), bool)), ("inside END-PRE", M3.in_END_PRE.to_numpy()),
                     ("outside END-PRE", ~M3.in_END_PRE.to_numpy()), ("inside END-POST", M3.in_END_POST.to_numpy()),
                     ("outside both", ~(M3.in_END_PRE | M3.in_END_POST).to_numpy())):
        x = M3[sel]
        row = {"M-3 USDJPY subset": lab, "trades": len(x), "share %": len(x) / len(M3) * 100,
               "win %": (x.R > 0).mean() * 100, "avg R": x.R.mean(), "t": tstat(x.R)}
        for p in PER:
            z = x[per_mask(x.day, p)].R
            row[f"{p} n"], row[f"{p} avg R"] = len(z), z.mean()
        m3rows.append(row)
    M3T = pd.DataFrame(m3rows).set_index("M-3 USDJPY subset")
    a, b = M3[M3.in_END_PRE].R, M3[~M3.in_END_PRE].R
    welch_t = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) if len(a) > 1 and len(b) > 1 else np.nan

    # gotobi
    gt = []
    for v in VARIANTS:
        x = trades[trades.variant == v]
        row = {"test": v}
        for lab, sel in (("0 fixes", x.n_gotobi == 0), ("1 fix", x.n_gotobi == 1), (">=2 fixes", x.n_gotobi >= 2)):
            row[f"{lab} n"], row[f"{lab} avg R"] = int(sel.sum()), x[sel].R.mean()
        row["corr(R, n gotobi fixes)"] = np.corrcoef(x.R, x.n_gotobi)[0, 1] if x.n_gotobi.std() > 0 else np.nan
        row["mean n gotobi fixes"] = x.n_gotobi.mean()
        gt.append(row)
    GT = pd.DataFrame(gt).set_index("test")

    P = None
    if survivors:
        P = prop(survivors, trades)
        P.to_csv(f"{OUT}/prop.csv")

    # ------------------------------------------------------------------ report
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R",
            "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n",
            "last3y avg R", "last3y t"]
    n_tests = len(VARIANTS)
    ovl = 0
    for g in ("MID", "END"):
        E = C[C.group == g].sort_values("first")
        ovl += int((E.pre_start.to_numpy()[1:] <= E.post_end.to_numpy()[:-1]).sum())
    cl_tab = C.groupby("group").agg(clusters=("cid", "size"), auctions=("n_auctions", "sum"),
                                    first=("first", "min"), last=("last", "max"))
    cl_tab["first"], cl_tab["last"] = cl_tab["first"].dt.date.astype(str), cl_tab["last"].dt.date.astype(str)
    cl_tab["clusters with < 3 auctions"] = C.groupby("group").n_auctions.apply(lambda s: int((s < 3).sum()))
    txt = ["# US Treasury auction concession cycle via USDJPY and gold (ust_auction)\n",
           "Script: `run_alpha_ust_auction.py` (all rules in its docstring, fixed before running). Costs included "
           "everywhere (USDJPY: $7/lot, 0.2 pip stop slippage, swap +1%; XAUUSD: run_all_matrix.net_r with "
           "commission, slippage and 3%/yr financing).\n",
           f"**Survivors: {len(survivors)} of {n_tests} tests** ({', '.join(survivors) or 'none'}); expected by luck: "
           f"{n_tests} x 0.006 = {n_tests * 0.006:.3f}.\n",
           "Survival = design 2010-17 t >= 2 AND avg R > 0 in check 2018-23 AND holdout 2024-26 (periods by entry day). "
           "Last 3 years = entries after 2023-10-07.\n",
           "Rules: PRE = 15:55 NY five NYSE trading days before the cluster's first auction -> 12:55 NY on its last "
           "auction day; POST = 13:05 NY on the last auction day -> 15:55 NY two trading days later. USDJPY BUY in PRE / "
           "SELL in POST, gold SELL in PRE / BUY in POST; market entry, time exit, SL 1.0 x ATR20, no TP. "
           "MID = 3y/10y/30y (incl. reopenings), END = 2y/5y/7y; nominal fixed-coupon only (TIPS, FRNs dropped).\n",
           "## Auction clusters\n", fmt_table(cl_tab, ".0f"),
           f"\nDropped as not real supply (offering < $1bn, a spec fix): "
           + ", ".join(f"{r.auction_date.date()} {r.security_term} ${float(r.offering_amt) / 1e6:.0f}m" for r in tiny.itertuples())
           + f". Consecutive same-group clusters whose windows overlap: {ovl} (the debt-ceiling split of Oct/Nov 2015).\n",
           "\nSkipped windows per variant:\n", fmt_table(SK, ".0f"),
           "\n## All tests (net R per trade)\n", fmt_table(S[cols + ["survives"]], ".3f"),
           "\n## Report-only: both markets pooled per group x window\n", fmt_table(POOL[cols], ".3f"),
           "\n## Avg R per calendar year (by entry day)\n", fmt_table(YR, ".2f"),
           "\nTrades per year:\n", fmt_table(YRN.fillna(0).astype(int).rename(columns=str), ".0f"),
           "\nYears with avg R > 0:\n", fmt_table(yrs_pos, ".0f"),
           "\n## Signed move before costs (fill to fill, in the trade's direction)\n",
           "USDJPY in pips, gold in USD; 'mean R before costs' uses the simulator's bid/ask fills (spread paid) "
           "but no commission, slippage or financing.\n", fmt_table(MV, ".2f"),
           "\n## Diagnostic 1: is the yield concession there? (bp, daily closes)\n",
           "PRE = close of the PRE start day -> close of the day before the last auction day; AUCTION DAY = close-to-close "
           "on the last auction day (holds both the pre-13:00 run-up and the post-result move); POST = close of the last "
           "auction day -> close two trading days later. Theory: PRE > 0 and POST < 0. FRED H.15 constant-maturity "
           "yields; bond-holiday gaps forward-filled.\n", fmt_table(YS, ".2f"),
           "\n## Diagnostic 2: overlap with the M-3 USDJPY leg (11:00-12:00 UTC, 3rd-last weekday, BUY)\n",
           fmt_table(M3T, ".3f"),
           f"\nInside vs outside END-PRE, Welch t of the difference in avg R: {welch_t:.2f}.\n",
           "\n## Diagnostic 3: gotobi fixes inside the scheduled window (entry -> scheduled exit)\n", fmt_table(GT, ".3f"),
           "\n## Sources\n",
           "- Auctions: data/extra/ust_auctions.csv, https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"
           "accounting/od/auctions_query (full URL in data/extra/SOURCES.csv).\n",
           "- Yields: data/extra/DGS10.csv, data/extra/DGS2.csv (FRED).\n",
           "\nFiles: summary.csv, trades.csv, per_year.csv, clusters.csv, yield_windows.csv, m3_overlap.csv"
           + (", prop.csv" if P is not None else "") + ".\n",
           "\n## Prop sim\n", ("Run below (survivors joined to run_m3_addon.build_legs())." if P is not None
                                else "Not run: no variant survived, so nothing is added to the Alpha Swing basket.") + "\n"]
    if P is not None:
        pcols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
                 "pass eventually %", "median months to pass", "months per funded account", "accepted"]
        txt += [fmt_table(P[[c for c in pcols if c in P.columns]], ".1f") + "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(S[cols + ["survives"]].round(3).to_string())
    print(POOL[cols].round(3).to_string())
    print(YR.round(2).to_string())
    print(MV.round(2).to_string())
    print(YS.round(2).to_string())
    print(M3T.round(3).to_string(), "welch", round(welch_t, 2))
    print(GT.round(3).to_string())
    print(SK.to_string())
    print("survivors", survivors, f"{time.time() - t_start:.0f}s")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
