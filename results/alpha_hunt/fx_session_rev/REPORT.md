# Alpha hunt: fx_session_rev (conditional cross-session currency-strength reversal)

Spec, rules and the survival bar are in the docstring of `run_alpha_fx_session_rev.py` (fixed before running).
Every weekday t: currency strength s_c from the 16:54 NY close of the previous weekday (A) to the 06:59 London
close of t (B), all 28 pairs; trade the weakest/strongest pair at the 07:00 London open, SL 1 x ATR20, no TP,
exit 16:05 London (X1) or 16:55 NY (X2). Reversal = buy the weakest, sell the strongest; momentum = opposite.
Filter F = D >= 1.5 x median D of the previous 60 valid days. Costs: real bid/ask, $7/lot, 0.2 pip slippage
per stop fill, swap (always 0: both exits are before the rollover).

Valid days (all 28 pairs live at both stamps): 4232 of 4373 weekdays. Invalid share by weekday (Mon..Fri, %): 8.7, 2.1, 1.8, 1.8, 1.7. F days: 913 (21.9% of valid days with a defined filter). Max |sum of s_c| = 1.0e-17 (rounding).

**Tests judged: 8 (4 reversal candidates V1-V4, 4 momentum controls V5-V8, same bar). Survivors of the charter bar (design t >= 2, check and holdout avg R > 0): none. Expected by luck: 8 x 0.006 = 0.05.**

## All tests (pooled over pairs, one trade per day, net R)

t = over trades; month t = month-clustered (sum of R per calendar month, zero-trade months count as 0). last3y = 2023-10-08..2026-10-07.

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | month t | design n | design avg R | design t | design month t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 4215.000 | 20.866 | 45.836 | 1.001 | -0.031 | -4.078 | -4.064 | 1967.000 | -0.038 | -3.468 | -3.407 | 1537.000 | -0.028 | -2.249 | 711.000 | -0.016 | -0.877 | 769.000 | -0.012 | -0.695 | False |
| V2 | 913.000 | 4.520 | 43.921 | 1.087 | -0.033 | -1.877 | -1.861 | 417.000 | -0.018 | -0.669 | -0.718 | 338.000 | -0.061 | -2.050 | 158.000 | -0.017 | -0.402 | 174.000 | -0.022 | -0.566 | False |
| V3 | 4215.000 | 20.866 | 45.765 | 0.959 | -0.044 | -5.217 | -5.515 | 1967.000 | -0.050 | -4.106 | -4.349 | 1537.000 | -0.040 | -2.788 | 711.000 | -0.037 | -1.801 | 769.000 | -0.031 | -1.530 | False |
| V4 | 913.000 | 4.520 | 43.921 | 1.092 | -0.037 | -1.818 | -1.904 | 417.000 | -0.018 | -0.592 | -0.660 | 338.000 | -0.081 | -2.458 | 158.000 | 0.006 | 0.121 | 174.000 | -0.003 | -0.071 | False |
| V5 | 4215.000 | 20.866 | 47.497 | 0.948 | -0.028 | -3.847 | -3.769 | 1967.000 | -0.023 | -2.171 | -2.039 | 1537.000 | -0.028 | -2.304 | 711.000 | -0.042 | -2.370 | 769.000 | -0.045 | -2.641 | False |
| V6 | 913.000 | 4.520 | 50.712 | 0.884 | -0.019 | -1.104 | -1.019 | 417.000 | -0.032 | -1.237 | -1.255 | 338.000 | 0.012 | 0.415 | 158.000 | -0.053 | -1.237 | 174.000 | -0.047 | -1.164 | False |
| V7 | 4215.000 | 20.866 | 47.355 | 0.945 | -0.033 | -4.109 | -4.525 | 1967.000 | -0.033 | -2.775 | -2.920 | 1537.000 | -0.033 | -2.371 | 711.000 | -0.036 | -1.914 | 769.000 | -0.042 | -2.310 | False |
| V8 | 913.000 | 4.520 | 50.931 | 0.841 | -0.031 | -1.601 | -1.610 | 417.000 | -0.047 | -1.614 | -1.705 | 338.000 | 0.011 | 0.341 | 158.000 | -0.080 | -1.721 | 174.000 | -0.071 | -1.618 | False |

