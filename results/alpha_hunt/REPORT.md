# Alpha hunt: final report

Date: 2026-10-11. Data: 2010-01 to 2026-10-07. All results are after costs (spread, commission, slippage, swap or financing).

## The short answer

- We tested 14 new families of ideas. That is 171 tests in total.
- About 1 test should pass by pure luck. 2 tests passed.
- Both passes are on the Nasdaq 100. Both buy a dip and hold for a few days.
- Three independent checks then attacked each pass.
  - MR4 (buy after a big down day, hold 5 days) failed all three checks. It is dead.
  - MR6 (RSI(2) dip-buy above the 200-day average) passed two checks and failed one. It is the only "verified" edge, and it is weak.
- MR6 does not make the Alpha Swing challenge faster. The basket stays as it is.
- In the Blueberry payout sim, MR6 adds about $47 to $69 per account over 24 months (+6% to +9%).
- There is no new FX edge. Your real edges are still the USDJPY clock and calendar flows (vol-box, vol-gotobi, fade, M-3).

## How to read the numbers

- **R** = profit in units of the risk on one trade. +0.10 R means you make 10% of your risk per trade on average.
- **Periods**: design 2010-17 (indices from their data start), check 2018-23, holdout 2024-26.
- **Pass bar** (set before any test): design t >= 2, AND avg R above 0 in check, AND above 0 in holdout.
- **t**: a t of 2 or more means the result is unlikely to be luck alone.
- **Expected by luck**: about 0.6% of tests pass the bar by chance.
- Every rule and variant was written down before its test was run.

## Every family tested

Avg R is per trade unless the row says otherwise. Columns: design avg R (t) / check avg R / holdout avg R.

| # | Family | Style | Tests | Expected by luck | Passed bar | Verified | Best test | Design (t) | Check | Holdout |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | index_meanrev | Mean reversion: index dip-buying | 44 | 0.26 | 2 | 1 (MR6, 2 of 3 checks) | Nasdaq MR6: RSI(2) < 5 above SMA200 | +0.433 (2.28) | +0.073 | +0.298 |
| 2 | fomc_cycle | Event: Fed meetings | 9 | 0.05 | 0 | 0 | Nasdaq pre-FOMC drift (F1) | -0.095 (-1.10) | +0.198 | +0.123 |
| 3 | trend_follow | Trend following, 13 markets | 8 | 0.05 | 0 | 0 | D3 trend-gated 20-day breakout, pooled | -0.005 (-0.04) | -0.065 | +0.164 |
| 4 | fx_carry | Carry: G8 FX | 9 | 0.05 | 0 | 0 | C8 carry + trend + low-vol filter (R per month) | +0.086 (1.07) | +0.009 | +0.136 |
| 5 | fx_rates | Macro: 2-year yield gaps | 10 | 0.06 | 0 | 0 | FV2 rate fair-value fade, 5 USD pairs | +0.025 (0.23) | +0.101 | +0.355 |
| 6 | index_flows | Calendar flows: option expiry, pension rebalancing | 8 | 0.05 | 0 | 0 | Nasdaq P4 turn-of-month when stocks beat bonds | +0.280 (1.49) | +0.273 | +0.176 |
| 7 | cross_zfade | Mean reversion: range-bound FX crosses | 9 | 0.05 | 0 | 0 | Z4 (50-day z-score 2.5, SL 1.5 ATR) | -0.147 (-1.38) | +0.128 | +0.037 |
| 8 | fx_session_rev | Intraday reversal: Asia extremes into London/NY | 8 | 0.05 | 0 | 0 | V4 (filtered, exit 16:55 NY) | -0.018 (-0.59) | -0.081 | +0.006 |
| 9 | cb_drift | Event: 7 central banks | 10 | 0.06 | 0 | 0 | D1 follow the decision-day move | +0.012 (0.31) | +0.031 | +0.008 |
| 10 | index_vol_timing | Volatility timing of index exposure | 18 | 0.11 | 0 | 0 | P4 VRP-scaled, 3 indices pooled (% per month vs buy-and-hold, not R) | +0.37 (2.12) | +0.01 | -0.10 |
| 11 | fx_value_mom | Value and momentum, G8 FX | 8 | 0.05 | 0 | 0 | V4 carry + momentum + value (R per month) | +0.074 (0.92) | -0.003 | +0.050 |
| 12 | ust_auction | Event: US Treasury auctions | 8 | 0.05 | 0 | 0 | Buy USDJPY before month-end 2y/5y/7y auctions | +0.218 (1.37) | +0.196 | +0.546 |
| 13 | eq_overnight_drift | Overnight drift: index at the European open | 14 | 0.08 | 0 | 0 | Nasdaq ON6 (after a down day) | -0.028 (-0.55) | -0.031 | +0.058 |
| 14 | cot_positioning | Positioning: CFTC futures data | 8 | 0.05 | 0 | 0 | P1 fade crowded speculators, 8 markets | -0.038 (-0.65) | +0.078 | +0.080 |
| | **Total** | | **171** | **1.03** | **2** | **1** | | | | |

