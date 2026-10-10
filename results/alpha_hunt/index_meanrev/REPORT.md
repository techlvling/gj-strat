# Alpha hunt: equity-index short-term reversal / dip-buying (`index_meanrev`)

Rules, variants and the survival bar are in the docstring of `run_alpha_index_meanrev.py` (fixed before running). Long-only on the close (MR11 = SELL control), 1-10 day holds, stops 1-2 x ATR20 checked minute by minute (S&P on hourly bars), all costs included. Periods: design 2010-17 (indices from data start), check 2018-23, holdout 2024-26; last 3 years = 2023-10-08..2026-10-07.

**Tests: 44 (11 variants x 4 markets). Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): 2 (Nasdaq 100 MR4, Nasdaq 100 MR6). Expected by luck: 0.26.**

## Summary and verdict

**Verdict: 2 of 44 tests clear the charter bar, both on the Nasdaq: MR4 and MR6. Both are weak. MR4's edge is mostly
the index's upward drift. MR6 rests on 61 trades. Neither is a robust new edge. At most, one of them is a small optional add-on.**

- **Survivors (Nasdaq 100):**
  - **MR4** (close < -1 sigma60, hold 5 closes, SL 2 ATR): 254 trades, 1.4/month, 57% wins, avg R +0.133.
    Design +0.201 (t 2.01), check +0.097, holdout +0.090, last 3y +0.091.
  - **MR6** (RSI2 < 5 above SMA200, exit C > SMA5): 61 trades, 0.35/month, 70% wins, avg R +0.235.
    Design +0.433 (t 2.28, only 20 trades, all 2014-17), check +0.073, holdout +0.298 (12 trades).
  - Luck alone gives about 0.26 survivors. The tests are not independent: MR1/MR3/MR4 share entries, and MR5-MR8 overlap heavily.
- **Replication (avg R over the whole period):**
  - MR4: S&P +0.059, Nikkei +0.086, gold +0.028.
  - MR6: S&P +0.264, Nikkei +0.086, gold +0.086.
  - Pooled indices, month-clustered: MR6 design t 1.94 (just under 2), check +0.085, holdout +0.361. MR4 design t 1.75.
  - No variant passes the bar pooled.
- **Drift caveat (post-hoc diagnostic, last section):**
  - A long-only 1-10 day hold earns index drift. That drift was 15-22%/yr on the Nasdaq and 17-27%/yr in 2024-26 for all markets.
  - MR4 after drift: design +0.07 (t 0.8), check +0.02, holdout -0.04. MR4 is essentially beta.
  - MR6 after drift: design +0.36 (t 1.9), check +0.02 (t 0.1), holdout +0.21 (t 1.5).
  - Both beat their unconditional same-mechanics benchmarks (B4 / B5) in every period. The check-period margins are small: +0.06 R for MR4 and +0.05 R for MR6.
- **What failed:**
  - The literature's core claim, a one-day reversal after a down close (MR1, MR2), is too weak to matter after costs. So are the VIX-conditioned version (MR3) and the IBS versions (MR9, MR10). On the Nasdaq their avg R is +0.03 to +0.06 and their design t is at most 1.42.
  - On the Nasdaq, MR3's VIX > median filter did worse than MR1.
  - Dip-buys did better in **low**-ATR regimes on the Nasdaq (every long variant) and in the S&P RSI2 variants. Nagel predicts the opposite. Gold did better in high-ATR regimes.
  - The SELL control MR11 is negative on all four markets, as theory plus drift predicts.
- **Crash risk:**
  - At 0.5% risk per trade (Nasdaq + S&P as one position, plus the Nikkei), the worst day is -0.9% to -1.15%.
  - Worst days fell most often in Feb/Mar 2020 and Feb/Mar 2018. The worst single index trade is -2.2R (a gap through the stop).
  - The ATR stops keep the crash days well inside a 5% daily limit at this size.
- **Prop impact (Alpha Swing):**
  - Adding the survivors changes months per funded account by 0.6 at most.
  - MR4 at 1% with the boost x1.5 rule: 4.86 -> 4.52 (starts 2011-25) and 4.34 -> 4.05 (starts 2018-25), and the pass-eventually rate goes up.
  - Under run_index_prop.py's acceptance rule (lower months per funded account AND pass-eventually not lower, in both windows), three of eight mixes are accepted: MR4 0.5% (normal risk), MR6 1% (normal risk) and MR4 1% (boost). The margins are small.
- **Fixes to the spec (also in the docstring):**
  - Every minute market needs ticks at the signal minute. S&P uses only hourly bars with ticks.
  - The close series is split at data gaps of more than 5 trading days (Nasdaq and S&P 2013, Nikkei 2015). Inside each part the indicators warm up again, so MR5-MR8 on the Nasdaq only start in mid-2014 and their design sample is small.
  - The S&P fills at the signal close itself, with zero lag, which is slightly optimistic.

## Judging

Nasdaq gets the charter bar; S&P and Nikkei replicate if avg R > 0 over the whole period; gold is judged on its own.

| variant | Nasdaq charter bar | S&P avg R | Nikkei avg R | Gold charter bar | Gold avg R | S&P replicates | Nikkei replicates |
|---|---|---|---|---|---|---|---|
| MR1 | False | 0.003 | 0.049 | False | -0.000 | True | True |
| MR2 | False | -0.038 | 0.147 | False | -0.037 | False | True |
| MR3 | False | -0.004 | 0.061 | False | 0.000 | False | True |
| MR4 | True | 0.059 | 0.086 | False | 0.028 | True | True |
| MR5 | False | 0.137 | -0.026 | False | 0.033 | True | False |
| MR6 | True | 0.264 | 0.086 | False | 0.086 | True | True |
| MR7 | False | 0.130 | -0.088 | False | 0.031 | True | False |
| MR8 | False | 0.100 | -0.092 | False | -0.007 | True | False |
| MR9 | False | 0.031 | 0.041 | False | 0.007 | True | True |
| MR10 | False | 0.151 | 0.191 | False | 0.003 | True | True |
| MR11 | False | -0.033 | -0.084 | False | -0.067 | False | False |


## Nasdaq 100 (USATECHIDXUSD)

