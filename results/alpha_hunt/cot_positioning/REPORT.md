# Alpha hunt: CFTC positioning (cot_positioning)

Script: `run_alpha_cot_positioning.py` (rules fixed in its docstring before the first run). Markets: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCHF, USDCAD (CME currency futures positioning mapped to spot) and XAUUSD (COMEX gold). CFTC Legacy Futures-Only reports 2005-2026, trades from 2010. Costs included everywhere (commission 7/lot, 0.2 pip slippage per stop fill, swap at FRED rates +1% markup; gold: run_all_matrix.net_r).

**Survivors (design t >= 2, check avg R > 0, holdout avg R > 0): none** of 8 pooled tests. Luck alone: 8 x 0.006 = 0.05 (about 0.2 counting the 32 per-market cells).

## Pooled results per variant

| variant | name | trades | trades/month | win % | avg win/avg loss | avg R | t | month t | design n | design avg R | design t | design month t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | markets avg R > 0 | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | P1 crowding 156w 90/10 | 569 | 2.859 | 46.573 | 1.193 | 0.017 | 0.391 | 0.396 | 300 | -0.038 | -0.647 | -0.641 | 169 | 0.078 | 0.919 | 100 | 0.080 | 0.683 | 107 | 0.168 | 1.426 | 4 | no |
| P2 | P2 crowding 156w 95/5 | 380 | 1.910 | 44.474 | 1.170 | -0.028 | -0.545 | -0.501 | 202 | -0.075 | -1.144 | -0.921 | 105 | 0.034 | 0.321 | 73 | 0.012 | 0.094 | 77 | 0.086 | 0.681 | 3 | no |
| P3 | P3 crowding 52w 90/10 | 847 | 4.256 | 47.107 | 1.146 | 0.009 | 0.244 | 0.211 | 433 | 0.013 | 0.248 | 0.211 | 290 | -0.005 | -0.078 | 124 | 0.028 | 0.295 | 136 | 0.126 | 1.334 | 5 | no |
| P4 | P4 P1 + VIX rising | 379 | 1.905 | 45.383 | 1.250 | 0.017 | 0.306 | 0.294 | 196 | -0.026 | -0.359 | -0.317 | 115 | 0.079 | 0.753 | 68 | 0.036 | 0.260 | 71 | 0.078 | 0.557 | 5 | no |
| P5 | P5 hedging pressure 1w | 3272 | 16.442 | 47.066 | 0.975 | -0.041 | -3.302 | -3.900 | 1596 | -0.045 | -2.573 | -3.206 | 1172 | -0.034 | -1.604 | 504 | -0.041 | -1.410 | 552 | -0.041 | -1.454 | 2 | no |
| P6 | P6 hedging pressure 4w cohorts | 816 | 4.101 | 40.319 | 1.168 | -0.102 | -2.823 | -3.063 | 400 | -0.113 | -2.218 | -2.457 | 292 | -0.079 | -1.264 | 124 | -0.119 | -1.358 | 136 | -0.106 | -1.278 | 2 | no |
| P7 | P7 flow reversal (KRT) 1w | 3272 | 16.442 | 49.205 | 1.014 | -0.005 | -0.410 | -0.467 | 1596 | -0.018 | -0.973 | -1.167 | 1172 | 0.008 | 0.371 | 504 | 0.005 | 0.153 | 552 | 0.014 | 0.454 | 2 | no |
| P8 | P8 flow continuation 1w | 3272 | 16.442 | 46.944 | 0.994 | -0.036 | -2.961 | -3.664 | 1596 | -0.024 | -1.363 | -1.735 | 1172 | -0.046 | -2.234 | 504 | -0.054 | -1.683 | 552 | -0.060 | -1.965 | 0 | no |

`t` = trade-level t; `month t` = t of the monthly sum of R (0 for empty months), which allows for the correlation between legs entered in the same week. Last 3 years = entries after 2023-10-07.

### Swap and stops