Notes on the table:
- Row 1: the second pass was Nasdaq MR4: +0.201 (t 2.01) / +0.097 / +0.090. All three checks refuted it.
- Row 10: 8 of the 18 tests passed the plain bar on monthly returns. But plain buy-and-hold also passes it. The family's own pre-declared rule also required beating buy-and-hold in check and holdout. None did. On the S&P alone, P4 beat buy-and-hold by +0.15%/month in check and -0.005%/month in holdout.
- Row 4 and row 11 are monthly portfolio R, not per trade.
- Row 1's luck figure is too low. The checks found that a random long trade on a rising index passes the bar 2% to 8% of the time, not 0.6%. With about 40 long-only tests, 1 to 3 lucky passes were likely.

## Why each family failed (one line each)

- **FOMC**: the pre-meeting drift is real before costs, but only since 2016. The 2010-15 years lost.
- **Trend following**: FX trend is flat or negative even before costs. Index and gold breakouts made money, but mostly from the bull market.
- **FX carry**: carry earned its swap, then gave it back in crash months (2015-08, 2020-03, 2024-08).
- **Rate gaps**: yield momentum copies price momentum. The fair-value fade only worked after 2018.
- **Index flows**: the turn-of-month long is the best near miss, but design t is only 1.49 and the S&P barely confirms it.
- **Cross fades**: 2-sigma moves on crosses kept running. The stop was hit on 43-58% of trades.
- **Session reversal**: no reversal and no momentum before costs. Costs make every variant lose.
- **Central banks**: no drift after the decision day. Follow and fade are mirror images.
- **Volatility timing**: it cuts the worst day and drawdown. It does not beat buy-and-hold. That is safety, not edge.
- **Value and momentum**: value lost on the yen in 2024-26. Momentum lost at every horizon.
- **Treasury auctions**: the USDJPY gain is a month-end USD effect (it overlaps M-3), not an auction effect.
- **Overnight drift**: real before costs (about 0.9 basis points per trade), but costs are about 3.3 basis points.
- **CFTC positioning**: fading crowds is flat in design. The other variants lose after weekly costs.

A common pattern: many "best" tests made money only in 2024-26. That looks like the recent bull market, not an edge.

## The verified edge: Nasdaq 100 MR6

### What it is

Buy the Nasdaq 100 after a sharp short-term dip, but only while the index is in a long-term uptrend. Sell on the first bounce.

### Exact trading rules

Market: Nasdaq 100 CFD (tested on Dukascopy USATECHIDXUSD; NAS100 or US Tech 100 at most brokers).

New York times move with US daylight saving. In India the times fall on the **next calendar day**.

| Event | New York | IST, US summer time (2nd Sun of March to 1st Sun of Nov) | IST, US winter time |
|---|---|---|---|
| Read the daily close | 15:54 (bid at 15:55:00) | 01:24-01:25 | 02:24-02:25 |
| Enter or exit at market | 15:55 | 01:25 | 02:25 |
| Daily bar for ATR20 starts and ends | 17:00 | 02:30 | 03:30 |

1. **Daily close (C)**: the bid price at 15:55:00 New York, once per NYSE trading day. If the CFD has no price then, skip that day.
2. **Entry signal**, both must be true:
   - C is above the 200-day simple average of these daily closes (today included).
   - RSI(2) is below 5. Use Wilder's RSI with period 2 on the same daily closes.
3. **Entry**: buy at market at 15:55 New York (01:25 or 02:25 IST). Only one trade at a time.
4. **Stop loss**: entry minus 2 x ATR20.
   - ATR20 = average of (daily high minus daily low) over the 20 previous days.
   - A day runs from 17:00 to 17:00 New York (02:30 to 02:30 IST in summer, 03:30 in winter).
   - Do not include the current day.
   - The stop is usually 1.3% to 4.9% of price (median 2.8%).
5. **Size**: lots = (account x risk %) / stop distance.
6. **Exit**: on each following trading day, read C at 15:54 New York.
   - If C is above the 5-day simple average of closes (today included), sell at market at 15:55.
   - If that has not happened by the 10th close after entry, sell at the 10th close anyway.
   - No take-profit. The stop stays live day and night.
7. **After a stop-out**: keep tracking the exit rule. Take no new signal until after the day the trade would have exited.

### How it performed (Nasdaq, after costs)

