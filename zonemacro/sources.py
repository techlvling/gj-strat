"""Download and cache (parquet) every external series used by the zone/macro backtest.

All series are stored exactly as published, keyed by observation date. Release-timing
(when a value becomes usable) is applied later, in macro.py, never here.

| key            | what                                                    | source                       |
|----------------|---------------------------------------------------------|------------------------------|
| DGS2, DGS10    | US 2y / 10y Treasury constant maturity, daily           | FRED fredgraph.csv           |
| DFF            | effective fed funds, daily                              | FRED fredgraph.csv           |
| CPI_FIRST      | CPIAUCSL first-release index per month + release date   | ALFRED, one call per vintage |
| JGB10          | Japan 10y JGB yield, daily                              | MoF jgbcm_all.csv + jgbcm.csv|
| BUND10         | Germany 10y federal yield (term structure), daily       | Bundesbank BBSIS             |
| BOJ_CALL       | BoJ uncollateralised overnight call rate, daily         | BoJ stat-search API          |
| ECB_DFR        | ECB deposit facility rate, daily                        | ECB data API                 |
| MOF_INTERVENTION | yen intervention days                                 | MoF feio CSV                 |
"""
from __future__ import annotations

import io
import os
import re
import time

import pandas as pd
import requests

CACHE = "zonemacro_data"          # small, committed: makes the macro inputs reproducible
UA: dict = {}                       # FRED stalls requests with a browser User-Agent


def _get(url: str, tries: int = 10) -> requests.Response:
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code not in (429, 500, 502, 503, 504):
                r.raise_for_status()
        except requests.RequestException:
            if k == tries - 1:
                raise
        time.sleep(min(2 ** k, 30))
    raise RuntimeError(f"failed: {url}")


def _cached(name: str, build, refresh: bool = False) -> pd.DataFrame:
    path = os.path.join(CACHE, f"{name}.parquet")
    if os.path.exists(path) and not refresh:
        return pd.read_parquet(path)
    os.makedirs(CACHE, exist_ok=True)
    df = build()
    df.to_parquet(path)
    return df


def _series_frame(dates, values) -> pd.DataFrame:
    df = pd.DataFrame({"date": pd.to_datetime(dates), "value": pd.to_numeric(values, errors="coerce")})
    return df.dropna().drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------- FRED
def fred(series: str, refresh: bool = False) -> pd.DataFrame:
    def build():
        r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
        df = pd.read_csv(io.StringIO(r.text))
        return _series_frame(df.iloc[:, 0], df.iloc[:, 1])
    return _cached(series, build, refresh)


