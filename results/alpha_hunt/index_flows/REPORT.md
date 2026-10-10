# Alpha hunt: index calendar flows - option expiry and month-end pension rebalancing (`index_flows`)

Rules, variants and the survival bar are in the docstring of `run_alpha_index_flows.py` (fixed before running). Swing trades of 3-7 trading days on the close, long and short, stops 1-2 x ATR20 (Nasdaq checked minute by minute on bid/ask; S&P on hourly bars), all costs included. Periods: design 2011-17 (data start), check 2018-23, holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.

**Candidate tests: 8 (O1-O4, P1-P4 on the Nasdaq; S&P = replication, C1-C4 = controls). Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): 0 (none). Expected by luck: 0.05.**

## Verdict

No candidate passes the charter bar, so no prop sim was run. Option-expiry and pension-rebalancing flows give no tradeable edge on these index CFDs after costs. The only near miss is P4 (turn-of-month long when stocks beat bonds month to date), and it is too weak to use.

- **O1 opex-week long**: Nasdaq +0.086R (design t 1.75), S&P +0.037R. It is no better than holding any other week: O1 minus C1 is +0.05R (t 0.7 on the Nasdaq, 0.9 on the S&P). It was positive in 2011-21 (Nasdaq +0.130R, t 1.85) and is flat since 2022 (Nasdaq 0.000, S&P -0.041). That fits the 0DTE-dilution story, but the earlier period was not significant either.
- **O2 post-opex short**: the predicted direction was wrong. The week after expiry was not weak: Nasdaq -0.187R (t -3.3), S&P -0.138R (t -2.2). The post-hoc mirror long (H1, data-snooped, below) makes only +0.108R on the Nasdaq (design t 1.36) and -0.013R on the S&P. So most of O2's loss is the equity drift plus short stops getting hit in rallies, not a long edge to flip into.
- **O3 / O4 (quarterly months)**: positive but noisy (O3 Nasdaq +0.167R, t 1.5, n 57). O4 is about zero.
- **P1-P3 rebalancing against the stock-bond gap G**: about zero on the Nasdaq (P1 +0.005R) and small on the S&P (P1 +0.085R, t 1.4). Quarter-end months (P3) are negative in both markets. The G-tercile table points the way the theory says: the unconditional long from day s to month-end (C2) falls as G rises (Nasdaq +0.195 / +0.128 / -0.086R; S&P +0.212 / +0.001 / -0.188R). But with a positive equity drift, the theta = 0 short loses in the middle tercile (small positive G). Even in the top tercile, the short is only about 0 to +0.12R.
- **P4 TOM long when G > 0**: the best result. Nasdaq +0.257R (t 2.12 over all years) and positive in every period: design +0.280R, check +0.273R, holdout +0.176R. It fails the bar on design t = 1.49 (39 trades). The S&P replicates only weakly (+0.091R) and its holdout is negative (-0.079R). The G > 0 vs G < 0 split (P4 vs C3) is +0.36R on the Nasdaq (t 1.8) and +0.17R on the S&P (t 0.9). The post-hoc half-day G fill lowers the design t to 1.20. 38% of trades are stopped out (1 x ATR20 stop over 3 days).
- **Controls**: C4 recomputes the earlier E1b exactly (163 trades, +0.128R, design +0.097R), which cross-checks the mechanics.
- **Risk**: one variant at 0.5% risk loses at most -0.5% to -0.85% in a day (MTM). The turn-of-month legs (P4 / C4) reach -1.30% (Nasdaq) and -1.65% (S&P) on 2020-09-03, when open profit was given back. All 8 candidates stacked at 0.5% each reach -2.24%.
- **Data notes**: the Nasdaq has no usable closes from 2011-09-22 to the end of 2011, and gaps in Feb-May 2013. G is missing in 20 of 182 months: the 2011 start, the 2013 gap, the future month 2026-10, and 10 months where pme or s is a half day or a missing year-end close. The 15:00 vs 16:00 S&P level on day s (the look-ahead fix for the Nasdaq) flips the sign of G in 4 of 162 months.

## Judging (candidates)

Nasdaq gets the charter bar; the S&P replicates if its avg R > 0 over the whole period.

| candidate | trades | design avg R | design t | check avg R | holdout avg R | last3y avg R | Nasdaq charter bar | S&P avg R | S&P t | S&P replicates |
|---|---|---|---|---|---|---|---|---|---|---|
| O1 | 170 | 0.173 | 1.753 | 0.044 | 0.007 | 0.036 | False | 0.037 | 0.661 | True |
| O2 | 169 | -0.299 | -3.651 | -0.085 | -0.195 | -0.178 | False | -0.138 | -2.214 | False |
| O3 | 57 | 0.218 | 1.201 | 0.184 | 0.029 | 0.140 | False | 0.132 | 1.264 | True |
| O4 | 56 | 0.012 | 0.079 | -0.043 | -0.165 | -0.180 | False | -0.018 | -0.181 | False |
| P1 | 160 | 0.066 | 0.630 | -0.024 | -0.043 | -0.051 | False | 0.085 | 1.422 | True |
| P2 | 101 | 0.114 | 0.683 | -0.056 | -0.056 | -0.048 | False | 0.083 | 1.021 | True |
| P3 | 52 | -0.023 | -0.100 | -0.134 | -0.303 | -0.253 | False | -0.055 | -0.499 | False |
| P4 | 102 | 0.280 | 1.491 | 0.273 | 0.176 | 0.171 | False | 0.091 | 0.767 | True |


