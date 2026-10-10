"""Market data: Dukascopy 1-minute BID/ASK candles -> continuous UTC minute grid.

Dukascopy serves one LZMA-compressed file per instrument/day/side:
    https://datafeed.dukascopy.com/datafeed/{SYM}/{YYYY}/{MM-1:02d}/{DD:02d}/{BID|ASK}_candles_min_1.bi5
Each record is big-endian: int32 seconds-from-midnight, int32 open, close, low, high
(price * 1000 for JPY pairs), float32 volume. Minutes without ticks come back as flat
candles with volume 0, so volume is what tells us whether a minute really traded.

Everything is put on one gap-free UTC minute grid so a timestamp maps to an index with
plain arithmetic. Missing minutes are forward-filled flat with volume 0.
"""
from __future__ import annotations

import lzma
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
CANDLE_DTYPE = np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"),
                         ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
MINORS = ["EURGBP", "EURJPY", "GBPJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD", "GBPCHF",
          "GBPAUD", "GBPCAD", "GBPNZD", "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF", "CADJPY",
          "CHFJPY", "NZDJPY", "NZDCAD", "NZDCHF", "CADCHF"]


def price_scale(sym: str) -> float:
    """Dukascopy stores prices as integers: 3 decimals for JPY pairs, gold and indices, 5 for the rest."""
    return 1000.0 if sym.endswith("JPY") or sym.startswith("XAU") or "IDX" in sym else 100000.0


@dataclass
class Market:
    """Minute grid. Index i is the bar that opens at t0 + i minutes (UTC)."""
    t0: pd.Timestamp
    bo: np.ndarray
    bh: np.ndarray
    bl: np.ndarray
    bc: np.ndarray
    ao: np.ndarray
    ah: np.ndarray
    al: np.ndarray
    ac: np.ndarray
    vol: np.ndarray          # bid tick volume; 0 = no real trading that minute
    quote_per_usd: np.ndarray  # units of the quote currency per 1 USD (1 for XXXUSD), ffilled
    has_ask: bool = True
    pip: float = 0.01        # 0.01 for JPY pairs, 0.0001 otherwise

    @property
    def n(self) -> int:
        return len(self.bo)

    def idx(self, ts: pd.Timestamp) -> int:
        return int((ts - self.t0) // pd.Timedelta(minutes=1))

    def ts(self, i: int) -> pd.Timestamp:
        return self.t0 + pd.Timedelta(minutes=int(i))


# --------------------------------------------------------------------------- download
def _url(sym: str, d: date, side: str) -> str:
    return f"{BASE_URL}/{sym}/{d.year}/{d.month - 1:02d}/{d.day:02d}/{side}_candles_min_1.bi5"


def _fetch(session: requests.Session, url: str, path: str) -> str:
    if os.path.exists(path):
        return "cached"
    for attempt in range(30):
        try:
            r = session.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 404:
                open(path, "wb").close()          # no file for that day (holiday / future)
                return "404"
            if r.status_code in (429, 500, 502, 503, 504):   # Dukascopy throttles hard
                time.sleep(min(2 ** attempt, 60) + random.random())
                continue
            r.raise_for_status()
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(r.content)
            os.replace(tmp, path)
            return "ok"
        except requests.RequestException:
            time.sleep(min(2 ** attempt, 60) + random.random())
    raise RuntimeError(f"failed to download {url}")


def download(sym: str, start: date, end: date, raw_dir: str, sides=("BID", "ASK"),
             workers: int = 4) -> None:
    os.makedirs(raw_dir, exist_ok=True)
    jobs = []
    d = start
    while d <= end:
        for side in sides:
            jobs.append((_url(sym, d, side), os.path.join(raw_dir, f"{sym}_{d:%Y%m%d}_{side}.bi5")))
        d += timedelta(days=1)
    with requests.Session() as s, ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda j: _fetch(s, *j), jobs))
    print(f"{sym}: {len(jobs)} files, {results.count('ok')} downloaded, "
          f"{results.count('cached')} cached, {results.count('404')} not on server")


