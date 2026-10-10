"""Event-driven execution of zone trades on 15-minute bid/ask bars.

Two stages, so the day filters (macro, none, trend, 1000 random seeds) can be compared on
exactly the same zones and fills:

1. candidates(): every zone's first touch and what the trade from it would be (entry, stop,
   TP, exit, R). Nothing here depends on the day filter: zones, touches, freshness and fills
   are properties of the price path.
2. run_portfolio(): walks the candidates in time order and applies the day filter, the
   one-open-position-per-pair rule and the skip rules, counting every skip.

Prices: zones, swings and stops are drawn on BID. Buys fill at ASK and exit at BID (their
SL/TP trigger on bid); sells fill at BID and exit at ASK. A demand zone is touched when the ask
low reaches its top (a buy limit there would fill); a supply zone when the bid high reaches its
bottom. That one touch definition is used for Version A fills, Version B "price enters the
zone", and freshness (zone dies at its first touch).

Exits: same 15m candle hits SL and TP -> SL. On a Version A fill candle only the SL is checked
(order inside the candle unknown). A candle that opens beyond the stop exits at its open. A TP
fills at the TP price (no positive slippage). No time stop; still open at the end of the data
-> closed at the last close, reason open_at_end.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .zones import DEMAND, SUPPLY

NS_15M = 15 * 60 * 1_000_000_000
NS_DAY = 86_400 * 1_000_000_000
SKIP_NONE, SKIP_STOP, SKIP_TP = 0, 1, 2
SKIP_NAMES = {SKIP_STOP: "stop_lt_2x_spread", SKIP_TP: "opposite_zone_tp_lt_1R"}


@dataclass
class M15:
    t: np.ndarray        # bar open time, int64 ns UTC
    bo: np.ndarray
    bh: np.ndarray
    bl: np.ndarray
    bc: np.ndarray
    ao: np.ndarray
    ah: np.ndarray
    al: np.ndarray
    ac: np.ndarray
    spread: np.ndarray   # typical spread known at the close of bar i (median of last 96 closes)
    atr: np.ndarray      # ATR(14) of the latest 4H bar closed by the close of bar i
    sh: np.ndarray       # latest confirmed 15m swing high (bid) at the close of bar i, NaN if none
    sl: np.ndarray       # latest confirmed 15m swing low (bid)

    @property
    def n(self) -> int:
        return len(self.t)


def confirmed_swings(h: np.ndarray, l: np.ndarray, w: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Swing high at k: high[k] strictly above the w highs on each side. It is only known
    once bar k+w has closed, so it is placed at index k+w and carried forward."""
    n = len(h)
    sh, sl = np.full(n, np.nan), np.full(n, np.nan)
    if n < 2 * w + 1:
        return sh, sl
    from numpy.lib.stride_tricks import sliding_window_view as win
    hw, lw = win(h, 2 * w + 1), win(l, 2 * w + 1)        # row r = bars r .. r+2w, centre r+w
    mid_h, mid_l = hw[:, w], lw[:, w]
    is_h = (mid_h > hw[:, :w].max(1)) & (mid_h > hw[:, w + 1:].max(1))
    is_l = (mid_l < lw[:, :w].min(1)) & (mid_l < lw[:, w + 1:].min(1))
    conf = np.arange(len(hw)) + 2 * w                    # centre k = r+w, confirmed at k+w
    sh[conf[is_h]] = mid_h[is_h]
    sl[conf[is_l]] = mid_l[is_l]
    return pd.Series(sh).ffill().to_numpy(), pd.Series(sl).ffill().to_numpy()


def build_m15(df15: pd.DataFrame, b4: pd.DataFrame, atr4: np.ndarray, window: int = 96) -> M15:
    t = df15.index.to_numpy().astype("datetime64[ns]").astype(np.int64)
    a = {c: df15[c].to_numpy(float) for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}
    spread = pd.Series(a["ac"] - a["bc"]).rolling(window, min_periods=1).median().to_numpy()
    close4 = b4.index.to_numpy().astype("datetime64[ns]").astype(np.int64) + 4 * 3600 * 10**9
    j = np.searchsorted(close4, t + NS_15M, side="right") - 1
    atr = np.where(j >= 0, atr4[np.clip(j, 0, None)], np.nan)
    sh, sl = confirmed_swings(a["bh"], a["bl"])
    return M15(t=t, spread=spread, atr=atr, sh=sh, sl=sl, **a)


