"""Dukascopy USATECHIDXUSD 1-minute BID + ASK candles -> one parquet file per year, ET clock.

Instrument: Dukascopy "USATECH.IDX/USD" (feed symbol USATECHIDXUSD), the Nasdaq 100 index CFD.
Raw files come from gjstrat.data (one LZMA .bi5 per UTC day and side, cached in data/raw, packed in
datastore/USATECHIDXUSD_<YEAR>.tar). Dukascopy writes a flat candle with volume 0 for every
minute without ticks (weekends, the 17:00-18:00 ET break); those rows are dropped, so a row in
the cache is a minute that really traded.

Volume is Dukascopy's candle volume on the BID side: tick activity reported by the broker's feed,
not exchange volume.

Each year is decoded, converted and written on its own (chunks); the backtest reads one year at a
time plus a few days of the previous year for the first overnight windows.
"""
from __future__ import annotations

import glob
import os
import tarfile
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from gjstrat.data import _decode, download

SYM = "USATECHIDXUSD"
NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
RAW = "data/raw"
PARQ = "data/nq_parquet"
STORE = "datastore"
SCALE = 1000.0                       # Dukascopy index prices are integers x 1000
COLS = ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "v"]


def to_et(ts_utc: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """UTC -> America/New_York (zoneinfo, DST handled)."""
    if ts_utc.tz is None:
        ts_utc = ts_utc.tz_localize(UTC)
    return ts_utc.tz_convert(NY)


def et_wall_clock(ts_utc: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Naive New York wall-clock times (what '18:00', '09:30' and '16:00' refer to)."""
    return to_et(ts_utc).tz_localize(None)


def restore_raw(years: range, raw_dir: str = RAW) -> None:
    """Unpack the committed per-year tars (and the catch-all tar) into data/raw."""
    os.makedirs(raw_dir, exist_ok=True)
    tars = [f"{STORE}/{SYM}_{y}.tar" for y in years] + [f"{STORE}/{SYM}.tar"]
    for path in tars:
        if not os.path.exists(path):
            continue
        with tarfile.open(path) as tar:
            members = [m for m in tar.getmembers()
                       if m.isfile() and "/" not in m.name and not os.path.exists(f"{raw_dir}/{m.name}")]
            tar.extractall(raw_dir, members=members, filter="data")


def fetch_missing(start: date, end: date, raw_dir: str = RAW) -> None:
    """Download any day/side not already cached (Dukascopy throttles; gjstrat retries with backoff)."""
    download(SYM, start, end, raw_dir, workers=1)


def decode_year(year: int, raw_dir: str = RAW, spread_if_no_ask: float = 1.0) -> tuple[pd.DataFrame, bool]:
    """All traded minutes of one UTC year: bid OHLC, ask OHLC, bid volume, UTC index."""
    frames, has_ask = [], True
    d, end = date(year, 1, 1), date(year, 12, 31)
    while d <= end:
        bid = _decode(os.path.join(raw_dir, f"{SYM}_{d:%Y%m%d}_BID.bi5"), SCALE, d)
        if bid is not None:
            ask = _decode(os.path.join(raw_dir, f"{SYM}_{d:%Y%m%d}_ASK.bi5"), SCALE, d)
            bid = bid[bid["v"] > 0]
            df = bid.rename(columns={"o": "bo", "h": "bh", "l": "bl", "c": "bc"})
            if ask is not None:
                ask = ask.reindex(bid.index)
                df["ao"], df["ah"], df["al"], df["ac"] = ask["o"], ask["h"], ask["l"], ask["c"]
            else:
                has_ask = False
                for s in "ohlc":
                    df["a" + s] = df["b" + s] + spread_if_no_ask
            frames.append(df[COLS])
        d += timedelta(days=1)
    if not frames:
        return pd.DataFrame(columns=COLS), has_ask
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    df.index = df.index.tz_localize(UTC)
    return df, has_ask


def build_year(year: int, raw_dir: str = RAW, out_dir: str = PARQ, force: bool = False) -> str:
    """data/nq_parquet/USATECHIDXUSD_<year>.parquet with ts_utc, ts_et and the bid/ask columns."""
    os.makedirs(out_dir, exist_ok=True)
    path = f"{out_dir}/{SYM}_{year}.parquet"
    if os.path.exists(path) and not force:
        return path
    df, has_ask = decode_year(year, raw_dir)
    out = df.copy()
    out.insert(0, "ts_et", to_et(df.index))
    out.insert(0, "ts_utc", df.index)
    out["has_ask"] = has_ask
    out.reset_index(drop=True).to_parquet(path + ".part", index=False)
    os.replace(path + ".part", path)
    return path


def load_year(year: int, out_dir: str = PARQ) -> pd.DataFrame:
    """One cached year, indexed by naive ET wall-clock time (the clock every rule uses)."""
    df = pd.read_parquet(f"{out_dir}/{SYM}_{year}.parquet")
    df.index = et_wall_clock(pd.DatetimeIndex(df["ts_utc"]))
    df.index.name = "et"
    if not df.index.is_monotonic_increasing:     # only possible in the repeated 01:00 hour in Nov
        df = df.sort_index(kind="stable")
    return df


def load_chunk(year: int, overlap_days: int = 4, out_dir: str = PARQ) -> pd.DataFrame:
    """A year plus the last `overlap_days` of the previous year (for January's overnight windows)."""
    df = load_year(year, out_dir)
    prev = f"{out_dir}/{SYM}_{year - 1}.parquet"
    if os.path.exists(prev):
        p = load_year(year - 1, out_dir)
        p = p[p.index >= pd.Timestamp(year, 1, 1) - pd.Timedelta(days=overlap_days)]
        df = pd.concat([p, df])
    return df


def available_years(out_dir: str = PARQ) -> list[int]:
    return sorted(int(os.path.basename(p)[len(SYM) + 1:-8]) for p in glob.glob(f"{out_dir}/{SYM}_*.parquet"))


def mid(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Mid OHLC = average of the bid and ask candles (used for every signal; fills use bid/ask)."""
    return {s: ((df["b" + s] + df["a" + s]) / 2).to_numpy(np.float64) for s in "ohlc"}
