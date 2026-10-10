"""Alpha hunt family `cross_zfade`: daily z-score fade to the mean on range-bound "twinned" crosses
(AUDNZD, EURGBP, AUDCAD, NZDCAD, EURCHF). Every rule below was fixed before the first run.

IDEA (Lens-3 #3): each cross is the spread between two currencies that share their macro anchor (AUD/NZD/CAD:
commodity terms of trade, China exposure, synchronised central-bank cycles; EUR/GBP/CHF: European trade and
policy). A large move in the cross is usually idiosyncratic flow (M&A, exporter / pension hedges, one central-bank
surprise), not a change in the anchor, and it partly reverses over days to weeks as relative-value desks lean
against it: short-horizon liquidity provision, not PPP. Evidence is mostly practitioner (bank range-trade notes;
AUDNZD has held roughly 1.00-1.15 since 2015; Bollinger 2001; Kaufman's efficiency ratio as a regime gauge). The
academic FX literature points to momentum at 1-12 months, so the test is honest. New vs the repo: the quiet-hours
Bollinger fade was intraday with tight stops; this is daily-horizon, 1.5 ATR stops, multi-day holds, small swaps.

MARKETS (5, one market loaded per worker and deleted; multiprocessing.Pool(2)):
  AUDNZD, EURGBP, AUDCAD, NZDCAD, EURCHF; data/<pair>_2010-01-01_2026-10-07.npz (all share t0 2009-12-31).

SIGNAL SERIES (DST-aware gjstrat.patterns.local_idx, America/New_York):
  * One candidate close per weekday (Mon-Fri calendar, 2010-01-01 .. last data day). C_t = bid close of the
    16:44 NY minute. A day is skipped (not in the series) if no minute in [16:40, 16:45) NY has ticks (vol > 0).
  * Entry = market order at the open of the 16:45 NY minute of the signal day (gjstrat.patterns.simulate:
    buys fill on ask, sells on bid). Every non-stop exit is at the open of the 16:45 NY minute of the exit day.
  * "Trading days" / "closes" = positions in this series (skipped days do not count).
  * Rollover-spread check (report only): median and p90 (ask - bid) in pips at the 16:45 NY minute vs at 12:00 NY
    (live minutes only) on the series days.

INDICATORS (on the close series, closes up to and including t; nothing after the 16:44 close is used):
  * z_N = (C_t - SMA_N) / SD_N over the last N closes (SD = sample standard deviation, ddof = 1, the pandas
    rolling default); N = 20 or 50. Undefined (no trade) until N closes exist or if SD_N = 0.
  * ER_N = |C_t - C_{t-N}| / sum_{i=t-N+1..t} |C_i - C_{i-1}| (Kaufman efficiency ratio; undefined if the
    denominator is 0).
  * ATR20 = gjstrat.patterns.daily_table(m).atr20 of the signal (= entry) day: mean daily (NY 17:00) high-low of
    the 20 previous days, shifted, so known before the day. If the day is missing from the daily table, the last
    earlier value.

RULES (per pair, per variant):
  * Entry: SELL when z_N >= +k; BUY when z_N <= -k (evaluated at each close; the trade fills at 16:45 NY).
  * Exit: at the first LATER close (position > entry close) where z_N has crossed back through 0 (z_N <= 0 for
    shorts, z_N >= 0 for longs) -> "MEAN"; otherwise the time stop at the close H positions after the entry close
    (H = 10 trading days for N = 20, H = 20 for N = 50) -> "TIME". A mean cross exactly on the time-stop close
    counts as MEAN. The exit close is path-independent (closes only), so it is precomputed and passed to simulate
    as exit_by_i = that close's 16:45 NY minute.
  * Stop: SL = 1.5 x ATR20 from the fill (Z9: 2.5 x ATR20), checked minute by minute on real bid/ask by
    gjstrat.patterns.simulate (gap through the stop fills at the bar open). No TP. 1R = the SL distance.
  * One position per pair per variant: signals while a trade is open are ignored. After an exit, a new entry
    needs a later close beyond +/-k: only closes whose 16:45 entry minute is strictly after the exit minute
    qualify (after a MEAN/TIME exit at day X's 16:45 the earliest re-entry is day X+1's close; after a stop hit
    during day X before 16:45, day X's own close qualifies). No requirement that z first returns inside the band.
  * EURCHF: no entries on signal days 2011-09-06 .. 2015-01-15 inclusive (SNB 1.20 floor and its removal).
    Reported separately: (a) open EURCHF exposure of every variant on 2015-01-15 (expected: none), (b) for
    illustration only, Z1 run on EURCHF WITHOUT the floor exclusion: the trade(s) open at the de-peg
    (2015-01-15 09:30 UTC) with their R, and Z1's floor-period trades in total. (c) Diagnostic: EURCHF trades
    with signal days 2015-01-16 .. 2015-03-31 (their z windows still contain floor prices).
  * Obvious-impossibility fix: if neither the mean exit nor the time stop exists before the end of the data, the
    trade exits at the last close's 16:45 minute ("END").

VARIANTS (9):
  Z1: N=20, k=2.0      Z2: N=20, k=2.5      Z3: N=50, k=2.0      Z4: N=50, k=2.5
  Z5-Z8: Z1-Z4, entries only when ER_N < 0.3 at the signal close (pre-declared defence against trending regimes:
         Brexit 2016, AUDNZD 2022-23). Exits unchanged.
  Z9: Z1 with SL 2.5 x ATR20.

COSTS (in every result): gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m, 10_000, commission=7,
swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'] ($7/lot round turn, 0.2 pip on the entry
and on stop exits, swap from FRED rates with a 1%/yr markup, 3x on Wednesdays). R_gross = price R before costs.

PERIODS / STATISTICS: run_edge_hunt.PER by signal day: design 2010-17, check 2018-23, holdout 2024-26; last 3 years
= 2023-10-08..2026-10-07. Per test: trades, trades/month, win %, avg win / avg loss, avg R and t per period, last
3 years, average hold (calendar and trading days), exit-reason mix (MEAN / TIME / SL / END), longest losing streak,
max running-R drawdown. Per pair (trade-level t, month t also shown) and pooled per variant over the 5 pairs with
the month-clustered t (sum of R per calendar month of the signal day, zero for months without trades, t over
months). Count of pairs with avg R > 0 (2010-2026). Worst 5 trades per variant with dates; EURGBP trades open
around the Brexit vote (2016-06-23 21:00 UTC .. 2016-06-24 21:00 UTC); AUDNZD 2022-23 trades. Avg R per signal year
(pooled per variant; per pair for Z1 and Z5). Gross vs cost vs net R; long vs short.

JUDGING: 9 pooled tests. A variant survives if the pooled 5-pair result meets the charter bar (design 2010-17
month-clustered t >= 2 AND avg R > 0 in check 2018-23 AND in holdout 2024-26) AND >= 4 of the 5 pairs have avg R > 0
over 2010-2026. Luck alone: 9 x 0.006 = 0.05 survivors. Per-pair charter results (45 tests) are information only.
IF A VARIANT SURVIVES: prop sim (gjstrat.prop.prop_table, run_m3_addon.ALPHA rules, normal risk and boost x1.5
(run_prop_risk_rules.make_rule), challenges started 2011-2025 and 2018-2025): run_m3_addon.build_legs() basket
(vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3%) plus the variant's 5-pair trades at 0.5% risk per trade,
and the variant alone at 0.5%. Trades join the USDJPY minute grid by their UTC timestamps (all pair files share
t0 2009-12-31, so the shift is 0). Also the correlation of monthly R (by exit month) with the basket legs.

ADDED AFTER THE FIRST RUN (reporting only; no rule, variant, market or bar changed): a `report` mode that rebuilds
REPORT.md from raw.pkl, and in the EURCHF illustration the Z1 trades entered or exited on 2015-01-15 itself.

OUTPUT: results/alpha_hunt/cross_zfade/REPORT.md, tests.csv (per pair), pooled.csv, trades.csv / trades.pkl,
by_year.csv, spreads.csv, eurchf_floor.csv, data_info.csv, raw.pkl, run.log.

    python run_alpha_cross_zfade.py          # everything (prop sim only if a variant survives)
    python run_alpha_cross_zfade.py prop     # prop sim from the saved trades
    python run_alpha_cross_zfade.py report   # rebuild the report from the saved raw results (raw.pkl)
"""
from __future__ import annotations

