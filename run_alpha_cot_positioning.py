"""Alpha hunt, family `cot_positioning`: CFTC futures positioning (Legacy Futures-Only COT) on the 7 G8 currencies
vs USD + gold, weekly. Crowded-speculator reversal (per market), hedging pressure and short-term speculative flow
(cross-sectional). Spec fixed BEFORE the first run; nothing below was chosen from the data.

Literature: Brunnermeier, Nagel & Pedersen 2008 (speculative positions and currency crash risk); Wang 2004 JFM and
Tornell & Yuan 2012 JFM (extreme speculator positioning near turning points); Bessembinder 1992 RFS and de Roon,
Nijman & Veld 2000 JF (hedging pressure moves futures risk premia); Basu & Miffre 2013 JBF (hedging-pressure long/short);
Kang, Rouwenhorst & Tang 2020 JF (short-horizon changes in speculative positions predict returns negatively: speculators
demand liquidity; the level of hedging pressure carries a premium). Counter-prior: Klitgaard & Weir 2004 (mostly
contemporaneous).

DATA
  CFTC Legacy Futures-Only annual files https://www.cftc.gov/files/dea/history/deacot{YYYY}.zip, 2005-2026, saved in
  data/extra/cftc/ (recorded in data/extra/SOURCES.csv, downloaded 2026-10-10). Rows with 'CFTC Contract Market Code' in
  {EUR 099741, JPY 097741, GBP 096742, CHF 092741, CAD 090741, AUD 232741, NZD 112741, GOLD 088691}. Fields 'As of Date in
  Form YYYY-MM-DD' (T, normally a Tuesday), 'Open Interest (All)', 'Noncommercial Positions-Long/Short (All)',
  'Commercial Positions-Long/Short (All)'. Files are concatenated in year order and (code, T) deduplicated keeping the last.

FEATURES (market, T), on each market's own report series (one row per weekly report)
  SP = (NC long - NC short) / OI.        HP = Comm long / (Comm long + Comm short).
  pct156 = percentile rank of SP_T among the 156 reports ending at T (T included); needs all 156 (the 2005-09 warm-up
           gives this before 2010). Rank definition: pct = 100 * (n_less + (n_equal - 1) / 2) / (N - 1), N = window,
           n_less / n_equal = window values < / == SP_T (n_equal counts SP_T itself). Max of window = 100, min = 0.
  pct52  = the same over 52 reports.
  zHP    = (HP_T - mean of HP over the 156 reports ending T) / sd (ddof=1) of the same.
  dSP    = SP_T - SP_prev, only if the previous report is within 9 days (else NaN).
  zdSP   = dSP_T / sd (ddof=1) of the 52 dSP values before T (T excluded); NaN if any of the 52 is NaN.

RELEASE AND ENTRY (no look-ahead)
  Pre-declared rule (kept for comparison): R_rule = T + 3 calendar days (Friday) 15:30 ET; if that day is a US federal
  holiday (holidays.US), the next weekday.
  Official dates: the CFTC release-schedule page is reachable but lists only 2026 (tentative schedule); past years are
  not online and web.archive.org is blocked. The CFTC "Historical Special Announcements" page lists the holiday delays
  and catch-up tables. Every official date found (2026 schedule: 52 dates; 2025 'original publish date' column: 16;
  special announcements 2011-11-14, 2014-12-30, 2015-07-06, 2018-12-28, 2019-01-04, 2020-12-28, 2021-06-21,
  2025-01-13) follows one rule, used here as the official release:
     R = the 3rd US federal business day after T, 15:30 ET (business day = Mon-Fri, not in holidays.US (observed days
     included) and not a federal closure day: 2007-01-02, 2007-12-24, 2008-12-26, 2009-01-20, 2012-12-24, 2014-12-26,
     2015-12-24, 2017-01-20, 2018-12-05, 2018-12-24, 2019-12-24, 2020-12-24, 2021-01-20, 2024-12-24, 2025-01-09).
  The script checks this rule against every official date above and reports mismatches, and reports how many
  tradeable reports have R_rule != R, and how many of those would have entered BEFORE the publication (look-ahead).
  SPEC FIX (impossibility = look-ahead): the pre-declared rule misses Wednesday/Thursday holidays (Thanksgiving,
  July 4, Veterans Day, Christmas, New Year) and Monday as-of dates (T + 3 = Thursday); in those weeks it would trade a
  report before it is published. The official rule is used for trading.
  Entry E = market order at the open of the 07:00 Europe/London minute on the first weekday strictly after R's date.
  SPEC FIX (impossibility): a minute with vol == 0 has no price, so "the 07:00 minute" of a market on a day is the first
  minute with vol > 0 in [07:00, 08:00) London; none (e.g. 25 Dec, 1 Jan) -> the next weekday, up to 7 tries
  (counted in the report). The same function gives every exit time, so an exit and the next entry share one minute.

EXCLUSION WINDOWS (reports published late in catch-up are not traded; their features still enter the rolling windows)
  T in [2013-09-30, 2013-11-15]  2013 shutdown (spec window to 2013-11-08; extended by one report as a precaution
                                 because the 2013 CFTC catch-up notice could not be fetched (rate limit / not found).
                                 CFTC notice 2011-04-08: no COT report in any week a funding lapse furloughs staff).
  T in [2018-12-17, 2019-03-08]  2018-19 shutdown. CFTC special announcement 2018-12-22 and PR 7864-19 (2019-01-29):
                                 catch-up from Fri 2019-02-01, one report Tue + one Fri, current by 2019-03-08.
  T in [2023-01-31, 2023-03-21]  SPEC FIX (look-ahead): ION Markets cyber incident. Special announcements 2023-02-02 ..
                                 2023-03-21: reports for T = 2023-01-31 .. 2023-03-14 were published 2023-02-24 ..
                                 2023-03-21 (weeks late). Not in the spec; added because trading them on the normal
                                 schedule would use unpublished data. T = 2023-03-21 is also excluded (no explicit
                                 return-to-normal notice).
  T in [2025-09-29, 2026-01-30]  2025 shutdown. Special announcement 2025-12-09 catch-up table: T = 2025-09-30 ..
                                 2026-01-13 published 2025-11-19 .. 2026-01-20; T = 2026-01-20 back on schedule.
  Only reports with T >= 2010-01-01 are traded.

INSTRUMENTS (long currency = ...)  EUR BUY EURUSD; GBP BUY GBPUSD; AUD BUY AUDUSD; NZD BUY NZDUSD; JPY SELL USDJPY;
  CHF SELL USDCHF; CAD SELL USDCAD; GOLD BUY XAUUSD. ATR20 = daily_table(m).atr20 of the NY session containing the
  entry minute (shifted = known before the session). No ATR (before 2010-03-18) -> not traded (warm-up).

HOLDS. Exit grid = the entry times of ALL weekly reports in order (for an excluded report: its normal-schedule entry
  time from the official rule). Weekly exit = the next grid time; 4-week exit = the 4th grid time after the entry.
  SPEC FIX: the spec's grid is "the next tradeable report"; across the exclusion windows that would turn a 1-week hold
  into a 2-4 month hold. Using all reports keeps the holds at 1 / 4 weeks as stated in VARIANTS; no information is
  needed for an exit time. Away from the windows the two definitions are identical.
  Stops checked minute by minute with gjstrat.patterns.simulate (real bid/ask). No TP. A trade whose exit time is after
  the data end (2026-10-07) is dropped.

VARIANTS (8 candidates)
  Crowding contrarian, per market, all 8 markets, one position per market per variant. Signals are ignored while a
  position is open; the next entry needs a report released after the previous exit (R > exit time).
    P1 pct156 >= 90 -> short the currency/gold; pct156 <= 10 -> long. 4-week hold, SL 2.5 x ATR20.
    P2 P1 with 95/5.
    P3 P1 using pct52 >= 90 / <= 10.
    P4 P1 only if VIX (FRED VIXCLS, data/extra/VIXCLS.csv, last value dated before R's date) >= its value 20
       observations (trading days) earlier.
  Hedging pressure, cross-sectional over the 7 currencies vs USD; needs all 7 zHP that week (ties by currency code):
    P5 long the 2 lowest zHP, short the 2 highest. 1-week hold, SL 2.0 x ATR20 per leg.
    P6 P5 rebalanced every 4th eligible tradeable report (eligible = tradeable with all 7 zHP; counted from the first
       eligible report with T >= 2010-01-01; cohort j enters when j % 4 == 0), 4-week hold, SL 2.5 x ATR20.
  Short-term flow, cross-sectional over the 7 currencies; needs all 7 zdSP:
    P7 short the 2 highest zdSP, long the 2 lowest. 1-week hold, SL 2.0 x ATR20.
    P8 the mirror of P7 (flow continuation), same bar.
  Each weekly leg is closed and reopened every week (full costs), even when the same currency stays.

COSTS. FX: gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m, 10_000, commission=7,
  swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'] (one call per market and variant).
  Gold: run_all_matrix.net_r (commission 0.07, slippage 0.02 per stop fill, 3%/yr financing). R = net / stop distance.
  Also R with swap set to zero (FX: account(swap=None); gold: net_r without the financing term).

STATS / SURVIVAL (charter). PER: design 2010-17, check 2018-23, holdout 2024-26 (by entry date). For each variant,
  pooled over its markets and legs: trades, trades/month, win %, avg win / avg loss, avg R and t per period,
  month-clustered t (sum of R per calendar month of entry, 0 for empty months, months from the first to the last
  entry month of the whole run), avg R with swap 0, last 3 years (entries after 2023-10-07). Per-market avg R and the
  number of markets with avg R > 0.
  SURVIVES if pooled trade-level design t >= 2 AND pooled avg R > 0 in check AND in holdout. A survivor whose
  month-clustered design t < 2 is labelled fragile (overlapping weekly legs are correlated).
  8 pooled tests -> 8 x 0.006 = 0.05 survivors expected by luck (about 0.2 if the 32 per-market cells counted).

DIAGNOSTICS (not used for survival)
  - share of FX trades on the higher-yield side (policy rates as in run_alpha_fx_carry.load_rates, last observation
    dated <= entry day - 1; long currency = higher-yield side if its rate > USD rate, short if USD rate > its rate).
  - share of trades in the direction of the pair's 63-session momentum (daily_table closes, last close before the entry
    session vs 63 closes earlier).
  - correlation of each variant's monthly R (sum per entry month) with fx_carry C1 monthly R (plain G8 carry,
    results/alpha_hunt/fx_carry/monthly_R.csv) and with 63-day cross-sectional FX momentum (fx_value_mom M2,
    results/alpha_hunt/fx_value_mom/monthly_R.csv), and with the current basket's monthly % (fx_carry/basket_monthly.csv);
    a carry or momentum copy is flagged (|corr| >= 0.5), not counted as new.
  - gold reported alone (per-market rows; P1-P4 also pooled without gold).
  - avg R in entry months where VIX rose > 30% (last VIXCLS value of the month vs last value of the previous month)
    vs other months.
  - overlap with the existing basket: number and avg R of USDJPY legs.

IF ANY SURVIVES: prop sim with gjstrat.prop.prop_table on run_m3_addon.build_legs() (basket vol-box 0.25% + vol-gotobi
  3% + fade 0.5% + M-3 USDJPY 3%) plus the survivor's trades as one leg at 0.5% and 1% risk, run_m3_addon.ALPHA rules,
  normal risk and boost x1.5 (run_prop_risk_rules.make_rule(boost=1.5)), challenge starts 2011-2025 and 2018-2025.
  Other-market trades are shifted onto the USDJPY grid by (m.t0 - m_usdjpy.t0) minutes. Accepted (as run_index_prop)
  if months per funded account is lower and pass eventually % not lower than the basket alone in both windows.

COMPUTE: COT features and plans need no prices. Then one market per worker (multiprocessing.Pool(2)): load, daily_table,
  exit grid, simulate every leg of every variant, account, del.

OUTPUT: results/alpha_hunt/cot_positioning/REPORT.md, cot_features.csv, trades.csv, summary.csv (+ per_market.csv,
  diagnostics.csv, release_check.csv, skipped.csv, run.log).

    python run_alpha_cot_positioning.py            # features, simulation, report (+ prop if a survivor)
    python run_alpha_cot_positioning.py --report   # report only, from trades.csv / skipped.csv
"""
import gc
import os
import sys
import time
import zipfile
from collections import namedtuple
from multiprocessing import Pool

