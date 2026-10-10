# US Treasury auction concession cycle via USDJPY and gold (ust_auction)

Script: `run_alpha_ust_auction.py` (all rules in its docstring, fixed before running). Costs included everywhere (USDJPY: $7/lot, 0.2 pip stop slippage, swap +1%; XAUUSD: run_all_matrix.net_r with commission, slippage and 3%/yr financing).

**Survivors: 0 of 8 tests** (none); expected by luck: 8 x 0.006 = 0.048.

Survival = design 2010-17 t >= 2 AND avg R > 0 in check 2018-23 AND holdout 2024-26 (periods by entry day). Last 3 years = entries after 2023-10-07.

Rules: PRE = 15:55 NY five NYSE trading days before the cluster's first auction -> 12:55 NY on its last auction day; POST = 13:05 NY on the last auction day -> 15:55 NY two trading days later. USDJPY BUY in PRE / SELL in POST, gold SELL in PRE / BUY in POST; market entry, time exit, SL 1.0 x ATR20, no TP. MID = 3y/10y/30y (incl. reopenings), END = 2y/5y/7y; nominal fixed-coupon only (TIPS, FRNs dropped).

## Auction clusters

| group | clusters | auctions | first | last | clusters with < 3 auctions |
|---|---|---|---|---|---|
| END | 209 | 624 | 2009-06-23 | 2026-09-24 | 2 |
| MID | 209 | 627 | 2009-06-09 | 2026-10-08 | 0 |

Dropped as not real supply (offering < $1bn, a spec fix): 2019-06-21 9-Year 11-Month $25m, 2021-12-02 19-Year 11-Month $25m. Consecutive same-group clusters whose windows overlap: 1 (the debt-ceiling split of Oct/Nov 2015).


Skipped windows per variant:

| variant | clusters | outside data / no ATR | no live entry minute | no fill / exit before entry |
|---|---|---|---|---|
| USDJPY-MID-PRE | 209 | 11 | 0 | 0 |
| USDJPY-MID-POST | 209 | 11 | 0 | 0 |
| USDJPY-END-PRE | 209 | 10 | 0 | 0 |
| USDJPY-END-POST | 209 | 9 | 0 | 0 |
| XAUUSD-MID-PRE | 209 | 11 | 0 | 0 |
| XAUUSD-MID-POST | 209 | 11 | 0 | 0 |
| XAUUSD-END-PRE | 209 | 10 | 0 | 0 |
| XAUUSD-END-POST | 209 | 9 | 0 | 0 |

## All tests (net R per trade)

| test | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY-MID-PRE | 198 | 1.005 | 33.838 | 1.746 | -0.065 | -0.659 | 93 | -0.063 | -0.438 | 72 | 0.013 | 0.078 | 33 | -0.237 | -1.024 | 35 | -0.278 | -1.267 | False |
| USDJPY-MID-POST | 198 | 1.005 | 43.434 | 0.966 | -0.100 | -1.690 | 93 | -0.072 | -0.868 | 72 | -0.067 | -0.618 | 33 | -0.251 | -1.968 | 36 | -0.182 | -1.340 | False |
| USDJPY-END-PRE | 199 | 1.011 | 48.744 | 1.635 | 0.264 | 2.505 | 94 | 0.218 | 1.370 | 72 | 0.196 | 1.170 | 33 | 0.546 | 2.104 | 36 | 0.476 | 1.943 | False |
| USDJPY-END-POST | 200 | 1.010 | 46.000 | 1.157 | -0.006 | -0.082 | 95 | -0.075 | -0.788 | 72 | 0.060 | 0.533 | 33 | 0.049 | 0.224 | 36 | 0.060 | 0.292 | False |
| XAUUSD-MID-PRE | 198 | 1.005 | 25.758 | 1.469 | -0.352 | -4.091 | 93 | -0.176 | -1.252 | 72 | -0.453 | -3.660 | 33 | -0.625 | -3.451 | 35 | -0.502 | -2.600 | False |
| XAUUSD-MID-POST | 198 | 1.005 | 49.495 | 0.998 | -0.008 | -0.125 | 93 | -0.117 | -1.487 | 72 | 0.077 | 0.628 | 33 | 0.112 | 0.653 | 36 | 0.201 | 1.106 | False |
| XAUUSD-END-PRE | 199 | 1.011 | 38.191 | 1.703 | 0.031 | 0.298 | 94 | 0.116 | 0.750 | 72 | -0.146 | -0.986 | 33 | 0.172 | 0.572 | 36 | 0.073 | 0.259 | False |
| XAUUSD-END-POST | 200 | 1.010 | 51.000 | 0.908 | -0.019 | -0.330 | 95 | -0.068 | -0.810 | 72 | -0.022 | -0.258 | 33 | 0.126 | 0.689 | 36 | 0.103 | 0.609 | False |

