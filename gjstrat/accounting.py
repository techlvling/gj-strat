"""Money management and statistics.

Trade paths don't depend on account size, so the engine produces price-level trades and
this module replays them in time order against a compounding balance:
  * risk = risk_pct of the *closed* balance at entry (trades from different days can overlap)
  * lots = floor(risk_usd / (risk_pips * pip_value_per_lot) / 0.01) * 0.01, minimum 0.01
  * pip value per 1.0 lot (100k base) = 100,000 x pip in the quote currency, converted to USD
    with Market.quote_per_usd at entry (sizing) and at exit (realised P/L)
  * commission is USD per lot round turn
R per trade = price move / 1R distance, minus commission, plus swap (if a SwapModel is given),
both expressed in R. Swap is booked when the trade closes. Stats are in R and %.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import Market
from .engine import IST, Trade

LOT = 100_000


def account(trades: list[Trade], m: Market, start_balance: float = 10_000.0,
            risk_pct: float = 1.0, commission: float = 0.0, lot_step: float = 0.01,
            swap=None, sym: str | None = None, slippage_pips: float = 0.0) -> pd.DataFrame:
    """swap: gjstrat.swap.SwapModel (needs sym, e.g. "USDJPY"); None = no financing.
    slippage_pips: worse fill on every stop order (entry, SL, BE stop); TP is a limit, none."""
    cols = ["day", "side", "trade_num", "entry_time_ist", "entry_price", "exit_time_ist",
            "exit_price", "range_pips", "risk_pips", "spread_pips", "R", "exit_reason", "lots",
            "pnl_usd", "swap_usd", "swap_nights", "balance_after", "gap_fill", "be_moved",
            "entry_i", "exit_i"]
    if not trades:
        return pd.DataFrame(columns=cols)
    # events: (bar, order, trade idx). On one bar, earlier trades' exits are booked before new
    # entries; a trade stopped out on its own entry bar exits after its entry.
    ev = sorted([(t.entry_i, 1, k) for k, t in enumerate(trades)] +
                [(t.exit_i, 0 if t.exit_i > t.entry_i else 2, k) for k, t in enumerate(trades)])
    bal = start_balance
    lots = np.zeros(len(trades))
    pnl = np.zeros(len(trades))
    rnet = np.zeros(len(trades))
    swap_usd = np.zeros(len(trades))
    nights = np.zeros(len(trades), dtype=int)
    bal_after = np.zeros(len(trades))
    for bar, kind, k in ev:
        t = trades[k]
        if kind == 1:   # entry
            pip_usd = LOT * m.pip / m.quote_per_usd[t.entry_i]
            raw = bal * risk_pct / 100 / (t.risk / m.pip * pip_usd)
            lots[k] = max(np.floor(raw / lot_step + 1e-9) * lot_step, lot_step)
        else:
            pips = (t.exit - t.entry if t.side == "BUY" else t.entry - t.exit) / m.pip
            gross = lots[k] * pips * LOT * m.pip / m.quote_per_usd[t.exit_i]
            comm = commission * lots[k]
            stop_fills = 1 + (t.reason in ("SL", "BE"))
            comm += slippage_pips * stop_fills * lots[k] * LOT * m.pip / m.quote_per_usd[t.exit_i]
            if swap is not None:
                swap_usd[k], nights[k] = swap.swap_usd(sym, t.side, lots[k], m.ts(t.entry_i),
                                                       m.ts(t.exit_i), t.entry,
                                                       m.quote_per_usd[t.entry_i])
            pnl[k] = gross - comm + swap_usd[k]
            risk_usd = lots[k] * (t.risk / m.pip) * LOT * m.pip / m.quote_per_usd[t.entry_i]
            rnet[k] = t.r + (swap_usd[k] - comm) / risk_usd
            bal += pnl[k]
            bal_after[k] = bal
    df = pd.DataFrame({
        "day": [t.day.date() for t in trades],
        "side": [t.side for t in trades],
        "trade_num": [t.num for t in trades],
        "entry_time_ist": [m.ts(t.entry_i) + IST for t in trades],
        "entry_price": [round(t.entry, 5) for t in trades],
        "exit_time_ist": [m.ts(t.exit_i) + IST for t in trades],
        "exit_price": [round(t.exit, 5) for t in trades],
        "range_pips": [round(t.range_pips, 1) for t in trades],
        "risk_pips": [round(t.risk / m.pip, 2) for t in trades],
        "spread_pips": [round(t.spread / m.pip, 2) for t in trades],
        "R": rnet.round(4),
        "exit_reason": [t.reason for t in trades],
        "lots": lots.round(2),
        "pnl_usd": pnl.round(2),
        "swap_usd": swap_usd.round(2),
        "swap_nights": nights,
        "balance_after": bal_after.round(2),
        "gap_fill": [t.gap_fill for t in trades],
        "be_moved": [t.be_moved for t in trades],
        "entry_i": [t.entry_i for t in trades],
        "exit_i": [t.exit_i for t in trades],
    })
    return df.sort_values(["exit_i", "entry_i"]).reset_index(drop=True)


def equity_curve(log: pd.DataFrame, start_balance: float = 10_000.0) -> pd.Series:
    """Closed-trade balance indexed by exit time (IST)."""
    s = pd.Series(log["balance_after"].to_numpy(), index=pd.DatetimeIndex(log["exit_time_ist"]))
    first = (log["entry_time_ist"].min() if len(log) else pd.Timestamp("2024-01-01"))
    return pd.concat([pd.Series([start_balance], index=[first - pd.Timedelta(minutes=1)]), s])


def longest_streak(r: np.ndarray) -> int:
    best = cur = 0
    for x in r:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def stats(log: pd.DataFrame, start_balance: float = 10_000.0, years: float | None = None) -> dict:
    n = len(log)
    if n == 0:
        return dict(trades=0, win_rate=np.nan, avg_R=np.nan, profit_factor=np.nan,
                    expectancy_R=np.nan, expectancy_pct=np.nan, sqn=np.nan, max_dd_pct=0.0,
                    longest_losing_streak=0, net_return_pct=0.0, cagr_pct=np.nan)
    r = log["R"].to_numpy()
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    eq = equity_curve(log, start_balance).to_numpy()
    peak = np.maximum.accumulate(eq)
    dd = ((peak - eq) / peak).max() * 100
    final = eq[-1]
    sd = r.std(ddof=1) if n > 1 else np.nan
    prev_bal = log["balance_after"].to_numpy() - log["pnl_usd"].to_numpy()
    out = dict(
        trades=n,
        win_rate=(r > 0).mean() * 100,
        avg_R=r.mean(),
        profit_factor=(pos / neg) if neg > 0 else np.inf,
        expectancy_R=(r > 0).mean() * (r[r > 0].mean() if (r > 0).any() else 0)
                     - (r < 0).mean() * (-r[r < 0].mean() if (r < 0).any() else 0),
        expectancy_pct=float(np.mean(log["pnl_usd"].to_numpy() / prev_bal) * 100),
        sqn=r.mean() / sd * np.sqrt(n) if sd and sd > 0 else np.nan,   # t-stat of mean R
        max_dd_pct=dd,
        longest_losing_streak=longest_streak(r),
        net_return_pct=(final / start_balance - 1) * 100,
        cagr_pct=np.nan,
    )
    if years:
        out["cagr_pct"] = ((final / start_balance) ** (1 / years) - 1) * 100 if final > 0 else -100
    return out


def breakdown(log: pd.DataFrame, by: pd.Series | str) -> pd.DataFrame:
    g = log.groupby(by if isinstance(by, str) else by.rename("group"), observed=True)["R"]
    out = pd.DataFrame({
        "trades": g.size(),
        "win_rate_%": g.apply(lambda x: (x > 0).mean() * 100),
        "avg_R": g.mean(),
        "total_R": g.sum(),
        "profit_factor": g.apply(lambda x: x[x > 0].sum() / -x[x < 0].sum() if (x < 0).any() else np.inf),
    })
    return out.round(3)
