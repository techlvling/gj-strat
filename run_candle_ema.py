"""NY-open candle vs 12 EMA (gjstrat.candle) on every pair in datastore/, last 3 years.

The reel's management is not disclosed, so a few common exits are tested side by side:
stop = far end of the 09:30-09:34 NY candle, target 1R / 1.5R / 2R / 3R, no target (flat at
16:00 NY), or no target with an exit on a 5-minute close back across the 12 EMA; and the same
with the stop floored at 2 x ATR(14) of 5-minute candles (the raw candle stop is often < 1 pip).
1% risk compounding from $10,000, each pair its own account. Costs: $7/lot round turn and
0.2 pip slippage on the entry and on every non-limit exit; the "gross" rows have no costs.

    python run_candle_ema.py      # needs data/raw (python fetch_pairs.py --save restores it)
"""
from __future__ import annotations

import os
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gjstrat.accounting import account, stats
from gjstrat.candle import CandleParams, atr5, direction_moves, ema5, ny_days, run_candle
from gjstrat.data import build_market
from run_backtest import C, INK2, fmt_table

END = date(2026, 10, 7)
START_3Y = date(2023, 10, 8)
LONG_HISTORY = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "GBPJPY"]   # stored from 2010
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
         "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD", "GBPCHF",
         "GBPAUD", "GBPCAD", "GBPNZD", "AUDNZD", "AUDCAD", "AUDCHF", "NZDCAD", "NZDCHF", "CADCHF"]
VARIANTS = [CandleParams(rr=1), CandleParams(rr=1.5), CandleParams(rr=2), CandleParams(rr=3),
            CandleParams(rr=None), CandleParams(rr=None, ema_trail=True),
            CandleParams(rr=2, stop_atr=2), CandleParams(rr=None, stop_atr=2),
            CandleParams(rr=None, stop_atr=2, ema_trail=True)]
COMMISSION, SLIPPAGE = 7.0, 0.2
OUT = "results/candle_ema"


def tstat(r: np.ndarray) -> float:
    return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 else np.nan


