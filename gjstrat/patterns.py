"""General single-trade simulator and pattern signal builders (beyond the box breakout).

A signal says: side, when the order goes live, how it fills (market / limit / stop), SL and TP
distances from the fill, and a time exit. The simulator applies the engine's conventions:
  * buys fill on ASK, exit on BID; sells fill on BID, exit on ASK
  * market orders fill at the bar open; limits fill at the level (or a better open); stops at the
    level (or a worse open on a gap)
  * stop and target in one bar -> stop first; on the fill bar only the stop can be hit
  * time exit at the open of the time-exit bar
All times are UTC minute indices into the Market grid.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Market
from .engine import EPS, Trade, _first

NY = "America/New_York"


@dataclass
class Signal:
    day: pd.Timestamp
    side: str                 # BUY / SELL
    start_i: int              # first bar the order is live
    kind: str                 # market / limit / stop
    level: float | None       # limit/stop price (ask for buys, bid for sells); None for market
    expiry_i: int             # order cancelled at this bar if unfilled
    sl_dist: float            # price distance from the fill
    tp_dist: float | None     # None = no target
    exit_by_i: int            # time exit at this bar's open
    tag: str = ""


def _fill(m: Market, s: Signal) -> tuple[int, float] | None:
    if s.kind == "market":
        i = s.start_i
        return i, (m.ao[i] if s.side == "BUY" else m.bo[i])
    end = min(s.expiry_i, m.n)
    L = s.level
    if s.side == "BUY":
        if s.kind == "limit":
            i = _first(lambda sl: m.al[sl] <= L + EPS, s.start_i, end)
            return None if i < 0 else (i, min(L, m.ao[i]))
        i = _first(lambda sl: m.ah[sl] >= L - EPS, s.start_i, end)
        return None if i < 0 else (i, max(L, m.ao[i]))
    if s.kind == "limit":
        i = _first(lambda sl: m.bh[sl] >= L - EPS, s.start_i, end)
        return None if i < 0 else (i, max(L, m.bo[i]))
    i = _first(lambda sl: m.bl[sl] <= L + EPS, s.start_i, end)
    return None if i < 0 else (i, min(L, m.bo[i]))


def simulate(m: Market, s: Signal) -> Trade | None:
    if s.start_i < 0 or s.exit_by_i >= m.n:
        return None                                  # signal outside the data
    f = _fill(m, s)
    if f is None:
        return None
    ei, px = f
    if ei >= s.exit_by_i:
        return None
    if s.side == "BUY":
        lo, hi, op = m.bl, m.bh, m.bo
        sl, tp = px - s.sl_dist, None if s.tp_dist is None else px + s.tp_dist
        adverse = lambda sl_: lo[sl_] <= sl + EPS
        favour = (lambda sl_: hi[sl_] >= tp - EPS) if tp is not None else None
        gapped = lambda i: op[i] < sl - EPS
    else:
        lo, hi, op = m.al, m.ah, m.ao
        sl, tp = px + s.sl_dist, None if s.tp_dist is None else px - s.tp_dist
        adverse = lambda sl_: hi[sl_] >= sl - EPS
        favour = (lambda sl_: lo[sl_] <= tp + EPS) if tp is not None else None
        gapped = lambda i: op[i] > sl + EPS
    spread = max(m.ao[ei] - m.bo[ei], 0.0)
    mk = lambda xi, xp, why: Trade(s.day, s.side, 1, ei, px, xi, xp, why, s.sl_dist, spread, 0.0,
                                   False, False)
    if adverse(slice(ei, ei + 1))[0]:
        return mk(ei, sl, "SL")
    end = min(s.exit_by_i, m.n - 1)
    fn = (lambda sl_: adverse(sl_) | favour(sl_)) if favour else adverse
    j = _first(fn, ei + 1, end)
    if j < 0:
        return mk(end, (m.bo if s.side == "BUY" else m.ao)[end], "TIME")
    if gapped(j):
        return mk(j, op[j], "SL")
    if adverse(slice(j, j + 1))[0]:
        return mk(j, sl, "SL")
    return mk(j, tp, "TP")


# --------------------------------------------------------------------------- shared helpers
def daily_table(m: Market) -> pd.DataFrame:
    """New York-close daily bars (bid) with session start/end indices and prior-day context."""
    from .bias import daily_bars
    d = daily_bars(m)[["high", "low", "close"]].copy()
    end_utc = (d.index + pd.Timedelta(hours=17)).tz_localize(NY).tz_convert("UTC").tz_localize(None)
    start_utc = ((d.index - pd.Timedelta(days=1)) + pd.Timedelta(hours=17)).tz_localize(NY) \
        .tz_convert("UTC").tz_localize(None)
    d["start_i"] = ((start_utc - m.t0) // pd.Timedelta(minutes=1)).astype(int)
    d["end_i"] = ((end_utc - m.t0) // pd.Timedelta(minutes=1)).astype(int)
    d["prev_high"], d["prev_low"], d["prev_close"] = d.high.shift(1), d.low.shift(1), d.close.shift(1)
    d["atr20"] = (d.high - d.low).rolling(20).mean().shift(1)          # known before the day starts
    d["sma50"] = d.close.rolling(50).mean().shift(1)
    d["sma50_prev"] = d["sma50"].shift(5)
    return d.dropna()


def bars(m: Market, minutes: int) -> dict[str, np.ndarray]:
    """Bid OHLC aggregated to `minutes`-bars aligned to the grid (t0 is midnight UTC)."""
    k = m.n // minutes
    def agg(a, how):
        x = a[:k * minutes].reshape(k, minutes)
        return {"o": x[:, 0], "h": x.max(1), "l": x.min(1), "c": x[:, -1]}[how]
    return {"o": agg(m.bo, "o"), "h": agg(m.bh, "h"), "l": agg(m.bl, "l"), "c": agg(m.bc, "c")}


def utc_idx(m: Market, day: pd.Timestamp, hh: int, mm: int = 0) -> int:
    return m.idx(day + pd.Timedelta(hours=hh, minutes=mm))


# --------------------------------------------------------------------------- P1: Tokyo fix
def is_gotobi(day: pd.Timestamp) -> bool:
    """5th/10th/15th/20th/25th/month-end, moved to the previous weekday if on a weekend.
    (Japanese public holidays are ignored.)"""
    month_end = (day + pd.offsets.MonthEnd(0)).normalize()
    targets = [day.replace(day=k) for k in (5, 10, 15, 20, 25)] + [month_end]
    for t in targets:
        while t.dayofweek >= 5:
            t -= pd.Timedelta(days=1)
        if t == day:
            return True
    return False


def tokyo_fix(m: Market, d: pd.DataFrame, mode: str, at: tuple[int, int], days_filter: str,
              sl_atr: float = 0.25) -> list[Signal]:
    """mode 'pre': BUY at `at` (UTC hh, mm) the evening/morning before, exit at the 09:55 JST fix
    (00:55 UTC). mode 'post': SELL at the fix, exit at `at` (UTC, same date)."""
    out = []
    for day, r in d.iterrows():                          # NY label = Tokyo date of that morning
        if day.dayofweek >= 5:
            continue
        g = is_gotobi(day)
        if (days_filter == "gotobi" and not g) or (days_filter == "other" and g):
            continue
        fix = utc_idx(m, day, 0, 55)
        if mode == "pre":
            hh, mm = at
            start = utc_idx(m, day - pd.Timedelta(days=1), hh, mm) if hh >= 12 else utc_idx(m, day, hh, mm)
            out.append(Signal(day, "BUY", start, "market", None, start + 1, sl_atr * r.atr20, None, fix, "fix-pre"))
        else:
            out.append(Signal(day, "SELL", fix, "market", None, fix + 1, sl_atr * r.atr20, None,
                              utc_idx(m, day, *at), "fix-post"))
    return out


# --------------------------------------------------------------------------- P2: prev-day sweep
def sweep_reversal(m: Market, d: pd.DataFrame, tf: int, tp: str, window=(7, 20)) -> list[Signal]:
    """A `tf`-minute bar trades through yesterday's high (low) and closes back inside -> fade it
    at the next bar open. SL just beyond the sweep bar's extreme (min 0.1 x ATR); TP 1R, 2R or the
    prior day's midpoint; time exit at the New York close. First sweep per side per day."""
    b = bars(m, tf)
    out = []
    for day, r in d.iterrows():
        lo_i, hi_i = utc_idx(m, day, window[0]) // tf, utc_idx(m, day, window[1]) // tf
        mid = (r.prev_high + r.prev_low) / 2
        done = set()
        for k in range(lo_i, min(hi_i, len(b["o"]) - 1)):
            for side in ("SELL", "BUY"):
                if side in done:
                    continue
                if side == "SELL" and b["h"][k] > r.prev_high and b["c"][k] < r.prev_high:
                    entry_est = b["c"][k]
                    sl_d = max(b["h"][k] - entry_est, 0.1 * r.atr20)
                elif side == "BUY" and b["l"][k] < r.prev_low and b["c"][k] > r.prev_low:
                    entry_est = b["c"][k]
                    sl_d = max(entry_est - b["l"][k], 0.1 * r.atr20)
                else:
                    continue
                done.add(side)
                tp_d = {"1R": sl_d, "2R": 2 * sl_d, "mid": abs(entry_est - mid)}[tp]
                if tp_d <= 0:
                    continue
                start = (k + 1) * tf
                out.append(Signal(day, side, start, "market", None, start + 1, sl_d, tp_d,
                                  int(r.end_i), f"sweep{tf}-{tp}"))
    return out


