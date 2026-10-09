"""Price data for the zone backtest.

Dukascopy 1-minute BID and ASK candles (already archived in datastore/<PAIR>_<YEAR>.tar and
datastore/<PAIR>.tar) -> 15-minute bid+ask bars, built one calendar year at a time (chunks) and
cached to data/cache/<PAIR>_15m.parquet. 4H bars (UTC 00/04/08/12/16/20) are built from the
15m bars. Daily closes for the 200-day trend benchmark come from the 15m bars, plus 2009
Dukascopy hourly candles to warm up the average.

Only minutes that actually traded (bid tick volume > 0) are used; a 15m bar with no traded
minute does not exist. If a day has no ASK file, ask = bid + the default spread parameter.
"""
from __future__ import annotations

import glob
import lzma
import os
import tarfile
from datetime import date, timedelta

import numpy as np
import pandas as pd

from gjstrat.data import CANDLE_DTYPE, _decode, price_scale

RAW, CACHE, STORE = "data/raw", "data/cache", "datastore"
PAIRS = ("USDJPY", "EURUSD")
PIP = {"USDJPY": 0.01, "EURUSD": 0.0001}
DEFAULT_SPREAD_PIPS = {"USDJPY": 1.0, "EURUSD": 0.8}
COLS = ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]


def restore_raw(sym: str) -> None:
    os.makedirs(RAW, exist_ok=True)
    for path in sorted(glob.glob(f"{STORE}/{sym}_*.tar") + glob.glob(f"{STORE}/{sym}.tar")):
        with tarfile.open(path) as tar:
            members = [m for m in tar.getmembers()
                       if m.isfile() and "/" not in m.name and not os.path.exists(f"{RAW}/{m.name}")]
            tar.extractall(RAW, members=members, filter="data")


