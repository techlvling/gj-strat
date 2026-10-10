"""Fade the 4H impulse on USDJPY and EURUSD (rules in zonemacro/fade.py).

    python -m pytest tests/test_fade.py -q
    python run_fade.py [--seeds 1000] [--out results/fade]  [--report-only]

18 combos per pair: K (1.5, 2, 3) x entry (impulse close, confirmation candle) x target (1R, 2R,
base). No day filter. Same costs, swap, one-position rule and protocol as the zone studies:
rank on in-sample only (avg expectancy of both pairs, with swap, >= 100 in-sample trades in each
pair), top 5 out-of-sample, plateau check, flags.

Benchmark: random side at the same moment. For every real trade, a placebo with the same entry
bar, the same stop distance and the same target distance, but a coin-flip direction (buys at
ask, sells at bid). 1000 seeds. Tests whether the FADE DIRECTION carries information beyond
volatility and costs. Control: random side at uniformly random times (the cost floor).
"""
from __future__ import annotations

import argparse
import itertools
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
from zonemacro.fade import fade_candidates
from zonemacro.report import md
from zonemacro.zones import find_zones

KS = (1.5, 2.0, 3.0)
ENTRIES = ("close", "confirm")
TARGETS = ("1R", "2R", "base")
COMBOS = list(itertools.product(KS, ENTRIES, TARGETS))       # 18
BASE = (2.0, "close", "2R")
SERIES = {"fade": ("#2a78d6", "Fade the impulse")}


def cname(c) -> str:
    return f"K{c[0]:g}_{c[1]}_{c[2]}"


def pair_candidates(d: dict, markup: float):
    m, out, st = d["m"], {}, {}
    for k in KS:
        z, zs = find_zones(d["b4"], k, "full", atr=d["atr4"])
        for entry, target in itertools.product(ENTRIES, TARGETS):
            c, s = fade_candidates(m, d["b4"], z, d["atr4"], entry, target)
            c["entry_ns"] = m.t[c["entry_idx"].to_numpy()] + E.NS_15M        # at the bar's close
            ok = c["exit_idx"].to_numpy() >= 0
            c["exit_ns"] = np.where(ok, m.t[np.where(ok, c["exit_idx"].to_numpy(), 0)], 0)
            c["swap_r"] = 0.0
            if ok.any():
                c.loc[ok, "swap_r"] = d["swap"].swap_r(c.loc[ok, "side"].to_numpy(), c.loc[ok, "entry_ns"].to_numpy(),
                                                        c.loc[ok, "exit_ns"].to_numpy(), c.loc[ok, "entry_price"].to_numpy(),
                                                        c.loc[ok, "R"].to_numpy(), markup)
            c = c[c["entry_ns"] >= R.START.value].reset_index(drop=True)
            c["day"] = d["filters"]["none"].day_index(m.t[c["entry_idx"].to_numpy()])
            out[(k, entry, target)] = c
            st[(k, entry, target)] = {**zs, **s}
    return out, st


def _sim(m, side, i, Rd, tpd):
    e = m.ac[i] if side > 0 else m.bc[i]
    xi, xp, _ = E.simulate_exit(m, side, e - side * Rd, e + side * tpd, i, False)
    return side * (xp - e) / Rd, m.t[xi]


def random_side(m, t, seeds, split_ns, grid_ns):
    idx, Rd = t["entry_idx"].to_numpy(), t["R"].to_numpy()
    tpd = t["side"].to_numpy() * (t["tp"].to_numpy() - t["entry_price"].to_numpy())
    ens = t["entry_ns"].to_numpy()
    rows, paths = [], np.zeros((seeds, len(grid_ns)))
    for seed in range(seeds):
        sd = np.random.default_rng(20_000 + seed).choice([-1, 1], len(t))
        r, xns = np.empty(len(t)), np.empty(len(t), np.int64)
        for j in range(len(t)):
            r[j], xns[j] = _sim(m, int(sd[j]), int(idx[j]), Rd[j], tpd[j])
        for period, mask in (("IS", ens < split_ns), ("OOS", ens >= split_ns), ("full", np.ones(len(t), bool))):
            x = r[mask]
            rows.append({"seed": seed, "period": period, "trades": len(x),
                         "expectancy_R": x.mean() if len(x) else np.nan,
                         "net_return_pct": (np.prod(1 + 0.01 * x) - 1) * 100})
        paths[seed] = equity_on_grid(xns, r, grid_ns)
    return rows, paths


