"""Version B (SL = 1 x box, 05:00 IST box) on the non-JPY minors: RR 1.5-10, BE off or 2R..RR-1.

Grid (fixed by the user before any result): RR 1.5, 2, 3 ... 10; BE off, or BE trigger at every
whole R from 2 up to RR - 1 (moves SL to entry + 5/30 of the SL distance) = 46 setups per pair.
Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill.
Data: 2024-2026 only, split 60/40 by tradable days into design / check. For each pair the best
design setup is checked; and every setup is also averaged over all pairs, which is much harder to
fit by luck. 46 x 15 = 690 tries: expect some great-looking design numbers from chance alone.

    python run_minors_grid.py                       # the 15 non-JPY minors
    python run_minors_grid.py --pairs EURUSD        # any pair(s) already in data/raw
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
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.swap import SwapModel
from run_backtest import C, INK2, fmt_table, split_days
from run_usdjpy_sl import tstat

PAIRS = ["EURGBP", "EURCHF", "EURAUD", "EURCAD", "EURNZD", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
         "AUDNZD", "AUDCAD", "AUDCHF", "NZDCAD", "NZDCHF", "CADCHF"]
RRS = [1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10]


SL_MULTS = [1.0]


def setups() -> list[Params]:
    out = []
    for mult in SL_MULTS:
        for rr in RRS:
            out.append(Params(rr=rr, sl_pips=30, be_trigger=None, be_plus=5, version="B", sl_box_mult=mult))
            for be in range(2, int(np.ceil(rr))):
                if be < rr:
                    out.append(Params(rr=rr, sl_pips=30, be_trigger=float(be), be_plus=5, version="B",
                                      sl_box_mult=mult))
    return out


def evaluate_pair(args):
    sym, end = args
    m = build_market(sym, date(2024, 1, 1), date.fromisoformat(end), "data/raw",
                     f"data/{sym.lower()}_1m.npz")
    days = trading_days(m, start="2024-01-01")
    _, probe = run(m, Params(sl_box_mult=1.0), days)
    skipped = {d for d, _ in probe.skipped_dates}
    valid = [d for d in days if d.date() not in skipped]
    design, check = split_days(valid)
    dset = set(design)
    swap = SwapModel.from_fred("rates", 1.0)
    rows = []
    for p in setups():
        trades, _ = run(m, p, valid)
        if not trades:
            continue
        lg = account(trades, m, 10_000, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
        is_design = pd.to_datetime(lg["day"]).isin(design).to_numpy()
        for pname, mask in (("design", is_design), ("check", ~is_design)):
            r = lg["R"].to_numpy()[mask]
            sl = "" if len(SL_MULTS) == 1 else f"SL{p.sl_box_mult:g}x "
            rows.append(dict(pair=sym, rr=p.rr, be=p.be_label, sl_mult=p.sl_box_mult,
                             setup=f"{sl}RR{p.rr:g} BE {p.be_label}",
                             period=pname, trades=len(r), win_rate=(r > 0).mean() * 100,
                             avg_R=r.mean() if len(r) else np.nan, t=tstat(r), total_R=r.sum()))
    info = dict(pair=sym, days=len(days), skipped=len(skipped), design_end=str(design[-1].date()),
                median_box_pips=float(np.median([t.range_pips for t in run(m, Params(sl_box_mult=1.0), valid)[0]
                                                 if t.num == 1])),
                median_spread_pips=float(np.median((m.ao - m.bo)[m.vol > 0]) / m.pip))
    print(f"{sym} done ({len(skipped)} of {len(days)} days skipped)", flush=True)
    return rows, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="*", default=PAIRS)
    ap.add_argument("--end", default="2026-10-07")
    ap.add_argument("--out", default="results/minors_grid")
    ap.add_argument("--sl-box", nargs="*", type=float, default=[1.0], help="SL multiples of the box")
    args = ap.parse_args()
    SL_MULTS[:] = args.sl_box
    os.makedirs(args.out, exist_ok=True)
    with Pool(min(os.cpu_count(), len(args.pairs))) as pool:
        out = pool.map(evaluate_pair, [(s, args.end) for s in args.pairs])
    res = pd.DataFrame([r for rows, _ in out for r in rows])
    info = pd.DataFrame([i for _, i in out]).set_index("pair")
    res.to_csv(f"{args.out}/grid.csv", index=False)

    des = res[res.period == "design"].set_index(["pair", "setup"])
    chk = res[res.period == "check"].set_index(["pair", "setup"])
    # per pair: best design setup, then its check result
    picks = []
    for sym in args.pairs:
        d = des.loc[sym]
        best = d["avg_R"].idxmax()
        c = chk.loc[(sym, best)]
        picks.append({"pair": sym, "design pick": best, "design avg R": d.loc[best, "avg_R"],
                      "design t": d.loc[best, "t"], "check avg R": c["avg_R"], "check t": c["t"],
                      "check trades": c["trades"], "held up?": "yes" if c["avg_R"] > 0 else "no"})
    picks = pd.DataFrame(picks).set_index("pair")
    # every setup averaged over all pairs (equal weight per pair)
    pooled = res.groupby(["period", "setup", "rr", "be", "sl_mult"])["avg_R"].mean().unstack("period")
    pooled["pairs positive in check"] = chk.groupby("setup")["avg_R"].apply(lambda x: int((x > 0).sum()))
    pooled = pooled.reset_index().sort_values("design", ascending=False).set_index("setup")
    pooled = pooled[["rr", "be", "sl_mult", "design", "check", "pairs positive in check"]]

    # chart: pooled avg R vs RR (BE off and the best BE per RR), design vs check
    fig, ax = plt.subplots(figsize=(11, 5))
    off = pooled[(pooled.be == "off") & (pooled.sl_mult == SL_MULTS[0])].sort_values("rr")
    ax.plot(off.rr, off.design, color=C[0], lw=2, marker="o", ms=5, ls="--", label="BE off — design")
    ax.plot(off.rr, off.check, color=C[0], lw=2, marker="o", ms=5, label="BE off — check")
    be2 = pooled[(pooled.be == "2R+5") & (pooled.sl_mult == SL_MULTS[0])].sort_values("rr")
    ax.plot(be2.rr, be2.design, color=C[1], lw=2, marker="s", ms=5, ls="--", label="BE at 2R — design")
    ax.plot(be2.rr, be2.check, color=C[1], lw=2, marker="s", ms=5, label="BE at 2R — check")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("RR")
    ax.set_ylabel("Avg R per trade, averaged over pairs (after costs)")
    ax.set_title(f"Version B on {len(args.pairs)} pairs: average across pairs by RR", loc="left")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{args.out}/pooled_by_rr.png", dpi=125)
    plt.close(fig)

    info.index.name = "Pair"
    rep = [f"# Version B (SL 1 × box, 05:00 IST) on {len(args.pairs)} pairs: RR 1.5–10 × BE\n",
           f"{len(setups())} setups per pair, {len(setups()) * len(args.pairs)} in total. $7/lot, swap "
           "(+1% markup), 0.2 pip slippage. 2024–2026 split 60/40 into design / check. "
           "With this many tries, judge by the check columns and by how many pairs agree.\n",
           "## Each pair's best design setup, checked\n", fmt_table(picks, ".3f"),
           f"\nPairs whose design pick held up in check: **{(picks['held up?'] == 'yes').sum()} of {len(picks)}**.\n",
           "## Every setup averaged over all pairs (top 15 by design)\n",
           fmt_table(pooled.drop(columns=["rr", "be", "sl_mult"]).head(15), ".3f"),
           "\n![Pooled](pooled_by_rr.png)\n", "## Data\n", fmt_table(info, ".2f"),
           "\nFull grid: `grid.csv`.\n"]
    with open(f"{args.out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))
    pd.set_option("display.width", 250)
    print(picks.round(3).to_string())
    print(pooled.drop(columns=["rr", "be", "sl_mult"]).head(15).round(3).to_string())
    by_mult = pooled.groupby("sl_mult")[["design", "check"]].agg(["mean", "max"])
    print(by_mult.round(3).to_string())
    print(info.round(2).to_string())


if __name__ == "__main__":
    main()
