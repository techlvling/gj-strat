"""Nas100 15-minute opening-range breakout, rules exactly as given (see gjstrat/nas_orb.py).

Data: Dukascopy USATECHIDXUSD (Nasdaq-100 CFD) 1-minute BID + ASK, Sep 2011 - Oct 2026, from
datastore/USATECHIDXUSD_<YEAR>.tar (unpacked into data/raw on start).

Costs: the real bid/ask spread, `--slip` points per market / stop fill (default 1), commission
per account below. Results in R = P/L / planned loss (rule 8: stop distance + estimated stop
slippage + fees), per contract.

Periods (fixed before looking): design 2011-2018, check 2019-2023, holdout 2024-2026.

Prop simulation (rule 8 sizing, one trade a day): a challenge is started on every signal day and
played forward. Accounts (edit ACCOUNTS):
  * Firm rules (as in run_prop_sim.py): Phase 1 +8%, Phase 2 +6% on a fresh balance, static 10%
    max loss, daily 4% of the day's starting balance, >= 3 trading days per phase, no time limit.
    Assumed 100K, Nas100 CFD at $1 / point per lot, 0.01-lot steps, no commission.
  * Futures 50K example: $2,000 end-of-day trailing max loss, $1,000 daily limit, +$3,000 target,
    MNQ = $2 / point, whole contracts, $1.50 round turn

    python run_nas_orb.py [--slip 1]
"""
from __future__ import annotations

import argparse
import glob
import os
import tarfile
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from gjstrat.data import load_market, load_side, save_market, to_grid
from gjstrat.nas_orb import Account, OrbParams, challenge, net_r, planned_loss, run, size, trading_days
from run_backtest import fmt_table

SYM = "USATECHIDXUSD"
START, END = date(2011, 9, 1), date(2026, 10, 7)
RAW, OUT = "data/raw", "results/nas_orb"
CACHE = f"data/nas100_{START}_{END}.npz"
PERIODS = [("design 2011-18", "2011", "2018"), ("check 2019-23", "2019", "2023"),
           ("holdout 2024-26", "2024", "2026")]
FIRM = Account("Firm 100K (8% + 6%, 10% / 4%)", 100_000, 10_000, False, 0, 8_000, 1.0, 0.01, 0.0,
               target2=6_000, daily_frac=0.04, min_days=3)
ACCOUNTS = [
    FIRM,
    Account("Futures 50K (MNQ)", 50_000, 2_000, True, 1_000, 3_000, 2.0, 1, 1.50),
]


def market():
    if os.path.exists(CACHE):
        return load_market(CACHE)
    os.makedirs(RAW, exist_ok=True)
    for path in sorted(glob.glob(f"datastore/{SYM}_*.tar")):
        with tarfile.open(path) as tar:
            tar.extractall(RAW, members=[x for x in tar.getmembers()
                                         if not os.path.exists(os.path.join(RAW, x.name))],
                           filter="data")
    bid = load_side(SYM, "BID", START, END, RAW)
    ask = load_side(SYM, "ASK", START, END, RAW)
    last = bid.index[bid["v"] > 0][-1]
    m = to_grid(bid.loc[:last], ask.loc[:last], 1.0, pip=1.0)
    save_market(m, CACHE)
    return m


def stats(r: pd.Series) -> dict:
    if len(r) == 0:
        return {"trades": 0}
    eq = r.cumsum()
    dd = (eq.cummax().clip(lower=0) - eq).max()
    streak = run_ = 0
    for x in r:
        run_ = run_ + 1 if x < 0 else 0
        streak = max(streak, run_)
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {"trades": len(r), "win %": 100 * (r > 0).mean(), "avg R": r.mean(),
            "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 else np.nan,
            "profit factor": wins / losses if losses else np.inf, "total R": r.sum(),
            "max DD (R)": dd, "worst losing streak": streak}