Months with data: 177. trades/month = trades / months with data.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 r < -1 sigma60, exit next close | 399 | 2.254 | 53.133 | 1.067 | 0.043 | 1.521 | 135 | 0.077 | 1.417 | 180 | -0.002 | -0.062 | 84 | 0.085 | 1.605 | 89 | 0.082 | 1.600 | 9.524 | False |
| MR2 r < -2 sigma60, exit next close | 133 | 0.751 | 55.639 | 0.960 | 0.046 | 0.860 | 43 | 0.060 | 0.592 | 60 | -0.008 | -0.100 | 30 | 0.136 | 1.321 | 31 | 0.111 | 1.072 | 14.286 | False |
| MR3 MR1 + VIX > 252d median, exit next close | 234 | 1.322 | 55.128 | 0.950 | 0.033 | 0.932 | 59 | 0.031 | 0.381 | 119 | 0.026 | 0.535 | 56 | 0.049 | 0.802 | 58 | 0.038 | 0.628 | 8.547 | False |
| MR4 MR1 entry, exit 5th close | 254 | 1.435 | 57.480 | 1.065 | 0.133 | 2.419 | 91 | 0.201 | 2.008 | 113 | 0.097 | 1.235 | 50 | 0.090 | 0.772 | 53 | 0.091 | 0.811 | 22.835 | True |
| MR5 C > SMA200 & RSI2 < 10, exit C > SMA5 (cap 10) | 106 | 0.599 | 69.811 | 0.673 | 0.132 | 1.954 | 34 | 0.171 | 1.273 | 42 | -0.023 | -0.198 | 30 | 0.304 | 3.645 | 32 | 0.297 | 3.736 | 21.698 | False |
| MR6 C > SMA200 & RSI2 < 5, exit C > SMA5 (cap 10) | 61 | 0.345 | 70.492 | 0.883 | 0.235 | 2.457 | 20 | 0.433 | 2.279 | 29 | 0.073 | 0.527 | 12 | 0.298 | 2.060 | 13 | 0.302 | 2.264 | 19.672 | True |
| MR7 C > SMA200 & RSI2 < 10, exit RSI2 > 70 (cap 10) | 102 | 0.576 | 73.529 | 0.630 | 0.197 | 2.532 | 33 | 0.239 | 1.670 | 40 | 0.008 | 0.056 | 29 | 0.410 | 3.833 | 30 | 0.362 | 3.186 | 25.490 | False |
| MR8 RSI2 < 10 (no SMA200), exit C > SMA5 (cap 10) | 161 | 0.910 | 69.565 | 0.697 | 0.135 | 2.489 | 61 | 0.195 | 1.957 | 65 | -0.001 | -0.009 | 35 | 0.282 | 3.466 | 37 | 0.277 | 3.556 | 20.497 | False |
| MR9 IBS <= 0.15 & down close, exit next close | 394 | 2.226 | 51.523 | 1.019 | 0.026 | 0.666 | 134 | 0.011 | 0.161 | 189 | 0.029 | 0.540 | 71 | 0.045 | 0.487 | 77 | 0.069 | 0.772 | 20.305 | False |
| MR10 MR9 + range >= 1.5 ATR, exit C > entry-day H (cap 3) | 74 | 0.418 | 54.054 | 0.972 | 0.056 | 0.502 | 36 | 0.204 | 1.257 | 27 | -0.080 | -0.431 | 11 | -0.097 | -0.355 | 12 | -0.013 | -0.050 | 29.730 | False |
| MR11 control SELL: r > +1 sigma60, exit next close | 491 | 2.774 | 43.381 | 1.077 | -0.032 | -1.557 | 175 | -0.055 | -1.524 | 221 | -0.012 | -0.384 | 95 | -0.037 | -0.885 | 104 | -0.040 | -1.023 | 3.259 | False |


## S&P 500 (USA500IDXUSD)

Months with data: 175. trades/month = trades / months with data.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 r < -1 sigma60, exit next close | 375 | 2.143 | 51.733 | 0.947 | 0.003 | 0.114 | 137 | 0.038 | 0.764 | 163 | -0.091 | -2.027 | 75 | 0.146 | 2.106 | 79 | 0.137 | 2.026 | 10.933 | False |
| MR2 r < -2 sigma60, exit next close | 116 | 0.663 | 51.724 | 0.801 | -0.038 | -0.654 | 37 | 0.009 | 0.092 | 55 | -0.098 | -1.111 | 24 | 0.028 | 0.214 | 24 | 0.028 | 0.214 | 14.655 | False |
| MR3 MR1 + VIX > 252d median, exit next close | 218 | 1.246 | 53.211 | 0.865 | -0.004 | -0.098 | 59 | -0.011 | -0.142 | 105 | -0.059 | -1.032 | 54 | 0.112 | 1.331 | 56 | 0.087 | 1.059 | 12.385 | False |
| MR4 MR1 entry, exit 5th close | 237 | 1.354 | 54.008 | 1.001 | 0.059 | 1.062 | 91 | 0.122 | 1.390 | 101 | -0.036 | -0.439 | 45 | 0.143 | 1.013 | 48 | 0.166 | 1.196 | 26.160 | False |
| MR5 C > SMA200 & RSI2 < 10, exit C > SMA5 (cap 10) | 106 | 0.606 | 69.811 | 0.666 | 0.137 | 1.961 | 33 | 0.133 | 1.039 | 42 | 0.048 | 0.422 | 31 | 0.264 | 2.121 | 32 | 0.224 | 1.762 | 23.585 | False |
| MR6 C > SMA200 & RSI2 < 5, exit C > SMA5 (cap 10) | 60 | 0.343 | 75.000 | 0.782 | 0.264 | 2.938 | 15 | 0.251 | 1.377 | 28 | 0.142 | 1.041 | 17 | 0.475 | 3.127 | 17 | 0.475 | 3.127 | 18.333 | False |
| MR7 C > SMA200 & RSI2 < 10, exit RSI2 > 70 (cap 10) | 100 | 0.571 | 69.000 | 0.644 | 0.130 | 1.617 | 32 | 0.145 | 1.050 | 39 | 0.012 | 0.095 | 29 | 0.272 | 1.792 | 30 | 0.229 | 1.498 | 28.000 | False |
| MR8 RSI2 < 10 (no SMA200), exit C > SMA5 (cap 10) | 162 | 0.926 | 67.901 | 0.651 | 0.100 | 1.762 | 58 | 0.072 | 0.709 | 67 | 0.041 | 0.484 | 37 | 0.250 | 2.266 | 38 | 0.216 | 1.925 | 24.691 | False |
| MR9 IBS <= 0.15 & down close, exit next close | 375 | 2.143 | 50.667 | 1.073 | 0.031 | 0.766 | 142 | 0.020 | 0.291 | 172 | 0.010 | 0.166 | 61 | 0.118 | 1.214 | 68 | 0.140 | 1.505 | 18.667 | False |
| MR10 MR9 + range >= 1.5 ATR, exit C > entry-day H (cap 3) | 73 | 0.417 | 50.685 | 1.319 | 0.151 | 1.172 | 30 | 0.224 | 1.122 | 30 | -0.018 | -0.089 | 13 | 0.372 | 1.181 | 14 | 0.443 | 1.476 | 36.986 | False |
| MR11 control SELL: r > +1 sigma60, exit next close | 485 | 2.771 | 43.505 | 1.078 | -0.033 | -1.479 | 173 | -0.033 | -0.793 | 213 | -0.020 | -0.587 | 99 | -0.063 | -1.590 | 107 | -0.076 | -2.024 | 3.505 | False |


