# Alpha hunt: US equity-index overnight drift at the European open (`eq_overnight_drift`)

Rules, variants and the survival bar are in the docstring of `run_alpha_eq_overnight_drift.py` (fixed before running). Long at the 08:00 Berlin open (first live minute in 07:55-08:00), exit 09:00 Berlin (X1) or 09:25 NY (X2), stop 0.5 / 1.0 x ATR20, all costs. Periods: design from data start (European-open minutes live from about 2013) to 2017, check 2018-23, holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.

**Tests: 14 (7 variants x 2 markets). Nasdaq survivors of the charter bar (design t >= 2, check and holdout avg R > 0): 0 (none). All tests meeting the charter bar (incl. S&P): 0. Expected by luck: 0.08.**

## Verdict (written after the run)

**No test survives.** 0 of 14 tests meet the charter bar, against 0.08 expected by luck. Every Nasdaq variant has
negative avg R in the 2018-23 check period, so none could pass whatever the design result. The S&P replication
"passes" only for ON6 (avg R +0.008, t 0.4, 2 of 3 periods positive). That is noise: Nasdaq ON6 is negative in
design and check.

1. **The drift exists before costs, but it is about 1 bp, not 2-6 bp.** Long from 08:00 to 09:00 Berlin every
   morning (ON1) earns +0.88 bp gross per trade on the Nasdaq (t 2.3) and +0.67 bp on the S&P (t 2.6). The sign
   matches the European-open drift of Boyarchenko, Larsen & Whelan. The size is much smaller than the plan
   assumed.
2. **Costs are 3-5 times the drift.** Average cost is 3.3 bp per trade. The median Nasdaq spread at 07:55 Berlin
   is 5.9 bp in the design period, 2.8 bp in check and 1.6 bp in holdout, against 5.7, 1.1 and 0.7 bp at
   10:00 NY. Before 2018 the CFD spread was wide all day; since 2018 the European open costs 2-2.6 times the
   US-hours spread. Even in 2024-26 the cost of ON1 (1.34 bp) uses up its gross drift (1.29 bp), so avg R is
   -0.005.
3. **The dealer-inventory channel appears in 2013-17 and then disappears.** The ON2 - ON7 gross gap (after a down
   session minus after an up session) is +2.2 bp on the Nasdaq (Welch t 2.4) and +1.5 bp on the S&P (t 2.3) in
   the design period. It is about 0 in the check period (t 0.1 and 0.0) and in the holdout (t 0.1 and 0.0). The
   r_cc terciles show the same picture: no ordering after 2017. Bigger down days (ON3) do not rescue the X1 exit.
   After costs, ON3 is about 0 on the Nasdaq and negative on the S&P.
4. **The longer hold (X2, to 09:25 NY; ON5 and ON6) is the only area with positive recent numbers.** Holdout and
   last-3-year avg R are +0.02 to +0.06 (t 1.0 to 1.7) on both markets. Gross is 5-12 bp per trade in 2024-26.
   All four are negative in the check period, and all but S&P ON6 are negative in design. In 2024-26 they
   were long the index for 7 hours in a strong bull market. This is beta, not a demonstrated edge. Record it as
   an observation, not a candidate.
5. **The design-period data is thin on the Nasdaq.** The 07:55-08:00 Berlin minute has ticks on only 29% / 6% / 5%
   of mornings in 2015 / 2016 / 2017 (the feed starts on the hour), so Nasdaq design n is 466 (ON1), mostly from
   2013-14. This cannot change the verdict, because the check period is negative for all seven Nasdaq variants.
   The S&P hourly bars cover 2013-17 fully, and every one-hour (X1) S&P variant is negative there too.
6. **Other diagnostics.** Correlation of daily R with the basket legs is about 0 (|corr| < 0.07). ON3 and ON6
   share 81% (Nasdaq) and 85% (S&P) of their signal days with index_meanrev MR1. No prop sim was run (no
   survivor).
7. **Contamination.** ON1 is the flow-atlas watch-list cell, so its positive gross drift is not new evidence. The
   new evidence (ON2-ON6 and the ON2 - ON7 gap) fails after 2017: all five variants are negative in the check
   period, and the gap is about 0 in both later periods.

Bottom line: the overnight drift at the European open is real before costs on both indices. At about 1 bp per
hour it is far below the 1.3-6 bp round-trip cost of a retail CFD at that hour, and the conditional
(after-selling) version did not hold out of sample. Drop the family.

### Gross drift and cost by period (bp per trade; from trades.csv, gross_bp / cost_bp columns)

