# Your boxes on all 31 markets, 2010–2026

Rules in run_boxes_all.py (fixed before running). 372 tests; about 2 survivors expected by luck.

**Survivors: 0**

None.

## Each box and setting across the 31 markets

|  | markets | markets positive all 3 periods | avg R 2010-17 (mean) | avg R 2018-23 (mean) | avg R 2024-26 (mean) | survivors |
|---|---|---|---|---|---|---|
| ('A 04:30-05:15 IST', 'RR 2, no BE') | 31.000 | 0.000 | -0.316 | -0.302 | -0.298 | 0.000 |
| ('A 04:30-05:15 IST', 'green rules (RR 9, BE 3R)') | 31.000 | 0.000 | -0.334 | -0.324 | -0.319 | 0.000 |
| ('A 04:30-05:15 IST', 'green rules + vol filter') | 31.000 | 0.000 | -0.319 | -0.294 | -0.275 | 0.000 |
| ('B 12:30-14:00 IST', 'RR 2, no BE') | 31.000 | 0.000 | -0.102 | -0.126 | -0.223 | 0.000 |
| ('B 12:30-14:00 IST', 'green rules (RR 9, BE 3R)') | 31.000 | 2.000 | -0.095 | -0.152 | -0.286 | 0.000 |
| ('B 12:30-14:00 IST', 'green rules + vol filter') | 31.000 | 2.000 | -0.115 | -0.165 | -0.267 | 0.000 |
| ("B' London 08:00-09:30 (DST)", 'RR 2, no BE') | 31.000 | 0.000 | -0.104 | -0.135 | -0.235 | 0.000 |
| ("B' London 08:00-09:30 (DST)", 'green rules (RR 9, BE 3R)') | 31.000 | 1.000 | -0.100 | -0.161 | -0.295 | 0.000 |
| ("B' London 08:00-09:30 (DST)", 'green rules + vol filter') | 31.000 | 1.000 | -0.128 | -0.173 | -0.281 | 0.000 |
| ('ref green 05:00-05:59 IST', 'RR 2, no BE') | 31.000 | 0.000 | -0.246 | -0.236 | -0.214 | 0.000 |
| ('ref green 05:00-05:59 IST', 'green rules (RR 9, BE 3R)') | 31.000 | 1.000 | -0.240 | -0.228 | -0.263 | 0.000 |
| ('ref green 05:00-05:59 IST', 'green rules + vol filter') | 31.000 | 3.000 | -0.251 | -0.223 | -0.236 | 0.000 |

## Positive in all three periods (any t)

| market | box | setting | trades | win % | design avg R | design t | check avg R | holdout avg R | last 3y avg R | last 3y t |
|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY | ref green 05:00-05:59 IST | green rules + vol filter | 1948 | 25.873 | 0.160 | 1.586 | 0.242 | 0.218 | 0.243 | 1.506 |
| USDJPY | ref green 05:00-05:59 IST | green rules (RR 9, BE 3R) | 4555 | 23.205 | 0.062 | 1.014 | 0.163 | 0.136 | 0.195 | 1.821 |
| USDJPY | B 12:30-14:00 IST | green rules (RR 9, BE 3R) | 4638 | 22.122 | 0.059 | 0.962 | 0.156 | 0.046 | 0.051 | 0.509 |
| GBPJPY | ref green 05:00-05:59 IST | green rules + vol filter | 2088 | 23.755 | 0.076 | 0.769 | 0.043 | 0.072 | 0.083 | 0.565 |
| EURJPY | B 12:30-14:00 IST | green rules + vol filter | 1945 | 22.982 | 0.075 | 0.721 | 0.063 | 0.043 | 0.056 | 0.372 |
| USDJPY | B 12:30-14:00 IST | green rules + vol filter | 1943 | 23.057 | 0.067 | 0.666 | 0.188 | 0.146 | 0.121 | 0.784 |
| AUDJPY | B 12:30-14:00 IST | green rules (RR 9, BE 3R) | 4618 | 22.261 | 0.036 | 0.590 | 0.074 | 0.000 | -0.015 | -0.152 |
| USDJPY | B' London 08:00-09:30 (DST) | green rules + vol filter | 1957 | 23.097 | 0.048 | 0.483 | 0.172 | 0.172 | 0.175 | 1.135 |
| EURJPY | ref green 05:00-05:59 IST | green rules + vol filter | 2042 | 24.045 | 0.036 | 0.360 | 0.086 | 0.016 | 0.003 | 0.024 |
| USDJPY | B' London 08:00-09:30 (DST) | green rules (RR 9, BE 3R) | 4664 | 21.998 | 0.012 | 0.197 | 0.124 | 0.072 | 0.099 | 0.980 |