## Nikkei 225 (JPNIDXJPY)

Months with data: 170. trades/month = trades / months with data.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 r < -1 sigma60, exit next close | 334 | 1.965 | 54.192 | 1.035 | 0.049 | 1.401 | 101 | 0.082 | 1.137 | 166 | 0.017 | 0.366 | 67 | 0.080 | 1.022 | 74 | 0.082 | 1.113 | 11.078 | False |
| MR2 r < -2 sigma60, exit next close | 88 | 0.518 | 59.091 | 1.089 | 0.147 | 1.589 | 19 | 0.335 | 1.381 | 45 | 0.025 | 0.211 | 24 | 0.225 | 1.328 | 24 | 0.225 | 1.328 | 18.182 | False |
| MR3 MR1 + VIX > 252d median, exit next close | 207 | 1.218 | 55.072 | 1.036 | 0.061 | 1.312 | 48 | 0.038 | 0.321 | 113 | 0.052 | 0.960 | 46 | 0.109 | 1.011 | 49 | 0.117 | 1.154 | 12.077 | False |
| MR4 MR1 entry, exit 5th close | 220 | 1.294 | 53.182 | 1.095 | 0.086 | 1.326 | 68 | 0.064 | 0.513 | 109 | 0.100 | 1.113 | 43 | 0.087 | 0.600 | 48 | 0.104 | 0.787 | 28.636 | False |
| MR5 C > SMA200 & RSI2 < 10, exit C > SMA5 (cap 10) | 82 | 0.482 | 64.634 | 0.502 | -0.026 | -0.327 | 19 | -0.051 | -0.284 | 40 | -0.164 | -1.399 | 23 | 0.234 | 1.934 | 25 | 0.240 | 2.119 | 30.488 | False |
| MR6 C > SMA200 & RSI2 < 5, exit C > SMA5 (cap 10) | 43 | 0.253 | 69.767 | 0.565 | 0.086 | 0.761 | 13 | 0.106 | 0.477 | 22 | 0.030 | 0.176 | 8 | 0.210 | 1.126 | 9 | 0.263 | 1.523 | 27.907 | False |
| MR7 C > SMA200 & RSI2 < 10, exit RSI2 > 70 (cap 10) | 77 | 0.453 | 62.338 | 0.462 | -0.088 | -1.026 | 18 | -0.028 | -0.143 | 37 | -0.312 | -2.574 | 22 | 0.239 | 1.879 | 24 | 0.253 | 2.167 | 36.364 | False |
| MR8 RSI2 < 10 (no SMA200), exit C > SMA5 (cap 10) | 146 | 0.859 | 58.219 | 0.539 | -0.092 | -1.487 | 53 | -0.128 | -1.195 | 64 | -0.146 | -1.540 | 29 | 0.094 | 0.785 | 31 | 0.108 | 0.950 | 34.932 | False |
| MR9 IBS <= 0.15 & down close, exit next close | 327 | 1.924 | 53.823 | 0.978 | 0.041 | 0.930 | 123 | 0.037 | 0.456 | 137 | 0.024 | 0.365 | 67 | 0.084 | 1.031 | 73 | 0.055 | 0.705 | 20.489 | False |
| MR10 MR9 + range >= 1.5 ATR, exit C > entry-day H (cap 3) | 35 | 0.206 | 51.429 | 1.363 | 0.191 | 0.950 | 21 | -0.059 | -0.244 | 9 | 0.465 | 1.281 | 5 | 0.749 | 1.026 | 5 | 0.749 | 1.026 | 34.286 | False |
| MR11 control SELL: r > +1 sigma60, exit next close | 381 | 2.241 | 42.257 | 0.875 | -0.084 | -3.275 | 119 | -0.135 | -2.830 | 177 | -0.075 | -2.114 | 85 | -0.032 | -0.556 | 97 | -0.021 | -0.403 | 7.612 | False |


## Gold (XAUUSD) - separate replication, not pooled

Months with data: 202. trades/month = trades / months with data.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | SL % | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 r < -1 sigma60, exit next close | 468 | 2.317 | 53.846 | 0.855 | -0.000 | -0.018 | 222 | -0.018 | -0.656 | 173 | -0.011 | -0.326 | 73 | 0.077 | 1.245 | 78 | 0.063 | 1.073 | 4.915 | False |
| MR2 r < -2 sigma60, exit next close | 115 | 0.569 | 49.565 | 0.833 | -0.037 | -0.818 | 51 | -0.022 | -0.321 | 46 | -0.100 | -1.433 | 18 | 0.079 | 0.616 | 19 | 0.058 | 0.469 | 8.696 | False |
| MR3 MR1 + VIX > 252d median, exit next close | 222 | 1.099 | 54.054 | 0.852 | 0.000 | 0.014 | 90 | 0.001 | 0.019 | 93 | -0.034 | -0.870 | 39 | 0.082 | 0.853 | 39 | 0.082 | 0.853 | 4.955 | False |
| MR4 MR1 entry, exit 5th close | 321 | 1.589 | 49.844 | 1.102 | 0.028 | 0.641 | 148 | -0.019 | -0.321 | 119 | -0.010 | -0.140 | 54 | 0.238 | 1.958 | 56 | 0.199 | 1.655 | 18.692 | False |
| MR5 C > SMA200 & RSI2 < 10, exit C > SMA5 (cap 10) | 92 | 0.455 | 64.130 | 0.633 | 0.033 | 0.481 | 36 | 0.029 | 0.244 | 34 | -0.062 | -0.536 | 22 | 0.186 | 1.757 | 24 | 0.213 | 2.130 | 19.565 | False |
| MR6 C > SMA200 & RSI2 < 5, exit C > SMA5 (cap 10) | 48 | 0.238 | 64.583 | 0.814 | 0.086 | 1.102 | 16 | -0.138 | -0.880 | 20 | 0.113 | 1.159 | 12 | 0.339 | 2.372 | 13 | 0.331 | 2.510 | 12.500 | False |
| MR7 C > SMA200 & RSI2 < 10, exit RSI2 > 70 (cap 10) | 88 | 0.436 | 63.636 | 0.635 | 0.031 | 0.413 | 36 | 0.037 | 0.296 | 32 | -0.083 | -0.651 | 20 | 0.203 | 1.514 | 22 | 0.232 | 1.856 | 23.864 | False |
| MR8 RSI2 < 10 (no SMA200), exit C > SMA5 (cap 10) | 184 | 0.911 | 61.957 | 0.597 | -0.007 | -0.153 | 93 | -0.025 | -0.362 | 64 | -0.037 | -0.456 | 27 | 0.125 | 1.272 | 29 | 0.152 | 1.609 | 22.283 | False |
| MR9 IBS <= 0.15 & down close, exit next close | 438 | 2.168 | 52.055 | 0.946 | 0.007 | 0.207 | 186 | -0.025 | -0.501 | 176 | -0.025 | -0.484 | 76 | 0.156 | 1.932 | 87 | 0.208 | 2.523 | 15.297 | False |
| MR10 MR9 + range >= 1.5 ATR, exit C > entry-day H (cap 3) | 119 | 0.589 | 51.261 | 0.960 | 0.003 | 0.043 | 56 | -0.035 | -0.345 | 44 | 0.048 | 0.391 | 19 | 0.011 | 0.062 | 20 | 0.007 | 0.042 | 23.529 | False |
| MR11 control SELL: r > +1 sigma60, exit next close | 517 | 2.559 | 46.035 | 0.786 | -0.067 | -3.425 | 228 | -0.043 | -1.635 | 182 | -0.066 | -1.892 | 107 | -0.119 | -2.516 | 117 | -0.125 | -2.763 | 5.609 | False |


