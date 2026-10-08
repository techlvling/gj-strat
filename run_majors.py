"""Versions A and B, base settings, on every major pair (GBPJPY alongside as the reference).

Same rules as the GBPJPY study: IST 05:00-05:59 box, SL 30 pips + spread, RR 4, BE 3R + 5 pips,
1% risk compounding from $10,000 per pair, real bid/ask, same 60/40 in-sample / out-of-sample
split by tradable days. Each pair is its own account.

    python run_majors.py         # data from data/raw (python fetch_pairs.py --majors-only --save)
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
from gjstrat.data import MAJORS, build_market
from gjstrat.engine import Params, run, trading_days
from run_backtest import BASE, C, INK2, START, START_BAL, clean_log, fmt_table, split_days, years_of

PAIRS = MAJORS + ["GBPJPY"]
VERSIONS = {"A": Params(**BASE, version="A"), "B": Params(**BASE, version="B")}


def tstat(r: np.ndarray) -> float:
    return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--out", default="results/majors")
    ap.add_argument("--commission", type=float, default=0.0)
    args = ap.parse_args()
    out = args.out
    os.makedirs(f"{out}/trade_logs", exist_ok=True)

    rows, curves, pooled, splits = [], {}, {v: {"is": [], "oos": [], "all": []} for v in VERSIONS}, {}
    for sym in PAIRS:
        m = build_market(sym, date.fromisoformat(START), date.fromisoformat(args.end), "data/raw",
                         f"data/{sym.lower()}_1m.npz")
        days = trading_days(m, start=START)
        probe_trades, probe = run(m, VERSIONS["A"], days)
        skipped = {d for d, _ in probe.skipped_dates}
        days = [d for d in days if d.date() not in skipped]
        is_days, oos_days = split_days(days)
        is_set = set(is_days)
        splits[sym] = oos_days[0]
        spreads = np.array([t.spread for t in probe_trades]) / m.pip
        ranges = np.array([t.range_pips for t in probe_trades if t.num == 1])
        for v, p in VERSIONS.items():
            trades, cnt = run(m, p, days)
            acct = lambda ts: account(ts, m, START_BAL, commission=args.commission)
            log = acct(trades)
            clean_log(log).to_csv(f"{out}/trade_logs/{sym}_{v}.csv", index=False)
            curves[(sym, v)] = equity_curve(log)
            s_all = stats(log, START_BAL, years_of(days))
            s_is = stats(acct([t for t in trades if t.day in is_set]), START_BAL, years_of(is_days))
            s_oos = stats(acct([t for t in trades if t.day not in is_set]), START_BAL, years_of(oos_days))
            r = log["R"].to_numpy()
            is_mask = pd.to_datetime(log["day"]).isin(is_days).to_numpy()
            pooled[v]["all"].append(r)
            pooled[v]["is"].append(r[is_mask])
            pooled[v]["oos"].append(r[~is_mask])
            rows.append(dict(
                pair=sym, version=v, trades=s_all["trades"], win_rate=s_all["win_rate"],
                avg_R=s_all["avg_R"], profit_factor=s_all["profit_factor"], t_stat=s_all["sqn"],
                max_dd_pct=s_all["max_dd_pct"], losing_streak=s_all["longest_losing_streak"],
                net_return_pct=s_all["net_return_pct"], is_avg_R=s_is["avg_R"], oos_avg_R=s_oos["avg_R"],
                is_return_pct=s_is["net_return_pct"], oos_return_pct=s_oos["net_return_pct"],
                skipped_days=probe.skipped_incomplete + probe.skipped_no_data,
                reentries_filled=cnt.reentry_filled, reentries_invalid=cnt.reentry_skipped_invalid,
                median_box_pips=float(np.median(ranges)), median_spread_pips=float(np.median(spreads))))
            print(f"{sym} {v}: trades={s_all['trades']} avgR={s_all['avg_R']:+.3f} "
                  f"t={s_all['sqn']:+.2f} ret={s_all['net_return_pct']:+.1f}% "
                  f"IS={s_is['avg_R']:+.3f} OOS={s_oos['avg_R']:+.3f}", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(f"{out}/summary.csv", index=False)

    # ---------------- chart: one panel per pair, A and B
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5), sharex=True)
    for ax, sym in zip(axes.flat, PAIRS):
        for k, v in enumerate(VERSIONS):
            eq = curves[(sym, v)]
            ax.plot(eq.index, eq.to_numpy(), color=C[k], lw=1.6, drawstyle="steps-post",
                    label=f"{v} ({eq.iloc[-1] / START_BAL * 100 - 100:+.0f}%)")
        ax.axhline(START_BAL, color=INK2, lw=0.8)
        ax.axvline(splits[sym], color=INK2, lw=0.8, ls="--")
        ax.set_title(sym + ("  (reference)" if sym == "GBPJPY" else ""), loc="left")
        ax.legend(loc="upper left", fontsize=8.5)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    fig.suptitle("Versions A and B, base settings: closed balance per pair from $10,000 "
                 "(dashed line = in-sample | out-of-sample)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{out}/equity_by_pair.png", dpi=120)
    plt.close(fig)

    # ---------------- report
    def table(v: str) -> str:
        t = res[res.version == v].set_index("pair")[[
            "trades", "win_rate", "avg_R", "profit_factor", "t_stat", "max_dd_pct", "losing_streak",
            "net_return_pct", "is_avg_R", "oos_avg_R"]].copy()
        t["both halves +"] = np.where((t.is_avg_R > 0) & (t.oos_avg_R > 0), "yes", "no")
        t.index.name = f"Version {v}"
        return fmt_table(t)

    pool_rows = []
    for v in VERSIONS:
        maj = {k: np.concatenate(x[:len(MAJORS)]) for k, x in pooled[v].items()}
        pool_rows.append(dict(version=v, trades=len(maj["all"]), avg_R=maj["all"].mean(),
                              t_stat=tstat(maj["all"]), is_avg_R=maj["is"].mean(),
                              oos_avg_R=maj["oos"].mean()))
    pool = pd.DataFrame(pool_rows).set_index("version")
    pool.index.name = "All 7 majors pooled"

    ctx = res[res.version == "A"].set_index("pair")[["median_box_pips", "median_spread_pips",
                                                     "skipped_days"]]
    ctx["SL as x box"] = (BASE["sl_pips"] / ctx.median_box_pips).round(2)
    ctx.index.name = "Pair"
    ab = res.pivot(index="pair", columns="version", values=["avg_R", "reentries_filled",
                                                            "reentries_invalid"])
    ab.columns = [f"{a} {b}" for a, b in ab.columns]
    ab["A better?"] = np.where(ab["avg_R A"] > ab["avg_R B"], "yes", "no")
    ab.index.name = "Pair"

    rep = ["# Versions A and B on every major pair\n",
           "Base settings: IST 05:00–05:59 box, SL 30 pips + spread, RR 4, BE 3R → +5 pips, 1% "
           "risk compounding from $10,000, each pair its own account. Dukascopy bid/ask, "
           f"{START} → {args.end}. 60/40 in-sample / out-of-sample split by tradable days. "
           "GBPJPY is the original pair, shown for reference only and not included in the pooled row.\n",
           "## Version A — breakout, re-entry at the 6-minute extreme\n", table("A"),
           "\n## Version B — breakout, re-entry at the original box level\n", table("B"),
           "\n## All majors pooled (every trade, equal weight)\n", fmt_table(pool, ".3f"),
           "\n## A vs B per pair\n", fmt_table(ab, ".3f"),
           "\n## Context: box size, spread, skipped days\n",
           "The SL is 30 pips on every pair. On a pair whose 05:00–06:00 IST box is small, 30 pips "
           "is a wide stop relative to that morning's movement; on GBPJPY it is close to one box.\n",
           fmt_table(ctx, ".2f"),
           "\n![Equity by pair](equity_by_pair.png)\n",
           "Trade logs: `trade_logs/<PAIR>_<A|B>.csv`. Raw numbers: `summary.csv`.\n"]
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    print(pool.round(3))


if __name__ == "__main__":
    main()
