"""Alpha hunt, family `fomc_cycle`: FOMC announcement premia (pre-FOMC drift, FOMC-cycle even weeks,
short USD on FOMC days). Spec fixed BEFORE running; nothing below was chosen from the data.

Literature: Lucca & Moench 2015 JF (pre-FOMC drift, +49 bp S&P in the 24 h before the statement);
Cieslak, Morse & Vissing-Jorgensen 2019 JF (CMVJ: equity premium earned in even weeks of the FOMC cycle);
Mueller, Tahbaz-Salehi & Vedolin 2017 JF (USD weakens on FOMC days, more against high-rate currencies);
Kurov, Wolfe & Gilbert 2021 (pre-FOMC drift weaker after 2015 -> decay test).

EVENTS (data/extra/fomc_dates.csv, built by `python run_alpha_fomc_cycle.py --dates` from
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021+) and
https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm (2010-2020)):
  scheduled FOMC statement days 2010-01 .. 2026-10 (Oct/Dec-2026 meetings are kept in the file only so the
  last even-week windows can be truncated; they are after the data end). Only regularly scheduled meetings:
  headings with "unscheduled", "Conference Call", "notation vote" or "cancelled" are dropped (e.g. 2010-05-09,
  2010-10-15, 2011-08-01, 2011-11-28, 2013-10-16, 2014-03-04, 2019-10-04, 2020-03-03, 2020-03-15,
  2020-03-17/18 cancelled, 2020-03-19/23/31 notation votes). Day 0 = statement day (2nd day of a 2-day
  meeting = the date in the statement's URL). Release time T:
    2010-2012: 14:15 ET; press-conference meetings Apr-2011..Dec-2012: 12:30 ET; from Jan-2013: 14:00 ET.
  Each statement page is fetched; where it states "For release at h:mm p.m." that time is compared with the
  rule (and wins if different; listed in the report). Older pages only say "For immediate release".
  Days are NYSE trading days (holidays.NYSE, plus 2025-01-09 national day of mourning, which the holidays
  package misses): day -1 = trading day before day 0, etc.

TIMING: America/New_York, DST aware (gjstrat.patterns.local_idx). Minute markets (Nasdaq 100 CFD
USATECHIDXUSD, Nikkei CFD JPNIDXJPY, FX) enter at market on the first live minute (vol > 0) within 5 minutes of
the stated time (run_index_anomalies.live_at; no live minute -> event skipped) and exit at the open of the
stated minute (gjstrat.patterns.simulate: bid/ask, SL on real bid/ask, gap fills at the open).
ATR20 = daily_table atr20 (shifted, known before the day) of the NY-close session containing the entry minute.
S&P 500 (USA500IDXUSD) hourly bid candles (data/hourly, as in run_index_replication): fills at hourly bar
closes, 1.0 index point per round trip, stop checked on hourly lows after the entry bar (gap through the stop
fills at the bar open) with 0.25 pt extra slippage, 3%/yr financing per calendar night (NY dates);
ATR20 from live (vol > 0) hourly bars grouped into 17:00-17:00 NY sessions, shifted one session.
Entry and exit bars must have vol > 0 (a flat, untraded bar has no real price; fix of an impossibility).

VARIANTS (11; 9 candidates F1-F8, F11; F9/F10 controls):
  F1 pre-FOMC drift, Nasdaq: BUY 14:00 ET day -1, time exit T-5 min on day 0, SL 1.0 x ATR20.
  F2 pre-FOMC drift, S&P: buy at the close of the 13:00-14:00 bar on day -1; sell at the close of the last full
     hourly bar ending at or before T-5 min on day 0 (12:00-13:00 bar for T = 14:00, 11:00-12:00 for T = 12:30);
     SL 1.0 x ATR20.  SPEC FIX: the spec's gloss names the 12:00-13:00 bar also for T = 14:15, but the rule
     "last full bar ending at or before T-5 = 14:10" gives the 13:00-14:00 bar; the rule is used, and the
     gloss version is reported as a sensitivity line (only the 3 S&P-era 14:15 events of 2012 differ).
  F3 pre-FOMC drift, Nikkei CFD (US hours): same window as F1; events with no ticks at entry skipped.
  F4 short-USD basket on FOMC day: BUY EURUSD GBPUSD AUDUSD NZDUSD, SELL USDJPY USDCHF USDCAD; enter 18:00 ET on
     day -1 (after the rollover spread), time exit 16:55 ET on day 0, SL 1.0 x ATR20 per leg, equal 1R per leg.
     Event R = mean of the legs that traded (normally all 7; events with missing legs are counted in the report).
  F5 high-yield short-USD: as F4 but only the 2 non-USD currencies with the highest policy rate dated <= day -2
     (BIS WS_CBPOL daily; EUR = ECB deposit facility rate), each long vs USD. Ties broken alphabetically by
     currency code (AUD < CAD < CHF < EUR < GBP < JPY < NZD). Event R = mean of the 2 legs (both must trade).
     Legs are the identical F4 leg trades (same entry/exit/SL), so their net R is reused.
  F6 even weeks, Nasdaq (CMVJ): week k = trading days 5k-1 .. 5k+3 relative to day 0, even k in {0,2,4,6}.
     BUY at the 15:55 ET minute of day 5k-2, time exit at the 15:55 ET minute of day 5k+3; the exit is truncated
     at the next scheduled meeting's day -2 and windows shorter than 3 trading days are dropped. SL 2.0 x ATR20.
  F7 even weeks, S&P: same days, closes of the 15:00-16:00 hourly bar, SL 2.0 x ATR20.
  F8 even weeks, Nikkei CFD: same NY timestamps as F6 (global Fed-put channel), SL 2.0 x ATR20.
  F9 control: odd weeks k in {1,3,5}, Nasdaq (same rules). Not a candidate.
  F10 control: odd weeks, S&P. Not a candidate.
  F11 week 0 only (days -1..+3), Nasdaq, SL 2.0 x ATR20.
  Report-only extras (not tests): F8c odd weeks Nikkei (control for F8); F2g = F2 with the gloss exit bar.

COSTS: Nasdaq and Nikkei: run_all_matrix.net_r (0.25 / 2.0 pt slippage per fill, + per stop fill, 3%/yr
financing per rollover). S&P as above. FX: gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m,
10_000, commission=7, swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'].

PROTOCOL / SURVIVAL (charter): PER design 2010-17 (indices from their data start), check 2018-23, holdout
2024-26 (period by the event's day 0 for F1-F5, by the entry day for week windows).
Survives = design t >= 2 AND avg R > 0 in check AND in holdout.
Extra condition for even-week variants (F6, F7, F8, F11): design-period even-minus-odd difference in per-trade R
with Welch t >= 2 (F6 vs F9, F11 vs F9, F7 vs F10, F8 vs F8c); otherwise it is just the equity premium.
Report per test: trades, trades/month, win %, avg win / avg loss, avg R and t per period, last 3 years
(entries after 2023-10-07). Also: F1-F3 split pre-2016 vs 2016+ (decay); mean daily return on even vs odd vs
all days (Nasdaq, S&P, Nikkei) and F6 vs buy-and-hold over the same months; per-leg avg R and legs positive for
F4/F5. 9 candidate tests -> ~0.05 survivors expected by luck (0.6% each).
If any variant survives: Alpha Swing prop sim joined to run_m3_addon.build_legs() as in run_index_prop.py
(survivor at 1% and 2% on top of the basket, normal risk and boost x1.5, starts 2011-2025 and 2018-2025;
accepted if months per funded account is lower and pass eventually % not lower in both windows).
Compute: Nasdaq, S&P hourly, Nikkei, then the 7 FX pairs, each loaded alone and deleted; no multiprocessing.

    python run_alpha_fomc_cycle.py --dates     # build data/extra/fomc_dates.csv
    python run_alpha_fomc_cycle.py             # run everything, write results/alpha_hunt/fomc_cycle/
"""
import gc
import glob
import lzma
import os
import re
import sys
import time
from collections import namedtuple
from datetime import date

