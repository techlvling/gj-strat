"""Flow atlas: one pre-declared scan for clock x calendar flows (2010-2026).

Series (39): the 8 currencies (USD EUR JPY GBP CHF AUD NZD CAD), split out of all 28 FX pairs; gold,
Nikkei (JPNIDXJPY) and Nasdaq (USATECHIDXUSD, both from 2011-09); and the 28 pairs themselves (a flow
between two currencies only, like gotobi in USDJPY, is diluted in the currency split).
  * 30-minute mid returns on one UTC grid. A half-hour counts only if it and the one before it traded
    (so weekend gaps never enter).
  * Currency strength = least-squares split of the 28 pair returns into 8 currency returns that sum to
    zero: s_c = (1/8) x sum over the other 7 currencies j of r(c/j). Clipped at 10 robust sd.
Clocks (4, daylight saving aware): Tokyo, Sydney, London, New York. Each local weekday = 48 half-hours.
Windows (214): start every 30 min, length 30m / 1h / 2h / 4h / 8h, inside the local day.
Day types (18, on the clock's local date): all weekdays; Mon..Fri; gotobi; last / 2nd-last / 3rd-last
weekday of the month; 1st / 2nd weekday of the month; NYSE holiday, the weekday before, the weekday after;
Japan market holiday (national holidays + Dec 31, Jan 2-3), the weekday before; England bank holiday.
=> currencies + assets 11 x 4 x 18 x 214 = 169,488 tests; pairs 28 x 4 x 18 x 214 = 431,424 tests.

Survival, fixed before running:
  1. design 2010-17: |t| >= 4 (currencies, assets) or >= 4.5 (pairs), and n >= 50
  2. check 2018-23: same sign and t >= 2
  3. holdout 2024-26: same sign
  Expected survivors from pure noise: ~0.12 (currencies + assets) and ~0.03 (pairs).
  Watch list (currencies + assets only): design 3.5 <= |t| < 4 plus 2 and 3 (~0.8 expected from noise).
  For scale: our real gotobi edge has design t 3.2 (as a trade), so only flows stronger than that can pass.
Survivors are merged into clusters (same series, clock, day type, sign, overlapping windows; then the same
flow seen from two clocks). The window with the best design |t| represents a cluster.

Tradeable check per cluster: every pair containing the currency (or the asset itself) is traded in the
cluster's direction: market entry at the window start, time exit at its end, SL 0.25 x ATR20 (and 1 x ATR20
for information), real bid/ask + $7/lot + 0.2 pip slippage + swap (gold $0.07/oz + $0.02; indices as in
run_box_indices). The pair with the best design t is the pick; it survives if design t >= 2 and check and
holdout avg R > 0 (our usual bar).

    python run_flow_atlas.py
"""
import os
import warnings
from datetime import date
from multiprocessing import Pool

import holidays
import numpy as np
import pandas as pd

from gjstrat.accounting import account
from gjstrat.data import MAJORS, MINORS, load_market
from gjstrat.patterns import NY, Signal, daily_table, is_gotobi, simulate
from gjstrat.swap import SwapModel
from run_backtest import fmt_table
from run_box_indices import net_r as index_net_r
from run_edge_hunt import PER, per_stats

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT = "results/flow_atlas"
T0 = pd.Timestamp("2009-12-31")
G = 8_820_000 // 30
PAIRS = MAJORS + MINORS
CCY = ["USD", "EUR", "JPY", "GBP", "CHF", "AUD", "NZD", "CAD"]
ASSETS = ["XAUUSD", "JPNIDXJPY", "USATECHIDXUSD"]
SERIES = CCY + ASSETS + PAIRS
FAMILY = {**{c: "currency" for c in CCY}, **{a: "asset" for a in ASSETS}, **{p: "pair" for p in PAIRS}}
FILES = {s: f"data/{s.lower()}_2010-01-01_2026-10-07.npz" for s in PAIRS + ["XAUUSD"]}
FILES.update({s: f"data/{s.lower()}_2011-01-02_2026-10-07.npz" for s in ASSETS[1:]})
CLOCKS = {"Tokyo": "Asia/Tokyo", "Sydney": "Australia/Sydney", "London": "Europe/London", "New York": "America/New_York"}
WINDOWS = [(a, L) for L in (1, 2, 4, 8, 16) for a in range(48 - L + 1)]
T1 = {"currency": 4.0, "asset": 4.0, "pair": 4.5}
T1_WATCH, T2 = 3.5, 2.0


