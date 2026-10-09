"""Daily trend following on all 28 FX pairs (7 majors + 21 minors), 2010-2026.

Pre-declared grid (7 portfolio tests), written before any result was seen:
  T1 time-series momentum: sign of the past 63 / 126 / 252-day return, rebalanced on each month's
     last trading day, held one month                                                     (3)
  T2 moving-average cross: long when SMA fast > SMA slow, else short; 50/200, 20/100       (2)
  T3 Donchian breakout: enter on a close beyond the prior 20 / 55-day closing channel,
     exit on the opposite 10 / 20-day channel, flat in between                            (2)
Every pair targets the same volatility (10% a year / sqrt(28)), sized by its 60-day stdev when
the position opens (T2, T3) or at each monthly rebalance (T1). Equal-risk portfolio of all pairs
with data that day. Costs: half spread + $7/lot + 0.2 pip slippage per unit traded; carry at
central-bank / interbank rates with a 1% a year markup (see gjstrat/trend.py).
Survival rule (as the pattern searches): design (2010-2017) daily-return t >= 2 AND check
(2018-2023) mean > 0. Holdout (2024-2026) shown only for survivors.

    python run_trend.py    # unpacks datastore/daily/candles.tar, downloads anything missing
"""
from __future__ import annotations

import argparse
import os
import tarfile

import numpy as np
import pandas as pd

from gjstrat.data import MAJORS, MINORS
from gjstrat.swap import SwapModel
from gjstrat.trend import (TRADING_DAYS, donchian, download_daily, load_daily, ma_cross, max_dd,
                           pair_returns, sharpe_t, tsmom_targets, weights)
from run_backtest import fmt_table
from run_patterns import PERIODS

PAIRS = MAJORS + MINORS
OUT = "results/trend"
STORE = "datastore/daily/candles.tar"
YEARS = range(2008, 2027)
PAIR_VOL = 0.10 / np.sqrt(len(PAIRS)) / np.sqrt(TRADING_DAYS)      # daily vol target per pair


def grid():
    g = [(f"T1 tsmom {lb}d monthly", "tsmom", dict(lookback=lb)) for lb in (63, 126, 252)]
    g += [(f"T2 ma-cross {f}/{s}", "ma", dict(fast=f, slow=s)) for f, s in ((50, 200), (20, 100))]
    g += [(f"T3 donchian {e}/{x}", "donchian", dict(entry=e, exit_=x)) for e, x in ((20, 10), (55, 20))]
    return g


def run_strategy(data, rates, fam, kw):
    per_pair = {}
    for sym, d in data.items():
        c = d["mid"]
        vol = c.pct_change().rolling(60).std()
        if fam == "tsmom":
            sig = tsmom_targets(c, kw["lookback"])
            me = c.index.to_series().groupby([c.index.year, c.index.month]).transform("max")
            w = weights(sig, vol, PAIR_VOL, resize_on=pd.Series(c.index == me.to_numpy(), index=c.index))
        elif fam == "ma":
            w = weights(ma_cross(c, kw["fast"], kw["slow"]), vol, PAIR_VOL)
        else:
            w = weights(donchian(c, kw["entry"], kw["exit_"]), vol, PAIR_VOL)
        per_pair[sym] = pair_returns(d, w, sym, rates)
    return per_pair


