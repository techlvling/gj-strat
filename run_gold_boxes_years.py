"""Year by year and the last 12 months for the boxes in run_gold_boxes.py (green rules; gold and USDJPY).

    python run_gold_boxes_years.py
"""
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import trading_days
from gjstrat.patterns import daily_table
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_backtest import fmt_table
from run_gold_boxes import BOXES, OUT, box_trades

if __name__ == "__main__":
    sw = SwapModel.from_fred("rates", 1.0)
    tabs = []
    for sym in ("XAUUSD", "USDJPY"):
        m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(m)
        med = d["atr20"].rolling(250, min_periods=250).median()
        days = trading_days(m, start="2010-01-01")
        for bname, kind in BOXES.items():
            tr = box_trades(m, kind, days, rr=9, be_trigger=3)
            r = net_r(m, sym, tr, sw)
            day = pd.DatetimeIndex([t.day for t in tr])
            hot = np.array([d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan) for t in tr], dtype=bool)
            for label, keep in (("", np.ones(len(r), bool)), (" + vol filter", hot)):
                s = pd.Series(r[keep], index=day[keep])
                row = s.groupby(s.index.year).sum().rename(lambda y: str(y))
                row["last 12 months"] = s[s.index >= pd.Timestamp("2025-10-07")].sum()
                row["last 12 months trades"] = int((s.index >= pd.Timestamp("2025-10-07")).sum())
                tabs.append(row.rename(f"{sym} · {bname}{label}"))
            print(sym, bname, flush=True)
    T = pd.DataFrame(tabs)
    T.index.name = "total R per year (green rules)"
    T.to_csv(f"{OUT}/years.csv")
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("## Total R per year and last 12 months (run_gold_boxes_years.py)\n\n" + fmt_table(T, ".1f") + "\n")
    pd.set_option("display.width", 300)
    print(T.round(1).to_string())