| variant | avg R | avg R swap0 | design avg R swap0 | check avg R swap0 | holdout avg R swap0 | SL % |
|---|---|---|---|---|---|---|
| P1 | 0.017 | 0.057 | -0.010 | 0.127 | 0.141 | 36.555 |
| P2 | -0.028 | 0.008 | -0.049 | 0.075 | 0.072 | 37.105 |
| P3 | 0.009 | 0.047 | 0.047 | 0.034 | 0.083 | 35.183 |
| P4 | 0.017 | 0.055 | 0.001 | 0.125 | 0.092 | 35.356 |
| P5 | -0.041 | -0.029 | -0.034 | -0.020 | -0.029 | 16.870 |
| P6 | -0.102 | -0.069 | -0.083 | -0.042 | -0.085 | 39.828 |
| P7 | -0.005 | 0.007 | -0.007 | 0.021 | 0.018 | 16.718 |
| P8 | -0.036 | -0.025 | -0.013 | -0.034 | -0.042 | 16.718 |

### Gross of costs (price R only, before commission, slippage and swap; descriptive, not a test)

| variant | price R | t | design price R | design t | check price R | check t | holdout price R | holdout t |
|---|---|---|---|---|---|---|---|---|
| P1 | 0.062 | 1.364 | -0.006 | -0.106 | 0.132 | 1.529 | 0.146 | 1.236 |
| P2 | 0.013 | 0.248 | -0.045 | -0.688 | 0.080 | 0.737 | 0.078 | 0.616 |
| P3 | 0.052 | 1.413 | 0.051 | 0.990 | 0.039 | 0.610 | 0.088 | 0.909 |
| P4 | 0.060 | 1.066 | 0.005 | 0.068 | 0.130 | 1.217 | 0.097 | 0.702 |
| P5 | -0.022 | -1.822 | -0.029 | -1.648 | -0.014 | -0.651 | -0.021 | -0.733 |
| P6 | -0.064 | -1.755 | -0.079 | -1.524 | -0.037 | -0.586 | -0.079 | -0.907 |
| P7 | 0.013 | 1.016 | -0.002 | -0.086 | 0.027 | 1.306 | 0.026 | 0.789 |
| P8 | -0.019 | -1.522 | -0.008 | -0.440 | -0.027 | -1.305 | -0.035 | -1.079 |

## Reading

- Crowding (P1-P4): design avg R -0.038 / -0.075 / 0.013 / -0.026 (t -0.65 / -1.14 / 0.25 / -0.36). Check and holdout avg R range from -0.005 to 0.080, with |t| <= 0.92, and per-market signs are mixed. Fading speculator extremes is a bet against 63-day momentum (only 16% of P1 trades go with it), and over 4-week holds it pays about 0.04R of swap per trade.
- Hedging pressure (P5, P6) has the wrong sign in every period: P5 avg R -0.041 (t -3.30; design t -2.57), gross price R -0.022 (gross t -1.82: about half of the net t comes from costs and swap). Going long the currencies whose commercials are unusually net short means going with speculators. 65% of P5 legs go with 63-day momentum (corr with FX momentum M2 0.31). The mirror was not pre-declared. Its gross edge (about 0.022R per leg) is about the size of the weekly cost and swap drag (about 0.018R), so it is not an edge either.
- Short-term flow: the Kang-Rouwenhorst-Tang sign is right before costs (P7 gross 0.013R, t 1.02; P8 gross -0.019R), but with a 2 x ATR20 stop (about 150-220 pips) one week of drift is a few pips, and costs and swap remove it (P7 net -0.005R).
- No variant copies carry or FX momentum (max |corr| 0.31) or the current basket (max |corr| 0.09). The positioning signal is new information, but none of these rules turns it into an edge after costs.

## Per market (avg R per period)