Nasdaq gross = mid to mid; S&P gross = bid to bid. t is the per-trade t of gross bp.

| market | variant | all gross bp | all gross t | all cost bp | design gross bp | design gross t | design cost bp | check gross bp | check gross t | check cost bp | holdout gross bp | holdout gross t | holdout cost bp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | ON1 | 0.88 | 2.30 | 3.28 | 0.77 | 1.72 | 6.14 | 0.72 | 1.19 | 3.29 | 1.29 | 2.07 | 1.34 |
| Nasdaq 100 | ON2 | 1.18 | 1.81 | 3.26 | 2.09 | 2.81 | 6.06 | 0.80 | 0.80 | 3.29 | 1.39 | 1.19 | 1.33 |
| Nasdaq 100 | ON3 | 3.14 | 1.94 | 2.98 | 1.45 | 0.96 | 5.34 | 3.17 | 1.32 | 3.26 | 3.84 | 1.40 | 1.35 |
| Nasdaq 100 | ON4 | 1.46 | 2.42 | 3.22 | 2.02 | 2.81 | 6.20 | 1.42 | 1.51 | 3.27 | 1.19 | 1.29 | 1.35 |
| Nasdaq 100 | ON5 | 3.19 | 1.61 | 3.25 | 3.96 | 1.28 | 6.05 | 1.89 | 0.65 | 3.27 | 5.47 | 1.45 | 1.32 |
| Nasdaq 100 | ON6 | 3.54 | 0.76 | 2.99 | 2.62 | 0.43 | 5.36 | -0.16 | -0.02 | 3.28 | 11.55 | 1.42 | 1.35 |
| Nasdaq 100 | ON7 | 0.66 | 1.42 | 3.28 | -0.11 | -0.20 | 6.22 | 0.65 | 0.86 | 3.29 | 1.19 | 1.75 | 1.34 |
| S&P 500 | ON1 | 0.67 | 2.59 | 3.35 | 1.47 | 4.54 | 4.95 | 0.12 | 0.25 | 2.89 | 0.50 | 1.08 | 1.64 |
| S&P 500 | ON7 | 0.44 | 1.42 | 3.32 | 0.86 | 1.99 | 4.94 | 0.10 | 0.18 | 2.89 | 0.49 | 0.99 | 1.64 |
| S&P 500 | ON2 | 0.98 | 2.24 | 3.36 | 2.38 | 4.79 | 4.97 | 0.10 | 0.13 | 2.89 | 0.51 | 0.58 | 1.64 |
| S&P 500 | ON4 | 1.04 | 2.61 | 3.29 | 2.10 | 4.37 | 4.95 | 0.70 | 0.98 | 2.89 | 0.18 | 0.24 | 1.63 |
| S&P 500 | ON5 | 3.29 | 2.50 | 3.35 | 2.89 | 1.83 | 4.96 | 2.66 | 1.14 | 2.88 | 5.42 | 1.95 | 1.62 |
| S&P 500 | ON3 | 1.50 | 1.38 | 3.30 | 3.00 | 2.31 | 4.97 | 1.24 | 0.68 | 2.90 | -0.19 | -0.08 | 1.67 |
| S&P 500 | ON6 | 6.08 | 1.82 | 3.28 | 7.79 | 1.90 | 4.95 | 4.19 | 0.74 | 2.89 | 7.93 | 1.11 | 1.65 |

## Judging

Nasdaq gets the charter bar; the S&P replicates if avg R > 0 over the whole period and in at least 2 of the 3 periods.

| variant | Nasdaq design t | Nasdaq check avg R | Nasdaq holdout avg R | Nasdaq last3y avg R | Nasdaq charter bar | S&P avg R | S&P periods > 0 | S&P replicates | S&P charter bar |
|---|---|---|---|---|---|---|---|---|---|
| ON1 | -13.114 | -0.035 | -0.005 | -0.008 | False | -0.057 | 0 | False | False |
| ON2 | -6.432 | -0.033 | -0.002 | -0.004 | False | -0.051 | 0 | False | False |
| ON3 | -2.716 | -0.011 | 0.028 | 0.027 | False | -0.038 | 0 | False | False |
| ON4 | -6.886 | -0.025 | -0.005 | -0.008 | False | -0.048 | 0 | False | False |
| ON5 | -0.446 | -0.015 | 0.021 | 0.027 | False | -0.011 | 1 | False | False |
| ON6 | -0.545 | -0.031 | 0.058 | 0.062 | False | 0.008 | 2 | True | False |
| ON7 | -12.355 | -0.036 | -0.008 | -0.011 | False | -0.062 | 0 | False | False |