def _decode(path: str, scale: float, day: date) -> pd.DataFrame | None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    raw = lzma.decompress(open(path, "rb").read())
    if not raw:
        return None
    rec = np.frombuffer(raw, dtype=CANDLE_DTYPE)
    idx = pd.Timestamp(day) + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
    return pd.DataFrame({"o": rec["o"] / scale, "h": rec["h"] / scale, "l": rec["l"] / scale,
                         "c": rec["c"] / scale, "v": rec["v"].astype(np.float64)}, index=idx)


def load_side(sym: str, side: str, start: date, end: date, raw_dir: str) -> pd.DataFrame:
    frames = []
    d = start
    while d <= end:
        df = _decode(os.path.join(raw_dir, f"{sym}_{d:%Y%m%d}_{side}.bi5"), price_scale(sym), d)
        if df is not None:
            frames.append(df)
        d += timedelta(days=1)
    if not frames:
        raise RuntimeError(f"no {sym} {side} data in {raw_dir}")
    return pd.concat(frames).sort_index()


# --------------------------------------------------------------------------- grid
def to_grid(bid: pd.DataFrame, ask: pd.DataFrame | None, conv: pd.Series | float | None,
            spread_pips: float = 2.5, pip: float = 0.01) -> Market:
    """Reindex onto a continuous minute grid. If ask is None, ask = bid + spread_pips."""
    t0 = bid.index[0].floor("D")
    grid = pd.date_range(t0, bid.index[-1], freq="1min")

    def fill(df: pd.DataFrame) -> pd.DataFrame:
        df = df[~df.index.duplicated()].reindex(grid)
        df["v"] = df["v"].fillna(0.0)
        df["c"] = df["c"].ffill().bfill()
        for col in ("o", "h", "l"):
            df[col] = df[col].fillna(df["c"])
        return df

    b = fill(bid.copy())
    if ask is not None:
        a = fill(ask.copy())
        has_ask = True
    else:
        a = b[["o", "h", "l", "c"]] + spread_pips * pip
        has_ask = False
    if isinstance(conv, pd.Series):
        uj = conv[~conv.index.duplicated()].reindex(grid).ffill().bfill().to_numpy()
    else:
        uj = np.full(len(grid), 150.0 if conv is None else float(conv))
    f = lambda s: np.ascontiguousarray(s.to_numpy(dtype=np.float64))
    return Market(t0=t0, bo=f(b["o"]), bh=f(b["h"]), bl=f(b["l"]), bc=f(b["c"]),
                  ao=f(a["o"]), ah=f(a["h"]), al=f(a["l"]), ac=f(a["c"]),
                  vol=f(b["v"]), quote_per_usd=uj.astype(np.float64), has_ask=has_ask,
                  pip=pip)


def save_market(m: Market, path: str) -> None:
    np.savez_compressed(path, t0=np.array(str(m.t0)), bo=m.bo, bh=m.bh, bl=m.bl, bc=m.bc,
                        ao=m.ao, ah=m.ah, al=m.al, ac=m.ac, vol=m.vol,
                        quote_per_usd=m.quote_per_usd, has_ask=np.array(m.has_ask),
                        pip=np.array(m.pip))


def load_market(path: str) -> Market:
    z = np.load(path)
    return Market(t0=pd.Timestamp(str(z["t0"])), bo=z["bo"], bh=z["bh"], bl=z["bl"], bc=z["bc"],
                  ao=z["ao"], ah=z["ah"], al=z["al"], ac=z["ac"], vol=z["vol"],
                  quote_per_usd=z["quote_per_usd"] if "quote_per_usd" in z else z["usdjpy"],
                  has_ask=bool(z["has_ask"]), pip=float(z["pip"]) if "pip" in z else 0.01)


def contract_size(sym: str) -> float:
    """Units per 1.0 lot: 100 oz for gold, 100k base units for FX."""
    return 100.0 if sym.startswith("XAU") else 100_000.0


