"""Alpha hunt -> prop: add the verified new edges to the current prop baskets. Fixed before running.

VERIFIED EDGES (results/alpha_hunt/<slug>/, passed the charter bar and the verification round):
  index_meanrev  Nasdaq 100 (USATECHIDXUSD) MR6: buy the 15:55 NY close when Connors RSI(2) < 5 and
                 C > SMA200; exit at the first later close > SMA5 (cap 10 closes); SL 2 x ATR20 checked
                 minute by minute on bid/ask (run_alpha_index_meanrev.py). 61 trades 2014-2026, 0.35 a
                 month, 70% wins, avg R +0.235 after costs (design +0.433 t 2.28, check +0.073, holdout
                 +0.298). Trades with net R (NON_FX costs + 3%/yr financing) are read from
                 results/alpha_hunt/index_meanrev/trades.pkl, written by that script (rebuilt with its
                 run_minute() if the file is missing).
  Only one edge was verified, so "all edges together" is the same mix as the edge alone and is not
  repeated (the code adds "all together" rows automatically when EDGES has more than one entry).

MINUTE GRID: other-market trades join the USDJPY minute grid as namedtuples (day, entry_i, exit_i) with
entry_i = (entry UTC time - m_usdjpy.t0) in minutes (= entry_i + (m_other.t0 - m_usdjpy.t0), the
run_index_prop.py shift); checked with m_usdjpy.ts(entry_i) == entry time. day = the signal's local date.

A. ALPHA SWING $10k (gjstrat.prop.prop_table, run_m3_addon.ALPHA: P1 +10%, P2 +5%, 10% static, 5% daily,
   >= 3 trading days). Legs from run_m3_addon.build_legs() (all costs: $7/lot, swap, 0.2 pip slippage).
   basket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3% (the current Alpha basket).
   Pre-declared risk levels for each new edge: 0.5%, 1%, 2% per trade (each edge alone; all edges together
   at the same level per edge when there is more than one).
   Risk rules: normal risk, and boost x1.5 (run_prop_risk_rules.make_rule(boost=1.5): x1.5 while the
   phase's progress is below 40% of its target, every trade capped at 4%).
   Windows: challenges started 2011-2025 (all trades) and 2018-2025 (run_m3_addon.since(legs, 2018-01-01)).
   ACCEPTED (per risk rule and mix): months per funded account (avg days per finished attempt / 30.4 /
   pass eventually share) LOWER than the basket's AND pass eventually % NOT LOWER, in BOTH windows.
   Decision: an edge joins the Alpha basket at the level with the lowest months per funded account under
   boost x1.5 (mean of the two windows) among the levels accepted under BOTH risk rules; none -> no change.

B. BLUEBERRY INSTANT ELITE $2.5k (gjstrat.prop.instant_table, run_m3_addon.BLUE, 10% cushion kept).
   basket = vol-box 0.25% + vol-gotobi 1.5% + M-3 USDJPY 1%. Each new edge at 0.5%, 1%, 1.5% (cap 1.5%).
   Windows: accounts started 2011-2024 and 2018-2024 (last start 2024-10-07, 24-month horizon).
   ACCEPTED: avg paid in 24 months HIGHER and account lost within 24 months % NOT HIGHER than the basket,
   in BOTH windows. Decision: the accepted level with the highest avg paid in 24 months (starts 2018-2024).

Diagnostics only (not used for acceptance): pass <= 1/3/6 months %, fail <= 6 months %, fails by daily
limit %, median months to pass, max DD %; the edge on its own on the USDJPY grid; how many edge trades
are open at the same time as a 3% basket trade (vol-gotobi or M-3). Note: prop_table books the daily loss
at trade exits (realised), as in all earlier prop runs, so a multi-day index trade's open loss is not
marked to market.

COMPUTE: one market in memory at a time (build_legs loads USDJPY, then the other pairs one by one);
multiprocessing.Pool(2) over (risk rule, window, mix) jobs.

    python run_alpha_prop.py
    python run_alpha_prop.py byyear    # POST-HOC diagnostic added after the main run (not used for any
                                       # decision): Blueberry avg paid / lost by account start year, basket
                                       # vs + each edge at 1% and 1.5%; writes blueberry_by_year.csv and
                                       # appends a section to REPORT.md
"""
from __future__ import annotations

