"""REPORT.md from the CSVs written by run_zone_macro.py.

    python -m zonemacro.report [results/zone_macro]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

PAIRS = ("USDJPY", "EURUSD")
FLAG_MIN_TRADES = 100


def _fmt(x, nd=2):
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "-"
        if np.isinf(x):
            return "inf"
        return f"{x:.{nd}f}"
    return str(x)


def md(df: pd.DataFrame, nd: int = 2) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(_fmt(r[c], nd) for c in cols) + " |")
    return "\n".join(out)


def flags(s: pd.Series) -> str:
    f = []
    if s["trades"] < FLAG_MIN_TRADES:
        f.append(f"n<{FLAG_MIN_TRADES}")
    if s["trades"] >= 30 and (s["profit_factor"] > 3 or s["win_rate"] > 75 or s["expectancy_R"] > 1):
        f.append("TOO GOOD?")
    return ", ".join(f)


def build(out: str) -> str:
    run = json.load(open(f"{out}/run.json"))
    sw = pd.read_csv(f"{out}/sweep.csv")
    rank = pd.read_csv(f"{out}/ranking.csv", index_col=0)
    plat = pd.read_csv(f"{out}/plateau.csv")
    rnd = pd.read_csv(f"{out}/random_benchmark.csv")
    bd = pd.read_csv(f"{out}/breakdowns.csv")
    cnt = pd.read_csv(f"{out}/counts.csv")
    focus, top = run["focus"], run["top5"]
    L = []
    A = L.append

    A("# Zone + macro-bias backtest: USDJPY and EURUSD\n")
    A(f"Period {run['start'][:10]} to {run['end'][:16]} UTC. In-sample = first 60% "
      f"(to {run['split'][:10]}), out-of-sample = last 40%. **Combos tested: {run['combos_tested']} per pair** "
      f"(3 K x 2 zone x 2 entry x 2 exit), each run with 3 day filters (macro, none, trend) plus "
      f"{run['seeds']} random-filter seeds for the base and top-5 combos. Swap markup {run['markup_pct']}% p.a.\n")
    A("All R figures include swap unless a table says otherwise. Ranking = in-sample, macro filter, "
      "with swap, average expectancy of the two pairs, >= 100 in-sample trades in EACH pair.\n")

    A("## Verdict\n\n<!-- VERDICT -->\n")

    # ---------------- ranking
    A("## In-sample ranking (macro filter)\n")
    r = rank.reset_index().rename(columns={"index": "combo"})
    r = r[["combo", "IS_avg_exp", "IS_exp_USDJPY", "IS_n_USDJPY", "IS_exp_EURUSD", "IS_n_EURUSD",
           "eligible_100_each", "OOS_avg_exp", "OOS_exp_USDJPY", "OOS_n_USDJPY", "OOS_exp_EURUSD",
           "OOS_n_EURUSD"]]
    A(md(r, 3))
    A(f"\n{int(rank['eligible_100_each'].sum())} of 24 combos have >= 100 in-sample trades in both pairs. "
      f"Top {len(top)} (chosen on in-sample only): {', '.join(top) or 'none'}.\n")
    A("OOS columns are shown for the record; nothing was selected with them.\n")

    # overfit flags
    A("### Top combos: in-sample vs out-of-sample\n")
    rows = []
    for name in top:
        x = rank.loc[name]
        verdict = []
        if x["OOS_avg_exp"] <= 0:
            verdict.append("OVERFIT: loses out-of-sample")
        elif x["OOS_avg_exp"] < 0.5 * x["IS_avg_exp"]:
            verdict.append("decays > 50% out-of-sample")
        if min(x["OOS_n_USDJPY"], x["OOS_n_EURUSD"]) < FLAG_MIN_TRADES:
            verdict.append("OOS n<100 in a pair")
        rows.append({"combo": name, "IS_avg_exp": x["IS_avg_exp"], "OOS_avg_exp": x["OOS_avg_exp"],
                     "OOS_USDJPY": x["OOS_exp_USDJPY"], "OOS_EURUSD": x["OOS_exp_EURUSD"],
                     "flag": "; ".join(verdict) or "holds"})
    A(md(pd.DataFrame(rows), 3) if rows else "No eligible combo.")

    # ---------------- plateau
    A("\n## Plateau check (neighbours differ by one setting, in-sample avg expectancy)\n")
    for name in top:
        p = plat[plat["top_combo"] == name]
        nb = p["neighbor_IS_avg_exp"]
        me = p["top_IS_avg_exp"].iloc[0]
        noise = me > 0 and (nb.median() <= 0 or nb.median() < 0.5 * me)
        label = ("no in-sample edge to check (IS <= 0)" if me <= 0
                 else "LIKELY NOISE" if noise else "plateau OK")
        A(f"**{name}** (IS {me:.3f}R): neighbour median {nb.median():.3f}R, "
          f"{(nb > 0).sum()}/{len(nb)} positive -> {label}\n")
        A(md(p[["neighbor", "changed", "neighbor_IS_avg_exp", "neighbor_IS_n_USDJPY",
                "neighbor_IS_n_EURUSD"]], 3))
        A("")

    # ---------------- main tables
    A("\n## Base and top-5: macro vs benchmarks\n")
    A("Random = median of the seeds; pctl = percentile of the macro filter's expectancy within the "
      "random-seed distribution (100 = better than every seed).\n")
    for name in focus:
        tag = "base" if name == "K2_full_A_2R" else "top-5"
        A(f"### {name} ({tag})\n")
        A(f"![equity](charts/equity_{name}.png)\n")
        for period in ("IS", "OOS", "full"):
            rows = []
            for pair in PAIRS:
                for swap in (True, False):
                    for f in ("macro", "none", "trend"):
                        s = sw[(sw.combo == name) & (sw.pair == pair) & (sw["filter"] == f)
                               & (sw.period == period) & (sw.swap == swap) & (sw.intervention == "all")].iloc[0]
                        rows.append({"pair": pair, "swap": "yes" if swap else "no", "filter": f,
                                     "trades": int(s.trades), "win%": s.win_rate, "avg win R": s.avg_win_R,
                                     "avg loss R": s.avg_loss_R, "PF": s.profit_factor,
                                     "exp R": s.expectancy_R, "maxDD%": s.max_dd_pct,
                                     "lose streak": int(s.longest_losing_streak),
                                     "net %": s.net_return_pct, "flags": flags(s)})
                    if swap:
                        q = rnd[(rnd.combo == name) & (rnd.pair == pair) & (rnd.period == period)]
                        mexp = rows[-3]["exp R"]
                        pct = (q["expectancy_R"] < mexp).mean() * 100 + (q["expectancy_R"] == mexp).mean() * 50
                        rows.append({"pair": pair, "swap": "yes", "filter": "random (median)",
                                     "trades": int(q.trades.median()), "win%": np.nan, "avg win R": np.nan,
                                     "avg loss R": np.nan, "PF": np.nan, "exp R": q.expectancy_R.median(),
                                     "maxDD%": np.nan, "lose streak": 0,
                                     "net %": q.net_return_pct.median(),
                                     "flags": f"p5 {q.expectancy_R.quantile(.05):.3f} / p95 "
                                              f"{q.expectancy_R.quantile(.95):.3f}; macro pctl {pct:.0f}"})
                if pair == "USDJPY":
                    for swap in (True, False):
                        s = sw[(sw.combo == name) & (sw.pair == pair) & (sw["filter"] == "macro")
                               & (sw.period == period) & (sw.swap == swap)
                               & (sw.intervention == "ex_intervention")].iloc[0]
                        rows.append({"pair": pair, "swap": "yes" if swap else "no",
                                     "filter": "macro ex-intervention", "trades": int(s.trades),
                                     "win%": s.win_rate, "avg win R": s.avg_win_R, "avg loss R": s.avg_loss_R,
                                     "PF": s.profit_factor, "exp R": s.expectancy_R, "maxDD%": s.max_dd_pct,
                                     "lose streak": int(s.longest_losing_streak), "net %": s.net_return_pct,
                                     "flags": flags(s)})
            A(f"**{period}**\n")
            A(md(pd.DataFrame(rows), 2))
            A("")

    # ---------------- random distribution summary
    A("\n## Random-filter distribution (with swap)\n")
    rows = []
    for name in focus:
        for pair in PAIRS:
            for period in ("IS", "OOS", "full"):
                q = rnd[(rnd.combo == name) & (rnd.pair == pair) & (rnd.period == period)]
                s = sw[(sw.combo == name) & (sw.pair == pair) & (sw["filter"] == "macro") & (sw.period == period)
                       & sw.swap & (sw.intervention == "all")].iloc[0]
                pct = (q.expectancy_R < s.expectancy_R).mean() * 100
                rows.append({"combo": name, "pair": pair, "period": period, "seeds": len(q),
                             "rand p5": q.expectancy_R.quantile(.05), "rand p50": q.expectancy_R.median(),
                             "rand p95": q.expectancy_R.quantile(.95), "macro exp R": s.expectancy_R,
                             "macro pctl": pct})
    A(md(pd.DataFrame(rows), 3))

    # ---------------- breakdowns
    A("\n## Breakdowns (with swap)\n")
    for by in ("pair", "side", "macro_score", "sample", "year"):
        A(f"### by {by}\n")
        x = bd[bd["by"] == by]
        if by == "year":
            x = x[x["filter"] == "macro"]
            piv = x.pivot_table(index="key", columns="combo", values="expectancy_R")
            n = x.pivot_table(index="key", columns="combo", values="trades")
            tab = piv.round(3).astype(str) + " (" + n.fillna(0).astype(int).astype(str) + ")"
            A("Macro filter, expectancy R (trades), both pairs pooled:\n")
            A(md(tab.reset_index().rename(columns={"key": "year"})))
        else:
            A(md(x[["combo", "filter", "key", "trades", "win_rate", "expectancy_R", "profit_factor",
                    "total_R"]], 3))
        A("")
    A("macro_score = how many of the 3 inputs agreed with the bias on the entry day (2 or 3); "
      "0 for no-filter/trend trades taken on macro no-trade days.\n")

    A("### Version A vs B (macro filter, in-sample and out-of-sample, avg of both pairs)\n")
    m = sw[(sw["filter"] == "macro") & sw.swap & (sw.intervention == "all") & (sw.period != "full")]
    g = m.groupby(["entry", "period"]).agg(trades=("trades", "sum"),
                                           mean_exp=("expectancy_R", "mean")).reset_index()
    A(md(g, 3))
    A("\nPaired by the other three settings (K, zone, exit), A minus B expectancy, macro filter:\n")
    piv = m.pivot_table(index=["K", "zone", "exit", "pair", "period"], columns="entry",
                        values="expectancy_R").reset_index()
    piv["A_minus_B"] = piv["A"] - piv["B"]
    A(md(piv.groupby(["pair", "period"])["A_minus_B"].describe()[["count", "mean", "50%", "min", "max"]]
         .reset_index(), 3))

    # ---------------- counts
    A("\n## Counts: zones, dead zones, skips, overlaps\n")
    c = cnt[cnt.combo.isin(focus)]
    cols = ["combo", "pair", "filter", "zones", "dead_expired_untouched", "dead_B_no_trigger_24h",
            "dead_B_closed_through_far_edge", "filtered_by_bias", "skipped_position_open",
            "stop_lt_2x_spread", "opposite_zone_tp_lt_1R", "tp_fallback_2R"]
    A(md(c[cols], 0))
    A("\nAll 24 combos (macro filter), totals over both pairs:\n")
    t = cnt[cnt["filter"] == "macro"].groupby("combo")[cols[3:]].sum().reset_index()
    A(md(t, 0))
    A("\nZone formation (same for every entry/exit, per pair and K): bases found, runs of 4+ "
      "small candles ignored, ambiguous (both directions on one candle), no impulse.\n")
    z = cnt[(cnt["filter"] == "macro")].drop_duplicates(["pair", "combo"])
    z = z[z.combo.str.endswith("_A_2R")][["combo", "pair", "bases", "long_runs_ignored", "ambiguous",
                                          "no_impulse", "zones"]]
    A(md(z, 0))
    A("\n### Data gaps (15m bars missing inside market hours Sun 22:00 - Fri 21:00 UTC)\n")
    A(md(pd.DataFrame([{"pair": p, **v} for p, v in run["gaps"].items()]), 0))
    A("\n### Yen intervention days used (MoF data, 2010+)\n")
    A(", ".join(run["intervention_days"]))
    A("")
    return "\n".join(L)


def write(out: str, verdict: str | None = None) -> None:
    text = build(out)
    if verdict is None and os.path.exists(f"{out}/VERDICT.md"):
        verdict = open(f"{out}/VERDICT.md").read()
    text = text.replace("<!-- VERDICT -->", verdict or "_(verdict pending)_")
    open(f"{out}/REPORT.md", "w").write(text)


if __name__ == "__main__":
    write(sys.argv[1] if len(sys.argv) > 1 else "results/zone_macro")