def period_stats(x: pd.DataFrame, a, b) -> dict:
    x = x[(x.index >= a) & (x.index <= b)]
    sr, t = sharpe_t(x.net)
    yrs = len(x) / TRADING_DAYS
    nm = x.net + x.markup
    return {"days": len(x), "ann ret %": x.net.sum() / yrs * 100, "sharpe": sr, "t": t,
            "ann vol %": x.net.std() * np.sqrt(TRADING_DAYS) * 100, "max DD %": max_dd(x.net) * 100,
            "gross %/yr": x.gross.sum() / yrs * 100, "cost %/yr": x.cost.sum() / yrs * 100,
            "carry %/yr": x.carry.sum() / yrs * 100, "markup %/yr": x.markup.sum() / yrs * 100,
            "no-markup ann ret %": nm.sum() / yrs * 100, "no-markup t": sharpe_t(nm)[1]}


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    OUT = ap.parse_args().out
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(STORE):                 # committed copy, so a new container skips the download
        os.makedirs("data/daily", exist_ok=True)
        with tarfile.open(STORE) as tar:
            tar.extractall("data/daily", members=[m for m in tar.getmembers()
                                                  if not os.path.exists(f"data/daily/{m.name}")], filter="data")
    download_daily(PAIRS, YEARS, "data/daily")
    data = load_daily(PAIRS, YEARS, "data/daily")
    rates = SwapModel.from_fred("rates", 1.0).rates
    cover = pd.DataFrame({s: {"first": d.index[0].date(), "last": d.index[-1].date(), "days": len(d)}
                          for s, d in data.items()}).T
    print(cover.to_string(), flush=True)

    rows, breadth = [], {}
    for name, fam, kw in grid():
        pp = run_strategy(data, rates, fam, kw)
        port = sum(p[["gross", "cost", "carry", "markup", "net"]] for p in pp.values()).fillna(0.0)
        port = port[port.index >= "2010-01-01"]
        row = {"setup": name}
        for pname, (a, b) in PERIODS.items():
            for k, v in period_stats(port, a, b).items():
                row[f"{pname} {k}"] = v
        rows.append(row)
        breadth[name] = {s: {f"{p} sharpe": sharpe_t(x.net[(x.index >= a) & (x.index <= b)])[0]
                             for p, (a, b) in PERIODS.items() if p != "holdout"}
                         for s, x in pp.items()}
        port.to_csv(f"{OUT}/daily_{name.split()[0]}_{name.split()[-1].replace('/', '-')}.csv")
        print(name, {k: round(v, 3) for k, v in row.items() if k != "setup" and "holdout" not in k},
              flush=True)

    res = pd.DataFrame(rows).set_index("setup")
    res["survives"] = (res["design t"] >= 2) & (res["check ann ret %"] > 0)
    hcols = [c for c in res.columns if c.startswith("holdout")]
    res.loc[~res.survives, hcols] = np.nan
    res.to_csv(f"{OUT}/grid.csv")
    best = res["design t"].idxmax()
    br = pd.DataFrame(breadth[best]).T.sort_values("design sharpe", ascending=False)
    br.index.name = "pair"
    br.to_csv(f"{OUT}/breadth_best.csv")

    show = ["design ann ret %", "design sharpe", "design t", "design ann vol %", "check ann ret %",
            "check sharpe", "check t", "survives"]
    parts = [f"{p} {k}" for p in ("design", "check") for k in
             ("gross %/yr", "cost %/yr", "carry %/yr", "markup %/yr", "no-markup ann ret %", "no-markup t")]
    surv = res[res.survives]
    rep = ["# Daily trend following — 28 FX pairs, 2010–2026\n",
           f"{len(res)} pre-declared portfolio tests (see run_trend.py). Equal-risk portfolio, 10% a year "
           "volatility target if pairs were uncorrelated. Costs: half spread + $7/lot + 0.2 pip per unit "
           "traded; carry at policy / interbank rates with a 1% a year markup. Survival rule fixed before "
           "running: design (2010–2017) t ≥ 2 AND check (2018–2023) return > 0. Holdout (2024–2026) only "
           "for survivors.\n",
           f"**Survivors: {len(surv)} of {len(res)}.**\n",
           fmt_table(res[show], ".2f"),
           "\n## Where the return comes from (% a year): price move, trading costs, interest carry, "
           "broker swap markup; and the result with no markup (futures / forwards-like financing)\n",
           fmt_table(res[parts], ".2f"),
           f"\n## Breadth: per-pair Sharpe of the best design-period setup ({best})\n",
           fmt_table(br, ".2f"),
           "\n## Data coverage (Dukascopy daily candles)\n",
           "Dukascopy publishes a year's daily-candle file only after the year ends, so the data stop at "
           "2025-12-31 and the holdout is 2024–2025.\n",
           fmt_table(cover, "")]
    if len(surv):
        rep += ["\n## Survivors incl. holdout\n", fmt_table(surv[[c for c in res.columns if c != "survives"]].T, ".2f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(res[show].round(2).to_string())
    print(res[parts].round(2).to_string())
    if len(surv):
        print(surv[hcols].round(2).to_string())


if __name__ == "__main__":
    main()