## Home-hours subset (W or S in JPY, AUD, NZD)

| variant | trades | trades/month | win % | avg win / avg loss | avg R | t | month t | design n | design avg R | design t | design month t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 3907.000 | 19.342 | 45.482 | 0.990 | -0.035 | -4.538 | -4.608 | 1834.000 | -0.040 | -3.561 | -3.507 | 1412.000 | -0.037 | -2.876 | 661.000 | -0.018 | -0.934 | 717.000 | -0.015 | -0.789 | False |
| V2 | 881.000 | 4.361 | 43.587 | 1.067 | -0.040 | -2.212 | -2.169 | 407.000 | -0.018 | -0.674 | -0.689 | 323.000 | -0.074 | -2.522 | 151.000 | -0.024 | -0.574 | 167.000 | -0.030 | -0.736 | False |
| V3 | 3907.000 | 19.342 | 45.457 | 0.955 | -0.047 | -5.413 | -5.838 | 1834.000 | -0.050 | -4.020 | -4.290 | 1412.000 | -0.047 | -3.242 | 661.000 | -0.037 | -1.741 | 717.000 | -0.031 | -1.512 | False |
| V4 | 881.000 | 4.361 | 43.360 | 1.081 | -0.044 | -2.166 | -2.263 | 407.000 | -0.017 | -0.548 | -0.591 | 323.000 | -0.094 | -2.859 | 151.000 | -0.012 | -0.238 | 167.000 | -0.020 | -0.422 | False |
| V5 | 3907.000 | 19.342 | 47.709 | 0.958 | -0.024 | -3.255 | -3.266 | 1834.000 | -0.022 | -2.010 | -1.888 | 1412.000 | -0.021 | -1.691 | 661.000 | -0.038 | -2.091 | 717.000 | -0.041 | -2.327 | False |
| V6 | 881.000 | 4.361 | 51.078 | 0.903 | -0.012 | -0.673 | -0.614 | 407.000 | -0.028 | -1.073 | -1.071 | 323.000 | 0.023 | 0.791 | 151.000 | -0.044 | -1.002 | 167.000 | -0.039 | -0.936 | False |
| V7 | 3907.000 | 19.342 | 47.581 | 0.943 | -0.032 | -3.802 | -4.197 | 1834.000 | -0.033 | -2.767 | -2.868 | 1412.000 | -0.027 | -1.925 | 661.000 | -0.036 | -1.837 | 717.000 | -0.041 | -2.188 | False |
| V8 | 881.000 | 4.361 | 51.532 | 0.853 | -0.022 | -1.130 | -1.108 | 407.000 | -0.046 | -1.582 | -1.628 | 323.000 | 0.028 | 0.861 | 151.000 | -0.065 | -1.370 | 167.000 | -0.057 | -1.278 | False |

## Avg R by D tercile (unfiltered variants)

D_rel = D / median(previous 60 valid D); tercile cutoffs from design days: 0.790, 1.241 (F needs D_rel >= 1.5). Raw D cutoffs (full sample): 34.9 bp, 56.4 bp.

