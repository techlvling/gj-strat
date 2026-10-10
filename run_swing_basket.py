"""Faster Alpha Swing pass: add the fade (Version C) to the vol-box + gotobi basket.

Part 1 (fixed before running): fade = Version C, RR 5, no BE, virtual SL by 11:00 IST, SL 1 x box.
Vol-filtered fade (same rule as the box: ATR20 >= rolling 250-day median) is accepted only if its
avg R is >= the unfiltered fade's in all three periods (2010-17 / 2018-23 / 2024-26).
Part 2: Alpha Swing challenge (P1 +10%, P2 +5%, 10% static, 5% daily, >= 3 days; no consistency
rule) for baskets of vol-box + gotobi + fade. Costs: $7/lot, swap +1%, 0.2 pip slippage.

    python run_swing_basket.py
"""
import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.engine import Params, run, trading_days
from gjstrat.patterns import daily_table, gotobi_short, simulate
from gjstrat.prop import prop_table
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_patterns import PERIODS
from run_usdjpy_sl import tstat

OUT = "results/swing_basket"
RULES = dict(targets=(0.10, 0.05), max_dd=0.10, daily=0.05, min_days=3)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    sw = SwapModel.from_fred("rates", 1.0)
    days = trading_days(m, start="2010-01-01")
    _, pr = run(m, Params(sl_box_mult=1.0), days)
    sk = {x for x, _ in pr.skipped_dates}
    days = [x for x in days if x.date() not in sk]
    base = dict(sl_pips=30, be_plus=5, sl_box_mult=1.0)
    box, _ = run(m, Params(rr=9, be_trigger=3, version="B", **base), days)
    fade, _ = run(m, Params(rr=5, be_trigger=None, version="C", fade_expiry_11=True, **base), days)
    d = daily_table(m)
    med = d["atr20"].rolling(250, min_periods=250).median()
    hot = lambda t: d["atr20"].get(t.day, np.nan) >= med.get(t.day, np.nan)
    vbox = [t for t in box if hot(t)]
    vfade = [t for t in fade if hot(t)]
    got = [t for t in (simulate(m, s) for s in gotobi_short(m, d[d.index >= pd.Timestamp("2011-01-01")])) if t is not None]

    def net(tr):
        tr = sorted(tr, key=lambda t: (t.exit_i, t.entry_i))
        return tr, account(tr, m, 10_000, commission=7, swap=sw, sym="USDJPY", slippage_pips=0.2)["R"].to_numpy()

    rows = []
    for name, tr in (("fade", fade), ("vol-filtered fade", vfade)):
        tr, r = net(tr)
        day = pd.DatetimeIndex([t.day for t in tr])
        row = {"setup": name}
        for per, (a, b) in PERIODS.items():
            x = r[np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))]
            row.update({f"{per} trades": len(x), f"{per} avg R": x.mean(), f"{per} t": tstat(x)})
        rows.append(row)
    f = pd.DataFrame(rows).set_index("setup")
    use_vfade = all(f.loc["vol-filtered fade", f"{p} avg R"] >= f.loc["fade", f"{p} avg R"] for p in PERIODS)
    fade_leg = vfade if use_vfade else fade
    fname = "vol-fade" if use_vfade else "fade"
    print(f.round(3).to_string(), "\nuse vol-filtered fade:", use_vfade)

    legs = [net(vbox), net(got), net(fade_leg)]
    mixes = {"vol-box 0.25% + gotobi 3% (current pick)": (0.25, 3, 0), "vol-box 0.25% + gotobi 4%": (0.25, 4, 0)}
    for fr in (0.25, 0.5):
        for g in (2, 3):
            mixes[f"vol-box 0.25% + gotobi {g}% + {fname} {fr:g}%"] = (0.25, g, fr)
    mixes[f"vol-box 0.5% + gotobi 3% + {fname} 0.5%"] = (0.5, 3, 0.5)
    tab = prop_table(m, legs, mixes, **RULES)
    tab["fees per funded account $"] = 100 / (tab["pass eventually %"] / 100)
    tab["months per funded account"] = tab["avg days per attempt"] / 30.4 / (tab["pass eventually %"] / 100)
    tab.to_csv(f"{OUT}/prop.csv")
    cols = ["pass ≤2 months %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %", "pass eventually %",
            "median months to pass", "months per funded account", "max DD %"]
    open(f"{OUT}/REPORT.md", "w").write("# Alpha Swing: adding the fade to vol-box + gotobi\n\nRules in run_swing_basket.py.\n\n"
                                        "## Fade, with and without the vol filter\n\n" + fmt_table(f, ".3f") +
                                        f"\n\nVol-filtered fade accepted: **{use_vfade}**\n\n## Alpha Swing challenge\n\n"
                                        + fmt_table(tab[cols], ".1f") + "\n")
    pd.set_option("display.width", 250)
    print(tab[cols].round(1).to_string())
