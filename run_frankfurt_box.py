"""Frankfurt-hour range breakout (2010-2026), EURUSD / GBPUSD / EURGBP / EURJPY.

Box = 07:00-07:59 Frankfurt time (DST-aware: 10:30 IST in EU summer, 11:30 IST in winter); OCO stops at
the box from 08:00 Frankfurt for 5 hours; engine Version B (re-entry at the box level, max 2 trades),
SL = 1 x box + spread. Pre-declared (12): per pair green rules (RR 9, BE 3R), green rules + vol filter
(ATR20 >= its rolling 250-day median), and RR 2 without break-even. Survives if design (2010-17) t >= 2
and avg R > 0 in check (2018-23) and holdout (2024-26). Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_frankfurt_box.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import per_stats

OUT = "results/frankfurt_box"
PAIRS = ["EURUSD", "GBPUSD", "EURGBP", "EURJPY"]


def frankfurt_trades(m, days, **kw):
    summer = [x for x in days if pd.Timestamp(x).tz_localize("Europe/Berlin").dst() != pd.Timedelta(0)]
    sset = set(summer)
    winter = [x for x in days if x not in sset]
    out = []
    for start, ds in ((630, summer), (690, winter)):              # 07:00 Frankfurt in IST minutes
        p = dict(sl_pips=30, be_plus=5, version="B", sl_box_mult=1.0, box_start_min=start, box_len=60, order_hours=5.0)
        _, pr = run(m, Params(**{**p, "rr": 2, "be_trigger": None}), ds)
        sk = {x for x, _ in pr.skipped_dates}
        tr, _ = run(m, Params(**{**p, **kw}), [x for x in ds if x.date() not in sk])
        out += tr
    return sorted(out, key=lambda t: (t.exit_i, t.entry_i))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sw = SwapModel.from_fred("rates", 1.0)
    rows = []
    for sym in PAIRS:
        m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        days = trading_days(m, start="2010-01-01")
        d = daily_table(m)
        med = d["atr20"].rolling(250, min_periods=250).median()
        green = frankfurt_trades(m, days, rr=9, be_trigger=3)
        rr2 = frankfurt_trades(m, days, rr=2, be_trigger=None)
        vol = [t for t in green if d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)]
        for name, tr in (("RR 9, BE 3R", green), ("RR 9, BE 3R + vol filter", vol), ("RR 2, no BE", rr2)):
            lg = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
            r = lg["R"].to_numpy()
            rows.append({"test": f"{sym} · {name}", "win %": (r > 0).mean() * 100,
                         **per_stats(r, pd.DatetimeIndex([t.day for t in tr]))})
            print(rows[-1]["test"], round(r.mean(), 3), flush=True)
    res = pd.DataFrame(rows).set_index("test")
    res["survives"] = (res["design t"] >= 2) & (res["check avg R"] > 0) & (res["holdout avg R"] > 0)
    res.to_csv(f"{OUT}/summary.csv")
    cols = ["design n", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t", "survives"]
    open(f"{OUT}/REPORT.md", "w").write("# Frankfurt-hour range breakout, 2010–2026\n\nRules in run_frankfurt_box.py.\n\n"
                                        f"**Survivors: {int(res.survives.sum())} of {len(res)}**\n\n" + fmt_table(res[cols], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].round(3).to_string())
