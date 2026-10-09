"""Zone + macro-bias backtest on USDJPY and EURUSD: 24-combo sweep, IS/OOS ranking, benchmarks.

    python -m pytest tests/test_zone_macro.py -q     # run first
    python run_zone_macro.py [--seeds 1000] [--markup 0.5] [--out results/zone_macro]

Outputs (results/zone_macro/): REPORT.md, sweep.csv, ranking.csv, plateau.csv, random_benchmark.csv,
breakdowns.csv, counts.csv, trade_logs/<combo>.csv, charts/*.png, run.json.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from zonemacro import engine as E
from zonemacro import macro as MC
from zonemacro import prices as P
from zonemacro import sources as S
from zonemacro.charts import equity_on_grid, plot_combo
from zonemacro.zones import atr_wilder, find_zones

START = pd.Timestamp("2010-01-01")
DAY0 = "2009-12-31"
KS = (1.5, 2.0, 3.0)
MODES = ("full", "body")
VERSIONS = ("A", "B")
EXITS = ("2R", "zone")
COMBOS = list(itertools.product(KS, MODES, VERSIONS, EXITS))      # 24
BASE = (2.0, "full", "A", "2R")
FILTERS = ("macro", "none", "trend")
SWAP_RATES = {"USDJPY": ("DFF", "BOJ_CALL"), "EURUSD": ("ECB_DFR", "DFF")}   # (base, quote)


def cname(c) -> str:
    k, mode, ver, ex = c
    return f"K{k:g}_{mode}_{ver}_{ex}"


# --------------------------------------------------------------------------- setup
def load_pair(pair: str, src: dict, markup: float):
    m15df = P.load_15m(pair)
    b4 = P.to_4h(m15df)
    atr4 = atr_wilder(b4["bh"].to_numpy(), b4["bl"].to_numpy(), b4["bc"].to_numpy())
    m = E.build_m15(m15df, b4, atr4)
    end = m15df.index[-1]
    bias = MC.macro_bias(src, pair, "2009-01-01", end.strftime("%Y-%m-%d"))
    day1 = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    filt = {"macro": MC.macro_filter(bias, pair, DAY0, day1),
            "none": MC.no_filter(DAY0, day1),
            "trend": MC.trend_filter(P.daily_closes(pair, m15df), DAY0, day1)}
    b, q = SWAP_RATES[pair]
    swap = E.build_swap(src[b], src[q], "2009-12-01", day1)
    return {"pair": pair, "m15df": m15df, "b4": b4, "atr4": atr4, "m": m, "bias": bias,
            "filters": filt, "swap": swap, "end": end, "gaps": P.data_gaps(m15df),
            "pip": P.PIP[pair]}


def pair_candidates(d: dict, markup: float):
    """All 24 combos' candidate trades for one pair (filter-independent)."""
    m, out, zstats = d["m"], {}, {}
    for k, mode in itertools.product(KS, MODES):
        z, zs = find_zones(d["b4"], k, mode, atr=d["atr4"])
        book = E.make_book(z, m)
        for ver, ex in itertools.product(VERSIONS, EXITS):
            c, st = E.candidates(m, book, ver, ex)
            c["entry_ns"] = m.t[c["entry_idx"].to_numpy()]
            if ver == "B":
                c["entry_ns"] += E.NS_15M                          # at the trigger candle's close
            ok = c["exit_idx"].to_numpy() >= 0
            xi = np.where(ok, c["exit_idx"].to_numpy(), 0)
            c["exit_ns"] = np.where(ok, m.t[xi], 0)
            c["swap_r"] = 0.0
            if ok.any():
                c.loc[ok, "swap_r"] = d["swap"].swap_r(c.loc[ok, "side"].to_numpy(),
                                                        c.loc[ok, "entry_ns"].to_numpy(),
                                                        c.loc[ok, "exit_ns"].to_numpy(),
                                                        c.loc[ok, "entry_price"].to_numpy(),
                                                        c.loc[ok, "R"].to_numpy(), markup)
            c = c[c["entry_ns"] >= START.value].reset_index(drop=True)
            c["day"] = d["filters"]["none"].day_index(m.t[c["entry_idx"].to_numpy()])
            out[(k, mode, ver, ex)] = c
            zstats[(k, mode, ver, ex)] = {**zs, **st}
    return out, zstats


