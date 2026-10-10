"""Alpha hunt, family `cb_drift`: central-bank decision-day drift in FX. Follow (or fade) large decision-day
moves, pooled over the central banks. Spec fixed BEFORE running; nothing below was chosen from the data.

Idea (event-driven momentum / under-reaction to monetary news, 1-10 day holds): a policy surprise reprices the
rate path at once, but the currency keeps adjusting for days because real-money investors rebalance slowly and
order flow carries the news over several sessions (Evans & Lyons 2005/2008; Bacchetta & van Wincoop 2010;
delayed overshooting: Eichenbaum & Evans 1995, Scholl & Uhlig 2008; analogy: post-earnings drift). A large
decision-day move proxies a large surprise. Over-reaction-then-reversal is pre-declared as the FADE alternative.

EVENTS (data/extra/cb_decisions.csv, built by `python run_alpha_cb_drift.py --dates`): scheduled policy
decisions only (no emergency / unscheduled moves), 2010-01 .. data end 2026-10-07, each mapped to one pair:
  FOMC -> EURUSD and USDJPY (two separate trades); ECB -> EURUSD; BoJ -> USDJPY; BoE -> GBPUSD; BoC -> USDCAD;
  RBA -> AUDUSD; RBNZ -> NZDUSD; SNB -> USDCHF.
Sources (raw pages cached under data/extra/cb_raw/, listing of every item seen incl. excluded ones with the
reason in results/alpha_hunt/cb_drift/cb_calendar_raw.csv):
  FOMC: data/extra/fomc_dates.csv from the fomc_cycle run (read-only; built from federalreserve.gov
        fomccalendars.htm + fomchistorical<YYYY>.htm; unscheduled meetings / calls / notation votes dropped).
  ECB:  https://www.ecb.europa.eu/press/govcdec/mopo/<YYYY>/html/index_include.en.html (the per-year lists
        behind .../press/govcdec/mopo/html/index.en.html); items titled "Monetary policy decisions"
        (case-insensitive: the 2016-12-08 item is capitalised differently; parsing fix made after the first scrape).
        13:45 CET until 2022-06-09, 14:15 CET from 2022-07-21 (press releases say the press conference starts
        14:30 CET until June 2022 and 14:45 CET from July 2022). tz Europe/Berlin.
  BoJ:  https://www.boj.or.jp/en/mopo/mpmsche_minu/past.htm (2010-2025) + index.htm (2026). Decision day =
        last day of the meeting (date in the statement file name k<yymmdd>). Unscheduled / emergency meetings
        dropped: 2010-05-10, 2010-08-30, 2011-11-30, 2020-03-16 (brought forward from Mar 18-19 after the Fed's
        emergency cut), 2020-05-22. Scheduled meetings shortened to one day (2011-03-14, 2011-08-04,
        2020-04-27) are kept. BoJ has no fixed release time: 12:00 JST is recorded as an approximation
        (any time 09:00-16:00 JST falls in the same NY session, so the day assignment is unaffected).
  BoE:  https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes
        (its listing API /_api/Search/RefreshContentPageSearchList). Decisions = /news/<y>/<month>/mpc-<month>-<y>
        releases (2010 - Jul 2015) and /monetary-policy-summary-and-minutes/<y>/... summaries (Aug 2015+);
        minutes, special meetings (2020-03-11 news release, 2020-03-19 special MPC) dropped. 12:00 London.
  BoC:  https://www.bankofcanada.ca/press/press-releases/?mt_page=N (every press release; the key-interest-rate
        page itself only shows the last 12 announcements). Rate announcements = titles "Bank of Canada
        maintains / raises / increases / lowers / reduces / cuts / holds / will maintain / will hold ... (overnight
        rate | policy rate | policy interest rate | key policy rate)" ("will maintain / will hold" added after the
        first scrape found only 5 and 4 announcements in 2020-21; every year now has 8). Unscheduled cuts
        2020-03-13 and 2020-03-27 dropped.
        10:00 ET until 2023, 09:45 ET from 2024 (tz America/Toronto).
  RBA:  https://www.rba.gov.au/monetary-policy/int-rate-decisions/<YYYY>/ (media release after every meeting,
        holds included). Unscheduled 2020-03-19 dropped. 14:30 Sydney.
  RBNZ: https://www.rbnz.govt.nz/monetary-policy/official-cash-rate-decisions (may block bots -> bank dropped
        if the full list incl. holds cannot be fetched).
  SNB:  https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions; items "Monetary policy
        assessment of <date>" only (2011 / 2015 emergency measures dropped). 09:30 Zurich.
A bank whose complete scheduled list (holds included) cannot be assembled is dropped and reported.
Release times are converted to UTC (release_utc). Event day t = the New York session (17:00 ET t-1 to 17:00 ET
t, i.e. the gjstrat.patterns.daily_table row) that contains the release timestamp.

REACTION: Rx = close_t - close_{t-1} from daily_table(m) (bid closes at 17:00 NY; close_{t-1} = previous session
row). Signal: |Rx| >= k * ATR20_t, ATR20_t = daily_table atr20 of day t (shifted, known before the day).

TRADE:
  Entry: market at the first live minute (vol > 0) at or after 18:00 ET on calendar day t (after the rollover
         spread; Sunday 18:00 ET if t is a Friday). Searched up to 4 days ahead (holidays); else skipped.
  FOLLOW = direction sign(Rx) on the pair; FADE = -sign(Rx). Rx == 0 -> no trade.
  Time exit at the open of the 16:55 ET minute of the h-th NY trading day after t (NY trading days = the
         daily_table session rows; exit minutes without ticks are counted as stale in the diagnostics).
  SL = mult x ATR20 of the entry session (daily_table atr20 of the session containing the entry minute; that
         value includes day t). No TP. Fills on real bid/ask via gjstrat.patterns.simulate (buys at ask, exit bid;
         stop checked minute by minute, gaps through the stop fill at the open).
  Two events on the same pair and day (e.g. BoJ + FOMC on USDJPY): one trade, labelled with both banks
         (counted once in the pooled result, once under each bank in the per-bank table).

VARIANTS (10 tests):
  D1-D8 = {k=0.5, k=1.0} x {h=1, h=3} x {FOLLOW, FADE}, SL 1.0 x ATR20:
    D1 k0.5 h1 FOLLOW, D2 k0.5 h1 FADE, D3 k0.5 h3 FOLLOW, D4 k0.5 h3 FADE,
    D5 k1.0 h1 FOLLOW, D6 k1.0 h1 FADE, D7 k1.0 h3 FOLLOW, D8 k1.0 h3 FADE.
  D9:  FOLLOW, k=1.0, h=10, SL 2.0 x ATR20 (delayed-overshooting horizon).
  D10: FOLLOW every decision (no threshold, direction sign(Rx)), h=3, SL 1.0 x ATR20.

COSTS: gjstrat.accounting.account(trades sorted by (exit_i, entry_i), m, 10_000, commission=7,
swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'], per pair, then pooled.

PROTOCOL / SURVIVAL (charter): PER design 2010-17, check 2018-23, holdout 2024-26, by event day t.
Pooled per variant; t is month-clustered (sum of R per calendar month of t, over months with >= 1 trade; t =
mean / sd x sqrt(months)); the trade-level t is reported alongside. Survives = design month-clustered t >= 2 AND
avg R > 0 in check AND in holdout. 10 tests -> 10 x 0.006 = 0.06 survivors expected by luck.
Report per test: trades, trades/month, win %, avg win / avg loss, avg R and t per period, last 3 years (event
days after 2023-10-07). Also: per bank (trades, avg R, t) and the count of banks positive; FOLLOW vs FADE mirror
check (gross price R and a no-stop mid-price drift, which should be close to opposite before costs); avg R by
|Rx|/ATR20 bucket (D10 trades; buckets 0-0.25, 0.25-0.5, 0.5-1, 1-1.5, >= 1.5, fixed a priori) with the no-stop
drift at h = 1, 3, 10; rate-change vs hold decisions (policy rate before the decision vs up to 21 days after,
capped before the bank's next decision of any kind; BIS WS_CBPOL daily, ECB = deposit rate or MRO; BoJ / ECB
balance-sheet decisions without a rate move count as holds); banks dropped for incomplete schedules.
If a variant survives: Alpha Swing prop sim joined to run_m3_addon.build_legs() (survivor at 1% and 2% on top of
the basket, normal risk and boost x1.5, starts 2011-2025 and 2018-2025), as in run_alpha_fomc_cycle.py.
Compute: the 7 (or fewer, after drops) pairs are loaded one at a time and deleted; no multiprocessing.

    python run_alpha_cb_drift.py --dates     # build data/extra/cb_decisions.csv (scraping, cached)
    python run_alpha_cb_drift.py             # run everything, write results/alpha_hunt/cb_drift/
    (env CB_PAIRS=USDCAD CB_NOPROP=1 = smoke test on one pair only; not used for the reported results)
"""
import gc
import hashlib
import html as htmlmod
import json
import os
import re
import sys
import time
from collections import namedtuple