| variant | tercile by | tercile | n | avg R | t | design avg R | design t | check avg R | check t | holdout avg R | holdout t | last3y avg R | last3y t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | D_rel (design cutoffs) | 1 | 1407 | -0.009 | -0.730 | -0.031 | -1.733 | 0.005 | 0.220 | 0.017 | 0.498 | 0.029 | 0.826 |
| V1 | D_rel (design cutoffs) | 2 | 1356 | -0.045 | -3.686 | -0.057 | -3.161 | -0.025 | -1.200 | -0.056 | -2.001 | -0.050 | -1.887 |
| V1 | D_rel (design cutoffs) | 3 | 1409 | -0.037 | -2.609 | -0.023 | -1.083 | -0.062 | -2.773 | -0.015 | -0.446 | -0.019 | -0.620 |
| V1 | raw D (full sample) | 1 | 1406 | -0.023 | -1.795 | -0.033 | -1.601 | -0.025 | -1.323 | -0.002 | -0.069 | 0.006 | 0.195 |
| V1 | raw D (full sample) | 2 | 1405 | -0.037 | -2.982 | -0.058 | -3.145 | -0.004 | -0.178 | -0.052 | -1.907 | -0.044 | -1.744 |
| V1 | raw D (full sample) | 3 | 1404 | -0.032 | -2.322 | -0.025 | -1.396 | -0.064 | -2.426 | 0.006 | 0.146 | -0.001 | -0.028 |
| V3 | D_rel (design cutoffs) | 1 | 1407 | -0.032 | -2.197 | -0.044 | -2.179 | -0.020 | -0.857 | -0.022 | -0.580 | -0.013 | -0.353 |
| V3 | D_rel (design cutoffs) | 2 | 1356 | -0.060 | -4.380 | -0.072 | -3.649 | -0.028 | -1.171 | -0.094 | -3.071 | -0.078 | -2.672 |
| V3 | D_rel (design cutoffs) | 3 | 1409 | -0.038 | -2.422 | -0.027 | -1.161 | -0.069 | -2.641 | 0.001 | 0.020 | -0.004 | -0.098 |
| V3 | raw D (full sample) | 1 | 1406 | -0.044 | -3.058 | -0.046 | -1.948 | -0.044 | -2.065 | -0.041 | -1.193 | -0.034 | -0.996 |
| V3 | raw D (full sample) | 2 | 1405 | -0.049 | -3.498 | -0.071 | -3.602 | -0.004 | -0.178 | -0.083 | -2.875 | -0.064 | -2.336 |
| V3 | raw D (full sample) | 3 | 1404 | -0.039 | -2.541 | -0.035 | -1.762 | -0.078 | -2.696 | 0.025 | 0.559 | 0.016 | 0.369 |
| V5 | D_rel (design cutoffs) | 1 | 1407 | -0.049 | -3.967 | -0.034 | -1.886 | -0.062 | -3.000 | -0.061 | -2.057 | -0.067 | -2.277 |
| V5 | D_rel (design cutoffs) | 2 | 1356 | -0.017 | -1.425 | -0.008 | -0.490 | -0.032 | -1.580 | -0.009 | -0.314 | -0.018 | -0.649 |
| V5 | D_rel (design cutoffs) | 3 | 1409 | -0.018 | -1.352 | -0.028 | -1.393 | 0.008 | 0.368 | -0.053 | -1.593 | -0.048 | -1.539 |
| V5 | raw D (full sample) | 1 | 1406 | -0.039 | -3.152 | -0.040 | -1.937 | -0.035 | -1.844 | -0.047 | -1.700 | -0.051 | -1.871 |
| V5 | raw D (full sample) | 2 | 1405 | -0.023 | -1.963 | -0.007 | -0.423 | -0.050 | -2.447 | -0.010 | -0.363 | -0.020 | -0.783 |
| V5 | raw D (full sample) | 3 | 1404 | -0.021 | -1.589 | -0.025 | -1.455 | 0.010 | 0.388 | -0.073 | -1.870 | -0.066 | -1.790 |
| V7 | D_rel (design cutoffs) | 1 | 1407 | -0.049 | -3.567 | -0.045 | -2.232 | -0.058 | -2.447 | -0.043 | -1.352 | -0.045 | -1.434 |
| V7 | D_rel (design cutoffs) | 2 | 1356 | -0.021 | -1.566 | -0.018 | -0.926 | -0.043 | -1.914 | 0.020 | 0.652 | -0.001 | -0.036 |
| V7 | D_rel (design cutoffs) | 3 | 1409 | -0.032 | -2.109 | -0.041 | -1.818 | 0.002 | 0.061 | -0.084 | -2.331 | -0.079 | -2.329 |
| V7 | raw D (full sample) | 1 | 1406 | -0.038 | -2.738 | -0.052 | -2.181 | -0.033 | -1.544 | -0.027 | -0.908 | -0.029 | -0.997 |
| V7 | raw D (full sample) | 2 | 1405 | -0.029 | -2.192 | -0.017 | -0.879 | -0.059 | -2.563 | 0.005 | 0.182 | -0.017 | -0.649 |
| V7 | raw D (full sample) | 3 | 1404 | -0.033 | -2.196 | -0.034 | -1.776 | 0.002 | 0.079 | -0.103 | -2.408 | -0.094 | -2.311 |

