"""Trade statistics in R and % (1% of current equity per trade, compounding, $10,000 start)."""
from __future__ import annotations

import numpy as np
import pandas as pd

START = 10_000.0
RISK = 0.01


def equity(r: np.ndarray, start: float = START, risk: float = RISK) -> np.ndarray:
    """Balance after each trade: risk = 1% of the balance at entry, P/L = R x risk."""
    return start * np.cumprod(1.0 + risk * np.asarray(r, float))


def max_drawdown_pct(eq: np.ndarray, start: float = START) -> float:
    path = np.r_[start, eq]
    peak = np.maximum.accumulate(path)
    return float(((peak - path) / peak).max() * 100)


def max_drawdown_r(r: np.ndarray) -> float:
    cum = np.r_[0.0, np.cumsum(r)]
    return float((np.maximum.accumulate(cum) - cum).max())


def losing_streak(r: np.ndarray, reasons: np.ndarray) -> int:
    """Longest run of losing trades. Break-even exits are skipped (neither win nor loss)."""
    best = cur = 0
    for x, why in zip(r, reasons):
        if why == "BE":
            continue
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def summarize(df: pd.DataFrame) -> dict:
    """df: trades of one variant in time order (columns R, exit_reason)."""
    r = df["R"].to_numpy(float)
    n = len(r)
    if n == 0:
        return dict(trades=0, win_rate=np.nan, avg_R=np.nan, profit_factor=np.nan, expectancy=np.nan,
                    max_dd_pct=0.0, max_dd_R=0.0, losing_streak=0, net_return_pct=0.0, total_R=0.0,
                    wins=0, losses=0, be=0)
    reasons = df["exit_reason"].to_numpy()
    be = reasons == "BE"
    gw, gl = r[r > 0].sum(), -r[r < 0].sum()
    eq = equity(r)
    return dict(trades=n, wins=int((r > 0).sum()), losses=int(((r < 0) & ~be).sum()), be=int(be.sum()),
                win_rate=float((r > 0).mean() * 100), avg_R=float(r.mean()),
                profit_factor=float(gw / gl) if gl > 0 else np.inf, expectancy=float(r.mean()),
                max_dd_pct=max_drawdown_pct(eq), max_dd_R=max_drawdown_r(r),
                losing_streak=losing_streak(r, reasons), net_return_pct=float((eq[-1] / START - 1) * 100),
                total_R=float(r.sum()))


def breakdown(df: pd.DataFrame, by) -> pd.DataFrame:
    g = df.groupby(by, observed=True)["R"]
    out = pd.DataFrame({"trades": g.size(), "win_rate": g.apply(lambda x: (x > 0).mean() * 100),
                        "avg_R": g.mean(), "total_R": g.sum()})
    return out


def random_benchmark(df: pd.DataFrame, seeds: int = 1000, first_seed: int = 1) -> dict:
    """Same entry timestamps, stop distances and target multiples as the real trades; each seed
    flips a fair coin for every trade's direction (r = real R if the coin matches the real side,
    else the opposite-side outcome computed by the engine at the same bar)."""
    same = df["R"].to_numpy(float)
    opp = df["r_opp"].to_numpy(float)
    n = len(same)
    exp = np.empty(seeds)
    net = np.empty(seeds)
    for k in range(seeds):
        rng = np.random.default_rng(first_seed + k)
        r = np.where(rng.random(n) < 0.5, same, opp)
        exp[k] = r.mean() if n else np.nan
        net[k] = (np.prod(1 + RISK * r) - 1) * 100 if n else 0.0
    real_exp = same.mean() if n else np.nan
    real_net = (np.prod(1 + RISK * same) - 1) * 100 if n else 0.0
    pct = lambda dist, x: float(((dist < x).sum() + 0.5 * (dist == x).sum()) / len(dist) * 100)
    return dict(n=n, real_exp=real_exp, real_net=real_net, exp=exp, net=net,
                exp_pctile=pct(exp, real_exp), net_pctile=pct(net, real_net))