| variant / market | sym | trades | avg R | t | design avg R | design t | check avg R | holdout avg R | last3y avg R |
|---|---|---|---|---|---|---|---|---|---|
| P1 AUD | AUDUSD | 79 | -0.012 | -0.102 | -0.029 | -0.177 | -0.187 | 0.221 | 0.221 |
| P1 CAD | USDCAD | 61 | 0.216 | 1.513 | 0.309 | 1.778 | 0.459 | -0.266 | -0.120 |
| P1 CHF | USDCHF | 75 | -0.066 | -0.502 | -0.205 | -1.071 | -0.169 | 0.830 | 0.883 |
| P1 EUR | EURUSD | 57 | -0.234 | -1.926 | -0.268 | -1.944 | -0.294 | 0.051 | 0.051 |
| P1 GBP | GBPUSD | 67 | 0.024 | 0.208 | -0.142 | -1.044 | 0.224 | 0.134 | 0.134 |
| P1 GOLD | XAUUSD | 81 | -0.018 | -0.144 | 0.028 | 0.173 | 0.039 | -0.280 | -0.052 |
| P1 JPY | USDJPY | 86 | 0.012 | 0.097 | -0.125 | -0.818 | 0.304 | -0.034 | 0.109 |
| P1 NZD | NZDUSD | 63 | 0.236 | 1.718 | 0.208 | 1.088 | 0.278 | 0.206 | 0.363 |
| P2 AUD | AUDUSD | 54 | -0.007 | -0.054 | 0.030 | 0.164 | -0.289 | 0.110 | 0.110 |
| P2 CAD | USDCAD | 42 | 0.159 | 0.915 | 0.168 | 0.784 | 0.540 | -0.122 | -0.003 |
| P2 CHF | USDCHF | 47 | -0.120 | -0.934 | -0.232 | -1.354 | -0.224 | 0.498 | 0.498 |
| P2 EUR | EURUSD | 42 | -0.276 | -2.022 | -0.343 | -2.132 | -0.016 | -0.253 | -0.253 |
| P2 GBP | GBPUSD | 46 | 0.046 | 0.323 | -0.165 | -1.045 | 0.361 | 0.094 | 0.094 |
| P2 GOLD | XAUUSD | 53 | -0.010 | -0.070 | 0.115 | 0.650 | 0.027 | -0.504 | -0.395 |
| P2 JPY | USDJPY | 59 | -0.052 | -0.383 | -0.101 | -0.578 | 0.008 | -0.004 | 0.168 |
| P2 NZD | NZDUSD | 37 | 0.049 | 0.280 | -0.106 | -0.443 | 0.128 | 0.265 | 0.480 |
| P3 AUD | AUDUSD | 109 | 0.083 | 0.686 | 0.118 | 0.693 | -0.131 | 0.387 | 0.409 |
| P3 CAD | USDCAD | 92 | 0.090 | 0.846 | 0.069 | 0.492 | 0.215 | -0.143 | -0.042 |
| P3 CHF | USDCHF | 102 | -0.067 | -0.621 | -0.203 | -1.308 | -0.034 | 0.417 | 0.484 |
| P3 EUR | EURUSD | 132 | -0.246 | -3.266 | -0.207 | -1.712 | -0.284 | -0.277 | -0.203 |
| P3 GBP | GBPUSD | 110 | -0.101 | -1.122 | -0.127 | -1.063 | -0.211 | 0.376 | 0.410 |
| P3 GOLD | XAUUSD | 112 | 0.080 | 0.732 | 0.209 | 1.460 | 0.106 | -0.441 | -0.233 |
| P3 JPY | USDJPY | 102 | 0.117 | 1.110 | 0.101 | 0.713 | 0.278 | -0.107 | 0.012 |
| P3 NZD | NZDUSD | 88 | 0.224 | 2.029 | 0.254 | 1.657 | 0.169 | 0.283 | 0.444 |
| P4 AUD | AUDUSD | 50 | 0.030 | 0.188 | -0.021 | -0.096 | -0.083 | 0.325 | 0.325 |
| P4 CAD | USDCAD | 40 | 0.331 | 1.785 | 0.498 | 1.990 | 0.379 | -0.138 | -0.097 |
| P4 CHF | USDCHF | 42 | 0.151 | 0.819 | 0.018 | 0.066 | 0.190 | 0.545 | 0.545 |
| P4 EUR | EURUSD | 37 | -0.286 | -2.028 | -0.355 | -2.215 | -0.126 | -0.194 | -0.194 |
| P4 GBP | GBPUSD | 49 | -0.083 | -0.710 | -0.086 | -0.522 | -0.069 | -0.097 | -0.097 |
| P4 GOLD | XAUUSD | 56 | -0.132 | -0.856 | -0.114 | -0.648 | -0.001 | -0.612 | -0.171 |
| P4 JPY | USDJPY | 58 | 0.011 | 0.076 | -0.272 | -1.764 | 0.469 | 0.167 | 0.167 |
| P4 NZD | NZDUSD | 47 | 0.144 | 0.912 | 0.247 | 1.087 | -0.023 | 0.294 | 0.294 |
| P5 AUD | AUDUSD | 441 | -0.041 | -1.270 | -0.126 | -2.614 | 0.064 | -0.058 | -0.033 |
| P5 CAD | USDCAD | 501 | -0.081 | -2.705 | -0.038 | -0.801 | -0.183 | 0.044 | 0.012 |
| P5 CHF | USDCHF | 400 | 0.021 | 0.568 | 0.016 | 0.335 | 0.069 | -0.162 | -0.162 |
| P5 EUR | EURUSD | 440 | 0.005 | 0.150 | -0.029 | -0.585 | 0.037 | 0.051 | 0.080 |
| P5 GBP | GBPUSD | 527 | -0.075 | -2.548 | -0.093 | -2.265 | -0.076 | -0.025 | -0.011 |
| P5 JPY | USDJPY | 509 | -0.002 | -0.050 | -0.001 | -0.021 | 0.026 | -0.051 | -0.065 |
| P5 NZD | NZDUSD | 454 | -0.097 | -2.982 | -0.058 | -1.259 | -0.134 | -0.150 | -0.180 |
| P6 AUD | AUDUSD | 113 | -0.111 | -1.170 | -0.336 | -2.919 | 0.224 | -0.294 | -0.267 |
| P6 CAD | USDCAD | 129 | -0.220 | -2.828 | -0.180 | -1.444 | -0.386 | 0.051 | -0.037 |
| P6 CHF | USDCHF | 99 | 0.042 | 0.357 | 0.055 | 0.333 | 0.125 | -0.356 | -0.356 |
| P6 EUR | EURUSD | 110 | -0.077 | -0.747 | -0.036 | -0.256 | -0.179 | 0.072 | 0.165 |
| P6 GBP | GBPUSD | 130 | -0.227 | -2.834 | -0.258 | -2.319 | -0.281 | -0.028 | 0.041 |
| P6 JPY | USDJPY | 122 | 0.100 | 0.903 | 0.069 | 0.464 | 0.311 | -0.190 | -0.190 |
| P6 NZD | NZDUSD | 113 | -0.182 | -2.162 | -0.130 | -1.044 | -0.258 | -0.206 | -0.234 |
| P7 AUD | AUDUSD | 446 | -0.036 | -1.073 | -0.047 | -0.957 | 0.007 | -0.113 | -0.108 |
| P7 CAD | USDCAD | 455 | -0.012 | -0.400 | -0.044 | -1.025 | 0.018 | 0.014 | 0.048 |
| P7 CHF | USDCHF | 482 | -0.006 | -0.163 | 0.007 | 0.107 | -0.043 | 0.040 | 0.020 |
| P7 EUR | EURUSD | 474 | 0.028 | 0.852 | 0.040 | 0.853 | 0.029 | -0.011 | -0.001 |
| P7 GBP | GBPUSD | 484 | -0.019 | -0.591 | -0.022 | -0.484 | -0.014 | -0.021 | -0.014 |
| P7 JPY | USDJPY | 500 | 0.041 | 1.159 | -0.031 | -0.652 | 0.069 | 0.209 | 0.197 |
| P7 NZD | NZDUSD | 431 | -0.039 | -1.205 | -0.033 | -0.751 | -0.013 | -0.105 | -0.062 |
| P8 AUD | AUDUSD | 446 | -0.003 | -0.101 | 0.021 | 0.434 | -0.060 | 0.067 | 0.073 |
| P8 CAD | USDCAD | 455 | -0.049 | -1.555 | -0.002 | -0.049 | -0.090 | -0.097 | -0.128 |
| P8 CHF | USDCHF | 482 | -0.015 | -0.461 | -0.042 | -0.933 | 0.053 | -0.092 | -0.066 |
| P8 EUR | EURUSD | 474 | -0.054 | -1.651 | -0.075 | -1.599 | -0.041 | -0.018 | -0.024 |
| P8 GBP | GBPUSD | 484 | -0.043 | -1.405 | -0.032 | -0.752 | -0.037 | -0.094 | -0.098 |
| P8 JPY | USDJPY | 500 | -0.061 | -1.884 | -0.003 | -0.072 | -0.102 | -0.153 | -0.154 |
| P8 NZD | NZDUSD | 431 | -0.025 | -0.746 | -0.027 | -0.573 | -0.047 | 0.022 | -0.013 |

