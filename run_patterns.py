"""Pattern search on one pair (default USDJPY) 2010-2026 beyond the box breakout.

Pre-declared grid (36 setups):
  P1 Tokyo fix, long into the 09:55 JST fix: entry 23:00 / 23:30 / 00:00 UTC x days all /
     gotobi / other                                                          (9)
  P1 Tokyo fix, short after the fix: exit 02:00 / 03:00 / 06:00 UTC x days all / gotobi / other (9)
  P2 previous-day high/low sweep reversal: 15m / 60m bars x TP 1R / 2R / prior-day mid  (6)
  P3 Asian range fade at London: 15m / 60m bars x TP range mid / opposite side        (4)
  P4 trend + pullback limit: k 0.25 / 0.5 ATR x SL 0.5 / 1 ATR x TP 1R / 2R             (8)
Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill (also charged on entries).
Periods: design 2010-2017, check 2018-2023, holdout 2024-2026.
Rule (fixed now): a setup survives if design avg R > 0 with t >= 2 AND check avg R > 0.
Holdout numbers are shown only for survivors.

    python run_patterns.py [--sym EURJPY]
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account, stats
from gjstrat.data import build_market
from gjstrat.patterns import asian_fade, daily_table, simulate, sweep_reversal, tokyo_fix, trend_pullback
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

SYM, OUT = "USDJPY", "results/patterns_usdjpy"
PERIODS = {"design": ("2010-01-01", "2017-12-31"), "check": ("2018-01-01", "2023-12-31"),
           "holdout": ("2024-01-01", "2026-12-31")}
M = D = SWAP = None


def grid():
    g = []
    for at in [(23, 0), (23, 30), (0, 0)]:
        for f in ("all", "gotobi", "other"):
            g.append((f"P1 fix-long {at[0]:02d}:{at[1]:02d}UTC {f}", "fix", dict(mode="pre", at=at, days_filter=f)))
    for at in [(2, 0), (3, 0), (6, 0)]:
        for f in ("all", "gotobi", "other"):
            g.append((f"P1 fix-short to {at[0]:02d}:00UTC {f}", "fix", dict(mode="post", at=at, days_filter=f)))
    for tf in (15, 60):
        for tp in ("1R", "2R", "mid"):
            g.append((f"P2 sweep {tf}m TP {tp}", "sweep", dict(tf=tf, tp=tp)))
    for tf in (15, 60):
        for tp in ("mid", "opposite"):
            g.append((f"P3 asian-fade {tf}m TP {tp}", "fade", dict(tf=tf, tp=tp)))
    for k in (0.25, 0.5):
        for sl in (0.5, 1.0):
            for rr in (1, 2):
                g.append((f"P4 pullback k{k:g} SL{sl:g}ATR RR{rr}", "pullback", dict(k_atr=k, sl_atr=sl, rr=rr)))
    return g


BUILDERS = {"fix": tokyo_fix, "sweep": sweep_reversal, "fade": asian_fade, "pullback": trend_pullback}


def evaluate(item):
    name, fam, kw = item
    sigs = BUILDERS[fam](M, D, **kw)
    trades = [t for t in (simulate(M, s) for s in sigs) if t is not None]
    rows = {"setup": name, "family": name.split()[0]}
    logs = {}
    for pname, (a, b) in PERIODS.items():
        ts = [t for t in trades if pd.Timestamp(a) <= t.day <= pd.Timestamp(b)]
        lg = account(ts, M, 10_000, risk_pct=0.5, commission=7, swap=SWAP, sym=SYM, slippage_pips=0.2)
        logs[pname] = lg
        r = lg["R"].to_numpy() if len(lg) else np.array([])
        s = stats(lg) if len(lg) else {}
        rows.update({f"{pname} trades": len(r), f"{pname} win %": (r > 0).mean() * 100 if len(r) else np.nan,
                     f"{pname} avg R": r.mean() if len(r) else np.nan, f"{pname} t": tstat(r),
                     f"{pname} max DD % (0.5%)": s.get("max_dd_pct", np.nan),
                     f"{pname} return % (0.5%)": s.get("net_return_pct", np.nan)})
    return rows, {k: v for k, v in logs.items()}


def main():
    global M, D, SWAP, SYM, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="USDJPY")
    SYM = ap.parse_args().sym
    OUT = f"results/patterns_{SYM.lower()}"
    os.makedirs(OUT, exist_ok=True)
    M = build_market(SYM, date(2010, 1, 1), date(2026, 10, 7), "data/raw",
                     f"data/{SYM.lower()}_2010-01-01_2026-10-07.npz")
    D = daily_table(M)
    D = D[D.index >= pd.Timestamp("2010-01-01")]
    SWAP = SwapModel.from_fred("rates", 1.0)
    g = grid()
    with Pool(os.cpu_count()) as pool:
        out = pool.map(evaluate, g)
    res = pd.DataFrame([r for r, _ in out]).set_index("setup")
    res["survives"] = (res["design avg R"] > 0) & (res["design t"] >= 2) & (res["check avg R"] > 0)
    for c in [c for c in res.columns if c.startswith("holdout")]:
        res.loc[~res.survives, c] = np.nan
    res.to_csv(f"{OUT}/grid.csv")
    for (name, _, _), (_, logs) in zip(g, out):
        if res.loc[name, "survives"]:
            pd.concat(logs.values()).to_csv(f"{OUT}/trades_{name.replace(' ', '_').replace(':', '')}.csv", index=False)

    cols = ["design trades", "design win %", "design avg R", "design t", "check trades", "check win %",
            "check avg R", "check t", "survives"]
    show = res[cols].sort_values("design t", ascending=False)
    surv = res[res.survives]
    rep = [f"# Pattern search — {SYM} 2010–2026 (beyond the box breakout)\n",
           "36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), "
           "0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 "
           "with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.\n",
           f"**Survivors: {len(surv)} of {len(res)}.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.\n",
           fmt_table(show, ".3f")]
    if len(surv):
        hcols = [c for c in res.columns if c.startswith(("design", "check", "holdout"))]
        rep += ["\n## Survivors: full numbers incl. holdout\n", fmt_table(surv[hcols].T, ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(show.round(3).to_string())
    if len(surv):
        print(surv[[c for c in res.columns if c.startswith("holdout")]].round(3).to_string())


if __name__ == "__main__":
    main()