# --------------------------------------------------------------------------- running
def run(c: pd.DataFrame, code: np.ndarray):
    taken, cnt = E.run_portfolio(c["entry_idx"].tolist(), c["exit_idx"].tolist(), c["side"].tolist(),
                                 c["skip"].tolist(), code[c["day"].to_numpy()].tolist())
    t = c.iloc[taken].copy()
    cnt["tp_fallback_2R"] = int(t["tp_fallback"].sum())
    return t, cnt


def intervention_windows(iv: pd.DataFrame, n: int = 3) -> list[tuple[int, int]]:
    """[d - n weekdays, d + n weekdays] for each MoF intervention day (UTC days, inclusive)."""
    bd = pd.offsets.BDay(n)
    out = []
    for d in iv["date"][iv["date"] >= "2010-01-01"]:
        lo, hi = d - bd, d + bd + pd.Timedelta(days=1)
        out.append((lo.value, hi.value))
    return out


def in_windows(t: pd.DataFrame, win) -> np.ndarray:
    m = np.zeros(len(t), bool)
    a, b = t["entry_ns"].to_numpy(), t["exit_ns"].to_numpy()
    for lo, hi in win:
        m |= (a < hi) & (b >= lo)
    return m


def r_col(t: pd.DataFrame, swap: bool) -> np.ndarray:
    return (t["r"] + t["swap_r"]).to_numpy() if swap else t["r"].to_numpy()


