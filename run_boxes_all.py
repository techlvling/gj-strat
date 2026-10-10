"""The user's boxes (run_gold_boxes.py) on every market: 28 FX pairs, gold, JPN225, Nasdaq 100.

Boxes A 04:30-05:15 IST, B 12:30-14:00 IST, B' London 08:00-09:30 (DST), ref green 05:00-05:59 IST; settings
green rules (RR 9, BE 3R), green rules + vol filter, RR 2 without BE: 31 x 4 x 3 = 372 tests.
Survives (fixed before running): design (2010-17; indices 2011-17) t >= 2 and avg R > 0 in 2018-23 and
2024-26. About 2 survivors are expected from luck alone at 372 tests.
Costs as run_all_matrix.py (FX $7/lot + 0.2 pip + swap; gold $0.07/oz + $0.02; JPN225 2 pt / Nasdaq 0.25 pt;
gold and indices 3%/yr financing).

    python run_boxes_all.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import trading_days
from gjstrat.patterns import daily_table
from gjstrat.swap import SwapModel
from run_all_matrix import MARKETS, net_r
from run_backtest import fmt_table
from run_gold_boxes import BOXES, SETUPS, box_trades, stats

OUT = "results/boxes_all"


def market(sym):
    sw = SwapModel.from_fred("rates", 1.0)
    start = date(2011, 1, 2) if "IDX" in sym else date(2010, 1, 1)
    m = build_market(sym, start, date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_{start}_2026-10-07.npz")
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    days = trading_days(m, start=str(start + pd.Timedelta(days=1)))
    rows = []
    for bname, kind in BOXES.items():
        for sname, kw in SETUPS.items():
            tr = box_trades(m, kind, days, **kw)
            if not tr:
                continue
            r = net_r(m, sym, tr, sw)
            day = pd.DatetimeIndex([t.day for t in tr])
            rows.append({"market": sym, "box": bname, "setting": sname, **stats("", r, day)})
            if sname.startswith("green"):
                keep = np.array([hot(t) for t in tr], dtype=bool)
                rows.append({"market": sym, "box": bname, "setting": "green rules + vol filter", **stats("", r[keep], day[keep])})
    print(sym, "done", flush=True)
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with Pool(4) as pool:
        res = pool.map(market, MARKETS, chunksize=1)
    T = pd.DataFrame([r for rows in res for r in rows]).drop(columns="test")
    T["survives"] = (T["design t"] >= 2) & (T["check avg R"] > 0) & (T["holdout avg R"] > 0)
    T.to_csv(f"{OUT}/all.csv", index=False)
    cols = ["market", "box", "setting", "trades", "win %", "design avg R", "design t", "check avg R", "holdout avg R",
            "last 3y avg R", "last 3y t"]
    surv = T[T.survives]
    allpos = T[(T["design avg R"] > 0) & (T["check avg R"] > 0) & (T["holdout avg R"] > 0)].sort_values("design t", ascending=False)
    fam = T.groupby(["box", "setting"]).agg(markets=("market", "size"), **{
        "markets positive all 3 periods": ("market", lambda s: int(((T.loc[s.index, "design avg R"] > 0) & (T.loc[s.index, "check avg R"] > 0)
                                                                     & (T.loc[s.index, "holdout avg R"] > 0)).sum())),
        "avg R 2010-17 (mean)": ("design avg R", "mean"), "avg R 2018-23 (mean)": ("check avg R", "mean"),
        "avg R 2024-26 (mean)": ("holdout avg R", "mean"), "survivors": ("survives", "sum")})
    last3 = T[T["trades"] > 0].sort_values("last 3y t", ascending=False).head(15)
    open(f"{OUT}/REPORT.md", "w").write(
        "# Your boxes on all 31 markets, 2010–2026\n\nRules in run_boxes_all.py (fixed before running). "
        f"372 tests; about 2 survivors expected by luck.\n\n**Survivors: {len(surv)}**\n\n" +
        (fmt_table(surv.set_index("market")[cols[1:]], ".3f") if len(surv) else "None.") +
        "\n\n## Each box and setting across the 31 markets\n\n" + fmt_table(fam, ".3f") +
        "\n\n## Positive in all three periods (any t)\n\n" + fmt_table(allpos.set_index("market")[cols[1:]], ".3f") +
        "\n\n## Best 15 in the last 3 years (by t)\n\n" + fmt_table(last3.set_index("market")[cols[1:]], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print("survivors:"); print(surv[cols].round(3).to_string())
    print(fam.round(3).to_string())
    print(allpos[cols].round(3).to_string())
    print(last3[cols].round(3).to_string())
