"""Equity-index calendar anomalies on the Nasdaq 100 CFD (USATECHIDXUSD), replicated on the S&P 500
CFD (USA500IDXUSD) when its data is present. Times New York (daylight saving aware); NYSE trading days.
Fixed before running (7 tests per index), "close" = the 15:55 NY bar, entries at market, all long except E4:
  E1a turn of month: buy at the close of the 2nd-to-last trading day, sell at the close of the 3rd
      trading day of the next month; SL 1 x ATR20.   E1b: buy at the close of the last trading day instead.
  E2a overnight: buy at the close, sell at 09:35 the next trading day; SL 0.5 x ATR20.
      E2b: weeknights only (next trading day is the next calendar day).
  E3  pre-holiday: buy at the close two trading days before an NYSE holiday, sell at the close of the
      day before it; SL 0.5 x ATR20.
  E4a intraday momentum (Gao et al. 2018): at 15:30 trade in the direction of the 09:30-10:00 move,
      exit 15:59; SL 0.25 x ATR20.  E4b: only when |09:30-10:00 move| >= its median of the previous 60 days.
Costs: bid/ask, 0.25 point slippage per stop fill, financing 3%/yr per rollover night (run_box_indices).
Survives (Nasdaq): design (data start-2017) t >= 2 and avg R > 0 in 2018-23 and 2024-26; and, if S&P data
exists, S&P avg R > 0 over the whole period (replication).

    python run_index_anomalies.py                 # Nasdaq (+ S&P once data/usa500idxusd_*.npz exists)
    WITH_SPX=1 python run_index_anomalies.py      # build the S&P cache from data/raw first
"""
import os
from datetime import date

import holidays
import numpy as np
import pandas as pd

import run_box_indices
from gjstrat.data import build_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from run_backtest import fmt_table
from run_box_indices import net_r
from run_usdjpy_sl import tstat

OUT = "results/index_anomalies"
run_box_indices.SLIP.setdefault("USA500IDXUSD", 0.25)
PER = {"design": ("2011-01-01", "2017-12-31"), "check": ("2018-01-01", "2023-12-31"), "holdout": ("2024-01-01", "2026-12-31")}
MARKETS = {"USATECHIDXUSD": ("2011-01-02", "data/usatechidxusd_2011-01-02_2026-10-07.npz"),
           "USA500IDXUSD": ("2011-01-01", "data/usa500idxusd_2011-01-01_2026-10-07.npz")}


def nyse_days(a, b):
    hol = set(holidays.NYSE(years=range(a.year, b.year + 1)))
    days = pd.bdate_range(a, b)
    return pd.DatetimeIndex([x for x in days if x.date() not in hol]), hol


def live_at(m, i):
    """First traded minute in [i, i+5), else -1."""
    if i < 0 or i + 5 >= m.n:
        return -1
    w = np.flatnonzero(m.vol[i: i + 5] > 0)
    return i + w[0] if len(w) else -1


def sig(m, day, side, i, j, sl, tag):
    s = live_at(m, i)
    if s < 0 or j <= s + 1 or j >= m.n or not sl > 0:
        return None
    return Signal(day, side, s, "market", None, s + 1, sl, None, j, tag)


