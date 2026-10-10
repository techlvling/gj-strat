"""Exact institutional times (1-minute precision, daylight-saving aware), 2010-2026.

Pre-declared tests (17), direction from theory, SL 0.25 x ATR20, time exit:
  NY 10:00 option cut, fade the 09:30-10:00 NY move from 10:00, exit 11:00 / 12:00 NY: USDJPY, EURUSD, XAUUSD (6)
  ECB reference rate 14:15 Frankfurt, fade the 13:45-14:15 move, exit 15:15 / 16:15 (EURUSD)          (2)
  Gold London PM fix 15:00 London, fade 14:30-15:00, exit 16:00 / 17:00 (XAUUSD)                      (2)
  Gold London AM fix 10:30 London, fade 10:00-10:30, exit 11:30 / 12:30 (XAUUSD)                      (2)
  Month-start Tokyo fix: first 3 business days of the month that are not gotobi days, sell USDJPY at
    09:55 JST, exit 12:00 / 15:00 JST (like gotobi)                                                    (2)
  Into the London 4pm fix: follow the 15:00-15:30 London move from 15:30 to 16:00: EURUSD, GBPUSD, USDJPY (3)
Survives: design (2010-17) t >= 2 AND avg R > 0 in check (2018-23) AND holdout (2024-26). ~0.5 by luck.
Costs: FX $7/lot + 0.2 pip slippage + swap; gold $0.07/oz + $0.02 slippage.

    python run_fix_times.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import LDN, NY, Signal, daily_table, is_gotobi, local_idx, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import per_stats

OUT = "results/fix_times"
FRA, TKY = "Europe/Berlin", "Asia/Tokyo"
SWAP = None


def stats(m, sym, sigs):
    tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
    if sym == "XAUUSD":
        r = np.array([t.r - (0.07 + 0.02 * (1 + (t.reason == "SL"))) / t.risk for t in tr])
    else:
        r = account(tr, m, 10_000, commission=7, swap=SWAP, sym=sym, slippage_pips=0.2)["R"].to_numpy()
    return {"win %": (r > 0).mean() * 100, **per_stats(r, pd.DatetimeIndex([t.day for t in tr]))}


def fade_or_follow(m, d, tz, a_hm, b_hm, exit_hm, mode):
    sigs = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or day < pd.Timestamp("2010-01-01"):
            continue
        a, b, x = (local_idx(m, day, *a_hm, tz), local_idx(m, day, *b_hm, tz), local_idx(m, day, *exit_hm, tz))
        if a < 0 or x >= m.n or m.vol[a] == 0 or m.vol[b] == 0:
            continue
        mv = m.bo[b] - m.bo[a]
        if mv == 0:
            continue
        up = mv > 0
        side = ("SELL" if up else "BUY") if mode == "fade" else ("BUY" if up else "SELL")
        sigs.append(Signal(day, side, b, "market", None, b + 1, 0.25 * r.atr20, None, x, mode))
    return sigs


def month_start_fix(m, d, exit_hm):
    wk = d.index[(d.index.dayofweek < 5) & (d.index >= pd.Timestamp("2010-01-01"))]
    first3 = pd.Series(wk, index=wk).groupby([wk.year, wk.month]).head(3)
    sigs = []
    for day in first3:
        if is_gotobi(day):
            continue
        s, x = local_idx(m, day, 9, 55, TKY), local_idx(m, day, *exit_hm, TKY)
        if s < 0 or x >= m.n:
            continue
        sigs.append(Signal(day, "SELL", s, "market", None, s + 1, 0.25 * d.loc[day, "atr20"], None, x, "mstart"))
    return sigs


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    SWAP = SwapModel.from_fred("rates", 1.0)
    mk = {s: build_market(s, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{s.lower()}_2010-01-01_2026-10-07.npz")
          for s in ("USDJPY", "EURUSD", "GBPUSD", "XAUUSD")}
    dt = {s: daily_table(m) for s, m in mk.items()}
    rows = []
    for s in ("USDJPY", "EURUSD", "XAUUSD"):
        for ex in ((11, 0), (12, 0)):
            rows.append({"test": f"NY 10:00 cut fade, {s}, exit {ex[0]}:00 NY",
                         **stats(mk[s], s, fade_or_follow(mk[s], dt[s], NY, (9, 30), (10, 0), ex, "fade"))})
    for ex in ((15, 15), (16, 15)):
        rows.append({"test": f"ECB 14:15 fix fade, EURUSD, exit {ex[0]}:{ex[1]:02d} Frankfurt",
                     **stats(mk["EURUSD"], "EURUSD", fade_or_follow(mk["EURUSD"], dt["EURUSD"], FRA, (13, 45), (14, 15), ex, "fade"))})
    for a, b, exits, label in (((14, 30), (15, 0), ((16, 0), (17, 0)), "PM 15:00"), ((10, 0), (10, 30), ((11, 30), (12, 30)), "AM 10:30")):
        for ex in exits:
            rows.append({"test": f"Gold London {label} fix fade, exit {ex[0]}:{ex[1]:02d} London",
                         **stats(mk["XAUUSD"], "XAUUSD", fade_or_follow(mk["XAUUSD"], dt["XAUUSD"], LDN, a, b, ex, "fade"))})
    for ex in ((12, 0), (15, 0)):
        rows.append({"test": f"Month-start Tokyo fix sell (non-gotobi), USDJPY, exit {ex[0]}:00 JST",
                     **stats(mk["USDJPY"], "USDJPY", month_start_fix(mk["USDJPY"], dt["USDJPY"], ex))})
    for s in ("EURUSD", "GBPUSD", "USDJPY"):
        rows.append({"test": f"Into London 4pm fix follow 15:30->16:00, {s}",
                     **stats(mk[s], s, fade_or_follow(mk[s], dt[s], LDN, (15, 0), (15, 30), (16, 0), "follow"))})
    res = pd.DataFrame(rows).set_index("test")
    res["survives"] = (res["design t"] >= 2) & (res["check avg R"] > 0) & (res["holdout avg R"] > 0)
    res.to_csv(f"{OUT}/summary.csv")
    cols = ["design n", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t", "survives"]
    open(f"{OUT}/REPORT.md", "w").write("# Exact institutional times — 17 pre-declared tests, 2010–2026\n\nRules in run_fix_times.py.\n\n"
                                        f"**Survivors: {int(res.survives.sum())} of {len(res)}** (about 0.5 expected by luck).\n\n"
                                        + fmt_table(res[cols].sort_values("design t", ascending=False), ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(res[cols].sort_values("design t", ascending=False).round(3).to_string())
