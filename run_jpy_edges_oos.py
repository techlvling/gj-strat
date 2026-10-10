"""Out-of-sample test of the two USDJPY edges on markets never used to find them.

Frozen rules:
  * gotobi Tokyo-fix short: on gotobi days sell at 00:55 UTC (09:55 JST fix), exit 06:00 UTC,
    SL 0.25 x ATR20 (tokyo_fix mode=post, at=(6, 0), days_filter=gotobi)
  * green box: Version B, SL 1 x box + spread, RR 9, BE 3R -> +5/30 SL, 05:00 IST box
Clean markets (every year unseen): AUDJPY, CADJPY, CHFJPY, NZDJPY, JPN225 (from 2011).
EURJPY / GBPJPY were looked at before, so they are shown for reference only and not pooled.

Costs: FX $7/lot + 0.2 pip slippage per stop fill, swap (+1% markup) on the box (it holds
overnight; gotobi exits the same morning). JPN225: 2 pt slippage, no commission, no swap model.
Pass rule, fixed before running: per edge, pooled over the 5 clean markets avg R > 0 with t >= 2.

    python run_jpy_edges_oos.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, simulate, tokyo_fix
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/jpy_edges_oos"
CLEAN = ["AUDJPY", "CADJPY", "CHFJPY", "NZDJPY", "JPNIDXJPY"]
REF = ["EURJPY", "GBPJPY", "USDJPY"]
GREEN = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0)
IDX_SLIP = 2.0


def net_r(m, sym, trades, swap) -> np.ndarray:
    if not trades:
        return np.array([])
    trades = sorted(trades, key=lambda t: (t.entry_i, t.exit_i))
    if "IDX" in sym:
        return np.array([t.r - IDX_SLIP * (1 + (t.reason in ("SL", "BE"))) / t.risk for t in trades])
    lg = account(trades, m, 10_000, risk_pct=0.5, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
    return lg.set_index(["entry_i", "exit_i"]).loc[[(t.entry_i, t.exit_i) for t in trades], "R"].to_numpy()


def main():
    os.makedirs(OUT, exist_ok=True)
    swap = SwapModel.from_fred("rates", 1.0)
    rows, pooled = [], {"gotobi": [], "box": []}
    for sym in CLEAN + REF:
        start = date(2011, 1, 2) if "IDX" in sym else date(2010, 1, 1)
        m = build_market(sym, start, date(2026, 10, 7), "data/raw",
                         f"data/{sym.lower()}_{start}_2026-10-07.npz")
        d = daily_table(m)
        d = d[d.index >= pd.Timestamp(start)]
        got = [t for t in (simulate(m, s) for s in tokyo_fix(m, d, mode="post", at=(6, 0), days_filter="gotobi"))
               if t is not None]
        days = trading_days(m, start=str(start))
        _, probe = run(m, Params(sl_box_mult=1.0), days)
        skipped = {x for x, _ in probe.skipped_dates}
        box, _ = run(m, GREEN, [x for x in days if x.date() not in skipped])
        row = {"market": sym, "clean": sym in CLEAN}
        for name, tr, sw in (("gotobi", got, None), ("box", box, swap)):
            r = net_r(m, sym, tr, sw)
            if sym in CLEAN:
                pooled[name].append(r)
            yrs = pd.Series(r, index=[t.day.year for t in sorted(tr, key=lambda t: (t.entry_i, t.exit_i))])
            row.update({f"{name} trades": len(r), f"{name} win %": (r > 0).mean() * 100,
                        f"{name} avg R": r.mean(), f"{name} t": tstat(r),
                        f"{name} years +": f"{(yrs.groupby(level=0).sum() > 0).sum()}/{yrs.index.nunique()}"})
        rows.append(row)
        print(row, flush=True)
        del m
    res = pd.DataFrame(rows).set_index("market")
    res.to_csv(f"{OUT}/summary.csv")
    lines, verdict = [], {}
    for name, rs in pooled.items():
        r = np.concatenate(rs)
        verdict[name] = r.mean() > 0 and tstat(r) >= 2
        lines.append(f"- {name}: pooled over {len(CLEAN)} clean markets {len(r)} trades, win {(r > 0).mean() * 100:.1f}%, "
                     f"avg {r.mean():+.3f}R, t {tstat(r):.2f} -> {'PASS' if verdict[name] else 'FAIL'}")
    open(f"{OUT}/REPORT.md", "w").write(
        "# USDJPY edges on unseen JPY markets — gotobi short and green box, 2010–2026\n\n"
        "Frozen rules, costs and pass rule in run_jpy_edges_oos.py. EURJPY / GBPJPY / USDJPY rows are "
        "reference only (not clean).\n\n" + "\n".join(lines) + "\n\n" + fmt_table(res, ".3f") + "\n")
    print("\n".join(lines))
    pd.set_option("display.width", 250)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