import os
import sys
import time
from collections import namedtuple
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import load_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/cross_zfade"
PAIRS = ["AUDNZD", "EURGBP", "AUDCAD", "NZDCAD", "EURCHF"]
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
FLOOR = (pd.Timestamp("2011-09-06"), pd.Timestamp("2015-01-15"))
DEPEG = pd.Timestamp("2015-01-15 09:30")          # SNB announcement, UTC
BREXIT = (pd.Timestamp("2016-06-23 21:00"), pd.Timestamp("2016-06-24 21:00"))
VARIANTS = {
    "Z1": dict(N=20, k=2.0, er=False, slm=1.5), "Z2": dict(N=20, k=2.5, er=False, slm=1.5),
    "Z3": dict(N=50, k=2.0, er=False, slm=1.5), "Z4": dict(N=50, k=2.5, er=False, slm=1.5),
    "Z5": dict(N=20, k=2.0, er=True, slm=1.5), "Z6": dict(N=20, k=2.5, er=True, slm=1.5),
    "Z7": dict(N=50, k=2.0, er=True, slm=1.5), "Z8": dict(N=50, k=2.5, er=True, slm=1.5),
    "Z9": dict(N=20, k=2.0, er=False, slm=2.5),
}
DESC = {v: f"N={c['N']} k={c['k']:g}" + (" ER<0.3" if c["er"] else "") + f" SL {c['slm']:g}ATR"
        for v, c in VARIANTS.items()}