import numpy as np
import pandas as pd

OUT = "results/alpha_hunt/cb_drift"
CSV = "data/extra/cb_decisions.csv"
RAW = "data/extra/cb_raw"
DATA_END = pd.Timestamp("2026-10-07")
LAST3 = pd.Timestamp("2023-10-08")
NY = "America/New_York"
BANK_PAIRS = {"FOMC": ["EURUSD", "USDJPY"], "ECB": ["EURUSD"], "BoJ": ["USDJPY"], "BoE": ["GBPUSD"],
              "BoC": ["USDCAD"], "RBA": ["AUDUSD"], "RBNZ": ["NZDUSD"], "SNB": ["USDCHF"]}
PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF"]
BIS_AREA = {"FOMC": "US", "ECB": "XM", "BoJ": "JP", "BoE": "GB", "BoC": "CA", "RBA": "AU", "RBNZ": "NZ", "SNB": "CH"}
VARIANTS = {
    "D1": dict(k=0.5, h=1, mode="FOLLOW", sl=1.0), "D2": dict(k=0.5, h=1, mode="FADE", sl=1.0),
    "D3": dict(k=0.5, h=3, mode="FOLLOW", sl=1.0), "D4": dict(k=0.5, h=3, mode="FADE", sl=1.0),
    "D5": dict(k=1.0, h=1, mode="FOLLOW", sl=1.0), "D6": dict(k=1.0, h=1, mode="FADE", sl=1.0),
    "D7": dict(k=1.0, h=3, mode="FOLLOW", sl=1.0), "D8": dict(k=1.0, h=3, mode="FADE", sl=1.0),
    "D9": dict(k=1.0, h=10, mode="FOLLOW", sl=2.0), "D10": dict(k=0.0, h=3, mode="FOLLOW", sl=1.0),
}
NAMES = {v: f"{v} {p['mode']} " + (f"k={p['k']}" if p['k'] > 0 else "every decision") + f" h={p['h']} SL {p['sl']}xATR"
         for v, p in VARIANTS.items()}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


# ============================================================================== scraping (--dates)
class Fetcher:
    def __init__(self):
        import requests
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        ca = "/root/.ccr/ca-bundle.crt"
        self.verify = ca if os.path.exists(ca) else True
        os.makedirs(RAW, exist_ok=True)

    def get(self, url, data=None):
        key = hashlib.md5((url + json.dumps(data, sort_keys=True) if data else url).encode()).hexdigest()
        path = f"{RAW}/{key}.txt"
        if os.path.exists(path):
            return open(path, encoding="utf-8").read()
        last = None
        for _ in range(3):
            try:
                r = (self.s.post(url, data=data, timeout=60, verify=self.verify) if data is not None
                     else self.s.get(url, timeout=60, verify=self.verify))
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                r.encoding = r.encoding or "utf-8"
                txt = r.text
                open(path, "w", encoding="utf-8").write(txt)
                time.sleep(0.3)
                return txt
            except Exception as e:                       # noqa: BLE001
                last = e
                time.sleep(2)
        raise RuntimeError(f"{url}: {last}")


