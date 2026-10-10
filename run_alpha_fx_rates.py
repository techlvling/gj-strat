"""Alpha hunt family `fx_rates`: FX under-reaction to relative 2-year yields -- yield-curve momentum (weekly /
monthly) and rate-spread fair-value residual (daily). Every rule below was fixed before the first run.

HYPOTHESIS: FX under-reacts to changes in expected relative monetary policy (2-year yields) and catches up over
weeks. Evidence: delayed overshooting (Eichenbaum & Evans 1995); distorted beliefs about rate persistence
(Gourinchas & Tornell 2004); yield-curve factors predict FX 1-24 months ahead (Chen & Tsang 2013); economic
momentum in rates predicts FX independently of carry and price momentum (Dahlquist & Hasseltoft 2020 JFE); rate
fundamentals forecast FX at 1-month horizons (Molodtsova & Papell 2009). Bank short-term fair-value models trade
1.5-2 SE residuals. First fundamental (non-price, non-clock) FX signal in this repo. Main risk: the FX / rates
beta was unstable while JGB yields were pinned (2016-21).

DATA (daily 2y yields in percentage points; files under data/extra, URLs in data/extra/SOURCES.csv and REPORT.md):
  USD  FRED DGS2 (DGS2.csv)
  EUR  ECB euro-area AAA Svensson 2y spot YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y (eur_2y_ecb_aaa.csv)
  JPY  MOF JGB constant-maturity 2Y: jgbcme_all.csv to 2026-09-30 (jpy_jgb_mof_all.csv) + the current-month file
       jgbcme.csv for 2026-10 (jpy_jgb_mof_current.csv)
  GBP  BoE nominal government spot curve, 2.0-year column of sheet '4. spot curve' of glcnominalddata.zip (files
       2005-2015, 2016-2024, 2025-present) -> gbp_2y_boe.csv (ends 2026-09-30)
  CAD  BoC 2y benchmark BD.CDN.2YR.DQ.YLD (cad_2y_boc.csv)
  AUD  RBA F2 2y (FCMYGBAG2D): f02dhist.xls (xlrd) to 2013-05-17 -> aud_2y_rba_hist.csv, then f2-data.csv
       (aud_f2_rba.csv) from 2013-09-02. The RBA publishes no 2y value for 2013-05-20..2013-08-30, so AUD is
       missing there (not filled; obvious-impossibility note).
  CHF (SNB series stops 2025-07-31) and NZD (RBNZ blocks downloads) are excluded.
  Each series goes on a Mon-Fri calendar and is forward-filled at most 3 weekdays (holidays). Spread
  x_c = y_c - y_USD. "Trading days" in yield lookbacks = weekdays of this calendar.
  PUBLICATION LAG: ECB, BoE and RBA publish day-t yields on day t+1, so weekly / monthly signals use yields dated
  <= the Thursday before the Monday entry (Y1-Y4) or <= signal day - 1 (Y5), and daily signals use yields dated
  <= t - 1 only.

MARKETS: EURUSD GBPUSD AUDUSD USDJPY USDCAD (Y1-Y4, FV1-FV5; plus Y5 legs) and the 10 crosses EURGBP EURJPY
GBPJPY EURAUD EURCAD GBPAUD GBPCAD AUDJPY AUDCAD CADJPY (Y5 legs only). Each market is loaded once inside a
worker of multiprocessing.Pool(2) (maxtasksperchild=1) and deleted. Pairs are oriented foreign/USD: log spot
s = log(EURUSD), log(GBPUSD), log(AUDUSD), log(1/USDJPY), log(1/USDCAD); "long foreign" = BUY EURUSD / GBPUSD /
AUDUSD, SELL USDJPY / USDCAD.

ATR20 = gjstrat.patterns.daily_table atr20 (mean bid high-low of the 20 previous NY-close days, shifted, known
before the day) at the NY label of the entry minute (or the latest earlier label). It is recomputed with the same
formula from gjstrat.bias.daily_bars because daily_table also drops days without sma50_prev (all days before
2010-03-18); values are identical where both exist (obvious-impossibility fix, gains Jan-Mar 2010).

A. YIELD MOMENTUM
  Y1-Y4 (time series, 5 USD pairs). Week = Monday..Sunday. Entry day = the week's first weekday whose 07:00 UTC
  minute or one of the next 4 minutes has ticks (normally Monday; a dead holiday Monday moves the entry to the
  next weekday of that week; obvious-impossibility fix); market entry at that minute. Thu = the Thursday before
  the week's Monday. d_c = x_c(Thu) - x_c(Thu - L weekdays). Long foreign vs USD if d_c > +h, short if
  d_c < -h, else flat; no trade if d_c is undefined. Time exit at the next calendar week's entry minute (no trade
  if that week has none). SL 3.0 x ATR20 from the fill, no TP. Every week is a separate trade (spread and
  commission paid weekly, conservative).
    Y1: L=63, h=0.25 pp.  Y2: L=63, h=0.  Y3: L=21, h=0.10.  Y4: L=126, h=0.25.
  Y5 (cross-sectional, monthly, 6 currencies USD EUR JPY GBP CAD AUD). Signal day D = last weekday of month M.
  Rank the currencies by the 63-weekday change of their own 2y yield (USD = DGS2) measured at the last weekday
  before D (yields dated <= D - 1): chg_c = y_c(p) - y_c(p - 63). All 6 changes must exist, else no trade that
  month. Long the top-2 vs the bottom-2 via the 4 crosses in quoted form (e.g. long JPY vs EUR = SELL EURJPY;
  long JPY vs USD = SELL USDJPY). Entry: per leg, the first weekday of month M+1 whose 07:00 UTC minute (or one
  of the next 4) has ticks; time exit at that leg's entry minute in month M+2. SL 3.0 x ATR20. Monthly R = mean
  of the legs' R (legs that traded). Y5 is judged on this monthly portfolio series.

B. FAIR-VALUE RESIDUAL (daily, 5 USD pairs; every model input dated <= t - 1)
  Close series: weekday t is a close day if the pair has ticks in [16:35, 16:44] New York and a ticked entry
  minute in [16:45, 16:50) NY (the first one is the entry minute; obvious-impossibility fix for dead minutes).
  C_t = bid close of the 16:44 NY minute (on the grid = last traded close at or before 16:44). s_t = oriented
  log C_t, x_t = spread on calendar date t. "Days" below = close days; t - 1 = the previous close day.
  ds_k = s_k - s_{k-1}, dx_k = x_k - x_{k-1}. A window of W days ending at t-1 needs >= ceil(0.9 W) days with
  both values (yield gaps), else z is undefined.
  * M1 (changes): OLS of ds on dx (with intercept) over the W days ending t-1 -> beta. u = ds - beta dx (same
    beta on the whole window). z_t = (sum of the last 20 u, all 20 must exist) / (std(u over W) x sqrt(20)).
  * M2 (levels): OLS of s on x over the W days ending t-1. z_t = residual(t-1) / std(residuals over W).
  (std with ddof = 1.) Entry: market at day t's entry minute (16:45 NY). z_t <= -k: buy foreign (cheap vs
  rates); z_t >= +k: sell foreign. Exit at the entry minute of the first later day q whose z_q (computed the same
  way) has crossed 0 (z_q >= 0 for longs, <= 0 for shorts), or at day j + 15 (15 close days later) if none;
  a trade still open at the end of the data exits at the last close day ("END"). SL 2.0 x ATR20, no TP. One
  position per pair per variant: signals are ignored while in a trade; after a z / time exit on day q the next
  entry can be on day q + 1 at the earliest; after a stop-out, after the first close day whose entry minute is at
  or after the stop minute.
    FV1: M1, W=250, k=1.5.  FV2: M1, W=250, k=2.0.  FV3: M1, W=60, k=2.0.  FV4: M2, W=250, k=2.0.
    FV5: M2, W=60, k=2.0.
  Exit minutes are precomputed from the signal series (path-independent); gjstrat.patterns.simulate checks the
  stop minute by minute on real bid/ask: Signal(day, side, entry_i, 'market', None, entry_i + 1, sl, None,
  exit_i).

COSTS (every result): gjstrat.accounting.account(trades of one variant on one pair sorted by (exit_i, entry_i),
m, 10_000, commission=7, swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'].

PERIODS / STATISTICS: run_edge_hunt.PER by entry day: design 2010-17, check 2018-23, holdout 2024-26; last 3
years = entries 2023-10-08..2026-10-07. Per test: trades, trades/month (over the months from the first possible
signal to 2026-10), win %, avg win / avg loss, avg R and trade-level t per period, last 3 years, % stopped, avg
hold days. Per pair (information) and pooled over the 5 pairs: pooled t is month-clustered (sum of R per calendar
month of the entry day, zero for months without trades, from the variant's first trade month to 2026-10; t over
months), plus the count of pairs with full-sample avg R > 0. Y5: its monthly portfolio series (months with a
trade; t over months), plus leg-level stats.

JUDGED TESTS: 10 = pooled Y1, Y2, Y3, Y4, FV1..FV5 and Y5's monthly series. Survival (charter bar): design t >= 2
(pooled: month-clustered; Y5: monthly) AND avg R > 0 in check AND in holdout (pooled: per-trade avg R; Y5: mean
monthly R). A pooled FV variant also needs > half the pairs positive (>= 3 of 5 with full-sample avg R > 0).
10 x 0.006 = 0.06 survivors expected by luck. Per-pair charter results (45 tests) are information only.

SEPARATENESS / DIAGNOSTICS (reporting only):
  * Monthly R of Y1 (sum over pairs by entry month) and Y5 (portfolio) vs in-script proxies on the same months:
    CARRY = k=2 cross-sectional carry: at D (last weekday of M) rank the 6 currencies by BIS central-bank policy
    rate (data/extra/policy_rates_bis_daily.csv; EUR = ECB deposit rate data/extra/ecb_deposit_rate_daily.csv),
    latest value dated <= D - 1, ties broken in the order USD EUR JPY GBP CAD AUD; long top-2 vs bottom-2 via the
    4 crosses, gross R-like return = signed (bid open at the month M+2 entry minute - bid open at the month M+1
    entry minute) / (3 x ATR20), mean of legs (no stop, no costs).
    MOMXS = the same with the ranking by 63-close-day price change vs USD (log of the oriented 16:44 NY close at
    the last close day <= D vs 63 close days earlier; USD = 0).
    MOMTS = weekly time-series price momentum on the 5 USD pairs: sign of the 63-close-day oriented log change at
    the last close day <= Thu, held from the week's entry minute to the next week's (gross, / 3 ATR20), summed
    over pairs by entry month.
    Reported: correlations, OLS of Y1 / Y5 monthly R on the three proxies (alpha and its t), and the share of
    active Y1 pair-weeks whose sign agrees with the MOMTS sign and with the policy-rate differential sign.
  * Median rolling beta per pair per period (M1 and M2, W = 250 and 60) = stability of the rates link.
  * Share of pair-weeks in position (Y1-Y4) and of close days in position (FV).
  * Sum of R by year for the pooled tests.

OUTPUT: results/alpha_hunt/fx_rates/REPORT.md (+ tests.csv, pooled.csv, trades.csv, monthly.csv, betas.csv,
fv_series.csv, corr.csv, by_year.csv, run.log).

    python run_alpha_fx_rates.py           # everything
    python run_alpha_fx_rates.py report    # rebuild the report from results/alpha_hunt/fx_rates/raw.pkl
"""
from __future__ import annotations