def period_mask(t: pd.DataFrame, period: str, split_ns: int) -> np.ndarray:
    e = t["entry_ns"].to_numpy()
    return {"IS": e < split_ns, "OOS": e >= split_ns, "full": np.ones(len(t), bool)}[period]


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--markup", type=float, default=0.5)
    ap.add_argument("--out", default="results/zone_macro")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(f"{args.out}/trade_logs", exist_ok=True)
    os.makedirs(f"{args.out}/charts", exist_ok=True)
    src = S.fetch_all()
    data = {p: load_pair(p, src, args.markup) for p in P.PAIRS}
    end = min(d["end"] for d in data.values())
    split = START + 0.6 * (end - START)
    split_ns = split.value
    iv_win = intervention_windows(src["MOF_INTERVENTION"])
    print(f"period {START.date()} .. {end}  split (60/40) at {split}", flush=True)

    cands, zst = {}, {}
    for p, d in data.items():
        cands[p], zst[p] = pair_candidates(d, args.markup)
        print(f"{p}: candidates built ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- every combo x pair x filter
    rows, trades, counts = [], {}, []
    for combo in COMBOS:
        for p in P.PAIRS:
            for f in FILTERS:
                t, cnt = run(cands[p][combo], data[p]["filters"][f].code)
                t["iv"] = in_windows(t, iv_win) if p == "USDJPY" else False
                trades[(combo, p, f)] = t
                counts.append({"combo": cname(combo), "pair": p, "filter": f, **zst[p][combo], **cnt})
                for period in ("IS", "OOS", "full"):
                    pm = period_mask(t, period, split_ns)
                    for swap in (True, False):
                        variants = [("all", pm)]
                        if p == "USDJPY":
                            variants.append(("ex_intervention", pm & ~t["iv"].to_numpy()))
                        for ivname, mask in variants:
                            s = E.stats(r_col(t[mask], swap))
                            rows.append({"combo": cname(combo), "K": combo[0], "zone": combo[1],
                                         "entry": combo[2], "exit": combo[3], "pair": p, "filter": f,
                                         "period": period, "swap": swap, "intervention": ivname, **s})
    sweep = pd.DataFrame(rows)
    sweep.to_csv(f"{args.out}/sweep.csv", index=False)
    pd.DataFrame(counts).to_csv(f"{args.out}/counts.csv", index=False)
    print(f"sweep done ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- rank on in-sample only (macro filter, with swap, all trades)
    sel = sweep[(sweep["filter"] == "macro") & (sweep["period"] == "IS") & sweep["swap"]
                & (sweep["intervention"] == "all")]
    piv = sel.pivot_table(index="combo", columns="pair", values=["expectancy_R", "trades"])
    rank = pd.DataFrame({"IS_exp_USDJPY": piv[("expectancy_R", "USDJPY")],
                         "IS_exp_EURUSD": piv[("expectancy_R", "EURUSD")],
                         "IS_n_USDJPY": piv[("trades", "USDJPY")].astype(int),
                         "IS_n_EURUSD": piv[("trades", "EURUSD")].astype(int)})
    rank["IS_avg_exp"] = rank[["IS_exp_USDJPY", "IS_exp_EURUSD"]].mean(1)
    rank["eligible_100_each"] = (rank["IS_n_USDJPY"] >= 100) & (rank["IS_n_EURUSD"] >= 100)
    rank = rank.sort_values(["eligible_100_each", "IS_avg_exp"], ascending=[False, False])
    top = [c for c in rank.index[rank["eligible_100_each"]][:5]]
    combo_by_name = {cname(c): c for c in COMBOS}
    oos = sweep[(sweep["filter"] == "macro") & (sweep["period"] == "OOS") & sweep["swap"]
                & (sweep["intervention"] == "all")].pivot_table(index="combo", columns="pair",
                                                                values=["expectancy_R", "trades"])
    rank["OOS_exp_USDJPY"] = oos[("expectancy_R", "USDJPY")]
    rank["OOS_exp_EURUSD"] = oos[("expectancy_R", "EURUSD")]
    rank["OOS_avg_exp"] = rank[["OOS_exp_USDJPY", "OOS_exp_EURUSD"]].mean(1)
    rank["OOS_n_USDJPY"] = oos[("trades", "USDJPY")].astype(int)
    rank["OOS_n_EURUSD"] = oos[("trades", "EURUSD")].astype(int)
    rank["top5"] = rank.index.isin(top)
    rank.to_csv(f"{args.out}/ranking.csv")

    # ---------------- plateau check
    plat = []
    for name in top:
        c = combo_by_name[name]
        for i, opts in enumerate((KS, MODES, VERSIONS, EXITS)):
            for o in opts:
                if o == c[i]:
                    continue
                if i == 0 and abs(KS.index(o) - KS.index(c[0])) != 1:
                    continue
                nb = list(c)
                nb[i] = o
                nn = cname(tuple(nb))
                plat.append({"top_combo": name, "neighbor": nn, "changed": ["K", "zone", "entry", "exit"][i],
                             "top_IS_avg_exp": rank.loc[name, "IS_avg_exp"],
                             "neighbor_IS_avg_exp": rank.loc[nn, "IS_avg_exp"],
                             "neighbor_IS_n_USDJPY": rank.loc[nn, "IS_n_USDJPY"],
                             "neighbor_IS_n_EURUSD": rank.loc[nn, "IS_n_EURUSD"]})
    plat = pd.DataFrame(plat)
    plat.to_csv(f"{args.out}/plateau.csv", index=False)

    # ---------------- random benchmark (base + top 5)
    focus = [cname(BASE)] + [n for n in top if n != cname(BASE)]
    grid = pd.date_range(START, end, freq="MS").append(pd.DatetimeIndex([end]))
    grid_ns = grid.to_numpy().astype("datetime64[ns]").astype(np.int64)
    rnd, paths = random_benchmark(data, cands, [combo_by_name[n] for n in focus], args.seeds,
                                  split_ns, (START, end), grid_ns)
    rnd.to_csv(f"{args.out}/random_benchmark.csv", index=False)
    print(f"random benchmark done ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- trade logs, breakdowns, charts
    bd = []
    for name in focus:
        c = combo_by_name[name]
        logs = []
        for p in P.PAIRS:
            bias = data[p]["bias"]
            mf = data[p]["filters"]["macro"]
            for f in FILTERS:
                t = trades[(c, p, f)]
                logs.append(trade_log(t, data[p], p, f, mf, split_ns))
        log = pd.concat(logs, ignore_index=True)
        log.to_csv(f"{args.out}/trade_logs/{name}.csv", index=False)
        bd.append(breakdowns(log, name))
        curves, bands = {}, {}
        for p in P.PAIRS:
            curves[p] = {f: equity_on_grid(trades[(c, p, f)]["exit_ns"].to_numpy(),
                                           r_col(trades[(c, p, f)], True), grid_ns) for f in FILTERS}
            pp = paths[(name, p)]
            bands[p] = tuple(np.percentile(pp, q, axis=0) for q in (5, 50, 95))
        tag = "base" if c == BASE else f"top{top.index(name) + 1}" if name in top else ""
        plot_combo(f"{args.out}/charts/equity_{name}.png",
                   f"{name} ({tag}) - equity with swap", curves, bands, grid, split)
    pd.concat(bd, ignore_index=True).to_csv(f"{args.out}/breakdowns.csv", index=False)
    json.dump({"start": str(START), "end": str(end), "split": str(split), "combos_tested": len(COMBOS),
               "top5": top, "focus": focus, "seeds": args.seeds, "markup_pct": args.markup,
               "gaps": {p: {k: v for k, v in d["gaps"].items() if k != "gaps_ge_1h_list"}
                        for p, d in data.items()},
               "intervention_days": [str(x.date()) for x in src["MOF_INTERVENTION"]["date"]
                                     if x >= pd.Timestamp("2010-01-01")],
               "runtime_s": round(time.time() - t0)}, open(f"{args.out}/run.json", "w"), indent=1)
    from zonemacro.report import write
    write(args.out)
    print(f"done ({time.time() - t0:.0f}s)", flush=True)


def trade_log(t: pd.DataFrame, d: dict, pair: str, f: str, mf: MC.DayFilter, split_ns: int) -> pd.DataFrame:
    pip = d["pip"]
    day = t["day"].to_numpy()
    return pd.DataFrame({
        "pair": pair, "filter": f,
        "date": pd.to_datetime(t["entry_ns"]).dt.date,
        "side": np.where(t["side"] > 0, "long", "short"),
        "entry_time": pd.to_datetime(t["entry_ns"]), "entry_price": t["entry_price"],
        "exit_time": pd.to_datetime(t["exit_ns"]), "exit_price": t["exit_price"],
        "zone_size_pips": t["zone_size"] / pip, "stop_dist_pips": t["R"] / pip,
        "R_result": t["r"], "swap_R": t["swap_r"], "R_with_swap": t["r"] + t["swap_r"],
        "exit_reason": t["reason"], "tp_fallback_2R": t["tp_fallback"],
        "macro_side": mf.code[day], "macro_score": mf.score[day],
        "sample": np.where(t["entry_ns"] < split_ns, "IS", "OOS"),
        "intervention_window": t["iv"]})


def breakdowns(log: pd.DataFrame, name: str) -> pd.DataFrame:
    out = []
    log = log.assign(year=pd.to_datetime(log["entry_time"]).dt.year)
    for by in ("year", "pair", "side", "macro_score", "sample"):
        for (f, key), g in log.groupby(["filter", by]):
            s = E.stats(g["R_with_swap"].to_numpy())
            out.append({"combo": name, "filter": f, "by": by, "key": key,
                        **{k: s[k] for k in ("trades", "win_rate", "expectancy_R", "profit_factor",
                                              "total_R")}})
    return pd.DataFrame(out)


def random_benchmark(data, cands, combos, seeds, split_ns, period, grid_ns):
    rows, paths = [], {}
    for p, d in data.items():
        bias = d["bias"]
        side = (bias["usd_bias"] * MC.USD_STRONG_SIDE[p])
        side = side[(side.index >= period[0] - pd.Timedelta(days=7)) & (side.index <= period[1])]
        props = np.array([(side == 1).mean(), (side == -1).mean(), (side == 0).mean()])
        cal = pd.date_range(DAY0, d["filters"]["none"].day0 + pd.Timedelta(days=len(d["filters"]["none"].code) - 1))
        dec_idx = np.searchsorted(side.index.values, (cal - pd.Timedelta(days=1)).values, side="right") - 1
        prep = []
        for c in combos:
            cc = cands[p][c]
            prep.append((c, cc["entry_idx"].tolist(), cc["exit_idx"].tolist(), cc["side"].tolist(),
                         cc["skip"].tolist(), cc["day"].to_numpy(),
                         (cc["r"] + cc["swap_r"]).to_numpy(), cc["entry_ns"].to_numpy(),
                         cc["exit_ns"].to_numpy()))
            paths[(cname(c), p)] = np.zeros((seeds, len(grid_ns)))
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            draw = rng.choice(np.array([1, -1, 0]), size=len(side), p=props / props.sum())
            code = np.where(dec_idx >= 0, draw[np.clip(dec_idx, 0, None)], 0)
            for c, ei, xi, sd, sk, day, r, ens, xns in prep:
                taken, _ = E.run_portfolio(ei, xi, sd, sk, code[day].tolist())
                rr, ee = r[taken], ens[taken]
                paths[(cname(c), p)][seed] = equity_on_grid(xns[taken], rr, grid_ns)
                for period_name, mask in (("IS", ee < split_ns), ("OOS", ee >= split_ns),
                                          ("full", np.ones(len(ee), bool))):
                    x = rr[mask]
                    rows.append({"combo": cname(c), "pair": p, "seed": seed, "period": period_name,
                                 "trades": len(x), "expectancy_R": x.mean() if len(x) else np.nan,
                                 "net_return_pct": (np.prod(1 + 0.01 * x) - 1) * 100})
        rows_props = {"buy": props[0], "sell": props[1], "none": props[2]}
        print(f"  random {p}: proportions {rows_props}", flush=True)
    return pd.DataFrame(rows), paths


if __name__ == "__main__":
    main()
