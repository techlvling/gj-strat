"""Alpha hunt family `index_vol_timing`: volatility-managed index premium with variance-risk-premium (VRP)
and VIX term-structure timing. Long-only portfolio weights, rebalanced monthly (P5 / P6 also act daily).
Every rule below was fixed BEFORE the first run.

IDEA: index returns do not rise one-for-one with volatility at monthly horizons, so scaling exposure by
inverse realized variance raises Sharpe and cuts the left tail (Moreira & Muir 2017 JF; Fleming, Kirby &
Ostdiek 2001; Harvey et al. 2018 JPM). Critiques (Cederburg et al. 2020 JFE; Liu, Tang & Zhou 2019) say
out-of-sample gains are smaller, so the constants come from theory, not the data: 16% vol target, weight
cap 2. A high VRP predicts higher index returns and a negative VRP marks a crisis in progress
(Bollerslev, Tauchen & Zhou 2009 RFS; Bekaert & Hoerova 2014). VIX backwardation (VIX >= VIX3M) marks
stress regimes. Prop use: a steady long-index leg whose exposure shrinks in the volatility clusters that
breach the 5% daily / 10% static rules.

MARKETS: USATECHIDXUSD (Nasdaq 100, minute bid/ask), JPNIDXJPY (Nikkei 225, minute bid/ask),
USA500IDXUSD (S&P 500, hourly bid candles). Loaded one at a time and deleted; single process.

CALENDARS: Nasdaq and S&P on NYSE trading days (holidays.NYSE); Nikkei on Japan holidays + Dec 31 +
Jan 2-3 (as run_alpha_index_meanrev / run_index_replication).

DAILY CLOSE SERIES (one close per trading day, DST-aware via gjstrat.patterns.local_idx):
  * Nasdaq: C = bid close of the 15:54 New York minute.
  * Nikkei: C = bid close of the 14:54 Asia/Tokyo minute, 15:24 from 2024-11-05 (TSE close moved).
  * S&P: C = close of the 15:00-16:00 NY hourly bar.
  * r_t = C_t / C_{t-1} - 1 between consecutive closes of the series.

PORTFOLIO ACCOUNTING: weight w = notional / equity, held from close to close.
  daily net return_t = w_{t-1} * r_t - w_{t-1} * 0.03 * (calendar days between the two closes) / 365
                       - |dw_t| * cost_t / C_t        (dw_t = weight change made at close t)
  cost_t (index points per unit of notional traded) = half the bid/ask spread at the signal minute +
  slippage (Nasdaq 0.25 pt, Nikkei 2.0 pt); S&P 0.5 pt. Monthly return = compounded daily net returns
  of the closes dated in that calendar month.

INPUTS (only data available at the signal close):
  * RV21_t = (sum of the last 21 r^2, including r_t) * 252/21, from the market's own returns (Moreira-Muir).
  * VIX, VXV = latest FRED VIXCLS / VXVCLS value dated strictly before the signal's local date (NY date
    for Nasdaq and S&P, Tokyo date for the Nikkei). Files data/extra/VIXCLS.csv, VXVCLS.csv.
  * VRP_t = (VIX/100)^2 - RV21 of the S&P. Where VRP is missing, P3 / P4 fall back to P2.

REBALANCE: monthly, at the signal close of the last trading day of the month using that day's data
(P5 / P6: see below).

VARIANTS (P0 = benchmark only, not a candidate; P1-P6 = 6 candidates):
  P0  buy-and-hold, w = 1.
  P1  w = min(2, 0.16^2 / RV21).
  P2  w = min(2, 0.16 / sqrt(RV21)).
  P3  P2, but w = 0 if VRP < 0.
  P4  P2 x 1.5 if VRP is in the top tercile of its previous 36 month-end values (>= 24 required),
      x 0.5 if in the bottom tercile, else x 1; cap 2. (Top: VRP > 2/3 quantile of those values;
      bottom: VRP < 1/3 quantile; numpy linear quantiles. Fewer than 24 values -> x 1.)
  P5  P2 target min(2, 0.16/sqrt(RV21)) recomputed at every daily close; trade (to the target) only when
      |w_target - w| / w > 0.25 (cost control).
  P6  P2 with a daily regime check: w = 0 while VIX/VXV >= 1 (backwardation); back to the current P2
      monthly weight once VIX/VXV < 1. The P2 weight is still recomputed at each month-end close.

REPORT per market x variant x period (design = data start-2017, check 2018-23, holdout 2024-26, as
run_edge_hunt.PER; plus last 3 years = months 2023-10..2026-09):
  monthly net return mean (%) and t; annualized Sharpe (mean/sd * sqrt 12); max drawdown of the daily
  equity curve; worst day %; worst month %; mean w (average w_{t-1} over days); turnover (sum |dw| per
  year); win % of months; avg winning / avg losing month; P_k - P0 monthly difference with t;
  Moreira-Muir alpha = OLS intercept of P_k monthly returns on P0 monthly returns, with its t.
  Prop view: scale s at which the worst historical day (whole sample) = -2.5% of equity, monthly mean
  at that scale (daily net returns x s, compounded), and the share of rolling 12-month windows (12
  consecutive included months, by start month) whose equity path at scale s touches -10% of its start.
  Also: pooled view (equal-weight average of the markets' monthly returns per month) and the count of
  markets positive; returns by year.

SURVIVAL (a candidate = market x P1..P6 needs both):
  (a) charter bar on its monthly net return series, each month = one trade: design t >= 2, mean > 0 in
      check and in holdout;
  (b) P_k - P0 mean monthly difference > 0 in check and in holdout (timing adds value over buy-and-hold).
  18 tests (6 candidates x 3 markets); at ~0.6% per test luck gives about 0.1 survivors.

FIXES OF OBVIOUS IMPOSSIBILITIES (decided before running; none changes a rule's intent):
  1. A day enters a minute market's close series only if the signal minute has ticks (vol > 0). The spec
     states this for the Nikkei; applied to the Nasdaq too because a forward-filled close is stale.
     S&P: only hourly bars with ticks (v > 0); the hourly files contain flat zero-volume bars.
  2. Data gaps: when more than 5 trading days in a row are missing (Nasdaq 2011-12 and Feb-May 2013,
     Nikkei 2011-12, Feb-May 2013 and most of 2015, S&P 2013), the series is split into segments: a
     "daily" return spanning months is not a daily return. RV21 is computed within a segment (warm-up
     restarts), every variant (P0 included) is flat outside segments, starts at the first month-end
     close of a segment with a valid RV21 and closes at the segment's last close (cost charged). A month
     counts only if the previous month-end close and its own month-end close lie in the same segment,
     the portfolio was invested after the previous one, and the segment continues after the month (so
     partial months at gaps and the unfinished 2026-10 are left out). All variants of a market share
     the same months.
  3. "Last trading day of the month" = last close available in the month (a day without ticks at the
     signal minute cannot be traded).
  4. VRP timing (the spec gives none): the S&P RV21 is taken at the latest S&P close at or before the
     signal time (the Nasdaq's 15:55 NY signal comes before the S&P's 16:00 close, so it uses the
     previous S&P close; the Nikkei uses the previous NY close; the S&P uses its own close). An S&P close
     older than 7 calendar days -> VRP missing (S&P data gaps). VRP history for P4 = VRP evaluated the
     same way at the signal time of the last calendar trading day of each of the previous 36 months
     (needs no close of the traded market, so gap months still have a value if the S&P has one).
  5. Spread: where the signal-minute ask is missing (ask - bid <= 0, Nasdaq / Nikkei 2011-2012), half
     the median positive signal-minute spread of the market's first 250 closes with a positive spread
     is used instead of zero.

OUTPUTS: results/alpha_hunt/index_vol_timing/ tests.csv (market x variant x period), monthly.csv,
daily.csv.gz, pooled.csv, by_year.csv, diagnostics.csv, tables.md (REPORT.md is written from these).

    python run_alpha_index_vol_timing.py
"""
from __future__ import annotations