## Nasdaq 100 (USATECHIDXUSD)

Months with data: 177. trades/month = trades / months with data. dir hit % = share of trades whose planned close-to-close window moved in the trade's direction (ignores the stop).

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | dir hit % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 opex-week long: Fri before -> X | 170 | 0.960 | 52.941 | 1.175 | 0.086 | 1.486 | 65 | 0.173 | 1.753 | 72 | 0.044 | 0.518 | 33 | 0.007 | 0.055 | 36 | 0.036 | 0.280 | 15.882 | 55.294 | False |
| O2 post-opex short: X -> end of next week | 169 | 0.955 | 34.320 | 1.017 | -0.187 | -3.318 | 64 | -0.299 | -3.651 | 72 | -0.085 | -0.855 | 33 | -0.195 | -1.842 | 36 | -0.178 | -1.767 | 20.710 | 36.686 | False |
| O3 O1 quarterly months | 57 | 0.322 | 57.895 | 1.204 | 0.167 | 1.541 | 22 | 0.218 | 1.201 | 24 | 0.184 | 0.989 | 11 | 0.029 | 0.176 | 12 | 0.140 | 0.749 | 19.298 | 59.649 | False |
| O4 O2 quarterly months | 56 | 0.316 | 41.071 | 1.229 | -0.046 | -0.475 | 21 | 0.012 | 0.079 | 24 | -0.043 | -0.268 | 11 | -0.165 | -0.797 | 12 | -0.180 | -0.951 | 12.500 | 44.643 | False |
| P1 rebalance: s -> ME, against sign(G) | 160 | 0.904 | 49.375 | 1.044 | 0.005 | 0.089 | 59 | 0.066 | 0.630 | 70 | -0.024 | -0.263 | 31 | -0.043 | -0.381 | 34 | -0.051 | -0.485 | 16.250 | 50.000 | False |
| P2 P1 with abs(G) > 2% | 101 | 0.571 | 48.515 | 1.060 | -0.000 | -0.005 | 33 | 0.114 | 0.683 | 48 | -0.056 | -0.506 | 20 | -0.056 | -0.343 | 21 | -0.048 | -0.310 | 21.782 | 50.495 | False |
| P3 P1 quarter-end months | 52 | 0.294 | 46.154 | 0.775 | -0.121 | -1.093 | 20 | -0.023 | -0.100 | 23 | -0.134 | -1.066 | 9 | -0.303 | -1.331 | 10 | -0.253 | -1.209 | 19.231 | 46.154 | False |
| P4 TOM long ME -> TD3 when G > 0 | 102 | 0.576 | 55.882 | 1.283 | 0.257 | 2.121 | 39 | 0.280 | 1.491 | 44 | 0.273 | 1.468 | 19 | 0.176 | 0.557 | 22 | 0.171 | 0.567 | 38.235 | 59.804 | False |
| C1 control: long non-expiry weeks | 547 | 3.090 | 55.027 | 0.928 | 0.041 | 1.252 | 207 | -0.019 | -0.337 | 233 | 0.067 | 1.407 | 107 | 0.099 | 1.321 | 115 | 0.105 | 1.453 | 20.658 | 55.759 | False |
| C2 control: long s -> ME unconditional | 169 | 0.955 | 56.805 | 0.925 | 0.059 | 0.983 | 65 | 0.142 | 1.354 | 71 | 0.067 | 0.735 | 33 | -0.123 | -1.131 | 36 | -0.106 | -1.032 | 18.343 | 55.030 | False |
| C3 control: TOM long when G < 0 | 51 | 0.288 | 35.294 | 1.476 | -0.106 | -0.666 | 16 | -0.116 | -0.439 | 25 | 0.046 | 0.181 | 10 | -0.468 | -1.654 | 10 | -0.468 | -1.654 | 43.137 | 47.059 | False |
| C4 control: E1b TOM long unconditional | 163 | 0.921 | 49.080 | 1.329 | 0.128 | 1.372 | 61 | 0.097 | 0.669 | 71 | 0.193 | 1.317 | 31 | 0.043 | 0.191 | 34 | 0.052 | 0.233 | 39.877 | 55.215 | False |


## S&P 500 (USA500IDXUSD, hourly) - replication

