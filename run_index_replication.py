"""Replication of the Nasdaq calendar effects that were positive in every period (run_index_anomalies.py):
E1a / E1b turn of month and E3 pre-holiday, on
  * S&P 500 (USA500IDXUSD): hourly bid closes (data/hourly, fetch_hourly.py); net % return close-to-close
    minus 1 index point (spread + slippage) and 3%/yr financing per calendar night.
  * Nikkei 225 (JPNIDXJPY): minute data, same rules as the Nasdaq test with Tokyo time and the Japanese
    market calendar (national holidays + Dec 31, Jan 2-3); "close" = 14:55 JST; SL 1 / 0.5 x ATR20.
Pre-declared: an effect replicates on a market if its average net result over the whole period is > 0.

    python run_index_replication.py
"""
import glob
import lzma
import os
from datetime import date

import holidays
import numpy as np
import pandas as pd

from gjstrat.data import CANDLE_DTYPE, build_market
from gjstrat.patterns import Signal, daily_table, local_idx, simulate
from run_backtest import fmt_table
from run_box_indices import net_r
from run_index_anomalies import PER, live_at
from run_usdjpy_sl import tstat

OUT = "results/index_anomalies"
NY, TKY = "America/New_York", "Asia/Tokyo"
TESTS = ("E1a turn of month", "E1b turn of month (from last day)", "E3 pre-holiday")


def calendar_trades(days, hol):
    """(test, entry day, exit day) for the three effects on a trading-day list."""
    out = []
    pos = pd.Series(np.arange(len(days)), index=days)
    mon = days.to_period("M")
    last = pos.groupby(mon).max()
    for k in range(len(last) - 1):
        li = last.iloc[k]
        nxt = pos[mon == last.index[k + 1]]
        if li < 1 or len(nxt) < 3:
            continue
        out += [(TESTS[0], days[li - 1], days[nxt.iloc[2]]), (TESTS[1], days[li], days[nxt.iloc[2]])]
    for n in range(1, len(days) - 1):
        h = days[n] + pd.Timedelta(days=1)
        while h.dayofweek >= 5:
            h += pd.Timedelta(days=1)
        if h.date() in hol:
            out.append((TESTS[2], days[n - 1], days[n]))
    return out


def spx():
    files = sorted(glob.glob("data/hourly/USA500IDXUSD/*.bi5"))
    parts = []
    for f in files:
        y, mth = map(int, os.path.basename(f)[:-4].split("_"))
        raw = open(f, "rb").read()
        if not raw:
            continue
        rec = np.frombuffer(lzma.decompress(raw), dtype=CANDLE_DTYPE)
        t0 = pd.Timestamp(year=y, month=mth, day=1)
        parts.append(pd.Series(rec["c"] / 1000.0, index=t0 + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")))
    px = pd.concat(parts).sort_index()
    loc = px.index.tz_localize("UTC").tz_convert(NY)
    bar = px[(loc.hour == 15)]                                 # hourly bar 15:00-16:00 NY: its close ~ 16:00
    close = pd.Series(bar.to_numpy(), index=loc[loc.hour == 15].tz_localize(None).normalize())
    close = close[~close.index.duplicated()]
    days_all = pd.bdate_range("2012-01-01", "2026-10-06")
    hol = set(holidays.NYSE(years=range(2012, 2027)))
    days = pd.DatetimeIndex([d for d in days_all if d.date() not in hol and d in close.index])
    rows = []
    for test, a, b in calendar_trades(days, hol):
        pa, pb = close.get(a, np.nan), close.get(b, np.nan)
        if np.isnan(pa) or np.isnan(pb):
            continue
        net = (pb - pa - 1.0) / pa * 100 - 3.0 / 365 * (b - a).days
        rows.append({"test": test, "day": a, "net %": net})
    return pd.DataFrame(rows)


def nikkei():
    m = build_market("JPNIDXJPY", date(2011, 1, 2), date(2026, 10, 7), "data/raw", "data/jpnidxjpy_2011-01-02_2026-10-07.npz")
    d = daily_table(m)
    yrs = range(2011, 2027)
    hol = set(holidays.Japan(years=yrs)) | {date(y, 12, 31) for y in yrs} | {date(y, 1, k) for y in yrs for k in (2, 3)}
    days = pd.DatetimeIndex([x for x in pd.bdate_range("2011-10-01", d.index.max()) if x.date() not in hol])
    close = lambda x: local_idx(m, x, 14, 55, TKY)
    sigs = []
    for test, a, b in calendar_trades(days, hol):
        s = live_at(m, close(a))
        sl = (1.0 if test != TESTS[2] else 0.5) * d["atr20"].get(a, np.nan)
        if s < 0 or not sl > 0 or close(b) >= m.n:
            continue
        sigs.append((test, Signal(a, "BUY", s, "market", None, s + 1, sl, None, close(b), test)))
    rows = []
    for test in TESTS:
        tr = sorted([t for t in (simulate(m, s) for name, s in sigs if name == test) if t is not None],
                    key=lambda t: (t.exit_i, t.entry_i))
        r = net_r(m, "JPNIDXJPY", tr)
        rows += [{"test": test, "day": t.day, "R": x} for t, x in zip(tr, r)]
    return pd.DataFrame(rows)


def summarise(df, col, market):
    out = []
    for test, g in df.groupby("test"):
        x, day = g[col].to_numpy(), pd.DatetimeIndex(g["day"])
        row = {"market": market, "test": test, "trades": len(x), "win %": (x > 0).mean() * 100, f"avg {col}": x.mean(), "t": tstat(x)}
        for p, (a, b) in PER.items():
            v = x[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))]
            row[f"{p} avg"] = v.mean() if len(v) else np.nan
        row["replicates"] = bool(x.mean() > 0)
        out.append(row)
    return pd.DataFrame(out).set_index(["market", "test"])


if __name__ == "__main__":
    S = summarise(spx(), "net %", "S&P 500 (net % per trade)")
    N = summarise(nikkei(), "R", "Nikkei 225 (R per trade)")
    S.to_csv(f"{OUT}/replication_spx.csv"); N.to_csv(f"{OUT}/replication_nikkei.csv")
    with open(f"{OUT}/REPORT.md", "a") as f:
        f.write("\n## Replication (run_index_replication.py)\n\n### S&P 500, hourly closes\n\n" + fmt_table(S.droplevel(0), ".3f")
                + "\n\n### Nikkei 225, minute data\n\n" + fmt_table(N.droplevel(0), ".3f") + "\n")
    pd.set_option("display.width", 250)
    print(S.round(3).to_string()); print(N.round(3).to_string())
