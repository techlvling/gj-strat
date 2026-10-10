"""Stop-miss bias from missing overnight data (design years) for Nasdaq MR4 / MR6.

The Nasdaq minute file has no ticks 16:00-02:00 NY in 2015-2017 (and only 09:30-16:00 NY in 2012; ~50% in
2013), so stops are only checked while data exists; an overnight dip through the stop that recovers by the
time data resumes is missed. Measure the bias where data is complete (2018-26 trades, signal day >= 2018-07):
re-run each trade's stop with the same hours blanked (masked minutes = forward-filled flat, as in the file)
and compare with the full-data result. Costs: 2x slippage (0.5 pt, 1.0 pt on SL) + 3%/yr financing.
Also: S&P 500 hourly bars (USA500IDXUSD) overnight in 2015-2017, if live, to check design trades directly.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/gj-strat"); os.chdir("/home/user/gj-strat")
sys.path.insert(0, "/home/user/gj-strat/results/alpha_hunt/index_meanrev/verify_execution")
import run_alpha_index_meanrev as A
from verify_exec import build
from gjstrat.engine import EPS
from gjstrat.patterns import NY, Signal, simulate
from gjstrat.swap import SwapModel
from run_all_matrix import FIN
from run_edge_hunt import PER
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/index_meanrev/verify_execution"
SLIP = 0.5


def main():
    m, cs, cal = build()
    I = cs.i.to_numpy()
    store = {}

    def execute(v, j, jx, side, slm):
        s = live_at(m, int(I[j]) + 1)
        x = int(I[jx]) + 1
        sl = slm * cs.atr20.iat[j]
        if s < 0 or x <= s + 1 or x >= m.n or not sl > 0:
            return None
        t = simulate(m, Signal(cs.index[j], side, s, "market", None, s + 1, sl, None, x, v))
        if t is not None:
            store.setdefault(v, []).append((t, x))
        return t

    A.plan(cs, execute)
    ts = m.t0 + pd.to_timedelta(np.arange(m.n), unit="min")
    loc = ts.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    hm = (loc.hour * 60 + loc.minute).to_numpy()
    del ts, loc
    masks = {"full": np.ones(m.n, bool),
             "2015-17 pattern (live 02:00-16:00 NY)": (hm >= 120) & (hm < 960),
             "2012 pattern (live 09:30-16:00 NY)": (hm >= 570) & (hm < 960)}

    def resim(t, x, live):
        px, S = t.entry, t.entry - t.risk
        ei = t.entry_i
        if m.bl[ei] <= S + EPS:
            return S, ei, "SL"
        idx = np.arange(ei + 1, x)
        idx = idx[live[idx]]
        hit = idx[m.bl[idx] <= S + EPS]
        if len(hit):
            j = hit[0]
            return (m.bo[j] if m.bo[j] < S - EPS else S), j, "SL"
        return m.bo[x], x, "TIME"

    rows, out = [], []
    for v, lst in store.items():
        if v not in ("MR4", "MR6"):
            continue
        for t, x in lst:
            rec = {"variant": v, "day": t.day}
            for mk, live in masks.items():
                px, j, why = resim(t, x, live)
                if mk == "full":
                    assert abs((px - t.entry) / t.risk - t.r) < 1e-9 and why == t.reason, (t, px, why)
                nights = SwapModel.rollovers(m.ts(t.entry_i), m.ts(j))["days"].sum()
                rec[mk] = (px - t.entry) / t.risk - (SLIP * (1 + (why == "SL")) + FIN * nights * t.entry) / t.risk
                rec[mk + " SL"] = why == "SL"
            out.append(rec)
    D = pd.DataFrame(out)
    D.to_csv(f"{OUT}/mask_trades.csv", index=False)
    for v, g in D.groupby("variant"):
        day = pd.DatetimeIndex(g.day)
        for lab, msk in (("2018-07..2026 (full data)", day >= "2018-07-01"), ("design 2011-17", day <= "2017-12-31")):
            x = g[np.asarray(msk)]
            r = {"variant": v, "trades": lab, "n": len(x)}
            for mk in masks:
                r[f"avg R [{mk}]"] = x[mk].mean()
                r[f"SL % [{mk}]"] = x[mk + " SL"].mean() * 100
            rows.append(r)
    S = pd.DataFrame(rows)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(S.round(3).to_string())
    S.to_csv(f"{OUT}/mask_summary.csv", index=False)


if __name__ == "__main__":
    main()