## Pooled indices (Nasdaq + Nikkei + S&P), month-clustered t

Sum of R per calendar month (zero for months without trades inside the data span), t over months. The three indices are close to one bet (see overlap), so pooling adds little independent evidence.

| variant | trades | avg R | month t (all) | design n | design avg R | design month t | check n | check avg R | check month t | holdout n | holdout avg R | holdout month t | last3y n | last3y avg R | last3y month t | indices avg R > 0 | pooled passes bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 | 1108 | 0.031 | 1.521 | 373 | 0.064 | 1.690 | 509 | -0.025 | -0.830 | 226 | 0.104 | 2.608 | 242 | 0.100 | 2.638 | 3 | False |
| MR2 | 337 | 0.044 | 1.077 | 99 | 0.094 | 1.256 | 160 | -0.030 | -0.487 | 78 | 0.130 | 1.733 | 79 | 0.120 | 1.597 | 2 | False |
| MR3 | 659 | 0.029 | 1.163 | 166 | 0.018 | 0.412 | 337 | 0.008 | 0.204 | 156 | 0.088 | 1.871 | 163 | 0.079 | 1.715 | 2 | False |
| MR4 | 711 | 0.094 | 2.155 | 250 | 0.135 | 1.746 | 323 | 0.056 | 0.946 | 138 | 0.106 | 0.986 | 149 | 0.119 | 1.190 | 3 | False |
| MR5 | 294 | 0.090 | 1.779 | 86 | 0.107 | 1.239 | 124 | -0.044 | -0.549 | 84 | 0.270 | 3.086 | 89 | 0.255 | 3.024 | 2 | False |
| MR6 | 164 | 0.207 | 2.625 | 48 | 0.288 | 1.935 | 79 | 0.085 | 0.699 | 37 | 0.361 | 2.831 | 39 | 0.368 | 3.036 | 3 | False |
| MR7 | 279 | 0.094 | 1.593 | 83 | 0.145 | 1.528 | 116 | -0.093 | -0.978 | 80 | 0.313 | 2.886 | 84 | 0.283 | 2.645 | 2 | False |
| MR8 | 469 | 0.052 | 1.301 | 172 | 0.054 | 0.810 | 196 | -0.034 | -0.533 | 101 | 0.216 | 2.863 | 106 | 0.206 | 2.812 | 2 | False |
| MR9 | 1096 | 0.032 | 1.131 | 399 | 0.022 | 0.436 | 498 | 0.021 | 0.541 | 199 | 0.081 | 1.142 | 218 | 0.087 | 1.289 | 3 | False |
| MR10 | 182 | 0.120 | 1.258 | 87 | 0.148 | 1.081 | 66 | 0.023 | 0.147 | 29 | 0.259 | 0.969 | 31 | 0.316 | 1.219 | 3 | False |
| MR11 | 1357 | -0.047 | -2.629 | 467 | -0.067 | -2.378 | 611 | -0.033 | -1.098 | 279 | -0.045 | -1.341 | 308 | -0.047 | -1.534 | 0 | False |


## Overlap of trade dates

### Between variants (same market)

| market | pair | A days | B days | % of A also B | % of B also A |
|---|---|---|---|---|---|
| USATECHIDXUSD | MR1 / MR5 | 399 | 106 | 15.5 | 58.5 |
| USATECHIDXUSD | MR1 / MR9 | 399 | 394 | 48.4 | 49.0 |
| USATECHIDXUSD | MR5 / MR9 | 106 | 394 | 33.0 | 8.9 |
| USA500IDXUSD | MR1 / MR5 | 375 | 106 | 15.5 | 54.7 |
| USA500IDXUSD | MR1 / MR9 | 375 | 375 | 42.9 | 42.9 |
| USA500IDXUSD | MR5 / MR9 | 106 | 375 | 46.2 | 13.1 |
| JPNIDXJPY | MR1 / MR5 | 334 | 82 | 12.9 | 52.4 |
| JPNIDXJPY | MR1 / MR9 | 334 | 327 | 39.2 | 40.1 |
| JPNIDXJPY | MR5 / MR9 | 82 | 327 | 23.2 | 5.8 |
| XAUUSD | MR1 / MR5 | 468 | 92 | 9.4 | 47.8 |
| XAUUSD | MR1 / MR9 | 468 | 438 | 48.7 | 52.1 |
| XAUUSD | MR5 / MR9 | 92 | 438 | 33.7 | 7.1 |


### Across indices (same variant)

| variant | Nasdaq days | S&P days | Nikkei days | % Nasdaq days also S&P | % Nasdaq days also Nikkei (same date) | % Nasdaq days with Nikkei next Tokyo day | corr monthly R Nasdaq-S&P | corr monthly R Nasdaq-Nikkei |
|---|---|---|---|---|---|---|---|---|
| MR1 | 399.00 | 375.00 | 334.00 | 67.92 | 13.53 | 32.08 | 0.51 | 0.01 |
| MR2 | 133.00 | 116.00 | 88.00 | 60.90 | 8.27 | 20.30 | 0.46 | 0.17 |
| MR3 | 234.00 | 218.00 | 207.00 | 73.93 | 18.38 | 29.06 | 0.45 | -0.07 |
| MR4 | 254.00 | 237.00 | 220.00 | 52.76 | 7.87 | 26.77 | 0.49 | 0.33 |
| MR5 | 106.00 | 106.00 | 82.00 | 39.62 | 7.55 | 9.43 | 0.42 | 0.16 |
| MR6 | 61.00 | 60.00 | 43.00 | 47.54 | 4.92 | 13.11 | 0.44 | 0.30 |
| MR7 | 102.00 | 100.00 | 77.00 | 38.24 | 8.82 | 7.84 | 0.48 | 0.19 |
| MR8 | 161.00 | 162.00 | 146.00 | 44.10 | 11.18 | 13.04 | 0.43 | 0.18 |
| MR9 | 394.00 | 375.00 | 327.00 | 58.38 | 9.14 | 13.96 | 0.53 | 0.21 |
| MR10 | 74.00 | 73.00 | 35.00 | 60.81 | 2.70 | 2.70 | 0.64 | 0.07 |
| MR11 | 491.00 | 485.00 | 381.00 | 72.30 | 13.24 | 27.09 | 0.76 | 0.12 |


