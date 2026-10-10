"""Supply/demand zones on their own (no macro or trend filter): do they beat chance?

    python run_zone_alone.py [--seeds 1000] [--out results/zone_alone]

Same zones, entries, exits, costs, swap and one-position rule as run_zone_macro.py, with every
day allowed (both zone types). Same anti-overfitting protocol: rank the 24 combos on in-sample
only (average expectancy of both pairs, with swap, >= 100 in-sample trades in each pair), test
the top 5 out-of-sample, plateau check, flags.

Benchmark = random-entry placebo. For every real trade, a placebo trade with the same side, the
same stop distance and the same TP distance, entered at market (buys at ask, sells at bid) at
the close of a random 15m bar inside the SAME zone's life (from the impulse close to the 50-bar
expiry), exits simulated with the same engine. So the placebo knows exactly what the zone knew
(its existence and direction) and only the timing of the entry differs: the touch vs a random
moment. 1000 seeds. If waiting for the zone touch carries information, real trades should beat
most placebo seeds. Compared without swap (swap does not depend on the entry point).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import run_zone_macro as R
from zonemacro import engine as E
from zonemacro import prices as P
from zonemacro import sources as S
from zonemacro.charts import equity_on_grid, plot_combo
from zonemacro.report import md

SERIES = {"zones": ("#2a78d6", "Zones (no filter)")}


def placebo(m: E.M15, t: pd.DataFrame, seeds: int, split_ns: int, grid_ns: np.ndarray):
    """Random-entry placebo for the taken trades t. Returns (per-seed stats rows, equity paths)."""
    side = t["side"].to_numpy()
    R_ = t["R"].to_numpy()
    tpd = side * (t["tp"].to_numpy() - t["entry_price"].to_numpy())
    lo = t["zone_active_idx"].to_numpy()
    hi = np.maximum(t["zone_expiry_idx"].to_numpy(), lo + 1)
    rows, paths = [], np.zeros((seeds, len(grid_ns)))
    for seed in range(seeds):
        rng = np.random.default_rng(10_000 + seed)
        k = rng.integers(lo, hi)
        r = np.empty(len(t))
        xns = np.empty(len(t), np.int64)
        for j in range(len(t)):
            s, i = int(side[j]), int(k[j])
            entry = m.ac[i] if s > 0 else m.bc[i]
            xi, xp, _ = E.simulate_exit(m, s, entry - s * R_[j], entry + s * tpd[j], i, False)
            r[j] = s * (xp - entry) / R_[j]
            xns[j] = m.t[xi]
        ens = m.t[k]
        for period, mask in (("IS", ens < split_ns), ("OOS", ens >= split_ns), ("full", np.ones(len(t), bool))):
            x = r[mask]
            rows.append({"seed": seed, "period": period, "trades": len(x),
                         "expectancy_R": x.mean() if len(x) else np.nan,
                         "win_rate": (x > 0).mean() * 100 if len(x) else np.nan,
                         "net_return_pct": (np.prod(1 + 0.01 * x) - 1) * 100})
        paths[seed] = equity_on_grid(xns, r, grid_ns)
    return rows, paths


def controls(m: E.M15, t: pd.DataFrame, seeds: int = 200) -> list[dict]:
    """Sanity controls for the placebo, same stop/TP geometry as the real trades:
    random side at a uniformly random time (should be ~ minus costs), the zone's side and the
    opposite side at a random time inside the zone's life, and the zone's side at activation."""
    side = t["side"].to_numpy()
    R_ = t["R"].to_numpy()
    tpd = side * (t["tp"].to_numpy() - t["entry_price"].to_numpy())
    lo = t["zone_active_idx"].to_numpy()
    hi = np.maximum(t["zone_expiry_idx"].to_numpy(), lo + 1)

    def mean_r(k, sd):
        out = np.empty(len(t))
        for j in range(len(t)):
            s, i = int(sd[j]), int(k[j])
            e = m.ac[i] if s > 0 else m.bc[i]
            _, xp, _ = E.simulate_exit(m, s, e - s * R_[j], e + s * tpd[j], i, False)
            out[j] = s * (xp - e) / R_[j]
        return out.mean()

    acc = {"random side, uniform random time": [], "zone side, random time in zone life": [],
           "opposite side, random time in zone life": []}
    for seed in range(seeds):
        rng = np.random.default_rng(50_000 + seed)
        k = rng.integers(lo, hi)
        acc["zone side, random time in zone life"].append(mean_r(k, side))
        acc["opposite side, random time in zone life"].append(mean_r(k, -side))
        ku = rng.integers(1000, m.n - 5000, len(t))
        acc["random side, uniform random time"].append(mean_r(ku, rng.choice([-1, 1], len(t))))
    rows = [{"control": c, "mean_exp_R": float(np.mean(v)), "p5": float(np.percentile(v, 5)),
             "p95": float(np.percentile(v, 95)), "seeds": seeds} for c, v in acc.items()]
    rows.append({"control": "zone side, at zone activation", "mean_exp_R": mean_r(lo, side),
                 "p5": np.nan, "p95": np.nan, "seeds": 1})
    rows.append({"control": "real zone trades", "mean_exp_R": float(t["r"].mean()), "p5": np.nan,
                 "p95": np.nan, "seeds": 0})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--markup", type=float, default=0.5)
    ap.add_argument("--out", default="results/zone_alone")
    ap.add_argument("--report-only", action="store_true", help="rebuild REPORT.md from the CSVs")
    args = ap.parse_args()
    if args.report_only:
        o = args.out
        write_report(o, json.load(open(f"{o}/run.json")), pd.read_csv(f"{o}/sweep.csv"),
                     pd.read_csv(f"{o}/ranking.csv", index_col=0), pd.read_csv(f"{o}/plateau.csv"),
                     pd.read_csv(f"{o}/placebo.csv"), pd.read_csv(f"{o}/breakdowns.csv"),
                     pd.read_csv(f"{o}/counts.csv"))
        return
    t0 = time.time()
    os.makedirs(f"{args.out}/trade_logs", exist_ok=True)
    os.makedirs(f"{args.out}/charts", exist_ok=True)
    src = S.fetch_all()
    data = {p: R.load_pair(p, src, args.markup) for p in P.PAIRS}
    end = min(d["end"] for d in data.values())
    split = R.START + 0.6 * (end - R.START)
    split_ns = split.value
    iv_win = R.intervention_windows(src["MOF_INTERVENTION"])
    cands, zst = {}, {}
    for p, d in data.items():
        cands[p], zst[p] = R.pair_candidates(d, args.markup)
    print(f"candidates built ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- sweep, no filter
    rows, trades, counts = [], {}, []
    for combo in R.COMBOS:
        for p in P.PAIRS:
            t, cnt = R.run(cands[p][combo], data[p]["filters"]["none"].code)
            t["iv"] = R.in_windows(t, iv_win) if p == "USDJPY" else False
            trades[(combo, p)] = t
            counts.append({"combo": R.cname(combo), "pair": p, **zst[p][combo], **cnt})
            for period in ("IS", "OOS", "full"):
                pm = R.period_mask(t, period, split_ns)
                for swap in (True, False):
                    variants = [("all", pm)]
                    if p == "USDJPY":
                        variants.append(("ex_intervention", pm & ~t["iv"].to_numpy()))
                    for ivname, mask in variants:
                        s = E.stats(R.r_col(t[mask], swap))
                        rows.append({"combo": R.cname(combo), "K": combo[0], "zone": combo[1],
                                     "entry": combo[2], "exit": combo[3], "pair": p, "period": period,
                                     "swap": swap, "intervention": ivname, **s})
    sw = pd.DataFrame(rows)
    sw.to_csv(f"{args.out}/sweep.csv", index=False)
    cnt = pd.DataFrame(counts)
    cnt.to_csv(f"{args.out}/counts.csv", index=False)

    # ---------------- rank in-sample only
    def piv(period):
        x = sw[(sw.period == period) & sw.swap & (sw.intervention == "all")]
        return x.pivot_table(index="combo", columns="pair", values=["expectancy_R", "trades"])
    i, o = piv("IS"), piv("OOS")
    rank = pd.DataFrame({"IS_exp_USDJPY": i[("expectancy_R", "USDJPY")], "IS_exp_EURUSD": i[("expectancy_R", "EURUSD")],
                         "IS_n_USDJPY": i[("trades", "USDJPY")].astype(int), "IS_n_EURUSD": i[("trades", "EURUSD")].astype(int)})
    rank["IS_avg_exp"] = rank[["IS_exp_USDJPY", "IS_exp_EURUSD"]].mean(axis=1)
    rank["eligible_100_each"] = (rank.IS_n_USDJPY >= 100) & (rank.IS_n_EURUSD >= 100)
    rank["OOS_exp_USDJPY"] = o[("expectancy_R", "USDJPY")]
    rank["OOS_exp_EURUSD"] = o[("expectancy_R", "EURUSD")]
    rank["OOS_avg_exp"] = rank[["OOS_exp_USDJPY", "OOS_exp_EURUSD"]].mean(axis=1)
    rank["OOS_n_USDJPY"] = o[("trades", "USDJPY")].astype(int)
    rank["OOS_n_EURUSD"] = o[("trades", "EURUSD")].astype(int)
    rank = rank.sort_values(["eligible_100_each", "IS_avg_exp"], ascending=[False, False])
    top = list(rank.index[rank.eligible_100_each][:5])
    rank["top5"] = rank.index.isin(top)
    rank.to_csv(f"{args.out}/ranking.csv")
    by_name = {R.cname(c): c for c in R.COMBOS}

    plat = []
    for name in top:
        c = by_name[name]
        for k, opts in enumerate((R.KS, R.MODES, R.VERSIONS, R.EXITS)):
            for v in opts:
                if v == c[k] or (k == 0 and abs(R.KS.index(v) - R.KS.index(c[0])) != 1):
                    continue
                nb = list(c)
                nb[k] = v
                nn = R.cname(tuple(nb))
                plat.append({"top_combo": name, "neighbor": nn, "changed": ["K", "zone", "entry", "exit"][k],
                             "top_IS_avg_exp": rank.loc[name, "IS_avg_exp"],
                             "neighbor_IS_avg_exp": rank.loc[nn, "IS_avg_exp"],
                             "neighbor_IS_n_USDJPY": rank.loc[nn, "IS_n_USDJPY"],
                             "neighbor_IS_n_EURUSD": rank.loc[nn, "IS_n_EURUSD"]})
    plat = pd.DataFrame(plat)
    plat.to_csv(f"{args.out}/plateau.csv", index=False)
    print(f"sweep + ranking done ({time.time() - t0:.0f}s); top5 {top}", flush=True)

    # ---------------- placebo benchmark, base + top 5
    focus = [R.cname(R.BASE)] + [n for n in top if n != R.cname(R.BASE)]
    grid = pd.date_range(R.START, end, freq="MS").append(pd.DatetimeIndex([end]))
    grid_ns = grid.to_numpy().astype("datetime64[ns]").astype(np.int64)
    prow, bd, logs_all = [], [], []
    for name in focus:
        c = by_name[name]
        curves, bands, logs = {}, {}, []
        for p in P.PAIRS:
            t = trades[(c, p)]
            rows_p, paths = placebo(data[p]["m"], t, args.seeds, split_ns, grid_ns)
            for r in rows_p:
                prow.append({"combo": name, "pair": p, **r})
            curves[p] = {"zones": equity_on_grid(t["exit_ns"].to_numpy(), t["r"].to_numpy(), grid_ns)}
            bands[p] = tuple(np.percentile(paths, q, axis=0) for q in (5, 50, 95))
            lg = R.trade_log(t, data[p], p, "none", data[p]["filters"]["macro"], split_ns)
            logs.append(lg)
            print(f"  placebo {name} {p} ({time.time() - t0:.0f}s)", flush=True)
        tag = "base" if c == R.BASE else f"top{top.index(name) + 1}" if name in top else ""
        plot_combo(f"{args.out}/charts/equity_{name}.png",
                   f"{name} ({tag}) - zones alone vs random entries, no swap", curves, bands, grid, split,
                   series=SERIES, band_label="Random entry")
        log = pd.concat(logs, ignore_index=True).drop(columns=["filter"])
        log.to_csv(f"{args.out}/trade_logs/{name}.csv", index=False)
        log = log.assign(year=pd.to_datetime(log["entry_time"]).dt.year, combo=name)
        logs_all.append(log)
        for by in ("year", "pair", "side", "sample"):
            for key, g in log.groupby(by):
                s = E.stats(g["R_with_swap"].to_numpy())
                bd.append({"combo": name, "by": by, "key": key, **{k: s[k] for k in
                           ("trades", "win_rate", "expectancy_R", "profit_factor", "total_R")}})
    pr = pd.DataFrame(prow)
    pr.to_csv(f"{args.out}/placebo.csv", index=False)
    ctl = []
    for p in P.PAIRS:
        for r in controls(data[p]["m"], trades[(R.BASE, p)]):
            ctl.append({"combo": R.cname(R.BASE), "pair": p, **r})
    pd.DataFrame(ctl).to_csv(f"{args.out}/controls.csv", index=False)
    print(f"controls done ({time.time() - t0:.0f}s)", flush=True)
    bd = pd.DataFrame(bd)
    bd.to_csv(f"{args.out}/breakdowns.csv", index=False)
    run = {"start": str(R.START), "end": str(end), "split": str(split), "combos_tested": len(R.COMBOS),
           "top5": top, "focus": focus, "seeds": args.seeds, "markup_pct": args.markup,
           "runtime_s": round(time.time() - t0)}
    json.dump(run, open(f"{args.out}/run.json", "w"), indent=1)
    write_report(args.out, run, sw, rank, plat, pr, bd, cnt)
    print(f"done ({time.time() - t0:.0f}s)", flush=True)


def write_report(out, run, sw, rank, plat, pr, bd, cnt):
    focus, top = run["focus"], run["top5"]
    L = []
    A = L.append
    A("# Supply/demand zones alone: USDJPY and EURUSD\n")
    A(f"Period {run['start'][:10]} to {run['end'][:16]} UTC, in-sample to {run['split'][:10]} (60%), "
      f"out-of-sample after. **Combos tested: {run['combos_tested']} per pair.** No day filter: demand and "
      "supply zones every day. Same zones, entries, exits, costs, swap and one-position rule as the macro study.\n")
    A("Benchmark: random-entry placebo, same side / stop distance / TP distance, entered at a random 15m close "
      f"inside the same zone's life (impulse close to 50-bar expiry), {run['seeds']} seeds. Only the entry timing "
      "differs. Placebo comparisons are without swap.\n")
    A("## Verdict\n\n<!-- VERDICT -->\n")
    A("## In-sample ranking (no filter, with swap)\n")
    r = rank.reset_index().rename(columns={"index": "combo"})
    A(md(r[["combo", "IS_avg_exp", "IS_exp_USDJPY", "IS_n_USDJPY", "IS_exp_EURUSD", "IS_n_EURUSD",
            "eligible_100_each", "OOS_avg_exp", "OOS_exp_USDJPY", "OOS_n_USDJPY", "OOS_exp_EURUSD",
            "OOS_n_EURUSD"]], 3))
    A(f"\n{int(rank.eligible_100_each.sum())} of 24 eligible. Top {len(top)} (in-sample only): {', '.join(top)}.\n")
    A("### Top 5: in-sample vs out-of-sample\n")
    rows = []
    for n in top:
        x = rank.loc[n]
        f = ("OVERFIT: loses out-of-sample" if x.OOS_avg_exp <= 0 else
             "decays > 50%" if x.OOS_avg_exp < 0.5 * x.IS_avg_exp else "holds")
        if min(x.OOS_n_USDJPY, x.OOS_n_EURUSD) < 100:
            f += "; OOS n<100 in a pair"
        if (x[["OOS_exp_USDJPY", "OOS_exp_EURUSD"]] <= 0).any() and x.OOS_avg_exp > 0:
            f += "; negative OOS in one pair"
        rows.append({"combo": n, "IS_avg_exp": x.IS_avg_exp, "OOS_avg_exp": x.OOS_avg_exp,
                     "OOS_USDJPY": x.OOS_exp_USDJPY, "OOS_EURUSD": x.OOS_exp_EURUSD, "flag": f})
    A(md(pd.DataFrame(rows), 3))
    A("\n## Plateau check\n")
    for n in top:
        p = plat[plat.top_combo == n]
        me, nb = p.top_IS_avg_exp.iloc[0], p.neighbor_IS_avg_exp
        lab = ("no in-sample edge to check (IS <= 0)" if me <= 0 else
               "LIKELY NOISE" if (nb.median() <= 0 or nb.median() < 0.5 * me) else "plateau OK")
        A(f"**{n}** (IS {me:.3f}R): neighbour median {nb.median():.3f}R, {(nb > 0).sum()}/{len(nb)} positive -> {lab}\n")
        A(md(p[["neighbor", "changed", "neighbor_IS_avg_exp", "neighbor_IS_n_USDJPY", "neighbor_IS_n_EURUSD"]], 3))
        A("")
    A("\n## Base and top 5: zones vs random entries\n")
    A("pctl = share of placebo seeds the real zone trades beat on expectancy (no swap). 95+ would suggest the "
      "zone entry carries information.\n")
    rows = []
    for n in focus:
        for p in ("USDJPY", "EURUSD"):
            for per in ("IS", "OOS", "full"):
                s0 = sw[(sw.combo == n) & (sw.pair == p) & (sw.period == per) & ~sw.swap & (sw.intervention == "all")].iloc[0]
                s1 = sw[(sw.combo == n) & (sw.pair == p) & (sw.period == per) & sw.swap & (sw.intervention == "all")].iloc[0]
                q = pr[(pr.combo == n) & (pr.pair == p) & (pr.period == per)]
                rows.append({"combo": n, "pair": p, "period": per, "trades": int(s0.trades),
                             "win%": s0.win_rate, "PF": s0.profit_factor, "exp R": s0.expectancy_R,
                             "exp R +swap": s1.expectancy_R, "maxDD% +swap": s1.max_dd_pct,
                             "lose streak": int(s1.longest_losing_streak), "net % +swap": s1.net_return_pct,
                             "placebo p5": q.expectancy_R.quantile(.05), "placebo p50": q.expectancy_R.median(),
                             "placebo p95": q.expectancy_R.quantile(.95),
                             "pctl": (q.expectancy_R < s0.expectancy_R).mean() * 100,
                             "flags": ("n<100" if s0.trades < 100 else "") +
                                      (" TOO GOOD?" if s0.trades >= 30 and (s0.profit_factor > 3 or s0.win_rate > 75) else "")})
    A(md(pd.DataFrame(rows), 3))
    for n in focus:
        A(f"\n![{n}](charts/equity_{n}.png)\n")
    if os.path.exists(f"{out}/controls.csv"):
        A("\n## Placebo controls (base combo, no swap, same stop/TP geometry as the real trades)\n")
        A("Random side at random times shows the cost floor; the zone side vs the opposite side inside the "
          "zone's life shows what price does after the impulse.\n")
        A(md(pd.read_csv(f"{out}/controls.csv"), 3))
    A("\n## USDJPY with and without trades open within +/-3 trading days of MoF interventions (with swap)\n")
    x = sw[sw.combo.isin(focus) & (sw.pair == "USDJPY") & sw.swap]
    A(md(x.pivot_table(index=["combo", "period"], columns="intervention",
                       values=["trades", "expectancy_R"]).round(3).reset_index().set_axis(
        ["combo", "period", "exp all", "exp ex-intervention", "n all", "n ex-intervention"], axis=1), 3))
    A("\n## Breakdowns (with swap)\n")
    for by in ("pair", "side", "sample"):
        A(f"### by {by}\n")
        A(md(bd[bd.by == by][["combo", "key", "trades", "win_rate", "expectancy_R", "profit_factor", "total_R"]], 3))
        A("")
    A("### by year (expectancy R, trades)\n")
    y = bd[bd.by == "year"]
    tab = (y.pivot_table(index="key", columns="combo", values="expectancy_R").round(3).astype(str) + " ("
           + y.pivot_table(index="key", columns="combo", values="trades").fillna(0).astype(int).astype(str) + ")")
    A(md(tab.reset_index().rename(columns={"key": "year"})))
    A("\n### Version A vs B (all 24 combos, paired by K / zone / exit, with swap)\n")
    m = sw[sw.swap & (sw.intervention == "all") & (sw.period != "full")]
    pv = m.pivot_table(index=["K", "zone", "exit", "pair", "period"], columns="entry", values="expectancy_R").reset_index()
    pv["A_minus_B"] = pv["A"] - pv["B"]
    A(md(pv.groupby(["pair", "period"]).agg(mean_A=("A", "mean"), mean_B=("B", "mean"),
                                           mean_A_minus_B=("A_minus_B", "mean"),
                                           A_better=("A_minus_B", lambda s: int((s > 0).sum()))).reset_index(), 3))
    A("\n### All 24 combos x 2 pairs, expectancy with swap\n")
    A(md(sw[sw.swap & (sw.intervention == "all")].pivot_table(index=["combo", "pair"], columns="period",
                                                              values=["expectancy_R", "trades"]).round(3)
         .reset_index().set_axis(["combo", "pair", "exp IS", "exp OOS", "exp full", "n IS", "n OOS", "n full"],
                                 axis=1), 3))
    A("\n## Counts\n")
    cols = ["combo", "pair", "zones", "dead_expired_untouched", "dead_B_no_trigger_24h",
            "dead_B_closed_through_far_edge", "skipped_position_open", "stop_lt_2x_spread",
            "opposite_zone_tp_lt_1R", "tp_fallback_2R"]
    A(md(cnt[cols], 0))
    text = "\n".join(L)
    v = open(f"{out}/VERDICT.md").read() if os.path.exists(f"{out}/VERDICT.md") else "_(verdict pending)_"
    open(f"{out}/REPORT.md", "w").write(text.replace("<!-- VERDICT -->", v))


if __name__ == "__main__":
    main()