def _ohlc15(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    g = df.resample("15min", label="left", closed="left")
    out = pd.DataFrame({f"{prefix}o": g["o"].first(), f"{prefix}h": g["h"].max(),
                        f"{prefix}l": g["l"].min(), f"{prefix}c": g["c"].last()})
    return out


def build_15m_year(sym: str, year: int, start: date, end: date) -> tuple[pd.DataFrame, int]:
    """15m bars for one year. Returns (bars, days with a synthetic ask)."""
    scale = price_scale(sym)
    spread = DEFAULT_SPREAD_PIPS[sym] * PIP[sym]
    bids, asks, synth = [], [], 0
    d = max(start, date(year, 1, 1))
    last = min(end, date(year, 12, 31))
    while d <= last:
        b = _decode(f"{RAW}/{sym}_{d:%Y%m%d}_BID.bi5", scale, d)
        if b is not None:
            b = b[b["v"] > 0]
            if len(b):
                a = _decode(f"{RAW}/{sym}_{d:%Y%m%d}_ASK.bi5", scale, d)
                if a is None or len(a) == 0:
                    a = b[["o", "h", "l", "c"]] + spread
                    synth += 1
                else:
                    a = a.reindex(b.index)
                    miss = a["c"].isna()
                    if miss.any():
                        a.loc[miss, ["o", "h", "l", "c"]] = (b.loc[miss, ["o", "h", "l", "c"]] + spread).to_numpy()
                bids.append(b)
                asks.append(a[["o", "h", "l", "c"]])
        d += timedelta(days=1)
    if not bids:
        return pd.DataFrame(columns=COLS + ["n1m"]), synth
    b = pd.concat(bids)
    a = pd.concat(asks)
    out = _ohlc15(b, "b").join(_ohlc15(a, "a"))
    out["n1m"] = b["o"].resample("15min", label="left", closed="left").count()
    out = out[out["n1m"] > 0]
    return out, synth


def load_15m(sym: str, start: date = date(2009, 12, 31), end: date | None = None,
             refresh: bool = False) -> pd.DataFrame:
    path = f"{CACHE}/{sym}_15m.parquet"
    if os.path.exists(path) and not refresh:
        return pd.read_parquet(path)
    restore_raw(sym)
    if end is None:
        files = sorted(glob.glob(f"{RAW}/{sym}_*_BID.bi5"))
        end = pd.Timestamp(os.path.basename(files[-1]).split("_")[1]).date()
    os.makedirs(CACHE, exist_ok=True)
    parts, synth = [], 0
    for year in range(start.year, end.year + 1):           # one year per chunk
        df, s = build_15m_year(sym, year, start, end)
        parts.append(df)
        synth += s
        print(f"  {sym} {year}: {len(df)} 15m bars", flush=True)
    out = pd.concat(parts)
    out = out[~out.index.duplicated()].sort_index()
    out.attrs["synthetic_ask_days"] = synth
    out.to_parquet(path)
    return out


def to_4h(m15: pd.DataFrame) -> pd.DataFrame:
    """UTC-aligned 4H bars (00, 04, ..., 20). Bars with no 15m data do not exist."""
    g = m15.resample("4h", label="left", closed="left")
    out = pd.DataFrame({"bo": g["bo"].first(), "bh": g["bh"].max(), "bl": g["bl"].min(),
                        "bc": g["bc"].last(), "ao": g["ao"].first(), "ah": g["ah"].max(),
                        "al": g["al"].min(), "ac": g["ac"].last(), "n15": g["bo"].count()})
    return out[out["n15"] > 0]


# --------------------------------------------------------------------------- daily closes
def _hourly_2009(sym: str) -> pd.DataFrame:
    path = f"{CACHE}/{sym}_2009_1h.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    import requests, time
    frames = []
    for month in range(12):
        url = f"https://datafeed.dukascopy.com/datafeed/{sym}/2009/{month:02d}/BID_candles_hour_1.bi5"
        r = None
        for k in range(12):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(min(2 + 2 * k, 30))
        if r is None or r.status_code != 200:
            raise RuntimeError(f"failed: {url}")
        rec = np.frombuffer(lzma.decompress(r.content), dtype=CANDLE_DTYPE)
        idx = pd.Timestamp(2009, month + 1, 1) + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
        frames.append(pd.DataFrame({"c": rec["c"] / price_scale(sym), "v": rec["v"]}, index=idx))
    df = pd.concat(frames)
    df = df[df["v"] > 0]
    os.makedirs(CACHE, exist_ok=True)
    df.to_parquet(path)
    return df


def daily_closes(sym: str, m15: pd.DataFrame) -> pd.Series:
    """Bid close of each UTC weekday (Mon-Fri), 2009 warm-up from hourly candles."""
    h = _hourly_2009(sym)["c"]
    h = h[h.index < m15.index[0].floor("D")]
    d1 = h.groupby(h.index.floor("D")).last()
    d2 = m15["bc"].groupby(m15.index.floor("D")).last()
    s = pd.concat([d1, d2])
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s.index.dayofweek < 5]


def data_gaps(m15: pd.DataFrame) -> dict:
    """Missing 15m bars inside market hours (Sun 22:00 - Fri 21:00 UTC, excluding Dec 25 and
    Jan 1). Gaps of 4+ consecutive missing bars (>= 1 hour) are listed."""
    full = pd.date_range(m15.index[0].floor("D"), m15.index[-1], freq="15min")
    dow, hr = full.dayofweek, full.hour
    open_ = ~((dow == 5) | ((dow == 6) & (hr < 22)) | ((dow == 4) & (hr >= 21)))
    md = full.strftime("%m-%d")
    open_ &= ~np.isin(md, ["12-25", "01-01"])
    expected = full[open_]
    missing = expected.difference(m15.index)
    gaps = []
    if len(missing):
        s = pd.Series(missing)
        brk = s.diff() != pd.Timedelta(minutes=15)
        grp = brk.cumsum()
        for _, g in s.groupby(grp):
            if len(g) >= 4:
                gaps.append((g.iloc[0], len(g)))
    return {"expected_15m_bars": len(expected), "missing_15m_bars": len(missing),
            "gaps_ge_1h": len(gaps), "gaps_ge_1h_list": gaps}