## Diagnostics

| variant | higher-yield side % | lower-yield side % | with 63d momentum % | corr carry C1 | corr mom63 M2 | corr basket | months corr | VIX-rise months n | VIX-rise months avg R | other months avg R | USDJPY legs | USDJPY avg R | price R | swap R | cost R | ex-gold avg R | ex-gold design t | ex-gold check avg R | ex-gold holdout avg R | copy flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 45.492 | 51.230 | 16.158 | 0.064 | -0.160 | -0.053 | 198 | 87 | -0.080 | 0.035 | 86 | 0.012 | 0.062 | -0.040 | 0.005 | 0.023 | -0.763 | 0.086 | 0.134 |  |
| P2 | 49.235 | 47.401 | 12.973 | 0.050 | -0.157 | -0.080 | 198 | 58 | -0.052 | -0.024 | 59 | -0.052 | 0.013 | -0.036 | 0.005 | -0.031 | -1.463 | 0.036 | 0.075 |  |
| P3 | 46.803 | 48.844 | 16.848 | -0.032 | -0.153 | -0.004 | 198 | 122 | 0.161 | -0.017 | 102 | 0.117 | 0.052 | -0.039 | 0.005 | -0.002 | -0.317 | -0.022 | 0.098 |  |
| P4 | 47.678 | 49.536 | 14.247 | -0.005 | -0.216 | -0.058 | 198 | 86 | 0.014 | 0.018 | 58 | 0.011 | 0.060 | -0.038 | 0.005 | 0.043 | -0.152 | 0.098 | 0.110 |  |
| P5 | 50.000 | 47.555 | 64.689 | -0.007 | 0.312 | 0.012 | 198 | 436 | -0.036 | -0.041 | 509 | -0.002 | -0.022 | -0.012 | 0.006 |  |  |  |  |  |
| P6 | 49.632 | 47.917 | 65.672 | 0.080 | 0.127 | 0.025 | 198 | 112 | -0.061 | -0.108 | 122 | 0.100 | -0.064 | -0.033 | 0.005 |  |  |  |  |  |
| P7 | 48.930 | 47.891 | 43.571 | -0.162 | -0.047 | 0.086 | 198 | 436 | 0.023 | -0.010 | 500 | 0.041 | 0.013 | -0.012 | 0.006 |  |  |  |  |  |
| P8 | 47.891 | 48.930 | 56.429 | 0.038 | 0.015 | -0.037 | 198 | 436 | -0.004 | -0.041 | 500 | -0.061 | -0.019 | -0.011 | 0.006 |  |  |  |  |  |