def trade_table(trades, acc: Account) -> pd.DataFrame:
    df = pd.DataFrame([{**t.__dict__, "risk_pts": t.risk_pts, "pnl_pts": t.pnl_pts,
                        "planned_loss_usd": planned_loss(t, acc), "R": net_r(t, acc)}
                       for t in trades])
    df["year"] = df.day.dt.year
    return df


def period_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = {name: stats(df[(df.day >= a) & (df.day < str(int(b) + 1))].R) for name, a, b in PERIODS}
    rows["all"] = stats(df.R)
    out = pd.DataFrame(rows).T
    out.index.name = "Period"
    return out


def prop_rows(trades, df, acc: Account, fixed_risk: float | None = None) -> dict:
    days = df.day.to_numpy()
    last = days[-1]
    r = pd.DataFrame([challenge(trades, acc, k, fixed_risk) for k in range(len(trades))])
    r["start"] = days
    r["days"] = [(days[x.end_k] - days[k]) / np.timedelta64(1, "D") for k, x in r.iterrows()]
    fail = r.result.str.startswith("fail")
    row = {"challenges": len(r)}
    for n in (90, 365):
        ok = (r.start + np.timedelta64(n, "D") <= last).to_numpy()   # enough data to judge n days
        row[f"pass <= {n}d %"] = 100 * ((r.result == "pass") & (r.days <= n))[ok].mean()
        row[f"fail <= {n}d %"] = 100 * (fail & (r.days <= n))[ok].mean()
    done = r[r.result != "unfinished"]
    row["pass % (finished)"] = 100 * (done.result == "pass").mean() if len(done) else np.nan
    row["fail in P1 % (finished)"] = 100 * (done.result.str.startswith("fail") & (done.phase == 1)).mean() \
        if len(done) else np.nan
    row["fails by daily limit"] = int((r.result == "fail: daily").sum())
    row["unfinished"] = int((r.result == "unfinished").sum())
    row["median days to pass"] = r[r.result == "pass"].days.median()
    row["signals skipped: 1 contract > budget %"] = \
        100 * r.skipped.sum() / max((r.skipped + r.taken).sum(), 1)
    return row


def prop_table(trades, df) -> pd.DataFrame:
    out = pd.DataFrame({acc.name: prop_rows(trades, df, acc) for acc in ACCOUNTS}).T
    out.index.name = "Account · rule 8 sizing"
    return out


def firm_fixed_table(trades, df) -> pd.DataFrame:
    """Context only: the firm's rules with a fixed % of the balance risked instead of rule 8."""
    out = pd.DataFrame({f"{x:.2%} of balance": prop_rows(trades, df, FIRM, x)
                        for x in (0.0025, 0.005, 0.01)}).T
    out.index.name = "Firm rules · fixed risk"
    return out


def firm_drift(trades) -> pd.DataFrame:
    """Rule 8 on the firm account never ends a challenge, so show where the balance goes:
    P/L after N calendar days from every signal day (phase 1, no stop at target or floor)."""
    days = pd.DatetimeIndex([t.day for t in trades])
    rows = {}
    for n in (90, 365):
        pl, peak = [], []
        for k0 in range(len(trades)):
            if days[k0] + pd.Timedelta(days=n) > days[-1]:
                break
            bal = hi = FIRM.start
            for k in range(k0, len(trades)):
                if (days[k] - days[k0]).days > n:
                    break
                t = trades[k]
                bal += size(t, FIRM, bal - (FIRM.start - FIRM.max_loss), FIRM.daily_frac * bal) * \
                    (t.pnl_pts * FIRM.point_value - FIRM.commission)
                hi = max(hi, bal)
            pl.append(bal - FIRM.start)
            peak.append(hi - FIRM.start)
        pl, peak = np.array(pl), np.array(peak)
        rows[f"after {n} days"] = {"starts": len(pl), "median P/L $": np.median(pl),
                                   "10th pct $": np.percentile(pl, 10), "90th pct $": np.percentile(pl, 90),
                                   "best peak of any start $": peak.max(),
                                   "starts that ever reach +8% %": 100 * (peak >= FIRM.target).mean()}
    out = pd.DataFrame(rows).T
    out.index.name = "Firm 100K · rule 8"
    return out


