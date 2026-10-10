"""Placebo check: does the gotobi Tokyo-fix flow show up in USD pairs without the yen?

Frozen rule from USDJPY (dollar falls after the 09:55 JST fix on gotobi days, exit 06:00 UTC,
SL 0.25 x ATR20, no TP), mapped to "short USD": BUY AUDUSD / NZDUSD / EURUSD / GBPUSD,
SELL USDCAD / USDCHF. USDJPY shown for reference. Costs: $7/lot, 0.2 pip slippage, no swap
(same-morning exit). Fixed before running: an effect counts only if pooled over the 6 pairs
avg R > 0 with t >= 2.

    python run_gotobi_usd_check.py
"""
from __future__ import annotations

import os
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import daily_table, gotobi_short, simulate
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/gotobi_usd_check"
PAIRS = ["AUDUSD", "NZDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDCHF", "USDJPY"]


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, pooled = [], []
    for sym in PAIRS:
        m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                         f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(m)
        d = d[d.index >= pd.Timestamp("2010-01-01")]
        sigs = gotobi_short(m, d)
        if not sym.startswith("USD"):
            sigs = [replace(s, side="BUY") for s in sigs]           # short USD = buy XXXUSD
        tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.entry_i, t.exit_i))
        r = account(tr, m, 10_000, risk_pct=0.5, commission=7, sym=sym, slippage_pips=0.2)["R"].to_numpy()
        if sym != "USDJPY":
            pooled.append(r)
        yrs = pd.Series(r, index=[t.day.year for t in tr])
        rows.append({"pair": sym, "side": sigs[0].side, "trades": len(r), "win %": (r > 0).mean() * 100,
                     "avg R": r.mean(), "t": tstat(r),
                     "years +": f"{(yrs.groupby(level=0).sum() > 0).sum()}/{yrs.index.nunique()}"})
        print(rows[-1], flush=True)
    res = pd.DataFrame(rows).set_index("pair")
    p = np.concatenate(pooled)
    verdict = p.mean() > 0 and tstat(p) >= 2
    line = (f"Pooled over the 6 non-yen pairs: {len(p)} trades, win {(p > 0).mean() * 100:.1f}%, "
            f"avg {p.mean():+.3f}R, t {tstat(p):.2f} -> {'EFFECT' if verdict else 'NO EFFECT'}")
    res.to_csv(f"{OUT}/summary.csv")
    open(f"{OUT}/REPORT.md", "w").write("# Gotobi placebo check on USD pairs without the yen, 2010–2026\n\n"
                                        "Rule and pass test in run_gotobi_usd_check.py.\n\n**" + line + "**\n\n"
                                        + fmt_table(res, ".3f") + "\n")
    print(line)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