import holidays
import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import CANDLE_DTYPE, load_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/fomc_cycle"
DATES = "data/extra/fomc_dates.csv"
FED = "https://www.federalreserve.gov"
NQ, JP = "USATECHIDXUSD", "JPNIDXJPY"
IDX_FILES = {NQ: "data/usatechidxusd_2011-01-02_2026-10-07.npz", JP: "data/jpnidxjpy_2011-01-02_2026-10-07.npz"}
FX = {"EURUSD": ("EUR", "BUY"), "GBPUSD": ("GBP", "BUY"), "AUDUSD": ("AUD", "BUY"), "NZDUSD": ("NZD", "BUY"),
      "USDJPY": ("JPY", "SELL"), "USDCHF": ("CHF", "SELL"), "USDCAD": ("CAD", "SELL")}
BIS_AREA = {"GBP": "GB", "JPY": "JP", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}
DATA_END = pd.Timestamp("2026-10-07")
LAST3 = pd.Timestamp("2023-10-08")
EVEN, ODD = (0, 2, 4, 6), (1, 3, 5)
CANDIDATES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F11"]
NAMES = {"F1": "F1 pre-FOMC drift, Nasdaq", "F2": "F2 pre-FOMC drift, S&P", "F3": "F3 pre-FOMC drift, Nikkei",
         "F4": "F4 short-USD basket, FOMC day", "F5": "F5 high-yield short-USD, FOMC day",
         "F6": "F6 even weeks, Nasdaq", "F7": "F7 even weeks, S&P", "F8": "F8 even weeks, Nikkei",
         "F9": "F9 control: odd weeks, Nasdaq", "F10": "F10 control: odd weeks, S&P",
         "F11": "F11 week 0 only, Nasdaq", "F8c": "F8c extra: odd weeks, Nikkei", "F2g": "F2g extra: F2 gloss exit"}
Event = namedtuple("Event", "day0 p hh mm")
Tr = namedtuple("Tr", "day entry_i exit_i")