Higher-/lower-yield side: FX trades only (gold excluded); the rest had equal policy rates. Correlations use monthly sums of R vs fx_carry C1 (plain G8 carry k=2), fx_value_mom M2 (63-day cross-sectional momentum k=2) and the current basket's monthly % (vol-box, gotobi, fade, M-3); `copy flag` marks |corr| >= 0.5. VIX-rise months: the month's last VIXCLS value > 1.3 x the previous month's. Price/swap/cost R: mean per trade (net R = price + swap - cost).

## Avg R by entry year

| year | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 |
|---|---|---|---|---|---|---|---|---|
| 2010 | -0.070 | -0.114 | 0.074 | -0.134 | -0.095 | -0.240 | -0.052 | 0.020 |
| 2011 | 0.005 | -0.109 | 0.007 | -0.005 | -0.061 | -0.164 | 0.019 | -0.056 |
| 2012 | 0.082 | -0.112 | -0.091 | -0.250 | -0.037 | -0.192 | -0.065 | 0.002 |
| 2013 | -0.072 | -0.099 | -0.063 | -0.266 | -0.009 | -0.017 | -0.075 | 0.036 |
| 2014 | -0.194 | -0.519 | -0.175 | 0.114 | -0.021 | 0.070 | -0.001 | -0.046 |
| 2015 | -0.045 | 0.133 | 0.208 | 0.022 | -0.021 | -0.076 | 0.048 | -0.048 |
| 2016 | -0.170 | -0.214 | -0.089 | 0.154 | -0.076 | -0.252 | -0.001 | -0.080 |
| 2017 | 0.072 | 0.160 | 0.246 | 0.184 | -0.048 | -0.056 | -0.031 | -0.001 |
| 2018 | 0.034 | 0.058 | -0.145 | 0.089 | -0.063 | -0.127 | -0.053 | -0.009 |
| 2019 | 0.385 | 0.443 | -0.155 | 0.397 | -0.080 | -0.335 | -0.033 | -0.037 |
| 2020 | -0.365 | -0.241 | 0.116 | -0.289 | 0.040 | 0.098 | 0.112 | -0.063 |
| 2021 | 0.230 | 0.371 | 0.014 | 0.178 | -0.068 | -0.125 | 0.011 | -0.056 |
| 2022 | 0.018 | -0.447 | -0.117 | 0.134 | 0.011 | -0.007 | -0.042 | -0.005 |
| 2023 | 0.569 | 0.532 | 0.263 | 0.308 | -0.054 | -0.011 | 0.049 | -0.113 |
| 2024 | -0.011 | 0.010 | 0.013 | -0.047 | -0.022 | -0.213 | 0.044 | -0.075 |
| 2025 | 0.066 | -0.193 | -0.107 | 0.250 | -0.074 | -0.048 | -0.081 | -0.016 |
| 2026 | 0.364 | 0.316 | 0.196 | -0.049 | -0.034 | -0.053 | 0.043 | -0.064 |

