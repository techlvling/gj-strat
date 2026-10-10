"""Round numbers (Osler 2000/2003): take-profit orders cluster AT round numbers (price tends to turn there),
stop-loss orders cluster just BEYOND them (price tends to run once through). 7 majors + gold, 2010-2026.

Every weekday at 07:00 UTC take the nearest round level above (U) and below (D) the mid price;
round = big figure (1.00 JPY, 0.0100 others, $10 gold). Orders live 07:00-20:00 UTC, time exit 20:00 UTC.
s = 0.1 x ATR20 (daily). Fixed before running:
  R1 fade:     sell limit at U, buy limit at D; SL s beyond the level; TP = RR x s   (RR 2 and 3)
  R2 breakout: buy stop at U + s/2, sell stop at D - s/2; SL s; TP = RR x s           (RR 2 and 3)
Control: the same orders at non-round levels (round + 0.37 x spacing). Pooled over the 8 markets.
Survives if pooled design (2010-17) t >= 2, pooled 2018-23 and 2024-26 avg R > 0, avg R above its control
in all three periods, and positive in more than half of the markets over 2010-2026.
Costs: bid/ask, $7/lot + 0.2 pip slippage on stop fills + swap; gold $0.07/oz + $0.02.

    python run_round_numbers.py
"""
import os
from datetime import date
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import Signal, daily_table, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER, per_stats
from run_usdjpy_sl import tstat

OUT = "results/round_numbers"
MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "XAUUSD"]
SPACING = {"USDJPY": 1.0, "XAUUSD": 10.0}
TESTS = [(kind, rr) for kind in ("R1 fade", "R2 breakout") for rr in (2, 3)]


def signals(m, d, kind, rr, offset):
    sp = SPACING.get(m_sym, 0.01)
    out = []
    for day, r in d.iterrows():
        if day.dayofweek >= 5 or day < pd.Timestamp("2010-01-01"):
            continue
        i = m.idx(day + pd.Timedelta(hours=7))
        j = m.idx(day + pd.Timedelta(hours=20))
        if i < 0 or j >= m.n or m.vol[i] == 0:
            continue
        mid = (m.bo[i] + m.ao[i]) / 2
        up = (np.floor((mid - offset * sp) / sp) + 1) * sp + offset * sp
        dn = up - sp
        s = 0.1 * r.atr20
        if not s > 0:
            continue
        if kind == "R1 fade":
            out += [Signal(day, "SELL", i, "limit", up, j, s, rr * s, j, "R1"),
                    Signal(day, "BUY", i, "limit", dn, j, s, rr * s, j, "R1")]
        else:
            out += [Signal(day, "BUY", i, "stop", up + s / 2, j, s, rr * s, j, "R2"),
                    Signal(day, "SELL", i, "stop", dn - s / 2, j, s, rr * s, j, "R2")]
    return out


def market_tests(sym):
    global m_sym
    m_sym = sym
    sw = SwapModel.from_fred("rates", 1.0)
    m = build_market(sym, date(2010, 1, 1), date(2026, 10, 7), "data/raw", f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
    d = daily_table(m)
    res = {}
    for kind, rr in TESTS:
        for label, off in (("round", 0.0), ("control", 0.37)):
            tr = sorted([t for t in (simulate(m, s) for s in signals(m, d, kind, rr, off)) if t is not None],
                        key=lambda t: (t.exit_i, t.entry_i))
            if sym == "XAUUSD":
                r = np.array([t.r - (0.07 + 0.02 * (1 + (t.reason == "SL"))) / t.risk for t in tr])
            else:
                r = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)["R"].to_numpy()
            res[(kind, rr, label)] = (pd.DatetimeIndex([t.day for t in tr]), r)
    print(sym, "done", flush=True)
    return sym, res


m_sym = None

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with Pool(4) as pool:
        R = dict(pool.map(market_tests, MARKETS, chunksize=1))
    rows, per_mkt = [], []
    for kind, rr in TESTS:
        row = {"test": f"{kind}, RR {rr}"}
        for label in ("round", "control"):
            day = pd.DatetimeIndex(np.concatenate([R[s][(kind, rr, label)][0].values for s in MARKETS]))
            r = np.concatenate([R[s][(kind, rr, label)][1] for s in MARKETS])
            st = per_stats(r, day)
            pre = "" if label == "round" else "control "
            row.update({f"{pre}trades": len(r), f"{pre}win %": (r > 0).mean() * 100, f"{pre}avg R": r.mean(),
                        **{f"{pre}{k}": v for k, v in st.items() if not k.endswith(" n")}})
        pos = sum(1 for s in MARKETS if R[s][(kind, rr, "round")][1].mean() > 0)
        row["markets positive"] = f"{pos}/{len(MARKETS)}"
        row["survives"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0 and pos > len(MARKETS) / 2
                               and all(row[f"{p} avg R"] > row[f"control {p} avg R"] for p in PER))
        rows.append(row)
        for s in MARKETS:
            r = R[s][(kind, rr, "round")][1]
            c = R[s][(kind, rr, "control")][1]
            per_mkt.append({"test": f"{kind}, RR {rr}", "market": s, "trades": len(r), "win %": (r > 0).mean() * 100,
                            "avg R": r.mean(), "t": tstat(r), "control avg R": c.mean()})
    T = pd.DataFrame(rows).set_index("test")
    PM = pd.DataFrame(per_mkt)
    T.to_csv(f"{OUT}/summary.csv"); PM.to_csv(f"{OUT}/per_market.csv", index=False)
    cols = ["trades", "win %", "avg R", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t",
            "control avg R", "control design avg R", "control check avg R", "control holdout avg R", "markets positive", "survives"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Round numbers (Osler): fade at the big figure / breakout beyond it\n\nRules in run_round_numbers.py (fixed before running).\n\n"
        f"**Survivors: {int(T.survives.sum())} of {len(T)}**\n\n## Pooled over 8 markets\n\n" + fmt_table(T[cols], ".3f") +
        "\n\n## Per market\n\n" + fmt_table(PM.set_index(["test", "market"]), ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(T[cols].round(3).to_string())