import csv
import io
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.bias import daily_bars
from gjstrat.data import load_market
from gjstrat.patterns import NY, Signal, local_idx, simulate, utc_idx
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/fx_rates"
XD = "data/extra"
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
END = pd.Timestamp("2026-10-07")
CCYS = ["USD", "EUR", "JPY", "GBP", "CAD", "AUD"]
USD_PAIRS = {"EURUSD": "EUR", "GBPUSD": "GBP", "AUDUSD": "AUD", "USDJPY": "JPY", "USDCAD": "CAD"}
CROSSES = ["EURGBP", "EURJPY", "GBPJPY", "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDJPY", "AUDCAD", "CADJPY"]
ALL = list(USD_PAIRS) + CROSSES
YV = {"Y1": (63, 0.25), "Y2": (63, 0.0), "Y3": (21, 0.10), "Y4": (126, 0.25)}
FVV = {"FV1": ("M1", 250, 1.5), "FV2": ("M1", 250, 2.0), "FV3": ("M1", 60, 2.0), "FV4": ("M2", 250, 2.0),
       "FV5": ("M2", 60, 2.0)}
NAMES = {"Y1": "yield mom L=63 h=0.25", "Y2": "yield mom L=63 h=0", "Y3": "yield mom L=21 h=0.10",
         "Y4": "yield mom L=126 h=0.25", "Y5": "XS yield mom monthly top2-bottom2",
         "FV1": "FV M1 W=250 k=1.5", "FV2": "FV M1 W=250 k=2", "FV3": "FV M1 W=60 k=2",
         "FV4": "FV M2 W=250 k=2", "FV5": "FV M2 W=60 k=2"}