| Period | Trades | Avg R | t |
|---|---|---|---|
| Design 2014-17 | 20 | +0.433 | 2.28 |
| Check 2018-23 | 29 | +0.073 | 0.53 |
| Holdout 2024-26 | 12 | +0.298 | 2.06 |
| Last 3 years | 13 | +0.302 | 2.26 |
| All | 61 | +0.235 | 2.46 |

- First trade 2014-10, last 2026-08. The 200-day average needed a warm-up after a data gap in 2013.
- About 4 to 5 trades a year (0.35 per month of data). Median hold 4 days, maximum 10.
- 70% winners. Average win is 0.88 x average loss.
- 49 trades exited on the rule (avg +0.55 R). 12 hit the stop (avg -1.03 R).
- Worst trade -1.16 R (a gap through the stop). Longest losing run: 4 trades. Deepest drawdown: -5.3 R.
- Worst day at 0.5% risk: -0.96% (marked to market), -1.09% (realised).
- R by year: 2014 +2.0, 2015 +3.9, 2016 -1.3, 2017 +4.1, 2018 -2.4, 2019 -1.4, 2020 -0.5, 2021 +5.0, 2022 +0.3, 2023 +1.1, 2024 +2.2, 2025 +0.0, 2026 +1.4.
- Same rule on other markets (all periods): S&P 500 +0.264 R, Nikkei +0.086 R, gold +0.086 R. All positive, none passes the bar alone.
- Pooled over the three indices: design month t 1.94 (just under 2), check +0.085, holdout +0.361.

### Why it is weak

- Only 61 trades. Only 20 are in the design period.
- The check period (2018-23) is nearly flat: +0.07 R, t 0.53.
- 2018, 2019 and 2020 all lost. The check period is positive only because of 2021 (+5.0 R from 10 trades).
- After removing the Nasdaq's normal upward drift, the check period is about zero (+0.02 R).
- It depends on the exact clock and threshold. Moving the signal 15 minutes earlier drops design t to 1.40. With RSI(2) < 3 the check period fails, and with RSI(2) < 10 the design t fails.

## Adversarial verification

Each of the 2 passes went through three independent checks. Each check tried to break the result.

| Check | What it did | MR4 (5-day hold after a big down day) | MR6 (RSI(2) dip-buy) |
|---|---|---|---|
| Code audit | Read every line. Rebuilt both trade lists from scratch without the project's helpers. | **Refuted.** Code is correct: 254 of 254 trades match. But the gain is the index's upward drift. A random long with the same exits does as well in the holdout (+0.083 vs +0.090 R). Only 18 of 60 nearby settings pass. | **Not refuted.** 61 of 61 trades match. It passes with 2x costs (t 2.18), with a 15:50 signal (t 2.50) and without the gap rule (t 2.87). It beats a random long in all periods, but only barely in check (t 0.11). |
| Execution realism | Real spreads and fills, gaps through stops, real financing, 2x slippage, harsher costs. | **Refuted.** Fills are clean, but design t has no room: 1.97 with 2x slippage, 1.90 with realistic costs, 1.53 under harsh costs. Holdout t is below 0.8. | **Not refuted.** Design t stays at or above 2 in every stress (2.02 under harsh costs). Check stays positive (+0.040 under harsh costs). Financing costs only about 0.013 R per trade. Costs are not the problem. |
| Robustness | Changed every parameter by about 25%, shifted the clock, split by year, corrected for 44 tests, ran drift-aware random trades. | **Refuted.** Only 14% of nearby settings pass. Clock 15 minutes earlier: design t 1.29. Without 2013 (7 trades, +7.2 R): t 1.28. Corrected for 44 tests: p = 0.36. | **Refuted.** Clock 15 minutes earlier: design t 1.40, check +0.003. RSI threshold is knife-edged. Check rests on 2021. Without the top 10 trades: +0.045 R, t 0.49. Corrected for 44 tests: p = 0.37. A random long passes the bar 2% to 8% of the time. |
| **Result** | | **Refuted by all 3. Dead.** | **Passed 2 of 3. Listed as verified, but weak.** |

What this means:
- The code and the costs are fine for MR6. The doubt is statistical.
- The robustness check found that 2 passes among about 40 long-only index tests is what drift plus luck would give.
- Treat MR6 as a small optional add-on. Do not treat it as a proven edge.

## Prop-simulation impact

The rules and the decision rule were fixed before the sim. Only MR6 was added. It was sized on its own stop.

### Alpha Swing $10k (current basket: vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%)

"Months per funded account": average months of challenge time per account that gets funded. Lower is better.
Two windows: challenges started 2011-25 / started 2018-25.