## Report-only: both markets pooled per group x window

| test | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled MID-PRE (USDJPY BUY + gold SELL) | 396 | 2.009 | 29.798 | 1.614 | -0.208 | -3.178 | 186 | -0.120 | -1.189 | 144 | -0.220 | -2.114 | 66 | -0.431 | -2.917 | 70 | -0.390 | -2.675 |
| pooled MID-POST (USDJPY SELL + gold BUY) | 396 | 2.009 | 46.465 | 0.988 | -0.054 | -1.230 | 186 | -0.094 | -1.658 | 144 | 0.005 | 0.066 | 66 | -0.069 | -0.641 | 72 | 0.010 | 0.083 |
| pooled END-PRE (USDJPY BUY + gold SELL) | 398 | 2.022 | 43.467 | 1.660 | 0.148 | 1.994 | 188 | 0.167 | 1.508 | 144 | 0.025 | 0.223 | 66 | 0.359 | 1.808 | 72 | 0.274 | 1.469 |
| pooled END-POST (USDJPY SELL + gold BUY) | 400 | 2.020 | 48.500 | 1.026 | -0.013 | -0.275 | 190 | -0.071 | -1.130 | 144 | 0.019 | 0.265 | 66 | 0.088 | 0.619 | 72 | 0.082 | 0.617 |

## Avg R per calendar year (by entry day)

| variant | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY-MID-PRE | -0.30 | -0.23 | 0.47 | 0.11 | -0.08 | -0.16 | -0.40 | -0.03 | -0.11 | -0.41 | -0.23 | 0.21 | 1.00 | -0.38 | 0.03 | -0.66 | -0.10 |
| USDJPY-MID-POST | 0.21 | 0.14 | -0.14 | -0.12 | 0.05 | -0.30 | -0.28 | -0.05 | 0.23 | -0.12 | 0.14 | -0.07 | -0.43 | -0.15 | -0.25 | -0.28 | -0.22 |
| USDJPY-END-PRE | -0.66 | -0.10 | 0.82 | 0.26 | 0.77 | 0.01 | 0.06 | 0.37 | 0.39 | -0.42 | -0.23 | 0.73 | -0.05 | 0.76 | 0.67 | 0.16 | 0.89 |
| USDJPY-END-POST | -0.07 | 0.00 | 0.10 | -0.04 | -0.17 | -0.22 | -0.20 | 0.01 | 0.09 | -0.02 | 0.41 | -0.17 | 0.33 | -0.28 | -0.05 | 0.01 | 0.24 |
| XAUUSD-MID-PRE | -0.89 | 0.15 | -0.12 | 0.11 | -0.95 | 0.43 | -0.45 | 0.04 | -0.78 | -0.72 | -0.56 | -0.14 | -0.43 | -0.09 | -0.68 | -0.93 | -0.17 |
| XAUUSD-MID-POST | -0.31 | 0.05 | -0.31 | -0.36 | 0.00 | 0.20 | -0.32 | 0.07 | -0.19 | -0.05 | 0.41 | 0.16 | -0.45 | 0.57 | 0.27 | 0.17 | -0.17 |
| XAUUSD-END-PRE | -0.52 | 0.11 | -0.14 | 0.52 | 0.65 | 0.22 | -0.03 | -0.06 | -0.17 | -0.69 | 0.16 | -0.05 | 0.02 | -0.14 | 0.14 | -0.09 | 0.56 |
| XAUUSD-END-POST | 0.22 | 0.04 | 0.23 | -0.56 | -0.20 | -0.29 | 0.17 | -0.08 | -0.21 | 0.15 | 0.18 | -0.05 | -0.20 | 0.00 | -0.07 | 0.51 | -0.13 |

