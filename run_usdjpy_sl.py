"""USDJPY Version A: is a wider stop (1.5x or 2x the box) better once costs are paid?

Pre-declared protocol (written before any result was seen):
  * candidates: SL = 1.0, 1.5, 2.0 x that day's 05:00-05:59 IST box (+ spread); TP 4R and BE 3R
    unchanged (BE offset = 5/30 of the SL distance)
  * costs: $7 per lot round turn (user's raw-spread account) + swap with 1% markup
  * pick ONE multiplier on 2010-2017 only, by avg R after 0.2 pip slippage per stop fill
  * check it on 2018-2026, which plays no part in the pick

    python run_usdjpy_sl.py        # needs data/usdjpy_2010-01-01_2026-10-07.npz (run_usdjpy_history.py)
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

from gjstrat.accounting import account, equity_curve, longest_streak, stats
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import BASE, C, INK2, START_BAL, clean_log, fmt_table, years_of

SYM = "USDJPY"
MULTS = [1.0, 1.5, 2.0]
DESIGN_END = pd.Timestamp("2018-01-01")      # design: 2010-2017, check: 2018-2026
PICK_SLIP = 0.2
SLIPS = [0.0, 0.2, 0.5]


def tstat(r) -> float:
    r = np.asarray(r, dtype=float)
    return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 else np.nan


def slipped(log: pd.DataFrame, slip: float) -> pd.Series:
    """R after `slip` pips of slippage on every stop fill (entry, SL, BE; TP is a limit)."""
    stop_exit = log["exit_reason"].isin(["SL", "BE"]).astype(float)
    return log["R"] - slip * (1 + stop_exit) / log["risk_pips"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--commission", type=float, default=7.0)
    ap.add_argument("--markup", type=float, default=1.0)
    ap.add_argument("--out", default="results/usdjpy_sl")
    args = ap.parse_args()
    out = args.out
    os.makedirs(f"{out}/trade_logs", exist_ok=True)

    m = build_market(SYM, date.fromisoformat(args.start), date.fromisoformat(args.end), "data/raw",
                     f"data/usdjpy_{args.start}_{args.end}.npz")
    days = trading_days(m, start=args.start)
    _, probe = run(m, Params(**BASE, sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    days = [d for d in days if d.date() not in skipped]
    periods = {"design 2010–2017": [d for d in days if d < DESIGN_END],
               "check 2018–2026": [d for d in days if d >= DESIGN_END]}
    swap = SwapModel.from_fred("rates", args.markup)

    rows, curves, full_logs = [], {}, {}
    for mult in MULTS:
        p = Params(**BASE, version="A", sl_box_mult=mult)
        trades, _ = run(m, p, days)
        full = account(trades, m, START_BAL, commission=args.commission, swap=swap, sym=SYM)
        full_logs[mult] = full
        curves[mult] = equity_curve(full)
        clean_log(full).to_csv(f"{out}/trade_logs/{SYM}_A_box{mult:g}.csv", index=False)
        for pname, pdays in periods.items():
            ds = set(pdays)
            lg = account([t for t in trades if t.day in ds], m, START_BAL,
                         commission=args.commission, swap=swap, sym=SYM)
            s = stats(lg, START_BAL, years_of(pdays))
            row = dict(sl=f"{mult:g} × box", mult=mult, period=pname, trades=s["trades"],
                       win_rate=s["win_rate"], median_risk_pips=lg["risk_pips"].median(),
                       max_dd_pct=s["max_dd_pct"], losing_streak=s["longest_losing_streak"],
                       net_return_pct=s["net_return_pct"])
            for sl in SLIPS:
                r = slipped(lg, sl)
                row[f"avg_R slip {sl:g}"] = r.mean()
                row[f"t slip {sl:g}"] = tstat(r)
            yearly = slipped(lg, PICK_SLIP).groupby(pd.to_datetime(lg["day"]).dt.year).mean()
            row["years positive (0.2 slip)"] = f"{int((yearly > 0).sum())}/{len(yearly)}"
            rows.append(row)
            print(f"{mult:g}x {pname}: n={s['trades']} avgR={row['avg_R slip 0']:+.3f} "
                  f"slip0.2={row['avg_R slip 0.2']:+.3f} slip0.5={row['avg_R slip 0.5']:+.3f} "
                  f"DD={s['max_dd_pct']:.1f}% streak={s['longest_losing_streak']}", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(f"{out}/summary.csv", index=False)

    design = res[res.period == "design 2010–2017"].set_index("mult")
    pick = float(design[f"avg_R slip {PICK_SLIP:g}"].idxmax())
    check = res[(res.period == "check 2018–2026") & (res.mult == pick)].iloc[0]

    # ---------------- chart
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    for k, mult in enumerate(MULTS):
        eq = curves[mult]
        ax.plot(eq.index, eq.to_numpy(), color=C[k], lw=1.8 if mult == pick else 1.3,
                drawstyle="steps-post",
                label=f"SL {mult:g} × box{' (picked)' if mult == pick else ''}  "
                      f"({eq.iloc[-1] / START_BAL * 100 - 100:+.0f}%)")
    ax.axvspan(pd.Timestamp(args.start), DESIGN_END, color=INK2, alpha=0.08, lw=0)
    ax.text(pd.Timestamp(args.start), 1.0, "  design (pick made here)", transform=ax.get_xaxis_transform(),
            va="top", fontsize=9, color=INK2)
    ax.set_yscale("log")
    ax.axhline(START_BAL, color=INK2, lw=0.8)
    ax.set_ylabel("Closed balance (USD, log)")
    ax.set_title(f"USDJPY Version A, ${args.commission:g}/lot + swap, 1% risk (no slippage)", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=9)
    ax = axes[1]
    width = 0.26
    for k, mult in enumerate(MULTS):
        lg = full_logs[mult]
        yearly = slipped(lg, PICK_SLIP).groupby(pd.to_datetime(lg["day"]).dt.year).mean()
        ax.bar(yearly.index + (k - 1) * width, yearly.to_numpy(), width=width, color=C[k],
               label=f"{mult:g} × box")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(DESIGN_END.year - 0.5, color=INK2, lw=0.8, ls="--")
    ax.set_title(f"Avg R per year, after ${args.commission:g} + {PICK_SLIP:g} pip slippage", loc="left")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(f"{out}/usdjpy_sl.png", dpi=125)
    plt.close(fig)

    # ---------------- report
    show = res.set_index(["period", "sl"]).drop(columns=["mult"])
    show.index = [f"{a} · {b}" for a, b in show.index]
    show.index.name = "Period · SL"
    rep = [f"# USDJPY Version A: wider stop-loss test (${args.commission:g}/lot, swap +{args.markup:g}% markup)\n",
           "Protocol fixed before any result: candidates SL = 1, 1.5, 2 × the day's box (+ spread), "
           "TP 4R and BE 3R unchanged. Pick ONE on 2010–2017 by avg R after "
           f"{PICK_SLIP:g} pip slippage per stop fill. Check it on 2018–2026.\n",
           f"**Pick (design 2010–2017): SL = {pick:g} × box.**  ",
           f"**Check 2018–2026:** avg R {check['avg_R slip 0']:+.3f} (no slippage), "
           f"{check['avg_R slip 0.2']:+.3f} (0.2 pip), {check['avg_R slip 0.5']:+.3f} (0.5 pip); "
           f"t {check['t slip 0.2']:+.2f} at 0.2 pip; max drawdown {check['max_dd_pct']:.1f}%; "
           f"longest losing streak {check['losing_streak']}.\n",
           fmt_table(show, ".3f"),
           "\n![SL test](usdjpy_sl.png)\n",
           "Drawdown, streak and return are with commission and swap but no slippage. "
           "Trade logs: `trade_logs/`.\n"]
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    print(f"PICK {pick:g}x ->", check[["avg_R slip 0", "avg_R slip 0.2", "avg_R slip 0.5",
                                       "t slip 0.2", "max_dd_pct", "losing_streak"]].to_dict())


if __name__ == "__main__":
    main()