Months with data: 175.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | dir hit % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 opex-week long: Fri before -> X | 169 | 0.966 | 53.254 | 0.992 | 0.037 | 0.661 | 64 | 0.174 | 1.864 | 72 | -0.058 | -0.683 | 33 | -0.018 | -0.143 | 36 | 0.020 | 0.155 | 18.935 | 56.805 | False |
| O2 post-opex short: X -> end of next week | 155 | 0.886 | 38.065 | 1.014 | -0.138 | -2.214 | 57 | -0.166 | -1.878 | 66 | -0.053 | -0.462 | 32 | -0.265 | -2.530 | 34 | -0.244 | -2.352 | 15.484 | 41.935 | False |
| O3 O1 quarterly months | 57 | 0.326 | 54.386 | 1.259 | 0.132 | 1.264 | 22 | 0.365 | 2.228 | 24 | 0.021 | 0.120 | 11 | -0.093 | -0.538 | 12 | 0.030 | 0.150 | 17.544 | 59.649 | False |
| O4 O2 quarterly months | 55 | 0.314 | 50.909 | 0.908 | -0.018 | -0.181 | 21 | 0.072 | 0.504 | 23 | 0.029 | 0.179 | 11 | -0.287 | -1.346 | 12 | -0.316 | -1.606 | 14.545 | 52.727 | False |
| P1 rebalance: s -> ME, against sign(G) | 155 | 0.886 | 54.194 | 1.154 | 0.085 | 1.422 | 57 | 0.115 | 1.135 | 69 | 0.082 | 0.866 | 29 | 0.032 | 0.289 | 32 | 0.038 | 0.372 | 12.903 | 58.710 | False |
| P2 P1 with abs(G) > 2% | 94 | 0.537 | 50.000 | 1.333 | 0.083 | 1.021 | 28 | 0.160 | 1.005 | 48 | 0.052 | 0.445 | 18 | 0.047 | 0.291 | 19 | 0.031 | 0.202 | 13.830 | 55.319 | False |
| P3 P1 quarter-end months | 51 | 0.291 | 50.980 | 0.787 | -0.055 | -0.499 | 19 | 0.070 | 0.291 | 23 | -0.123 | -1.076 | 9 | -0.150 | -0.602 | 10 | -0.135 | -0.603 | 21.569 | 52.941 | False |
| P4 TOM long ME -> TD3 when G > 0 | 95 | 0.543 | 51.579 | 1.132 | 0.091 | 0.767 | 36 | 0.201 | 1.017 | 42 | 0.065 | 0.384 | 17 | -0.079 | -0.258 | 19 | -0.125 | -0.449 | 38.947 | 62.105 | False |
| C1 control: long non-expiry weeks | 524 | 2.994 | 52.863 | 0.840 | -0.019 | -0.566 | 194 | -0.110 | -2.096 | 227 | 0.035 | 0.693 | 103 | 0.037 | 0.485 | 110 | 0.045 | 0.602 | 22.901 | 58.397 | False |
| C2 control: long s -> ME unconditional | 163 | 0.931 | 50.920 | 0.919 | -0.013 | -0.233 | 62 | 0.035 | 0.352 | 70 | 0.029 | 0.339 | 31 | -0.206 | -1.794 | 34 | -0.169 | -1.568 | 19.018 | 53.374 | False |
| C3 control: TOM long when G < 0 | 53 | 0.303 | 37.736 | 1.394 | -0.080 | -0.508 | 18 | -0.356 | -1.418 | 26 | 0.262 | 1.070 | 9 | -0.517 | -2.034 | 10 | -0.210 | -0.551 | 45.283 | 49.057 | False |
| C4 control: E1b TOM long unconditional | 158 | 0.903 | 46.835 | 1.192 | 0.024 | 0.258 | 60 | -0.011 | -0.073 | 70 | 0.107 | 0.776 | 28 | -0.111 | -0.505 | 31 | -0.051 | -0.234 | 41.772 | 57.595 | False |


## Option expiry: 2011-2021 vs 2022+ (0DTE era)

| market · variant | 2011-2021 n | 2011-2021 avg R | 2011-2021 t | 2011-2021 win % | 2022+ n | 2022+ avg R | 2022+ t | 2022+ win % |
|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 · O1 | 113 | 0.130 | 1.850 | 56.637 | 57 | -0.000 | -0.001 | 45.614 |
| Nasdaq 100 · O2 | 112 | -0.196 | -2.673 | 34.821 | 57 | -0.171 | -1.977 | 33.333 |
| Nasdaq 100 · O3 | 38 | 0.178 | 1.325 | 60.526 | 19 | 0.145 | 0.772 | 52.632 |
| Nasdaq 100 · O4 | 37 | -0.040 | -0.325 | 40.541 | 19 | -0.058 | -0.362 | 42.105 |
| Nasdaq 100 · C1 | 362 | 0.031 | 0.765 | 54.972 | 185 | 0.060 | 1.095 | 55.135 |
| S&P 500 · O1 | 112 | 0.077 | 1.110 | 57.143 | 57 | -0.041 | -0.420 | 45.614 |
| S&P 500 · O2 | 101 | -0.113 | -1.374 | 39.604 | 54 | -0.186 | -2.001 | 35.185 |
| S&P 500 · O3 | 38 | 0.191 | 1.474 | 55.263 | 19 | 0.013 | 0.075 | 52.632 |
| S&P 500 · O4 | 36 | 0.042 | 0.359 | 55.556 | 19 | -0.130 | -0.726 | 42.105 |
| S&P 500 · C1 | 345 | -0.032 | -0.784 | 52.754 | 179 | 0.006 | 0.112 | 53.073 |


## Pension rebalancing: the stock-bond gap G

