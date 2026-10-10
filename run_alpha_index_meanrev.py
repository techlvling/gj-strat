"""Alpha hunt family `index_meanrev`: equity-index short-term reversal / dip-buying (liquidity provision).
Long-only multi-day swing (1-10 day holds) on the close; one SELL control. Fixed before running.

Idea: since ~2000 daily index returns are negatively autocorrelated (Baltussen, van Bekkum & Da 2019 JFE):
index arbitrage and mechanical flows (leveraged-ETF close rebalancing, vol targeting / CTA de-risking,
short-gamma hedging) push prices too far on down days and whoever absorbs the flow is paid, more so when
VIX is high (Nagel 2012 RFS). Practitioner versions: Connors & Alvarez RSI(2) above SMA200, IBS effect
(Pagonidis 2014). New vs earlier work: E2 bought every close unconditionally, P4 was an intraday limit;
here the entry is conditional on the close and the hold is multi-day.

MARKETS: USATECHIDXUSD (Nasdaq 100, primary, minute bid/ask), JPNIDXJPY (Nikkei 225, minute),
USA500IDXUSD (S&P 500, hourly bid candles, replication), XAUUSD (gold, minute, separate replication,
never pooled with the indices). Markets are loaded one at a time and deleted; single process.

CALENDARS: Nasdaq and S&P use NYSE trading days (holidays.NYSE). Nikkei uses Japan holidays + Dec 31 +
Jan 2-3 (as run_index_replication.nikkei). Gold uses weekdays.

SIGNAL CLOSE C (one per trading day, DST-aware via gjstrat.patterns.local_idx):
  * Nasdaq: C = bid close of the 15:54 New York minute (the price at 15:55:00). Entry = market at the
    open of the first live minute (vol > 0) in [15:55, 16:00) NY (run_index_anomalies.live_at). Every
    time exit is at the open of the 15:55 NY minute on the exit day (exit_by_i = that index).
  * Nikkei: the same with 14:54 / 14:55 Asia/Tokyo through 2024-11-04 and 15:24 / 15:25 from 2024-11-05
    (the TSE close moved to 15:30).
  * Gold: 16:44 / 16:45 NY (before the 17:00 rollover spread).
  * Minute markets: a day enters the close series only if the signal minute has ticks (vol > 0)
    (the spec states this for the Nikkei, whose Asian hours are missing in 2015-2017; applied to all
    minute markets, because a forward-filled close is not a close - obvious-impossibility fix).
  * S&P (hourly only): C = close of the 15:00-16:00 NY hourly bar (only bars with ticks, v > 0; the
    hourly files contain flat zero-volume bars - same fix). Fills at C: buys at C + 0.5 pt, sells at
    C - 0.5 pt (1.0 pt round trip, as run_index_replication). The stop is checked on later hourly bars
    (bid low for longs, bid high for shorts) from the 16:00 bar of the entry day through the 15:00 bar
    of the exit day; it fills at the stop level, or at the bar open if price gapped through, minus
    0.25 pt slippage (plus 0.25 pt for a short). S&P daily H/L/ATR: live hourly bars grouped into
    17:00-17:00 NY days (weekday labels); ATR20 = mean(H - L) of the 20 previous days.

DATA GAPS (obvious-impossibility fix): r_t is taken between consecutive available trading days as
specified, but when more than 5 calendar trading days are missing in a row (Nasdaq Feb-May 2013,
Nikkei 2015, S&P 2013, ...) the close series is split into segments: a "daily" return spanning months
is not a daily return. All features (r, sigma60, RSI2, SMA200, SMA5, previous close) are computed within
a segment (warm-up restarts), and an exit day must lie in the entry's segment (else no trade).

FEATURES (only data up to C_t):
  r_t = ln(C_t / C_{t-1}); sigma60 = std (ddof 1) of the 60 previous r (t excluded); RSI2 = Wilder RSI,
  period 2, on C (seeded with the mean of the first 2 gains/losses); SMA200 and SMA5 of C including C_t;
  ATR20 = gjstrat.patterns.daily_table(m).atr20 of day t (shifted: known before the day);
  IBS = (C - L) / (H - L) with H/L the session bid high/low from the session open to the signal minute:
  Nasdaq 09:30-15:54 NY; Nikkei 09:00-14:54 JST (15:24 from 2024-11-05); S&P live hourly bars starting
  10:00..15:00 NY; gold 17:00 NY of the previous calendar day to 16:44 NY.
  VIX = latest FRED VIXCLS (data/extra/VIXCLS.csv) dated strictly before the signal's local calendar
  date; VIXmed = median of the 252 VIX values before that one.

RULES: long only except MR11. One position per market per variant: a signal is ignored while a trade
is open, i.e. a new entry needs a signal close strictly after the previous trade's planned exit close.
Exit days come from the close series only (path-independent); a stop-out does not free the slot early.
Minute markets are simulated with gjstrat.patterns.simulate(Signal(day, side, entry_i, 'market', None,
entry_i + 1, sl_dist=k * ATR20, tp_dist=None, exit_by_i=exit minute)), so the stop is checked minute by
minute on real bid/ask. "Exit at signal close X" = exit at the open of the entry minute on day X.

VARIANTS (11):
  MR1  r_t < -1.0 sigma60. Exit at the next signal close. SL 1.5 ATR20.
  MR2  r_t < -2.0 sigma60. Exit at the next close. SL 1.5 ATR20.
  MR3  MR1 AND VIX > VIXmed (Nagel). Exit at the next close. SL 1.5 ATR20.
  MR4  MR1 entry. Time exit at the 5th signal close after entry. SL 2.0 ATR20.
  MR5  (Connors) C_t > SMA200 AND RSI2 < 10. Exit at the first later close with C > SMA5, else after
       10 closes. SL 2.0 ATR20.
  MR6  MR5 with RSI2 < 5.
  MR7  MR5 entry, exit at the first later close with RSI2 > 70 (10-close cap). SL 2.0 ATR20.
  MR8  (control for the trend filter) MR5 without the SMA200 condition.
  MR9  IBS <= 0.15 AND C_t < C_{t-1}. Exit at the next close. SL 1.0 ATR20.
  MR10 MR9 AND session (H - L) >= 1.5 ATR20. Exit at the first later close above the entry day's
       session H, else after 3 closes. SL 1.5 ATR20.
  MR11 (control, SELL) r_t > +1.0 sigma60. Exit at the next close. SL 1.5 ATR20. Theory: <= 0.

COSTS: Nasdaq, Nikkei, gold via run_all_matrix.net_r (bid/ask fills, NON_FX commission / slippage with
double slippage on stop fills, 3%/yr financing per rollover night); trades sorted by (exit_i, entry_i).
S&P: as above + 3%/yr x calendar nights / 365 x entry price. R = net P&L / stop distance.

PERIODS / SURVIVAL (charter): run_edge_hunt.PER: design 2010-17 (indices from data start), check
2018-23, holdout 2024-26. A test (market x variant) survives if design t >= 2 AND avg R > 0 in check
AND in holdout. Nasdaq gets the charter bar first; S&P and Nikkei are replications (avg R > 0 over the
whole period); gold is judged on its own (charter bar). 44 tests (11 x 4) -> ~0.3 survivors by luck.

REPORT (results/alpha_hunt/index_meanrev/REPORT.md + csv): per market x variant: trades, trades/month
(per month with data), win %, avg win / avg loss, avg R and t per period, last 3 years
(2023-10-08..2026-10-07). Pooled indices (Nasdaq + Nikkei + S&P) per variant with month-clustered t
(sum R per calendar month, zero for months without trades inside the data span, t over months) and the
count of indices with avg R > 0. Gold separately. Overlap of trade dates between MR1 / MR5 / MR9 and
across indices. Avg R split by regime: ATR20 >= vs < its trailing 250-day median. Worst single day in %
at 0.5% risk per trade (marked to market at each signal close and booked by NY trading day, and
realised-only), with Nasdaq and S&P counted as one position (their average when both are open) plus
the Nikkei; gold alone. Avg R by year for the pooled indices (crash years 2020, 2022).

IF ANY TEST SURVIVES: prop sim with gjstrat.prop.prop_table, run_m3_addon.build_legs() plus the new
leg at 0.5% and 1% risk, run_m3_addon.ALPHA rules (normal risk and boost x1.5), challenges started
2011-2025 and 2018-2025. Trades join the USDJPY grid at (their UTC time - m_usdjpy.t0) minutes, which is
the run_index_prop.py shift (m_other.t0 - m_usdjpy.t0).

    python run_alpha_index_meanrev.py          # everything (prop sim only if a test survives)
    python run_alpha_index_meanrev.py prop     # prop sim from the saved trades
"""
from __future__ import annotations