import holidays
import numpy as np
import pandas as pd

from gjstrat.data import load_market
from gjstrat.patterns import LDN, NY, Signal, daily_table, local_idx, simulate
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/cot_positioning"
DATA = "data/{}_2010-01-01_2026-10-07.npz"
CODES = {"099741": "EUR", "097741": "JPY", "096742": "GBP", "092741": "CHF", "090741": "CAD", "232741": "AUD",
         "112741": "NZD", "088691": "GOLD"}
INSTR = {"EUR": ("EURUSD", 1), "GBP": ("GBPUSD", 1), "AUD": ("AUDUSD", 1), "NZD": ("NZDUSD", 1),
         "JPY": ("USDJPY", -1), "CHF": ("USDCHF", -1), "CAD": ("USDCAD", -1), "GOLD": ("XAUUSD", 1)}
CCY7 = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD"]
ALL8 = CCY7 + ["GOLD"]
VARIANTS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
NAMES = {"P1": "P1 crowding 156w 90/10", "P2": "P2 crowding 156w 95/5", "P3": "P3 crowding 52w 90/10",
         "P4": "P4 P1 + VIX rising", "P5": "P5 hedging pressure 1w", "P6": "P6 hedging pressure 4w cohorts",
         "P7": "P7 flow reversal (KRT) 1w", "P8": "P8 flow continuation 1w"}