## Costs (share of R)

R unit = 1 x ATR20 of the traded pair. Round-trip spread = (spread at the entry bar + spread at the exit bar) / 2 (half of each is paid crossing from mid). Gross = on real bid/ask before commission/slippage; mid-to-mid = gross + round-trip spread (approximate: frictionless result). Total cost = round-trip spread + commission + slippage.

| variant | entry spread / R | exit-bar spread / R | round-trip spread (R) | commission + slippage (R) | total cost (R) | mid-to-mid avg R (approx) | mid-to-mid t | gross avg R (bid/ask, before comm.) | net avg R | avg hold h |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 0.019 | 0.018 | 0.018 | 0.012 | 0.030 | -0.001 | -0.095 | -0.019 | -0.031 | 8.947 |
| V2 | 0.017 | 0.015 | 0.016 | 0.011 | 0.027 | -0.006 | -0.339 | -0.022 | -0.033 | 8.841 |
| V3 | 0.019 | 0.035 | 0.027 | 0.012 | 0.039 | -0.005 | -0.639 | -0.032 | -0.044 | 14.335 |
| V4 | 0.017 | 0.029 | 0.023 | 0.011 | 0.034 | -0.003 | -0.134 | -0.026 | -0.037 | 14.086 |
| V5 | 0.019 | 0.018 | 0.019 | 0.012 | 0.030 | 0.002 | 0.291 | -0.016 | -0.028 | 8.927 |
| V6 | 0.017 | 0.016 | 0.016 | 0.011 | 0.028 | 0.008 | 0.481 | -0.008 | -0.019 | 8.824 |
| V7 | 0.019 | 0.035 | 0.027 | 0.012 | 0.039 | 0.005 | 0.665 | -0.022 | -0.033 | 14.301 |
| V8 | 0.017 | 0.030 | 0.023 | 0.011 | 0.035 | 0.003 | 0.167 | -0.020 | -0.031 | 13.988 |

## Per pair (n = trades, avg R net)

Pairs positive among pairs with >= 20 trades: V1 7/26, V2 5/12, V3 6/26, V4 6/12, V5 7/26, V6 4/12, V7 6/26, V8 5/12

