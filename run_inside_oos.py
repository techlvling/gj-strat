"""Out-of-sample test of the inside-day breakout on markets never used to pick it.

The rule was found on USDJPY / EURJPY / GBPJPY / EURUSD / GBPUSD (run_patterns_intraday.py, I3)
and is frozen here exactly: after an inside day, OCO stops at that day's high / low (buy stop
+ spread on ask), live 07:00-16:00 UTC, only if price starts inside; SL = that day's range
(min 0.1 x ATR20), TP 1R (primary) or 2R; time exit just before the New York close (no swap).

New markets (all 2010-2026, indices from 2011): gold, JPN225, Nasdaq 100, AUDJPY, CADJPY,
CHFJPY, NZDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD and 15 crosses. Every year of them is unseen.

Costs: FX $7 per 100k round turn + 0.2 pip slippage per stop fill (as before).
Gold: $7 per 100 oz round turn ($0.07/oz) + $0.02 slippage. Nasdaq: 0.25 pt slippage,
JPN225: 2 pt slippage, no commission. Spread is in the bid/ask fills for all.

Pass rule, fixed before running: TP1R pooled over the new markets avg R > 0 with t >= 2,
and positive on more than half of them.

    python run_inside_oos.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import contraction_breakout, daily_table, simulate
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/inside_oos"
NEW = ["XAUUSD", "JPNIDXJPY", "USATECHIDXUSD", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
       "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURGBP", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
       "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "NZDCAD",
       "NZDCHF"]
NON_FX = {"XAUUSD": (0.07, 0.02), "USATECHIDXUSD": (0.0, 0.25), "JPNIDXJPY": (0.0, 2.0)}  # comm, slip (price)


def net_r(m, sym, trades) -> np.ndarray:
    if not trades:
        return np.array([])
    if sym in NON_FX:
        comm, slip = NON_FX[sym]
        return np.array([t.r - (comm + slip * (1 + (t.reason == "SL"))) / t.risk for t in trades])
    lg = account(trades, m, 10_000, risk_pct=0.5, commission=7, sym=sym, slippage_pips=0.2)
    return lg.set_index(["entry_i", "exit_i"]).loc[[(t.entry_i, t.exit_i) for t in trades], "R"].to_numpy()


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, pooled = [], {1: [], 2: []}
    for sym in NEW:
        start = date(2011, 1, 2) if "IDX" in sym else date(2010, 1, 1)    # indices: data from 2011
        m = build_market(sym, start, date(2026, 10, 7), "data/raw",
                         f"data/{sym.lower()}_{start}_2026-10-07.npz")
        d = daily_table(m)
        d = d[d.index >= pd.Timestamp("2010-01-01")]
        row = {"market": sym}
        for rr in (1, 2):
            tr = sorted([t for t in (simulate(m, s) for s in contraction_breakout(m, d, "inside", rr))
                         if t is not None], key=lambda t: (t.entry_i, t.exit_i))
            r = net_r(m, sym, tr)
            pooled[rr].append(r)
            yrs = pd.Series(r, index=[t.day.year for t in tr])
            row.update({f"TP{rr}R trades": len(r), f"TP{rr}R win %": (r > 0).mean() * 100,
                        f"TP{rr}R avg R": r.mean(), f"TP{rr}R t": tstat(r),
                        f"TP{rr}R years positive": f"{(yrs.groupby(level=0).sum() > 0).sum()}/{yrs.index.nunique()}"})
        rows.append(row)
        print(row, flush=True)
        del m
    res = pd.DataFrame(rows).set_index("market")
    res.to_csv(f"{OUT}/summary.csv")
    pool = {}
    for rr in (1, 2):
        r = np.concatenate(pooled[rr])
        pool[rr] = dict(trades=len(r), win=(r > 0).mean() * 100, avg=r.mean(), t=tstat(r),
                        pos=int((res[f"TP{rr}R avg R"] > 0).sum()))
    passed = pool[1]["avg"] > 0 and pool[1]["t"] >= 2 and pool[1]["pos"] > len(NEW) / 2
    lines = [f"- TP{rr}R pooled: {p['trades']} trades, win {p['win']:.1f}%, avg {p['avg']:+.3f}R, "
             f"t {p['t']:.2f}, positive on {p['pos']}/{len(NEW)} markets" for rr, p in pool.items()]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Inside-day breakout — out-of-sample on 26 new markets, 2010–2026\n\n"
        "Rules frozen from run_patterns_intraday.py (I3 inside). Costs and pass rule in run_inside_oos.py.\n\n"
        + "\n".join(lines) + f"\n\n**Verdict (TP1R rule): {'PASS' if passed else 'FAIL'}**\n\n"
        + fmt_table(res, ".3f") + "\n")
    print("\n".join(lines), "\nPASS" if passed else "\nFAIL")
    pd.set_option("display.width", 250)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