import glob
import lzma
import os
import time
from datetime import date

import holidays
import numpy as np
import pandas as pd

from gjstrat.data import CANDLE_DTYPE, load_market
from gjstrat.patterns import NY, local_idx
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/index_vol_timing"
TKY = "Asia/Tokyo"
NIK_SWITCH = pd.Timestamp("2024-11-05")
GAP = 5
FIN = 0.03
TARGET, CAP = 0.16, 2.0
L3 = (pd.Period("2023-10", "M"), pd.Period("2026-09", "M"))
VARS = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
CANDS = VARS[1:]
DESC = {
    "P0": "buy-and-hold w=1 (benchmark)",
    "P1": "min(2, 0.16^2/RV21) monthly",
    "P2": "min(2, 0.16/sqrt(RV21)) monthly",
    "P3": "P2, w=0 if VRP<0",
    "P4": "P2 x1.5/x0.5 by VRP tercile (36m)",
    "P5": "P2 target daily, trade if |dw|/w>0.25",
    "P6": "P2, w=0 while VIX/VXV>=1 (daily)",
}
MINUTE = {
    "USATECHIDXUSD": dict(path="data/usatechidxusd_2011-01-02_2026-10-07.npz", tz=NY, cal="nyse", slip=0.25),
    "JPNIDXJPY": dict(path="data/jpnidxjpy_2011-01-02_2026-10-07.npz", tz=TKY, cal="japan", slip=2.0),
}
NAMES = {"USATECHIDXUSD": "Nasdaq 100", "JPNIDXJPY": "Nikkei 225", "USA500IDXUSD": "S&P 500"}
ORDER = ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY"]


