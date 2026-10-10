# FOMC announcement premia (fomc_cycle)

Script: `run_alpha_fomc_cycle.py` (all rules in its docstring, fixed before running). Costs included everywhere (Nasdaq/Nikkei: run_all_matrix.net_r; S&P: 1 pt round trip + 0.25 pt stop slippage + 3%/yr financing; FX: $7/lot, 0.2 pip stop slippage, swap +1%).

**Survivors: 0 of 9 candidate tests** (none); expected by luck: 9 x 0.006 = 0.054.

Survival = design (2010-17; indices from their data start) t >= 2 AND avg R > 0 in check 2018-23 AND holdout 2024-26; even-week variants also need a design-period even-minus-odd Welch t >= 2. Last 3 years = entries after 2023-10-07.

Events: 133 scheduled statements 2010-01..2026-09-16 (data end 2026-10-07); 850 cycle-week windows (455 even, 395 odd).

## All tests (net R per trade; F4/F5 = per event, mean of the legs)

| test | role | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | even-odd Welch t | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 pre-FOMC drift, Nasdaq | candidate | 113 | 0.654 | 51.327 | 1.336 | 0.070 | 1.359 | 44 | -0.095 | -1.099 | 47 | 0.198 | 3.116 | 22 | 0.123 | 0.916 | 24 | 0.145 | 1.168 |  | False |
| F2 pre-FOMC drift, S&P | candidate | 114 | 0.655 | 48.246 | 1.297 | 0.034 | 0.742 | 45 | -0.063 | -0.923 | 47 | 0.114 | 1.869 | 22 | 0.061 | 0.449 | 24 | 0.081 | 0.645 |  | False |
| F3 pre-FOMC drift, Nikkei | candidate | 104 | 0.654 | 48.077 | 1.588 | 0.071 | 1.426 | 35 | 0.119 | 1.090 | 47 | 0.011 | 0.186 | 22 | 0.123 | 1.284 | 24 | 0.120 | 1.283 |  | False |
| F4 short-USD basket, FOMC day | candidate | 131 | 0.666 | 54.962 | 1.056 | 0.069 | 1.185 | 62 | 0.051 | 0.585 | 47 | 0.185 | 2.121 | 22 | -0.126 | -0.791 | 24 | -0.056 | -0.360 |  | False |
| F5 high-yield short-USD, FOMC day | candidate | 131 | 0.666 | 51.145 | 1.055 | 0.033 | 0.477 | 62 | 0.027 | 0.240 | 47 | 0.116 | 1.205 | 22 | -0.128 | -0.786 | 24 | -0.077 | -0.504 |  | False |
| F6 even weeks, Nasdaq | candidate | 380 | 2.188 | 58.684 | 0.866 | 0.065 | 1.712 | 145 | 0.082 | 1.263 | 159 | 0.045 | 0.798 | 76 | 0.075 | 0.895 | 82 | 0.086 | 1.023 | 0.727 | False |
| F7 even weeks, S&P | candidate | 379 | 2.169 | 56.728 | 0.898 | 0.049 | 1.298 | 146 | 0.074 | 1.146 | 158 | 0.024 | 0.418 | 75 | 0.054 | 0.668 | 81 | 0.080 | 0.980 | 1.402 | False |
| F8 even weeks, Nikkei | candidate | 349 | 2.181 | 53.009 | 1.010 | 0.042 | 0.969 | 123 | 0.076 | 1.000 | 150 | -0.061 | -0.955 | 76 | 0.189 | 2.120 | 82 | 0.173 | 2.002 | 1.658 | False |
| F11 week 0 only, Nasdaq | candidate | 113 | 0.654 | 61.062 | 0.880 | 0.117 | 1.506 | 44 | 0.126 | 1.052 | 47 | 0.085 | 0.702 | 22 | 0.166 | 0.864 | 24 | 0.265 | 1.404 | 0.820 | False |
| F9 control: odd weeks, Nasdaq | control | 327 | 1.888 | 57.492 | 0.912 | 0.069 | 1.602 | 125 | 0.011 | 0.146 | 137 | 0.094 | 1.525 | 65 | 0.128 | 1.285 | 71 | 0.131 | 1.400 |  | False |
| F10 control: odd weeks, S&P | control | 326 | 1.865 | 57.362 | 0.759 | 0.007 | 0.160 | 124 | -0.062 | -0.858 | 137 | 0.041 | 0.683 | 65 | 0.065 | 0.675 | 71 | 0.078 | 0.869 |  | False |
| F8c extra: odd weeks, Nikkei | report-only | 298 | 1.867 | 51.342 | 0.938 | -0.003 | -0.076 | 102 | -0.103 | -1.345 | 131 | 0.057 | 0.837 | 65 | 0.031 | 0.298 | 71 | 0.047 | 0.486 |  | False |
| F2g extra: F2 gloss exit | report-only | 114 | 0.655 | 48.246 | 1.299 | 0.034 | 0.746 | 45 | -0.063 | -0.923 | 47 | 0.114 | 1.869 | 22 | 0.061 | 0.449 | 24 | 0.081 | 0.645 |  | False |