def main():
    os.makedirs(f"{OUT}/trade_logs", exist_ok=True)
    rows, pooled, direction = [], {p.label: [] for p in VARIANTS}, {}
    for sym in PAIRS:
        start = START_3Y if sym in LONG_HISTORY else date(2024, 1, 1)
        m = build_market(sym, start, END, "data/raw", f"data/{sym.lower()}_candle_{start}.npz")
        days = ny_days(m, start=str(start), end=str(END))
        ema, atr = ema5(m), atr5(m)
        mv = direction_moves(m, days, ema)
        direction[sym] = dict(days=len(mv), right_pct=(mv > 0).mean() * 100, mean_pips=mv.mean(),
                              t_stat=tstat(mv))
        yrs = (pd.Timestamp(days[-1]) - pd.Timestamp(days[0])).days / 365.25
        for p in VARIANTS:
            trades, cnt = run_candle(m, p, days, ema, atr)
            net = account(trades, m, 10_000, 1.0, commission=COMMISSION, slippage_pips=SLIPPAGE)
            gross = account(trades, m, 10_000, 1.0)
            s, g = stats(net, 10_000, yrs), stats(gross, 10_000, yrs)
            net["pair"] = sym
            net["entry_time_ny"] = pd.to_datetime(net["entry_i"].map(m.ts)).dt.tz_localize("UTC") \
                .dt.tz_convert("America/New_York").dt.tz_localize(None)
            pooled[p.label].append(net)
            if p.label == "2R":
                net.drop(columns=["entry_time_ist", "exit_time_ist", "gap_fill", "be_moved",
                                  "trade_num", "swap_usd", "swap_nights"]) \
                    .to_csv(f"{OUT}/trade_logs/{sym}_2R.csv", index=False)
            r = net["R"].to_numpy()
            rows.append(dict(pair=sym, variant=p.label, first_day=days[0].date(), trades=s["trades"],
                             win_rate=s["win_rate"], avg_R=s["avg_R"], total_R=r.sum(),
                             profit_factor=s["profit_factor"], t_stat=tstat(r),
                             net_return_pct=s["net_return_pct"], max_dd_pct=s["max_dd_pct"],
                             gross_avg_R=g["avg_R"], gross_return_pct=g["net_return_pct"],
                             median_risk_pips=net["risk_pips"].median(),
                             median_spread_pips=net["spread_pips"].median(),
                             skipped=cnt["no_data"] + cnt["flat_close"] + cnt["bad_risk"]))
        print(sym, "done", flush=True)
    res = pd.DataFrame(rows)
    res.round(4).to_csv(f"{OUT}/summary.csv", index=False)

    # pooled per variant: every trade of every pair, 1R each
    pool_rows, curves = {}, {}
    for label, logs in pooled.items():
        allt = pd.concat(logs).sort_values("entry_time_ny")
        r = allt["R"].to_numpy()
        yr = allt["entry_time_ny"].dt.year
        pool_rows[label] = dict(
            trades=len(r), win_rate=(r > 0).mean() * 100, avg_R=r.mean(),
            profit_factor=r[r > 0].sum() / -r[r < 0].sum(), t_stat=tstat(r),
            pairs_positive=int((res[res.variant == label].total_R > 0).sum()),
            **{f"avg_R_{y}": allt.loc[yr == y, "R"].mean() for y in sorted(yr.unique())})
        curves[label] = pd.Series(r.cumsum() / len(PAIRS), index=allt["entry_time_ny"].to_numpy())
    pool = pd.DataFrame(pool_rows).T
    pool.index.name = "Exit"

    fig, ax = plt.subplots(figsize=(12, 5))
    for k, (label, cur) in enumerate(curves.items()):
        ax.plot(cur.index, cur.to_numpy(), color=C[k % len(C)], lw=1.6, ls="--" if "ATR" in label else "-", label=f"{label} ({cur.iloc[-1]:+.1f}R)")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title("NY-open candle vs 12 EMA: cumulative R per pair (avg of 24 pairs, all costs)",
                 loc="left")
    ax.set_ylabel("R per pair")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/pooled_equity.png", dpi=125)
    plt.close(fig)

    def pivot(col):
        t = res.pivot(index="pair", columns="variant", values=col)[[p.label for p in VARIANTS]]
        t = t.loc[PAIRS]
        t.index.name = "Pair"
        return t

    cand = res[res.variant == "2R"]
    dirn = pd.DataFrame(direction).T.loc[PAIRS]
    dirn.index.name = "Pair"
    dirn.round(4).to_csv(f"{OUT}/direction.csv")
    best = res.loc[res.groupby("pair")["avg_R"].idxmax()].set_index("pair").loc[PAIRS]
    best = best[["variant", "trades", "win_rate", "avg_R", "profit_factor", "t_stat",
                 "net_return_pct", "max_dd_pct"]]
    best.index.name = "Pair"
    info = res[res.variant == "2R"].set_index("pair").loc[PAIRS][
        ["first_day", "trades", "median_risk_pips", "median_spread_pips"]]
    info.index.name = "Pair"
    rep = [
        "# NY-open candle vs 12 EMA — all stored FX pairs, last 3 years\n",
        "Rule (from the reel): 5-minute chart, the 09:30–09:34 New York candle. Close above the "
        "12 EMA → buy at the 09:35 open, close below → sell. Stop = far end of that candle "
        "(+ spread on shorts). The reel hides its trade management, so several exits are compared, "
        "plus the same with the stop floored at 2 × ATR(14) of 5-minute candles. "
        "Every open trade is closed at 16:00 New York.\n",
        f"Window: {START_3Y} → {END} for {', '.join(LONG_HISTORY)}; 2024-01-01 → {END} for the "
        "rest (stored data starts there). XAUUSD is left out (stored only to 2015). "
        f"Costs: ${COMMISSION:g}/lot round turn + {SLIPPAGE:g} pip slippage on the entry and on "
        "every non-limit exit. 1% risk compounding from $10,000, each pair its own account.\n",
        f"**Verdict: no edge.** {int((res.avg_R > 0).sum())} of {len(res)} pair × exit runs are "
        f"positive after costs and {int((res.gross_avg_R > 0).sum())} before costs "
        f"({', '.join(res[res.gross_avg_R > 0].apply(lambda x: f'{x.pair} {x.variant}', axis=1))}). "
        f"The direction alone is right on {dirn.right_pct.mean():.1f}% of days before any cost, so "
        "better management cannot rescue it, and the raw candle stop (median "
        f"{cand.median_risk_pips.min():.1f}–{cand.median_risk_pips.max():.1f} pips by pair, often "
        "< 1 pip from the fill) makes spread and commission a large share of 1R.\n",
        "## Is the direction right? (no stop, no target, no costs)\n",
        "Mid price from the 09:35 open to the 16:00 NY open, signed by the signal. "
        f"Right on {dirn.right_pct.mean():.1f}% of days on average; mean move > 0 on "
        f"{int((dirn.mean_pips > 0).sum())} of {len(dirn)} pairs.\n",
        fmt_table(dirn, ".2f"),
        "\n## All pairs pooled (net of costs)\n",
        fmt_table(pool, ".3f"), "\n![Pooled equity](pooled_equity.png)\n",
        "## Average R per trade, net (pair × exit)\n", fmt_table(pivot("avg_R"), "+.3f"),
        "\n## Average R per trade, gross (no commission, no slippage)\n",
        fmt_table(pivot("gross_avg_R"), "+.3f"),
        "\n## Net return % at 1% risk (pair × exit)\n", fmt_table(pivot("net_return_pct"), "+.1f"),
        "\n## Max drawdown % (pair × exit)\n", fmt_table(pivot("max_dd_pct"), ".1f"),
        "\n## Best exit per pair (picked in hindsight — optimistic)\n", fmt_table(best, ".2f"),
        "\n## Signal candle size and cost\n", fmt_table(info, ".1f"), "",
    ]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep))
    print(dirn.round(2).to_string())
    print(pool.round(3).to_string())
    print(pivot("avg_R").round(3).to_string())
    print(best.round(3).to_string())


if __name__ == "__main__":
    main()
