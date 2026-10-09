"""Dragonfly Intercept: event-driven 15m loop (one pair, one parameter set).

Bar i is processed in this order:
  1. intrabar: a pending limit placed at an EARLIER close may fill (buy limit: ask low <= limit,
     fill at the limit, or at the ask open if the bar opens through it). On the fill bar only the
     stop can be hit (we cannot know whether TP / the BE trigger came before the fill).
  2. intrabar: an open position from an earlier bar is managed: stop first (a gap through it fills
     at the open), then TP (limit: gap through fills at the open), then the +1R break-even trigger
     (the stop moves to entry from the NEXT bar). SL and TP / BE in the same bar -> SL.
  3. at the close: pending-order cancels: close beyond 78.6% of the leg, 1H trend not in the
     order's direction, or 12 candles without a fill.
  4. at the close: a completed leg is a signal. It is skipped (and counted) if an order is
     pending or a position is open, or if the stop distance is under 3 x spread.

Buys fill at ask and exit at bid; sells fill at bid and exit at ask. Leg prices are bid.
mode="chase": no limit order; the signal is entered at market at the completion close
(ask for buys, bid for sells) with the same stop, target, BE and risk rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

NY = "America/New_York"


@dataclass
class Params:
    retrace: float = 0.5           # R: limit at H - R x Leg (buy)
    target: str = "T1"             # T1 = H, T2 = H + 0.5 x Leg (buy)
    spread: float = 0.025          # nominal spread in PRICE units (buffer and 3x-spread rule)
    buffer_atr: float = 0.1
    min_stop_spreads: float = 3.0
    expiry_bars: int = 12
    cancel_frac: float = 0.786
    be_at_r: float = 1.0
    risk: float = 0.01
    start_equity: float = 10_000.0
    commission_per_lot: float = 0.0   # USD per 100k units, round turn
    swap_long_per_lot: float = 0.0    # USD per 100k units per night (+ = credit); Wed counts 3
    swap_short_per_lot: float = 0.0
    mode: str = "limit"               # "limit" (dragonfly) or "chase"


@dataclass
class Bars:
    """15m arrays for one pair plus the per-bar inputs the strategy needs (all known at close)."""
    t: pd.DatetimeIndex            # bar open times (UTC)
    bo: np.ndarray
    bh: np.ndarray
    bl: np.ndarray
    bc: np.ndarray
    ao: np.ndarray
    ah: np.ndarray
    al: np.ndarray
    ac: np.ndarray
    usd_per_quote: np.ndarray
    atr15: np.ndarray
    trend: np.ndarray              # +1 / -1 / 0 from the last CLOSED 1H bar at this bar's close
    legs: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.bo)


@dataclass
class Position:
    side: int
    entry_i: int
    entry: float
    stop: float
    tp: float
    r: float                       # |entry - initial stop| at the actual fill
    be_on: bool
    be_done: bool = False


def manage_bar(p: Position, b: Bars, i: int, stop_only: bool = False):
    """Check one bar for an exit. Returns (exit_price, reason, gap) or None. May move the stop
    to break-even (effective from the next bar)."""
    if p.side == 1:
        if b.bo[i] <= p.stop:
            return b.bo[i], "BE" if p.be_done else "SL", True
        if b.bl[i] <= p.stop:
            return p.stop, "BE" if p.be_done else "SL", False
        if stop_only:
            return None
        if b.bh[i] >= p.tp:
            return (b.bo[i], "TP", True) if b.bo[i] >= p.tp else (p.tp, "TP", False)
        if p.be_on and not p.be_done and b.bh[i] >= p.entry + p.r:
            p.be_done, p.stop = True, p.entry
    else:
        if b.ao[i] >= p.stop:
            return b.ao[i], "BE" if p.be_done else "SL", True
        if b.ah[i] >= p.stop:
            return p.stop, "BE" if p.be_done else "SL", False
        if stop_only:
            return None
        if b.al[i] <= p.tp:
            return (b.ao[i], "TP", True) if b.ao[i] <= p.tp else (p.tp, "TP", False)
        if p.be_on and not p.be_done and b.al[i] <= p.entry - p.r:
            p.be_done, p.stop = True, p.entry
    return None


def rollovers(t0: pd.Timestamp, t1: pd.Timestamp) -> np.ndarray:
    """UTC times of the 17:00 New York rollovers (Mon-Fri) in [t0 - 1d, t1 + 1d], with weights
    (Wednesday = 3 nights)."""
    days = pd.date_range(t0.floor("D") - pd.Timedelta(days=1), t1.ceil("D") + pd.Timedelta(days=1))
    days = days[days.dayofweek < 5]
    utc = (days + pd.Timedelta(hours=17)).tz_localize(NY).tz_convert("UTC").tz_localize(None)
    return np.asarray(utc.as_unit("ns").asi8), np.where(days.dayofweek == 2, 3, 1)


def run(b: Bars, p: Params) -> dict:
    """Simulate one pair. Returns dict of DataFrames: trades, orders, signals."""
    L = b.legs
    n = b.n
    t = pd.DatetimeIndex(b.t).as_unit("ns")
    tns = t.asi8
    q15 = 15 * 60 * 10**9
    roll_t, roll_w = rollovers(t[0], t[-1])
    equity = p.start_equity
    pend = None                    # dict for the pending order
    pos: Position | None = None
    meta = None                    # signal info carried from the order to the trade
    trades, orders, signals = [], [], []

    def close_trade(k: int, price: float, reason: str, gap: bool):
        nonlocal equity, pos, meta
        side = pos.side
        pnl = side * meta["units"] * (price - pos.entry) * b.usd_per_quote[k]
        lots = meta["units"] / 1e5
        comm = p.commission_per_lot * lots
        t_in = meta["entry_ns"]
        t_out = tns[k] if reason != "END" else tns[k] + q15
        sel = (roll_t > t_in) & (roll_t <= t_out)
        nights = int(roll_w[sel].sum())
        swap = (p.swap_long_per_lot if side == 1 else p.swap_short_per_lot) * lots * nights
        net = pnl - comm + swap
        equity += net
        trades.append({**meta["log"], "entry_time": pd.Timestamp(t_in), "entry_price": pos.entry,
                       "exit_time": t[k], "exit_price": price, "exit_reason": reason,
                       "exit_gap": gap, "be_moved": pos.be_done, "be_rule_on": pos.be_on,
                       "bars_held": k - pos.entry_i, "rollovers": int(sel.sum()),
                       "risk_usd": meta["risk_usd"], "pnl_usd": net,
                       "R": net / meta["risk_usd"], "equity_after": equity})
        pos, meta = None, None

    def open_position(i: int, fill: float, entry_ns: int, info: dict, units: float, risk_usd: float):
        nonlocal pos, meta
        r = abs(fill - info["stop"])
        be_on = abs(info["tp"] - fill) >= p.be_at_r * r
        pos = Position(info["side"], i, fill, info["stop"], info["tp"], r, be_on)
        meta = {"units": units, "risk_usd": risk_usd, "entry_ns": entry_ns, "log": info["log"]}

    for i in range(n):
        filled_now = False
        # 1. pending limit fill
        if pend is not None:
            s, P = pend["side"], pend["price"]
            hit = (b.al[i] <= P) if s == 1 else (b.bh[i] >= P)
            if hit:
                op = b.ao[i] if s == 1 else b.bo[i]
                gap = (op <= P) if s == 1 else (op >= P)
                fill = op if gap else P
                pend["log"].update(fill_gap=gap, bars_to_fill=i - pend["placed_i"])
                orders.append({**pend["olog"], "outcome": "filled", "end_time": t[i]})
                open_position(i, fill, tns[i], pend, pend["units"], pend["risk_usd"])
                pend = None
                filled_now = True
                ex = manage_bar(pos, b, i, stop_only=True)
                if ex:
                    close_trade(i, *ex)
        # 2. manage open position (not on its entry bar)
        elif pos is not None and pos.entry_i < i:
            ex = manage_bar(pos, b, i)
            if ex:
                close_trade(i, *ex)
        # 3. pending-order cancels at the close
        if pend is not None and not filled_now:
            s = pend["side"]
            reason = None
            if (s == 1 and b.bc[i] < pend["cancel_lvl"]) or (s == -1 and b.bc[i] > pend["cancel_lvl"]):
                reason = "cancel_786"
            elif b.trend[i] != s:
                reason = "cancel_trend"
            elif i - pend["placed_i"] >= p.expiry_bars:
                reason = "cancel_expired"
            if reason:
                orders.append({**pend["olog"], "outcome": reason, "end_time": t[i] + pd.Timedelta(minutes=15)})
                pend = None
        # 4. signal at the close
        tr = b.trend[i]
        if tr == 0:
            continue
        key = "buy" if tr == 1 else "sell"
        if not L[key][i]:
            continue
        s = int(tr)
        H, Lo = L[f"{key}_H"][i], L[f"{key}_L"][i]
        leg = H - Lo
        sig_time = t[i] + pd.Timedelta(minutes=15)
        sig = {"signal_time": sig_time, "side": "buy" if s == 1 else "sell"}
        if pend is not None:
            signals.append({**sig, "outcome": "skip_pending"})
            continue
        if pos is not None:
            signals.append({**sig, "outcome": "skip_position"})
            continue
        buf = max(p.spread, p.buffer_atr * b.atr15[i])
        tgt_ext = 0.0 if p.target == "T1" else 0.5 * leg
        if s == 1:
            stop, tp, cancel_lvl = Lo - buf, H + tgt_ext, H - p.cancel_frac * leg
            price = H - p.retrace * leg if p.mode == "limit" else b.ac[i]
        else:
            stop, tp, cancel_lvl = H + buf, Lo - tgt_ext, Lo + p.cancel_frac * leg
            price = Lo + p.retrace * leg if p.mode == "limit" else b.bc[i]
        dist = abs(price - stop)
        if dist < p.min_stop_spreads * p.spread:
            signals.append({**sig, "outcome": "skip_small_stop"})
            continue
        if s * (tp - price) <= 0:          # chase only: market price already at/through the target
            signals.append({**sig, "outcome": "skip_target_reached"})
            continue
        risk_usd = p.risk * equity
        units = risk_usd / (dist * b.usd_per_quote[i])
        log = {"side": sig["side"], "signal_time": sig_time, "H": H, "L": Lo, "leg": leg,
               "leg_atr": leg / b.atr15[i], "atr15": b.atr15[i], "buffer": buf,
               "order_price": price, "stop": stop, "tp": tp, "stop_dist": dist,
               "target_R_planned": abs(tp - price) / dist, "fill_gap": False, "bars_to_fill": 0}
        signals.append({**sig, "outcome": "placed"})
        info = {"side": s, "price": price, "stop": stop, "tp": tp, "cancel_lvl": cancel_lvl,
                "placed_i": i, "units": units, "risk_usd": risk_usd, "log": log,
                "olog": {"signal_time": sig_time, "side": sig["side"], "order_price": price}}
        if p.mode == "chase":
            orders.append({**info["olog"], "outcome": "filled", "end_time": sig_time})
            open_position(i, price, tns[i] + q15, info, units, risk_usd)
        elif (s == 1 and b.bc[i] < cancel_lvl) or (s == -1 and b.bc[i] > cancel_lvl):
            # the completion candle itself already closed beyond 78.6%: never chase
            orders.append({**info["olog"], "outcome": "cancel_786_at_signal", "end_time": sig_time})
        else:
            pend = info

    if pend is not None:
        orders.append({**pend["olog"], "outcome": "open_at_end", "end_time": t[-1]})
    if pos is not None:
        k = n - 1
        close_trade(k, b.bc[k] if pos.side == 1 else b.ac[k], "END", False)
    return {"trades": pd.DataFrame(trades), "orders": pd.DataFrame(orders),
            "signals": pd.DataFrame(signals)}
