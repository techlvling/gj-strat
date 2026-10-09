"""Dragonfly Intercept - Phase 1 (2020-01-01 -> latest stored day) on GBPJPY and EURUSD.

    python -m pytest -q tests/test_dragonfly.py     # rule tests first
    python run_dragonfly.py [--seeds 1000] [--commission 0] [--out results/dragonfly]

6 combos (R in 0.382/0.5/0.618 x T1/T2), identical on both pairs. Ranked on the first 60% of the
period (in-sample) by the average of the two pairs' expectancy in R, min 100 trades per pair.
Only the top 3 are evaluated on the last 40% (out-of-sample). Benchmarks: chase (market entry at
the completion close) and 1000-seed random entry. Phase 2 (2010-2019) is NOT run here.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import zlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dragonfly.benchmarks import percentile_of, random_benchmark
from dragonfly.data import PIP, SPREAD_PIPS, data_gaps, load_15m, to_hourly
from dragonfly.engine import Bars, Params, run
from dragonfly.indicators import atr, hourly_to_15m, legs, trend_1h

PAIRS = ["GBPJPY", "EURUSD"]
RETRACES = [0.382, 0.5, 0.618]
TARGETS = ["T1", "T2"]
COMBOS = [(r, t) for r in RETRACES for t in TARGETS]
IS_FRAC = 0.6
MIN_TRADES = 100
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def name(c):
    return f"chase_{c[1]}" if c[0] == "chase" else f"R{c[0]}_{c[1]}"


# ----------------------------------------------------------------------------- setup
def prepare(sym: str) -> tuple[Bars, pd.DataFrame]:
    df = load_15m(sym)
    hourly = to_hourly(df)
    b = Bars(t=pd.DatetimeIndex(df.index), **{k: df[k].to_numpy(float) for k in
             ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "usd_per_quote")},
             atr15=atr(df["bh"].to_numpy(float), df["bl"].to_numpy(float), df["bc"].to_numpy(float), 14),
             trend=hourly_to_15m(df.index, hourly.index, trend_1h(hourly)).astype(np.int8))
    b.legs = legs(b.bh, b.bl, b.atr15)
    return b, df


def seg_of(times: pd.Series, split: pd.Timestamp) -> np.ndarray:
    return np.where(pd.to_datetime(times) < split, "IS", "OOS")


# ----------------------------------------------------------------------------- metrics
def session_of(ts: pd.Series) -> pd.Series:
    h = pd.to_datetime(ts).dt.hour
    return pd.Series(np.where((h >= 7) & (h < 13), "London", np.where((h >= 13) & (h < 21), "New York", "Asia")),
                     index=ts.index)


def equity_path(R: np.ndarray, risk=0.01, start=10_000.0) -> np.ndarray:
    return start * np.cumprod(np.r_[1.0, 1 + risk * R])


def max_dd(eq: np.ndarray) -> float:
    peak = np.maximum.accumulate(eq)
    return float(((peak - eq) / peak).max() * 100) if len(eq) else 0.0


def longest_streak(R: np.ndarray) -> int:
    best = cur = 0
    for r in R:
        cur = cur + 1 if r < 0 else 0
        best = max(best, cur)
    return best


def trade_stats(tr: pd.DataFrame) -> dict:
    R = tr["R"].to_numpy(float) if len(tr) else np.array([])
    n = len(R)
    if n == 0:
        return {"trades": 0}
    eq = equity_path(R)
    win, loss = R[R > 0], R[R < 0]
    return {"trades": n, "win_rate": 100 * len(win) / n, "avg_R": R.mean(),
            "avg_win_R": win.mean() if len(win) else np.nan,
            "avg_loss_R": loss.mean() if len(loss) else np.nan,
            "profit_factor": win.sum() / -loss.sum() if len(loss) else np.inf,
            "total_R": R.sum(), "net_return_pct": (eq[-1] / eq[0] - 1) * 100,
            "max_dd_pct": max_dd(eq), "max_dd_R": float((np.maximum.accumulate(np.r_[0, R.cumsum()]) - np.r_[0, R.cumsum()]).max()),
            "longest_losing_streak": longest_streak(R),
            "pct_be_exits": 100 * (tr["exit_reason"] == "BE").mean(),
            "pct_held_over_rollover": 100 * (tr["rollovers"] > 0).mean(),
            "median_bars_held": float(tr["bars_held"].median()),
            "open_at_end": int((tr["exit_reason"] == "END").sum()),
            "buys": int((tr["side"] == "buy").sum()), "sells": int((tr["side"] == "sell").sum())}


def flow_counts(out: dict, seg: str, split) -> dict:
    s, o = out["signals"], out["orders"]
    s = s[seg_of(s["signal_time"], split) == seg] if len(s) else s
    o = o[seg_of(o["signal_time"], split) == seg] if len(o) else o
    so = s["outcome"].value_counts() if len(s) else pd.Series(dtype=int)
    oo = o["outcome"].value_counts() if len(o) else pd.Series(dtype=int)
    placed = len(o)
    filled = int(oo.get("filled", 0))
    return {"signals": len(s), "orders_placed": placed, "filled": filled,
            "fill_rate_pct": 100 * filled / placed if placed else np.nan,
            "fills_per_signal_pct": 100 * filled / len(s) if len(s) else np.nan,
            "skip_pending": int(so.get("skip_pending", 0)), "skip_position": int(so.get("skip_position", 0)),
            "skip_small_stop": int(so.get("skip_small_stop", 0)),
            "skip_target_reached": int(so.get("skip_target_reached", 0)),
            "cancel_786_at_signal": int(oo.get("cancel_786_at_signal", 0)),
            "cancel_786": int(oo.get("cancel_786", 0)), "cancel_trend": int(oo.get("cancel_trend", 0)),
            "cancel_expired": int(oo.get("cancel_expired", 0)), "open_at_end": int(oo.get("open_at_end", 0)),
            "unfilled_orders": placed - filled}


def breakdown(tr: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = tr.copy()
    et = pd.to_datetime(t["entry_time"])
    t["year"], t["month"], t["session"] = et.dt.year, et.dt.month, session_of(t["entry_time"])
    out = {}
    for key in ("year", "pair", "side", "session", "month"):
        g = t.groupby(key)["R"]
        out[key] = pd.DataFrame({"trades": g.size(), "win_rate": g.apply(lambda r: 100 * (r > 0).mean()),
                                 "avg_R": g.mean(), "total_R": g.sum()})
    return out


# ----------------------------------------------------------------------------- formatting
def fmt(v, nd=2):
    if isinstance(v, (float, np.floating)):
        if np.isnan(v):
            return "-"
        if np.isinf(v):
            return "inf"
        return f"{v:.{nd}f}"
    return str(v)


def md_table(df: pd.DataFrame, nd=2) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
             "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [fmt(v, nd) for v in row.to_numpy()]) + " |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- charts
def style(ax, title):
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)


def plot_equity(curves: dict, path: str, title: str):
    """curves: {pair: [(label, times, equity, is_benchmark)]}"""
    fig, axes = plt.subplots(len(curves), 1, figsize=(11.5, 3.4 * len(curves)), sharex=False)
    axes = np.atleast_1d(axes)
    for ax, (pair, lines) in zip(axes, curves.items()):
        k = 0
        for label, t, eq, bench in lines:
            if bench:
                ax.plot(t, eq, color=MUTED, lw=1.2, ls="--" if label.endswith("T1") else ":", label=label)
            else:
                ax.plot(t, eq, color=SERIES[k % len(SERIES)], lw=1.6, label=label)
                k += 1
        ax.axhline(10_000, color=MUTED, lw=0.6)
        style(ax, f"{pair} - {title}")
        ax.set_ylabel("equity, USD (start 10,000)", fontsize=8, color=MUTED)
        ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_random(items: list, path: str):
    """items: (label, dist avg_R, real avg_R, chase avg_R)"""
    fig, axes = plt.subplots(len(items), 1, figsize=(8, 2.0 * len(items)))
    axes = np.atleast_1d(axes)
    for ax, (label, dist, real, chase) in zip(axes, items):
        ax.hist(dist, bins=40, color="#2a78d6", alpha=0.85, rwidth=0.9)
        ax.axvline(real, color=INK, lw=2, label=f"dragonfly {real:+.3f}R")
        if chase is not None and np.isfinite(chase):
            ax.axvline(chase, color="#eb6834", lw=2, ls="--", label=f"chase {chase:+.3f}R")
        style(ax, label)
        ax.legend(fontsize=7, frameon=False)
    axes[-1].set_xlabel("average R per trade (1000 random-entry seeds)", fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--commission", type=float, default=0.0, help="USD per 100k units round turn")
    ap.add_argument("--swap-long", type=float, default=0.0)
    ap.add_argument("--swap-short", type=float, default=0.0)
    ap.add_argument("--out", default="results/dragonfly")
    a = ap.parse_args()
    out_dir = a.out
    for d in ("", "trade_logs", "charts", "breakdowns"):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)

    bars, gaps = {}, {}
    for sym in PAIRS:
        bars[sym], df = prepare(sym)
        gaps[sym] = data_gaps(df)
    start = max(b.t[0] for b in bars.values())
    end = max(b.t[-1] for b in bars.values()) + pd.Timedelta(minutes=15)
    split = (start + IS_FRAC * (end - start)).floor("15min")
    print(f"Phase 1 {start} -> {end}, split {split}", flush=True)

    def params(sym, **kw):
        return Params(spread=SPREAD_PIPS[sym] * PIP[sym], commission_per_lot=a.commission,
                      swap_long_per_lot=a.swap_long, swap_short_per_lot=a.swap_short, **kw)

    runs, chase = {}, {}
    for sym in PAIRS:
        for c in COMBOS:
            runs[sym, c] = run(bars[sym], params(sym, retrace=c[0], target=c[1]))
        for t in TARGETS:
            chase[sym, t] = run(bars[sym], params(sym, target=t, mode="chase"))
        print(f"{sym} simulated", flush=True)

    for (sym, c), o in list(runs.items()) + [((s, ("chase", t)), o) for (s, t), o in chase.items()]:
        tr = o["trades"]
        if len(tr):
            tr.insert(0, "pair", sym)
            tr.insert(1, "combo", name(c))
            tr.insert(2, "segment", seg_of(tr["signal_time"], split))
            tr["leg_pips"] = tr["leg"] / PIP[sym]
            tr["stop_dist_pips"] = tr["stop_dist"] / PIP[sym]

    def seg_trades(o, seg):
        tr = o["trades"]
        return tr[tr["segment"] == seg] if len(tr) else tr

    # trend-filter and leg counts per segment
    leg_counts = {}
    for sym, b in bars.items():
        sig_t = b.t + pd.Timedelta(minutes=15)
        for seg in ("IS", "OOS"):
            m = (sig_t < split) if seg == "IS" else (sig_t >= split)
            leg_counts[sym, seg] = {
                "valid_legs_buy": int((b.legs["buy"] & m).sum()),
                "valid_legs_sell": int((b.legs["sell"] & m).sum()),
                "legs_blocked_by_trend_filter": int(((b.legs["buy"] & (b.trend != 1)) |
                                                     (b.legs["sell"] & (b.trend != -1)))[m].sum()),
                "pct_bars_trend_up": 100 * float((b.trend[m] == 1).mean()),
                "pct_bars_trend_down": 100 * float((b.trend[m] == -1).mean())}

    # ------------------------------------------------------------ random benchmark helper
    rand_cache = {}

    def random_for(sym, c, seg):
        key = (sym, c, seg)
        if key in rand_cache:
            return rand_cache[key]
        b = bars[sym]
        tr = seg_trades(runs[sym, c], seg)
        sig_t = b.t + pd.Timedelta(minutes=15)
        m = ((sig_t < split) if seg == "IS" else (sig_t >= split)) & np.isfinite(b.atr15)
        m[-1] = False
        elig = {1: np.flatnonzero(m & (b.trend == 1)), -1: np.flatnonzero(m & (b.trend == -1))}
        d = float(tr["stop_dist"].median())
        mult = float(tr["target_R_planned"].median())
        comm_R = a.commission / (1e5 * d * float(np.median(b.usd_per_quote)))
        dist = random_benchmark(b, elig, {1: int((tr["side"] == "buy").sum()),
                                          -1: int((tr["side"] == "sell").sum())},
                                d, mult, seeds=a.seeds, comm_R=comm_R,
                                seed0=zlib.crc32(f"{sym}{name(c)}{seg}".encode()))
        st = trade_stats(tr)
        res = {"stop_dist_pips": d / PIP[sym], "target_multiple": mult, "dist": dist,
               "real_avg_R": st["avg_R"], "real_net_return": st["net_return_pct"] / 100,
               "pct_avg_R": percentile_of(st["avg_R"], dist["avg_R"]),
               "pct_net_return": percentile_of(st["net_return_pct"] / 100, dist["net_return"])}
        res.update({f"rand_avg_R_{q}": float(np.percentile(dist["avg_R"], q)) for q in (5, 50, 95)})
        res.update({f"rand_ret_{q}": 100 * float(np.percentile(dist["net_return"], q)) for q in (5, 50, 95)})
        rand_cache[key] = res
        print(f"random {sym} {name(c)} {seg}: real {st['avg_R']:+.3f}R at pct {res['pct_avg_R']:.1f}", flush=True)
        return res

    def block(seg, combos):
        """Per pair x combo rows: dragonfly stats, flow, chase, random."""
        rows = []
        for c in combos:
            for sym in PAIRS:
                st = trade_stats(seg_trades(runs[sym, c], seg))
                fl = flow_counts(runs[sym, c], seg, split)
                ch = trade_stats(seg_trades(chase[sym, c[1]], seg))
                rnd = random_for(sym, c, seg) if st["trades"] else {}
                rows.append({"combo": name(c), "pair": sym, **st, **fl,
                             **{f"chase_{k}": v for k, v in ch.items()},
                             **{f"random_{k}": v for k, v in rnd.items() if k != "dist"}})
        return pd.DataFrame(rows)

    # ------------------------------------------------------------ in-sample: all 6, rank
    is_df = block("IS", COMBOS)
    pv = is_df.pivot(index="combo", columns="pair", values="avg_R")
    rank = pd.DataFrame({"avg_expectancy_R": pv.mean(axis=1), "gbpjpy_R": pv["GBPJPY"], "eurusd_R": pv["EURUSD"],
                         "min_trades": is_df.groupby("combo")["trades"].min()})
    rank.index.name = "combo"
    rank["eligible"] = rank["min_trades"] >= MIN_TRADES
    rank = rank.sort_values(["eligible", "avg_expectancy_R"], ascending=[False, False])
    rank["rank"] = np.arange(1, len(rank) + 1)
    top = [c for c in COMBOS if name(c) in rank[rank["eligible"]].index[:3]]
    top.sort(key=lambda c: rank.loc[name(c), "rank"])
    print("in-sample ranking:\n", rank, flush=True)

    # plateau check
    plateau = []
    for c in top:
        ri = RETRACES.index(c[0])
        neigh = [(RETRACES[j], c[1]) for j in (ri - 1, ri + 1) if 0 <= j < len(RETRACES)]
        neigh.append((c[0], "T2" if c[1] == "T1" else "T1"))
        ns = [rank.loc[name(x), "avg_expectancy_R"] for x in neigh]
        own = rank.loc[name(c), "avg_expectancy_R"]
        noise = own > 0 and (np.mean(ns) <= 0 or np.mean(ns) < 0.5 * own)
        plateau.append({"pick": name(c), "pick_R": own,
                        "neighbours": ", ".join(f"{name(x)} {v:+.3f}" for x, v in zip(neigh, ns)),
                        "neighbour_mean_R": float(np.mean(ns)), "likely_noise": bool(noise)})
    plateau = pd.DataFrame(plateau).set_index("pick") if plateau else pd.DataFrame()

    # ------------------------------------------------------------ out-of-sample: top 3 only
    oos_df = block("OOS", top) if top else pd.DataFrame()

    # ------------------------------------------------------------ flags
    def flags_for(df):
        fl = []
        for _, r in df.iterrows():
            tag = f"{r['combo']} {r['pair']}"
            if r["trades"] < MIN_TRADES:
                fl.append(f"{tag}: only {r['trades']} trades (< {MIN_TRADES})")
            if r["trades"] and (r["profit_factor"] > 3 or r["avg_R"] > 0.75):
                fl.append(f"{tag}: unrealistically good (PF {r['profit_factor']:.2f}, avg {r['avg_R']:+.2f}R) - check")
        return fl

    def beats(df):
        out = {}
        for combo, g in df.groupby("combo", sort=False):
            out[combo] = {
                "avg_R_both_pairs": float(g["avg_R"].mean()),
                "positive_both_pairs": bool((g["avg_R"] > 0).all()),
                "beats_chase_both_pairs": bool((g["avg_R"] > g["chase_avg_R"]).all()),
                "beats_random_95pct_both_pairs": bool((g["random_pct_avg_R"] >= 95).all()),
                "random_percentiles": {p: float(v) for p, v in zip(g["pair"], g["random_pct_avg_R"])}}
            out[combo]["useful"] = (out[combo]["positive_both_pairs"] and out[combo]["beats_chase_both_pairs"]
                                    and out[combo]["beats_random_95pct_both_pairs"])
        return out

    is_beats, oos_beats = beats(is_df), beats(oos_df) if len(oos_df) else {}
    oos_fail = [c for c, v in oos_beats.items() if not (v["positive_both_pairs"] and v["avg_R_both_pairs"] > 0)]

    # ------------------------------------------------------------ trade logs
    log_cols = ["pair", "combo", "segment", "side", "signal_time", "entry_time", "entry_price",
                "exit_time", "exit_price", "leg", "leg_pips", "leg_atr", "stop", "tp", "stop_dist",
                "stop_dist_pips", "target_R_planned", "R", "exit_reason", "exit_gap", "fill_gap",
                "bars_to_fill", "be_rule_on", "be_moved", "bars_held", "rollovers", "risk_usd",
                "pnl_usd", "equity_after", "H", "L", "order_price", "buffer", "atr15"]
    all_logs = []
    for (sym, c), o in runs.items():
        if len(o["trades"]):
            all_logs.append(o["trades"][log_cols])
    for (sym, t), o in chase.items():
        if len(o["trades"]):
            all_logs.append(o["trades"][log_cols])
    logs = pd.concat(all_logs, ignore_index=True)
    for (pair, combo), g in logs.groupby(["pair", "combo"]):
        g.to_csv(f"{out_dir}/trade_logs/{pair}_{combo}.csv", index=False)
    orders = pd.concat([o["orders"].assign(pair=s, combo=name(c)) for (s, c), o in runs.items() if len(o["orders"])])
    orders["segment"] = seg_of(orders["signal_time"], split)
    orders.to_csv(f"{out_dir}/trade_logs/orders.csv", index=False)
    is_df.to_csv(f"{out_dir}/in_sample_all6.csv", index=False)
    if len(oos_df):
        oos_df.to_csv(f"{out_dir}/out_of_sample_top3.csv", index=False)
    rank.to_csv(f"{out_dir}/in_sample_ranking.csv")

    # ------------------------------------------------------------ breakdowns (top 3)
    bd_md = {}
    for c in top:
        for seg in ("IS", "OOS"):
            tr = pd.concat([seg_trades(runs[s, c], seg) for s in PAIRS])
            bd = breakdown(tr)
            for k, v in bd.items():
                v.to_csv(f"{out_dir}/breakdowns/{name(c)}_{seg}_{k}.csv")
            if c == top[0]:
                bd_md[seg] = bd
                for sym in PAIRS:
                    bd_md[seg, sym] = breakdown(seg_trades(runs[sym, c], seg))

    # ------------------------------------------------------------ charts
    def curve(tr, label, bench=False):
        if not len(tr):
            return None
        t = pd.to_datetime(pd.concat([pd.Series([tr["entry_time"].iloc[0]]), tr["exit_time"]]))
        return (label, t.to_numpy(), equity_path(tr["R"].to_numpy(float)), bench)

    for seg, combos in (("IS", COMBOS), ("OOS", top)):
        if not combos:
            continue
        curves = {}
        for sym in PAIRS:
            lines = [curve(seg_trades(runs[sym, c], seg), name(c)) for c in combos]
            lines += [curve(seg_trades(chase[sym, t], seg), f"chase {t}", True) for t in TARGETS]
            curves[sym] = [x for x in lines if x]
        label = "in-sample, all 6 combos" if seg == "IS" else "out-of-sample, top 3 (in-sample ranked)"
        plot_equity(curves, f"{out_dir}/charts/equity_{seg}.png", label)
    items = []
    for c in top:
        for sym in PAIRS:
            for seg in ("IS", "OOS"):
                rnd = rand_cache.get((sym, c, seg))
                if rnd:
                    ch = trade_stats(seg_trades(chase[sym, c[1]], seg)).get("avg_R")
                    items.append((f"{sym} {name(c)} {seg}: pct {rnd['pct_avg_R']:.1f}", rnd["dist"]["avg_R"],
                                  rnd["real_avg_R"], ch))
    if items:
        plot_random(items, f"{out_dir}/charts/random_benchmark.png")

    # ------------------------------------------------------------ report
    def perf_table(df, chase_cols=True):
        cols = ["trades", "fill_rate_pct", "win_rate", "avg_R", "avg_win_R", "avg_loss_R", "profit_factor",
                "max_dd_pct", "longest_losing_streak", "net_return_pct", "pct_held_over_rollover"]
        t = df.set_index(df["combo"] + " " + df["pair"])[cols]
        t.index.name = "combo / pair"
        return md_table(t)

    def bench_table(df):
        t = pd.DataFrame({
            "dragonfly trades": df["trades"].to_numpy(), "dragonfly avg R": df["avg_R"].to_numpy(),
            "dragonfly return %": df["net_return_pct"].to_numpy(),
            "chase trades": df["chase_trades"].to_numpy(), "chase avg R": df["chase_avg_R"].to_numpy(),
            "chase win %": df["chase_win_rate"].to_numpy(), "chase PF": df["chase_profit_factor"].to_numpy(),
            "chase maxDD %": df["chase_max_dd_pct"].to_numpy(), "chase return %": df["chase_net_return_pct"].to_numpy(),
            "random avg R p5/p50/p95": [f"{a:+.3f} / {b:+.3f} / {c:+.3f}" for a, b, c in
                                        zip(df["random_rand_avg_R_5"], df["random_rand_avg_R_50"], df["random_rand_avg_R_95"])],
            "real pct (avg R)": df["random_pct_avg_R"].to_numpy(),
            "random return % p5/p50/p95": [f"{a:+.1f} / {b:+.1f} / {c:+.1f}" for a, b, c in
                                           zip(df["random_rand_ret_5"], df["random_rand_ret_50"], df["random_rand_ret_95"])],
            "real pct (return)": df["random_pct_net_return"].to_numpy(),
            "rand stop pips / tgt x": [f"{a:.1f} / {b:.2f}" for a, b in zip(df["random_stop_dist_pips"], df["random_target_multiple"])],
        }, index=pd.Index(df["combo"] + " " + df["pair"], name="combo / pair"))
        return md_table(t, 3)

    def flow_table(df):
        cols = ["signals", "skip_pending", "skip_position", "skip_small_stop", "orders_placed", "filled",
                "fill_rate_pct", "cancel_786_at_signal", "cancel_786", "cancel_trend", "cancel_expired",
                "open_at_end", "unfilled_orders"]
        t = df.set_index(df["combo"] + " " + df["pair"])[cols]
        t.index.name = "combo / pair"
        return md_table(t, 1)

    chase_flow = []
    for (sym, t), o in chase.items():
        for seg in ("IS", "OOS"):
            f = flow_counts(o, seg, split)
            chase_flow.append({"run": f"chase {t} {sym} {seg}", **{k: f[k] for k in
                               ("signals", "skip_position", "skip_small_stop", "skip_target_reached", "filled")}})
    chase_flow = pd.DataFrame(chase_flow).set_index("run")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    L = []
    w = L.append
    w("# Dragonfly Intercept - Phase 1 report\n")
    w("Plain-English verdict: `VERDICT.md` (written after reviewing these tables). Unit tests: `unit_tests.txt`.\n")
    w(f"Data: Dukascopy BID+ASK (1m aggregated to 15m and 1H, UTC), {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M}. "
      f"In-sample {start:%Y-%m-%d} -> {split:%Y-%m-%d %H:%M} (60%), out-of-sample {split:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d} (40%). "
      f"Trades belong to the segment of their signal time. Each segment starts at $10,000 per pair, 1% risk compounding. "
      f"Commission ${a.commission}/lot, swap long/short {a.swap_long}/{a.swap_short} USD/lot/night. "
      f"Nominal spread (buffer + 3x rule): GBPJPY {SPREAD_PIPS['GBPJPY']} pips, EURUSD {SPREAD_PIPS['EURUSD']} pips; fills use real bid/ask. "
      f"Random benchmark: {a.seeds} seeds. Code commit {commit}.\n")
    w(f"**Combos tested: {len(COMBOS)}** (R 0.382/0.5/0.618 x T1/T2), identical parameters on both pairs. "
      "No other parameter was varied.\n")
    w("## 1. In-sample ranking (the only basis for selection)\n")
    w("Ranked by the average of the two pairs' in-sample expectancy (avg R per trade); a combo needs >= 100 "
      "in-sample trades on BOTH pairs to be eligible.\n")
    w(md_table(rank[["rank", "avg_expectancy_R", "gbpjpy_R", "eurusd_R", "min_trades", "eligible"]], 3) + "\n")
    w(f"Top 3 taken to out-of-sample: **{', '.join(name(c) for c in top) or 'none'}**\n")
    w("## 2. In-sample, all 6 combos\n")
    w("avg R = expectancy per trade in R (win% x avg win + loss% x avg loss). Max DD is on closed-trade equity. "
      "Losing streak counts consecutive R < 0 trades (a break-even exit ends a streak).\n")
    w(perf_table(is_df) + "\n")
    w("### Benchmarks, in-sample\n")
    w("Chase = market entry at the completion close, same stop/target/BE/risk. Random = same trade count and "
      "buy/sell mix, random entry bars while the 1H filter points that way, stop = the strategy's median stop "
      "distance, target = its median planned target multiple. 'real pct' = percentile of the real result in the "
      "random distribution.\n")
    w(bench_table(is_df) + "\n")
    w("### Signal flow, in-sample\n")
    w(flow_table(is_df) + "\n")
    w("## 3. Plateau check (in-sample)\n")
    w("Neighbours = adjacent retracement with the same target, and the same retracement with the other target. "
      "'likely noise' = the pick is positive but its neighbours average <= 0 or less than half of it.\n")
    w(md_table(plateau, 3) + "\n" if len(plateau) else "No eligible picks.\n")
    w("## 4. Out-of-sample, top 3 only\n")
    if len(oos_df):
        w(perf_table(oos_df) + "\n")
        w("### Benchmarks, out-of-sample\n")
        w(bench_table(oos_df) + "\n")
        w("### Signal flow, out-of-sample\n")
        w(flow_table(oos_df) + "\n")
    w("## 5. Does it beat both benchmarks?\n")
    w("'useful' = avg R > 0 on both pairs AND avg R above chase on both pairs AND at or above the 95th "
      "percentile of the random benchmark on both pairs.\n")
    for seg, bt in (("In-sample", is_beats), ("Out-of-sample", oos_beats)):
        if not bt:
            continue
        t = pd.DataFrame(bt).T.drop(columns="random_percentiles")
        t.index.name = f"{seg}"
        w(md_table(t, 3) + "\n")
    w("## 6. Flags\n")
    fl = [f"IS: {x}" for x in flags_for(is_df)] + ([f"OOS: {x}" for x in flags_for(oos_df)] if len(oos_df) else [])
    fl += [f"In-sample pick {c} FAILS out-of-sample (avg R <= 0 on at least one pair)" for c in oos_fail]
    fl += [f"Plateau: {p} looks like noise (neighbours {r['neighbours']})" for p, r in plateau.iterrows() if r["likely_noise"]] if len(plateau) else []
    w("\n".join(f"- {x}" for x in fl) + "\n" if fl else "- none\n")
    if top:
        w(f"## 7. Breakdowns for the in-sample #1 ({name(top[0])}), both pairs\n")
        w("Session by entry hour (UTC): Asia 21:00-07:00, London 07:00-13:00, New York 13:00-21:00. "
          "CSV breakdowns for all top-3 combos are in `breakdowns/`.\n")
        for seg in ("IS", "OOS"):
            if seg not in bd_md:
                continue
            for k in ("pair", "side", "session", "year", "month"):
                w(f"**{seg} by {k}**\n\n" + md_table(bd_md[seg][k]) + "\n")
            for sym in PAIRS:
                for k in ("side", "session", "year"):
                    w(f"**{seg} {sym} by {k}**\n\n" + md_table(bd_md[seg, sym][k]) + "\n")
    w("## 8. Counts\n")
    w("### Legs and trend filter\n")
    lc = pd.DataFrame(leg_counts).T
    lc.index = [f"{s} {g}" for s, g in lc.index]
    lc.index.name = "pair / segment"
    w(md_table(lc, 1) + "\n")
    w("### Chase signal flow\n")
    w(md_table(chase_flow, 0) + "\n")
    w("### Data gaps (missing 15m bars outside the weekend close)\n")
    for sym, g in gaps.items():
        w(f"- {sym}: {g['missing_weekday_15m_bars']} missing bars in {g['gap_episodes']} episodes "
          f"({g['gaps_over_1h']} longer than 1h). Largest: " +
          ", ".join(f"{s} ({n} bars)" for s, n in g["largest"][:8]))
    w("\nAll gaps longer than 1h are the Christmas and New Year closures.\n")
    w("## 9. Files\n")
    w("- `trade_logs/<PAIR>_<combo>.csv`, `trade_logs/<PAIR>_chase_<T1|T2>.csv`, `trade_logs/orders.csv`\n"
      "- `in_sample_all6.csv`, `in_sample_ranking.csv`, `out_of_sample_top3.csv`\n"
      "- `charts/equity_IS.png`, `charts/equity_OOS.png`, `charts/random_benchmark.png`\n"
      "- `breakdowns/<combo>_<segment>_<year|pair|side|session|month>.csv`\n")
    with open(f"{out_dir}/REPORT.md", "w") as f:
        f.write("\n".join(L))
    json.dump({"split": str(split), "start": str(start), "end": str(end), "combos_tested": len(COMBOS),
               "top3": [name(c) for c in top], "is_beats": is_beats, "oos_beats": oos_beats,
               "gaps": gaps, "flags": fl}, open(f"{out_dir}/summary.json", "w"), indent=1, default=str)
    print(f"report -> {out_dir}/REPORT.md", flush=True)


if __name__ == "__main__":
    main()
