"""Alpha hunt, family `fx_carry`: G8 cross-sectional FX carry with crash-risk switches (VIX, FX vol, trend)
and dollar carry. Spec fixed BEFORE running; nothing below was chosen from the data.

Literature: Fama 1984 (forward premium puzzle: UIP fails); Lustig, Roussanov & Verdelhan 2011 RFS (carry factor)
and 2014 JFE (dollar carry); Brunnermeier, Nagel & Pedersen 2008 (carry crashes, funding liquidity);
Menkhoff, Sarno, Schmeling & Schrimpf 2012 JF (global FX vol prices carry); Daniel, Hodrick & Lu 2017.
Idea: high-yielders earn the rate gap (swap); the premium pays for crash risk, so gates on VIX, FX vol and
trend try to sidestep the unwinds (2015-08, 2020-03, 2024-08).

RATES FOR THE SIGNAL
  BIS WS_CBPOL daily policy rates (data/extra/policy_rates_bis_daily.csv; REF_AREA US, JP, GB, CH, AU, CA, NZ;
  TIME_PERIOD, OBS_VALUE). EUR = ECB deposit facility rate (data/extra/ecb_deposit_rate_daily.csv), which anchored
  EONIA/ESTR 2014-2022. Rate of a currency = last non-missing observation dated <= signal day - 1 calendar day.
  (BIS has no JP observation 2013-04-04 .. 2016-09-20 (BoJ monetary-base targeting); the rule then carries the
  last value, 0.05, forward. JPY is a bottom-3 currency in that window either way.)

SCHEDULE (UTC)
  Signal day = last weekday of each month (Dec 25 and Jan 1 excluded: step back to the previous weekday).
  Entry = market order at the 07:00 UTC minute open on the first weekday of the next month (Jan 1 excluded).
  Time exit at the 07:00 UTC minute of the following month's entry day (exit_by_i = that index); the new
  month's legs enter at the same minute.
  SPEC FIX (impossibility): a minute with vol == 0 has no real price, so "the 07:00 minute" of a pair is the first
  minute with vol > 0 in [07:00, 08:00) UTC of that day (normally 07:00 itself); none -> that pair has no
  entry/exit that month (leg skipped, counted in the report). The same index is used for the previous month's
  time exit and the new entry, so the two still coincide.
  SL = 3.0 x ATR20 (daily_table atr20 of the entry day's NY session, shifted = known before the day). No TP.
  A stopped leg stays flat until the next rebalance.
  R per leg = gjstrat.accounting.account(trades of that pair sorted by (exit_i, entry_i), m, 10_000, commission=7,
  swap=SwapModel.from_fred('rates', 1.0), sym=sym, slippage_pips=0.2)['R'] -> swap (the carry income) is inside R.
  (R is independent of the account balance: commission, slippage and swap all scale with lots.)

PORTFOLIO RULE
  Rank the 8 currencies (AUD CAD CHF EUR GBP JPY NZD USD) by rate, ties alphabetical (order = sort by
  (-rate, code)). Long the top-k, short the bottom-k. Trade every top x bottom cross in its quoted form among the
  28 pairs (long AUD / short JPY = AUDJPY BUY; long NZD / short EUR = EURNZD SELL), 1R per leg.
  Monthly portfolio R = mean R of that month's legs. A flat month (rule leaves no legs) = 0 and is included.
  Month = entry month (the period of a month is its entry date: design 2010-17, check 2018-23, holdout 2024-26).
  Warm-up: a month is left out of a variant's series (not counted as flat) when an input that variant needs is
  not yet defined (ATR20 of an entry day; 63 closes; 250-day median; 252 previous VIX/FXVOL values). A month whose
  exit is after the data end (Oct 2026) is left out. A month with legs but none simulated is left out (counted).

VARIANTS (10; candidates C1-C9, C10 is a cost sensitivity, not a candidate)
  C1: k=2 (4 crosses).
  C2: k=1 (1 cross).
  C3: k=3 (9 crosses).
  C4: C1, keeping only legs whose rate gap (long rate - short rate) >= 1.0 pp.
  C5: C1, flat for the month if VIXCLS (last value dated <= signal day - 1) > the 80th percentile
      (numpy linear) of its previous 252 values.
  C6: C1, flat if FXVOL > the 80th percentile of its previous 252 daily values. FXVOL on a date = mean over the
      28 pairs (those with a value) of the 20-day std of daily_table close-to-close log returns; value at the
      signal day = last FXVOL dated <= signal day (the signal day's NY close is before the 07:00 UTC entry).
  C7: C1, keeping a leg only if the pair's 63-trading-day spot log return (signal-day close vs 63 daily_table
      closes earlier) in the carry direction is > 0 (carry + trend).
  C8: C7, and also the pair's 20-day realized vol (std of 20 daily log returns at the signal day) < its trailing
      250-day median (rolling 250 values ending at the signal day).
  C9: dollar carry (LRV 2014): BUY the 7 foreign currencies vs USD (EURUSD/GBPUSD/AUDUSD/NZDUSD BUY,
      USDJPY/USDCHF/USDCAD SELL) if the mean foreign rate > the US rate, else the reverse. 7 legs.
  C10: C1 with SwapModel.from_fred('rates', 2.5) (prop-broker swap markup). Cost sensitivity, not a candidate.

SURVIVAL (charter, applied to the MONTHLY PORTFOLIO R series): design t >= 2 AND avg R > 0 in check AND in holdout.
9 candidates -> about 9 x 0.006 = 0.05 survivors expected by luck. A narrow design miss with positive later
periods is reported as inconclusive, not negative.

REPORT: monthly portfolio R per period with t; leg-level stats (trades, trades/month, win %, avg win / avg loss,
avg R and t per period, last 3 years = entries after 2023-10-07); R split into price (spot incl. spread),
cost (commission + slippage) and swap; pooled legs across C1-C8; currencies held by year; worst single day in %
at 0.25% risk per leg (mark-to-market on NY 17:00 closes: bid close for longs, ask close for shorts; costs and
swap booked on the exit day); results in 2015-08, 2020-03, 2024-08; correlation of the C1 monthly R with the
monthly result of the run_m3_addon.build_legs() basket (if time allows; `--basket`).

COMPUTE: pass 1 loads each of the 28 pairs once, computes daily_table (close, atr20, end_i), caches it to
results/alpha_hunt/fx_carry/daily.csv, then del. Pass 2 builds every variant's legs from the cache. Pass 3 loads
each traded pair once, simulates and accounts all its unique legs (sym, month, side) for every variant, then del.
One market in memory at a time; no multiprocessing.

    python run_alpha_fx_carry.py            # passes 1-3 + report
    python run_alpha_fx_carry.py --basket   # basket monthly R for the correlation (cached), then report
    python run_alpha_fx_carry.py --report   # report only, from the caches
"""
import gc
import os
import sys
import time