import glob
import lzma
import os
import pickle
import sys
import time
from collections import namedtuple
from datetime import date

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

OUT = "results/alpha_hunt/index_meanrev"
TKY = "Asia/Tokyo"
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
NIK_SWITCH = pd.Timestamp("2024-11-05")
GAP = 5                                            # > 5 missing trading days in a row -> new segment
VARIANTS = {  # name: (side, SL x ATR20, description)
    "MR1": ("BUY", 1.5, "r < -1 sigma60, exit next close"),
    "MR2": ("BUY", 1.5, "r < -2 sigma60, exit next close"),
    "MR3": ("BUY", 1.5, "MR1 + VIX > 252d median, exit next close"),
    "MR4": ("BUY", 2.0, "MR1 entry, exit 5th close"),
    "MR5": ("BUY", 2.0, "C > SMA200 & RSI2 < 10, exit C > SMA5 (cap 10)"),
    "MR6": ("BUY", 2.0, "C > SMA200 & RSI2 < 5, exit C > SMA5 (cap 10)"),
    "MR7": ("BUY", 2.0, "C > SMA200 & RSI2 < 10, exit RSI2 > 70 (cap 10)"),
    "MR8": ("BUY", 2.0, "RSI2 < 10 (no SMA200), exit C > SMA5 (cap 10)"),
    "MR9": ("BUY", 1.0, "IBS <= 0.15 & down close, exit next close"),
    "MR10": ("BUY", 1.5, "MR9 + range >= 1.5 ATR, exit C > entry-day H (cap 3)"),
    "MR11": ("SELL", 1.5, "control SELL: r > +1 sigma60, exit next close"),
}
MINUTE = {
    "USATECHIDXUSD": dict(path="data/usatechidxusd_2011-01-02_2026-10-07.npz", tz=NY, cal="nyse"),
    "JPNIDXJPY": dict(path="data/jpnidxjpy_2011-01-02_2026-10-07.npz", tz=TKY, cal="japan"),
    "XAUUSD": dict(path="data/xauusd_2010-01-01_2026-10-07.npz", tz=NY, cal="weekdays"),
}
NAMES = {"USATECHIDXUSD": "Nasdaq 100", "USA500IDXUSD": "S&P 500", "JPNIDXJPY": "Nikkei 225", "XAUUSD": "Gold"}
INDICES = ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY"]