# --------------------------------------------------------------------------- calendars / FRED
def calendar(kind: str, a: pd.Timestamp, b: pd.Timestamp) -> pd.DatetimeIndex:
    days = pd.bdate_range(a.normalize(), b.normalize())
    yrs = range(a.year, b.year + 1)
    if kind == "nyse":
        hol = set(holidays.NYSE(years=yrs))
    else:
        hol = set(holidays.Japan(years=yrs)) | {date(y, 12, 31) for y in yrs} | {date(y, 1, k) for y in yrs for k in (2, 3)}
    return pd.DatetimeIndex([d for d in days if d.date() not in hol])


def fred(name: str) -> pd.Series:
    df = pd.read_csv(f"data/extra/{name}.csv", parse_dates=["observation_date"])
    return pd.Series(pd.to_numeric(df[name], errors="coerce").to_numpy(), index=df["observation_date"]).dropna()


def before(s: pd.Series, days) -> np.ndarray:
    """Latest value of s dated strictly before each local date."""
    days = pd.DatetimeIndex(days).normalize()
    p = np.searchsorted(s.index.values, days.values, side="left") - 1
    return np.where(p >= 0, s.to_numpy()[np.maximum(p, 0)], np.nan)


def sig_hm(sym: str, day: pd.Timestamp) -> tuple[int, int]:
    if sym == "USATECHIDXUSD":
        return 15, 54
    if sym == "JPNIDXJPY":
        return (14, 54) if day < NIK_SWITCH else (15, 24)
    return 15, 0                                   # S&P: hourly bar 15:00-16:00 NY


def sig_ts(sym: str, days: pd.DatetimeIndex) -> np.ndarray:
    """UTC time at which the signal close is known (end of the signal minute / hourly bar)."""
    tz = TKY if sym == "JPNIDXJPY" else NY
    out = []
    for d in days:
        hh, mm = sig_hm(sym, d)
        step = 60 if sym == "USA500IDXUSD" else 1
        t = (d + pd.Timedelta(hours=hh, minutes=mm + step)).tz_localize(tz).tz_convert("UTC").tz_localize(None)
        out.append(t)
    return pd.DatetimeIndex(out).values


# --------------------------------------------------------------------------- close series
def minute_closes(sym: str):
    cfg = MINUTE[sym]
    t0 = time.time()
    m = load_market(cfg["path"])
    cal = calendar(cfg["cal"], m.t0 + pd.Timedelta(days=1), m.ts(m.n - 1))
    rows = []
    for day in cal:
        hh, mm = sig_hm(sym, day)
        i = local_idx(m, day, hh, mm, cfg["tz"])
        if i < 0 or i >= m.n - 1 or not m.vol[i] > 0:
            continue
        rows.append((day, float(m.bc[i]), float(m.ac[i] - m.bc[i]), m.ts(i + 1)))
    del m
    cs = pd.DataFrame(rows, columns=["day", "C", "spread", "ts"]).set_index("day")
    pos = cs.spread[cs.spread > 0].iloc[:250]
    fallback = float(pos.median())
    cs["spread_used"] = np.where(cs.spread > 0, cs.spread, fallback)
    cs["cost"] = cs.spread_used / 2 + cfg["slip"]
    print(f"{sym}: {len(cs)} closes, spread fallback {fallback:.3f} on {(cs.spread <= 0).sum()} days, "
          f"{time.time() - t0:.0f}s", flush=True)
    return cs[["C", "ts", "cost", "spread"]], cal, fallback