# --------------------------------------------------------------------------- ALFRED CPI
def alfred_vintage_dates(series: str = "CPIAUCSL") -> list[pd.Timestamp]:
    html = _get(f"https://alfred.stlouisfed.org/series/downloaddata?seid={series}").text
    return sorted({pd.Timestamp(d) for d in re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"', html)})


def first_releases(vintages: list[tuple[pd.Timestamp, pd.DataFrame]]) -> pd.DataFrame:
    """vintages: (vintage date, frame with columns month, value) in date order.
    A month is first released in the first vintage that contains it; its value there is the
    first-release value. Values of the same month in later (revised) vintages are ignored.
    In the first vintage only the newest month counts as released on that date."""
    rows: dict[pd.Timestamp, tuple[float, pd.Timestamp]] = {}
    seen: set[pd.Timestamp] = set()
    for v, df in sorted(vintages, key=lambda x: x[0]):
        df = df.dropna().sort_values("month")
        if not seen and len(df):
            seen.update(df["month"].iloc[:-1])
        for m, val in zip(df["month"], df["value"]):
            if m not in seen:
                rows[m] = (float(val), v)
                seen.add(m)
    return pd.DataFrame([(m, val, d) for m, (val, d) in sorted(rows.items())],
                        columns=["month", "value", "release_date"])


def cpi_first_release(since: str = "2006-06-01", refresh: bool = False) -> pd.DataFrame:
    """One row per CPI month: the index value as FIRST published and the date it was published.
    Every ALFRED vintage of CPIAUCSL since `since` is downloaded (one call each)."""
    def build():
        vint = []
        for v in [v for v in alfred_vintage_dates() if v >= pd.Timestamp(since)]:
            r = _get("https://alfred.stlouisfed.org/graph/alfredgraph.csv"
                     f"?id=CPIAUCSL&vintage_date={v:%Y-%m-%d}")
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = ["month", "value"]
            df["month"] = pd.to_datetime(df["month"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            vint.append((v, df))
            time.sleep(0.3)
        return first_releases(vint)
    return _cached("CPI_FIRST", build, refresh)


# --------------------------------------------------------------------------- Japan (MoF)
_ERA = {"S": 1925, "H": 1988, "R": 2018}


def _jp_date(s: str) -> pd.Timestamp | None:
    m = re.match(r"^([SHR])(\d+)\.(\d+)\.(\d+)$", str(s).strip())
    if not m:
        return None
    return pd.Timestamp(_ERA[m.group(1)] + int(m.group(2)), int(m.group(3)), int(m.group(4)))


def jgb10(refresh: bool = False) -> pd.DataFrame:
    def build():
        frames = []
        for url in ("https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
                    "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"):
            text = _get(url).content.decode("shift_jis", errors="replace")
            for line in text.splitlines():
                parts = line.split(",")
                d = _jp_date(parts[0]) if parts else None
                if d is not None and len(parts) > 10:
                    frames.append((d, parts[10]))          # column 10 = 10-year
        dates, vals = zip(*frames)
        return _series_frame(dates, vals)
    return _cached("JGB10", build, refresh)


# --------------------------------------------------------------------------- Germany (Bundesbank)
def bund10(refresh: bool = False) -> pd.DataFrame:
    def build():
        url = ("https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
               "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv")
        dates, vals = [], []
        for line in _get(url).content.decode("utf-8-sig").splitlines():
            parts = line.split(";")
            if len(parts) >= 2 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
                dates.append(parts[0])
                vals.append(parts[1].replace(",", ".") if parts[1] != "." else None)
        return _series_frame(dates, vals)
    return _cached("BUND10", build, refresh)


# --------------------------------------------------------------------------- policy rates (swap)
def boj_call(refresh: bool = False) -> pd.DataFrame:
    def build():
        url = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=en"
               "&db=FM01&startDate=200801&code=STRDCLUCON")
        dates, vals = [], []
        for line in _get(url).text.splitlines():
            if line.startswith("STRDCLUCON,"):
                parts = line.rsplit(",", 2)
                if parts[-1] != "null":
                    dates.append(pd.Timestamp(parts[-2]))
                    vals.append(parts[-1])
        return _series_frame(dates, vals)
    return _cached("BOJ_CALL", build, refresh)


def ecb_dfr(refresh: bool = False) -> pd.DataFrame:
    def build():
        url = ("https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV"
               "?format=csvdata&startPeriod=2008-01-01")
        df = pd.read_csv(io.StringIO(_get(url).text))
        return _series_frame(df["TIME_PERIOD"], df["OBS_VALUE"])
    return _cached("ECB_DFR", build, refresh)


# --------------------------------------------------------------------------- MoF interventions
_MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                     "Sep", "Oct", "Nov", "Dec"], 1)}


def mof_interventions(refresh: bool = False) -> pd.DataFrame:
    """Every intervention day in the MoF file. Year and month are only printed when they
    change, so they are carried forward row to row."""
    def build():
        url = ("https://www.mof.go.jp/policy/international_policy/reference/feio/"
               "foreign_exchange_intervention_operations.csv")
        text = _get(url).content.decode("shift_jis", errors="replace")
        import csv
        year = month = None
        rows = []
        for parts in csv.reader(io.StringIO(text)):
            if len(parts) < 9:
                continue
            y, mo, d = parts[3].strip(), parts[4].strip(), parts[5].strip()
            if y.isdigit() and len(y) == 4:
                year = int(y)
            if mo in _MON:
                month = _MON[mo]
            if d.isdigit() and year and month and "Japanese yen" in parts[8]:
                rows.append((pd.Timestamp(year, month, int(d)),
                             float(parts[6].replace(",", "")), parts[8].strip()))
        return pd.DataFrame(rows, columns=["date", "amount_100m_jpy", "operation"])
    return _cached("MOF_INTERVENTION", build, refresh)


def fetch_all(refresh: bool = False) -> dict[str, pd.DataFrame]:
    out = {s: fred(s, refresh) for s in ("DGS2", "DGS10", "DFF")}
    out["CPI_FIRST"] = cpi_first_release(refresh=refresh)
    out["JGB10"] = jgb10(refresh)
    out["BUND10"] = bund10(refresh)
    out["BOJ_CALL"] = boj_call(refresh)
    out["ECB_DFR"] = ecb_dfr(refresh)
    out["MOF_INTERVENTION"] = mof_interventions(refresh)
    return out


if __name__ == "__main__":
    for k, v in fetch_all().items():
        print(f"{k:18s} rows={len(v):6d}\n{v.head(2)}\n{v.tail(2)}\n")