# --------------------------------------------------------------------------- calendars / VIX
def calendar(kind: str, a: pd.Timestamp, b: pd.Timestamp) -> pd.DatetimeIndex:
    days = pd.bdate_range(a.normalize(), b.normalize())
    yrs = range(a.year, b.year + 1)
    if kind == "nyse":
        hol = set(holidays.NYSE(years=yrs))
    elif kind == "japan":
        hol = set(holidays.Japan(years=yrs)) | {date(y, 12, 31) for y in yrs} | {date(y, 1, k) for y in yrs for k in (2, 3)}
    else:
        hol = set()
    return pd.DatetimeIndex([d for d in days if d.date() not in hol])


def load_vix():
    df = pd.read_csv("data/extra/VIXCLS.csv", parse_dates=["observation_date"])
    s = pd.Series(pd.to_numeric(df["VIXCLS"], errors="coerce").to_numpy(), index=df["observation_date"]).dropna()
    med = s.shift(1).rolling(252).median()                    # 252 values before the current one
    return s, med


def vix_for(days: pd.DatetimeIndex, vix, vmed):
    """Latest VIX dated strictly before each local signal date, and its 252-value median."""
    p = np.searchsorted(vix.index.values, days.values, side="left") - 1
    ok = p >= 0
    v = np.where(ok, vix.to_numpy()[np.maximum(p, 0)], np.nan)
    m = np.where(ok, vmed.to_numpy()[np.maximum(p, 0)], np.nan)
    return v, m


# --------------------------------------------------------------------------- features
def rsi_wilder(c: np.ndarray, n: int = 2) -> np.ndarray:
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g, l = np.maximum(d, 0), np.maximum(-d, 0)
    val = lambda ag, al: (100.0 if ag > 0 else 50.0) if al == 0 else 100 - 100 / (1 + ag / al)
    ag, al = g[:n].mean(), l[:n].mean()
    out[n] = val(ag, al)
    for k in range(n, len(d)):
        ag, al = (ag * (n - 1) + g[k]) / n, (al * (n - 1) + l[k]) / n
        out[k + 1] = val(ag, al)
    return out


def add_features(cs: pd.DataFrame, cal: pd.DatetimeIndex, atr_med: pd.Series, vix, vmed) -> pd.DataFrame:
    """cs: one row per available day (index = local trading date) with C, H, L, atr20. Adds segments and
    features computed within segments."""
    pos = cal.get_indexer(cs.index)
    assert (pos >= 0).all()
    gap = np.diff(pos, prepend=pos[0] - 1) - 1
    cs["seg"] = np.cumsum(gap > GAP)
    parts = []
    for _, g in cs.groupby("seg", sort=True):
        g = g.copy()
        c = g["C"]
        g["prevC"] = c.shift(1)
        g["r"] = np.log(c / c.shift(1))
        g["sig60"] = g["r"].shift(1).rolling(60).std()
        g["rsi2"] = rsi_wilder(c.to_numpy())
        g["sma200"] = c.rolling(200).mean()
        g["sma5"] = c.rolling(5).mean()
        parts.append(g)
    cs = pd.concat(parts)
    cs["ibs"] = np.where(cs.H > cs.L, (cs.C - cs.L) / (cs.H - cs.L), np.nan)
    cs["vix"], cs["vixmed"] = vix_for(pd.DatetimeIndex(cs.index), vix, vmed)   # index = local signal date
    cs["atr_med"] = atr_med.reindex(cs.index).to_numpy()
    return cs