def hm(slot):
    return f"{slot // 2:02d}:{(slot % 2) * 30:02d}"


# --------------------------------------------------------------------------- 1. half-hour returns
def slot_returns(sym):
    z = np.load(FILES[sym])
    off = int((pd.Timestamp(str(z["t0"])) - T0) // pd.Timedelta(minutes=30))
    bo, ao, vol = z["bo"], z["ao"], z["vol"]
    n = len(bo) // 30
    lm = np.log((bo[: n * 30: 30] + ao[: n * 30: 30]) / 2)        # mid at the open of each half-hour
    live = vol[: n * 30].reshape(n, 30).sum(1) > 0
    r = np.full(n, np.nan)
    r[:-1] = lm[1:] - lm[:-1]
    ok = live.copy()
    ok[0] = False
    ok[1:] &= live[:-1]
    r[~ok] = np.nan
    out = np.full(G, np.nan)
    k = min(n, G - off)
    out[off: off + k] = r[:k]
    return sym, out


def clip(x, k=10.0):
    v = x[~np.isnan(x)]
    med = np.median(v)
    s = 1.4826 * np.median(np.abs(v - med))
    return np.clip(x, med - k * s, med + k * s)


def build_series():
    with Pool(4) as pool:
        r = dict(pool.map(slot_returns, PAIRS + ASSETS, chunksize=1))
    out = {}
    for c in CCY:
        legs = [r[p] if p[:3] == c else -r[p] for p in PAIRS if c in (p[:3], p[3:])]
        assert len(legs) == 7
        out[c] = clip(np.sum(legs, axis=0) / 8) * 1e4             # NaN unless all 7 legs traded
    for a in ASSETS + PAIRS:
        out[a] = clip(r[a]) * 1e4
    return out


# --------------------------------------------------------------------------- 2. clocks and day types
def day_types(d):
    yrs = range(2009, 2028)
    nyse = set(holidays.NYSE(years=yrs))
    jp = set(holidays.Japan(years=yrs)) | {date(y, 12, 31) for y in yrs} | {date(y, 1, k) for y in yrs for k in (2, 3)}
    uk = set(holidays.UK(subdiv="ENG", years=yrs))
    isin = lambda arr, s: np.array([x in s for x in arr])
    dd, nxt, prv = d.date, (d + pd.offsets.BDay(1)).date, (d - pd.offsets.BDay(1)).date
    D = d.values.astype("datetime64[D]")
    m0 = D.astype("datetime64[M]").astype("datetime64[D]")
    m1 = (D.astype("datetime64[M]") + np.timedelta64(1, "M")).astype("datetime64[D]")
    from_start, from_end = np.busday_count(m0, D), np.busday_count(D + np.timedelta64(1, "D"), m1)
    us, jh, dow = isin(dd, nyse), isin(dd, jp), d.dayofweek
    return {"all weekdays": np.ones(len(d), bool),
            **{nm: dow == k for k, nm in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])},
            "gotobi day": np.array([is_gotobi(x) for x in d]),
            "last weekday of month": from_end == 0, "2nd-last weekday of month": from_end == 1,
            "3rd-last weekday of month": from_end == 2,
            "1st weekday of month": from_start == 0, "2nd weekday of month": from_start == 1,
            "US holiday": us, "day before a US holiday": isin(nxt, nyse) & ~us, "day after a US holiday": isin(prv, nyse) & ~us,
            "Japan holiday": jh, "day before a Japan holiday": isin(nxt, jp) & ~jh,
            "England bank holiday": isin(dd, uk)}


