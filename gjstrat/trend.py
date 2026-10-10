"""Daily trend following across the 28 FX pairs (vectorised, daily bars).

Data: Dukascopy yearly files of daily candles (UTC midnight to midnight), BID and ASK:
    https://datafeed.dukascopy.com/datafeed/{SYM}/{YYYY}/{BID|ASK}_candles_day_1.bi5
Only Monday-Friday bars are used, so Monday's return (Friday close -> Monday close) includes the
Sunday evening session.

Conventions (no look-ahead):
  * a signal is computed from closes up to and including day t and traded at day t's close
  * position weight w = fraction of equity in notional, sign = side; returns are mid-close to
    mid-close, so day t+1's P/L is w_t x r_{t+1}
  * size = (per-pair vol target) / (60-day stdev of daily returns, up to day t), set when the
    position is opened or flipped (T2, T3) or at each monthly rebalance (T1), then held fixed
  * cost per unit of |change in w|: half the bid/ask spread (20-day median of close spreads)
    + commission ($7 per 100k round turn = 0.35 bp a side) + `slip_pips` pips, all over the mid
  * carry: w x (base rate - quote rate) per calendar day held (weekends included); a broker
    swap markup on |w| is booked separately (`markup`), using the same central-bank / interbank rates as gjstrat/swap.py
"""
from __future__ import annotations

import lzma
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from .data import BASE_URL, CANDLE_DTYPE, _fetch, pip_size, price_scale

TRADING_DAYS = 252


# --------------------------------------------------------------------------- data
def _day_url(sym: str, year: int, side: str) -> str:
    return f"{BASE_URL}/{sym}/{year}/{side}_candles_day_1.bi5"


def download_daily(syms: list[str], years: range, raw_dir: str, workers: int = 4) -> None:
    os.makedirs(raw_dir, exist_ok=True)
    jobs = [(_day_url(s, y, side), os.path.join(raw_dir, f"{s}_{y}_{side}_day.bi5"))
            for s in syms for y in years for side in ("BID", "ASK")]
    with requests.Session() as sess, ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda j: _fetch(sess, *j), jobs))
    print(f"daily candles: {len(jobs)} files, {res.count('ok')} downloaded, "
          f"{res.count('cached')} cached, {res.count('404')} not on server", flush=True)


def _decode_year(path: str, sym: str, year: int) -> pd.DataFrame | None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    raw = lzma.decompress(open(path, "rb").read())
    if not raw:
        return None
    rec = np.frombuffer(raw, dtype=CANDLE_DTYPE)
    idx = pd.Timestamp(f"{year}-01-01") + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
    sc = price_scale(sym)
    return pd.DataFrame({"o": rec["o"] / sc, "h": rec["h"] / sc, "l": rec["l"] / sc,
                         "c": rec["c"] / sc, "v": rec["v"].astype(np.float64)}, index=idx)


def load_daily(syms: list[str], years: range, raw_dir: str) -> dict[str, pd.DataFrame]:
    """Per pair: Mon-Fri daily bars with bid close `c`, ask close `ac`, mid close `mid`."""
    out = {}
    for s in syms:
        side = {}
        for sd in ("BID", "ASK"):
            frames = [f for y in years
                      if (f := _decode_year(os.path.join(raw_dir, f"{s}_{y}_{sd}_day.bi5"), s, y)) is not None]
            side[sd] = pd.concat(frames).sort_index() if frames else None
        if side["BID"] is None or side["ASK"] is None:
            continue
        b, a = side["BID"], side["ASK"]
        d = b[["o", "h", "l", "c", "v"]].join(a[["c"]].rename(columns={"c": "ac"}), how="inner")
        d = d[(d.index.dayofweek < 5)]
        d = d[d.v > 0] if (d.v > 0).any() else d
        d["mid"] = (d.c + d.ac) / 2
        out[s] = d
    return out


# --------------------------------------------------------------------------- signals
def tsmom_targets(close: pd.Series, lookback: int) -> pd.Series:
    """+1/-1 by the sign of the past `lookback`-day return, set on each month's last trading day
    and held to the next month end (NaN before the first rebalance)."""
    sig = np.sign(close / close.shift(lookback) - 1)
    month_end = close.index.to_series().groupby([close.index.year, close.index.month]).transform("max")
    rebal = close.index == month_end.to_numpy()
    s = pd.Series(np.where(rebal, sig, np.nan), index=close.index)
    s[rebal & sig.isna().to_numpy()] = 0.0
    return s.ffill()


