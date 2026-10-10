"""Out-of-sample test of the USDJPY impulse fade on the other JPY pairs, rules FROZEN.

    python run_jpy_crosses.py [--seeds 1000] [--out results/fade_jpy_crosses]

The rules were found on USDJPY 2010-2020 in run_fade.py and are not re-tuned here:
  primary   K3_close_2R  (impulse >= 3 x ATR, sell/buy at the impulse close, stop beyond the
                          impulse extreme + max(spread, 0.1 x ATR), target 2R)
  secondary K3_close_1R  (same, target 1R)
Fresh pairs: EURJPY, GBPJPY, AUDJPY, CADJPY, CHFJPY (NZDJPY has data only to 2012). USDJPY is
shown for reference but is NOT part of the test.

Pass criteria, fixed before running (primary rule, with swap, the 5 fresh pairs, 2010-2026):
  1. pooled expectancy > 0
  2. pooled fade beats >= 95% of random-side seeds (same moment, same stop and target, coin-flip
     direction, 1000 seeds)
  3. positive expectancy on at least 3 of the 5 pairs
Swap: base-currency policy rate minus the BoJ call rate, 0.5% p.a. markup, triple Wednesday.
Rates: ECB deposit rate (EUR, daily); FRED monthly overnight/interbank rates in rates/ for GBP,
AUD, CAD (IRSTCI01*) and CHF (IR3TIB01CHM156N); fed funds for USD.
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
from zonemacro import macro as MC
from zonemacro import prices as P
from zonemacro import sources as S
from zonemacro.charts import equity_on_grid, plot_grid
from zonemacro.fade import fade_candidates
from zonemacro.report import md
from zonemacro.zones import atr_wilder, find_zones

FRESH = ("EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY")
REFERENCE = ("USDJPY",)
RULES = {"K3_close_2R": (3.0, "close", "2R"), "K3_close_1R": (3.0, "close", "1R")}
PRIMARY = "K3_close_2R"
MONTHLY = {"GBP": "IRSTCI01GBM156N", "AUD": "IRSTCI01AUM156N", "CAD": "IRSTCI01CAM156N",
           "CHF": "IR3TIB01CHM156N"}


def base_rate(ccy: str, src: dict) -> pd.DataFrame:
    if ccy == "USD":
        return src["DFF"]
    if ccy == "EUR":
        return src["ECB_DFR"]
    df = pd.read_csv(f"rates/{MONTHLY[ccy]}.csv")
    return pd.DataFrame({"date": pd.to_datetime(df.iloc[:, 0]), "value": pd.to_numeric(df.iloc[:, 1], errors="coerce")}).dropna()


def load(pair: str, src: dict) -> dict:
    df = P.load_15m(pair)
    b4 = P.to_4h(df)
    atr4 = atr_wilder(b4["bh"].to_numpy(), b4["bl"].to_numpy(), b4["bc"].to_numpy())
    end = df.index[-1]
    day1 = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return {"pair": pair, "m": E.build_m15(df, b4, atr4), "b4": b4, "atr4": atr4, "end": end,
            "none": MC.no_filter(R.DAY0, day1), "gaps": P.data_gaps(df), "pip": P.PIP[pair],
            "swap": E.build_swap(base_rate(pair[:3], src), src["BOJ_CALL"], "2009-12-01", day1),
            "spread_median_pips": float(np.median(df["ac"] - df["bc"]) / P.PIP[pair])}


def trades_for(d: dict, rule, markup: float) -> pd.DataFrame:
    k, entry, target = rule
    m = d["m"]
    z, _ = find_zones(d["b4"], k, "full", atr=d["atr4"])
    c, _ = fade_candidates(m, d["b4"], z, d["atr4"], entry, target)
    c["entry_ns"] = m.t[c["entry_idx"].to_numpy()] + E.NS_15M
    ok = c["exit_idx"].to_numpy() >= 0
    c["exit_ns"] = np.where(ok, m.t[np.where(ok, c["exit_idx"].to_numpy(), 0)], 0)
    c["swap_r"] = 0.0
    if ok.any():
        c.loc[ok, "swap_r"] = d["swap"].swap_r(c.loc[ok, "side"].to_numpy(), c.loc[ok, "entry_ns"].to_numpy(),
                                                c.loc[ok, "exit_ns"].to_numpy(), c.loc[ok, "entry_price"].to_numpy(),
                                                c.loc[ok, "R"].to_numpy(), markup)
    c = c[c["entry_ns"] >= R.START.value].reset_index(drop=True)
    c["day"] = d["none"].day_index(m.t[c["entry_idx"].to_numpy()])
    t, cnt = R.run(c, d["none"].code)
    return t, cnt


def random_side(m: E.M15, t: pd.DataFrame, seeds: int, grid_ns: np.ndarray):
    """Per seed: sum and count of R (no swap) for the random-side twins, and an equity path."""
    idx, Rd = t["entry_idx"].to_numpy(), t["R"].to_numpy()
    tpd = t["side"].to_numpy() * (t["tp"].to_numpy() - t["entry_price"].to_numpy())
    sums, paths = np.zeros(seeds), np.zeros((seeds, len(grid_ns)))
    for seed in range(seeds):
        sd = np.random.default_rng(30_000 + seed).choice([-1, 1], len(t))
        r, xns = np.empty(len(t)), np.empty(len(t), np.int64)
        for j in range(len(t)):
            s, i = int(sd[j]), int(idx[j])
            e = m.ac[i] if s > 0 else m.bc[i]
            xi, xp, _ = E.simulate_exit(m, s, e - s * Rd[j], e + s * tpd[j], i, False)
            r[j], xns[j] = s * (xp - e) / Rd[j], m.t[xi]
        sums[seed] = r.sum()
        paths[seed] = equity_on_grid(xns, r, grid_ns)
    return sums, paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--markup", type=float, default=0.5)
    ap.add_argument("--out", default="results/fade_jpy_crosses")
    args = ap.parse_args()
    o = args.out
    t0 = time.time()
    os.makedirs(f"{o}/trade_logs", exist_ok=True)
    os.makedirs(f"{o}/charts", exist_ok=True)
    src = S.fetch_all()
    iv_win = R.intervention_windows(src["MOF_INTERVENTION"])
    pairs = FRESH + REFERENCE
    data = {p: load(p, src) for p in pairs}
    end = min(d["end"] for d in data.values())
    split = R.START + 0.6 * (end - R.START)
    grid = pd.date_range(R.START, end, freq="MS").append(pd.DatetimeIndex([end]))
    grid_ns = grid.to_numpy().astype("datetime64[ns]").astype(np.int64)
    print(f"data loaded ({time.time() - t0:.0f}s), end {end}", flush=True)

    rows, rnd, counts = [], [], []
    for name, rule in RULES.items():
        curves, bands, logs = {}, {}, []
        for p in pairs:
            d = data[p]
            t, cnt = trades_for(d, rule, args.markup)
            t["iv"] = R.in_windows(t, iv_win)
            counts.append({"rule": name, "pair": p, **cnt})
            e = t["entry_ns"].to_numpy()
            for period, pm in (("2010-2020 (IS for USDJPY)", e < split.value), ("2020-2026", e >= split.value),
                               ("full", np.ones(len(t), bool))):
                for swap in (True, False):
                    for ivname, mask in (("all", pm), ("ex_intervention", pm & ~t["iv"].to_numpy())):
                        s = E.stats(R.r_col(t[mask], swap))
                        rows.append({"rule": name, "pair": p, "fresh": p in FRESH, "period": period, "swap": swap,
                                     "intervention": ivname, "r_sum": float(R.r_col(t[mask], swap).sum()), **s})
            sums, paths = random_side(d["m"], t, args.seeds, grid_ns)
            rnd += [{"rule": name, "pair": p, "seed": k, "r_sum": sums[k], "trades": len(t)} for k in range(args.seeds)]
            label = p if p in FRESH else f"{p} (reference: rules found here)"
            curves[label] = equity_on_grid(t["exit_ns"].to_numpy(), R.r_col(t, True), grid_ns)
            bands[label] = tuple(np.percentile(paths, q, axis=0) for q in (5, 50, 95))
            lg = R.trade_log(t, d, p, "none", d["none"], split.value)
            logs.append(lg.drop(columns=["filter", "tp_fallback_2R", "macro_side", "macro_score", "sample"])
                        .rename(columns={"zone_size_pips": "impulse_beyond_base_pips"}))
            print(f"  {name} {p}: {len(t)} trades ({time.time() - t0:.0f}s)", flush=True)
        pd.concat(logs, ignore_index=True).to_csv(f"{o}/trade_logs/{name}.csv", index=False)
        plot_grid(f"{o}/charts/equity_{name}.png",
                  f"{name}, rules frozen from USDJPY: fade vs random side (with swap; band without swap)",
                  curves, bands, grid, None, "Fade (frozen USDJPY rules)", "Random side")
    sw = pd.DataFrame(rows)
    sw.to_csv(f"{o}/results.csv", index=False)
    rd = pd.DataFrame(rnd)
    rd.to_csv(f"{o}/random_side.csv", index=False)
    pd.DataFrame(counts).to_csv(f"{o}/counts.csv", index=False)
    run = {"start": str(R.START), "end": str(end), "split": str(split), "seeds": args.seeds, "markup_pct": args.markup,
           "fresh_pairs": FRESH, "reference": REFERENCE, "primary": PRIMARY,
           "gaps": {p: {k: v for k, v in d["gaps"].items() if k != "gaps_ge_1h_list"} for p, d in data.items()},
           "spread_median_pips": {p: d["spread_median_pips"] for p, d in data.items()},
           "runtime_s": round(time.time() - t0)}
    json.dump(run, open(f"{o}/run.json", "w"), indent=1)
    write_report(o)
    print(f"done ({time.time() - t0:.0f}s)", flush=True)


def write_report(o: str) -> None:
    run = json.load(open(f"{o}/run.json"))
    sw, rd, cnt = pd.read_csv(f"{o}/results.csv"), pd.read_csv(f"{o}/random_side.csv"), pd.read_csv(f"{o}/counts.csv")
    L = []
    A = L.append
    A("# Frozen USDJPY impulse fade, tested on the other JPY pairs\n")
    A(f"Period {run['start'][:10]} to {run['end'][:16]} UTC. Rules taken unchanged from the USDJPY fade study "
      f"(no re-tuning). Fresh pairs: {', '.join(run['fresh_pairs'])}. USDJPY shown for reference only. "
      f"Random-side benchmark: {run['seeds']} seeds, same moment, same stop and target, coin-flip direction, no swap.\n")
    A("**Pass criteria (fixed before running, primary rule K3_close_2R, with swap, fresh pairs, full period):** "
      "(1) pooled expectancy > 0; (2) pooled fade beats >= 95% of random-side seeds; (3) positive on >= 3 of 5 pairs.\n")
    A("## Verdict\n\n<!-- VERDICT -->\n")
    for rule in sw.rule.unique():
        A(f"## {rule}\n")
        f = sw[(sw.rule == rule) & (sw.period == "full") & (sw.intervention == "all")]
        rows = []
        for p in list(run["fresh_pairs"]) + list(run["reference"]):
            s1 = f[(f.pair == p) & f.swap].iloc[0]
            s0 = f[(f.pair == p) & ~f.swap].iloc[0]
            q = rd[(rd.rule == rule) & (rd.pair == p)]
            rexp = q.r_sum / q.trades
            rows.append({"pair": p + ("" if p in run["fresh_pairs"] else " (reference)"), "trades": int(s1.trades),
                         "win%": s1.win_rate, "PF": s1.profit_factor, "exp R +swap": s1.expectancy_R,
                         "exp R no swap": s0.expectancy_R, "maxDD%": s1.max_dd_pct,
                         "lose streak": int(s1.longest_losing_streak), "net %": s1.net_return_pct,
                         "rand p50": rexp.median(), "rand p95": rexp.quantile(.95),
                         "pctl vs random": (rexp < s0.expectancy_R).mean() * 100})
        fresh = f[f.fresh]
        n1 = fresh[fresh.swap].trades.sum()
        pooled1 = fresh[fresh.swap].r_sum.sum() / n1
        pooled0 = fresh[~fresh.swap].r_sum.sum() / fresh[~fresh.swap].trades.sum()
        q = rd[(rd.rule == rule) & rd.pair.isin(run["fresh_pairs"])].groupby("seed").agg(s=("r_sum", "sum"), n=("trades", "sum"))
        pexp = q.s / q.n
        pct = (pexp < pooled0).mean() * 100
        rows.append({"pair": "POOLED fresh pairs", "trades": int(n1), "win%": np.nan, "PF": np.nan,
                     "exp R +swap": pooled1, "exp R no swap": pooled0, "maxDD%": np.nan, "lose streak": 0,
                     "net %": np.nan, "rand p50": pexp.median(), "rand p95": pexp.quantile(.95), "pctl vs random": pct})
        A(md(pd.DataFrame(rows), 3))
        npos = int((fresh[fresh.swap].expectancy_R > 0).sum())
        c1, c2, c3 = pooled1 > 0, pct >= 95, npos >= 3
        A(f"\nCriteria: (1) pooled expectancy {pooled1:+.3f}R -> {'PASS' if c1 else 'FAIL'}; "
          f"(2) pooled percentile {pct:.1f} -> {'PASS' if c2 else 'FAIL'}; "
          f"(3) positive on {npos}/5 pairs -> {'PASS' if c3 else 'FAIL'}. "
          f"**{'ALL PASS' if (c1 and c2 and c3) else 'FAILS'}**" + (" (secondary rule, for information)" if rule != run["primary"] else "") + "\n")
        A(f"![{rule}](charts/equity_{rule}.png)\n")
        A("### By period (with swap)\n")
        x = sw[(sw.rule == rule) & sw.swap & (sw.intervention == "all")]
        A(md(x.pivot_table(index="pair", columns="period", values="expectancy_R").round(3).reset_index(), 3))
        A("\nTrades per period:\n")
        A(md(x.pivot_table(index="pair", columns="period", values="trades").reset_index(), 0))
        A("\n### With and without trades open within +/-3 trading days of MoF yen interventions (full, with swap)\n")
        y = sw[(sw.rule == rule) & sw.swap & (sw.period == "full")]
        A(md(y.pivot_table(index="pair", columns="intervention", values=["expectancy_R", "trades"]).round(3)
             .reset_index().set_axis(["pair", "exp all", "exp ex-intervention", "n all", "n ex-intervention"], axis=1), 3))
        A("")
    A("## Counts\n")
    A(md(cnt[["rule", "pair", "skipped_position_open", "stop_lt_2x_spread"]], 0))
    A("\n## Data\n")
    A(md(pd.DataFrame([{"pair": p, "median spread pips": run["spread_median_pips"][p], **g} for p, g in run["gaps"].items()]), 2))
    text = "\n".join(L)
    v = open(f"{o}/VERDICT.md").read() if os.path.exists(f"{o}/VERDICT.md") else "_(verdict pending)_"
    open(f"{o}/REPORT.md", "w").write(text.replace("<!-- VERDICT -->", v))


if __name__ == "__main__":
    import sys
    if "--report-only" in sys.argv:
        write_report(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "results/fade_jpy_crosses")
    else:
        main()
