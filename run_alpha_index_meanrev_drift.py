"""POST-HOC diagnostic for run_alpha_index_meanrev.py (written after seeing its results; NOT a test, does not
change the survival verdict): how much of the long variants' avg R is plain upward drift of the index?
Every long variant earns drift just by being long for 1-10 days, and 2024-26 was a strong bull market.

(1) Unconditional benchmarks with the same machinery (same close series, fills, stops, costs, one position
    at a time, same feature warm-up as the variant they shadow):
      B1  buy every close (sigma60 defined), exit next close, SL 1.5 ATR20      -> compare MR1 / MR2 / MR3
      B4  buy every close (sigma60 defined), exit 5th close, SL 2.0 ATR20       -> compare MR4
      B5  buy every close with C > SMA200, exit first later close > SMA5 (cap 10), SL 2.0 ATR20 -> MR5 / MR6 / MR7
      B8  buy every close (RSI2 defined), exit first later close > SMA5 (cap 10), SL 2.0 ATR20 -> MR8
      B9  buy every close (previous close defined), exit next close, SL 1.0 ATR20 -> MR9
(2) Analytic drift per trade of every variant: mu = mean log close-to-close return per calendar day of
    that market in that period (design / check / holdout), drift R = sign x mu x calendar days held x
    entry price / stop distance; excess R = R - drift R (in-period mu: a benchmark, not a rule).

    python run_alpha_index_meanrev_drift.py       # appends a section to results/alpha_hunt/index_meanrev/REPORT.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import run_alpha_index_meanrev as M
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = M.OUT
BENCH = {"B1": ("BUY", 1.5, "every close, exit next close"), "B4": ("BUY", 2.0, "every close, exit 5th close"),
         "B5": ("BUY", 2.0, "every close with C > SMA200, exit C > SMA5 (cap 10)"),
         "B8": ("BUY", 2.0, "every close, exit C > SMA5 (cap 10)"), "B9": ("BUY", 1.0, "every close (previous close defined), exit next close")}
SHADOW = {"MR1": "B1", "MR2": "B1", "MR3": "B1", "MR4": "B4", "MR5": "B5", "MR6": "B5", "MR7": "B5", "MR8": "B8", "MR9": "B9"}


def bench_plan(cs, execute):
    C, seg, n = cs.C.to_numpy(), cs.seg.to_numpy(), len(cs)
    f = lambda col: cs[col].to_numpy(dtype=float)
    s60, rsi, s200, s5, atr, prevC = f("sig60"), f("rsi2"), f("sma200"), f("sma5"), f("atr20"), f("prevC")

    def kth(j, k):
        jj = j + k
        return jj if jj < n and seg[jj] == seg[j] else None

    def first(j, cond, cap):
        for k in range(1, cap + 1):
            jj = j + k
            if jj >= n or seg[jj] != seg[j]:
                return None
            if cond(jj):
                return jj
        return j + cap

    with np.errstate(invalid="ignore"):
        rules = {"B1": (np.isfinite(s60), lambda j: kth(j, 1)), "B4": (np.isfinite(s60), lambda j: kth(j, 5)),
                 "B5": (C > s200, lambda j: first(j, lambda x: C[x] > s5[x], 10)),
                 "B8": (np.isfinite(rsi), lambda j: first(j, lambda x: C[x] > s5[x], 10)),
                 "B9": (np.isfinite(prevC), lambda j: kth(j, 1))}
    out = {}
    for v, (ent, ex) in rules.items():
        side, slm, _ = BENCH[v]
        busy, trades = -1, []
        for j in np.flatnonzero(ent):
            if j <= busy or not atr[j] > 0:
                continue
            jx = ex(j)
            if jx is None:
                continue
            t = execute(v, j, jx, side, slm)
            if t is None:
                continue
            trades.append(t)
            busy = jx
        out[v] = trades
    return out


def period_of(day):
    for p, (a, b) in PER.items():
        if pd.Timestamp(a) <= day <= pd.Timestamp(b):
            return p
    return None


def drift_mu(cl: pd.DataFrame) -> dict:
    """Mean log return per calendar day, per period, within segments."""
    c = cl.copy()
    c["r"] = np.log(c.C / c.C.shift(1)).where(c.seg == c.seg.shift(1))
    c["days"] = pd.Series(c.index, index=c.index).diff().dt.days.where(c.seg == c.seg.shift(1))
    c = c.dropna(subset=["r"])
    out = {}
    for p, (a, b) in PER.items():
        x = c[(c.index >= pd.Timestamp(a)) & (c.index <= pd.Timestamp(b))]
        out[p] = x.r.sum() / x.days.sum() if len(x) else np.nan
    return out


def main():
    M.plan = bench_plan                                   # run the same pipeline with the benchmark rules
    vix, vmed = M.load_vix()
    bt, closes = [], {}
    for sym in ["USATECHIDXUSD", "JPNIDXJPY", "XAUUSD"]:
        t, c, _ = M.run_minute(sym, vix, vmed)
        bt.append(t); closes[sym] = c
    t, c, _ = M.run_spx(vix, vmed)
    bt.append(t); closes["USA500IDXUSD"] = c
    B = pd.concat(bt, ignore_index=True)
    B["day"] = pd.to_datetime(B.day)
    B.to_csv(f"{OUT}/drift_benchmarks_trades.csv", index=False)
    T = pd.read_pickle(f"{OUT}/trades.pkl")
    mus = {s: drift_mu(closes[s]) for s in closes}

    # analytic drift per trade
    hold = (pd.DatetimeIndex(T.exit_ts) - pd.DatetimeIndex(T.entry_ts)).total_seconds().to_numpy() / 86400
    per = [period_of(d) for d in T.day]
    mu = np.array([mus[s].get(p, np.nan) if p else np.nan for s, p in zip(T.market, per)])
    sgn = np.where(T.side == "BUY", 1.0, -1.0)
    T["drift R"] = sgn * mu * hold * T.entry.to_numpy() / T.risk.to_numpy()
    T["excess R"] = T.R - T["drift R"]
    T["period"] = per

    rows = []
    for sym in ["USATECHIDXUSD", "USA500IDXUSD", "JPNIDXJPY", "XAUUSD"]:
        for v in list(M.VARIANTS) + list(BENCH):
            src = B if v in BENCH else T
            g = src[(src.market == sym) & (src.variant == v)]
            row = {"market": M.NAMES[sym], "test": v, "trades": len(g), "avg R": g.R.mean()}
            for p in PER:
                x = g[[period_of(d) == p for d in g.day]]
                row[f"{p} avg R"] = x.R.mean() if len(x) else np.nan
                if v not in BENCH:
                    row[f"{p} excess R"] = x["excess R"].mean() if len(x) else np.nan
                    row[f"{p} excess t"] = tstat(x["excess R"].to_numpy()) if len(x) else np.nan
            if v in SHADOW:
                bg = B[(B.market == sym) & (B.variant == SHADOW[v])]
                row["benchmark"] = SHADOW[v]
                row["avg R minus benchmark"] = g.R.mean() - bg.R.mean()
            rows.append(row)
    D = pd.DataFrame(rows)
    D.to_csv(f"{OUT}/drift.csv", index=False)
    mu_tab = pd.DataFrame(mus).T * 365 * 100
    mu_tab.index = [M.NAMES[s] for s in mu_tab.index]
    mu_tab.index.name = "market"
    mu_tab.columns = [f"{c} drift %/yr (log)" for c in mu_tab.columns]

    bcols = ["trades", "avg R", "design avg R", "check avg R", "holdout avg R"]
    vcols = ["trades", "avg R", "benchmark", "avg R minus benchmark", "design excess R", "design excess t",
             "check excess R", "check excess t", "holdout excess R", "holdout excess t"]
    txt = ["\n## Post-hoc diagnostic: how much is plain index drift? (run_alpha_index_meanrev_drift.py)\n",
           "Written after seeing the results; not a test and does not change the verdict. (1) Unconditional long "
           "benchmarks through the same pipeline (same closes, fills, stops, costs, one position at a time). (2) Per trade, "
           "drift R = in-period mean log return per calendar day x days held x entry / stop; excess R = R - drift R.\n",
           "### Index drift by period\n", fmt_table(mu_tab, ".1f"), "\n",
           "### Unconditional benchmarks\n" + "\n".join(f"- {k}: {v[2]}, SL {v[1]} x ATR20" for k, v in BENCH.items()) + "\n",
           fmt_table(D[D.test.isin(list(BENCH))].set_index("market")[["test"] + bcols], ".3f"), "\n",
           "### Variants: avg R minus benchmark, and drift-adjusted (excess) R per period\n",
           fmt_table(D[~D.test.isin(list(BENCH))].set_index("market")[["test"] + vcols], ".3f"), "\n"]
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n".join(txt))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(mu_tab.round(1).to_string())
    print(D[D.test.isin(list(BENCH))][["market", "test"] + bcols].round(3).to_string())
    print(D[~D.test.isin(list(BENCH))][["market", "test"] + vcols].round(3).to_string())
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
