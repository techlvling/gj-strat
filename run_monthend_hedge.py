"""Month-end hedge rebalancing on USDJPY, signalled by US vs Japanese equities (2011-2026).

Idea: Japanese holders of hedged US equities (and US holders of hedged Japanese equities) rebalance
FX hedges at the month-end London 4pm (WM/R) fix. If US stocks beat Japanese stocks month-to-date,
there are more US assets to re-hedge -> USD selling -> SELL USDJPY into the fix; else BUY.
Signal: Nasdaq 100 MTD return minus JPN225 MTD return (each in its own currency), from the previous
month-end 16:00 London to the entry time (bid closes of the index CFDs).

Pre-declared variants (6): entry 14:00 London on the last trading day / 00:00 UTC (Tokyo morning)
of the last day / 16:05 London the day before; all exit 16:05 London on the last day, SL 0.5 x ATR20.
x signal filter: every month / only |gap| >= 2%. Quarter-ends reported as a subset (not selected on).
Selection: best design (2011-2017) t; counts only if design t >= 2 and avg R > 0 in check
(2018-2023) and holdout (2024-2026). Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_monthend_hedge.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import LDN, Signal, daily_table, local_idx, month_end_days, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

OUT = "results/monthend_hedge"


def price_at(mx, ts: pd.Timestamp) -> float:
    i = int((ts - mx.t0) // pd.Timedelta(minutes=1))
    return mx.bc[i] if 0 <= i < mx.n else np.nan


def ldn_utc(day, hh, mm):
    return (day + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(LDN).tz_convert("UTC").tz_localize(None)


def main():
    os.makedirs(OUT, exist_ok=True)
    uj = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    nas = build_market("USATECHIDXUSD", date(2011, 1, 2), date(2026, 10, 7), "data/raw",
                       "data/usatechidxusd_2011-01-02_2026-10-07.npz")
    jpn = build_market("JPNIDXJPY", date(2011, 1, 2), date(2026, 10, 7), "data/raw", "data/jpnidxjpy_2011-01-02_2026-10-07.npz")
    swap = SwapModel.from_fred("rates", 1.0)
    d = daily_table(uj)
    d = d[d.index >= pd.Timestamp("2011-01-01")]
    ends = month_end_days(d)
    sessions = list(d.index)
    entries = {"14:00 LDN last day": lambda day, prev: ldn_utc(day, 14, 0),
               "Tokyo morning last day": lambda day, prev: day,                    # 00:00 UTC
               "16:05 LDN day before": lambda day, prev: ldn_utc(prev, 16, 5)}
    rows, logs = [], {}
    for ename, entry_fn in entries.items():
        for filt in ("all", "gap>=2%"):
            sigs, info = [], []
            for k in range(1, len(ends)):
                day, last = ends[k], ends[k - 1]
                prev = sessions[sessions.index(day) - 1]
                t_in, t_out = entry_fn(day, prev), ldn_utc(day, 16, 5)
                base_t = ldn_utc(last, 16, 0)
                n0, n1, j0, j1 = (price_at(nas, base_t), price_at(nas, t_in), price_at(jpn, base_t), price_at(jpn, t_in))
                if np.isnan([n0, n1, j0, j1]).any() or min(n0, j0) <= 0:
                    continue
                gap = (n1 / n0 - 1) - (j1 / j0 - 1)
                if filt == "gap>=2%" and abs(gap) < 0.02:
                    continue
                i_in, i_out = uj.idx(t_in), uj.idx(t_out)
                side = "SELL" if gap > 0 else "BUY"                     # US outperformed -> USD selling
                sigs.append(Signal(day, side, i_in, "market", None, i_in + 1, 0.5 * d.loc[day, "atr20"], None,
                                   i_out, "me-hedge"))
                info.append((day, gap))
            tr = [(t, g) for (t, g) in ((simulate(uj, s), g) for s, (_, g) in zip(sigs, info)) if t is not None]
            ts = sorted([t for t, _ in tr], key=lambda t: (t.exit_i, t.entry_i))
            lg = account(ts, uj, 10_000, risk_pct=0.5, commission=7, swap=swap, sym="USDJPY", slippage_pips=0.2)
            r, day_ = lg["R"].to_numpy(), pd.to_datetime(lg["day"])
            name = f"{ename}, {filt}"
            row = {"setup": name}
            for per, (a, b) in PERIODS.items():
                a = max(pd.Timestamp(a), pd.Timestamp("2011-01-01"))
                x = r[np.asarray((day_ >= a) & (day_ <= pd.Timestamp(b)))]
                row.update({f"{per} trades": len(x), f"{per} win %": (x > 0).mean() * 100 if len(x) else np.nan,
                            f"{per} avg R": x.mean() if len(x) else np.nan, f"{per} t": tstat(x)})
            q = r[np.asarray(day_.dt.month.isin([3, 6, 9, 12]))]
            row.update({"all trades": len(r), "all avg R": r.mean(), "all t": tstat(r),
                        "quarter-end trades": len(q), "quarter-end avg R": q.mean()})
            rows.append(row)
            print(row, flush=True)
    res = pd.DataFrame(rows).set_index("setup")
    res.to_csv(f"{OUT}/grid.csv")
    best = res["design t"].idxmax()
    ok = {"design t >= 2": res.loc[best, "design t"] >= 2, "check avg R > 0": res.loc[best, "check avg R"] > 0,
          "holdout avg R > 0": res.loc[best, "holdout avg R"] > 0}
    verdict = "PASS" if all(ok.values()) else "FAIL"
    cols = [f"{p} {c}" for p in ("design", "check", "holdout") for c in ("trades", "win %", "avg R", "t")] + \
           ["all avg R", "all t", "quarter-end trades", "quarter-end avg R"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Month-end hedge rebalancing on USDJPY (Nasdaq vs JPN225 signal), 2011–2026\n\n"
        "Rules, variants and selection in run_monthend_hedge.py (fixed before running).\n\n"
        f"**Design-best: {best}** — " + ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in ok.items()) +
        f" → **{verdict}**\n\n" + fmt_table(res[cols].sort_values("design t", ascending=False), ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(3).to_string())
    print(best, ok, verdict)


if __name__ == "__main__":
    main()
