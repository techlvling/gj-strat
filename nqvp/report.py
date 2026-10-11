"""Analysis of the simulated trades: IS/OOS split, ranking, plateau, benchmarks, robustness, report."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from .data import available_years, load_year
from .engine import Params
from .stats import breakdown, equity, random_benchmark, summarize

BASE = "0930|POC|B2on|BEoff"
NF = {"BEoff": "NOFILTER|2R|BEoff", "BEon": "NOFILTER|2R|BEon"}
SETTINGS = ("start", "target", "b2", "be")
OPTIONS = {"start": ("0930", "0945"), "target": ("POC", "2R"), "b2": ("B2on", "B2off"), "be": ("BEoff", "BEon")}
COMBOS = [f"{s}|{t}|{b}|{e}" for s in OPTIONS["start"] for t in OPTIONS["target"]
          for b in OPTIONS["b2"] for e in OPTIONS["be"]]
MIN_TRADES = 100
# palette: reference categorical slots in fixed order (light mode), text and grid tokens
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE, NEUTRAL = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#8a8984"


def settings(name: str) -> dict:
    return dict(zip(SETTINGS, name.split("|")[:4]))


def neighbours(name: str) -> list[tuple[str, str]]:
    s = settings(name)
    out = []
    for k in SETTINGS:
        alt = [o for o in OPTIONS[k] if o != s[k]][0]
        out.append((f"{k}={alt}", "|".join(alt if kk == k else s[kk] for kk in SETTINGS)))
    return out


# --------------------------------------------------------------------------- formatting
def fmt(x) -> str:
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(x)
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "-"
        if np.isinf(x):
            return "inf"
        return f"{x:,.2f}"
    return str(x)


def md(df: pd.DataFrame, index: bool = False) -> str:
    if index:
        df = df.reset_index()
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(x) for x in row) + " |")
    return "\n".join(lines)


STAT_COLS = ["trades", "win_rate", "avg_R", "profit_factor", "expectancy", "max_dd_pct", "max_dd_R",
             "losing_streak", "net_return_pct"]
STAT_NAMES = {"trades": "trades", "win_rate": "win %", "avg_R": "avg R", "profit_factor": "PF",
              "expectancy": "expectancy R", "max_dd_pct": "max DD %", "max_dd_R": "max DD R",
              "losing_streak": "longest losing streak", "net_return_pct": "net return %"}


def flags(s: dict) -> str:
    f = []
    if s["trades"] < MIN_TRADES:
        f.append("<100 trades")
    if s["trades"] >= 20 and (s["profit_factor"] > 3 or s["expectancy"] > 1.0 or s["win_rate"] > 75):
        f.append("unrealistically good?")
    return ", ".join(f)


# --------------------------------------------------------------------------- analysis
def analyse(days: pd.DataFrame, trades: pd.DataFrame, counts: pd.DataFrame, P: Params = Params(),
            seeds: int = 1000, out: str = "results/nq_vp") -> dict:
    os.makedirs(out, exist_ok=True)
    os.makedirs(f"{out}/trade_logs", exist_ok=True)
    days = days.sort_values("date").reset_index(drop=True)
    days["skip"] = days["skip"].fillna("")
    trades = trades.sort_values(["variant", "entry_time"]).reset_index(drop=True)
    tradable = days.loc[days["skip"] == "", "date"].reset_index(drop=True)
    n_is = int(round(0.6 * len(tradable)))
    is_end, oos_start = tradable.iloc[n_is - 1], tradable.iloc[n_is]
    trades["sample"] = np.where(trades["date"] <= is_end, "IS", "OOS")
    counts["sample"] = np.where(counts["date"] <= is_end, "IS", "OOS")

    def sub(variant, sample="ALL"):
        t = trades[trades["variant"] == variant]
        return t if sample == "ALL" else t[t["sample"] == sample]

    def st(variant, sample="ALL"):
        return summarize(sub(variant, sample))

    # ---------------------------------------------------------------- 16-combo IS ranking
    rows = []
    for c in COMBOS:
        s = st(c, "IS")
        rows.append(dict(combo=c, **{STAT_NAMES[k]: s[k] for k in STAT_COLS}, flags=flags(s)))
    rank = pd.DataFrame(rows)
    rank["qualifies (>=100 IS trades)"] = rank["trades"] >= MIN_TRADES
    rank = rank.sort_values(["qualifies (>=100 IS trades)", "expectancy R"], ascending=[False, False])
    rank.insert(0, "IS rank", np.where(rank["qualifies (>=100 IS trades)"],
                                       np.arange(1, len(rank) + 1).astype(object), "-"))
    top = rank.loc[rank["qualifies (>=100 IS trades)"], "combo"].head(3).tolist()
    reported = list(dict.fromkeys([BASE] + top))

    # ---------------------------------------------------------------- plateau
    plateau_tables, plateau_verdict = {}, {}
    for c in top:
        s0 = st(c, "IS")
        nb = []
        for label, n in neighbours(c):
            s = st(n, "IS")
            nb.append(dict(change=label, combo=n, trades=s["trades"], expectancy_R=s["expectancy"],
                           PF=s["profit_factor"], net_return_pct=s["net_return_pct"]))
        nbd = pd.DataFrame(nb)
        e = nbd["expectancy_R"].fillna(-9)
        pos = int((e > 0).sum())
        if s0["expectancy"] <= 0:
            verdict = "top combo itself is not positive"
        elif pos <= 1 or e.mean() <= 0:
            verdict = "LIKELY NOISE: good combo with poor neighbours"
        elif pos >= 3 and e.mean() >= 0.5 * s0["expectancy"]:
            verdict = "plateau: neighbours hold up"
        else:
            verdict = "mixed: some neighbours weak"
        plateau_tables[c], plateau_verdict[c] = nbd, f"{verdict} ({pos}/4 neighbours positive)"
    base_nb = pd.DataFrame([dict(change=label, combo=n, **{k: st(n, "IS")[k] for k in
                                                           ("trades", "expectancy", "profit_factor")})
                            for label, n in neighbours(BASE)])

    # ---------------------------------------------------------------- main table (IS & OOS)
    rnd = {}
    for c in reported + [NF["BEoff"], NF["BEon"]]:
        for smp in ("IS", "OOS"):
            rnd[(c, smp)] = random_benchmark(sub(c, smp), seeds)
    main_rows = []
    for c in reported + [NF["BEoff"], NF["BEon"]]:
        for smp in ("IS", "OOS"):
            s = st(c, smp)
            role = ("base" if c == BASE else "") + (f" top{top.index(c) + 1}" if c in top else "")
            if c in NF.values():
                role = "benchmark 1"
            r = rnd[(c, smp)]
            main_rows.append(dict(combo=c, role=role.strip(), sample=smp,
                                  **{STAT_NAMES[k]: s[k] for k in STAT_COLS},
                                  **{"random mean exp R": float(np.nanmean(r["exp"])) if r["n"] else np.nan,
                                     "random pctile": r["exp_pctile"] if r["n"] else np.nan},
                                  flags=flags(s)))
    main = pd.DataFrame(main_rows)

    # ---------------------------------------------------------------- OOS verdicts for top 3
    oos_rows = []
    for c in top:
        si, so = st(c, "IS"), st(c, "OOS")
        if so["trades"] == 0 or so["expectancy"] <= 0:
            v = "OVERFIT: fails out-of-sample"
        elif so["expectancy"] < 0.5 * si["expectancy"]:
            v = "degrades >50% out-of-sample"
        else:
            v = "holds out-of-sample"
        oos_rows.append(dict(combo=c, IS_trades=si["trades"], IS_exp=si["expectancy"], OOS_trades=so["trades"],
                             OOS_exp=so["expectancy"], OOS_PF=so["profit_factor"],
                             OOS_net_pct=so["net_return_pct"], verdict=v,
                             plateau=plateau_verdict[c], flags=flags(so)))
    oos = pd.DataFrame(oos_rows)

    # ---------------------------------------------------------------- benchmark 1: no filter vs fixed-2R
    b1 = []
    for c in [x for x in COMBOS if settings(x)["target"] == "2R"]:
        nf = NF[settings(c)["be"]]
        row = dict(combo=c, vs=nf)
        for smp in ("IS", "OOS"):
            s, sn = st(c, smp), st(nf, smp)
            if smp == "OOS" and c not in reported:       # only selected/base combos see out-of-sample
                s = dict(trades="not tested", expectancy=np.nan)
            row.update({f"{smp} trades": s["trades"], f"{smp} exp R": s["expectancy"],
                        f"{smp} NF trades": sn["trades"], f"{smp} NF exp R": sn["expectancy"],
                        f"{smp} beats NF": ("-" if s["trades"] == "not tested" else
                                            bool(s["trades"] > 0 and s["expectancy"] > sn["expectancy"]))})
        b1.append(row)
    bench1 = pd.DataFrame(b1)

    # ---------------------------------------------------------------- benchmark 2: random direction
    b2 = []
    for c in reported:
        for smp in ("IS", "OOS"):
            r = rnd[(c, smp)]
            if not r["n"]:
                continue
            e, nr = r["exp"], r["net"]
            b2.append({"combo": c, "sample": smp, "trades": r["n"], "real exp R": r["real_exp"],
                       "random mean": e.mean(), "random p5": np.percentile(e, 5),
                       "random p50": np.percentile(e, 50), "random p95": np.percentile(e, 95),
                       "real exp pctile": r["exp_pctile"], "real net %": r["real_net"],
                       "random net % p50": np.percentile(nr, 50), "random net % p95": np.percentile(nr, 95),
                       "real net pctile": r["net_pctile"]})
    bench2 = pd.DataFrame(b2)

    # ---------------------------------------------------------------- robustness: next-bar open
    rob = []
    for c in reported:
        for smp in ("IS", "OOS", "ALL"):
            s, sn = st(c, smp), st(c + "|nextopen", smp)
            rob.append({"combo": c, "sample": smp, "close: trades": s["trades"], "close: exp R": s["expectancy"],
                        "close: net %": s["net_return_pct"], "next open: trades": sn["trades"],
                        "next open: exp R": sn["expectancy"], "next open: net %": sn["net_return_pct"],
                        "exp diff R": sn["expectancy"] - s["expectancy"]})
    robust = pd.DataFrame(rob)

    # ---------------------------------------------------------------- breakdowns
    wd = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    bd = {}
    for c in reported:
        t = sub(c).copy()
        if t.empty:
            continue
        t["year"] = t["date"].dt.year
        t["weekday"] = pd.Categorical(t["date"].dt.dayofweek.map(dict(enumerate(wd))), wd, ordered=True)
        bd[c] = {k: breakdown(t, k) for k in ("year", "side", "bias_type", "weekday", "exit_reason")}
        bd[c]["sample x side"] = breakdown(t, ["sample", "side"])
        bd[c]["sample x bias_type"] = breakdown(t, ["sample", "bias_type"])

    # ---------------------------------------------------------------- counts
    weekdays = len(days)
    skip_counts = days["skip"].replace("", "traded (not skipped)").value_counts()
    ok = days[days["skip"] != "nyse_holiday"]
    on = ok["on_bars"]
    coverage = pd.DataFrame({"overnight 1m bars (of 930 possible)": [
        on.min(), on.quantile(0.05), on.quantile(0.25), on.median(), on.mean(), on.quantile(0.75), on.max()]},
        index=["min", "p5", "p25", "median", "mean", "p75", "max"])
    coverage["% of window"] = coverage.iloc[:, 0] / 930 * 100
    rth = rth_coverage(days.loc[days["skip"] == "", "date"])
    coverage["RTH 09:30-16:00 1m bars (of 390)"] = [rth.min(), rth.quantile(0.05), rth.quantile(0.25),
                                                    rth.median(), rth.mean(), rth.quantile(0.75), rth.max()]
    gap = ok["max_gap_0700"]
    spreads = spread_table()
    bias_cols = [c for c in days.columns if c.startswith("bias_") and not c.endswith("_active")]
    bias_tab = pd.DataFrame({c[5:]: days.loc[days["skip"] == "", c].value_counts() for c in bias_cols}).fillna(0).astype(int)

    ckeys = ["setups_started", "sweep_extreme_updated", "died_no_drive_in", "died_no_drive_out_5bars",
             "died_entry_window_end", "signals", "signals_skipped", "skip_reward_lt_1.5R", "skip_stop_gt_2xATR15",
             "skip_poc_wrong_side", "skip_no_next_bar", "trades", "day_done_TP", "day_done_2SL",
             "nf_sweep_not_near_va", "sweep_both_sides_same_bar"]
    for k in ckeys:
        if k not in counts:
            counts[k] = 0
    cnt_tab = counts.groupby("variant")[ckeys].sum().astype(int)
    cnt_tab = cnt_tab.loc[[c for c in COMBOS + list(NF.values()) if c in cnt_tab.index]]
    tpd = []
    for c in reported + list(NF.values()):
        k = counts.loc[counts["variant"] == c, "trades"]
        n_tr = len(tradable)
        dist = k.value_counts().reindex(range(0, int(k.max()) + 1 if len(k) else 1), fill_value=0)
        tpd.append({"combo": c, "tradable days": n_tr, "days with 0 trades": n_tr - int((k > 0).sum()),
                    **{f"days with {i}": int(dist.get(i, 0)) for i in range(1, 4)},
                    "days with 4+": int(dist[dist.index >= 4].sum()),
                    "trades / tradable day": k.sum() / n_tr, "trades / traded day": k.sum() / max((k > 0).sum(), 1)})
    tpd = pd.DataFrame(tpd)

    # ---------------------------------------------------------------- files
    cols = ["date", "side", "bias_type", "entry_time", "entry_price", "exit_time", "exit_price", "stop_dist",
            "reward_R", "R", "exit_reason", "stop_price", "tp_price", "spread", "atr15", "poc", "vah", "val",
            "sweep_extreme", "sweep_bar_time", "sample"]
    for c in reported + list(NF.values()):
        t = sub(c)[cols].copy()
        t["equity_after"] = equity(t["R"].to_numpy())
        t.to_csv(f"{out}/trade_logs/{c.replace('|', '_')}.csv", index=False, float_format="%.4f")
    seen_oos = set(reported) | set(NF.values())
    seen = trades["variant"].str.replace("|nextopen", "", regex=False).isin(seen_oos)
    trades.loc[seen | (trades["sample"] == "IS"), ["variant"] + cols + ["r_opp"]].to_csv(
        f"{out}/trade_logs/all_variants.csv", index=False, float_format="%.4f")
    full = []
    for c in sorted(trades["variant"].unique()):
        for smp in (("IS", "OOS", "ALL") if c.replace("|nextopen", "") in seen_oos else ("IS",)):
            full.append(dict(variant=c, sample=smp, **st(c, smp)))
    pd.DataFrame(full).to_csv(f"{out}/all_variant_stats.csv", index=False, float_format="%.4f")
    days.to_csv(f"{out}/days.csv", index=False, float_format="%.3f")
    cnt_tab.to_csv(f"{out}/counts_by_variant.csv")

    charts(trades, reported, top, rnd, out, is_end)

    # ---------------------------------------------------------------- report
    meta = dict(first_day=str(days["date"].min().date()), last_day=str(days["date"].max().date()),
                weekdays=weekdays, tradable_days=len(tradable), is_days=n_is, oos_days=len(tradable) - n_is,
                is_end=str(is_end.date()), oos_start=str(oos_start.date()), combos_tested=len(COMBOS),
                top=top, commission=P.commission, seeds=seeds)
    write_report(out, meta, rank, top, plateau_tables, plateau_verdict, main, oos, bench1, bench2, robust,
                 bd, skip_counts, coverage, gap, spreads, bias_tab, cnt_tab, tpd, base_nb)
    summary = dict(meta, main=main.to_dict("records"), oos=oos.to_dict("records"),
                   bench2=bench2.to_dict("records"))
    with open(f"{out}/summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=str)
    return summary


def rth_coverage(dates: pd.Series) -> pd.Series:
    """1m bars per tradable day in 09:30-16:00 ET."""
    want = set(pd.to_datetime(dates).dt.date)
    out = []
    for y in available_years():
        df = load_year(y)
        m = df.index.hour * 60 + df.index.minute
        sel = (m >= 570) & (m < 960)
        c = pd.Series(1, index=df.index[sel].date).groupby(level=0).size()
        out.append(c[[d in want for d in c.index]])
    return pd.concat(out)


def spread_table() -> pd.DataFrame:
    rows = []
    for y in available_years():
        if y < 2020:
            continue
        df = load_year(y)
        m = df.index.hour * 60 + df.index.minute
        sp = df["ac"] - df["bc"]
        e = (m >= 570) & (m < 660)
        o = (m >= 18 * 60) | (m < 570)
        rows.append({"year": y, "median spread 09:30-11:00": sp[e].median(), "p95 09:30-11:00": sp[e].quantile(.95),
                     "median spread overnight": sp[o].median()})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- charts
def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def charts(trades, reported, top, rnd, out, is_end):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(f"{out}/charts", exist_ok=True)
    color = {c: SLOTS[i] for i, c in enumerate(reported)}          # colour follows the combo
    label = {c: c + (" (base)" if c == BASE else "") + (f" (top {top.index(c) + 1})" if c in top else "")
             for c in reported}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), facecolor=SURFACE, sharey=False)
    for ax, smp in zip(axes, ("IS", "OOS")):
        _style(ax)
        for c in reported + [NF["BEoff"]]:
            t = trades[(trades["variant"] == c) & (trades["sample"] == smp)]
            if t.empty:
                continue
            y = np.r_[0.0, (equity(t["R"].to_numpy()) / 10_000 - 1) * 100]
            x = np.r_[t["entry_time"].iloc[:1].to_numpy(), t["exit_time"].to_numpy()]
            bench = c in NF.values()
            ax.plot(x, y, color=NEUTRAL if bench else color[c], lw=2, ls="--" if bench else "-",
                    drawstyle="steps-post", label="no-filter benchmark (2R, BE off)" if bench else label[c])
            if not bench:                                   # one marker per closed trade
                ax.plot(x[1:], y[1:], ls="none", marker="o", ms=4.5, color=color[c], mec=SURFACE, mew=1)
            ax.annotate(f"{y[-1]:+.0f}%", (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points",
                        fontsize=8, color=INK2, va="center")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_title(("In-sample" if smp == "IS" else "Out-of-sample") + " equity, % return (1% risk, compounding)",
                     fontsize=10, color=INK, loc="left")
    axes[0].legend(fontsize=7.5, frameon=False, labelcolor=INK, loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{out}/charts/equity_is_oos.png", dpi=130)
    plt.close(fig)

    keys = [(c, s) for c in reported for s in ("IS", "OOS") if rnd[(c, s)]["n"]]
    if keys:
        fig, axes = plt.subplots(len(reported), 2, figsize=(11, 2.3 * len(reported)), facecolor=SURFACE,
                                 squeeze=False)
        for i, c in enumerate(reported):
            for j, smp in enumerate(("IS", "OOS")):
                ax = axes[i, j]
                _style(ax)
                r = rnd[(c, smp)]
                if not r["n"]:
                    ax.set_visible(False)
                    continue
                ax.hist(r["exp"], bins=40, color=color[c], edgecolor=SURFACE, linewidth=0.5)
                ax.axvline(r["real_exp"], color=INK, lw=2)
                ax.annotate(f"real {r['real_exp']:+.2f}R, {r['exp_pctile']:.0f}th pct", (r["real_exp"], 1),
                            xycoords=("data", "axes fraction"), xytext=(5, -4), textcoords="offset points",
                            fontsize=8, color=INK, va="top",
                            bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none"))
                ax.set_title(f"{label[c]}, {'in' if smp == 'IS' else 'out-of'}-sample, {r['n']} trades: "
                             f"expectancy (R) of {len(r['exp'])} random-direction seeds", fontsize=8.5,
                             color=INK, loc="left")
        fig.tight_layout()
        fig.savefig(f"{out}/charts/random_benchmark.png", dpi=130)
        plt.close(fig)


# --------------------------------------------------------------------------- report text
def write_report(out, meta, rank, top, plateau_tables, plateau_verdict, main, oos, bench1, bench2, robust,
                 bd, skip_counts, coverage, gap, spreads, bias_tab, cnt_tab, tpd, base_nb):
    L = []
    w = L.append
    w("# Nasdaq 100 CFD: overnight volume profile + 15m bias + 1m sweep entries\n")
    w(f"Data: Dukascopy **USATECH.IDX/USD** (feed symbol `USATECHIDXUSD`), 1-minute **BID and ASK** candles, "
      f"{meta['first_day']} to {meta['last_day']} (New York dates). All times America/New_York (zoneinfo, DST "
      f"handled). Fills use the real bid/ask; signals use mid = (bid + ask) / 2.\n")
    w("**Volume is TICK VOLUME, not real volume**: the profile is weighted by Dukascopy's 1m candle volume "
      "(BID side), a tick-activity figure from the broker's own feed. It is not exchange volume and not a raw "
      "tick count; only its relative size inside one night matters for POC / value area.\n")
    w(f"1 unit = $1 per index point, fractional units. Risk 1% of current equity per trade (compounding), "
      f"$10,000 start. Commission: ${meta['commission']:.2f} per unit round turn.\n")
    w(f"**Combos tested: {meta['combos_tested']}** (the ranked sweep). Plus 2 no-filter benchmark runs, "
      f"16 next-bar-open robustness runs (not ranked) and {meta['seeds']} random-direction seeds per reported "
      f"combo and sample.\n")
    w(f"Split: tradable days in time order, first 60% in-sample (**{meta['is_days']} days, to "
      f"{meta['is_end']}**), last 40% out-of-sample (**{meta['oos_days']} days, from {meta['oos_start']}**). "
      f"Ranking uses in-sample expectancy only, minimum {MIN_TRADES} in-sample trades.\n")
    if os.path.exists(f"{out}/VERDICT.md"):
        w(open(f"{out}/VERDICT.md").read().strip() + "\n")

    w("## 1. Headline: base setup and top 3, in-sample and out-of-sample, next to the benchmarks\n")
    w("Benchmark 1 = no-filter (1m pattern both directions near VAH/VAL, fixed 2R). Benchmark 2 = random "
      "direction at the same timestamps (mean expectancy of the seeds, and the percentile where the real "
      "result lands).\n")
    w(md(main) + "\n")
    w("![equity](charts/equity_is_oos.png)\n")

    w("## 2. In-sample ranking of all 16 combos (expectancy in R, >= 100 trades)\n")
    w(md(rank) + "\n")
    if len(top) < 3:
        w(f"**{len(top)} of 16 combos reach {MIN_TRADES} in-sample trades** (most: "
          f"{int(rank['trades'].max())}), so {'only those go' if top else 'nothing goes'} to out-of-sample "
          f"(agreed rule: only qualifiers are tested). Non-qualifying combos are listed for information, not "
          f"ranked, and their out-of-sample results are not computed in this report or its files.\n")
    w("## 3. Out-of-sample test of the in-sample top combos (chosen on in-sample only)\n")
    w(md(oos) + "\n" if len(oos) else "No combo qualified, so no combo was selected and none was tested "
      "out-of-sample. The base setup's out-of-sample row in section 1 is shown only because it was fixed in "
      "advance; it is not a selection.\n")
    w("### Plateau check (combos one setting away, in-sample)\n")
    for c in top:
        w(f"**{c}**: {plateau_verdict[c]}\n")
        w(md(plateau_tables[c]) + "\n")
    if not top:
        w("No top combo to check. For information, the base setup's in-sample neighbours:\n")
        w(md(base_nb) + "\n")

    w("## 4. Benchmark 1: no-filter vs the strategy's fixed-2R variants\n")
    w("Same 1m pattern, stops, risk and daily limits; both directions allowed whenever the swept level is within "
      "1 x ATR(14, 15m) of VAH or VAL, 09:30-11:00, fixed 2R. Each fixed-2R combo is compared with the "
      "no-filter run that has the same break-even setting.\n")
    w(md(bench1) + "\n")
    w("## 5. Benchmark 2: random direction (same trades, timestamps, stop distance, target multiple)\n")
    w(md(bench2) + "\n")
    w("![random](charts/random_benchmark.png)\n")
    w("## 6. Robustness: entry at the next bar's open instead of the signal bar's close (not ranked)\n")
    w("Decision, stop price and target price are fixed at the signal bar's close; the fill moves to the next "
      "bar's open (buy at ask, sell at bid). R = P/L / planned 1R, so the delay's cost shows up in R.\n")
    w(md(robust) + "\n")

    w("## 7. Breakdowns (full period)\n")
    for c, tabs in bd.items():
        w(f"### {c}\n")
        for k, t in tabs.items():
            w(f"By {k}:\n\n" + md(t, index=True) + "\n")

    w("## 8. Counts\n")
    if os.path.exists(f"{out}/funnel.md"):
        w(open(f"{out}/funnel.md").read().strip() + "\n")
    w(f"Weekdays in range: {meta['weekdays']:,}. Tradable (not skipped): {meta['tradable_days']:,}.\n")
    w("Days skipped or traded, by reason:\n\n" + md(skip_counts.rename("days").to_frame(), index=True) + "\n")
    w("Typical session coverage (non-holiday weekdays for the overnight window; tradable days for RTH):\n\n"
      + md(coverage, index=True) + "\n")
    w(f"Longest pre-market hole 07:00-09:30: median {gap.median():.0f} min, p95 {gap.quantile(.95):.0f} min, "
      f"days over 30 min: {(gap > 30).sum()}.\n")
    w("Spread (ask - bid at the close of each 1m bar, index points):\n\n" + md(spreads) + "\n")
    w("15m bias outcome per tradable day (+ long, - short):\n\n" + md(bias_tab, index=True) + "\n")
    w("Setups, signals, skips and deaths per combo (full period; a skipped signal can fail several E6 checks, "
      "so reason counts can add up to more than `signals_skipped`):\n\n" + md(cnt_tab, index=True) + "\n")
    w("Trades per day:\n\n" + md(tpd) + "\n")

    w("## 9. Modelling decisions\n")
    for line in DECISIONS:
        w(f"* {line}")
    w("\n## Files\n")
    w("* `trade_logs/<combo>.csv`: trade log for the base, the top combos and the benchmarks; "
      "`trade_logs/all_variants.csv`: every variant (incl. next-open runs).")
    w("* `all_variant_stats.csv`, `counts_by_variant.csv`, `days.csv` (levels, coverage, skip reason, bias per "
      "day), `summary.json`, `charts/`.")
    w("* Code: `nqvp/` (data, core rules, engine, stats, report), `run_nqvp.py`, tests `tests/test_nqvp.py`.")
    with open(f"{out}/REPORT.md", "w") as f:
        f.write("\n".join(L) + "\n")


DECISIONS = [
    "Signals (profile, 15m bars, swings, sweeps, gaps, bodies, ATR) use mid bars; this makes long and short exact "
    "mirrors. Buys fill at ask, sells at bid; longs exit on bid, shorts on ask.",
    "Profile bins are [k, k+1) index points; a bar's volume is split equally over every bin from its low's bin "
    "to its high's bin. POC = centre of the top bin (ties: lowest bin); VAH/VAL = top/bottom edge of the value "
    "area. Value-area step: compare the next two bins above vs below, add ONE bin on the heavier side; on an "
    "exact tie add one bin on each side.",
    "Overnight window = 1m bars opening 18:00 the prior calendar day to 09:29 (Sunday 18:00 for Monday). Skip if "
    "< 360 bars, or > 30 consecutive missing minutes between 07:00 and 09:30 (edges included). NYSE full-day "
    "holidays (holidays.NYSE) are not traded. Early-close days are traded; the time exit then uses the last bar "
    "before 16:00.",
    "15m bars are built from 1m bars on the :00/:15/:30/:45 clock and are usable at their end time. B1 window = "
    "the sweep bar plus the next 4 eligible 15m bars. If one 15m bar confirms B1 long and B1 short together the "
    "day has no bias (counted as conflict). If B1 and B2 confirm on the same bar (same side only) B1 wins.",
    "Swing low = low strictly below the 5 bars on each side, usable from the 6th bar after it. The 'obvious low' "
    "must also be intact (no later bar traded below it), so a level already taken is not swept twice.",
    "Setups start only from a sweep bar that opens at/after max(09:30, bias active time) (your choice). The "
    "drive-in window and swing history can reach back before that. Entry = close of a drive-out bar that "
    "closes by 11:00.",
    "ATR(20, 1m) for the body tests includes the bar being tested (a closed bar, as a chart indicator shows it). "
    "ATR(14, 15m) = mean true range of the last 14 closed 15m bars at the signal bar's close.",
    "If drive-in fails for the current sweep extreme, the setup stays alive: a lower low can restart the clock "
    "with a new extreme that is re-tested. Otherwise it dies 5 bars after the extreme. A drive-out bar cannot "
    "itself print a new extreme (a new extreme restarts the clock instead).",
    "Stop = sweep extreme -/+ the spread at the signal bar's close. 1R = |fill - stop|. B1 POC target: TP = POC; "
    "reward = (POC - entry) / 1R. Fixed targets: 2R from the fill. E6 skips (reward < 1.5R, stop > 2 x ATR15, "
    "B1 with POC on the wrong side, which applies to all B1 trades incl. the 2R variants: your choice).",
    "Exits per bar: stop first (a bar opening through the stop fills at its open), then TP (limit at TP, also "
    "when the bar gaps over it: no positive slippage), then the +1R break-even trigger; the BE stop is live from "
    "the next bar. No exit by 16:00: close of the last bar before 16:00. Exit times are the minute bar in which "
    "the fill happened (16:00 for the time exit).",
    "Daily limits: a TP ends the day; two stop-losses in a row end the day; a BE exit neither adds to nor resets "
    "the count; no new setup while a trade is open; the next setup can start on the bar after the exit.",
    "No-filter benchmark: long and short machines, one setup at a time; a sweep counts only if the swept level is "
    "within 1 x ATR(14, 15m) of VAH or VAL at the sweep bar's close; a bar sweeping both sides is ignored.",
    "Random benchmark: each real trade keeps its timestamp, stop distance and target multiple (and BE rule); a "
    "fair coin picks the side; the opposite-side outcome is simulated by the engine at the same bar. Daily "
    "limits are not re-applied. 1000 seeds.",
]
