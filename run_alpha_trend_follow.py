"""Alpha hunt family `trend_follow`: monthly time-series momentum (TSMOM) + daily Turtle / chandelier
breakout trend with multi-week holds. Every rule below was fixed before the first run.

IDEA: investors under-react to slowly diffusing macro news and hedger / CTA flows extend moves, so trailing
returns predict future returns (Moskowitz, Ooi & Pedersen 2012 JFE, 58 futures incl. FX, gold, indices;
Hurst, Ooi & Pedersen 2017, a century of trend following; Faith 2007 Turtle rules; LeBeau chandelier exit).
Counter-evidence: FX trend profits decayed after the 1990s (Neely, Weller & Ulrich 2009) and the SG Trend
index was weak 2011-19, so FX is reported separately. New in this repo: everything tested so far was flat
within 24 h; this holds for weeks.

MARKETS (13, loaded one at a time inside each worker and deleted; multiprocessing.Pool(2)):
  FX majors (7): EURUSD GBPUSD USDJPY USDCHF AUDUSD USDCAD NZDUSD; JPY crosses (2): AUDJPY EURJPY;
  gold: XAUUSD; indices (3): USATECHIDXUSD (Nasdaq 100), JPNIDXJPY (Nikkei 225), USA500IDXUSD (S&P 500,
  hourly bid candles only).

SIGNAL CLOSE C AND ENTRY MINUTE (DST-aware gjstrat.patterns.local_idx):
  * FX and gold: C = bid close of the 16:44 New York minute; entry = market at the 16:45 NY minute open
    (weekdays).
  * Nasdaq: 15:54 / 15:55 NY (NYSE trading days, holidays.NYSE).
  * Nikkei: 14:54 / 14:55 Asia/Tokyo, 15:24 / 15:25 from 2024-11-05 (TSE days = Japan holidays + Dec 31 +
    Jan 2-3; days without ticks are skipped).
  * S&P: C = close of the 15:00-16:00 NY hourly bar (live bars, v > 0); fills at C + 0.5 pt (buy) or
    C - 0.5 pt (sell); a time exit fills at C_exit - 0.5 (long) / + 0.5 (short) (1.0 pt round trip); the stop
    is checked on the later hourly bars (bid low for longs, bid high for shorts) from the 16:00 bar of the
    entry day through the 15:00 bar of the exit day and fills at the stop, or the bar open if gapped through,
    with 0.25 pt slippage.
  * Minute markets: a day enters the close series only if the signal minute has ticks (vol > 0) and a live
    entry minute exists; the entry minute is the first live minute in [signal+1, signal+6)
    (run_index_anomalies.live_at). A forward-filled close is not a close (obvious-impossibility fix).
  * "Exit at day X" = time exit at the open of day X's entry minute (simulate's exit_by_i).
  ATR20 = gjstrat.patterns.daily_table(m).atr20 of the signal day (shifted: known before the day; if the day
  is missing from the daily table, the last earlier value). S&P: live hourly bars grouped into 17:00-17:00 NY
  days (weekday labels), ATR20 = mean(H - L) of the 20 previous days.
  Rollover-spread check: median (ask - bid) at the entry minute vs at 12:00 NY on the same days, per minute
  market, in pips (index points for indices, cents for gold).

DATA GAPS (obvious-impossibility fixes): the close series is split into segments where more than 5 calendar
trading days in a row have no close (Nasdaq 2013, Nikkei 2015, ...). Donchian windows (55 / 20 previous
closes) are computed within a segment. A breakout trade whose exit rule has not fired by the last close of
its segment exits at that close's entry minute ("SEGEND"); one still open at the end of the data exits at the
last close ("END"). The lookbacks L = 21 / 63 / 252 are in calendar trading days: C_{t-L} = the close at
calendar position pos(t) - L, or the latest close in the 5 calendar trading days before it; else undefined.

A. MONTHLY TSMOM (Moskowitz-Ooi-Pedersen; Hurst-Ooi-Pedersen). Both sides on every market, indices included.
  * Rebalance day of a month = its last calendar trading day; if that day has no close, the latest close
    among the 3 calendar trading days before it in the same month; else no rebalance that month.
  * Signal at the rebalance close t: position = sign(ER_L), ER_L = ln(C_t / C_{t-L}) + carry, with
    carry: FX = (r_base - r_quote) * L / 252; XAUUSD = -r_USD * L / 252; Nasdaq and S&P = -r_USD * L / 252;
    Nikkei = -r_JPY * L / 252. Rates: BIS central-bank policy rates (data/extra/policy_rates_bis_daily.csv,
    https://stats.bis.org/api/v1/data/WS_CBPOL/D.US+XM+JP+GB+CH+AU+CA+NZ/all?startPeriod=2009-01-01&format=csv)
    with EUR = ECB deposit facility rate (data/extra/ecb_deposit_rate_daily.csv,
    https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata), latest value dated
    <= t - 1 calendar day, in % / 100.
  * Execution: enter at the rebalance day's entry minute, time exit at the next month's rebalance entry
    minute, then re-enter (every month is one trade). The next rebalance must be in the next calendar month,
    else no trade (data gap). Catastrophe SL 3.0 x ATR20 of the signal day; if stopped, flat until the next
    rebalance. R = 3.0 x ATR20.
  * T1: L = 21. T2: L = 63. T3: L = 252. T4: blend sign(sign21 + sign63 + sign252) (needs all three).

B. DAILY BREAKOUT TREND. Indices long-only (pre-declared, equity premium); both sides on FX and gold.
  * E1 (Turtle System 2): C_t > max(C_{t-55..t-1}) -> long; C_t < min(C_{t-55..t-1}) -> short.
  * E2 (TSMOM-gated): C_t > C_{t-252} AND C_t > max(C_{t-20..t-1}) -> long; mirror for shorts
    (C_{t-252} as in A, price only, no carry).
  * Entry at the signal day's entry minute. Initial hard stop 2.0 x ATR20 (signal day) from the fill,
    checked minute by minute on real bid/ask (S&P: hourly bars). R = this distance.
  * X1 (chandelier): first later signal close with C < max(C since entry, incl. the entry day) - 3.0 x ATR20
    of that day (shorts: C > min(C since entry) + 3.0 x ATR20). Exit at that day's entry minute; the hard
    stop stays.
  * X2 (Donchian): first later close with C < min(previous 20 C) for longs, C > max(previous 20 C) for shorts.
  * No TP. One position per market per variant (signals while in a trade are ignored; no stop-and-reverse).
    Re-entry needs the entry condition true at a close after the exit day. The exit day of a time exit is
    the exit-rule day; of a stop-out it is the first close day whose entry minute is at or after the stop
    minute (the trading day the stop fell in), so the earliest re-entry is the following close.
  * D1 = E1 + X1, D2 = E1 + X2, D3 = E2 + X1, D4 = E2 + X2.
  Implementation: the exit day comes from the close series (path-independent); then
  gjstrat.patterns.simulate(Signal(day, side, entry_i, 'market', None, entry_i + 1, sl_dist=stop,
  tp_dist=None, exit_by_i=exit minute)) checks the hard stop. If the stop hits first the trade ends there.

COSTS (in every result): FX via run_all_matrix.net_r = gjstrat.accounting.account(..., commission=7,
swap=SwapModel.from_fred('rates', 1.0), slippage_pips=0.2) (swap matters for multi-week holds); gold, Nasdaq,
Nikkei via run_all_matrix.net_r (bid/ask fills, NON_FX commission / slippage, 3%/yr financing per rollover
night, long or short); S&P: 1.0 pt round trip + 0.25 pt per stop fill + 3%/yr x calendar nights x entry price.

PERIODS / STATISTICS: run_edge_hunt.PER by signal day: design 2010-17 (indices from data start), check
2018-23, holdout 2024-26; last 3 years = 2023-10-08..2026-10-07. Per test: trades, trades/month (per month
with data), win %, avg win / avg loss, avg R and t per period, last 3 years, skew of R, longest losing streak
(trades, by exit time), average hold days, % stopped.
Reported 8 variants x (each market; asset classes FX majors (7), JPY crosses (2), gold, indices (3); pooled
13 markets; FX-only pooled (9), separate so the gold bull run is not credited to FX). Pooled results use the
month-clustered t (sum of R per calendar month of the signal day, zero for months without trades inside the
data span, t over months) and give the count of markets with avg R > 0, the deepest running-R drawdown of the
pooled sequence (by exit time), the longest losing streak, and the correlation of the T3 and D1 pooled
monthly R (by exit month).

JUDGING (charter bar on the pooled 13-market result per variant): design month-clustered t >= 2 AND avg R > 0
in check AND in holdout. 8 pooled tests -> 8 x 0.006 = 0.05 survivors expected by luck. Per-market charter
results (104 tests, ~0.6 by luck) are shown for information only.
IF A VARIANT SURVIVES: prop sim (gjstrat.prop.prop_table, run_m3_addon.ALPHA rules, normal risk and boost x1.5,
challenges started 2011-2025 and 2018-2025) with run_m3_addon.build_legs() plus the variant's trades on all
13 markets at 0.5% risk per trade (and the variant alone at 0.5%); trades join the USDJPY minute grid at their
UTC times (the run_index_prop.py shift).

ADDED AFTER THE FIRST RUN (reporting only; no rule, variant, market or bar changed): marked-to-market monthly
correlation (the by-exit-month version came out negative, an artefact of booking a whole breakout trade in its
exit month); gross vs cost vs net R per asset class; long vs short split; an independent sanity check of the
TSMOM sign on FRED noon rates (data/extra/DEX*.csv, 7 majors, month-end closes, sign of the 1/3/12-month
log return x next-month log return, no stops, no costs, no carry).

OUTPUT: results/alpha_hunt/trend_follow/REPORT.md, tests.csv, pooled.csv, trades.csv / trades.pkl, spreads.csv.

    python run_alpha_trend_follow.py          # everything (prop sim only if a pooled variant survives)
    python run_alpha_trend_follow.py prop     # prop sim from the saved trades
"""
from __future__ import annotations

