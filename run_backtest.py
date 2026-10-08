"""GBPJPY IST 05:00-06:00 range breakout: base A/B comparison, Version A sweep, IS/OOS,
plateau checks, breakdowns, charts, trade logs and a markdown report.

    python run_backtest.py                 # Dukascopy data (downloads + caches under data/)
    python run_backtest.py --synthetic     # random-walk sanity run, no download
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
from datetime import date
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from gjstrat.accounting import account, breakdown, equity_curve, stats
from gjstrat.data import build_dukascopy_market, synthetic_market
from gjstrat.engine import Params, run, trading_days

START, START_BAL = "2024-01-01", 10_000.0
BASE = dict(rr=4.0, sl_pips=30.0, be_trigger=3.0, be_plus=5.0)
RRS = [1, 1.5, 2, 3, 4, 5]
SLS = [15, 20, 30, 40, 50]
BES = [None] + [(t, p) for t in (1, 1.5, 2, 3) for p in (0, 5)]
IS_FRAC = 0.6

# reference palette (dataviz skill, light mode)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
DIVERGE = LinearSegmentedColormap.from_list(
    "rb", ["#c83a3a", "#e98d8a", "#f0efec", "#86b6ef", "#1c5cab"])
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titleweight": "bold",
    "axes.titlesize": 11, "legend.frameon": False,
})

M = None   # market, global so forked workers share it


def combos() -> list[Params]:
    out = []
    for rr, sl, be in itertools.product(RRS, SLS, BES):
        if be is not None and be[0] >= rr:
            continue
        out.append(Params(rr=rr, sl_pips=sl, be_trigger=None if be is None else be[0],
                          be_plus=0 if be is None else be[1], version="A"))
    return out


def split_days(days):
    k = int(round(len(days) * IS_FRAC))
    return days[:k], days[k:]


def years_of(days) -> float:
    return max((days[-1] - days[0]).days / 365.25, 1e-9)


def evaluate(p: Params, days, is_days, oos_days) -> dict:
    trades, cnt = run(M, p, days)
    is_set = set(is_days)
    t_is = [t for t in trades if t.day in is_set]
    t_oos = [t for t in trades if t.day not in is_set]
    row = dict(label=p.label, rr=p.rr, sl=p.sl_pips, be=p.be_label, be_trigger=p.be_trigger,
               be_plus=p.be_plus)
    for tag, ts, ds in (("is", t_is, is_days), ("oos", t_oos, oos_days), ("all", trades, days)):
        s = stats(account(ts, M, START_BAL), START_BAL, years_of(ds))
        row.update({f"{tag}_{k}": v for k, v in s.items()})
    row.update({f"cnt_{k}": v for k, v in cnt.as_dict().items()})
    return row


def _eval_star(args):
    return evaluate(*args)


# --------------------------------------------------------------------------- charts
def plot_equity(curves: dict[str, pd.Series], path: str, title: str, split=None, log=False):
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for k, (name, eq) in enumerate(curves.items()):
        ax.plot(eq.index, eq.to_numpy(), color=C[k % len(C)], lw=2, drawstyle="steps-post",
                label=f"{name}  ({eq.iloc[-1] / START_BAL * 100 - 100:+.0f}%)")
    if split is not None:
        ax.axvline(split, color=INK2, lw=1, ls="--")
        ax.text(split, 1.0, "  out-of-sample →", transform=ax.get_xaxis_transform(),
                va="top", fontsize=9, color=INK2)
        ax.text(split, 1.0, "← in-sample  ", transform=ax.get_xaxis_transform(),
                va="top", ha="right", fontsize=9, color=INK2)
    ax.axhline(START_BAL, color=INK2, lw=0.8)
    if log:
        ax.set_yscale("log")
    ax.set_ylabel("Closed balance (USD)")
    ax.set_title(title, loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=min(len(curves), 3), fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def heat(ax, grid: pd.DataFrame, title: str, fmt: str, vmax: float):
    data = grid.to_numpy(dtype=float)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    ax.imshow(np.ma.masked_invalid(data), cmap=DIVERGE, norm=norm, aspect="auto")
    ax.set_xticks(range(grid.shape[1]), [f"{c:g}" for c in grid.columns])
    ax.set_yticks(range(grid.shape[0]), [f"{r:g}" for r in grid.index])
    ax.set_xlabel("SL (pips + spread)")
    ax.set_ylabel("RR")
    ax.grid(False)
    for (i, j), v in np.ndenumerate(data):
        txt = "n/a" if np.isnan(v) else format(v, fmt)
        ax.text(j, i, txt, ha="center", va="center", fontsize=8.5,
                color=INK if np.isnan(v) or abs(v) < vmax * 0.6 else "white")
    ax.set_title(title, loc="left", fontsize=10)


def plot_heatmaps(res: pd.DataFrame, best_be: str, path: str):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.6))
    specs = [("is_avg_R", "In-sample avg R", "+.2f"), ("is_net_return_pct", "In-sample net return %", "+.0f"),
             ("oos_avg_R", "Out-of-sample avg R (not used for selection)", "+.2f")]
    for r, be in enumerate(["off", best_be]):
        sub = res[res.be == be]
        for c, (col, name, fmt) in enumerate(specs):
            g = sub.pivot(index="rr", columns="sl", values=col).reindex(index=RRS, columns=SLS)
            g = g.dropna(how="all")          # RR rows where this BE trigger is not < RR
            vmax = np.nanmax(np.abs(res[col].to_numpy())) or 1
            heat(axes[r, c], g, f"BE {be}: {name}", fmt, vmax)
    fig.suptitle("Version A sweep: RR × SL size (blue = positive, red = negative)", x=0.01,
                 ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------- helpers
def fmt_table(df: pd.DataFrame, floatfmt=".2f") -> str:
    def f(v):
        if isinstance(v, (float, np.floating)):
            if np.isinf(v):
                return "inf"
            return "" if np.isnan(v) else format(v, floatfmt)
        return str(v)
    cols = list(df.columns)
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
             "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [f(row[c]) for c in cols]) + " |")
    return "\n".join(lines)


STAT_ROWS = [("trades", "Trades", "{:.0f}"), ("win_rate", "Win rate %", "{:.1f}"),
             ("avg_R", "Avg R", "{:+.3f}"), ("profit_factor", "Profit factor", "{:.2f}"),
             ("expectancy_R", "Expectancy (R/trade)", "{:+.3f}"),
             ("expectancy_pct", "Expectancy (% equity/trade)", "{:+.3f}"),
             ("sqn", "t-stat of mean R (SQN)", "{:+.2f}"), ("max_dd_pct", "Max drawdown %", "{:.1f}"),
             ("longest_losing_streak", "Longest losing streak", "{:.0f}"),
             ("net_return_pct", "Net return %", "{:+.1f}"), ("cagr_pct", "CAGR %", "{:+.1f}")]


def stat_table(cols: dict[str, dict]) -> str:
    out = ["| Metric | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for key, name, f in STAT_ROWS:
        vals = []
        for s in cols.values():
            v = s.get(key, np.nan)
            vals.append("" if v is None or (isinstance(v, float) and np.isnan(v))
                        else ("inf" if np.isinf(v) else f.format(v)))
        out.append(f"| {name} | " + " | ".join(vals) + " |")
    return "\n".join(out)


def range_bucket(x):
    return pd.cut(x, [-np.inf, 20, 40, 60, np.inf], right=False,
                  labels=["<20", "20-40", "40-60", "60+"])


def breakdowns(log: pd.DataFrame) -> str:
    d = pd.to_datetime(log["day"])
    parts = [("Range size (pips)", range_bucket(log["range_pips"])),
             ("Side", log["side"]), ("Trade number", log["trade_num"]),
             ("Day of week", pd.Categorical(d.dt.day_name(), ["Monday", "Tuesday", "Wednesday",
                                                              "Thursday", "Friday"], ordered=True)),
             ("Month", d.dt.strftime("%Y-%m")),
             ("Exit reason", log["exit_reason"])]
    out = []
    for name, key in parts:
        b = breakdown(log, pd.Series(key, index=log.index))
        b.index.name = name
        out.append(f"**By {name.lower()}**\n\n" + fmt_table(b, ".3f"))
    return "\n\n".join(out)


def clean_log(log: pd.DataFrame) -> pd.DataFrame:
    out = log.drop(columns=["entry_i", "exit_i"]).copy()
    out.insert(1, "weekday", pd.to_datetime(out["day"]).dt.day_name())
    for c in ("entry_time_ist", "exit_time_ist"):
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d %H:%M")
    out["R"] = out["R"].round(3)
    return out


def neighbours(res: pd.DataFrame, row) -> pd.DataFrame:
    i, j = RRS.index(row.rr), SLS.index(row.sl)
    cand = [(i + di, j + dj) for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= i + di < len(RRS) and 0 <= j + dj < len(SLS)]
    keys = [(RRS[a], SLS[b]) for a, b in cand]
    sub = res[(res.be == row.be) & res.apply(lambda r: (r.rr, r.sl) in keys, axis=1)]
    return sub


# --------------------------------------------------------------------------- main
def main():
    global M
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--end", default=None, help="last UTC date to download (default: yesterday)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--commission", type=float, default=0.0, help="USD per lot round turn")
    ap.add_argument("--max-missing", type=int, default=0,
                    help="allowed tick-less minutes in the 05:00-05:59 range window")
    args = ap.parse_args()

    out = args.out
    os.makedirs(f"{out}/trade_logs", exist_ok=True)
    os.makedirs(f"{out}/charts", exist_ok=True)

    if args.synthetic:
        M = synthetic_market(START, days=700)
        source = "SYNTHETIC random walk (engine sanity check — not market data)"
    else:
        end = date.fromisoformat(args.end) if args.end else (pd.Timestamp.utcnow().date() - pd.Timedelta(days=1))
        M = build_dukascopy_market(date.fromisoformat(START), end, "data/raw", "data/gbpjpy_1m.npz")
        source = "Dukascopy GBPJPY 1-minute BID + ASK candles; USDJPY 1-minute BID for pip value"

    days = trading_days(M, start=START)
    # IS/OOS split on days that actually have a valid range (skipped days don't count)
    probe_trades, probe_cnt = run(M, Params(**BASE), days, max_missing=args.max_missing)
    skipped = {d for d, _ in probe_cnt.skipped_dates}
    valid_days = [d for d in days if d.date() not in skipped]
    is_days, oos_days = split_days(valid_days)
    split_ts = oos_days[0]
    days = valid_days          # skipped days are skipped either way; keep the count from the probe
    spreads = np.array([t.spread for t in probe_trades]) / 0.01

    # ---------------- base: Version A vs B
    base = {}
    for v in ("A", "B"):
        p = Params(**BASE, version=v)
        trades, cnt = run(M, p, days)
        log = account(trades, M, START_BAL, commission=args.commission)
        is_set = set(is_days)
        base[v] = dict(
            p=p, log=log, cnt=cnt,
            all=stats(log, START_BAL, years_of(days)),
            is_=stats(account([t for t in trades if t.day in is_set], M, START_BAL, commission=args.commission),
                      START_BAL, years_of(is_days)),
            oos=stats(account([t for t in trades if t.day not in is_set], M, START_BAL, commission=args.commission),
                      START_BAL, years_of(oos_days)))
        clean_log(log).to_csv(f"{out}/trade_logs/base_version_{v}.csv", index=False)
    plot_equity({f"Version A (6-bar extreme)": equity_curve(base["A"]["log"]),
                 f"Version B (original range level)": equity_curve(base["B"]["log"])},
                f"{out}/charts/equity_base_A_vs_B.png",
                "Base settings (RR 4, SL 30+spread, BE 3R+5): closed balance, 1% risk compounding",
                split=split_ts)

    # ---------------- sweep (Version A)
    cs = combos()
    with Pool(os.cpu_count()) as pool:
        rows = pool.map(_eval_star, [(p, days, is_days, oos_days) for p in cs], chunksize=2)
    res = pd.DataFrame(rows)
    res.to_csv(f"{out}/sweep_version_A.csv", index=False)
    n_combos = len(res)

    # rank on IN-SAMPLE only: t-stat of mean R (penalises small/noisy samples)
    res["is_rank"] = res["is_sqn"].rank(ascending=False, method="first", na_option="bottom").astype(int)
    res = res.sort_values("is_rank")
    top = res.head(5).copy()

    # plateau: same BE setting, adjacent RR and SL values, judged on in-sample numbers only
    plateau_rows, flags = [], {}
    for _, r in top.iterrows():
        nb = neighbours(res, r)
        pos_share = (nb.is_avg_R > 0).mean() if len(nb) else np.nan
        med_sqn = nb.is_sqn.median() if len(nb) else np.nan
        f = []
        if len(nb) == 0 or pos_share < 0.5 or med_sqn < 0.5 * r.is_sqn:
            f.append("NOISE? (weak neighbours)")
        if r.is_avg_R > 0 and (r.oos_avg_R <= 0 or r.oos_profit_factor < 1):
            f.append("OVERFIT (fails OOS)")
        elif r.is_avg_R > 0 and r.oos_avg_R < 0.5 * r.is_avg_R:
            f.append("DEGRADED OOS (<50% of IS avg R)")
        if r.is_trades < 100 or r.oos_trades < 100:
            f.append("SMALL SAMPLE (<100 trades)")
        if (r.is_profit_factor > 2.5 or r.is_cagr_pct > 100 or
                (r.is_win_rate > 75 and r.rr >= 2)):
            f.append("UNREALISTICALLY GOOD?")
        flags[r.label] = f or ["—"]
        for _, n in nb.iterrows():
            plateau_rows.append(dict(top=r.label, neighbour=n.label, is_avg_R=n.is_avg_R,
                                     is_sqn=n.is_sqn, is_trades=n.is_trades))
        plateau_rows.append(dict(top=r.label, neighbour="→ share of neighbours with IS avg R > 0",
                                 is_avg_R=pos_share, is_sqn=med_sqn, is_trades=np.nan))
    plateau = pd.DataFrame(plateau_rows)

    # top-5 full detail
    top_detail = {}
    for k, (_, r) in enumerate(top.iterrows(), 1):
        be_on = not pd.isna(r.be_trigger)
        p = Params(rr=r.rr, sl_pips=r.sl, be_trigger=r.be_trigger if be_on else None,
                   be_plus=r.be_plus if be_on else 0, version="A")
        trades, cnt = run(M, p, days)
        log = account(trades, M, START_BAL, commission=args.commission)
        clean_log(log).to_csv(f"{out}/trade_logs/top{k}_{p.label}.csv", index=False)
        top_detail[p.label] = dict(p=p, log=log, cnt=cnt, row=r)
    plot_equity({f"#{k} {lbl}": equity_curve(d["log"]) for k, (lbl, d) in enumerate(top_detail.items(), 1)},
                f"{out}/charts/equity_top5.png",
                "Top 5 by in-sample t-stat: full-period closed balance (rank chosen left of the line)",
                split=split_ts)

    # BE vs no BE (paired on identical RR × SL cells)
    off = res[res.be == "off"].set_index(["rr", "sl"])
    be_cmp = []
    for be in [b for b in res.be.unique() if b != "off"]:
        on = res[res.be == be].set_index(["rr", "sl"])
        common = on.index.intersection(off.index)
        be_cmp.append(dict(be=be, cells=len(common),
                           is_avg_R_diff=(on.loc[common, "is_avg_R"] - off.loc[common, "is_avg_R"]).mean(),
                           is_return_diff=(on.loc[common, "is_net_return_pct"] - off.loc[common, "is_net_return_pct"]).mean(),
                           is_better_share=((on.loc[common, "is_avg_R"] > off.loc[common, "is_avg_R"]).mean() * 100),
                           oos_avg_R_diff=(on.loc[common, "oos_avg_R"] - off.loc[common, "oos_avg_R"]).mean()))
    be_cmp = pd.DataFrame(be_cmp).set_index("be").sort_values("is_avg_R_diff", ascending=False)
    best_be = be_cmp.index[0]
    plot_heatmaps(res, best_be, f"{out}/charts/heatmaps_rr_x_sl.png")

    by_rr = res.groupby("rr")[["is_avg_R", "is_net_return_pct", "oos_avg_R"]].median()
    by_sl = res.groupby("sl")[["is_avg_R", "is_net_return_pct", "oos_avg_R"]].median()

    # how lucky could the best look by chance? expected max of N independent N(0,1) t-stats
    exp_max_t = np.sqrt(2 * np.log(n_combos))

    # ---------------- report
    a, b = base["A"], base["B"]
    cA = a["cnt"]
    rep = []
    w = rep.append
    w("# GBPJPY 05:00–06:00 IST range breakout — backtest report\n")
    w(f"*Data:* {source}.  ")
    w(f"*Period:* {days[0].date()} → {days[-1].date()} (IST trading days), "
      f"{len(days)} tradable days.  ")
    w(f"*In-sample:* {is_days[0].date()} → {is_days[-1].date()} ({len(is_days)} days).  "
      f"*Out-of-sample:* {oos_days[0].date()} → {oos_days[-1].date()} ({len(oos_days)} days).  ")
    w(f"*Costs:* real bid/ask from the data (median entry spread {np.median(spreads):.1f} pips, "
      f"90th pct {np.percentile(spreads, 90):.1f}), commission ${args.commission:g}/lot, no swap, "
      f"lots rounded down to 0.01. Start $10,000, 1% risk of closed balance per trade.\n")

    w("## Data quality\n")
    w(f"| | Count |\n|---|---|\n| Mon–Fri IST dates in period | {probe_cnt.days_total} |\n"
      f"| Skipped — no data (market closed/holiday) | {probe_cnt.skipped_no_data} |\n"
      f"| Skipped — incomplete range window (minutes without ticks) | {probe_cnt.skipped_incomplete} |\n"
      f"| Days traded | {probe_cnt.traded_days} |\n")
    if probe_cnt.skipped_dates:
        w("Skipped dates: " + ", ".join(f"{d} ({why})" for d, why in probe_cnt.skipped_dates) + "\n")

    w("## 1. Base settings: Version A vs Version B\n")
    w("RR 4, SL 30 pips + spread, BE at 3R → entry + 5 pips. Full period:\n")
    w(stat_table({"Version A (6-bar extreme)": a["all"], "Version B (range level)": b["all"]}))
    w("\nIn-sample / out-of-sample split of the same runs:\n")
    w(stat_table({"A in-sample": a["is_"], "A out-of-sample": a["oos"],
                  "B in-sample": b["is_"], "B out-of-sample": b["oos"]}))
    w("\n![Base equity](charts/equity_base_A_vs_B.png)\n")
    w("### Order and re-entry counts\n")
    keys = [("traded_days", "Days with a valid range"), ("initial_expired", "06:00 orders expired unfilled at 11:00"),
            ("open_fill_0600", "06:00 level already crossed → filled at market"),
            ("reentry_considered", "SL/BE exits before 11:00 (re-entry candidates)"),
            ("reentry_skipped_time", "Re-entry skipped: 6-bar wait reaches 11:00"),
            ("reentry_skipped_invalid", "Re-entry skipped: price already beyond level (invalid stop)"),
            ("reentry_expired", "Re-entry orders expired unfilled"),
            ("reentry_filled", "Re-entry orders filled"),
            ("exit_after_11_no_reentry", "SL/BE exits at/after 11:00 (no re-entry)")]
    w("| | Version A | Version B |\n|---|---|---|")
    for k, name in keys:
        w(f"| {name} | {getattr(a['cnt'], k)} | {getattr(b['cnt'], k)} |")
    for v in ("A", "B"):
        lg = base[v]["log"]
        ov = (pd.to_datetime(lg.exit_time_ist).dt.date != pd.to_datetime(lg.entry_time_ist).dt.date).sum()
        w(f"\nVersion {v}: {ov} of {len(lg)} trades were held overnight (swap not modelled); "
          f"{(lg.exit_reason == 'OPEN_AT_END').sum()} still open at data end (marked to market); "
          f"{lg.gap_fill.sum()} entries filled at a gapped open.")
    w("\n### Breakdowns — base Version A\n")
    w(breakdowns(a["log"]))
    w("\n### Breakdowns — base Version B\n")
    w(breakdowns(b["log"]))

    w(f"\n## 2. Parameter sweep (Version A)\n")
    w(f"**{n_combos} combinations tested** (6 RR × 5 SL × 9 BE settings, minus combos with BE "
      f"trigger ≥ RR). Ranked by **in-sample t-stat of mean R** (SQN) only. With {n_combos} tries, "
      f"pure luck alone would be expected to produce a best t-stat of roughly "
      f"**{exp_max_t:.1f}** if every combo had zero edge (fewer effective tries because combos are "
      f"correlated, so call it 2.5–{exp_max_t:.1f}). A top combo below that is "
      f"indistinguishable from the luckiest of many coin-flippers.\n")
    w("Full table: `results/sweep_version_A.csv` (every combo × IS / OOS / full-period metrics).\n")
    show = res[["label", "is_trades", "is_win_rate", "is_avg_R", "is_profit_factor", "is_max_dd_pct",
                "is_net_return_pct", "is_sqn", "oos_trades", "oos_avg_R", "oos_profit_factor",
                "oos_net_return_pct"]].head(25).set_index("label")
    show.index.name = "Top 25 by in-sample t-stat"
    w(fmt_table(show))
    w("\n### Summary\n")
    w("Median across all combos sharing each value (in-sample for decisions; OOS shown only for context):\n")
    by_rr.index.name = "RR"
    by_sl.index.name = "SL pips"
    w(fmt_table(by_rr, ".3f"))
    w("")
    w(fmt_table(by_sl, ".3f"))
    w("\n**BE vs no BE** — each BE setting compared with BE off on the identical RR × SL cells:\n")
    be_cmp.index.name = "BE setting"
    w(fmt_table(be_cmp, ".3f"))
    w(f"\n![Heatmaps](charts/heatmaps_rr_x_sl.png)\n")
    w(f"Heatmap rows: BE off, and the best BE setting by paired in-sample improvement (**{best_be}**).\n")

    w("## 3. Top 5 (picked in-sample) tested out-of-sample\n")
    cols = {}
    for k, (lbl, d) in enumerate(top_detail.items(), 1):
        r = d["row"]
        cols[f"#{k} IS"] = {s: r[f"is_{s}"] for s, _, _ in STAT_ROWS}
        cols[f"#{k} OOS"] = {s: r[f"oos_{s}"] for s, _, _ in STAT_ROWS}
    w("| # | Combo | Flags |\n|---|---|---|")
    for k, lbl in enumerate(top_detail, 1):
        w(f"| {k} | `{lbl}` | {'; '.join(flags[lbl])} |")
    w("")
    w(stat_table(cols))
    w("\nFull-period stats of the top 5:\n")
    w(stat_table({f"#{k}": stats(d["log"], START_BAL, years_of(days))
                  for k, d in enumerate(top_detail.values(), 1)}))
    w("\n![Top 5 equity](charts/equity_top5.png)\n")
    w("### Plateau check (in-sample, same BE setting, adjacent RR and SL)\n")
    pl = plateau.set_index("top")
    pl.index.name = "Top combo"
    w(fmt_table(pl, ".3f"))
    first = next(iter(top_detail.values()))
    w(f"\n### Breakdowns — #1 `{first['p'].label}` (full period)\n")
    w(breakdowns(first["log"]))
    w("\n## 4. Verdict\n")
    vpath = f"{out}/verdict.md"      # hand-written after reading the numbers; kept across re-runs
    w(open(vpath).read() if os.path.exists(vpath) else "_Not written yet._\n")
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(rep))

    summary = dict(n_combos=n_combos, exp_max_t=exp_max_t, best_be=best_be,
                   split=str(split_ts.date()), base={v: {k: base[v][k] for k in ("all", "is_", "oos")}
                                                    for v in ("A", "B")},
                   counts={v: base[v]["cnt"].as_dict() for v in ("A", "B")},
                   top=[dict(label=l, flags=flags[l]) for l in top_detail])
    with open(f"{out}/summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
