"""Edge hunt: (1) USDJPY clock scan, (2) Nikkei / Nasdaq -> USDJPY lead-lag, (3) US jobs report (NFP).
Periods: design 2010(11)-2017, check 2018-2023, holdout 2024-2026. Costs: spread via bid/ask fills
plus ~1.0 pip ($7/lot commission ~ 1 pip on USDJPY) on the scan; parts 2-3 use the full engine costs.

(1) Clock scan, pre-declared: entry at the open of every 30-minute UTC slot (48), hold 60 or 180
    minutes (market in, market out, no stop), on: all weekdays / Mon / Tue / Wed / Thu / Fri /
    month-start (first 3 business days) / month-end (last 2) / gotobi days  -> 48 x 2 x 9 = 864 tests,
    both directions; the direction is taken from the design period. Result in R = 0.25 x ATR20
    (the gotobi stop size). Survives only with design t >= 3.7 (Bonferroni for 864 x 2 tests at 5%)
    AND avg > 0 in check AND holdout. Sanity check: gotobi days near 01:00 UTC should show up.
(2) Lead-lag, pre-declared (16): JPN225 move 00:00-00:30 / 00:00-01:00 UTC (Tokyo open) -> trade
    USDJPY in the same direction for 1 h / 2 h; Nasdaq move 09:30-10:00 / 09:30-10:30 New York (NY open)
    -> USDJPY same direction 1 h / 2 h; all with |move| >= 0.2% or any move. SL 0.25 x ATR20.
(3) NFP, pre-declared (12): first Friday of the month, 08:30 New York. USDJPY / EURUSD / gold:
    follow or fade the 08:30-08:45 move from 08:45, exit 10:00 or 12:00 NY, SL 0.5 x ATR20.
(2)+(3) survive with design t >= 2 AND avg > 0 in check AND holdout (28 tests: ~1 by luck).

    python run_edge_hunt.py
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import build_market
from gjstrat.patterns import NY, Signal, daily_table, is_gotobi, local_idx, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_usdjpy_sl import tstat

OUT = "results/edge_hunt"
PER = {"design": ("2010-01-01", "2017-12-31"), "check": ("2018-01-01", "2023-12-31"), "holdout": ("2024-01-01", "2026-12-31")}
COST = 0.010                    # ~1 pip on USDJPY beyond the spread (commission + slippage)


def per_stats(x, day, prefix=""):
    out = {}
    for p, (a, b) in PER.items():
        v = x[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))]
        v = v[~np.isnan(v)]
        out.update({f"{prefix}{p} n": len(v), f"{prefix}{p} avg R": v.mean() if len(v) else np.nan,
                    f"{prefix}{p} t": tstat(v)})
    return out


def clock_scan(m, d):
    days = pd.bdate_range("2010-01-04", "2026-10-06")
    ny_label = lambda ts: (ts.tz_localize("UTC").tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize()
    labels = d.index
    lab = pd.Series(labels, index=labels)
    wk = lab[labels.dayofweek < 5]
    first3 = set(pd.DatetimeIndex(wk.groupby([wk.index.year, wk.index.month]).head(3).values))
    last2 = set(pd.DatetimeIndex(wk.groupby([wk.index.year, wk.index.month]).tail(2).values))
    conds = {"all weekdays": lambda x: True, "Mon": lambda x: x.dayofweek == 0, "Tue": lambda x: x.dayofweek == 1,
             "Wed": lambda x: x.dayofweek == 2, "Thu": lambda x: x.dayofweek == 3, "Fri": lambda x: x.dayofweek == 4,
             "month-start": lambda x: x in first3, "month-end": lambda x: x in last2, "gotobi": lambda x: is_gotobi(x)}
    rows = []
    for slot in range(48):
        hh, mm = divmod(slot * 30, 60)
        ts = days + pd.Timedelta(hours=hh, minutes=mm)
        i = ((ts - m.t0) // pd.Timedelta(minutes=1)).to_numpy().astype(int)
        lbl = ny_label(ts)
        atr = d["atr20"].reindex(lbl).to_numpy()
        cmask = {c: np.array([bool(f(x)) for x in lbl]) for c, f in conds.items()}
        for H in (60, 180):
            ok = (i >= 0) & (i + H < m.n) & ~np.isnan(atr)
            ii = np.where(ok, i, 0)
            live = ok & (m.vol[ii] > 0) & (m.vol[np.minimum(ii + H, m.n - 1)] > 0)
            longr = np.where(live, (m.bo[np.minimum(ii + H, m.n - 1)] - m.ao[ii] - COST) / (0.25 * atr), np.nan)
            shortr = np.where(live, (m.bo[ii] - m.ao[np.minimum(ii + H, m.n - 1)] - COST) / (0.25 * atr), np.nan)
            for c, cm in cmask.items():
                sel = cm & live
                dl = pd.DatetimeIndex(lbl[sel])
                L, S = longr[sel], shortr[sel]
                dmask = (dl >= pd.Timestamp("2010-01-01")) & (dl <= pd.Timestamp("2017-12-31"))
                side = "BUY" if np.nanmean(L[dmask]) >= np.nanmean(S[dmask]) else "SELL"
                x = L if side == "BUY" else S
                rows.append({"slot (UTC)": f"{hh:02d}:{mm:02d}", "hold min": H, "days": c, "side": side,
                             **per_stats(x, dl)})
    res = pd.DataFrame(rows)
    res["survives"] = (res["design t"] >= 3.7) & (res["check avg R"] > 0) & (res["holdout avg R"] > 0)
    res["weak (t>=2, all +)"] = (res["design t"] >= 2) & (res["check avg R"] > 0) & (res["holdout avg R"] > 0)
    return res


def lead_lag(uj, idx_m, idx_name, d):
    rows = []
    days = d.index[d.index >= pd.Timestamp("2011-01-03")]
    specs = []
    if idx_name == "JPN225":
        for w in (30, 60):
            for hold in (60, 120):
                specs.append((f"JPN225 00:00-{w // 60:02d}:{w % 60:02d} UTC -> USDJPY {hold // 60}h", (0, 0), w, hold))
    else:
        for w in (30, 60):
            for hold in (60, 120):
                specs.append((f"Nasdaq 09:30 NY +{w}m -> USDJPY {hold // 60}h", (9, 30), w, hold))
    for name, (hh, mm), w, hold in specs:
        for thr in (0.0, 0.002):
            sigs = []
            for day in days:
                t_a = day + pd.Timedelta(hours=hh, minutes=mm)
                if idx_name != "JPN225":                       # New York wall clock (DST-aware)
                    t_a = t_a.tz_localize(NY).tz_convert("UTC").tz_localize(None)
                ia = int((t_a - idx_m.t0) // pd.Timedelta(minutes=1)); ib = ia + w
                if ia < 0 or ib >= idx_m.n or idx_m.vol[ia] == 0 or idx_m.vol[ib] == 0:
                    continue
                ret = idx_m.bc[ib] / idx_m.bc[ia] - 1
                if abs(ret) <= thr:
                    continue
                s = uj.idx(t_a) + w
                if s < 0 or s + hold >= uj.n or day not in d.index:
                    continue
                sigs.append(Signal(day, "BUY" if ret > 0 else "SELL", s, "market", None, s + 1,
                                   0.25 * d.loc[day, "atr20"], None, s + hold, "leadlag"))
            rows.append({"test": f"{name}, |move| > {thr:.1%}", **trade_stats(uj, "USDJPY", sigs)})
    return rows


def nfp(markets, d_by):
    rows = []
    for sym, m in markets.items():
        d = d_by[sym]
        fridays = [x for x in d.index if x.dayofweek == 4 and x.day <= 7 and x >= pd.Timestamp("2010-01-01")]
        for mode in ("follow", "fade"):
            for ex in ((10, 0), (12, 0)):
                sigs = []
                for day in fridays:
                    a, b = local_idx(m, day, 8, 30, NY), local_idx(m, day, 8, 45, NY)
                    if a < 0 or b >= m.n or m.vol[a] == 0:
                        continue
                    mv = m.bo[b] - m.bo[a]
                    if mv == 0:
                        continue
                    up = mv > 0
                    side = ("BUY" if up else "SELL") if mode == "follow" else ("SELL" if up else "BUY")
                    sigs.append(Signal(day, side, b, "market", None, b + 1, 0.5 * d.loc[day, "atr20"], None,
                                       local_idx(m, day, *ex, NY), "nfp"))
                rows.append({"test": f"NFP {sym} {mode} 08:45 -> {ex[0]}:00 NY", **trade_stats(m, sym, sigs)})
    return rows


SWAP = None


def trade_stats(m, sym, sigs):
    tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
    if not tr:
        return {}
    if sym == "XAUUSD":
        r = np.array([t.r - (0.07 + 0.02 * (1 + (t.reason == "SL"))) / t.risk for t in tr])
    else:
        r = account(tr, m, 10_000, commission=7, swap=SWAP, sym=sym, slippage_pips=0.2)["R"].to_numpy()
    out = per_stats(r, pd.DatetimeIndex([t.day for t in tr]))
    out["win %"] = (r > 0).mean() * 100
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    SWAP = SwapModel.from_fred("rates", 1.0)
    uj = build_market("USDJPY", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/usdjpy_2010-01-01_2026-10-07.npz")
    d_uj = daily_table(uj)

    scan = clock_scan(uj, d_uj)
    scan.to_csv(f"{OUT}/clock_scan.csv", index=False)
    surv = scan[scan.survives].sort_values("design t", ascending=False)
    weak = scan[scan["weak (t>=2, all +)"]].sort_values("design t", ascending=False)
    print("clock scan: survivors", len(surv), "weak", len(weak))
    print(scan.sort_values("design t", ascending=False).head(15).round(3).to_string())

    jpn = build_market("JPNIDXJPY", date(2011, 1, 2), date(2026, 10, 7), "data/raw", "data/jpnidxjpy_2011-01-02_2026-10-07.npz")
    nas = build_market("USATECHIDXUSD", date(2011, 1, 2), date(2026, 10, 7), "data/raw", "data/usatechidxusd_2011-01-02_2026-10-07.npz")
    ll = pd.DataFrame(lead_lag(uj, jpn, "JPN225", d_uj) + lead_lag(uj, nas, "Nasdaq", d_uj))
    eu = build_market("EURUSD", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/eurusd_2010-01-01_2026-10-07.npz")
    au = build_market("XAUUSD", date(2010, 1, 1), date(2026, 10, 7), "data/raw", "data/xauusd_2010-01-01_2026-10-07.npz")
    mk = {"USDJPY": uj, "EURUSD": eu, "XAUUSD": au}
    nf = pd.DataFrame(nfp(mk, {s: daily_table(x) for s, x in mk.items()}))
    other = pd.concat([ll, nf]).set_index("test")
    other["survives"] = (other["design t"] >= 2) & (other["check avg R"] > 0) & (other["holdout avg R"] > 0)
    other.to_csv(f"{OUT}/leadlag_nfp.csv")

    cols = ["slot (UTC)", "hold min", "days", "side", "design n", "design avg R", "design t", "check avg R", "check t",
            "holdout avg R", "holdout t"]
    ocols = ["design n", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t", "survives"]
    rep = ["# Edge hunt — USDJPY clock scan, Nikkei/Nasdaq lead-lag, NFP\n", "Tests and rules in run_edge_hunt.py "
           "(all fixed before running).\n",
           f"## 1. Clock scan: {len(scan)} tests, survivors (design t ≥ 3.7, check and holdout > 0): **{len(surv)}**\n",
           fmt_table(surv[cols].set_index("slot (UTC)"), ".3f") if len(surv) else "None.\n",
           f"\n### Weaker candidates (design t ≥ 2, check and holdout > 0): {len(weak)} — about "
           f"{len(scan) * 0.025 * 0.25:.0f} expected by luck\n", fmt_table(weak[cols].head(25).set_index("slot (UTC)"), ".3f"),
           f"\n## 2–3. Lead-lag and NFP: {len(other)} tests, survivors: **{int(other.survives.sum())}**\n",
           fmt_table(other[ocols].sort_values("design t", ascending=False), ".3f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    print(surv[cols].round(3).to_string())
    print(weak[cols].head(25).round(3).to_string())
    print(other[ocols].sort_values("design t", ascending=False).round(3).to_string())