def cost_floor(m, t, seeds=200):
    Rd = t["R"].to_numpy()
    tpd = t["side"].to_numpy() * (t["tp"].to_numpy() - t["entry_price"].to_numpy())
    v = []
    for seed in range(seeds):
        rng = np.random.default_rng(60_000 + seed)
        k, sd = rng.integers(1000, m.n - 5000, len(t)), rng.choice([-1, 1], len(t))
        v.append(np.mean([_sim(m, int(sd[j]), int(k[j]), Rd[j], tpd[j])[0] for j in range(len(t))]))
    return float(np.mean(v)), float(np.percentile(v, 5)), float(np.percentile(v, 95))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--markup", type=float, default=0.5)
    ap.add_argument("--out", default="results/fade")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    o = args.out
    if args.report_only:
        write_report(o)
        return
    t0 = time.time()
    os.makedirs(f"{o}/trade_logs", exist_ok=True)
    os.makedirs(f"{o}/charts", exist_ok=True)
    src = S.fetch_all()
    data = {p: R.load_pair(p, src, args.markup) for p in P.PAIRS}
    end = min(d["end"] for d in data.values())
    split = R.START + 0.6 * (end - R.START)
    split_ns = split.value
    iv_win = R.intervention_windows(src["MOF_INTERVENTION"])
    cands, cst = {}, {}
    for p, d in data.items():
        cands[p], cst[p] = pair_candidates(d, args.markup)
    print(f"candidates built ({time.time() - t0:.0f}s)", flush=True)

    rows, trades, counts = [], {}, []
    for combo in COMBOS:
        for p in P.PAIRS:
            t, cnt = R.run(cands[p][combo], data[p]["filters"]["none"].code)
            t["iv"] = R.in_windows(t, iv_win) if p == "USDJPY" else False
            trades[(combo, p)] = t
            counts.append({"combo": cname(combo), "pair": p, **cst[p][combo],
                           **{k: v for k, v in cnt.items() if k not in ("filtered_by_bias", "tp_fallback_2R")}})
            for period in ("IS", "OOS", "full"):
                pm = R.period_mask(t, period, split_ns)
                for swap in (True, False):
                    variants = [("all", pm)]
                    if p == "USDJPY":
                        variants.append(("ex_intervention", pm & ~t["iv"].to_numpy()))
                    for ivname, mask in variants:
                        s = E.stats(R.r_col(t[mask], swap))
                        rows.append({"combo": cname(combo), "K": combo[0], "entry": combo[1], "target": combo[2],
                                     "pair": p, "period": period, "swap": swap, "intervention": ivname, **s})
    sw = pd.DataFrame(rows)
    sw.to_csv(f"{o}/sweep.csv", index=False)
    pd.DataFrame(counts).to_csv(f"{o}/counts.csv", index=False)

    def piv(period):
        x = sw[(sw.period == period) & sw.swap & (sw.intervention == "all")]
        return x.pivot_table(index="combo", columns="pair", values=["expectancy_R", "trades"])
    i, oo = piv("IS"), piv("OOS")
    rank = pd.DataFrame({"IS_exp_USDJPY": i[("expectancy_R", "USDJPY")], "IS_exp_EURUSD": i[("expectancy_R", "EURUSD")],
                         "IS_n_USDJPY": i[("trades", "USDJPY")].astype(int), "IS_n_EURUSD": i[("trades", "EURUSD")].astype(int)})
    rank["IS_avg_exp"] = rank[["IS_exp_USDJPY", "IS_exp_EURUSD"]].mean(axis=1)
    rank["eligible_100_each"] = (rank.IS_n_USDJPY >= 100) & (rank.IS_n_EURUSD >= 100)
    rank["OOS_exp_USDJPY"] = oo[("expectancy_R", "USDJPY")]
    rank["OOS_exp_EURUSD"] = oo[("expectancy_R", "EURUSD")]
    rank["OOS_avg_exp"] = rank[["OOS_exp_USDJPY", "OOS_exp_EURUSD"]].mean(axis=1)
    rank["OOS_n_USDJPY"] = oo[("trades", "USDJPY")].astype(int)
    rank["OOS_n_EURUSD"] = oo[("trades", "EURUSD")].astype(int)
    rank = rank.sort_values(["eligible_100_each", "IS_avg_exp"], ascending=[False, False])
    top = list(rank.index[rank.eligible_100_each][:5])
    rank["top5"] = rank.index.isin(top)
    rank.to_csv(f"{o}/ranking.csv")
    by_name = {cname(c): c for c in COMBOS}

    plat = []
    for name in top:
        c = by_name[name]
        for k, opts in enumerate((KS, ENTRIES, TARGETS)):
            for v in opts:
                if v == c[k] or (k == 0 and abs(KS.index(v) - KS.index(c[0])) != 1):
                    continue
                nb = list(c)
                nb[k] = v
                nn = cname(tuple(nb))
                plat.append({"top_combo": name, "neighbor": nn, "changed": ["K", "entry", "target"][k],
                             "top_IS_avg_exp": rank.loc[name, "IS_avg_exp"], "neighbor_IS_avg_exp": rank.loc[nn, "IS_avg_exp"],
                             "neighbor_IS_n_USDJPY": rank.loc[nn, "IS_n_USDJPY"], "neighbor_IS_n_EURUSD": rank.loc[nn, "IS_n_EURUSD"]})
    pd.DataFrame(plat).to_csv(f"{o}/plateau.csv", index=False)
    print(f"sweep + ranking done ({time.time() - t0:.0f}s); top5 {top}", flush=True)

    focus = [cname(BASE)] + [n for n in top if n != cname(BASE)]
    grid = pd.date_range(R.START, end, freq="MS").append(pd.DatetimeIndex([end]))
    grid_ns = grid.to_numpy().astype("datetime64[ns]").astype(np.int64)
    prow, bd, ctl = [], [], []
    for name in focus:
        c = by_name[name]
        curves, bands, logs = {}, {}, []
        for p in P.PAIRS:
            t = trades[(c, p)]
            rr, paths = random_side(data[p]["m"], t, args.seeds, split_ns, grid_ns)
            prow += [{"combo": name, "pair": p, **r} for r in rr]
            curves[p] = {"fade": equity_on_grid(t["exit_ns"].to_numpy(), t["r"].to_numpy(), grid_ns)}
            bands[p] = tuple(np.percentile(paths, q, axis=0) for q in (5, 50, 95))
            lg = R.trade_log(t, data[p], p, "none", data[p]["filters"]["macro"], split_ns)
            logs.append(lg.drop(columns=["filter", "tp_fallback_2R", "macro_side", "macro_score"])
                        .rename(columns={"zone_size_pips": "impulse_beyond_base_pips"}))
            if c == BASE:
                mu, lo, hi = cost_floor(data[p]["m"], t)
                ctl.append({"combo": name, "pair": p, "control": "random side, uniform random time (cost floor)",
                            "mean_exp_R": mu, "p5": lo, "p95": hi})
            print(f"  random-side {name} {p} ({time.time() - t0:.0f}s)", flush=True)
        tag = "base" if c == BASE else f"top{top.index(name) + 1}" if name in top else ""
        plot_combo(f"{o}/charts/equity_{name}.png", f"{name} ({tag}) - fade vs random side, no swap",
                   curves, bands, grid, split, series=SERIES, band_label="Random side")
        log = pd.concat(logs, ignore_index=True)
        log.to_csv(f"{o}/trade_logs/{name}.csv", index=False)
        log = log.assign(year=pd.to_datetime(log["entry_time"]).dt.year)
        for by in ("year", "pair", "side", "sample"):
            for key, g in log.groupby(by):
                s = E.stats(g["R_with_swap"].to_numpy())
                bd.append({"combo": name, "by": by, "key": key,
                           **{k: s[k] for k in ("trades", "win_rate", "expectancy_R", "profit_factor", "total_R")}})
    pd.DataFrame(prow).to_csv(f"{o}/random_side.csv", index=False)
    pd.DataFrame(bd).to_csv(f"{o}/breakdowns.csv", index=False)
    pd.DataFrame(ctl).to_csv(f"{o}/controls.csv", index=False)
    json.dump({"start": str(R.START), "end": str(end), "split": str(split), "combos_tested": len(COMBOS),
               "top5": top, "focus": focus, "seeds": args.seeds, "markup_pct": args.markup,
               "runtime_s": round(time.time() - t0)}, open(f"{o}/run.json", "w"), indent=1)
    write_report(o)
    print(f"done ({time.time() - t0:.0f}s)", flush=True)


