"""The green strategy (Version B, SL 1 x box + spread, RR 9, BE 3R, 05:00 IST box) unchanged on
other pairs over 2010-2026, with all costs ($7/lot, swap +1% markup, 0.2 pip slippage).

Same periods and survival rule as the pattern search, fixed before running:
design 2010-2017 avg R > 0 with t >= 2 AND check 2018-2023 avg R > 0. Holdout 2024-2026 shown.

    python run_box_multi.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

PAIRS = ["USDJPY", "EURJPY", "GBPJPY", "EURUSD", "GBPUSD"]
OUT = "results/box_multi"
GREEN = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0)


def main():
    os.makedirs(OUT, exist_ok=True)
    swap = SwapModel.from_fred("rates", 1.0)
    rows = []
    for sym in PAIRS:
        m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                         f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        days = trading_days(m, start="2010-01-01")
        _, probe = run(m, Params(sl_box_mult=1.0), days)
        skipped = {d for d, _ in probe.skipped_dates}
        trades, _ = run(m, GREEN, [d for d in days if d.date() not in skipped])
        row = {"pair": sym}
        for pname, (a, b) in PERIODS.items():
            ts = [t for t in trades if pd.Timestamp(a) <= t.day <= pd.Timestamp(b)]
            lg = account(ts, m, 10_000, risk_pct=0.5, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
            r = lg["R"].to_numpy()
            row.update({f"{pname} trades": len(r), f"{pname} avg R": r.mean(), f"{pname} t": tstat(r),
                        f"{pname} max DD % (0.5%)": stats(lg)["max_dd_pct"]})
        rows.append(row)
        print(row, flush=True)
    res = pd.DataFrame(rows).set_index("pair")
    res["survives"] = (res["design avg R"] > 0) & (res["design t"] >= 2) & (res["check avg R"] > 0)
    res.to_csv(f"{OUT}/summary.csv")
    open(f"{OUT}/REPORT.md", "w").write(
        "# Green box strategy on other pairs, 2010–2026\n\n"
        "Version B, SL 1 × box + spread, RR 9, BE 3R, 05:00 IST box, unchanged. All costs, 0.5% risk. "
        "Rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) "
        "avg R > 0. USDJPY is included for reference (its rules came from 2024–2026).\n\n"
        + fmt_table(res, ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