JUDGED = list(YV) + ["Y5"] + list(FVV)
SOURCES = [
    ("USD 2y", "data/extra/DGS2.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"),
    ("EUR 2y", "data/extra/eur_2y_ecb_aaa.csv",
     "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata&startPeriod=2009-01-01"),
    ("JPY 2y", "data/extra/jpy_jgb_mof_all.csv",
     "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"),
    ("JPY 2y (Oct 2026)", "data/extra/jpy_jgb_mof_current.csv",
     "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"),
    ("GBP 2y", "data/extra/gbp_2y_boe.csv",
     "https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/glcnominalddata.zip"),
    ("CAD 2y", "data/extra/cad_2y_boc.csv",
     "https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD/csv?start_date=2009-01-01"),
    ("AUD 2y to 2013-05", "data/extra/aud_2y_rba_hist.csv", "https://www.rba.gov.au/statistics/tables/xls-hist/f02dhist.xls"),
    ("AUD 2y from 2013-09", "data/extra/aud_f2_rba.csv", "https://www.rba.gov.au/statistics/tables/csv/f2-data.csv"),
    ("Policy rates", "data/extra/policy_rates_bis_daily.csv",
     "https://stats.bis.org/api/v1/data/WS_CBPOL/D.US+XM+JP+GB+CH+AU+CA+NZ/all?startPeriod=2009-01-01&format=csv"),
    ("ECB deposit rate", "data/extra/ecb_deposit_rate_daily.csv",
     "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=2009-01-01"),
]


def path_of(sym):
    return f"data/{sym.lower()}_2010-01-01_2026-10-07.npz"


# --------------------------------------------------------------------------- yields / rates
def _ser(dates, vals) -> pd.Series:
    s = pd.Series(pd.to_numeric(pd.Series(vals), errors="coerce").to_numpy(), index=pd.DatetimeIndex(dates))
    s = s.dropna().sort_index()
    return s[~s.index.duplicated(keep="last")].astype(float)


def _mof(path) -> pd.Series:
    raw = open(path, encoding="latin1").read().splitlines()
    rows = []
    for line in raw:
        p = line.split(",")
        if len(p) > 2 and p[0][:2] in ("19", "20") and "/" in p[0]:
            rows.append((pd.Timestamp(p[0].replace("/", "-")), p[2]))
    return _ser([r[0] for r in rows], [r[1] for r in rows])


