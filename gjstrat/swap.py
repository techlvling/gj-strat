"""Overnight financing (swap / rollover) from real overnight interest rates.

  * A position open over the 17:00 New York rollover pays or earns one day of interest; the
    Wednesday rollover counts 3 days (it carries the weekend, T+2 settlement).
  * Long BASE/QUOTE earns the base rate and pays the quote rate:
        rate = r_base - r_quote - markup     (short: r_quote - r_base - markup)
    markup is the broker's spread on the differential, % per year (both sides pay it).
  * interest = notional in USD x rate / 100 x days / 365, booked when the trade closes.
Rates: rates/DFF.csv (USD effective Fed Funds, daily) and rates/IRSTCI01JPM156N.csv (Japan
overnight call rate, monthly), both from FRED, forward-filled to every day.
Only pairs with a USD leg are supported (notional in USD needs no third rate).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

NY = "America/New_York"
FRED_FILES = {"USD": "DFF.csv", "JPY": "IRSTCI01JPM156N.csv"}


class SwapModel:
    def __init__(self, rates: dict[str, pd.Series], markup_pct: float = 1.0):
        self.rates = {k: v.sort_index() for k, v in rates.items()}
        self.markup = markup_pct

    @classmethod
    def from_fred(cls, folder: str = "rates", markup_pct: float = 1.0) -> "SwapModel":
        rates = {}
        for ccy, fname in FRED_FILES.items():
            df = pd.read_csv(os.path.join(folder, fname), parse_dates=["observation_date"])
            s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            rates[ccy] = pd.Series(s.to_numpy(), index=df["observation_date"]).dropna()
        return cls(rates, markup_pct)

    def rate(self, ccy: str, days: pd.DatetimeIndex) -> np.ndarray:
        s = self.rates[ccy]
        return s.reindex(s.index.union(days)).ffill().reindex(days).to_numpy()

    @staticmethod
    def rollovers(start_utc: pd.Timestamp, end_utc: pd.Timestamp) -> pd.DataFrame:
        """Every weekday 17:00 New York rollover in (start, end], with its day weight."""
        days = pd.date_range(start_utc.floor("D") - pd.Timedelta(days=1),
                             end_utc.ceil("D") + pd.Timedelta(days=1), freq="D")
        days = days[days.dayofweek < 5]
        roll = (days + pd.Timedelta(hours=17)).tz_localize(NY).tz_convert("UTC").tz_localize(None)
        keep = (roll > start_utc) & (roll <= end_utc)
        return pd.DataFrame({"ny_date": days[keep], "utc": roll[keep],
                             "days": np.where(days[keep].dayofweek == 2, 3, 1)})

    def swap_usd(self, sym: str, side: str, lots: float, entry_utc: pd.Timestamp,
                 exit_utc: pd.Timestamp, price: float) -> tuple[float, int]:
        """(swap in USD, rollovers held). Positive = paid to the trader."""
        r = self.rollovers(entry_utc, exit_utc)
        if r.empty:
            return 0.0, 0
        base, quote = sym[:3], sym[3:]
        if base == "USD":
            notional_usd = lots * 100_000
        elif quote == "USD":
            notional_usd = lots * 100_000 * price
        else:
            raise NotImplementedError(f"swap for {sym}: needs a USD leg")
        idx = pd.DatetimeIndex(r["ny_date"])
        diff = self.rate(base, idx) - self.rate(quote, idx)
        rate = (diff if side == "BUY" else -diff) - self.markup
        usd = float((notional_usd * rate / 100 * r["days"].to_numpy() / 365).sum())
        return usd, len(r)