def clock_frame(tz):
    loc = pd.DatetimeIndex(T0 + pd.to_timedelta(np.arange(G) * 30, unit="min")).tz_localize("UTC").tz_convert(tz)
    ld = loc.tz_localize(None).normalize()
    dates, code = np.unique(ld.values, return_inverse=True)
    dates = pd.DatetimeIndex(dates)
    slot = loc.hour.to_numpy() * 2 + loc.minute.to_numpy() // 30
    keep = dates.dayofweek < 5
    return dict(dates=dates, code=code, slot=slot, keep=keep, types=day_types(dates))


def windows_matrix(x, cf):
    M = np.full((len(cf["dates"]), 48), np.nan)
    M[cf["code"], cf["slot"]] = x
    ok = ~np.isnan(M)
    S = np.concatenate([np.zeros((len(M), 1)), np.cumsum(np.where(ok, M, 0), 1)], 1)
    C = np.concatenate([np.zeros((len(M), 1)), np.cumsum(ok, 1)], 1)
    a = np.array([w[0] for w in WINDOWS])
    b = a + np.array([w[1] for w in WINDOWS])
    W = S[:, b] - S[:, a]
    W[(C[:, b] - C[:, a]) < (b - a)] = np.nan
    return W


def moments(W):
    n = (~np.isnan(W)).sum(0)
    mu, sd = np.nanmean(W, 0), np.nanstd(W, 0, ddof=1)
    return n, mu, mu / sd * np.sqrt(n), sd


def scan(series):
    rows = []
    for cname, tz in CLOCKS.items():
        cf = clock_frame(tz)
        per = {p: cf["keep"] & (cf["dates"] >= pd.Timestamp(a)) & (cf["dates"] <= pd.Timestamp(b)) for p, (a, b) in PER.items()}
        for s in SERIES:
            W = windows_matrix(series[s], cf)
            for ty, mask in cf["types"].items():
                rec = {"series": s, "family": FAMILY[s], "clock": cname, "day type": ty,
                       "a": [a for a, _ in WINDOWS], "L": [L for _, L in WINDOWS]}
                for p, pm in per.items():
                    n, mu, t, sd = moments(W[mask & pm])
                    rec.update({f"{p} n": n, f"{p} bp": mu, f"{p} t": t})
                    if p == "design":
                        sd_c, n_c, mu_c = sd, n, mu
                if ty != "all weekdays":                          # condition vs the other weekdays (design)
                    n_o, mu_o, _, sd_o = moments(W[~mask & per["design"]])
                    rec["vs other days t"] = (mu_c - mu_o) / np.sqrt(sd_c ** 2 / n_c + sd_o ** 2 / n_o)
                else:
                    rec["vs other days t"] = np.nan
                rows.append(pd.DataFrame(rec))
        print("scanned", cname, flush=True)
    return pd.concat(rows, ignore_index=True), {c: clock_frame(tz) for c, tz in CLOCKS.items()}


# --------------------------------------------------------------------------- 3. clusters
def utc_span(row, ref):
    tz = CLOCKS[row["clock"]]
    a = (ref + pd.Timedelta(minutes=30 * row["a"])).tz_localize(tz).tz_convert("UTC").tz_localize(None)
    return (a - ref) / pd.Timedelta(minutes=1), (a - ref) / pd.Timedelta(minutes=1) + 30 * row["L"]


def clusters(surv):
    if surv.empty:
        return surv
    surv = surv.copy()
    surv["sign"] = np.sign(surv["design t"])
    reps = []
    for _, g in surv.groupby(["series", "clock", "day type", "sign"]):
        g = g.sort_values("a")
        cur, end = [], -1
        for i, r in g.iterrows():
            if cur and r["a"] >= end:
                reps.append(g.loc[cur].assign(windows=len(cur)).loc[[g.loc[cur, "design t"].abs().idxmax()]])
                cur = []
            cur.append(i)
            end = max(end, r["a"] + r["L"]) if len(cur) > 1 else r["a"] + r["L"]
        reps.append(g.loc[cur].assign(windows=len(cur)).loc[[g.loc[cur, "design t"].abs().idxmax()]])
    R = pd.concat(reps).sort_values("design t", key=np.abs, ascending=False).reset_index(drop=True)
    refs = [pd.Timestamp("2015-01-14"), pd.Timestamp("2015-07-15")]
    for ref in refs:
        sp = R.apply(lambda r: utc_span(r, ref), axis=1)
        R[f"u0_{ref.month}"], R[f"u1_{ref.month}"] = [x[0] for x in sp], [x[1] for x in sp]
    R["also seen from"], R["dup"] = "", False
    for i in range(len(R)):
        if R.loc[i, "dup"]:
            continue
        for j in range(i + 1, len(R)):
            if R.loc[j, "dup"] or any(R.loc[i, k] != R.loc[j, k] for k in ("series", "day type", "sign")):
                continue
            if all(R.loc[i, f"u0_{m}"] < R.loc[j, f"u1_{m}"] and R.loc[j, f"u0_{m}"] < R.loc[i, f"u1_{m}"] for m in (1, 7)):
                R.loc[j, "dup"] = True
                R.loc[i, "also seen from"] += ("; " if R.loc[i, "also seen from"] else "") + \
                    f"{R.loc[j, 'clock']} {R.loc[j, 'start']}-{R.loc[j, 'end']}"
    return R[~R["dup"]].reset_index(drop=True)