def spx_closes():
    parts = []
    for f in sorted(glob.glob("data/hourly/USA500IDXUSD/*.bi5")):
        y, mth = map(int, os.path.basename(f)[:-4].split("_"))
        raw = open(f, "rb").read()
        if not raw:
            continue
        rec = np.frombuffer(lzma.decompress(raw), dtype=CANDLE_DTYPE)
        t0 = pd.Timestamp(year=y, month=mth, day=1)
        idx = t0 + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
        parts.append(pd.DataFrame({"c": rec["c"] / 1000.0, "v": rec["v"].astype(float)}, index=idx))
    b = pd.concat(parts).sort_index()
    b = b[~b.index.duplicated()]
    b = b[b.v > 0]
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    sel = loc.hour == 15
    cs = pd.DataFrame({"C": b.c.to_numpy()[sel], "ts": b.index[sel] + pd.Timedelta(hours=1)},
                      index=loc[sel].normalize())
    cs = cs[~cs.index.duplicated()]
    cal = calendar("nyse", pd.Timestamp("2012-01-01"), pd.Timestamp("2026-10-07"))
    cs = cs[cs.index.isin(cal)]
    cs.index.name = "day"
    cs["cost"] = 0.5
    cs["spread"] = np.nan
    print(f"USA500IDXUSD: {len(cs)} closes", flush=True)
    return cs, cal