## Pre-FOMC drift: decay split (pre-2016 vs 2016+)

| test | split | trades | win % | avg R | t |
|---|---|---|---|---|---|
| F1 pre-FOMC drift, Nasdaq | pre-2016 | 28 | 28.571 | -0.150 | -1.389 |
| F1 pre-FOMC drift, Nasdaq | 2016+ | 85 | 58.824 | 0.142 | 2.527 |
| F2 pre-FOMC drift, S&P | pre-2016 | 29 | 27.586 | -0.135 | -1.449 |
| F2 pre-FOMC drift, S&P | 2016+ | 85 | 55.294 | 0.091 | 1.804 |
| F3 pre-FOMC drift, Nikkei | pre-2016 | 20 | 55.000 | 0.093 | 0.750 |
| F3 pre-FOMC drift, Nikkei | 2016+ | 84 | 46.429 | 0.066 | 1.207 |

Move in bp from entry fill to exit fill (Nasdaq/Nikkei: ask in, bid out; S&P: bid closes), before slippage and financing:

| test | split | n | mean fill-to-fill bp (before slippage/financing) | t |
|---|---|---|---|---|
| F1 pre-FOMC drift, Nasdaq | all | 113 | 17.04 | 2.04 |
| F1 pre-FOMC drift, Nasdaq | pre-2016 | 28 | -12.24 | -0.92 |
| F1 pre-FOMC drift, Nasdaq | 2016+ | 85 | 26.69 | 2.66 |
| F2 pre-FOMC drift, S&P | all | 114 | 13.50 | 2.42 |
| F2 pre-FOMC drift, S&P | pre-2016 | 29 | -3.13 | -0.35 |
| F2 pre-FOMC drift, S&P | 2016+ | 85 | 19.18 | 2.84 |
| F3 pre-FOMC drift, Nikkei | all | 104 | 18.16 | 2.20 |
| F3 pre-FOMC drift, Nikkei | pre-2016 | 20 | 24.97 | 1.19 |
| F3 pre-FOMC drift, Nikkei | 2016+ | 84 | 16.54 | 1.84 |

## Even vs odd cycle weeks: mean daily close-to-close return (bp)