# --------------------------------------------------------------------------- zone book
@dataclass
class ZoneBook:
    kind: np.ndarray
    top: np.ndarray
    bottom: np.ndarray
    atr: np.ndarray
    a_idx: np.ndarray      # first 15m bar at/after activation (impulse close)
    e_idx: np.ndarray      # first 15m bar at/after expiry (50 4H bars)
    touch: np.ndarray      # first touch bar in [a_idx, e_idx), -1 = never touched (expired)

    @property
    def dead(self) -> np.ndarray:
        return np.where(self.touch >= 0, self.touch, self.e_idx)


def _ns(ts: pd.Series) -> np.ndarray:
    v = pd.to_datetime(ts)
    out = np.empty(len(v), np.int64)
    for k, x in enumerate(v):
        out[k] = np.iinfo(np.int64).max if x == pd.Timestamp.max else x.value
    return out


def make_book(z: pd.DataFrame, m: M15) -> ZoneBook:
    a_idx = np.searchsorted(m.t, _ns(z["active_from"]), side="left")
    e_idx = np.searchsorted(m.t, _ns(z["expires"]), side="left")
    kind, top, bot = z["kind"].to_numpy(int), z["top"].to_numpy(float), z["bottom"].to_numpy(float)
    touch = np.full(len(z), -1, np.int64)
    for k in range(len(z)):
        a, e = a_idx[k], e_idx[k]
        if a >= e:
            continue
        hit = m.al[a:e] <= top[k] if kind[k] == DEMAND else m.bh[a:e] >= bot[k]
        if hit.any():
            touch[k] = a + int(np.argmax(hit))
    return ZoneBook(kind, top, bot, z["atr"].to_numpy(float), a_idx, e_idx, touch)


def opposite_tp(book: ZoneBook, side: int, price: float, i: int, known: int) -> float:
    """Near edge of the nearest fresh opposite-type zone in the trade direction, using only
    zones active by bar `known` and not yet touched by bar i. NaN if none."""
    fresh = (book.a_idx <= known) & (book.dead > i)
    if side > 0:
        mask = fresh & (book.kind == SUPPLY) & (book.bottom > price)
        return float(book.bottom[mask].min()) if mask.any() else np.nan
    mask = fresh & (book.kind == DEMAND) & (book.top < price)
    return float(book.top[mask].max()) if mask.any() else np.nan


def simulate_exit(m: M15, side: int, stop: float, tp: float, i: int,
                  check_entry_bar: bool) -> tuple[int, float, str]:
    """First SL/TP after entry in bar i. check_entry_bar: also test the SL (only) on bar i."""
    if check_entry_bar:
        if side > 0 and m.bl[i] <= stop:
            return i, min(stop, m.bo[i]), "SL"
        if side < 0 and m.ah[i] >= stop:
            return i, max(stop, m.ao[i]), "SL"
    s, ch, n = i + 1, 2048, m.n
    while s < n:
        e = min(n, s + ch)
        if side > 0:
            sl, tph = m.bl[s:e] <= stop, m.bh[s:e] >= tp
        else:
            sl, tph = m.ah[s:e] >= stop, m.al[s:e] <= tp
        hit = sl | tph
        if hit.any():
            k = int(np.argmax(hit))
            j = s + k
            if sl[k]:                                     # SL first if both in one candle
                return j, (min(stop, m.bo[j]) if side > 0 else max(stop, m.ao[j])), "SL"
            return j, tp, "TP"
        s, ch = e, ch * 2
    return n - 1, (m.bc[-1] if side > 0 else m.ac[-1]), "open_at_end"


