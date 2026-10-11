"""Per-day event loop: overnight profile -> 15m bias -> 1m sweep / drive-in / drive-out -> exits.

Fills: buys at ask, sells at bid; longs exit on bid, shorts on ask. Signals use mid bars.
Long stop = sweep low - spread (spread = ask - bid at the entry bar's close); short mirror.
1R = |fill - stop|. R result = price move / 1R - commission per unit / 1R.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .core import (ENTRY_END, EOD, GAP_CHECK, ON_START, RTH_OPEN, Bias, atr15_at_close, bars15,
                   drive_in, drive_out, find_bias, obvious_level, sma, swing_highs, swing_lows,
                   true_range, value_area, volume_profile)


@dataclass(frozen=True)
class Params:
    """Fixed rules (not swept)."""
    min_on_bars: int = 360          # overnight window needs >= 6 h of 1m bars
    max_gap_min: int = 30           # no gap over 30 min between 07:00 and 09:30
    bin_size: float = 1.0
    va_pct: float = 0.70
    swing_n: int = 5
    lookback: int = 60
    atr1_n: int = 20
    atr1_incl_bar: bool = True      # ATR(20, 1m) for body tests includes the tested bar (False: prior 20)
    atr15_n: int = 14
    body_k: float = 1.5
    drive_in_bars: int = 10
    drive_out_bars: int = 5
    min_reward: float = 1.5
    max_stop_atr15: float = 2.0
    b2_rr: float = 2.0
    fixed_rr: float = 2.0
    nf_near_atr15: float = 1.0
    commission: float = 0.0         # $ per unit round turn (1 unit = $1 per point)


@dataclass(frozen=True)
class Variant:
    start: int = RTH_OPEN           # eligible start for 15m bias bars: 570 (09:30) or 585 (09:45)
    target: str = "POC"             # reversal (B1) target: "POC" or "2R"
    acceptance: bool = True         # B2 acceptance trades
    be: bool = False                # break-even at +1R
    entry: str = "close"            # "close" (signal bar close) or "next_open" (robustness)
    mode: str = "strategy"          # "strategy" or "nofilter" (benchmark 1)

    @property
    def name(self) -> str:
        if self.mode == "nofilter":
            return f"NOFILTER|2R|BE{'on' if self.be else 'off'}" + ("|nextopen" if self.entry != "close" else "")
        return (f"{'0930' if self.start == RTH_OPEN else '0945'}|{self.target}|"
                f"B2{'on' if self.acceptance else 'off'}|BE{'on' if self.be else 'off'}"
                + ("|nextopen" if self.entry != "close" else ""))


@dataclass
class Day:
    date: date
    tod: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    bo: np.ndarray
    bh: np.ndarray
    bl: np.ndarray
    bc: np.ndarray
    ao: np.ndarray
    ah: np.ndarray
    al: np.ndarray
    ac: np.ndarray
    v: np.ndarray
    poc: float = np.nan
    vah: float = np.nan
    val: float = np.nan
    va_coverage: float = np.nan
    s15: np.ndarray = field(default=None)
    h15: np.ndarray = field(default=None)
    l15: np.ndarray = field(default=None)
    c15: np.ndarray = field(default=None)
    atr20: np.ndarray = field(default=None)
    atr15_at: np.ndarray = field(default=None)
    i0: int = 0
    i_end: int = 0
    e_end: int = 0
    lvl: dict = field(default_factory=dict)       # side -> level array (NaN = none)
    di_ok: dict = field(default_factory=dict)     # side -> drive-in ok if bar is the sweep extreme
    di_gap: dict = field(default_factory=dict)    # side -> gap level for that drive-in

    def time(self, m: int) -> pd.Timestamp:
        return pd.Timestamp(self.date) + pd.Timedelta(minutes=int(m))


# --------------------------------------------------------------------------- day preparation
def day_slice(frame: pd.DataFrame, d: date, hist_hours: int = 12) -> pd.DataFrame:
    """Bars from (d-1) 12:00 ET to d 16:00 ET; frame is indexed by naive ET wall-clock time."""
    D = pd.Timestamp(d)
    idx = frame.index.values
    a = np.searchsorted(idx, (D - pd.Timedelta(hours=hist_hours)).to_datetime64())
    b = np.searchsorted(idx, (D + pd.Timedelta(minutes=EOD)).to_datetime64())
    return frame.iloc[a:b]


def overnight_quality(tod: np.ndarray) -> tuple[int, int]:
    """(1m bars in 18:00 prior day .. 09:29, longest run of missing minutes between 07:00 and 09:30)."""
    on = int(((tod >= ON_START) & (tod < RTH_OPEN)).sum())
    w = tod[(tod >= GAP_CHECK) & (tod < RTH_OPEN)]
    if len(w) == 0:
        return on, RTH_OPEN - GAP_CHECK
    edges = np.r_[GAP_CHECK - 1, w, RTH_OPEN]
    return on, int((np.diff(edges) - 1).max())


def prepare_day(sl: pd.DataFrame, d: date, P: Params = Params()) -> tuple[Day | None, dict]:
    """Everything that does not depend on the variant. Returns (Day or None if skipped, info)."""
    D = pd.Timestamp(d)
    tod = ((sl.index.values - D.to_datetime64()) // np.timedelta64(1, "m")).astype(np.int64)
    on_bars, max_gap = overnight_quality(tod)
    info = dict(date=d, on_bars=on_bars, max_gap_0700=max_gap, skip="")
    if on_bars < P.min_on_bars:
        info["skip"] = "overnight_lt_6h"
        return None, info
    if max_gap > P.max_gap_min:
        info["skip"] = "gap_gt_30m_0700_0930"
        return None, info
    if not ((tod >= RTH_OPEN) & (tod < ENTRY_END)).any():
        info["skip"] = "no_bars_0930_1100"
        return None, info
    g = lambda col: sl[col].to_numpy(np.float64)
    bo, bh, bl, bc, ao, ah, al, ac = (g(x) for x in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"))
    day = Day(date=d, tod=tod, o=(bo + ao) / 2, h=(bh + ah) / 2, l=(bl + al) / 2, c=(bc + ac) / 2,
              bo=bo, bh=bh, bl=bl, bc=bc, ao=ao, ah=ah, al=al, ac=ac, v=g("v"))
    compute_features(day, P)
    info.update(poc=day.poc, vah=day.vah, val=day.val)
    return day, info


def compute_features(day: Day, P: Params = Params()) -> Day:
    tod, o, h, l, c = day.tod, day.o, day.h, day.l, day.c
    on = (tod >= ON_START) & (tod < RTH_OPEN)        # 18:00 prior day .. bar 09:29 (closes 09:30)
    k0, prof = volume_profile(l[on], h[on], day.v[on], P.bin_size)
    lv = value_area(k0, prof, P.bin_size, P.va_pct)
    day.poc, day.vah, day.val = lv.poc, lv.vah, lv.val
    day.va_coverage = lv.coverage
    day.s15, o15, day.h15, day.l15, day.c15 = bars15(tod, o, h, l, c)
    atr15 = sma(true_range(day.h15, day.l15, day.c15), P.atr15_n)
    day.atr15_at = atr15_at_close(tod, day.s15, atr15)
    day.atr20 = sma(true_range(h, l, c), P.atr1_n)        # includes the bar itself (closed)
    if not P.atr1_incl_bar:
        day.atr20 = np.r_[np.nan, day.atr20[:-1]]
    day.i0 = int(np.searchsorted(tod, RTH_OPEN))
    day.i_end = int(np.searchsorted(tod, ENTRY_END))
    day.e_end = int(np.searchsorted(tod, EOD))
    n = len(tod)
    sw = {1: swing_lows(l, P.swing_n), -1: swing_highs(h, P.swing_n)}
    for side, px in ((1, l), (-1, h)):
        lvl = np.full(n, np.nan)
        ok = np.zeros(n, bool)
        gap = np.full(n, np.nan)
        for t in range(day.i0, day.i_end):
            lvl[t] = obvious_level(px, sw[side], t, side, P.swing_n, P.lookback)[0]
            ok[t], gap[t] = drive_in(o, h, l, c, day.atr20, t, side, P.drive_in_bars, P.body_k)
        day.lvl[side], day.di_ok[side], day.di_gap[side] = lvl, ok, gap
    return day


def day_bias(day: Day, v: Variant) -> Bias:
    return find_bias(day.s15, day.h15, day.l15, day.c15, day.vah, day.val, v.start, v.acceptance)


# --------------------------------------------------------------------------- exits
def simulate_exit(day: Day, side: int, u0: int, entry: float, stop: float, tp: float,
                  dist: float, be_on: bool) -> tuple[int, float, str]:
    """Walk 1m bars u0 .. last bar before 16:00. Long exits on bid, short on ask. Per bar: stop
    first (a bar opening beyond the stop fills at its open), then TP (limit, fills at TP), then the
    BE trigger (+1R on the exit side). A BE stop sits at entry and is live from the next bar.
    No exit by 16:00 -> close of the last bar before 16:00. Returns (bar, price, reason)."""
    if side > 0:
        O, H, L, C = day.bo, day.bh, day.bl, day.bc
    else:
        O, H, L, C = day.ao, day.ah, day.al, day.ac
    cur, be_live, armed = stop, False, False
    for u in range(u0, day.e_end):
        if armed:
            cur, be_live, armed = entry, True, False
        hit = "BE" if be_live else "SL"
        if side > 0:
            if O[u] <= cur:
                return u, O[u], hit
            if L[u] <= cur:
                return u, cur, hit
            if H[u] >= tp:
                return u, tp, "TP"
            if be_on and not be_live and H[u] >= entry + dist:
                armed = True
        else:
            if O[u] >= cur:
                return u, O[u], hit
            if H[u] >= cur:
                return u, cur, hit
            if L[u] <= tp:
                return u, tp, "TP"
            if be_on and not be_live and L[u] <= entry - dist:
                armed = True
    last = max(day.e_end - 1, u0 - 1)
    return last, C[last], "EOD"


class DayLimits:
    """X2/X3: a TP ends the day; two stop-losses in a row end the day; a BE exit is neither a win
    nor a loss (does not reset or add to the count); 16:00 ends the day anyway."""

    def __init__(self):
        self.consec_sl = 0
        self.done = ""

    def record(self, reason: str) -> None:
        if reason == "TP":
            self.done = "TP"
        elif reason == "SL":
            self.consec_sl += 1
            if self.consec_sl >= 2:
                self.done = "2SL"
        elif reason == "EOD":
            self.done = "EOD"


# --------------------------------------------------------------------------- the day loop
def run_day(day: Day, v: Variant, bias: Bias | None, P: Params = Params(),
            trace: list | None = None) -> tuple[list[dict], Counter]:
    """trace: optional list; each setup's end is appended as (event, side, extreme bar, end bar)."""
    cnt: Counter = Counter()
    trades: list[dict] = []
    if v.mode == "strategy":
        if bias is None or bias.side == 0:
            return trades, cnt
        sides, w0, kind = (bias.side,), max(RTH_OPEN, bias.active), bias.kind
    else:
        sides, w0, kind = (1, -1), RTH_OPEN, "NF"
    lim = DayLimits()
    setup = None                                   # [side, sweep extreme bar]
    t = int(np.searchsorted(day.tod, w0))          # first bar opening at/after the window start
    while t < day.i_end and not lim.done:
        if setup is None:                          # E1/E2: look for a sweep of the obvious level
            cands = []
            for sd in sides:
                lvl = day.lvl[sd][t]
                if np.isnan(lvl) or not ((day.l[t] < lvl) if sd > 0 else (day.h[t] > lvl)):
                    continue
                if v.mode == "nofilter" and not (min(abs(lvl - day.vah), abs(lvl - day.val))
                                                 <= P.nf_near_atr15 * day.atr15_at[t]):
                    cnt["nf_sweep_not_near_va"] += 1
                    continue
                cands.append(sd)
            if len(cands) == 2:
                cnt["sweep_both_sides_same_bar"] += 1
            elif cands:
                setup = [cands[0], t]
                cnt["setups_started"] += 1
            t += 1
            continue
        sd, s = setup
        if (day.l[t] < day.l[s]) if sd > 0 else (day.h[t] > day.h[s]):   # new extreme: restart clock
            setup[1] = t
            cnt["sweep_extreme_updated"] += 1
            t += 1
            continue
        ok = day.di_ok[sd][s]
        if ok and drive_out(day.o, day.c, day.atr20, t, sd, day.di_gap[sd][s], P.body_k):
            cnt["signals"] += 1
            if trace is not None:
                trace.append(("signal", sd, s, t))
            setup = None
            tr = take_signal(day, v, kind, t, sd, s, P, cnt)
            if tr is None:
                t += 1
                continue
            trades.append(tr)
            lim.record(tr["exit_reason"])
            t = tr["exit_i"] + 1
            continue
        if t - s >= P.drive_out_bars:
            cnt["died_no_drive_out_5bars" if ok else "died_no_drive_in"] += 1
            if trace is not None:
                trace.append(("died_no_drive_out" if ok else "died_no_drive_in", sd, s, t))
            setup = None
        t += 1
    if setup is not None:
        cnt["died_entry_window_end"] += 1
        if trace is not None:
            trace.append(("died_window_end", setup[0], setup[1], t))
    if lim.done in ("TP", "2SL"):
        cnt[f"day_done_{lim.done}"] += 1
    return trades, cnt