## Nasdaq 100 (USATECHIDXUSD), minute bid/ask

Months with a live entry morning: 136.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | month t | design n | design avg R | design t | design month t | check n | check avg R | check t | check month t | holdout n | holdout avg R | holdout t | holdout month t | last3y n | last3y avg R | last3y t | SL % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 every morning, X1, SL 0.5 ATR | 2604.000 | 19.147 | 39.670 | 0.879 | -0.039 | -10.133 | -8.169 | 466.000 | -0.100 | -13.114 | -7.706 | 1445.000 | -0.035 | -6.488 | -6.589 | 693.000 | -0.005 | -0.722 | -0.652 | 751.000 | -0.008 | -1.179 | 0.269 |
| ON2 r_cc < 0, X1, SL 0.5 ATR | 1121.000 | 8.243 | 42.194 | 0.896 | -0.033 | -5.152 | -5.243 | 196.000 | -0.077 | -6.432 | -5.573 | 632.000 | -0.033 | -3.667 | -4.150 | 293.000 | -0.002 | -0.152 | -0.145 | 312.000 | -0.004 | -0.330 | 0.357 |
| ON3 r_cc <= -1 sigma60, X1, SL 0.5 ATR | 336.000 | 2.471 | 46.726 | 1.054 | -0.007 | -0.526 | -0.551 | 43.000 | -0.071 | -2.716 | -1.898 | 197.000 | -0.011 | -0.545 | -0.600 | 96.000 | 0.028 | 1.142 | 1.226 | 102.000 | 0.027 | 1.174 | 0.595 |
| ON4 r_lh < 0 (last hour down), X1, SL 0.5 ATR | 1265.000 | 9.301 | 42.688 | 0.901 | -0.029 | -5.138 | -5.057 | 204.000 | -0.085 | -6.886 | -4.915 | 718.000 | -0.025 | -3.082 | -3.559 | 343.000 | -0.005 | -0.550 | -0.517 | 373.000 | -0.008 | -0.842 | 0.316 |
| ON5 r_cc < 0, X2, SL 1.0 ATR | 1121.000 | 8.243 | 52.275 | 0.880 | -0.005 | -0.455 | -0.506 | 196.000 | -0.011 | -0.446 | -0.550 | 632.000 | -0.015 | -1.118 | -1.145 | 293.000 | 0.021 | 1.011 | 1.300 | 312.000 | 0.027 | 1.342 | 2.319 |
| ON6 r_cc <= -1 sigma60, X2, SL 1.0 ATR | 336.000 | 2.471 | 53.274 | 0.847 | -0.005 | -0.243 | -0.263 | 43.000 | -0.028 | -0.545 | -0.679 | 197.000 | -0.031 | -1.102 | -1.182 | 96.000 | 0.058 | 1.386 | 1.504 | 102.000 | 0.062 | 1.550 | 3.274 |
| ON7 control: r_cc > 0, X1, SL 0.5 ATR | 1451.000 | 10.669 | 37.836 | 0.860 | -0.042 | -9.030 | -7.181 | 257.000 | -0.114 | -12.355 | -7.112 | 801.000 | -0.036 | -5.479 | -5.046 | 393.000 | -0.008 | -0.922 | -0.861 | 431.000 | -0.011 | -1.474 | 0.138 |


## S&P 500 (USA500IDXUSD), hourly bid bars

