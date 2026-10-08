"""Dynamic risk for the prop challenge (USDJPY Version B, same rules as run_prop_sim.py).

Schemes fixed before any result:
  fixed 0.5% / fixed 1%                         baselines
  step-down   1% while down < 5% from the phase start, 0.5% at 5-8% down, 0.25% beyond 8%
  room / N    risk = (balance - 10% floor) / N, N = 10, 15, 20  (starts at 1%, 0.67%, 0.5%)
"Expected days to funded" assumes you restart right after a failure:
    (1 - p) / p x mean days of a failed attempt + mean days of a passed attempt

    python run_prop_dynamic.py
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from run_backtest import fmt_table
from run_prop_sim import challenge, prepare


def step_down(bal, floor, target):
    down = 1 - bal
    return 1.0 if down < 0.05 else 0.5 if down < 0.08 else 0.25


def room(n):
    return lambda bal, floor, target: max(bal - floor, 0) / n * 100


SCHEMES = {"fixed 0.5%": 0.5, "fixed 1%": 1.0, "step-down 1 / 0.5 / 0.25%": step_down,
           "room ÷ 10 (starts 1%)": room(10), "room ÷ 15 (starts 0.67%)": room(15),
           "room ÷ 20 (starts 0.5%)": room(20)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slippage", type=float, default=0.2)
    ap.add_argument("--out", default="results/prop_dynamic")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    m, trades, R, ny_day, ist_day, ev, bar_of_pos, starts = prepare(args.slippage)

    rows, detail = [], []
    for name, risk in SCHEMES.items():
        res = []
        for s in starts:
            r, phase, pos = challenge(ev, R, ny_day, ist_day, s, risk)
            days = (m.ts(bar_of_pos[pos]) - m.ts(trades[s].entry_i)).days
            res.append((r, phase, days, ist_day[s]))
        d = pd.DataFrame(res, columns=["result", "phase", "days", "start"])
        d["scheme"] = name
        detail.append(d)
        d = d[d.result != "unfinished"]
        for era, g in [("all", d), ("2018–2026", d[pd.to_datetime(d.start) >= pd.Timestamp("2018-01-01")])]:
            ok = g[g.result == "PASS"]
            p = len(ok) / len(g)
            mean_fail = g[g.result != "PASS"]["days"].mean()
            rows.append({"scheme": name, "starts": era, "challenges": len(g), "PASS %": p * 100,
                         "median days to pass": ok["days"].median(),
                         "median days to fail": g[g.result != "PASS"]["days"].median(),
                         "attempts per pass": 1 / p if p else np.inf,
                         "expected days to funded": (1 - p) / p * mean_fail + ok["days"].mean() if p else np.inf})
        print(f"{name} done", flush=True)
    allc = pd.concat(detail)
    allc.to_csv(f"{args.out}/challenges.csv", index=False)
    # fair comparison: every start with >= 12 months of data; stuck challenges count as not passed
    last = pd.to_datetime(allc.start).max() - pd.Timedelta(days=365)
    fair_rows = []
    for name, g in allc[pd.to_datetime(allc.start) <= last].groupby("scheme", sort=False):
        r = {"scheme": name, "challenges": len(g)}
        for T in (90, 180, 365):
            r[f"pass ≤{T}d %"] = ((g.result == "PASS") & (g.days <= T)).mean() * 100
        r["failed ≤365d %"] = (g.result.str.startswith("fail") & (g.days <= 365)).mean() * 100
        r["stuck >365d %"] = 100 - r["pass ≤365d %"] - r["failed ≤365d %"]
        fair_rows.append(r)
    fair = pd.DataFrame(fair_rows).set_index("scheme")
    fair.index.name = "Scheme"
    res = pd.DataFrame(rows).set_index(["starts", "scheme"])
    res.index = [f"{a} · {b}" for a, b in res.index]
    res.index.name = "Starts · scheme"
    rep = ["# Prop challenge: dynamic risk — USDJPY Version B\n",
           "Same rules as `results/prop_sim` (P1 +8%, P2 +6%, static 10%, daily 4%, ≥3 days, costs + "
           f"{args.slippage:g} pip slippage). Schemes fixed before any result (see run_prop_dynamic.py).\n",
           "## Fair comparison: passed within 3 / 6 / 12 months\n",
           "Every challenge started at least 12 months before the data ends. Use this table: the "
           "'room' schemes shrink risk toward zero instead of failing, so most of their challenges "
           "get stuck for years, and the plain pass % below (which drops unfinished challenges) "
           "flatters them.\n",
           fmt_table(fair, ".1f"),
           "\n## Raw table (unfinished challenges excluded — misleading for 'room' schemes)\n",
           fmt_table(res, ".1f")]
    with open(f"{args.out}/REPORT.md", "w") as f:
        f.write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(res.round(1).to_string())


if __name__ == "__main__":
    main()