import os
import time
from collections import namedtuple
from multiprocessing import get_context

import numpy as np
import pandas as pd

from gjstrat.prop import instant_table, prop_table
from run_backtest import fmt_table
from run_edge_hunt import per_stats
from run_m3_addon import ALPHA, BLUE, build_legs, since
from run_prop_risk_rules import make_rule
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/prop"
Tr = namedtuple("Tr", "day entry_i exit_i")
EDGES = [dict(slug="index_meanrev", label="Nasdaq MR6", market="USATECHIDXUSD", variant="MR6", n_expected=61,
              desc="Nasdaq 100 MR6: RSI2 < 5 & C > SMA200, exit first close > SMA5 (cap 10), SL 2 x ATR20",
              trades_per_month=0.345)]
A_BASE = (0.25, 3, 0.5, 3, 0)          # vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 other five pairs
B_BASE = (0.25, 1.5, 0, 1, 0)
A_LEVELS = (0.5, 1, 2)
B_LEVELS = (0.5, 1, 1.5)
RULES = {"normal risk": None, "boost x1.5": dict(boost=1.5)}
A_WIN = {"starts 2011-2025": None, "starts 2018-2025": "2018-01-01"}
B_WIN = {"starts 2011-2024": None, "starts 2018-2024": "2018-01-01"}
M, LEGS, A_MIXES, B_MIXES = None, None, None, None