Months with a live entry bar: 169.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | month t | design n | design avg R | design t | design month t | check n | check avg R | check t | check month t | holdout n | holdout avg R | holdout t | holdout month t | last3y n | last3y avg R | last3y t | SL % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 every morning, X1, SL 0.5 ATR | 3359.000 | 19.876 | 34.504 | 0.869 | -0.057 | -15.916 | -13.404 | 1164.000 | -0.088 | -13.789 | -10.590 | 1506.000 | -0.049 | -9.011 | -9.210 | 689.000 | -0.024 | -3.469 | -3.457 | 747.000 | -0.027 | -4.094 | 0.417 |
| ON2 r_cc < 0, X1, SL 0.5 ATR | 1501.000 | 8.882 | 38.574 | 0.854 | -0.051 | -8.797 | -8.810 | 522.000 | -0.072 | -8.167 | -7.003 | 681.000 | -0.048 | -5.104 | -5.710 | 298.000 | -0.020 | -1.672 | -1.838 | 317.000 | -0.020 | -1.741 | 0.733 |
| ON3 r_cc <= -1 sigma60, X1, SL 0.5 ATR | 412.000 | 2.438 | 42.718 | 0.919 | -0.038 | -2.835 | -3.109 | 129.000 | -0.052 | -2.554 | -2.522 | 199.000 | -0.036 | -1.689 | -1.860 | 84.000 | -0.021 | -0.737 | -0.925 | 90.000 | -0.021 | -0.791 | 1.456 |
| ON4 r_lh < 0 (last hour down), X1, SL 0.5 ATR | 1618.000 | 9.574 | 37.268 | 0.903 | -0.048 | -9.136 | -8.778 | 522.000 | -0.075 | -8.555 | -6.536 | 752.000 | -0.039 | -4.737 | -5.739 | 344.000 | -0.026 | -2.558 | -2.416 | 373.000 | -0.029 | -3.023 | 0.556 |
| ON5 r_cc < 0, X2, SL 1.0 ATR | 1501.000 | 8.882 | 50.167 | 0.914 | -0.011 | -1.202 | -1.358 | 522.000 | -0.025 | -1.728 | -2.026 | 681.000 | -0.017 | -1.248 | -1.347 | 298.000 | 0.027 | 1.286 | 1.622 | 317.000 | 0.035 | 1.712 | 2.265 |
| ON6 r_cc <= -1 sigma60, X2, SL 1.0 ATR | 412.000 | 2.438 | 52.913 | 0.939 | 0.008 | 0.419 | 0.462 | 129.000 | 0.016 | 0.503 | 0.708 | 199.000 | -0.017 | -0.578 | -0.651 | 84.000 | 0.057 | 1.186 | 1.071 | 90.000 | 0.056 | 1.234 | 3.398 |
| ON7 control: r_cc > 0, X1, SL 0.5 ATR | 1814.000 | 10.734 | 31.257 | 0.869 | -0.062 | -13.454 | -11.581 | 617.000 | -0.099 | -10.799 | -8.431 | 813.000 | -0.050 | -7.918 | -8.428 | 384.000 | -0.027 | -3.329 | -3.486 | 422.000 | -0.032 | -4.226 | 0.110 |


## Size: gross drift vs costs (bp per trade)

Nasdaq gross = mid-to-mid (fills less half the fill-minute spread); S&P gross = bid-to-bid. Cost = gross - net.

| variant | Nasdaq gross bp | Nasdaq cost bp | Nasdaq net bp | Nasdaq avg stop bp | S&P gross bp | S&P cost bp | S&P net bp |
|---|---|---|---|---|---|---|---|
| ON1 | 0.88 | 3.28 | -2.40 | 89.97 | 0.67 | 3.35 | -2.68 |
| ON2 | 1.18 | 3.26 | -2.08 | 92.54 | 0.98 | 3.36 | -2.39 |
| ON3 | 3.14 | 2.98 | 0.16 | 102.32 | 1.50 | 3.30 | -1.80 |
| ON4 | 1.46 | 3.22 | -1.77 | 90.46 | 1.04 | 3.29 | -2.25 |
| ON5 | 3.19 | 3.25 | -0.06 | 185.08 | 3.29 | 3.35 | -0.06 |
| ON6 | 3.54 | 2.99 | 0.55 | 204.64 | 6.08 | 3.28 | 2.79 |
| ON7 | 0.66 | 3.28 | -2.62 | 88.41 | 0.44 | 3.32 | -2.88 |


### Nasdaq spread, entry minute vs 10:00 NY

| period | mornings | median spread bp at entry (07:55 Berlin) | mean spread bp at entry | median spread bp at 10:00 NY |
|---|---|---|---|---|
| all | 2604.00 | 2.58 | 3.03 | 1.03 |
| design | 466.00 | 5.90 | 5.56 | 5.69 |
| check | 1445.00 | 2.82 | 3.07 | 1.08 |
| holdout | 693.00 | 1.56 | 1.23 | 0.67 |
| last3y | 751.00 | 1.60 | 1.30 | 0.68 |


## Conditional channel: ON2 (after a down session) minus ON7 (after an up session)

Theory: ON2 > ON7, ON7 about 0. Welch t on per-trade values.