G source by month: {'S&P': 162, 'none': 20} (S&P hourly closes; Nasdaq fallback). Nasdaq trades use the look-ahead-free G (S&P 15:00 price on day s); S&P trades use the 16:00 close. Months where the sign of G differs between the two: 4 of 162; where abs(G) > 2% differs: 7.

| market | months with G | G>0 months | abs(G)>2% months | G tercile cut 1 | G tercile cut 2 | G mean | G sd |
|---|---|---|---|---|---|---|---|
| Nasdaq 100 | 162 | 109 | 103 | 0.0008 | 0.0284 | 0.0126 | 0.0426 |
| S&P 500 | 162 | 107 | 100 | -0.0005 | 0.0288 | 0.0128 | 0.0421 |


### Avg R by G tercile (full-sample tercile cut-offs of each market's G; descriptive only)

P1-P3 trade against sign(G) (low tercile = BUY, high = SELL); P4 / C3 / C4 / C2 are longs. dir hit % = the planned window moved the predicted way.

| market · variant · tercile | G range | n | avg R | t | win % | dir hit % |
|---|---|---|---|---|---|---|
| Nasdaq 100 · C2 · T1 low | -14.4%..+0.0% | 54 | 0.195 | 1.729 | 64.815 | 64.815 |
| Nasdaq 100 · C2 · T2 mid | +0.1%..+2.8% | 54 | 0.128 | 1.124 | 62.963 | 62.963 |
| Nasdaq 100 · C2 · T3 high | +2.9%..+10.8% | 52 | -0.086 | -0.936 | 46.154 | 40.385 |
| Nasdaq 100 · C3 · T1 low | -14.4%..-0.1% | 51 | -0.106 | -0.666 | 35.294 | 47.059 |
| Nasdaq 100 · C4 · T1 low | -14.4%..+0.0% | 52 | -0.123 | -0.787 | 34.615 | 46.154 |
| Nasdaq 100 · C4 · T2 mid | +0.1%..+2.8% | 53 | 0.320 | 1.824 | 58.491 | 64.151 |
| Nasdaq 100 · C4 · T3 high | +3.0%..+10.8% | 48 | 0.214 | 1.267 | 54.167 | 56.250 |
| Nasdaq 100 · P1 · T1 low | -14.4%..+0.0% | 54 | 0.176 | 1.551 | 62.963 | 62.963 |
| Nasdaq 100 · P1 · T2 mid | +0.1%..+2.8% | 54 | -0.151 | -1.542 | 35.185 | 35.185 |
| Nasdaq 100 · P1 · T3 high | +2.9%..+10.8% | 52 | -0.010 | -0.104 | 50.000 | 51.923 |
| Nasdaq 100 · P2 · T1 low | -14.4%..-2.2% | 30 | 0.128 | 0.713 | 56.667 | 60.000 |
| Nasdaq 100 · P2 · T2 mid | +2.0%..+2.8% | 19 | -0.177 | -0.862 | 31.579 | 31.579 |
| Nasdaq 100 · P2 · T3 high | +2.9%..+10.8% | 52 | -0.010 | -0.104 | 50.000 | 51.923 |
| Nasdaq 100 · P3 · T1 low | -14.4%..+0.0% | 21 | 0.006 | 0.029 | 57.143 | 57.143 |
| Nasdaq 100 · P3 · T2 mid | +0.1%..+2.7% | 19 | -0.318 | -2.221 | 31.579 | 31.579 |
| Nasdaq 100 · P3 · T3 high | +2.9%..+9.8% | 12 | -0.030 | -0.162 | 50.000 | 50.000 |
| Nasdaq 100 · P4 · T1 low | +0.0%..+0.0% | 1 | -1.023 |  | 0.000 | 0.000 |
| Nasdaq 100 · P4 · T2 mid | +0.1%..+2.8% | 53 | 0.320 | 1.824 | 58.491 | 64.151 |
| Nasdaq 100 · P4 · T3 high | +3.0%..+10.8% | 48 | 0.214 | 1.267 | 54.167 | 56.250 |
| S&P 500 · C2 · T1 low | -13.4%..-0.1% | 52 | 0.212 | 1.864 | 67.308 | 69.231 |
| S&P 500 · C2 · T2 mid | -0.0%..+2.8% | 52 | 0.001 | 0.012 | 48.077 | 53.846 |
| S&P 500 · C2 · T3 high | +3.0%..+10.9% | 51 | -0.188 | -2.224 | 41.176 | 41.176 |
| S&P 500 · C3 · T1 low | -13.4%..-0.1% | 52 | -0.062 | -0.385 | 38.462 | 50.000 |
| S&P 500 · C3 · T2 mid | -0.0%..-0.0% | 1 | -1.051 |  | 0.000 | 0.000 |
| S&P 500 · C4 · T1 low | -13.4%..-0.1% | 52 | -0.062 | -0.385 | 38.462 | 50.000 |
| S&P 500 · C4 · T2 mid | -0.0%..+2.7% | 48 | 0.110 | 0.603 | 54.167 | 66.667 |
| S&P 500 · C4 · T3 high | +3.0%..+10.9% | 48 | 0.048 | 0.319 | 47.917 | 56.250 |
| S&P 500 · P1 · T1 low | -13.4%..-0.1% | 52 | 0.212 | 1.864 | 67.308 | 69.231 |
| S&P 500 · P1 · T2 mid | -0.0%..+2.8% | 52 | -0.080 | -0.849 | 42.308 | 48.077 |
| S&P 500 · P1 · T3 high | +3.0%..+10.9% | 51 | 0.123 | 1.238 | 52.941 | 58.824 |
| S&P 500 · P2 · T1 low | -13.4%..-2.1% | 29 | 0.177 | 0.986 | 55.172 | 58.621 |
| S&P 500 · P2 · T2 mid | +2.0%..+2.8% | 14 | -0.257 | -1.631 | 28.571 | 35.714 |
| S&P 500 · P2 · T3 high | +3.0%..+10.9% | 51 | 0.123 | 1.238 | 52.941 | 58.824 |
| S&P 500 · P3 · T1 low | -13.4%..-0.1% | 20 | 0.112 | 0.494 | 65.000 | 65.000 |
| S&P 500 · P3 · T2 mid | -0.0%..+2.8% | 19 | -0.270 | -2.037 | 31.579 | 36.842 |
| S&P 500 · P3 · T3 high | +3.3%..+10.2% | 12 | 0.006 | 0.030 | 58.333 | 58.333 |
| S&P 500 · P4 · T2 mid | +0.0%..+2.7% | 47 | 0.135 | 0.730 | 55.319 | 68.085 |
| S&P 500 · P4 · T3 high | +3.0%..+10.9% | 48 | 0.048 | 0.319 | 47.917 | 56.250 |