# ----------------------------------------------------------------------------------------- FOMC dates
def build_dates():
    import requests
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (research; gj-strat)"
    get = lambda u: sess.get(u, timeout=60).text
    rows = []
    bad = ("unscheduled", "conference call", "notation", "cancelled")
    for y in range(2010, 2021):
        url = f"{FED}/monetarypolicy/fomchistorical{y}.htm"
        t = get(url)
        heads = [(mt.start(), re.sub(r"\s+", " ", mt.group(1)).strip()) for mt in re.finditer(r"<h5[^>]*>(.*?)</h5>", t, re.S)]
        heads = [(k, h) for k, h in heads if re.search(rf"- {y}$", h)]
        for n, (k, h) in enumerate(heads):
            body = t[k: heads[n + 1][0] if n + 1 < len(heads) else len(t)]
            st = re.search(r'href="/newsevents/press(?:releases)?/monetary/?(\d{8})a\.htm"', body)
            keep = "meeting" in h.lower() and not any(b in h.lower() for b in bad)
            rows.append({"heading": h, "statement": st.group(1) if st else None, "keep": keep,
                         "press_conference": "Press Conference" in body, "source_url": url})
    url = f"{FED}/monetarypolicy/fomccalendars.htm"
    t = get(url)
    yblocks = [(mt.start(), int(mt.group(1))) for mt in re.finditer(r"<h4><a[^>]*>(\d{4}) FOMC Meetings</a></h4>", t)]
    for n, (k, y) in enumerate(yblocks):
        if y < 2021:
            continue
        blk = t[k: yblocks[n + 1][0] if n + 1 < len(yblocks) else len(t)]
        parts = re.split(r'<div class="[^"]*row fomc-meeting"', blk)[1:]
        for p in parts:
            mon = re.search(r"fomc-meeting__month[^>]*><strong>([^<]+)</strong>", p).group(1).strip()
            dd = re.search(r"fomc-meeting__date[^>]*>([^<]+)</div>", p).group(1).strip()
            h = f"{mon} {dd} - {y}"
            st = re.search(r'href="/newsevents/pressreleases/monetary(\d{8})a\.htm"', p)
            keep = not any(b in h.lower() for b in bad)
            if not st and keep:                        # future meeting: statement on the last listed day
                last_mon = mon.split("/")[-1]
                last_day = re.match(r"(\d+)", dd.split("-")[-1]).group(1)
                st_date = pd.Timestamp(f"{last_mon} {last_day} {y}").strftime("%Y%m%d")
            else:
                st_date = st.group(1) if st else None
            rows.append({"heading": h, "statement": st_date, "keep": keep,
                         "press_conference": "Press Conference" in p or not st, "source_url": url})
    allm = pd.DataFrame(rows)
    allm.to_csv(f"{OUT}/fomc_calendar_raw.csv", index=False)
    ev = allm[allm.keep & allm.statement.notna()].copy()
    ev["date"] = pd.to_datetime(ev.statement)
    ev = ev[(ev.date >= "2010-01-01") & (ev.date <= "2026-12-31")].sort_values("date").drop_duplicates("date")
    out = []
    for r in ev.itertuples():
        d0 = r.date
        if d0 >= pd.Timestamp("2013-01-01"):
            rule = "14:00"
        elif r.press_conference and d0 >= pd.Timestamp("2011-04-01"):
            rule = "12:30"
        else:
            rule = "14:15"
        st_url = f"{FED}/newsevents/pressreleases/monetary{d0:%Y%m%d}a.htm"
        page = ""
        if d0 <= DATA_END:
            try:
                txt = get(st_url)
                mt = re.search(r'class="releaseTime">\s*For release at\s+(\d{1,2}):(\d{2})\s*([ap])\.m\.', txt)
                if mt:
                    hh = int(mt.group(1)) % 12 + (12 if mt.group(3) == "p" else 0)
                    page = f"{hh:02d}:{mt.group(2)}"
                elif "For immediate release" in txt:
                    page = "immediate (no time on page)"
                time.sleep(0.2)
            except Exception as e:                       # noqa: BLE001
                page = f"fetch failed: {e.__class__.__name__}"
        used = page if re.fullmatch(r"\d\d:\d\d", page) else rule
        out.append({"date": d0.date(), "release_time_ET": used, "press_conference": bool(r.press_conference),
                    "source_url": r.source_url, "statement_url": st_url, "rule_time_ET": rule, "time_on_page": page,
                    "heading": r.heading})
        print(d0.date(), rule, page, flush=True)
    pd.DataFrame(out).to_csv(DATES, index=False)
    print("wrote", DATES, len(out))


# ----------------------------------------------------------------------------------------- calendar
def nyse_days():
    hol = set(holidays.NYSE(years=range(2009, 2028))) | {date(2025, 1, 9)}
    return pd.DatetimeIndex([x for x in pd.bdate_range("2009-06-01", "2027-03-31") if x.date() not in hol])


def load_events(days):
    ev = pd.read_csv(DATES, parse_dates=["date"])
    pos = {d: k for k, d in enumerate(days)}
    out = []
    for r in ev.itertuples():
        assert r.date in pos, f"statement day {r.date.date()} is not an NYSE trading day"
        hh, mm = map(int, r.release_time_ET.split(":"))
        out.append(Event(r.date, pos[r.date], hh, mm))
    return out


def week_windows(events, days, ks):
    """(k, day0, entry day, exit day, n trading days) per window; exit truncated at the next meeting's day -2."""
    out = []
    for j in range(len(events) - 1):
        e, cap = events[j], events[j + 1].p - 2
        if e.day0 > pd.Timestamp("2026-10-31"):
            continue
        for k in ks:
            a, b = e.p + 5 * k - 2, min(e.p + 5 * k + 3, cap)
            if b - a < 3:
                continue
            out.append((k, e.day0, days[a], days[b], b - a))
    return out


def cycle_week(events, days):
    """Series: trading day -> cycle week k (day -1 starts week 0; days up to the next meeting's day -2)."""
    k = pd.Series(np.nan, index=days)
    for j in range(len(events) - 1):
        p, cap = events[j].p, events[j + 1].p - 2
        for q in range(p - 1, cap + 1):
            k.iloc[q] = (q - p + 1) // 5
    return k