| market | period | ON2 n | ON2 avg R | ON7 n | ON7 avg R | ON2 - ON7 R | Welch t (R) | ON2 gross bp | ON7 gross bp | Welch t (gross bp) |
|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | all | 1121 | -0.033 | 1451 | -0.042 | 0.010 | 1.211 | 1.178 | 0.664 | 0.643 |
| Nasdaq 100 | design | 196 | -0.077 | 257 | -0.114 | 0.037 | 2.413 | 2.090 | -0.109 | 2.386 |
| Nasdaq 100 | check | 632 | -0.033 | 801 | -0.036 | 0.003 | 0.269 | 0.799 | 0.651 | 0.118 |
| Nasdaq 100 | holdout | 293 | -0.002 | 393 | -0.008 | 0.006 | 0.410 | 1.385 | 1.194 | 0.142 |
| Nasdaq 100 | last3y | 312 | -0.004 | 431 | -0.011 | 0.008 | 0.566 | 1.268 | 0.977 | 0.229 |
| S&P 500 | all | 1501 | -0.051 | 1814 | -0.062 | 0.011 | 1.497 | 0.976 | 0.440 | 1.001 |
| S&P 500 | design | 522 | -0.072 | 617 | -0.099 | 0.027 | 2.083 | 2.382 | 0.860 | 2.308 |
| S&P 500 | check | 681 | -0.048 | 813 | -0.050 | 0.002 | 0.215 | 0.101 | 0.101 | 0.000 |
| S&P 500 | holdout | 298 | -0.020 | 384 | -0.027 | 0.007 | 0.487 | 0.512 | 0.485 | 0.027 |
| S&P 500 | last3y | 317 | -0.020 | 422 | -0.032 | 0.012 | 0.909 | 0.585 | 0.200 | 0.405 |


## ON1 by tercile of r_cc(S) (cut points fixed on design data)

| market | tercile | cuts (design, %) | n | avg R | t | gross bp | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y avg R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | T1 (down) | -0.13 / 0.41 | 962 | -0.029 | -4.177 | 1.286 | 151 | -0.074 | -5.434 | 553 | -0.033 | -3.346 | 258 | 0.005 | 0.394 | 0.002 |
| Nasdaq 100 | T2 (mid) | -0.13 / 0.41 | 616 | -0.058 | -7.984 | -0.061 | 151 | -0.113 | -8.773 | 303 | -0.052 | -5.032 | 162 | -0.018 | -1.195 | -0.019 |
| Nasdaq 100 | T3 (up) | -0.13 / 0.41 | 994 | -0.034 | -6.147 | 1.090 | 151 | -0.108 | -9.049 | 577 | -0.027 | -3.489 | 266 | -0.008 | -0.813 | -0.011 |
| S&P 500 | T1 (down) | -0.15 / 0.28 | 1184 | -0.048 | -7.139 | 0.936 | 380 | -0.065 | -6.266 | 562 | -0.046 | -4.200 | 242 | -0.028 | -2.031 | -0.026 |
| S&P 500 | T2 (mid) | -0.15 / 0.28 | 887 | -0.076 | -12.707 | 0.237 | 380 | -0.110 | -11.619 | 336 | -0.070 | -7.460 | 171 | -0.012 | -0.999 | -0.017 |
| S&P 500 | T3 (up) | -0.15 / 0.28 | 1245 | -0.052 | -8.890 | 0.752 | 380 | -0.086 | -6.554 | 596 | -0.040 | -5.448 | 269 | -0.028 | -2.792 | -0.034 |


## Avg R by year

### Nasdaq

| variant | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 | -0.116 | -0.104 | -0.083 | -0.067 | 0.007 | -0.054 | -0.059 | -0.009 | -0.030 | -0.022 | -0.041 | -0.020 | -0.015 | 0.029 |
| ON2 | -0.082 | -0.071 | -0.083 | -0.081 | -0.100 | -0.035 | -0.087 | -0.018 | -0.013 | -0.025 | -0.025 | -0.008 | -0.025 | 0.033 |
| ON3 | -0.018 | -0.063 | -0.117 | -0.078 | -0.047 | 0.051 | -0.023 | -0.040 | 0.004 | -0.031 | -0.017 | 0.037 | -0.016 | 0.072 |
| ON4 | -0.077 | -0.096 | -0.058 | -0.190 | -0.016 | -0.053 | -0.039 | 0.003 | -0.018 | -0.014 | -0.035 | -0.019 | -0.018 | 0.032 |
| ON5 | 0.022 | -0.033 | -0.023 | -0.033 | 0.132 | -0.019 | -0.046 | -0.048 | -0.013 | -0.002 | 0.028 | 0.030 | -0.014 | 0.053 |
| ON6 | -0.084 | -0.073 | 0.038 | 0.107 | 0.204 | -0.001 | -0.027 | -0.137 | -0.038 | -0.019 | 0.043 | 0.043 | -0.049 | 0.209 |
| ON7 | -0.136 | -0.124 | -0.086 | -0.048 | 0.131 | -0.074 | -0.039 | -0.005 | -0.040 | -0.018 | -0.052 | -0.031 | -0.008 | 0.025 |