## Worst single day at 0.5% risk per trade

MTM = open trades marked at each close, booked by NY trading day (17:00 roll); realised = net R on the exit day.

| market · set | worst day % (MTM) | date | worst day % (realised) | date  | days < -0.5% (MTM) | worst trade R |
|---|---|---|---|---|---|---|
| Nasdaq 100 · O1 | -0.81 | 2017-05-17 | -0.52 | 2016-06-16 | 10 | -1.03 |
| Nasdaq 100 · O2 | -0.85 | 2017-10-27 | -0.58 | 2017-06-22 | 5 | -1.16 |
| Nasdaq 100 · O3 | -0.71 | 2024-12-18 | -0.52 | 2016-06-16 | 4 | -1.03 |
| Nasdaq 100 · O4 | -0.50 | 2026-09-21 | -0.58 | 2017-06-22 | 1 | -1.16 |
| Nasdaq 100 · P1 | -0.64 | 2012-06-29 | -0.54 | 2025-03-31 | 14 | -1.08 |
| Nasdaq 100 · P2 | -0.61 | 2020-02-27 | -0.54 | 2025-03-31 | 9 | -1.08 |
| Nasdaq 100 · P3 | -0.64 | 2012-06-29 | -0.54 | 2025-03-31 | 6 | -1.08 |
| Nasdaq 100 · P4 | -1.30 | 2020-09-03 | -0.58 | 2025-02-03 | 36 | -1.17 |
| Nasdaq 100 · C1 | -1.31 | 2016-06-24 | -0.74 | 2016-06-24 | 38 | -1.48 |
| Nasdaq 100 · C2 | -0.70 | 2014-07-31 | -0.66 | 2015-06-29 | 21 | -1.33 |
| Nasdaq 100 · C3 | -0.83 | 2025-04-03 | -0.58 | 2012-06-01 | 19 | -1.15 |
| Nasdaq 100 · C4 | -1.30 | 2020-09-03 | -0.58 | 2025-02-03 | 58 | -1.17 |
| S&P 500 · O1 | -0.73 | 2017-08-17 | -0.65 | 2020-03-16 | 10 | -1.31 |
| S&P 500 · O2 | -0.78 | 2015-08-26 | -0.57 | 2017-05-25 | 5 | -1.14 |
| S&P 500 · O3 | -0.66 | 2022-09-13 | -0.65 | 2020-03-16 | 3 | -1.31 |
| S&P 500 · O4 | -0.51 | 2026-09-21 | -0.52 | 2016-06-23 | 1 | -1.04 |
| S&P 500 · P1 | -0.69 | 2022-04-29 | -0.52 | 2017-09-29 | 10 | -1.05 |
| S&P 500 · P2 | -0.69 | 2022-04-29 | -0.52 | 2021-08-30 | 4 | -1.03 |
| S&P 500 · P3 | -0.53 | 2017-06-29 | -0.52 | 2017-09-29 | 4 | -1.05 |
| S&P 500 · P4 | -1.65 | 2020-09-03 | -0.58 | 2025-02-03 | 32 | -1.16 |
| S&P 500 · C1 | -1.51 | 2016-06-24 | -0.90 | 2016-06-24 | 40 | -1.81 |
| S&P 500 · C2 | -0.69 | 2022-04-29 | -0.53 | 2018-01-30 | 18 | -1.05 |
| S&P 500 · C3 | -0.86 | 2018-12-04 | -0.55 | 2017-07-06 | 19 | -1.09 |
| S&P 500 · C4 | -1.65 | 2020-09-03 | -0.58 | 2025-02-03 | 53 | -1.16 |
| Nasdaq 100 · all 8 candidates at 0.5% each | -2.24 | 2012-09-27 | -1.62 | 2025-03-31 | 137 | -1.17 |
| Nasdaq 100 · O1 + O2 + P1 + P4 at 0.5% each | -1.36 | 2017-10-27 | -1.04 | 2014-11-28 | 67 | -1.17 |


