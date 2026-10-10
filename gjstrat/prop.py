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
               last_start: str = "2025-10-07", **rules) -> pd.DataFrame:
    """legs: [(trades, net R array aligned with trades), ...]; mixes: name -> risk % per leg.
    rules: passed to run_prop_sim.challenge (targets, max_dd, daily, min_days, consistency)."""
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
            r, _, pos = challenge(ev, R, ny_day, cal_day, s, risk, **rules)
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
                     "fails by daily limit %": (res.result == "fail: daily 4%").mean() * 100,
                     "max DD %": dd * 100, "per year %": (bal ** (1 / years) - 1) * 100,
                     "pass eventually %": passed[done].mean() * 100,
                     "avg days per attempt": res.days[done].mean()})
    return pd.DataFrame(rows).set_index("mix")


def instant_table(m: Market, legs: list[tuple[list, np.ndarray]], mixes: dict[str, tuple[float, ...]],
                  cushions=(0.10,), size: float = 2_500, split: float = 0.8, min_pay: float = 100,
                  every: int = 14, dd: float = 0.10, qday: float = 0.005, ndays: int = 5,
                  last_start: str = "2024-10-07", horizon: int = 730) -> pd.DataFrame:
    """Instant-funded account (Blueberry Instant Elite rules, see run_blueberry_elite.py): drawdown `dd`
    trailing the balance high and locking at the start balance; a payout every `every` days once `ndays`
    qualifying days (day P/L >= qday x the day's start balance) have passed since the last one, taking the
    profit above max(start, floor + cushion), trader share `split`, at least `min_pay`; no open trades at
    the payout moment. Accounts start on every trading day up to `last_start` and run `horizon` days.
    legs: [(trades, net R array aligned with trades), ...]; mixes: name -> risk % per leg."""
    allt = [(t, r, s) for s, (tr, rs) in enumerate(legs) for t, r in zip(tr, rs)]
    allt.sort(key=lambda x: (x[0].entry_i, x[0].exit_i))
    T = [x[0] for x in allt]
    R = np.array([x[1] for x in allt])
    S = np.array([x[2] for x in allt])
    ev = sorted([(t.entry_i, 1, k) for k, t in enumerate(T)] +
                [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(T)])
    kind = np.array([o == 1 for _, o, _ in ev])
    trade = np.array([k for _, _, k in ev])
    bar = np.array([b for b, _, _ in ev])
    ny = np.array((pd.DatetimeIndex([m.ts(t.exit_i) for t in T]).tz_localize("UTC").tz_convert("America/New_York")
                   + pd.Timedelta(hours=7)).tz_localize(None).normalize())
    first_pos = {}
    for p in np.flatnonzero(kind):
        first_pos.setdefault(trade[p], p)
    rows = []
    for cush in cushions:
        for name, mix in mixes.items():
            risk = np.array(mix, dtype=float)[S]
            live = [k for k in range(len(T)) if risk[k] > 0]
            starts = [k for i, k in enumerate(live) if (i == 0 or T[k].day != T[live[i - 1]].day)
                      and T[k].day <= pd.Timestamp(last_start)]
            out = []
            for s0 in starts:
                t0 = m.ts(T[s0].entry_i)
                bal, peak, floor, open_ = 1.0, 1.0, 1 - dd, {}
                cur, day0, day_pnl, qdays = None, 1.0, 0.0, 0
                paid, pay12, n_pay, next_pay, breached, first_pay = 0.0, 0.0, 0, t0 + pd.Timedelta(days=every), False, None
                for p in range(first_pos[s0], len(ev)):
                    k = trade[p]
                    if k < s0 or risk[k] == 0:
                        continue
                    now = m.ts(bar[p])
                    if now > t0 + pd.Timedelta(days=horizon):
                        break
                    while now >= next_pay:
                        base = max(1.0, floor + cush)
                        amt = (bal - base) * size
                        if amt * split >= min_pay and qdays >= ndays and not open_:
                            paid += amt * split; n_pay += 1; qdays = 0
                            pay12 += amt * split if next_pay <= t0 + pd.Timedelta(days=365) else 0
                            first_pay = first_pay or (next_pay - t0).days
                            bal = base
                        next_pay += pd.Timedelta(days=every)
                    if kind[p]:
                        open_[k] = risk[k] / 100 * bal
                        continue
                    if k not in open_:
                        continue
                    if ny[k] != cur:
                        if cur is not None and day_pnl >= qday * day0:
                            qdays += 1
                        cur, day0, day_pnl = ny[k], bal, 0.0
                    pnl = open_.pop(k) * R[k]
                    bal += pnl; day_pnl += pnl
                    peak = max(peak, bal)
                    floor = min(max(floor, peak - dd), 1.0)
                    if bal <= floor:
                        breached = True
                        break
                out.append((paid, pay12, n_pay, breached, first_pay))
            o = pd.DataFrame(out, columns=["paid", "paid12", "n", "breached", "first"])
            months = horizon / 365.25 * 12
            rows.append({"cushion kept": f"{cush:.0%}", "plan": name, "got ≥1 payout %": (o.n > 0).mean() * 100,
                         "days to first payout (median)": o["first"].median(),
                         "avg paid in 12 months $": o.paid12.mean(), "median paid in 12 months $": o.paid12.median(),
                         "avg paid in 24 months $": o.paid.mean(), "avg per month $": o.paid.mean() / round(months),
                         "account lost within 24 months %": o.breached.mean() * 100})
    return pd.DataFrame(rows).set_index(["cushion kept", "plan"])