import glob
import lzma
import os
import sys
import time
from collections import namedtuple
from datetime import date
from multiprocessing import Pool

import holidays
import numpy as np
import pandas as pd

from gjstrat.data import CANDLE_DTYPE, load_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/trend_follow"
TKY = "Asia/Tokyo"
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
NIK_SWITCH = pd.Timestamp("2024-11-05")
GAP = 5
FX_MAJ = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
JPYX = ["AUDJPY", "EURJPY"]
FX = FX_MAJ + JPYX
INDICES = ["USATECHIDXUSD", "JPNIDXJPY", "USA500IDXUSD"]
MARKETS = FX + ["XAUUSD"] + INDICES
CLS = {**{s: "FX majors" for s in FX_MAJ}, **{s: "JPY crosses" for s in JPYX}, "XAUUSD": "Gold",
       **{s: "Indices" for s in INDICES}}
NAMES = {"USATECHIDXUSD": "Nasdaq 100", "USA500IDXUSD": "S&P 500", "JPNIDXJPY": "Nikkei 225", "XAUUSD": "Gold"}
VARIANTS = {"T1": "TSMOM L=21", "T2": "TSMOM L=63", "T3": "TSMOM L=252", "T4": "TSMOM blend 21/63/252",
            "D1": "Turtle 55 + chandelier 3 ATR", "D2": "Turtle 55 + Donchian 20 exit",
            "D3": "TSMOM-gated 20 + chandelier", "D4": "TSMOM-gated 20 + Donchian 20 exit"}