def build(m, d):
    days, hol = nyse_days(pd.Timestamp("2011-01-03"), d.index.max())
    atr = d["atr20"]
    close = lambda x: local_idx(m, x, 15, 55, NY)
    out = {k: [] for k in ("E1a turn of month", "E1b turn of month (from last day)", "E2a overnight", "E2b overnight, weeknights",
                           "E3 pre-holiday", "E4a intraday momentum", "E4b intraday momentum, strong first half-hour")}
    pos = pd.Series(np.arange(len(days)), index=days)
    mon = days.to_period("M")
    last_idx = pos.groupby(mon).max()
    for k, mo in enumerate(last_idx.index[:-1]):           # turn of month
        li = last_idx.iloc[k]
        nxt = pos[mon == last_idx.index[k + 1]]
        if li < 1 or len(nxt) < 3:
            continue
        exit_day = days[nxt.iloc[2]]
        for name, ent in (("E1a turn of month", days[li - 1]), ("E1b turn of month (from last day)", days[li])):
            a = atr.get(ent, np.nan)
            s = sig(m, ent, "BUY", close(ent), close(exit_day), 1.0 * a, name)
            if s:
                out[name].append(s)
    move = {}
    for n, day in enumerate(days[:-1]):                     # overnight, pre-holiday, intraday momentum
        nd = days[n + 1]
        a = atr.get(day, np.nan)
        s = sig(m, day, "BUY", close(day), local_idx(m, nd, 9, 35, NY), 0.5 * a, "E2a")
        if s:
            out["E2a overnight"].append(s)
            if (nd - day).days == 1:
                out["E2b overnight, weeknights"].append(s)
        h = nd + pd.Timedelta(days=1)
        while h.dayofweek >= 5:
            h += pd.Timedelta(days=1)
        if h.date() in hol and n + 1 < len(days):            # nd is the last trading day before a holiday
            s = sig(m, day, "BUY", close(day), close(nd), 0.5 * atr.get(day, np.nan), "E3")
            if s:
                out["E3 pre-holiday"].append(s)
        i0, i1, i2 = local_idx(m, day, 9, 30, NY), local_idx(m, day, 10, 0, NY), local_idx(m, day, 15, 30, NY)
        a0, a1 = live_at(m, i0), live_at(m, i1)
        if a0 < 0 or a1 < 0:
            continue
        mv = m.bo[a1] - m.bo[a0]
        move[day] = abs(mv) / m.bo[a0]
        if mv == 0:
            continue
        side = "BUY" if mv > 0 else "SELL"
        s = sig(m, day, side, i2, local_idx(m, day, 15, 59, NY), 0.25 * atr.get(day, np.nan), "E4")
        if s:
            out["E4a intraday momentum"].append(s)
            hist = pd.Series(move).iloc[-61:-1]
            if len(hist) == 60 and move[day] >= hist.median():
                out["E4b intraday momentum, strong first half-hour"].append(s)
    return out


def evaluate(sym):
    start, cache = MARKETS[sym]
    s0 = date.fromisoformat(start)
    m = build_market(sym, s0, date(2026, 10, 7), "data/raw", cache)
    d = daily_table(m)
    rows, trades = [], {}
    for name, sigs in build(m, d).items():
        tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
        r = net_r(m, sym, tr) if tr else np.array([])
        day = pd.DatetimeIndex([t.day for t in tr])
        wins, losses = r[r > 0], r[r <= 0]
        row = {"index": sym, "test": name, "trades": len(r), "win %": (r > 0).mean() * 100 if len(r) else np.nan,
               "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
               "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}
        for p, (a, b) in PER.items():
            v = r[np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b)))]
            row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v)})
        rows.append(row)
        trades[name] = (tr, r)
        print(sym, name, len(r), round(np.nanmean(r), 3) if len(r) else None, flush=True)
    return pd.DataFrame(rows), trades, m


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    tabs = []
    for sym, (start, cache) in MARKETS.items():
        have = os.path.exists(cache) or sym == "USATECHIDXUSD" or os.environ.get("WITH_SPX") == "1"
        if not have:
            print("no data for", sym)
            continue
        tabs.append(evaluate(sym)[0])
    T = pd.concat(tabs, ignore_index=True)
    nq = T[T["index"] == "USATECHIDXUSD"].set_index("test")
    sp = T[T["index"] == "USA500IDXUSD"].set_index("test") if (T["index"] == "USA500IDXUSD").any() else None
    nq["survives"] = (nq["design t"] >= 2) & (nq["check avg R"] > 0) & (nq["holdout avg R"] > 0)
    if sp is not None:
        nq["S&P avg R"] = sp["avg R"]
        nq["survives"] &= nq["S&P avg R"] > 0
    T.to_csv(f"{OUT}/all.csv", index=False)
    cols = ["trades", "win %", "avg win / avg loss", "avg R", "design n", "design avg R", "design t", "check avg R", "check t",
            "holdout avg R", "holdout t"] + (["S&P avg R"] if sp is not None else []) + ["survives"]
    txt = ("# Equity-index calendar anomalies (Nasdaq 100, S&P 500 replication)\n\nRules in run_index_anomalies.py "
           f"(fixed before running).\n\n**Survivors: {int(nq.survives.sum())} of {len(nq)}**\n\n## Nasdaq 100\n\n" + fmt_table(nq[cols], ".3f"))
    if sp is not None:
        txt += "\n\n## S&P 500\n\n" + fmt_table(sp[cols[:-2]], ".3f")
    open(f"{OUT}/REPORT.md", "w").write(txt + "\n")
    pd.set_option("display.width", 250)
    print(nq[cols].round(3).to_string())
    if sp is not None:
        print(sp[cols[:-2]].round(3).to_string())
