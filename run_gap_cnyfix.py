"""(A) Monday gap fill on 28 FX pairs + gold, (B) China CNY fix minute on AUDUSD / NZDUSD. 2010-2026.

(A) Weekend gap = first live bid open after the weekend minus Friday's last bid close. Fade it
    toward Friday's close (TP = Friday's close, limit-like via TP distance), time exit 24 h.
    Pre-declared variants (8): entry at the reopen / 60 min later x min gap 0.1 / 0.25 x ATR20 x
    SL = remaining gap distance / 0.25 x ATR20. Skipped when the gap is already filled at entry.
    Judged POOLED over the 29 markets: survives if pooled design t >= 2, pooled check and holdout
    avg R > 0, and positive on more than half of the markets over 2010-2026.
(B) CNY fix 09:15 Beijing = 01:15 UTC (no DST). Follow / fade the 01:15-01:30 UTC move from 01:30,
    exit 02:30 / 03:30 UTC, SL 0.25 x ATR20, AUDUSD and NZDUSD (8). Survives if design t >= 2 and
    check and holdout avg R > 0.
Costs: real bid/ask (incl. Sunday-open spreads), $7/lot + 0.2 pip slippage + swap; gold $0.07/oz + $0.02.

    python run_gap_cnyfix.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import MAJORS, MINORS, build_market
from gjstrat.patterns import Signal, daily_table, simulate, utc_idx
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER, per_stats
from run_usdjpy_sl import tstat

OUT = "results/gap_cnyfix"
MARKETS = sorted(set(MAJORS + MINORS)) + ["XAUUSD"]
VARIANTS = [(delay, thr, slm) for delay in (0, 60) for thr in (0.1, 0.25) for slm in ("gap", "atr")]


def vname(v):
    delay, thr, slm = v
    return f"entry +{delay}m, gap >= {thr:g} ATR, SL {'= gap' if slm == 'gap' else '0.25 ATR'}"


def net(m, sym, sigs, swap):
    tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
    if not tr:
        return np.array([]), pd.DatetimeIndex([])
    if sym == "XAUUSD":
        r = np.array([t.r - (0.07 + 0.02 * (1 + (t.reason == "SL"))) / t.risk for t in tr])
    else:
        r = account(tr, m, 10_000, commission=7, swap=swap, sym=sym, slippage_pips=0.2)["R"].to_numpy()
    return r, pd.DatetimeIndex([t.day for t in tr])


def gap_market(sym):
    swap = SwapModel.from_fred("rates", 1.0)
    m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
    d = daily_table(m)
    live = np.flatnonzero(m.vol > 0)
    jumps = np.flatnonzero(np.diff(live) > 36 * 60)              # weekend closures
    out = {}
    for v in VARIANTS:
        delay, thr, slm = v
        sigs = []
        for j in jumps:
            fri, op = live[j], live[j + 1]
            e = op + delay
            if e + 1440 >= m.n or m.vol[e] == 0:
                continue
            ts = m.ts(op)
            label = (ts.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=7)).normalize()
            atr = d["atr20"].get(label, np.nan)
            if np.isnan(atr) or label < pd.Timestamp("2010-01-01"):
                continue
            fc = m.bc[fri]
            gap = m.bo[op] - fc
            if abs(gap) < thr * atr:
                continue
            side = "SELL" if gap > 0 else "BUY"
            remaining = (m.bo[e] - fc) if side == "SELL" else (fc - m.ao[e])
            if remaining <= 0:
                continue                                          # already filled
            sl = remaining if slm == "gap" else 0.25 * atr
            sigs.append(Signal(label, side, e, "market", None, e + 1, sl, remaining, e + 1440, "gap"))
        out[v] = net(m, sym, sigs, swap)
    return sym, out


def cny(m, sym, d, swap, mode, exit_h):
    sigs = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or day < pd.Timestamp("2010-01-01"):
            continue
        a, b, x = utc_idx(m, day, 1, 15), utc_idx(m, day, 1, 30), utc_idx(m, day, exit_h, 30)
        if a < 0 or x >= m.n or m.vol[a] == 0 or m.vol[b] == 0:
            continue
        mv = m.bo[b] - m.bo[a]
        if mv == 0:
            continue
        up = mv > 0
        side = ("BUY" if up else "SELL") if mode == "follow" else ("SELL" if up else "BUY")
        sigs.append(Signal(day, side, b, "market", None, b + 1, 0.25 * r.atr20, None, x, "cny"))
    return net(m, sym, sigs, swap)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with Pool(3) as pool:
        res = dict(pool.map(gap_market, MARKETS, chunksize=1))
    rows, per_market = [], []
    for v in VARIANTS:
        rs = [res[s][v][0] for s in MARKETS]
        ds = [res[s][v][1] for s in MARKETS]
        r, day = np.concatenate(rs), pd.DatetimeIndex(np.concatenate([x.values for x in ds]))
        pos = sum(1 for x in rs if len(x) and x.mean() > 0)
        row = {"variant": vname(v), "trades": len(r), "win %": (r > 0).mean() * 100, **per_stats(r, day),
               "markets positive": f"{pos}/{len(MARKETS)}"}
        row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0 and pos > len(MARKETS) / 2)
        rows.append(row)
        for s, x in zip(MARKETS, rs):
            per_market.append({"variant": vname(v), "market": s, "trades": len(x), "avg R": x.mean() if len(x) else np.nan,
                               "t": tstat(x)})
    gap_tab = pd.DataFrame(rows).set_index("variant")
    pm = pd.DataFrame(per_market)
    gap_tab.to_csv(f"{OUT}/gap_pooled.csv"); pm.to_csv(f"{OUT}/gap_per_market.csv", index=False)

    swap = SwapModel.from_fred("rates", 1.0)
    crow = []
    for sym in ("AUDUSD", "NZDUSD"):
        m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(m)
        for mode in ("follow", "fade"):
            for eh in (2, 3):
                r, day = cny(m, sym, d, swap, mode, eh)
                crow.append({"test": f"CNY fix {sym} {mode} 01:30 -> {eh}:30 UTC", "win %": (r > 0).mean() * 100, **per_stats(r, day)})
    cny_tab = pd.DataFrame(crow).set_index("test")
    cny_tab["survives"] = (cny_tab["design t"] >= 2) & (cny_tab["check avg R"] > 0) & (cny_tab["holdout avg R"] > 0)
    cny_tab.to_csv(f"{OUT}/cny.csv")
    gc = ["trades", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t",
          "markets positive", "survives"]
    cc = ["design n", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t", "survives"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Monday gap fill (28 FX + gold) and China CNY-fix minute (AUD, NZD), 2010–2026\n\nRules in run_gap_cnyfix.py.\n\n"
        f"## A. Gap fill, pooled over {len(MARKETS)} markets — survivors: **{int(gap_tab.survives.sum())} of {len(gap_tab)}**\n\n"
        + fmt_table(gap_tab[gc], ".3f") +
        f"\n\n## B. CNY fix minute — survivors: **{int(cny_tab.survives.sum())} of {len(cny_tab)}**\n\n" + fmt_table(cny_tab[cc], ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(gap_tab[gc].round(3).to_string()); print(cny_tab[cc].round(3).to_string())