def prep(cs: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """Segments, returns, calendar days and RV21 (all within segments)."""
    cs = cs.copy()
    pos = cal.get_indexer(cs.index)
    assert (pos >= 0).all()
    gap = np.diff(pos, prepend=pos[0] - 1) - 1
    cs["seg"] = np.cumsum(gap > GAP)
    g = cs.groupby("seg", sort=True)
    cs["r"] = g["C"].pct_change()
    dd = pd.Series(cs.index, index=cs.index)
    cs["cd"] = (dd - dd.groupby(cs["seg"]).shift(1)).dt.days.to_numpy()
    cs["rv21"] = (cs["r"] ** 2).groupby(cs["seg"]).transform(lambda x: x.rolling(21).sum() * 252 / 21)
    return cs


# --------------------------------------------------------------------------- VRP / regime inputs
class SpxRV:
    def __init__(self, spx: pd.DataFrame):
        ok = spx["rv21"].notna()
        self.ts = spx.loc[ok, "ts"].values
        self.rv = spx.loc[ok, "rv21"].to_numpy()

    def at(self, t_utc: np.ndarray) -> np.ndarray:
        p = np.searchsorted(self.ts, t_utc, side="right") - 1
        rv = np.where(p >= 0, self.rv[np.maximum(p, 0)], np.nan)
        age = (t_utc - self.ts[np.maximum(p, 0)]) / np.timedelta64(1, "D")
        return np.where((p >= 0) & (age <= 7), rv, np.nan)


def add_inputs(sym, cs, cal, vix, vxv, spxrv: SpxRV):
    cs = cs.copy()
    v = before(vix, cs.index)
    cs["vix"] = v
    cs["vxv"] = before(vxv, cs.index)
    cs["vrp"] = (v / 100) ** 2 - spxrv.at(cs["ts"].values)
    # month-end VRP history on the market calendar (signal time of the last calendar trading day)
    s = pd.Series(cal, index=cal)
    last = pd.DatetimeIndex(s.groupby(cal.to_period("M")).max().to_numpy())
    hv = (before(vix, last) / 100) ** 2 - spxrv.at(sig_ts(sym, last))
    hist = pd.Series(hv, index=last.to_period("M"))
    return cs, hist


def p4_mult(cs: pd.DataFrame, hist: pd.Series) -> np.ndarray:
    mult = np.ones(len(cs))
    per = cs.index.to_period("M")
    for j in range(len(cs)):
        x = cs["vrp"].iat[j]
        if not np.isfinite(x):
            continue
        k = per[j]
        prev = hist.reindex(pd.period_range(k - 36, k - 1, freq="M")).dropna().to_numpy()
        if len(prev) < 24:
            continue
        lo, hi = np.quantile(prev, [1 / 3, 2 / 3])
        mult[j] = 1.5 if x > hi else (0.5 if x < lo else 1.0)
    return mult


# --------------------------------------------------------------------------- simulation
def simulate(cs: pd.DataFrame, mult4: np.ndarray) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    n = len(cs)
    seg = cs["seg"].to_numpy()
    per = cs.index.to_period("M")
    is_me = np.r_[per[:-1] != per[1:], True]
    seg_last = np.r_[seg[:-1] != seg[1:], True]
    rv = cs["rv21"].to_numpy()
    r = cs["r"].to_numpy()
    cd = cs["cd"].to_numpy()
    C = cs["C"].to_numpy()
    cost = cs["cost"].to_numpy()
    vrp = cs["vrp"].to_numpy()
    ratio = cs["vix"].to_numpy() / cs["vxv"].to_numpy()
    p2 = np.minimum(CAP, TARGET / np.sqrt(rv))
    p1 = np.minimum(CAP, TARGET ** 2 / rv)
    # activation: first month-end close of each segment with valid RV21
    act = np.zeros(n, bool)                    # strategy invested after close j (if not segment end)
    first_act = {}
    for j in range(n):
        if seg[j] not in first_act and is_me[j] and np.isfinite(rv[j]) and not seg_last[j]:
            first_act[seg[j]] = j
        act[j] = seg[j] in first_act
    out = {}
    for v in VARS:
        w = 0.0
        base = 0.0
        rows = np.zeros((n, 6))
        for j in range(n):
            if j > 0 and seg[j] == seg[j - 1] and w != 0.0:
                gross, fin = w * r[j], w * FIN * cd[j] / 365
            else:
                gross = fin = 0.0
            if seg_last[j] or not act[j]:
                wn = 0.0
            elif v == "P0":
                wn = 1.0
            elif v == "P1":
                wn = p1[j] if is_me[j] else w
            elif v == "P2":
                wn = p2[j] if is_me[j] else w
            elif v == "P3":
                wn = (0.0 if (np.isfinite(vrp[j]) and vrp[j] < 0) else p2[j]) if is_me[j] else w
            elif v == "P4":
                wn = min(CAP, p2[j] * mult4[j]) if is_me[j] else w
            elif v == "P5":
                tgt = p2[j]
                wn = tgt if (w == 0.0 or abs(tgt - w) / w > 0.25) else w
            else:  # P6
                if is_me[j]:
                    base = p2[j]
                wn = 0.0 if (np.isfinite(ratio[j]) and ratio[j] >= 1) else base
            c = abs(wn - w) * cost[j] / C[j]
            rows[j] = (w, wn, gross, fin, c, gross - fin - c)
            w = wn
        out[v] = pd.DataFrame(rows, columns=["w_prev", "w", "gross", "fin", "cost", "net"], index=cs.index)
    # included months
    me = np.flatnonzero(is_me)
    inc = []
    for a, b in zip(me[:-1], me[1:]):
        if seg[a] == seg[b] and act[a] and not seg_last[a] and not seg_last[b]:
            inc.append((per[b], a, b))
    months = pd.DataFrame(inc, columns=["month", "a", "b"])
    return out, months


def monthly(daily: pd.DataFrame, months: pd.DataFrame, scale: float = 1.0) -> pd.Series:
    net = daily["net"].to_numpy() * scale
    vals = [np.prod(1 + net[a + 1:b + 1]) - 1 for a, b in zip(months.a, months.b)]
    return pd.Series(vals, index=pd.PeriodIndex(months.month, freq="M"))


def period_of(p: pd.PeriodIndex) -> np.ndarray:
    ts = p.to_timestamp()
    lab = np.full(len(p), "", dtype=object)
    for k, (a, b) in PER.items():
        lab[(ts >= pd.Timestamp(a)) & (ts <= pd.Timestamp(b))] = k
    return lab


def maxdd(net: np.ndarray) -> float:
    eq = np.r_[1.0, np.cumprod(1 + net)]
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def ols_alpha(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float]:
    if len(y) < 4:
        return np.nan, np.nan, np.nan
    X = np.c_[np.ones(len(x)), x]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    s2 = e @ e / (len(y) - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta[0], beta[0] / np.sqrt(cov[0, 0]), beta[1]


def windows12(daily: pd.DataFrame, months: pd.DataFrame, scale: float) -> pd.Series:
    """For each start month with 12 consecutive included months: does equity at `scale` touch -10%?"""
    net = daily["net"].to_numpy() * scale
    mp = pd.PeriodIndex(months.month, freq="M")
    pos = {p: k for k, p in enumerate(mp)}
    res = {}
    for k, p in enumerate(mp):
        last = p + 11
        if last not in pos or pos[last] - k != 11:
            continue
        a, b = months.a.iat[k], months.b.iat[pos[last]]
        eq = np.cumprod(1 + net[a + 1:b + 1])
        res[p] = bool(eq.min() <= 0.90)
    return pd.Series(list(res.values()), index=pd.PeriodIndex(list(res.keys()), freq="M"), dtype=bool)


def stats_block(sym, v, daily, months, M, M0, s_prop):
    """Rows for every period (+ all, last3y)."""
    lab = period_of(M.index)
    day_month = daily.index.to_period("M")
    inc_days = np.zeros(len(daily), bool)
    for a, b in zip(months.a, months.b):
        inc_days[a + 1:b + 1] = True
    Ms = monthly(daily, months, s_prop)
    W = windows12(daily, months, s_prop)
    wlab = period_of(W.index) if len(W) else np.array([])
    rows = []
    sets = [(k, lab == k) for k in PER] + [("all", np.ones(len(M), bool)),
                                          ("last3y", (M.index >= L3[0]) & (M.index <= L3[1]))]
    for pname, sel in sets:
        mm = M.index[sel]
        x = M.to_numpy()[sel]
        x0 = M0.to_numpy()[sel]
        dmask = inc_days & np.asarray(day_month.isin(mm))
        dn = daily["net"].to_numpy()[dmask]
        dw = np.abs(daily["w"].to_numpy() - daily["w_prev"].to_numpy())[dmask]
        wins, losses = x[x > 0], x[x < 0]
        a, at, beta = ols_alpha(x, x0) if v != "P0" else (np.nan, np.nan, 1.0)   # P0 on itself is degenerate
        if pname in PER:
            wsel = wlab == pname
        elif pname == "all":
            wsel = np.ones(len(W), bool)
        else:
            wsel = (W.index >= L3[0]) & (W.index <= L3[1]) if len(W) else np.array([], bool)
        rows.append({
            "market": sym, "variant": v, "period": pname, "months": len(x),
            "first": str(mm.min()) if len(mm) else "", "last": str(mm.max()) if len(mm) else "",
            "mean %": x.mean() * 100 if len(x) else np.nan, "t": tstat(x),
            "sharpe": x.mean() / x.std(ddof=1) * np.sqrt(12) if len(x) > 1 else np.nan,
            "win %": (x > 0).mean() * 100 if len(x) else np.nan,
            "avg win %": wins.mean() * 100 if len(wins) else np.nan,
            "avg loss %": losses.mean() * 100 if len(losses) else np.nan,
            "win/loss": wins.mean() / -losses.mean() if len(wins) and len(losses) else np.nan,
            "maxDD %": maxdd(dn) * 100 if len(dn) else np.nan,
            "worst day %": dn.min() * 100 if len(dn) else np.nan,
            "worst month %": x.min() * 100 if len(x) else np.nan,
            "mean w": daily["w_prev"].to_numpy()[dmask].mean() if dmask.any() else np.nan,
            "turnover/yr": dw.sum() * 12 / len(x) if len(x) else np.nan,
            "rebal/month": (dw > 1e-12).sum() / len(x) if len(x) else np.nan,
            "cost %/yr": daily["cost"].to_numpy()[dmask].sum() * 12 / len(x) * 100 if len(x) else np.nan,
            "fin %/yr": daily["fin"].to_numpy()[dmask].sum() * 12 / len(x) * 100 if len(x) else np.nan,
            "diff vs P0 %": (x - x0).mean() * 100 if len(x) else np.nan, "diff t": tstat(x - x0),
            "MM alpha %": a * 100, "MM alpha t": at, "beta": beta,
            "prop s": s_prop, "prop mean % at s": Ms.to_numpy()[sel].mean() * 100 if len(x) else np.nan,
            "12m windows": int(wsel.sum()) if len(W) else 0,
            "12m touch -10% share": W.to_numpy()[wsel].mean() if len(W) and wsel.any() else np.nan,
        })
    return rows


# --------------------------------------------------------------------------- main
def run_market(sym, cs, cal, vix, vxv, spxrv):
    cs = prep(cs, cal)
    cs, hist = add_inputs(sym, cs, cal, vix, vxv, spxrv)
    mult4 = p4_mult(cs, hist)
    daily, months = simulate(cs, mult4)
    M = {v: monthly(daily[v], months) for v in VARS}
    rows = []
    inc_days = np.zeros(len(cs), bool)
    for a, b in zip(months.a, months.b):
        inc_days[a + 1:b + 1] = True
    for v in VARS:
        worst = daily[v]["net"].to_numpy()[inc_days].min()
        s_prop = 0.025 / -worst if worst < 0 else np.nan
        rows += stats_block(sym, v, daily[v], months, M[v], M["P0"], s_prop)
    # diagnostics (month-end values on included months' rebalance closes)
    me_rows = cs.iloc[months.b.to_numpy()]
    m4 = mult4[months.b.to_numpy()]
    diag = {"market": sym, "closes": len(cs), "segments": cs.seg.nunique(), "months": len(months),
            "first month": str(months.month.min()), "last month": str(months.month.max()),
            "VRP missing % (month-ends)": me_rows.vrp.isna().mean() * 100,
            "VRP<0 % (month-ends)": (me_rows.vrp < 0).mean() * 100,
            "P4 x1.5 %": (m4 == 1.5).mean() * 100, "P4 x0.5 %": (m4 == 0.5).mean() * 100,
            "backwardation % of days": (cs.vix / cs.vxv >= 1)[inc_days].mean() * 100,
            "median RV21 vol %": np.sqrt(cs.rv21[inc_days]).median() * 100,
            "median cost bp": (cs.cost / cs.C)[inc_days].median() * 1e4}
    mon = pd.DataFrame({v: M[v] for v in VARS})
    mon.insert(0, "market", sym)
    dl = []
    for v in VARS:
        x = daily[v].copy()
        x["inc"] = inc_days
        x.insert(0, "variant", v)
        x.insert(0, "market", sym)
        dl.append(x)
    dl = pd.concat(dl)
    dl["vrp"] = np.tile(cs.vrp.to_numpy(), len(VARS))
    dl["vix/vxv"] = np.tile((cs.vix / cs.vxv).to_numpy(), len(VARS))
    dl["rv21"] = np.tile(cs.rv21.to_numpy(), len(VARS))
    print(f"{sym}: {len(months)} months {months.month.min()}..{months.month.max()}", flush=True)
    return rows, mon, dl, diag


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    vix, vxv = fred("VIXCLS"), fred("VXVCLS")
    spx, spx_cal = spx_closes()
    spx_p = prep(spx, spx_cal)
    spxrv = SpxRV(spx_p)
    rows, mons, dls, diags = [], [], [], []
    for sym in ORDER:
        if sym == "USA500IDXUSD":
            cs, cal = spx, spx_cal
        else:
            cs, cal, _ = minute_closes(sym)
        r_, m_, d_, g_ = run_market(sym, cs, cal, vix, vxv, spxrv)
        rows += r_
        mons.append(m_)
        dls.append(d_)
        diags.append(g_)
    T = pd.DataFrame(rows)
    MON = pd.concat(mons)
    MON.index.name = "month"
    DL = pd.concat(dls)
    DG = pd.DataFrame(diags)
    T.to_csv(f"{OUT}/tests_long.csv", index=False)
    MON.to_csv(f"{OUT}/monthly.csv")
    DL.to_csv(f"{OUT}/daily.csv.gz")
    DG.to_csv(f"{OUT}/diagnostics.csv", index=False)

    # ---- judging
    def g(sym, v, p, col):
        return T[(T.market == sym) & (T.variant == v) & (T.period == p)][col].iat[0]

    J = []
    for sym in ORDER:
        for v in VARS:
            a = (g(sym, v, "design", "t") >= 2) and g(sym, v, "check", "mean %") > 0 and g(sym, v, "holdout", "mean %") > 0
            b = g(sym, v, "check", "diff vs P0 %") > 0 and g(sym, v, "holdout", "diff vs P0 %") > 0
            row = {"market": sym, "variant": v, "rule": DESC[v], "months": g(sym, v, "all", "months"),
                   "trades/month": 1.0, "win %": g(sym, v, "all", "win %"), "win/loss": g(sym, v, "all", "win/loss"),
                   "mean %": g(sym, v, "all", "mean %")}
            for p in ["design", "check", "holdout", "last3y"]:
                row[f"{p} mean %"] = g(sym, v, p, "mean %")
                row[f"{p} t"] = g(sym, v, p, "t")
            for p in ["design", "check", "holdout"]:
                row[f"{p} diff %"] = g(sym, v, p, "diff vs P0 %")
                row[f"{p} diff t"] = g(sym, v, p, "diff t")
            row.update({"(a) charter": bool(a), "(b) beats P0": bool(b),
                        "survives": bool(a and b) if v != "P0" else False})
            J.append(row)
    J = pd.DataFrame(J)
    J.to_csv(f"{OUT}/tests.csv", index=False)

    # ---- pooled (equal weight of available markets per month)
    P = []
    for v in VARS:
        piv = MON.reset_index().pivot(index="month", columns="market", values=v)
        piv0 = MON.reset_index().pivot(index="month", columns="market", values="P0")
        pm, pm0 = piv.mean(axis=1), piv0.mean(axis=1)
        idx = pd.PeriodIndex(pm.index, freq="M")
        lab = period_of(idx)
        row = {"variant": v}
        for p in list(PER) + ["last3y"]:
            sel = lab == p if p != "last3y" else (idx >= L3[0]) & (idx <= L3[1])
            x, x0 = pm.to_numpy()[sel], pm0.to_numpy()[sel]
            row[f"{p} months"] = len(x)
            row[f"{p} mean %"] = x.mean() * 100
            row[f"{p} t"] = tstat(x)
            row[f"{p} diff %"] = (x - x0).mean() * 100
            row[f"{p} diff t"] = tstat(x - x0)
            if p in PER:
                row[f"{p} mkts>0"] = int(sum(g(s, v, p, "mean %") > 0 for s in ORDER))
                row[f"{p} mkts beat P0"] = int(sum(g(s, v, p, "diff vs P0 %") > 0 for s in ORDER))
        P.append(row)
    P = pd.DataFrame(P)
    P.to_csv(f"{OUT}/pooled.csv", index=False)

    # ---- by year (compounded included months)
    Y = []
    for sym in ORDER:
        mm = MON[MON.market == sym]
        yr = pd.PeriodIndex(mm.index, freq="M").year
        for v in VARS:
            s = (1 + mm[v]).groupby(yr).prod() - 1
            cnt = mm[v].groupby(yr).size()
            for y_, val in s.items():
                Y.append({"market": sym, "variant": v, "year": y_, "months": cnt[y_], "return %": val * 100})
    Y = pd.DataFrame(Y).pivot_table(index=["market", "year", "months"], columns="variant", values="return %").reset_index()
    Y.to_csv(f"{OUT}/by_year.csv", index=False)

    # ---- tables.md
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    cols_main = ["months", "mean %", "t", "sharpe", "win %", "win/loss", "maxDD %", "worst day %", "worst month %",
                 "mean w", "turnover/yr", "diff vs P0 %", "diff t", "MM alpha %", "MM alpha t", "beta"]
    cols_prop = ["prop s", "prop mean % at s", "12m windows", "12m touch -10% share"]
    txt = ["# tables (generated)\n", "## Judging\n", fmt_table(J.set_index(["market", "variant"]), ".3f"), "\n",
           "## Pooled\n", fmt_table(P.set_index("variant"), ".3f"), "\n", "## Diagnostics\n",
           fmt_table(DG.set_index("market"), ".2f"), "\n"]
    for sym in ORDER:
        for p in ["design", "check", "holdout", "last3y", "all"]:
            tt = T[(T.market == sym) & (T.period == p)].set_index("variant")
            txt += [f"## {NAMES[sym]} - {p} ({tt['first'].iat[0]}..{tt['last'].iat[0]})\n", fmt_table(tt[cols_main], ".3f"), "\n"]
        tt = T[(T.market == sym)].set_index(["variant", "period"])
        txt += [f"## {NAMES[sym]} - prop view\n", fmt_table(tt[cols_prop], ".3f"), "\n"]
    txt += ["## By year (%)\n", fmt_table(Y.set_index(["market", "year"]), ".2f"), "\n"]
    open(f"{OUT}/tables.md", "w").write("\n".join(txt))
    print(J[["market", "variant", "months", "mean %", "design mean %", "design t", "check mean %", "holdout mean %",
             "check diff %", "holdout diff %", "(a) charter", "(b) beats P0", "survives"]].round(3).to_string())
    print(P.round(3).to_string())
    print(DG.round(2).to_string())
    print("survivors:", list(J[J.survives].apply(lambda r: f"{r.market} {r.variant}", axis=1)))
    print(f"elapsed {time.time() - t0:.0f}s")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