LBS = (21, 63, 252)


def path_of(sym):
    start = "2011-01-02" if sym in ("USATECHIDXUSD", "JPNIDXJPY") else "2010-01-01"
    return f"data/{sym.lower()}_{start}_2026-10-07.npz"


# --------------------------------------------------------------------------- rates / calendars
_RATES = None


def rates() -> dict[str, pd.Series]:
    global _RATES
    if _RATES is None:
        b = pd.read_csv("data/extra/policy_rates_bis_daily.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
        b["TIME_PERIOD"] = pd.to_datetime(b.TIME_PERIOD)
        out = {}
        for ccy, area in {"USD": "US", "JPY": "JP", "GBP": "GB", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}.items():
            s = b[b.REF_AREA == area].dropna(subset=["OBS_VALUE"]).set_index("TIME_PERIOD").OBS_VALUE.sort_index()
            out[ccy] = s[~s.index.duplicated(keep="last")].astype(float)
        e = pd.read_csv("data/extra/ecb_deposit_rate_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
        e["TIME_PERIOD"] = pd.to_datetime(e.TIME_PERIOD)
        s = e.dropna(subset=["OBS_VALUE"]).set_index("TIME_PERIOD").OBS_VALUE.sort_index()
        out["EUR"] = s[~s.index.duplicated(keep="last")].astype(float)
        _RATES = out
    return _RATES


def rate_before(s: pd.Series, days: pd.DatetimeIndex) -> np.ndarray:
    """Latest value dated <= day - 1 calendar day, as a fraction."""
    q = (days - pd.Timedelta(days=1)).values
    p = np.searchsorted(s.index.values, q, side="right") - 1
    return np.where(p >= 0, s.to_numpy()[np.maximum(p, 0)], np.nan) / 100


def carry(sym: str, days: pd.DatetimeIndex, L: int) -> np.ndarray:
    R = rates()
    f = lambda c: rate_before(R[c], days)
    if sym in FX:
        return (f(sym[:3]) - f(sym[3:])) * L / 252
    if sym == "JPNIDXJPY":
        return -f("JPY") * L / 252
    return -f("USD") * L / 252                     # gold, Nasdaq, S&P


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


# --------------------------------------------------------------------------- features / plan
def lookback(pos: np.ndarray, C: np.ndarray, L: int) -> np.ndarray:
    """C at calendar position pos - L, or the latest close in the 5 calendar trading days before it."""
    target = pos - L
    k = np.searchsorted(pos, target, side="right") - 1
    ok = (k >= 0) & (pos[np.maximum(k, 0)] >= target - 5)
    return np.where(ok, C[np.maximum(k, 0)], np.nan)


def add_features(cs: pd.DataFrame, cal: pd.DatetimeIndex, sym: str) -> pd.DataFrame:
    pos = cal.get_indexer(cs.index)
    assert (pos >= 0).all()
    cs["pos"] = pos
    gap = np.diff(pos, prepend=pos[0] - 1) - 1
    cs["seg"] = np.cumsum(gap > GAP)
    g = cs.C.groupby(cs.seg)
    cs["hi55"] = g.transform(lambda x: x.shift(1).rolling(55).max())
    cs["lo55"] = g.transform(lambda x: x.shift(1).rolling(55).min())
    cs["hi20"] = g.transform(lambda x: x.shift(1).rolling(20).max())
    cs["lo20"] = g.transform(lambda x: x.shift(1).rolling(20).min())
    C = cs.C.to_numpy()
    days = pd.DatetimeIndex(cs.index)
    for L in LBS:
        cs[f"C{L}"] = lookback(pos, C, L)
        cs[f"ER{L}"] = np.log(C / cs[f"C{L}"].to_numpy()) + carry(sym, days, L)
    # rebalance day: last close of the month, at most 3 calendar trading days before the month's last day
    cper = cal.to_period("M")
    last_pos = pd.Series(np.arange(len(cal)), index=cper).groupby(level=0).max()
    per = days.to_period("M")
    is_last = np.r_[per[1:] != per[:-1], True]
    cs["rebal"] = is_last & (pos >= last_pos.reindex(per).to_numpy() - 3)
    return cs


def plan(cs: pd.DataFrame, execute, long_only: bool) -> dict[str, list]:
    """execute(variant, j, jx, side, sl_mult, why) -> (trade, busy index) or None."""
    C, seg, atr = cs.C.to_numpy(), cs.seg.to_numpy(), cs.atr20.to_numpy(dtype=float)
    hi55, lo55, hi20, lo20 = (cs[c].to_numpy(dtype=float) for c in ("hi55", "lo55", "hi20", "lo20"))
    C252 = cs.C252.to_numpy(dtype=float)
    n = len(cs)
    out = {}
    # A. TSMOM
    rb = np.flatnonzero(cs.rebal.to_numpy())
    per = pd.DatetimeIndex(cs.index).to_period("M")
    sg = {L: np.sign(cs[f"ER{L}"].to_numpy(dtype=float)) for L in LBS}
    blend = np.sign(sg[21] + sg[63] + sg[252])
    for v, s in (("T1", sg[21]), ("T2", sg[63]), ("T3", sg[252]), ("T4", blend)):
        tr = []
        for a, b in zip(rb[:-1], rb[1:]):
            if per[b] != per[a] + 1:
                continue
            x = s[a]
            if not np.isfinite(x) or x == 0 or not atr[a] > 0:
                continue
            res = execute(v, a, b, "BUY" if x > 0 else "SELL", 3.0, "REBAL")
            if res is not None:
                tr.append(res[0])
        out[v] = tr
    # B. breakouts
    with np.errstate(invalid="ignore"):
        e1l, e1s = C > hi55, C < lo55
        e2l, e2s = (C > C252) & (C > hi20), (C < C252) & (C < lo20)
    if long_only:
        e1s = e2s = np.zeros(n, dtype=bool)

    def exit_day(j, side, X):
        ext = C[j]
        for k in range(j + 1, n):
            if seg[k] != seg[j]:
                return (k - 1, "SEGEND") if k - 1 > j else None
            if X == "X1":
                a = atr[k]
                if side == "BUY":
                    ext = max(ext, C[k])
                    if C[k] < ext - 3.0 * a:
                        return k, "X1"
                else:
                    ext = min(ext, C[k])
                    if C[k] > ext + 3.0 * a:
                        return k, "X1"
            else:
                if side == "BUY" and C[k] < lo20[k]:
                    return k, "X2"
                if side == "SELL" and C[k] > hi20[k]:
                    return k, "X2"
        return (n - 1, "END") if n - 1 > j else None

    for v, (el, es, X) in {"D1": (e1l, e1s, "X1"), "D2": (e1l, e1s, "X2"), "D3": (e2l, e2s, "X1"),
                           "D4": (e2l, e2s, "X2")}.items():
        busy, tr = -1, []
        for j in np.flatnonzero(el | es):
            if j <= busy or not atr[j] > 0:
                continue
            side = "BUY" if el[j] else "SELL"
            ex = exit_day(j, side, X)
            if ex is None:
                continue
            res = execute(v, j, ex[0], side, 2.0, ex[1])
            if res is None:
                continue
            tr.append(res[0])
            busy = res[1]
        out[v] = tr
    return out


# --------------------------------------------------------------------------- markets
def run_minute(sym: str):
    t0 = time.time()
    m = load_market(path_of(sym))
    d = daily_table(m)
    swap = SwapModel.from_fred("rates", 1.0)
    if sym == "USATECHIDXUSD":
        tz, kind = NY, "nyse"
    elif sym == "JPNIDXJPY":
        tz, kind = TKY, "japan"
    else:
        tz, kind = NY, "weekdays"
    last = m.ts(m.n - 1)
    cal = calendar(kind, m.t0 + pd.Timedelta(days=1), last + pd.offsets.MonthEnd(0))

    def sig_hm(day):
        if sym == "USATECHIDXUSD":
            return 15, 54
        if sym == "JPNIDXJPY":
            return (14, 54) if day < NIK_SWITCH else (15, 24)
        return 16, 44

    rows = []
    for day in cal:
        if day > last:
            break
        hh, mm = sig_hm(day)
        i = local_idx(m, day, hh, mm, tz)
        if i < 0 or i >= m.n - 7 or not m.vol[i] > 0:
            continue
        s = live_at(m, i + 1)
        if s < 0:
            continue
        rows.append((day, i, s, m.bc[i]))
    cs = pd.DataFrame(rows, columns=["day", "i", "s", "C"]).set_index("day")
    atr = d["atr20"]
    cs["atr20"] = atr.reindex(atr.index.union(cs.index)).ffill().reindex(cs.index).to_numpy()
    cs["ts"] = [m.ts(i + 1) for i in cs.i]
    cs = add_features(cs, cal, sym)
    S = cs.s.to_numpy()
    days = cs.index

    # rollover-spread check: entry minute vs 12:00 NY (live minutes only)
    spr_e = (m.ao[S] - m.bo[S]) / m.pip
    noon = np.array([local_idx(m, x, 12, 0, NY) for x in days])
    okn = (noon >= 0) & (noon < m.n)
    noon = noon[okn]
    noon = noon[m.vol[noon] > 0]
    spr_n = (m.ao[noon] - m.bo[noon]) / m.pip
    spreads = {"market": sym, "entry minute": "15:55 NY" if sym == "USATECHIDXUSD" else
               ("14:55/15:25 JST" if sym == "JPNIDXJPY" else "16:45 NY"),
               "median spread at entry (pips/pts)": float(np.median(spr_e)), "median spread at 12:00 NY": float(np.median(spr_n)),
               "p90 spread at entry": float(np.percentile(spr_e, 90)), "p90 spread at 12:00 NY": float(np.percentile(spr_n, 90)),
               "median ATR20 (pips/pts)": float(np.nanmedian(cs.atr20) / m.pip)}

    def execute(v, j, jx, side, slm, why):
        s, x = int(S[j]), int(S[jx])
        sl = slm * cs.atr20.iat[j]
        if x <= s + 1 or x >= m.n or not sl > 0:
            return None
        t = simulate(m, Signal(days[j], side, s, "market", None, s + 1, sl, None, x, v))
        if t is None:
            return None
        k = jx if t.reason != "SL" else int(np.searchsorted(S, t.exit_i, side="left"))
        return (t, why), k

    raw = plan(cs, execute, long_only=sym in INDICES)
    recs = []
    for v, tw in raw.items():
        tw = sorted(tw, key=lambda x: (x[0].exit_i, x[0].entry_i))
        tr = [x[0] for x in tw]
        R = net_r(m, sym, tr, swap)
        for (t, why), r in zip(tw, R):
            recs.append(dict(market=sym, cls=CLS[sym], variant=v, day=t.day, side=t.side, entry_ts=m.ts(t.entry_i),
                             exit_ts=m.ts(t.exit_i), entry=t.entry, exit=t.exit, reason="SL" if t.reason == "SL" else why,
                             risk=t.risk, R_gross=t.r, R=r))
    info = {"market": sym, "closes": len(cs), "segments": int(cs.seg.nunique()), "first close": cs.index[0].date(),
            "last close": cs.index[-1].date(), "months with data": int(pd.DatetimeIndex(cs.index).to_period("M").nunique()),
            "trades": len(recs), "seconds": round(time.time() - t0)}
    print(f"{sym}: {info}", flush=True)
    keep = cs[["C", "ts"]].copy()
    del m, d
    return pd.DataFrame(recs), info, spreads, keep


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


def run_spx():
    sym = "USA500IDXUSD"
    t0 = time.time()
    b = spx_bars()
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    lab = (loc + pd.Timedelta(hours=7)).normalize()
    dd = pd.DataFrame({"high": b.h.to_numpy(), "low": b.l.to_numpy()}, index=lab).groupby(level=0).agg(
        high=("high", "max"), low=("low", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.high - dd.low).rolling(20).mean().shift(1)
    last = loc.max().normalize()
    cal = calendar("nyse", pd.Timestamp("2012-01-01"), last + pd.offsets.MonthEnd(0))
    hr, ldate = loc.hour, loc.normalize()
    c15 = b[hr == 15]
    cs = pd.DataFrame({"C": c15.c.to_numpy(), "start": c15.index}, index=ldate[hr == 15])
    cs = cs[cs.index.isin(cal)]
    cs = cs[~cs.index.duplicated()]
    cs["atr20"] = atr.reindex(atr.index.union(cs.index)).ffill().reindex(cs.index).to_numpy()
    cs["ts"] = cs.start + pd.Timedelta(hours=1)
    cs = add_features(cs, cal, sym)
    starts = b.index.values
    O, Hh, Ll = b.o.to_numpy(), b.h.to_numpy(), b.l.to_numpy()
    TS = cs.ts.values
    days = cs.index

    def execute(v, j, jx, side, slm, why):
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
            nights = (xts.tz_localize("UTC").tz_convert(NY).tz_localize(None).normalize() - days[j]).days
            busy = int(np.searchsorted(TS, xts.to_datetime64(), side="left"))
        else:
            px = Cx - 0.5 if side == "BUY" else Cx + 0.5
            reason, xts = why, cs.ts.iat[jx]
            nights = (days[jx] - days[j]).days
            busy = jx
        gross = (px - entry) if side == "BUY" else (entry - px)
        fin = 0.03 * max(nights, 0) / 365 * entry
        rec = dict(market=sym, cls=CLS[sym], variant=v, day=days[j], side=side, entry_ts=cs.ts.iat[j], exit_ts=xts,
                   entry=entry, exit=px, reason=reason, risk=sl, R_gross=gross / sl, R=(gross - fin) / sl)
        return rec, busy

    raw = plan(cs, execute, long_only=True)
    recs = [t for v in raw.values() for t in v]
    info = {"market": sym, "closes": len(cs), "segments": int(cs.seg.nunique()), "first close": cs.index[0].date(),
            "last close": cs.index[-1].date(), "months with data": int(pd.DatetimeIndex(cs.index).to_period("M").nunique()),
            "trades": len(recs), "seconds": round(time.time() - t0)}
    print(f"{sym}: {info}", flush=True)
    spreads = {"market": sym, "entry minute": "16:00 NY (hourly close)", "median spread at entry (pips/pts)": 1.0,
               "median spread at 12:00 NY": np.nan, "p90 spread at entry": np.nan, "p90 spread at 12:00 NY": np.nan,
               "median ATR20 (pips/pts)": float(np.nanmedian(cs.atr20))}
    return pd.DataFrame(recs), info, spreads, cs[["C", "ts"]].copy()


def run_market(sym):
    return run_spx() if sym == "USA500IDXUSD" else run_minute(sym)


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
    return {"trades": len(r), "win %": (r > 0).mean() * 100 if len(r) else np.nan,
            "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
            "avg R": r.mean() if len(r) else np.nan, "t": tstat(r), "skew": pd.Series(r).skew() if len(r) > 2 else np.nan,
            "longest losing streak": streak(seq), "max running-R DD": max_dd(seq),
            "avg hold days": float(np.mean(hold)) if len(r) else np.nan,
            "SL %": (g.reason == "SL").mean() * 100 if len(g) else np.nan}


def period_masks(day):
    out = {p: (day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)) for p, (a, b) in PER.items()}
    out["last3y"] = (day >= L3[0]) & (day <= L3[1])
    return out


def test_row(g: pd.DataFrame, months: int) -> dict:
    r = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    row = basic(g)
    row["trades/month"] = len(r) / months if months else np.nan
    for p, mk in period_masks(day).items():
        v = r[np.asarray(mk)]
        row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v)})
    row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    return row