Trades per year:

| variant | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY-MID-PRE | 9 | 12 | 13 | 12 | 11 | 12 | 12 | 12 | 13 | 12 | 11 | 12 | 12 | 12 | 13 | 11 | 9 |
| USDJPY-MID-POST | 9 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |
| USDJPY-END-PRE | 9 | 12 | 12 | 12 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |
| USDJPY-END-POST | 10 | 12 | 12 | 12 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |
| XAUUSD-MID-PRE | 9 | 12 | 13 | 12 | 11 | 12 | 12 | 12 | 13 | 12 | 11 | 12 | 12 | 12 | 13 | 11 | 9 |
| XAUUSD-MID-POST | 9 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |
| XAUUSD-END-PRE | 9 | 12 | 12 | 12 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |
| XAUUSD-END-POST | 10 | 12 | 12 | 12 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 9 |

Years with avg R > 0:

| variant | years > 0 | years |
|---|---|---|
| USDJPY-MID-PRE | 5 | 17 |
| USDJPY-MID-POST | 5 | 17 |
| USDJPY-END-PRE | 12 | 17 |
| USDJPY-END-POST | 8 | 17 |
| XAUUSD-MID-PRE | 4 | 17 |
| XAUUSD-MID-POST | 9 | 17 |
| XAUUSD-END-PRE | 8 | 17 |
| XAUUSD-END-POST | 8 | 17 |

## Signed move before costs (fill to fill, in the trade's direction)

USDJPY in pips, gold in USD; 'mean R before costs' uses the simulator's bid/ask fills (spread paid) but no commission, slippage or financing.

| test | unit | mean move (signed, fill to fill) | t | mean move bp | mean R before costs | mean R net | mean SL (unit) | mean hours held | SL exits % | stale exits | design move | check move | holdout move |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY-MID-PRE | pips | -2.91 | -0.29 | -1.08 | -0.06 | -0.06 | 93.81 | 136.44 | 56.57 | 0 | -3.63 | 6.47 | -21.33 |
| USDJPY-MID-POST | pips | -8.37 | -1.39 | -5.98 | -0.07 | -0.10 | 94.27 | 83.17 | 25.25 | 0 | -5.71 | -4.01 | -25.36 |
| USDJPY-END-PRE | pips | 20.44 | 2.15 | 16.64 | 0.27 | 0.26 | 94.27 | 155.64 | 44.72 | 0 | 14.69 | 16.75 | 44.86 |
| USDJPY-END-POST | pips | 1.87 | 0.28 | 1.34 | 0.03 | -0.01 | 94.32 | 79.21 | 31.00 | 0 | -5.76 | 8.64 | 9.03 |
| XAUUSD-MID-PRE | USD | -9.22 | -2.75 | -43.43 | -0.31 | -0.35 | 28.34 | 127.91 | 66.67 | 0 | -1.75 | -7.48 | -34.04 |
| XAUUSD-MID-POST | USD | -0.68 | -0.27 | -1.71 | 0.01 | -0.01 | 28.56 | 79.89 | 29.29 | 1 | -2.35 | 2.30 | -2.47 |
| XAUUSD-END-PRE | USD | 6.34 | 1.25 | 19.98 | 0.08 | 0.03 | 28.45 | 145.42 | 54.27 | 0 | 4.30 | 0.46 | 24.98 |
| XAUUSD-END-POST | USD | 1.46 | 0.69 | 3.03 | 0.00 | -0.02 | 28.60 | 81.46 | 27.00 | 3 | -0.35 | 0.22 | 9.39 |

## Diagnostic 1: is the yield concession there? (bp, daily closes)

PRE = close of the PRE start day -> close of the day before the last auction day; AUCTION DAY = close-to-close on the last auction day (holds both the pre-13:00 run-up and the post-result move); POST = close of the last auction day -> close two trading days later. Theory: PRE > 0 and POST < 0. FRED H.15 constant-maturity yields; bond-holiday gaps forward-filled.

