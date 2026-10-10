"""What does USDJPY do after a green-box trade is stopped out? (2010-2026, descriptive only)

For every SL exit, price moves are measured from the SL fill in units of that trade's R (box):
  + = continues the way the SL was hit (against the original trade)
  - = reverses back toward the original trade direction
Horizons 30 min / 1 h / 4 h / 24 h (bid close for SL'd buys, ask close for SL'd sells), plus
how often price came back to the original entry within 4 h / 24 h, and how often it then went
on to the original 9R target within 24 h.

    python run_after_sl.py
"""
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from run_backtest import fmt_table

m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
days = trading_days(m, start="2010-01-01")
_, pr = run(m, Params(sl_box_mult=1.0), days)
sk = {x for x, _ in pr.skipped_dates}
tr, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
            [x for x in days if x.date() not in sk])
sl = [t for t in tr if t.reason == "SL" and t.exit_i + 1440 < m.n]
H = {"30 min": 30, "1 h": 60, "4 h": 240, "24 h": 1440}
rows, back4, back24, tp24 = [], 0, 0, 0
for t in sl:
    buy = t.side == "BUY"
    c = m.bc if buy else m.ac                      # where an exit/re-entry would be priced
    sign = -1 if buy else 1                        # + = further against the original trade
    rows.append({k: sign * (c[t.exit_i + h] - t.exit) / t.risk for k, h in H.items()})
    w4, w24 = slice(t.exit_i + 1, t.exit_i + 241), slice(t.exit_i + 1, t.exit_i + 1441)
    hit = (lambda w: m.bh[w].max() >= t.entry) if buy else (lambda w: m.al[w].min() <= t.entry)
    back4 += hit(w4); back24 += hit(w24)
    tgt = t.entry + 9 * t.risk if buy else t.entry - 9 * t.risk
    tp24 += (m.bh[w24].max() >= tgt) if buy else (m.al[w24].min() <= tgt)
df = pd.DataFrame(rows)
tab = pd.DataFrame({"continues (same way as SL) %": (df > 0).mean() * 100,
                    "reverses (back toward trade) %": (df < 0).mean() * 100,
                    "average move (R)": df.mean(), "median move (R)": df.median()})
tab.index.name = "After the SL"
n = len(sl)
txt = (f"# What USDJPY does after a box trade hits its SL (2010–2026)\n\n{n} stopped-out trades. Moves in R "
       f"(1R = that trade's SL distance); + = keeps going the SL way, − = turns back.\n\n" + fmt_table(tab, ".2f") +
       f"\n\n- Price came back to the original entry within 4 h: {back4 / n * 100:.1f}%, within 24 h: {back24 / n * 100:.1f}%\n"
       f"- Price reached the original 9R target within 24 h after the SL: {tp24 / n * 100:.1f}%\n")
open("results/after_sl/REPORT.md", "w").write(txt)
print(txt)