def edge_trades(e: dict, m) -> tuple[list, np.ndarray]:
    """The edge's trades moved onto the USDJPY minute grid, sorted by (exit_i, entry_i), with net R."""
    path = f"results/alpha_hunt/{e['slug']}/trades.pkl"
    if os.path.exists(path):
        T = pd.read_pickle(path)
    else:                                                     # rebuild (loads only the Nasdaq market)
        from run_alpha_index_meanrev import load_vix, run_minute
        vix, vmed = load_vix()
        T, _, _ = run_minute(e["market"], vix, vmed)
    g = T[(T.market == e["market"]) & (T.variant == e["variant"])].copy()
    g["ei"] = ((pd.DatetimeIndex(g.entry_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
    g["xi"] = ((pd.DatetimeIndex(g.exit_ts) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
    assert all(m.ts(i) == pd.Timestamp(t) for i, t in zip(g.ei, g.entry_ts)), "grid shift"
    assert all(m.ts(i) == pd.Timestamp(t) for i, t in zip(g.xi, g.exit_ts)), "grid shift"
    assert (g.xi > g.ei).all()
    g = g[(g.ei >= 0) & (g.xi < m.n)].sort_values(["xi", "ei"])
    if len(g) != e["n_expected"]:
        print(f"WARNING {e['label']}: {len(g)} trades, expected {e['n_expected']}", flush=True)
    return [Tr(pd.Timestamp(d), int(a), int(b)) for d, a, b in zip(g.day, g.ei, g.xi)], g.R.to_numpy(dtype=float)


def mixes(base: tuple, levels: tuple, tag: str) -> dict[str, tuple]:
    k = len(EDGES)
    out = {f"basket ({tag})": base + (0,) * k}
    for lv in levels:
        for j, e in enumerate(EDGES):
            out[f"+ {e['label']} {lv:g}%"] = base + tuple(lv if i == j else 0 for i in range(k))
        if k > 1:
            out[f"+ all {k} edges {lv:g}% each"] = base + (lv,) * k
    return out


def window_legs(start):
    return LEGS if start is None else since(LEGS, start)


def alpha_job(job):
    rule, window, mix = job
    t0 = time.time()
    kw = {} if RULES[rule] is None else {"scale": make_rule(**RULES[rule])}
    t = prop_table(M, window_legs(A_WIN[window]), {mix: A_MIXES[mix]}, **ALPHA, **kw)
    t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
    t.insert(0, "window", window)
    t.insert(0, "risk rule", rule)
    print(f"alpha | {rule} | {window} | {mix} | {time.time() - t0:.0f}s", flush=True)
    return t


def blue_job(job):
    window, mix = job
    t0 = time.time()
    t = instant_table(M, window_legs(B_WIN[window]), {mix: B_MIXES[mix]}, (0.10,), last_start="2024-10-07",
                      **BLUE).droplevel(0)
    t.insert(0, "window", window)
    print(f"blueberry | {window} | {mix} | {time.time() - t0:.0f}s", flush=True)
    return t


def overlap(edge_leg, legs) -> tuple[int, int]:
    """Edge trades open at the same time as a vol-gotobi (leg 1) or M-3 USDJPY (leg 3) trade; same NY exit
    day as one."""
    iv = [(t.entry_i, t.exit_i) for k in (1, 3) for t in legs[k][0]]
    a = np.array([x for x, _ in iv]); b = np.array([y for _, y in iv])
    ny = lambda i: (M.ts(i).tz_localize("UTC").tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize()
    exit_days = {ny(y) for y in b}
    n_open = sum(bool(((a < t.exit_i) & (b > t.entry_i)).any()) for t in edge_leg[0])
    n_day = sum(ny(t.exit_i) in exit_days for t in edge_leg[0])
    return n_open, n_day


def year_job(y):
    lg = since(LEGS, f"{y}-01-01")
    t = instant_table(M, lg, B_MIXES, (0.10,), last_start=min(f"{y}-12-31", "2024-10-07"), **BLUE).droplevel(0)
    t.insert(0, "start year", y)
    print(f"blueberry by year | {y}", flush=True)
    return t


def by_year():
    """POST-HOC: Blueberry results by account start year (see the docstring)."""
    global M, LEGS, B_MIXES
    M, LEGS = build_legs()
    LEGS = LEGS + [edge_trades(e, M) for e in EDGES]
    full = mixes(B_BASE, B_LEVELS, "vol-box 0.25% + vol-gotobi 1.5% + M-3 1%")
    keep = [list(full)[0]] + [k for k in full if k.endswith(" 1%") or k.endswith(" 1.5%") or k.endswith(" 1% each")
                              or k.endswith(" 1.5% each")]
    B_MIXES = {k: full[k] for k in keep}
    with get_context("fork").Pool(2) as pool:
        Y = pd.concat(pool.map(year_job, range(2011, 2025), chunksize=1))
    Y.index.name = "mix"
    Y.to_csv(f"{OUT}/blueberry_by_year.csv")
    short = {k: ("basket" if k.startswith("basket") else k[2:]) for k in B_MIXES}
    paid = Y.reset_index().pivot(index="start year", columns="mix", values="avg paid in 24 months $")[list(B_MIXES)]
    lost = Y.reset_index().pivot(index="start year", columns="mix", values="account lost within 24 months %")[list(B_MIXES)]
    paid.columns = [f"paid $: {short[c]}" for c in paid.columns]
    lost.columns = [f"lost %: {short[c]}" for c in lost.columns]
    tab = pd.concat([paid, lost], axis=1)
    tab.index = tab.index.astype(str)
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Post-hoc diagnostic: Blueberry by account start year\n\n"
                "Added after the main run to see where the Blueberry gain comes from; not used for any decision. "
                "Accounts started in each calendar year (2024: up to 2024-10-07), 24-month horizon, 10% cushion. "
                "paid $ = avg paid in 24 months; lost % = account lost within 24 months.\n\n" + fmt_table(tab, ".1f") + "\n")
    print(tab.round(1).to_string())


if __name__ == "__main__":
    import sys
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "byyear":
        by_year()
        sys.exit(0)
    t_start = time.time()
    M, LEGS = build_legs()
    edge_legs = [edge_trades(e, M) for e in EDGES]
    LEGS = LEGS + edge_legs
    A_MIXES = mixes(A_BASE, A_LEVELS, "vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%")
    B_MIXES = mixes(B_BASE, B_LEVELS, "vol-box 0.25% + vol-gotobi 1.5% + M-3 1%")
    a_base, b_base = list(A_MIXES)[0], list(B_MIXES)[0]

    # the edges on their own (on the USDJPY grid) + overlap with the 3% basket legs
    solo = []
    for e, (tr, r) in zip(EDGES, edge_legs):
        day = pd.DatetimeIndex([t.day for t in tr])
        w, lo = r[r > 0], r[r <= 0]
        l3 = r[np.asarray(day >= pd.Timestamp("2023-10-08"))]
        n_open, n_day = overlap((tr, r), LEGS)
        solo.append({"edge": e["label"], "trades": len(r), "trades/month": e["trades_per_month"],
                     "win %": (r > 0).mean() * 100, "avg win / avg loss": w.mean() / -lo.mean(),
                     "avg R": r.mean(), "t": tstat(r), **per_stats(r, day),
                     "last3y n": len(l3), "last3y avg R": l3.mean(),
                     "open with a 3% basket trade": n_open, "exit on a 3% basket trade's exit day": n_day})
    S = pd.DataFrame(solo).set_index("edge")
    print(S.round(3).to_string(), flush=True)

    a_jobs = [(rule, w, mix) for rule in RULES for w in A_WIN for mix in A_MIXES]
    b_jobs = [(w, mix) for w in B_WIN for mix in B_MIXES]
    with get_context("fork").Pool(2) as pool:
        A = pd.concat(pool.map(alpha_job, a_jobs, chunksize=1))
        B = pd.concat(pool.map(blue_job, b_jobs, chunksize=1))
    A.index.name = B.index.name = "mix"

    # A. acceptance
    def a_row(rule, w, mix):
        return A[(A["risk rule"] == rule) & (A.window == w)].loc[mix]
    acc = {}
    for rule in RULES:
        for mix in list(A_MIXES)[1:]:
            acc[(rule, mix)] = all(a_row(rule, w, mix)["months per funded account"] < a_row(rule, w, a_base)["months per funded account"]
                                   and a_row(rule, w, mix)["pass eventually %"] >= a_row(rule, w, a_base)["pass eventually %"]
                                   for w in A_WIN)
    A["Δ months per funded"] = [r["months per funded account"] - a_row(r["risk rule"], r.window, a_base)["months per funded account"]
                                for _, r in A.iterrows()]
    A["Δ pass eventually"] = [r["pass eventually %"] - a_row(r["risk rule"], r.window, a_base)["pass eventually %"]
                              for _, r in A.iterrows()]
    A["accepted"] = [None if mix == a_base else acc[(rule, mix)] for rule, mix in zip(A["risk rule"], A.index)]
    A.to_csv(f"{OUT}/alpha.csv")

    # B. acceptance
    def b_row(w, mix):
        return B[B.window == w].loc[mix]
    bacc = {mix: all(b_row(w, mix)["avg paid in 24 months $"] > b_row(w, b_base)["avg paid in 24 months $"]
                     and b_row(w, mix)["account lost within 24 months %"] <= b_row(w, b_base)["account lost within 24 months %"]
                     for w in B_WIN) for mix in list(B_MIXES)[1:]}
    B["Δ avg paid 24m $"] = [r["avg paid in 24 months $"] - b_row(r.window, b_base)["avg paid in 24 months $"] for _, r in B.iterrows()]
    B["Δ lost %"] = [r["account lost within 24 months %"] - b_row(r.window, b_base)["account lost within 24 months %"]
                     for _, r in B.iterrows()]
    B["accepted"] = [None if mix == b_base else bacc[mix] for mix in B.index]
    B.to_csv(f"{OUT}/blueberry.csv")

    # decisions (pre-declared)
    groups = [(e["label"], [f"+ {e['label']} {lv:g}%" for lv in A_LEVELS], [f"+ {e['label']} {lv:g}%" for lv in B_LEVELS])
              for e in EDGES]
    if len(EDGES) > 1:
        groups.append((f"all {len(EDGES)} edges", [f"+ all {len(EDGES)} edges {lv:g}% each" for lv in A_LEVELS],
                       [f"+ all {len(EDGES)} edges {lv:g}% each" for lv in B_LEVELS]))
    dec = []
    for name, amix, bmix in groups:
        ok = [x for x in amix if acc[("normal risk", x)] and acc[("boost x1.5", x)]]
        mpf = {x: np.mean([a_row("boost x1.5", w, x)["months per funded account"] for w in A_WIN]) for x in ok}
        a_pick = min(mpf, key=mpf.get) if ok else None
        bok = [x for x in bmix if bacc[x]]
        b_pick = max(bok, key=lambda x: b_row("starts 2018-2024", x)["avg paid in 24 months $"]) if bok else None
        dec.append({"addition": name,
                    "Alpha accepted (normal risk)": ", ".join(x.split()[-1] for x in amix if acc[("normal risk", x)]) or "none",
                    "Alpha accepted (boost x1.5)": ", ".join(x.split()[-1] for x in amix if acc[("boost x1.5", x)]) or "none",
                    "Alpha decision": f"add at {a_pick.split()[-1]}" if a_pick else "no change",
                    "Blueberry accepted": ", ".join(x.split()[-1] for x in bmix if bacc[x]) or "none",
                    "Blueberry decision": f"add at {b_pick.split()[-1]}" if b_pick else "no change"})
    D = pd.DataFrame(dec).set_index("addition")
    D.to_csv(f"{OUT}/decision.csv")

    acols = ["risk rule", "window", "challenges", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
             "fails by daily limit %", "pass eventually %", "median months to pass", "months per funded account",
             "Δ months per funded", "Δ pass eventually", "max DD %", "accepted"]
    bcols = ["window", "got ≥1 payout %", "days to first payout (median)", "avg paid in 12 months $", "avg paid in 24 months $",
             "avg per month $", "account lost within 24 months %", "Δ avg paid 24m $", "Δ lost %", "accepted"]
    scols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R", "design t",
             "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n", "last3y avg R",
             "open with a 3% basket trade", "exit on a 3% basket trade's exit day"]
    edges_txt = "\n".join(f"- `{e['slug']}`: {e['desc']}" for e in EDGES)
    txt = ["# Alpha hunt -> prop: verified edges added to the Alpha Swing and Blueberry baskets\n",
           "Rules, risk levels and acceptance are in the docstring of `run_alpha_prop.py` (fixed before running). "
           "All results after costs.\n",
           "## Edges added\n", edges_txt + "\n",
           "Only one edge was verified, so \"all edges together\" is the same mix as the edge alone.\n",
           "## Decision (pre-declared rule)\n", fmt_table(D), "\n",
           "## The edge on its own (on the USDJPY minute grid)\n",
           "trades/month from the edge report (per month with Nasdaq data). Overlap columns: trades open at the same time as a "
           "vol-gotobi or M-3 USDJPY trade, and trades exiting on the same NY day as one of them.\n",
           fmt_table(S[scols], ".3f"), "\n",
           "## A. Alpha Swing $10k (P1 +10%, P2 +5%, 10% static, 5% daily, >= 3 days)\n",
           f"Basket = {a_base[len('basket ('):-1]} (run_m3_addon.build_legs). New edge at 0.5%, 1%, 2%. Accepted if months per "
           "funded account is lower AND pass eventually % is not lower than the basket, in both windows (per risk rule). "
           "Δ = mix minus basket in the same rule and window.\n",
           fmt_table(A[acols], ".2f"), "\n",
           "## B. Blueberry Instant Elite $2.5k (10% cushion kept, 24-month horizon)\n",
           f"Basket = {b_base[len('basket ('):-1]}. New edge at 0.5%, 1%, 1.5%. Accepted if avg paid in 24 months is higher "
           "AND account lost within 24 months % is not higher, in both windows.\n",
           fmt_table(B[bcols], ".1f"), "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    print(A[acols].round(2).to_string()); print(B[bcols].round(1).to_string()); print(D.to_string())
    print(f"DONE {time.time() - t_start:.0f}s", flush=True)
