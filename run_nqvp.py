"""Nasdaq 100 CFD overnight volume-profile strategy: 16-variant sweep, IS/OOS, benchmarks, report.

    python -m pytest -q tests/test_nqvp.py     # rule tests first
    python run_nqvp.py                         # simulate (per-year chunks, cached) + analyse
    python run_nqvp.py --analyse-only          # reuse results/nq_vp/sim/*.parquet
    python run_nqvp.py --commission 0.5        # $ per unit round turn (default 0)

Data: Dukascopy USATECH.IDX/USD (feed symbol USATECHIDXUSD) 1m BID + ASK, cached to
data/nq_parquet/USATECHIDXUSD_<year>.parquet. Output: results/nq_vp/.
"""
from __future__ import annotations

import argparse
import os
import time
from dataclasses import replace
from datetime import date

import holidays
import numpy as np
import pandas as pd

from nqvp.data import available_years, build_year, fetch_missing, load_chunk, restore_raw
from nqvp.engine import Params, Variant, day_bias, day_slice, prepare_day, run_day

OUT = "results/nq_vp"
SIM = f"{OUT}/sim"
START = date(2020, 1, 1)

VARIANTS = [Variant(start=s, target=t, acceptance=a, be=b)
            for s in (570, 585) for t in ("POC", "2R") for a in (True, False) for b in (False, True)]
ROBUST = [replace(v, entry="next_open") for v in VARIANTS]
BENCH = [Variant(mode="nofilter", target="2R", be=b) for b in (False, True)]
BASE = Variant(start=570, target="POC", acceptance=True, be=False)


# --------------------------------------------------------------------------- simulation
def simulate_year(year: int, end: date, P: Params) -> None:
    """One chunk: every NY trading day of `year`, all variants. Writes days/trades/counts parquet."""
    frame = load_chunk(year)
    hol = holidays.NYSE(years=year)
    days, trades, counts = [], [], []
    for ts in pd.date_range(max(START, date(year, 1, 1)), min(end, date(year, 12, 31)), freq="D"):
        d = ts.date()
        if d.weekday() >= 5:
            continue
        if d in hol:
            days.append(dict(date=d, skip="nyse_holiday", holiday=hol.get(d)))
            continue
        day, info = prepare_day(day_slice(frame, d), d, P)
        if day is None:
            days.append(info)
            continue
        info["va_coverage"] = day.va_coverage
        biases = {}
        for s in (570, 585):
            for a in (True, False):
                b = day_bias(day, Variant(start=s, acceptance=a))
                biases[(s, a)] = b
                key = f"bias_{'0930' if s == 570 else '0945'}_B2{'on' if a else 'off'}"
                info[key] = f"{b.kind}{'' if b.side == 0 else ('+' if b.side > 0 else '-')}"
                info[key + "_active"] = b.active
        days.append(info)
        for v in VARIANTS + ROBUST + BENCH:
            b = biases[(v.start, v.acceptance)] if v.mode == "strategy" else None
            tr, cnt = run_day(day, v, b, P)
            for t in tr:
                t["variant"] = v.name
            trades += tr
            counts.append(dict(date=d, variant=v.name, trades=len(tr), **cnt))
    os.makedirs(SIM, exist_ok=True)
    pd.DataFrame(days).assign(date=lambda x: pd.to_datetime(x["date"])).to_parquet(f"{SIM}/days_{year}.parquet")
    tdf = pd.DataFrame(trades)
    if len(tdf):
        tdf["date"] = pd.to_datetime(tdf["date"])
    tdf.to_parquet(f"{SIM}/trades_{year}.parquet")
    cdf = pd.DataFrame(counts).fillna(0)
    cdf["date"] = pd.to_datetime(cdf["date"])
    cdf.to_parquet(f"{SIM}/counts_{year}.parquet")


def simulate(P: Params, fetch: bool) -> date:
    years = range(START.year, date.today().year + 1)
    restore_raw(range(START.year - 1, date.today().year + 1))
    if fetch:
        fetch_missing(date(2026, 10, 8), date.today())
    for y in range(START.year - 1, date.today().year + 1):
        build_year(y)
    last = load_chunk(max(available_years())).index[-1]
    end = last.date() if last.hour * 60 + last.minute >= 16 * 60 else (last - pd.Timedelta(days=1)).date()
    for y in years:
        t0 = time.time()
        simulate_year(y, end, P)
        print(f"simulated {y} in {time.time() - t0:.0f}s", flush=True)
    return end


def load_sim() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rd = lambda kind: pd.concat([pd.read_parquet(f"{SIM}/{f}") for f in sorted(os.listdir(SIM))
                                 if f.startswith(kind + "_")], ignore_index=True)
    return rd("days"), rd("trades"), rd("counts").fillna(0)


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyse-only", action="store_true")
    ap.add_argument("--fetch", action="store_true", help="try to download days missing from data/raw")
    ap.add_argument("--commission", type=float, default=0.0, help="$ per unit round turn")
    ap.add_argument("--seeds", type=int, default=1000)
    args = ap.parse_args()
    P = Params(commission=args.commission)
    if not args.analyse_only:
        simulate(P, args.fetch)
    from nqvp.report import analyse
    analyse(*load_sim(), P=P, seeds=args.seeds, out=OUT)


if __name__ == "__main__":
    main()
