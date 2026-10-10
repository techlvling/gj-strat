"""Event-driven simulation of the IST 05:00-06:00 GBPJPY range breakout.

Each IST trading day runs its own little state machine:

    RANGE (05:00-05:59) -> PENDING OCO (06:00-10:59) -> TRADE 1 -> [WAIT 6 bars -> PENDING -> TRADE 2]

Days never share state, so an open trade never blocks the next day. The event loop walks
from event to event; finding "the next bar where something happens" is done with numpy
over a chunk of bars instead of a Python loop per minute (same result, ~100x faster).

Price conventions (decided with the user):
  * range and re-entry extremes use BID candles
  * buy stop triggers when ASK high >= level and fills at ask; long exits are on BID
  * sell stop triggers when BID low <= level and fills at bid; short exits are on ASK
  * gap through a stop (order or SL/BE) -> fill at that bar's open
  * at 06:00, a level already crossed at the open -> fill at market at the 06:00 open
  * re-entry stop already crossed when placed -> skipped and counted
  * same bar touches SL and TP/BE trigger -> SL first
  * entry bar: SL can be hit, TP/BE cannot (order within a bar unknown -> conservative)
  * BE trigger bar: the moved stop is live from the next bar
  * TP is a limit: fills at the TP price, no positive slippage on gaps
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import Market

PIP = 0.01          # JPY-pair pip; Market.pip holds the actual pip of each pair
EPS = 1e-7          # price-comparison tolerance (data has 0.001 resolution)
IST = pd.Timedelta(hours=5, minutes=30)


@dataclass(frozen=True)
class Params:
    rr: float = 4.0
    sl_pips: float = 30.0
    be_trigger: float | None = 3.0     # in R; None = break-even off
    be_plus: float = 5.0               # pips beyond entry for the moved stop
    version: str = "A"                 # A: re-entry at 6-bar extreme, B: at original range level,
                                       # C: fade - first break is virtual, trade its SL (A re-entry)
                                       # W: weekly-breakout bias - one side only, one trade, no re-entry
    reentry_wait: int = 6
    box_start_min: int = 300           # box start, minutes after IST midnight of the trading day (05:00)
    box_len: int = 60                  # box length in minutes
    order_hours: float = 5.0           # orders live this long after the box closes (06:00 -> 11:00)
    min_box_rel: float | None = None   # set: skip the day if its box < k x median box of the
    box_lookback: int = 20             #   previous `box_lookback` valid days (needs a full window)
    sl_box_mult: float | None = None   # set: SL = mult x that day's box (+ spread) instead of sl_pips;
                                       # the BE offset scales the same way (be_plus / sl_pips of it)
    fade_expiry_11: bool = True        # C: reversal stop expires at 11:00 (False: lives with virtual trade)

    def __post_init__(self):
        if self.be_trigger is not None and self.be_trigger >= self.rr:
            raise ValueError("BE trigger must be < RR")

    @property
    def be_label(self) -> str:
        return "off" if self.be_trigger is None else f"{self.be_trigger:g}R+{self.be_plus:g}"

    @property
    def label(self) -> str:
        v = self.version + ("" if self.version != "C" or self.fade_expiry_11 else "-noexp")
        sl = f"{self.sl_pips:g}" if self.sl_box_mult is None else f"box{self.sl_box_mult:g}"
        return f"RR{self.rr:g}_SL{sl}_BE{self.be_label}_{v}"


@dataclass
class Trade:
    day: pd.Timestamp          # IST trading date
    side: str                  # BUY / SELL
    num: int                   # 1 or 2
    entry_i: int
    entry: float
    exit_i: int
    exit: float
    reason: str                # TP / SL / BE / OPEN_AT_END
    risk: float                # price distance of 1R (SL pips + entry spread)
    spread: float              # entry spread (price)
    range_pips: float
    gap_fill: bool             # entry filled at a bar open beyond the level
    be_moved: bool

    @property
    def r(self) -> float:
        d = self.exit - self.entry if self.side == "BUY" else self.entry - self.exit
        return d / self.risk


@dataclass
class Counters:
    days_total: int = 0                 # Mon-Fri IST dates in the window
    skipped_no_data: int = 0            # market closed / no file (holidays)
    skipped_incomplete: int = 0         # some minutes of the range window had no ticks
    traded_days: int = 0                # days that got a valid range and orders
    initial_expired: int = 0            # neither 06:00 stop filled by 11:00
    open_fill_0600: int = 0             # level already crossed at 06:00 -> market fill
    reentry_considered: int = 0         # SL/BE exits before 11:00
    reentry_skipped_time: int = 0       # 6-bar wait ends at/after 11:00
    reentry_skipped_invalid: int = 0    # price already beyond level when placing
    reentry_expired: int = 0            # re-entry stop not filled by 11:00
    reentry_filled: int = 0
    exit_after_11_no_reentry: int = 0   # SL/BE exit at/after 11:00
    fade_cancel_tp: int = 0             # C: virtual breakout hit TP -> reversal cancelled
    fade_cancel_be: int = 0             # C: virtual breakout hit BE stop -> reversal cancelled
    fade_cancel_open: int = 0           # C: virtual breakout still open at data end
    fade_expired: int = 0               # C: virtual SL hit at/after 11:00 -> reversal stop expired
    fade_filled: int = 0                # C: reversal trades opened
    fade_same_bar: int = 0              # C: reversal filled on the very bar that broke the range
    w_no_bias: int = 0                  # W: no weekly bias -> no trade
    w_buy_days: int = 0                 # W: buy stop only
    w_sell_days: int = 0                # W: sell stop only
    skipped_small_box: int = 0          # box < min_box_rel x recent median box
    skipped_dates: list = field(default_factory=list)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d.pop("skipped_dates")
        return d


# --------------------------------------------------------------------------- helpers
def _first(mask_fn, start: int, end: int) -> int:
    """First index i in [start, end) where mask_fn(slice) is True, else -1.
    Scans in growing chunks so short trades stay cheap and long ones stay vectorised."""
    s, chunk = start, 256
    while s < end:
        e = min(s + chunk, end)
        m = mask_fn(slice(s, e))
        if m.any():
            return s + int(np.argmax(m))
        s, chunk = e, min(chunk * 4, 65536)
    return -1


def find_entry(m: Market, start: int, end: int, buy_lvl: float | None,
               sell_lvl: float | None) -> tuple[str, int, float, bool] | None:
    """First fill of the buy stop and/or sell stop in bars [start, end)."""
    bl, ah, ao, bo = m.bl, m.ah, m.ao, m.bo
    if buy_lvl is not None and sell_lvl is not None:
        fn = lambda s: (ah[s] >= buy_lvl - EPS) | (bl[s] <= sell_lvl + EPS)
    elif buy_lvl is not None:
        fn = lambda s: ah[s] >= buy_lvl - EPS
    else:
        fn = lambda s: bl[s] <= sell_lvl + EPS
    i = _first(fn, start, end)
    if i < 0:
        return None
    buy_hit = buy_lvl is not None and ah[i] >= buy_lvl - EPS
    sell_hit = sell_lvl is not None and bl[i] <= sell_lvl + EPS
    if buy_hit and sell_hit:
        # both stops inside one candle: whichever is beyond at the open went first,
        # otherwise the level nearer the open
        buy_over = ao[i] - buy_lvl
        sell_over = sell_lvl - bo[i]
        if buy_over >= 0 or sell_over >= 0:
            side = "BUY" if buy_over >= sell_over else "SELL"
        else:
            side = "BUY" if -buy_over <= -sell_over else "SELL"
    else:
        side = "BUY" if buy_hit else "SELL"
    if side == "BUY":
        gap = ao[i] > buy_lvl + EPS
        return side, i, (ao[i] if gap else buy_lvl), gap
    gap = bo[i] < sell_lvl - EPS
    return side, i, (bo[i] if gap else sell_lvl), gap


def manage(m: Market, side: str, ei: int, entry: float, risk: float,
           p: Params, be_offset: float | None = None) -> tuple[int, float, str, bool]:
    """Run an open position to its exit. Returns (exit_i, exit_price, reason, be_moved)."""
    n = m.n
    if side == "BUY":
        lo, hi, op = m.bl, m.bh, m.bo           # long exits on bid
        sl, tp = entry - risk, entry + p.rr * risk
        be_lvl = None if p.be_trigger is None else entry + p.be_trigger * risk
        be_stop = entry + (p.be_plus * m.pip if be_offset is None else be_offset)
        adverse = lambda s, lvl: lo[s] <= lvl + EPS
        favour = lambda s, lvl: hi[s] >= lvl - EPS
        gapped = lambda i, lvl: op[i] < lvl - EPS
    else:
        lo, hi, op = m.al, m.ah, m.ao           # short exits on ask
        sl, tp = entry + risk, entry - p.rr * risk
        be_lvl = None if p.be_trigger is None else entry - p.be_trigger * risk
        be_stop = entry - (p.be_plus * m.pip if be_offset is None else be_offset)
        adverse = lambda s, lvl: hi[s] >= lvl - EPS
        favour = lambda s, lvl: lo[s] <= lvl + EPS
        gapped = lambda i, lvl: op[i] > lvl + EPS

    # entry bar: only the stop can be hit (it's the stop level, never a gap — we are inside the bar)
    if adverse(slice(ei, ei + 1), sl)[0]:
        return ei, sl, "SL", False

    # phase 1: original stop, TP, BE trigger
    trig = tp if be_lvl is None else be_lvl          # be_lvl < tp, so it is reached first
    j = _first(lambda s: adverse(s, sl) | favour(s, trig), ei + 1, n)
    if j < 0:
        return n - 1, (m.bc if side == "BUY" else m.ac)[n - 1], "OPEN_AT_END", False
    if gapped(j, sl):
        return j, op[j], "SL", False
    if adverse(slice(j, j + 1), sl)[0]:
        return j, sl, "SL", False                    # SL first if both in one bar
    if favour(slice(j, j + 1), tp)[0]:
        return j, tp, "TP", False
    # BE triggered on bar j; moved stop is live from j+1
    k = _first(lambda s: adverse(s, be_stop) | favour(s, tp), j + 1, n)
    if k < 0:
        return n - 1, (m.bc if side == "BUY" else m.ac)[n - 1], "OPEN_AT_END", True
    if gapped(k, be_stop):
        return k, op[k], "BE", True
    if adverse(slice(k, k + 1), be_stop)[0]:
        return k, be_stop, "BE", True
    return k, tp, "TP", True


# --------------------------------------------------------------------------- day loop
def trading_days(m: Market, start: str | None = None, end: str | None = None) -> list[pd.Timestamp]:
    """Mon-Fri IST dates whose 05:00-11:00 IST window lies inside the data."""
    first = (m.t0 + IST).normalize() + pd.Timedelta(days=1)
    last = (m.ts(m.n - 1) + IST).normalize()
    if (m.ts(m.n - 1) + IST) < last + pd.Timedelta(hours=11):
        last -= pd.Timedelta(days=1)
    days = pd.date_range(first, last, freq="D")
    if start:
        days = days[days >= pd.Timestamp(start)]
    if end:
        days = days[days <= pd.Timestamp(end)]
    return [d for d in days if d.dayofweek < 5]


def run(m: Market, p: Params, days: list[pd.Timestamp] | None = None,
        max_missing: int = 0, bias: dict | None = None) -> tuple[list[Trade], Counters]:
    """bias: {IST day: 'BUY' | 'SELL' | None}, required for Version W (see gjstrat.bias)."""
    if p.version == "W" and bias is None:
        raise ValueError("Version W needs a bias map (gjstrat.bias.weekly_bias)")
    days = trading_days(m) if days is None else days
    c = Counters()
    recent_boxes: list[float] = []                        # valid days' box sizes, oldest first
    trades: list[Trade] = []
    for day in days:
        c.days_total += 1
        rs = m.idx(day + pd.Timedelta(minutes=p.box_start_min) - IST)   # default 05:00 IST
        bl_ = p.box_len
        place, expiry = rs + bl_, rs + bl_ + int(round(p.order_hours * 60))   # 06:00 / 11:00 IST
        if rs < 0 or expiry >= m.n:
            c.skipped_no_data += 1
            continue
        vol = m.vol[rs:rs + bl_]
        live = int((vol > 0).sum())
        if live == 0:
            c.skipped_no_data += 1
            c.skipped_dates.append((day.date(), "no data"))
            continue
        if bl_ - live > max_missing:
            c.skipped_incomplete += 1
            c.skipped_dates.append((day.date(), f"{bl_ - live} empty minutes in range"))
            continue
        hi = float(m.bh[rs:rs + bl_].max())
        lo = float(m.bl[rs:rs + bl_].min())
        if hi <= lo:                                      # flat box (e.g. a holiday): nothing to trade
            c.skipped_incomplete += 1
            c.skipped_dates.append((day.date(), "flat range"))
            continue
        c.traded_days += 1
        range_pips = (hi - lo) / m.pip
        if p.min_box_rel is not None:
            window = recent_boxes[-p.box_lookback:]
            recent_boxes.append(hi - lo)
            if len(window) == p.box_lookback and hi - lo < p.min_box_rel * float(np.median(window)):
                c.skipped_small_box += 1
                continue
        if p.sl_box_mult is None:
            sl_dist, be_off = p.sl_pips * m.pip, p.be_plus * m.pip
        else:
            sl_dist = p.sl_box_mult * (hi - lo)
            be_off = sl_dist * p.be_plus / p.sl_pips

        buy_lvl, sell_lvl = hi, lo
        if p.version == "W":
            b = bias.get(day)
            if b is None:
                c.w_no_bias += 1
                continue
            if b == "BUY":
                sell_lvl = None
                c.w_buy_days += 1
            else:
                buy_lvl = None
                c.w_sell_days += 1
        hit = find_entry(m, place, expiry, buy_lvl, sell_lvl)
        if hit is None:
            c.initial_expired += 1
            continue
        side, ei, px, gap = hit
        if ei == place and gap:
            c.open_fill_0600 += 1
        if p.version == "C":
            # the breakout is virtual: its stop-loss price is where the real, opposite trade starts
            vrisk = sl_dist + max(m.ao[ei] - m.bo[ei], 0.0)
            vxi, vxp, vreason, _ = manage(m, side, ei, px, vrisk, p, be_off)
            if vreason != "SL":
                if vreason == "TP":
                    c.fade_cancel_tp += 1
                elif vreason == "BE":
                    c.fade_cancel_be += 1
                else:
                    c.fade_cancel_open += 1
                continue
            if p.fade_expiry_11 and vxi >= expiry:
                c.fade_expired += 1
                continue
            vsl = px + vrisk if side == "SELL" else px - vrisk
            c.fade_filled += 1
            c.fade_same_bar += vxi == ei
            gap = abs(vxp - vsl) > EPS            # virtual stop gapped -> reversal fills at the open
            side, ei, px = ("BUY" if side == "SELL" else "SELL"), vxi, vxp
        num = 1
        while True:
            spread = max(m.ao[ei] - m.bo[ei], 0.0)
            risk = sl_dist + spread
            xi, xp, reason, be_moved = manage(m, side, ei, px, risk, p, be_off)
            trades.append(Trade(day, side, num, ei, px, xi, xp, reason, risk, spread,
                                range_pips, gap, be_moved))
            if reason not in ("SL", "BE") or num == 2 or p.version == "W":
                break
            if xi >= expiry:
                c.exit_after_11_no_reentry += 1
                break
            c.reentry_considered += 1
            q = xi + p.reentry_wait                       # window = bars xi .. xi+5
            if q >= expiry:
                c.reentry_skipped_time += 1
                break
            if side == "BUY":                             # stopped out long -> sell stop
                ext = float(m.bl[xi:q].min())
                lvl = ext if (p.version in ("A", "C") and ext < lo) else lo
                if m.bo[q] <= lvl + EPS:
                    c.reentry_skipped_invalid += 1
                    break
                hit = find_entry(m, q, expiry, None, lvl)
            else:                                         # stopped out short -> buy stop
                ext = float(m.bh[xi:q].max())
                lvl = ext if (p.version in ("A", "C") and ext > hi) else hi
                if m.ao[q] >= lvl - EPS:
                    c.reentry_skipped_invalid += 1
                    break
                hit = find_entry(m, q, expiry, lvl, None)
            if hit is None:
                c.reentry_expired += 1
                break
            c.reentry_filled += 1
            side, ei, px, gap = hit
            num = 2
    return trades, c