HOLD = {20: 10, 50: 20}
ER_MAX = 0.3


def path_of(sym):
    return f"data/{sym.lower()}_2010-01-01_2026-10-07.npz"


# --------------------------------------------------------------------------- close series
def close_series(m, d) -> pd.DataFrame:
    last = m.ts(m.n - 1)
    rows = []
    for day in pd.bdate_range("2010-01-01", last.normalize()):
        i = local_idx(m, day, 16, 44, NY)
        if i < 4 or i + 1 >= m.n:
            continue
        if not m.vol[i - 4: i + 1].sum() > 0:                 # no ticks in [16:40, 16:45) NY
            continue
        rows.append((day, i, i + 1, m.bc[i]))
    cs = pd.DataFrame(rows, columns=["day", "i", "s", "C"]).set_index("day")
    atr = d["atr20"]
    cs["atr20"] = atr.reindex(atr.index.union(cs.index)).ffill().reindex(cs.index).to_numpy()
    C = cs.C
    absd = C.diff().abs()
    for N in (20, 50):
        sma = C.rolling(N).mean()
        sd = C.rolling(N).std(ddof=1)
        cs[f"z{N}"] = ((C - sma) / sd.where(sd > 0)).to_numpy()
        den = absd.rolling(N).sum()
        cs[f"er{N}"] = ((C - C.shift(N)).abs() / den.where(den > 0)).to_numpy()
    return cs


def plan_variant(m, cs, v, cfg, block_floor: bool):
    """Sequential one-position plan. Returns list of (Trade, reason, j, kx)."""
    N, k, slm = cfg["N"], cfg["k"], cfg["slm"]
    H = HOLD[N]
    z = cs[f"z{N}"].to_numpy(dtype=float)
    er = cs[f"er{N}"].to_numpy(dtype=float)
    atr = cs.atr20.to_numpy(dtype=float)
    S = cs.s.to_numpy()
    days = cs.index
    n = len(cs)
    out = []
    last_exit = -1
    for j in range(n):
        if S[j] <= last_exit:
            continue
        zj = z[j]
        if not np.isfinite(zj):
            continue
        if zj >= k:
            side = "SELL"
        elif zj <= -k:
            side = "BUY"
        else:
            continue
        if cfg["er"] and not (er[j] < ER_MAX):
            continue
        if block_floor and FLOOR[0] <= days[j] <= FLOOR[1]:
            continue
        if not atr[j] > 0:
            continue
        kx, why = None, None
        for q in range(j + 1, min(j + H, n - 1) + 1):
            if (side == "SELL" and z[q] <= 0) or (side == "BUY" and z[q] >= 0):
                kx, why = q, "MEAN"
                break
        if kx is None:
            if j + H <= n - 1:
                kx, why = j + H, "TIME"
            elif n - 1 > j:
                kx, why = n - 1, "END"
            else:
                continue
        t = simulate(m, Signal(days[j], side, int(S[j]), "market", None, int(S[j]) + 1, slm * atr[j], None,
                               int(S[kx]), v))
        if t is None:
            continue
        out.append((t, "SL" if t.reason == "SL" else why, j, kx))
        last_exit = t.exit_i
    return out