def session_label(ts_utc):
    return (pd.Timestamp(ts_utc).tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


# ----------------------------------------------------------------------------------------- minute markets
def msig(m, d, day, side, i, j, mult, tag):
    s = live_at(m, i)
    if s < 0 or j <= s + 1 or j >= m.n:
        return None
    sl = mult * d["atr20"].get(session_label(m.ts(s)), np.nan)
    if not sl > 0:
        return None
    return Signal(day, side, s, "market", None, s + 1, sl, None, j, tag)


def run_sigs(m, sym, sigs, variant, fx_swap=None):
    tr = sorted([t for t in (simulate(m, s) for s in sigs if s is not None) if t is not None],
                key=lambda t: (t.exit_i, t.entry_i))
    if not tr:
        return pd.DataFrame()
    if sym in FX:
        lg = account(tr, m, 10_000, commission=7, swap=fx_swap, sym=sym, slippage_pips=0.2)
        assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
        r = lg["R"].to_numpy()
    else:
        r = net_r(m, sym, tr, None)
    stale = [t.reason == "TIME" and m.vol[max(t.exit_i - 4, 0): t.exit_i + 1].sum() == 0 for t in tr]
    return pd.DataFrame({"variant": variant, "sym": sym, "day": [t.day for t in tr], "R": r,
                         "entry_utc": [m.ts(t.entry_i) for t in tr], "exit_utc": [m.ts(t.exit_i) for t in tr],
                         "entry": [t.entry for t in tr], "exit": [t.exit for t in tr], "sl": [t.risk for t in tr],
                         "reason": [t.reason for t in tr], "stale_exit": stale})


def minute_index(sym, events, days, wins):
    m = load_market(IDX_FILES[sym])
    d = daily_table(m)
    pre = []
    for e in events:
        if e.day0 > DATA_END:
            continue
        hh, mm = divmod(e.hh * 60 + e.mm - 5, 60)
        pre.append(msig(m, d, e.day0, "BUY", local_idx(m, days[e.p - 1], 14, 0, NY), local_idx(m, e.day0, hh, mm, NY), 1.0, "pre"))
    wk = {k: [] for k in range(7)}
    for k, d0, a, b, n in wins:
        wk[k].append(msig(m, d, a, "BUY", local_idx(m, a, 15, 55, NY), local_idx(m, b, 15, 55, NY), 2.0, f"k{k}"))
    out = []
    if sym == NQ:
        out += [run_sigs(m, sym, pre, "F1"), run_sigs(m, sym, sum((wk[k] for k in EVEN), []), "F6"),
                run_sigs(m, sym, sum((wk[k] for k in ODD), []), "F9"), run_sigs(m, sym, wk[0], "F11")]
    else:
        out += [run_sigs(m, sym, pre, "F3"), run_sigs(m, sym, sum((wk[k] for k in EVEN), []), "F8"),
                run_sigs(m, sym, sum((wk[k] for k in ODD), []), "F8c")]
    # daily closes at 15:55 ET for the even/odd day analysis
    cl = {}
    for x in days[(days >= pd.Timestamp("2011-09-19")) & (days <= DATA_END)]:
        s = live_at(m, local_idx(m, x, 15, 55, NY))
        if s >= 0:
            cl[x] = m.bo[s]
    T = pd.concat(out, ignore_index=True)
    kmap = {a: k for k, d0, a, b, n in wins}                    # entry days are unique across windows
    T["week_k"] = T["day"].map(kmap).where(T.variant.isin(["F6", "F9", "F11", "F8", "F8c"]))
    del m, d
    gc.collect()
    return T, pd.Series(cl)


# ----------------------------------------------------------------------------------------- S&P hourly
def spx_bars():
    parts = []
    for f in sorted(glob.glob("data/hourly/USA500IDXUSD/*.bi5")):
        y, mth = map(int, os.path.basename(f)[:-4].split("_"))
        raw = open(f, "rb").read()
        if not raw:
            continue
        rec = np.frombuffer(lzma.decompress(raw), dtype=CANDLE_DTYPE)
        t = pd.Timestamp(year=y, month=mth, day=1) + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
        parts.append(pd.DataFrame({"o": rec["o"] / 1000.0, "h": rec["h"] / 1000.0, "l": rec["l"] / 1000.0,
                                   "c": rec["c"] / 1000.0, "v": rec["v"].astype(float)}, index=t))
    B = pd.concat(parts).sort_index()
    B = B[~B.index.duplicated()]
    B["ny"] = B.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)       # local bar start
    B["label"] = (B["ny"] + pd.Timedelta(hours=7)).dt.normalize()
    live = B[B.v > 0]
    dd = live.groupby("label").agg(high=("h", "max"), low=("l", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.high - dd.low).rolling(20).mean().shift(1)
    return B.reset_index(names="utc"), atr


def spx_trade(B, pos, atr, day, ent_key, ex_key, mult, variant):
    a, b = pos.get(ent_key), pos.get(ex_key)
    if a is None or b is None or b <= a or not (B.v.iat[a] > 0 and B.v.iat[b] > 0):
        return None
    entry = B.c.iat[a]
    sl = mult * atr.get(B.label.iat[a], np.nan)
    if not sl > 0:
        return None
    stop = entry - sl
    hit = np.flatnonzero(B.l.to_numpy()[a + 1: b + 1] <= stop)
    if len(hit):
        k = a + 1 + hit[0]
        px, reason, slip = min(stop, B.o.iat[k]) , "SL", 0.25
    else:
        k, px, reason, slip = b, B.c.iat[b], "TIME", 0.0
    nights = (B.ny.iat[k].normalize() - B.ny.iat[a].normalize()).days
    cost = 1.0 + slip + 0.03 / 365 * nights * entry
    return {"variant": variant, "sym": "USA500IDXUSD", "day": day, "R": (px - entry - cost) / sl,
            "entry_utc": B.utc.iat[a] + pd.Timedelta(hours=1), "exit_utc": B.utc.iat[k] + pd.Timedelta(hours=1),
            "entry": entry, "exit": px, "sl": sl, "reason": reason, "stale_exit": False}


def spx_tests(events, days, wins):
    B, atr = spx_bars()
    pos = {t: k for k, t in enumerate(B.ny)}
    rows = []
    for e in events:
        if e.day0 > DATA_END:
            continue
        dm1 = days[e.p - 1]
        end_h = (e.hh * 60 + e.mm - 5) // 60                   # last full bar ends at end_h:00
        r = spx_trade(B, pos, atr, e.day0, dm1 + pd.Timedelta(hours=13), e.day0 + pd.Timedelta(hours=end_h - 1), 1.0, "F2")
        if r:
            rows.append(r)
        gl = 11 if (e.hh, e.mm) == (12, 30) else 12            # the spec's gloss: 12:00-13:00 bar also for 14:15
        r = spx_trade(B, pos, atr, e.day0, dm1 + pd.Timedelta(hours=13), e.day0 + pd.Timedelta(hours=gl), 1.0, "F2g")
        if r:
            rows.append({**r, "week_k": np.nan})
    for k, d0, a, b, n in wins:
        v = "F7" if k in EVEN else "F10"
        r = spx_trade(B, pos, atr, a, a + pd.Timedelta(hours=15), b + pd.Timedelta(hours=15), 2.0, v)
        if r:
            rows.append({**r, "week_k": k})
    T = pd.DataFrame(rows)
    c15 = B[(B.ny.dt.hour == 15) & (B.v > 0)]
    cl = pd.Series(c15.c.to_numpy(), index=c15.ny.dt.normalize().to_numpy())
    cl = cl[~cl.index.duplicated()]
    return T, cl


# ----------------------------------------------------------------------------------------- FX
def policy_rates():
    b = pd.read_csv("data/extra/policy_rates_bis_daily.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    b["TIME_PERIOD"] = pd.to_datetime(b.TIME_PERIOD)
    out = {}
    for ccy, area in BIS_AREA.items():
        s = b[b.REF_AREA == area].dropna().set_index("TIME_PERIOD")["OBS_VALUE"].sort_index()
        out[ccy] = s
    e = pd.read_csv("data/extra/ecb_deposit_rate_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"]).dropna()
    out["EUR"] = pd.Series(e.OBS_VALUE.to_numpy(), index=pd.to_datetime(e.TIME_PERIOD)).sort_index()
    return out


def fx_legs(events, days):
    sw = SwapModel.from_fred("rates", 1.0)
    legs = []
    for sym, (ccy, side) in FX.items():
        t0 = time.time()
        m = load_market(f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
        d = daily_table(m)
        sigs = [msig(m, d, e.day0, side, local_idx(m, days[e.p - 1], 18, 0, NY), local_idx(m, e.day0, 16, 55, NY), 1.0, "fx")
                for e in events if e.day0 <= DATA_END]
        T = run_sigs(m, sym, sigs, "F4", sw)
        T["ccy"] = ccy
        legs.append(T)
        print(sym, len(T), round(T.R.mean(), 3), f"{time.time() - t0:.0f}s", flush=True)
        del m, d
        gc.collect()
    return pd.concat(legs, ignore_index=True)


# ----------------------------------------------------------------------------------------- stats
def per_mask(day, p):
    a, b = PER[p]
    return (day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))


def summary(name, r, day):
    r, day = np.asarray(r, float), pd.DatetimeIndex(day)
    wins, losses = r[r > 0], r[r <= 0]
    months = max(((day.max() - day.min()).days + 1) / 30.44, 1.0) if len(r) else np.nan
    row = {"test": name, "trades": len(r), "trades/month": len(r) / months if len(r) else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}
    for p in PER:
        v = r[np.asarray(per_mask(day, p))]
        row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v)})
    v = r[np.asarray(day >= LAST3)]
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    return row


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    diff = a.mean() - b.mean()
    return diff, diff / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def daily_split(cl, kser, label):
    cl = cl.sort_index()
    days_ok = kser.index
    cl = cl[cl.index.isin(days_ok)]
    pos = pd.Series(np.arange(len(days_ok)), index=days_ok)
    p = pos.reindex(cl.index).to_numpy()
    ret = pd.Series(cl.to_numpy()[1:] / cl.to_numpy()[:-1] - 1, index=cl.index[1:])
    ret = ret[np.diff(p) == 1] * 1e4                       # consecutive trading days only, in bp
    k = kser.reindex(ret.index)
    rows = []
    for per in ["all"] + list(PER):
        sel = np.ones(len(ret), bool) if per == "all" else np.asarray(per_mask(ret.index, per))
        x, kk = ret[sel], k[sel]
        ev, od = x[kk.isin(EVEN)], x[kk.isin(ODD)]
        diff, t = welch(ev, od)
        rows.append({"market": label, "period": per, "even days": len(ev), "even mean bp": ev.mean(),
                     "odd days": len(od), "odd mean bp": od.mean(), "all days": len(x), "all mean bp": x.mean(),
                     "even-odd bp": diff, "Welch t": t})
    return pd.DataFrame(rows), ret