Closes: Nasdaq and Nikkei CFD at 15:55 ET, S&P at the 16:00 hourly close. Day t's return is assigned to t's cycle week (week 0 = day -1..+3, days after the next meeting's day -2 belong to the next cycle).

| market | period | even days | even mean bp | odd days | odd mean bp | all days | all mean bp | even-odd bp | Welch t |
|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | all | 1880 | 8.19 | 1601 | 5.45 | 3539 | 7.44 | 2.74 | 0.64 |
| Nasdaq 100 | design | 733 | 10.69 | 629 | 0.84 | 1374 | 6.30 | 9.85 | 1.98 |
| Nasdaq 100 | check | 777 | 6.62 | 661 | 6.96 | 1483 | 7.77 | -0.34 | -0.04 |
| Nasdaq 100 | holdout | 370 | 6.54 | 311 | 11.59 | 682 | 9.00 | -5.05 | -0.49 |
| S&P 500 | all | 1866 | 4.59 | 1582 | 4.23 | 3506 | 4.85 | 0.36 | 0.10 |
| S&P 500 | design | 720 | 8.05 | 612 | -1.01 | 1344 | 4.04 | 9.05 | 2.15 |
| S&P 500 | check | 779 | 1.26 | 661 | 6.83 | 1485 | 4.63 | -5.57 | -0.88 |
| S&P 500 | holdout | 367 | 4.85 | 309 | 9.04 | 677 | 6.93 | -4.19 | -0.56 |
| Nikkei 225 | all | 1692 | 7.49 | 1421 | 4.19 | 3167 | 6.39 | 3.30 | 0.67 |
| Nikkei 225 | design | 586 | 13.04 | 489 | -2.51 | 1083 | 5.87 | 15.54 | 1.85 |
| Nikkei 225 | check | 736 | -0.88 | 623 | 8.22 | 1404 | 4.28 | -9.10 | -1.36 |
| Nikkei 225 | holdout | 370 | 15.35 | 309 | 6.67 | 680 | 11.59 | 8.68 | 0.71 |

## F6 (even weeks, Nasdaq) vs buy-and-hold over the same months

| period | years | F6 windows | F6 window days | share of days in windows % | F6 gross %/yr (log) | F6 net %/yr | buy-and-hold %/yr (log) |
|---|---|---|---|---|---|---|---|
| all | 13.83 | 380.00 | 1865.00 | 53.53 | 6.55 | 5.72 | 16.06 |
| design | 5.25 | 145.00 | 712.00 | 53.78 | 8.93 | 7.73 | 13.58 |
| check | 5.88 | 159.00 | 783.00 | 52.80 | 3.51 | 2.97 | 16.58 |
| holdout | 2.69 | 76.00 | 370.00 | 54.65 | 8.53 | 7.80 | 19.79 |

## F4 / F5 legs (long each currency vs USD, 18:00 ET day -1 to 16:55 ET day 0)

| leg | trades | win % | avg R | t | design avg R | check avg R | holdout avg R |
|---|---|---|---|---|---|---|---|
| long AUD vs USD (AUDUSD) | 131.000 | 54.198 | 0.073 | 0.945 | 0.030 | 0.253 | -0.193 |
| long EUR vs USD (EURUSD) | 131.000 | 56.489 | 0.121 | 1.661 | 0.138 | 0.216 | -0.130 |
| long GBP vs USD (GBPUSD) | 131.000 | 55.725 | 0.116 | 1.765 | 0.112 | 0.237 | -0.132 |
| long NZD vs USD (NZDUSD) | 131.000 | 51.908 | 0.063 | 0.870 | 0.024 | 0.189 | -0.095 |
| long CAD vs USD (USDCAD) | 131.000 | 48.855 | 0.039 | 0.593 | 0.058 | 0.071 | -0.082 |
| long CHF vs USD (USDCHF) | 131.000 | 56.489 | 0.083 | 1.171 | 0.130 | 0.152 | -0.200 |
| long JPY vs USD (USDJPY) | 131.000 | 49.618 | -0.011 | -0.153 | -0.138 | 0.175 | -0.048 |

Legs with avg R > 0: all 6/7, design 6/7, check 7/7, holdout 0/7. F4 events with fewer than 7 legs: 0.


F5 top-2 picks (policy rate dated <= day -2), number of events:

| top2 | events |
|---|---|
| AUD+NZD | 68 |
| CAD+NZD | 32 |
| AUD+GBP | 15 |
| GBP+NZD | 10 |
| AUD+CAD | 6 |

F5 legs by currency:

| ccy | legs | avg R |
|---|---|---|
| AUD | 89.000 | -0.035 |
| CAD | 38.000 | 0.030 |
| GBP | 25.000 | -0.118 |
| NZD | 110.000 | 0.123 |

## Diagnostics

- Release times: 85 statement pages state a time ('For release at ...'); 0 differ from the rule. Older pages say only 'For immediate release'; the rule time is used there.

- Time exits whose exit minute and the 4 before it had no ticks (stale price): F3 1, F6 2, F8 2, F11 1, F9 3, F8c 3.

- F2g (report-only) uses the spec's gloss exit bar (12:00-13:00 also for T = 14:15); it differs from F2 only on the 2012 14:15 events.


## Sources

- FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021+), https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm (2010-2020); statement pages https://www.federalreserve.gov/newsevents/pressreleases/monetary<YYYYMMDD>a.htm (fetched 2026-10-10) -> data/extra/fomc_dates.csv.