def records(m, sym, cs, v, plan, swap):
    plan = sorted(plan, key=lambda x: (x[0].exit_i, x[0].entry_i))
    tr = [x[0] for x in plan]
    if not tr:
        return []
    lg = account(tr, m, 10_000, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
    assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
    R = lg["R"].to_numpy()
    S = cs.s.to_numpy()
    recs = []
    for (t, why, j, kx), r, sw in zip(plan, R, lg["swap_usd"].to_numpy()):
        xk = kx if why != "SL" else int(np.searchsorted(S, t.exit_i, side="left"))
        recs.append(dict(market=sym, variant=v, day=t.day, side=t.side, entry_ts=m.ts(t.entry_i),
                         exit_ts=m.ts(t.exit_i), entry=t.entry, exit=t.exit, reason=why, risk=t.risk,
                         risk_pips=t.risk / m.pip, z=cs[f"z{VARIANTS[v]['N']}"].iat[j] if v in VARIANTS else np.nan,
                         er=cs[f"er{VARIANTS[v]['N']}"].iat[j] if v in VARIANTS else np.nan,
                         hold_tdays=xk - j, R_gross=t.r, R=r, swap_usd=sw))
    return recs


# --------------------------------------------------------------------------- one market
def run_market(sym: str):
    t0 = time.time()
    m = load_market(path_of(sym))
    d = daily_table(m)
    swap = SwapModel.from_fred("rates", 1.0)
    cs = close_series(m, d)
    S = cs.s.to_numpy()

    # rollover-spread check
    spr_e = (m.ao[S] - m.bo[S]) / m.pip
    noon = np.array([local_idx(m, x, 12, 0, NY) for x in cs.index])
    noon = noon[(noon >= 0) & (noon < m.n)]
    noon = noon[m.vol[noon] > 0]
    spr_n = (m.ao[noon] - m.bo[noon]) / m.pip
    spreads = {"pair": sym, "median spread 16:45 NY (pips)": float(np.median(spr_e)),
               "median spread 12:00 NY (pips)": float(np.median(spr_n)),
               "p90 spread 16:45 NY": float(np.percentile(spr_e, 90)), "p90 spread 12:00 NY": float(np.percentile(spr_n, 90)),
               "median ATR20 (pips)": float(np.nanmedian(cs.atr20) / m.pip),
               "median 16:45 spread / (1.5 ATR20)": float(np.nanmedian(spr_e * m.pip / (1.5 * cs.atr20.to_numpy())))}

    recs = []
    for v, cfg in VARIANTS.items():
        plan = plan_variant(m, cs, v, cfg, block_floor=(sym == "EURCHF"))
        recs += records(m, sym, cs, v, plan, swap)

    floor_recs = []
    if sym == "EURCHF":                                    # illustration only: Z1 without the floor exclusion
        plan = plan_variant(m, cs, "Z1", VARIANTS["Z1"], block_floor=False)
        floor_recs = records(m, sym, cs, "Z1", plan, swap)
        for r in floor_recs:
            r["variant"] = "Z1 incl. floor (illustration)"
        # de-peg day prices for the record
        a = m.idx(pd.Timestamp("2015-01-15 09:00"))
        b = m.idx(pd.Timestamp("2015-01-15 21:00"))
        print(f"EURCHF 2015-01-15 09:00-21:00 UTC bid low {m.bl[a:b].min():.4f} high {m.bh[a:b].max():.4f}", flush=True)

    info = {"pair": sym, "closes": len(cs), "first close": cs.index[0].date(), "last close": cs.index[-1].date(),
            "weekdays skipped (no ticks 16:40-16:45)": int(len(pd.bdate_range("2010-01-01", cs.index[-1])) - len(cs)),
            "months with data": int(pd.DatetimeIndex(cs.index).to_period("M").nunique()),
            "z20 share |z|>=2": float(np.nanmean(np.abs(cs.z20) >= 2)), "z50 share |z|>=2": float(np.nanmean(np.abs(cs.z50) >= 2)),
            "median ER20": float(np.nanmedian(cs.er20)), "median ER50": float(np.nanmedian(cs.er50)),
            "trades (all variants)": len(recs), "seconds": round(time.time() - t0)}
    print(f"{sym}: {info}", flush=True)
    del m, d
    return pd.DataFrame(recs), info, spreads, pd.DataFrame(floor_recs)


# --------------------------------------------------------------------------- statistics
def streak(r) -> int:
    best = cur = 0
    for x in r:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def max_dd(r) -> float:
    c = np.cumsum(r)
    return float((np.maximum.accumulate(np.r_[0.0, c])[1:] - c).max()) if len(c) else np.nan


def basic(g: pd.DataFrame) -> dict:
    r = g.R.to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    seq = g.sort_values(["exit_ts", "entry_ts"]).R.to_numpy()
    hold = (pd.DatetimeIndex(g.exit_ts) - pd.DatetimeIndex(g.entry_ts)) / pd.Timedelta(days=1)
    n = len(g)
    out = {"trades": n, "win %": (r > 0).mean() * 100 if n else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if n else np.nan, "t": tstat(r),
           "longest losing streak": streak(seq), "max running-R DD": max_dd(seq),
           "avg hold days": float(np.mean(hold)) if n else np.nan,
           "avg hold tdays": float(g.hold_tdays.mean()) if n else np.nan}
    for rs in ("MEAN", "TIME", "SL", "END"):
        out[f"{rs} %"] = (g.reason == rs).mean() * 100 if n else np.nan
    return out


def month_series(g: pd.DataFrame, a, b, col="day") -> pd.Series:
    months = pd.period_range(a, b, freq="M")
    x = g[(pd.DatetimeIndex(g[col]) >= a) & (pd.DatetimeIndex(g[col]) <= b)]
    return x.groupby(pd.DatetimeIndex(x[col]).to_period("M")).R.sum().reindex(months, fill_value=0.0)


def periods():
    p = {k: (pd.Timestamp(a), pd.Timestamp(b)) for k, (a, b) in PER.items()}
    p["last3y"] = L3
    return p


def test_row(g: pd.DataFrame, span, months: int) -> dict:
    row = basic(g)
    row["trades/month"] = len(g) / months if months else np.nan
    day = pd.DatetimeIndex(g.day)
    row["month t (all)"] = tstat(month_series(g, span[0], span[1]).to_numpy())
    for p, (a, b) in periods().items():
        a, b = max(a, span[0]), min(b, span[1])
        x = g[np.asarray((day >= a) & (day <= b))]
        row.update({f"{p} n": len(x), f"{p} avg R": x.R.mean() if len(x) else np.nan, f"{p} t": tstat(x.R.to_numpy()),
                    f"{p} month t": tstat(month_series(x, a, b).to_numpy()) if len(x) else np.nan})
    return row


# --------------------------------------------------------------------------- prop sim
def prop(survivors: list[str]):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    T = pd.read_pickle(f"{OUT}/trades.pkl")
    Tr = namedtuple("Tr", "day entry_i exit_i")
    m, legs = build_legs()
    names = []
    for v in survivors:
        g = T[T.variant == v].copy()
        g["ei"] = ((pd.DatetimeIndex(g.entry_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g["xi"] = ((pd.DatetimeIndex(g.exit_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g = g[g.xi < m.n].sort_values(["xi", "ei"])
        legs.append(([Tr(pd.Timestamp(d), int(a), int(b)) for d, a, b in zip(g.day, g.ei, g.xi)], g.R.to_numpy()))
        names.append(f"{v} ({DESC[v]}) 5 crosses")
    # monthly R correlation (by exit month) with the basket legs
    leg_names = ["vol-box", "vol-gotobi", "fade", "M-3 USDJPY", "M-3 others"] + names
    ms = {}
    for nm, (tr, r) in zip(leg_names, legs):
        idx = pd.DatetimeIndex([m.ts(t.exit_i) for t in tr]).to_period("M")
        ms[nm] = pd.Series(r, index=idx).groupby(level=0).sum()
    M = pd.DataFrame(ms).fillna(0.0)
    CORR = M.corr().loc[leg_names[:5], names] if names else pd.DataFrame()
    base = (0.25, 3, 0.5, 3, 0)
    zero = (0,) * len(base)
    mixes = {"basket": base + (0,) * len(names)}
    for j, nm in enumerate(names):
        mixes[f"basket + {nm} 0.5%"] = base + tuple(0.5 if i == j else 0 for i in range(len(names)))
        mixes[f"{nm} alone 0.5%"] = zero + tuple(0.5 if i == j else 0 for i in range(len(names)))
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
    P.index.name = "mix"
    P.to_csv(f"{OUT}/prop.csv")
    cols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
            "pass eventually %", "median months to pass", "months per funded account", "max DD %"]
    CORR.index.name = "basket leg (monthly R by exit month)"
    txt = ("\n## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)\n\nBasket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + "
           "M-3 USDJPY 3% (run_m3_addon.build_legs); the surviving variant's trades on the 5 crosses added at 0.5% risk "
           "per trade (and alone at 0.5%).\n\n" + fmt_table(P[cols], ".1f") + "\n\n### Correlation of monthly R\n\n"
           + (fmt_table(CORR, ".2f") if len(CORR) else "") + "\n")
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write(txt)
    print(P[cols].round(1).to_string())
    print(CORR.round(2).to_string())
    return P


# --------------------------------------------------------------------------- main
def main(report_only: bool = False):
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    if report_only:
        res = pd.read_pickle(f"{OUT}/raw.pkl")
    else:
        with Pool(2) as pool:
            res = pool.map(run_market, PAIRS, chunksize=1)
        pd.to_pickle(res, f"{OUT}/raw.pkl")
    T = pd.concat([r[0] for r in res], ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T["hold days"] = (pd.DatetimeIndex(T.exit_ts) - pd.DatetimeIndex(T.entry_ts)) / pd.Timedelta(days=1)
    T.to_pickle(f"{OUT}/trades.pkl")
    T.to_csv(f"{OUT}/trades.csv", index=False)
    INFO = pd.DataFrame([r[1] for r in res]).set_index("pair")
    SPR = pd.DataFrame([r[2] for r in res]).set_index("pair")
    FL = pd.concat([r[3] for r in res if len(r[3])], ignore_index=True)
    INFO.to_csv(f"{OUT}/data_info.csv")
    SPR.to_csv(f"{OUT}/spreads.csv")
    first = {s: pd.Timestamp(INFO.loc[s, "first close"]) for s in PAIRS}
    lastc = {s: pd.Timestamp(INFO.loc[s, "last close"]) for s in PAIRS}
    span = (min(first.values()), max(lastc.values()))
    nmon = len(pd.period_range(span[0], span[1], freq="M"))

    # per pair x variant
    rows = []
    for sym in PAIRS:
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            row = test_row(g, (first[sym], lastc[sym]), INFO.loc[sym, "months with data"])
            row["passes bar"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
            rows.append({"pair": sym, "variant": v, **row})
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT}/tests.csv", index=False)

    # pooled per variant (judged)
    prow = []
    for v in VARIANTS:
        g = T[T.variant == v]
        row = test_row(g, span, nmon)
        pm = R[R.variant == v]
        row["pairs avg R > 0"] = int((pm["avg R"] > 0).sum())
        row["pairs passing bar"] = int(pm["passes bar"].sum())
        row["charter bar (pooled)"] = bool(row["design month t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
        row["survives (bar + >=4/5 pairs)"] = bool(row["charter bar (pooled)"] and row["pairs avg R > 0"] >= 4)
        prow.append({"variant": v, "rule": DESC[v], **row})
    PL = pd.DataFrame(prow).set_index("variant")
    PL.to_csv(f"{OUT}/pooled.csv")
    bar = [v for v in VARIANTS if PL.loc[v, "charter bar (pooled)"]]
    surv = [v for v in VARIANTS if PL.loc[v, "survives (bar + >=4/5 pairs)"]]

    # by year
    yr = pd.DatetimeIndex(T.day).year
    YR = T.groupby(["variant", yr]).R.mean().unstack().reindex(list(VARIANTS))
    YRn = T.groupby(["variant", yr]).R.size().unstack().reindex(list(VARIANTS))
    YR.columns = YRn.columns = [str(c) for c in YR.columns]
    YR.index.name = "variant (avg R, 5 pairs)"
    YRn.index.name = "variant (trades, 5 pairs)"
    BY = T.groupby(["market", "variant", yr]).R.agg(["size", "mean", "sum"]).reset_index()
    BY.columns = ["pair", "variant", "year", "trades", "avg R", "sum R"]
    BY.to_csv(f"{OUT}/by_year.csv", index=False)

    def pair_year(v):
        x = T[T.variant == v]
        t = x.groupby(["market", pd.DatetimeIndex(x.day).year]).R.mean().unstack().reindex(PAIRS)
        t.columns = [str(c) for c in t.columns]
        t.index.name = f"{v} avg R"
        return t

    # gross / cost / net, long / short
    T["cost"] = T.R - T.R_gross
    CO = T.groupby("variant").agg(gross=("R_gross", "mean"), cost=("cost", "mean"), net=("R", "mean"),
                                  swap_usd_per_trade=("swap_usd", "mean")).reindex(list(VARIANTS))
    CO.index.name = "variant (avg R per trade; swap $ at 1% risk of $10k)"
    SD = T.groupby(["variant", "side"]).R.agg(["size", "mean"]).unstack("side").reindex(list(VARIANTS))
    SD.columns = [f"{s} {k.replace('size', 'n').replace('mean', 'avg R')}" for k, s in SD.columns]
    SD.index.name = "variant"

    # worst trades
    def worst(v):
        x = T[T.variant == v].nsmallest(5, "R")[["market", "side", "day", "entry_ts", "exit_ts", "reason", "risk_pips",
                                                 "R_gross", "R"]].copy()
        x["day"] = pd.DatetimeIndex(x.day).date
        x.index = range(1, len(x) + 1)
        x.index.name = v
        return x

    # Brexit check
    br = T[(T.market == "EURGBP") & (pd.DatetimeIndex(T.entry_ts) < BREXIT[1]) & (pd.DatetimeIndex(T.exit_ts) > BREXIT[0])]
    BR = br[["variant", "side", "day", "entry_ts", "exit_ts", "entry", "exit", "reason", "risk_pips", "R"]].copy()
    BR["day"] = pd.DatetimeIndex(BR.day).date
    BR = BR.set_index("variant")
    eg16 = T[(T.market == "EURGBP") & (pd.DatetimeIndex(T.day).year == 2016)].groupby("variant").R.agg(
        ["size", "mean", "sum"]).reindex(list(VARIANTS))
    eg16.columns = ["EURGBP 2016 trades", "avg R", "sum R"]
    eg16.index.name = "variant"
    # AUDNZD 2022-23
    an = T[(T.market == "AUDNZD") & (pd.DatetimeIndex(T.day).year.isin([2022, 2023]))]
    AN = an.groupby("variant").agg(trades=("R", "size"), win_pct=("R", lambda x: (x > 0).mean() * 100),
                                   avg_R=("R", "mean"), sum_R=("R", "sum"),
                                   SL_pct=("reason", lambda x: (x == "SL").mean() * 100)).reindex(list(VARIANTS))
    AN.index.name = "variant (AUDNZD 2022-23)"

    # EURCHF floor
    ch = T[T.market == "EURCHF"]
    open_dp = ch[(pd.DatetimeIndex(ch.entry_ts) < pd.Timestamp("2015-01-16")) & (pd.DatetimeIndex(ch.exit_ts) > pd.Timestamp("2015-01-15"))]
    FL.to_csv(f"{OUT}/eurchf_floor.csv", index=False)
    fl_in = FL[(FL.day >= FLOOR[0]) & (FL.day <= FLOOR[1])] if len(FL) else FL
    dp = FL[(pd.DatetimeIndex(FL.entry_ts) <= DEPEG) & (pd.DatetimeIndex(FL.exit_ts) > DEPEG)] if len(FL) else FL
    dday = FL[(pd.DatetimeIndex(FL.entry_ts).normalize() == pd.Timestamp("2015-01-15"))
              | (pd.DatetimeIndex(FL.exit_ts).normalize() == pd.Timestamp("2015-01-15"))] if len(FL) else FL
    post = ch[(ch.day > FLOOR[1]) & (ch.day <= pd.Timestamp("2015-03-31"))]
    POST = post.groupby("variant").R.agg(["size", "mean", "sum"]).reindex(list(VARIANTS))
    POST.columns = ["trades 2015-01-16..03-31", "avg R", "sum R"]
    POST.index.name = "variant (EURCHF)"
    ch_ex = ch[~((ch.day > FLOOR[1]) & (ch.day <= pd.Timestamp("2015-03-31")))]
    POST["EURCHF avg R all"] = ch.groupby("variant").R.mean().reindex(list(VARIANTS))
    POST["EURCHF avg R excl. these"] = ch_ex.groupby("variant").R.mean().reindex(list(VARIANTS))

    # ------------------------------------------------------------------ report
    n_tests = len(VARIANTS)
    pcols = ["rule", "trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t (all)",
             "design n", "design avg R", "design t", "design month t", "check n", "check avg R", "check t",
             "check month t", "holdout n", "holdout avg R", "holdout t", "holdout month t", "last3y n", "last3y avg R",
             "last3y t", "pairs avg R > 0", "pairs passing bar", "avg hold days", "avg hold tdays", "MEAN %", "TIME %",
             "SL %", "END %", "longest losing streak", "max running-R DD", "charter bar (pooled)",
             "survives (bar + >=4/5 pairs)"]
    mcols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t (all)", "design n",
             "design avg R", "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t",
             "last3y n", "last3y avg R", "last3y t", "avg hold days", "MEAN %", "TIME %", "SL %", "longest losing streak",
             "max running-R DD", "passes bar"]

    def mtab(v):
        x = R[R.variant == v].set_index("pair")[mcols].copy()
        x.index.name = "pair"
        return fmt_table(x, ".3f")

    heat = R.pivot(index="pair", columns="variant", values="avg R").reindex(PAIRS)
    heat.index.name = "avg R 2010-26"
    heat_l3 = R.pivot(index="pair", columns="variant", values="last3y avg R").reindex(PAIRS)
    heat_l3.index.name = "last-3y avg R"
    heat_d = R.pivot(index="pair", columns="variant", values="design t").reindex(PAIRS)
    heat_d.index.name = "design t (trade level)"
    pm_pass = R[R["passes bar"]]
    s_bar = ", ".join(f"{v} ({DESC[v]})" for v in bar) or "none"
    s_list = ", ".join(f"{v} ({DESC[v]})" for v in surv) or "none"
    best = PL.sort_values("design month t", ascending=False).index[0]
    txt = ["# Alpha hunt: range-bound crosses, daily z-score fade (`cross_zfade`)\n",
           "Rules, variants and the survival bar are in the docstring of `run_alpha_cross_zfade.py` (fixed before running). "
           "5 crosses (AUDNZD, EURGBP, AUDCAD, NZDCAD, EURCHF excluding entries 2011-09-06..2015-01-15), signal = bid close "
           "of the 16:44 NY minute, market entry and non-stop exits at the 16:45 NY open, SL 1.5 x ATR20 (Z9 2.5), "
           "exit on the z-score crossing 0 or a 10 / 20 trading-day time stop. All costs included ($7/lot, 0.2 pip on the "
           "entry and stop exits, FRED swap with 1%/yr markup). Periods by signal day: design 2010-17, check 2018-23, "
           "holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.\n",
           f"**Judged tests: {n_tests} (pooled 5-pair result per variant). Charter bar on the pooled result (design "
           f"month-clustered t >= 2, check and holdout avg R > 0): {len(bar)} ({s_bar}). Survivors (bar AND >= 4 of 5 pairs "
           f"with avg R > 0): {len(surv)} ({s_list}). Expected by luck: {n_tests * 0.006:.2f}.**\n",
           f"Per-pair tests (information only): {len(R)}; passing the charter bar: {len(pm_pass)} "
           f"({', '.join(f'{a} {b}' for a, b in zip(pm_pass.pair, pm_pass.variant)) or 'none'}); expected by luck "
           f"{len(R) * 0.006:.2f}.\n",
           f"Best pooled design month t: {best} ({DESC[best]}) {PL.loc[best, 'design month t']:.2f}.\n",
           "## Pooled, 5 pairs (the judged tests)\n",
           "month t = month-clustered t (sum of R per calendar month of the signal day, zero for months without trades, t "
           "over months); t = trade-level. avg hold days = calendar days; tdays = trading days (closes). Exit mix: MEAN = "
           "z back through 0, TIME = time stop, SL = stop, END = end of data. max running-R DD = deepest drop of the "
           "cumulative R of all pooled trades in exit order.\n",
           fmt_table(PL[pcols], ".3f"), "\n",
           "## Avg R per pair x variant (2010-2026)\n", fmt_table(heat, ".3f"), "\n",
           "## Design-period t per pair x variant (trade level)\n", fmt_table(heat_d, ".2f"), "\n",
           "## Last-3-year avg R per pair x variant\n", fmt_table(heat_l3, ".3f"), "\n",
           "## Avg R per signal year, pooled\n", fmt_table(YR, ".3f"), "\n",
           "### Trades per signal year, pooled\n", fmt_table(YRn, ".0f"), "\n",
           "## Avg R per pair per year: Z1 (no filter) and Z5 (ER filter)\n", fmt_table(pair_year("Z1"), ".2f"), "\n",
           fmt_table(pair_year("Z5"), ".2f"), "\n",
           "## Gross vs cost vs net (avg R per trade)\n", fmt_table(CO, ".3f"), "\n",
           "## Long vs short\n", fmt_table(SD, ".3f"), "\n",
           "## Worst 5 trades per variant (net R)\n"]
    for v in VARIANTS:
        txt += [f"### {v}: {DESC[v]}\n", fmt_table(worst(v), ".3f"), "\n"]
    txt += ["## Regime checks\n",
            "### EURGBP trades open around the Brexit result (2016-06-23 21:00 .. 2016-06-24 21:00 UTC)\n",
            (fmt_table(BR, ".4f") if len(BR) else "None of the 9 variants had an EURGBP position open in that window.") + "\n",
            fmt_table(eg16, ".3f"), "\n",
            "### AUDNZD 2022-23 (signal days)\n", fmt_table(AN, ".3f"), "\n",
            "### EURCHF and the SNB floor\n",
            f"Open EURCHF exposure on 2015-01-15 across the 9 variants (with the pre-declared floor exclusion): "
            f"{len(open_dp)} trade(s).\n",
            "Illustration only (not part of any test): Z1 run on EURCHF without the floor exclusion. "
            + (f"Trades with signal days in the floor window: {len(fl_in)}, avg R {fl_in.R.mean():.3f}, sum R {fl_in.R.sum():.2f} "
               f"(SL {(fl_in.reason == 'SL').mean() * 100:.0f}%). " if len(fl_in) else "")
            + (f"Trade(s) open at the de-peg (2015-01-15 09:30 UTC): "
               + "; ".join(f"{r.side} from {pd.Timestamp(r.entry_ts)} at {r.entry:.5f}, SL {r.risk_pips:.1f} pips, exit "
                           f"{pd.Timestamp(r.exit_ts)} at {r.exit:.5f} ({r.reason}), R {r.R:.2f}" for r in dp.itertuples())
               if len(dp) else "No Z1 trade would have been open at the de-peg.")
            + (" Z1 trades entered or exited on 2015-01-15 (NY 16:45 entry, after the crash): "
               + "; ".join(f"{r.side} at {pd.Timestamp(r.entry_ts)} UTC at {r.entry:.5f} (z {r.z:.2f}), SL {r.risk_pips:.1f} pips "
                           f"(ATR20 from the floor period), exit {pd.Timestamp(r.exit_ts)} at {r.exit:.5f} ({r.reason}), "
                           f"R {r.R:.2f}" for r in dday.itertuples()) if len(dday) else "") + "\n",
            "Diagnostic: EURCHF trades with signal days 2015-01-16..2015-03-31 (z windows still contain floor prices; "
            "kept in all results as pre-declared).\n", fmt_table(POST, ".3f"), "\n",
            "## Rollover-spread check (16:45 NY entry minute vs 12:00 NY, same days, pips)\n", fmt_table(SPR, ".3f"), "\n",
            "## Data used\n", fmt_table(INFO, ".3f"), "\n",
            "## Per pair, by variant\n"]
    for v in VARIANTS:
        txt += [f"### {v}: {DESC[v]}\n", mtab(v), "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(PL[["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "design avg R", "design month t",
              "check avg R", "holdout avg R", "last3y avg R", "pairs avg R > 0", "SL %", "charter bar (pooled)",
              "survives (bar + >=4/5 pairs)"]].round(3).to_string())
    print(heat.round(3).to_string())
    print(SPR.round(2).to_string())
    print("charter bar:", s_bar, "| survivors:", s_list, flush=True)
    print(f"main done in {time.time() - t_start:.0f}s", flush=True)
    if surv:
        prop(surv)
    print("DONE", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prop":
        PLs = pd.read_csv(f"{OUT}/pooled.csv")
        s = PLs[PLs["survives (bar + >=4/5 pairs)"]].variant.tolist()
        prop(s)
        print("DONE", flush=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        main(report_only=True)                     # rebuild the report from raw.pkl (no rule changes)
    else:
        main()
