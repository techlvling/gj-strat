"""Prop-challenge pass rates for a portfolio of strategies on one minute grid.

Challenge (as run_prop_sim.challenge): P1 +8%, P2 +6%, static 10% max loss, 4% daily loss (NY day),
>= 3 trading days per phase. A challenge starts at the first trade the mix itself takes on every
trading day up to `last_start`; risk is a % of the current balance per strategy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import Market


def prop_table(m: Market, legs: list[tuple[list, np.ndarray]], mixes: dict[str, tuple[float, ...]],
               last_start: str = "2025-10-07") -> pd.DataFrame:
    """legs: [(trades, net R array aligned with trades), ...]; mixes: name -> risk % per leg."""
    from run_prop_sim import challenge
    trades = [(t, r, s) for s, (tr, rs) in enumerate(legs) for t, r in zip(tr, rs)]
    trades.sort(key=lambda x: (x[0].entry_i, x[0].exit_i, x[2]))
    T = [x[0] for x in trades]
    R = np.array([x[1] for x in trades])
    strat = np.array([x[2] for x in trades])
    exit_utc = pd.DatetimeIndex([m.ts(t.exit_i) for t in T])
    ny_day = np.array((exit_utc.tz_localize("UTC").tz_convert("America/New_York") + pd.Timedelta(hours=7))
                      .tz_localize(None).normalize())
    cal_day = np.array([t.day for t in T])
    raw = sorted([(t.entry_i, 1, k) for k, t in enumerate(T)] +
                 [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(T)])
    kind = np.array([1 if o == 1 else 0 for _, o, _ in raw])
    trade = np.array([k for _, _, k in raw])
    first_pos = np.empty(len(T), dtype=int)
    for pos in np.flatnonzero(kind == 1):
        first_pos[trade[pos]] = pos
    ev = {"kind": kind, "trade": trade, "first_pos": first_pos}
    bar_of_pos = np.array([x for x, _, _ in raw])
    rows = []
    for name, mix in mixes.items():
        risk = np.array(mix, dtype=float)[strat]
        live = np.flatnonzero(risk > 0)
        starts = [k for i, k in enumerate(live) if (i == 0 or cal_day[k] != cal_day[live[i - 1]])
                  and cal_day[k] <= pd.Timestamp(last_start)]
        res = []
        for s in starts:
            r, _, pos = challenge(ev, R, ny_day, cal_day, s, risk)
            res.append((r, (m.ts(bar_of_pos[pos]) - m.ts(T[s].entry_i)).days))
        res = pd.DataFrame(res, columns=["result", "days"])
        passed = res.result == "PASS"
        bal, peak, dd, open_, eq_t = 1.0, 1.0, 0.0, {}, []
        for pos in range(len(kind)):
            k = trade[pos]
            if risk[k] == 0:
                continue
            if kind[pos] == 1:
                open_[k] = risk[k] / 100 * bal
            else:
                bal += open_.pop(k) * R[k]
                peak = max(peak, bal)
                dd = max(dd, 1 - bal / peak)
                eq_t.append(m.ts(T[k].exit_i))
        years = (eq_t[-1] - eq_t[0]).days / 365.25
        done = res.result != "unfinished"
        rows.append({"mix": name, "challenges": len(res),
                     "pass ≤1 month %": (passed & (res.days <= 31)).mean() * 100,
                     "pass ≤2 months %": (passed & (res.days <= 61)).mean() * 100,
                     "pass ≤3 months %": (passed & (res.days <= 92)).mean() * 100,
                     "pass ≤6 months %": (passed & (res.days <= 183)).mean() * 100,
                     "fail ≤6 months %": (res.result.str.startswith("fail") & (res.days <= 183)).mean() * 100,
                     "median months to pass": res.days[passed].median() / 30.4,
                     "fails by daily 4% %": (res.result == "fail: daily 4%").mean() * 100,
                     "max DD %": dd * 100, "per year %": (bal ** (1 / years) - 1) * 100,
                     "pass eventually %": passed[done].mean() * 100,
                     "avg days per attempt": res.days[done].mean()})
    return pd.DataFrame(rows).set_index("mix")
