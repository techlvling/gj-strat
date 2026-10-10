"""After a green-box trade hits its SL: how far does price run on (past the SL) and how far
does it come back? Then: a trade opened at the SL fill in the SL direction with a HALF-size stop
(0.5 x box), what happens first - the half stop or a target?

Set: green-box (Version B) SL exits on USDJPY 2010-2026; also the subset that matches the fade
idea (first trade of the day, SL hit before 11:00 IST). Window: 24 h after the SL (minute bars,
bid for SL'd buys, ask for SL'd sells). 1R = the box trade's SL distance. Descriptive; the
half-stop table is gross of commission/slippage (spread is in the bid/ask) with a net estimate.

    python run_after_sl_excursion.py
"""
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import build_market
from gjstrat.engine import IST, Params, run, trading_days
from run_backtest import fmt_table

m = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
days = trading_days(m, start="2010-01-01")
_, pr = run(m, Params(sl_box_mult=1.0), days)
sk = {x for x, _ in pr.skipped_dates}
tr, _ = run(m, Params(rr=9, sl_pips=30, be_trigger=3, be_plus=5, version="B", sl_box_mult=1.0),
            [x for x in days if x.date() not in sk])
W = 1440
sl = [t for t in tr if t.reason == "SL" and t.exit_i + W < m.n]


def excursions(t):
    """Run-on (continuation past SL) and come-back (toward the old trade), in R, over the window,
    plus the first-touch sequence needed for the half-stop trade."""
    w = slice(t.exit_i + 1, t.exit_i + 1 + W)
    if t.side == "BUY":            # SL'd buy -> price fell; new trade = SELL at the bid fill, exits on ask
        run_on = (t.exit - m.al[w]) / t.risk               # ask lows below the SL fill
        back = (m.ah[w] - t.exit) / t.risk                 # ask highs back up
    else:                          # SL'd sell -> price rose; new trade = BUY at the ask fill, exits on bid
        run_on = (m.bh[w] - t.exit) / t.risk
        back = (t.exit - m.bl[w]) / t.risk
    return run_on, back


rows, seq = [], []
for t in sl:
    ro, bk = excursions(t)
    ist = m.ts(t.exit_i) + IST
    rows.append({"day": t.day, "first_by_11": t.num == 1 and ist.hour < 11, "box_pips": t.risk / m.pip,
                 "run_on_max": ro.max(), "back_max": bk.max()})
    seq.append((ro, bk))
df = pd.DataFrame(rows)


def half_stop_table(mask, label):
    """Trade at the SL fill in the SL direction, stop 0.5R; target k x 0.5R; stop wins ties."""
    out = []
    idx = np.flatnonzero(mask.to_numpy())
    cost_r = ((0.7 + 0.4) / (0.5 * df["box_pips"].to_numpy()[idx]))      # $7/lot ~0.7 pip + 2 x 0.2 slip, in new R
    for k in (1, 2, 3, 4, 6):
        res = []
        for i in idx:
            ro, bk = seq[i]
            stop = np.flatnonzero(bk >= 0.5)
            tgt = np.flatnonzero(ro >= 0.5 * k)
            s, g = (stop[0] if len(stop) else W), (tgt[0] if len(tgt) else W)
            res.append(k if g < s else (-1.0 if s <= g and s < W else np.nan))
        res = np.array(res)
        done = ~np.isnan(res)
        win = (res[done] > 0).mean() * 100
        gross = np.where(done, res, 0.0)                      # open after 24 h counted as 0 (approx.)
        out.append({"set": label, "target (x new SL)": k, "target in old R": 0.5 * k, "win %": win,
                    "unresolved after 24 h %": (~done).mean() * 100,
                    "avg gross (new R)": gross.mean(), "avg net est. (new R)": (gross - cost_r).mean()})
    return out


tab = pd.DataFrame(half_stop_table(df["first_by_11"] | True, "all SLs") +
                   half_stop_table(df["first_by_11"], "first trade, SL before 11:00"))
q = lambda s: s.quantile([0.25, 0.5, 0.75]).round(2).tolist()
lines = [f"# After the box SL: run-on, come-back and a half-size-stop trade (USDJPY 2010–2026)\n",
         f"{len(df)} SL exits ({int(df.first_by_11.sum())} were the day's first trade, before 11:00). "
         f"Median box (= 1R) {df.box_pips.median():.1f} pips.\n",
         "## How far it goes past the SL vs how far it comes back (24 h, in old R)\n",
         "| | 25% | median | 75% |\n|---|---|---|---|",
         f"| Runs on past the SL (max) | " + " | ".join(map(str, q(df.run_on_max))) + " |",
         f"| Comes back toward the old trade (max) | " + " | ".join(map(str, q(df.back_max))) + " |",
         f"\n- Comes back at least 0.5R (a half-size stop would be hit): {(df.back_max >= 0.5).mean() * 100:.0f}% within 24 h",
         f"- Runs on at least 1R: {(df.run_on_max >= 1).mean() * 100:.0f}%, at least 2R: {(df.run_on_max >= 2).mean() * 100:.0f}%\n",
         "## Trade at the SL, half-size stop (0.5 x box): which comes first?\n",
         "Net estimate subtracts ~1.1 pip (commission + slippage) per trade; spread is already in the fills.\n",
         fmt_table(tab.set_index(["set", "target (x new SL)"]), ".2f")]
txt = "\n".join(lines) + "\n"
open("results/after_sl/EXCURSION.md", "w").write(txt)
print(txt)
