"""Indicators, the 1H trend filter and 15m leg ("prey") detection.

Every array value at index i uses only bars <= i, i.e. it is known at the CLOSE of bar i.
Prices are BID candles (the chart price); fills use bid/ask in the engine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK = 8          # closed 15m candles in the leg window


def ema(x: np.ndarray, n: int) -> np.ndarray:
    """EMA with alpha 2/(n+1), seeded with the SMA of the first n values (NaN before)."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder ATR, seeded with the mean of the first n true ranges (NaN before)."""
    prev = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - prev), np.abs(l - prev)]), axis=0)
    out = np.full(len(h), np.nan)
    if len(h) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(h)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def trend_1h(hourly: pd.DataFrame, ema_n: int = 50, slope_bars: int = 5, atr_n: int = 14,
             slope_k: float = 0.1) -> np.ndarray:
    """+1 = buys allowed (close > EMA and EMA rose by > k*ATR over the last `slope_bars` bars),
    -1 = sells allowed (mirror), 0 = flat. One value per (closed) 1H bar."""
    c = hourly["c"].to_numpy(float)
    e = ema(c, ema_n)
    a = atr(hourly["h"].to_numpy(float), hourly["l"].to_numpy(float), c, atr_n)
    slope = e - np.r_[np.full(slope_bars, np.nan), e[:-slope_bars]]
    up = (c > e) & (slope > slope_k * a)
    dn = (c < e) & (slope < -slope_k * a)
    return np.where(up, 1, np.where(dn, -1, 0)).astype(np.int8)


def hourly_to_15m(t15: pd.DatetimeIndex, hourly_index: pd.DatetimeIndex, values: np.ndarray,
                  fill=0) -> np.ndarray:
    """Value of the latest 1H bar that has CLOSED by the close of each 15m bar.
    15m bar opening at t closes at t+15m; 1H bar labelled h closes at h+1h, so it is usable iff
    h + 1h <= t + 15m."""
    cutoff = (pd.DatetimeIndex(t15) + pd.Timedelta(minutes=15) - pd.Timedelta(hours=1)).as_unit("ns").asi8
    pos = np.searchsorted(pd.DatetimeIndex(hourly_index).as_unit("ns").asi8, cutoff, side="right") - 1
    out = np.where(pos >= 0, values[np.clip(pos, 0, None)], fill)
    return out


def legs(bh: np.ndarray, bl: np.ndarray, atr15: np.ndarray, min_atr: float = 2.0,
         lookback: int = LOOKBACK) -> dict[str, np.ndarray]:
    """Leg detection at the close of every 15m bar i, using the `lookback` closed candles
    i-lookback+1 .. i (the completion candle i included).

    BUY leg completes at i when candle i fails to make a higher high than i-1 (bh[i] <= bh[i-1])
    and the window's highest high H was made by candle i-1 (strictly above every earlier high
    in the window). L = lowest low of the window candles BEFORE the H candle. Valid if
    H - L >= min_atr * ATR15[i]. SELL is the mirror (lows / highs swapped).
    """
    n = len(bh)
    k = lookback - 2                      # candles before the extreme candle in the window
    out = {key: np.full(n, np.nan) for key in ("buy_H", "buy_L", "sell_H", "sell_L")}
    out["buy"] = np.zeros(n, bool)
    out["sell"] = np.zeros(n, bool)
    if n < lookback:
        return out
    # sliding windows over candles i-7 .. i-2 (the `k` candles before candle i-1)
    win_h = np.lib.stride_tricks.sliding_window_view(bh, k)      # row j covers j .. j+k-1
    win_l = np.lib.stride_tricks.sliding_window_view(bl, k)
    i = np.arange(lookback - 1, n)
    j = i - (lookback - 1)                                        # window start = i-7
    prior_hi, prior_lo = win_h[j].max(axis=1), win_l[j].min(axis=1)
    peak = bh[i - 1]
    trough = bl[i - 1]
    a = atr15[i]
    with np.errstate(invalid="ignore"):
        buy = (bh[i] <= bh[i - 1]) & (peak > prior_hi) & (peak - prior_lo >= min_atr * a)
        sell = (bl[i] >= bl[i - 1]) & (trough < prior_lo) & (prior_hi - trough >= min_atr * a)
    out["buy"][i] = buy
    out["buy_H"][i], out["buy_L"][i] = peak, prior_lo
    out["sell"][i] = sell
    out["sell_H"][i], out["sell_L"][i] = prior_hi, trough
    return out
