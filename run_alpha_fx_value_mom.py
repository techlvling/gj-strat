"""Alpha hunt, family `fx_value_mom`: G8 cross-sectional FX value (5-year real exchange-rate reversal), FX momentum
and the carry-momentum-value combination. Spec fixed BEFORE running; nothing below was chosen from the data.

Literature: Rogoff 1996 and Taylor & Taylor 2004 (real exchange rates revert to PPP, 3-5 year half-lives);
Asness, Moskowitz & Pedersen 2013 JF (value = 5-year real FX reversal; momentum 12-1; value and momentum are
negatively correlated); Menkhoff, Sarno, Schmeling & Schrimpf 2012 JFE (currency momentum strongest at 1-month
formation) and 2017 RFS (currency value); Kroencke, Schindler & Schrimpf 2014 and Barroso & Santa-Clara 2015
(carry + momentum + value diversify). Expected combo Sharpe about 0.5-0.8 per year: not a fast passer, a background
P&L stream. Weakness: 8 currencies, few independent value bets in 16 years.

CURRENCIES: USD EUR JPY GBP CHF AUD CAD NZD, traded through the 28 FX pairs (gjstrat.data MAJORS + MINORS).

SIGNAL DAY: the last weekday of each month (Dec 25 and Jan 1 excluded: step back to the previous weekday). All
inputs are dated <= that day (CPI with the publication lags below).

VALUE (Asness-Moskowitz-Pedersen)
  S_c,m = FRED H.10 noon NY spot in USD per unit of c on the last available day of month m (DEXUSEU, DEXUSUK,
          DEXUSAL, DEXUSNZ direct; DEXJPUS, DEXSZUS, DEXCAUS inverted). For the signal month, the last H.10 value
          dated <= the signal day. (H.10 is published weekly, but the noon rate is a market price observable at noon
          NY on its date, so using it on that date is not look-ahead.)
  P = BIS long CPI (data/extra/cpi_bis_monthly.csv; REF_AREA US, XM (EUR), JP, GB, CH, AU, CA, NZ). Publication lag:
      2 months for monthly CPIs, 4 months for AU and NZ (quarterly values repeated over the quarter's months).
  q_c,m = ln S_c,m + ln P_c,(m - lag_c) - ln P_US,(m - 2)
  v_c,t = -( q_c,t - mean of q_c,m over m = t-66 .. t-54 )  (13 months centred 5 years back); v_USD = 0.
  Higher v = cheaper in real terms = more attractive.
  SPEC FIX (impossibility): BIS has no US CPI for 2025-10 (US government shutdown; never published). A missing CPI
  month inside a series uses the last earlier value (forward fill). This touches only the 2025-12 signal (P_US for
  m-2 = 2025-10).

MOMENTUM
  Daily excess log return of currency c vs USD on observation d = ln S_c,d - ln S_c,prev + (r_c - r_USD)/100/252,
  where S = USD per unit of c from the daily_table (NY 17:00 bid) closes of the USD pair (EURUSD, GBPUSD, AUDUSD,
  NZDUSD direct; USDJPY, USDCHF, USDCAD inverted) from the first daily_table date (2010-03-18; daily_table drops its
  first ~55 days for the sma50 warm-up), and H.10 noon rates before that date (spliced as one level series).
  Rates r = BIS policy rates (data/extra/policy_rates_bis_daily.csv) with EUR = ECB deposit facility rate
  (data/extra/ecb_deposit_rate_daily.csv), each = last observation dated <= d - 1 calendar day. (BIS has no JP
  observation 2013-04-04 .. 2016-09-20; the last value 0.05 is carried forward.)
  Windows on each currency's own observation series, k = last observation dated <= signal day:
    21d  = sum of the returns from price k-21 to k (last 21 returns);
    63d  = from price k-63 to k;
    12-1 = from price k-252 to price k-21 (231 returns; skips the last month).
  USD = 0. Higher = more attractive.

CARRY: policy rate of c (same sources) = last observation dated <= signal day - 1 calendar day. Higher = more attractive.

RANKING: per style, rank the 8 currencies 1..8 (1 = most attractive; tied values share the average rank).
  A combo's score = sum of its style ranks (equivalent to the mean). Order = sort by (score, currency code), so
  remaining ties break alphabetically (the fx_carry convention). Top-k = first k, bottom-k = last k.

EXECUTION (identical to run_alpha_fx_carry.py)
  Long the top-k vs short the bottom-k via the k x k crosses in quoted form among the 28 pairs (long AUD / short JPY
  = AUDJPY BUY; long NZD / short EUR = EURNZD SELL), 1R per leg.
  Entry = market at the 07:00 UTC minute open on the first weekday of the next month (Jan 1 excluded).
  Time exit at 07:00 UTC on the first weekday of the following month (the next entry minute).
  SL = 3.0 x ATR20 (daily_table atr20 of the entry day, shifted = known before the day). No TP. A stopped leg stays
  flat until the next rebalance. An unchanged leg is still closed and reopened each month (full costs each month).
  SPEC FIX (impossibility): a minute with vol == 0 has no real price, so "the 07:00 minute" of a pair is the first
  minute with vol > 0 in [07:00, 08:00) UTC (normally 07:00); none -> that leg is skipped (counted in the report).
  Monthly portfolio R = mean R of the month's legs. A flat month (V5 gate) = 0 and is included.
  Month = entry month (period of a month = its entry date: design 2010-17, check 2018-23, holdout 2024-26).
  Warm-up: a month is left out of a variant's series (not counted as flat) when an input it needs is undefined
  (ATR20 of the entry day for every leg; the momentum windows; value history; 252 previous FXVOL values).
  A month whose exit is after the data end (2026-10-07) is left out.

VARIANTS (8 candidates; CARRY is an in-script reference for the correlations, not a candidate)
  V1: value, k=2 (4 crosses)
  V2: value, k=3 (9 crosses)
  M1: cross-sectional momentum 21d, k=2 (Menkhoff et al. 2012 best)
  M2: momentum 63d, k=2
  M3: momentum 12-1, k=2 (AMP)
  V3: 50/50 combo = value rank + M3 rank, k=2
  V4: 3-style combo = carry rank + M3 rank + value rank, k=2
  V5: V4, flat for the month when FXVOL > the 80th percentile (numpy linear) of its previous 252 daily values.
      FXVOL on a date = mean over the 28 pairs (those with a value) of the 20-day std of daily_table close-to-close
      log returns; value at the signal day = last FXVOL dated <= signal day.
  CARRY (reference): carry rank, k=2 (= fx_carry C1; used as a pipeline cross-check against that run).

COSTS: per pair, gjstrat.accounting.account(trades of the pair sorted by (exit_i, entry_i), m, 10_000, commission=7,
  swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'] (swap inside R).

SURVIVAL (charter, applied to the MONTHLY PORTFOLIO R series): design (2010-17) t >= 2 AND avg R > 0 in check
  (2018-23) AND in holdout (2024-26). 8 tests -> about 8 x 0.006 = 0.05 survivors expected by luck.
  "Inconclusive" (pre-declared) = design t in [1.5, 2) with design, check and holdout avg R all > 0.

REPORT: monthly portfolio R per period with t; leg stats (trades, trades/month, win %, avg win / avg loss, avg R and t
  per period, last 3 years = entries after 2023-10-07); R split price / cost / swap; turnover (legs changed per
  month); correlations of the monthly R: V1 vs M3 (theory: negative), V1 and V4 vs CARRY, full matrix; yearly table
  of top/bottom currencies per style; worst month; sum of monthly R by year; unique legs by pair; data cross-checks
  (BIS CPI vs FRED CPIAUCSL / HICP; CARRY vs fx_carry C1).

ADDED AFTER THE FIRST RUN (descriptive only; no new tests, the verdict is unchanged): (a) the part of the swap that
  is the 1%/yr broker markup, approximated per leg as 0.01 x calendar days held / 365 x entry price / SL distance
  (entry price ~ the pair's daily_table close before the entry day), and the net R with that markup removed;
  (b) V1 and V2 legs by long/short currency per period (where the value P&L came from).

COMPUTE: pass 1 loads each of the 28 pairs once (Pool(2), maxtasksperchild=1) for daily_table close/atr20/end_i,
  caches results/alpha_hunt/fx_value_mom/daily.csv, then del. Pass 2 builds the signals and legs from the cache.
  Pass 3 loads each traded pair once (Pool(2)) and simulates every unique (pair, month, side) leg of all variants.

    python run_alpha_fx_value_mom.py            # passes 1-3 + report
    python run_alpha_fx_value_mom.py --report   # report only, from the caches
"""
import gc
import os
import sys
import time
from multiprocessing import get_context