| pair | n V1 | n V2 | avg R V1 | avg R V2 | avg R V3 | avg R V4 | avg R V5 | avg R V6 | avg R V7 | avg R V8 |
|---|---|---|---|---|---|---|---|---|---|---|
| AUDJPY | 650.000 | 209.000 | -0.010 | 0.008 | 0.000 | 0.016 | -0.037 | -0.063 | -0.045 | -0.059 |
| NZDJPY | 580.000 | 190.000 | -0.066 | -0.104 | -0.070 | -0.100 | 0.008 | 0.057 | -0.016 | 0.021 |
| NZDUSD | 409.000 | 79.000 | -0.009 | -0.032 | -0.018 | -0.070 | -0.053 | -0.029 | -0.060 | 0.003 |
| AUDUSD | 354.000 | 81.000 | -0.042 | -0.102 | -0.050 | -0.108 | -0.010 | 0.044 | -0.012 | 0.058 |
| USDJPY | 237.000 | 47.000 | -0.039 | -0.151 | -0.064 | -0.159 | 0.024 | 0.093 | 0.029 | 0.074 |
| AUDNZD | 205.000 | 34.000 | -0.046 | 0.070 | -0.073 | 0.015 | -0.056 | -0.132 | -0.061 | -0.095 |
| NZDCHF | 169.000 | 30.000 | -0.041 | -0.020 | -0.087 | -0.081 | -0.050 | -0.052 | -0.053 | -0.049 |
| AUDCHF | 158.000 | 29.000 | -0.131 | -0.090 | -0.173 | -0.112 | 0.050 | 0.065 | 0.059 | 0.065 |
| GBPJPY | 140.000 | 27.000 | -0.022 | -0.025 | -0.020 | 0.045 | -0.029 | -0.029 | -0.023 | -0.096 |
| EURJPY | 133.000 | 21.000 | 0.077 | 0.177 | 0.082 | 0.330 | -0.105 | -0.158 | -0.112 | -0.256 |
| CADJPY | 131.000 | 31.000 | -0.021 | 0.159 | -0.065 | 0.018 | -0.005 | -0.176 | -0.004 | -0.139 |
| GBPNZD | 127.000 | 14.000 | -0.022 | -0.118 | -0.040 | -0.043 | -0.060 | 0.039 | -0.090 | -0.091 |
| EURAUD | 121.000 | 26.000 | 0.071 | 0.017 | 0.070 | 0.106 | -0.113 | -0.035 | -0.125 | -0.109 |
| NZDCAD | 115.000 | 18.000 | -0.076 | 0.007 | -0.092 | -0.081 | -0.043 | -0.105 | -0.077 | -0.140 |
| GBPAUD | 112.000 | 16.000 | -0.027 | -0.158 | -0.049 | -0.152 | -0.014 | 0.101 | -0.004 | 0.090 |
| EURNZD | 110.000 | 15.000 | -0.094 | -0.093 | -0.122 | -0.162 | 0.022 | 0.004 | 0.021 | 0.049 |
| AUDCAD | 87.000 | 5.000 | -0.070 | -0.055 | -0.103 | 0.044 | -0.033 | -0.035 | -0.020 | -0.171 |
| CHFJPY | 69.000 | 9.000 | -0.131 | -0.109 | -0.150 | -0.143 | 0.042 | 0.058 | 0.044 | 0.075 |
| EURUSD | 55.000 | 4.000 | -0.059 | 0.410 | -0.042 | 0.566 | 0.033 | -0.622 | 0.016 | -0.877 |
| GBPUSD | 51.000 | 10.000 | 0.087 | 0.206 | 0.035 | 0.193 | -0.126 | -0.267 | -0.085 | -0.344 |
| USDCHF | 42.000 | 6.000 | -0.018 | -0.125 | -0.081 | -0.149 | -0.068 | 0.071 | -0.032 | 0.088 |
| CADCHF | 32.000 | 3.000 | 0.007 | -0.073 | -0.047 | -0.263 | -0.171 | -0.013 | -0.127 | 0.141 |
| USDCAD | 30.000 |  | 0.019 |  | -0.035 |  | -0.074 |  | -0.040 |  |
| GBPCAD | 28.000 | 2.000 | -0.088 | 0.529 | -0.046 | 0.878 | 0.045 | -0.415 | 0.037 | -0.387 |
| GBPCHF | 26.000 |  | 0.191 |  | 0.114 |  | -0.223 |  | -0.198 |  |
| EURCAD | 24.000 | 2.000 | 0.048 | -0.372 | 0.046 | -0.272 | -0.106 | 0.314 | -0.103 | 0.204 |
| EURGBP | 10.000 | 2.000 | -0.066 | 0.233 | -0.141 | 0.123 | 0.054 | -0.594 | 0.166 | -0.566 |
| EURCHF | 10.000 | 3.000 | 0.295 | 0.332 | 0.292 | 0.466 | -0.142 | -0.304 | -0.225 | -0.454 |

## Avg R by year