import numpy as np
import pandas as pd

from gjstrat.accounting import LOT, account
from gjstrat.data import MAJORS, MINORS, load_market
from gjstrat.patterns import NY, Signal, daily_table, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_edge_hunt import PER
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/fx_carry"
DATA = "data/{}_2010-01-01_2026-10-07.npz"
PAIRS = MAJORS + MINORS
CCYS = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
BIS_AREA = {"US": "USD", "JP": "JPY", "GB": "GBP", "CH": "CHF", "AU": "AUD", "CA": "CAD", "NZ": "NZD"}
LAST3 = pd.Timestamp("2023-10-07")
LEG_RISK = 0.25
SL_ATR = 3.0
EPISODES = ["2015-08", "2020-03", "2024-08"]
VARIANTS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
CANDIDATES = VARIANTS[:9]
NAMES = {"C1": "C1 carry k=2 (4 crosses)", "C2": "C2 carry k=1", "C3": "C3 carry k=3 (9 crosses)",
         "C4": "C4 C1, rate gap >= 1pp", "C5": "C5 C1, VIX gate", "C6": "C6 C1, FXVOL gate",
         "C7": "C7 C1 + 63d trend", "C8": "C8 C7 + vol < median", "C9": "C9 dollar carry (7 USD pairs)",
         "C10": "C10 C1, swap markup 2.5 (cost check)"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def quoted(a, b):
    """(sym, side) that is long currency a, short currency b."""
    if a + b in PAIRS:
        return a + b, "BUY"
    if b + a in PAIRS:
        return b + a, "SELL"
    raise ValueError(a + b)


def first_weekday(y, mo):
    d = pd.Timestamp(y, mo, 1)
    while d.dayofweek >= 5 or (d.month == 1 and d.day == 1):
        d += pd.Timedelta(days=1)
    return d


def last_weekday(y, mo):
    d = pd.Timestamp(y, mo, 1) + pd.offsets.MonthEnd(0)
    while d.dayofweek >= 5 or (d.month == 12 and d.day == 25) or (d.month == 1 and d.day == 1):
        d -= pd.Timedelta(days=1)
    return d


def ny_label(ts):
    return (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def period_of(day):
    for p, (a, b) in PER.items():
        if pd.Timestamp(a) <= day <= pd.Timestamp(b):
            return p
    return None


# ----------------------------------------------------------------------------------------------- pass 1
def pass1():
    path = f"{OUT}/daily.csv"
    if os.path.exists(path) and os.path.exists(f"{OUT}/meta.csv"):
        return pd.read_csv(path, parse_dates=["date"]), pd.read_csv(f"{OUT}/meta.csv").set_index("sym")
    rows, meta = [], []
    for sym in PAIRS:
        m = load_market(DATA.format(sym.lower()))
        d = daily_table(m)
        rows.append(pd.DataFrame({"sym": sym, "date": d.index, "close": d["close"].to_numpy(),
                                  "atr20": d["atr20"].to_numpy(), "end_i": d["end_i"].to_numpy()}))
        meta.append({"sym": sym, "t0": str(m.t0), "n": m.n, "pip": m.pip, "last_ts": str(m.ts(m.n - 1))})
        log("pass1", sym, len(d))
        del m, d
        gc.collect()
    daily = pd.concat(rows, ignore_index=True)
    daily.to_csv(path, index=False)
    meta = pd.DataFrame(meta).set_index("sym")
    meta.to_csv(f"{OUT}/meta.csv")
    return daily, meta


# ----------------------------------------------------------------------------------------------- pass 2
def load_rates():
    b = pd.read_csv("data/extra/policy_rates_bis_daily.csv", usecols=["REF_AREA", "TIME_PERIOD", "OBS_VALUE"])
    out = {}
    for area, ccy in BIS_AREA.items():
        x = b[b.REF_AREA == area].dropna(subset=["OBS_VALUE"])
        out[ccy] = pd.Series(x.OBS_VALUE.to_numpy(float), index=pd.to_datetime(x.TIME_PERIOD)).sort_index()
    e = pd.read_csv("data/extra/ecb_deposit_rate_daily.csv", usecols=["TIME_PERIOD", "OBS_VALUE"]).dropna()
    out["EUR"] = pd.Series(e.OBS_VALUE.to_numpy(float), index=pd.to_datetime(e.TIME_PERIOD)).sort_index()
    return out


def last_before(s, day):
    """Value of the last observation dated <= day (NaN if none) and its position."""
    k = s.index.searchsorted(day, side="right") - 1
    return (s.iloc[k], k) if k >= 0 else (np.nan, -1)


def pctl_gate(s, day, n=252, q=80):
    """(value, q-th percentile of the previous n values) for the last observation dated <= day."""
    v, k = last_before(s, day)
    if k < n:
        return v, np.nan
    return v, float(np.percentile(s.iloc[k - n:k].to_numpy(), q))


def features(daily):
    close = {s: g.set_index("date")["close"] for s, g in daily.groupby("sym")}
    atr = {s: g.set_index("date")["atr20"] for s, g in daily.groupby("sym")}
    lr = {s: np.log(c).diff() for s, c in close.items()}
    vol20 = {s: x.rolling(20).std() for s, x in lr.items()}
    med250 = {s: v.rolling(250).median() for s, v in vol20.items()}
    ret63 = {s: np.log(c / c.shift(63)) for s, c in close.items()}
    fxvol = pd.DataFrame(vol20).mean(axis=1, skipna=True).dropna()
    vix = pd.read_csv("data/extra/VIXCLS.csv", parse_dates=["observation_date"])
    vix = pd.Series(pd.to_numeric(vix.VIXCLS, errors="coerce").to_numpy(), index=vix.observation_date).dropna()
    return dict(close=close, atr=atr, vol20=vol20, med250=med250, ret63=ret63, fxvol=fxvol, vix=vix)


def asof(s, day):
    """Last value of a daily series dated <= day (NaN if none or if that value is NaN)."""
    k = s.index.searchsorted(day, side="right") - 1
    return float(s.iloc[k]) if k >= 0 else np.nan


def pass2(daily, meta):
    F = features(daily)
    rates = load_rates()
    data_end = pd.Timestamp(meta["last_ts"].min())
    legs, mon = [], []
    months = pd.period_range("2010-01", "2026-10", freq="M")
    for p in months:
        prev, nxt = p - 1, p + 1
        sig = last_weekday(prev.year, prev.month)
        entry = first_weekday(p.year, p.month)
        nxt_entry = first_weekday(nxt.year, nxt.month)
        r = {c: last_before(rates[c], sig - pd.Timedelta(days=1))[0] for c in CCYS}
        order = sorted(CCYS, key=lambda c: (-r[c], c))
        vix_v, vix_p = pctl_gate(F["vix"], sig - pd.Timedelta(days=1))
        fx_v, fx_p = pctl_gate(F["fxvol"], sig)
        mf = np.mean([r[c] for c in CCYS if c != "USD"])
        row = dict(month=str(p), signal_day=sig.date(), entry_day=entry.date(), next_entry=nxt_entry.date(),
                   order=" > ".join(order), vix=vix_v, vix_p80=vix_p, fxvol=fx_v, fxvol_p80=fx_p,
                   mean_foreign=mf, usd=r["USD"], **{f"r_{c}": r[c] for c in CCYS})
        complete = nxt_entry + pd.Timedelta(hours=8) < data_end
        cand = {}

        def cross(k):
            return [(L, S) for L in order[:k] for S in order[-k:]]

        def mk(L, S):
            sym, side = quoted(L, S)
            sgn = 1 if side == "BUY" else -1
            return dict(sym=sym, side=side, long=L, short=S, gap=r[L] - r[S], atr=asof(F["atr"][sym], entry),
                        trend=sgn * asof(F["ret63"][sym], sig), vol20=asof(F["vol20"][sym], sig),
                        med250=asof(F["med250"][sym], sig))

        c1 = [mk(L, S) for L, S in cross(2)]
        cand["C1"] = (c1, None)
        cand["C2"] = ([mk(L, S) for L, S in cross(1)], None)
        cand["C3"] = ([mk(L, S) for L, S in cross(3)], None)
        cand["C4"] = ([x for x in c1 if x["gap"] >= 1.0 - 1e-9], None)
        cand["C5"] = ([] if vix_v > vix_p else c1, np.isnan(vix_p) or np.isnan(vix_v))
        cand["C6"] = ([] if fx_v > fx_p else c1, np.isnan(fx_p) or np.isnan(fx_v))
        cand["C7"] = ([x for x in c1 if x["trend"] > 0], any(np.isnan(x["trend"]) for x in c1))
        cand["C8"] = ([x for x in c1 if x["trend"] > 0 and x["vol20"] < x["med250"]],
                      any(np.isnan(x["trend"]) or np.isnan(x["vol20"]) or np.isnan(x["med250"]) for x in c1))
        long_foreign = mf > r["USD"]
        c9 = [mk(c, "USD") if long_foreign else mk("USD", c) for c in CCYS if c != "USD"]
        cand["C9"] = (c9, None)
        cand["C10"] = (c1, None)
        row["c9_long_foreign"] = long_foreign
        base_need = {"C1": c1, "C2": cand["C2"][0], "C3": cand["C3"][0], "C4": c1, "C5": c1, "C6": c1, "C7": c1,
                     "C8": c1, "C9": c9, "C10": c1}
        for v in VARIANTS:
            lv, warm = cand[v]
            warm = bool(warm) or any(np.isnan(x["atr"]) for x in base_need[v])
            status = "incomplete" if not complete else ("warmup" if warm else "ok")
            row[f"{v}_status"] = status
            row[f"{v}_legs"] = len(lv)
            for x in lv:
                legs.append(dict(variant=v, month=str(p), entry_day=entry, next_entry=nxt_entry, status=status, **x))
        mon.append(row)
    return pd.DataFrame(legs), pd.DataFrame(mon).set_index("month")


# ----------------------------------------------------------------------------------------------- pass 3
def pass3(L, daily, meta):
    sw1, sw25 = SwapModel.from_fred("rates", 1.0), SwapModel.from_fred("rates", 2.5)
    todo = L[L.status != "incomplete"][["sym", "month", "side", "entry_day", "next_entry", "atr"]] \
        .drop_duplicates(["sym", "month", "side"])
    res, mtm, skipped = [], [], []
    for sym, g in todo.groupby("sym"):
        m = load_market(DATA.format(sym.lower()))
        dd = daily[daily.sym == sym]
        e_i, e_day = dd["end_i"].to_numpy(), pd.DatetimeIndex(dd["date"])

        def T(day):
            i0 = m.idx(day + pd.Timedelta(hours=7))
            if i0 < 0 or i0 >= m.n:
                return None
            w = np.flatnonzero(m.vol[i0:i0 + 60] > 0)
            return int(i0 + w[0]) if len(w) else None

        trades, keys = [], []
        for x in g.itertuples(index=False):
            ei, xi = T(x.entry_day), T(x.next_entry)
            if ei is None or xi is None or np.isnan(x.atr):
                skipped.append(dict(sym=sym, month=x.month, side=x.side, why="no live minute 07:00-08:00 UTC"
                                    if (ei is None or xi is None) else "no ATR"))
                continue
            s = Signal(x.entry_day, x.side, ei, "market", None, ei + 1, SL_ATR * x.atr, None, xi, x.month)
            t = simulate(m, s)
            if t is None:
                skipped.append(dict(sym=sym, month=x.month, side=x.side, why="simulate None"))
                continue
            trades.append(t)
            keys.append(x.month)
        if not trades:
            del m
            gc.collect()
            continue
        order = sorted(range(len(trades)), key=lambda k: (trades[k].exit_i, trades[k].entry_i))
        trades, keys = [trades[k] for k in order], [keys[k] for k in order]
        logs = {}
        for name, sw in (("1", sw1), ("25", sw25)):
            lg = account(trades, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)
            logs[name] = lg.set_index(["entry_i", "exit_i", "side"])
        for t, mo in zip(trades, keys):
            k = (t.entry_i, t.exit_i, t.side)
            a1, a25 = logs["1"].loc[k], logs["25"].loc[k]
            risk_usd = a1["lots"] * t.risk * LOT / m.quote_per_usd[t.entry_i]
            swapR = a1["swap_usd"] / risk_usd
            swapR25 = a25["swap_usd"] / risk_usd
            R, R25 = float(a1["R"]), float(a25["R"])
            res.append(dict(sym=sym, month=mo, side=t.side, entry_i=t.entry_i, exit_i=t.exit_i,
                            entry_ts=m.ts(t.entry_i), exit_ts=m.ts(t.exit_i), reason=t.reason,
                            sl_pips=t.risk / m.pip, spread_pips=t.spread / m.pip, priceR=t.r,
                            swapR=swapR, costR=t.r + swapR - R, R=R, swapR25=swapR25, R25=R25,
                            nights=int(a1["swap_nights"]),
                            entry_live_at_0700=bool(t.entry_i == m.idx(t.day + pd.Timedelta(hours=7)))))
            # mark-to-market on NY closes strictly inside the trade
            sel = (e_i > t.entry_i) & (e_i < t.exit_i)
            sgn = 1 if t.side == "BUY" else -1
            mark = m.bc if t.side == "BUY" else m.ac
            path = sgn * (mark[e_i[sel] - 1] - t.entry) / t.risk
            dates = list(e_day[sel])
            prev = np.concatenate([[0.0], path[:-1]])
            last = path[-1] if len(path) else 0.0
            xd = ny_label(m.ts(t.exit_i))
            lid = f"{sym}|{mo}|{t.side}"
            for dt, a, b in zip(dates, path, prev):
                mtm.append((lid, dt, a - b, a - b))
            mtm.append((lid, xd, R - last, R25 - last))
        log("pass3", sym, len(trades), "legs")
        del m, logs
        gc.collect()
    res = pd.DataFrame(res)
    mtm = pd.DataFrame(mtm, columns=["leg", "date", "dR", "dR25"])
    return res, mtm, pd.DataFrame(skipped, columns=["sym", "month", "side", "why"])


# ----------------------------------------------------------------------------------------------- stats
def leg_summary(r, day, nmonths):
    r, day = np.asarray(r, float), pd.DatetimeIndex(day)
    win, loss = r[r > 0], r[r <= 0]
    out = {"trades": len(r), "trades/month": len(r) / nmonths if nmonths else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win/avg loss": win.mean() / -loss.mean() if len(win) and len(loss) and loss.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r)}
    for p, (a, b) in PER.items():
        v = r[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))]
        out[f"{p} n"], out[f"{p} avg R"], out[f"{p} t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
    v = r[day > LAST3]
    out["last3y n"], out["last3y avg R"], out["last3y t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
    return out


def month_summary(s):
    """s: monthly portfolio R indexed by month entry date."""
    day = pd.DatetimeIndex(s.index)
    r = s.to_numpy(float)
    out = {"months": len(r), "flat %": (r == 0).mean() * 100 if len(r) else np.nan,
           "avg R": r.mean(), "t": tstat(r), "Sharpe/yr": r.mean() / r.std(ddof=1) * np.sqrt(12) if len(r) > 1 else np.nan,
           "win months %": (r > 0).mean() * 100}
    for p, (a, b) in PER.items():
        v = r[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))]
        out[f"{p} n"], out[f"{p} avg R"], out[f"{p} t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
    v = r[day > LAST3]
    out["last3y n"], out["last3y avg R"], out["last3y t"] = len(v), v.mean() if len(v) else np.nan, tstat(v)
    return out


def variant_legs(L, res, v):
    lv = L[(L.variant == v) & (L.status == "ok")]
    j = lv.merge(res, on=["sym", "month", "side"], how="left")
    if v == "C10":
        j["R"], j["swapR"] = j["R25"], j["swapR25"]
        j["costR"] = j["priceR"] + j["swapR"] - j["R"]
    return j


def monthly_series(L, M, res, v):
    ok = M.index[M[f"{v}_status"] == "ok"]
    j = variant_legs(L, res, v)
    g = j.groupby("month")["R"]
    out, dropped = {}, []
    for mo in ok:
        nlegs = M.loc[mo, f"{v}_legs"]
        if nlegs == 0:
            out[mo] = 0.0
        elif mo in g.groups and g.get_group(mo).notna().any():
            out[mo] = g.get_group(mo).mean()
        else:
            dropped.append(mo)
    s = pd.Series(out, dtype=float)
    s.index = pd.DatetimeIndex([pd.Timestamp(M.loc[mo, "entry_day"]) for mo in s.index])
    return s.sort_index(), dropped


# ----------------------------------------------------------------------------------------------- basket
def basket():
    path = f"{OUT}/basket_monthly.csv"
    if os.path.exists(path):
        return pd.read_csv(path, index_col=0)
    from run_m3_addon import build_legs
    m, legs = build_legs()
    w = (0.25, 3, 0.5, 3, 0)      # Alpha basket: vol-box 0.25%, vol-gotobi 3%, fade 0.5%, M-3 USDJPY 3%
    rows = []
    for k, (tr, r) in enumerate(legs):
        for t, x in zip(tr, r):
            rows.append(dict(month=pd.Timestamp(t.day).strftime("%Y-%m"), leg=k, R=x, pct=x * w[k]))
    b = pd.DataFrame(rows)
    out = pd.DataFrame({"pct": b.groupby("month")["pct"].sum(), "sumR_legs0to3": b[b.leg < 4].groupby("month")["R"].sum()})
    out.to_csv(path)
    del m, legs
    gc.collect()
    return out


# ----------------------------------------------------------------------------------------------- report
def report(L, M, res, mtm, skipped):
    res = res.copy()
    S, MS, legstats, split, series, drops = [], [], [], [], {}, {}
    for v in VARIANTS:
        s, dropped = monthly_series(L, M, res, v)
        series[v], drops[v] = s, dropped
        j = variant_legs(L, res, v).dropna(subset=["R"])
        ms = month_summary(s)
        ms["first month"] = s.index.min().strftime("%Y-%m") if len(s) else ""
        surv = (v in CANDIDATES and ms["design t"] >= 2 and ms["check avg R"] > 0 and ms["holdout avg R"] > 0)
        ms["survives"] = "YES" if surv else ("n/a" if v not in CANDIDATES else "no")
        MS.append(pd.Series(ms, name=NAMES[v]))
        days = pd.DatetimeIndex(j["entry_day"])
        legstats.append(pd.Series(leg_summary(j["R"], days, len(s)), name=NAMES[v]))
        sp = {}
        for p, (a, b) in list(PER.items()) + [("all", ("2000-01-01", "2030-01-01"))]:
            q = j[(days >= pd.Timestamp(a)) & (days <= pd.Timestamp(b))]
            sp[f"{p} price R"], sp[f"{p} cost R"], sp[f"{p} swap R"], sp[f"{p} net R"] = \
                q.priceR.mean(), -q.costR.mean(), q.swapR.mean(), q.R.mean()
        split.append(pd.Series(sp, name=NAMES[v]))
    MS, legstats, split = pd.DataFrame(MS), pd.DataFrame(legstats), pd.DataFrame(split)
    MS.index.name = legstats.index.name = split.index.name = "variant"
    MS.to_csv(f"{OUT}/monthly_summary.csv")
    legstats.to_csv(f"{OUT}/leg_summary.csv")
    split.to_csv(f"{OUT}/swap_split.csv")
    pd.DataFrame(series).to_csv(f"{OUT}/monthly_R.csv")

    # common window (all variants defined)
    start = max(s.index.min() for s in series.values())
    CW = pd.DataFrame([pd.Series(month_summary(series[v][series[v].index >= start]), name=NAMES[v])
                       for v in VARIANTS])
    CW.index.name = "variant"

    # pooled legs C1-C8 (with duplicates) and unique legs
    pool = pd.concat([variant_legs(L, res, v).dropna(subset=["R"]) for v in VARIANTS[:8]])
    uniq = pool.drop_duplicates(["sym", "month", "side"])
    nmon = len(series["C1"])
    P = pd.DataFrame([pd.Series(leg_summary(pool.R, pool.entry_day, nmon), name="pooled C1-C8 legs (dups kept)"),
                      pd.Series(leg_summary(uniq.R, uniq.entry_day, nmon), name="unique legs in C1-C8")])
    P.index.name = "pool"
    # pooled by pair (unique legs)
    BP = uniq.groupby("sym").apply(lambda q: pd.Series({"legs": len(q), "avg R": q.R.mean(), "t": tstat(q.R),
                                                         "swap R": q.swapR.mean(), "win %": (q.R > 0).mean() * 100}))
    BP.index.name = "pair"
    npos = int((BP["avg R"] > 0).sum())

    # currencies held by year (C1, C2, C3)
    held = []
    for v in ("C2", "C1", "C3"):
        lv = L[(L.variant == v) & (L.status == "ok")].copy()
        lv["year"] = pd.DatetimeIndex(lv.entry_day).year
        a = lv.drop_duplicates(["month", "long"]).groupby(["year", "long"]).size().unstack(fill_value=0)
        b = lv.drop_duplicates(["month", "short"]).groupby(["year", "short"]).size().unstack(fill_value=0)
        t = pd.DataFrame(index=sorted(set(a.index) | set(b.index)))
        for c in CCYS:
            la = a[c] if c in a else pd.Series(dtype=int)
            sb = b[c] if c in b else pd.Series(dtype=int)
            t[c] = [f"L{int(la.get(y, 0))}/S{int(sb.get(y, 0))}" if (la.get(y, 0) or sb.get(y, 0)) else "" for y in t.index]
        t.index.name = f"{v} year"
        held.append(t)

    # worst day and episodes (MTM, 0.25% per leg)
    mtm = mtm.copy()
    mtm["date"] = pd.to_datetime(mtm["date"])
    WD, EP, dailyp = [], [], {}
    for v in VARIANTS:
        j = variant_legs(L, res, v).dropna(subset=["R"])
        ids = set(j.sym + "|" + j.month + "|" + j.side)
        q = mtm[mtm.leg.isin(ids)]
        col = "dR25" if v == "C10" else "dR"
        d = q.groupby("date")[col].sum() * LEG_RISK
        dailyp[v] = d
        mpct = j.groupby("month")["R"].sum() * LEG_RISK
        eq = mpct.cumsum()
        dd = (eq - eq.cummax()).min()
        WD.append(pd.Series({"worst day %": d.min(), "worst day": d.idxmin().date() if len(d) else None,
                             "2nd worst day %": d.nsmallest(2).iloc[-1] if len(d) > 1 else np.nan,
                             "days < -1%": int((d < -1).sum()), "best day %": d.max(),
                             "worst month %": mpct.min(), "worst month": mpct.idxmin() if len(mpct) else None,
                             "max DD % (monthly closes)": dd,
                             "total %": mpct.sum()}, name=NAMES[v]))
        for e in EPISODES:
            jj = j[j.month == e]
            de = d[(d.index >= pd.Timestamp(e + "-01")) & (d.index <= pd.Timestamp(e + "-01") + pd.offsets.MonthEnd(0))]
            st = M.loc[e, f"{v}_status"]
            EP.append(dict(variant=NAMES[v], month=e, status=st, legs=len(jj),
                           pairs=" ".join(f"{a}{'+' if b == 'BUY' else '-'}" for a, b in zip(jj.sym, jj.side)),
                           stopped=int((jj.reason == "SL").sum()),
                           monthR=series[v].get(pd.Timestamp(M.loc[e, "entry_day"]), np.nan),
                           month_pct=jj.R.sum() * LEG_RISK,
                           worst_day_pct=de.min() if len(de) else np.nan,
                           worst_day=de.idxmin().date() if len(de) and de.min() < 0 else None))
    WD = pd.DataFrame(WD)
    WD.index.name = "variant"
    EP = pd.DataFrame(EP).set_index("variant")
    WD.to_csv(f"{OUT}/worst_day.csv")
    EP.to_csv(f"{OUT}/episodes.csv")
    pd.DataFrame(dailyp).to_csv(f"{OUT}/daily_pct_mtm.csv")

    # yearly monthly-R table
    Y = pd.DataFrame({NAMES[v].split(" ")[0]: series[v].groupby(series[v].index.year).sum() for v in VARIANTS})
    Y.index.name = "year (sum of monthly R)"

    # gates
    ok = M[M.C1_status == "ok"]
    G = pd.DataFrame({"months C1 ok": [len(ok)],
                      "C5 VIX-gated flat": [int(((M.C5_status == "ok") & (M.C5_legs == 0)).sum())],
                      "C6 FXVOL-gated flat": [int(((M.C6_status == "ok") & (M.C6_legs == 0)).sum())],
                      "C4 flat (no gap >= 1pp)": [int(((M.C4_status == "ok") & (M.C4_legs == 0)).sum())],
                      "C7 flat": [int(((M.C7_status == "ok") & (M.C7_legs == 0)).sum())],
                      "C8 flat": [int(((M.C8_status == "ok") & (M.C8_legs == 0)).sum())],
                      "C9 long-foreign months": [int(ok.c9_long_foreign.sum())]}, index=["count"])
    # gated vs not gated C1 months
    c1 = series["C1"]
    gate_tab = []
    for v, nm in (("C5", "VIX gate"), ("C6", "FXVOL gate")):
        okv = M[M[f"{v}_status"] == "ok"]
        on = [pd.Timestamp(okv.loc[mo, "entry_day"]) for mo in okv.index if okv.loc[mo, f"{v}_legs"] == 0]
        off = [pd.Timestamp(okv.loc[mo, "entry_day"]) for mo in okv.index if okv.loc[mo, f"{v}_legs"] > 0]
        a, b = c1.reindex(on).dropna(), c1.reindex(off).dropna()
        gate_tab.append(dict(gate=nm, **{"gated months n": len(a), "C1 avg R gated": a.mean(), "gated t": tstat(a),
                                         "open months n": len(b), "C1 avg R open": b.mean(), "open t": tstat(b)}))
    gate_tab = pd.DataFrame(gate_tab).set_index("gate")

    # basket correlation
    corr_txt = "Basket correlation not computed (run `python run_alpha_fx_carry.py --basket`)."
    if os.path.exists(f"{OUT}/basket_monthly.csv"):
        b = pd.read_csv(f"{OUT}/basket_monthly.csv", index_col=0)
        c1m = pd.Series(c1.to_numpy(), index=c1.index.strftime("%Y-%m"))
        jn = pd.concat([c1m.rename("C1"), b], axis=1, join="inner").fillna(0)
        rows = []
        for lab, a in (("all common months", None), ("since 2018-01", "2018-01")):
            q = jn if a is None else jn[jn.index >= a]
            rows.append({"window": lab, "months": len(q), "corr C1 vs basket %": q["C1"].corr(q["pct"]),
                         "corr C1 vs basket sum R": q["C1"].corr(q["sumR_legs0to3"])})
        corr_txt = ("Basket = run_m3_addon.build_legs(), Alpha mix vol-box 0.25% + vol-gotobi 3% + fade 0.5% + "
                    "M-3 USDJPY 3% (monthly % by entry month); also the plain monthly sum of R of those 4 legs. "
                    "Months without basket trades count as 0.\n\n" + fmt_table(pd.DataFrame(rows).set_index("window"), ".3f"))

    # write
    cand = MS.loc[[NAMES[v] for v in CANDIDATES]]
    survivors = list(cand.index[cand.survives == "YES"])
    mcols = ["first month", "months", "flat %", "avg R", "t", "Sharpe/yr", "design n", "design avg R", "design t",
             "check n", "check avg R", "check t", "holdout n", "holdout avg R", "holdout t", "last3y avg R",
             "last3y t", "survives"]
    lcols = ["trades", "trades/month", "win %", "avg win/avg loss", "avg R", "t", "design avg R", "design t",
             "check avg R", "check t", "holdout avg R", "holdout t", "last3y n", "last3y avg R", "last3y t"]
    skipped_txt = "none" if skipped is None or len(skipped) == 0 else \
        fmt_table(skipped.groupby(["why"]).size().rename("legs").to_frame(), ".0f")
    drop_txt = ", ".join(f"{v}: {len(d)}" for v, d in drops.items() if d) or "none"
    entry_late = int((~res.entry_live_at_0700).sum()) if "entry_live_at_0700" in res else 0
    txt = ["# Alpha hunt: fx_carry (G8 cross-sectional FX carry with crash-risk switches, dollar carry)\n",
           "Spec fixed before running: see the docstring of `run_alpha_fx_carry.py` (rates = BIS policy rates, EUR = ECB "
           "deposit rate, dated <= signal day - 1; signal = last weekday of the month; entry/exit 07:00 UTC first weekday; "
           "SL 3 x ATR20, no TP; costs $7/lot, 0.2 pip slippage per stop fill, swap from FRED rates with 1.0%/yr markup "
           "(C10: 2.5%), so the carry income is inside R).\n",
           f"Survival bar (on the monthly portfolio R series): design t >= 2 AND avg R > 0 in check AND in holdout. "
           f"9 candidates (C1-C9) -> ~{9 * 0.006:.2f} survivors expected by luck.\n",
           f"**Survivors: {', '.join(survivors) if survivors else 'none'}.**\n",
           "## Monthly portfolio R (mean R of the month's legs; flat month = 0)\n",
           fmt_table(MS[mcols], ".3f"),
           "\nWarm-up months are left out per variant (first month column). Months with legs but no simulated trade "
           f"(left out): {drop_txt}. Legs skipped: {skipped_txt}. Entries/exits moved past a dead 07:00 minute: "
           f"{entry_late} of {len(res)} legs.\n",
           "\n### Same table on the common window (all variants defined, from " + start.strftime("%Y-%m") + ")\n",
           fmt_table(CW[mcols[1:-1]], ".3f"),
           "\n## Leg-level stats (each leg = one cross held a month or until its 3xATR stop)\n",
           fmt_table(legstats[lcols], ".3f"),
           "\n## R split per leg: price (spot move incl. spread) + cost (commission + slippage) + swap = net\n",
           fmt_table(split, ".3f"),
           "\n## Pooled legs\n", fmt_table(P[lcols], ".3f"),
           f"\nUnique C1-C8 legs by pair ({npos} of {len(BP)} pairs with avg R > 0):\n",
           fmt_table(BP.sort_values("legs", ascending=False), ".3f"),
           "\n## Gates\n", fmt_table(G, ".0f"), "\n", fmt_table(gate_tab, ".3f"),
           "\n## Worst single day (MTM on NY closes, 0.25% risk per leg)\n",
           "C1 runs 4 legs = 1% total risk; C3 9 legs = 2.25%; C9 7 legs = 1.75%.\n\n",
           fmt_table(WD, ".2f"),
           "\n## Crash months (legs entered the first weekday of the month)\n",
           fmt_table(EP, ".3f"),
           "\n## Sum of monthly R by year\n", fmt_table(Y, ".2f"),
           "\n## Currencies held (months long L / short S per year)\n"]
    for t in held:
        txt += [fmt_table(t, ".0f"), "\n"]
    txt += ["\n## Correlation with the current prop basket\n", corr_txt, "\n"]
    with open(f"{OUT}/REPORT_tables.md", "w") as f:
        f.write("\n".join(txt))
    return MS, legstats, survivors


# ----------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    daily, meta = pass1()
    assert meta["t0"].nunique() == 1, "pairs on different grids"
    log("pass1 done", round(time.time() - t0))
    if "--basket" in sys.argv:
        basket()
        log("basket done", round(time.time() - t0))
    L, M = pass2(daily, meta)
    L.to_csv(f"{OUT}/legs_plan.csv", index=False)
    M.to_csv(f"{OUT}/months.csv")
    log("pass2 done", len(L), "planned legs", round(time.time() - t0))
    if os.path.exists(f"{OUT}/leg_results.csv") and ("--report" in sys.argv or "--basket" in sys.argv):
        res = pd.read_csv(f"{OUT}/leg_results.csv")
        mtm = pd.read_csv(f"{OUT}/mtm.csv")
        skipped = pd.read_csv(f"{OUT}/skipped.csv")
    else:
        res, mtm, skipped = pass3(L, daily, meta)
        res.to_csv(f"{OUT}/leg_results.csv", index=False)
        mtm.to_csv(f"{OUT}/mtm.csv", index=False)
        skipped.to_csv(f"{OUT}/skipped.csv", index=False)
        log("pass3 done", len(res), "legs", round(time.time() - t0))
    L["entry_day"] = pd.to_datetime(L["entry_day"])
    MS, LS, surv = report(L, M, res, mtm, skipped)
    pd.set_option("display.width", 250)
    print(MS[["months", "avg R", "t", "design avg R", "design t", "check avg R", "check t", "holdout avg R",
              "holdout t", "survives"]].round(3).to_string())
    print("survivors:", surv)
    log("DONE", round(time.time() - t0))


if __name__ == "__main__":
    main()