def month_series(g: pd.DataFrame, a, b, col="day") -> pd.Series:
    months = pd.period_range(a, b, freq="M")
    x = g[(pd.DatetimeIndex(g[col]) >= a) & (pd.DatetimeIndex(g[col]) <= b)]
    return x.groupby(pd.DatetimeIndex(x[col]).to_period("M")).R.sum().reindex(months, fill_value=0.0)


def pooled_row(g: pd.DataFrame, span, per_market: pd.DataFrame) -> dict:
    row = basic(g)
    nmon = len(pd.period_range(span[0], span[1], freq="M"))
    row["trades/month"] = len(g) / nmon
    row["month t (all)"] = tstat(month_series(g, span[0], span[1]).to_numpy())
    day = pd.DatetimeIndex(g.day)
    pers = dict(PER)
    pers["last3y"] = (str(L3[0].date()), str(L3[1].date()))
    for p, (a, b) in pers.items():
        a, b = max(pd.Timestamp(a), span[0]), min(pd.Timestamp(b), span[1])
        x = g[np.asarray((day >= a) & (day <= b))]
        row.update({f"{p} n": len(x), f"{p} avg R": x.R.mean() if len(x) else np.nan, f"{p} t": tstat(x.R.to_numpy()),
                    f"{p} month t": tstat(month_series(x, a, b).to_numpy()) if len(x) else np.nan})
    row["markets"] = len(per_market)
    row["markets avg R > 0"] = int((per_market["avg R"] > 0).sum())
    row["passes bar"] = bool(row["design month t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    return row


def mtm_months(tr: pd.DataFrame, closes: pd.DataFrame) -> pd.Series:
    """Monthly R of every trade marked to market at each signal close (UTC month of the close), costs on the
    exit. Sum over the trades."""
    cts, cpx = closes.ts.values.astype("datetime64[ns]"), closes.C.to_numpy()
    out = {}
    for t in tr.itertuples():
        e, x = pd.Timestamp(t.entry_ts).to_datetime64(), pd.Timestamp(t.exit_ts).to_datetime64()
        a, z = np.searchsorted(cts, e, side="right"), np.searchsorted(cts, x, side="left")
        ts = np.r_[cts[a:z], x]
        px = np.r_[t.entry, cpx[a:z], t.exit]
        inc = (1.0 if t.side == "BUY" else -1.0) * np.diff(px) / t.risk
        inc[-1] += t.R - t.R_gross
        for mth, v in zip(pd.DatetimeIndex(ts).to_period("M"), inc):
            out[mth] = out.get(mth, 0.0) + v
    return pd.Series(out, dtype=float)


FRED = {"EURUSD": "DEXUSEU", "GBPUSD": "DEXUSUK", "USDJPY": "DEXJPUS", "USDCHF": "DEXSZUS", "AUDUSD": "DEXUSAL",
        "USDCAD": "DEXCAUS", "NZDUSD": "DEXUSNZ"}


def fred_check() -> pd.DataFrame:
    """No-stop, no-cost monthly TSMOM on FRED noon rates (independent data source), 7 majors."""
    rows, pool = [], {1: [], 3: [], 12: []}
    for pair, sid in FRED.items():
        df = pd.read_csv(f"data/extra/{sid}.csv", parse_dates=["observation_date"])
        s_ = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy(), index=df.observation_date).dropna()
        me = np.log(s_[s_.index >= "2009-01-01"].resample("ME").last())
        nxt = me.shift(-1) - me
        row = {"pair": pair}
        for L in (1, 3, 12):
            x = (np.sign(me - me.shift(L)) * nxt).dropna()
            x = x[x.index >= "2010-01-01"]
            row.update({f"L={L}m mean %/month": x.mean() * 100, f"L={L}m t": tstat(x.to_numpy())})
            pool[L].append(x)
        rows.append(row)
    row = {"pair": "pooled 7 (equal weight)"}
    for L in (1, 3, 12):
        x = pd.concat(pool[L], axis=1).mean(axis=1)
        row.update({f"L={L}m mean %/month": x.mean() * 100, f"L={L}m t": tstat(x.to_numpy())})
    rows.append(row)
    return pd.DataFrame(rows).set_index("pair")


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
        names.append(f"{v} ({VARIANTS[v]}) 13 markets")
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
    txt = ("\n## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)\n\nBasket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + "
           "M-3 USDJPY 3% (run_m3_addon.build_legs); the surviving variant's trades on all 13 markets added at 0.5% risk "
           "per trade (and alone at 0.5%).\n\n" + fmt_table(P[cols], ".1f") + "\n")
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write(txt)
    print(P[cols].round(1).to_string())
    return P


# --------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    rates()
    with Pool(2) as pool:
        res = pool.map(run_market, MARKETS, chunksize=1)
    T = pd.concat([r[0] for r in res], ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T["hold days"] = (pd.DatetimeIndex(T.exit_ts) - pd.DatetimeIndex(T.entry_ts)) / pd.Timedelta(days=1)
    T.to_pickle(f"{OUT}/trades.pkl")
    T.to_csv(f"{OUT}/trades.csv", index=False)
    INFO = pd.DataFrame([r[1] for r in res]).set_index("market")
    SPR = pd.DataFrame([r[2] for r in res]).set_index("market")
    CLOSES = {sym: r[3] for sym, r in zip(MARKETS, res)}
    INFO.to_csv(f"{OUT}/data_info.csv")
    SPR.to_csv(f"{OUT}/spreads.csv")
    first = {s: pd.Timestamp(INFO.loc[s, "first close"]) for s in MARKETS}
    lastc = {s: pd.Timestamp(INFO.loc[s, "last close"]) for s in MARKETS}

    # per market x variant
    rows = []
    for sym in MARKETS:
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            rows.append({"market": sym, "class": CLS[sym], "variant": v, **test_row(g, INFO.loc[sym, "months with data"])})
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT}/tests.csv", index=False)

    # pooled groups
    groups = {"ALL 13": MARKETS, "FX only (9)": FX, "FX majors (7)": FX_MAJ, "JPY crosses (2)": JPYX, "Gold": ["XAUUSD"],
              "Indices (3)": INDICES}
    prow = []
    for gname, mk in groups.items():
        span = (min(first[s] for s in mk), max(lastc[s] for s in mk))
        for v in VARIANTS:
            g = T[(T.market.isin(mk)) & (T.variant == v)]
            pm = R[(R.market.isin(mk)) & (R.variant == v)]
            prow.append({"group": gname, "variant": v, **pooled_row(g, span, pm)})
    PL = pd.DataFrame(prow)
    PL.to_csv(f"{OUT}/pooled.csv", index=False)
    ALL = PL[PL.group == "ALL 13"].set_index("variant")
    surv = [v for v in VARIANTS if ALL.loc[v, "passes bar"]]

    # correlation T3 vs D1 pooled monthly R (by exit month), plus by-year pooled
    span_all = (min(first.values()), max(lastc.values()))
    ms = lambda v, mk=MARKETS: month_series(T[(T.variant == v) & T.market.isin(mk)].assign(
        xd=pd.DatetimeIndex(T[(T.variant == v) & T.market.isin(mk)].exit_ts)), span_all[0], span_all[1] + pd.offsets.MonthEnd(1), col="xd")
    months_all = pd.period_range(span_all[0], span_all[1], freq="M")
    mtm = {(v, sym): mtm_months(T[(T.variant == v) & (T.market == sym)], CLOSES[sym]) for v in ("T3", "T4", "D1", "D3")
           for sym in MARKETS}
    mm = lambda v, mk=MARKETS: sum(mtm[(v, s_)].reindex(months_all, fill_value=0.0) for s_ in mk)
    ss = lambda v, mk=MARKETS: month_series(T[(T.variant == v) & T.market.isin(mk)], span_all[0], span_all[1])
    pairs = (("T3", "D1"), ("T4", "D1"), ("T3", "D3"))
    corr = pd.DataFrame({
        "13 mkts, marked to market": [mm(a).corr(mm(b)) for a, b in pairs],
        "FX only, marked to market": [mm(a, FX).corr(mm(b, FX)) for a, b in pairs],
        "13 mkts, by signal month": [ss(a).corr(ss(b)) for a, b in pairs],
        "13 mkts, by exit month": [ms(a).corr(ms(b)) for a, b in pairs],
        "FX only, by exit month": [ms(a, FX).corr(ms(b, FX)) for a, b in pairs]},
        index=[f"{a} vs {b}" for a, b in pairs])
    corr.index.name = "monthly R correlation"
    YR = T.groupby(["variant", pd.DatetimeIndex(T.day).year]).R.sum().unstack().reindex(list(VARIANTS))
    YR.columns = [str(c) for c in YR.columns]
    YR.index.name = "variant (sum R, 13 markets)"
    YR.to_csv(f"{OUT}/by_year_sumR.csv")
    YRf = T[T.market.isin(FX)].groupby(["variant", pd.DatetimeIndex(T[T.market.isin(FX)].day).year]).R.sum().unstack().reindex(list(VARIANTS))
    YRf.columns = [str(c) for c in YRf.columns]
    YRf.index.name = "variant (sum R, FX 9)"
    # costs, sides, FRED check
    T["cost"] = T.R - T.R_gross
    CO = T.groupby(["variant", "cls"]).agg(gross=("R_gross", "mean"), cost=("cost", "mean"), net=("R", "mean")).unstack("cls")
    CO.columns = [f"{c} {k}" for k, c in CO.columns]
    CO = CO[[f"{c} {k}" for c in ("FX majors", "JPY crosses", "Gold", "Indices") for k in ("gross", "cost", "net")]]
    CO = CO.reindex(list(VARIANTS))
    CO.index.name = "variant (avg R per trade)"
    SD = T.assign(grp=np.where(T.market.isin(FX), "FX", np.where(T.market == "XAUUSD", "gold", "indices"))).groupby(
        ["variant", "grp", "side"]).R.agg(["size", "mean"]).unstack(["grp", "side"])
    SD.columns = [f"{g} {sd} {k.replace('size', 'n').replace('mean', 'avg R')}" for k, g, sd in SD.columns]
    SD = SD[sorted(SD.columns)].reindex(list(VARIANTS))
    for c in [c for c in SD.columns if c.endswith(" n")]:
        SD[c] = [("" if pd.isna(x) else str(int(x))) for x in SD[c]]
    SD.index.name = "variant"
    FC = fred_check()
    # exit reasons
    RS = T.groupby(["variant", "reason"]).size().unstack(fill_value=0).reindex(list(VARIANTS))
    RS.index.name = "variant"

    # ------------------------------------------------------------------ report
    n_tests = len(VARIANTS)
    s_list = ", ".join(f"{v} ({VARIANTS[v]})" for v in surv) or "none"
    pm_surv = R[R.survives]
    pcols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t (all)", "skew",
             "design n", "design avg R", "design t", "design month t", "check n", "check avg R", "check month t",
             "holdout n", "holdout avg R", "holdout month t", "last3y n", "last3y avg R", "last3y month t",
             "markets avg R > 0", "longest losing streak", "max running-R DD", "avg hold days", "SL %", "passes bar"]

    def ptab(gname):
        x = PL[PL.group == gname].set_index("variant")[pcols].copy()
        x.index = [f"{v} {VARIANTS[v]}" for v in x.index]
        x.index.name = "variant"
        return fmt_table(x, ".3f")

    mcols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "skew", "design n", "design avg R",
             "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n",
             "last3y avg R", "last3y t", "longest losing streak", "avg hold days", "SL %", "survives"]

    def mtab(v):
        x = R[R.variant == v].set_index("market")[mcols].copy()
        x.index.name = "market"
        return fmt_table(x, ".3f")

    heat = R.pivot(index="market", columns="variant", values="avg R").reindex(MARKETS)
    heat.index.name = "avg R (all periods)"
    heat_l3 = R.pivot(index="market", columns="variant", values="last3y avg R").reindex(MARKETS)
    heat_l3.index.name = "last-3y avg R"
    txt = ["# Alpha hunt: trend following (`trend_follow`) - monthly TSMOM + daily Turtle / chandelier breakouts\n",
           "Rules, variants and the survival bar are in the docstring of `run_alpha_trend_follow.py` (fixed before running). "
           "13 markets (7 FX majors, AUDJPY, EURJPY, gold, Nasdaq 100, Nikkei 225, S&P 500 hourly), all costs included "
           "(FX: $7/lot + 0.2 pip + swap with 1% markup; gold / indices: 3%/yr financing per night). Periods: design 2010-17 "
           "(indices from data start), check 2018-23, holdout 2024-26 (by signal day); last 3 years = 2023-10-08..2026-10-07.\n",
           f"**Judged tests: {n_tests} (pooled 13-market result per variant). Survivors of the charter bar (design month-clustered "
           f"t >= 2, check and holdout avg R > 0): {len(surv)} ({s_list}). Expected by luck: {n_tests * 0.006:.2f}.**\n",
           f"Per-market tests (information only): {len(R)}; passing the charter bar: {len(pm_surv)} "
           f"({', '.join(f'{a} {b}' for a, b in zip(pm_surv.market, pm_surv.variant)) or 'none'}); expected by luck "
           f"{len(R) * 0.006:.2f}.\n",
           "## Pooled, all 13 markets (the judged tests)\n",
           "month t = month-clustered t (sum of R per calendar month of the signal day, zero for months without trades, "
           "t over months). design t / check t columns elsewhere are trade-level. max running-R DD = deepest drop of the "
           "cumulative R of all trades in exit order (at 0.5% risk per trade multiply by 0.5 for %, ignoring compounding).\n",
           ptab("ALL 13"), "\n",
           "## FX only (9 pairs; gold excluded so its bull run is not credited to FX)\n", ptab("FX only (9)"), "\n",
           "## By asset class\n"]
    for gname in ("FX majors (7)", "JPY crosses (2)", "Gold", "Indices (3)"):
        txt += [f"### {gname}\n", ptab(gname), "\n"]
    txt += ["## Avg R per market x variant (all periods)\n", fmt_table(heat, ".3f"), "\n",
            "## Last-3-year avg R per market x variant\n", fmt_table(heat_l3, ".3f"), "\n",
            "## Correlation of pooled monthly R\n",
            "Marked to market = every open trade revalued at each signal close and summed by calendar month (costs on the "
            "exit), the fair way to compare a monthly-rebalanced book with weeks-long breakout trades. By exit month books "
            "a whole breakout trade in the month it closes, usually the month its trend reverses, which biases the "
            "correlation downwards.\n", fmt_table(corr, ".2f"), "\n",
            "## Gross vs cost vs net (avg R per trade)\n", fmt_table(CO, ".3f"), "\n",
            "## Long vs short\n", "Indices trade short only in T1-T4 (D variants are long-only on indices).\n",
            fmt_table(SD, ".3f"), "\n",
            "## Independent check: FX TSMOM on FRED noon rates (no stops, no costs, no carry), 2010-2026\n",
            "Sign of the trailing 1/3/12-month log return x the next month's log return, month-end FRED closes.\n",
            fmt_table(FC, ".3f"), "\n",
            "## Sum of R per signal year, all 13 markets\n", fmt_table(YR, ".1f"), "\n",
            "## Sum of R per signal year, FX only\n", fmt_table(YRf, ".1f"), "\n",
            "## Exit reasons (trades)\n",
            "REBAL = monthly time exit; X1 = chandelier; X2 = Donchian-20; SL = hard / catastrophe stop; SEGEND = data gap; "
            "END = end of data.\n", fmt_table(RS, ".0f"), "\n",
            "## Rollover-spread check (median spread at the entry minute vs 12:00 NY, same days)\n",
            "FX in pips, gold in cents, indices in index points. S&P is hourly bid only: 1.0 pt round trip is assumed.\n",
            fmt_table(SPR, ".2f"), "\n",
            "## Data used\n", fmt_table(INFO, ".0f"), "\n",
            "## Per market, by variant\n"]
    for v in VARIANTS:
        txt += [f"### {v}: {VARIANTS[v]}\n", mtab(v), "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(PL[["group", "variant", "trades", "win %", "avg win / avg loss", "avg R", "design avg R", "design month t",
              "check avg R", "holdout avg R", "last3y avg R", "markets avg R > 0", "passes bar"]].round(3).to_string())
    print(heat.round(3).to_string())
    print(SPR.round(2).to_string())
    print(corr.round(2).to_string())
    print("survivors:", s_list, flush=True)
    print(f"main done in {time.time() - t_start:.0f}s", flush=True)
    if surv:
        prop(surv)
    print("DONE", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prop":
        PLs = pd.read_csv(f"{OUT}/pooled.csv")
        s = PLs[(PLs.group == "ALL 13") & PLs["passes bar"]].variant.tolist()
        prop(s)
        print("DONE", flush=True)
    else:
        main()
