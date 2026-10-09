"""NY-open candle vs 12 EMA (the "one candle, one EMA" Nasdaq reel, run on FX).

Each New York trading day (Mon-Fri, America/New_York, DST-aware):

    signal candle = the 5-minute BID candle 09:30-09:34 NY
    close > EMA(12) of 5-minute bid closes  -> BUY at the 09:35 open (ask)
    close < EMA(12)                          -> SELL at the 09:35 open (bid)

The reel does not give its management, so it is a parameter:
  * stop = the far end of the signal candle (long: bid low; short: bid high + entry spread,
    triggered on ask), so 1R = distance from the fill to that stop, spread included
  * stop_atr = optional floor: the stop sits at least stop_atr x ATR(14) of 5-minute bid
    candles (taken at the signal close) away from the fill
  * or a stop that ignores the candle: sl_pips = fixed pips, sl_atr = k x ATR(14); both
    + the entry spread (1R = SL + spread, as in gjstrat.engine)
  * rr = target in R (None = no target)
  * ema_trail = also exit at the next 1-minute open once a 5-minute close crosses back over
    the EMA (long: close < EMA, short: close > EMA)
  * every trade still open is closed at the flat time (16:00 NY open of that minute)

The EMA uses only 5-minute buckets that traded (weekend flat bars are left out) and is
forward-filled across the rest. Same-bar conventions as gjstrat.engine: entry bar can only
hit the stop, stop before target when both are inside one bar, gaps through the stop fill at
the bar's open, the target is a limit (no positive slippage).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Market
from .engine import EPS, Trade

NY = "America/New_York"


@dataclass(frozen=True)
class CandleParams:
    rr: float | None = 1.0
    ema_trail: bool = False
    stop_atr: float | None = None
    sl_pips: float | None = None
    sl_atr: float | None = None
    ema_len: int = 12
    open_hm: tuple[int, int] = (9, 30)
    flat_hm: tuple[int, int] = (16, 0)

    @property
    def label(self) -> str:
        tgt = "EOD" if self.rr is None else f"{self.rr:g}R"
        return self.stop_label + (" " if self.stop_label else "") + tgt \
            + ("+EMAtrail" if self.ema_trail else "")

    @property
    def stop_label(self) -> str:
        if self.sl_pips is not None:
            return f"SL{self.sl_pips:g}p"
        if self.sl_atr is not None:
            return f"SL{self.sl_atr:g}ATR"
        return "" if self.stop_atr is None else f"stop>={self.stop_atr:g}ATR"

    def __post_init__(self):
        if sum(x is not None for x in (self.stop_atr, self.sl_pips, self.sl_atr)) > 1:
            raise ValueError("set at most one of stop_atr, sl_pips, sl_atr")


def ema5(m: Market, length: int = 12) -> np.ndarray:
    """EMA of 5-minute bid closes, one value per 5-minute bucket (bucket g = minutes 5g..5g+4).
    Requires m.t0 on a 5-minute boundary (to_grid floors it to midnight)."""
    g = m.n // 5
    close = m.bc[4:g * 5:5]
    live = m.vol[:g * 5].reshape(g, 5).sum(axis=1) > 0
    e = pd.Series(close[live]).ewm(span=length, adjust=False).mean().to_numpy()
    out = np.full(g, np.nan)
    out[live] = e
    return pd.Series(out).ffill().to_numpy()


def atr5(m: Market, length: int = 14) -> np.ndarray:
    """ATR of 5-minute bid candles per 5-minute bucket (traded buckets only, forward-filled)."""
    g = m.n // 5
    live = m.vol[:g * 5].reshape(g, 5).sum(axis=1) > 0
    h = m.bh[:g * 5].reshape(g, 5).max(axis=1)[live]
    lo = m.bl[:g * 5].reshape(g, 5).min(axis=1)[live]
    c = m.bc[4:g * 5:5][live]
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h, pc) - np.minimum(lo, pc)
    out = np.full(g, np.nan)
    out[live] = pd.Series(tr).rolling(length, min_periods=1).mean().to_numpy()
    return pd.Series(out).ffill().to_numpy()


def ny_days(m: Market, start: str | None = None, end: str | None = None) -> list[pd.Timestamp]:
    first = (m.t0.tz_localize("UTC").tz_convert(NY)).normalize().tz_localize(None)
    last = (m.ts(m.n - 1).tz_localize("UTC").tz_convert(NY)).normalize().tz_localize(None)
    days = pd.date_range(first, last, freq="D")
    if start:
        days = days[days >= pd.Timestamp(start)]
    if end:
        days = days[days <= pd.Timestamp(end)]
    return [d for d in days if d.dayofweek < 5]


def _utc_idx(m: Market, day: pd.Timestamp, hm: tuple[int, int]) -> int:
    t = (day + pd.Timedelta(hours=hm[0], minutes=hm[1])).tz_localize(NY).tz_convert("UTC")
    return m.idx(t.tz_localize(None))


def _first(mask: np.ndarray) -> int:
    return int(np.argmax(mask)) if mask.any() else -1


def direction_moves(m: Market, days: list[pd.Timestamp], ema: np.ndarray,
                    p: CandleParams = CandleParams()) -> np.ndarray:
    """Signal check with no stop and no costs: mid price move, in pips, from the 09:35 open
    to the flat-time open, signed by the signal (+ = the candle/EMA side was right)."""
    out = []
    for day in days:
        s0, flat = _utc_idx(m, day, p.open_hm), _utc_idx(m, day, p.flat_hm)
        if s0 < 0 or flat >= m.n or (m.vol[s0:s0 + 5] == 0).any():
            continue
        diff = m.bc[s0 + 4] - ema[(s0 + 4) // 5]
        if abs(diff) <= EPS:
            continue
        mid = lambda i: (m.bo[i] + m.ao[i]) / 2
        out.append(np.sign(diff) * (mid(flat) - mid(s0 + 5)) / m.pip)
    return np.array(out)


def run_candle(m: Market, p: CandleParams, days: list[pd.Timestamp],
               ema: np.ndarray | None = None, atr: np.ndarray | None = None
               ) -> tuple[list[Trade], dict]:
    ema = ema5(m, p.ema_len) if ema is None else ema
    if (p.stop_atr is not None or p.sl_atr is not None) and atr is None:
        atr = atr5(m)
    c = dict(days=0, no_data=0, flat_close=0, bad_risk=0, trades=0)
    trades: list[Trade] = []
    for day in days:
        c["days"] += 1
        s0 = _utc_idx(m, day, p.open_hm)
        flat = _utc_idx(m, day, p.flat_hm)
        if s0 < 0 or flat >= m.n or (m.vol[s0:s0 + 5] == 0).any():
            c["no_data"] += 1
            continue
        g = (s0 + 4) // 5                                 # signal candle's 5-minute bucket
        close, level = m.bc[s0 + 4], ema[g - 1] if np.isnan(ema[g]) else ema[g]
        if abs(close - level) <= EPS:
            c["flat_close"] += 1
            continue
        side = "BUY" if close > level else "SELL"
        e = s0 + 5
        spread = max(m.ao[e] - m.bo[e], 0.0)
        if side == "BUY":
            px, sl = m.ao[e], m.bl[s0:s0 + 5].min()
            risk = px - sl
            lo, hi, op, cl = m.bl, m.bh, m.bo, m.bc
        else:
            px, sl = m.bo[e], m.bh[s0:s0 + 5].max() + spread
            risk = sl - px
            lo, hi, op, cl = m.al, m.ah, m.ao, m.ac
        sgn = 1 if side == "BUY" else -1
        if p.stop_atr is not None and risk < p.stop_atr * atr[g]:
            risk = p.stop_atr * atr[g]
        elif p.sl_pips is not None:
            risk = p.sl_pips * m.pip + spread
        elif p.sl_atr is not None:
            risk = p.sl_atr * atr[g] + spread
        sl = px - sgn * risk
        if risk <= EPS:
            c["bad_risk"] += 1
            continue
        tp = None if p.rr is None else px + sgn * p.rr * risk
        adverse = (lo[e:flat] <= sl + EPS) if side == "BUY" else (hi[e:flat] >= sl - EPS)
        if tp is None:
            favour = np.zeros(flat - e, bool)
        else:
            favour = (hi[e:flat] >= tp - EPS) if side == "BUY" else (lo[e:flat] <= tp + EPS)
        favour[0] = False                                 # entry bar: only the stop
        hit = _first(adverse | favour)
        xi, xp, reason = flat, op[flat], "EOD"
        if hit >= 0:
            j = e + hit
            if adverse[hit]:
                gapped = (op[j] < sl - EPS) if side == "BUY" else (op[j] > sl + EPS)
                xi, xp, reason = j, (op[j] if gapped and j > e else sl), "SL"
            else:
                xi, xp, reason = j, tp, "TP"
        if p.ema_trail:
            # 5-minute buckets that close after entry and before the current exit
            gs = np.arange(e // 5, min(xi, flat) // 5)
            if len(gs):
                bc5 = m.bc[gs * 5 + 4]
                cross = (bc5 < ema[gs] - EPS) if side == "BUY" else (bc5 > ema[gs] + EPS)
                k = _first(cross)
                if k >= 0 and (gs[k] + 1) * 5 <= xi:     # its open comes before a hit on that bar
                    xi = (gs[k] + 1) * 5
                    xp, reason = op[xi], "EMA"
        trades.append(Trade(day, side, 1, e, float(px), int(xi), float(xp), reason, float(risk),
                            float(spread), float((m.bh[s0:s0 + 5].max() - m.bl[s0:s0 + 5].min()) / m.pip),
                            False, False))
        c["trades"] += 1
    return trades, c