def ma_cross(close: pd.Series, fast: int, slow: int) -> pd.Series:
    f, s = close.rolling(fast).mean(), close.rolling(slow).mean()
    return pd.Series(np.where(s.isna(), np.nan, np.sign(f - s)), index=close.index)


def donchian(close: pd.Series, entry: int, exit_: int) -> pd.Series:
    """Long on a close above the prior `entry`-day high close, short below the prior low close;
    a long exits on a close below the prior `exit_`-day low close (short: above the high)."""
    hi_e, lo_e = close.shift(1).rolling(entry).max(), close.shift(1).rolling(entry).min()
    hi_x, lo_x = close.shift(1).rolling(exit_).max(), close.shift(1).rolling(exit_).min()
    c = close.to_numpy()
    pos = np.full(len(c), np.nan)
    cur = 0.0
    for i in range(len(c)):
        if np.isnan(hi_e.iat[i]):
            continue
        if cur > 0 and c[i] < lo_x.iat[i]:
            cur = 0.0
        elif cur < 0 and c[i] > hi_x.iat[i]:
            cur = 0.0
        if c[i] > hi_e.iat[i]:
            cur = 1.0
        elif c[i] < lo_e.iat[i]:
            cur = -1.0
        pos[i] = cur
    return pd.Series(pos, index=close.index)


# --------------------------------------------------------------------------- backtest
def weights(signal: pd.Series, vol: pd.Series, target: float, resize_on: pd.Series | None = None) -> pd.Series:
    """Signal -> held notional weight. The size (target / vol) is fixed when the signal changes
    (or on `resize_on` days) and held until the next change."""
    sig = signal.fillna(0.0)
    change = sig.ne(sig.shift(1).fillna(0.0))
    if resize_on is not None:
        change |= resize_on.fillna(False).astype(bool)
    size = (target / vol).where(change).ffill()
    w = (sig * size).fillna(0.0)
    return w.where(sig != 0, 0.0)


def pair_returns(d: pd.DataFrame, w: pd.Series, sym: str, rates: dict[str, pd.Series] | None,
                 markup_pct: float = 1.0, commission_bp: float = 0.35, slip_pips: float = 0.2,
                 ) -> pd.DataFrame:
    """Daily P/L of holding weight `w` (decided at each close) as a fraction of equity."""
    mid = d["mid"]
    r = mid.pct_change()
    held = w.shift(1).fillna(0.0)
    gross = held * r
    spread = (d.ac - d.c).clip(lower=0).rolling(20, min_periods=1).median()
    unit_cost = (spread / 2 + slip_pips * pip_size(sym)) / mid + commission_bp / 1e4
    cost = w.diff().abs().fillna(w.abs()) * unit_cost
    carry = markup = pd.Series(0.0, index=d.index)
    if rates is not None:
        days = d.index.to_series().diff().dt.days.fillna(1).to_numpy()
        base, quote = sym[:3], sym[3:]
        rb = rates[base].reindex(rates[base].index.union(d.index)).ffill().reindex(d.index)
        rq = rates[quote].reindex(rates[quote].index.union(d.index)).ffill().reindex(d.index)
        diff = (rb - rq).shift(1).fillna(0.0)
        carry = held * diff / 100 * days / 365
        markup = held.abs() * markup_pct / 100 * days / 365
    return pd.DataFrame({"gross": gross.fillna(0.0), "cost": cost, "carry": carry, "markup": markup,
                         "net": gross.fillna(0.0) - cost + carry - markup, "w": w,
                         "turnover": w.diff().abs()})


def sharpe_t(x: pd.Series) -> tuple[float, float]:
    x = x.dropna()
    if len(x) < 2 or x.std() == 0:
        return np.nan, np.nan
    sr = x.mean() / x.std() * np.sqrt(TRADING_DAYS)
    return sr, x.mean() / x.std() * np.sqrt(len(x))


def max_dd(x: pd.Series) -> float:
    eq = x.cumsum()
    return float((eq.cummax() - eq).max())
