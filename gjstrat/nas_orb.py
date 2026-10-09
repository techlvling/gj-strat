"""Nas100 15-minute opening-range breakout (New York cash open), as written by the user.

  1. Range = highest high / lowest low of 09:30:00-09:44:59 New York (15 one-minute bars).
  2. From 09:45, 5-minute candles (09:45, 09:50, ... 10:55; the last one closes at 11:00).
     The first one that closes outside the range is the signal; one signal per day.
  3. Close above the high = BUY, below the low = SELL.
  4. Entry at the next candle's open. If that open is back inside the range, skip the day.
  5. Stop at the opposite edge of the range. 6. R = |entry - stop|, target = entry +- 2R.
  7. Anything still open is closed at the 11:30 open.

Fill conventions (same as gjstrat/patterns.py):
  * range and candle closes use BID candles (what a chart shows)
  * buys fill on ASK and exit on BID; sells fill on BID and exit on ASK, so a sell's stop at the
    range high triggers when the ask reaches it
  * market entry / time exit and stop fills get `slip` points of slippage against the trade;
    a stop gapped through fills at the bar open (minus slippage); the target is a limit and fills
    at its price
  * stop and target touched in the same minute -> stop first
Days: Mon-Fri New York dates, NYSE holidays skipped, and days where any of the 15 range minutes
had no ticks skipped.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

import numpy as np
import pandas as pd
from pandas.tseries.holiday import (GoodFriday, USLaborDay, USMartinLutherKingJr, USMemorialDay,
                                    USPresidentsDay, USThanksgivingDay)

from .data import Market
from .patterns import NY, local_idx

# one-off NYSE closures (Hurricane Sandy, national days of mourning)
SPECIAL_CLOSURES = ["2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09"]


def _observed(d: pd.Timestamp) -> pd.Timestamp:
    """Saturday -> Friday, Sunday -> Monday."""
    return d - pd.Timedelta(days=1) if d.dayofweek == 5 else (
        d + pd.Timedelta(days=1) if d.dayofweek == 6 else d)


def nyse_holidays(y0: int, y1: int) -> set[pd.Timestamp]:
    out = {pd.Timestamp(s) for s in SPECIAL_CLOSURES}
    for rule in (USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, USLaborDay,
                 USThanksgivingDay):
        out.update(rule.dates(f"{y0}-01-01", f"{y1}-12-31"))
    for y in range(y0, y1 + 1):
        ny = pd.Timestamp(f"{y}-01-01")
        if ny.dayofweek != 5:                 # NYSE does not close the Friday before a Saturday New Year
            out.add(_observed(ny))
        out.add(_observed(pd.Timestamp(f"{y}-07-04")))
        out.add(_observed(pd.Timestamp(f"{y}-12-25")))
        if y >= 2022:
            out.add(_observed(pd.Timestamp(f"{y}-06-19")))
    return out


def trading_days(start: date, end: date) -> list[pd.Timestamp]:
    hol = nyse_holidays(start.year, end.year)
    return [d for d in pd.date_range(start, end, freq="B") if d not in hol]


@dataclass
class OrbParams:
    range_minutes: int = 15        # 09:30 + this
    candle: int = 5                # signal candle length (minutes)
    last_signal: tuple = (10, 55)  # last signal candle opens here (closes 11:00)
    exit_at: tuple = (11, 30)      # flat at this bar's open
    rr: float = 2.0
    skip_if_back_inside: bool = True
    slip: float = 1.0              # index points per market / stop fill


@dataclass
class OrbTrade:
    day: pd.Timestamp
    side: str
    range_hi: float
    range_lo: float
    signal_i: int                  # first minute of the signal candle
    entry_i: int
    entry: float
    stop: float
    target: float
    exit_i: int
    exit: float
    reason: str                    # TP / SL / TIME
    spread: float                  # ask - bid at the entry open
    gap: bool = False              # stop filled at a bar open beyond it

    @property
    def risk_pts(self) -> float:
        return abs(self.entry - self.stop)

    @property
    def pnl_pts(self) -> float:
        return self.exit - self.entry if self.side == "BUY" else self.entry - self.exit


@dataclass
class OrbCounters:
    days: int = 0
    no_data: int = 0               # some range minute had no ticks (or outside the data)
    no_signal: int = 0
    back_inside: int = 0
    traded: int = 0
    skipped: list = field(default_factory=list)


def run_day(m: Market, day: pd.Timestamp, p: OrbParams) -> tuple[str, OrbTrade | None]:
    a = local_idx(m, day, 9, 30, NY)
    r_end = a + p.range_minutes
    x = local_idx(m, day, *p.exit_at, NY)
    if a < 0 or x >= m.n or not (m.vol[a:r_end] > 0).all():
        return "no_data", None
    hi, lo = m.bh[a:r_end].max(), m.bl[a:r_end].min()
    last = local_idx(m, day, *p.last_signal, NY)
    for s in range(r_end, last + 1, p.candle):
        c = m.bc[s + p.candle - 1]
        if c > hi:
            side = "BUY"
        elif c < lo:
            side = "SELL"
        else:
            continue
        e = s + p.candle
        if p.skip_if_back_inside and (lo <= m.bo[e] <= hi):
            return "back_inside", None
        return "traded", _trade(m, day, side, hi, lo, s, e, x, p)
    return "no_signal", None


def _trade(m, day, side, hi, lo, s, e, x, p: OrbParams) -> OrbTrade:
    spread = max(m.ao[e] - m.bo[e], 0.0)
    if side == "BUY":
        entry = m.ao[e] + p.slip
        stop = lo
        tgt = entry + p.rr * (entry - stop)
        lo_, hi_, op = m.bl, m.bh, m.bo
        hit_stop = lambda i: lo_[i] <= stop
        hit_tgt = lambda i: hi_[i] >= tgt
        sign = 1.0
    else:
        entry = m.bo[e] - p.slip
        stop = hi
        tgt = entry - p.rr * (stop - entry)
        lo_, hi_, op = m.al, m.ah, m.ao
        hit_stop = lambda i: hi_[i] >= stop
        hit_tgt = lambda i: lo_[i] <= tgt
        sign = -1.0
    mk = lambda xi, xp, why, gap=False: OrbTrade(day, side, hi, lo, s, e, entry, stop, tgt, xi, xp,
                                                 why, spread, gap)
    if sign * (entry - stop) <= 0:            # entry at/through the stop (cannot happen with the
        return mk(e, entry, "SL")             # back-inside skip on; kept for the variant without it)
    for i in range(e, x):
        if hit_stop(i):
            gapped = sign * (op[i] - stop) < 0
            px = (op[i] if gapped else stop) - sign * p.slip
            return mk(i, px, "SL", gapped)
        if hit_tgt(i):
            return mk(i, tgt, "TP")
    return mk(x, op[x] - sign * p.slip, "TIME")


def run(m: Market, p: OrbParams, days: list[pd.Timestamp]) -> tuple[list[OrbTrade], OrbCounters]:
    c = OrbCounters()
    out = []
    for d in days:
        c.days += 1
        what, t = run_day(m, d, p)
        setattr(c, what, getattr(c, what) + 1)
        if what == "no_data":
            c.skipped.append(d)
        if t is not None:
            out.append(t)
    return out, c


# --------------------------------------------------------------------------- costs / sizing
@dataclass
class Account:
    """Prop account rules for the sizing in rule 8 and the challenge simulation."""
    name: str
    start: float
    max_loss: float                # cushion at the start
    trailing: bool                 # end-of-day trailing floor (stops at the starting balance)
    daily_limit: float
    target: float                  # profit to pass
    point_value: float             # USD per index point per contract / lot
    step: float                    # contract size increment (1 = whole contracts)
    commission: float              # USD per contract round turn
    risk_frac: float = 0.025       # of the remaining cushion (capped by the daily allowance)
    est_slip: float = 1.0          # points of stop slippage assumed when sizing
    target2: float = 0.0           # phase 2 profit target on a fresh balance; 0 = one phase
    daily_frac: float = 0.0        # daily limit as a fraction of the day's starting balance
                                   # (used instead of daily_limit when > 0)
    min_days: int = 0              # trading days needed in each phase


def planned_loss(t: OrbTrade, acc: Account) -> float:
    """USD lost per contract if the stop fills with the estimated slippage, fees included."""
    return (t.risk_pts + acc.est_slip) * acc.point_value + acc.commission


def net_r(t: OrbTrade, acc: Account) -> float:
    """Trade result in units of its planned loss (per contract, so independent of rounding)."""
    return (t.pnl_pts * acc.point_value - acc.commission) / planned_loss(t, acc)


def size(t: OrbTrade, acc: Account, cushion: float, daily_left: float) -> float:
    """Rule 8 read as: planned loss <= 2.5% of the remaining cushion, and never more than the
    remaining daily loss allowance. Whole steps, rounded down; 0 = skip the trade."""
    budget = min(acc.risk_frac * cushion, daily_left)
    n = np.floor(budget / planned_loss(t, acc) / acc.step + 1e-9) * acc.step
    return float(n) if n >= acc.step - 1e-12 else 0.0


def challenge(trades: list[OrbTrade], acc: Account, k0: int, fixed_risk: float | None = None) -> dict:
    """Play the account forward from trade k0. Sizing is rule 8, or `fixed_risk` x balance when
    given (capped by the daily allowance in both cases). Closed P/L only: one trade a day, so the
    daily limit can only be breached by that trade. With target2 a passed phase 1 restarts on a
    fresh balance for phase 2."""
    phase, taken, skipped = 1, 0, 0
    bal, floor, days = acc.start, acc.start - acc.max_loss, 0
    for k in range(k0, len(trades)):
        t = trades[k]
        daily = acc.daily_frac * bal if acc.daily_frac > 0 else acc.daily_limit
        if fixed_risk is None:
            n = size(t, acc, bal - floor, daily)
        else:
            n = size(t, replace(acc, risk_frac=1.0), fixed_risk * bal, daily)
        if n == 0:
            skipped += 1
            continue
        pnl = n * (t.pnl_pts * acc.point_value - acc.commission)
        bal += pnl
        taken += 1
        days += 1
        if pnl <= -daily:
            return dict(result="fail: daily", phase=phase, taken=taken, skipped=skipped, end_k=k)
        if bal <= floor:
            return dict(result="fail: max loss", phase=phase, taken=taken, skipped=skipped, end_k=k)
        target = acc.target if phase == 1 else acc.target2
        if bal >= acc.start + target and days >= acc.min_days:
            if phase == 1 and acc.target2 > 0:
                phase, bal, floor, days = 2, acc.start, acc.start - acc.max_loss, 0
                continue
            return dict(result="pass", phase=phase, taken=taken, skipped=skipped, end_k=k)
        if acc.trailing:
            floor = min(max(floor, bal - acc.max_loss), acc.start)
    return dict(result="unfinished", phase=phase, taken=taken, skipped=skipped, end_k=len(trades) - 1)