Trades:

| variant | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 | 129 | 237 | 73 | 14 | 13 | 191 | 252 | 249 | 252 | 251 | 250 | 251 | 250 | 192 |
| ON2 | 52 | 96 | 33 | 8 | 7 | 89 | 99 | 92 | 108 | 139 | 105 | 103 | 103 | 87 |
| ON3 | 4 | 25 | 9 | 4 | 1 | 32 | 22 | 34 | 31 | 49 | 29 | 33 | 35 | 28 |
| ON4 | 68 | 91 | 33 | 7 | 5 | 103 | 112 | 125 | 135 | 121 | 122 | 126 | 128 | 89 |
| ON5 | 52 | 96 | 33 | 8 | 7 | 89 | 99 | 92 | 108 | 139 | 105 | 103 | 103 | 87 |
| ON6 | 4 | 25 | 9 | 4 | 1 | 32 | 22 | 34 | 31 | 49 | 29 | 33 | 35 | 28 |
| ON7 | 71 | 137 | 37 | 6 | 6 | 99 | 150 | 155 | 143 | 111 | 143 | 145 | 143 | 105 |


### S&P

| variant | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 | -0.148 | -0.091 | -0.107 | -0.046 | -0.063 | -0.125 | -0.056 | -0.075 | -0.024 | -0.050 | -0.031 | -0.060 | -0.040 | -0.033 | 0.010 |
| ON2 | -0.145 | -0.045 | -0.070 | -0.046 | -0.064 | -0.113 | -0.070 | -0.103 | -0.021 | -0.042 | -0.030 | -0.027 | -0.036 | -0.039 | 0.020 |
| ON3 | -0.125 | -0.026 | -0.018 | -0.059 | -0.035 | -0.120 | 0.065 | -0.096 | -0.070 | -0.065 | -0.022 | -0.078 | -0.032 | -0.054 | 0.046 |
| ON4 | -0.142 | -0.059 | -0.090 | -0.031 | -0.076 | -0.106 | -0.045 | -0.049 | -0.013 | -0.049 | -0.014 | -0.057 | -0.046 | -0.035 | 0.009 |
| ON5 | -0.073 | -0.002 | -0.035 | -0.048 | -0.033 | 0.019 | -0.024 | -0.030 | -0.023 | -0.031 | -0.002 | 0.003 | 0.018 | 0.003 | 0.065 |
| ON6 | -0.062 | -0.079 | 0.016 | 0.027 | 0.008 | 0.050 | 0.032 | -0.016 | -0.095 | -0.009 | 0.004 | -0.042 | 0.037 | -0.050 | 0.246 |
| ON7 | -0.152 | -0.125 | -0.130 | -0.047 | -0.049 | -0.137 | -0.046 | -0.054 | -0.028 | -0.053 | -0.031 | -0.083 | -0.043 | -0.028 | -0.000 |


Trades:

| variant | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON1 | 47 | 135 | 235 | 250 | 248 | 249 | 251 | 252 | 250 | 252 | 251 | 250 | 252 | 250 | 187 |
| ON2 | 23 | 59 | 94 | 125 | 113 | 108 | 119 | 100 | 107 | 107 | 140 | 108 | 103 | 104 | 91 |
| ON3 | 3 | 6 | 31 | 40 | 31 | 18 | 40 | 22 | 30 | 32 | 43 | 32 | 28 | 34 | 22 |
| ON4 | 20 | 68 | 92 | 118 | 114 | 110 | 136 | 120 | 118 | 136 | 117 | 125 | 117 | 128 | 99 |
| ON5 | 23 | 59 | 94 | 125 | 113 | 108 | 119 | 100 | 107 | 107 | 140 | 108 | 103 | 104 | 91 |
| ON6 | 3 | 6 | 31 | 40 | 31 | 18 | 40 | 22 | 30 | 32 | 43 | 32 | 28 | 34 | 22 |
| ON7 | 24 | 71 | 137 | 120 | 128 | 137 | 129 | 149 | 141 | 144 | 110 | 140 | 146 | 142 | 96 |


## Monday / after-holiday / other mornings

