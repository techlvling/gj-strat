"""USDJPY green box on gotobi days only (2010-2026).

The box (05:00-05:59 IST = 08:30-09:29 JST) and its order window (to 11:00 IST = 14:30 JST)
straddle the 09:55 JST Tokyo fix, where gotobi days see importer dollar buying, then a fall.
Pre-declared variants (green rules: SL 1 x box, RR 9, BE 3R):
  B (both sides, re-entry): all days / gotobi days / non-gotobi days
  one side only (engine Version W: one trade, no re-entry): SELL on gotobi days, BUY on gotobi days,
  and SELL / BUY on all days for reference.
It counts as an improvement only if the gotobi-day version beats the same rule on all days in
avg R in all three periods (2010-17 / 2018-23 / 2024-26). Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_box_gotobi_days.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import is_gotobi
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

M = DAYS = SWAP = None
GREEN = dict(rr=9, sl_pips=30, be_trigger=3, be_plus=5, sl_box_mult=1.0)


def variants():
    got = [x for x in DAYS if is_gotobi(x)]
    non = [x for x in DAYS if not is_gotobi(x)]
    v = [("B all days (green)", "B", DAYS, None), ("B gotobi days", "B", got, None), ("B non-gotobi days", "B", non, None)]
    for side in ("SELL", "BUY"):
        v.append((f"{side} only, gotobi days", "W", got, side))
        v.append((f"{side} only, all days", "W", DAYS, side))
    return v


def evaluate(item):
    name, ver, days, side = item
    bias = {x: side for x in days} if ver == "W" else None
    tr, _ = run(M, Params(version=ver, **GREEN), days, bias=bias)
    tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
    lg = account(tr, M, 10_000, risk_pct=0.5, commission=7, swap=SWAP, sym="USDJPY", slippage_pips=0.2)
    r, day = lg["R"].to_numpy(), pd.to_datetime(lg["day"])
    row = {"setup": name}
    for per, (a, b) in PERIODS.items():
        x = r[np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))]
        row.update({f"{per} trades": len(x), f"{per} win %": (x > 0).mean() * 100, f"{per} avg R": x.mean(),
                    f"{per} t": tstat(x)})
    row.update({"all trades": len(r), "all avg R": r.mean(), "all t": tstat(r)})
    return row


if __name__ == "__main__":
    M = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    days = trading_days(M, start="2010-01-01")
    _, pr = run(M, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    DAYS = [x for x in days if x.date() not in sk]
    SWAP = SwapModel.from_fred("rates", 1.0)
    with Pool(4) as pool:
        res = pd.DataFrame(pool.map(evaluate, variants())).set_index("setup")
    pairs = {"B gotobi days": "B all days (green)", "SELL only, gotobi days": "SELL only, all days",
             "BUY only, gotobi days": "BUY only, all days"}
    res["beats all-days in every period"] = [
        bool(all(res.loc[s, f"{p} avg R"] > res.loc[pairs[s], f"{p} avg R"] for p in PERIODS)) if s in pairs else None
        for s in res.index]
    cols = [f"{p} {c}" for p in PERIODS for c in ("trades", "win %", "avg R", "t")] + ["all avg R", "all t",
                                                                                      "beats all-days in every period"]
    os.makedirs("results/box_gotobi_days", exist_ok=True)
    res.to_csv("results/box_gotobi_days/grid.csv")
    open("results/box_gotobi_days/REPORT.md", "w").write(
        "# USDJPY green box on gotobi days only, 2010–2026\n\nVariants and pass rule in run_box_gotobi_days.py.\n\n"
        + fmt_table(res[cols], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(3).to_string())