| series | group | period | clusters | PRE bp | PRE t | AUCTION DAY bp | AUCTION DAY t | POST bp | POST t |
|---|---|---|---|---|---|---|---|---|---|
| DGS10 | MID | all | 201 | 2.02 | 2.23 | -0.11 | -0.26 | 0.23 | 0.42 |
| DGS10 | MID | design | 96 | 2.06 | 1.54 | -0.01 | -0.02 | -0.99 | -1.63 |
| DGS10 | MID | check | 72 | 2.60 | 1.76 | -0.42 | -0.52 | 0.65 | 0.57 |
| DGS10 | MID | holdout | 33 | 0.64 | 0.28 | 0.27 | 0.25 | 2.85 | 2.63 |
| DGS10 | END | all | 202 | 0.23 | 0.28 | -0.10 | -0.27 | -1.15 | -2.25 |
| DGS10 | END | design | 97 | 0.02 | 0.02 | 0.28 | 0.56 | -1.33 | -2.02 |
| DGS10 | END | check | 72 | 0.10 | 0.06 | -0.32 | -0.47 | -1.51 | -1.58 |
| DGS10 | END | holdout | 33 | 1.12 | 0.68 | -0.73 | -1.03 | 0.18 | 0.14 |
| DGS2 | MID | all | 201 | 1.52 | 2.18 | 0.12 | 0.33 | 0.52 | 0.80 |
| DGS2 | MID | design | 96 | 0.91 | 1.42 | 0.06 | 0.23 | -0.15 | -0.39 |
| DGS2 | MID | check | 72 | 2.61 | 1.94 | 0.62 | 0.73 | 0.65 | 0.39 |
| DGS2 | MID | holdout | 33 | 0.91 | 0.37 | -0.79 | -0.73 | 2.18 | 2.10 |
| DGS2 | END | all | 202 | 0.31 | 0.49 | -0.21 | -0.70 | -0.39 | -0.96 |
| DGS2 | END | design | 97 | 1.53 | 2.53 | -0.28 | -0.96 | -0.71 | -2.24 |
| DGS2 | END | check | 72 | -0.36 | -0.28 | -0.39 | -0.59 | -0.78 | -0.87 |
| DGS2 | END | holdout | 33 | -1.82 | -0.99 | 0.39 | 0.54 | 1.39 | 1.13 |

## Diagnostic 2: overlap with the M-3 USDJPY leg (11:00-12:00 UTC, 3rd-last weekday, BUY)

| M-3 USDJPY subset | trades | share % | win % | avg R | t | design n | design avg R | check n | check avg R | holdout n | holdout avg R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all M-3 trades | 189 | 100.000 | 58.730 | 0.124 | 3.866 | 84 | 0.091 | 72 | 0.210 | 33 | 0.022 |
| inside END-PRE | 121 | 64.021 | 62.810 | 0.156 | 3.776 | 56 | 0.103 | 45 | 0.235 | 20 | 0.131 |
| outside END-PRE | 68 | 35.979 | 51.471 | 0.067 | 1.336 | 28 | 0.066 | 27 | 0.170 | 13 | -0.146 |
| inside END-POST | 62 | 32.804 | 50.000 | 0.078 | 1.561 | 24 | 0.104 | 25 | 0.170 | 13 | -0.146 |
| outside both | 6 | 3.175 | 66.667 | -0.051 | -0.209 | 4 | -0.163 | 2 | 0.172 | 0 |  |

Inside vs outside END-PRE, Welch t of the difference in avg R: 1.38.


## Diagnostic 3: gotobi fixes inside the scheduled window (entry -> scheduled exit)