| year | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 |
|---|---|---|---|---|---|---|---|---|
| 2010 | -0.066 | -0.116 | -0.087 | -0.177 | -0.004 | 0.053 | -0.001 | 0.088 |
| 2011 | -0.041 | -0.083 | -0.068 | -0.081 | -0.012 | 0.019 | -0.018 | -0.026 |
| 2012 | -0.057 | 0.014 | -0.064 | 0.005 | -0.012 | -0.065 | -0.033 | -0.067 |
| 2013 | -0.058 | -0.115 | -0.068 | -0.084 | 0.005 | 0.053 | -0.011 | 0.033 |
| 2014 | 0.011 | 0.141 | -0.022 | 0.039 | -0.082 | -0.189 | -0.060 | -0.094 |
| 2015 | -0.040 | -0.026 | -0.053 | -0.016 | -0.023 | -0.008 | -0.041 | -0.029 |
| 2016 | -0.042 | 0.050 | -0.018 | 0.141 | -0.015 | -0.081 | -0.050 | -0.178 |
| 2017 | -0.022 | -0.048 | -0.031 | -0.068 | -0.035 | -0.008 | -0.039 | -0.023 |
| 2018 | -0.100 | -0.163 | -0.104 | -0.178 | 0.038 | 0.094 | 0.038 | 0.089 |
| 2019 | 0.013 | 0.037 | 0.025 | 0.043 | -0.077 | -0.109 | -0.082 | -0.108 |
| 2020 | -0.007 | 0.031 | -0.031 | -0.063 | -0.042 | -0.057 | -0.051 | -0.039 |
| 2021 | -0.045 | -0.091 | -0.057 | -0.084 | -0.008 | 0.046 | -0.018 | 0.038 |
| 2022 | -0.031 | -0.080 | -0.064 | -0.101 | -0.031 | 0.034 | -0.024 | 0.045 |
| 2023 | 0.001 | -0.081 | -0.006 | -0.071 | -0.049 | 0.035 | -0.060 | 0.008 |
| 2024 | -0.008 | -0.002 | -0.050 | -0.014 | -0.053 | -0.090 | -0.030 | -0.081 |
| 2025 | -0.034 | -0.039 | -0.022 | 0.021 | -0.023 | -0.003 | -0.044 | -0.073 |
| 2026 | -0.005 | -0.006 | -0.041 | 0.016 | -0.051 | -0.072 | -0.035 | -0.092 |

## Which currencies are the extremes (valid days)

| ccy | weakest W % | strongest S % |
|---|---|---|
| AUD | 20.4 | 19.5 |
| CAD | 5.2 | 5.4 |
| CHF | 7.0 | 5.0 |
| EUR | 5.2 | 5.8 |
| GBP | 6.0 | 5.9 |
| JPY | 22.0 | 24.1 |
| NZD | 19.7 | 21.1 |
| USD | 14.5 | 13.4 |

## Cross-check of the strength computation vs data/flow_series_v2.npz (Tue-Fri)

| ccy | days | corr | mean |s| (bp) | mean |flow| (bp) |
|---|---|---|---|---|
| AUD | 3433.000 | 0.974 | 18.456 | 17.786 |
| CAD | 3433.000 | 0.955 | 8.216 | 8.221 |
| CHF | 3433.000 | 0.926 | 9.236 | 9.014 |
| EUR | 3433.000 | 0.980 | 8.071 | 7.991 |
| GBP | 3433.000 | 0.846 | 8.223 | 7.882 |
| JPY | 3433.000 | 0.933 | 18.881 | 18.293 |
| NZD | 3433.000 | 0.971 | 18.838 | 18.308 |
| USD | 3433.000 | 0.993 | 11.926 | 11.858 |

## Overlap with the current prop basket (run_m3_addon.build_legs)

same UTC day = a basket trade is open at some time on the UTC date of our trade day; overlap = a basket trade is open during our holding period.