## Release dates and exclusions

- Official-date check: the rule used (3rd US federal business day after T, 15:30 ET) matches 76 of 76 official dates found on cftc.gov; the pre-declared T+3 rule matches 64. Mismatches of the rule used: 0.
- Tradeable reports 2010-2026: 830. R differs from the pre-declared rule for 44; in 44 of them the pre-declared rule would have entered on or before the official release day (look-ahead) - these are Wednesday/Thursday-holiday weeks and Monday as-of dates.
- Not traded (published late in catch-up): 2013 shutdown: 7 reports, T 2013-10-01 .. 2013-11-12; 2018-19 shutdown: 12 reports, T 2018-12-18 .. 2019-03-05; 2023 ION incident: 8 reports, T 2023-01-31 .. 2023-03-21; 2025 shutdown: 18 reports, T 2025-09-30 .. 2026-01-27.
- Entry/exit minutes moved to the next weekday because 07:00-08:00 London had no ticks: 32 market-weeks (holidays such as 25 Dec / 1 Jan).
- Legs not simulated: exit after data end: 41, no ATR20 (warm-up): 193, no entry minute: 21.

## Data

`cot_features.csv` (SP, HP, pct156, pct52, zHP, dSP, zdSP per market and report, with release date, entry date, tradeable flag and the P4 VIX gate), `trades.csv` (every simulated leg with R, R at zero swap, swap R, side, yield side, momentum alignment), `summary.csv`, `per_market.csv`, `diagnostics.csv`, `release_check.csv`, `skipped.csv`.