def sizing_table(df: pd.DataFrame) -> pd.DataFrame:
    """What one contract costs at the stop vs the rule-8 budget with a $2,000 cushion ($50)."""
    rows = {}
    for y, g in df.groupby("year"):
        mnq = (g.risk_pts + 1) * 2 + 1.5
        rows[y] = {"median stop distance (pts)": g.risk_pts.median(),
                   "median range (pts)": (g.range_hi - g.range_lo).median(),
                   "median spread (pts)": g.spread.median(),
                   "1 MNQ at stop, median $": mnq.median(),
                   "% signals 1 MNQ <= $50": 100 * (mnq <= 50).mean(),
                   "CFD lots for $50, median": (50 / (g.risk_pts + 1)).median()}
    out = pd.DataFrame(rows).T
    out.index.name = "Year"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slip", type=float, default=1.0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    m = market()
    days = trading_days(START, END)
    p = OrbParams(slip=args.slip)
    trades, c = run(m, p, days)
    acc = FIRM                                      # R stats: CFD costs (no commission)
    df = trade_table(trades, acc)
    df.drop(columns=["year"]).to_csv(f"{OUT}/trades.csv", index=False)

    main_t = period_table(df)
    by_year = pd.DataFrame({y: stats(g.R) for y, g in df.groupby("year")}).T
    by_year.index.name = "Year"
    by_side = pd.DataFrame({s: stats(g.R) for s, g in df.groupby("side")}).T
    by_side.index.name = "Side"
    exits = df.groupby("reason").R.agg(["count", "mean"]).rename(columns={"mean": "avg R"})
    exits.index.name = "Exit"

    # costs and nearby rule variants: context only, nothing here is picked by result
    sens = {}
    for name, q in [("as written, slip 0", replace(p, slip=0.0)),
                    ("as written, slip 1", replace(p, slip=1.0)),
                    ("as written, slip 2", replace(p, slip=2.0)),
                    ("target 1R", replace(p, rr=1.0)), ("target 1.5R", replace(p, rr=1.5)),
                    ("target 3R", replace(p, rr=3.0)),
                    ("no back-inside skip", replace(p, skip_if_back_inside=False)),
                    ("hold to 16:00", replace(p, exit_at=(16, 0)))]:
        tq, _ = run(m, q, days)
        dq = trade_table(tq, acc)
        for per, row in period_table(dq).iterrows():
            sens[(name, per)] = {k: row[k] for k in ("trades", "win %", "avg R", "t")}
    sens = pd.DataFrame(sens).T.unstack(1)
    sens = sens.reorder_levels([1, 0], axis=1)[[(per, k) for per in [x[0] for x in PERIODS] + ["all"]
                                                for k in ("trades", "avg R", "t")]]
    sens.columns = [f"{a} {b}" for a, b in sens.columns]
    sens.index.name = "Variant"

    prop = prop_table(trades, df)
    fixed = firm_fixed_table(trades, df)
    drift = firm_drift(trades)
    sizing = sizing_table(df)

    rep = [f"# Nas100 15-minute opening-range breakout — {df.day.min():%b %Y} to {df.day.max():%b %Y}\n",
           "Rules exactly as given; see `gjstrat/nas_orb.py` for fill conventions. Data: Dukascopy "
           "USATECHIDXUSD 1-minute bid/ask (Nasdaq-100 CFD). Costs: real spread + "
           f"{args.slip:g} pt slippage per market/stop fill. **R = P/L ÷ planned loss** "
           "(stop distance + 1 pt estimated slippage), per contract.\n",
           f"Days: {c.days} NYSE trading days, {c.no_data} skipped for missing data, "
           f"{c.no_signal} without a signal, {c.back_inside} skipped because the entry open was back "
           f"inside the range, **{c.traded} trades**.\n",
           "## Verdict\n",
           f"* **No edge after costs.** All {len(df)} trades: avg {main_t.loc['all', 'avg R']:+.3f} R "
           f"(t {main_t.loc['all', 't']:+.1f}), win rate {main_t.loc['all', 'win %']:.0f}%. Design years "
           f"{main_t.iloc[0]['avg R']:+.3f} R, check {main_t.iloc[1]['avg R']:+.3f} R, holdout "
           f"{main_t.iloc[2]['avg R']:+.3f} R (t {main_t.iloc[2]['t']:+.1f}): recent years are about "
           "break-even, not a reliable profit. Every nearby variant (1R/1.5R/3R target, hold to 16:00, "
           "no back-inside skip) is negative overall too, so it is not one unlucky setting.\n",
           f"* **The 2R target is rarely reached before 11:30**: {exits.loc['TP', 'count'] if 'TP' in exits.index else 0:.0f} "
           f"targets, {exits.loc['SL', 'count']:.0f} stops, {exits.loc['TIME', 'count']:.0f} time exits. "
           "Most trades are small time-exit results that spread and slippage eat.\n",
           "* **Costs decide the sign.** With zero slippage the whole sample is about flat; each point of "
           "slippage per fill takes roughly 0.06 R per trade.\n",
           "* **On the firm's rules (8% + 6%, 10% max loss, 4% daily, 3 days) rule 8 sizing never "
           "passes and never fails.** Risk is 2.5% of the cushion ($250 on a fresh 100K), so a 2R win is "
           f"+$500 against an $8,000 target; the balance drifts down (median P/L {drift.iloc[-1]['median P/L $']:+,.0f} USD "
           f"after a year) and no start date ever reaches +8% (best peak {drift.iloc[-1]['best peak of any start $']:+,.0f} USD). "
           "With a fixed 1% of balance instead, most challenges fail inside a year "
           f"({fixed.iloc[-1]['fail <= 365d %']:.0f}% fail vs {fixed.iloc[-1]['pass <= 365d %']:.0f}% pass). "
           "On a $2,000-cushion futures account the $50 budget is below one MNQ on every signal since 2020.\n",
           "* Data caveat: before mid-2013 Dukascopy has no separate ask (spread 0) and 2013 misses 86 "
           "days, so the early years flatter the cost side — and still lose.\n",
           "## Result by period\n", fmt_table(main_t, ".3f"),
           "\n## By year\n", fmt_table(by_year, ".3f"),
           "\n## By side\n", fmt_table(by_side, ".3f"),
           "\n## Exits\n", fmt_table(exits, ".3f"),
           "\n## Costs and nearby variants (context only — not a parameter search)\n", fmt_table(sens, ".3f"),
           "\n## Rule 8 sizing in practice\n",
           "With a $2,000 cushion the budget is $50. One MNQ ($2/pt, $1.50 fees) at the stop:\n",
           fmt_table(sizing, ".2f"),
           "\n## Prop challenge simulation (rule 8 sizing)\n",
           "A challenge is started on every signal day and played forward on the trades above "
           "(closed P/L only, no time limit). Only start days with at least N days of data after them "
           "count towards the N-day columns. Firm rules: Phase 1 +8%, Phase 2 +6%, static 10% max "
           "loss, daily 4% of the day's starting balance, >= 3 trading days per phase; assumed 100K, "
           "$1 / point per lot, 0.01-lot steps, no commission.\n", fmt_table(prop, ".1f"),
           "\nRule 8 never ends a firm challenge, so this is where the balance goes instead:\n",
           fmt_table(drift, ".0f"),
           "\n### Firm rules with a fixed % risk instead of rule 8 (context only)\n",
           "Same challenges, but each trade risks a fixed share of the balance.\n",
           fmt_table(fixed, ".1f")]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(rep) + "\n")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(f"{c}".split(", skipped=")[0])
    for t in (main_t, by_year, by_side, exits, sens, sizing, prop, drift, fixed):
        print(t.round(3).to_string(), "\n")


if __name__ == "__main__":
    main()