| test | 0 fixes n | 0 fixes avg R | 1 fix n | 1 fix avg R | >=2 fixes n | >=2 fixes avg R | corr(R, n gotobi fixes) | mean n gotobi fixes |
|---|---|---|---|---|---|---|---|---|
| USDJPY-MID-PRE | 0 |  | 42 | -0.065 | 156 | -0.065 | 0.000 | 1.788 |
| USDJPY-MID-POST | 33 | -0.058 | 165 | -0.108 | 0 |  | -0.022 | 0.833 |
| USDJPY-END-PRE | 0 |  | 58 | 0.264 | 141 | 0.265 | 0.000 | 1.709 |
| USDJPY-END-POST | 41 | 0.286 | 157 | -0.086 | 2 | 0.281 | -0.137 | 0.805 |
| XAUUSD-MID-PRE | 0 |  | 42 | -0.266 | 156 | -0.375 | -0.037 | 1.788 |
| XAUUSD-MID-POST | 33 | -0.056 | 165 | 0.001 | 0 |  | 0.023 | 0.833 |
| XAUUSD-END-PRE | 0 |  | 58 | 0.249 | 141 | -0.059 | -0.096 | 1.709 |
| XAUUSD-END-POST | 41 | 0.162 | 157 | -0.054 | 2 | -1.005 | -0.135 | 0.805 |

## Sources

- Auctions: data/extra/ust_auctions.csv, https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query (full URL in data/extra/SOURCES.csv).

- Yields: data/extra/DGS10.csv, data/extra/DGS2.csv (FRED).


Files: summary.csv, trades.csv, per_year.csv, clusters.csv, yield_windows.csv, m3_overlap.csv.


## Prop sim

Not run: no variant survived, so nothing is added to the Alpha Swing basket.

## Interpretation (written after the run; nothing here changes a test)

- **0 of 8 tests survive** (about 0.05 expected by luck). No prop sim was run.
- **Best non-survivor: USDJPY-END-PRE** (buy USDJPY from 15:55 NY five days before the 2y/5y/7y week to 12:55 NY on
  the last auction day): +0.264R net, t 2.5 over all 199 trades, +20 pips gross (t 2.15), 12 of 17 years positive,
  avg R positive in every period (design +0.218, t 1.37; check +0.196; holdout +0.546, t 2.10). It **fails the design
  bar** (t 1.37 < 2). The auction channel also cannot explain it. DGS10 does **not** rise before the END clusters
  (PRE +0.23 bp, t 0.28; DGS2 +0.31 bp, t 0.49), so any USDJPY gain in these windows comes from something else. The
  most likely source is the late-month USD bid: 64% of M-3 trades fall inside an END-PRE window, and M-3 does better
  inside than outside (+0.156R vs +0.067R; Welch t 1.38, not significant). The M-3 hour itself is only about 3-4 pips
  of the 20, and the USDJPY drift over the sample gives about +6 bp over the average hold (+16.6 bp observed). This
  is a late-month USDJPY drift, not a Treasury-supply effect. It is not tradeable under the charter, and it would
  largely double the existing M-3 exposure.
- **MID clusters (3y/10y/30y):** the yield concession does exist in DGS10 (PRE +2.0 bp, t 2.23; weak in the holdout,
  +0.6 bp), but no recovery follows (POST +0.2 bp). USDJPY does not pass it through (MID-PRE -0.065R, -2.9 pips).
  Gold moves *against* the theory: shorting gold in MID-PRE loses -0.35R (t -4.1). Part of that is gold's uptrend
  (drift-implied -12 bp over the hold vs -43 bp observed; 2024-26 gold drift is about 4x the sample average). Even
  reversed, it would fail the design bar (design t 1.25). The mirror image, short gold in END-PRE +20 bp against a
  drift-implied -14 bp, hints at a gold pattern within the month (firm in the first half, soft in the last third).
  That pattern has nothing to do with Treasury supply, because USDJPY does not share it. It is a post-hoc lead only
  and would need its own pre-declared family.
- **POST windows:** there is no post-auction recovery trade in either market (USDJPY SELL -0.10R / -0.01R; gold BUY
  -0.01R / -0.02R), although DGS10 falls -1.15 bp (t -2.25) in the two days after the END cluster.
- **Gotobi:** every PRE window contains at least one gotobi fix, so there is nothing to compare there (correlation
  about 0). END-POST windows without a fix did better (USDJPY SELL +0.29R vs -0.09R, n = 41), but this was not
  selected on and the sample is small.
- **Costs** are small here (stop about 94 pips on USDJPY, about $28 on gold): USDJPY-END-PRE goes from +0.27R gross
  to +0.26R net. These ideas fail on signal, not on costs.