def buy_hold(f6, ret_bp):
    """F6 gross / net vs buy-and-hold over the same months (Nasdaq)."""
    rows = []
    lo = f6.day.min().to_period("M").to_timestamp()
    hi = f6.day.max().to_period("M").to_timestamp("M")
    ret = ret_bp[(ret_bp.index >= lo) & (ret_bp.index <= hi)] / 1e4
    for per in ["all"] + list(PER):
        if per == "all":
            fx, rx = f6, ret
        else:
            fx, rx = f6[per_mask(pd.DatetimeIndex(f6.day), per)], ret[per_mask(ret.index, per)]
        if not len(rx):
            continue
        yrs = len(rx) / 252
        gross = np.log(fx.exit / fx.entry).sum()
        net = (fx.R * fx.sl / fx.entry).sum()
        rows.append({"period": per, "years": yrs, "F6 windows": len(fx), "F6 window days": int(fx.n_days.sum()),
                     "share of days in windows %": fx.n_days.sum() / len(rx) * 100,
                     "F6 gross %/yr (log)": gross / yrs * 100, "F6 net %/yr": net / yrs * 100,
                     "buy-and-hold %/yr (log)": np.log1p(rx).sum() / yrs * 100})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------- prop
def prop(survivors, trades):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    m, legs = build_legs()
    base = (0.25, 3, 0.5, 3, 0)
    nlegs = {"F4": 7, "F5": 2}
    mixes = {"basket": base + (0,) * len(survivors)}
    for v in survivors:
        T = trades[trades.variant == v].sort_values(["exit_utc", "entry_utc"])
        ei = ((pd.DatetimeIndex(T.entry_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        xi = ((pd.DatetimeIndex(T.exit_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        legs.append(([Tr(pd.Timestamp(d), a, b) for d, a, b in zip(T.day, ei, xi)], T.R.to_numpy()))
    for risk in (1, 2):
        for j, v in enumerate(survivors):
            mixes[f"basket + {v} {risk}%"] = base + tuple(risk / nlegs.get(v, 1) if i == j else 0 for i in range(len(survivors)))
    tabs = []
    for rule, scale in (("normal risk", None), ("boost x1.5", make_rule(boost=1.5))):
        for w, lg in (("starts 2011-2025", legs), ("starts 2018-2025", since(legs, "2018-01-01"))):
            t = prop_table(m, lg, mixes, **ALPHA, **({"scale": scale} if scale else {}))
            t["months per funded account"] = t["avg days per attempt"] / 30.4 / (t["pass eventually %"] / 100)
            t.insert(0, "window", w)
            t.insert(0, "risk rule", rule)
            tabs.append(t)
    P = pd.concat(tabs)
    acc = []
    for rule, mix in zip(P["risk rule"], P.index):
        if mix == "basket":
            acc.append(None)
            continue
        ok = True
        for w in P.window.unique():
            q = P[(P["risk rule"] == rule) & (P.window == w)]
            ok &= bool(q.loc[mix, "months per funded account"] < q.loc["basket", "months per funded account"]
                       and q.loc[mix, "pass eventually %"] >= q.loc["basket", "pass eventually %"])
        acc.append(ok)
    P["accepted"] = acc
    P.index.name = "mix"
    return P


# ----------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    days = nyse_days()
    events = load_events(days)
    ev_trade = [e for e in events if e.day0 <= DATA_END]
    wins = week_windows(events, days, EVEN + ODD)
    kser = cycle_week(events, days)
    print("events", len(events), "tradeable", len(ev_trade), "windows", len(wins), flush=True)
    W = pd.DataFrame(wins, columns=["k", "day0", "entry_day", "exit_day", "n_days"])
    W.to_csv(f"{OUT}/week_windows.csv", index=False)
    nwin = dict(zip(W.entry_day, W.n_days))

    parts, closes = [], {}
    for sym in (NQ,):
        T, cl = minute_index(sym, events, days, wins)
        parts.append(T); closes["Nasdaq 100"] = cl
        print(sym, "done", f"{time.time() - t_start:.0f}s", flush=True)
    T, cl = spx_tests(events, days, wins)
    parts.append(T); closes["S&P 500"] = cl
    print("S&P done", f"{time.time() - t_start:.0f}s", flush=True)
    T, cl = minute_index(JP, events, days, wins)
    parts.append(T); closes["Nikkei 225"] = cl
    print(JP, "done", f"{time.time() - t_start:.0f}s", flush=True)
    legs = fx_legs(ev_trade, days)
    print("FX done", f"{time.time() - t_start:.0f}s", flush=True)
    legs.to_csv(f"{OUT}/fx_legs.csv", index=False)

    # F4 / F5 event R
    rates = policy_rates()
    f4, f5, picks = [], [], []
    for e in ev_trade:
        g = legs[legs.day == e.day0]
        if not len(g):
            continue
        f4.append({"variant": "F4", "sym": "7 USD majors", "day": e.day0, "R": g.R.mean(), "n_legs": len(g),
                   "entry_utc": g.entry_utc.min(), "exit_utc": g.exit_utc.max()})
        ref = days[e.p - 2]
        rr = {c: s[s.index <= ref].iloc[-1] for c, s in rates.items() if (s.index <= ref).any()}
        top = sorted(rr, key=lambda c: (-rr[c], c))[:2]
        picks.append({"day0": e.day0.date(), "rates_dated_le": ref.date(), **{f"rate {c}": rr.get(c) for c in sorted(rr)},
                      "top2": "+".join(top)})
        h = g[g.ccy.isin(top)]
        if len(h) == 2:
            f5.append({"variant": "F5", "sym": "+".join(top), "day": e.day0, "R": h.R.mean(), "n_legs": 2,
                       "entry_utc": h.entry_utc.min(), "exit_utc": h.exit_utc.max()})
    F45 = pd.DataFrame(f4 + f5)
    pd.DataFrame(picks).to_csv(f"{OUT}/f5_rate_picks.csv", index=False)
    trades = pd.concat(parts + [F45], ignore_index=True)
    trades["day"] = pd.to_datetime(trades.day)
    trades["n_days"] = trades.day.map(nwin).where(trades.variant.isin(["F6", "F7", "F8", "F9", "F10", "F11", "F8c"]))
    trades.to_csv(f"{OUT}/trades.csv", index=False)

    # charter table
    order = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F11", "F9", "F10", "F8c", "F2g"]
    S = pd.DataFrame([summary(NAMES[v], trades[trades.variant == v].R, trades[trades.variant == v].day) for v in order]).set_index("test")
    S.insert(0, "role", ["candidate" if v in CANDIDATES else ("control" if v in ("F9", "F10") else "report-only")
                         for v in order])
    pair = {"F6": "F9", "F11": "F9", "F7": "F10", "F8": "F8c"}
    S["even-odd design diff R"], S["even-odd Welch t"] = np.nan, np.nan
    for v, c in pair.items():
        a = trades[(trades.variant == v) & per_mask(trades.day, "design")].R
        b = trades[(trades.variant == c) & per_mask(trades.day, "design")].R
        S.loc[NAMES[v], ["even-odd design diff R", "even-odd Welch t"]] = welch(a, b)
    S["survives"] = False
    for v in CANDIDATES:
        x = S.loc[NAMES[v]]
        ok = x["design t"] >= 2 and x["check avg R"] > 0 and x["holdout avg R"] > 0
        if v in pair:
            ok = ok and x["even-odd Welch t"] >= 2
        S.loc[NAMES[v], "survives"] = bool(ok)
    S.to_csv(f"{OUT}/summary.csv")
    survivors = [v for v in CANDIDATES if S.loc[NAMES[v], "survives"]]

    # decay split F1-F3
    dec = []
    for v in ("F1", "F2", "F3"):
        g = trades[trades.variant == v]
        for lab, sel in (("pre-2016", g.day < "2016-01-01"), ("2016+", g.day >= "2016-01-01")):
            x = g[sel].R.to_numpy()
            dec.append({"test": NAMES[v], "split": lab, "trades": len(x), "win %": (x > 0).mean() * 100 if len(x) else np.nan,
                        "avg R": x.mean() if len(x) else np.nan, "t": tstat(x)})
    DEC = pd.DataFrame(dec).set_index("test")

    # gross pre-FOMC return in bp (no costs) for context
    gross = []
    for v in ("F1", "F2", "F3"):
        g = trades[(trades.variant == v)]
        bp = (g.exit / g.entry - 1) * 1e4
        for lab, sel in (("all", np.ones(len(g), bool)), ("pre-2016", (g.day < "2016-01-01").to_numpy()),
                         ("2016+", (g.day >= "2016-01-01").to_numpy())):
            x = bp[sel].to_numpy()
            gross.append({"test": NAMES[v], "split": lab, "n": len(x), "mean fill-to-fill bp (before slippage/financing)": x.mean(),
                          "t": tstat(x)})
    GR = pd.DataFrame(gross).set_index("test")

    # even / odd daily returns, F6 vs buy-and-hold
    DS, rets = [], {}
    for lab, cl in closes.items():
        t, ret = daily_split(cl, kser, lab)
        DS.append(t); rets[lab] = ret
    DS = pd.concat(DS).set_index("market")
    BH = buy_hold(trades[trades.variant == "F6"], rets["Nasdaq 100"]).set_index("period")

    # FX legs
    leg_rows = []
    for (sym, ccy), g in legs.groupby(["sym", "ccy"]):
        row = {"leg": f"{'long ' + ccy + ' vs USD'} ({sym})", "trades": len(g), "win %": (g.R > 0).mean() * 100, "avg R": g.R.mean(), "t": tstat(g.R)}
        for p in PER:
            v = g[per_mask(g.day, p)].R
            row[f"{p} avg R"] = v.mean()
        leg_rows.append(row)
    LEG = pd.DataFrame(leg_rows).set_index("leg")
    legpos = {p: int((LEG[f"{p} avg R"] > 0).sum()) for p in PER}
    legpos["all"] = int((LEG["avg R"] > 0).sum())
    PK = pd.DataFrame(picks)
    pick_freq = PK.top2.map(lambda x: "+".join(sorted(x.split("+")))).value_counts()
    f5legs = []
    for e_row in picks:
        for c in e_row["top2"].split("+"):
            g = legs[(legs.day == pd.Timestamp(e_row["day0"])) & (legs.ccy == c)]
            if len(g):
                f5legs.append({"ccy": c, "day": g.day.iloc[0], "R": g.R.iloc[0]})
    F5L = pd.DataFrame(f5legs)
    f5leg_tab = F5L.groupby("ccy").R.agg(["size", "mean"]).rename(columns={"size": "legs", "mean": "avg R"})
    f5leg_tab["legs"] = f5leg_tab["legs"].astype(int)

    # diagnostics
    diag = {v: int(trades[(trades.variant == v)].stale_exit.fillna(False).astype(bool).sum()) for v in order}
    miss = int((F45[F45.variant == "F4"].n_legs < 7).sum()) if len(F45) else 0
    ev_csv = pd.read_csv(DATES)
    mism = ev_csv[ev_csv.time_on_page.astype(str).str.fullmatch(r"\d\d:\d\d") & (ev_csv.time_on_page != ev_csv.rule_time_ET)]
    n_page = int(ev_csv.time_on_page.astype(str).str.fullmatch(r"\d\d:\d\d").sum())

    P = None
    if survivors:
        P = prop(survivors, trades)
        P.to_csv(f"{OUT}/prop.csv")

    # ------------------------------------------------------------------ report
    cols = ["role", "trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "design n", "design avg R",
            "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y n",
            "last3y avg R", "last3y t", "even-odd Welch t", "survives"]
    tests_run = len(CANDIDATES)
    txt = [f"# FOMC announcement premia (fomc_cycle)\n",
           "Script: `run_alpha_fomc_cycle.py` (all rules in its docstring, fixed before running). Costs included "
           "everywhere (Nasdaq/Nikkei: run_all_matrix.net_r; S&P: 1 pt round trip + 0.25 pt stop slippage + 3%/yr "
           "financing; FX: $7/lot, 0.2 pip stop slippage, swap +1%).\n",
           f"**Survivors: {len(survivors)} of {tests_run} candidate tests** "
           f"({', '.join(NAMES[v] for v in survivors) or 'none'}); expected by luck: {tests_run} x 0.006 = {tests_run * 0.006:.3f}.\n",
           "Survival = design (2010-17; indices from their data start) t >= 2 AND avg R > 0 in check 2018-23 AND holdout "
           "2024-26; even-week variants also need a design-period even-minus-odd Welch t >= 2. Last 3 years = entries after 2023-10-07.\n",
           f"Events: {len(ev_trade)} scheduled statements 2010-01..{ev_trade[-1].day0.date()} (data end {DATA_END.date()}); "
           f"{len(W)} cycle-week windows ({(W.k.isin(EVEN)).sum()} even, {(W.k.isin(ODD)).sum()} odd).\n",
           "## All tests (net R per trade; F4/F5 = per event, mean of the legs)\n", fmt_table(S[cols], ".3f"),
           "\n## Pre-FOMC drift: decay split (pre-2016 vs 2016+)\n", fmt_table(DEC, ".3f"),
           "\nMove in bp from entry fill to exit fill (Nasdaq/Nikkei: ask in, bid out; S&P: bid closes), before slippage and financing:\n", fmt_table(GR, ".2f"),
           "\n## Even vs odd cycle weeks: mean daily close-to-close return (bp)\n",
           "Closes: Nasdaq and Nikkei CFD at 15:55 ET, S&P at the 16:00 hourly close. Day t's return is assigned to t's "
           "cycle week (week 0 = day -1..+3, days after the next meeting's day -2 belong to the next cycle).\n",
           fmt_table(DS, ".2f"),
           "\n## F6 (even weeks, Nasdaq) vs buy-and-hold over the same months\n", fmt_table(BH, ".2f"),
           "\n## F4 / F5 legs (long each currency vs USD, 18:00 ET day -1 to 16:55 ET day 0)\n", fmt_table(LEG, ".3f"),
           f"\nLegs with avg R > 0: all {legpos['all']}/7, design {legpos['design']}/7, check {legpos['check']}/7, "
           f"holdout {legpos['holdout']}/7. F4 events with fewer than 7 legs: {miss}.\n",
           "\nF5 top-2 picks (policy rate dated <= day -2), number of events:\n",
           fmt_table(pick_freq.rename("events").to_frame(), ".0f"),
           "\nF5 legs by currency:\n", fmt_table(f5leg_tab, ".3f"),
           "\n## Diagnostics\n",
           f"- Release times: {n_page} statement pages state a time ('For release at ...'); "
           f"{len(mism)} differ from the rule{(': ' + ', '.join(f'{r.date} page {r.time_on_page} rule {r.rule_time_ET}' for r in mism.itertuples())) if len(mism) else ''}. "
           "Older pages say only 'For immediate release'; the rule time is used there.\n",
           "- Time exits whose exit minute and the 4 before it had no ticks (stale price): "
           + ", ".join(f"{v} {n}" for v, n in diag.items() if n) + (" (none)" if not any(diag.values()) else "") + ".\n",
           "- F2g (report-only) uses the spec's gloss exit bar (12:00-13:00 also for T = 14:15); it differs from F2 "
           "only on the 2012 14:15 events.\n",
           "\n## Sources\n",
           "- FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021+), "
           "https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm (2010-2020); statement pages "
           "https://www.federalreserve.gov/newsevents/pressreleases/monetary<YYYYMMDD>a.htm (fetched 2026-10-10) -> "
           "data/extra/fomc_dates.csv.\n",
           "- Policy rates: data/extra/policy_rates_bis_daily.csv, data/extra/ecb_deposit_rate_daily.csv (URLs in "
           "data/extra/SOURCES.csv).\n",
           "\nFiles: summary.csv, trades.csv, fx_legs.csv, f5_rate_picks.csv, week_windows.csv"
           + (", prop.csv" if P is not None else "") + ".\n",
           "\n## Prop sim\n", ("Run below (survivors joined to run_m3_addon.build_legs())." if P is not None
                                else "Not run: no variant survived, so nothing is added to the Alpha Swing basket.") + "\n"]
    if P is not None:
        pcols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
                 "pass eventually %", "median months to pass", "months per funded account", "accepted"]
        txt += ["\n## Prop sim (Alpha Swing, survivors added to the current basket)\n",
                fmt_table(P[[c for c in pcols if c in P.columns]], ".1f") + "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250)
    print(S[cols].round(3).to_string())
    print(DEC.round(3).to_string())
    print(DS.round(2).to_string())
    print(BH.round(2).to_string())
    print(LEG.round(3).to_string())
    print("survivors", survivors, f"{time.time() - t_start:.0f}s")
    print("DONE", flush=True)


if __name__ == "__main__":
    if "--dates" in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        build_dates()
    else:
        main()