- Policy rates: data/extra/policy_rates_bis_daily.csv, data/extra/ecb_deposit_rate_daily.csv (URLs in data/extra/SOURCES.csv).


Files: summary.csv, trades.csv, fx_legs.csv, f5_rate_picks.csv, week_windows.csv.


## Prop sim

Not run: no variant survived, so nothing is added to the Alpha Swing basket.

## Reading (written after the run; numbers from the tables above)

**Verdict: no FOMC-premium variant clears the bar (0 of 9; luck alone would give ~0.05). Nothing goes to the prop basket.**

- **Pre-FOMC drift (F1-F3).** Before costs there is a drift: on average +13.5 bp per event on the S&P (t 2.4) and +17 bp on
  the Nasdaq (t 2.0) from 14:00 ET on day -1 to just before the statement. That is a third of Lucca-Moench's +49 bp. It is
  also on the wrong side of the expected decay: 2012-15 was negative (S&P -3 bp, Nasdaq -12 bp, win rate 28%) and all of
  the drift is in 2016+. Because of that, F1/F2 fail the design period (Nasdaq -0.10R, S&P -0.06R). After costs F1 is
  +0.20R in check (t 3.1) and +0.12R in holdout (t 0.9). Picking "2016+" now would be a split chosen after seeing the data,
  so it is not a survivor. At most it is something to watch: about 8 trades a year, 1R stop, roughly 23 hours of exposure.
- **FOMC-cycle even weeks (F6-F8, F11).** Over 2012-17 the CMVJ pattern shows up in daily returns. Even weeks beat odd weeks
  by +9 bp/day on the S&P (Welch t 2.15) and +10 bp/day on the Nasdaq (t 1.98); this sample overlaps CMVJ's own. Out of
  sample the pattern flips: in 2018-23 and 2024-26 odd weeks earned more than even weeks on both US indices. As trades,
  even weeks earn only about the equity premium. Their design t is 1.0-1.3 and none beats its odd-week control (Welch t
  0.7-1.7, needed >= 2). F6 makes 5.7%/yr net while holding 54% of days; buy-and-hold made 16%/yr over the same months.
  F8 (Nikkei) is +0.19R in holdout (t 2.1) but -0.06R in check, so it is not stable.
- **Short USD on FOMC day (F4, F5).** All 7 legs gained in 2018-23 (+0.19R per event, t 2.1). They were small in 2010-17
  (+0.05R, t 0.6) and lost on all 7 legs in 2024-26 (-0.13R). Mueller et al. predict a bigger effect against high-rate
  currencies. Here the high-yield tilt (F5, mostly AUD/NZD) did worse than the plain basket, not better. Fails.
- **Decay test.** Kurov et al. expect weakening after 2015. Here it is the reverse: no drift in 2012-15, positive since.
  The split doubles as a warning that this premium comes and goes over periods of several years.

Data and spec notes:
- Release times: the 85 statement pages from 2016 onward show "For release at 2:00 p.m.", which matches the rule. Pages
  and PDFs for 2010-15 say only "For immediate release", so the rule times (14:15; 12:30 for the 2011-12 press-conference
  meetings; 14:00 from 2013) are used there without a check on the page.
- The holidays package misses the NYSE closure on 2025-01-09 (national day of mourning), so it was added by hand.
- F2 spec fix: the rule "last full bar ending at or before T-5" is used for T = 14:15 (the 13:00-14:00 bar). The spec's
  gloss version (F2g, the 12:00-13:00 bar) gives the same result to three decimals.
- daily_table drops its first ~56 sessions (SMA50 warm-up), and index data is patchy before 2012. So the FX legs start at
  the 2010-04 meeting, and the Nasdaq/S&P/Nikkei tests start in 2012.
- Prop sim not run (no survivor). Runtime about 1 minute, one market in memory at a time, no multiprocessing.