| variant | trades | vol-box same UTC day % | vol-box overlap % | vol-gotobi same UTC day % | vol-gotobi overlap % | fade same UTC day % | fade overlap % | M-3 USDJPY same UTC day % | M-3 USDJPY overlap % | M-3 other five same UTC day % | M-3 other five overlap % | any leg same UTC day % | any leg overlap % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 4215.0 | 46.2 | 40.8 | 11.7 | 0.0 | 41.1 | 32.9 | 4.4 | 4.4 | 4.4 | 4.4 | 69.8 | 63.4 |
| V2 | 913.0 | 53.1 | 45.2 | 12.9 | 0.0 | 42.2 | 31.8 | 3.8 | 3.7 | 3.8 | 3.7 | 74.3 | 65.6 |
| V3 | 4215.0 | 46.2 | 40.8 | 11.7 | 0.0 | 41.1 | 32.9 | 4.4 | 4.4 | 4.4 | 4.4 | 69.8 | 63.4 |
| V4 | 913.0 | 53.1 | 45.2 | 12.9 | 0.0 | 42.2 | 31.8 | 3.8 | 3.7 | 3.8 | 3.7 | 74.3 | 65.6 |
| V5 | 4215.0 | 46.2 | 40.8 | 11.7 | 0.0 | 41.1 | 32.9 | 4.4 | 4.4 | 4.4 | 4.4 | 69.8 | 63.4 |
| V6 | 913.0 | 53.1 | 45.2 | 12.9 | 0.0 | 42.2 | 31.8 | 3.8 | 3.8 | 3.8 | 3.8 | 74.3 | 65.6 |
| V7 | 4215.0 | 46.2 | 40.8 | 11.7 | 0.0 | 41.1 | 32.9 | 4.4 | 4.4 | 4.4 | 4.4 | 69.8 | 63.4 |
| V8 | 913.0 | 53.1 | 45.2 | 12.9 | 0.0 | 42.2 | 31.8 | 3.8 | 3.8 | 3.8 | 3.8 | 74.3 | 65.6 |


## Reading (written after the run)

**Verdict: no survivor (0 of 8; 0.05 expected by luck). The theory's main prediction also fails.**

- **There is no edge before costs.** Frictionless (mid-to-mid) avg R is between -0.006 and +0.008 in all 8 variants, with
  |t| <= 0.67. Reversal and momentum are both zero. Costs are about 3-4% of R (round-trip spread 1.6-2.7%, commission
  plus slippage 1.1-1.2%), roughly as the spec expected. The net result is therefore about -0.03 R per trade everywhere,
  and the design t values of -2 to -4 on the unfiltered variants measure the costs, not a reversed edge.
- **The concession does not grow with the imbalance.** Grossman-Miller predicts that reversal R rises with D. It does
  not. V1's top D_rel tercile (-0.037) is no better than the bottom one (-0.009). The top tercile is the worst one in
  the check period (-0.062). The F filter (top ~22% of days) makes reversal worse in the check period (V2 -0.061,
  V4 -0.081) and leaves the holdout at about 0.
- **Momentum (the competing hypothesis) fails too.** V6 and V8 are slightly positive in the check period and negative
  in design and holdout.
- **What the test actually traded.** With raw equal-weight log strength, the extreme currencies are almost always the
  high-volatility ones: AUD, NZD and JPY are W or S on 93% of days, and AUDJPY, NZDJPY, NZDUSD and AUDUSD take about
  half of all trades. The home-hours subset is therefore nearly the whole sample and gives the same answer.
- **No pair-level pocket.** 6-7 of 26 pairs are positive for the reversal variants (pairs with >= 20 trades), which is
  what noise gives around a slightly negative mean. EURJPY reversal (+0.08, 133 trades) is not a finding.
- **Strength computation checks out.** s_c sums to 0 within 1e-17. Its correlation with the flow-atlas 30-min strength
  over the same window is 0.85-0.99 (GBP lowest, mainly from clipping and NaN half-hours in the atlas series).
- **No prop sim**, because nothing survived. For reference, about 63-66% of the trades would have overlapped a
  basket trade, mostly the USDJPY vol-box and fade legs, which run in the same London morning.
- **Spec and compute.** No spec fixes were needed. Compute was 56 pair loads with Pool(2), about 3 minutes in total;
  no market was dropped. Days with no live tick at either stamp: 141 of 4,373 weekdays, mostly Mondays after
  holidays and Christmas/New Year. Daily_table warm-up removed 17 early-2010 days.

Files: tests.csv, home_subset.csv, terciles.csv, costs.csv, per_pair.csv, by_year.csv, basket_overlap.csv,
flow_crosscheck.csv, days.csv (per-day strengths, S, W, D, F, pair), trades.csv (all variants' trades), run.log.