| market | variant | Monday n | Monday avg R | Monday t | other Tue-Fri n | other Tue-Fri avg R | other Tue-Fri t | after holiday n | after holiday avg R | after holiday t |
|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | ON1 | 491 | -0.030 | -3.357 | 2036 | -0.040 | -9.365 | 77 | -0.049 | -2.376 |
| Nasdaq 100 | ON2 | 215 | -0.020 | -1.393 | 884 | -0.036 | -5.015 | 22 | -0.027 | -0.606 |
| Nasdaq 100 | ON3 | 76 | -0.002 | -0.055 | 257 | -0.012 | -0.753 | 3 | 0.240 | 2.181 |
| Nasdaq 100 | ON4 | 226 | -0.030 | -2.416 | 1012 | -0.029 | -4.510 | 27 | -0.022 | -0.616 |
| Nasdaq 100 | ON5 | 215 | 0.021 | 0.856 | 884 | -0.007 | -0.612 | 22 | -0.167 | -1.885 |
| Nasdaq 100 | ON6 | 76 | 0.043 | 0.828 | 257 | -0.014 | -0.613 | 3 | -0.447 | -1.614 |
| Nasdaq 100 | ON7 | 261 | -0.037 | -3.282 | 1147 | -0.043 | -8.215 | 43 | -0.053 | -1.956 |
| S&P 500 | ON1 | 629 | -0.051 | -6.012 | 2632 | -0.059 | -14.405 | 98 | -0.070 | -3.340 |
| S&P 500 | ON2 | 274 | -0.023 | -1.538 | 1194 | -0.058 | -9.226 | 33 | -0.027 | -0.637 |
| S&P 500 | ON3 | 92 | -0.011 | -0.397 | 315 | -0.051 | -3.364 | 5 | 0.286 | 2.676 |
| S&P 500 | ON4 | 283 | -0.043 | -3.436 | 1301 | -0.049 | -8.486 | 34 | -0.016 | -0.526 |
| S&P 500 | ON5 | 274 | 0.012 | 0.483 | 1194 | -0.013 | -1.383 | 33 | -0.103 | -1.428 |
| S&P 500 | ON6 | 92 | 0.021 | 0.386 | 315 | 0.006 | 0.293 | 5 | -0.072 | -0.290 |
| S&P 500 | ON7 | 334 | -0.072 | -7.581 | 1429 | -0.058 | -11.011 | 51 | -0.092 | -3.349 |


## Overlap with index_meanrev MR1 (MR1 signal day = our S, so MR1 is holding during our trade)

| market | variant | trades | MR1 trades | % of trades with S = MR1 day | % of MR1 days followed by a trade | avg R on MR1 days | avg R other days |
|---|---|---|---|---|---|---|---|
| Nasdaq 100 | ON1 | 2604 | 399 | 11.44 | 74.69 | -0.02 | -0.04 |
| Nasdaq 100 | ON2 | 1121 | 399 | 26.58 | 74.69 | -0.02 | -0.04 |
| Nasdaq 100 | ON3 | 336 | 399 | 80.65 | 67.92 | -0.01 | 0.01 |
| Nasdaq 100 | ON4 | 1265 | 399 | 15.81 | 50.13 | -0.00 | -0.03 |
| Nasdaq 100 | ON5 | 1121 | 399 | 26.58 | 74.69 | 0.00 | -0.01 |
| Nasdaq 100 | ON6 | 336 | 399 | 80.65 | 67.92 | 0.00 | -0.03 |
| Nasdaq 100 | ON7 | 1451 | 399 | 0.00 | 0.00 |  | -0.04 |
| S&P 500 | ON1 | 3359 | 375 | 10.45 | 93.60 | -0.04 | -0.06 |
| S&P 500 | ON2 | 1501 | 375 | 23.38 | 93.60 | -0.04 | -0.05 |
| S&P 500 | ON3 | 412 | 375 | 85.19 | 93.60 | -0.04 | -0.03 |
| S&P 500 | ON4 | 1618 | 375 | 14.22 | 61.33 | -0.02 | -0.05 |
| S&P 500 | ON5 | 1501 | 375 | 23.38 | 93.60 | 0.00 | -0.02 |
| S&P 500 | ON6 | 412 | 375 | 85.19 | 93.60 | 0.00 | 0.03 |
| S&P 500 | ON7 | 1814 | 375 | 0.00 | 0.00 |  | -0.06 |


## Correlation of daily R with the existing basket legs (run_m3_addon.build_legs)

Daily R by 17:00-NY day of exit, zero on days without a trade, business days of the overlapping span.