## Avg R by volatility regime (ATR20 >= vs < its trailing 250-day median)

| market | variant | high-ATR n | high-ATR avg R | high-ATR t | low-ATR n | low-ATR avg R | low-ATR t |
|---|---|---|---|---|---|---|---|
| USATECHIDXUSD | MR1 | 266 | 0.039 | 1.125 | 107 | 0.082 | 1.587 |
| USATECHIDXUSD | MR2 | 98 | 0.002 | 0.030 | 29 | 0.218 | 1.921 |
| USATECHIDXUSD | MR3 | 203 | 0.039 | 1.049 | 26 | -0.020 | -0.187 |
| USATECHIDXUSD | MR4 | 150 | 0.064 | 0.905 | 85 | 0.254 | 2.697 |
| USATECHIDXUSD | MR5 | 61 | 0.089 | 1.078 | 45 | 0.190 | 1.674 |
| USATECHIDXUSD | MR6 | 36 | 0.205 | 1.715 | 25 | 0.278 | 1.737 |
| USATECHIDXUSD | MR7 | 57 | 0.154 | 1.526 | 45 | 0.251 | 2.059 |
| USATECHIDXUSD | MR8 | 89 | 0.028 | 0.412 | 58 | 0.245 | 2.601 |
| USATECHIDXUSD | MR9 | 234 | 0.004 | 0.087 | 125 | 0.080 | 1.158 |
| USATECHIDXUSD | MR10 | 40 | -0.074 | -0.467 | 26 | 0.246 | 1.332 |
| USATECHIDXUSD | MR11 | 308 | -0.017 | -0.685 | 158 | -0.062 | -1.704 |
| USA500IDXUSD | MR1 | 213 | 0.046 | 1.147 | 140 | -0.048 | -0.956 |
| USA500IDXUSD | MR2 | 67 | -0.068 | -0.924 | 42 | 0.058 | 0.550 |
| USA500IDXUSD | MR3 | 181 | 0.012 | 0.278 | 32 | -0.057 | -0.462 |
| USA500IDXUSD | MR4 | 122 | 0.067 | 0.904 | 100 | 0.058 | 0.653 |
| USA500IDXUSD | MR5 | 42 | 0.015 | 0.148 | 63 | 0.238 | 2.563 |
| USA500IDXUSD | MR6 | 25 | 0.179 | 1.355 | 34 | 0.317 | 2.518 |
| USA500IDXUSD | MR7 | 41 | 0.025 | 0.208 | 58 | 0.224 | 2.093 |
| USA500IDXUSD | MR8 | 77 | -0.012 | -0.154 | 74 | 0.246 | 2.928 |
| USA500IDXUSD | MR9 | 205 | 0.054 | 0.987 | 143 | 0.011 | 0.156 |
| USA500IDXUSD | MR10 | 33 | 0.139 | 0.685 | 37 | 0.176 | 0.983 |
| USA500IDXUSD | MR11 | 273 | -0.034 | -1.211 | 186 | -0.020 | -0.503 |
| JPNIDXJPY | MR1 | 191 | -0.006 | -0.134 | 116 | 0.099 | 1.541 |
| JPNIDXJPY | MR2 | 58 | 0.040 | 0.395 | 27 | 0.414 | 2.110 |
| JPNIDXJPY | MR3 | 141 | 0.013 | 0.246 | 59 | 0.148 | 1.460 |
| JPNIDXJPY | MR4 | 124 | 0.018 | 0.235 | 79 | 0.142 | 1.230 |
| JPNIDXJPY | MR5 | 50 | -0.033 | -0.372 | 32 | -0.015 | -0.097 |
| JPNIDXJPY | MR6 | 26 | 0.001 | 0.010 | 17 | 0.216 | 1.183 |
| JPNIDXJPY | MR7 | 46 | -0.060 | -0.596 | 31 | -0.130 | -0.842 |
| JPNIDXJPY | MR8 | 81 | -0.069 | -0.963 | 55 | -0.040 | -0.343 |
| JPNIDXJPY | MR9 | 183 | 0.058 | 1.026 | 106 | -0.012 | -0.151 |
| JPNIDXJPY | MR10 | 16 | 0.294 | 0.895 | 8 | 0.522 | 1.351 |
| JPNIDXJPY | MR11 | 224 | -0.021 | -0.717 | 125 | -0.198 | -4.111 |
| XAUUSD | MR1 | 226 | 0.034 | 1.199 | 221 | -0.039 | -1.278 |
| XAUUSD | MR2 | 54 | 0.020 | 0.296 | 55 | -0.104 | -1.601 |
| XAUUSD | MR3 | 139 | 0.014 | 0.363 | 76 | -0.020 | -0.455 |
| XAUUSD | MR4 | 151 | 0.083 | 1.285 | 154 | -0.046 | -0.760 |
| XAUUSD | MR5 | 57 | 0.112 | 1.282 | 31 | -0.129 | -1.090 |
| XAUUSD | MR6 | 31 | 0.168 | 1.658 | 15 | -0.107 | -0.843 |
| XAUUSD | MR7 | 53 | 0.119 | 1.179 | 31 | -0.147 | -1.207 |
| XAUUSD | MR8 | 84 | 0.080 | 1.129 | 92 | -0.107 | -1.583 |
| XAUUSD | MR9 | 211 | 0.052 | 1.163 | 207 | -0.043 | -0.859 |
| XAUUSD | MR10 | 46 | 0.013 | 0.129 | 65 | -0.006 | -0.055 |
| XAUUSD | MR11 | 252 | -0.063 | -2.201 | 233 | -0.078 | -2.628 |


## Worst single day at 0.5% risk per trade

Indices: Nasdaq and S&P count as one position (average of the two when both are open) + Nikkei, each 0.5%. MTM = every open trade marked at each signal close, booked by NY trading day (17:00 roll); realised = net R on the exit day. Gold alone at 0.5%.