import numpy as np
import pandas as pd

from gjstrat.accounting import LOT, account
from gjstrat.data import MAJORS, MINORS, load_market
from gjstrat.patterns import Signal, daily_table, simulate
from gjstrat.swap import SwapModel
from run_alpha_fx_carry import (asof, first_weekday, last_before, last_weekday, leg_summary, load_rates,
                                month_summary, pctl_gate, quoted)
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/fx_value_mom"
DATA = "data/{}_2010-01-01_2026-10-07.npz"
PAIRS = MAJORS + MINORS
CCYS = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
FOREIGN = [c for c in CCYS if c != "USD"]
H10 = {"EUR": ("DEXUSEU", False), "GBP": ("DEXUSUK", False), "AUD": ("DEXUSAL", False), "NZD": ("DEXUSNZ", False),
       "JPY": ("DEXJPUS", True), "CHF": ("DEXSZUS", True), "CAD": ("DEXCAUS", True)}
USDPAIR = {"EUR": ("EURUSD", False), "GBP": ("GBPUSD", False), "AUD": ("AUDUSD", False), "NZD": ("NZDUSD", False),
           "JPY": ("USDJPY", True), "CHF": ("USDCHF", True), "CAD": ("USDCAD", True)}
CPI_AREA = {"USD": "US", "EUR": "XM", "JPY": "JP", "GBP": "GB", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}
CPI_LAG = {c: (4 if c in ("AUD", "NZD") else 2) for c in CCYS}
SL_ATR = 3.0
LAST3 = pd.Timestamp("2023-10-07")
STYLES = ["val", "m21", "m63", "m12", "carry"]
SPEC = {"V1": (["val"], 2, False), "V2": (["val"], 3, False), "M1": (["m21"], 2, False),
        "M2": (["m63"], 2, False), "M3": (["m12"], 2, False), "V3": (["val", "m12"], 2, False),
        "V4": (["carry", "m12", "val"], 2, False), "V5": (["carry", "m12", "val"], 2, True),
        "CARRY": (["carry"], 2, False)}
