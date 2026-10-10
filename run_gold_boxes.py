"""The user's boxes on gold (and USDJPY for comparison), 2010-2026, same breakout engine as the green box.

Boxes (IST; orders live 5 hours after the box closes):
  A. 04:30-05:15 IST (45 min; 08:00-08:45 Tokyo)
  B. 12:30-14:00 IST (90 min, fixed IST: 08:00-09:30 London in summer, 07:00-08:30 in winter)
  B'. London 08:00-09:30 every day (follows UK daylight saving: 12:30 IST in summer, 13:30 IST in winter)
  ref. the green box 05:00-05:59 IST (for comparison)
Settings, fixed before running: green rules (Version B, SL 1 x box + spread, RR 9, BE at 3R -> +1/6, re-entry
at the box level, max 2 trades); green rules + vol filter (ATR20 >= its 250-day median); RR 2 without BE.
Survives if design (2010-17) t >= 2 and avg R > 0 in 2018-23 and 2024-26 (our usual bar). The last three
years (from 2023-10-07) are shown separately.
Costs: gold $0.07/oz + $0.02 slippage per stop fill + 3%/yr financing per night; USDJPY $7/lot + 0.2 pip + swap.

    python run_gold_boxes.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_backtest import fmt_table
from run_edge_hunt import per_stats
from run_usdjpy_sl import tstat

OUT = "results/gold_boxes"
BOXES = {"A 04:30-05:15 IST": "A", "B 12:30-14:00 IST": "B", "B' London 08:00-09:30 (DST)": "L", "ref green 05:00-05:59 IST": "G"}
SETUPS = {"green rules (RR 9, BE 3R)": dict(rr=9, be_trigger=3), "RR 2, no BE": dict(rr=2, be_trigger=None)}
LAST3 = pd.Timestamp("2023-10-07")


def groups(kind, days):
    """[(box_start_min IST, box_len, days)]"""
    if kind == "A":
        return [(270, 45, days)]
    if kind == "B":
        return [(750, 90, days)]
    if kind == "G":
        return [(300, 60, days)]
    summer = [x for x in days if pd.Timestamp(x).tz_localize("Europe/London").dst() != pd.Timedelta(0)]
    ss = set(summer)
    return [(750, 90, summer), (810, 90, [x for x in days if x not in ss])]


def box_trades(m, kind, days, **kw):
    out = []
    for start, ln, ds in groups(kind, days):
        p = dict(sl_pips=30, be_plus=5, version="B", sl_box_mult=1.0, box_start_min=start, box_len=ln, order_hours=5.0)
        _, pr = run(m, Params(**{**p, "rr": 2, "be_trigger": None}), ds)
        sk = {x for x, _ in pr.skipped_dates}
        out += run(m, Params(**{**p, **kw}), [x for x in ds if x.date() not in sk])[0]
    return sorted(out, key=lambda t: (t.exit_i, t.entry_i))


def stats(name, r, day):
    wins, losses = r[r > 0], r[r <= 0]
    last = r[np.asarray(day >= LAST3)]
    return {"test": name, "trades": len(r), "win %": (r > 0).mean() * 100,
            "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) else np.nan,
            **per_stats(r, day), "last 3y avg R": last.mean(), "last 3y t": tstat(last)}


def market(sym):
    sw = SwapModel.from_fred("rates", 1.0)
    m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    days = trading_days(m, start="2010-01-01")
    rows = []
    for bname, kind in BOXES.items():
        for sname, kw in SETUPS.items():
            tr = box_trades(m, kind, days, **kw)
            r = net_r(m, sym, tr, sw)
            day = pd.DatetimeIndex([t.day for t in tr])
            rows.append({"market": sym, **stats(f"{bname} · {sname}", r, day)})
            if sname.startswith("green"):
                keep = np.array([hot(t) for t in tr], dtype=bool)
                rows.append({"market": sym, **stats(f"{bname} · green rules + vol filter", r[keep], day[keep])})
        print(sym, bname, flush=True)
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with Pool(2) as pool:
        res = pool.map(market, ["XAUUSD", "USDJPY"])
    T = pd.DataFrame([r for rows in res for r in rows]).set_index(["market", "test"])
    T["survives"] = (T["design t"] >= 2) & (T["check avg R"] > 0) & (T["holdout avg R"] > 0)
    T.to_csv(f"{OUT}/summary.csv")
    cols = ["trades", "win %", "avg win / avg loss", "design avg R", "design t", "check avg R", "check t", "holdout avg R",
            "holdout t", "last 3y avg R", "last 3y t", "survives"]
    txt = "# Your boxes on gold (and USDJPY), 2010–2026\n\nRules in run_gold_boxes.py (fixed before running).\n\n"
    for sym in ("XAUUSD", "USDJPY"):
        txt += f"## {sym}\n\n" + fmt_table(T.loc[sym][cols], ".3f") + "\n\n"
    open(f"{OUT}/REPORT.md", "w").write(txt)
    pd.set_option("display.width", 250)
    for sym in ("XAUUSD", "USDJPY"):
        print(sym); print(T.loc[sym][cols].round(3).to_string())