def _tp(book, exit_mode, side, entry, R, i, known):
    """(tp, fallback_flag, skip_code)"""
    if exit_mode == "2R":
        return entry + side * 2 * R, False, SKIP_NONE
    q = opposite_tp(book, side, entry, i, known)
    if np.isnan(q):
        return entry + side * 2 * R, True, SKIP_NONE
    if side * (q - entry) < R:
        return q, False, SKIP_TP
    return q, False, SKIP_NONE


CAND_COLS = ["zone", "side", "touch_idx", "entry_idx", "entry_price", "stop", "tp", "R",
             "exit_idx", "exit_price", "reason", "r", "zone_size", "spread", "skip", "tp_fallback"]


def candidates(m: M15, book: ZoneBook, version: str, exit_mode: str) -> tuple[pd.DataFrame, dict]:
    rows = []
    st = {"zones": len(book.kind), "dead_expired_untouched": int((book.touch < 0).sum()),
          "dead_B_no_trigger_24h": 0, "dead_B_closed_through_far_edge": 0}
    day24 = 24 * 3600 * 10**9
    for z in np.flatnonzero(book.touch >= 0):
        side = int(book.kind[z])
        top, bot = book.top[z], book.bottom[z]
        t0 = int(book.touch[z])
        if version == "A":
            i = t0
            a = int(book.a_idx[z])
            sp = m.spread[max(a - 1, 0)]                  # known when the order is placed
            buf = max(sp, 0.1 * book.atr[z])
            if side > 0:
                entry, stop = min(m.ao[i], top), bot - buf
            else:
                entry, stop = max(m.bo[i], bot), top + buf
            known, check_entry = i, True
        else:
            w_end = int(np.searchsorted(m.t, m.t[t0] + day24, side="left"))
            ext, i, died = (np.inf if side > 0 else -np.inf), -1, None
            for k in range(t0, w_end):
                if side > 0:
                    ext = min(ext, m.bl[k])
                    if m.bc[k] < bot:
                        died = "dead_B_closed_through_far_edge"
                        break
                    if m.bc[k] > m.sh[k]:                 # NaN compares False
                        i = k
                        break
                else:
                    ext = max(ext, m.bh[k])
                    if m.bc[k] > top:
                        died = "dead_B_closed_through_far_edge"
                        break
                    if m.bc[k] < m.sl[k]:
                        i = k
                        break
            if i < 0:
                st[died or "dead_B_no_trigger_24h"] += 1
                continue
            sp = m.spread[i]
            buf = max(sp, 0.1 * m.atr[i])
            if side > 0:
                entry, stop = m.ac[i], ext - buf
            else:
                entry, stop = m.bc[i], ext + buf
            known, check_entry = i + 1, False
        R = side * (entry - stop)
        skip, tp, fb = SKIP_NONE, np.nan, False
        if not R >= 2 * sp:
            skip = SKIP_STOP
        else:
            tp, fb, skip = _tp(book, exit_mode, side, entry, R, i, known)
        if skip == SKIP_NONE:
            xi, xp, reason = simulate_exit(m, side, stop, tp, i, check_entry)
            r = side * (xp - entry) / R
        else:
            xi, xp, reason, r = -1, np.nan, "", np.nan
        rows.append((z, side, t0, i, entry, stop, tp, R, xi, xp, reason, r, top - bot, sp, skip, fb))
    c = pd.DataFrame(rows, columns=CAND_COLS)
    c = c.sort_values(["entry_idx", "zone"], kind="stable").reset_index(drop=True)
    return c, st


# --------------------------------------------------------------------------- swap
@dataclass
class SwapTable:
    roll_ns: np.ndarray     # 17:00 New York rollovers (weekdays), int64 ns UTC
    cw: np.ndarray          # cumulative day weights (Wednesday = 3)
    cwd: np.ndarray         # cumulative weight x (r_base - r_quote), % p.a.

    def swap_r(self, side, entry_ns, exit_ns, price, R, markup: float = 0.5) -> np.ndarray:
        """Swap in R per trade: for every rollover in (entry, exit], one day (three on
        Wednesday) of (side x (r_base - r_quote) - markup) % p.a. on the position, /365."""
        lo = np.searchsorted(self.roll_ns, entry_ns, side="right")
        hi = np.searchsorted(self.roll_ns, exit_ns, side="right")
        w = self.cw[hi] - self.cw[lo]
        wd = self.cwd[hi] - self.cwd[lo]
        pct = np.asarray(side) * wd - markup * w
        return pct / 100.0 / 365.0 * np.asarray(price) / np.asarray(R)