HOLD = {"P1": 4, "P2": 4, "P3": 4, "P4": 4, "P5": 1, "P6": 4, "P7": 1, "P8": 1}
SLM = {"P1": 2.5, "P2": 2.5, "P3": 2.5, "P4": 2.5, "P5": 2.0, "P6": 2.5, "P7": 2.0, "P8": 2.0}
LAST3 = pd.Timestamp("2023-10-07")
TRADE_FROM = pd.Timestamp("2010-01-01")
DAY = pd.Timedelta(days=1)
US_HOL = {pd.Timestamp(d) for d in holidays.US(years=range(2004, 2028))}
CLOSURES = {pd.Timestamp(d) for d in ["2007-01-02", "2007-12-24", "2008-12-26", "2009-01-20", "2012-12-24",
                                      "2014-12-26", "2015-12-24", "2017-01-20", "2018-12-05", "2018-12-24",
                                      "2019-12-24", "2020-12-24", "2021-01-20", "2024-12-24", "2025-01-09"]}
EXCL = [("2013-09-30", "2013-11-15", "2013 shutdown"), ("2018-12-17", "2019-03-08", "2018-19 shutdown"),
        ("2023-01-31", "2023-03-21", "2023 ION incident"), ("2025-09-29", "2026-01-30", "2025 shutdown")]
# official dates found on cftc.gov (release-schedule page 2026; special announcements)
OFF_2026 = ["2026-01-05", "2026-01-09", "2026-01-16", "2026-01-23", "2026-01-30", "2026-02-06", "2026-02-13",
            "2026-02-20", "2026-02-27", "2026-03-06", "2026-03-13", "2026-03-20", "2026-03-27", "2026-04-03",
            "2026-04-10", "2026-04-17", "2026-04-24", "2026-05-01", "2026-05-08", "2026-05-15", "2026-05-22",
            "2026-05-29", "2026-06-05", "2026-06-12", "2026-06-22", "2026-06-26", "2026-07-06", "2026-07-10",
            "2026-07-17", "2026-07-24", "2026-07-31", "2026-08-07", "2026-08-14", "2026-08-21", "2026-08-28",
            "2026-09-04", "2026-09-11", "2026-09-18", "2026-09-25", "2026-10-02", "2026-10-09", "2026-10-16",
            "2026-10-23", "2026-10-30", "2026-11-06", "2026-11-16", "2026-11-20", "2026-11-30", "2026-12-04",
            "2026-12-11", "2026-12-18", "2026-12-28"]
OFF_OTHER = [("2011-11-08", "2011-11-14", "SA 2011-11-04 (Veterans Day Fri)"),
             ("2014-12-23", "2014-12-30", "SA 2014-12-19 (Dec 25-26)"),
             ("2015-06-30", "2015-07-06", "SA 2015-06-30 (July 3)"),
             ("2018-12-24", "2018-12-28", "SA 2018-12-21 (Monday data, Friday as usual)"),
             ("2018-12-31", "2019-01-04", "SA 2018-12-21 (Monday data, Friday as usual)"),
             ("2020-12-21", "2020-12-28", "SA 2020-12-28 (Dec 24 closure)"),
             ("2021-06-15", "2021-06-21", "SA 2021-06-17 (Juneteenth)"),
             ("2025-01-07", "2025-01-13", "SA 2025-01-07 (day of mourning)")] + \
            [(t, r, "SA 2025-12-09 original publish date") for t, r in [
                ("2025-09-30", "2025-10-03"), ("2025-10-07", "2025-10-10"), ("2025-10-14", "2025-10-17"),
                ("2025-10-21", "2025-10-24"), ("2025-10-28", "2025-10-31"), ("2025-11-04", "2025-11-07"),
                ("2025-11-10", "2025-11-14"), ("2025-11-18", "2025-11-21"), ("2025-11-25", "2025-12-01"),
                ("2025-12-02", "2025-12-05"), ("2025-12-09", "2025-12-12"), ("2025-12-16", "2025-12-19"),
                ("2025-12-23", "2025-12-29"), ("2025-12-30", "2026-01-05"), ("2026-01-06", "2026-01-09"),
                ("2026-01-13", "2026-01-16")]]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------------------------------------- schedule
def us_bday(d):
    return d.dayofweek < 5 and d not in US_HOL and d not in CLOSURES


def release_official(T):
    d, n = T, 0
    while n < 3:
        d += DAY
        n += us_bday(d)
    return d


def release_rule(T):
    R = T + 3 * DAY
    if R in US_HOL:
        R += DAY
        while R.dayofweek >= 5:
            R += DAY
    return R


def next_weekday(d):
    d += DAY
    while d.dayofweek >= 5:
        d += DAY
    return d


