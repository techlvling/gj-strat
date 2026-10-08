"""Which time of day does the box breakout work best? USDJPY, 2010-2026.

Grid (fixed before any result): 1-hour box starting at every hour 00:00-23:00 IST x order
window 1-7 hours after the box closes = 168 windows. Everything else is the approved Version B:
SL = 1 x box + spread, RR 9, BE 3R, re-entry at the box level, max 2 trades.
Scores:
  * avg R and win rate after $7/lot, swap (+1% markup) and 0.2 pip slippage per stop fill
  * follow-through: share of first trades that reach +1R / +2R / +3R before the stop
    (independent of RR/BE)
Pick ONE window on 2010-2017 by avg R; check it on 2018-2026. 168 windows means a lucky best
is expected: with no edge anywhere, the best t-stat would be around sqrt(2 ln 168) ~ 3.2.

    python run_window_scan.py      # needs data/usdjpy_2010-01-01_2026-10-07.npz
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.analysis import levels_before_stop
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import DIVERGE, INK, fmt_table, heat
from run_usdjpy_sl import DESIGN_END, SYM, tstat

HOURS = list(range(24))
WINDOWS = list(range(1, 8))
M = DAYS = SWAP = None


def evaluate(hw):
    h, w = hw
    p = Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0,
               box_start_min=h * 60, order_hours=w)
    trades, cnt = run(M, p, DAYS)
    if not trades:
        return []
    lg = account(trades, M, 10_000, commission=7, swap=SWAP, sym=SYM, slippage_pips=0.2)
    by_key = lg.set_index(["entry_i", "exit_i"])["R"]
    rows = []
    for pname, inside in (("design", lambda d: d < DESIGN_END), ("check", lambda d: d >= DESIGN_END)):
        ts = [t for t in trades if inside(t.day)]
        if not ts:
            continue
        r = by_key.loc[[(t.entry_i, t.exit_i) for t in ts]].to_numpy()
        firsts = [t for t in ts if t.num == 1]
        reach = np.array([levels_before_stop(M, t) for t in firsts])
        rows.append(dict(hour=h, window=w, period=pname, trades=len(ts), win_rate=(r > 0).mean() * 100,
                         avg_R=r.mean(), t=tstat(r), total_R=r.sum(),
                         reach_1R=(reach >= 1).mean() * 100, reach_2R=(reach >= 2).mean() * 100,
                         reach_3R=(reach >= 3).mean() * 100,
                         median_box_pips=float(np.median([t.range_pips for t in firsts]))))
    return rows


def main():
    global M, DAYS, SWAP
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/window_scan")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    M = build_market(SYM, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                     "data/usdjpy_2010-01-01_2026-10-07.npz")
    DAYS = trading_days(M, start="2010-01-01")
    SWAP = SwapModel.from_fred("rates", 1.0)

    grid = [(h, w) for h in HOURS for w in WINDOWS]
    with Pool(os.cpu_count()) as pool:
        rows = []
        for k, rs in enumerate(pool.imap_unordered(evaluate, grid, chunksize=2), 1):
            rows += rs
            if k % 12 == 0:
                print(f"{k}/{len(grid)} windows done", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(f"{args.out}/scan.csv", index=False)

    des = res[res.period == "design"].set_index(["hour", "window"])
    chk = res[res.period == "check"].set_index(["hour", "window"])
    pick = des["avg_R"].idxmax()
    base = (5, 5)
    top = des["avg_R"].sort_values(ascending=False).head(10).index

    # ---------------- heatmaps: hour x window
    fig, axes = plt.subplots(2, 2, figsize=(15, 13))
    specs = [(des, "avg_R", "Design 2010–2017: avg R after costs", "+.2f"),
             (chk, "avg_R", "Check 2018–2026: avg R after costs", "+.2f"),
             (des, "reach_1R", "Design: % of breakouts reaching +1R before SL", ".0f"),
             (chk, "reach_1R", "Check: % of breakouts reaching +1R before SL", ".0f")]
    for ax, (df, col, title, fmt) in zip(axes.flat, specs):
        g = df[col].unstack("window").reindex(index=HOURS, columns=WINDOWS)
        if col == "avg_R":
            heat(ax, g, title, fmt, float(np.nanmax(np.abs(res["avg_R"]))))
        else:
            centred = g - float(np.nanmedian(res[col]))
            heat(ax, centred, title + " (vs median)", "+.0f", float(np.nanmax(np.abs(centred.to_numpy()))))
        ax.set_xlabel("order window after the box (hours)")
        ax.set_ylabel("box start (IST)")
        ax.set_yticks(range(24), [f"{h:02d}:00" for h in HOURS])
        ax.set_xticks(range(7), [str(w) for w in WINDOWS])
        for (hh, ww), mark in ((base, "□"), (pick, "◎")):
            ax.text(WINDOWS.index(ww) + 0.38, HOURS.index(hh) - 0.25, mark, fontsize=11, color=INK)
    fig.suptitle("USDJPY box breakout by time of day (□ = current 05:00 box + 5 h, ◎ = design pick)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{args.out}/window_heatmaps.png", dpi=110)
    plt.close(fig)

    # ---------------- report
    def line(key):
        d, c = des.loc[key], chk.loc[key]
        return {"window": f"{key[0]:02d}:00 box + {key[1]} h", "design avg R": d.avg_R, "design t": d.t,
                "check avg R": c.avg_R, "check t": c.t, "check win %": c.win_rate,
                "check reach 1R %": c.reach_1R, "check reach 3R %": c.reach_3R,
                "check trades": c.trades}
    tab = pd.DataFrame([line(k) for k in top]).set_index("window")
    tab.index.name = "Top 10 by design avg R"
    cur = pd.DataFrame([line(base)]).set_index("window")
    cur.index.name = "Current window"
    by_hour = res.groupby(["period", "hour"])[["avg_R", "reach_1R"]].mean().unstack("period")
    by_hour.columns = [f"{a} {b}" for a, b in by_hour.columns]
    by_hour.index = [f"{h:02d}:00" for h in by_hour.index]
    by_hour.index.name = "Box start (IST), avg over windows"
    p = line(pick)
    rep = ["# USDJPY: which time of day does the box breakout work?\n",
           "1-hour box at every hour 00:00–23:00 IST × order window 1–7 h = 168 windows, Version B "
           "(SL 1 × box, RR 9, BE 3R), $7/lot + swap + 0.2 pip slippage. Pick on 2010–2017 by avg R, "
           "check on 2018–2026. With 168 tries, a best design t-stat near 3 is expected from luck alone.\n",
           f"**Design pick: {p['window']}** — design {p['design avg R']:+.3f}R (t {p['design t']:+.2f}), "
           f"**check {p['check avg R']:+.3f}R** (t {p['check t']:+.2f}).\n",
           fmt_table(cur, ".3f"), "", fmt_table(tab, ".3f"),
           "\n![Heatmaps](window_heatmaps.png)\n", "## By box start hour (averaged over the 7 windows)\n",
           fmt_table(by_hour, ".3f"), "\nFull grid: `scan.csv`.\n"]
    with open(f"{args.out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    pd.set_option("display.width", 250)
    print(cur.round(3).to_string())
    print(tab.round(3).to_string())
    print(by_hour.round(3).to_string())


if __name__ == "__main__":
    main()
