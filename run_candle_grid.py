"""NY-open candle vs 12 EMA (gjstrat.candle): RR x stop-loss grid on every stored FX pair.

Any mix of targets and stops can be passed; the default is the full grid below.

    python run_candle_grid.py
    python run_candle_grid.py --rr 1 2 5 eod --sl candle atr1.5 pips15 --pairs EURUSD USDJPY

    --rr  : target in R, or "eod" (no target, flat at 16:00 NY)
    --sl  : candle      far end of the 09:30 candle (the reel's stop)
            candleNatr  candle stop, but at least N x ATR(14) of 5-minute candles
            atrN        N x ATR(14), ignoring the candle (+ spread)
            pipsN       N pips, ignoring the candle (+ spread)

Same costs and window as run_candle_ema.py. Each pair's days are split 60/40 into in-sample
and out-of-sample; "best" combos are picked on in-sample t-stat only, then shown out of sample.
"""
from __future__ import annotations

import argparse
import os
import re
from concurrent.futures import ProcessPoolExecutor
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from gjstrat.accounting import account, stats
from gjstrat.candle import CandleParams, atr5, ema5, ny_days, run_candle
from gjstrat.data import build_market
from run_backtest import DIVERGE, INK, IS_FRAC, fmt_table
from run_candle_ema import COMMISSION, END, LONG_HISTORY, PAIRS, SLIPPAGE, START_3Y, tstat

RR_DEFAULT = ["1", "1.5", "2", "3", "4", "5", "7", "10", "eod"]
SL_DEFAULT = ["candle", "candle1atr", "candle2atr", "atr0.5", "atr1", "atr2", "atr3", "atr4",
              "pips5", "pips10", "pips15", "pips20", "pips30"]


def parse_sl(s: str) -> dict:
    if s == "candle":
        return {}
    for pat, key in ((r"candle([\d.]+)atr", "stop_atr"), (r"atr([\d.]+)", "sl_atr"),
                     (r"pips([\d.]+)", "sl_pips")):
        mt = re.fullmatch(pat, s)
        if mt:
            return {key: float(mt.group(1))}
    raise SystemExit(f"bad --sl value: {s}")


def parse_rr(s: str) -> float | None:
    return None if s.lower() == "eod" else float(s)


def run_pair(job) -> tuple[list[dict], dict]:
    sym, sls, rrs = job
    start = START_3Y if sym in LONG_HISTORY else date(2024, 1, 1)
    m = build_market(sym, start, END, "data/raw", f"data/{sym.lower()}_candle_{start}.npz")
    days = ny_days(m, start=str(start), end=str(END))
    split = days[int(round(len(days) * IS_FRAC))]
    ema, atr = ema5(m), atr5(m)
    yrs = (days[-1] - days[0]).days / 365.25
    rows, pooled = [], {}
    for sl in sls:
        for rr in rrs:
            p = CandleParams(rr=parse_rr(rr), **parse_sl(sl))
            trades, _ = run_candle(m, p, days, ema, atr)
            log = account(trades, m, 10_000, 1.0, commission=COMMISSION, slippage_pips=SLIPPAGE)
            s = stats(log, 10_000, yrs)
            r = log["R"].to_numpy()
            gross = np.array([t.r for t in trades])
            is_ = (pd.to_datetime(log["day"]) < split).to_numpy()
            rows.append(dict(pair=sym, sl=sl, rr=rr, trades=len(r), win_rate=s["win_rate"],
                             avg_R=s["avg_R"], gross_avg_R=gross.mean() if len(gross) else np.nan,
                             profit_factor=s["profit_factor"], t_stat=tstat(r),
                             is_avg_R=r[is_].mean(), is_t=tstat(r[is_]),
                             oos_avg_R=r[~is_].mean(), oos_t=tstat(r[~is_]),
                             net_return_pct=s["net_return_pct"], max_dd_pct=s["max_dd_pct"],
                             median_risk_pips=log["risk_pips"].median()))
            pooled[(sl, rr)] = (r, is_)
    print(sym, "done", flush=True)
    return rows, pooled