| market | variant | days | corr vol-box | corr vol-gotobi | corr fade | corr M-3 USDJPY | corr M-3 others | corr basket (risk-weighted %) | days with a basket trade too % |
|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | ON1 | 3490 | -0.002 | 0.028 | -0.005 | -0.036 | 0.008 | 0.012 | 57.258 |
| Nasdaq 100 | ON2 | 3490 | 0.003 | 0.038 | -0.010 | 0.010 | 0.011 | 0.027 | 57.270 |
| Nasdaq 100 | ON3 | 3490 | 0.017 | 0.045 | -0.020 | -0.007 | 0.024 | 0.029 | 54.167 |
| Nasdaq 100 | ON4 | 3490 | 0.013 | 0.008 | -0.011 | -0.025 | 0.007 | 0.001 | 57.470 |
| Nasdaq 100 | ON5 | 3490 | -0.017 | 0.012 | -0.025 | 0.010 | 0.022 | -0.006 | 57.270 |
| Nasdaq 100 | ON6 | 3490 | -0.010 | -0.010 | -0.020 | -0.010 | 0.005 | -0.022 | 54.167 |
| Nasdaq 100 | ON7 | 3490 | -0.009 | 0.000 | 0.009 | -0.063 | -0.000 | -0.009 | 57.271 |
| S&P 500 | ON1 | 3819 | -0.019 | 0.039 | -0.004 | -0.026 | -0.001 | 0.017 | 57.719 |
| S&P 500 | ON2 | 3819 | -0.006 | 0.003 | -0.013 | -0.003 | 0.010 | -0.006 | 58.611 |
| S&P 500 | ON3 | 3819 | 0.007 | 0.013 | -0.021 | 0.021 | -0.011 | 0.006 | 55.961 |
| S&P 500 | ON4 | 3819 | -0.005 | -0.007 | 0.000 | -0.009 | 0.010 | -0.009 | 58.721 |
| S&P 500 | ON5 | 3819 | -0.020 | 0.004 | -0.002 | -0.009 | 0.011 | -0.006 | 58.572 |
| S&P 500 | ON6 | 3819 | -0.011 | -0.037 | -0.000 | 0.007 | -0.018 | -0.031 | 55.825 |
| S&P 500 | ON7 | 3819 | -0.018 | 0.053 | 0.014 | -0.032 | -0.007 | 0.035 | 57.056 |


## Data coverage by year

| year | Nasdaq mornings | Nasdaq live entry % | Nasdaq S in close series % | S&P mornings | S&P live entry % | S&P S in close series % |
|---|---|---|---|---|---|---|
| 2011 | 72.0 | 0.0 | 4.2 |  |  |  |
| 2012 | 250.0 | 0.0 | 93.2 | 249.0 | 26.5 | 91.2 |
| 2013 | 252.0 | 51.2 | 69.8 | 252.0 | 53.6 | 68.7 |
| 2014 | 252.0 | 94.0 | 98.0 | 252.0 | 93.3 | 98.0 |
| 2015 | 252.0 | 29.0 | 97.2 | 252.0 | 99.2 | 98.0 |
| 2016 | 252.0 | 5.6 | 99.2 | 252.0 | 98.4 | 97.6 |
| 2017 | 251.0 | 5.2 | 99.2 | 251.0 | 99.2 | 98.4 |
| 2018 | 251.0 | 76.1 | 98.4 | 251.0 | 100.0 | 98.8 |
| 2019 | 252.0 | 100.0 | 98.8 | 252.0 | 100.0 | 98.8 |
| 2020 | 253.0 | 98.4 | 99.2 | 253.0 | 98.8 | 99.2 |
| 2021 | 252.0 | 100.0 | 99.6 | 252.0 | 100.0 | 99.6 |
| 2022 | 251.0 | 100.0 | 99.6 | 251.0 | 100.0 | 99.6 |
| 2023 | 250.0 | 100.0 | 99.2 | 250.0 | 100.0 | 99.2 |
| 2024 | 252.0 | 99.6 | 98.8 | 252.0 | 100.0 | 98.8 |
| 2025 | 251.0 | 99.6 | 98.4 | 251.0 | 99.6 | 98.4 |
| 2026 | 192.0 | 100.0 | 100.0 | 192.0 | 97.4 | 97.9 |


## Contamination note

ON1 overlaps the flow-atlas watch-list cell (Nasdaq, London 00:30-08:30, all weekdays), so it is not independent evidence. Only ON2-ON6 and the ON2 - ON7 gap are new.

## Prop sim

Not run: no Nasdaq variant survived the charter bar.
