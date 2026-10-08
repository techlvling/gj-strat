"""USDJPY, SL = 1 x box: Versions A and B across RR 2-10, break-even off or at 3R.

Pre-declared protocol (written before any result was seen):
  * grid: version A/B x RR 2..10 x BE {off, 3R -> entry + 5/30 of SL} (BE only where 3 < RR)
  * costs: $7 per lot round turn + swap with 1% markup
  * pick ONE combo on 2010-2017 only, by avg R after 0.2 pip slippage per stop fill
  * check it on 2018-2026, which plays no part in the pick

    python run_usdjpy_grid.py       # needs data/usdjpy_2010-01-01_2026-10-07.npz
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

from gjstrat.accounting import account, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import C, INK2, START_BAL, clean_log, fmt_table, years_of
from run_usdjpy_sl import DESIGN_END, PICK_SLIP, SLIPS, SYM, slipped, tstat

RRS = [2, 3, 4, 5, 6, 7, 8, 9, 10]
M = DAYS = PERIODS = SWAP = ARGS = None


def combos() -> list[Params]:
    out = []
    for v in ("A", "B"):
        for rr in RRS:
            out.append(Params(rr=rr, sl_pips=30, be_trigger=None, be_plus=5, version=v, sl_box_mult=1.0))
            if rr > 3:
                out.append(Params(rr=rr, sl_pips=30, be_trigger=3.0, be_plus=5, version=v, sl_box_mult=1.0))
    return out


def evaluate(p: Params) -> list[dict]:
    trades, _ = run(M, p, DAYS)
    rows = []
    for pname, pdays in PERIODS.items():
        ds = set(pdays)
        lg = account([t for t in trades if t.day in ds], M, START_BAL, commission=ARGS.commission,
                     swap=SWAP, sym=SYM)
        s = stats(lg, START_BAL, years_of(pdays))
        hours = (pd.to_datetime(lg["exit_time_ist"]) - pd.to_datetime(lg["entry_time_ist"])).dt.total_seconds() / 3600
        row = dict(label=p.label, version=p.version, rr=p.rr, be=p.be_label, period=pname,
                   trades=s["trades"], win_rate=s["win_rate"], max_dd_pct=s["max_dd_pct"],
                   losing_streak=s["longest_losing_streak"], median_hours=hours.median(),
                   avg_swap_nights=lg["swap_nights"].mean())
        for sl in SLIPS:
            r = slipped(lg, sl)
            row[f"avg_R slip {sl:g}"] = r.mean()
            row[f"t slip {sl:g}"] = tstat(r)
        rows.append(row)
    return rows


def main():
    global M, DAYS, PERIODS, SWAP, ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--commission", type=float, default=7.0)
    ap.add_argument("--markup", type=float, default=1.0)
    ap.add_argument("--out", default="results/usdjpy_grid")
    ARGS = args = ap.parse_args()
    out = args.out
    os.makedirs(out, exist_ok=True)

    M = build_market(SYM, date.fromisoformat(args.start), date.fromisoformat(args.end), "data/raw",
                     f"data/usdjpy_{args.start}_{args.end}.npz")
    days = trading_days(M, start=args.start)
    _, probe = run(M, Params(sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    DAYS = [d for d in days if d.date() not in skipped]
    PERIODS = {"design 2010–2017": [d for d in DAYS if d < DESIGN_END],
               "check 2018–2026": [d for d in DAYS if d >= DESIGN_END]}
    SWAP = SwapModel.from_fred("rates", args.markup)

    cs = combos()
    with Pool(os.cpu_count()) as pool:
        rows = [r for rs in pool.map(evaluate, cs) for r in rs]
    res = pd.DataFrame(rows)
    res.to_csv(f"{out}/grid.csv", index=False)
    key = f"avg_R slip {PICK_SLIP:g}"
    des = res[res.period == "design 2010–2017"].set_index("label")
    chk = res[res.period == "check 2018–2026"].set_index("label")
    both = des[["version", "rr", "be", "trades", key, f"t slip {PICK_SLIP:g}", "max_dd_pct"]].join(
        chk[[key, f"t slip {PICK_SLIP:g}", "avg_R slip 0.5", "max_dd_pct", "losing_streak",
             "median_hours", "avg_swap_nights"]], lsuffix=" design", rsuffix=" check")
    both = both.sort_values(f"{key} design", ascending=False)
    both["rank (design)"] = range(1, len(both) + 1)
    pick = both.index[0]

    # ---------------- chart: avg R after costs vs RR, design and check
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    series = [("A", "off"), ("A", "3R+5"), ("B", "off"), ("B", "3R+5")]
    for ax, (pname, df) in zip(axes, [("design 2010–2017 (pick made here)", des),
                                      ("check 2018–2026", chk)]):
        for k, (v, be) in enumerate(series):
            d = df[(df.version == v) & (df.be == be)].sort_values("rr")
            ax.plot(d.rr, d[key], color=C[k], lw=2, marker="o", ms=5, label=f"{v}, BE {be}")
        pr = df.loc[pick]
        ax.scatter([pr.rr], [pr[key]], s=160, facecolors="none", edgecolors="#0b0b0b", lw=1.5, zorder=5)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xlabel("RR (TP as multiple of the SL)")
        ax.set_title(pname, loc="left")
        ax.set_xticks(RRS)
    axes[0].set_ylabel(f"Avg R per trade after $7 + swap + {PICK_SLIP:g} pip slippage")
    axes[0].legend(fontsize=9)
    fig.suptitle(f"USDJPY, SL = 1 × box: RR 2–10 (circle = pick: {pick})", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{out}/usdjpy_grid.png", dpi=125)
    plt.close(fig)

    show = both.drop(columns=["version", "rr", "be"])
    show.index.name = "Combo (sorted by design score)"
    p = both.iloc[0]
    rep = [f"# USDJPY, SL = 1 × box: Versions A and B, RR 2–10, BE off / 3R\n",
           f"Protocol fixed before any result: {len(cs)} combos, ${args.commission:g}/lot + swap "
           f"(+{args.markup:g}% markup). Pick ONE on 2010–2017 by avg R after {PICK_SLIP:g} pip "
           "slippage per stop fill; check it on 2018–2026.\n",
           f"**Pick: `{pick}`** — design {p[key + ' design']:+.3f}R (t {p['t slip 0.2 design']:+.2f}); "
           f"**check {p[key + ' check']:+.3f}R** (t {p['t slip 0.2 check']:+.2f}), "
           f"{p['avg_R slip 0.5']:+.3f}R at 0.5 pip slippage, check max drawdown "
           f"{p['max_dd_pct check']:.1f}%, longest losing streak {int(p['losing_streak'])}.\n",
           f"With {len(cs)} combos tried, the design winner is flattered by luck; judge it by the "
           "check column.\n",
           fmt_table(show, ".3f"), "\n![Grid](usdjpy_grid.png)\n",
           "Columns: avg R / t after costs and 0.2 pip slippage; drawdown and streak with costs, "
           "no slippage; median hours in trade and swap nights in the check period. Full grid: "
           "`grid.csv`.\n"]
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    pd.set_option("display.width", 250)
    print(both.round(3).to_string())


if __name__ == "__main__":
    main()
