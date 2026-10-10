"""Zones-alone and fade sweeps on ONE instrument (default XAUUSD).

    python run_single.py [--pair XAUUSD] [--seeds 1000] [--out results/xauusd]

Same rules, costs, engine and benchmarks as run_zone_alone.py (24 zone combos, random entries
inside each zone's life + controls) and run_fade.py (18 fade combos, random side at the same
moment + cost floor). One instrument, so ranking = in-sample expectancy (with swap) of that
instrument, >= 100 in-sample trades; top 5 tested out-of-sample; plateau check; flags.

Swap for XAUUSD: long gold earns the gold lease rate (taken as 0%) and pays the USD rate (fed
funds), minus the 0.5% p.a. markup on both sides; triple Wednesday.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import run_fade as F
import run_zone_alone as ZA
import run_zone_macro as R
from zonemacro import engine as E
from zonemacro import macro as MC
from zonemacro import prices as P
from zonemacro import sources as S
from zonemacro.charts import equity_on_grid, plot_combo
from zonemacro.report import md
from zonemacro.zones import atr_wilder

ZERO = pd.DataFrame({"date": [pd.Timestamp("2000-01-01")], "value": [0.0]})
SWAP_LEGS = {"XAUUSD": ("ZERO", "DFF")}          # (base, quote)


def load(pair: str, src: dict) -> dict:
    df = P.load_15m(pair)
    b4 = P.to_4h(df)
    atr4 = atr_wilder(b4["bh"].to_numpy(), b4["bl"].to_numpy(), b4["bc"].to_numpy())
    end = df.index[-1]
    day1 = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    b, q = SWAP_LEGS[pair]
    leg = lambda k: ZERO if k == "ZERO" else src[k]
    none = MC.no_filter(R.DAY0, day1)
    return {"pair": pair, "m": E.build_m15(df, b4, atr4), "b4": b4, "atr4": atr4, "end": end,
            "filters": {"none": none}, "none": none, "pip": P.PIP[pair], "gaps": P.data_gaps(df),
            "swap": E.build_swap(leg(b), leg(q), "2009-12-01", day1),
            "spread_median": float(np.median(df["ac"] - df["bc"])),
            "atr_median": float(np.nanmedian(atr4))}


def sweep(name, combos, cname, cands, d, split_ns):
    rows, trades, counts = [], {}, []
    for c in combos:
        t, cnt = R.run(cands[c], d["none"].code)
        t["iv"] = False                      # no intervention toggle outside the yen pairs
        trades[c] = t
        counts.append({"study": name, "combo": cname(c), **cnt})
        for period in ("IS", "OOS", "full"):
            pm = R.period_mask(t, period, split_ns)
            for swap in (True, False):
                s = E.stats(R.r_col(t[pm], swap))
                rows.append({"study": name, "combo": cname(c), "period": period, "swap": swap, **s})
    return pd.DataFrame(rows), trades, counts


def rank_and_plateau(sw, combos, cname, dims, dim_names):
    x = sw[sw.swap]
    piv = x.pivot_table(index="combo", columns="period", values=["expectancy_R", "trades"])
    rank = pd.DataFrame({"IS_exp": piv[("expectancy_R", "IS")], "IS_n": piv[("trades", "IS")].astype(int),
                         "OOS_exp": piv[("expectancy_R", "OOS")], "OOS_n": piv[("trades", "OOS")].astype(int),
                         "full_exp": piv[("expectancy_R", "full")], "full_n": piv[("trades", "full")].astype(int)})
    rank["eligible_100"] = rank.IS_n >= 100
    rank = rank.sort_values(["eligible_100", "IS_exp"], ascending=[False, False])
    top = list(rank.index[rank.eligible_100][:5])
    rank["top5"] = rank.index.isin(top)
    by = {cname(c): c for c in combos}
    plat = []
    for n in top:
        c = by[n]
        for k, opts in enumerate(dims):
            for v in opts:
                if v == c[k] or (k == 0 and abs(dims[0].index(v) - dims[0].index(c[0])) != 1):
                    continue
                nb = list(c)
                nb[k] = v
                nn = cname(tuple(nb))
                plat.append({"top_combo": n, "neighbor": nn, "changed": dim_names[k], "top_IS_exp": rank.loc[n, "IS_exp"],
                             "neighbor_IS_exp": rank.loc[nn, "IS_exp"], "neighbor_IS_n": rank.loc[nn, "IS_n"]})
    return rank, top, pd.DataFrame(plat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="XAUUSD")
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--markup", type=float, default=0.5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    pair = args.pair
    o = args.out or f"results/{pair.lower()}"
    t0 = time.time()
    os.makedirs(f"{o}/trade_logs", exist_ok=True)
    os.makedirs(f"{o}/charts", exist_ok=True)
    src = S.fetch_all()
    d = load(pair, src)
    end = d["end"]
    split = R.START + 0.6 * (end - R.START)
    split_ns = split.value
    grid = pd.date_range(R.START, end, freq="MS").append(pd.DatetimeIndex([end]))
    grid_ns = grid.to_numpy().astype("datetime64[ns]").astype(np.int64)
    zc, zst = R.pair_candidates(d, args.markup)
    fc, fst = F.pair_candidates(d, args.markup)
    print(f"candidates built ({time.time() - t0:.0f}s)", flush=True)

    studies = {
        "zones": dict(combos=R.COMBOS, cname=R.cname, cands=zc, st=zst, base=R.BASE,
                      dims=(R.KS, R.MODES, R.VERSIONS, R.EXITS), dim_names=["K", "zone", "entry", "exit"]),
        "fade": dict(combos=F.COMBOS, cname=F.cname, cands=fc, st=fst, base=F.BASE,
                     dims=(F.KS, F.ENTRIES, F.TARGETS), dim_names=["K", "entry", "target"]),
    }
    all_sw, all_rank, all_plat, all_bench, all_ctl, all_cnt, all_bd = [], [], [], [], [], [], []
    run = {"pair": pair, "start": str(R.START), "end": str(end), "split": str(split), "seeds": args.seeds,
           "markup_pct": args.markup, "spread_median": d["spread_median"], "atr4h_median": d["atr_median"],
           "gaps": {k: v for k, v in d["gaps"].items() if k != "gaps_ge_1h_list"}}
    for name, S_ in studies.items():
        sw, trades, counts = sweep(name, S_["combos"], S_["cname"], S_["cands"], d, split_ns)
        for c in counts:
            c.update({k: v for k, v in S_["st"][next(x for x in S_["combos"] if S_["cname"](x) == c["combo"])].items()})
        rank, top, plat = rank_and_plateau(sw, S_["combos"], S_["cname"], S_["dims"], S_["dim_names"])
        run[f"{name}_top5"] = top
        by = {S_["cname"](c): c for c in S_["combos"]}
        focus = [S_["cname"](S_["base"])] + [n for n in top if n != S_["cname"](S_["base"])]
        run[f"{name}_focus"] = focus
        for n in focus:
            t = trades[by[n]]
            if name == "zones":
                rows, paths = ZA.placebo(d["m"], t, args.seeds, split_ns, grid_ns)
                blabel, lab = "Random entry in zone life", "Zones (no filter)"
            else:
                rows, paths = F.random_side(d["m"], t, args.seeds, split_ns, grid_ns)
                blabel, lab = "Random side", "Fade the impulse"
            all_bench += [{"study": name, "combo": n, **r} for r in rows]
            curves = {pair: {"s": equity_on_grid(t["exit_ns"].to_numpy(), t["r"].to_numpy(), grid_ns)}}
            bands = {pair: tuple(np.percentile(paths, q, axis=0) for q in (5, 50, 95))}
            tag = "base" if by[n] == S_["base"] else f"top{top.index(n) + 1}"
            plot_combo(f"{o}/charts/{name}_{n}.png", f"{pair} {name}: {n} ({tag}) vs benchmark, no swap",
                       curves, bands, grid, split, series={"s": ("#2a78d6", lab)}, band_label=blabel)
            lg = R.trade_log(t, d, pair, "none", d["none"], split_ns).drop(
                columns=["filter", "macro_side", "macro_score", "intervention_window"], errors="ignore")
            if name == "fade":
                lg = lg.drop(columns=["tp_fallback_2R"]).rename(columns={"zone_size_pips": "impulse_beyond_base_pips"})
            lg.to_csv(f"{o}/trade_logs/{name}_{n}.csv", index=False)
            lg = lg.assign(year=pd.to_datetime(lg["entry_time"]).dt.year)
            for byk in ("year", "side", "sample"):
                for key, g in lg.groupby(byk):
                    s = E.stats(g["R_with_swap"].to_numpy())
                    all_bd.append({"study": name, "combo": n, "by": byk, "key": key,
                                   **{k: s[k] for k in ("trades", "win_rate", "expectancy_R", "profit_factor", "total_R")}})
            if by[n] == S_["base"]:
                if name == "zones":
                    all_ctl += [{"study": name, "combo": n, **r} for r in ZA.controls(d["m"], t)]
                else:
                    mu, lo, hi = F.cost_floor(d["m"], t)
                    all_ctl.append({"study": name, "combo": n, "control": "random side, uniform random time (cost floor)",
                                    "mean_exp_R": mu, "p5": lo, "p95": hi})
            print(f"  {name} {n} benchmark done ({time.time() - t0:.0f}s)", flush=True)
        all_sw.append(sw)
        all_rank.append(rank.assign(study=name))
        all_plat.append(plat.assign(study=name))
        all_cnt += counts
    pd.concat(all_sw).to_csv(f"{o}/sweep.csv", index=False)
    pd.concat(all_rank).to_csv(f"{o}/ranking.csv")
    pd.concat(all_plat).to_csv(f"{o}/plateau.csv", index=False)
    pd.DataFrame(all_bench).to_csv(f"{o}/benchmark.csv", index=False)
    pd.DataFrame(all_ctl).to_csv(f"{o}/controls.csv", index=False)
    pd.DataFrame(all_cnt).to_csv(f"{o}/counts.csv", index=False)
    pd.DataFrame(all_bd).to_csv(f"{o}/breakdowns.csv", index=False)
    run["runtime_s"] = round(time.time() - t0)
    json.dump(run, open(f"{o}/run.json", "w"), indent=1)
    write_report(o)
    print(f"done ({time.time() - t0:.0f}s)", flush=True)


def write_report(o: str) -> None:
    run = json.load(open(f"{o}/run.json"))
    sw, rank = pd.read_csv(f"{o}/sweep.csv"), pd.read_csv(f"{o}/ranking.csv", index_col=0)
    plat, bench = pd.read_csv(f"{o}/plateau.csv"), pd.read_csv(f"{o}/benchmark.csv")
    ctl, cnt, bd = pd.read_csv(f"{o}/controls.csv"), pd.read_csv(f"{o}/counts.csv"), pd.read_csv(f"{o}/breakdowns.csv")
    pair = run["pair"]
    L = []
    A = L.append
    A(f"# {pair}: supply/demand zones and impulse fade\n")
    A(f"Period {run['start'][:10]} to {run['end'][:16]} UTC, in-sample to {run['split'][:10]} (60%), out-of-sample after. "
      f"Median spread {run['spread_median']:.2f}, median 4H ATR {run['atr4h_median']:.2f} (price units). "
      "Same rules, engine, costs and benchmarks as the USDJPY/EURUSD studies. Ranking: in-sample expectancy "
      "with swap, >= 100 in-sample trades. This is a fresh search on this instrument: any winner is an in-sample "
      "pick and needs its own confirmation.\n")
    A("Swap: long gold pays fed funds + 0.5% p.a. markup (gold lease rate taken as 0%); short earns fed funds - 0.5%.\n")
    A("## Verdict\n\n<!-- VERDICT -->\n")
    for name, title, blabel in (("zones", "Zones alone (24 combos)", "random entry inside the same zone's life"),
                                ("fade", "Fade the impulse (18 combos)", "random side at the same moment")):
        A(f"## {title}\n")
        rk = rank[rank.study == name].drop(columns="study")
        A(md(rk.reset_index().rename(columns={"index": "combo"}), 3))
        top = run[f"{name}_top5"]
        A(f"\n{int(rk.eligible_100.sum())} of {len(rk)} eligible. Top {len(top)} (in-sample only): {', '.join(top)}.\n")
        rows = []
        for n in top:
            x = rk.loc[n]
            f = "OVERFIT: loses out-of-sample" if x.OOS_exp <= 0 else "decays > 50%" if x.OOS_exp < 0.5 * x.IS_exp else "holds"
            if x.OOS_n < 100:
                f += "; OOS n<100"
            rows.append({"combo": n, "IS_exp": x.IS_exp, "IS_n": x.IS_n, "OOS_exp": x.OOS_exp, "OOS_n": x.OOS_n, "flag": f})
        A("### Top 5: in-sample vs out-of-sample\n")
        A(md(pd.DataFrame(rows), 3))
        A("\n### Plateau check\n")
        pl = plat[plat.study == name]
        for n in top:
            p = pl[pl.top_combo == n]
            me, nb = p.top_IS_exp.iloc[0], p.neighbor_IS_exp
            lab = ("no in-sample edge to check (IS <= 0)" if me <= 0 else
                   "LIKELY NOISE" if (nb.median() <= 0 or nb.median() < 0.5 * me) else "plateau OK")
            A(f"**{n}** (IS {me:.3f}R): neighbour median {nb.median():.3f}R, {(nb > 0).sum()}/{len(nb)} positive -> {lab}\n")
            A(md(p[["neighbor", "changed", "neighbor_IS_exp", "neighbor_IS_n"]], 3))
            A("")
        A(f"### Base and top 5 vs benchmark ({blabel}, {run['seeds']} seeds, no swap)\n")
        rows = []
        for n in run[f"{name}_focus"]:
            for per in ("IS", "OOS", "full"):
                s0 = sw[(sw.study == name) & (sw.combo == n) & (sw.period == per) & ~sw.swap].iloc[0]
                s1 = sw[(sw.study == name) & (sw.combo == n) & (sw.period == per) & sw.swap].iloc[0]
                q = bench[(bench.study == name) & (bench.combo == n) & (bench.period == per)]
                rows.append({"combo": n, "period": per, "trades": int(s0.trades), "win%": s0.win_rate, "PF": s0.profit_factor,
                             "exp R": s0.expectancy_R, "exp R +swap": s1.expectancy_R, "maxDD% +swap": s1.max_dd_pct,
                             "lose streak": int(s1.longest_losing_streak), "net % +swap": s1.net_return_pct,
                             "t +swap": s1.t_stat, "bench p50": q.expectancy_R.median(), "bench p95": q.expectancy_R.quantile(.95),
                             "pctl": (q.expectancy_R < s0.expectancy_R).mean() * 100,
                             "flags": ("n<100" if s0.trades < 100 else "") +
                                      (" TOO GOOD?" if s0.trades >= 30 and (s0.profit_factor > 3 or s0.win_rate > 75
                                                                           or s0.expectancy_R > 1) else "")})
        A(md(pd.DataFrame(rows), 3))
        for n in run[f"{name}_focus"]:
            A(f"\n![{n}](charts/{name}_{n}.png)\n")
        c = ctl[ctl.study == name]
        if len(c):
            A("### Controls (base combo, same stop/target geometry, no swap)\n")
            A(md(c.drop(columns=["study"]), 3))
        A("\n### Breakdowns (with swap)\n")
        b = bd[bd.study == name]
        for byk in ("side", "sample"):
            A(md(b[b.by == byk][["combo", "by", "key", "trades", "win_rate", "expectancy_R", "profit_factor", "total_R"]], 3))
            A("")
        y = b[b.by == "year"]
        A("By year, expectancy R (trades):\n")
        tab = (y.pivot_table(index="key", columns="combo", values="expectancy_R").round(3).astype(str) + " ("
               + y.pivot_table(index="key", columns="combo", values="trades").fillna(0).astype(int).astype(str) + ")")
        A(md(tab.reset_index().rename(columns={"key": "year"})))
        A("\n### Counts\n")
        cc = cnt[cnt.study == name]
        cols = [k for k in ("combo", "zones", "impulses", "dead_expired_untouched", "dead_B_no_trigger_24h",
                            "dead_B_closed_through_far_edge", "no_confirmation", "skipped_position_open",
                            "stop_lt_2x_spread", "opposite_zone_tp_lt_1R", "tp_fallback_2R") if k in cc.columns]
        A(md(cc[cols], 0))
        A("")
    A("## Data gaps (15m bars missing in FX market hours; gold also has a daily 1h break, so this overstates gaps)\n")
    A(md(pd.DataFrame([run["gaps"]]), 0))
    text = "\n".join(L)
    v = open(f"{o}/VERDICT.md").read() if os.path.exists(f"{o}/VERDICT.md") else "_(verdict pending)_"
    open(f"{o}/REPORT.md", "w").write(text.replace("<!-- VERDICT -->", v))


if __name__ == "__main__":
    import sys
    if "--report-only" in sys.argv:
        write_report(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "results/xauusd")
    else:
        main()
