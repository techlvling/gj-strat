"""USDJPY, Versions A and B, SL = that day's box + spread, over the long history, with swap.

The rules were found on 2024-2026 data, so 2010-2023 is a true out-of-sample test: nothing was
fitted there. Swap uses real overnight rates (see gjstrat/swap.py); results are shown without
swap, with pure carry (no markup) and with a broker markup (default 1% a year).

    python run_usdjpy_history.py                       # 2010-01-01 .. 2026-10-07
    python run_usdjpy_history.py --start 2024-01-01    # only the period the rules came from
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gjstrat.accounting import account, equity_curve, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import BASE, C, INK2, START_BAL, clean_log, fmt_table, stat_table, years_of

SYM = "USDJPY"
FOUND = pd.Timestamp("2024-01-01")          # the rules were discovered on data from here on


def tstat(r) -> float:
    r = np.asarray(r, dtype=float)
    return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--markup", type=float, default=1.0, help="broker swap markup, % a year")
    ap.add_argument("--out", default="results/usdjpy_history")
    args = ap.parse_args()
    out = args.out
    os.makedirs(f"{out}/trade_logs", exist_ok=True)

    m = build_market(SYM, date.fromisoformat(args.start), date.fromisoformat(args.end), "data/raw",
                     f"data/usdjpy_{args.start}_{args.end}.npz")
    days = trading_days(m, start=args.start)
    _, probe = run(m, Params(**BASE, sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    days = [d for d in days if d.date() not in skipped]
    periods = {"2010–2023 (never seen)": [d for d in days if d < FOUND],
               "2024–2026 (where found)": [d for d in days if d >= FOUND],
               "Full period": days}
    periods = {k: v for k, v in periods.items() if v}
    costs = {"no swap": None,
             "swap, pure carry": SwapModel.from_fred("rates", 0.0),
             f"swap, +{args.markup:g}% markup": SwapModel.from_fred("rates", args.markup)}
    main_cost = list(costs)[-1]

    res, logs = {}, {}
    for v in ("A", "B"):
        trades, cnt = run(m, Params(**BASE, version=v, sl_box_mult=1.0), days)
        for cname, sw in costs.items():
            for pname, pdays in periods.items():
                ds = set(pdays)
                lg = account([t for t in trades if t.day in ds], m, START_BAL, swap=sw, sym=SYM)
                res[(v, cname, pname)] = stats(lg, START_BAL, years_of(pdays))
                if pname == "Full period":
                    logs[(v, cname)] = lg
        clean_log(logs[(v, main_cost)]).to_csv(f"{out}/trade_logs/{SYM}_{v}_swap.csv", index=False)
        print(f"{v} done: {len(trades)} trades", flush=True)

    # ---------------- per-year table (A, main cost)
    lg = logs[("A", main_cost)].copy()
    lg["year"] = pd.to_datetime(lg["day"]).dt.year
    lg["swap_R"] = lg["R"] - logs[("A", "no swap")].set_index(["entry_i", "exit_i"]).loc[
        list(zip(lg.entry_i, lg.exit_i)), "R"].to_numpy()
    by_year = lg.groupby("year").agg(trades=("R", "size"), win_rate=("R", lambda x: (x > 0).mean() * 100),
                                     avg_R=("R", "mean"), total_R=("R", "sum"),
                                     t_stat=("R", tstat), swap_R=("swap_R", "sum"))
    by_year.index.name = "Year (A, " + main_cost + ")"
    side = lg.groupby("side").agg(trades=("R", "size"), avg_R=("R", "mean"), swap_R=("swap_R", "sum"),
                                  avg_nights=("swap_nights", "mean"))
    side.index.name = "Side (A, " + main_cost + ")"

    # ---------------- charts
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    for k, (key, name) in enumerate([(("A", "no swap"), "A, no swap"), (("A", main_cost), f"A, {main_cost}"),
                                     (("B", main_cost), f"B, {main_cost}")]):
        eq = equity_curve(logs[key])
        ax.plot(eq.index, eq.to_numpy(), color=C[k], lw=1.8, drawstyle="steps-post",
                label=f"{name}  ({eq.iloc[-1] / START_BAL * 100 - 100:+.0f}%)")
    ax.axvspan(FOUND, pd.Timestamp(args.end), color=INK2, alpha=0.08, lw=0)
    ax.text(FOUND, 1.0, "  where the rules were found", transform=ax.get_xaxis_transform(),
            va="top", fontsize=9, color=INK2)
    ax.set_yscale("log")
    ax.axhline(START_BAL, color=INK2, lw=0.8)
    ax.set_ylabel("Closed balance (USD, log scale)")
    ax.set_title(f"USDJPY, SL = 1 × box: closed balance from $10,000, 1% risk", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=9)
    ax = axes[1]
    yr = by_year["avg_R"]
    ax.bar(yr.index.astype(str), yr.to_numpy(), color=np.where(yr > 0, "#2a78d6", "#e34948"), width=0.7)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(f"Version A avg R per trade by year ({main_cost})", loc="left")
    ax.tick_params(axis="x", labelrotation=60, labelsize=8.5)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(f"{out}/usdjpy_history.png", dpi=125)
    plt.close(fig)

    # ---------------- report
    rep = [f"# USDJPY {args.start[:4]}–{args.end[:4]}: Versions A and B, SL = 1 × box, with swap\n",
           "Rules: IST 05:00–05:59 box, SL = that day's box + spread, TP 4R, BE at 3R → entry + "
           "5/30 of the SL distance, 1% risk compounding from $10,000, Dukascopy bid/ask. "
           f"{len(days)} tradable days; {probe.skipped_incomplete + probe.skipped_no_data} skipped "
           "(no data or a tick-less minute in the box).\n",
           "Swap: real overnight rates (USD effective Fed Funds, Japan overnight call rate), "
           "rollover at 17:00 New York, Wednesday counts 3 days. The markup is the broker's cut on "
           "the rate differential and is paid on both sides.\n"]
    for pname in periods:
        rep.append(f"## {pname}\n")
        rep.append(stat_table({f"{v}, {c}": res[(v, c, pname)] for v in ("A", "B") for c in costs}))
        rep.append("")
    rep += ["![USDJPY history](usdjpy_history.png)\n", "## Version A by year\n",
            fmt_table(by_year, ".3f"), "\n## Version A by side\n", fmt_table(side, ".3f"),
            "\nTrade logs (with swap): `trade_logs/`.\n"]
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    for pname in periods:
        for v in ("A", "B"):
            for c in costs:
                s = res[(v, c, pname)]
                print(f"{pname:26s} {v} {c:22s} n={s['trades']:5d} avgR={s['avg_R']:+.3f} "
                      f"t={s['sqn']:+.2f} DD={s['max_dd_pct']:5.1f}% ret={s['net_return_pct']:+9.1f}%")
    print(by_year.round(3))
    print(side.round(3))


if __name__ == "__main__":
    main()