def take_signal(day: Day, v: Variant, kind: str, t: int, sd: int, s: int, P: Params,
                cnt: Counter) -> dict | None:
    """E5/E6 at the signal bar's close, then the fill and the exit walk."""
    entry_sig = day.ac[t] if sd > 0 else day.bc[t]
    spread = day.ac[t] - day.bc[t]
    stop = day.l[s] - spread if sd > 0 else day.h[s] + spread
    dist = (entry_sig - stop) * sd
    if not dist > 0:                               # cannot happen with a valid drive-out; guard
        cnt["skip_nonpositive_stop"] += 1
        return None
    if kind == "B1" and v.target == "POC":
        tp = day.poc
        reward = (tp - entry_sig) * sd / dist
    else:
        reward = P.b2_rr if kind == "B2" else P.fixed_rr
        tp = entry_sig + sd * reward * dist
    a15 = day.atr15_at[t]
    reasons = []
    if reward < P.min_reward:
        reasons.append("reward_lt_1.5R")
    if not dist <= P.max_stop_atr15 * a15:
        reasons.append("stop_gt_2xATR15")
    if kind == "B1" and (day.poc - entry_sig) * sd <= 0:
        reasons.append("poc_wrong_side")
    if reasons:
        cnt["signals_skipped"] += 1
        for r in reasons:
            cnt["skip_" + r] += 1
        return None
    if v.entry == "next_open":                     # robustness: fill at the next bar's open
        fi = t + 1
        if fi >= day.e_end:
            cnt["skip_no_next_bar"] += 1
            return None
        fill, u0, entry_tod = (day.ao[fi] if sd > 0 else day.bo[fi]), fi, int(day.tod[fi])
        opp_fill = day.bo[fi] if sd > 0 else day.ao[fi]
    else:
        fill, u0, entry_tod = entry_sig, t + 1, int(day.tod[t]) + 1
        opp_fill = day.bc[t] if sd > 0 else day.ac[t]
    u, px, reason = simulate_exit(day, sd, u0, fill, stop, tp, dist, v.be)
    comm_r = P.commission / dist
    r = (px - fill) * sd / dist - comm_r
    # same timestamp, same stop distance and target multiple, opposite side (random benchmark)
    o_stop, o_tp = opp_fill + sd * dist, opp_fill - sd * reward * dist
    ou, opx, oreason = simulate_exit(day, -sd, u0, opp_fill, o_stop, o_tp, dist, v.be)
    r_opp = (opx - opp_fill) * (-sd) / dist - comm_r
    exit_tod = int(day.tod[u]) + (1 if reason == "EOD" else 0)
    return dict(date=day.date, side="LONG" if sd > 0 else "SHORT", bias_type=kind,
                entry_time=day.time(entry_tod), entry_price=fill,
                exit_time=day.time(exit_tod), exit_price=px, stop_price=stop, tp_price=tp,
                stop_dist=dist, reward_R=reward, R=r, exit_reason=reason,
                sweep_extreme=day.l[s] if sd > 0 else day.h[s], sweep_bar_time=day.time(day.tod[s]),
                signal_time=day.time(int(day.tod[t]) + 1), spread=spread, atr15=a15,
                poc=day.poc, vah=day.vah, val=day.val, r_opp=r_opp, opp_exit_reason=oreason,
                entry_i=u0, exit_i=u)
