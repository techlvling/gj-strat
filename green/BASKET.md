# USDJPY basket: 4 trades (all times IST)

## Risk per trade, by account
| Trade | Alpha $10k | Blueberry $2.5k | Real money |
|---|---|---|---|
| 1. Vol-box | 0.25% | 0.25% | 0.25% |
| 2. Vol-gotobi | 3% | 1.5% | 1% |
| 3. Fade | 0.5% | — | — |
| 4. Month-end USD (M-3) | 3% | 1% | 1% |

Lots = risk $ ÷ (SL pips × pip value). USDJPY pip value ≈ $6.80 per lot at 147 (1,000 JPY ÷ price).

## Vol filter (trades 1 and 2 only)
- ATR20 = average daily high−low of the last 20 days (New York-close candles).
- **ON** when today's ATR20 ≥ the median ATR20 of the last 250 trading days. **OFF** → skip trades 1 and 2.
- Early Oct 2026: ATR20 ≈ 121 pips vs median ≈ 109 → ON.

## Daily timeline
| IST | What |
|---|---|
| 05:00–05:59 | Box forms (trades 1 and 3) |
| 06:00 | Place the box stop orders |
| 06:25 | Gotobi days: sell (trade 2) |
| 11:00 | Unfilled box/fade orders expire |
| 11:30 | Close the gotobi trade |
| 16:30–17:30 | 3rd-last weekday of the month: month-end trade (trade 4) |

## 1. Vol-box (only when the vol filter is ON)
1. Box = high/low of 05:00–05:59. At 06:00: buy stop at box high, sell stop at box low; one fills → cancel the other.
2. SL = box size + spread. TP = 9 × SL.
3. At +3R move SL to entry + 1/6 of the SL distance.
4. Stopped out before 11:00 → wait 6 minutes → one stop on the opposite side at the original box level
   (skip if price is already past it). Max 2 trades a day; done after a TP.
5. Unfilled orders expire 11:00. Open trades run until SL/TP/BE.

## 2. Vol-gotobi (only when the vol filter is ON)
1. Days: 5th, 10th, 15th, 20th, 25th and last day of the month; a weekend date moves back to Friday.
2. 06:25 (= 09:55 Tokyo fix): SELL USDJPY at market.
3. SL = 0.25 × ATR20. No TP. Close at 11:30.

## 3. Fade (Alpha only, every day)
1. Same box and 06:00 levels as trade 1, but the first break is **not** traded.
2. If price breaks one side and then comes back to the far side of the box (box size + spread from that
   break) before 11:00, and before going 5 × box in the breakout's favour → trade the second break
   (e.g. breaks up, falls back to box low → SELL there).
3. SL = box size + spread. TP = 5 × SL. No break-even.
4. Stopped out before 11:00 → one re-entry after 6 minutes on the opposite side (at the 6-minute
   extreme if it is beyond the box level, else the box level). Max 2 trades.

## 4. Month-end USD bid (every month)
1. Day: 3rd-last weekday of the month (count Mon–Fri back from the last weekday; holidays count).
2. 16:30: BUY USDJPY at market. SL = 0.25 × ATR20. No TP.
3. Close at 17:30.

## Next dates
| Month | Gotobi (trade 2, if filter ON) | Month-end (trade 4) |
|---|---|---|
| Oct 2026 | Thu 15, Tue 20, Fri 23, Fri 30 | Wed 28 |
| Nov 2026 | Thu 5, Tue 10, Fri 13, Fri 20, Wed 25, Mon 30 | Thu 26 |
| Dec 2026 | Fri 4, Thu 10, Tue 15, Fri 18, Fri 25, Thu 31 | Tue 29 |

## Last 3 years (Oct 2023 – Oct 2026), all costs, one compounding account
| Plan | Start → end | Per year | Max drawdown | Worst month |
|---|---|---|---|---|
| Alpha (all 4) | $10,000 → $25,481 | +36.6% | 24.8% | −7.2% |
| Blueberry (1 + 2 + 4) | $2,500 → $4,083 | +17.8% | 10.9% | −2.7% |
| Real money (1 + 2 + 4) | $10,000 → $14,900 | +14.2% | 8.1% | −2.4% |

- The month-end trade made only +0.3R in these 3 years (36 trades). Its benefit in the prop tests comes
  from 2011–2023.
- Alpha's 24.8% drawdown is over the 10% challenge limit; the prop simulation (results/m3_addon/) gives
  the real odds: about 59% of challenges pass eventually, 7.3 months per funded account.
- Details: results/basket_last3y/REPORT.md, results/m3_addon/REPORT.md, results/m3_monthly/REPORT.md.