# --------------------------------------------------------------------------- 4. tradeable check
def ny_label(ts_utc):
    ny = ts_utc.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    return ny.normalize() + pd.Timedelta(days=1 if ny.hour >= 17 else 0)


def trade_pair(job):
    sym, specs = job
    m = load_market(FILES[sym])
    d = daily_table(m)
    sw = SwapModel.from_fred("rates", 1.0)
    out = []
    for cid, side, tz, a, L, dates in specs:
        ent = pd.DatetimeIndex(dates) + pd.Timedelta(minutes=30 * a)
        ext = pd.DatetimeIndex(dates) + pd.Timedelta(minutes=30 * (a + L))
        eu = ent.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").tz_localize(None)
        xu = ext.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").tz_localize(None)
        for slm in (0.25, 1.0):
            sigs = []
            for day, e, x in zip(dates, eu, xu):
                if pd.isna(e) or pd.isna(x):
                    continue
                i, j = m.idx(e), m.idx(x)
                if i < 0 or j >= m.n - 1:
                    continue
                live = np.flatnonzero(m.vol[i: i + 5] > 0)
                if not len(live) or i + live[0] >= j - 1:
                    continue
                atr = d["atr20"].get(ny_label(e), np.nan)
                if np.isnan(atr):
                    continue
                sigs.append(Signal(day, side, i + live[0], "market", None, i + live[0] + 1, slm * atr, None, j, "flow"))
            tr = sorted([t for t in (simulate(m, s) for s in sigs) if t is not None], key=lambda t: (t.exit_i, t.entry_i))
            if not tr:
                continue
            if sym == "XAUUSD":
                r = np.array([t.r - (0.07 + 0.02 * (1 + (t.reason == "SL"))) / t.risk for t in tr])
            elif "IDX" in sym:
                r = index_net_r(m, sym, tr)
            else:
                r = account(tr, m, 10_000, commission=7, swap=sw, sym=sym, slippage_pips=0.2)["R"].to_numpy()
            days = pd.DatetimeIndex([t.day for t in tr])
            out.append({"cluster": cid, "symbol": sym, "side": side, "SL x ATR20": slm, "trades": len(r),
                        "win %": (r > 0).mean() * 100, **per_stats(r, days)})
    print("traded", sym, flush=True)
    return out


