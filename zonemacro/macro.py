"""Macro bias (3 fixed inputs) and the day filters used by the backtest.

Timing (no look-ahead):
  * A daily series value dated d is usable from UTC day d+1.
  * CPI (first release only) published on day r is usable from UTC day r+1.
  * The bias is decided at the close of each weekday D using only values usable on D, and
    applies to the next calendar day(s): trading day T uses the decision of the last weekday
    before T. So T sees daily observations dated <= T-2 and CPI released <= T-2 (both lags
    stacked, as agreed).

Inputs, each scored on its change over the last 63 trading days (weekdays, values carried
forward over holidays):
  1. DGS2 - DFF               rising +1 (USD-bullish), falling -1, unchanged/unknown 0
  2. DGS10 - foreign 10y      (JGB10 for USDJPY, BUND10 for EURUSD) widening +1, narrowing -1
  3. US CPI YoY (first release of month m / first release of month m-12)  rising +1, falling -1
>= 2 inputs at +1 -> USD strong (+1); >= 2 at -1 -> USD weak (-1); otherwise no trade (0).

Day filters are arrays over calendar days with codes:  2 both sides, 1 buys only,
-1 sells only, 0 no trade.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK = 63
FOREIGN = {"USDJPY": "JGB10", "EURUSD": "BUND10"}
# pair side taken when USD is strong: +1 = buy pair (demand zones), -1 = sell pair (supply zones)
USD_STRONG_SIDE = {"USDJPY": +1, "EURUSD": -1}
BOTH, NONE = 2, 0


def usable_values(values: pd.Series, usable_from: pd.Series, days: pd.DatetimeIndex) -> np.ndarray:
    """Value usable on each day: the latest value whose usable_from <= day (NaN before any)."""
    src = pd.DataFrame({"u": pd.to_datetime(usable_from).to_numpy(),
                        "v": np.asarray(values, dtype=float)}).dropna().sort_values("u")
    src = src.drop_duplicates("u", keep="last")
    q = pd.DataFrame({"d": days})
    out = pd.merge_asof(q, src, left_on="d", right_on="u", direction="backward")
    return out["v"].to_numpy()


def daily_usable(df: pd.DataFrame, days: pd.DatetimeIndex) -> np.ndarray:
    """Daily series (columns date, value): value dated d usable from d + 1 day."""
    return usable_values(df["value"], df["date"] + pd.Timedelta(days=1), days)


def cpi_yoy_first_release(cpi: pd.DataFrame) -> pd.DataFrame:
    """YoY % from first-release values only: first(m) / first(m-12) - 1. Published (and so
    knowable) on the release date of month m."""
    s = cpi.set_index("month")["value"]
    prev = s.reindex(s.index - pd.DateOffset(years=1)).to_numpy()
    out = pd.DataFrame({"month": s.index, "yoy": (s.to_numpy() / prev - 1) * 100,
                        "release_date": cpi.set_index("month")["release_date"].to_numpy()})
    return out.dropna().reset_index(drop=True)


def sign_score(x: np.ndarray) -> np.ndarray:
    s = np.sign(x)
    s[np.isnan(s)] = 0
    return s.astype(int)


def change_score(x: np.ndarray, lookback: int = LOOKBACK) -> np.ndarray:
    ch = np.full(len(x), np.nan)
    ch[lookback:] = x[lookback:] - x[:-lookback]
    return sign_score(ch)


def decision_days(start: str, end: str) -> pd.DatetimeIndex:
    d = pd.date_range(start, end, freq="D")
    return d[d.dayofweek < 5]


def macro_bias(src: dict[str, pd.DataFrame], pair: str, start: str, end: str) -> pd.DataFrame:
    """One row per weekday decision day D (values usable on D)."""
    days = decision_days(start, end)
    dgs2, dff = daily_usable(src["DGS2"], days), daily_usable(src["DFF"], days)
    dgs10, fy = daily_usable(src["DGS10"], days), daily_usable(src[FOREIGN[pair]], days)
    yoy = cpi_yoy_first_release(src["CPI_FIRST"])
    cpi = usable_values(yoy["yoy"], yoy["release_date"] + pd.Timedelta(days=1), days)
    s1 = change_score(dgs2 - dff)
    s2 = change_score(dgs10 - fy)
    s3 = change_score(cpi)
    pos = (np.stack([s1, s2, s3]) == 1).sum(0)
    neg = (np.stack([s1, s2, s3]) == -1).sum(0)
    bias = np.where(pos >= 2, 1, np.where(neg >= 2, -1, 0))
    agree = np.where(bias == 1, pos, np.where(bias == -1, neg, 0))
    return pd.DataFrame({"rate_spread": dgs2 - dff, "yield_gap": dgs10 - fy, "cpi_yoy": cpi,
                         "s_rate": s1, "s_gap": s2, "s_cpi": s3, "usd_bias": bias,
                         "n_agree": agree}, index=days)


# --------------------------------------------------------------------------- day filters
class DayFilter:
    """Calendar-day lookup of the allowed side. code[k] applies to UTC day day0 + k."""

    def __init__(self, day0: pd.Timestamp, code: np.ndarray, score: np.ndarray | None = None,
                 name: str = ""):
        self.day0 = pd.Timestamp(day0)
        self.code = np.asarray(code, dtype=np.int8)
        self.score = np.zeros(len(code), np.int8) if score is None else np.asarray(score, np.int8)
        self.name = name

    def day_index(self, ts_ns: np.ndarray) -> np.ndarray:
        return ((np.asarray(ts_ns, dtype=np.int64) - self.day0.value) // 86_400_000_000_000).astype(np.int64)


def apply_next_day(decisions: pd.Series, day0: str, day1: str) -> np.ndarray:
    """Each calendar day T takes the decision of the last weekday decision day strictly before T."""
    cal = pd.date_range(day0, day1, freq="D")
    dec = decisions.sort_index()
    q = pd.DataFrame({"d": cal - pd.Timedelta(days=1)})
    src = pd.DataFrame({"u": dec.index, "v": dec.to_numpy()})
    out = pd.merge_asof(q, src, left_on="d", right_on="u", direction="backward")
    return out["v"].fillna(0).to_numpy()


def macro_filter(bias: pd.DataFrame, pair: str, day0: str, day1: str) -> DayFilter:
    side = bias["usd_bias"] * USD_STRONG_SIDE[pair]
    code = apply_next_day(side, day0, day1)
    score = apply_next_day(bias["n_agree"], day0, day1)
    return DayFilter(pd.Timestamp(day0), code, score, "macro")


def no_filter(day0: str, day1: str) -> DayFilter:
    n = len(pd.date_range(day0, day1, freq="D"))
    return DayFilter(pd.Timestamp(day0), np.full(n, BOTH), name="none")


def trend_filter(daily_close: pd.Series, day0: str, day1: str, n: int = 200) -> DayFilter:
    """Close above its 200-day average at the close of weekday D -> buys only from D+1."""
    sma = daily_close.rolling(n, min_periods=n).mean()
    dec = pd.Series(np.sign(daily_close - sma).fillna(0).to_numpy(), index=daily_close.index)
    return DayFilter(pd.Timestamp(day0), apply_next_day(dec, day0, day1), name="trend")


def random_filter(macro_bias_side: pd.Series, day0: str, day1: str, seed: int) -> DayFilter:
    """Each decision day drawn independently as buy / sell / none with the same proportions
    as the real macro filter's decisions (pair-side terms) over the backtest period."""
    vals = macro_bias_side.to_numpy()
    p = np.array([(vals == 1).mean(), (vals == -1).mean(), (vals == 0).mean()])
    rng = np.random.default_rng(seed)
    draw = rng.choice(np.array([1, -1, 0]), size=len(vals), p=p / p.sum())
    dec = pd.Series(draw, index=macro_bias_side.index)
    return DayFilter(pd.Timestamp(day0), apply_next_day(dec, day0, day1), name=f"random{seed}")