def pip_size(sym: str) -> float:
    """0.01 for JPY pairs and gold (Dukascopy's gold pip = 1 cent), 0.0001 otherwise."""
    if "IDX" in sym:
        return 1.0                     # index CFDs (JPNIDXJPY, USATECHIDXUSD): 1 index point
    return 0.01 if sym.endswith("JPY") or sym.startswith("XAU") else 0.0001


def build_market(sym: str, start: date, end: date, raw_dir: str, cache: str) -> Market:
    """Minute grid for one pair, with the quote->USD conversion needed for pip value:
    XXXUSD -> 1, USDXXX -> the pair's own price, cross -> USD<quote> (JPY, CHF, CAD) or
    1 / <quote>USD (EUR, GBP, AUD, NZD)."""
    if os.path.exists(cache):
        return load_market(cache)
    # one extra UTC day before start: the IST 05:00 range of `start` begins at 23:30 UTC the day before
    dl_start = start - timedelta(days=1)
    download(sym, dl_start, end, raw_dir)
    bid = load_side(sym, "BID", dl_start, end, raw_dir)
    ask = load_side(sym, "ASK", dl_start, end, raw_dir)
    base, quote = sym[:3], sym[3:]
    if quote == "USD":
        conv = 1.0
    elif base == "USD":
        conv = bid["c"]
    elif f"USD{quote}" in MAJORS:
        download(f"USD{quote}", dl_start, end, raw_dir, sides=("BID",))
        conv = load_side(f"USD{quote}", "BID", dl_start, end, raw_dir)["c"]
    else:
        download(f"{quote}USD", dl_start, end, raw_dir, sides=("BID",))
        conv = 1.0 / load_side(f"{quote}USD", "BID", dl_start, end, raw_dir)["c"]
    # trim the trailing never-traded minutes (e.g. today's partial / empty file)
    last_live = bid.index[bid["v"] > 0][-1]
    bid, ask = bid.loc[:last_live], ask.loc[:last_live]
    m = to_grid(bid, ask, conv, pip=pip_size(sym))
    save_market(m, cache)
    return m


def build_dukascopy_market(start: date, end: date, raw_dir: str, cache: str) -> Market:
    return build_market("GBPJPY", start, end, raw_dir, cache)


# --------------------------------------------------------------------------- synthetic
def synthetic_market(start: str = "2024-01-01", days: int = 400, seed: int = 7,
                     spread_pips: float = 2.5) -> Market:
    """Random-walk GBPJPY for testing the engine end-to-end. Weekends are flat, volume 0.
    A strategy should show ~zero edge (minus spread) on this."""
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start) - pd.Timedelta(days=1)
    n = (days + 1) * 1440
    ts = t0 + pd.to_timedelta(np.arange(n), unit="min")
    # closed from Fri 22:00 UTC to Sun 22:00 UTC
    dow, hour = ts.dayofweek.to_numpy(), ts.hour.to_numpy()
    closed = ((dow == 4) & (hour >= 22)) | (dow == 5) | ((dow == 6) & (hour < 22))
    # vol clustering: quieter in the Asian session
    sig = np.where((hour >= 7) & (hour < 17), 0.035, 0.018) * rng.lognormal(0, 0.3, n)
    steps = rng.standard_t(4, n) * sig / np.sqrt(2)
    steps[closed] = 0.0
    weekend_gap = closed[:-1] & ~closed[1:]
    steps[1:][weekend_gap] += rng.normal(0, 0.25, weekend_gap.sum())
    close = 190 + np.cumsum(steps)
    open_ = np.concatenate([[190.0], close[:-1]])
    wick = np.abs(rng.normal(0, 1, (2, n))) * sig * 0.6
    wick[:, closed] = 0
    high = np.maximum(open_, close) + wick[0]
    low = np.minimum(open_, close) - wick[1]
    vol = np.where(closed, 0.0, 1.0)
    spr = spread_pips * 0.01
    uj = 150 + np.cumsum(rng.normal(0, 0.003, n))
    return Market(t0=t0, bo=open_, bh=high, bl=low, bc=close, ao=open_ + spr, ah=high + spr,
                  al=low + spr, ac=close + spr, vol=vol, quote_per_usd=uj, has_ask=True)
