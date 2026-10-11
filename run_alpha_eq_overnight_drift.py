"""Alpha hunt family `eq_overnight_drift`: US equity-index overnight drift at the European open
(dealer-inventory channel), unconditional and after US-session selling. Intraday long-only (one hour, or the
European session up to the US pre-open), conditional on the prior US session. Fixed before running.

IDEA: Boyarchenko, Larsen & Whelan (2023 RFS, "The Overnight Drift") find that US index futures earn a large
share of the equity premium in one hour, 02:00-03:00 ET, when European markets open. Mechanism: end-of-day
selling leaves dealers long; they lay that risk off with a price concession when European liquidity
arrives, so the drift is larger after negative US-session returns and close to zero after up days. See also
Lou, Polk & Skouras (2019 JFE). New here: index_meanrev was close-to-close; run_index_anomalies E2 was
close -> 09:35 unconditional (flat). The flow atlas put "Nasdaq London 00:30-08:30" on its watch list
(+3-4 bp, design t 3.7, check t 2.2, holdout t 1.9) but its tradeable check used a 0.25 x ATR20 stop.
The conditional version, the one-hour window and a stop sized for the hold are untested.

MARKETS: USATECHIDXUSD (Nasdaq 100 CFD, minute bid/ask, data/usatechidxusd_2011-01-02_2026-10-07.npz) is
primary and gets the charter bar. USA500IDXUSD (S&P 500, hourly bid candles data/hourly/USA500IDXUSD/*.bi5,
decoded with gjstrat.data.CANDLE_DTYPE as run_index_replication.spx / run_alpha_index_meanrev.spx_bars) is
the replication. Markets are loaded one at a time and deleted. Single process.

CALENDAR: trade morning M = an NYSE trading day (holidays.NYSE, via run_alpha_index_meanrev.calendar). Its
signal session S = the latest NYSE session strictly before M (Monday follows Friday; the morning after a
holiday follows the last session before it). Monday mornings and post-holiday Tue-Fri mornings are reported
separately.

ANCHOR (European open): 08:00 Europe/Berlin on date M (= 02:00 ET except in the weeks when US and EU
daylight saving differ, then 03:00 ET). All times DST-aware via gjstrat.patterns.local_idx.

NASDAQ EXECUTION (minute data):
  ENTRY: market BUY at the open of the first live minute (vol > 0) in [07:55, 08:00) Berlin
    (run_index_anomalies.live_at on the 07:55 Berlin index). If none, no trade that morning.
  EXITS: X1 = open of the 09:00 Berlin minute (one hour, the paper's peak).
         X2 = open of the 09:25 America/New_York minute (rest of the European session, before the US open).
  Stop checked minute by minute with gjstrat.patterns.simulate(Signal(M, 'BUY', i, 'market', None, i + 1,
  sl, None, exit_i, tag)) on real bid/ask. No take-profit.
  ATR20 = gjstrat.patterns.daily_table(m).atr20 of the NY-close day (17:00 NY roll) containing the entry
  minute (shifted, known before the day).

SESSION FEATURES (Nasdaq bid, minute data, all known before entry):
  C_S = bid close of the 15:59 NY minute of S; P15_S = bid close of the 14:59 NY minute of S.
  r_cc(S) = ln(C_S / C_{S-1}) where S-1 = the previous session in the close series; r_lh(S) = ln(C_S / P15_S)
  (last hour). sigma60(S) = sample sd (ddof 1) of the 60 r_cc before S (S excluded).
  A session enters the close series only if its 15:59 NY minute has ticks (vol > 0). r_lh additionally needs
  ticks in the 14:59 NY minute, else r_lh is undefined for that session (ON4 then has no trade) - reading of
  "a session enters only if its signal minutes have ticks", stated before running.
  Data gaps longer than 5 NYSE days split the close series into segments; r_cc and sigma60 are computed
  within a segment (warm-up restarts), as run_alpha_index_meanrev does.
  The conditional variants need S itself in the close series with r_cc (and sigma60 where used) defined;
  otherwise that morning has no conditional trade (no earlier session is substituted). ON1 needs only a live
  entry minute and ATR20.

VARIANTS (7 per market, all long, no TP):
  ON1 every morning,              X1, SL 0.5 x ATR20.
  ON2 r_cc(S) < 0,                X1, SL 0.5 x ATR20.
  ON3 r_cc(S) <= -1.0 sigma60,    X1, SL 0.5 x ATR20.
  ON4 r_lh(S) < 0 (sold into the close), X1, SL 0.5 x ATR20.
  ON5 r_cc(S) < 0,                X2, SL 1.0 x ATR20.
  ON6 r_cc(S) <= -1.0 sigma60,    X2, SL 1.0 x ATR20.
  ON7 falsification control: r_cc(S) > 0, X1, SL 0.5 x ATR20. Theory predicts about 0 and below ON2.

S&P REPLICATION (hourly bid candles; live bars only, v > 0):
  r_cc uses the closes of the 15:00-16:00 NY bar; r_lh = that close vs the 14:00-15:00 NY bar close (needs
  that bar live). Same segment / sigma60 rules on the S&P close series. ATR20 and daily H/L come from live
  hourly bars grouped into 17:00-17:00 NY days (weekday labels), ATR20 = mean(H - L) of the 20 previous
  days (as run_alpha_index_meanrev.run_spx); the day used is the one containing the entry bar.
  Entry = open of the hourly bar starting at 08:00 Berlin (06:00 or 07:00 UTC) + 0.5 pt; that bar must be
  live, else no trade. X1 = close of that bar - 0.5 pt. X2 = close of the bar ending at 09:00 NY (starting
  08:00 NY) - 0.5 pt; if that bar is not live, the last live bar starting at or before 08:00 NY is used
  (obvious-impossibility fix, stated before running). Stop = entry - k x ATR20: if a held bar's bid low <=
  stop, the trade exits at the stop (or at the bar open if it gapped through) - 0.25 pt. Held bars = the
  entry bar (X1) or all live bars from the entry bar to the X2 bar (X2).

COSTS: Nasdaq via run_all_matrix.net_r(m, sym, trades, swap) (bid/ask fills, NON_FX commission 0 and 0.25 pt
slippage, double slippage on stop fills, 3%/yr financing per 17:00 NY rollover). No rollover is crossed, so
financing is 0; the script asserts that (the swap argument is unused for indices and is passed as None).
S&P costs as above (0.5 pt per side + 0.25 pt on stop fills; no financing). R = net P&L / stop distance.
Also reported: gross mid-price return in bp per trade (Nasdaq: fills converted to mid with half the spread of
the fill minute; S&P: bid-to-bid, i.e. without the 0.5 pt adds), cost in bp per trade (= gross - net), and
the median Nasdaq spread in bp at the entry minute (07:55 Berlin) vs at the 10:00 NY minute of the same day.

STATS / SURVIVAL (charter): run_edge_hunt.PER periods (design from the data start: the European-open
minute is live only from about 2013-14, so n per period is reported), check 2018-23, holdout 2024-26.
For every test: trades, trades/month (trades / months with at least one live entry morning), win %,
avg win / avg loss, avg R and t per period, month-clustered t (sum of R per month, zero for months with
data but no trade, t over months), last 3 years (2023-10-08 to 2026-10-07).
  * Nasdaq test survives if design t >= 2 AND avg R > 0 in 2018-23 AND in 2024-26.
  * The S&P replication passes if avg R > 0 over the whole period AND in at least 2 of the 3 periods.
  * The charter bar is also printed for the S&P tests. 14 tests: about 14 x 0.006 = 0.08 survivors by luck.

DIAGNOSTICS: Welch t of the ON2 - ON7 difference in mean R (the conditional channel), overall and per
period, both markets. Avg R by tercile of r_cc(S) on the ON1 trades, tercile cut points fixed on design-period
data (per market). Avg R by year (incl. 2020 and 2022). Monday / post-holiday / other mornings. Overlap of
trade days with index_meanrev MR1 (results/alpha_hunt/index_meanrev/trades.csv: MR1 signal day == our S,
i.e. MR1 is holding during our trade). Correlation of daily R (by 17:00-NY day of exit, zero on days without
a trade, business days of the overlapping span) with the existing basket legs (run_m3_addon.build_legs():
vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 others, and the risk-weighted basket 0.25/3/0.5/3/0 %).
CONTAMINATION: ON1 overlaps the flow-atlas watch-list cell, so it is not independent evidence. Only ON2-ON6
and the ON2 - ON7 gap are new.

IF ANY NASDAQ TEST SURVIVES: gjstrat.prop.prop_table with run_m3_addon.build_legs() plus the new leg at 0.5%
and 1% risk, run_m3_addon.ALPHA rules, normal risk and boost x1.5 (run_prop_risk_rules.make_rule), challenges
started 2011-2025 and 2018-2025. Index trades join the USDJPY grid shifted by (m_index.t0 - m_usdjpy.t0)
minutes, as in run_index_prop.py.

OUTPUT: results/alpha_hunt/eq_overnight_drift/REPORT.md + trades.csv + summary.csv (+ diagnostic csv).

    python run_alpha_eq_overnight_drift.py
"""
from __future__ import annotations