## Avg R per trade by year

### Nasdaq 100

| variant | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 | -0.13 | 0.29 | 0.05 | 0.36 | 0.25 | 0.17 | 0.01 | 0.30 | 0.16 | -0.18 | -0.35 | 0.33 | -0.19 | 0.22 | -0.02 |
| O2 | -0.20 | -0.28 | -0.29 | -0.19 | -0.30 | -0.50 | 0.05 | -0.17 | 0.13 | -0.25 | -0.06 | -0.22 | -0.34 | -0.18 | -0.02 |
| O3 | 0.26 | 0.31 | -0.35 | 0.59 | 0.32 | 0.21 | -0.21 | 0.88 | 0.13 | -0.31 | -0.39 | 1.00 | -0.24 | 0.25 | 0.10 |
| O4 | 0.54 | -0.58 | 0.15 | 0.34 | -0.45 | -0.08 | 0.26 | -0.16 | -0.14 | -0.40 | 0.00 | 0.18 | -0.41 | -0.21 | 0.22 |
| P1 | 0.06 | -0.36 | -0.07 | 0.13 | 0.43 | 0.04 | -0.14 | 0.02 | -0.25 | -0.04 | 0.13 | 0.15 | 0.29 | -0.33 | -0.10 |
| P2 | 0.14 | -0.37 | -0.34 | 0.23 | 0.63 | 0.13 | -0.28 | 0.01 | -0.42 | 0.20 | 0.29 | -0.09 | 0.38 | -0.49 | 0.01 |
| P3 | -0.45 | -0.51 | -0.48 | 0.20 | 0.93 | -0.29 | -0.30 | 0.06 | -0.00 | -0.52 | -0.34 | 0.35 | 0.01 | -0.95 | 0.03 |
| P4 | 0.63 | 0.94 | -0.06 | 0.06 | 0.08 | 0.46 | 0.36 | 0.23 | 0.49 | 0.25 | -0.30 | 0.32 | 0.92 | -0.74 | 0.49 |
| C1 | -0.06 | -0.04 | -0.05 | -0.20 | 0.00 | 0.22 | 0.06 | 0.11 | 0.12 | 0.10 | -0.17 | 0.18 | 0.21 | -0.04 | 0.14 |
| C2 | 0.21 | 0.16 | 0.14 | -0.17 | 0.26 | 0.28 | -0.14 | -0.14 | -0.03 | -0.13 | 0.23 | 0.63 | -0.20 | -0.13 | -0.01 |
| C3 | -0.60 | 1.82 | -0.27 | -0.11 | 0.50 | -1.03 | -0.54 | 0.53 | 1.38 | -0.86 | 0.27 | -0.86 | -0.47 | -0.53 | -0.41 |
| C4 | -0.05 | 0.40 | -0.13 | 0.08 | -0.00 | 0.34 | -0.01 | 0.41 | 0.79 | 0.07 | -0.01 | -0.07 | 0.47 | -0.51 | 0.19 |


### S&P 500

| variant | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| O1 | 0.10 | 0.48 | 0.14 | 0.19 | 0.10 | 0.13 | 0.02 | 0.20 | -0.04 | -0.39 | -0.34 | 0.20 | -0.16 | 0.22 | -0.15 |
| O2 | 0.02 | -0.27 | 0.00 | -0.01 | -0.29 | -0.47 | 0.11 | -0.11 | 0.40 | -0.53 | -0.10 | -0.04 | -0.44 | -0.30 | 0.01 |
| O3 | 0.52 | 0.44 | 0.37 | 0.43 | -0.08 | 0.42 | -0.23 | 0.79 | -0.13 | -0.62 | -0.40 | 0.72 | -0.09 | 0.17 | -0.45 |
| O4 | 0.55 | -0.56 | 0.17 | 0.51 | -0.51 | 0.06 | 0.54 | 0.09 | 0.01 | -0.64 | -0.08 | 0.25 | -0.58 | -0.31 | 0.14 |
| P1 | 0.12 | -0.09 | 0.05 | 0.14 | 0.44 | -0.05 | 0.24 | -0.06 | -0.21 | 0.21 | 0.13 | 0.16 | 0.29 | -0.26 | 0.07 |
| P2 | 0.15 | 0.07 | -0.38 | -0.07 | 0.69 | 0.18 | 0.29 | -0.10 | -0.30 | 0.45 | 0.23 | -0.30 | 0.33 | -0.34 | 0.18 |
| P3 | -0.13 | -0.51 | -0.41 | 0.21 | 0.92 | -0.17 | -0.15 | -0.03 | -0.02 | -0.32 | -0.29 | 0.09 | -0.02 | -1.02 | 0.59 |
| P4 | 0.80 | 1.19 | -0.44 | 0.01 | -0.45 | 0.73 | -0.22 | -0.19 | 0.42 | 0.30 | -0.47 | 0.13 | 0.41 | -0.75 | 0.15 |
| C1 | -0.21 | -0.05 | -0.17 | -0.22 | -0.13 | 0.11 | 0.03 | 0.00 | 0.05 | 0.19 | -0.14 | 0.07 | 0.18 | -0.08 | -0.00 |
| C2 | -0.02 | -0.17 | 0.13 | -0.26 | 0.20 | 0.24 | -0.21 | 0.00 | -0.06 | -0.23 | 0.20 | 0.49 | -0.22 | -0.25 | -0.14 |
| C3 | -0.68 | 1.49 | -0.31 | -0.02 | -0.10 | -1.07 | -0.46 | 1.24 | 0.59 | 0.19 | 0.50 | -0.17 | -1.02 | -0.54 | 0.01 |
| C4 | 0.06 | 0.33 | -0.39 | 0.11 | -0.36 | 0.28 | -0.32 | 0.15 | 0.48 | 0.28 | 0.05 | 0.01 | 0.07 | -0.46 | 0.10 |