def write_report(o: str) -> None:
    run = json.load(open(f"{o}/run.json"))
    sw, rank = pd.read_csv(f"{o}/sweep.csv"), pd.read_csv(f"{o}/ranking.csv", index_col=0)
    plat, pr = pd.read_csv(f"{o}/plateau.csv"), pd.read_csv(f"{o}/random_side.csv")
    bd, cnt, ctl = pd.read_csv(f"{o}/breakdowns.csv"), pd.read_csv(f"{o}/counts.csv"), pd.read_csv(f"{o}/controls.csv")
    focus, top = run["focus"], run["top5"]
    L = []
    A = L.append
    A("# Fade the 4H impulse: USDJPY and EURUSD\n")
    A(f"Period {run['start'][:10]} to {run['end'][:16]} UTC, in-sample to {run['split'][:10]} (60%), out-of-sample after. "
      f"**Combos tested: {run['combos_tested']} per pair** (K 1.5/2/3 x entry at impulse close / after a confirmation "
      "candle x target 1R / 2R / back to the base). No day filter. Same costs, swap and one-position rule as the zone studies.\n")
    A(f"Benchmark: random side at the same moment with the same stop and target distances, {run['seeds']} seeds "
      "(no swap). It tests whether the fade direction carries information beyond volatility and costs.\n")
    A("## Verdict\n\n<!-- VERDICT -->\n")
    A("## In-sample ranking (with swap)\n")
    r = rank.reset_index().rename(columns={"index": "combo"})
    A(md(r[["combo", "IS_avg_exp", "IS_exp_USDJPY", "IS_n_USDJPY", "IS_exp_EURUSD", "IS_n_EURUSD", "eligible_100_each",
            "OOS_avg_exp", "OOS_exp_USDJPY", "OOS_n_USDJPY", "OOS_exp_EURUSD", "OOS_n_EURUSD"]], 3))
    A(f"\n{int(rank.eligible_100_each.sum())} of {run['combos_tested']} eligible. Top {len(top)} (in-sample only): {', '.join(top)}.\n")
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
    A("\n## Base and top 5 vs random side\n")
    A("pctl = share of random-side seeds the real fade beats on expectancy (no swap).\n")
    rows = []
    for n in focus:
        for p in ("USDJPY", "EURUSD"):
            for per in ("IS", "OOS", "full"):
                s0 = sw[(sw.combo == n) & (sw.pair == p) & (sw.period == per) & ~sw.swap & (sw.intervention == "all")].iloc[0]
                s1 = sw[(sw.combo == n) & (sw.pair == p) & (sw.period == per) & sw.swap & (sw.intervention == "all")].iloc[0]
                q = pr[(pr.combo == n) & (pr.pair == p) & (pr.period == per)]
                rows.append({"combo": n, "pair": p, "period": per, "trades": int(s0.trades), "win%": s0.win_rate,
                             "avg win R": s0.avg_win_R, "avg loss R": s0.avg_loss_R, "PF": s0.profit_factor,
                             "exp R": s0.expectancy_R, "exp R +swap": s1.expectancy_R, "maxDD% +swap": s1.max_dd_pct,
                             "lose streak": int(s1.longest_losing_streak), "net % +swap": s1.net_return_pct,
                             "rand p5": q.expectancy_R.quantile(.05), "rand p50": q.expectancy_R.median(),
                             "rand p95": q.expectancy_R.quantile(.95), "pctl": (q.expectancy_R < s0.expectancy_R).mean() * 100,
                             "flags": ("n<100" if s0.trades < 100 else "") +
                                      (" TOO GOOD?" if s0.trades >= 30 and (s0.profit_factor > 3 or s0.win_rate > 75
                                                                           or s0.expectancy_R > 1) else "")})
    A(md(pd.DataFrame(rows), 3))
    for n in focus:
        A(f"\n![{n}](charts/equity_{n}.png)\n")
    A("\n## Cost floor control (base combo)\n")
    A(md(ctl, 3))
    A("\n## USDJPY with and without trades open within +/-3 trading days of MoF interventions (with swap)\n")
    x = sw[sw.combo.isin(focus) & (sw.pair == "USDJPY") & sw.swap]
    A(md(x.pivot_table(index=["combo", "period"], columns="intervention", values=["trades", "expectancy_R"]).round(3)
         .reset_index().set_axis(["combo", "period", "exp all", "exp ex-intervention", "n all", "n ex-intervention"], axis=1), 3))
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
    A("\n### Entry at impulse close vs after confirmation (paired by K / target, with swap)\n")
    m = sw[sw.swap & (sw.intervention == "all") & (sw.period != "full")]
    pv = m.pivot_table(index=["K", "target", "pair", "period"], columns="entry", values="expectancy_R").reset_index()
    pv["close_minus_confirm"] = pv["close"] - pv["confirm"]
    A(md(pv, 3))
    A("\n### All combos x 2 pairs, expectancy with swap\n")
    A(md(sw[sw.swap & (sw.intervention == "all")].pivot_table(index=["combo", "pair"], columns="period",
                                                              values=["expectancy_R", "trades"]).round(3)
         .reset_index().set_axis(["combo", "pair", "exp IS", "exp OOS", "exp full", "n IS", "n OOS", "n full"], axis=1), 3))
    A("\n## Counts\n")
    A(md(cnt[["combo", "pair", "impulses", "no_confirmation", "skipped_position_open", "stop_lt_2x_spread",
              "opposite_zone_tp_lt_1R"]].rename(columns={"opposite_zone_tp_lt_1R": "base_target_lt_1R"}), 0))
    text = "\n".join(L)
    v = open(f"{o}/VERDICT.md").read() if os.path.exists(f"{o}/VERDICT.md") else "_(verdict pending)_"
    open(f"{o}/REPORT.md", "w").write(text.replace("<!-- VERDICT -->", v))


if __name__ == "__main__":
    main()