| variant | indices worst day % (MTM) | date | indices worst day % (realised) | date  | indices days < -1% (MTM) | worst single index trade R | gold worst day % (MTM) | gold date |
|---|---|---|---|---|---|---|---|---|
| MR1 | -1.07 | 2020-02-28 | -1.07 | 2020-02-28 | 9 | -1.34 | -0.51 | 2011-05-05 |
| MR2 | -1.13 | 2020-03-12 | -1.13 | 2020-03-12 | 5 | -1.29 | -0.51 | 2021-06-17 |
| MR3 | -1.07 | 2020-02-28 | -1.07 | 2020-02-28 | 6 | -1.29 | -0.50 | 2020-02-04 |
| MR4 | -1.10 | 2021-11-26 | -1.04 | 2012-11-13 | 2 | -1.18 | -0.87 | 2025-10-21 |
| MR5 | -1.10 | 2018-02-05 | -1.08 | 2018-03-23 | 1 | -1.16 | -0.54 | 2024-11-11 |
| MR6 | -0.96 | 2021-10-04 | -1.09 | 2018-03-23 | 0 | -1.16 | -0.50 | 2026-03-19 |
| MR7 | -1.15 | 2020-02-24 | -1.08 | 2018-03-23 | 2 | -1.16 | -0.54 | 2024-11-11 |
| MR8 | -1.10 | 2018-02-05 | -1.08 | 2018-03-23 | 1 | -1.18 | -0.54 | 2024-11-11 |
| MR9 | -1.14 | 2012-07-23 | -1.14 | 2012-07-23 | 7 | -2.20 | -0.52 | 2023-09-28 |
| MR10 | -0.89 | 2019-05-06 | -1.02 | 2022-01-10 | 0 | -1.34 | -0.78 | 2024-11-11 |
| MR11 | -0.99 | 2025-10-06 | -0.99 | 2025-10-06 | 0 | -1.99 | -0.51 | 2019-06-20 |


## Avg R per trade by year, pooled indices

| variant | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MR1 | -0.03 | 0.21 | 0.02 | -0.00 | 0.06 | 0.25 | -0.11 | 0.05 | 0.07 | -0.01 | -0.06 | -0.05 | 0.07 | 0.17 | 0.05 |
| MR2 | -0.15 | -0.12 | 0.13 | -0.00 | 0.20 | 0.29 | -0.08 | 0.08 | -0.09 | 0.14 | -0.04 | -0.21 | 0.02 | 0.27 | 0.08 |
| MR3 | 0.06 | -0.06 | -0.07 | 0.02 | 0.07 | 0.24 | -0.08 | 0.06 | 0.09 | 0.19 | -0.06 | 0.04 | 0.01 | 0.14 | 0.09 |
| MR4 | 0.13 | 0.64 | -0.00 | 0.14 | -0.05 | 0.30 | -0.04 | 0.22 | 0.24 | -0.01 | -0.14 | 0.19 | 0.17 | 0.12 | 0.01 |
| MR5 | -1.04 |  | -0.19 | 0.16 | 0.07 | 0.32 | -0.36 | -0.19 | -0.07 | 0.24 | -0.44 | 0.10 | 0.29 | 0.20 | 0.29 |
| MR6 | 0.60 |  | -0.25 | 0.50 | -0.19 | 0.69 | -0.30 | -0.38 | -0.09 | 0.54 | -0.14 | 0.23 | 0.39 | 0.14 | 0.50 |
| MR7 | -1.04 |  | -0.14 | 0.10 | 0.17 | 0.39 | -0.42 | -0.47 | -0.04 | 0.26 | -0.44 | 0.03 | 0.31 | 0.31 | 0.32 |
| MR8 | -0.06 | 0.19 | -0.16 | 0.07 | 0.07 | 0.32 | -0.28 | 0.06 | -0.08 | 0.20 | -0.11 | 0.10 | 0.24 | 0.08 | 0.31 |
| MR9 | -0.02 | 0.08 | -0.02 | -0.10 | -0.00 | 0.27 | -0.06 | 0.02 | 0.16 | -0.07 | -0.02 | 0.08 | 0.06 | 0.09 | 0.10 |
| MR10 | 0.15 | -0.31 | 0.27 | -0.24 | -0.05 | 0.91 | -0.15 | -0.25 | 0.55 | 0.07 | -0.57 | 0.74 | 0.37 | 0.17 | 0.15 |
| MR11 | -0.15 | -0.12 | -0.06 | -0.05 | 0.05 | -0.09 | -0.03 | -0.04 | 0.07 | -0.12 | 0.03 | -0.10 | -0.02 | -0.04 | -0.08 |


## Prop sim (Alpha Swing, run_m3_addon.ALPHA rules)

Basket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 USDJPY 3% (run_m3_addon.build_legs); new leg(s) added at 0.5% and 1% risk.

| mix | risk rule | window | pass ≤1 month % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | median months to pass | months per funded account | max DD % |
|---|---|---|---|---|---|---|---|---|---|---|
| basket | normal risk | starts 2011-2025 | 7.8 | 28.0 | 44.4 | 31.1 | 59.1 | 3.3 | 7.3 | 26.4 |
| basket + Nasdaq 100 MR4 0.5% | normal risk | starts 2011-2025 | 7.6 | 27.5 | 45.3 | 29.9 | 60.5 | 3.5 | 7.1 | 26.6 |
| basket + Nasdaq 100 MR6 0.5% | normal risk | starts 2011-2025 | 7.8 | 28.2 | 45.0 | 31.2 | 59.9 | 3.3 | 7.2 | 26.1 |
| basket + Nasdaq 100 MR4 1% | normal risk | starts 2011-2025 | 7.6 | 29.6 | 47.8 | 29.7 | 61.4 | 3.2 | 6.7 | 26.7 |
| basket + Nasdaq 100 MR6 1% | normal risk | starts 2011-2025 | 7.8 | 28.8 | 45.6 | 30.6 | 60.5 | 3.3 | 7.1 | 26.0 |
| basket | normal risk | starts 2018-2025 | 6.9 | 32.9 | 58.1 | 19.4 | 74.0 | 3.6 | 5.8 | 24.8 |
| basket + Nasdaq 100 MR4 0.5% | normal risk | starts 2018-2025 | 6.6 | 32.1 | 58.7 | 18.6 | 74.6 | 3.7 | 5.8 | 23.5 |
| basket + Nasdaq 100 MR6 0.5% | normal risk | starts 2018-2025 | 6.9 | 32.8 | 57.9 | 19.4 | 73.9 | 3.6 | 5.8 | 24.5 |
| basket + Nasdaq 100 MR4 1% | normal risk | starts 2018-2025 | 6.5 | 32.6 | 59.4 | 19.4 | 73.2 | 3.5 | 5.7 | 22.3 |
| basket + Nasdaq 100 MR6 1% | normal risk | starts 2018-2025 | 7.0 | 33.3 | 58.1 | 19.2 | 74.4 | 3.5 | 5.8 | 24.2 |
| basket | boost x1.5 | starts 2011-2025 | 12.2 | 31.3 | 43.4 | 50.9 | 46.2 | 2.0 | 4.9 | 26.4 |
| basket + Nasdaq 100 MR4 0.5% | boost x1.5 | starts 2011-2025 | 11.9 | 31.6 | 44.3 | 50.6 | 46.5 | 2.0 | 4.7 | 26.6 |
| basket + Nasdaq 100 MR6 0.5% | boost x1.5 | starts 2011-2025 | 12.1 | 31.2 | 43.0 | 51.3 | 45.5 | 1.9 | 4.9 | 26.1 |
| basket + Nasdaq 100 MR4 1% | boost x1.5 | starts 2011-2025 | 12.8 | 32.3 | 45.7 | 49.2 | 47.8 | 1.9 | 4.5 | 26.7 |
| basket + Nasdaq 100 MR6 1% | boost x1.5 | starts 2011-2025 | 12.3 | 31.5 | 42.6 | 51.4 | 44.8 | 1.9 | 5.0 | 26.0 |
| basket | boost x1.5 | starts 2018-2025 | 11.9 | 34.5 | 51.9 | 42.7 | 55.2 | 2.3 | 4.3 | 24.8 |
| basket + Nasdaq 100 MR4 0.5% | boost x1.5 | starts 2018-2025 | 11.3 | 34.8 | 52.8 | 42.4 | 54.7 | 2.3 | 4.2 | 23.5 |
| basket + Nasdaq 100 MR6 0.5% | boost x1.5 | starts 2018-2025 | 11.8 | 34.5 | 51.9 | 42.6 | 54.5 | 2.2 | 4.3 | 24.5 |
| basket + Nasdaq 100 MR4 1% | boost x1.5 | starts 2018-2025 | 12.9 | 35.8 | 54.7 | 40.0 | 57.0 | 2.2 | 4.0 | 22.3 |
| basket + Nasdaq 100 MR6 1% | boost x1.5 | starts 2018-2025 | 12.0 | 34.4 | 50.4 | 43.4 | 52.6 | 2.1 | 4.6 | 24.2 |