import os
import time
from collections import namedtuple

import numpy as np
import pandas as pd

from gjstrat.data import load_market
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate
from gjstrat.swap import SwapModel
from run_all_matrix import net_r
from run_alpha_index_meanrev import calendar, spx_bars
from run_backtest import fmt_table
from run_edge_hunt import PER, per_stats
from run_index_anomalies import live_at
from run_usdjpy_sl import tstat

OUT = "results/alpha_hunt/eq_overnight_drift"
BER = "Europe/Berlin"
NQ, SP = "USATECHIDXUSD", "USA500IDXUSD"
NQ_PATH = "data/usatechidxusd_2011-01-02_2026-10-07.npz"
NAMES = {NQ: "Nasdaq 100", SP: "S&P 500"}
L3 = (pd.Timestamp("2023-10-08"), pd.Timestamp("2026-10-07"))
GAP = 5
VARIANTS = {  # name: (condition, exit, SL x ATR20, description)
    "ON1": ("all", "X1", 0.5, "every morning, X1, SL 0.5 ATR"),
    "ON2": ("rcc<0", "X1", 0.5, "r_cc < 0, X1, SL 0.5 ATR"),
    "ON3": ("rcc<=-1sig", "X1", 0.5, "r_cc <= -1 sigma60, X1, SL 0.5 ATR"),
    "ON4": ("rlh<0", "X1", 0.5, "r_lh < 0 (last hour down), X1, SL 0.5 ATR"),
    "ON5": ("rcc<0", "X2", 1.0, "r_cc < 0, X2, SL 1.0 ATR"),
    "ON6": ("rcc<=-1sig", "X2", 1.0, "r_cc <= -1 sigma60, X2, SL 1.0 ATR"),
    "ON7": ("rcc>0", "X1", 0.5, "control: r_cc > 0, X1, SL 0.5 ATR"),
}
BASE_MIX = (0.25, 3, 0.5, 3, 0)
LEG_NAMES = ["vol-box", "vol-gotobi", "fade", "M-3 USDJPY", "M-3 others"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def wants(cond, rcc, sig, rlh) -> bool:
    if cond == "all":
        return True
    if cond == "rcc<0":
        return bool(rcc < 0)
    if cond == "rcc<=-1sig":
        return bool(rcc <= -1.0 * sig)                  # NaN -> False
    if cond == "rlh<0":
        return bool(rlh < 0)
    if cond == "rcc>0":
        return bool(rcc > 0)
    raise ValueError(cond)


def ny_label(ts) -> pd.DatetimeIndex:
    """17:00-NY trading-day label of UTC timestamps."""
    ts = pd.DatetimeIndex(ts)
    return (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()


def to_utc(day: pd.Timestamp, hh: int, mm: int, tz: str) -> pd.Timestamp:
    return (day + pd.Timedelta(hours=hh, minutes=mm)).tz_localize(tz).tz_convert("UTC").tz_localize(None)


def session_features(cs: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """cs: index = session date, columns C, P15. Adds seg, r (= r_cc), sig60, rlh."""
    pos = cal.get_indexer(cs.index)
    assert (pos >= 0).all()
    gap = np.diff(pos, prepend=pos[0] - 1) - 1
    cs = cs.copy()
    cs["seg"] = np.cumsum(gap > GAP)
    parts = []
    for _, g in cs.groupby("seg", sort=True):
        g = g.copy()
        g["r"] = np.log(g.C / g.C.shift(1))
        g["sig60"] = g["r"].shift(1).rolling(60).std()
        parts.append(g)
    cs = pd.concat(parts)
    cs["rlh"] = np.log(cs.C / cs.P15)
    return cs


def day_kind(M: pd.Timestamp, S: pd.Timestamp) -> str:
    if M.dayofweek == 0:
        return "Monday"
    return "after holiday" if (M - S).days > 1 else "other Tue-Fri"


# --------------------------------------------------------------------------- Nasdaq (minute)
def run_nasdaq():
    t_start = time.time()
    m = load_market(NQ_PATH)
    d = daily_table(m)
    atr = d["atr20"]
    cal = calendar("nyse", m.t0 + pd.Timedelta(days=1), m.ts(m.n - 1))
    rows = []
    for S in cal:
        i15 = local_idx(m, S, 15, 59, NY)
        if i15 < 0 or i15 >= m.n or not m.vol[i15] > 0:
            continue
        i14 = local_idx(m, S, 14, 59, NY)
        rows.append((S, m.bc[i15], m.bc[i14] if m.vol[i14] > 0 else np.nan))
    cs = session_features(pd.DataFrame(rows, columns=["day", "C", "P15"]).set_index("day"), cal)
    log(f"Nasdaq: {len(cs)} sessions, {cs.seg.nunique()} segments, {cs.P15.isna().sum()} without 14:59 ticks")

    mor, sigs = [], {v: [] for v in VARIANTS}
    for k in range(1, len(cal)):
        M, S = cal[k], cal[k - 1]
        i0 = local_idx(m, M, 7, 55, BER)
        x1, x2 = local_idx(m, M, 9, 0, BER), local_idx(m, M, 9, 25, NY)
        e = live_at(m, i0) if 0 <= i0 < m.n else -1
        f = cs.loc[S] if S in cs.index else None
        rcc = f.r if f is not None else np.nan
        sig = f.sig60 if f is not None else np.nan
        rlh = f.rlh if f is not None else np.nan
        rec = dict(day=M, S=S, kind=day_kind(M, S), live=e >= 0, S_in_series=f is not None, rcc=rcc, sig60=sig, rlh=rlh,
                   atr20=np.nan, spread_entry_bp=np.nan, spread_10ny_bp=np.nan)
        if e < 0 or x2 >= m.n - 1:
            mor.append(rec)
            continue
        a = atr.get(ny_label([m.ts(e)])[0], np.nan)
        mid = (m.ao[e] + m.bo[e]) / 2
        rec["atr20"] = a
        rec["spread_entry_bp"] = (m.ao[e] - m.bo[e]) / mid * 1e4
        j10 = local_idx(m, M, 10, 0, NY)
        if 0 <= j10 < m.n and m.vol[j10] > 0:
            rec["spread_10ny_bp"] = (m.ao[j10] - m.bo[j10]) / ((m.ao[j10] + m.bo[j10]) / 2) * 1e4
        mor.append(rec)
        if not a > 0:
            continue
        for v, (cond, xk, slm, _) in VARIANTS.items():
            if wants(cond, rcc, sig, rlh):
                sigs[v].append(Signal(M, "BUY", e, "market", None, e + 1, slm * a, None, x1 if xk == "X1" else x2, v))
    MOR = pd.DataFrame(mor)
    feat = MOR.set_index("day")
    recs = []
    for v, ss in sigs.items():
        tr = sorted([t for t in (simulate(m, s) for s in ss) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
        nights = [SwapModel.rollovers(m.ts(t.entry_i), m.ts(t.exit_i))["days"].sum() for t in tr]
        assert all(n == 0 for n in nights), "a trade crossed a 17:00 NY rollover"
        R = net_r(m, NQ, tr, None)
        for t, x in zip(tr, R):
            ei, xi = t.entry_i, t.exit_i
            mid_e = (m.ao[ei] + m.bo[ei]) / 2
            exit_mid = t.exit + max(m.ao[xi] - m.bo[xi], 0.0) / 2
            gross = (exit_mid / mid_e - 1) * 1e4
            net = x * t.risk / mid_e * 1e4
            fr = feat.loc[t.day]
            recs.append(dict(market=NQ, variant=v, day=t.day, S=fr.S, kind=fr.kind, entry_i=ei, exit_i=xi,
                             entry_ts=m.ts(ei), exit_ts=m.ts(xi), entry=t.entry, exit=t.exit, reason=t.reason, risk=t.risk,
                             R_gross=t.r, R=x, gross_bp=gross, net_bp=net, cost_bp=gross - net, rcc=fr.rcc, sig60=fr.sig60,
                             rlh=fr.rlh, spread_entry_bp=(m.ao[ei] - m.bo[ei]) / mid_e * 1e4))
    t0 = m.t0
    log(f"Nasdaq: {len(MOR)} mornings, {int(MOR.live.sum())} live, {len(recs)} trades, {time.time() - t_start:.0f}s")
    del m, d
    return pd.DataFrame(recs), MOR, cs, t0


# --------------------------------------------------------------------------- S&P (hourly)
def run_spx():
    t_start = time.time()
    b = spx_bars()                                         # live bars only, index = UTC bar start
    loc = b.index.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    lab = (loc + pd.Timedelta(hours=7)).normalize()
    dd = pd.DataFrame({"high": b.h.to_numpy(), "low": b.l.to_numpy()}, index=lab).groupby(level=0).agg(
        high=("high", "max"), low=("low", "min"))
    dd = dd[dd.index.dayofweek < 5]
    atr = (dd.high - dd.low).rolling(20).mean().shift(1)
    cal = calendar("nyse", pd.Timestamp("2012-01-01"), pd.Timestamp("2026-10-07"))
    hr, ldate = loc.hour, loc.normalize()
    c15 = pd.Series(b.c.to_numpy()[hr == 15], index=ldate[hr == 15])
    c14 = pd.Series(b.c.to_numpy()[hr == 14], index=ldate[hr == 14])
    c15, c14 = c15[~c15.index.duplicated()], c14[~c14.index.duplicated()]
    c15 = c15[c15.index.isin(cal)]
    cs = pd.DataFrame({"C": c15, "P15": c14.reindex(c15.index)})
    cs = session_features(cs, cal)
    log(f"S&P: {len(cs)} sessions, {cs.seg.nunique()} segments, {cs.P15.isna().sum()} without a live 14:00 bar")
    starts = b.index.values
    pos_of = pd.Series(np.arange(len(b)), index=b.index)
    O, H, L, C = (b[k].to_numpy() for k in "ohlc")
    mor, recs = [], []
    for k in range(1, len(cal)):
        M, S = cal[k], cal[k - 1]
        st = to_utc(M, 8, 0, BER)
        p = int(pos_of[st]) if st in pos_of.index else -1
        f = cs.loc[S] if S in cs.index else None
        rcc = f.r if f is not None else np.nan
        sig = f.sig60 if f is not None else np.nan
        rlh = f.rlh if f is not None else np.nan
        rec = dict(day=M, S=S, kind=day_kind(M, S), live=p >= 0, S_in_series=f is not None, rcc=rcc, sig60=sig, rlh=rlh,
                   atr20=np.nan)
        if p < 0:
            mor.append(rec)
            continue
        a = atr.get(ny_label([st])[0], np.nan)
        rec["atr20"] = a
        mor.append(rec)
        if not a > 0:
            continue
        p2 = int(np.searchsorted(starts, to_utc(M, 8, 0, NY).to_datetime64(), side="right")) - 1
        p2 = max(p2, p)
        for v, (cond, xk, slm, _) in VARIANTS.items():
            if not wants(cond, rcc, sig, rlh):
                continue
            px_end = p if xk == "X1" else p2
            sl = slm * a
            entry = O[p] + 0.5
            stop = entry - sl
            hit = np.flatnonzero(L[p:px_end + 1] <= stop)
            if len(hit):
                j = p + hit[0]
                raw = min(stop, O[j])
                px, reason, xts = raw - 0.25, "SL", pd.Timestamp(starts[j]) + pd.Timedelta(minutes=30)
            else:
                j = px_end
                raw = C[j]
                px, reason, xts = raw - 0.5, "TIME", pd.Timestamp(starts[j]) + pd.Timedelta(hours=1)
            gross = (raw / O[p] - 1) * 1e4
            net = (px - entry) / O[p] * 1e4
            recs.append(dict(market=SP, variant=v, day=M, S=S, kind=rec["kind"], entry_i=-1, exit_i=-1, entry_ts=st,
                             exit_ts=xts, entry=entry, exit=px, reason=reason, risk=sl, R_gross=(raw - O[p]) / sl,
                             R=(px - entry) / sl, gross_bp=gross, net_bp=net, cost_bp=gross - net, rcc=rcc, sig60=sig,
                             rlh=rlh, spread_entry_bp=np.nan))
    MOR = pd.DataFrame(mor)
    log(f"S&P: {len(MOR)} mornings, {int(MOR.live.sum())} live, {len(recs)} trades, {time.time() - t_start:.0f}s")
    return pd.DataFrame(recs), MOR, cs


# --------------------------------------------------------------------------- statistics
def data_months(MOR: pd.DataFrame) -> pd.PeriodIndex:
    x = MOR[MOR.live]
    return pd.PeriodIndex(sorted(set(pd.DatetimeIndex(x.day).to_period("M"))), freq="M")


def month_t(g: pd.DataFrame, months: pd.PeriodIndex, a, b) -> float:
    ms = months[(months.start_time >= pd.Timestamp(a)) & (months.start_time <= pd.Timestamp(b))]
    x = g[(g.day >= pd.Timestamp(a)) & (g.day <= pd.Timestamp(b))]
    s = x.groupby(pd.DatetimeIndex(x.day).to_period("M")).R.sum().reindex(ms, fill_value=0.0)
    return tstat(s.to_numpy())


def test_row(g: pd.DataFrame, months: pd.PeriodIndex) -> dict:
    r = g.R.to_numpy()
    day = pd.DatetimeIndex(g.day)
    wins, losses = r[r > 0], r[r <= 0]
    row = {"trades": len(r), "trades/month": len(r) / len(months) if len(months) else np.nan,
           "win %": (r > 0).mean() * 100 if len(r) else np.nan,
           "avg win / avg loss": wins.mean() / -losses.mean() if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
           "avg R": r.mean() if len(r) else np.nan, "t": tstat(r),
           "month t": month_t(g, months, "2000-01-01", "2030-12-31")}
    row.update(per_stats(r, day))
    for p, (a, b) in PER.items():
        row[f"{p} month t"] = month_t(g, months, a, b)
    v = r[np.asarray((day >= L3[0]) & (day <= L3[1]))]
    row.update({"last3y n": len(v), "last3y avg R": v.mean() if len(v) else np.nan, "last3y t": tstat(v)})
    row["SL %"] = (g.reason == "SL").mean() * 100 if len(g) else np.nan
    row["gross bp"] = g.gross_bp.mean()
    row["cost bp"] = g.cost_bp.mean()
    row["net bp"] = g.net_bp.mean()
    row["charter bar"] = bool(row["design t"] >= 2 and row["check avg R"] > 0 and row["holdout avg R"] > 0)
    pos = sum(bool(row[f"{p} avg R"] > 0) for p in PER)
    row["periods avg R > 0"] = pos
    row["replication pass"] = bool(row["avg R"] > 0 and pos >= 2)
    return row


def welch(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return np.nan
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def diff_table(T: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym in (NQ, SP):
        a_all, b_all = T[(T.market == sym) & (T.variant == "ON2")], T[(T.market == sym) & (T.variant == "ON7")]
        spans = {"all": ("2000-01-01", "2030-12-31"), **PER, "last3y": (str(L3[0].date()), str(L3[1].date()))}
        for p, (x, y) in spans.items():
            sel = lambda g: g[(g.day >= pd.Timestamp(x)) & (g.day <= pd.Timestamp(y))]
            a, b = sel(a_all), sel(b_all)
            rows.append({"market": NAMES[sym], "period": p, "ON2 n": len(a), "ON2 avg R": a.R.mean(), "ON7 n": len(b),
                         "ON7 avg R": b.R.mean(), "ON2 - ON7 R": a.R.mean() - b.R.mean(),
                         "Welch t (R)": welch(a.R.to_numpy(), b.R.to_numpy()),
                         "ON2 gross bp": a.gross_bp.mean(), "ON7 gross bp": b.gross_bp.mean(),
                         "Welch t (gross bp)": welch(a.gross_bp.to_numpy(), b.gross_bp.to_numpy())})
    return pd.DataFrame(rows).set_index("market")


def tercile_table(T: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym in (NQ, SP):
        g = T[(T.market == sym) & (T.variant == "ON1") & T.rcc.notna()]
        des = g[(g.day >= pd.Timestamp(PER["design"][0])) & (g.day <= pd.Timestamp(PER["design"][1]))]
        q1, q2 = des.rcc.quantile([1 / 3, 2 / 3]).to_numpy()
        lab = np.where(g.rcc <= q1, "T1 (down)", np.where(g.rcc <= q2, "T2 (mid)", "T3 (up)"))
        for tl in ("T1 (down)", "T2 (mid)", "T3 (up)"):
            x = g[lab == tl]
            row = {"market": NAMES[sym], "tercile": tl, "cuts (design, %)": f"{q1 * 100:.2f} / {q2 * 100:.2f}",
                   "n": len(x), "avg R": x.R.mean(), "t": tstat(x.R.to_numpy()), "gross bp": x.gross_bp.mean()}
            for p, (a, b) in PER.items():
                y = x[(x.day >= pd.Timestamp(a)) & (x.day <= pd.Timestamp(b))]
                row.update({f"{p} n": len(y), f"{p} avg R": y.R.mean() if len(y) else np.nan, f"{p} t": tstat(y.R.to_numpy())})
            y = x[(x.day >= L3[0]) & (x.day <= L3[1])]
            row.update({"last3y avg R": y.R.mean() if len(y) else np.nan})
            rows.append(row)
    return pd.DataFrame(rows).set_index("market")


def by_year(T: pd.DataFrame, sym: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = T[T.market == sym]
    yr = pd.DatetimeIndex(g.day).year
    A = g.groupby(["variant", yr]).R.mean().unstack()
    N = g.groupby(["variant", yr]).R.size().unstack()
    A.columns = N.columns = [str(c) for c in A.columns]
    A.index.name = N.index.name = "variant"
    return A, N


def kind_table(T: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym in (NQ, SP):
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            row = {"market": NAMES[sym], "variant": v}
            for kd in ("Monday", "other Tue-Fri", "after holiday"):
                x = g[g.kind == kd].R.to_numpy()
                row.update({f"{kd} n": len(x), f"{kd} avg R": x.mean() if len(x) else np.nan, f"{kd} t": tstat(x)})
            rows.append(row)
    return pd.DataFrame(rows).set_index("market")


def mr1_overlap(T: pd.DataFrame) -> pd.DataFrame:
    path = "results/alpha_hunt/index_meanrev/trades.csv"
    if not os.path.exists(path):
        return pd.DataFrame()
    mr = pd.read_csv(path, parse_dates=["day"])
    rows = []
    for sym in (NQ, SP):
        mr1 = set(pd.DatetimeIndex(mr[(mr.market == sym) & (mr.variant == "MR1")].day))
        for v in VARIANTS:
            g = T[(T.market == sym) & (T.variant == v)]
            S = set(pd.DatetimeIndex(g.S))
            both = S & mr1
            gm = g[pd.DatetimeIndex(g.S).isin(list(mr1))]
            rows.append({"market": NAMES[sym], "variant": v, "trades": len(g), "MR1 trades": len(mr1),
                         "% of trades with S = MR1 day": len(gm) / len(g) * 100 if len(g) else np.nan,
                         "% of MR1 days followed by a trade": len(both) / len(mr1) * 100 if mr1 else np.nan,
                         "avg R on MR1 days": gm.R.mean() if len(gm) else np.nan,
                         "avg R other days": g[~pd.DatetimeIndex(g.S).isin(list(mr1))].R.mean()})
    return pd.DataFrame(rows).set_index("market")


def coverage(MOR_nq: pd.DataFrame, MOR_sp: pd.DataFrame) -> pd.DataFrame:
    out = []
    for nm, M in (("Nasdaq", MOR_nq), ("S&P", MOR_sp)):
        g = M.groupby(pd.DatetimeIndex(M.day).year)
        out.append(pd.DataFrame({f"{nm} mornings": g.size(), f"{nm} live entry %": g.live.mean() * 100,
                                 f"{nm} S in close series %": g.S_in_series.mean() * 100}))
    C = pd.concat(out, axis=1)
    C.index.name = "year"
    return C


def spread_table(MOR: pd.DataFrame) -> pd.DataFrame:
    rows = []
    spans = {"all": ("2000-01-01", "2030-12-31"), **PER, "last3y": (str(L3[0].date()), str(L3[1].date()))}
    for p, (a, b) in spans.items():
        x = MOR[MOR.live & (MOR.day >= pd.Timestamp(a)) & (MOR.day <= pd.Timestamp(b))]
        rows.append({"period": p, "mornings": len(x), "median spread bp at entry (07:55 Berlin)": x.spread_entry_bp.median(),
                     "mean spread bp at entry": x.spread_entry_bp.mean(),
                     "median spread bp at 10:00 NY": x.spread_10ny_bp.median()})
    return pd.DataFrame(rows).set_index("period")


# --------------------------------------------------------------------------- basket legs: correlation + prop
Tr = namedtuple("Tr", "day entry_i exit_i")


def basket_corr(T: pd.DataFrame, m, legs) -> pd.DataFrame:
    lab_leg = []
    for tr, r in legs:
        lb = ny_label([m.ts(t.exit_i) for t in tr])
        lab_leg.append(pd.Series(r, index=lb).groupby(level=0).sum())
    rows = []
    for sym in (NQ, SP):
        g0 = T[T.market == sym]
        a = max(pd.Timestamp("2011-01-03"), g0.day.min())
        days = pd.bdate_range(a, pd.Timestamp("2026-10-07"))
        L = pd.concat([s.reindex(days, fill_value=0.0) for s in lab_leg], axis=1)
        L.columns = LEG_NAMES
        L["basket (risk-weighted %)"] = (L[LEG_NAMES] * np.array(BASE_MIX)).sum(1)
        for v in VARIANTS:
            g = g0[g0.variant == v]
            mine = pd.Series(g.R.to_numpy(), index=ny_label(g.exit_ts)).groupby(level=0).sum().reindex(days, fill_value=0.0)
            row = {"market": NAMES[sym], "variant": v, "days": len(days)}
            for c in L.columns:
                row[f"corr {c}"] = mine.corr(L[c])
            row["days with a basket trade too %"] = ((mine != 0) & (L["basket (risk-weighted %)"] != 0)).sum() / max((mine != 0).sum(), 1) * 100
            rows.append(row)
    return pd.DataFrame(rows).set_index("market")


def prop(T: pd.DataFrame, survivors: list[str], m, legs, nq_t0) -> pd.DataFrame:
    from gjstrat.prop import prop_table
    from run_m3_addon import ALPHA, since
    from run_prop_risk_rules import make_rule
    off = int((nq_t0 - m.t0) // pd.Timedelta(minutes=1))
    names = []
    legs = list(legs)
    for v in survivors:
        g = T[(T.market == NQ) & (T.variant == v)].copy()
        g["ei"], g["xi"] = g.entry_i + off, g.exit_i + off
        chk = ((pd.DatetimeIndex(g.entry_ts) - m.t0) // pd.Timedelta(minutes=1)).to_numpy()
        assert (chk == g.ei.to_numpy()).all()
        g = g[g.xi < m.n].sort_values(["xi", "ei"])
        legs.append(([Tr(pd.Timestamp(dd), int(a), int(b)) for dd, a, b in zip(g.day, g.ei, g.xi)], g.R.to_numpy()))
        names.append(f"Nasdaq {v}")
    mixes = {"basket": BASE_MIX + (0,) * len(names)}
    for risk in (0.5, 1):
        for j, nm in enumerate(names):
            mixes[f"basket + {nm} {risk}%"] = BASE_MIX + tuple(risk if i == j else 0 for i in range(len(names)))
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
    return P


# --------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    Tn, MOR_nq, cs_nq, nq_t0 = run_nasdaq()
    Ts, MOR_sp, cs_sp = run_spx()
    T = pd.concat([Tn, Ts], ignore_index=True)
    T["day"] = pd.to_datetime(T.day)
    T["S"] = pd.to_datetime(T.S)
    T.to_csv(f"{OUT}/trades.csv", index=False)
    months = {NQ: data_months(MOR_nq), SP: data_months(MOR_sp)}

    rows = []
    for sym in (NQ, SP):
        for v in VARIANTS:
            rows.append({"market": sym, "variant": v, "rule": VARIANTS[v][3],
                         **test_row(T[(T.market == sym) & (T.variant == v)], months[sym])})
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT}/summary.csv", index=False)
    nq = R[R.market == NQ].set_index("variant")
    sp = R[R.market == SP].set_index("variant")
    surv = [v for v in VARIANTS if nq.loc[v, "charter bar"]]
    sp_bar = [v for v in VARIANTS if sp.loc[v, "charter bar"]]
    log("Nasdaq survivors:", surv, "| S&P tests meeting the charter bar:", sp_bar)

    D = diff_table(T); D.to_csv(f"{OUT}/on2_minus_on7.csv")
    TT = tercile_table(T); TT.to_csv(f"{OUT}/terciles.csv")
    YA_nq, YN_nq = by_year(T, NQ); YA_sp, YN_sp = by_year(T, SP)
    YA_nq.to_csv(f"{OUT}/by_year_nasdaq.csv"); YA_sp.to_csv(f"{OUT}/by_year_spx.csv")
    K = kind_table(T); K.to_csv(f"{OUT}/day_kind.csv")
    OV = mr1_overlap(T); OV.to_csv(f"{OUT}/mr1_overlap.csv")
    COV = coverage(MOR_nq, MOR_sp); COV.to_csv(f"{OUT}/coverage.csv")
    SPR = spread_table(MOR_nq); SPR.to_csv(f"{OUT}/spreads.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    show = ["trades", "trades/month", "win %", "avg R", "t", "design n", "design avg R", "design t", "check avg R", "check t",
            "holdout avg R", "holdout t", "last3y avg R", "gross bp", "cost bp", "charter bar", "replication pass"]
    print(R.set_index(["market", "variant"])[show].round(3).to_string(), flush=True)
    print(D.round(3).to_string(), flush=True)
    print(TT.round(3).to_string(), flush=True)

    log("building basket legs")
    from run_m3_addon import build_legs
    m, legs = build_legs()
    BC = basket_corr(T, m, legs); BC.to_csv(f"{OUT}/basket_corr.csv")
    print(BC.round(3).to_string(), flush=True)
    P = prop(T, surv, m, legs, nq_t0) if surv else None

    # ------------------------------------------------------------------ report
    cols = ["trades", "trades/month", "win %", "avg win / avg loss", "avg R", "t", "month t", "design n", "design avg R",
            "design t", "design month t", "check n", "check avg R", "check t", "check month t", "holdout n", "holdout avg R",
            "holdout t", "holdout month t", "last3y n", "last3y avg R", "last3y t", "SL %"]

    def tab(x):
        y = x[cols].copy()
        y.index = [f"{v} {VARIANTS[v][3]}" for v in y.index]
        y.index.name = "variant"
        return fmt_table(y, ".3f")

    judge = pd.DataFrame({"Nasdaq design t": nq["design t"], "Nasdaq check avg R": nq["check avg R"],
                          "Nasdaq holdout avg R": nq["holdout avg R"], "Nasdaq last3y avg R": nq["last3y avg R"],
                          "Nasdaq charter bar": nq["charter bar"], "S&P avg R": sp["avg R"],
                          "S&P periods > 0": sp["periods avg R > 0"], "S&P replicates": sp["replication pass"],
                          "S&P charter bar": sp["charter bar"]})
    judge.index.name = "variant"
    bp = pd.DataFrame({"Nasdaq gross bp": nq["gross bp"], "Nasdaq cost bp": nq["cost bp"], "Nasdaq net bp": nq["net bp"],
                       "Nasdaq avg stop bp": [T[(T.market == NQ) & (T.variant == v)].eval("risk / entry").mean() * 1e4 for v in VARIANTS],
                       "S&P gross bp": sp["gross bp"], "S&P cost bp": sp["cost bp"], "S&P net bp": sp["net bp"]})
    bp.index.name = "variant"
    n_tests = len(R)
    n_charter = int(R["charter bar"].sum())
    s_txt = ", ".join(f"Nasdaq {v}" for v in surv) or "none"
    txt = ["# Alpha hunt: US equity-index overnight drift at the European open (`eq_overnight_drift`)\n",
           "Rules, variants and the survival bar are in the docstring of `run_alpha_eq_overnight_drift.py` (fixed before "
           "running). Long at the 08:00 Berlin open (first live minute in 07:55-08:00), exit 09:00 Berlin (X1) or 09:25 NY "
           "(X2), stop 0.5 / 1.0 x ATR20, all costs. Periods: design from data start (European-open minutes live from "
           "about 2013) to 2017, check 2018-23, holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.\n",
           f"**Tests: {n_tests} (7 variants x 2 markets). Nasdaq survivors of the charter bar (design t >= 2, check and "
           f"holdout avg R > 0): {len(surv)} ({s_txt}). All tests meeting the charter bar (incl. S&P): {n_charter}. "
           f"Expected by luck: {n_tests * 0.006:.2f}.**\n",
           "## Judging\n", "Nasdaq gets the charter bar; the S&P replicates if avg R > 0 over the whole period and in at "
           "least 2 of the 3 periods.\n", fmt_table(judge, ".3f"), "\n",
           f"## Nasdaq 100 ({NQ}), minute bid/ask\n", f"Months with a live entry morning: {len(months[NQ])}.\n", tab(nq), "\n",
           f"## S&P 500 ({SP}), hourly bid bars\n", f"Months with a live entry bar: {len(months[SP])}.\n", tab(sp), "\n",
           "## Size: gross drift vs costs (bp per trade)\n",
           "Nasdaq gross = mid-to-mid (fills less half the fill-minute spread); S&P gross = bid-to-bid. Cost = gross - net.\n",
           fmt_table(bp, ".2f"), "\n", "### Nasdaq spread, entry minute vs 10:00 NY\n", fmt_table(SPR, ".2f"), "\n",
           "## Conditional channel: ON2 (after a down session) minus ON7 (after an up session)\n",
           "Theory: ON2 > ON7, ON7 about 0. Welch t on per-trade values.\n", fmt_table(D, ".3f"), "\n",
           "## ON1 by tercile of r_cc(S) (cut points fixed on design data)\n", fmt_table(TT, ".3f"), "\n",
           "## Avg R by year\n", "### Nasdaq\n", fmt_table(YA_nq, ".3f"), "\n", "Trades:\n", fmt_table(YN_nq, ".0f"), "\n",
           "### S&P\n", fmt_table(YA_sp, ".3f"), "\n", "Trades:\n", fmt_table(YN_sp, ".0f"), "\n",
           "## Monday / after-holiday / other mornings\n", fmt_table(K, ".3f"), "\n",
           "## Overlap with index_meanrev MR1 (MR1 signal day = our S, so MR1 is holding during our trade)\n",
           fmt_table(OV, ".2f") if len(OV) else "index_meanrev trades.csv not found.\n", "\n",
           "## Correlation of daily R with the existing basket legs (run_m3_addon.build_legs)\n",
           "Daily R by 17:00-NY day of exit, zero on days without a trade, business days of the overlapping span.\n",
           fmt_table(BC, ".3f"), "\n",
           "## Data coverage by year\n", fmt_table(COV, ".1f"), "\n",
           "## Contamination note\n",
           "ON1 overlaps the flow-atlas watch-list cell (Nasdaq, London 00:30-08:30, all weekdays), so it is not independent "
           "evidence. Only ON2-ON6 and the ON2 - ON7 gap are new.\n"]
    if P is not None:
        pcols = ["risk rule", "window", "pass ≤1 month %", "pass ≤3 months %", "pass ≤6 months %", "fail ≤6 months %",
                 "pass eventually %", "median months to pass", "months per funded account", "max DD %", "accepted"]
        txt += ["## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)\n",
                "Basket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3% (run_m3_addon.build_legs); surviving "
                "Nasdaq leg(s) added at 0.5% and 1% risk. Accepted if months per funded account is lower and pass eventually % "
                "is not lower than the basket, in both windows.\n", fmt_table(P[pcols], ".1f"), "\n"]
    else:
        txt += ["## Prop sim\n", "Not run: no Nasdaq variant survived the charter bar.\n"]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(txt))
    if P is not None:
        print(P.round(1).to_string(), flush=True)
    log("survivors:", s_txt)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