def trade_check(C, frames):
    jobs = {}
    for cid, r in C.iterrows():
        cf = frames[r["clock"]]
        mask = cf["types"][r["day type"]] & cf["keep"] & (cf["dates"] >= pd.Timestamp("2010-01-01"))
        dates = list(cf["dates"][mask])
        up = r["design t"] > 0
        if r["series"] in CCY:
            for p in PAIRS:
                if r["series"] in (p[:3], p[3:]):
                    side = "BUY" if (p[:3] == r["series"]) == up else "SELL"
                    jobs.setdefault(p, []).append((cid, side, CLOCKS[r["clock"]], r["a"], r["L"], dates))
        else:
            jobs.setdefault(r["series"], []).append((cid, "BUY" if up else "SELL", CLOCKS[r["clock"]], r["a"], r["L"], dates))
    with Pool(4) as pool:
        res = pool.map(trade_pair, sorted(jobs.items()), chunksize=1)
    return pd.DataFrame([x for xs in res for x in xs])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cache = "data/flow_series_v2.npz"
    if os.path.exists(cache):
        series = dict(np.load(cache))
    else:
        series = build_series()
        np.savez_compressed(cache, **series)
    print("series built", flush=True)
    A, frames = scan(series)
    thr = A["family"].map(T1)
    at = A["design t"].abs()
    big = A["design n"] >= 50
    A["tier"] = np.where(big & (at >= thr), "A", np.where(big & (A["family"] != "pair") & (at >= T1_WATCH), "watch", ""))
    s1 = A["tier"] != ""
    sg = np.sign(A["design t"])
    s2 = s1 & (A["check t"] * sg >= T2)
    s3 = s2 & (A["holdout bp"] * sg > 0)
    S = A[s1].copy()
    S["start"], S["end"] = S["a"].map(hm), (S["a"] + S["L"]).map(hm)
    S.to_csv(f"{OUT}/stage1_passes.csv", index=False)
    count = pd.DataFrame({f"stage {k}": A[m].groupby(["family", "tier"]).size() for k, m in ((1, s1), (2, s2), (3, s3))}).fillna(0).astype(int)
    C = clusters(S[s3[s1].to_numpy()])
    cols = ["tier", "series", "clock", "day type", "start", "end", "windows", "design n", "design bp", "design t", "check bp",
            "check t", "holdout n", "holdout bp", "holdout t", "vs other days t", "also seen from"]
    C[cols].to_csv(f"{OUT}/clusters.csv")
    print(count.to_string(), flush=True)
    pd.set_option("display.width", 250)
    print(C[cols].round(2).to_string(), flush=True)

    MAXC = len(C)                                                 # every cluster gets the trade check
    Ct = C.loc[C["design t"].abs().sort_values(ascending=False).index[:MAXC]]
    T = trade_check(Ct, frames)
    T.to_csv(f"{OUT}/trades_by_pair.csv", index=False)
    P = T[T["SL x ATR20"] == 0.25].sort_values("design t", ascending=False).groupby("cluster").head(1).set_index("cluster")
    W1 = T[T["SL x ATR20"] == 1.0].set_index(["cluster", "symbol"])
    best = Ct[["tier", "series", "clock", "day type", "start", "end"]].join(
        P[["symbol", "side", "trades", "win %", "design avg R", "design t", "check avg R", "check t", "holdout avg R", "holdout t"]])
    best["SL 1xATR design/check/holdout t"] = [
        "/".join(f"{W1.loc[(c, s), f'{p} t']:.1f}" for p in PER) if (c, s) in W1.index else "" for c, s in zip(best.index, best["symbol"])]
    best["survives"] = (best["design t"] >= 2) & (best["check avg R"] > 0) & (best["holdout avg R"] > 0)
    best.to_csv(f"{OUT}/tradeable.csv")
    tcols = ["tier", "series", "clock", "day type", "start", "end", "symbol", "side", "trades", "win %", "design avg R", "design t",
             "check avg R", "check t", "holdout avg R", "holdout t", "SL 1xATR design/check/holdout t", "survives"]
    open(f"{OUT}/REPORT.md", "w").write(
        "# Flow atlas: clock x calendar scan, 2010–2026\n\nRules in run_flow_atlas.py (fixed before running).\n\n"
        f"**Tests: {len(A):,} → {len(C)} surviving clusters ({int(best['survives'].sum())} tradeable after costs).**\n\n"
        "Expected from pure noise: ~0.12 tier-A survivors (currencies + assets), ~0.03 (pairs), ~0.8 on the watch list.\n\n"
        "## Passes per stage\n\n" + fmt_table(count.reset_index().set_index("family"), ".0f") +
        "\n\n## Surviving flows (currency strength, pair or asset return, basis points per window)\n\n"
        + fmt_table(C[cols], ".2f") +
        "\n\n## Tradeable check (best pair per flow, SL 0.25 × ATR20, all costs)\n\n"
        + fmt_table(best[tcols], ".3f") + "\n")
    print(best[tcols].round(3).to_string())