def rollovers(start: str, end: str) -> pd.DataFrame:
    days = pd.date_range(start, end, freq="D")
    days = days[days.dayofweek < 5]
    utc = (days + pd.Timedelta(hours=17)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None)
    return pd.DataFrame({"ny_date": days, "utc": utc, "w": np.where(days.dayofweek == 2, 3, 1)})


def build_swap(base_rate: pd.DataFrame, quote_rate: pd.DataFrame, start: str, end: str) -> SwapTable:
    r = rollovers(start, end)

    def asof(df):
        s = df.set_index("date")["value"].sort_index()
        return s.reindex(s.index.union(r["ny_date"])).ffill().reindex(r["ny_date"]).to_numpy()

    diff = np.nan_to_num(asof(base_rate) - asof(quote_rate))
    w = r["w"].to_numpy(float)
    return SwapTable(r["utc"].to_numpy().astype("datetime64[ns]").astype(np.int64),
                     np.concatenate([[0.0], np.cumsum(w)]),
                     np.concatenate([[0.0], np.cumsum(w * diff)]))


# --------------------------------------------------------------------------- portfolio
def run_portfolio(entry_idx: list, exit_idx: list, side: list, skip: list, code_at_entry: list):
    """One open position at a time. Returns (taken positions, counts).
    Order of checks at a trigger: day filter -> position already open -> skip rules."""
    taken = []
    filtered = overlap = sk_stop = sk_tp = 0
    pos_exit = -1
    for k in range(len(entry_idx)):
        c = code_at_entry[k]
        if not (c == 2 or c == side[k]):
            filtered += 1
            continue
        if entry_idx[k] <= pos_exit:
            overlap += 1
            continue
        s = skip[k]
        if s:
            if s == SKIP_STOP:
                sk_stop += 1
            else:
                sk_tp += 1
            continue
        taken.append(k)
        pos_exit = exit_idx[k]
    return taken, {"filtered_by_bias": filtered, "skipped_position_open": overlap,
                   SKIP_NAMES[SKIP_STOP]: sk_stop, SKIP_NAMES[SKIP_TP]: sk_tp}


# --------------------------------------------------------------------------- stats
def stats(r: np.ndarray, risk: float = 0.01) -> dict:
    r = np.asarray(r, float)
    n = len(r)
    if n == 0:
        return {"trades": 0, "win_rate": np.nan, "avg_win_R": np.nan, "avg_loss_R": np.nan,
                "profit_factor": np.nan, "expectancy_R": np.nan, "total_R": 0.0,
                "max_dd_pct": 0.0, "longest_losing_streak": 0, "net_return_pct": 0.0, "t_stat": np.nan}
    wins, losses = r[r > 0], r[r <= 0]
    eq = np.cumprod(1 + risk * r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = (1 - eq / peak).max() * 100
    streak = best = 0
    for x in r:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    sd = r.std(ddof=1) if n > 1 else np.nan
    return {"trades": n, "win_rate": len(wins) / n * 100,
            "avg_win_R": wins.mean() if len(wins) else np.nan,
            "avg_loss_R": losses.mean() if len(losses) else np.nan,
            "profit_factor": wins.sum() / -losses.sum() if losses.sum() < 0 else np.inf,
            "expectancy_R": r.mean(), "total_R": r.sum(), "max_dd_pct": dd,
            "longest_losing_streak": best, "net_return_pct": (eq[-1] - 1) * 100,
            "t_stat": r.mean() / sd * np.sqrt(n) if sd and sd > 0 else np.nan}