def plan(cs: pd.DataFrame, execute) -> dict[str, list]:
    """Walk the close series; for each variant take signals (one position at a time, exit days from the
    close series). execute(variant, j, jx, side, sl_mult) -> trade record or None."""
    C, seg, n = cs.C.to_numpy(), cs.seg.to_numpy(), len(cs)
    f = lambda col: cs[col].to_numpy(dtype=float)
    r, s60, rsi, s200, s5, H, L, atr = f("r"), f("sig60"), f("rsi2"), f("sma200"), f("sma5"), f("H"), f("L"), f("atr20")
    vix, vmed, ibs, prevC = f("vix"), f("vixmed"), f("ibs"), f("prevC")
    with np.errstate(invalid="ignore"):
        e1 = r < -1.0 * s60
        e2 = r < -2.0 * s60
        e3 = e1 & (vix > vmed)
        e5 = (C > s200) & (rsi < 10)
        e6 = (C > s200) & (rsi < 5)
        e8 = rsi < 10
        e9 = (ibs <= 0.15) & (C < prevC)
        e10 = e9 & ((H - L) >= 1.5 * atr)
        e11 = r > 1.0 * s60

    def kth(j, k):
        jj = j + k
        return jj if jj < n and seg[jj] == seg[j] else None

    def first(j, cond, cap):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= n or seg[jj] != seg[j]:
                return None
            if cond(jj):
                return jj
        return j + cap

    rules = {
        "MR1": (e1, lambda j: kth(j, 1)), "MR2": (e2, lambda j: kth(j, 1)), "MR3": (e3, lambda j: kth(j, 1)),
        "MR4": (e1, lambda j: kth(j, 5)),
        "MR5": (e5, lambda j: first(j, lambda x: C[x] > s5[x], 10)),
        "MR6": (e6, lambda j: first(j, lambda x: C[x] > s5[x], 10)),
        "MR7": (e5, lambda j: first(j, lambda x: rsi[x] > 70, 10)),
        "MR8": (e8, lambda j: first(j, lambda x: C[x] > s5[x], 10)),
        "MR9": (e9, lambda j: kth(j, 1)),
        "MR10": (e10, lambda j: first(j, lambda x, hj=H[j]: C[x] > hj, 3)),
        "MR11": (e11, lambda j: kth(j, 1)),
    }
    out = {}
    for v, (ent, ex) in rules.items():
        side, slm, _ = VARIANTS[v]
        busy, trades = -1, []
        for j in np.flatnonzero(ent):
            if j <= busy or not atr[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = execute(v, j, jx, side, slm)
            if t is None:
                continue
            trades.append(t)
            busy = jx
        out[v] = trades
    return out


# --------------------------------------------------------------------------- minute markets
def run_minute(sym: str, vix, vmed):
    cfg = MINUTE[sym]
    t0 = time.time()
    m = load_market(cfg["path"])
    d = daily_table(m)
    atr_med = d["atr20"].rolling(250, min_periods=250).median()
    hot_flag = (d["atr20"] >= atr_med).astype(float).where(atr_med.notna())
    last = m.ts(m.n - 1)
    cal = calendar(cfg["cal"], m.t0 + pd.Timedelta(days=1), last)
    tz = cfg["tz"]

    def sig_hm(day):
        if sym == "USATECHIDXUSD":
            return 15, 54
        if sym == "JPNIDXJPY":
            return (14, 54) if day < NIK_SWITCH else (15, 24)
        return 16, 44

    rows = []
    for day in cal:
        hh, mm = sig_hm(day)
        i = local_idx(m, day, hh, mm, tz)
        if i < 0 or i >= m.n - 1 or not m.vol[i] > 0:
            continue
        if sym == "USATECHIDXUSD":
            a = local_idx(m, day, 9, 30, NY)
        elif sym == "JPNIDXJPY":
            a = local_idx(m, day, 9, 0, TKY)
        else:
            a = local_idx(m, day - pd.Timedelta(days=1), 17, 0, NY)
        a = max(a, 0)
        rows.append((day, i, m.bc[i], m.bh[a:i + 1].max(), m.bl[a:i + 1].min()))
    cs = pd.DataFrame(rows, columns=["day", "i", "C", "H", "L"]).set_index("day")
    cs["atr20"] = d["atr20"].reindex(cs.index).to_numpy()
    cs["hot"] = hot_flag.reindex(cs.index).to_numpy()
    cs["ts"] = [m.ts(i + 1) for i in cs.i]                     # UTC time of the close (end of the signal minute)
    cs = add_features(cs, cal, atr_med, vix, vmed)
    I = cs.i.to_numpy()

    def execute(v, j, jx, side, slm):
        s = live_at(m, int(I[j]) + 1)
        x = int(I[jx]) + 1
        sl = slm * cs.atr20.iat[j]
        if s < 0 or x <= s + 1 or x >= m.n or not sl > 0:
            return None
        return simulate(m, Signal(cs.index[j], side, s, "market", None, s + 1, sl, None, x, v))

    raw = plan(cs, execute)
    recs = []
    for v, tr in raw.items():
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        R = net_r(m, sym, tr, None)
        for t, x in zip(tr, R):
            recs.append(dict(market=sym, variant=v, day=t.day, side=t.side, entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i),
                             entry=t.entry, exit=t.exit, reason=t.reason, risk=t.risk, R_gross=t.r, R=x,
                             hot=cs.hot.get(t.day, np.nan)))
    months = cs.index.to_period("M").nunique()
    print(f"{sym}: {len(cs)} closes, {cs.seg.nunique()} segments, {len(recs)} trades, {time.time() - t0:.0f}s", flush=True)
    keep = cs[["C", "ts", "seg"]].copy()
    del m, d
    return pd.DataFrame(recs), keep, months