def load_yields() -> pd.DataFrame:
    s = {}
    d = pd.read_csv(f"{XD}/DGS2.csv")
    s["USD"] = _ser(pd.to_datetime(d.observation_date), d.DGS2)
    e = pd.read_csv(f"{XD}/eur_2y_ecb_aaa.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
    s["EUR"] = _ser(pd.to_datetime(e.TIME_PERIOD), e.OBS_VALUE)
    j = pd.concat([_mof(f"{XD}/jpy_jgb_mof_all.csv"), _mof(f"{XD}/jpy_jgb_mof_current.csv")])
    s["JPY"] = j[~j.index.duplicated(keep="last")].sort_index()
    g = pd.read_csv(f"{XD}/gbp_2y_boe.csv")
    s["GBP"] = _ser(pd.to_datetime(g.date), g.gbp_2y)
    txt = open(f"{XD}/cad_2y_boc.csv", encoding="utf-8-sig").read()
    c = pd.read_csv(io.StringIO(txt[txt.index('"OBSERVATIONS"') + len('"OBSERVATIONS"'):].lstrip()))
    s["CAD"] = _ser(pd.to_datetime(c.date), c.iloc[:, 1])
    ah = pd.read_csv(f"{XD}/aud_2y_rba_hist.csv")
    rows = []
    with open(f"{XD}/aud_f2_rba.csv", encoding="utf-8-sig") as f:
        for p in csv.reader(f):
            if len(p) > 1 and p[1] != "":
                try:
                    rows.append((pd.to_datetime(p[0], format="%d-%b-%Y"), p[1]))
                except (ValueError, TypeError):
                    pass
    a_new = _ser([r[0] for r in rows], [r[1] for r in rows])
    a = pd.concat([_ser(pd.to_datetime(ah.date), ah.aud_2y), a_new])
    s["AUD"] = a[~a.index.duplicated(keep="last")].sort_index()
    wd = pd.bdate_range("2009-01-01", "2026-10-09")
    Y = pd.DataFrame({c: s[c].reindex(s[c].index.union(wd)).reindex(wd) for c in CCYS})
    # observations only on their own dates (no weekend values exist), then ffill <= 3 weekdays
    Y = Y.ffill(limit=3)
    Y.attrs["raw_last"] = {c: str(s[c].index.max().date()) for c in CCYS}
    Y.attrs["raw_first"] = {c: str(s[c].index.min().date()) for c in CCYS}
    return Y


def load_policy() -> dict[str, pd.Series]:
    b = pd.read_csv(f"{XD}/policy_rates_bis_daily.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    b["TIME_PERIOD"] = pd.to_datetime(b.TIME_PERIOD)
    out = {}
    for ccy, area in {"USD": "US", "JPY": "JP", "GBP": "GB", "AUD": "AU", "CAD": "CA"}.items():
        x = b[b.REF_AREA == area]
        out[ccy] = _ser(x.TIME_PERIOD, x.OBS_VALUE)
    e = pd.read_csv(f"{XD}/ecb_deposit_rate_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
    out["EUR"] = _ser(pd.to_datetime(e.TIME_PERIOD), e.OBS_VALUE)
    return out


def value_before(s: pd.Series, day: pd.Timestamp) -> float:
    """Latest value dated <= day - 1 calendar day."""
    p = np.searchsorted(s.index.values, np.datetime64(day - pd.Timedelta(days=1)), side="right") - 1
    return float(s.iat[p]) if p >= 0 else np.nan


def pair_of(long_c: str, short_c: str) -> tuple[str, str]:
    """(symbol, side) that is long `long_c` vs `short_c` in quoted form."""
    if long_c + short_c in ALL:
        return long_c + short_c, "BUY"
    if short_c + long_c in ALL:
        return short_c + long_c, "SELL"
    raise KeyError(long_c + short_c)


def last_weekday(per: pd.Period) -> pd.Timestamp:
    return pd.bdate_range(per.start_time, per.end_time.normalize())[-1]


# --------------------------------------------------------------------------- plans from yields
def weekly_signals(Y: pd.DataFrame) -> pd.DataFrame:
    """One row per (week Monday, ccy, variant): signal +1 / -1 / 0, NaN = undefined."""
    X = Y[[c for c in CCYS if c != "USD"]].sub(Y["USD"], axis=0)
    wd = Y.index
    rows = []
    for mon in pd.date_range("2010-01-04", "2026-10-05", freq="W-MON"):
        thu = mon - pd.Timedelta(days=4)
        p = wd.get_loc(thu)
        for c in X.columns:
            for v, (L, h) in YV.items():
                dc = X[c].iat[p] - X[c].iat[p - L] if p - L >= 0 else np.nan
                sg = np.nan if not np.isfinite(dc) else (1.0 if dc > h else (-1.0 if dc < -h else 0.0))
                rows.append((mon, c, v, dc, sg))
    return pd.DataFrame(rows, columns=["week", "ccy", "variant", "d", "sig"])


def month_plans(Y: pd.DataFrame, pol: dict) -> pd.DataFrame:
    """Y5 and CARRY legs per entry month (signal at the last weekday of the previous month)."""
    wd = Y.index
    rows = []
    for sm in pd.period_range("2009-12", "2026-09", freq="M"):
        D = last_weekday(sm)
        p = wd.searchsorted(D) - 1                       # last weekday before D (yields dated <= D - 1)
        chg = {c: (Y[c].iat[p] - Y[c].iat[p - 63]) for c in CCYS}
        em = sm + 1
        if all(np.isfinite(v) for v in chg.values()):
            order = sorted(CCYS, key=lambda c: -chg[c])          # stable: ties keep CCYS order
            top, bot = order[:2], order[-2:]
            for a in top:
                for b in bot:
                    sym, side = pair_of(a, b)
                    rows.append(("Y5", str(em), D, sym, side, ",".join(top), ",".join(bot)))
        rates = {c: value_before(pol[c], D) for c in CCYS}
        if all(np.isfinite(v) for v in rates.values()):
            order = sorted(CCYS, key=lambda c: -rates[c])
            top, bot = order[:2], order[-2:]
            for a in top:
                for b in bot:
                    sym, side = pair_of(a, b)
                    rows.append(("CARRY", str(em), D, sym, side, ",".join(top), ",".join(bot)))
    return pd.DataFrame(rows, columns=["plan", "entry_month", "signal_day", "sym", "side", "top", "bot"])


# --------------------------------------------------------------------------- market worker helpers
def live_at(m, i, k=5):
    """First traded minute in [i, i + k), else -1."""
    if i < 0 or i + k >= m.n:
        return -1
    w = np.flatnonzero(m.vol[i: i + k] > 0)
    return i + int(w[0]) if len(w) else -1


def rolling_z(s: pd.Series, x: pd.Series, model: str, W: int) -> tuple[pd.Series, pd.Series]:
    """(z_t, beta_t) for signal day t, from data on days <= t - 1 (series indexed by close day)."""
    mp = int(np.ceil(0.9 * W))
    if model == "M1":
        a, b = s.diff(), x.diff()
    else:
        a, b = s.copy(), x.copy()
    ok = a.notna() & b.notna()
    a, b = a.where(ok), b.where(ok)
    cov = a.rolling(W, min_periods=mp).cov(b)
    vb = b.rolling(W, min_periods=mp).var()
    va = a.rolling(W, min_periods=mp).var()
    vb = vb.where(vb > 1e-12)
    beta = cov / vb
    resid_var = (va - cov ** 2 / vb).where(lambda v: v > 0)
    sd = np.sqrt(resid_var)
    if model == "M1":
        su = a.rolling(20, min_periods=20).sum() - beta * b.rolling(20, min_periods=20).sum()
        z = su / (sd * np.sqrt(20))
    else:
        ma, mb = a.rolling(W, min_periods=mp).mean(), b.rolling(W, min_periods=mp).mean()
        z = (a - (ma + beta * (b - mb))) / sd
    return z.shift(1), beta.shift(1)


def run_market(job):
    sym, ctx = job
    t0 = time.time()
    m = load_market(path_of(sym))
    swap = SwapModel.from_fred("rates", 1.0)
    db = daily_bars(m)
    atr = (db.high - db.low).rolling(20).mean().shift(1).dropna()
    atr_idx, atr_val = atr.index.values, atr.to_numpy()

    def atr_at(day):
        p = np.searchsorted(atr_idx, np.datetime64(day), side="right") - 1
        return float(atr_val[p]) if p >= 0 else np.nan

    last = m.ts(m.n - 1)
    wdays = pd.bdate_range("2010-01-01", last.normalize())
    e07 = {}
    for day in wdays:
        s = live_at(m, utc_idx(m, day, 7, 0))
        if s >= 0:
            e07[day] = s
    ent = pd.Series(e07)
    wk = ent.groupby(ent.index - pd.to_timedelta(ent.index.dayofweek, unit="D")).head(1)
    week_entry = pd.Series(wk.to_numpy(), index=wk.index - pd.to_timedelta(wk.index.dayofweek, unit="D"))
    week_day = pd.Series(wk.index, index=week_entry.index)
    mo = ent.groupby(ent.index.to_period("M")).head(1)
    month_entry = pd.Series(mo.to_numpy(), index=mo.index.to_period("M"))
    month_day = pd.Series(mo.index, index=month_entry.index)

    trades = []        # (variant, Trade, extra dict)

    def sim(v, day, side, s, x, sl, extra):
        if not (sl > 0) or x <= s + 1 or x >= m.n:
            return None
        t = simulate(m, Signal(day, side, int(s), "market", None, int(s) + 1, sl, None, int(x), v))
        if t is not None:
            trades.append((v, t, extra))
        return t

    # monthly table (proxies) for every symbol
    mrows = []
    for per, s in month_entry.items():
        nxt = per + 1
        if nxt in month_entry.index:
            x = month_entry[nxt]
            day = month_day[per]
            mrows.append((sym, str(per), day, int(s), int(x), m.bo[s], m.bo[x], atr_at(day)))
    mtab = pd.DataFrame(mrows, columns=["sym", "entry_month", "day", "e_i", "x_i", "bo_e", "bo_x", "atr"])

    # Y5 legs
    for em, side in ctx["y5"]:
        per = pd.Period(em, "M")
        if per in month_entry.index and per + 1 in month_entry.index:
            day = month_day[per]
            sim("Y5", day, side, month_entry[per], month_entry[per + 1], 3.0 * atr_at(day), {"entry_month": em})

    wtab = pd.DataFrame()
    cs_out = pd.DataFrame()
    fv_series = pd.DataFrame()
    fv_info = {}
    if sym in USD_PAIRS:
        ccy = USD_PAIRS[sym]
        base_foreign = sym.startswith(ccy)
        side_of = lambda pos: "BUY" if (pos > 0) == base_foreign else "SELL"
        # weekly table + Y1-Y4
        wrows = []
        for wkm, s in week_entry.items():
            nw = wkm + pd.Timedelta(days=7)
            if nw in week_entry.index:
                x = week_entry[nw]
                day = week_day[wkm]
                wrows.append((sym, wkm, day, int(s), int(x), m.bo[s], m.bo[x], atr_at(day)))
        wtab = pd.DataFrame(wrows, columns=["sym", "week", "day", "e_i", "x_i", "bo_e", "bo_x", "atr"])
        sig = ctx["weekly"]                             # DataFrame week x variant (signals for this ccy)
        for r in wtab.itertuples(index=False):
            if r.week not in sig.index:
                continue
            for v in YV:
                g = sig.at[r.week, v]
                if not np.isfinite(g) or g == 0:
                    continue
                sim(v, r.day, side_of(g), r.e_i, r.x_i, 3.0 * r.atr, {"pos": g})
        # close series
        rows = []
        for day in wdays:
            i = local_idx(m, day, 16, 44, NY)
            if i < 10 or i + 7 >= m.n:
                continue
            if not (m.vol[i - 9: i + 1] > 0).any():
                continue
            s = live_at(m, i + 1)
            if s < 0:
                continue
            rows.append((day, i, s, m.bc[i]))
        cs = pd.DataFrame(rows, columns=["day", "i", "s", "C"]).set_index("day")
        sgn = 1.0 if base_foreign else -1.0
        slog = sgn * np.log(cs.C)
        xs = ctx["spread"].reindex(cs.index)
        cs_out = pd.DataFrame({"sym": sym, "day": cs.index, "C": cs.C.to_numpy(), "s": slog.to_numpy(),
                               "x": xs.to_numpy()})
        S = cs.s.to_numpy()
        days = cs.index
        n = len(cs)
        ser = {"sym": sym, "day": days}
        cache = {}
        for (model, W) in {(a, b) for a, b, _ in FVV.values()}:
            z, beta = rolling_z(slog, xs, model, W)
            cache[(model, W)] = z.to_numpy()
            ser[f"z_{model}_{W}"] = z.to_numpy()
            ser[f"beta_{model}_{W}"] = beta.to_numpy()
        fv_series = pd.DataFrame(ser)
        for v, (model, W, k) in FVV.items():
            z = cache[(model, W)]
            busy, in_days = -1, 0
            for j in range(n):
                if j <= busy or not np.isfinite(z[j]):
                    continue
                if z[j] <= -k:
                    pos = 1.0
                elif z[j] >= k:
                    pos = -1.0
                else:
                    continue
                a = atr_at(days[j])
                if not a > 0:
                    continue
                jx, why = None, None
                for q in range(j + 1, min(j + 15, n - 1) + 1):
                    if (pos > 0 and z[q] >= 0) or (pos < 0 and z[q] <= 0):
                        jx, why = q, "ZX"
                        break
                if jx is None:
                    if j + 15 <= n - 1:
                        jx, why = j + 15, "TIME"
                    elif n - 1 > j:
                        jx, why = n - 1, "END"
                    else:
                        continue
                t = sim(v, days[j], side_of(pos), S[j], S[jx], 2.0 * a,
                        {"pos": pos, "z": float(z[j]), "why": why, "hold_days_plan": jx - j})
                if t is None:
                    continue
                busy = jx if t.reason != "SL" else int(np.searchsorted(S, t.exit_i, side="left"))
                in_days += (min(busy, n - 1) - j)
            fv_info[v] = {"days_z": int(np.isfinite(z).sum()), "days_in_pos": int(in_days)}
    # costs per variant
    recs = []
    by_v = {}
    for v, t, ex in trades:
        by_v.setdefault(v, []).append((t, ex))
    for v, lst in by_v.items():
        lst.sort(key=lambda te: (te[0].exit_i, te[0].entry_i))
        tr = [te[0] for te in lst]
        lg = account(tr, m, 10_000, commission=7, swap=swap, sym=sym, slippage_pips=0.2)
        assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
        R = lg["R"].to_numpy()
        for (t, ex), r in zip(lst, R):
            reason = "SL" if t.reason == "SL" else ex.get("why", "TIME")
            recs.append(dict(variant=v, sym=sym, day=pd.Timestamp(t.day), side=t.side, pos=ex.get("pos", np.nan),
                             entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i), entry=t.entry, exit=t.exit,
                             reason=reason, risk=t.risk, R_gross=t.r, R=float(r), z=ex.get("z", np.nan),
                             entry_month=ex.get("entry_month", ""),
                             hold_days=(m.ts(t.exit_i) - m.ts(t.entry_i)) / pd.Timedelta(days=1)))
    info = {"sym": sym, "weeks": len(week_entry), "months": len(month_entry), "close_days": len(cs_out),
            "trades": len(recs), "seconds": round(time.time() - t0)}
    print(f"{sym}: {info}", flush=True)
    del m, db
    return dict(sym=sym, trades=pd.DataFrame(recs), mtab=mtab, wtab=wtab, cs=cs_out, fv=fv_series,
                fv_info=fv_info, info=info)


# --------------------------------------------------------------------------- statistics
def period_of(day: pd.Series) -> pd.Series:
    out = pd.Series("", index=day.index)
    for p, (a, b) in PER.items():
        out[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))] = p
    return out