def heatmap(ax, grid: pd.DataFrame, title: str, fmt: str, vmax: float):
    data = grid.to_numpy(dtype=float)
    ax.imshow(np.ma.masked_invalid(data), cmap=DIVERGE, aspect="auto",
              norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax))
    ax.set_xticks(range(grid.shape[1]), list(grid.columns))
    ax.set_yticks(range(grid.shape[0]), list(grid.index))
    ax.set_xlabel("Target (R)")
    ax.set_ylabel("Stop loss")
    ax.grid(False)
    for (i, j), v in np.ndenumerate(data):
        ax.text(j, i, format(v, fmt), ha="center", va="center", fontsize=8.5,
                color=INK if abs(v) < vmax * 0.6 else "white")
    ax.set_title(title, loc="left", fontsize=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rr", nargs="*", default=RR_DEFAULT)
    ap.add_argument("--sl", nargs="*", default=SL_DEFAULT)
    ap.add_argument("--pairs", nargs="*", default=PAIRS)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="results/candle_grid")
    a = ap.parse_args()
    for s in a.sl:
        parse_sl(s)
    os.makedirs(a.out, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as ex:
        out = list(ex.map(run_pair, [(sym, a.sl, a.rr) for sym in a.pairs]))
    res = pd.DataFrame([r for rows, _ in out for r in rows])
    res.round(4).to_csv(f"{a.out}/grid.csv", index=False)

    # pooled: all pairs' trades per combo, 1R each
    pool = []
    for sl in a.sl:
        for rr in a.rr:
            r = np.concatenate([pl[(sl, rr)][0] for _, pl in out])
            is_ = np.concatenate([pl[(sl, rr)][1] for _, pl in out])
            sub = res[(res.sl == sl) & (res.rr == rr)]
            pool.append(dict(sl=sl, rr=rr, trades=len(r), win_rate=(r > 0).mean() * 100,
                             avg_R=r.mean(), gross_avg_R=np.average(sub.gross_avg_R, weights=sub.trades),
                             profit_factor=r[r > 0].sum() / -r[r < 0].sum(), t_stat=tstat(r),
                             is_avg_R=r[is_].mean(), is_t=tstat(r[is_]), oos_avg_R=r[~is_].mean(),
                             oos_t=tstat(r[~is_]), pairs_positive=int((sub.avg_R > 0).sum()),
                             pairs_oos_positive=int((sub.oos_avg_R > 0).sum())))
    pool = pd.DataFrame(pool)
    pool.round(4).to_csv(f"{a.out}/pooled.csv", index=False)
    piv = lambda col: pool.pivot(index="sl", columns="rr", values=col).loc[a.sl, a.rr]

    fig, axes = plt.subplots(1, 3, figsize=(20, 0.55 * len(a.sl) + 2.2))
    for ax, col, title, fmt in ((axes[0], "avg_R", "Avg R / trade, net (all pairs pooled)", "+.2f"),
                                (axes[1], "gross_avg_R", "Avg R / trade, gross (no costs)", "+.2f"),
                                (axes[2], "oos_avg_R", "Avg R / trade, net, out-of-sample 40%", "+.2f")):
        g = piv(col)
        heatmap(ax, g, title, fmt, max(np.nanmax(np.abs(g.to_numpy(dtype=float))), 0.05))
    fig.tight_layout()
    fig.savefig(f"{a.out}/grid_heatmap.png", dpi=120)
    plt.close(fig)

    best_is = pool.loc[pool.is_t.idxmax()]
    per_pair = res.loc[res.groupby("pair")["is_t"].idxmax()].set_index("pair").loc[a.pairs]
    per_pair = per_pair[["sl", "rr", "trades", "is_avg_R", "is_t", "oos_avg_R", "oos_t", "avg_R",
                         "net_return_pct", "max_dd_pct"]]
    per_pair.index.name = "Pair"
    top = pool.sort_values("avg_R", ascending=False).head(10).set_index(["sl", "rr"])
    top.index = [f"{s} / {r}" for s, r in top.index]
    top.index.name = "Stop / target"
    pos = res[res.avg_R > 0].sort_values("avg_R", ascending=False)
    pos_t = pos.set_index(["pair", "sl", "rr"])[["trades", "avg_R", "t_stat", "is_avg_R", "oos_avg_R",
                                                  "net_return_pct", "max_dd_pct"]]
    pos_t.index = [" / ".join(i) for i in pos_t.index]
    pos_t.index.name = "Pair / stop / target"

    rep = [
        "# NY-open candle vs 12 EMA — stop × target grid\n",
        f"Rule as in `results/candle_ema/`. Stops: {', '.join(a.sl)}. Targets: {', '.join(a.rr)} "
        "(eod = no target, flat at 16:00 NY). `candleNatr` = candle stop but at least N × ATR(14) "
        "of 5-minute candles; `atrN` / `pipsN` ignore the candle (+ spread). "
        f"{len(a.pairs)} pairs, {len(a.sl) * len(a.rr)} combos each = {len(res)} runs. "
        f"Costs ${COMMISSION:g}/lot + {SLIPPAGE:g} pip slippage, 1% risk compounding per pair. "
        f"In-sample = first {IS_FRAC:.0%} of each pair's days, out-of-sample = the rest.\n",
        f"**Positive after costs: {len(pos)} of {len(res)} pair × combo runs; "
        f"{int((pool.avg_R > 0).sum())} of {len(pool)} combos pooled over all pairs.** "
        f"Best pooled combo picked in-sample: {best_is.sl} / {best_is.rr} → in-sample "
        f"{best_is.is_avg_R:+.3f}R (t {best_is.is_t:+.2f}), out-of-sample {best_is.oos_avg_R:+.3f}R "
        f"(t {best_is.oos_t:+.2f}).\n",
        "![Grid](grid_heatmap.png)\n",
        "## Top 10 combos, all pairs pooled (net)\n", fmt_table(top, ".3f"),
        "\n## Best combo per pair, picked on in-sample t-stat\n", fmt_table(per_pair, ".3f"),
        "\n## Every pair × combo that is positive after costs\n",
        fmt_table(pos_t, ".3f") if len(pos_t) else "None.", "",
    ]
    open(f"{a.out}/REPORT.md", "w").write("\n".join(rep))
    print(top.round(3).to_string())
    print(per_pair.round(3).to_string())
    print("positive runs:", len(pos), "/", len(res))
    print(pos_t.round(3).to_string())


if __name__ == "__main__":
    main()
