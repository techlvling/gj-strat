"""Weekly-breakout direction bias (Version W).

Rules agreed with the user:
  * daily candles close at 17:00 New York (standard forex day; 21:00 or 22:00 UTC with US DST)
  * a daily close above last week's high -> BUY only; below last week's low -> SELL only;
    back inside last week's range -> no bias. The most recent daily close decides.
  * only daily closes from the *current* week count: Monday's box (Sunday 23:30 UTC) has no
    closed daily candle of the new week yet, so Monday never has a bias
  * no bias -> no trade that day
Built from BID candles, minutes with real ticks only.
"""
from __future__ import annotations

import pandas as pd

from .data import Market

NY = "America/New_York"


def daily_bars(m: Market) -> pd.DataFrame:
    """Mon-Fri daily bars labelled by the New York date on which they close at 17:00."""
    live = m.vol > 0
    ts = (m.t0 + pd.to_timedelta(pd.Series(range(m.n))[live].to_numpy(), unit="min"))
    ny = pd.DatetimeIndex(ts).tz_localize("UTC").tz_convert(NY)
    label = (ny + pd.Timedelta(hours=7)).tz_localize(None).normalize()   # 17:00 NY -> next date
    df = pd.DataFrame({"high": m.bh[live], "low": m.bl[live], "close": m.bc[live]}, index=label)
    d = df.groupby(level=0).agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    d = d[d.index.dayofweek < 5]                      # stray weekend ticks are not a trading day
    d["week"] = d.index - pd.to_timedelta(d.index.dayofweek, unit="D")
    return d


def weekly_bias(m: Market, days: list[pd.Timestamp]) -> dict[pd.Timestamp, str | None]:
    """Bias for each IST trading day's 05:00 box: 'BUY', 'SELL' or None."""
    d = daily_bars(m)
    wk = d.groupby("week").agg(high=("high", "max"), low=("low", "min"))
    weeks = list(wk.index)
    out: dict[pd.Timestamp, str | None] = {}
    for day in days:
        week = day - pd.Timedelta(days=day.dayofweek)
        prev = [w for w in weeks if w < week]
        # daily candles of this week already closed before the box (label <= day - 1)
        closed = d[(d.week == week) & (d.index < day)]
        if not prev or closed.empty:
            out[day] = None
            continue
        pwh, pwl = wk.loc[prev[-1], "high"], wk.loc[prev[-1], "low"]
        c = closed["close"].iloc[-1]
        out[day] = "BUY" if c > pwh else "SELL" if c < pwl else None
    return out