## Post-hoc checks (added after seeing the first run; NOT candidates, not counted)

H1 = long the week after expiry (mirror of O2, chosen because O2 lost) - data-snooped, so its 'survives' flag means nothing statistically. Rows with suffix h = P-variants re-run with G filled on half days (last live price that day); months filled for the Nasdaq: 10 (2013-10, 2013-12, 2014-12, 2015-01, 2016-01, 2016-11, 2019-12, 2022-11, 2024-12, 2025-12). Primary rows shown next to them.

### Nasdaq 100

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check avg R | check t | holdout avg R | holdout t | last3y avg R | last3y t | 2011-21 avg R | 2022+ avg R | dir hit % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 post-hoc: long X -> end of next week (O2 mirror) | 169 | 0.955 | 57.988 | 1.019 | 0.108 | 1.855 | 64 | 0.140 | 1.364 | 0.061 | 0.724 | 0.147 | 1.178 | 0.129 | 1.106 | 0.119 | 0.086 | 55.621 | False |
| O2 post-opex short: X -> end of next week | 169 | 0.955 | 34.320 | 1.017 | -0.187 | -3.318 | 64 | -0.299 | -3.651 | -0.085 | -0.855 | -0.195 | -1.842 | -0.178 | -1.767 | -0.196 | -0.171 | 36.686 | False |
| C1 control: long non-expiry weeks | 547 | 3.090 | 55.027 | 0.928 | 0.041 | 1.252 | 207 | -0.019 | -0.337 | 0.067 | 1.407 | 0.099 | 1.321 | 0.105 | 1.453 | 0.031 | 0.060 | 55.759 | False |
| P1 rebalance: s -> ME, against sign(G) | 160 | 0.904 | 49.375 | 1.044 | 0.005 | 0.089 | 59 | 0.066 | 0.630 | -0.024 | -0.263 | -0.043 | -0.381 | -0.051 | -0.485 | -0.010 | 0.035 | 50.000 | False |
| P1h rebalance: s -> ME, against sign(G) [half-day G fill] | 168 | 0.949 | 50.000 | 1.077 | 0.022 | 0.377 | 64 | 0.063 | 0.653 | -0.020 | -0.218 | 0.032 | 0.267 | 0.018 | 0.163 | -0.005 | 0.076 | 50.000 | False |
| P2 P1 with abs(G) > 2% | 101 | 0.571 | 48.515 | 1.060 | -0.000 | -0.005 | 33 | 0.114 | 0.683 | -0.056 | -0.506 | -0.056 | -0.343 | -0.048 | -0.310 | -0.013 | 0.028 | 50.495 | False |
| P2h P1 with abs(G) > 2% [half-day G fill] | 108 | 0.610 | 49.074 | 1.111 | 0.022 | 0.280 | 37 | 0.094 | 0.633 | -0.049 | -0.450 | 0.058 | 0.341 | 0.060 | 0.370 | -0.012 | 0.096 | 50.926 | False |
| P3 P1 quarter-end months | 52 | 0.294 | 46.154 | 0.775 | -0.121 | -1.093 | 20 | -0.023 | -0.100 | -0.134 | -1.066 | -0.303 | -1.331 | -0.253 | -1.209 | -0.103 | -0.158 | 46.154 | False |
| P3h P1 quarter-end months [half-day G fill] | 57 | 0.322 | 49.123 | 0.852 | -0.059 | -0.551 | 22 | -0.010 | -0.047 | -0.117 | -0.957 | -0.031 | -0.116 | -0.012 | -0.050 | -0.080 | -0.016 | 47.368 | False |
| P4 TOM long ME -> TD3 when G > 0 | 102 | 0.576 | 55.882 | 1.283 | 0.257 | 2.121 | 39 | 0.280 | 1.491 | 0.273 | 1.468 | 0.176 | 0.557 | 0.171 | 0.567 | 0.304 | 0.150 | 59.804 | False |
| P4h TOM long ME -> TD3 when G > 0 [half-day G fill] | 109 | 0.616 | 55.963 | 1.272 | 0.253 | 2.177 | 42 | 0.215 | 1.198 | 0.273 | 1.513 | 0.287 | 0.973 | 0.269 | 0.945 | 0.280 | 0.194 | 59.633 | False |
| C3 control: TOM long when G < 0 | 51 | 0.288 | 35.294 | 1.476 | -0.106 | -0.666 | 16 | -0.116 | -0.439 | 0.046 | 0.181 | -0.468 | -1.654 | -0.468 | -1.654 | 0.028 | -0.297 | 47.059 | False |
| C3h control: TOM long when G < 0 [half-day G fill] | 53 | 0.299 | 35.849 | 1.436 | -0.107 | -0.690 | 18 | -0.118 | -0.482 | 0.046 | 0.181 | -0.468 | -1.654 | -0.468 | -1.654 | 0.018 | -0.297 | 47.170 | False |

