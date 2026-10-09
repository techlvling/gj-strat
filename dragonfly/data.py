"""Dukascopy 1-minute BID+ASK (already stored in datastore/*.tar) -> 15m and 1H UTC bars.

Dukascopy's datafeed has no native 15m files; 15m candles are the 1m candles aggregated
(first open, max high, min low, last close), which is exactly how its 15m charts are built.
Minutes with zero bid tick volume are flat filler candles and are dropped before aggregating,
so a 15m bar exists only if at least one minute in it traded.

Only files dated >= PHASE1_START are extracted: Phase 1 never touches 2010-2019 data.
The 15m frames are cached to data/cache/<PAIR>_15m.parquet.
"""
from __future__ import annotations

import os
import tarfile
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import load_side

STORE, RAW, CACHE = "datastore", "data/raw", "data/cache"
PHASE1_START = date(2020, 1, 1)
PIP = {"GBPJPY": 0.01, "EURUSD": 0.0001, "USDJPY": 0.01}
SPREAD_PIPS = {"GBPJPY": 2.5, "EURUSD": 0.8}


def _extract(sym: str, start: date, end: date) -> None:
    """Unpack this pair's .bi5 files dated in [start, end] from the committed tars."""
    os.makedirs(RAW, exist_ok=True)
    lo, hi = f"{start:%Y%m%d}", f"{end:%Y%m%d}"
    tars = [f"{STORE}/{sym}_{y}.tar" for y in range(start.year, end.year + 1)] + [f"{STORE}/{sym}.tar"]
    for path in tars:
        if not os.path.exists(path):
            continue
        with tarfile.open(path) as tar:
            members = [m for m in tar.getmembers()
                       if m.isfile() and "/" not in m.name and lo <= m.name.split("_")[1] <= hi
                       and not os.path.exists(f"{RAW}/{m.name}")]
            tar.extractall(RAW, members=members, filter="data")


def _last_file_date(sym: str) -> date:
    with tarfile.open(f"{STORE}/{sym}.tar") as tar:
        return max(date.fromisoformat(f"{n.split('_')[1][:4]}-{n.split('_')[1][4:6]}-{n.split('_')[1][6:8]}")
                   for n in tar.getnames())


def aggregate_15m(bid: pd.DataFrame, ask: pd.DataFrame) -> pd.DataFrame:
    """1m bid/ask (columns o,h,l,c,v) -> 15m bars labelled by their UTC open time.
    Uses only minutes where the bid traded (v > 0); ask is taken at the same minutes."""
    bid = bid[~bid.index.duplicated()]
    ask = ask[~ask.index.duplicated()].reindex(bid.index)
    live = (bid["v"] > 0).to_numpy() & ask["c"].notna().to_numpy()
    b, a = bid[live], ask[live]
    key = b.index.floor("15min")
    agg = {"o": "first", "h": "max", "l": "min", "c": "last"}
    gb = b.groupby(key).agg({**agg, "v": "sum"})
    ga = a.groupby(key).agg(agg)
    out = pd.DataFrame({"bo": gb["o"], "bh": gb["h"], "bl": gb["l"], "bc": gb["c"],
                        "ao": ga["o"], "ah": ga["h"], "al": ga["l"], "ac": ga["c"], "vol": gb["v"]})
    out.index.name = "time"
    return out


def load_15m(sym: str, start: date = PHASE1_START, end: date | None = None,
             refresh: bool = False) -> pd.DataFrame:
    """15m bid+ask bars for `sym`, plus `usd_per_quote` (USD value of 1 unit of quote currency,
    at that bar's close). Cached to parquet."""
    end = end or _last_file_date(sym)
    os.makedirs(CACHE, exist_ok=True)
    path = f"{CACHE}/{sym}_15m_{start:%Y%m%d}_{end:%Y%m%d}.parquet"
    if os.path.exists(path) and not refresh:
        return pd.read_parquet(path)
    _extract(sym, start, end)
    bars = aggregate_15m(load_side(sym, "BID", start, end, RAW), load_side(sym, "ASK", start, end, RAW))
    quote = sym[3:]
    if quote == "USD":
        bars["usd_per_quote"] = 1.0
    elif quote == "JPY":
        uj = load_15m("USDJPY", start, end) if sym != "USDJPY" else bars
        bars["usd_per_quote"] = 1.0 / uj["bc"].reindex(bars.index).ffill().bfill()
    else:
        raise ValueError(f"no USD conversion for {sym}")
    bars.to_parquet(path)
    return bars


def to_hourly(bars15: pd.DataFrame) -> pd.DataFrame:
    """1H bid bars from 15m bars. Bar labelled HH:00 covers HH:00-HH:59 and closes at HH+1:00."""
    g = bars15.groupby(bars15.index.floor("1h"))
    return pd.DataFrame({"o": g["bo"].first(), "h": g["bh"].max(), "l": g["bl"].min(), "c": g["bc"].last()})


def data_gaps(bars15: pd.DataFrame) -> dict:
    """Missing 15m bars outside the weekend close (Fri 21:00 -> Sun 22:00 UTC, covers both DST states)."""
    full = pd.date_range(bars15.index[0], bars15.index[-1], freq="15min").as_unit("ns")
    missing = full.difference(pd.DatetimeIndex(bars15.index).as_unit("ns"))
    dow, hr = missing.dayofweek, missing.hour
    weekend = ((dow == 4) & (hr >= 21)) | (dow == 5) | ((dow == 6) & (hr < 22))
    miss = missing[~weekend]
    # group consecutive missing slots into gap episodes
    if len(miss):
        brk = np.r_[True, np.diff(miss.asi8) != 15 * 60 * 10**9]
        starts = miss[brk]
        lens = np.diff(np.r_[np.flatnonzero(brk), len(miss)])
    else:
        starts, lens = miss, np.array([], dtype=int)
    order = np.argsort(-lens)[:10]
    return {"missing_weekday_15m_bars": int(len(miss)), "gap_episodes": int(len(starts)),
            "gaps_over_1h": int((lens > 4).sum()),
            "largest": [(str(starts[k]), int(lens[k])) for k in order]}