| Risk rule | MR6 risk | Months per funded account | Pass eventually % | Accepted |
|---|---|---|---|---|
| Normal | none (basket) | 7.29 / 5.79 | 59.1 / 74.0 | - |
| Normal | 0.5% | 7.18 / 5.83 | 59.9 / 73.9 | No |
| Normal | 1% | 7.07 / 5.76 | 60.5 / 74.4 | Yes |
| Normal | 2% | 6.68 / 5.56 | 63.5 / 75.9 | Yes |
| Boost x1.5 | none (basket) | 4.86 / 4.34 | 46.24 / 55.2 | - |
| Boost x1.5 | 0.5% | 4.88 / 4.35 | 45.5 / 54.5 | No |
| Boost x1.5 | 1% | 5.00 / 4.56 | 44.8 / 52.6 | No |
| Boost x1.5 | 2% | 4.74 / 4.20 | 46.18 / 55.6 | No |

- With normal risk, MR6 helps a little at 1% and 2%.
- With the x1.5 boost (the speed-up in use), it does not help. At 2% it misses only because pass-eventually slips from 46.24% to 46.18%.
- Why the boost hurts: MR6 losses land on the same days as boosted 3% legs. Fails from the 5% daily limit rise from 19.7% to 22.0% (2011-25) and from 12.3% to 14.7% (2018-25).
- The rule needs a level accepted under both risk rules. None is. **The Alpha Swing basket does not change.**
- The family's own earlier sim liked MR4 at 1% with boost (4.86 to 4.52 months). MR4 is now refuted, so ignore that.

### Blueberry Instant Elite $2.5k (basket: vol-box 0.25% + vol-gotobi 1.5% + M-3 1%, 24 months)

| MR6 risk | Avg paid in 24 months, starts 2011-24 | Lost within 24 months, 2011-24 | Avg paid in 24 months, starts 2018-24 | Lost within 24 months, 2018-24 |
|---|---|---|---|---|
| none (basket) | $571 | 9.0% | $729 | 2.3% |
| 0.5% | $589 | 7.7% | $754 | 1.8% |
| 1% | $632 | 1.4% | $776 | 1.9% |
| 1.5% | $651 | 2.4% | $798 | 1.9% |

- Accepted at every level. The rule picks **1.5%**.
- The honest gain is the 2018-24 window: about +$47 to +$69 per account over 24 months (+6% to +9%).
- The big drop in lost accounts for 2011-24 is not evidence. It comes from 2013-14 starts that were saved by MR6's design-period trades.
- It cuts both ways. At 1.5%, 31.7% of 2017 starts are lost, against 0% for the basket.
- By start year, MR6 lowers payouts for 2018-19 starts and raises them for 2020-24 starts.

### Caveat for both sims

Both sims count the daily loss only when a trade closes. MR6 holds for several days, so its open loss is not marked each day. Its daily-limit risk is somewhat understated.

## Honest bottom line

- The hunt was wide: 14 styles, 171 pre-declared tests, all with costs.
- The result is mostly negative. That is a real finding, not a failure.
- 2 passes against about 1 expected by luck is not a meaningful excess. For long index trades, 1 to 3 lucky passes were likely.
- MR4 is dead.
- MR6 survives the code and cost checks but not the robustness check. It trades 4 to 5 times a year. Its 2018-23 record is flat.
- **Alpha Swing**: keep the basket unchanged. MR6 does not speed up the challenge with the boost you use.
- **Blueberry**: the pre-declared rule allows MR6 at 1.5%. Expect a small gain at best. If you add it, start smaller (0.5% to 1%) and remember the daily-limit caveat.
- The lesson from earlier work still holds. Slow FX styles (carry, trend, value, momentum, rates, positioning) and event drifts do not survive retail costs on this data. Your edges are the USDJPY clock and calendar flows you already trade.
- Near misses, as leads only (each needs a new pre-declared test on fresh logic, not a re-fit):
  - Nasdaq turn-of-month when stocks beat bonds (design t 1.49).
  - USDJPY before month-end Treasury auctions (design t 1.37; likely the same flow as M-3).
  - Pre-FOMC drift since 2016 (this split was found after looking at the data, so it does not count).

## Files

- Charter: `results/alpha_hunt/CHARTER.md`
- Per-family reports: `results/alpha_hunt/<family>/REPORT.md` (fx_value_mom has only `REPORT_tables.md`).
- Scripts: `run_alpha_<family>.py`.
- Verification of the index passes: `results/alpha_hunt/index_meanrev/verify_code/`, `verify_execution/`, `verify_robustness/`.
- Prop sim: `run_alpha_prop.py`, `results/alpha_hunt/prop/REPORT.md` (+ alpha.csv, blueberry.csv, decision.csv, blueberry_by_year.csv).
