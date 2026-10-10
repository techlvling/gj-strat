"""Every strategy family we tested, on every market we have: last 3 years vs 2010-2023.

One representative setting per family (the main / best-known rule; no new tuning):
  BOX-A, BOX-B        box breakout, 05:00 IST box, SL 1 x box, RR 9, BE 3R (green = B)
  GOTOBI              sell at the 09:55 JST fix on gotobi days, exit 06:00 UTC (JPY-quoted only)
  P2 sweep            prev-day high/low sweep reversal, 60m, TP 2R
  P3 asian-fade       Asian range fade at London, 60m, TP opposite side
  P4 pullback         trend + pullback limit, k 0.5 ATR, SL 1 ATR, RR 2
  F1 month-end        follow the month-to-date move into the London 4pm fix (exit 16:05)
  F2 ldn-fix fade     fade the 15:00-16:00 London move, exit 18:00, SL 0.5 ATR
  F3 ny-open mom      follow 09:30-10:00 NY, exit 16:00 NY, SL 0.5 ATR
  I1 ldn-breakout     Asian-range breakout at 07:00 UTC, SL 1 x range, TP 2R
  I2 prevday-bo       prev-day high/low breakout, SL 0.5 ATR, TP 2R
  I3 inside-bo        inside-day breakout, TP 1R
  I4 ny-orb           NY 60-minute opening-range breakout, TP 2R
  I5 night-scalp      quiet-hours Bollinger 2 sd fade, SL 0.3 ATR
Markets: 28 FX pairs, gold (2010-2026), JPN225 and Nasdaq 100 (2011-2026).
Periods: last 3 years = trades from 2023-10-07; "before" = 2010 (2011) to 2023-10-06.
Costs: FX $7/lot + 0.2 pip slippage + swap (+1% markup); gold $0.07/oz + $0.02 slippage;
JPN225 2 pt / Nasdaq 0.25 pt slippage; gold and indices pay 3%/yr financing per rollover day.

About 400 tests: ~10 will show t >= 2 in 3 years by luck alone. The "before" columns are the
reality check — an edge should be positive there too.

    python run_all_matrix.py
"""
from __future__ import annotations

import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import MAJORS, MINORS, build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import (asian_fade, contraction_breakout, daily_table, gotobi_short, london_breakout,
                              london_fix_fade, month_end_fix, night_reversion, ny_open_momentum, ny_orb,
                              prevday_breakout, simulate, sweep_reversal, trend_pullback)
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/all_matrix"
SPLIT = pd.Timestamp("2023-10-07")
MARKETS = sorted(set(MAJORS + MINORS)) + ["XAUUSD", "JPNIDXJPY", "USATECHIDXUSD"]
NON_FX = {"XAUUSD": (0.07, 0.02), "JPNIDXJPY": (0.0, 2.0), "USATECHIDXUSD": (0.0, 0.25)}   # comm, slip
FIN = 0.03 / 365
PATTERNS = {
    "P2 sweep": (sweep_reversal, dict(tf=60, tp="2R")),
    "P3 asian-fade": (asian_fade, dict(tf=60, tp="opposite")),
    "P4 pullback": (trend_pullback, dict(k_atr=0.5, sl_atr=1.0, rr=2)),
    "F1 month-end": (month_end_fix, dict(direction="follow", exit_at=(16, 5))),
    "F2 ldn-fix fade": (london_fix_fade, dict(exit_at=(18, 0), sl_atr=0.5)),
    "F3 ny-open mom": (ny_open_momentum, dict(exit_at=(16, 0), sl_atr=0.5)),
    "I1 ldn-breakout": (london_breakout, dict(sl_range=1.0, rr=2)),
    "I2 prevday-bo": (prevday_breakout, dict(sl_atr=0.5, rr=2)),
    "I3 inside-bo": (contraction_breakout, dict(kind="inside", rr=1)),
    "I4 ny-orb": (ny_orb, dict(minutes=60, rr=2)),
    "I5 night-scalp": (night_reversion, dict(band_std=2.0, sl_atr=0.3)),
}


