"""Where do the 1m setups die? Diagnostic for the nqvp report (no parameters change).

    python run_nqvp_funnel.py      # -> results/nq_vp/funnel.md (included in REPORT.md)

For every setup end in the base combo and the no-filter benchmark: which drive-in condition was
missing (gap / big body), and for setups that passed drive-in but got no drive-out within 5 bars,
whether any of the 5 bars had the big body, closed above the gap top, or both.
"""
from __future__ import annotations

from collections import Counter

import holidays
import numpy as np
import pandas as pd

from nqvp.core import drive_in
from nqvp.engine import Params, Variant, day_bias, day_slice, prepare_day, run_day
from nqvp.data import load_chunk
from nqvp.report import md
from run_nqvp import BENCH, VARIANTS

OUT = "results/nq_vp"
RUNS = {"base 0930|POC|B2on|BEoff": Variant(), "no-filter 2R BEoff": Variant(mode="nofilter", target="2R")}


def main() -> None:
    P = Params()
    stats = {k: Counter() for k in RUNS}
    near = {k: [] for k in RUNS}
    base_rate = Counter()
    alt = Counter()                                    # trade counts if ATR(20, 1m) excludes the tested bar
    P_alt = Params(atr1_incl_bar=False)
    for year in range(2020, 2027):
        frame = load_chunk(year)
        hol = holidays.NYSE(years=year)
        for ts in pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="B"):
            if ts.date() in hol or ts > frame.index[-1]:
                continue
            day, info = prepare_day(day_slice(frame, ts.date()), ts.date(), P)
            if day is None:
                continue
            day_alt, _ = prepare_day(day_slice(frame, ts.date()), ts.date(), P_alt)
            for v in VARIANTS + BENCH:
                b = day_bias(day_alt, v) if v.mode == "strategy" else None
                alt[v.name] += len(run_day(day_alt, v, b, P_alt)[0])
            w = slice(day.i0, day.i_end)
            body = np.abs(day.c[w] - day.o[w])
            base_rate["bars"] += len(body)
            base_rate["body >= 1.5 x ATR20"] += int((body >= 1.5 * day.atr20[w]).sum())
            for name, v in RUNS.items():
                trace: list = []
                run_day(day, v, day_bias(day, v) if v.mode == "strategy" else None, P, trace)
                for ev, sd, s, t in trace:
                    c = stats[name]
                    c[ev] += 1
                    if ev == "died_no_drive_in":
                        a = max(s - P.drive_in_bars + 1, 0)
                        gap_ok = not np.isnan(drive_in(day.o, day.h, day.l, day.c, day.atr20, s, sd)[1])
                        big_ok = bool(np.any((day.o[a:s + 1] - day.c[a:s + 1]) * sd >= 1.5 * day.atr20[a:s + 1]))
                        c["  drive-in: no gap, has big body" if big_ok and not gap_ok else
                          "  drive-in: gap, no big body" if gap_ok and not big_ok else
                          "  drive-in: neither"] += 1
                    elif ev == "died_no_drive_out":
                        gap = day.di_gap[sd][s]
                        u = np.arange(s + 1, min(s + P.drive_out_bars, day.i_end - 1) + 1)
                        big = (day.c[u] - day.o[u]) * sd >= 1.5 * day.atr20[u]
                        rec = (day.c[u] - gap) * sd > 0
                        c["  drive-out: a big bar, none closed above gap" if big.any() and not rec.any() else
                          "  drive-out: closed above gap, body too small" if rec.any() and not big.any() else
                          "  drive-out: big bar and reclaim on different bars" if big.any() and rec.any() else
                          "  drive-out: neither"] += 1
                        near[name].append(dict(gap_dist_atr15=(gap - day.l[s] if sd > 0 else day.h[s] - gap)
                                               / day.atr15_at[s],
                                               best_body_atr=float(((day.c[u] - day.o[u]) * sd / day.atr20[u]).max())))
    order = ["signal", "died_no_drive_in", "  drive-in: no gap, has big body", "  drive-in: gap, no big body",
             "  drive-in: neither", "died_no_drive_out", "  drive-out: a big bar, none closed above gap",
             "  drive-out: closed above gap, body too small", "  drive-out: big bar and reclaim on different bars",
             "  drive-out: neither", "died_window_end"]
    tab = pd.DataFrame({k: [stats[k].get(o, 0) for o in order] for k in RUNS}, index=order)
    lines = ["### Where the 1m setups end (full period)\n",
             "Every setup that started (a sweep of the obvious level inside the window) ends in one of: a signal, "
             "death for no drive-in at the final sweep extreme, death for no drive-out within 5 bars, or still "
             "open at 11:00.\n", md(tab, index=True) + "\n"]
    for k in RUNS:
        nd = pd.DataFrame(near[k])
        if len(nd):
            lines.append(f"{k}, setups that died with drive-in OK: median distance from sweep extreme to gap top "
                         f"= {nd.gap_dist_atr15.median():.2f} x ATR(14, 15m); median best drive-out body in the 5 "
                         f"bars = {nd.best_body_atr.median():.2f} x ATR(20, 1m) (needs 1.5).\n")
    lines.append("Interpretation check (not a variant, not ranked): if ATR(20, 1m) for the body tests used the "
                 "20 bars BEFORE the tested bar instead of including it, total trades over the full period would "
                 "be:\n")
    lines.append(md(pd.DataFrame({"combo": [v.name for v in VARIANTS + BENCH],
                                  "trades, full period": [alt[v.name] for v in VARIANTS + BENCH]})) + "\n")
    lines.append(f"Base rate: {base_rate['body >= 1.5 x ATR20'] / base_rate['bars'] * 100:.1f}% of all 1m bars "
                 f"09:30-11:00 have a body >= 1.5 x ATR(20, 1m) (either direction).\n")
    open(f"{OUT}/funnel.md", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