### S&P 500

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check avg R | check t | holdout avg R | holdout t | last3y avg R | last3y t | 2011-21 avg R | 2022+ avg R | dir hit % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 post-hoc: long X -> end of next week (O2 mirror) | 155 | 0.886 | 50.968 | 0.919 | -0.013 | -0.236 | 57 | -0.111 | -1.242 | 0.005 | 0.050 | 0.124 | 1.007 | 0.107 | 0.894 | -0.043 | 0.042 | 58.065 | False |
| O2 post-opex short: X -> end of next week | 155 | 0.886 | 38.065 | 1.014 | -0.138 | -2.214 | 57 | -0.166 | -1.878 | -0.053 | -0.462 | -0.265 | -2.530 | -0.244 | -2.352 | -0.113 | -0.186 | 41.935 | False |
| C1 control: long non-expiry weeks | 524 | 2.994 | 52.863 | 0.840 | -0.019 | -0.566 | 194 | -0.110 | -2.096 | 0.035 | 0.693 | 0.037 | 0.485 | 0.045 | 0.602 | -0.032 | 0.006 | 58.397 | False |
| P1 rebalance: s -> ME, against sign(G) | 155 | 0.886 | 54.194 | 1.154 | 0.085 | 1.422 | 57 | 0.115 | 1.135 | 0.082 | 0.866 | 0.032 | 0.289 | 0.038 | 0.372 | 0.086 | 0.083 | 58.710 | False |
| P1h rebalance: s -> ME, against sign(G) [half-day G fill] | 162 | 0.926 | 54.938 | 1.167 | 0.097 | 1.653 | 61 | 0.103 | 1.067 | 0.084 | 0.900 | 0.114 | 0.949 | 0.112 | 1.015 | 0.081 | 0.128 | 59.259 | False |
| P2 P1 with abs(G) > 2% | 94 | 0.537 | 50.000 | 1.333 | 0.083 | 1.021 | 28 | 0.160 | 1.005 | 0.052 | 0.445 | 0.047 | 0.291 | 0.031 | 0.202 | 0.111 | 0.029 | 55.319 | False |
| P2h P1 with abs(G) > 2% [half-day G fill] | 101 | 0.577 | 51.485 | 1.339 | 0.102 | 1.304 | 32 | 0.131 | 0.914 | 0.055 | 0.486 | 0.172 | 1.006 | 0.151 | 0.924 | 0.102 | 0.104 | 56.436 | False |
| P3 P1 quarter-end months | 51 | 0.291 | 50.980 | 0.787 | -0.055 | -0.499 | 19 | 0.070 | 0.291 | -0.123 | -1.076 | -0.150 | -0.602 | -0.135 | -0.603 | -0.019 | -0.128 | 52.941 | False |
| P3h P1 quarter-end months [half-day G fill] | 55 | 0.314 | 52.727 | 0.877 | -0.006 | -0.056 | 20 | 0.051 | 0.219 | -0.108 | -0.981 | 0.113 | 0.414 | 0.104 | 0.416 | -0.021 | 0.022 | 54.545 | False |
| P4 TOM long ME -> TD3 when G > 0 | 95 | 0.543 | 51.579 | 1.132 | 0.091 | 0.767 | 36 | 0.201 | 1.017 | 0.065 | 0.384 | -0.079 | -0.258 | -0.125 | -0.449 | 0.164 | -0.082 | 62.105 | False |
| P4h TOM long ME -> TD3 when G > 0 [half-day G fill] | 102 | 0.583 | 51.961 | 1.106 | 0.087 | 0.762 | 39 | 0.169 | 0.914 | 0.016 | 0.094 | 0.081 | 0.276 | 0.025 | 0.091 | 0.131 | -0.014 | 62.745 | False |
| C3 control: TOM long when G < 0 | 53 | 0.303 | 37.736 | 1.394 | -0.080 | -0.508 | 18 | -0.356 | -1.418 | 0.262 | 1.070 | -0.517 | -2.034 | -0.210 | -0.551 | -0.071 | -0.094 | 49.057 | False |
| C3h control: TOM long when G < 0 [half-day G fill] | 55 | 0.314 | 38.182 | 1.389 | -0.074 | -0.474 | 20 | -0.310 | -1.281 | 0.262 | 1.070 | -0.517 | -2.034 | -0.210 | -0.551 | -0.061 | -0.094 | 49.091 | False |