def basic(R: np.ndarray) -> dict:
    R = np.asarray(R, dtype=float)
    w, l = R[R > 0], R[R < 0]
    return {"n": len(R), "win %": (R > 0).mean() * 100 if len(R) else np.nan,
            "avg win / avg loss": (w.mean() / -l.mean()) if len(w) and len(l) else np.nan,
            "avg R": R.mean() if len(R) else np.nan, "t": tstat(R) if len(R) > 1 else np.nan}


def month_sum(df: pd.DataFrame, first: pd.Period, last: pd.Period) -> pd.Series:
    rng = pd.period_range(first, last, freq="M")
    s = df.groupby(df.day.dt.to_period("M"))["R"].sum()
    return s.reindex(rng, fill_value=0.0)


def test_row(df: pd.DataFrame, months_total: int, ms: pd.Series | None) -> dict:
    """df: trades of one test (one pair or pooled). ms: monthly R series for the month-clustered t."""
    R = df.R.to_numpy()
    b = basic(R)
    row = {"trades": b["n"], "trades/month": b["n"] / months_total if months_total else np.nan,
           "win %": b["win %"], "avg win / avg loss": b["avg win / avg loss"], "avg R": b["avg R"], "t": b["t"]}
    if ms is not None:
        row["month t (all)"] = tstat(ms.to_numpy())
    per = period_of(df.day)
    for p in PER:
        x = df.R[per == p].to_numpy()
        row[f"{p} n"] = len(x)
        row[f"{p} avg R"] = x.mean() if len(x) else np.nan
        row[f"{p} t"] = tstat(x) if len(x) > 1 else np.nan
        if ms is not None:
            a, bb = PER[p]
            mm = ms[(ms.index >= pd.Period(a[:7], "M")) & (ms.index <= pd.Period(bb[:7], "M"))]
            row[f"{p} month t"] = tstat(mm.to_numpy()) if len(mm) > 1 else np.nan
    x = df[(df.day >= L3[0]) & (df.day <= L3[1])].R.to_numpy()
    row["last3y n"], row["last3y avg R"] = len(x), (x.mean() if len(x) else np.nan)
    row["last3y t"] = tstat(x) if len(x) > 1 else np.nan
    if ms is not None:
        mm = ms[ms.index >= pd.Period("2023-10", "M")]
        row["last3y month t"] = tstat(mm.to_numpy()) if len(mm) > 1 else np.nan
    row["SL %"] = (df.reason == "SL").mean() * 100 if len(df) else np.nan
    row["avg hold days"] = df.hold_days.mean() if len(df) else np.nan
    return row


def y5_series(tr: pd.DataFrame) -> pd.DataFrame:
    y5 = tr[tr.variant == "Y5"]
    g = y5.groupby("entry_month").agg(R=("R", "mean"), legs=("R", "size"), day=("day", "min"))
    g.index = pd.PeriodIndex(g.index, freq="M")
    return g.sort_index()