Acceptance by run_index_prop.py's rule (months per funded account lower AND pass eventually % not lower than the basket, for both
start windows): accepted = MR4 0.5% (normal risk; 7.09 vs 7.29 and 5.76 vs 5.79 months), MR6 1% (normal risk; 7.07 vs 7.29 and
5.76 vs 5.79 months), MR4 1% (boost x1.5; 4.52 vs 4.86 and 4.05 vs 4.34 months). Not accepted = MR4 1% normal (pass eventually 73.2%
vs 74.0% for starts 2018-25), MR6 0.5% normal, MR4 0.5% boost, MR6 0.5% and 1% boost.

## Post-hoc diagnostic: how much is plain index drift? (run_alpha_index_meanrev_drift.py)

Written after seeing the results; not a test and does not change the verdict. (1) Unconditional long benchmarks through the same pipeline (same closes, fills, stops, costs, one position at a time). (2) Per trade, drift R = in-period mean log return per calendar day x days held x entry / stop; excess R = R - drift R.

### Index drift by period

| market | design drift %/yr (log) | check drift %/yr (log) | holdout drift %/yr (log) |
|---|---|---|---|
| Nasdaq 100 | 15.0 | 16.1 | 22.2 |
| Nikkei 225 | 10.3 | 6.4 | 26.8 |
| Gold | 2.2 | 7.7 | 24.8 |
| S&P 500 | 10.9 | 9.6 | 17.1 |


### Unconditional benchmarks
- B1: every close, exit next close, SL 1.5 x ATR20
- B4: every close, exit 5th close, SL 2.0 x ATR20
- B5: every close with C > SMA200, exit C > SMA5 (cap 10), SL 2.0 x ATR20
- B8: every close, exit C > SMA5 (cap 10), SL 2.0 x ATR20
- B9: every close (previous close defined), exit next close, SL 1.0 x ATR20

| market | test | trades | avg R | design avg R | check avg R | holdout avg R |
|---|---|---|---|---|---|---|
| Nasdaq 100 | B1 | 1728 | -0.002 | 0.000 | -0.002 | -0.008 |
| Nasdaq 100 | B4 | 576 | 0.047 | 0.063 | 0.038 | 0.035 |
| Nasdaq 100 | B5 | 927 | 0.021 | 0.014 | 0.024 | 0.024 |
| Nasdaq 100 | B8 | 1177 | 0.008 | -0.003 | 0.011 | 0.025 |
| Nasdaq 100 | B9 | 1763 | -0.007 | -0.006 | -0.002 | -0.020 |
| S&P 500 | B1 | 1723 | -0.012 | -0.002 | -0.015 | -0.024 |
| S&P 500 | B4 | 574 | 0.008 | -0.028 | 0.033 | 0.021 |
| S&P 500 | B5 | 939 | -0.006 | -0.003 | -0.011 | -0.000 |
| S&P 500 | B8 | 1205 | -0.002 | -0.018 | 0.011 | 0.004 |
| S&P 500 | B9 | 1773 | -0.018 | -0.006 | -0.018 | -0.044 |
| Nikkei 225 | B1 | 1495 | -0.018 | 0.008 | -0.050 | 0.011 |
| Nikkei 225 | B4 | 497 | 0.015 | 0.074 | -0.044 | 0.051 |
| Nikkei 225 | B5 | 691 | 0.024 | 0.072 | -0.006 | 0.029 |
| Nikkei 225 | B8 | 1015 | 0.014 | 0.005 | 0.007 | 0.042 |
| Nikkei 225 | B9 | 1569 | -0.020 | -0.011 | -0.055 | 0.035 |
| Gold | B1 | 2051 | 0.002 | -0.022 | 0.001 | 0.072 |
| Gold | B4 | 683 | 0.058 | 0.005 | 0.066 | 0.189 |
| Gold | B5 | 845 | 0.020 | -0.006 | 0.022 | 0.054 |
| Gold | B8 | 1276 | 0.014 | 0.001 | 0.015 | 0.046 |
| Gold | B9 | 2057 | 0.009 | -0.028 | 0.013 | 0.102 |


### Variants: avg R minus benchmark, and drift-adjusted (excess) R per period