VARIANTS = list(SPEC)
CANDIDATES = VARIANTS[:8]
NAMES = {"V1": "V1 value k=2", "V2": "V2 value k=3", "M1": "M1 mom 21d k=2", "M2": "M2 mom 63d k=2",
         "M3": "M3 mom 12-1 k=2", "V3": "V3 value+M3 k=2", "V4": "V4 carry+M3+value k=2",
         "V5": "V5 V4 + FXVOL gate", "CARRY": "CARRY k=2 (reference)"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------------------------------------- pass 1
def _daily_pair(sym):
    m = load_market(DATA.format(sym.lower()))
    d = daily_table(m)
    df = pd.DataFrame({"sym": sym, "date": d.index, "close": d["close"].to_numpy(),
                       "atr20": d["atr20"].to_numpy(), "end_i": d["end_i"].to_numpy()})
    meta = {"sym": sym, "t0": str(m.t0), "n": m.n, "pip": m.pip, "last_ts": str(m.ts(m.n - 1))}
    del m, d
    gc.collect()
    return df, meta


def pass1():
    path = f"{OUT}/daily.csv"
    if os.path.exists(path) and os.path.exists(f"{OUT}/meta.csv"):
        return pd.read_csv(path, parse_dates=["date"]), pd.read_csv(f"{OUT}/meta.csv").set_index("sym")
    rows, meta = [], []
    with get_context("fork").Pool(2, maxtasksperchild=1) as pool:
        for df, mt in pool.imap(_daily_pair, PAIRS, chunksize=1):
            rows.append(df)
            meta.append(mt)
            log("pass1", mt["sym"], len(df))
    daily = pd.concat(rows, ignore_index=True)
    daily.to_csv(path, index=False)
    meta = pd.DataFrame(meta).set_index("sym")
    meta.to_csv(f"{OUT}/meta.csv")
    return pd.read_csv(path, parse_dates=["date"]), meta


# ----------------------------------------------------------------------------------------------- pass 2
def load_h10():
    out = {}
    for c, (sid, inv) in H10.items():
        x = pd.read_csv(f"data/extra/{sid}.csv")
        s = pd.Series(pd.to_numeric(x[sid], errors="coerce").to_numpy(),
                      index=pd.to_datetime(x["observation_date"])).dropna()
        s = s[s > 0].sort_index()
        out[c] = 1.0 / s if inv else s
    return out


def load_cpi():
    c = pd.read_csv("data/extra/cpi_bis_monthly.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    out, filled = {}, []
    for ccy, area in CPI_AREA.items():
        x = c[c.REF_AREA == area]
        s = pd.Series(pd.to_numeric(x.OBS_VALUE, errors="coerce").to_numpy(),
                      index=pd.PeriodIndex(x.TIME_PERIOD, freq="M")).sort_index()
        filled += [f"{ccy} {p}" for p in s.index[s.isna()]]
        out[ccy] = s.ffill()
    return out, filled


def rate_on(s, days):
    """Value of the last observation of s dated <= each of days (NaN before the first)."""
    k = s.index.searchsorted(days, side="right") - 1
    v = s.to_numpy()[np.clip(k, 0, None)]
    return np.where(k >= 0, v, np.nan)


def features(daily):
    close = {s: g.set_index("date")["close"].sort_index() for s, g in daily.groupby("sym")}
    atr = {s: g.set_index("date")["atr20"].sort_index() for s, g in daily.groupby("sym")}
    lr = {s: np.log(c).diff() for s, c in close.items()}
    vol20 = {s: x.rolling(20).std() for s, x in lr.items()}
    fxvol = pd.DataFrame(vol20).mean(axis=1, skipna=True).dropna()
    rates = load_rates()
    h10 = load_h10()
    cpi, cpi_filled = load_cpi()
    spot, X, splice = {}, {}, {}
    for c, (sym, inv) in USDPAIR.items():
        dt = close[sym].dropna()
        dt = 1.0 / dt if inv else dt
        first = dt.index.min()
        splice[c] = first
        s = pd.concat([h10[c][h10[c].index < first], dt]).sort_index()
        spot[c] = s
        d1 = s.index - pd.Timedelta(days=1)
        acc = (rate_on(rates[c], d1) - rate_on(rates["USD"], d1)) / 100.0 / 252.0
        x = np.log(s).diff() + acc
        X[c] = x.iloc[1:]
    ms = {c: s.groupby(s.index.to_period("M")).last() for c, s in h10.items()}
    return dict(close=close, atr=atr, fxvol=fxvol, rates=rates, h10=h10, cpi=cpi, cpi_filled=cpi_filled,
                spot=spot, X=X, ms=ms, splice=splice)


def window_sum(x, day, a, b):
    """Sum of the returns from price k-a to price k-b (positions k-a+1 .. k-b), k = last obs dated <= day."""
    k = x.index.searchsorted(day, side="right") - 1
    lo, hi = k - a + 1, k - b
    if lo < 1 or hi < lo:
        return np.nan
    w = x.to_numpy()[lo:hi + 1]
    return np.nan if np.isnan(w).any() else float(w.sum())


def q_of(F, c, m, S=None):
    if S is None:
        S = F["ms"][c].get(m, np.nan)
    pc = F["cpi"][c].get(m - CPI_LAG[c], np.nan)
    pu = F["cpi"]["USD"].get(m - CPI_LAG["USD"], np.nan)
    return np.log(S) + np.log(pc) - np.log(pu)


def signals(F, sig):
    t = sig.to_period("M")
    out = {s: {"USD": 0.0} for s in STYLES}
    for c in FOREIGN:
        S = last_before(F["h10"][c], sig)[0]
        qt = q_of(F, c, t, S)
        hist = [q_of(F, c, m) for m in pd.period_range(t - 66, t - 54, freq="M")]
        out["val"][c] = -(qt - float(np.mean(hist)))
        out["m21"][c] = window_sum(F["X"][c], sig, 21, 0)
        out["m63"][c] = window_sum(F["X"][c], sig, 63, 0)
        out["m12"][c] = window_sum(F["X"][c], sig, 252, 21)
    for c in CCYS:
        out["carry"][c] = last_before(F["rates"][c], sig - pd.Timedelta(days=1))[0]
    return out


def order_of(sg, styles):
    """Currencies sorted from most to least attractive; None if any input is undefined."""
    score = pd.Series(0.0, index=CCYS)
    for s in styles:
        x = pd.Series(sg[s]).reindex(CCYS)
        if x.isna().any():
            return None
        score += x.rank(ascending=False, method="average")
    return sorted(CCYS, key=lambda c: (score[c], c))


def pass2(daily, meta, F):
    data_end = pd.Timestamp(meta["last_ts"].min())
    legs, mon = [], []
    for p in pd.period_range("2010-01", "2026-10", freq="M"):
        prev, nxt = p - 1, p + 1
        sig = last_weekday(prev.year, prev.month)
        entry = first_weekday(p.year, p.month)
        nxt_entry = first_weekday(nxt.year, nxt.month)
        sg = signals(F, sig)
        fx_v, fx_p = pctl_gate(F["fxvol"], sig)
        complete = nxt_entry + pd.Timedelta(hours=8) < data_end
        row = dict(month=str(p), signal_day=sig.date(), entry_day=entry.date(), next_entry=nxt_entry.date(),
                   fxvol=fx_v, fxvol_p80=fx_p)
        for s in STYLES:
            for c in CCYS:
                row[f"{s}_{c}"] = sg[s][c]
        for v, (styles, k, gate) in SPEC.items():
            order = order_of(sg, styles)
            row[f"{v}_order"] = " > ".join(order) if order else ""
            if order is None:
                lv, warm = [], True
            else:
                base = []
                for L in order[:k]:
                    for S in order[-k:]:
                        sym, side = quoted(L, S)
                        base.append(dict(sym=sym, side=side, long=L, short=S, atr=asof(F["atr"][sym], entry)))
                warm = any(np.isnan(x["atr"]) for x in base)
                lv = base
                if gate:
                    warm = warm or np.isnan(fx_v) or np.isnan(fx_p)
                    if not warm and fx_v > fx_p:
                        lv = []
                    row[f"{v}_gated"] = bool(not warm and fx_v > fx_p)
            status = "incomplete" if not complete else ("warmup" if warm else "ok")
            row[f"{v}_status"] = status
            row[f"{v}_legs"] = len(lv)
            for x in lv:
                legs.append(dict(variant=v, month=str(p), entry_day=entry, next_entry=nxt_entry, status=status, **x))
        mon.append(row)
    return pd.DataFrame(legs), pd.DataFrame(mon).set_index("month")


# ----------------------------------------------------------------------------------------------- pass 3
def _sim_pair(args):
    sym, rows = args
    m = load_market(DATA.format(sym.lower()))
    sw = SwapModel.from_fred("rates", 1.0)

    def T(day):
        i0 = m.idx(pd.Timestamp(day) + pd.Timedelta(hours=7))
        if i0 < 0 or i0 >= m.n:
            return None
        w = np.flatnonzero(m.vol[i0:i0 + 60] > 0)
        return int(i0 + w[0]) if len(w) else None

    trades, keys, skipped, res = [], [], [], []
    for month, side, entry_day, next_entry, atr in rows:
        ei, xi = T(entry_day), T(next_entry)
        if ei is None or xi is None or np.isnan(atr):
            skipped.append(dict(sym=sym, month=month, side=side,
                                why="no live minute 07:00-08:00 UTC" if (ei is None or xi is None) else "no ATR"))
            continue
        s = Signal(pd.Timestamp(entry_day), side, ei, "market", None, ei + 1, SL_ATR * atr, None, xi, month)
        t = simulate(m, s)
        if t is None:
            skipped.append(dict(sym=sym, month=month, side=side, why="simulate None"))
            continue
        trades.append(t)
        keys.append(month)
    if trades:
        order = sorted(range(len(trades)), key=lambda k: (trades[k].exit_i, trades[k].entry_i))
        trades, keys = [trades[k] for k in order], [keys[k] for k in order]
        lg = account(trades, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
        lg = lg.set_index(["entry_i", "exit_i", "side"])
        for t, mo in zip(trades, keys):
            a = lg.loc[(t.entry_i, t.exit_i, t.side)]
            risk_usd = a["lots"] * t.risk * LOT / m.quote_per_usd[t.entry_i]
            swapR = a["swap_usd"] / risk_usd
            R = float(a["R"])
            res.append(dict(sym=sym, month=mo, side=t.side, entry_i=t.entry_i, exit_i=t.exit_i,
                            entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i), reason=t.reason,
                            sl_pips=t.risk / m.pip, spread_pips=t.spread / m.pip, priceR=t.r, swapR=swapR,
                            costR=t.r + swapR - R, R=R, nights=int(a["swap_nights"]),
                            entry_live_at_0700=bool(t.entry_i == m.idx(t.day + pd.Timedelta(hours=7)))))
    del m
    gc.collect()
    return sym, res, skipped


def pass3(L):
    todo = L[L.status == "ok"][["sym", "month", "side", "entry_day", "next_entry", "atr"]] \
        .drop_duplicates(["sym", "month", "side"])
    jobs = [(sym, [(x.month, x.side, x.entry_day, x.next_entry, x.atr) for x in g.itertuples(index=False)])
            for sym, g in todo.groupby("sym")]
    res, skipped = [], []
    with get_context("fork").Pool(2, maxtasksperchild=1) as pool:
        for sym, r, sk in pool.imap_unordered(_sim_pair, jobs, chunksize=1):
            res += r
            skipped += sk
            log("pass3", sym, len(r), "legs")
    return pd.DataFrame(res), pd.DataFrame(skipped, columns=["sym", "month", "side", "why"])


# ----------------------------------------------------------------------------------------------- report
def variant_legs(L, res, v):
    lv = L[(L.variant == v) & (L.status == "ok")]
    return lv.merge(res, on=["sym", "month", "side"], how="left")


def monthly_series(L, M, res, v):
    ok = M.index[M[f"{v}_status"] == "ok"]
    g = variant_legs(L, res, v).groupby("month")["R"]
    out, dropped = {}, []
    for mo in ok:
        if M.loc[mo, f"{v}_legs"] == 0:
            out[mo] = 0.0
        elif mo in g.groups and g.get_group(mo).notna().any():
            out[mo] = g.get_group(mo).mean()
        else:
            dropped.append(mo)
    s = pd.Series(out, dtype=float)
    s.index = pd.DatetimeIndex([pd.Timestamp(M.loc[mo, "entry_day"]) for mo in s.index])
    return s.sort_index(), dropped


def turnover(L, M, v):
    ok = [mo for mo in M.index if M.loc[mo, f"{v}_status"] == "ok"]
    lv = L[(L.variant == v) & (L.status == "ok")]
    sets = {mo: set(zip(g.sym, g.side)) for mo, g in lv.groupby("month")}
    lng = {mo: set(g.long) for mo, g in lv.groupby("month")}
    sht = {mo: set(g.short) for mo, g in lv.groupby("month")}
    new, nl, cch = [], [], []
    for a, b in zip(ok[:-1], ok[1:]):
        if (pd.Period(b, "M") - pd.Period(a, "M")).n != 1:
            continue
        cur, prv = sets.get(b, set()), sets.get(a, set())
        new.append(len(cur - prv))
        nl.append(len(cur))
        cch.append(len(lng.get(b, set()) - lng.get(a, set())) + len(sht.get(b, set()) - sht.get(a, set())))
    new, nl = np.array(new, float), np.array(nl, float)
    return {"month pairs": len(new), "avg legs": nl.mean(), "avg legs changed/month": new.mean(),
            "% of legs changed": new.sum() / nl.sum() * 100 if nl.sum() else np.nan,
            "months with no change %": (new == 0).mean() * 100,
            "avg currency slots changed/month": np.mean(cch)}


def held_table(M, v, k=2):
    rows = []
    for mo in M.index:
        if M.loc[mo, f"{v}_status"] != "ok":
            continue
        order = M.loc[mo, f"{v}_order"].split(" > ")
        y = pd.Timestamp(M.loc[mo, "entry_day"]).year
        rows += [dict(year=y, ccy=c, side="L") for c in order[:k]] + [dict(year=y, ccy=c, side="S") for c in order[-k:]]
    h = pd.DataFrame(rows)
    a = h[h.side == "L"].groupby(["year", "ccy"]).size().unstack(fill_value=0)
    b = h[h.side == "S"].groupby(["year", "ccy"]).size().unstack(fill_value=0)
    t = pd.DataFrame(index=sorted(set(a.index) | set(b.index)))
    for c in CCYS:
        la = a[c] if c in a else pd.Series(dtype=int)
        sb = b[c] if c in b else pd.Series(dtype=int)
        t[c] = [f"L{int(la.get(y, 0))}/S{int(sb.get(y, 0))}" if (la.get(y, 0) or sb.get(y, 0)) else "" for y in t.index]
    t.index.name = f"{v} year"
    return t


def cross_checks(F):
    rows = []
    for ser, ccy in (("CPIAUCSL", "USD"), ("CP0000EZ19M086NEST", "EUR")):
        x = pd.read_csv(f"data/extra/{ser}.csv")
        s = pd.Series(pd.to_numeric(x[ser], errors="coerce").to_numpy(),
                      index=pd.PeriodIndex(pd.to_datetime(x.observation_date), freq="M")).dropna()
        b = F["cpi"][ccy]
        j = pd.concat([np.log(s).diff(12).rename("fred"), np.log(b).diff(12).rename("bis")], axis=1).dropna()
        j = j[j.index >= pd.Period("2004-01", "M")]
        rows.append({"check": f"BIS {CPI_AREA[ccy]} CPI vs FRED {ser} (yoy log change)", "n": len(j),
                     "corr": j.fred.corr(j.bis), "mean abs diff (pp)": (j.fred - j.bis).abs().mean() * 100})
    for c, (sym, inv) in USDPAIR.items():
        h = np.log(F["ms"][c])
        dt = F["close"][sym].dropna()
        dt = np.log(1.0 / dt if inv else dt)
        d = dt.groupby(dt.index.to_period("M")).last()
        j = pd.concat([h.diff().rename("h10"), d.diff().rename("dt")], axis=1).dropna()
        rows.append({"check": f"H.10 {H10[c][0]} vs daily_table {sym} (monthly log change)", "n": len(j),
                     "corr": j.h10.corr(j.dt), "mean abs diff (pp)": (j.h10 - j.dt).abs().mean() * 100})
    return pd.DataFrame(rows).set_index("check")


def markup_table(L, res, F, meta):
    """Descriptive (added after the run): approximate 1%/yr markup part of swap R and net R without it."""
    r = res.copy()
    r["entry_ts"], r["exit_ts"] = pd.to_datetime(r["entry_ts"]), pd.to_datetime(r["exit_ts"])
    days = (r.exit_ts - r.entry_ts).dt.total_seconds() / 86400
    px = np.array([asof(F["close"][s], ts.normalize() - pd.Timedelta(days=1)) for s, ts in zip(r.sym, r.entry_ts)])
    pip = r.sym.map(meta["pip"]).to_numpy(float)
    r["markupR"] = 0.01 * days / 365 * px / (r.sl_pips.to_numpy(float) * pip)
    rows = []
    for v in VARIANTS:
        j = variant_legs(L, r, v).dropna(subset=["R"])
        d = pd.DatetimeIndex(j.entry_day)
        row = {}
        for p, (a, b) in list(PER.items()) + [("all", ("2000-01-01", "2030-01-01"))]:
            q = j[(d >= pd.Timestamp(a)) & (d <= pd.Timestamp(b))]
            row[f"{p} markup R"] = -q.markupR.mean()
            row[f"{p} swap ex-markup R"] = (q.swapR + q.markupR).mean()
            row[f"{p} net R ex-markup"] = (q.R + q.markupR).mean()
        rows.append(pd.Series(row, name=NAMES[v]))
    out = pd.DataFrame(rows)
    out.index.name = "variant"
    return out


def side_table(L, res, v):
    """Descriptive (added after the run): legs of variant v by long and by short currency, avg R per period."""
    j = variant_legs(L, res, v).dropna(subset=["R"])
    d = pd.DatetimeIndex(j.entry_day)
    j["per"] = np.select([d <= pd.Timestamp(PER["design"][1]), d <= pd.Timestamp(PER["check"][1])],
                         ["design", "check"], "holdout")
    rows = []
    for role in ("long", "short"):
        for c in CCYS:
            q = j[j[role] == c]
            if not len(q):
                continue
            row = {"legs": len(q)}
            for p in PER:
                qq = q[q.per == p]
                row[f"{p} n"], row[f"{p} avg R"] = len(qq), qq.R.mean() if len(qq) else np.nan
            rows.append(pd.Series(row, name=f"{role} {c}"))
    out = pd.DataFrame(rows)
    out.index.name = f"{v} legs by currency"
    return out


def report(L, M, res, skipped, F, meta):
    series, drops, MS, LS, split, TO = {}, {}, [], [], [], []
    for v in VARIANTS:
        s, dropped = monthly_series(L, M, res, v)
        series[v], drops[v] = s, dropped
        j = variant_legs(L, res, v).dropna(subset=["R"])
        ms = month_summary(s)
        ms["first month"] = s.index.min().strftime("%Y-%m") if len(s) else ""
        if v in CANDIDATES:
            surv = ms["design t"] >= 2 and ms["check avg R"] > 0 and ms["holdout avg R"] > 0
            inc = (not surv and 1.5 <= ms["design t"] < 2 and ms["design avg R"] > 0 and ms["check avg R"] > 0
                   and ms["holdout avg R"] > 0)
            ms["survives"] = "YES" if surv else ("inconclusive" if inc else "no")
        else:
            ms["survives"] = "n/a"
        w = s.idxmin() if len(s) else None
        ms["worst month"] = w.strftime("%Y-%m") if w is not None else ""
        ms["worst month R"] = s.min()
        eq = s.cumsum()
        ms["max DD (sum of monthly R)"] = (eq - eq.cummax()).min()
        MS.append(pd.Series(ms, name=NAMES[v]))
        days = pd.DatetimeIndex(j["entry_day"])
        LS.append(pd.Series(leg_summary(j["R"], days, len(s)), name=NAMES[v]))
        sp = {}
        for p, (a, b) in list(PER.items()) + [("all", ("2000-01-01", "2030-01-01"))]:
            q = j[(days >= pd.Timestamp(a)) & (days <= pd.Timestamp(b))]
            sp[f"{p} price R"], sp[f"{p} cost R"], sp[f"{p} swap R"], sp[f"{p} net R"] = \
                q.priceR.mean(), -q.costR.mean(), q.swapR.mean(), q.R.mean()
        sp["SL hit %"] = (j.reason == "SL").mean() * 100
        split.append(pd.Series(sp, name=NAMES[v]))
        TO.append(pd.Series(turnover(L, M, v), name=NAMES[v]))
    MS, LS, split, TO = pd.DataFrame(MS), pd.DataFrame(LS), pd.DataFrame(split), pd.DataFrame(TO)
    for t in (MS, LS, split, TO):
        t.index.name = "variant"
    MS.to_csv(f"{OUT}/monthly_summary.csv")
    LS.to_csv(f"{OUT}/leg_summary.csv")
    split.to_csv(f"{OUT}/swap_split.csv")
    TO.to_csv(f"{OUT}/turnover.csv")
    SR = pd.DataFrame(series)
    SR.to_csv(f"{OUT}/monthly_R.csv")

    # correlations
    C = SR.corr(min_periods=24)
    C.to_csv(f"{OUT}/corr.csv")
    crow = []
    for a, b in (("V1", "M3"), ("V1", "CARRY"), ("V4", "CARRY"), ("V3", "CARRY"), ("M3", "CARRY"), ("V2", "M3"),
                 ("V1", "M1")):
        r = {"pair": f"{a} vs {b}"}
        j = SR[[a, b]].dropna()
        r["all n"], r["all corr"] = len(j), j[a].corr(j[b])
        for p, (x, y) in PER.items():
            q = j[(j.index >= pd.Timestamp(x)) & (j.index <= pd.Timestamp(y))]
            r[f"{p} corr"] = q[a].corr(q[b]) if len(q) > 2 else np.nan
        crow.append(r)
    CP = pd.DataFrame(crow).set_index("pair")
    Cshow = C.copy()
    Cshow.index.name = "monthly R corr"

    # common window
    start = max(s.index.min() for s in series.values())
    CW = pd.DataFrame([pd.Series(month_summary(series[v][series[v].index >= start]), name=NAMES[v])
                       for v in VARIANTS])
    CW.index.name = "variant"

    # yearly sums
    Y = pd.DataFrame({v: series[v].groupby(series[v].index.year).sum() for v in VARIANTS})
    Y.index.name = "year (sum of monthly R)"

    # unique legs by pair (candidates)
    pool = pd.concat([variant_legs(L, res, v).dropna(subset=["R"]) for v in CANDIDATES])
    uniq = pool.drop_duplicates(["sym", "month", "side"])
    BP = uniq.groupby("sym").apply(lambda q: pd.Series({"legs": len(q), "avg R": q.R.mean(), "t": tstat(q.R),
                                                         "swap R": q.swapR.mean(), "win %": (q.R > 0).mean() * 100}))
    BP.index.name = "pair"
    npos = int((BP["avg R"] > 0).sum())
    PL = pd.DataFrame([pd.Series(leg_summary(uniq.R, pd.DatetimeIndex(uniq.entry_day), len(series["V1"])),
                                 name="unique legs of V1-V5, M1-M3")])
    PL.index.name = "pool"

    # held tables
    held = [held_table(M, v) for v in ("V1", "M1", "M2", "M3", "CARRY", "V3", "V4")]

    # latest signal snapshot
    last_mo = M.index[-1]
    snap = pd.DataFrame({s: [M.loc[last_mo, f"{s}_{c}"] for c in CCYS] for s in STYLES}, index=CCYS)
    snap.index.name = f"signal {M.loc[last_mo, 'signal_day']}"
    snap_orders = "\n".join(f"- {NAMES[v]}: {M.loc[last_mo, f'{v}_order']}" for v in ("V1", "M1", "M3", "V3", "V4",
                                                                                         "CARRY"))

    # checks
    X = cross_checks(F)
    fx_c1 = "fx_carry monthly_R.csv not found"
    if os.path.exists("results/alpha_hunt/fx_carry/monthly_R.csv"):
        o = pd.read_csv("results/alpha_hunt/fx_carry/monthly_R.csv", index_col=0, parse_dates=True)["C1"].dropna()
        j = pd.concat([o.rename("fx_carry C1"), series["CARRY"].rename("CARRY")], axis=1).dropna()
        fx_c1 = (f"CARRY vs fx_carry C1: {len(j)} common months, max |diff| = {(j.iloc[:, 0] - j.iloc[:, 1]).abs().max():.6f} R, "
                 f"corr = {j.iloc[:, 0].corr(j.iloc[:, 1]):.4f}")

    gated = int(M.get("V5_gated", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    cand = MS.loc[[NAMES[v] for v in CANDIDATES]]
    survivors = list(cand.index[cand.survives == "YES"])
    inconclusive = list(cand.index[cand.survives == "inconclusive"])
    mcols = ["first month", "months", "flat %", "avg R", "t", "Sharpe/yr", "win months %", "design n", "design avg R",
             "design t", "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t",
             "last3y avg R", "last3y t", "survives"]
    lcols = ["trades", "trades/month", "win %", "avg win/avg loss", "avg R", "t", "design avg R", "design t",
             "check avg R", "check t", "holdout avg R", "holdout t", "last3y n", "last3y avg R", "last3y t"]
    drop_txt = ", ".join(f"{v}: {len(d)}" for v, d in drops.items() if d) or "none"
    entry_late = int((~res.entry_live_at_0700.astype(bool)).sum()) if len(res) else 0
    sk = (", ".join(f"{a}: {b}" for a, b in skipped.groupby("why").size().items()) if len(skipped) else "none")
    txt = ["# Alpha hunt: fx_value_mom (G8 FX value, cross-sectional momentum, carry-momentum-value combos)\n",
           "Spec fixed before running: see the docstring of `run_alpha_fx_value_mom.py`.\n",
           f"Survival bar (monthly portfolio R): design t >= 2 AND check avg R > 0 AND holdout avg R > 0. "
           f"8 candidates -> ~{8 * 0.006:.2f} survivors expected by luck.\n",
           f"**Survivors: {', '.join(survivors) if survivors else 'none'}.** "
           f"Inconclusive (design t in [1.5, 2), all periods > 0): {', '.join(inconclusive) if inconclusive else 'none'}.\n",
           "## Monthly portfolio R (mean R of the month's legs; flat month = 0)\n",
           fmt_table(MS[mcols], ".3f"),
           f"\nMonths with legs but no simulated trade (left out): {drop_txt}. Skipped legs: {sk}. "
           f"Entries/exits moved past a dead 07:00 minute: {entry_late} of {len(res)} simulated legs. "
           f"V5 gated (flat) months: {gated}.\n",
           "\n### Common window (all variants defined, from " + start.strftime("%Y-%m") + ")\n",
           fmt_table(CW[mcols[1:-1]], ".3f"),
           "\n## Worst month and drawdown (monthly portfolio R)\n",
           fmt_table(MS[["worst month", "worst month R", "max DD (sum of monthly R)"]], ".3f"),
           "\n## Leg-level stats (each leg = one cross held a month or until its 3xATR stop)\n",
           fmt_table(LS[lcols], ".3f"),
           "\n## R split per leg: price (spot incl. spread) + cost (commission + slippage) + swap = net\n",
           fmt_table(split, ".3f"),
           "\n## Turnover (consecutive included months)\n",
           fmt_table(TO, ".2f"),
           "\n## Correlations of the monthly portfolio R\n",
           fmt_table(CP, ".3f"), "\n", fmt_table(Cshow, ".2f"),
           "\n## Sum of monthly R by year\n", fmt_table(Y, ".2f"),
           "\n## Unique legs pooled across the 8 candidates\n", fmt_table(PL[lcols], ".3f"),
           f"\nBy pair ({npos} of {len(BP)} pairs with avg R > 0):\n",
           fmt_table(BP.sort_values("legs", ascending=False), ".3f"),
           "\n## Currencies held per style (months long L / short S per year, k=2)\n"]
    for t in held:
        txt += [fmt_table(t, ".0f"), "\n"]
    txt += [f"\n## Latest signal (for the {last_mo} entry; that month is incomplete in the data)\n",
            "val = value v (log points), m21/m63/m12 = momentum excess log return, carry = policy rate %.\n\n",
            fmt_table(snap, ".3f"), "\n", snap_orders, "\n",
            "\n## Descriptive, added after the run (not tests): 1%/yr swap markup and net R without it\n",
            "Markup R ~ 0.01 x days held / 365 x entry price / SL distance per leg (negative = cost).\n\n",
            fmt_table(markup_table(L, res, F, meta), ".3f"), "\n",
            "\n## Descriptive, added after the run (not tests): value legs by long / short currency\n",
            fmt_table(side_table(L, res, "V1"), ".3f"), "\n", fmt_table(side_table(L, res, "V2"), ".3f"), "\n",
            "\n## Data cross-checks\n", fmt_table(X, ".3f"), "\n",
            f"\n{fx_c1}.\n",
            f"\nCPI months forward-filled (missing in BIS): {', '.join(F['cpi_filled']) or 'none'}. "
            f"Momentum splice (first daily_table date per currency): "
            f"{', '.join(f'{c} {d.date()}' for c, d in F['splice'].items())}.\n"]
    with open(f"{OUT}/REPORT_tables.md", "w") as f:
        f.write("\n".join(txt))
    return MS, LS, survivors, inconclusive, CP


# ----------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    daily, meta = pass1()
    assert meta["t0"].nunique() == 1, "pairs on different grids"
    log("pass1 done", round(time.time() - t0))
    F = features(daily)
    L, M = pass2(daily, meta, F)
    L.to_csv(f"{OUT}/legs_plan.csv", index=False)
    M.to_csv(f"{OUT}/months.csv")
    log("pass2 done", len(L), "planned legs", round(time.time() - t0))
    if os.path.exists(f"{OUT}/leg_results.csv") and "--report" in sys.argv:
        res = pd.read_csv(f"{OUT}/leg_results.csv")
        skipped = pd.read_csv(f"{OUT}/skipped.csv")
    else:
        res, skipped = pass3(L)
        res.to_csv(f"{OUT}/leg_results.csv", index=False)
        skipped.to_csv(f"{OUT}/skipped.csv", index=False)
        log("pass3 done", len(res), "legs", round(time.time() - t0))
    L["entry_day"] = pd.to_datetime(L["entry_day"])
    MS, LS, surv, inc, CP = report(L, M, res, skipped, F, meta)
    pd.set_option("display.width", 250)
    print(MS[["months", "avg R", "t", "Sharpe/yr", "design avg R", "design t", "check avg R", "check t",
              "holdout avg R", "holdout t", "last3y avg R", "survives"]].round(3).to_string())
    print(CP.round(3).to_string())
    print("survivors:", surv, "inconclusive:", inc)
    log("DONE", round(time.time() - t0))


if __name__ == "__main__":
    main()
