# Edge hunt — USDJPY clock scan, Nikkei/Nasdaq lead-lag, NFP

Tests and rules in run_edge_hunt.py (all fixed before running).

## 1. Clock scan: 864 tests, survivors (design t ≥ 3.7, check and holdout > 0): **0**

None.


### Weaker candidates (design t ≥ 2, check and holdout > 0): 1 — about 5 expected by luck

| slot (UTC) | hold min | days | side | design n | design avg R | design t | check avg R | check t | holdout avg R | holdout t |
|---|---|---|---|---|---|---|---|---|---|---|
| 23:30 | 180 | month-end | SELL | 160 | 0.220 | 3.280 | 0.172 | 1.905 | 0.065 | 0.426 |

## 2–3. Lead-lag and NFP: 28 tests, survivors: **0**

| test | design n | win % | design avg R | design t | check avg R | check t | holdout avg R | holdout t | survives |
|---|---|---|---|---|---|---|---|---|---|
| JPN225 00:00-01:00 UTC -> USDJPY 2h, |move| > 0.2% | 371 | 45.718 | 0.056 | 1.472 | -0.055 | -2.303 | -0.046 | -1.292 | False |
| NFP USDJPY follow 08:45 -> 10:00 NY | 92 | 49.746 | 0.035 | 0.532 | -0.066 | -1.019 | -0.005 | -0.059 | False |
| NFP EURUSD fade 08:45 -> 12:00 NY | 92 | 47.716 | 0.032 | 0.378 | -0.086 | -0.882 | 0.003 | 0.024 | False |
| JPN225 00:00-01:00 UTC -> USDJPY 1h, |move| > 0.2% | 371 | 45.659 | 0.010 | 0.337 | -0.058 | -3.108 | -0.058 | -2.072 | False |
| NFP XAUUSD follow 08:45 -> 12:00 NY | 91 | 49.223 | 0.010 | 0.111 | -0.031 | -0.315 | 0.084 | 0.432 | False |
| NFP XAUUSD follow 08:45 -> 10:00 NY | 91 | 45.596 | 0.001 | 0.022 | -0.090 | -1.123 | -0.002 | -0.022 | False |
| NFP EURUSD follow 08:45 -> 10:00 NY | 92 | 47.208 | -0.007 | -0.101 | -0.039 | -0.630 | -0.045 | -0.360 | False |
| NFP EURUSD fade 08:45 -> 10:00 NY | 92 | 47.208 | -0.018 | -0.271 | -0.031 | -0.495 | -0.017 | -0.149 | False |
| NFP USDJPY follow 08:45 -> 12:00 NY | 92 | 47.208 | -0.029 | -0.345 | -0.063 | -0.712 | -0.075 | -0.631 | False |
| NFP USDJPY fade 08:45 -> 12:00 NY | 92 | 45.178 | -0.038 | -0.440 | -0.006 | -0.055 | -0.125 | -1.091 | False |
| NFP XAUUSD fade 08:45 -> 12:00 NY | 91 | 45.078 | -0.056 | -0.566 | -0.035 | -0.335 | 0.068 | 0.415 | False |
| JPN225 00:00-01:00 UTC -> USDJPY 2h, |move| > 0.0% | 685 | 44.160 | -0.018 | -0.664 | -0.062 | -3.424 | -0.072 | -2.668 | False |
| NFP EURUSD follow 08:45 -> 12:00 NY | 92 | 47.716 | -0.070 | -0.832 | -0.032 | -0.333 | -0.029 | -0.178 | False |
| Nasdaq 09:30 NY +30m -> USDJPY 1h, |move| > 0.2% | 680 | 46.534 | -0.027 | -0.940 | -0.068 | -2.558 | -0.014 | -0.448 | False |
| JPN225 00:00-00:30 UTC -> USDJPY 2h, |move| > 0.2% | 320 | 44.879 | -0.057 | -1.404 | -0.061 | -2.128 | -0.067 | -1.723 | False |
| Nasdaq 09:30 NY +30m -> USDJPY 2h, |move| > 0.2% | 680 | 44.788 | -0.050 | -1.448 | -0.093 | -3.146 | 0.019 | 0.475 | False |
| NFP XAUUSD fade 08:45 -> 10:00 NY | 91 | 46.114 | -0.125 | -1.711 | -0.023 | -0.333 | -0.036 | -0.392 | False |
| JPN225 00:00-01:00 UTC -> USDJPY 1h, |move| > 0.0% | 685 | 44.581 | -0.038 | -1.799 | -0.065 | -4.638 | -0.072 | -3.343 | False |
| NFP USDJPY fade 08:45 -> 10:00 NY | 92 | 42.640 | -0.120 | -1.955 | -0.057 | -0.867 | -0.093 | -1.083 | False |
| JPN225 00:00-00:30 UTC -> USDJPY 1h, |move| > 0.2% | 320 | 43.194 | -0.067 | -2.052 | -0.062 | -2.608 | -0.065 | -2.130 | False |
| JPN225 00:00-00:30 UTC -> USDJPY 2h, |move| > 0.0% | 690 | 44.588 | -0.064 | -2.309 | -0.069 | -3.396 | -0.064 | -2.175 | False |
| JPN225 00:00-00:30 UTC -> USDJPY 1h, |move| > 0.0% | 690 | 43.958 | -0.065 | -2.884 | -0.064 | -4.000 | -0.050 | -2.176 | False |
| Nasdaq 09:30 NY +30m -> USDJPY 1h, |move| > 0.0% | 1434 | 45.459 | -0.065 | -3.358 | -0.081 | -4.126 | -0.052 | -2.163 | False |
| Nasdaq 09:30 NY +30m -> USDJPY 2h, |move| > 0.0% | 1434 | 43.345 | -0.078 | -3.456 | -0.106 | -4.668 | -0.038 | -1.275 | False |
| Nasdaq 09:30 NY +60m -> USDJPY 1h, |move| > 0.2% | 760 | 42.794 | -0.090 | -3.700 | -0.077 | -3.688 | -0.030 | -1.000 | False |
| Nasdaq 09:30 NY +60m -> USDJPY 2h, |move| > 0.2% | 760 | 43.103 | -0.110 | -3.832 | -0.088 | -3.599 | -0.015 | -0.392 | False |
| Nasdaq 09:30 NY +60m -> USDJPY 2h, |move| > 0.0% | 1434 | 43.384 | -0.103 | -4.954 | -0.098 | -4.998 | -0.042 | -1.504 | False |
| Nasdaq 09:30 NY +60m -> USDJPY 1h, |move| > 0.0% | 1434 | 42.055 | -0.103 | -6.173 | -0.087 | -5.179 | -0.053 | -2.300 | False |