| market | test | trades | avg R | benchmark | avg R minus benchmark | design excess R | design excess t | check excess R | check excess t | holdout excess R | holdout excess t |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 100 | MR1 | 399 | 0.043 | B1 | 0.045 | 0.040 | 0.740 | -0.024 | -0.584 | 0.048 | 0.902 |
| Nasdaq 100 | MR2 | 133 | 0.046 | B1 | 0.049 | 0.025 | 0.242 | -0.027 | -0.335 | 0.097 | 0.964 |
| Nasdaq 100 | MR3 | 234 | 0.033 | B1 | 0.035 | -0.006 | -0.076 | 0.007 | 0.139 | 0.017 | 0.278 |
| Nasdaq 100 | MR4 | 254 | 0.133 | B4 | 0.086 | 0.074 | 0.766 | 0.020 | 0.258 | -0.037 | -0.327 |
| Nasdaq 100 | MR5 | 106 | 0.132 | B5 | 0.111 | 0.086 | 0.643 | -0.080 | -0.692 | 0.217 | 2.576 |
| Nasdaq 100 | MR6 | 61 | 0.235 | B5 | 0.214 | 0.364 | 1.927 | 0.018 | 0.127 | 0.213 | 1.484 |
| Nasdaq 100 | MR7 | 102 | 0.197 | B5 | 0.176 | 0.140 | 0.990 | -0.060 | -0.441 | 0.299 | 2.823 |
| Nasdaq 100 | MR8 | 161 | 0.135 | B8 | 0.126 | 0.110 | 1.097 | -0.051 | -0.599 | 0.202 | 2.478 |
| Nasdaq 100 | MR9 | 394 | 0.026 | B9 | 0.032 | -0.041 | -0.579 | -0.002 | -0.035 | -0.006 | -0.069 |
| Nasdaq 100 | MR10 | 74 | 0.056 |  |  | 0.097 | 0.607 | -0.145 | -0.802 | -0.214 | -0.815 |
| Nasdaq 100 | MR11 | 491 | -0.032 |  |  | -0.020 | -0.561 | 0.013 | 0.412 | -0.003 | -0.078 |
| S&P 500 | MR1 | 375 | 0.003 | B1 | 0.016 | 0.006 | 0.116 | -0.110 | -2.427 | 0.106 | 1.522 |
| S&P 500 | MR2 | 116 | -0.038 | B1 | -0.026 | -0.021 | -0.223 | -0.115 | -1.306 | -0.015 | -0.115 |
| S&P 500 | MR3 | 218 | -0.004 | B1 | 0.008 | -0.040 | -0.505 | -0.074 | -1.286 | 0.077 | 0.915 |
| S&P 500 | MR4 | 237 | 0.059 | B4 | 0.051 | 0.007 | 0.079 | -0.095 | -1.176 | 0.003 | 0.022 |
| S&P 500 | MR5 | 106 | 0.137 | B5 | 0.143 | 0.055 | 0.434 | -0.001 | -0.007 | 0.178 | 1.433 |
| S&P 500 | MR6 | 60 | 0.264 | B5 | 0.270 | 0.174 | 0.952 | 0.096 | 0.696 | 0.401 | 2.636 |
| S&P 500 | MR7 | 100 | 0.130 | B5 | 0.136 | 0.036 | 0.265 | -0.048 | -0.362 | 0.153 | 1.009 |
| S&P 500 | MR8 | 162 | 0.100 | B8 | 0.102 | -0.000 | -0.005 | -0.000 | -0.003 | 0.172 | 1.564 |
| S&P 500 | MR9 | 375 | 0.031 | B9 | 0.049 | -0.028 | -0.405 | -0.017 | -0.280 | 0.058 | 0.598 |
| S&P 500 | MR10 | 73 | 0.151 |  |  | 0.131 | 0.658 | -0.071 | -0.354 | 0.253 | 0.826 |
| S&P 500 | MR11 | 485 | -0.033 |  |  | -0.001 | -0.026 | 0.001 | 0.036 | -0.023 | -0.570 |
| Nikkei 225 | MR1 | 334 | 0.049 | B1 | 0.067 | 0.059 | 0.818 | 0.006 | 0.122 | 0.040 | 0.504 |
| Nikkei 225 | MR2 | 88 | 0.147 | B1 | 0.165 | 0.316 | 1.298 | 0.015 | 0.123 | 0.182 | 1.066 |
| Nikkei 225 | MR3 | 207 | 0.061 | B1 | 0.079 | 0.017 | 0.143 | 0.041 | 0.769 | 0.070 | 0.653 |
| Nikkei 225 | MR4 | 220 | 0.086 | B4 | 0.072 | -0.011 | -0.086 | 0.062 | 0.706 | -0.031 | -0.217 |
| Nikkei 225 | MR5 | 82 | -0.026 | B5 | -0.050 | -0.089 | -0.498 | -0.187 | -1.594 | 0.166 | 1.339 |
| Nikkei 225 | MR6 | 43 | 0.086 | B5 | 0.063 | 0.070 | 0.313 | 0.009 | 0.055 | 0.130 | 0.662 |
| Nikkei 225 | MR7 | 77 | -0.088 | B5 | -0.112 | -0.076 | -0.388 | -0.343 | -2.840 | 0.144 | 1.114 |
| Nikkei 225 | MR8 | 146 | -0.092 | B8 | -0.106 | -0.166 | -1.544 | -0.169 | -1.786 | 0.019 | 0.152 |
| Nikkei 225 | MR9 | 327 | 0.041 | B9 | 0.062 | 0.009 | 0.109 | 0.008 | 0.114 | 0.033 | 0.411 |
| Nikkei 225 | MR10 | 35 | 0.191 |  |  | -0.108 | -0.453 | 0.431 | 1.198 | 0.678 | 0.905 |
| Nikkei 225 | MR11 | 381 | -0.084 |  |  | -0.113 | -2.368 | -0.064 | -1.805 | 0.003 | 0.046 |
| Gold | MR1 | 468 | -0.000 | B1 | -0.002 | -0.022 | -0.808 | -0.027 | -0.827 | 0.038 | 0.621 |
| Gold | MR2 | 115 | -0.037 | B1 | -0.039 | -0.026 | -0.391 | -0.117 | -1.668 | 0.045 | 0.345 |
| Gold | MR3 | 222 | 0.000 | B1 | -0.002 | -0.003 | -0.064 | -0.050 | -1.268 | 0.048 | 0.502 |
| Gold | MR4 | 321 | 0.028 | B4 | -0.030 | -0.034 | -0.567 | -0.067 | -0.984 | 0.096 | 0.811 |
| Gold | MR5 | 92 | 0.033 | B5 | 0.013 | 0.018 | 0.153 | -0.112 | -0.956 | 0.096 | 0.879 |
| Gold | MR6 | 48 | 0.086 | B5 | 0.066 | -0.149 | -0.954 | 0.066 | 0.659 | 0.282 | 2.020 |
| Gold | MR7 | 88 | 0.031 | B5 | 0.011 | 0.023 | 0.182 | -0.142 | -1.111 | 0.078 | 0.567 |
| Gold | MR8 | 184 | -0.007 | B8 | -0.021 | -0.036 | -0.513 | -0.083 | -1.004 | 0.040 | 0.400 |
| Gold | MR9 | 438 | 0.007 | B9 | -0.002 | -0.031 | -0.621 | -0.048 | -0.954 | 0.101 | 1.253 |
| Gold | MR10 | 119 | 0.003 |  |  | -0.047 | -0.462 | 0.003 | 0.024 | -0.118 | -0.711 |
| Gold | MR11 | 517 | -0.067 |  |  | -0.038 | -1.457 | -0.048 | -1.362 | -0.075 | -1.592 |

