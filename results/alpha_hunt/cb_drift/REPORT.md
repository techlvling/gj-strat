# Central-bank decision-day drift in FX (cb_drift)

Script: `run_alpha_cb_drift.py` (every rule in its docstring, fixed before running). Costs in every R: $7/lot commission, 0.2 pip slippage per market/stop fill, swap (FRED rates +1%), real bid/ask fills.

**Survivors: 0 of 10 tests** (none); expected by luck 10 x 0.006 = 0.06.

Survival = pooled design 2010-17 month-clustered t >= 2 AND avg R > 0 in check 2018-23 AND in holdout 2024-26 (periods by event day t). Last 3 years = event days after 2023-10-07. 'banks positive' = banks with avg R > 0 over the whole sample (a trade labelled with two banks counts for both).

Banks used: FOMC, ECB, BoJ, BoE, BoC, RBA, SNB; pairs: EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCHF. Banks dropped (complete scheduled list incl. holds could not be assembled): RBNZ (RuntimeError: https://www.rbnz.govt.nz/monetary-policy/official-cash-rate-decisions: HTTP 403).

## Verdict

- No variant clears the bar. Best pooled design month-clustered t: 0.31 (D1 FOLLOW k=0.5 h=1 SL 1.0xATR); 2 of 10 variants have a positive full-sample avg R, the largest +0.023 R per trade.
- FOLLOW and FADE are near mirror images before costs (gross R sums -0.053 to -0.017 R = spread and stop asymmetry). The no-stop mid-price drift from 18:00 ET on the decision day to the exit is -0.104 to +0.030 ATR20 (|t| <= 1.48): no measurable continuation (under-reaction) or reversal (over-reaction) after a scheduled decision day.
- Commission, slippage and swap cost 0.017 R per trade on average on top of the spread.
- Per bank: 4 of 70 variant x bank cells are positive in all three periods; with no edge about 1/8 of cells (9) would be by chance, and the pooled tests above are the pre-declared ones.
- The |Rx|/ATR buckets and the rate-change / hold split are descriptive only (not tests); they show no monotone pattern that theory would predict (larger surprise -> more drift).

## All tests (pooled over banks and pairs, net R per trade)

| test | trades | trades/month | win % | avg win / avg loss | avg R | t | t (months) | design n | design avg R | design t | design t (months) | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | last3y t | banks positive | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 FOLLOW k=0.5 h=1 SL 1.0xATR | 642 | 3.246 | 50.935 | 1.030 | 0.018 | 0.649 | 0.603 | 332 | 0.012 | 0.337 | 0.313 | 207 | 0.031 | 0.656 | 103 | 0.008 | 0.102 | 115 | 0.021 | 0.266 | 4/7 | False |
| D2 FADE k=0.5 h=1 SL 1.0xATR | 642 | 3.246 | 44.081 | 1.024 | -0.058 | -2.077 | -1.909 | 332 | -0.048 | -1.298 | -1.213 | 207 | -0.088 | -1.908 | 103 | -0.028 | -0.328 | 115 | -0.033 | -0.418 | 0/7 | False |
| D3 FOLLOW k=0.5 h=3 SL 1.0xATR | 642 | 3.246 | 45.639 | 1.191 | -0.000 | -0.002 | -0.002 | 332 | -0.017 | -0.309 | -0.295 | 207 | -0.039 | -0.552 | 103 | 0.130 | 1.032 | 115 | 0.115 | 0.985 | 4/7 | False |
| D4 FADE k=0.5 h=3 SL 1.0xATR | 642 | 3.246 | 41.589 | 1.144 | -0.085 | -2.167 | -1.953 | 332 | -0.088 | -1.648 | -1.617 | 207 | -0.051 | -0.715 | 103 | -0.147 | -1.430 | 115 | -0.148 | -1.525 | 2/7 | False |
| D5 FOLLOW k=1.0 h=1 SL 1.0xATR | 291 | 1.478 | 46.392 | 0.972 | -0.047 | -1.180 | -1.108 | 150 | 0.020 | 0.348 | 0.302 | 97 | -0.074 | -1.090 | 44 | -0.214 | -2.256 | 50 | -0.209 | -2.161 | 1/7 | False |
| D6 FADE k=1.0 h=1 SL 1.0xATR | 291 | 1.478 | 49.828 | 0.921 | -0.024 | -0.606 | -0.548 | 150 | -0.058 | -1.062 | -0.912 | 97 | -0.008 | -0.115 | 44 | 0.056 | 0.498 | 50 | 0.079 | 0.734 | 3/7 | False |
| D7 FOLLOW k=1.0 h=3 SL 1.0xATR | 291 | 1.478 | 40.893 | 1.100 | -0.113 | -1.972 | -1.908 | 150 | -0.067 | -0.850 | -0.861 | 97 | -0.196 | -1.988 | 44 | -0.090 | -0.562 | 50 | -0.152 | -1.039 | 1/7 | False |
| D8 FADE k=1.0 h=3 SL 1.0xATR | 291 | 1.478 | 46.048 | 1.234 | 0.023 | 0.366 | 0.350 | 150 | -0.055 | -0.653 | -0.635 | 97 | 0.167 | 1.486 | 44 | -0.026 | -0.156 | 50 | 0.025 | 0.158 | 4/7 | False |
| D9 FOLLOW k=1.0 h=10 SL 2.0xATR | 291 | 1.478 | 45.361 | 0.980 | -0.079 | -1.494 | -1.508 | 150 | -0.003 | -0.041 | -0.046 | 97 | -0.151 | -1.661 | 44 | -0.178 | -1.530 | 50 | -0.159 | -1.419 | 1/7 | False |
| D10 FOLLOW every decision h=3 SL 1.0xATR | 1102 | 5.571 | 44.011 | 1.200 | -0.025 | -0.780 | -0.768 | 565 | 0.005 | 0.127 | 0.133 | 374 | -0.106 | -2.000 | 163 | 0.059 | 0.632 | 178 | 0.039 | 0.449 | 2/7 | False |

t = trade-level t; t (months) = month-clustered t (sum of R per calendar month). The survival bar uses design t (months).


## Banks positive per period (avg net R > 0)

| test | design banks positive | check banks positive | holdout banks positive | banks positive in all 3 periods |
|---|---|---|---|---|
| D1 | 4/7 | 4/7 | 3/7 | FOMC |
| D2 | 2/7 | 2/7 | 3/7 | - |
| D3 | 2/7 | 3/7 | 5/7 | BoJ |
| D4 | 3/7 | 2/7 | 1/7 | - |
| D5 | 5/7 | 3/7 | 2/7 | - |
| D6 | 3/7 | 2/7 | 4/7 | - |
| D7 | 3/7 | 2/7 | 4/7 | - |
| D8 | 4/7 | 6/7 | 2/7 | BoE |
| D9 | 3/7 | 3/7 | 4/7 | - |
| D10 | 4/7 | 1/7 | 4/7 | BoJ |

## Per bank (net R; trades labelled with two banks appear under both)

| variant | bank | trades | win % | avg R | t | design avg R | check avg R | holdout avg R |
|---|---|---|---|---|---|---|---|---|
| D1 | FOMC | 162 | 55.556 | 0.108 | 1.665 | 0.031 | 0.129 | 0.275 |
| D1 | ECB | 94 | 52.128 | 0.032 | 0.467 | 0.102 | -0.075 | -0.013 |
| D1 | BoJ | 92 | 47.826 | 0.011 | 0.183 | 0.069 | 0.049 | -0.269 |
| D1 | BoE | 79 | 53.165 | 0.007 | 0.080 | 0.052 | 0.082 | -0.219 |
| D1 | BoC | 78 | 50.000 | -0.051 | -0.731 | -0.048 | -0.150 | 0.139 |
| D1 | RBA | 103 | 45.631 | -0.014 | -0.246 | -0.052 | 0.101 | -0.196 |
| D1 | SNB | 40 | 47.500 | -0.089 | -1.022 | -0.228 | -0.033 | 0.094 |
| D2 | FOMC | 162 | 40.741 | -0.083 | -1.262 | -0.077 | -0.127 | -0.021 |
| D2 | ECB | 94 | 44.681 | -0.007 | -0.084 | -0.064 | 0.105 | -0.054 |
| D2 | BoJ | 92 | 44.565 | -0.118 | -1.797 | -0.127 | -0.195 | 0.061 |
| D2 | BoE | 79 | 45.570 | -0.020 | -0.273 | -0.045 | -0.060 | 0.100 |
| D2 | BoC | 78 | 44.872 | -0.058 | -0.808 | -0.052 | 0.033 | -0.261 |
| D2 | RBA | 103 | 44.660 | -0.058 | -0.982 | 0.019 | -0.221 | 0.098 |
| D2 | SNB | 40 | 47.500 | -0.050 | -0.594 | 0.128 | -0.148 | -0.252 |
| D3 | FOMC | 162 | 48.148 | 0.103 | 1.027 | -0.053 | 0.037 | 0.630 |
| D3 | ECB | 94 | 37.234 | -0.107 | -1.148 | -0.182 | -0.100 | 0.268 |
| D3 | BoJ | 92 | 52.174 | 0.142 | 1.250 | 0.146 | 0.176 | 0.060 |
| D3 | BoE | 79 | 43.038 | -0.098 | -0.891 | -0.021 | -0.080 | -0.314 |
| D3 | BoC | 78 | 43.590 | -0.126 | -1.238 | -0.067 | -0.329 | 0.073 |
| D3 | RBA | 103 | 47.573 | 0.012 | 0.127 | 0.155 | -0.080 | -0.348 |
| D3 | SNB | 40 | 47.500 | 0.025 | 0.186 | -0.285 | 0.306 | 0.247 |
| D4 | FOMC | 162 | 38.272 | -0.116 | -1.323 | -0.152 | -0.094 | -0.062 |
| D4 | ECB | 94 | 48.936 | 0.003 | 0.033 | 0.022 | 0.102 | -0.402 |
| D4 | BoJ | 92 | 32.609 | -0.178 | -1.671 | -0.220 | -0.162 | -0.057 |
| D4 | BoE | 79 | 49.367 | 0.011 | 0.099 | 0.014 | -0.060 | 0.113 |
| D4 | BoC | 78 | 48.718 | -0.077 | -0.746 | -0.147 | 0.108 | -0.201 |
| D4 | RBA | 103 | 36.893 | -0.120 | -1.294 | -0.099 | -0.059 | -0.407 |
| D4 | SNB | 40 | 37.500 | -0.118 | -0.876 | 0.197 | -0.359 | -0.397 |
| D5 | FOMC | 64 | 50.000 | 0.015 | 0.156 | 0.023 | 0.188 | -0.196 |
| D5 | ECB | 50 | 48.000 | -0.004 | -0.037 | 0.095 | -0.191 | -0.091 |
| D5 | BoJ | 46 | 50.000 | -0.034 | -0.367 | 0.154 | -0.116 | -0.264 |
| D5 | BoE | 41 | 43.902 | -0.065 | -0.543 | 0.019 | 0.019 | -0.365 |
| D5 | BoC | 40 | 47.500 | -0.058 | -0.627 | 0.058 | -0.262 | 0.467 |
| D5 | RBA | 36 | 36.111 | -0.098 | -1.201 | -0.084 | -0.049 | -0.408 |
| D5 | SNB | 17 | 47.059 | -0.193 | -1.292 | -0.511 | 0.060 | 0.146 |
| D6 | FOMC | 64 | 48.438 | -0.031 | -0.324 | -0.040 | -0.168 | 0.145 |
| D6 | ECB | 50 | 50.000 | 0.021 | 0.182 | -0.114 | 0.287 | 0.036 |
| D6 | BoJ | 46 | 45.652 | -0.143 | -1.540 | -0.237 | -0.037 | -0.115 |
| D6 | BoE | 41 | 56.098 | 0.052 | 0.524 | 0.039 | -0.034 | 0.212 |
| D6 | BoC | 40 | 47.500 | -0.076 | -0.761 | -0.170 | 0.100 | -0.583 |
| D6 | RBA | 36 | 52.778 | -0.006 | -0.068 | 0.040 | -0.175 | 0.418 |
| D6 | SNB | 17 | 47.059 | 0.033 | 0.228 | 0.406 | -0.314 | -0.266 |
| D7 | FOMC | 64 | 40.625 | -0.043 | -0.317 | -0.195 | 0.091 | 0.131 |
| D7 | ECB | 50 | 26.000 | -0.311 | -2.515 | -0.227 | -0.491 | -0.216 |
| D7 | BoJ | 46 | 47.826 | 0.071 | 0.420 | 0.156 | -0.011 | 0.027 |
| D7 | BoE | 41 | 39.024 | -0.193 | -1.218 | -0.156 | -0.028 | -0.523 |
| D7 | BoC | 40 | 47.500 | -0.042 | -0.317 | 0.197 | -0.458 | 0.974 |
| D7 | RBA | 36 | 50.000 | -0.029 | -0.165 | 0.205 | -0.257 | -0.593 |
| D7 | SNB | 17 | 47.059 | -0.098 | -0.392 | -0.630 | 0.251 | 0.622 |
| D8 | FOMC | 64 | 43.750 | -0.018 | -0.124 | -0.257 | 0.177 | 0.271 |
| D8 | ECB | 50 | 56.000 | 0.133 | 1.004 | 0.040 | 0.416 | -0.653 |
| D8 | BoJ | 46 | 34.783 | -0.106 | -0.611 | -0.219 | 0.067 | -0.138 |
| D8 | BoE | 41 | 53.659 | 0.156 | 0.902 | 0.202 | 0.047 | 0.235 |
| D8 | BoC | 40 | 47.500 | -0.138 | -0.925 | -0.383 | 0.268 | -1.024 |
| D8 | RBA | 36 | 36.111 | 0.032 | 0.179 | 0.084 | 0.072 | -0.492 |
| D8 | SNB | 17 | 47.059 | 0.115 | 0.433 | 0.700 | -0.277 | -0.663 |
| D9 | FOMC | 64 | 56.250 | 0.065 | 0.577 | 0.255 | -0.175 | -0.068 |
| D9 | ECB | 50 | 48.000 | -0.042 | -0.361 | 0.090 | -0.336 | 0.207 |
| D9 | BoJ | 46 | 45.652 | -0.041 | -0.244 | 0.061 | 0.073 | -0.381 |
| D9 | BoE | 41 | 34.146 | -0.263 | -2.246 | -0.326 | 0.012 | -0.566 |
| D9 | BoC | 40 | 42.500 | -0.161 | -1.245 | -0.181 | -0.169 | 0.122 |
| D9 | RBA | 36 | 38.889 | -0.104 | -0.648 | -0.038 | -0.275 | 0.195 |
| D9 | SNB | 17 | 47.059 | -0.055 | -0.250 | -0.415 | 0.091 | 0.613 |
| D10 | FOMC | 262 | 45.420 | 0.054 | 0.709 | 0.001 | -0.003 | 0.325 |
| D10 | ECB | 151 | 40.397 | -0.052 | -0.638 | -0.054 | -0.147 | 0.167 |
| D10 | BoJ | 166 | 46.386 | 0.055 | 0.674 | 0.089 | 0.007 | 0.007 |
| D10 | BoE | 158 | 42.405 | -0.091 | -1.109 | -0.048 | -0.134 | -0.169 |
| D10 | BoC | 132 | 45.455 | -0.083 | -1.042 | 0.038 | -0.231 | -0.102 |
| D10 | RBA | 174 | 45.977 | -0.019 | -0.251 | 0.097 | -0.107 | -0.206 |
| D10 | SNB | 66 | 37.879 | -0.161 | -1.517 | -0.292 | -0.234 | 0.365 |

## Per pair: avg net R

| pair | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD | -0.014 | -0.058 | 0.012 | -0.120 | -0.098 | -0.006 | -0.029 | 0.032 | -0.104 | -0.019 |
| EURUSD | 0.033 | -0.026 | -0.064 | -0.040 | -0.046 | 0.063 | -0.239 | 0.155 | 0.018 | -0.026 |
| GBPUSD | 0.007 | -0.020 | -0.098 | 0.011 | -0.065 | 0.052 | -0.193 | 0.156 | -0.263 | -0.091 |
| USDCAD | -0.051 | -0.058 | -0.126 | -0.077 | -0.058 | -0.076 | -0.042 | -0.138 | -0.161 | -0.083 |
| USDCHF | -0.089 | -0.050 | 0.025 | -0.118 | -0.193 | 0.033 | -0.098 | 0.115 | -0.055 | -0.161 |
| USDJPY | 0.085 | -0.114 | 0.167 | -0.157 | 0.032 | -0.173 | 0.004 | -0.157 | -0.038 | 0.067 |

## FOLLOW vs FADE mirror check

gross R = price R on bid/ask fills (spread paid) before commission, slippage and swap. The no-stop drift is the mid-price move from the entry minute to the exit minute in ATR20 units in the FOLLOW direction (all triggered events, no costs, no stop).

| pair | FOLLOW n | FADE n | FOLLOW gross R | FADE gross R | sum gross (spread drag) | FOLLOW net R | FADE net R | events | no-stop drift to the exit (ATR, follow dir.) | drift t |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 vs D2 (k=0.5, h=1) | 642.000 | 642.000 | 0.029 | -0.046 | -0.017 | 0.018 | -0.058 | 642.000 | 0.030 | 1.006 |
| D3 vs D4 (k=0.5, h=3) | 642.000 | 642.000 | 0.019 | -0.066 | -0.046 | -0.000 | -0.085 | 642.000 | 0.023 | 0.490 |
| D5 vs D6 (k=1.0, h=1) | 291.000 | 291.000 | -0.035 | -0.012 | -0.047 | -0.047 | -0.024 | 291.000 | -0.016 | -0.381 |
| D7 vs D8 (k=1.0, h=3) | 291.000 | 291.000 | -0.095 | 0.042 | -0.053 | -0.113 | 0.023 | 291.000 | -0.104 | -1.481 |

## Avg R by |Rx| / ATR20 bucket

D10 = FOLLOW every decision, h=3, SL 1xATR (net R). drift h = no-stop mid-price drift in the decision-day direction (ATR20 units, no costs) over all events in the bucket.

| |Rx|/ATR20 | D10 trades | D10 avg R | D10 t | D10 design avg R | D10 check avg R | D10 holdout avg R | events | drift h=1 | drift h=1 t | drift h=3 | drift h=3 t | drift h=10 | drift h=10 t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-0.25 | 227.000 | -0.092 | -1.361 | -0.003 | -0.180 | -0.252 | 227.000 | -0.045 | -0.840 | -0.073 | -0.888 | 0.059 | 0.347 |
| 0.25-0.5 | 233.000 | -0.027 | -0.374 | 0.082 | -0.199 | 0.053 | 233.000 | 0.004 | 0.073 | 0.003 | 0.030 | 0.026 | 0.196 |
| 0.5-1 | 351.000 | 0.094 | 1.627 | 0.025 | 0.100 | 0.295 | 351.000 | 0.068 | 1.600 | 0.129 | 2.043 | -0.143 | -1.285 |
| 1-1.5 | 176.000 | -0.248 | -3.598 | -0.361 | -0.125 | -0.144 | 176.000 | -0.086 | -1.623 | -0.242 | -2.835 | -0.233 | -1.452 |
| >=1.5 | 115.000 | 0.093 | 0.953 | 0.373 | -0.326 | -0.030 | 115.000 | 0.092 | 1.414 | 0.106 | 0.888 | 0.017 | 0.091 |

## Rate-change vs hold decisions (net R)

Change = policy rate (BIS WS_CBPOL daily; ECB deposit rate or MRO) differs between the day before the decision and up to 21 days after (capped before the bank's next decision of any kind).

| test | decision | trades | win % | avg R | t | design avg R | check avg R | holdout avg R |
|---|---|---|---|---|---|---|---|---|
| D1 | change | 122 | 50.820 | 0.019 | 0.342 | 0.069 | -0.055 | 0.098 |
| D1 | hold | 520 | 50.962 | 0.017 | 0.559 | 0.005 | 0.063 | -0.029 |
| D2 | change | 122 | 44.262 | -0.076 | -1.305 | -0.122 | 0.008 | -0.177 |
| D2 | hold | 520 | 44.038 | -0.054 | -1.697 | -0.039 | -0.124 | 0.033 |
| D3 | change | 122 | 50.000 | 0.063 | 0.729 | 0.277 | -0.188 | 0.275 |
| D3 | hold | 520 | 44.615 | -0.015 | -0.321 | -0.052 | 0.017 | 0.071 |
| D4 | change | 122 | 35.246 | -0.155 | -1.655 | -0.406 | 0.064 | -0.262 |
| D4 | hold | 520 | 43.077 | -0.069 | -1.591 | -0.049 | -0.093 | -0.100 |
| D5 | change | 66 | 45.455 | -0.065 | -0.910 | 0.133 | -0.194 | -0.150 |
| D5 | hold | 225 | 46.667 | -0.042 | -0.884 | -0.002 | -0.027 | -0.248 |
| D6 | change | 66 | 46.970 | -0.029 | -0.416 | -0.207 | 0.086 | 0.047 |
| D6 | hold | 225 | 50.667 | -0.022 | -0.478 | -0.030 | -0.044 | 0.061 |
| D7 | change | 66 | 45.455 | -0.000 | -0.000 | 0.275 | -0.245 | 0.000 |
| D7 | hold | 225 | 39.556 | -0.147 | -2.270 | -0.132 | -0.177 | -0.136 |
| D8 | change | 66 | 37.879 | -0.019 | -0.141 | -0.388 | 0.238 | 0.107 |
| D8 | hold | 225 | 48.444 | 0.036 | 0.499 | 0.008 | 0.140 | -0.096 |
| D9 | change | 66 | 46.970 | 0.005 | 0.041 | 0.274 | -0.318 | 0.154 |
| D9 | hold | 225 | 44.889 | -0.103 | -1.715 | -0.056 | -0.086 | -0.350 |
| D10 | change | 202 | 47.030 | 0.069 | 0.902 | 0.293 | -0.090 | 0.159 |
| D10 | hold | 900 | 43.333 | -0.046 | -1.320 | -0.021 | -0.112 | 0.005 |

Decisions by type:

| bank | change | hold |
|---|---|---|
| BoC | 29 | 105 |
| BoE | 23 | 138 |
| BoJ | 8 | 161 |
| ECB | 32 | 122 |
| FOMC | 30 | 103 |
| RBA | 40 | 136 |
| SNB | 11 | 56 |

## Event coverage

| bank | pairs | decisions | first | last | rate changes | events with a session + entry | D1 trades | D5 trades | D10 trades |
|---|---|---|---|---|---|---|---|---|---|
| FOMC | EURUSD+USDJPY | 133 | 2010-01-27 | 2026-09-16 | 30 | 262 | 162 | 64 | 262 |
| ECB | EURUSD | 154 | 2010-01-14 | 2026-09-10 | 32 | 151 | 94 | 50 | 151 |
| BoJ | USDJPY | 169 | 2010-01-26 | 2026-09-18 | 8 | 166 | 92 | 46 | 166 |
| BoE | GBPUSD | 161 | 2010-01-07 | 2026-09-17 | 23 | 158 | 79 | 41 | 158 |
| BoC | USDCAD | 134 | 2010-01-19 | 2026-09-02 | 29 | 132 | 78 | 40 | 132 |
| RBA | AUDUSD | 176 | 2010-02-02 | 2026-09-29 | 40 | 174 | 103 | 36 | 174 |
| SNB | USDCHF | 67 | 2010-03-11 | 2026-09-24 | 11 | 66 | 40 | 17 | 66 |

Scheduled decisions per year (from the scraped lists; used to check completeness):
| year | BoC | BoE | BoJ | ECB | FOMC | RBA | SNB |
|---|---|---|---|---|---|---|---|
| 2010 | 8 | 12 | 14 | 12 | 8 | 11 | 4 |
| 2011 | 8 | 12 | 14 | 12 | 8 | 11 | 4 |
| 2012 | 8 | 12 | 14 | 12 | 8 | 11 | 4 |
| 2013 | 8 | 12 | 14 | 12 | 8 | 11 | 4 |
| 2014 | 8 | 12 | 14 | 12 | 8 | 11 | 4 |
| 2015 | 8 | 12 | 14 | 8 | 8 | 11 | 4 |
| 2016 | 8 | 11 | 8 | 8 | 8 | 11 | 4 |
| 2017 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2018 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2019 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2020 | 8 | 8 | 7 | 8 | 7 | 11 | 4 |
| 2021 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2022 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2023 | 8 | 8 | 8 | 8 | 8 | 11 | 4 |
| 2024 | 8 | 8 | 8 | 8 | 8 | 8 | 4 |
| 2025 | 8 | 8 | 8 | 8 | 8 | 8 | 4 |
| 2026 | 6 | 6 | 6 | 6 | 6 | 6 | 3 |


Same-pair same-day events traded once with both labels: 7 (USDJPY 2010-08-10 BoJ+FOMC, USDJPY 2012-03-13 BoJ+FOMC, USDJPY 2014-04-30 BoJ+FOMC, USDJPY 2016-09-21 BoJ+FOMC, USDJPY 2021-09-22 BoJ+FOMC, USDJPY 2024-07-31 BoJ+FOMC, USDJPY 2025-03-19 BoJ+FOMC).

Skipped events: 18 (see skipped_events.csv; mostly decisions before the daily_table warm-up in early 2010). Time exits on a stale minute (no ticks in the exit minute and the 4 before): D3 4, D4 3, D7 2, D10 8.


## Sources

data/extra/cb_decisions.csv (bank, date, release_time_local, tz, release_utc, pair, source_url); every scraped item incl. excluded ones with the reason in cb_calendar_raw.csv; FOMC from data/extra/fomc_dates.csv (fomc_cycle run). Pages: ECB https://www.ecb.europa.eu/press/govcdec/mopo/<YYYY>/html/index_include.en.html; BoJ https://www.boj.or.jp/en/mopo/mpmsche_minu/past.htm + index.htm; BoE https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes (listing API); BoC https://www.bankofcanada.ca/press/press-releases/?mt_page=N; RBA https://www.rba.gov.au/monetary-policy/int-rate-decisions/<YYYY>/; SNB https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions; RBNZ https://www.rbnz.govt.nz/monetary-policy/official-cash-rate-decisions.


Files: summary.csv, per_bank.csv, trades.csv, events.csv, skipped_events.csv, cb_calendar_raw.csv, decisions_per_year.csv.


## Prop sim

Not run: no variant survived. Best design t (months): D1 FOLLOW k=0.5 h=1 SL 1.0xATR.