def net_r(m, sym, trades, swap):
    if not trades:
        return np.array([])
    if sym in NON_FX:
        comm, slip = NON_FX[sym]
        out = []
        for t in trades:
            nights = SwapModel.rollovers(m.ts(t.entry_i), m.ts(t.exit_i))["days"].sum()
            out.append(t.r - (comm + slip * (1 + (t.reason in ("SL", "BE"))) + FIN * nights * t.entry) / t.risk)
        return np.array(out)
    lg = account(trades, m, 10_000, risk_pct=0.5, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
    # account() returns rows sorted by (exit_i, entry_i); callers pass trades in that order, and any
    # remaining ties share entry and exit bars (same day), so the period split is unaffected
    assert (lg["entry_i"].to_numpy() == [t.entry_i for t in trades]).all()
    return lg["R"].to_numpy()


def market_rows(sym):
    swap = SwapModel.from_fred("rates", 1.0)
    start = date(2011, 1, 2) if "IDX" in sym else date(2010, 1, 1)
    m = build_market(sym, start, date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_{start}_2026-10-07.npz")
    d = daily_table(m)
    d = d[d.index >= pd.Timestamp(start)]
    strategies = {}
    days = trading_days(m, start=str(start + pd.Timedelta(days=1)))
    _, probe = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in probe.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    for v in ("A", "B"):
        strategies[f"BOX-{v}"] = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version=v,
                                               sl_box_mult=1.0), days)[0]
    if sym.endswith("JPY"):
        strategies["GOTOBI"] = [t for t in (simulate(m, s) for s in gotobi_short(m, d)) if t is not None]
    for name, (fn, kw) in PATTERNS.items():
        strategies[name] = [t for t in (simulate(m, s) for s in fn(m, d, **kw)) if t is not None]
    rows = []
    for name, tr in strategies.items():
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        r = net_r(m, sym, tr, swap)
        day = pd.DatetimeIndex([t.day for t in tr])
        row = {"market": sym, "strategy": name}
        for per, mask in (("last3y", day >= SPLIT), ("before", day < SPLIT)):
            x = r[np.asarray(mask)] if len(r) else np.array([])
            row.update({f"{per} trades": len(x), f"{per} win %": (x > 0).mean() * 100 if len(x) else np.nan,
                        f"{per} avg R": x.mean() if len(x) else np.nan, f"{per} t": tstat(x)})
        rows.append(row)
    print(sym, "done", flush=True)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    with Pool(3) as pool:
        out = pool.map(market_rows, MARKETS, chunksize=1)
    res = pd.DataFrame([r for rows in out for r in rows]).set_index(["strategy", "market"]).sort_index()
    res.to_csv(f"{OUT}/matrix.csv")
    heat = res["last3y avg R"].unstack("market")
    heat.to_csv(f"{OUT}/last3y_avgR_heatmap.csv")
    top = res[res["last3y trades"] >= 30].sort_values("last3y t", ascending=False).head(25)
    both = res[(res["last3y t"] >= 2) & (res["before avg R"] > 0) & (res["before t"] >= 2)]
    n, lucky = len(res), int((res["last3y t"] >= 2).sum())
    fam = res.groupby(level="strategy").apply(
        lambda g: pd.Series({"markets": len(g), "last3y avg R (mean)": g["last3y avg R"].mean(),
                             "markets + last3y": int((g["last3y avg R"] > 0).sum()),
                             "before avg R (mean)": g["before avg R"].mean(),
                             "markets + before": int((g["before avg R"] > 0).sum())}))
    def lab(df):
        df = df.copy()
        df.index = [f"{a} · {b}" for a, b in df.index]
        df.index.name = "Strategy · market"
        return df
    cols = ["last3y trades", "last3y win %", "last3y avg R", "last3y t", "before trades", "before avg R", "before t"]
    rep = ["# All strategies × all markets — last 3 years (from 2023-10-07) vs 2010–2023\n",
           f"{n} tests. With t ≥ 2 in the last 3 years: {lucky} (about {n * 0.025:.0f} expected by luck). "
           f"Also t ≥ 2 and positive in 2010–2023: **{len(both)}**.\n",
           "## Families on average\n", fmt_table(fam.sort_values("last3y avg R (mean)", ascending=False), ".3f"),
           "\n## Top 25 by last-3-year t (≥ 30 trades)\n", fmt_table(lab(top[cols]), ".3f"),
           "\n## Strong in both periods (last-3y t ≥ 2 and 2010–2023 t ≥ 2)\n",
           fmt_table(lab(both[cols]), ".3f") if len(both) else "None.\n",
           "\nFull matrix: matrix.csv; last-3y avg R per strategy × market: last3y_avgR_heatmap.csv\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep))
    pd.set_option("display.width", 250)
    print(fam.round(3).to_string())
    print(lab(top[cols]).round(3).to_string())
    print("both:", lab(both[cols]).round(3).to_string() if len(both) else "none")


if __name__ == "__main__":
    main()