# --------------------------------------------------------------------------- P3: Asian range fade
def asian_fade(m: Market, d: pd.DataFrame, tf: int, tp: str) -> list[Signal]:
    """Asian range = 00:00-06:59 UTC. Between 07:00 and 10:00 UTC a `tf`-minute bar breaks out of
    it and closes back inside -> fade at the next bar open. SL beyond that bar's extreme
    (min 0.1 x ATR); TP = range middle or the opposite side; time exit 16:00 UTC. First signal
    per side per day."""
    b = bars(m, tf)
    out = []
    for day, r in d.iterrows():
        a0, a1 = utc_idx(m, day, 0), utc_idx(m, day, 7)
        if a0 < 0 or a1 >= m.n:
            continue
        ah, al = m.bh[a0:a1].max(), m.bl[a0:a1].min()
        mid = (ah + al) / 2
        done = set()
        for k in range(a1 // tf, utc_idx(m, day, 10) // tf):
            for side in ("SELL", "BUY"):
                if side in done:
                    continue
                if side == "SELL" and b["h"][k] > ah and b["c"][k] < ah:
                    e = b["c"][k]; sl_d = max(b["h"][k] - e, 0.1 * r.atr20); tgt = mid if tp == "mid" else al
                elif side == "BUY" and b["l"][k] < al and b["c"][k] > al:
                    e = b["c"][k]; sl_d = max(e - b["l"][k], 0.1 * r.atr20); tgt = mid if tp == "mid" else ah
                else:
                    continue
                done.add(side)
                tp_d = abs(e - tgt)
                if tp_d <= 0:
                    continue
                start = (k + 1) * tf
                out.append(Signal(day, side, start, "market", None, start + 1, sl_d, tp_d,
                                  utc_idx(m, day, 16), f"asianfade{tf}-{tp}"))
    return out


# --------------------------------------------------------------------------- P4: trend + pullback
def trend_pullback(m: Market, d: pd.DataFrame, k_atr: float, sl_atr: float, rr: float) -> list[Signal]:
    """Uptrend: prior close above a rising 50-day SMA -> buy limit at prior close - k x ATR,
    live 07:00-16:00 UTC; SL sl_atr x ATR below the fill, TP rr x SL, time exit at the New York
    close. Downtrend mirrored."""
    out = []
    for day, r in d.iterrows():
        up = r.prev_close > r.sma50 and r.sma50 > r.sma50_prev
        dn = r.prev_close < r.sma50 and r.sma50 < r.sma50_prev
        if not (up or dn):
            continue
        s0, s1 = utc_idx(m, day, 7), utc_idx(m, day, 16)
        sl_d = sl_atr * r.atr20
        if up:
            out.append(Signal(day, "BUY", s0, "limit", r.prev_close - k_atr * r.atr20, s1, sl_d,
                              rr * sl_d, int(r.end_i), "pullback"))
        else:
            out.append(Signal(day, "SELL", s0, "limit", r.prev_close + k_atr * r.atr20, s1, sl_d,
                              rr * sl_d, int(r.end_i), "pullback"))
    return out


# --------------------------------------------------------------------------- flow / session patterns
LDN = "Europe/London"


def local_idx(m: Market, day: pd.Timestamp, hh: int, mm: int, tz: str) -> int:
    """Grid index of `day` hh:mm wall-clock time in `tz` (daylight saving aware)."""
    t = (day + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(tz).tz_convert("UTC").tz_localize(None)
    return m.idx(t)


def month_end_days(d: pd.DataFrame) -> pd.DatetimeIndex:
    """Last weekday session label of each month in the daily table."""
    wk = d.index[d.index.dayofweek < 5]
    s = pd.Series(wk, index=wk)
    return pd.DatetimeIndex(s.groupby([wk.year, wk.month]).max().to_numpy())


def month_end_fix(m: Market, d: pd.DataFrame, direction: str, exit_at: tuple[int, int],
                  sl_atr: float = 0.5) -> list[Signal]:
    """Last trading day of the month: at 14:00 London trade against ('fade') or with ('follow')
    the month-to-date move (from the previous month's last close), exit at `exit_at` London."""
    out = []
    ends = month_end_days(d)
    for k in range(1, len(ends)):
        day = ends[k]
        r = d.loc[day]
        start = local_idx(m, day, 14, 0, LDN)
        if start < 0 or start >= m.n:
            continue
        mtd = m.bo[start] - d.loc[ends[k - 1], "close"]
        if mtd == 0:
            continue
        up = mtd > 0
        side = ("SELL" if up else "BUY") if direction == "fade" else ("BUY" if up else "SELL")
        out.append(Signal(day, side, start, "market", None, start + 1, sl_atr * r.atr20, None,
                          local_idx(m, day, *exit_at, LDN), f"monthend-{direction}"))
    return out


def london_fix_fade(m: Market, d: pd.DataFrame, exit_at: tuple[int, int], sl_atr: float,
                    min_move_atr: float = 0.2) -> list[Signal]:
    """Every day: if 15:00-16:00 London moved at least `min_move_atr` x ATR20, trade against that
    move at 16:00 London (the WM/R fix); exit at `exit_at` London."""
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5:
            continue
        a, b = local_idx(m, day, 15, 0, LDN), local_idx(m, day, 16, 0, LDN)
        if a < 0 or b >= m.n:
            continue
        move = m.bo[b] - m.bo[a]
        if abs(move) < min_move_atr * r.atr20:
            continue
        out.append(Signal(day, "SELL" if move > 0 else "BUY", b, "market", None, b + 1,
                          sl_atr * r.atr20, None, local_idx(m, day, *exit_at, LDN), "ldnfix-fade"))
    return out


def ny_open_momentum(m: Market, d: pd.DataFrame, exit_at: tuple[int, int], sl_atr: float) -> list[Signal]:
    """Every day: trade in the direction of the 09:30-10:00 New York move at 10:00 NY; exit at
    `exit_at` New York."""
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5:
            continue
        a, b = local_idx(m, day, 9, 30, NY), local_idx(m, day, 10, 0, NY)
        if a < 0 or b >= m.n:
            continue
        move = m.bo[b] - m.bo[a]
        if move == 0:
            continue
        out.append(Signal(day, "BUY" if move > 0 else "SELL", b, "market", None, b + 1,
                          sl_atr * r.atr20, None, local_idx(m, day, *exit_at, NY), "nyopen-mom"))
    return out


# --------------------------------------------------------------------------- intraday breakouts / scalp
def _oco(m: Market, a: Signal, b: Signal) -> Signal | None:
    """One-cancels-other: keep the stop that fills first (None if neither fills)."""
    fa, fb = _fill(m, a), _fill(m, b)
    if fa is None and fb is None:
        return None
    if fb is None or (fa is not None and fa[0] <= fb[0]):
        return a
    return b


def _bracket(m: Market, day, hi_bid: float, lo_bid: float, start: int, expiry: int, sl_d: float,
             tp_d: float, exit_by: int, tag: str) -> Signal | None:
    """Buy stop at hi_bid + spread (on ask), sell stop at lo_bid (on bid), OCO. Skipped if the
    price is already outside the levels when the orders go live."""
    if start < 0 or exit_by >= m.n or sl_d <= 0 or tp_d <= 0:
        return None
    spread = max(m.ao[start] - m.bo[start], 0.0)
    if not (lo_bid < m.bo[start] < hi_bid):
        return None
    buy = Signal(day, "BUY", start, "stop", hi_bid + spread, expiry, sl_d, tp_d, exit_by, tag)
    sell = Signal(day, "SELL", start, "stop", lo_bid, expiry, sl_d, tp_d, exit_by, tag)
    return _oco(m, buy, sell)


def london_breakout(m: Market, d: pd.DataFrame, sl_range: float, rr: float) -> list[Signal]:
    """Asian range 00:00-06:59 UTC; at 07:00 OCO stops at its edges, live to 12:00 UTC.
    SL = sl_range x range (min 0.1 ATR), TP = rr x SL, time exit at the New York close."""
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5:
            continue
        a, b = utc_idx(m, day, 0), utc_idx(m, day, 7)
        if a < 0 or b >= m.n:
            continue
        hi, lo = m.bh[a:b].max(), m.bl[a:b].min()
        sl_d = max(sl_range * (hi - lo), 0.1 * r.atr20)
        s = _bracket(m, day, hi, lo, b, utc_idx(m, day, 12), sl_d, rr * sl_d, int(r.end_i) - 1, "ldn-bo")
        if s is not None:
            out.append(s)
    return out


def prevday_breakout(m: Market, d: pd.DataFrame, sl_atr: float, rr: float) -> list[Signal]:
    """OCO stops at yesterday's high / low, live 07:00-16:00 UTC (only if price starts inside).
    SL sl_atr x ATR20, TP rr x SL, time exit at the New York close."""
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5:
            continue
        sl_d = sl_atr * r.atr20
        s = _bracket(m, day, r.prev_high, r.prev_low, utc_idx(m, day, 7), utc_idx(m, day, 16), sl_d,
                     rr * sl_d, int(r.end_i) - 1, "pd-bo")
        if s is not None:
            out.append(s)
    return out


def contraction_breakout(m: Market, d: pd.DataFrame, kind: str, rr: float) -> list[Signal]:
    """After an NR7 day (narrowest of the last 7) or an inside day: OCO stops at that day's
    high / low, live 07:00-16:00 UTC. SL = that day's range (min 0.1 ATR), TP rr x SL,
    time exit at the New York close."""
    rng = d.high - d.low
    nr7 = (rng == rng.rolling(7).min()).shift(1, fill_value=False)
    inside = ((d.high <= d.high.shift(1)) & (d.low >= d.low.shift(1))).shift(1, fill_value=False)
    flag = nr7 if kind == "nr7" else inside
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or not flag[day]:
            continue
        sl_d = max(r.prev_high - r.prev_low, 0.1 * r.atr20)
        s = _bracket(m, day, r.prev_high, r.prev_low, utc_idx(m, day, 7), utc_idx(m, day, 16), sl_d,
                     rr * sl_d, int(r.end_i) - 1, f"{kind}-bo")
        if s is not None:
            out.append(s)
    return out


def ny_orb(m: Market, d: pd.DataFrame, minutes: int, rr: float) -> list[Signal]:
    """New York opening range 09:30 + `minutes`; OCO stops at its edges until 12:00 NY.
    SL = range (min 0.1 ATR), TP rr x range, time exit 16:00 NY."""
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5:
            continue
        a = local_idx(m, day, 9, 30, NY)
        b = a + minutes
        if a < 0 or b >= m.n:
            continue
        hi, lo = m.bh[a:b].max(), m.bl[a:b].min()
        sl_d = max(hi - lo, 0.1 * r.atr20)
        s = _bracket(m, day, hi, lo, b, local_idx(m, day, 12, 0, NY), sl_d, rr * sl_d,
                     local_idx(m, day, 16, 0, NY), f"orb{minutes}")
        if s is not None:
            out.append(s)
    return out


def night_reversion(m: Market, d: pd.DataFrame, band_std: float, sl_atr: float) -> list[Signal]:
    """Quiet-hours scalp, 22:00-06:00 UTC (Tue-Fri nights; Sunday reopen skipped): a 15-minute
    bar closes outside its 20-bar Bollinger band (`band_std`) -> fade at the next bar open,
    TP = the band middle, SL sl_atr x ATR20, time exit 07:00 UTC. First signal per side per night."""
    b = bars(m, 15)
    c = b["c"]
    mid = pd.Series(c).rolling(20).mean().to_numpy()
    sd = pd.Series(c).rolling(20).std().to_numpy()
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or day.dayofweek == 0:
            continue
        k0 = utc_idx(m, day - pd.Timedelta(days=1), 22) // 15
        k1 = utc_idx(m, day, 6) // 15
        x = utc_idx(m, day, 7)
        if k0 < 20 or x >= m.n:
            continue
        done = set()
        for k in range(k0, k1):
            if np.isnan(sd[k]) or sd[k] == 0:
                continue
            if "SELL" not in done and c[k] > mid[k] + band_std * sd[k]:
                side = "SELL"
            elif "BUY" not in done and c[k] < mid[k] - band_std * sd[k]:
                side = "BUY"
            else:
                continue
            done.add(side)
            tp_d = abs(c[k] - mid[k])
            start = (k + 1) * 15
            out.append(Signal(day, side, start, "market", None, start + 1, sl_atr * r.atr20, tp_d, x,
                              f"night{band_std:g}"))
    return out


# --------------------------------------------------------------------------- gotobi short variants
def is_month_end_gotobi(day: pd.Timestamp) -> bool:
    """The month-end gotobi date (last day of the month, moved back to a weekday)."""
    t = (day + pd.offsets.MonthEnd(0)).normalize()
    while t.dayofweek >= 5:
        t -= pd.Timedelta(days=1)
    return t == day


def is_gotobi_jp(day: pd.Timestamp, hol) -> bool:
    """Gotobi with the Japanese business calendar: 5/10/15/20/25/month-end, moved back to the
    previous day that is neither a weekend nor a Japanese public holiday (`hol`: date set)."""
    if day.dayofweek >= 5 or day.date() in hol:
        return False
    month_end = (day + pd.offsets.MonthEnd(0)).normalize()
    for t in [day.replace(day=k) for k in (5, 10, 15, 20, 25)] + [month_end]:
        while t.dayofweek >= 5 or t.date() in hol:
            t -= pd.Timedelta(days=1)
        if t == day:
            return True
    return False


def gotobi_short(m: Market, d: pd.DataFrame, exit_at: tuple[int, int] = (6, 0), sl_atr: float = 0.25,
                 tp_r: float | None = None, filt: str = "none", calendar: str = "simple",
                 entry_at: tuple[int, int] = (0, 55)) -> list[Signal]:
    """Gotobi days: SELL at the 09:55 JST fix (00:55 UTC), exit at `exit_at` UTC, SL sl_atr x ATR20,
    optional TP tp_r x SL. filt: 'none', 'runup' (only if bid at the fix is above 08:00 JST),
    'monthend' (month-end gotobi only) or 'nomonday'. calendar: 'simple' (weekends only) or 'jp'
    (also Japanese public holidays). entry_at: UTC entry time (default the 09:55 JST fix)."""
    hol = set()
    if calendar == "jp":
        import holidays
        hol = set(holidays.Japan(years=range(d.index.min().year, d.index.max().year + 1)))
    gday = (lambda x: is_gotobi_jp(x, hol)) if calendar == "jp" else is_gotobi
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or not gday(day):
            continue
        if filt == "monthend" and not is_month_end_gotobi(day):
            continue
        if filt == "nomonday" and day.dayofweek == 0:
            continue
        fix = utc_idx(m, day, *entry_at)
        if filt == "runup":
            a = utc_idx(m, day - pd.Timedelta(days=1), 23, 0)
            if a < 0 or fix >= m.n or not m.bo[fix] > m.bo[a]:
                continue
        sl = sl_atr * r.atr20
        out.append(Signal(day, "SELL", fix, "market", None, fix + 1, sl, None if tp_r is None else tp_r * sl,
                          utc_idx(m, day, *exit_at), f"gotobi-{filt}"))
    return out