# --------------------------------------------------------------------------- S&P hourly
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
    return b[b.v > 0]                                          # live bars only


def run_spx(vix, vmed):
    t0 = time.time()
    b = spx_bars()
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    lab = (loc + pd.Timedelta(hours=7)).normalize()
    dd = pd.DataFrame({"high": b.h.to_numpy(), "low": b.l.to_numpy()}, index=lab).groupby(level=0).agg(high=("high", "max"), low=("low", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.high - dd.low).rolling(20).mean().shift(1)
    atr_med = atr.rolling(250, min_periods=250).median()
    hot_flag = (atr >= atr_med).astype(float).where(atr_med.notna())
    cal = calendar("nyse", pd.Timestamp("2012-01-01"), pd.Timestamp("2026-10-07"))
    hr, ldate = loc.hour, loc.normalize()
    sess = pd.DataFrame({"h": b.h.to_numpy(), "l": b.l.to_numpy()}, index=ldate)[(hr >= 10) & (hr <= 15)]
    sH, sL = sess.groupby(level=0).h.max(), sess.groupby(level=0).l.min()
    c15 = b[hr == 15]
    c15 = pd.DataFrame({"C": c15.c.to_numpy(), "start": c15.index}, index=ldate[hr == 15])
    c15 = c15[c15.index.isin(cal)]
    cs = c15.copy()
    cs["H"], cs["L"] = sH.reindex(cs.index).to_numpy(), sL.reindex(cs.index).to_numpy()
    cs["atr20"] = atr.reindex(cs.index).to_numpy()
    cs["hot"] = hot_flag.reindex(cs.index).to_numpy()
    cs["ts"] = cs.start + pd.Timedelta(hours=1)
    cs = add_features(cs, cal, atr_med, vix, vmed)
    starts = b.index.values
    O, Hh, Ll = b.o.to_numpy(), b.h.to_numpy(), b.l.to_numpy()

    def execute(v, j, jx, side, slm):
        sl = slm * cs.atr20.iat[j]
        if not sl > 0:
            return None
        Cj, Cx = cs.C.iat[j], cs.C.iat[jx]
        a = np.searchsorted(starts, cs.start.values[j], side="right")
        z = np.searchsorted(starts, cs.start.values[jx], side="right")
        if side == "BUY":
            entry = Cj + 0.5
            stop = entry - sl
            hit = np.flatnonzero(Ll[a:z] <= stop)
        else:
            entry = Cj - 0.5
            stop = entry + sl
            hit = np.flatnonzero(Hh[a:z] >= stop)
        if len(hit):
            k = a + hit[0]
            px = (min(stop, O[k]) - 0.25) if side == "BUY" else (max(stop, O[k]) + 0.25)
            reason, xts = "SL", pd.Timestamp(starts[k]) + pd.Timedelta(minutes=30)
        else:
            px = Cx - 0.5 if side == "BUY" else Cx + 0.5
            reason, xts = "TIME", cs.ts.iat[jx]
        gross = (px - entry) if side == "BUY" else (entry - px)
        nights = (cs.index[jx] - cs.index[j]).days if reason == "TIME" else \
            (xts.tz_localize("UTC").tz_convert(NY).tz_localize(None).normalize() - cs.index[j]).days
        fin = 0.03 * max(nights, 0) / 365 * entry
        return dict(market="USA500IDXUSD", variant=v, day=cs.index[j], side=side, entry_ts=cs.ts.iat[j], exit_ts=xts,
                    entry=entry, exit=px, reason=reason, risk=sl, R_gross=gross / sl, R=(gross - fin) / sl,
                    hot=cs.hot.iat[j])

    raw = plan(cs, execute)
    recs = [t for v in raw.values() for t in v]
    months = cs.index.to_period("M").nunique()
    print(f"USA500IDXUSD: {len(cs)} closes, {cs.seg.nunique()} segments, {len(recs)} trades, {time.time() - t0:.0f}s", flush=True)
    return pd.DataFrame(recs), cs[["C", "ts", "seg"]].copy(), months


# --------------------------------------------------------------------------- statistics
def label(ts) -> pd.DatetimeIndex:
    ts = pd.DatetimeIndex(ts)
    return (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def test_row(g: pd.DataFrame, months: int) -> dict:
    r = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    wins, losses = r[r > 0], r[r <= 0]
    row = {"trades": len(r), "trades/month": len(r) / months if months else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}
    row.update(per_stats(r, day))
    v = r[np.asarray((day >= L3[0]) & (day <= L3[1]))]
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    row["SL %"] = (g.reason == "SL").mean() * 100 if len(g) else np.nan
    row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    return row


def month_t(g: pd.DataFrame, a, b, span) -> tuple[float, float, int, int]:
    """(avg R per trade, month-clustered t, trades, months) for signal days in [a, b]."""
    a, b = max(pd.Timestamp(a), span[0]), min(pd.Timestamp(b), span[1])
    months = pd.period_range(a, b, freq="M")
    x = g[(g.day >= a) & (g.day <= b)]
    s = x.groupby(pd.DatetimeIndex(x.day).to_period("M")).R.sum().reindex(months, fill_value=0.0)
    return (x.R.mean() if len(x) else np.nan), tstat(s.to_numpy()), len(x), len(months)


def mtm_days(tr: pd.DataFrame, closes: pd.DataFrame) -> dict:
    """Daily R of every trade marked to market at each signal close, by NY trading-day label, costs on the
    exit day. Returns {label: R summed over the trades}."""
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
    s = pd.Series(tr.R.to_numpy(), index=label(tr.exit_ts)).groupby(level=0).sum()
    return s.to_dict()


def combine_us_nikkei(nq: dict, sp: dict, nk: dict, risk=0.5) -> pd.Series:
    keys = set(nq) | set(sp) | set(nk)
    out = {}
    for k in keys:
        us = [x[k] for x in (nq, sp) if k in x]
        out[k] = risk * ((np.mean(us) if us else 0.0) + nk.get(k, 0.0))
    return pd.Series(out).sort_index()


# --------------------------------------------------------------------------- prop sim
def prop(survivors: list[tuple[str, str]]):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    T = pd.read_pickle(f"{OUT}/trades.pkl")
    Tr = namedtuple("Tr", "day entry_i exit_i")
    m, legs = build_legs()
    names = []
    for sym, v in survivors:
        g = T[(T.market == sym) & (T.variant == v)].copy()
        g["ei"] = ((pd.DatetimeIndex(g.entry_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g["xi"] = ((pd.DatetimeIndex(g.exit_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        g = g[g.xi < m.n].sort_values(["xi", "ei"])
        legs.append(([Tr(pd.Timestamp(d), int(a), int(b)) for d, a, b in zip(g.day, g.ei, g.xi)], g.R.to_numpy()))
        names.append(f"{NAMES[sym]} {v}")
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(names)}
    for risk in (0.5, 1):
        for j, nm in enumerate(names):
            mixes[f"basket + {nm} {risk}%"] = base + tuple(risk if i == j else 0 for i in range(len(names)))
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
    txt = ("\n## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)\n\nBasket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + "
           "M-3 USDJPY 3% (run_m3_addon.build_legs); new leg(s) added at 0.5% and 1% risk.\n\n" + fmt_table(P[cols], ".1f") + "\n")
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write(txt)
    print(P[cols].round(1).to_string())
    return P


# --------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    vix, vmed = load_vix()
    trades, closes, months = [], {}, {}
    for sym in ["USATECHIDXUSD", "JPNIDXJPY", "XAUUSD"]:
        t, c, mo = run_minute(sym, vix, vmed)
        trades.append(t); closes[sym] = c; months[sym] = mo
    t, c, mo = run_spx(vix, vmed)
    trades.append(t); closes["USA500IDXUSD"] = c; months["USA500IDXUSD"] = mo
    T = pd.concat(trades, ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T.to_pickle(f"{OUT}/trades.pkl")
    T.to_csv(f"{OUT}/trades.csv", index=False)

    # charter table
    rows = []
    for sym in ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY", "XAUUSD"]:
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            rows.append({"market": sym, "variant": v, **test_row(g, months[sym])})
    R = pd.DataFrame(rows)
    R["replicates (avg R > 0)"] = R["avg R"] > 0
    R.to_csv(f"{OUT}/tests.csv", index=False)
    surv = R[R.survives]

    # pooled indices
    span = (min(closes[s].index.min() for s in INDICES), max(closes[s].index.max() for s in INDICES))
    prow = []
    for v in VARIANTS:
        g = T[(T.market.isin(INDICES)) & (T.variant == v)]
        row = {"variant": v, "trades": len(g), "avg R": g.R.mean(), "month t (all)": month_t(g, span[0], span[1], span)[1]}
        for p, (a, b) in PER.items():
            avg, mt, n, nm = month_t(g, a, b, span)
            row.update({f"{p} n": n, f"{p} avg R": avg, f"{p} month t": mt})
        avg, mt, n, nm = month_t(g, L3[0], L3[1], span)
        row.update({"last3y n": n, "last3y avg R": avg, "last3y month t": mt})
        row["indices avg R > 0"] = int(sum(R[(R.market == s) & (R.variant == v)]["avg R"].iloc[0] > 0 for s in INDICES))
        row["pooled passes bar"] = bool(row["design month t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
        prow.append(row)
    PL = pd.DataFrame(prow).set_index("variant")
    PL.to_csv(f"{OUT}/pooled_indices.csv")

    # overlap
    days_of = lambda sym, v: set(T[(T.market == sym) & (T.variant == v)].day)
    ov = []
    for sym in ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY", "XAUUSD"]:
        for a, b in (("MR1", "MR5"), ("MR1", "MR9"), ("MR5", "MR9")):
            A, B = days_of(sym, a), days_of(sym, b)
            ov.append({"market": sym, "pair": f"{a} / {b}", "A days": len(A), "B days": len(B),
                       "% of A also B": len(A & B) / len(A) * 100 if A else np.nan,
                       "% of B also A": len(A & B) / len(B) * 100 if B else np.nan})
    OV = pd.DataFrame(ov)
    nk_cal = closes["JPNIDXJPY"].index
    xo = []
    for v in VARIANTS:
        nq, sp, nk = days_of("USATECHIDXUSD", v), days_of("USA500IDXUSD", v), days_of("JPNIDXJPY", v)
        k = np.searchsorted(nk_cal.values, pd.DatetimeIndex(sorted(nq)).values, side="right")
        nq_next = {nk_cal[x] for x in k if x < len(nk_cal)}

        def mon(sym):
            g = T[(T.market == sym) & (T.variant == v)]
            return g.groupby(pd.DatetimeIndex(g.day).to_period("M")).R.sum()
        mm = pd.concat({"nq": mon("USATECHIDXUSD"), "sp": mon("USA500IDXUSD"), "nk": mon("JPNIDXJPY")}, axis=1).fillna(0)
        xo.append({"variant": v, "Nasdaq days": len(nq), "S&P days": len(sp), "Nikkei days": len(nk),
                   "% Nasdaq days also S&P": len(nq & sp) / len(nq) * 100 if nq else np.nan,
                   "% Nasdaq days also Nikkei (same date)": len(nq & nk) / len(nq) * 100 if nq else np.nan,
                   "% Nasdaq days with Nikkei next Tokyo day": len(nq_next & nk) / len(nq) * 100 if nq else np.nan,
                   "corr monthly R Nasdaq-S&P": mm.nq.corr(mm.sp), "corr monthly R Nasdaq-Nikkei": mm.nq.corr(mm.nk)})
    XO = pd.DataFrame(xo).set_index("variant")
    OV.to_csv(f"{OUT}/overlap_variants.csv", index=False); XO.to_csv(f"{OUT}/overlap_indices.csv")

    # regime split
    rg = []
    for sym in ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY", "XAUUSD"]:
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            hot, cold = g[g.hot == 1], g[g.hot == 0]
            rg.append({"market": sym, "variant": v, "high-ATR n": len(hot), "high-ATR avg R": hot.R.mean(), "high-ATR t": tstat(hot.R),
                       "low-ATR n": len(cold), "low-ATR avg R": cold.R.mean(), "low-ATR t": tstat(cold.R)})
    RG = pd.DataFrame(rg)
    RG.to_csv(f"{OUT}/regime.csv", index=False)

    # worst day
    wd = []
    for v in VARIANTS:
        sub = {s: T[(T.market == s) & (T.variant == v)] for s in closes}
        mtm = {s: mtm_days(sub[s], closes[s]) for s in closes}
        rea = {s: realised_days(sub[s]) for s in closes}
        P_m = combine_us_nikkei(mtm["USATECHIDXUSD"], mtm["USA500IDXUSD"], mtm["JPNIDXJPY"])
        P_r = combine_us_nikkei(rea["USATECHIDXUSD"], rea["USA500IDXUSD"], rea["JPNIDXJPY"])
        G_m = pd.Series(mtm["XAUUSD"]).sort_index() * 0.5
        G_r = pd.Series(rea["XAUUSD"]).sort_index() * 0.5
        wd.append({"variant": v, "indices worst day % (MTM)": P_m.min(), "date": P_m.idxmin().date(),
                   "indices worst day % (realised)": P_r.min(), "date ": P_r.idxmin().date(),
                   "indices days < -1% (MTM)": int((P_m < -1).sum()),
                   "worst single index trade R": T[(T.market.isin(INDICES)) & (T.variant == v)].R.min(),
                   "gold worst day % (MTM)": G_m.min() if len(G_m) else np.nan,
                   "gold date": G_m.idxmin().date() if len(G_m) else None})
    WD = pd.DataFrame(wd).set_index("variant")
    WD.to_csv(f"{OUT}/worst_day.csv")

    # by year, pooled indices
    I_ = T[T.market.isin(INDICES)]
    YR = I_.groupby(["variant", pd.DatetimeIndex(I_.day).year]).R.mean().unstack()
    YR = YR.reindex(list(VARIANTS))
    YR.columns = [str(c) for c in YR.columns]
    YR.index.name = "variant"
    YR.to_csv(f"{OUT}/by_year_indices.csv")

    # ------------------------------------------------------------------ report
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R", "design t",
            "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n", "last3y avg R",
            "last3y t", "SL %", "survives"]

    def tab(sym):
        x = R[R.market == sym].set_index("variant")[cols].copy()
        x.index = [f"{v} {VARIANTS[v][2]}" for v in x.index]
        x.index.name = "variant"
        return fmt_table(x, ".3f")

    nq = R[R.market == "USATECHIDXUSD"].set_index("variant")
    judge = pd.DataFrame({"Nasdaq charter bar": nq.survives,
                          "S&P avg R": R[R.market == "USA500IDXUSD"].set_index("variant")["avg R"],
                          "Nikkei avg R": R[R.market == "JPNIDXJPY"].set_index("variant")["avg R"],
                          "Gold charter bar": R[R.market == "XAUUSD"].set_index("variant").survives,
                          "Gold avg R": R[R.market == "XAUUSD"].set_index("variant")["avg R"]})
    judge["S&P replicates"] = judge["S&P avg R"] > 0
    judge["Nikkei replicates"] = judge["Nikkei avg R"] > 0
    judge.index.name = "variant"
    n_tests = len(R)
    s_list = ", ".join(f"{NAMES[a]} {b}" for a, b in zip(surv.market, surv.variant)) or "none"
    txt = [f"# Alpha hunt: equity-index short-term reversal / dip-buying (`index_meanrev`)\n",
           "Rules, variants and the survival bar are in the docstring of `run_alpha_index_meanrev.py` (fixed before running). "
           "Long-only on the close (MR11 = SELL control), 1-10 day holds, stops 1-2 x ATR20 checked minute by minute "
           "(S&P on hourly bars), all costs included. Periods: design 2010-17 (indices from data start), check 2018-23, "
           "holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.\n",
           f"**Tests: {n_tests} (11 variants x 4 markets). Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): "
           f"{len(surv)} ({s_list}). Expected by luck: {n_tests * 0.006:.2f}.**\n",
           "## Judging\n", "Nasdaq gets the charter bar; S&P and Nikkei replicate if avg R > 0 over the whole period; gold is judged on its own.\n",
           fmt_table(judge, ".3f"), "\n"]
    for sym in ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY", "XAUUSD"]:
        txt += [f"## {NAMES[sym]} ({sym}){' - separate replication, not pooled' if sym == 'XAUUSD' else ''}\n",
                f"Months with data: {months[sym]}. trades/month = trades / months with data.\n", tab(sym), "\n"]
    pcols = ["trades", "avg R", "month t (all)", "design n", "design avg R", "design month t", "check n", "check avg R",
             "check month t", "holdout n", "holdout avg R", "holdout month t", "last3y n", "last3y avg R", "last3y month t",
             "indices avg R > 0", "pooled passes bar"]
    txt += ["## Pooled indices (Nasdaq + Nikkei + S&P), month-clustered t\n",
            "Sum of R per calendar month (zero for months without trades inside the data span), t over months. "
            "The three indices are close to one bet (see overlap), so pooling adds little independent evidence.\n",
            fmt_table(PL[pcols], ".3f"), "\n",
            "## Overlap of trade dates\n", "### Between variants (same market)\n", fmt_table(OV.set_index("market"), ".1f"), "\n",
            "### Across indices (same variant)\n", fmt_table(XO, ".2f"), "\n",
            "## Avg R by volatility regime (ATR20 >= vs < its trailing 250-day median)\n",
            fmt_table(RG.set_index("market"), ".3f"), "\n",
            "## Worst single day at 0.5% risk per trade\n",
            "Indices: Nasdaq and S&P count as one position (average of the two when both are open) + Nikkei, each 0.5%. "
            "MTM = every open trade marked at each signal close, booked by NY trading day (17:00 roll); realised = net R on the exit day. "
            "Gold alone at 0.5%.\n", fmt_table(WD, ".2f"), "\n",
            "## Avg R per trade by year, pooled indices\n", fmt_table(YR, ".2f"), "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(R[["market", "variant", "trades", "trades/month", "win %", "avg R", "design avg R", "design t", "check avg R",
             "holdout avg R", "last3y avg R", "survives"]].round(3).to_string())
    print(PL[pcols].round(3).to_string())
    print(WD.round(2).to_string())
    print("survivors:", s_list, flush=True)
    if len(surv):
        prop(list(zip(surv.market, surv.variant)))
    print("DONE", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prop":
        R = pd.read_csv(f"{OUT}/tests.csv")
        s = R[R.survives]
        prop(list(zip(s.market, s.variant)))
        print("DONE", flush=True)
    else:
        main()