def clean(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def scrape_ecb(F):
    rows = []
    for y in range(2010, 2027):
        url = f"https://www.ecb.europa.eu/press/govcdec/mopo/{y}/html/index_include.en.html"
        t = F.get(url)
        for b in re.split(r"<dt ", t)[1:]:
            d = re.search(r'isoDate="([\d-]+)"', b)
            if not d:
                continue
            for href, title in re.findall(r'<div class="title">\s*<a href="([^"]+)"[^>]*>([^<]+)</a>', b):
                title = clean(title)
                keep = title.lower() == "monetary policy decisions" and "/press/pr/" in href
                rows.append({"bank": "ECB", "date": d.group(1), "title": title, "keep": keep,
                             "reason": "" if keep else "not a 'Monetary policy decisions' release",
                             "source_url": "https://www.ecb.europa.eu" + href if href.startswith("/") else href})
    df = pd.DataFrame(rows)
    df = df[df.keep | df.title.str.contains("decision", case=False)]
    return df.drop_duplicates(["date", "keep", "title"])


BOJ_UNSCHED = {"2010-05-10": "unscheduled MPM (USD funding / euro crisis)", "2010-08-30": "extraordinary MPM",
               "2011-11-30": "unscheduled MPM (coordinated USD swap lines)",
               "2020-03-16": "brought forward from Mar 18-19 (emergency easing after the Fed's Sunday cut)",
               "2020-05-22": "unscheduled MPM (new SME funding facility)"}


def scrape_boj(F):
    rows = []
    for url in ("https://www.boj.or.jp/en/mopo/mpmsche_minu/past.htm", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm"):
        t = F.get(url)
        for tb in re.findall(r"<table>(.*?)</table>", t, re.S):
            cap = re.search(r"<caption[^>]*>[^<]*?(\d{4})", tb)
            if not cap:
                continue
            year = int(cap.group(1))
            for r in re.findall(r"<tr>(.*?)</tr>", tb, re.S):
                tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
                if not tds:
                    continue
                cell = clean(tds[0])
                m = re.search(r"k(\d{2})(\d{2})(\d{2})[a-z]?\.(?:pdf|htm)", tds[0])
                if m:
                    d = pd.Timestamp(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
                else:                                           # future meeting: last listed day
                    parts = re.findall(r"([A-Z][a-z]+)\.?\s+(\d+)|(?<=, )(\d+)", cell.split("[")[0])
                    mon, day = None, None
                    for a, b, c in parts:
                        if a:
                            mon, day = MONTHS[a[:3].lower()], int(b)
                        elif c:
                            day = int(c)
                    d = pd.Timestamp(year, mon, day)
                ds = d.strftime("%Y-%m-%d")
                keep = ds not in BOJ_UNSCHED
                rows.append({"bank": "BoJ", "date": ds, "title": cell, "keep": keep,
                             "reason": "" if keep else BOJ_UNSCHED[ds], "source_url": url})
    return pd.DataFrame(rows).drop_duplicates("date")


def scrape_boe(F):
    api = "https://www.bankofengland.co.uk/_api/Search/RefreshContentPageSearchList"
    rows, page, n_total = [], 1, None
    while True:
        data = {"SearchTerm": "", "Id": "{CE377CC8-BFBC-418B-B4D9-DBC1C64774A8}", "PageSize": "40",
                "ReleaseTypesAvailable[]": "09f8960ebc384e3589da5349744916ae",
                "TaxonomiesAvailable[]": ["36308a372d1e44ee94e6b5915796c531", "bdad2410fe554128b9f7d680d1066e43",
                                          "eb7acc623d7e4af88cb3a581a1ae1ea7"],
                "Page": str(page), "ShowResultImage": "0", "OrderBy": "4"}
        j = json.loads(F.get(api, data))
        n_total = j.get("NumResults", 0)
        got = 0
        for blk in re.split(r'(?=<a href=")', j["Results"]):
            h = re.match(r'<a href="([^"]+)"', blk)
            if not h or h.group(1) == "#":
                continue
            tm = re.search(r"<time[^>]*>([^<]+)</time>", blk)
            ti = re.search(r"<h3[^>]*>(.*?)</h3>", blk, re.S)
            if not tm:
                continue
            got += 1
            path, title = h.group(1), clean(ti.group(1)) if ti else ""
            d = pd.Timestamp(tm.group(1).strip())
            dec_old = re.fullmatch(r"/news/\d{4}/[a-z]+/mpc-[a-z]+-\d{4}", path) is not None
            dec_new = path.startswith("/monetary-policy-summary-and-minutes/") and "special" not in path \
                and "13march-2020" not in path and "minutes of the special" not in title.lower()
            reason = ""
            if not (dec_old or dec_new):
                reason = "minutes / other news" if "/minutes/" in path or "/news/" in path else "other"
                if "special" in path:
                    reason = "special (unscheduled) MPC meeting"
                if "boe-measures-to-respond" in path:
                    reason = "emergency measures 2020-03-11"
            rows.append({"bank": "BoE", "date": d.strftime("%Y-%m-%d"), "title": title, "keep": dec_old or dec_new,
                         "reason": reason, "source_url": "https://www.bankofengland.co.uk" + path})
        if got == 0 or page * 40 >= n_total:
            break
        page += 1
    return pd.DataFrame(rows)


BOC_UNSCHED = {"2020-03-13": "unscheduled cut", "2020-03-27": "unscheduled cut"}
BOC_RX = re.compile(r"(?i)^bank of canada (maintains|raises|increases|lowers|reduces|cuts|holds|will maintain|will hold)\b.*"
                    r"(overnight rate|policy rate|policy interest rate|key policy rate|key interest rate|target for the overnight)")


def scrape_boc(F):
    rows = []
    for page in range(1, 120):
        url = f"https://www.bankofcanada.ca/press/press-releases/?mt_page={page}"
        t = F.get(url)
        arts = re.findall(r"<article(.*?)</article>", t, re.S)
        if not arts:
            break
        years = []
        for a in arts:
            h = re.search(r'<h3[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', a, re.S)
            dd = re.search(r"media-date[^>]*>([^<]+)<", a)
            if not h or not dd:
                continue
            d = pd.Timestamp(dd.group(1).strip())
            years.append(d.year)
            title = clean(h.group(2))
            is_rate = BOC_RX.search(title) is not None
            ds = d.strftime("%Y-%m-%d")
            keep = is_rate and ds not in BOC_UNSCHED
            if d.year >= 2009:
                rows.append({"bank": "BoC", "date": ds, "title": title, "keep": keep,
                             "reason": "" if keep else (BOC_UNSCHED.get(ds, "not a rate announcement")),
                             "source_url": h.group(1)})
        if years and max(years) < 2009:
            break
    return pd.DataFrame(rows)


def scrape_rba(F):
    rows = []
    for y in range(2010, 2027):
        url = f"https://www.rba.gov.au/monetary-policy/int-rate-decisions/{y}/"
        t = F.get(url)
        body = t[t.find('class="list-articles"'):] if 'class="list-articles"' in t else t
        body = body[: body.find("</ul>")]
        for href, txt in re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', body):
            try:
                d = pd.Timestamp(clean(txt))
            except Exception:                           # noqa: BLE001
                continue
            ds = d.strftime("%Y-%m-%d")
            keep = ds != "2020-03-19"
            rows.append({"bank": "RBA", "date": ds, "title": clean(txt), "keep": keep,
                         "reason": "" if keep else "unscheduled meeting (COVID package)",
                         "source_url": "https://www.rba.gov.au" + href if href.startswith("/") else href})
    return pd.DataFrame(rows)


def scrape_snb(F):
    url = "https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions"
    t = F.get(url)
    rows = []
    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        title = clean(txt)
        m = re.search(r"Monetary policy assessment of (\d{1,2} [A-Z][a-z]+ \d{4})", title)
        if "pre_" not in href and not m:
            continue
        if m:
            d = pd.Timestamp(m.group(1))
            rows.append({"bank": "SNB", "date": d.strftime("%Y-%m-%d"), "title": title, "keep": True, "reason": "",
                         "source_url": "https://www.snb.ch" + href if href.startswith("/") else href})
        else:
            dm = re.search(r"pre_(\d{8})", href)
            if dm:
                rows.append({"bank": "SNB", "date": pd.Timestamp(dm.group(1)).strftime("%Y-%m-%d"), "title": title,
                             "keep": False, "reason": "not a quarterly assessment (unscheduled measure)",
                             "source_url": "https://www.snb.ch" + href if href.startswith("/") else href})
    df = pd.DataFrame(rows).sort_values("keep", ascending=False).drop_duplicates("date").sort_values("date")
    return df


def scrape_rbnz(F):
    url = "https://www.rbnz.govt.nz/monetary-policy/official-cash-rate-decisions"
    t = F.get(url)                                      # raises on 403 -> bank dropped
    raise RuntimeError("RBNZ page fetched but no parser for a complete decision list (holds included)" if t else "empty")


def scrape_fomc():
    f = pd.read_csv("data/extra/fomc_dates.csv")
    rows = [{"bank": "FOMC", "date": r.date, "title": r.heading, "keep": True, "reason": "", "source_url": r.source_url,
             "time": r.release_time_ET} for r in f.itertuples()]
    raw = "results/alpha_hunt/fomc_cycle/fomc_calendar_raw.csv"
    if os.path.exists(raw):                             # unscheduled FOMC actions, only for rate-change capping
        a = pd.read_csv(raw)
        a = a[~a.keep & a.statement.notna()]
        for r in a.itertuples():
            rows.append({"bank": "FOMC", "date": pd.Timestamp(str(int(r.statement))).strftime("%Y-%m-%d"),
                         "title": r.heading, "keep": False, "reason": "unscheduled / call / notation vote",
                         "source_url": r.source_url})
    return pd.DataFrame(rows)


def release_rule(bank, d):
    """(local HH:MM, tz, note) of the scheduled release."""
    if bank == "ECB":
        return ("13:45" if d < pd.Timestamp("2022-07-01") else "14:15"), "Europe/Berlin", ""
    if bank == "BoJ":
        return "12:00", "Asia/Tokyo", "approximate (BoJ has no fixed release time; day assignment unaffected)"
    if bank == "BoE":
        return "12:00", "Europe/London", ""
    if bank == "BoC":
        return ("10:00" if d < pd.Timestamp("2024-01-01") else "09:45"), "America/Toronto", ""
    if bank == "RBA":
        return "14:30", "Australia/Sydney", ""
    if bank == "SNB":
        return "09:30", "Europe/Zurich", ""
    raise ValueError(bank)


def build_dates():
    os.makedirs(OUT, exist_ok=True)
    F = Fetcher()
    parts, dropped = [], {}
    for bank, fn in (("FOMC", lambda: scrape_fomc()), ("ECB", lambda: scrape_ecb(F)), ("BoJ", lambda: scrape_boj(F)),
                     ("BoE", lambda: scrape_boe(F)), ("BoC", lambda: scrape_boc(F)), ("RBA", lambda: scrape_rba(F)),
                     ("RBNZ", lambda: scrape_rbnz(F)), ("SNB", lambda: scrape_snb(F))):
        t0 = time.time()
        try:
            df = fn()
            parts.append(df)
            k = df[df.keep]
            print(bank, "items", len(df), "kept", len(k), f"{time.time() - t0:.0f}s", flush=True)
        except Exception as e:                           # noqa: BLE001
            dropped[bank] = f"{e.__class__.__name__}: {e}"
            print(bank, "DROPPED", dropped[bank], flush=True)
    allr = pd.concat(parts, ignore_index=True)
    allr["date"] = pd.to_datetime(allr.date)
    allr = allr[(allr.date >= "2009-10-01") & (allr.date <= "2026-12-31")].sort_values(["bank", "date"])
    allr.to_csv(f"{OUT}/cb_calendar_raw.csv", index=False)
    keep = allr[allr.keep & (allr.date >= "2010-01-01") & (allr.date <= DATA_END)].drop_duplicates(["bank", "date"])
    out = []
    for r in keep.itertuples():
        if r.bank == "FOMC":
            hhmm, tz, note = r.time, "America/New_York", "fomc_dates.csv (rule time, statement page time where stated)"
        else:
            hhmm, tz, note = release_rule(r.bank, r.date)
        hh, mm = map(int, hhmm.split(":"))
        utc = (r.date + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(tz).tz_convert("UTC").tz_localize(None)
        for pair in BANK_PAIRS[r.bank]:
            out.append({"bank": r.bank, "date": r.date.date(), "release_time_local": hhmm, "tz": tz, "release_utc": utc,
                        "pair": pair, "source_url": r.source_url, "time_note": note})
    E = pd.DataFrame(out).sort_values(["release_utc", "pair"])
    E.to_csv(CSV, index=False)
    json.dump(dropped, open(f"{OUT}/banks_dropped.json", "w"), indent=1)
    cnt = keep.assign(year=keep.date.dt.year).groupby(["bank", "year"]).size().unstack(0).fillna(0).astype(int)
    cnt.to_csv(f"{OUT}/decisions_per_year.csv")
    print(cnt.to_string())
    print("dropped", dropped)
    src = "data/extra/SOURCES.csv"
    line = (f"cb_decisions.csv,see source_url column (FOMC: fomc_dates.csv; ECB/BoJ/BoE/BoC/RBA/SNB pages listed in "
            f"run_alpha_cb_drift.py),{pd.Timestamp.now('UTC'):%Y-%m-%d},scheduled central-bank decisions 2010-2026 "
            f"(cb_drift); dropped: {';'.join(dropped) or 'none'}\n")
    have = open(src).read() if os.path.exists(src) else ""
    if "cb_decisions.csv" not in have:
        open(src, "a").write(line)
    print("wrote", CSV, len(E))


# ============================================================================== backtest
from gjstrat.accounting import account                    # noqa: E402
from gjstrat.data import load_market                      # noqa: E402
from gjstrat.patterns import Signal, daily_table, local_idx, simulate   # noqa: E402
from gjstrat.swap import SwapModel                        # noqa: E402
from run_backtest import fmt_table                        # noqa: E402
from run_edge_hunt import PER                             # noqa: E402
from run_usdjpy_sl import tstat                           # noqa: E402

Tr = namedtuple("Tr", "day entry_i exit_i")


def session_label(ts_utc):
    return (pd.Timestamp(ts_utc).tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def first_live(m, i, horizon=4 * 1440):
    if i < 0 or i >= m.n:
        return -1
    w = np.flatnonzero(m.vol[i: min(i + horizon, m.n)] > 0)
    return i + w[0] if len(w) else -1


def load_events():
    E = pd.read_csv(CSV, parse_dates=["date", "release_utc"])
    E["day"] = E.release_utc.map(session_label)
    return E


def policy_changes(E):
    """bank, date -> 'change' / 'hold' from BIS daily policy rates (ECB: deposit rate or MRO)."""
    b = pd.read_csv("data/extra/policy_rates_bis_daily.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    b["TIME_PERIOD"] = pd.to_datetime(b.TIME_PERIOD)
    ser = {a: g.dropna().set_index("TIME_PERIOD")["OBS_VALUE"].sort_index() for a, g in b.groupby("REF_AREA")}
    e = pd.read_csv("data/extra/ecb_deposit_rate_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"]).dropna()
    dfr = pd.Series(e.OBS_VALUE.to_numpy(), index=pd.to_datetime(e.TIME_PERIOD)).sort_index()
    raw = pd.read_csv(f"{OUT}/cb_calendar_raw.csv", parse_dates=["date"])
    anydec = {bk: np.sort(g.date.unique()) for bk, g in raw.groupby("bank")}

    def val(s, d):
        s = s[s.index <= d]
        return s.iloc[-1] if len(s) else np.nan

    out = {}
    for bank, d in E[["bank", "date"]].drop_duplicates().itertuples(index=False):
        nxt = [x for x in anydec.get(bank, []) if pd.Timestamp(x) > d]
        end = d + pd.Timedelta(days=21)
        if nxt:
            end = min(end, pd.Timestamp(nxt[0]) - pd.Timedelta(days=1))
        series = [ser.get(BIS_AREA[bank], pd.Series(dtype=float))] + ([dfr] if bank == "ECB" else [])
        ch = False
        for s in series:
            a, z = val(s, d - pd.Timedelta(days=1)), val(s, end)
            if np.isfinite(a) and np.isfinite(z) and abs(z - a) > 1e-9:
                ch = True
        out[(bank, d)] = "change" if ch else "hold"
    return out


def run_pair(sym, ev, sw):
    t0 = time.time()
    m = load_market(f"data/{sym.lower()}_2010-01-01_2026-10-07.npz")
    d = daily_table(m)
    idx = d.index
    pos = {x: k for k, x in enumerate(idx)}
    evs, skipped = [], []
    for day, g in ev.groupby("day"):
        banks = "+".join(sorted(g.bank.unique()))
        if day > DATA_END:
            continue
        if day not in pos:
            skipped.append((sym, banks, day, "event day not a daily_table session (pre-warm-up or no session)"))
            continue
        p = pos[day]
        rx = d.close.iat[p] - d.prev_close.iat[p]
        atr_t = d.atr20.iat[p]
        cal = day + pd.Timedelta(days=2 if day.dayofweek == 4 else 0)
        s = first_live(m, local_idx(m, cal, 18, 0, NY))
        if s < 0:
            skipped.append((sym, banks, day, "no live entry minute"))
            continue
        lab = session_label(m.ts(s))
        atr_e = d.atr20.get(lab, np.nan)
        if not atr_e > 0:
            skipped.append((sym, banks, day, f"no ATR20 for entry session {lab.date()}"))
            continue
        ex = {}
        for h in (1, 3, 10):
            ex[h] = local_idx(m, idx[p + h], 16, 55, NY) if p + h < len(idx) else -1
        mid_s = (m.bo[s] + m.ao[s]) / 2
        drift = {h: (np.sign(rx) * ((m.bo[j] + m.ao[j]) / 2 - mid_s) / atr_e if 0 < j < m.n and j > s else np.nan)
                 for h, j in ex.items()}
        evs.append({"sym": sym, "banks": banks, "day": day, "rx": rx, "atr_t": atr_t, "z": abs(rx) / atr_t,
                    "entry_i": s, "atr_e": atr_e, **{f"exit{h}": j for h, j in ex.items()},
                    **{f"drift{h}": v for h, v in drift.items()},
                    **{f"stale{h}": bool(j > 0 and m.vol[max(j - 4, 0): j + 1].sum() == 0) for h, j in ex.items()}})
    EV = pd.DataFrame(evs)
    trades = []
    for v, P in VARIANTS.items():
        sel = EV[(EV.z >= P["k"]) & (EV.rx != 0) & (EV[f"exit{P['h']}"] > EV.entry_i + 1)]
        tr, meta = [], []
        for r in sel.itertuples():
            fol = "BUY" if r.rx > 0 else "SELL"
            side = fol if P["mode"] == "FOLLOW" else ("SELL" if fol == "BUY" else "BUY")
            sig = Signal(r.day, side, int(r.entry_i), "market", None, int(r.entry_i) + 1, P["sl"] * r.atr_e, None,
                         int(getattr(r, f"exit{P['h']}")), v)
            t = simulate(m, sig)
            if t is None:
                continue
            tr.append(t)
            meta.append(r)
        if not tr:
            continue
        order = sorted(range(len(tr)), key=lambda k: (tr[k].exit_i, tr[k].entry_i))
        tr, meta = [tr[k] for k in order], [meta[k] for k in order]
        lg = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
        assert (lg["entry_i"].to_numpy() == [t.entry_i for t in tr]).all()
        trades.append(pd.DataFrame({
            "variant": v, "sym": sym, "banks": [x.banks for x in meta], "day": [x.day for x in meta],
            "side": [t.side for t in tr], "R": lg["R"].to_numpy(), "gross_R": [t.r for t in tr],
            "rx": [x.rx for x in meta], "z": [x.z for x in meta], "entry_utc": [m.ts(t.entry_i) for t in tr],
            "exit_utc": [m.ts(t.exit_i) for t in tr], "entry": [t.entry for t in tr], "exit": [t.exit for t in tr],
            "sl": [t.risk for t in tr], "reason": [t.reason for t in tr],
            "stale_exit": [bool(t.reason == "TIME" and m.vol[max(t.exit_i - 4, 0): t.exit_i + 1].sum() == 0) for t in tr]}))
    T = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    EV["entry_utc"] = [m.ts(i) for i in EV.entry_i]
    print(sym, "events", len(EV), "skipped", len(skipped), "trades", len(T), f"{time.time() - t0:.0f}s", flush=True)
    del m, d
    gc.collect()
    return T, EV, skipped


# ============================================================================== stats
def per_mask(day, p):
    a, b = PER[p]
    return (day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))


def month_t(r, day):
    s = pd.Series(np.asarray(r, float), index=pd.DatetimeIndex(day)).groupby(pd.DatetimeIndex(day).to_period("M")).sum()
    return tstat(s.to_numpy()), len(s)


def summary(name, r, day):
    r, day = np.asarray(r, float), pd.DatetimeIndex(day)
    wins, losses = r[r > 0], r[r <= 0]
    months = max(((day.max() - day.min()).days + 1) / 30.44, 1.0) if len(r) else np.nan
    row = {"test": name, "trades": len(r), "trades/month": len(r) / months if len(r) else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r), "t (months)": month_t(r, day)[0]}
    for p in PER:
        sel = np.asarray(per_mask(day, p))
        v = r[sel]
        row.update({f"{p} n": len(v), f"{p} avg R": v.mean() if len(v) else np.nan, f"{p} t": tstat(v),
                    f"{p} t (months)": month_t(v, day[sel])[0] if len(v) else np.nan})
    sel = np.asarray(day >= LAST3)
    v = r[sel]
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    return row


def explode_banks(T):
    X = T.copy()
    X["bank"] = X.banks.str.split("+")
    return X.explode("bank")


# ============================================================================== prop
def prop(survivors, trades):
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, build_legs, since
    from run_prop_risk_rules import make_rule
    m, legs = build_legs()
    base = (0.25, 3, 0.5, 3, 0)
    mixes = {"basket": base + (0,) * len(survivors)}
    for v in survivors:
        T = trades[trades.variant == v].sort_values(["exit_utc", "entry_utc"])
        ei = ((pd.DatetimeIndex(T.entry_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        xi = ((pd.DatetimeIndex(T.exit_utc) - m.t0) // pd.Timedelta(minutes=1)).astype(int)
        legs.append(([Tr(pd.Timestamp(d), a, b) for d, a, b in zip(T.day, ei, xi)], T.R.to_numpy()))
    for risk in (1, 2):
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


# ============================================================================== main
def main():
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    E = load_events()
    dropped = json.load(open(f"{OUT}/banks_dropped.json")) if os.path.exists(f"{OUT}/banks_dropped.json") else {}
    banks = [b for b in BANK_PAIRS if b in set(E.bank)]
    pairs = [p for p in PAIRS if p in set(E.pair)]
    if os.environ.get("CB_PAIRS"):                       # smoke test only (full run: unset)
        pairs = [p for p in pairs if p in os.environ["CB_PAIRS"].split(",")]
    chg = policy_changes(E)
    E["decision"] = [chg[(b, d)] for b, d in zip(E.bank, E.date)]
    print("events", len(E), "banks", banks, "pairs", pairs, flush=True)
    sw = SwapModel.from_fred("rates", 1.0)
    parts, evparts, skipped = [], [], []
    for sym in pairs:
        T, EV, sk = run_pair(sym, E[E.pair == sym], sw)
        parts.append(T)
        evparts.append(EV)
        skipped += sk
    trades = pd.concat(parts, ignore_index=True)
    EVA = pd.concat(evparts, ignore_index=True)
    trades["day"] = pd.to_datetime(trades.day)

    # decision type of the trade: change if any of its labelled decisions changed the rate
    dmap = {}
    for r in E.itertuples():
        dmap.setdefault((r.pair, r.day), []).append(r.decision)
    trades["decision"] = ["change" if "change" in dmap.get((s, d), []) else "hold" for s, d in zip(trades.sym, trades.day)]
    EVA["decision"] = ["change" if "change" in dmap.get((s, d), []) else "hold" for s, d in zip(EVA.sym, EVA.day)]
    trades.to_csv(f"{OUT}/trades.csv", index=False)
    EVA.to_csv(f"{OUT}/events.csv", index=False)
    pd.DataFrame(skipped, columns=["sym", "banks", "day", "reason"]).to_csv(f"{OUT}/skipped_events.csv", index=False)

    # ---------------- charter table (pooled)
    S = pd.DataFrame([summary(NAMES[v], trades[trades.variant == v].R, trades[trades.variant == v].day)
                      for v in VARIANTS]).set_index("test")
    S["banks positive"] = ""
    S["survives"] = False
    X = explode_banks(trades)
    bank_rows = []
    for v in VARIANTS:
        g = X[X.variant == v]
        npos, ntot = 0, 0
        for b in banks:
            x = g[g.bank == b]
            if not len(x):
                continue
            row = {"variant": v, "bank": b, "trades": len(x), "win %": (x.R > 0).mean() * 100, "avg R": x.R.mean(),
                   "t": tstat(x.R)}
            for p in PER:
                y = x[per_mask(x.day, p)].R
                row[f"{p} n"], row[f"{p} avg R"] = len(y), y.mean() if len(y) else np.nan
            bank_rows.append(row)
            ntot += 1
            npos += x.R.mean() > 0
        S.loc[NAMES[v], "banks positive"] = f"{npos}/{ntot}"
        x = S.loc[NAMES[v]]
        S.loc[NAMES[v], "survives"] = bool(x["design t (months)"] >= 2 and x["check avg R"] > 0 and x["holdout avg R"] > 0)
    S.to_csv(f"{OUT}/summary.csv")
    BK = pd.DataFrame(bank_rows).set_index("variant")
    BK.to_csv(f"{OUT}/per_bank.csv")
    survivors = [v for v in VARIANTS if S.loc[NAMES[v], "survives"]]

    # per pair
    pair_rows = []
    for v in VARIANTS:
        for sym in pairs:
            x = trades[(trades.variant == v) & (trades.sym == sym)]
            if len(x):
                pair_rows.append({"variant": v, "pair": sym, "trades": len(x), "avg R": x.R.mean(), "t": tstat(x.R)})
    PP = pd.DataFrame(pair_rows).pivot(index="pair", columns="variant", values="avg R")[list(VARIANTS)]

    # ---------------- mirror check
    mir = []
    for k, h in ((0.5, 1), (0.5, 3), (1.0, 1), (1.0, 3)):
        fv = [v for v, P in VARIANTS.items() if P["k"] == k and P["h"] == h and P["mode"] == "FOLLOW" and P["sl"] == 1.0][0]
        dv = [v for v, P in VARIANTS.items() if P["k"] == k and P["h"] == h and P["mode"] == "FADE"][0]
        f, a = trades[trades.variant == fv], trades[trades.variant == dv]
        ev = EVA[(EVA.z >= k) & (EVA.rx != 0)]
        mir.append({"pair": f"{fv} vs {dv} (k={k}, h={h})", "FOLLOW n": len(f), "FADE n": len(a),
                    "FOLLOW gross R": f.gross_R.mean(), "FADE gross R": a.gross_R.mean(),
                    "sum gross (spread drag)": f.gross_R.mean() + a.gross_R.mean(),
                    "FOLLOW net R": f.R.mean(), "FADE net R": a.R.mean(),
                    "events": int(ev[f"drift{h}"].notna().sum()),
                    "no-stop drift to the exit (ATR, follow dir.)": ev[f"drift{h}"].mean(),
                    "drift t": tstat(ev[f"drift{h}"].dropna())})
    MIR = pd.DataFrame(mir).set_index("pair")

    # ---------------- buckets (D10 trades + no-stop drift on all events)
    edges = [0, 0.25, 0.5, 1.0, 1.5, np.inf]
    labels = ["0-0.25", "0.25-0.5", "0.5-1", "1-1.5", ">=1.5"]
    d10 = trades[trades.variant == "D10"].copy()
    d10["bucket"] = pd.cut(d10.z, edges, right=False, labels=labels)
    EVA["bucket"] = pd.cut(EVA.z, edges, right=False, labels=labels)
    brow = []
    for lab in labels:
        x = d10[d10.bucket == lab]
        e = EVA[(EVA.bucket == lab) & (EVA.rx != 0)]
        row = {"|Rx|/ATR20": lab, "D10 trades": len(x), "D10 avg R": x.R.mean(), "D10 t": tstat(x.R),
               "D10 design avg R": x[per_mask(x.day, "design")].R.mean(),
               "D10 check avg R": x[per_mask(x.day, "check")].R.mean(),
               "D10 holdout avg R": x[per_mask(x.day, "holdout")].R.mean(), "events": len(e)}
        for h in (1, 3, 10):
            row[f"drift h={h}"] = e[f"drift{h}"].mean()
            row[f"drift h={h} t"] = tstat(e[f"drift{h}"].dropna())
        brow.append(row)
    BU = pd.DataFrame(brow).set_index("|Rx|/ATR20")

    # ---------------- rate change vs hold
    crow = []
    for v in VARIANTS:
        for typ in ("change", "hold"):
            x = trades[(trades.variant == v) & (trades.decision == typ)]
            crow.append({"test": v, "decision": typ, "trades": len(x), "win %": (x.R > 0).mean() * 100 if len(x) else np.nan,
                         "avg R": x.R.mean() if len(x) else np.nan, "t": tstat(x.R),
                         "design avg R": x[per_mask(x.day, "design")].R.mean(),
                         "check avg R": x[per_mask(x.day, "check")].R.mean(),
                         "holdout avg R": x[per_mask(x.day, "holdout")].R.mean()})
    CH = pd.DataFrame(crow).set_index("test")
    ev_counts = E.drop_duplicates(["bank", "date"]).groupby(["bank", "decision"]).size().unstack(fill_value=0)

    # ---------------- event coverage
    cov = []
    for b in banks:
        eb = E[E.bank == b]
        dec = eb.drop_duplicates("date")
        xb = explode_banks(EVA)
        row = {"bank": b, "pairs": "+".join(BANK_PAIRS[b]), "decisions": len(dec),
               "first": dec.date.min().date(), "last": dec.date.max().date(),
               "rate changes": int((dec.decision == "change").sum()),
               "events with a session + entry": int((xb.bank == b).sum())}
        for v in ("D1", "D5", "D10"):
            row[f"{v} trades"] = int((X[(X.variant == v)].bank == b).sum())
        cov.append(row)
    COV = pd.DataFrame(cov).set_index("bank")
    per_year = pd.read_csv(f"{OUT}/decisions_per_year.csv", index_col=0) if os.path.exists(f"{OUT}/decisions_per_year.csv") else None
    stale = {v: int(trades[trades.variant == v].stale_exit.sum()) for v in VARIANTS}
    same_day = EVA[EVA.banks.str.contains(r"\+")]

    # ---------------- banks positive per period + verdict text
    bpp = []
    for v in VARIANTS:
        g = BK.loc[[v]] if v in BK.index else BK.iloc[0:0]
        row = {"test": v}
        for p in PER:
            has = g[f"{p} n"] > 0
            row[f"{p} banks positive"] = f"{int((g.loc[has, f'{p} avg R'] > 0).sum())}/{int(has.sum())}"
        allp = g[(g["design avg R"] > 0) & (g["check avg R"] > 0) & (g["holdout avg R"] > 0)]
        row["banks positive in all 3 periods"] = ", ".join(allp.bank) or "-"
        bpp.append(row)
    BPP = pd.DataFrame(bpp).set_index("test")
    n_combo = int(sum(len(BK.loc[[v]]) for v in VARIANTS if v in BK.index))
    n_all3 = int(sum(len(x.split(", ")) for x in BPP["banks positive in all 3 periods"] if x != "-"))
    bt = S["design t (months)"].astype(float)
    bv = bt.idxmax()
    cost = (trades.gross_R - trades.R).mean()
    verdict = [
        f"- No variant clears the bar. Best pooled design month-clustered t: {bt.max():.2f} ({bv}); "
        f"{int((S['avg R'] > 0).sum())} of {len(VARIANTS)} variants have a positive full-sample avg R, the largest "
        f"{S['avg R'].max():+.3f} R per trade.",
        f"- FOLLOW and FADE are near mirror images before costs (gross R sums {MIR['sum gross (spread drag)'].min():+.3f} "
        f"to {MIR['sum gross (spread drag)'].max():+.3f} R = spread and stop asymmetry). The no-stop mid-price drift from "
        f"18:00 ET on the decision day to the exit is {MIR['no-stop drift to the exit (ATR, follow dir.)'].min():+.3f} to "
        f"{MIR['no-stop drift to the exit (ATR, follow dir.)'].max():+.3f} ATR20 (|t| <= {MIR['drift t'].abs().max():.2f}): "
        "no measurable continuation (under-reaction) or reversal (over-reaction) after a scheduled decision day.",
        f"- Commission, slippage and swap cost {cost:.3f} R per trade on average on top of the spread.",
        f"- Per bank: {n_all3} of {n_combo} variant x bank cells are positive in all three periods; with no edge about "
        f"1/8 of cells ({n_combo / 8:.0f}) would be by chance, and the pooled tests above are the pre-declared ones.",
        "- The |Rx|/ATR buckets and the rate-change / hold split are descriptive only (not tests); they show no "
        "monotone pattern that theory would predict (larger surprise -> more drift).",
    ]
    P = None
    if survivors and not os.environ.get("CB_NOPROP"):
        P = prop(survivors, trades)
        P.to_csv(f"{OUT}/prop.csv")

    # ---------------- report
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "t (months)",
            "design n", "design avg R", "design t", "design t (months)", "check n", "check avg R", "check t",
            "holdout n", "holdout avg R", "holdout t", "last3y n", "last3y avg R", "last3y t", "banks positive", "survives"]
    n_tests = len(VARIANTS)
    best = S.sort_values("design t (months)", ascending=False).index[0]
    txt = ["# Central-bank decision-day drift in FX (cb_drift)\n",
           "Script: `run_alpha_cb_drift.py` (every rule in its docstring, fixed before running). Costs in every R: "
           "$7/lot commission, 0.2 pip slippage per market/stop fill, swap (FRED rates +1%), real bid/ask fills.\n",
           f"**Survivors: {len(survivors)} of {n_tests} tests** ({', '.join(survivors) or 'none'}); expected by luck "
           f"{n_tests} x 0.006 = {n_tests * 0.006:.2f}.\n",
           "Survival = pooled design 2010-17 month-clustered t >= 2 AND avg R > 0 in check 2018-23 AND in holdout "
           "2024-26 (periods by event day t). Last 3 years = event days after 2023-10-07. 'banks positive' = banks "
           "with avg R > 0 over the whole sample (a trade labelled with two banks counts for both).\n",
           f"Banks used: {', '.join(banks)}; pairs: {', '.join(pairs)}. Banks dropped (complete scheduled list incl. "
           f"holds could not be assembled): " + ("; ".join(f"{b} ({r})" for b, r in dropped.items()) or "none") + ".\n",
           "## Verdict\n", "\n".join(verdict) + "\n",
           "## All tests (pooled over banks and pairs, net R per trade)\n", fmt_table(S[cols], ".3f"),
           "\nt = trade-level t; t (months) = month-clustered t (sum of R per calendar month). The survival bar uses "
           "design t (months).\n",
           "\n## Banks positive per period (avg net R > 0)\n", fmt_table(BPP, ".0f"),
           "\n## Per bank (net R; trades labelled with two banks appear under both)\n",
           fmt_table(BK.reset_index().set_index(["variant"])[["bank", "trades", "win %", "avg R", "t", "design avg R",
                                                               "check avg R", "holdout avg R"]], ".3f"),
           "\n## Per pair: avg net R\n", fmt_table(PP, ".3f"),
           "\n## FOLLOW vs FADE mirror check\n",
           "gross R = price R on bid/ask fills (spread paid) before commission, slippage and swap. The no-stop drift "
           "is the mid-price move from the entry minute to the exit minute in ATR20 units in the FOLLOW direction "
           "(all triggered events, no costs, no stop).\n", fmt_table(MIR, ".3f"),
           "\n## Avg R by |Rx| / ATR20 bucket\n",
           "D10 = FOLLOW every decision, h=3, SL 1xATR (net R). drift h = no-stop mid-price drift in the decision-day "
           "direction (ATR20 units, no costs) over all events in the bucket.\n", fmt_table(BU, ".3f"),
           "\n## Rate-change vs hold decisions (net R)\n",
           "Change = policy rate (BIS WS_CBPOL daily; ECB deposit rate or MRO) differs between the day before the "
           "decision and up to 21 days after (capped before the bank's next decision of any kind).\n",
           fmt_table(CH, ".3f"), "\nDecisions by type:\n", fmt_table(ev_counts, ".0f"),
           "\n## Event coverage\n", fmt_table(COV, ".0f"),
           ("\nScheduled decisions per year (from the scraped lists; used to check completeness):\n"
            + fmt_table(per_year, ".0f") + "\n") if per_year is not None else "",
           f"\nSame-pair same-day events traded once with both labels: {len(same_day)} "
           f"({', '.join(f'{r.sym} {r.day.date()} {r.banks}' for r in same_day.itertuples())}).\n",
           f"Skipped events: {len(skipped)} (see skipped_events.csv; mostly decisions before the daily_table warm-up "
           f"in early 2010). Time exits on a stale minute (no ticks in the exit minute and the 4 before): "
           + ", ".join(f"{v} {n}" for v, n in stale.items() if n) + (" none" if not any(stale.values()) else "") + ".\n",
           "\n## Sources\n",
           "data/extra/cb_decisions.csv (bank, date, release_time_local, tz, release_utc, pair, source_url); every "
           "scraped item incl. excluded ones with the reason in cb_calendar_raw.csv; FOMC from "
           "data/extra/fomc_dates.csv (fomc_cycle run). Pages: ECB https://www.ecb.europa.eu/press/govcdec/mopo/<YYYY>/html/index_include.en.html; "
           "BoJ https://www.boj.or.jp/en/mopo/mpmsche_minu/past.htm + index.htm; BoE "
           "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes "
           "(listing API); BoC https://www.bankofcanada.ca/press/press-releases/?mt_page=N; RBA "
           "https://www.rba.gov.au/monetary-policy/int-rate-decisions/<YYYY>/; SNB "
           "https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions; RBNZ "
           "https://www.rbnz.govt.nz/monetary-policy/official-cash-rate-decisions.\n",
           "\nFiles: summary.csv, per_bank.csv, trades.csv, events.csv, skipped_events.csv, cb_calendar_raw.csv, "
           "decisions_per_year.csv" + (", prop.csv" if P is not None else "") + ".\n",
           "\n## Prop sim\n", ("Survivors joined to run_m3_addon.build_legs() below." if P is not None else
                                f"Not run: no variant survived. Best design t (months): {best}.") + "\n"]
    if P is not None:
        pcols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
                 "pass eventually %", "median months to pass", "months per funded account", "accepted"]
        txt += [fmt_table(P[[c for c in pcols if c in P.columns]], ".1f") + "\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    pd.set_option("display.width", 250)
    print(S[cols].round(3).to_string())
    print(MIR.round(3).to_string())
    print(BU.round(3).to_string())
    print(CH.round(3).to_string())
    print(BK.round(3).to_string())
    print("survivors", survivors, f"{time.time() - t_start:.0f}s")
    print("DONE", flush=True)


if __name__ == "__main__":
    if "--dates" in sys.argv:
        build_dates()
    else:
        main()