## Best 15 in the last 3 years (by t)

| market | box | setting | trades | win % | design avg R | design t | check avg R | holdout avg R | last 3y avg R | last 3y t |
|---|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | ref green 05:00-05:59 IST | green rules + vol filter | 2306 | 22.376 | -0.124 | -1.325 | -0.111 | 0.246 | 0.243 | 2.151 |
| XAUUSD | ref green 05:00-05:59 IST | green rules (RR 9, BE 3R) | 4487 | 21.261 | -0.083 | -1.376 | -0.082 | 0.215 | 0.216 | 2.138 |
| USDJPY | ref green 05:00-05:59 IST | green rules (RR 9, BE 3R) | 4555 | 23.205 | 0.062 | 1.014 | 0.163 | 0.136 | 0.195 | 1.821 |
| USDJPY | A 04:30-05:15 IST | green rules + vol filter | 1997 | 22.884 | 0.020 | 0.215 | -0.004 | 0.309 | 0.275 | 1.680 |
| USDJPY | ref green 05:00-05:59 IST | green rules + vol filter | 1948 | 25.873 | 0.160 | 1.586 | 0.242 | 0.218 | 0.243 | 1.506 |
| USDJPY | ref green 05:00-05:59 IST | RR 2, no BE | 4539 | 35.845 | 0.004 | 0.117 | -0.045 | 0.064 | 0.061 | 1.188 |
| USDJPY | B' London 08:00-09:30 (DST) | green rules + vol filter | 1957 | 23.097 | 0.048 | 0.483 | 0.172 | 0.172 | 0.175 | 1.135 |
| USDJPY | B' London 08:00-09:30 (DST) | green rules (RR 9, BE 3R) | 4664 | 21.998 | 0.012 | 0.197 | 0.124 | 0.072 | 0.099 | 0.980 |
| USATECHIDXUSD | B' London 08:00-09:30 (DST) | green rules + vol filter | 2073 | 20.550 | -0.010 | -0.088 | 0.091 | 0.113 | 0.107 | 0.888 |
| USATECHIDXUSD | B 12:30-14:00 IST | green rules + vol filter | 1949 | 20.729 | 0.010 | 0.079 | -0.047 | 0.137 | 0.099 | 0.823 |
| USDJPY | B 12:30-14:00 IST | green rules + vol filter | 1943 | 23.057 | 0.067 | 0.666 | 0.188 | 0.146 | 0.121 | 0.784 |
| AUDJPY | B' London 08:00-09:30 (DST) | green rules + vol filter | 1979 | 23.092 | -0.082 | -0.897 | -0.022 | 0.139 | 0.121 | 0.783 |
| AUDJPY | ref green 05:00-05:59 IST | green rules (RR 9, BE 3R) | 4889 | 22.315 | -0.010 | -0.165 | 0.057 | 0.081 | 0.064 | 0.646 |
| JPNIDXJPY | A 04:30-05:15 IST | RR 2, no BE | 309 | 33.657 | 0.148 | 0.200 | -0.168 | 0.066 | 0.066 | 0.641 |
| USATECHIDXUSD | B 12:30-14:00 IST | green rules (RR 9, BE 3R) | 3276 | 20.330 | -0.114 | -1.266 | -0.007 | 0.103 | 0.058 | 0.602 |