def et_ts(day, hh, mm):
    return (day + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(NY).tz_convert("UTC").tz_localize(None)


def excluded(T):
    for a, b, why in EXCL:
        if pd.Timestamp(a) <= T <= pd.Timestamp(b):
            return why
    return ""


def release_check():
    rows = []
    tues = pd.date_range("2025-12-30", "2026-12-22", freq="7D")
    for T, R in zip(tues, OFF_2026):
        rows.append(dict(T=T.date(), official=R, source="release schedule 2026", rule_official=release_official(T).date(),
                         rule_spec=release_rule(T).date()))
    for T, R, src in OFF_OTHER:
        T = pd.Timestamp(T)
        rows.append(dict(T=T.date(), official=R, source=src, rule_official=release_official(T).date(),
                         rule_spec=release_rule(T).date()))
    c = pd.DataFrame(rows)
    c["official_rule_ok"] = c.rule_official.astype(str) == c.official
    c["spec_rule_ok"] = c.rule_spec.astype(str) == c.official
    return c


# ----------------------------------------------------------------------------------------------- COT features
def pct_rank(w):
    x = w[-1]
    return 100.0 * ((w < x).sum() + ((w == x).sum() - 1) / 2) / (len(w) - 1)


def load_cot():
    num = lambda s: pd.to_numeric(s.str.strip().str.replace(",", ""), errors="coerce")
    rows = []
    for y in range(2005, 2027):
        z = zipfile.ZipFile(f"data/extra/cftc/deacot{y}.zip")
        df = pd.read_csv(z.open(z.namelist()[0]), dtype=str, low_memory=False)
        df["code"] = df["CFTC Contract Market Code"].str.strip()
        x = df[df.code.isin(CODES)]
        rows.append(pd.DataFrame({
            "ccy": x.code.map(CODES).to_numpy(), "code": x.code.to_numpy(),
            "T": pd.to_datetime(x["As of Date in Form YYYY-MM-DD"].str.strip()).to_numpy(),
            "OI": num(x["Open Interest (All)"]).to_numpy(),
            "NC_long": num(x["Noncommercial Positions-Long (All)"]).to_numpy(),
            "NC_short": num(x["Noncommercial Positions-Short (All)"]).to_numpy(),
            "Comm_long": num(x["Commercial Positions-Long (All)"]).to_numpy(),
            "Comm_short": num(x["Commercial Positions-Short (All)"]).to_numpy()}))
    c = pd.concat(rows, ignore_index=True).drop_duplicates(["code", "T"], keep="last")
    return c.sort_values(["ccy", "T"]).reset_index(drop=True)


def features(c):
    out = []
    for ccy, g in c.groupby("ccy", sort=False):
        g = g.sort_values("T").copy()
        g["SP"] = (g.NC_long - g.NC_short) / g.OI
        g["HP"] = g.Comm_long / (g.Comm_long + g.Comm_short)
        g["pct156"] = g.SP.rolling(156).apply(pct_rank, raw=True)
        g["pct52"] = g.SP.rolling(52).apply(pct_rank, raw=True)
        g["zHP"] = (g.HP - g.HP.rolling(156).mean()) / g.HP.rolling(156).std(ddof=1)
        gap = g["T"].diff().dt.days
        g["dSP"] = g.SP.diff().where(gap <= 9)
        g["zdSP"] = g.dSP / g.dSP.shift(1).rolling(52).std(ddof=1)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def load_vix():
    v = pd.read_csv("data/extra/VIXCLS.csv", parse_dates=["observation_date"])
    return pd.Series(pd.to_numeric(v.VIXCLS, errors="coerce").to_numpy(), index=v.observation_date).dropna().sort_index()


def schedule(F, vix):
    S = pd.DataFrame({"T": sorted(F["T"].unique())})
    S["T"] = pd.to_datetime(S["T"])
    S["R_rule"] = S["T"].map(release_rule)
    S["R"] = S["T"].map(release_official)
    S["rel_ts"] = S["R"].map(lambda d: et_ts(d, 15, 30))
    S["E_date"] = S["R"].map(next_weekday)
    S["E_rule"] = S["R_rule"].map(next_weekday)
    S["excl"] = S["T"].map(excluded)
    S["tradeable"] = (S["T"] >= TRADE_FROM) & (S.excl == "")
    vi = vix.index
    last, ago = [], []
    for R in S["R"]:
        k = vi.searchsorted(R, side="left") - 1          # last value dated strictly before R's date
        last.append(vix.iloc[k] if k >= 0 else np.nan)
        ago.append(vix.iloc[k - 20] if k >= 20 else np.nan)
    S["vix"], S["vix_20ago"] = last, ago
    S["vix_up"] = S.vix >= S.vix_20ago
    S["k"] = np.arange(len(S))
    return S


def plans(F, S):
    """P1-P4: per (variant, ccy) dict k -> direction of the currency (+1 long / -1 short).
    P5-P8: list of legs (variant, ccy, k, direction)."""
    kof = dict(zip(S["T"], S["k"]))
    trad = dict(zip(S["k"], S["tradeable"]))
    vixup = dict(zip(S["k"], S["vix_up"]))
    sig = {(v, c): {} for v in VARIANTS[:4] for c in ALL8}
    for r in F.itertuples(index=False):
        k = kof[r.T]
        if not trad[k]:
            continue
        for v, col, hi, lo in (("P1", "pct156", 90, 10), ("P2", "pct156", 95, 5), ("P3", "pct52", 90, 10)):
            x = getattr(r, col)
            if np.isnan(x):
                continue
            d = -1 if x >= hi else (1 if x <= lo else 0)
            if d:
                sig[(v, r.ccy)][k] = d
        if r.ccy and not np.isnan(r.pct156) and (r.pct156 >= 90 or r.pct156 <= 10) and vixup[k]:
            sig[("P4", r.ccy)][k] = -1 if r.pct156 >= 90 else 1
    legs = []
    X = F[F.ccy.isin(CCY7)]
    wide = {col: X.pivot(index="T", columns="ccy", values=col)[CCY7] for col in ("zHP", "zdSP")}
    j6 = 0
    for T in S.loc[S.tradeable, "T"]:
        k = kof[T]
        z = wide["zHP"].loc[T] if T in wide["zHP"].index else None
        if z is not None and z.notna().all():
            order = sorted(CCY7, key=lambda c: (z[c], c))
            lv = [(c, 1) for c in order[:2]] + [(c, -1) for c in order[-2:]]
            legs += [("P5", c, k, d) for c, d in lv]
            if j6 % 4 == 0:
                legs += [("P6", c, k, d) for c, d in lv]
            j6 += 1
        q = wide["zdSP"].loc[T] if T in wide["zdSP"].index else None
        if q is not None and q.notna().all():
            order = sorted(CCY7, key=lambda c: (q[c], c))
            legs += [("P7", c, k, 1) for c in order[:2]] + [("P7", c, k, -1) for c in order[-2:]]
            legs += [("P8", c, k, -1) for c in order[:2]] + [("P8", c, k, 1) for c in order[-2:]]
    return sig, legs


# ----------------------------------------------------------------------------------------------- per-market worker
def ny_label(ts):
    return (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def worker(job):
    ccy, S, sig, legs = job
    from run_all_matrix import NON_FX, net_r
    from gjstrat.accounting import account
    from gjstrat.swap import SwapModel
    sym, sgn = INSTR[ccy]
    sw = SwapModel.from_fred("rates", 1.0)
    m = load_market(DATA.format(sym.lower()))
    d = daily_table(m)
    close = d["close"].to_numpy()
    K = len(S)
    grid = np.full(K, -1, dtype=np.int64)
    fallback = np.zeros(K, dtype=bool)
    for k, day in enumerate(S["E_date"]):
        dd = day
        for _ in range(7):
            i0 = local_idx(m, dd, 7, 0, LDN)
            if i0 >= m.n:
                break
            if i0 >= 0:
                w = np.flatnonzero(m.vol[i0:i0 + 60] > 0)
                if len(w):
                    grid[k] = i0 + w[0]
                    fallback[k] = dd != day
                    break
            dd = next_weekday(dd)
    rel = S["rel_ts"].to_numpy()
    Tcol = S["T"].to_numpy()
    skipped = []

    def make(v, k, dccy):
        """Simulate one leg; returns (trade, meta) or None (reason appended to skipped)."""
        kx = k + HOLD[v]
        ei = grid[k]
        xi = grid[kx] if kx < K else -1
        if ei < 0 or xi < 0 or xi >= m.n:
            skipped.append(dict(variant=v, ccy=ccy, T=Tcol[k], why="exit after data end" if ei >= 0 else "no entry minute"))
            return None
        if xi <= ei:
            skipped.append(dict(variant=v, ccy=ccy, T=Tcol[k], why="exit grid <= entry"))
            return None
        lab = ny_label(m.ts(ei))
        p = d.index.searchsorted(lab)
        if p >= len(d) or d.index[p] != lab or np.isnan(d["atr20"].iat[p]):
            skipped.append(dict(variant=v, ccy=ccy, T=Tcol[k], why="no ATR20 (warm-up)"))
            return None
        atr = float(d["atr20"].iat[p])
        side = "BUY" if dccy * sgn > 0 else "SELL"
        day = m.ts(ei).normalize()
        t = simulate(m, Signal(day, side, int(ei), "market", None, int(ei) + 1, SLM[v] * atr, None, int(xi), v))
        if t is None:
            skipped.append(dict(variant=v, ccy=ccy, T=Tcol[k], why="simulate None"))
            return None
        mom = np.log(close[p - 1] / close[p - 64]) if p >= 64 else np.nan
        meta = dict(variant=v, ccy=ccy, sym=sym, side=side, dir_ccy=dccy, k=k, T=pd.Timestamp(Tcol[k]),
                    release_ts=pd.Timestamp(rel[k]), entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i),
                    entry_day=day, reason=t.reason, atr=atr, sl_pips=t.risk / m.pip, spread_pips=t.spread / m.pip,
                    priceR=t.r,
                    mom63_pair=mom, mom_aligned=(np.sign(mom) == (1 if side == "BUY" else -1)) if not np.isnan(mom)
                    else np.nan, entry_fallback=bool(fallback[k]), entry_i=t.entry_i, exit_i=t.exit_i)
        return t, meta

    out = []
    for v in VARIANTS:
        pairs = []
        if v in ("P1", "P2", "P3", "P4"):
            last_exit = None
            for k in sorted(sig[(v, ccy)]):
                if last_exit is not None and rel[k] <= np.datetime64(last_exit):
                    continue
                x = make(v, k, sig[(v, ccy)][k])
                if x is None:
                    continue
                pairs.append(x)
                last_exit = x[1]["exit_ts"]
        else:
            for (vv, c, k, dccy) in legs:
                if vv == v and c == ccy:
                    x = make(v, k, dccy)
                    if x is not None:
                        pairs.append(x)
        if not pairs:
            continue
        pairs.sort(key=lambda x: (x[0].exit_i, x[0].entry_i))
        tr = [x[0] for x in pairs]
        if sym == "XAUUSD":
            R = net_r(m, sym, tr, sw)
            comm, slip = NON_FX[sym]
            R0 = np.array([t.r - (comm + slip * (1 + (t.reason in ("SL", "BE")))) / t.risk for t in tr])
        else:
            lg = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
            lg0 = account(tr, m, 10_000, commission=7, swap=None, sym=sym, slippage_pips=0.2)
            assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
            assert (lg0["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
            R, R0 = lg["R"].to_numpy(), lg0["R"].to_numpy()
        for (t, meta), a, b in zip(pairs, R, R0):
            meta.update(R=float(a), R0=float(b), swapR=float(a - b))
            out.append(meta)
    info = dict(ccy=ccy, sym=sym, t0=str(m.t0), n=m.n, fallbacks=int(fallback[grid >= 0].sum()),
                grid_missing=int((grid < 0).sum()))
    del m, d
    gc.collect()
    return out, skipped, info


# ----------------------------------------------------------------------------------------------- stats
def period_mask(day, p):
    a, b = PER[p]
    return (day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))


def summarize(df, months):
    """df: trades with R, R0, entry_day. months: PeriodIndex of the whole run (0 for empty months)."""
    r = df["R"].to_numpy(float)
    r0 = df["R0"].to_numpy(float)
    day = pd.DatetimeIndex(df["entry_day"])
    win, loss = r[r > 0], r[r <= 0]
    o = {"trades": len(r), "trades/month": len(r) / len(months),
         "win %": (r > 0).mean() * 100 if len(r) else np.nan,
         "avg win/avg loss": win.mean() / -loss.mean() if len(win) and len(loss) and loss.mean() < 0 else np.nan,
         "avg R": r.mean() if len(r) else np.nan, "t": tstat(r), "avg R swap0": r0.mean() if len(r) else np.nan,
         "SL %": (df["reason"] == "SL").mean() * 100 if len(r) else np.nan}
    mon = day.to_period("M")
    msum = pd.Series(r, index=mon).groupby(level=0).sum().reindex(months, fill_value=0.0)
    o["month t"] = tstat(msum.to_numpy())
    for p in PER:
        sel = period_mask(day, p)
        v = r[sel]
        o[f"{p} n"], o[f"{p} avg R"], o[f"{p} t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
        a, b = PER[p]
        ms = msum[(msum.index >= pd.Period(a[:7], "M")) & (msum.index <= pd.Period(b[:7], "M"))]
        o[f"{p} month t"] = tstat(ms.to_numpy())
        o[f"{p} avg R swap0"] = r0[sel].mean() if sel.any() else np.nan
    v = r[day > LAST3]
    o["last3y n"], o["last3y avg R"], o["last3y t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
    return o


def monthly(df, months):
    mon = pd.DatetimeIndex(df["entry_day"]).to_period("M")
    return pd.Series(df["R"].to_numpy(float), index=mon).groupby(level=0).sum().reindex(months, fill_value=0.0)


def ref_monthly(path, col):
    if not os.path.exists(path):
        return None
    x = pd.read_csv(path, index_col=0)
    if col not in x:
        return None
    s = pd.to_numeric(x[col], errors="coerce")
    s.index = pd.PeriodIndex(pd.to_datetime(x.index.astype(str)), freq="M")
    return s.dropna()


def corr(a, b):
    if b is None:
        return np.nan, 0
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    return (j.iloc[:, 0].corr(j.iloc[:, 1]) if len(j) > 2 else np.nan), len(j)


# ----------------------------------------------------------------------------------------------- report
def report(T, skipped, S, F, chk, infos):
    T = T.copy()
    for c in ("T", "entry_day", "entry_ts", "exit_ts", "release_ts"):
        T[c] = pd.to_datetime(T[c])
    first, last = T.entry_day.min().to_period("M"), T.entry_day.max().to_period("M")
    months = pd.period_range(first, last, freq="M")

    # higher-yield side
    from run_alpha_fx_carry import last_before, load_rates
    rates = load_rates()
    hy = []
    for r in T.itertuples(index=False):
        if r.ccy == "GOLD":
            hy.append(np.nan)
            continue
        dd = r.entry_day - DAY
        rc, ru = last_before(rates[r.ccy], dd)[0], last_before(rates["USD"], dd)[0]
        diff = (rc - ru) * r.dir_ccy
        hy.append(1.0 if diff > 0 else (0.0 if diff < 0 else 0.5))
    T["hy_side"] = hy
    vix = load_vix()
    vm = vix.groupby(vix.index.to_period("M")).last()
    vrise = (vm / vm.shift(1) - 1) > 0.30
    T["vix_rise_month"] = pd.DatetimeIndex(T.entry_day).to_period("M").map(lambda p: bool(vrise.get(p, False)))

    carry = ref_monthly("results/alpha_hunt/fx_carry/monthly_R.csv", "C1")
    mom = ref_monthly("results/alpha_hunt/fx_value_mom/monthly_R.csv", "M2")
    bpath = "results/alpha_hunt/fx_carry/basket_monthly.csv"
    basket = None
    if os.path.exists(bpath):
        b = pd.read_csv(bpath, index_col=0)
        basket = pd.Series(b["pct"].to_numpy(float), index=pd.PeriodIndex(b.index.astype(str), freq="M"))

    SUM, PM, DG, YR = [], [], [], []
    for v in VARIANTS:
        q = T[T.variant == v]
        s = summarize(q, months)
        s["markets avg R > 0"] = int((q.groupby("ccy")["R"].mean() > 0).sum())
        s["markets"] = q.ccy.nunique()
        surv = s["design t"] >= 2 and s["check avg R"] > 0 and s["holdout avg R"] > 0
        s["survives"] = ("YES (fragile: month t < 2)" if s["design month t"] < 2 else "YES") if surv else "no"
        SUM.append(pd.Series(s, name=v))
        for c, g in q.groupby("ccy"):
            x = summarize(g, months)
            PM.append(dict(variant=v, ccy=c, sym=INSTR[c][0], trades=x["trades"], **{"avg R": x["avg R"], "t": x["t"]},
                           **{f"{p} avg R": x[f"{p} avg R"] for p in PER}, **{"design t": x["design t"]},
                           **{"last3y avg R": x["last3y avg R"]}))
        ms = monthly(q, months)
        cc, nc = corr(ms, carry)
        cm, nm = corr(ms, mom)
        cb, nb = corr(ms, basket)
        fx = q[q.ccy != "GOLD"]
        vr = q[q.vix_rise_month]
        vo = q[~q.vix_rise_month]
        jp = q[q.ccy == "JPY"]
        g = {"higher-yield side %": (fx.hy_side == 1).mean() * 100, "lower-yield side %": (fx.hy_side == 0).mean() * 100,
             "with 63d momentum %": q.mom_aligned.dropna().astype(float).mean() * 100,
             "corr carry C1": cc, "corr mom63 M2": cm, "corr basket": cb, "months corr": nc,
             "VIX-rise months n": len(vr), "VIX-rise months avg R": vr.R.mean(),
             "other months avg R": vo.R.mean(), "USDJPY legs": len(jp), "USDJPY avg R": jp.R.mean(),
             "price R": q.priceR.mean(), "swap R": q.swapR.mean(), "cost R": (q.priceR + q.swapR - q.R).mean()}
        if v in VARIANTS[:4]:
            xg = summarize(fx, months)
            g["ex-gold avg R"], g["ex-gold design t"] = xg["avg R"], xg["design t"]
            g["ex-gold check avg R"], g["ex-gold holdout avg R"] = xg["check avg R"], xg["holdout avg R"]
        g["copy flag"] = "carry" if abs(cc) >= 0.5 else ("momentum" if abs(cm) >= 0.5 else "")
        DG.append(pd.Series(g, name=v))
        yr = q.groupby(pd.DatetimeIndex(q.entry_day).year)["R"].agg(["count", "mean"])
        YR.append(yr["mean"].rename(v))
    SUM, DG = pd.DataFrame(SUM), pd.DataFrame(DG)
    SUM.index.name = DG.index.name = "variant"
    PM = pd.DataFrame(PM)
    YR = pd.DataFrame(YR).T
    YR.index.name = "year"
    SUM.insert(0, "name", [NAMES[v] for v in SUM.index])
    SUM.to_csv(f"{OUT}/summary.csv")
    PM.to_csv(f"{OUT}/per_market.csv", index=False)
    DG.to_csv(f"{OUT}/diagnostics.csv")
    T.to_csv(f"{OUT}/trades.csv", index=False)

    # release-date statistics on tradeable reports
    St = S[S.tradeable & (S["T"] <= pd.Timestamp("2026-10-06"))]
    diff = St[St.R != St.R_rule]
    early = diff[diff.E_rule <= diff.R]        # rule entry day on or before the official release day -> look-ahead
    survivors = [v for v in VARIANTS if SUM.loc[v, "survives"].startswith("YES")]

    L = []
    L.append("# Alpha hunt: CFTC positioning (cot_positioning)\n")
    L.append("Script: `run_alpha_cot_positioning.py` (rules fixed in its docstring before the first run). Markets: "
             "EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCHF, USDCAD (CME currency futures positioning mapped to spot) "
             "and XAUUSD (COMEX gold). CFTC Legacy Futures-Only reports 2005-2026, trades from 2010. "
             "Costs included everywhere (commission 7/lot, 0.2 pip slippage per stop fill, swap at FRED rates "
             "+1% markup; gold: run_all_matrix.net_r).\n")
    L.append(f"**Survivors (design t >= 2, check avg R > 0, holdout avg R > 0): {', '.join(survivors) or 'none'}** "
             f"of 8 pooled tests. Luck alone: 8 x 0.006 = 0.05 (about 0.2 counting the 32 per-market cells).\n")
    L.append("## Pooled results per variant\n")
    cols = ["name", "trades", "trades/month", "win %", "avg win/avg loss", "avg R", "t", "month t", "design n",
            "design avg R", "design t", "design month t", "check n", "check avg R", "check t", "holdout n",
            "holdout avg R", "holdout t", "last3y n", "last3y avg R", "last3y t", "markets avg R > 0", "survives"]
    L.append(fmt_table(SUM[cols], ".3f") + "\n")
    L.append("`t` = trade-level t; `month t` = t of the monthly sum of R (0 for empty months), which allows for the "
             "correlation between legs entered in the same week. Last 3 years = entries after 2023-10-07.\n")
    L.append("### Swap and stops\n")
    cols2 = ["avg R", "avg R swap0", "design avg R swap0", "check avg R swap0", "holdout avg R swap0", "SL %"]
    L.append(fmt_table(SUM[cols2], ".3f") + "\n")
    L.append("### Gross of costs (price R only, before commission, slippage and swap; descriptive, not a test)\n")
    GR = []
    for v in VARIANTS:
        q = T[T.variant == v]
        day = pd.DatetimeIndex(q.entry_day)
        g = {"price R": q.priceR.mean(), "t": tstat(q.priceR)}
        for p in PER:
            x = q.priceR[period_mask(day, p)]
            g[f"{p} price R"], g[f"{p} t"] = x.mean(), tstat(x)
        GR.append(pd.Series(g, name=v))
    GR = pd.DataFrame(GR)
    GR.index.name = "variant"
    L.append(fmt_table(GR, ".3f") + "\n")
    L.append("## Reading\n")
    s5, d5 = SUM.loc["P5"], DG.loc["P5"]
    L.append(
        f"- Crowding (P1-P4): design avg R {SUM.loc['P1', 'design avg R']:.3f} / {SUM.loc['P2', 'design avg R']:.3f} / "
        f"{SUM.loc['P3', 'design avg R']:.3f} / {SUM.loc['P4', 'design avg R']:.3f} (t {SUM.loc['P1', 'design t']:.2f} / "
        f"{SUM.loc['P2', 'design t']:.2f} / {SUM.loc['P3', 'design t']:.2f} / {SUM.loc['P4', 'design t']:.2f}). Check and "
        f"holdout avg R range from {SUM.loc['P1':'P4', ['check avg R', 'holdout avg R']].min().min():.3f} to "
        f"{SUM.loc['P1':'P4', ['check avg R', 'holdout avg R']].max().max():.3f}, with |t| <= "
        f"{SUM.loc['P1':'P4', ['check t', 'holdout t']].abs().max().max():.2f}, and per-market signs are mixed. "
        "Fading speculator extremes "
        "is a bet against 63-day momentum (only "
        f"{DG.loc['P1', 'with 63d momentum %']:.0f}% of P1 trades go with it), and over 4-week holds it pays about "
        f"{-DG.loc['P1', 'swap R']:.2f}R of swap per trade.")
    L.append(
        f"- Hedging pressure (P5, P6) has the wrong sign in every period: P5 avg R {s5['avg R']:.3f} (t {s5['t']:.2f}; "
        f"design t {s5['design t']:.2f}), gross price R {GR.loc['P5', 'price R']:.3f} (gross t {GR.loc['P5', 't']:.2f}: "
        "about half of the net t comes from costs and swap). Going long the currencies whose "
        "commercials are unusually net short means going with speculators. "
        f"{d5['with 63d momentum %']:.0f}% of P5 legs go with 63-day momentum (corr with FX momentum M2 "
        f"{d5['corr mom63 M2']:.2f}). The mirror was not pre-declared. Its gross edge (about "
        f"{-GR.loc['P5', 'price R']:.3f}R per leg) is about the size of the weekly cost and swap drag "
        f"(about {d5['cost R'] - d5['swap R']:.3f}R), so it is not an edge either.")
    L.append(
        f"- Short-term flow: the Kang-Rouwenhorst-Tang sign is right before costs (P7 gross {GR.loc['P7', 'price R']:.3f}R, "
        f"t {GR.loc['P7', 't']:.2f}; P8 gross {GR.loc['P8', 'price R']:.3f}R), but with a 2 x ATR20 stop (about 150-220 "
        "pips) one week of drift is a few pips, and costs and swap remove it (P7 net "
        f"{SUM.loc['P7', 'avg R']:.3f}R).")
    mc = DG[["corr carry C1", "corr mom63 M2"]].abs().max().max()
    mb = DG["corr basket"].abs().max()
    L.append(f"- No variant copies carry or FX momentum (max |corr| {mc:.2f}) or the current basket (max |corr| "
             f"{mb:.2f}). The positioning signal is new information, but none of these rules turns it into an edge "
             "after costs.\n")
    L.append("## Per market (avg R per period)\n")
    pm = PM.copy()
    pm["cell"] = pm["variant"] + " " + pm["ccy"]
    pm = pm.set_index("cell")[["sym", "trades", "avg R", "t", "design avg R", "design t", "check avg R",
                                "holdout avg R", "last3y avg R"]]
    pm.index.name = "variant / market"
    L.append(fmt_table(pm, ".3f") + "\n")
    L.append("## Diagnostics\n")
    L.append(fmt_table(DG, ".3f") + "\n")
    L.append("Higher-/lower-yield side: FX trades only (gold excluded); the rest had equal policy rates. "
             "Correlations use monthly sums of R vs fx_carry C1 (plain G8 carry k=2), fx_value_mom M2 (63-day "
             "cross-sectional momentum k=2) and the current basket's monthly % (vol-box, gotobi, fade, M-3); "
             "`copy flag` marks |corr| >= 0.5. VIX-rise months: the month's last VIXCLS value > 1.3 x the previous "
             "month's. Price/swap/cost R: mean per trade (net R = price + swap - cost).\n")
    L.append("## Avg R by entry year\n")
    L.append(fmt_table(YR, ".3f") + "\n")
    L.append("## Release dates and exclusions\n")
    nb = int((~chk.official_rule_ok).sum())
    L.append(f"- Official-date check: the rule used (3rd US federal business day after T, 15:30 ET) matches "
             f"{int(chk.official_rule_ok.sum())} of {len(chk)} official dates found on cftc.gov; the pre-declared "
             f"T+3 rule matches {int(chk.spec_rule_ok.sum())}. Mismatches of the rule used: {nb}"
             + ("" if nb == 0 else " (" + "; ".join(f"T {r.T}: official {r.official}, rule {r.rule_official} ({r.source})"
                                                  for r in chk[~chk.official_rule_ok].itertuples()) + ")") + ".")
    L.append(f"- Tradeable reports 2010-2026: {len(St)}. R differs from the pre-declared rule for {len(diff)}; in "
             f"{len(early)} of them the pre-declared rule would have entered on or before the official release day "
             f"(look-ahead) - these are Wednesday/Thursday-holiday weeks and Monday as-of dates.")
    ex = S[(S["T"] >= TRADE_FROM) & (S.excl != "")].groupby("excl")["T"].agg(["count", "min", "max"])
    L.append("- Not traded (published late in catch-up): " + "; ".join(
        f"{i}: {r['count']} reports, T {r['min'].date()} .. {r['max'].date()}" for i, r in ex.iterrows()) + ".")
    fb = sum(i["fallbacks"] for i in infos) if infos else 0
    L.append(f"- Entry/exit minutes moved to the next weekday because 07:00-08:00 London had no ticks: {fb} market-weeks "
             f"(holidays such as 25 Dec / 1 Jan).")
    sk = skipped.groupby(["why"]).size() if len(skipped) else pd.Series(dtype=int)
    L.append("- Legs not simulated: " + (", ".join(f"{k}: {n}" for k, n in sk.items()) or "none") + ".\n")
    L.append("## Data\n")
    L.append("`cot_features.csv` (SP, HP, pct156, pct52, zHP, dSP, zdSP per market and report, with release date, "
             "entry date, tradeable flag and the P4 VIX gate), `trades.csv` (every simulated leg with R, R at zero "
             "swap, swap R, side, yield side, momentum alignment), `summary.csv`, `per_market.csv`, "
             "`diagnostics.csv`, `release_check.csv`, `skipped.csv`.\n")
    return "\n".join(L), survivors


# ----------------------------------------------------------------------------------------------- prop
Tr = namedtuple("Tr", "day entry_i exit_i")


def prop(T, survivors):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    m, legs = build_legs()
    t0 = {}
    for ccy in ALL8:
        sym = INSTR[ccy][0]
        if sym == "USDJPY":
            t0[ccy] = m.t0
        else:
            mm = load_market(DATA.format(sym.lower()))
            t0[ccy] = mm.t0
            del mm
            gc.collect()
    base = (0.25, 3, 0.5, 3, 0)
    for v in survivors:
        q = T[T.variant == v].sort_values(["exit_ts", "entry_ts"])
        tr, r = [], []
        for x in q.itertuples(index=False):
            off = int((t0[x.ccy] - m.t0) // pd.Timedelta(minutes=1))
            tr.append(Tr(pd.Timestamp(x.entry_day), int(x.entry_i) + off, int(x.exit_i) + off))
            r.append(x.R)
        legs.append((tr, np.array(r)))
    mixes = {"basket": base + (0,) * len(survivors)}
    for risk in (0.5, 1):
        for j, v in enumerate(survivors):
            mixes[f"basket + {v} {risk}%"] = base + tuple(risk if i == j else 0 for i in range(len(survivors)))
    tabs = []
    for rule, scale in (("normal risk", None), ("boost x1.5", make_rule(boost=1.5))):
        for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
            t = prop_table(m, lg, mixes, **ALPHA, **({"scale": scale} if scale else {}))
            t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
            t.insert(0, "window", w)
            t.insert(0, "risk rule", rule)
            tabs.append(t)
            log("prop", rule, w)
    P = pd.concat(tabs)
    acc = {}
    for rule in P["risk rule"].unique():
        for mix in list(mixes)[1:]:
            acc[(rule, mix)] = all(
                P[(P["risk rule"] == rule) & (P.window == w)].loc[mix, "months per funded account"]
                < P[(P["risk rule"] == rule) & (P.window == w)].loc["basket", "months per funded account"]
                and P[(P["risk rule"] == rule) & (P.window == w)].loc[mix, "pass eventually %"]
                >= P[(P["risk rule"] == rule) & (P.window == w)].loc["basket", "pass eventually %"]
                for w in P.window.unique())
    P["accepted"] = [None if mix == "basket" else acc[(rule, mix)] for rule, mix in zip(P["risk rule"], P.index)]
    P.index.name = "mix"
    P.to_csv(f"{OUT}/prop.csv")
    cols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
            "pass eventually %", "median months to pass", "months per funded account", "accepted"]
    cols = [c for c in cols if c in P.columns]
    return "## Prop simulation (Alpha Swing, survivors added to the basket)\n\n" + fmt_table(P[cols], ".1f") + "\n"


# ----------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    only_report = "--report" in sys.argv
    t_start = time.time()
    c = load_cot()
    F = features(c)
    vix = load_vix()
    S = schedule(F, vix)
    chk = release_check()
    chk.to_csv(f"{OUT}/release_check.csv", index=False)
    log("COT rows", len(F), "reports", len(S), "tradeable", int(S.tradeable.sum()),
        "official-rule mismatches", int((~chk.official_rule_ok).sum()), "of", len(chk))
    feat = F.merge(S[["T", "R_rule", "R", "E_date", "tradeable", "excl", "vix", "vix_20ago", "vix_up"]], on="T")
    feat.rename(columns={"R": "R_official", "E_date": "entry_date"}).to_csv(f"{OUT}/cot_features.csv", index=False)
    if only_report:
        T = pd.read_csv(f"{OUT}/trades.csv")
        skipped = pd.read_csv(f"{OUT}/skipped.csv")
        infos = pd.read_csv(f"{OUT}/markets.csv").to_dict("records")
    else:
        sig, legs = plans(F, S)
        log("plans: P1-P4 signals", {v: sum(len(sig[(v, cc)]) for cc in ALL8) for v in VARIANTS[:4]},
            "P5-P8 legs", pd.Series([x[0] for x in legs]).value_counts().to_dict())
        Sx = S[["T", "rel_ts", "E_date"]].copy()
        jobs = [(cc, Sx, {key: val for key, val in sig.items() if key[1] == cc}, [x for x in legs if x[1] == cc])
                for cc in ALL8]
        rows, skipped, infos = [], [], []
        with Pool(2) as pool:
            for out, sk, info in pool.imap_unordered(worker, jobs):
                rows += out
                skipped += sk
                infos.append(info)
                log("market done", info, "legs", len(out), f"{time.time() - t_start:.0f}s")
        T = pd.DataFrame(rows)
        skipped = pd.DataFrame(skipped, columns=["variant", "ccy", "T", "why"])
        skipped.to_csv(f"{OUT}/skipped.csv", index=False)
        pd.DataFrame(infos).to_csv(f"{OUT}/markets.csv", index=False)
        T.to_csv(f"{OUT}/trades.csv", index=False)
    text, survivors = report(T, skipped, S, F, chk, infos)
    if survivors and not only_report:
        Tt = pd.read_csv(f"{OUT}/trades.csv", parse_dates=["entry_day", "entry_ts", "exit_ts"])
        text += "\n" + prop(Tt, survivors)
    open(f"{OUT}/REPORT.md", "w").write(text)
    pd.set_option("display.width", 250)
    S2 = pd.read_csv(f"{OUT}/summary.csv", index_col=0)
    print(S2[["trades", "avg R", "t", "month t", "design avg R", "design t", "check avg R", "holdout avg R",
              "last3y avg R", "survives"]].round(3).to_string())
    log("survivors", survivors, f"total {time.time() - t_start:.0f}s")
    log("DONE")


if __name__ == "__main__":
    main()