def corr_block(monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in ("Y1", "Y5"):
        d = monthly[[y, "CARRY", "MOMXS", "MOMTS"]].dropna()
        r = {"series": y, "months": len(d)}
        for p in ("CARRY", "MOMXS", "MOMTS"):
            r[f"corr {p}"] = d[y].corr(d[p])
        Xm = np.column_stack([np.ones(len(d)), d[["CARRY", "MOMXS", "MOMTS"]].to_numpy()])
        yv = d[y].to_numpy()
        beta, *_ = np.linalg.lstsq(Xm, yv, rcond=None)
        res = yv - Xm @ beta
        s2 = res @ res / (len(d) - Xm.shape[1])
        se = np.sqrt(np.diag(s2 * np.linalg.inv(Xm.T @ Xm)))
        r["mean monthly R"] = yv.mean()
        r["alpha (monthly R)"] = beta[0]
        r["alpha t"] = beta[0] / se[0]
        for k, p in enumerate(("CARRY", "MOMXS", "MOMTS"), 1):
            r[f"b {p}"] = beta[k]
            r[f"t {p}"] = beta[k] / se[k]
        rows.append(r)
    return pd.DataFrame(rows).set_index("series")


# --------------------------------------------------------------------------- main
def compute():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    Y = load_yields()
    pol = load_policy()
    print("yields first:", Y.attrs["raw_first"], "last:", Y.attrs["raw_last"], flush=True)
    X = Y[[c for c in CCYS if c != "USD"]].sub(Y["USD"], axis=0)
    ws = weekly_signals(Y)
    mp = month_plans(Y, pol)
    jobs = []
    for sym in ALL:
        ctx = {"y5": [(r.entry_month, r.side) for r in mp[(mp.plan == "Y5") & (mp.sym == sym)].itertuples()]}
        if sym in USD_PAIRS:
            c = USD_PAIRS[sym]
            ctx["weekly"] = ws[ws.ccy == c].pivot(index="week", columns="variant", values="sig")
            ctx["spread"] = X[c]
        jobs.append((sym, ctx))
    res = []
    with Pool(2, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_market, jobs):
            res.append(r)
    raw = dict(res=res, Y=Y, ws=ws, mp=mp, pol=pol, seconds=time.time() - t0)
    with open(f"{OUT}/raw.pkl", "wb") as f:
        pickle.dump(raw, f)
    return raw


def report(raw):
    res, Y, ws, mp, pol = raw["res"], raw["Y"], raw["ws"], raw["mp"], raw["pol"]
    tr = pd.concat([r["trades"] for r in res], ignore_index=True)
    tr["day"] = pd.to_datetime(tr.day)
    mtab = pd.concat([r["mtab"] for r in res], ignore_index=True)
    wtab = pd.concat([r["wtab"] for r in res if len(r["wtab"])], ignore_index=True)
    cs = pd.concat([r["cs"] for r in res if len(r["cs"])], ignore_index=True)
    fv = pd.concat([r["fv"] for r in res if len(r["fv"])], ignore_index=True)
    infos = pd.DataFrame([r["info"] for r in res]).set_index("sym").loc[ALL]
    fv_info = {r["sym"]: r["fv_info"] for r in res if r["fv_info"]}
    tr.sort_values(["variant", "sym", "entry_ts"]).to_csv(f"{OUT}/trades.csv", index=False)
    fv.to_csv(f"{OUT}/fv_series.csv", index=False)
    end_m = pd.Period("2026-10", "M")

    # ---------------- per-pair and pooled tests
    rows, prow = [], []
    for v in list(YV) + list(FVV):
        tv = tr[tr.variant == v]
        if not len(tv):
            continue
        first_m = tv.day.min().to_period("M")
        months_total = len(pd.period_range(first_m, end_m, freq="M"))
        for sym in USD_PAIRS:
            d = tv[tv.sym == sym]
            if not len(d):
                continue
            r = {"variant": v, "name": NAMES[v], "pair": sym}
            r.update(test_row(d, months_total, None))
            r["passes bar"] = bool(r["design t"] >= 2 and r["check avg R"] > 0 and r["holdout avg R"] > 0)
            rows.append(r)
        ms = month_sum(tv, first_m, end_m)
        r = {"variant": v, "name": NAMES[v], "pair": "pooled 5"}
        r.update(test_row(tv, months_total, ms))
        pos = tv.groupby("sym").R.mean()
        r["pairs avg R > 0"] = int((pos > 0).sum())
        ok = r["design month t"] >= 2 and r["check avg R"] > 0 and r["holdout avg R"] > 0
        if v in FVV:
            ok = ok and r["pairs avg R > 0"] >= 3
        r["passes bar"] = bool(ok)
        prow.append(r)
    # Y5 judged on the monthly portfolio series
    y5m = y5_series(tr)
    y5 = tr[tr.variant == "Y5"]
    r = {"variant": "Y5", "name": NAMES["Y5"], "pair": "monthly portfolio (4 legs)"}
    months_total = len(pd.period_range(y5m.index.min(), end_m, freq="M"))
    lt = test_row(y5, months_total, None)
    r.update({"trades": lt["trades"], "trades/month": lt["trades/month"], "win %": lt["win %"],
              "avg win / avg loss": lt["avg win / avg loss"], "avg R": y5m.R.mean(), "t": tstat(y5m.R.to_numpy()),
              "month t (all)": tstat(y5m.R.to_numpy())})
    for p, (a, b) in PER.items():
        mm = y5m[(y5m.index >= pd.Period(a[:7], "M")) & (y5m.index <= pd.Period(b[:7], "M"))].R
        r[f"{p} n"] = len(mm)
        r[f"{p} avg R"] = mm.mean()
        r[f"{p} t"] = tstat(mm.to_numpy())
        r[f"{p} month t"] = r[f"{p} t"]
    mm = y5m[y5m.index >= pd.Period("2023-10", "M")].R
    r["last3y n"], r["last3y avg R"], r["last3y t"] = len(mm), mm.mean(), tstat(mm.to_numpy())
    r["last3y month t"] = r["last3y t"]
    r["SL %"] = (y5.reason == "SL").mean() * 100
    r["avg hold days"] = y5.hold_days.mean()
    r["pairs avg R > 0"] = int((y5.groupby("sym").R.mean() > 0).sum())
    r["passes bar"] = bool(r["design t"] >= 2 and r["check avg R"] > 0 and r["holdout avg R"] > 0)
    prow.append(r)
    pooled = pd.DataFrame(prow).set_index("variant").loc[JUDGED]
    tests = pd.DataFrame(rows)
    pooled.to_csv(f"{OUT}/pooled.csv")
    tests.to_csv(f"{OUT}/tests.csv", index=False)

    # Y5 leg-level stats per period (information)
    y5legs = pd.DataFrame([{"Y5 legs": "all", **test_row(y5, months_total, None)}]).set_index("Y5 legs")

    # ---------------- by year
    by_year = tr.groupby([tr.variant, tr.day.dt.year]).R.sum().unstack(0)
    by_year["Y5 (monthly portfolio)"] = y5m.groupby(y5m.index.year).R.sum()
    by_year = by_year[[c for c in JUDGED if c in by_year.columns and c != "Y5"] + ["Y5 (monthly portfolio)"]]
    by_year.index.name = "year"
    by_year.to_csv(f"{OUT}/by_year.csv")

    # ---------------- proxies and correlations
    mtab["entry_month"] = mtab.entry_month.astype(str)
    mt = mtab.set_index(["entry_month", "sym"])
    sgn = lambda side: 1.0 if side == "BUY" else -1.0

    def leg_gross(em, sym, side):
        if (em, sym) not in mt.index:
            return np.nan
        q = mt.loc[(em, sym)]
        return sgn(side) * (q.bo_x - q.bo_e) / (3.0 * q.atr) if q.atr > 0 else np.nan

    carry = mp[mp.plan == "CARRY"].copy()
    carry["g"] = [leg_gross(r.entry_month, r.sym, r.side) for r in carry.itertuples()]
    carry_m = carry.groupby("entry_month").g.mean()
    # cross-sectional price momentum ranking from the 16:44 NY closes of the USD pairs
    csd = cs.copy()
    csd["day"] = pd.to_datetime(csd.day)
    closes = {USD_PAIRS[s]: g.set_index("day").s for s, g in csd.groupby("sym")}
    mrows = []
    for sm in pd.period_range("2009-12", "2026-09", freq="M"):
        D = last_weekday(sm)
        chg = {"USD": 0.0}
        for c, s in closes.items():
            p = s.index.searchsorted(D, side="right") - 1
            chg[c] = s.iat[p] - s.iat[p - 63] if p - 63 >= 0 else np.nan
        if not all(np.isfinite(v) for v in chg.values()):
            continue
        order = sorted(CCYS, key=lambda c: -chg[c])
        em = str(sm + 1)
        for a in order[:2]:
            for b in order[-2:]:
                sym, side = pair_of(a, b)
                mrows.append((em, sym, side, leg_gross(em, sym, side)))
    momxs = pd.DataFrame(mrows, columns=["entry_month", "sym", "side", "g"])
    momxs_m = momxs.groupby("entry_month").g.mean()
    # weekly TS momentum on the 5 USD pairs + sign agreement with Y1
    wt = wtab.copy()
    wt["week"] = pd.to_datetime(wt.week)
    agree_rows = []
    trows = []
    y1sig = ws[ws.variant == "Y1"].set_index(["week", "ccy"]).sig
    for sym, g in wt.groupby("sym"):
        c = USD_PAIRS[sym]
        s = closes[c]
        base_foreign = sym.startswith(c)
        for r in g.itertuples(index=False):
            thu = r.week - pd.Timedelta(days=4)
            p = s.index.searchsorted(thu, side="right") - 1
            if p - 63 < 0 or not r.atr > 0:
                continue
            msig = np.sign(s.iat[p] - s.iat[p - 63])
            fx_ret = (r.bo_x - r.bo_e) * (1.0 if base_foreign else -1.0) / (3.0 * r.atr)   # oriented foreign/USD
            trows.append((pd.Timestamp(r.day).to_period("M"), msig * fx_ret))
            ysg = y1sig.get((r.week, c), np.nan)
            cdiff = value_before(pol[c], r.week - pd.Timedelta(days=3)) - value_before(pol["USD"], r.week - pd.Timedelta(days=3))
            if np.isfinite(ysg) and ysg != 0:
                agree_rows.append((sym, ysg == msig, ysg == np.sign(cdiff) if cdiff != 0 else np.nan))
    momts_m = pd.DataFrame(trows, columns=["m", "g"]).groupby("m").g.sum()
    y1 = tr[tr.variant == "Y1"]
    y1m = month_sum(y1, y1.day.min().to_period("M"), end_m)
    monthly = pd.DataFrame({"Y1": y1m})
    idx = monthly.index
    monthly["Y5"] = y5m.R.reindex(idx)
    monthly["CARRY"] = carry_m.rename(index=lambda x: pd.Period(x, "M")).reindex(idx)
    monthly["MOMXS"] = momxs_m.rename(index=lambda x: pd.Period(x, "M")).reindex(idx)
    monthly["MOMTS"] = momts_m.reindex(idx)
    monthly.index.name = "entry_month"
    monthly.to_csv(f"{OUT}/monthly.csv")
    corr = corr_block(monthly)
    corr.to_csv(f"{OUT}/corr.csv")
    ag = pd.DataFrame(agree_rows, columns=["sym", "mom", "carry"])
    agree = ag.groupby("sym").agg(active_weeks=("mom", "size"), agree_mom_pct=("mom", "mean"),
                                  agree_carry_pct=("carry", lambda x: pd.to_numeric(x, errors="coerce").mean()))
    agree.loc["all"] = [len(ag), ag["mom"].mean(), pd.to_numeric(ag["carry"], errors="coerce").mean()]
    agree[["agree_mom_pct", "agree_carry_pct"]] *= 100
    # Y5 legs in common with carry / momxs legs
    y5p = mp[mp.plan == "Y5"]
    common = []
    for em, g in y5p.groupby("entry_month"):
        legs = set(zip(g.sym, g.side))
        cg = carry[carry.entry_month == em]
        mg = momxs[momxs.entry_month == em]
        common.append((em, len(legs & set(zip(cg.sym, cg.side)))/4 if len(cg) else np.nan,
                       len(legs & set(zip(mg.sym, mg.side)))/4 if len(mg) else np.nan))
    common = pd.DataFrame(common, columns=["m", "carry", "momxs"])

    # ---------------- betas
    fvd = fv.copy()
    fvd["day"] = pd.to_datetime(fvd.day)
    fvd["period"] = period_of(fvd.day)
    bcols = [c for c in fvd.columns if c.startswith("beta_")]
    betas = fvd[fvd.period != ""].groupby(["sym", "period"])[bcols].median().unstack("period")
    betas = betas.reindex(columns=[(b, p) for b in bcols for p in PER])
    betas.columns = [f"{b.replace('beta_', '')} {p}" for b, p in betas.columns]
    betas.to_csv(f"{OUT}/betas.csv")
    sign_share = fvd[fvd.period != ""].groupby(["sym", "period"])["beta_M1_250"].apply(lambda x: (x > 0).mean() * 100).unstack()

    # ---------------- exposure
    expo = []
    for v in YV:
        x = ws[ws.variant == v]
        x = x[x.week <= END]
        fin = x.sig.notna()
        expo.append({"variant": v, "pair-weeks with a signal": int(fin.sum()),
                     "in position %": (x.sig[fin] != 0).mean() * 100,
                     "long foreign %": (x.sig[fin] > 0).mean() * 100, "short foreign %": (x.sig[fin] < 0).mean() * 100})
    for v in FVV:
        dz = sum(fv_info[s][v]["days_z"] for s in fv_info)
        dp = sum(fv_info[s][v]["days_in_pos"] for s in fv_info)
        expo.append({"variant": v, "pair-weeks with a signal": np.nan, "pair-days with z": dz,
                     "in position %": dp / dz * 100 if dz else np.nan})
    expo = pd.DataFrame(expo).set_index("variant")

    # ---------------- data coverage
    cov = Y.groupby(Y.index.year).apply(lambda d: d.notna().mean() * 100).round(1)
    cov.index.name = "year"

    # ---------------- report
    surv = [v for v in JUDGED if pooled.loc[v, "passes bar"]]
    L = []
    L.append("# Alpha hunt: FX under-reaction to relative 2-year yields (`fx_rates`)\n")
    L.append("Rules, variants and the survival bar are in the docstring of `run_alpha_fx_rates.py` (fixed before "
             "the first run). Markets: EURUSD GBPUSD AUDUSD USDJPY USDCAD (Y1-Y4, FV1-FV5) plus the 10 crosses "
             "among EUR JPY GBP CAD AUD for the cross-sectional Y5. All costs included ($7/lot, 0.2 pip slippage "
             "on stop fills, bid/ask fills, swap with 1% markup). Periods by entry day: design 2010-17, check "
             "2018-23, holdout 2024-26; last 3 years = entries 2023-10-08..2026-10-07.\n")
    L.append(f"**Judged tests: {len(JUDGED)}. Survivors of the charter bar (design t >= 2, avg R > 0 in check and "
             f"holdout; FV pooled also >= 3 of 5 pairs positive): {len(surv)} ({', '.join(surv) if surv else 'none'}). "
             f"Expected by luck: {len(JUDGED) * 0.006:.2f}.**\n")
    L.append("## Judged tests (pooled 5 USD pairs; Y5 = monthly portfolio series)\n")
    L.append("month t = month-clustered t (sum of R per calendar month of the entry day, zero for months "
             "without trades, from the first trade month; t over months); the design / check / holdout `t` "
             "columns are trade-level (Y5: monthly). For Y5, trades / win % / avg win/loss are leg-level and avg R, "
             "t and period columns are on the monthly portfolio R (mean of the 4 legs).\n")
    cols = ["name", "trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t (all)",
            "design n", "design avg R", "design t", "design month t", "check n", "check avg R", "check month t",
            "holdout n", "holdout avg R", "holdout month t", "last3y n", "last3y avg R", "last3y month t",
            "pairs avg R > 0", "SL %", "avg hold days", "passes bar"]
    L.append(fmt_table(pooled[cols], ".3f") + "\n")
    L.append("## Per pair (information only; trade-level t)\n")
    tcols = ["variant", "pair", "trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n",
             "design avg R", "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R",
             "holdout t", "last3y n", "last3y avg R", "last3y t", "SL %", "avg hold days", "passes bar"]
    tt = tests[tcols].set_index("variant")
    L.append(fmt_table(tt, ".3f") + "\n")
    L.append(f"Per-pair tests passing the charter bar: {int(tests['passes bar'].sum())} of {len(tests)} "
             f"(~{len(tests) * 0.006:.2f} expected by luck).\n")
    L.append("### Y5 legs (all 15 pairs, leg-level, information)\n")
    L.append(fmt_table(y5legs[[c for c in tcols if c in y5legs.columns]], ".3f") + "\n")
    y5bysym = tr[tr.variant == "Y5"].groupby("sym").R.agg(["size", "mean"]).rename(columns={"size": "legs", "mean": "avg R"})
    L.append(fmt_table(y5bysym.T, ".3f") + "\n")
    L.append("## Sum of R by year (entry year; Y5 = sum of monthly portfolio R)\n")
    L.append(fmt_table(by_year, ".2f") + "\n")
    L.append("## Is the signal separate from carry and price momentum?\n")
    L.append("Monthly series by entry month. CARRY = k=2 cross-sectional policy-rate carry (BIS policy rates, EUR = "
             "ECB deposit rate), MOMXS = k=2 cross-sectional 63-day price momentum, MOMTS = weekly 63-day "
             "time-series price momentum on the 5 USD pairs (all gross, no stop, in units of 3 x ATR20). OLS: "
             "monthly R on the three proxies with intercept (alpha t = plain OLS t).\n")
    L.append(fmt_table(corr, ".3f") + "\n")
    L.append("Sign agreement of active Y1 pair-weeks with the 63-day price-momentum sign and with the sign of the "
             "policy-rate differential (foreign - USD):\n")
    L.append(fmt_table(agree, ".1f") + "\n")
    L.append(f"Y5 legs shared with the CARRY legs in the same month: {common.carry.mean() * 100:.1f}% on average; "
             f"with the MOMXS legs: {common.momxs.mean() * 100:.1f}%.\n")
    L.append("## Stability of the FX / rates link: median rolling beta per pair and period\n")
    L.append("M1 = daily log-FX change (foreign/USD) per 1 pp change of the 2y spread (OLS slope); M2 = level slope. "
             "Positive = foreign currency rises when its 2y spread over the US rises.\n")
    L.append(fmt_table(betas, ".4f") + "\n")
    L.append("Share of days with a positive M1 W=250 beta (%):\n")
    L.append(fmt_table(sign_share[[p for p in PER]], ".1f") + "\n")
    L.append("## Exposure\n")
    L.append(fmt_table(expo, ".1f") + "\n")
    L.append("## Data\n")
    L.append("Yields: raw first / last observation: " + ", ".join(
        f"{c} {Y.attrs['raw_first'][c]}..{Y.attrs['raw_last'][c]}" for c in CCYS) + ". Coverage after the "
        "<= 3-weekday forward fill, % of weekdays per year:\n")
    L.append(fmt_table(cov, ".1f") + "\n")
    L.append("Sources:\n")
    for nm, f, u in SOURCES:
        L.append(f"- {nm}: `{f}` <- {u}")
    L.append("- CHF and NZD excluded (SNB rendoblid stops 2025-07-31; RBNZ blocks downloads).\n")
    L.append("Markets:\n")
    L.append(fmt_table(infos, ".0f") + "\n")
    L.append(f"Run time {raw['seconds'] / 60:.1f} min.\n")
    with open(f"{OUT}/REPORT.md", "w") as f:
        f.write("\n".join(L))
    print(pooled[["design n", "design avg R", "design month t", "check avg R", "holdout avg R", "last3y avg R",
                  "pairs avg R > 0", "passes bar"]].to_string(), flush=True)
    print(corr.to_string(), flush=True)
    return pooled


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(f"{OUT}/raw.pkl", "rb") as f:
            raw = pickle.load(f)
    else:
        raw = compute()
    report(raw)
    print("DONE", flush=True)
